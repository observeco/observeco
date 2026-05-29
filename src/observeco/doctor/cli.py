"""observeco doctor — CLI for intelligent environment troubleshooting."""
from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .diagnostics import DiagnosticReport, run_diagnostics
from .feedback import collect_fix_outcome, is_telemetry_opted_out
from .llm import (
    LLMFix,
    detect_llm_providers,
    diagnose_with_llm,
    get_auto_provider,
)

doctor_app = typer.Typer(help="Intelligent environment troubleshooter", no_args_is_help=True)
console = Console()


@doctor_app.command(name="run")
def doctor_run(
    auto_fix: bool = typer.Option(False, "--auto-fix", "-y", help="Apply fixes automatically without prompts"),
    provider: str = typer.Option("auto", "--provider", "-p", help="LLM provider: auto, openai, anthropic, google, ollama, none"),
    json_output: bool = typer.Option(False, "--json", help="Output diagnostics as JSON"),
) -> None:
    """Diagnose environment issues and get AI-powered fixes."""
    # 1. Run diagnostics
    console.print("\n🔍 Running diagnostics...\n")
    report = run_diagnostics()

    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
        return

    # Display results
    _display_diagnostics(report)

    if not report.issues:
        console.print("\n[green]✓ All checks passed. No issues found.[/green]")
        return

    # 2. Detect LLM provider
    llm_used = False
    llm_provider_name = "none"

    if provider != "none":
        providers = detect_llm_providers()

        if provider == "auto":
            selected = get_auto_provider(providers)
        else:
            selected = next((p for p in providers if p.name == provider), None)

        if selected and selected.available:
            llm_provider_name = selected.name
            console.print(f"\n🤖 Using {selected.name} for AI-powered diagnosis...")
        else:
            console.print(f"\n[yellow]⚠ LLM provider '{provider}' not available. Using static help.[/yellow]")
            selected = None
    else:
        console.print("\n[yellow]⚠ LLM disabled. Using static help.[/yellow]")
        selected = None

    # 3. Get fixes
    fixes = diagnose_with_llm(report, selected)
    llm_used = selected is not None

    if not fixes:
        console.print("\n[yellow]No fixes available. Check the documentation manually.[/yellow]")
        return

    # 4. Display and apply fixes
    console.print(f"\n📋 {len(fixes)} fix(es) recommended:\n")
    _display_fixes(fixes)

    fixes_applied = 0
    fixes_skipped = 0
    fixes_succeeded = 0
    fixes_failed = 0

    for fix in fixes:
        if fix.fix_command:
            if auto_fix:
                console.print(f"\n[cyan]Running: {fix.fix_command}[/cyan]")
                success = _run_command(fix.fix_command)
                if success:
                    fixes_succeeded += 1
                    console.print("[green]  ✓ Success[/green]")
                else:
                    fixes_failed += 1
                    console.print("[red]  ✗ Failed[/red]")
                fixes_applied += 1
            else:
                if typer.confirm(f"  Run: {fix.fix_command}", default=True):
                    success = _run_command(fix.fix_command)
                    if success:
                        fixes_succeeded += 1
                        console.print("[green]  ✓ Success[/green]")
                    else:
                        fixes_failed += 1
                        console.print("[red]  ✗ Failed[/red]")
                    fixes_applied += 1
                else:
                    fixes_skipped += 1
        elif fix.fix_manual:
            console.print(f"\n[yellow]Manual steps required:[/yellow]\n{fix.fix_manual}")
            fixes_skipped += 1
        else:
            console.print(f"\n[dim]No automated fix available for: {fix.issue}[/dim]")
            fixes_skipped += 1

    # 5. Collect feedback
    if not is_telemetry_opted_out():
        collect_fix_outcome(
            fixes_applied=fixes_applied,
            fixes_skipped=fixes_skipped,
            fixes_succeeded=fixes_succeeded,
            fixes_failed=fixes_failed,
            report=report,
            llm_provider=llm_provider_name,
            llm_used=llm_used,
        )

    # 6. Summary
    console.print(f"\n{'─' * 50}")
    console.print(f"  Applied: {fixes_applied} | Succeeded: {fixes_succeeded} | Failed: {fixes_failed} | Skipped: {fixes_skipped}")

    if fixes_succeeded > 0:
        console.print("\n[dim]Re-run `observeco doctor` to verify fixes.[/dim]")


@doctor_app.command(name="diagnose")
def doctor_diagnose() -> None:
    """Run diagnostics only (no fixes). Quick health check."""
    report = run_diagnostics()
    _display_diagnostics(report)

    if not report.issues:
        console.print("\n[green]✓ All checks passed.[/green]")
    else:
        console.print(f"\n[yellow]⚠ {len(report.issues)} issue(s) found. Run `observeco doctor run` for fixes.[/yellow]")


@doctor_app.command(name="providers")
def doctor_providers() -> None:
    """List available LLM providers."""
    providers = detect_llm_providers()

    table = Table(title="LLM Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Key Source")

    for p in providers:
        if p.name == "ollama":
            source = "Local (localhost:11434)"
        elif p.name == "openai":
            source = "OPENAI_API_KEY"
        elif p.name == "anthropic":
            source = "ANTHROPIC_API_KEY"
        elif p.name == "google":
            source = "GOOGLE_API_KEY"
        else:
            source = "Unknown"

        status = "✓ Available" if p.available else "✗ Not configured"
        table.add_row(p.name, status, source)

    console.print(table)


def _display_diagnostics(report: DiagnosticReport) -> None:
    """Display diagnostic results in a table."""
    table = Table(title="Environment Diagnostics")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    for check in report.checks:
        status_style = {
            "ok": "[green]✓[/green]",
            "warning": "[yellow]⚠[/yellow]",
            "error": "[red]✗[/red]",
        }.get(check.status, "?")
        table.add_row(check.name, status_style, check.message[:60])

    console.print(table)
    console.print(f"\n  OS: {report.os_name} | Python: {report.python_version} | Issues: {len(report.issues)}")


def _display_fixes(fixes: list[LLMFix]) -> None:
    """Display recommended fixes."""
    for i, fix in enumerate(fixes, 1):
        severity_style = {
            "critical": "[red]CRITICAL[/red]",
            "warning": "[yellow]WARNING[/yellow]",
            "info": "[dim]INFO[/dim]",
        }.get(fix.severity, fix.severity)

        console.print(f"  {i}. [{severity_style}] {fix.issue}")
        console.print(f"     {fix.explanation}")
        if fix.fix_command:
            console.print(f"     [cyan]→ {fix.fix_command}[/cyan]")


def _run_command(cmd: str) -> bool:
    """Run a shell command and return success status."""
    import subprocess
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False
