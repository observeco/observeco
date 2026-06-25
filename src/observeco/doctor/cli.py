"""observeco doctor — CLI for intelligent environment troubleshooting."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from .diagnostics import DiagnosticReport, check_data_health, run_diagnostics
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
    data_health: bool = typer.Option(False, "--data-health", help="Run data continuity health checks only"),
) -> None:
    """Diagnose environment issues and get AI-powered fixes."""

    # GS-019: Data health check mode
    if data_health:
        _display_data_health()
        return

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
                success, output = _run_command(fix.fix_command, auto_fix=True)
                if success:
                    fixes_succeeded += 1
                    console.print("[green]  ✓ Success[/green]")
                else:
                    fixes_failed += 1
                    console.print(f"[red]  ✗ {output}[/red]")
                fixes_applied += 1
            else:
                if typer.confirm(f"  Run: {fix.fix_command}", default=True):
                    success, output = _run_command(fix.fix_command)
                    if success:
                        fixes_succeeded += 1
                        console.print("[green]  ✓ Success[/green]")
                    else:
                        fixes_failed += 1
                        console.print(f"[red]  ✗ {output}[/red]")
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


def _display_data_health() -> None:
    """GS-019: Display data continuity health checks."""
    console.print("\n🔍 Running data health checks...\n")

    checks = check_data_health()

    table = Table(title="Data Health Check")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    for check in checks:
        status_style = {
            "ok": "[green]✓[/green]",
            "warning": "[yellow]⚠[/yellow]",
            "error": "[red]✗[/red]",
        }.get(check.status, "?")
        table.add_row(check.name, status_style, check.message[:60])

    console.print(table)

    issues = [c for c in checks if c.status != "ok"]
    if not issues:
        console.print("\n[green]✓ All data health checks passed.[/green]")
    else:
        console.print(f"\n[yellow]⚠ {len(issues)} issue(s) found.[/yellow]")
        for issue in issues:
            if issue.auto_fix:
                console.print(f"  → Fix: {issue.auto_fix}")


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

# --- Command safety ---

# Allowlist of safe command prefixes (validated before execution)
SAFE_COMMAND_PREFIXES = [
    "pip install",
    "pip3 install",
    "pip install --upgrade",
    "pip3 install --upgrade",
    "python -m pip install",
    "python3 -m pip install",
    "echo",
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "du",
    "df",
    "which",
    "mkdir",
    "touch",
    "cp",
    "mv",
    "whoami",
    "uname",
]

# Dangerous patterns that must never be executed
DANGEROUS_PATTERNS = [
    "rm ", "rmdir", "del ", "format ",
    "sudo ", "su ", "chmod ", "chown ",
    "curl ", "wget ", "ssh ", "scp ",
    "eval ", "exec ",
    ";", "&&", "||", "|",
    ">", ">>",
    "$(", "${",
]

# Commands parsed as shlex list (safer than raw string for subprocess.run)
import shlex  # noqa: E402


def _validate_command(cmd: str) -> tuple[bool, str]:
    """Validate a command before execution.

    Returns (is_safe, reason).
    """
    cmd_stripped = cmd.strip()

    # Reject empty commands
    if not cmd_stripped:
        return False, "Empty command"

    # Reject commands with too many parts
    parts = shlex.split(cmd_stripped)
    if len(parts) > 10:
        return False, f"Command too complex ({len(parts)} parts, max 10)"

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_stripped:
            return False, f"Contains dangerous pattern: {pattern}"

    # Check against allowlist
    cmd_lower = cmd_stripped.lower()
    for prefix in SAFE_COMMAND_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            return True, "OK"

    return False, f"Command not in allowlist: {parts[0] if parts else cmd_stripped[:50]}"


def _run_command(cmd: str, auto_fix: bool = False) -> tuple[bool, str]:
    """Run a shell command safely.

    Returns (success, output).
    """
    import subprocess

    # Validate command
    is_safe, reason = _validate_command(cmd)
    if not is_safe:
        return False, f"Command rejected: {reason}"

    try:
        # Parse command string into list for shell=False safety
        try:
            cmd_args = shlex.split(cmd)
        except ValueError as e:
            return False, f"Command parse error: {e}"
        result = subprocess.run(
            cmd_args, shell=False, capture_output=True, text=True, timeout=30,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output[:500]
    except FileNotFoundError:
        return False, f"Command not found: {cmd_args[0]}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 30s"
    except Exception as e:
        return False, f"Error: {e}"


# --- GS-019 §Recovery: Backup/Restore commands ---


@doctor_app.command(name="backup")
def backup_command():
    """Create a backup of the database."""
    from ..db import Database
    db = Database()
    result = db.backup()
    if result:
        backup_dir = db.db_path.parent / "backups"
        console.print(f"[green]✅ Backup created:[/green] {backup_dir}")
    else:
        console.print("[yellow]⚠️  Backup skipped (cooldown active)[/yellow]")


@doctor_app.command(name="restore")
def restore_command(
    backup_file: str = typer.Option(None, help="Specific backup file to restore"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Restore database from backup."""
    from ..db import Database
    db = Database()

    if not force:
        confirm = typer.confirm("This will replace your current database. Continue?")
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Exit()

    result = db.restore(backup_path=backup_file)
    if result["status"] == "restored":
        console.print(f"[green]✅ Restored from {result['from']}[/green] — {result['rows']} rows recovered")
    else:
        console.print(f"[red]❌ Restore failed:[/red] {result['message']}")
        raise typer.Exit(code=1)
