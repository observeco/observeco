"""`observeco heal` — auto-heal agents: detect, diagnose, fix common failure modes."""
from __future__ import annotations

import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table

from observeco.dirs import hermes_home
from observeco.config import load_config
from observeco.db import Database

console = Console()
HEAL_CIRCUIT: dict[str, dict] = {}
MAX_HEAL_RETRIES = 3
COOLDOWN_HOURS = 4

def _get_flags_dir() -> Path:
    from observeco.dirs import get_data_dir
    p = get_data_dir() / "flags"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _get_heal_log_dir() -> Path:
    from observeco.dirs import get_data_dir
    p = get_data_dir() / "heal"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _write_critical_flag(agent_name: str, failures: int, error: str, cooldown_until: float) -> None:
    flags_dir = _get_flags_dir()
    flag_path = flags_dir / f"{agent_name}-heal-failure.flag"
    cooldown_str = datetime.fromtimestamp(cooldown_until).isoformat()
    flag_path.write_text(
        f"CRITICAL: {agent_name} heal failed {failures}x.\n"
        f"Last error: {error}\n"
        f"Circuit open until: {cooldown_str}\n"
        f"Action required: acknowledge this flag before heal resumes on {agent_name}.\n"
    )
    console.print(f"[bold red]! Critical flag written: {flag_path}[/bold red]")

def _format_ts_md(ts: int) -> str:
    """Format timestamp as YYYYMMDD-HHMM for filenames."""
    return datetime.fromtimestamp(ts).strftime("%Y%m%d-%H%M")

def _snapshot_before_heal(agent_name: str, diagnosis: str, action: str,
                           recent_errors: list, recent_pulses: list,
                           action_timestamp: int) -> Path:
    """Snapshot pre-heal state to an investigation log BEFORE any destructive action.

    Required by spec: "Every healing action preserves the evidence.
    You can audit exactly what happened."

    Creates: ~/.observeco/heal/{agent}-{YYYYMMDD-HHMM}.investigation.md
    """
    heal_dir = _get_heal_log_dir()
    ts_str = _format_ts_md(action_timestamp)
    path = heal_dir / f"{agent_name}-{ts_str}.investigation.md"

    # Collect last 3 errors
    error_lines = []
    for i, e in enumerate(recent_errors[:3], 1):
        msg = e.get("error_message", "") or e.get("message", "?")
        etype = e.get("error_type", "unknown")
        sev = e.get("severity", "unknown")
        e_ts = e.get("timestamp", "?")
        error_lines.append(f"  [{i}] {e_ts} | {etype} ({sev}): {msg[:200]}")

    # Collect last pulse status for 5 ticks
    pulse_lines = []
    for p in recent_pulses[:5]:
        pulse_lines.append(
            f"  - status={p.get('status', '?')}, "
            f"latency={p.get('latency_ms', 0):.0f}ms, "
            f"ts={p.get('timestamp', '?')}"
        )

    text = (
        f"# Heal Investigation: {agent_name}\n"
        f"\n"
        f"Agent '{agent_name}' heal triggered at {datetime.fromtimestamp(action_timestamp).isoformat()}.\n"
        f"\n"
        f"## Diagnosis: {diagnosis}\n"
        f"## Action taken: {action}\n"
        f"\n"
        f"## Pre-heal evidence (saved before action executed)\n"
        f"\n"
        f"Last {min(len(recent_errors), 3)} errors:\n"
        f"{chr(10).join(error_lines) if error_lines else '  (none recorded)'}\n"
        f"\n"
        f"Last health ticks:\n"
        f"{chr(10).join(pulse_lines) if pulse_lines else '  (none recorded)'}\n"
        f"\n"
        f"---\n"
        f"Investigation log: {path}\n"
    )
    path.write_text(text)
    return path


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
        # obs-spec-018: Check restart_log for TOCTOU pattern before crash diagnosis
        try:
            recent = db.get_recent_restarts(agent_name=agent_name, limit=5)
            toctou_count = sum(1 for r in recent if r.get("restart_type") == "toctou")
            if toctou_count >= 2:
                return {"diagnosis": "toctou_loop", "action": "code_fix",
                        "action_args": {"agent_name": agent_name},
                        "message": f"TOCTOU race loop detected ({toctou_count} occurrences). "
                                   "File consumed between fsnotify and .stat(). Code fix needed in the agent's watcher — add guard before sort/filter."}
        except Exception:
            pass
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

    # ── LLM escalation: static patterns found nothing → let LLM try ──
    try:
        return _llm_escalation(agent_name, db, pulses, errors, last_status)
    except Exception:
        pass

    return None


HEAL_ESCALATION_PROMPT = """You are an agent crash diagnostician. Given pulse history, error logs, and system state, diagnose why an agent is failing.

Agent name: {agent_name}
Current status: {status}
Last few statuses: {statuses}
Recent error messages: {errors}
Recent latency (ms): {latencies}

Static diagnosis failed to identify this failure. The agent may have a novel crash pattern not covered by the 7 known patterns (circuit_tripped, toctou_loop, memory_leak, env_broken, overwhelmed, context_drift, memory_debt).

Diagnose the most likely root cause. Respond in this format:
DIAGNOSIS: <one-word label>
ACTION: <restart|cooldown|pip_install|code_fix>
EXPLANATION: <one-line explanation>
CONFIDENCE: <high|medium|low>

If you cannot diagnose, respond with: CANNOT_DIAGNOSE
"""

HEAL_FEEDBACK_PROMPT = """You are a post-heal evaluator. After a healing action was taken on an agent, evaluate whether the agent recovered successfully.

Agent name: {agent_name}
Heal action taken: {action_taken}
Post-heal pulse statuses: {statuses}
Post-heal latencies (ms): {latencies}

Evaluate whether the agent recovered. Respond in ONE line:
- If recovered: "Agent {{name}}: recovered. Diagnosis confirmed: {{root cause}}."
- If still failing: "Agent {{name}}: still degraded ({{brief reason}})."
- If inconclusive: "Agent {{name}}: insufficient data to evaluate."

Keep it concise — one sentence only.
"""

ERROR_TRANSLATION_PROMPT = """You are a technical error translator. Translate the following error message into plain English that a non-technical user can understand.

Error message:
{error_msg}

Respond in ONE sentence, plain English, no jargon. If the error is self-explanatory, say so. Be concise — 20 words max.
"""


def _llm_escalation(agent_name: str, db: Database, pulses: list, errors: list, status: str | None) -> Optional[dict]:
    """Call LLM to diagnose novel failures when static patterns fail."""
    from observeco.llm_service import ask

    # Collect context
    statuses = [p.get("status", "?") for p in pulses[:10]]
    error_msgs = [e.get("error_message", "") or e.get("message", "") for e in errors[:5]]
    latencies = [f"{p.get('latency_ms', 0):.0f}" for p in pulses[:10]]

    response = ask(
        HEAL_ESCALATION_PROMPT.format(
            agent_name=agent_name,
            status=status or "unknown",
            statuses=", ".join(statuses) if statuses else "none",
            errors=" | ".join(error_msgs) if error_msgs else "none",
            latencies=", ".join(latencies) if latencies else "none",
        ),
        "",
        consumer="heal_escalation",
        max_cost_cents=0.02,
        cache_ttl_secs=600,
        tier=1,
    )

    if response is None or "CANNOT_DIAGNOSE" in response:
        return None

    # Parse response
    result = {"diagnosis": "llm_unknown", "action": "restart", "action_args": {"agent_name": agent_name}, "message": "LLM could not identify specific pattern."}
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("DIAGNOSIS:"):
            result["diagnosis"] = f"llm_{line[10:].strip().lower()}"
        elif line.startswith("ACTION:"):
            action = line[7:].strip().lower()
            if action in ("restart", "cooldown", "pip_install", "code_fix"):
                result["action"] = action
            elif action == "acknowledge":
                result["action"] = "acknowledge"
        elif line.startswith("EXPLANATION:"):
            result["message"] = line[12:].strip()
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line[11:].strip().lower()

    return result


def _post_heal_evaluation(agent_name: str, action_taken: str, db: Database) -> None:
    """After a successful heal, wait for recovery and have LLM evaluate the result."""
    try:
        time.sleep(5)
        pulses = db.get_recent_pulses(agent_name, limit=5)
        statuses = [p.get("status", "?") for p in pulses]
        latencies = [f"{p.get('latency_ms', 0):.0f}" for p in pulses]

        from observeco.llm_service import ask
        evaluation = ask(
            HEAL_FEEDBACK_PROMPT.format(
                agent_name=agent_name,
                action_taken=action_taken,
                statuses=", ".join(statuses) if statuses else "none",
                latencies=", ".join(latencies) if latencies else "none",
            ),
            "",
            consumer="heal_feedback",
            max_cost_cents=0.005,
            cache_ttl_secs=3600,
            tier=2,
        )

        if evaluation:
            console.print(f"  [dim]Heal feedback: {evaluation}[/dim]")
            db.log_heal_event(
                agent_name, "heal_feedback", "evaluated",
                duration_ms=0, details=evaluation,
            )
    except Exception:
        pass  # fire-and-forget; LLM feedback is non-critical


def _translate_error(error_msg: str) -> str | None:
    """Translate an obscure error message to plain English via LLM.

    Returns translated text, or None if LLM is unavailable (caller
    should fall back to the raw error message).
    """
    from observeco.llm_service import ask

    try:
        response = ask(
            ERROR_TRANSLATION_PROMPT.format(error_msg=error_msg[:300]),
            "",
            consumer="error_translation",
            max_cost_cents=0.005,
            cache_ttl_secs=3600,
            tier=2,
        )
        return response
    except Exception:
        return None


def translate_error(error_msg: str) -> str:
    """Public API: translate a technical error to plain English.

    Returns the LLM-translated text if available, otherwise the raw
    error message unchanged. Designed to be called from any module
    that displays error messages to users.
    """
    translated = _translate_error(error_msg)
    return translated if translated else error_msg


def _execute_action(action: str, args: dict) -> tuple[bool, str]:
    agent_name = args["agent_name"]
    if action == "restart_with_cap":
        try:
            env = os.environ.copy()
            env.update(args.get("env", {}))
            # ponytail: pgrep/kill are POSIX-only. Windows fallback uses tasklist/taskkill.
            # Upgrade path: add cross-platform process-utils module if more signals needed.
            try:
                result = subprocess.run(["pgrep", "-f", re.escape(agent_name)], capture_output=True, text=True, timeout=5)
            except FileNotFoundError:
                result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {agent_name}"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for pid in result.stdout.strip().split("\n"):
                    try:
                        subprocess.run(["kill", pid], timeout=3)
                    except FileNotFoundError:
                        subprocess.run(["taskkill", "/PID", pid, "/F"], timeout=3)
                time.sleep(1)
            return True, f"Restarted {agent_name} with memory cap"
        except Exception as e:
            return False, str(e)
    elif action == "restart":
        try:
            # ponytail: same pgrep/kill fallback as restart_with_cap
            try:
                result = subprocess.run(["pgrep", "-f", re.escape(agent_name)], capture_output=True, text=True, timeout=5)
            except FileNotFoundError:
                result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {agent_name}"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for pid in result.stdout.strip().split("\n"):
                    try:
                        subprocess.run(["kill", pid], timeout=3)
                    except FileNotFoundError:
                        subprocess.run(["taskkill", "/PID", pid, "/F"], timeout=3)
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
            db = Database()
            conn = db._get_conn()
            now = int(time.time())
            db.reset_breaker(agent_name)
            # Record cooldown as a dedicated event so state reconstruction can handle it
            conn.execute(
                "INSERT INTO circuit_events (agent_name, event_type, payload, created_at) VALUES (?, 'cooldown', ?, ?)",
                (agent_name, str(now + seconds), now),
            )
            conn.commit()
            return True, f"Cooldown set for {seconds}s on {agent_name}"
        except Exception as e:
            return False, str(e)
    elif action == "trim":
        try:
            import sys
            from io import StringIO

            from observeco.chisel.trim import run_trim as _run_trim
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
    hh = hermes_home()
    if hh is None:
        return findings
    config_path = hh / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            yaml.safe_load(config_path.read_text())
        except Exception as e:
            findings.append({"component": "config.yaml", "status": "broken",
                             "message": f"YAML parse error: {e}"})
    env_path = hh / ".env"
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

        # --- SNAPSHOT BEFORE HEAL ---
        # Always snapshot before destructive actions, in ALL modes
        errors = db.get_errors(name, limit=5)
        pulses = db.get_recent_pulses(name, limit=5)
        action_ts = int(time.time())
        snapshot_path = _snapshot_before_heal(
            agent_name=name,
            diagnosis=diagnosis['diagnosis'],
            action=diagnosis['action'],
            recent_errors=errors,
            recent_pulses=pulses,
            action_timestamp=action_ts,
        )
        console.print(f"[dim]Pre-heal snapshot: {snapshot_path}[/dim]")
        # --- END SNAPSHOT ---

        if auto_heal:
            # ponytail: safe_actions allowlist blocks pip_install/code_fix from auto-execution.
            # Upgrade path: add config-driven allowlist (per-agent heal_config table has max_restarts_per_hour already).
            safe_actions = {"restart", "restart_with_cap", "cooldown", "trim", "garden_cleanup"}
            if diagnosis['action'] in safe_actions:
                success, msg = _execute_action(diagnosis['action'], diagnosis['action_args'])
            elif diagnosis['action'] in ("acknowledge", "pip_install", "code_fix"):
                table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                             f"[yellow]Skipped (requires user confirmation)[/yellow]")
                results.append({"agent": name, "status": "skipped_safe", "action": diagnosis['action']})
                continue
            else:
                # Unknown action — skip auto execution
                table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                             "[yellow]Skipped (unknown action)[/yellow]")
                results.append({"agent": name, "status": "skipped_safe", "action": diagnosis['action']})
                continue
            if success:
                table.add_row(name, f"[yellow]{diagnosis['diagnosis']}[/yellow]", diagnosis['action'],
                             f"[green]OK {msg}[/green]")
                results.append({"agent": name, "status": "fixed", "action": diagnosis['action']})
                # Post-heal feedback: wait for recovery, then LLM evaluates
                _post_heal_evaluation(name, diagnosis['action'], db)
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

    # §21: Log heal actions to unified action_log
    import json as _json
    try:
        _db = Database()
        for _r in results:
            _status = _r.get("status", "unknown")
            _agent = _r.get("agent", "unknown")
            _action = _r.get("action", "heal")
            if _status == "fixed":
                _db.log_action(
                    agent_name=_agent, action_type="heal",
                    action_detail=f"L1 restart: {_agent} restarted ({_action})",
                    status="success", triggered_by="daemon",
                    metadata=_json.dumps({"action": _action}),
                )
            elif _status == "failed":
                _db.log_action(
                    agent_name=_agent, action_type="heal",
                    action_detail=f"Heal failed: {_r.get('error', 'unknown')}",
                    status="failure", triggered_by="daemon",
                    metadata=_json.dumps({"error": _r.get("error", "")}),
                )
    except Exception:
        pass  # fire-and-forget
    if failed > 0:
        failed_details = [r for r in results if r.get('status') == 'failed']
        for fd in failed_details:
            err = fd.get('error', 'unknown')
            agent = fd['agent']
            console.print(f"  [red]! {agent}:[/red] heal failed — {err}. [bold]Manual intervention needed.[/bold]")
            hermes_base = hermes_home()
            console.print(f"    [dim]➤ Check agent logs in {hermes_base}/logs/{agent}*.log[/dim]")
            console.print(f"    [dim]➤ Restart manually: [bold]observeco start {agent}[/bold][/dim]")
