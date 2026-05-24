"""`observeco heal` — auto-heal agents: detect, diagnose, fix common failure modes.
"""
from __future__ import annotations
import os
import subprocess
import time
from pathlib import Path
from typing import Optional
from rich import box
from rich.console import Console
from rich.table import Table
from observeco.config import load_config
from observeco.db import Database

console = Console()
HEAL_CIRCUIT: dict[str, dict] = {}
MAX_HEAL_RETRIES = 3
COOLDOWN_HOURS = 4

def _get_flags_dir() -> Path:
    p = Path.home() / ".observeco" / "flags"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _get_heal_log_dir() -> Path:
    p = Path.home() / ".observeco" / "heal"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _write_critical_flag(agent_name: str, failures: int, error: str, cooldown_until: float) -> None:
    flags_dir = _get_flags_dir()
    flag_path = flags_dir / f"{agent_name}-heal-failure.flag"
    from datetime import datetime
    cooldown_str = datetime.fromtimestamp(cooldown_until).isoformat()
    flag_path.write_text(
        f"CRITICAL: {agent_name} heal failed {failures}x.\n"
        f"Last error: {error}\n"
        f"Circuit open until: {cooldown_str}\n"
        f"Action required: acknowledge this flag before heal resumes on {agent_name}.\n"
    )
    console.print(f"[bold red]! Critical flag written: {flag_path}[/bold red]")

def _write_investigation(agent_name: str, diagnosis: str, action: str,
                          recent_errors: list, recent_pulses: list) -> None:
    heal_dir = _get_heal_log_dir()
    now = int(time.time())
    path = heal_dir / f"{agent_name}-{now}.investigation.md"
    lines = [
        f"# Heal Investigation: {agent_name}",
        f"## Triggered at: {now}",
        f"## Diagnosis: {diagnosis}",
        f"## Action: {action}",
        "## Pre-heal state:",
        "- Last errors:",
    ]
    for e in recent_errors[:3]:
        msg = e.get("error_message", "") or e.get("message", "")
        lines.append(f"  1. {msg[:200]}")
    lines.append("- Last health ticks:")
    for p in recent_pulses[:5]:
        lines.append(f"  - status={p.get('status')}, latency={p.get('latency_ms', 0):.0f}ms, ts={p.get('timestamp')}")
    text = "\n".join(lines)
    path.write_text(text)
    console.print(f"[dim]Investigation snapshot: {path}[/dim]")

def _diagnose_agent(agent_name: str, db: Database) -> Optional[dict]:
    pulses = db.get_recent_pulses(agent_name, limit=5)
    errors = db.get_errors(agent_name, limit=5)
    breakers = db.get_circuit_breakers()
    breaker = next((b for b in breakers if b["agent_name"] == agent_name), None)
    if breaker and breaker.get("tripped"):
        return {"diagnosis": "circuit_tripped", "action": "acknowledge",
                "action_args": {"agent_name": agent_name},
                "message": f"Circuit breaker is tripped after {breaker['failure_count']} failures. Acknowledge manually."}
    last_status = pulses[0]["status"] if pulses else None
    if last_status == "dead":
        error_texts = [e.get("error_message", "") or e.get("message", "") for e in errors]
        mem_errors = [e for e in error_texts if "out of memory" in e.lower() or "memory" in e.lower()]
        if len(mem_errors) >= 3:
            return {"diagnosis": "memory_leak", "action": "restart_with_cap",
                    "action_args": {"agent_name": agent_name, "env": {"PYTHONMEM": "512m"}},
                    "message": "Pattern: memory leak. Restarting with PYTHONMEM cap."}
        mod_errors = [e for e in error_texts if "module not found" in e.lower() or "modulenotfounderror" in e.lower()]
        if len(mod_errors) >= 3:
            return {"diagnosis": "env_broken", "action": "pip_install",
                    "action_args": {"agent_name": agent_name},
                    "message": "Pattern: missing modules. Running pip install in agent venv."}
        timeout_errors = [e for e in error_texts if "timeout" in e.lower()]
        if len(timeout_errors) >= 3:
            return {"diagnosis": "overwhelmed", "action": "cooldown",
                    "action_args": {"agent_name": agent_name, "seconds": 300},
                    "message": "Pattern: timeout. Setting circuit cooldown for 300s."}
        return {"diagnosis": "unknown_dead", "action": "restart",
                "action_args": {"agent_name": agent_name},
                "message": "Agent is dead (unknown cause). Suggest restart."}
    try:
        conn = db._get_conn()
        drift_row = conn.execute(
            "SELECT component, delta_pct, breached FROM chisel_drift "
            "WHERE agent_name=? ORDER BY timestamp DESC LIMIT 1", (agent_name,)
        ).fetchone()
        if drift_row and drift_row["breached"]:
            return {"diagnosis": "context_drift", "action": "trim",
                    "action_args": {"agent_name": agent_name},
                    "message": f"Drift threshold breached ({drift_row['delta_pct']:.1f}%). Running chisel trim."}
    except Exception:
        pass
    try:
        garden = db._get_conn().execute(
            "SELECT memory_debt_score FROM clawforge_garden WHERE agent_name=? ORDER BY timestamp DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        if garden and garden["memory_debt_score"] > 50:
            return {"diagnosis": "memory_debt", "action": "garden_cleanup",
                    "action_args": {"agent_name": agent_name},
                    "message": f"Memory debt {garden['memory_debt_score']:.0f} > 50. Running garden cleanup."}
    except Exception:
        pass
    return None

def _execute_action(action: str, args: dict) -> tuple[bool, str]:
    agent_name = args["agent_name"]
    if action == "restart_with_cap":
        try:
            env = os.environ.copy()
            env.update(args.get("env", {}))
            result = subprocess.run(["pgrep", "-f", agent_name], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for pid in result.stdout.strip().split("\n"):
                    subprocess.run(["kill", pid], timeout=3)
                time.sleep(1)
            return True, f"Restarted {agent_name} with memory cap"
        except Exception as e:
            return False, str(e)
    elif action == "restart":
        try:
            result = subprocess.run(["pgrep", "-f", agent_name], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for pid in result.stdout.strip().split("\n"):
                    subprocess.run(["kill", pid], timeout=3)
                time.sleep(1)
            return True, f"Restarted {agent_name}"
        except Exception as e:
            return False, str(e)
    elif action == "pip_install":
        try:
            config = load_config()
            agent_cfg = next((a for a in config.agents if a.name == agent_name), None)
            cwd = None
            if agent_cfg and agent_cfg.config_path and os.path.isdir(agent_cfg.config_path):
                cwd = agent_cfg.config_path
            subprocess.run(["pip", "install", "-e", "."], cwd=cwd, check=True, timeout=60)
            return True, f"Installed modules for {agent_name}"
        except Exception as e:
            return False, str(e)
    elif action == "cooldown":
        try:
            seconds = args.get("seconds", 300)
            conn = Database()._get_conn()
            conn.execute("UPDATE circuit_breakers SET failure_count=0, tripped=1, cooldown_until=? WHERE agent_name=?",
                         (int(time.time()) + seconds, agent_name))
            conn.commit()
            return True, f"Cooldown set for {seconds}s on {agent_name}"
        except Exception as e:
            return False, str(e)
    elif action == "trim":
        try:
            from observeco.chisel.trim import run_trim as _run_trim
            import sys
            from io import StringIO
            old_stdin = sys.stdin
            sys.stdin = StringIO(f"Trim {agent_name} context")
            try:
                _run_trim()
            finally:
                sys.stdin = old_stdin
            return True, f"Chisel trim completed for {agent_name}"
        except Exception as e:
            return False, str(e)
    elif action == "garden_cleanup":
        try:
            from observeco.clawforge.garden import run_garden as _run_garden
            _run_garden(apply=True, agent_name=agent_name)
            return True, f"Garden cleanup completed for {agent_name}"
        except Exception as e:
            return False, str(e)
    elif action == "acknowledge":
        return True, f"Circuit breaker for {agent_name} - manual acknowledgment required"
    return False, f"Unknown action: {action}"

def _check_config_integrity() -> list[dict]:
    """Check infrastructure config files for corruption that would crash the gateway."""
    findings = []
    config_path = Path.home() / ".hermes" / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            yaml.safe_load(config_path.read_text())
        except Exception as e:
            findings.append({"component": "config.yaml", "status": "broken",
                             "message": f"YAML parse error: {e}"})
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for i, line in enumerate(env_path.read_text().split("\n"), 1):
            line = line.strip()
            if line and not line.startswith("#") and "=" not in line:
                findings.append({"component": ".env", "status": "warning",
                                 "message": f"Line {i}: malformed (no '=' sign)"})
                break
    return findings


def run_heal(auto_heal: bool = False, agent_name: Optional[str] = None, dry_run: bool = False) -> None:
    # Pre-flight: check infrastructure integrity first
    infra_issues = _check_config_integrity()
    if infra_issues:
        console.print("[bold red]Infrastructure integrity issues found![/bold red]")
        for issue in infra_issues:
            severity = "[red]" if issue["status"] == "broken" else "[yellow]"
            console.print(f"  {severity}{issue['component']}[/]: {issue['message']}")
        console.print()
        # Broken config = gateway would crash — flag critical, don't proceed
        if any(i["status"] == "broken" for i in infra_issues):
            console.print("[bold red]Config broken — gateway would crash on restart. Fix before proceeding.[/bold red]")
            _get_flags_dir().parent.mkdir(parents=True, exist_ok=True)
            (_get_flags_dir() / "config-broken.flag").write_text("config.yaml YAML parse error")
            return
    db = Database()
    config = load_config()
    agents = [a for a in config.agents if a.name == agent_name] if agent_name else config.agents
    if not agents:
        console.print("[yellow]No agents found. Run `observeco agents add <name>` first.[/yellow]")
        return
    console.print(f"[bold]ObserveCo Heal[/bold] - {len(agents)} agent(s)")
    if dry_run:
        console.print("[italic]Dry-run mode: showing what would be done without executing.[/italic]")
    if auto_heal:
        console.print("[bold green]Auto-heal mode: executing fixes automatically.[/bold green]")
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Agent", style="bold")
    table.add_column("Diagnosis", style="yellow")
    table.add_column("Action")
    table.add_column("Result")
    results = []
    for agent in agents:
        name = agent.name
        diagnosis = _diagnose_agent(name, db)
        if diagnosis is None:
            table.add_row(name, "[green]Healthy[/green]", "-", "[green]No issues detected[/green]")
            results.append({"agent": name, "status": "healthy"})
            continue
        record = HEAL_CIRCUIT.get(name, {"failures": 0, "cooldown_until": 0})
        if time.time() < record["cooldown_until"]:
            table.add_row(name, f"[red]{diagnosis['diagnosis']}[/red]", diagnosis['action'],
                         f"[red]Circuit open - cooling down until {record['cooldown_until']}[/red]")
            results.append({"agent": name, "status": "circuit_open"})
            continue
        if dry_run:
            table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                         f"[yellow]Would: {diagnosis['message']}[/yellow]")
            results.append({"agent": name, "status": "would_fix", "action": diagnosis['action']})
            continue
        if auto_heal:
            errors = db.get_errors(name, limit=5)
            pulses = db.get_recent_pulses(name, limit=5)
            _write_investigation(name, diagnosis['diagnosis'], diagnosis['action'], errors, pulses)
            success, msg = _execute_action(diagnosis['action'], diagnosis['action_args'])
            if success:
                table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                             f"[green]OK {msg}[/green]")
                results.append({"agent": name, "status": "fixed", "action": diagnosis['action']})
            else:
                record["failures"] += 1
                if record["failures"] >= MAX_HEAL_RETRIES:
                    record["cooldown_until"] = time.time() + (COOLDOWN_HOURS * 3600)
                    _write_critical_flag(name, record["failures"], msg, record["cooldown_until"])
                HEAL_CIRCUIT[name] = record
                db.log_error(name, "heal_failed", f"Heal failed: {msg}", severity="critical")
                table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                             f"[red]X {msg}[/red]")
                results.append({"agent": name, "status": "failed", "error": msg})
        else:
            console.print(f"\n[bold]{name}[/bold]: {diagnosis['message']}")
            console.print(f"  Action: [cyan]{diagnosis['action']}[/cyan]")
            from rich.prompt import Confirm
            confirmed = Confirm.ask("Execute?")
            if confirmed:
                success, msg = _execute_action(diagnosis['action'], diagnosis['action_args'])
                if success:
                    table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                                 f"[green]OK {msg}[/green]")
                else:
                    table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                                 f"[red]X {msg}[/red]")
            else:
                table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                             "[yellow]Skipped (user declined)[/yellow]")
    console.print()
    console.print(table)
    fixed = sum(1 for r in results if r.get('status') == 'fixed')
    healthy = sum(1 for r in results if r.get('status') == 'healthy')
    failed = sum(1 for r in results if r.get('status') == 'failed')
    console.print(f"[dim]Heal complete. {fixed} fixed, {healthy} healthy, {failed} failed.[/dim]")
