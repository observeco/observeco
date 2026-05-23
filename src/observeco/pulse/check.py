"""Agent liveness detection.

Checks agents from auto-detection + config files, probes them,
displays results as a rich table, and writes to SQLite.
"""

from __future__ import annotations

import subprocess
import time
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table
from rich import box

from observeco.config import load_config, AgentConfig
from observeco.db import Database

console = Console()
db = Database()


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
                cb = db.record_failure(agent.name, error)
                if cb["tripped"]:
                    db.log_error(agent.name, "circuit_tripped",
                                 f"Circuit breaker tripped after {cb['failures']} failures", "error")
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
