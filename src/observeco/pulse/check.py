"""Agent liveness detection.

Checks agents from auto-detection + config files, probes them,
displays results as a rich table, and writes to SQLite.

Also classifies daemon restarts (obs-spec-018): healthy/TOCTOU/crash.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import httpx
from rich import box
from rich.console import Console
from rich.table import Table

from observeco.config import AgentConfig, load_config
from observeco.db import Database

console = Console()
db = Database()


# ---------------------------------------------------------------------------
# obs-spec-018: Crash Classification
# ---------------------------------------------------------------------------

def classify_restart(agent_name: str, error_message: str = "",
                     exit_code: int = -1) -> tuple[str, str, str]:
    """Classify a daemon restart into healthy/TOCTOU/crash.

    Returns (restart_type, snippet, evidence).

    restart_type is one of: 'healthy', 'toctou', 'crash'
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

    # 6. Duration heuristic: no data — default to healthy for KeepAlive patterns
    return ("healthy", log_lines[:500], evidence)


def _find_agent_log(agent_name: str) -> Path | None:
    """Find the most recent log file for an agent."""
    log_dirs = [
        Path.home() / ".hermes" / "logs",
        Path("/var/log"),
        Path("/tmp"),
    ]
    for d in log_dirs:
        if not d.exists():
            continue
        candidates = sorted(d.glob(f"{agent_name}*.log"),
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

def _probe_agent(agent: AgentConfig) -> tuple[str, float, str]:
    """Probe a single agent and return (status, latency_ms, error_message)."""
    start = time.time()

    # 1. If health check is a URL
    if agent.health_check and agent.health_check.startswith(("http://", "https://")):
        try:
            resp = httpx.get(agent.health_check, timeout=10.0)
            latency = (time.time() - start) * 1000
            if resp.status_code < 500:
                return ("alive", latency, "")
            else:
                return ("error", latency, f"HTTP {resp.status_code}")
        except httpx.TimeoutException:
            latency = (time.time() - start) * 1000
            return ("dead", latency, "timeout")
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ("error", latency, str(e)[:200])

    # 2. If health check is a command
    if agent.health_check and not agent.health_check.startswith(("http://", "https://")):
        try:
            result = subprocess.run(
                agent.health_check, shell=True, capture_output=True, text=True, timeout=10
            )
            latency = (time.time() - start) * 1000
            if result.returncode == 0:
                return ("alive", latency, "")
            else:
                return ("dead", latency, result.stderr[:200] or result.stdout[:200])
        except subprocess.TimeoutExpired:
            latency = (time.time() - start) * 1000
            return ("dead", latency, "timeout")
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ("error", latency, str(e)[:200])

    # 3. No explicit check: probe by process name
    try:
        result = subprocess.run(
            ["pgrep", "-f", agent.name],
            capture_output=True, text=True, timeout=5,
        )
        latency = (time.time() - start) * 1000
        if result.returncode == 0:
            return ("alive", latency, "")
        else:
            return ("dead", latency, "no matching process")
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ("error", latency, str(e)[:200])


# ---------------------------------------------------------------------------
# Main check function
# ---------------------------------------------------------------------------

def run_check(watch: bool = False) -> None:
    """Run agent liveness check and display results."""
    config = load_config()

    if not config.agents:
        console.print("[yellow]No agents detected. Run `observeco agents add <name>` to add one.[/yellow]")
        console.print("Searched: ~/.hermes/config.yaml, ~/.hermes/agents/, SOUL.md, ~/.observeco/agents.json")
        return

    def _do_check() -> list[dict]:
        results = []
        for agent in config.agents:
            status, latency, error = _probe_agent(agent)
            db.log_pulse(agent.name, status, latency, error, agent.framework)

            if status == "dead":
                # obs-spec-018: Classify the restart before recording failure
                rtype, snippet, evidence = classify_restart(agent.name, error)

                # Log to restart_log regardless
                db.log_restart(
                    agent_name=agent.name,
                    restart_type=rtype,
                    duration_ms=int(latency),
                    crash_log_snippet=snippet,
                    evidence=evidence,
                )

                # Only record circuit breaker failure for real crashes
                if rtype == "crash":
                    cb = db.record_failure(agent.name, error)
                    if cb["tripped"]:
                        db.log_error(agent.name, "circuit_tripped",
                                     f"Circuit breaker tripped after {cb['failures']} failures", "error")
                else:
                    # TOCTOU or healthy restart: auto-reset breaker so they don't accumulate
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
    console.print(f"[dim]{alive_count}/{len(results)} agents alive[/dim]")
