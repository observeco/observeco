"""7-day token allocation drift detection.

Compares current token composition against rolling 7-day average,
flags components with >10% drift.
"""

from __future__ import annotations

import time
from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table

from observeco.constants import DRIFT_CRITICAL_PCT as DRIFT_THRESHOLD_PCT
from observeco.db import Database

console = Console()
db = Database()


def run_drift(agent: Optional[str] = None) -> None:
    """Display drift report for all agents or a specific agent."""
    components = ["identity", "skills", "memory", "tools", "guidance"]

    if agent:
        trims = db.get_trims(agent_name=agent, limit=50)
    else:
        trims = db.get_trims(limit=100)

    if not trims:
        console.print("[yellow]No trim data found. Run `observeco chisel trim` to collect data first.[/yellow]")
        return

    # Group by agent
    agents_data: dict[str, list[dict]] = {}
    for t in trims:
        aname = t["agent_name"]
        if aname not in agents_data:
            agents_data[aname] = []
        agents_data[aname].append(t)

    for aname, entries in agents_data.items():
        if agent and aname != agent:
            continue

        now = time.time()
        week_ago = now - 7 * 86400

        # Latest entry = most recent
        latest = entries[0]
        # 7-day average from entries in the last week
        week_entries = [e for e in entries if e["timestamp"] >= week_ago]
        if not week_entries:
            week_entries = entries

        table = Table(title=f"Chisel Drift — {aname}", box=box.ROUNDED, header_style="bold magenta")
        table.add_column("Component", style="bold")
        table.add_column("Current", justify="right")
        table.add_column("7d Avg", justify="right")
        table.add_column("Δ%", justify="right")
        table.add_column("Breach")

        for comp in components:
            current = latest.get(f"{comp}_tokens", 0) if comp != "guidance" else latest.get("guidance_tokens", 0)
            week_vals = [e.get(f"{comp}_tokens" if comp != "guidance" else "guidance_tokens", 0)
                        for e in week_entries]
            week_avg = int(sum(week_vals) / max(len(week_vals), 1))
            delta_pct = ((current - week_avg) / max(week_avg, 1)) * 100

            breached = abs(delta_pct) > DRIFT_THRESHOLD_PCT
            delta_str = f"{delta_pct:+.1f}%"
            breach_str = "🔴 BREACH" if breached else "✅ OK"

            db.log_drift(aname, comp, current, week_avg, delta_pct, breached)

            table.add_row(
                comp.capitalize(),
                str(current),
                str(week_avg),
                delta_str,
                breach_str,
            )

        console.print(table)
