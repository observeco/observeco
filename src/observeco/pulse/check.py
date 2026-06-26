"""Agent liveness detection.

Checks agents from auto-detection + config files, probes them,
displays results as a rich table, and writes to SQLite.

Also classifies daemon restarts (obs-spec-018): healthy/TOCTOU/crash.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table

from observeco.config import AgentConfig, hermes_home, load_config
from observeco.db import Database
from observeco.probe.registry import ProbeResult, resolve_probe

console = Console()
db = Database()


# ---------------------------------------------------------------------------
# obs-spec-018: Crash Classification
# ---------------------------------------------------------------------------

def classify_restart(agent_name: str, error_message: str = "",
                     exit_code: int = -1) -> tuple[str | None, str, str]:
    """Classify a daemon restart into healthy/TOCTOU/crash.

    Returns (restart_type, snippet, evidence).
    restart_type is one of: 'healthy', 'toctou', 'crash', or None if no
    evidence of a restart type can be determined.

    IMPORTANT: None means "we detected the agent is dead but have no evidence
    of what caused it." This is NOT the same as a healthy restart. The caller
    must NOT log a restart entry when type is None — dead != restarted.
    """
    # 1. Try to read agent logs for contextual evidence
    crash_log_path = _find_agent_log(agent_name)
    log_lines = ""
    if crash_log_path:
        try:
            log_lines = _read_last_n_lines(str(crash_log_path), 30)
        except Exception:
            pass

    evidence = ""
    if crash_log_path:
        evidence = f"log:{crash_log_path}"

    # 2. Exit code analysis
    if exit_code == 0:
        return ("healthy", log_lines[:500], evidence)

    # 3. TOCTOU detection: FileNotFoundError + .stat() pattern
    if "FileNotFoundError" in log_lines and ".stat()" in log_lines:
        return ("toctou", log_lines[:500], evidence)

    # 4. Check error_message from pulse probe
    if "FileNotFoundError" in error_message and "stat" in error_message:
        return ("toctou", error_message[:500], evidence)

    # 5. Known crash signals in log
    for sig in ["SIGSEGV", "SIGKILL", "SIGABRT", "SIGTERM"]:
        if sig in log_lines or sig in error_message:
            return ("crash", log_lines[:500], evidence)

    if "OutOfMemoryError" in log_lines or "MemoryError" in log_lines \
       or "OutOfMemoryError" in error_message or "MemoryError" in error_message:
        return ("crash", log_lines[:500], evidence)

    for pat in ["ModuleNotFoundError", "PermissionError",
                "config parse error", "config corruption"]:
        if pat in log_lines or pat in error_message:
            if ".stat()" not in log_lines and "FileNotFoundError" not in log_lines:
                return ("crash", log_lines[:500], evidence)

    # 6. No evidence found — return None.
    # The caller skips logging when rtype is None, so this death is invisible
    # in the restart quality tab. That's honest: we don't know why it died.
    # Upgrade path: add duration_ms parameter and classify sub-second restarts
    # as healthy even without log evidence.
    return (None, log_lines[:500], evidence)


def _find_agent_log(agent_name: str) -> Path | None:
    """Find the most recent log file for an agent.

    Uses precise naming patterns to avoid false matches (e.g. 'kanban_ack.log'
    matching 'kanban'). Searches in order of preference:
      1. {agent_name}_agent.log   (e.g. dreamer_agent.log)
      2. {agent_name}.log         (e.g. gateway.log)
      3. {agent_name}_daemon.log  (e.g. dreamer_daemon.log)
    """
    log_dirs = [
        d / "logs" if d else None
        for d in [hermes_home(), Path("/var/log"), Path("/tmp")]
    ]
    log_dirs = [d for d in log_dirs if d is not None]
    # Precise patterns — no fuzzy globs
    patterns = [
        f"{agent_name}_agent.log",
        f"{agent_name}.log",
        f"{agent_name}_daemon.log",
    ]
    for d in log_dirs:
        if not d.exists():
            continue
        for pat in patterns:
            candidates = sorted(d.glob(pat),
                                key=lambda p: p.stat().st_mtime if p.exists() else 0,
                                reverse=True)
            if candidates:
                return candidates[0]
    return None


def _read_last_n_lines(path: str, n: int = 20) -> str:
    """Read last N lines from a file efficiently."""
    p = Path(path)
    if not p.exists():
        return ""
    # Use tail for large files, fallback to python for small ones
    try:
        result = subprocess.run(
            ["tail", "-n", str(n), path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    # Fallback
    try:
        lines = p.read_text().splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Agent Probing
# ---------------------------------------------------------------------------

def _probe_agent(agent: AgentConfig) -> tuple[str, float, str, str]:
    """Probe a single agent and return (status, latency_ms, error_message, metadata_json).

    Delegates to the Probe Driver Registry (probe/registry.py) —
    resolves the agent's health_check scheme to the correct typed probe.
    """
    start = time.time()
    try:
        probe = resolve_probe(agent)
        result: ProbeResult = probe.probe(agent, timeout=10.0)
        # Convert ProbeResult back to legacy 4-tuple for backward compat
        return (result.status, result.latency_ms, result.error, result.metadata)
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ("error", latency, str(e)[:200], "")


# ---------------------------------------------------------------------------
# Main check function
# ---------------------------------------------------------------------------

def run_check(watch: bool = False) -> None:
    """Run agent liveness check and display results."""
    config = load_config()

    if not config.agents:
        console.print("[yellow]No agents detected. Run `observeco agents add <name>` to add one.[/yellow]")
        hermes_base = hermes_home()
        console.print(f"Searched: {hermes_base}/config.yaml, {hermes_base}/agents/, "
                      "SOUL.md, ~/.observeco/agents.json")
        return

    def _do_check() -> list[dict]:
        results = []
        for agent in config.agents:
            status, latency, error, metadata_json = _probe_agent(agent)
            db.log_pulse(agent.name, status, latency, error, agent.framework, metadata_json=metadata_json)

            if status == "dead":
                # obs-spec-018: Classify the restart before recording failure
                rtype, snippet, evidence = classify_restart(agent.name, error)

                # Only log restart when we have positive evidence of a type.
                # None means "agent is dead but we can't determine cause" —
                # that's NOT the same as a restart. Dead != restarted.
                if rtype is not None:
                    db.log_restart(
                        agent_name=agent.name,
                        restart_type=rtype,
                        duration_ms=int(latency),
                        crash_log_snippet=snippet,
                        evidence=evidence,
                    )

                # Circuit breaker logic
                if rtype == "crash":
                    cb = db.record_failure(agent.name, error)
                    if cb["tripped"]:
                        db.log_error(agent.name, "circuit_tripped",
                                     f"Circuit breaker tripped after {cb['failures']} failures", "error")
                elif rtype in ("healthy", "toctou"):
                    # Known safe restart: auto-reset breaker so they don't accumulate
                    db.reset_breaker(agent.name)

            results.append({
                "name": agent.name,
                "framework": agent.framework,
                "status": status,
                "latency": latency,
                "error": error,
            })
        return results

    if watch:
        for cycle in range(3):
            if cycle > 0:
                time.sleep(5)
            results = _do_check()
            _display_results(results, cycle=cycle + 1)
    else:
        results = _do_check()
        _display_results(results)


def _display_results(results: list[dict], cycle: int = 0) -> None:
    """Display pulse check results as a rich table."""
    title = f"Agent Pulse Check [dim](Cycle {cycle})[/dim]" if cycle else "Agent Pulse Check"
    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Agent", style="bold")
    table.add_column("Framework", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Latency", justify="right")
    table.add_column("Error")

    alive_count = 0
    for r in results:
        status_icon = {"alive": "🟢 alive", "dead": "🔴 dead", "error": "🟡 error"}.get(
            r["status"], "⚪ unknown"
        )
        latency_str = f"{r['latency']:.0f}ms" if r["latency"] > 0 else "-"
        table.add_row(
            r["name"],
            r["framework"],
            status_icon,
            latency_str,
            r["error"][:60] if r["error"] else "",
        )
        if r["status"] == "alive":
            alive_count += 1

    console.print(table)

    # ── Recommendation footer ──
    dead_agents = [r["name"] for r in results if r["status"] == "dead"]
    error_agents = [r["name"] for r in results if r["status"] == "error"]
    if dead_agents:
        console.print(f"[red]🔴 {len(dead_agents)} agent(s) dead: {', '.join(dead_agents)}[/red]")
        console.print("  [dim]➤ Run [bold]observeco heal[/bold] to diagnose and attempt auto-recovery.[/dim]")
        console.print("  [dim]➤ Or start manually: [bold]observeco start <agent>[/bold][/dim]")
    if error_agents:
        console.print(f"[yellow]🟡 {len(error_agents)} agent(s) in error: {', '.join(error_agents)}[/yellow]")
        console.print("  [dim]➤ Run [bold]observeco heal --diagnose <agent>[/bold] to investigate.[/dim]")
        console.print("  [dim]➤ Check agent logs for crash or config issues.[/dim]")
    if not dead_agents and not error_agents:
        console.print(f"[dim]{alive_count}/{len(results)} agents alive — all clear.[/dim]")

    # ── Signal quality disclosure ──
    console.print(f"[dim]{len(results)} agent(s) checked. Results based on live probe — no stored history.[/dim]"
                  f"[dim] For confidence scores and FP/FN risk, visit [bold]observeco dashboard[/bold].[/dim]")
