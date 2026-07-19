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

from observeco.db import Database

console = Console()
db = Database()


def run_drift(agent: Optional[str] = None) -> None:
    """Display drift report for all agents or a specific agent."""
    components = ["identity", "skills", "memory", "tools", "guidance"]
    FLOOR = 50

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
        two_weeks_ago = now - 14 * 86400

        # Use time-based query for accurate 7-day window
        all_entries = db.get_trims_since(aname, week_ago)
        if not all_entries or len(all_entries) < 2:
            all_entries = entries

        latest = all_entries[-1]  # last in ASC order = most recent
        week_entries = all_entries

        # Old entries for week-over-week
        old_all = db.get_trims_since(aname, two_weeks_ago)
        old_entries = [e for e in old_all if e["timestamp"] < week_ago]

        table = Table(title=f"Chisel Drift — {aname}", box=box.ROUNDED, header_style="bold magenta")
        table.add_column("Component", style="bold")
        table.add_column("Current", justify="right")
        table.add_column("7d Avg", justify="right")
        table.add_column("Δ% (A)", justify="right")
        table.add_column("WoW% (B)", justify="right")
        table.add_column("Δ tok (C)", justify="right")
        table.add_column("Breach")

        for comp in components:
            current = latest.get(f"{comp}_tokens", 0) if comp != "guidance" else latest.get("guidance_tokens", 0)
            week_vals = [e.get(f"{comp}_tokens" if comp != "guidance" else "guidance_tokens", 0)
                        for e in week_entries]
            week_avg = int(sum(week_vals) / max(len(week_vals), 1))

            # Option A: Rolling window with floor
            delta_pct = ((current - week_avg) / max(week_avg, FLOOR)) * 100
            delta_tokens = current - week_avg
            breached = abs(delta_tokens) > 50 and abs(delta_pct) > 10.0

            # Option B: Week-over-week
            wow_str = "—"
            if old_entries and len(old_entries) >= 2:
                old_vals = [e.get(f"{comp}_tokens" if comp != "guidance" else "guidance_tokens", 0)
                           for e in old_entries]
                last_avg = int(sum(old_vals) / max(len(old_vals), 1))
                wow_pct = ((week_avg - last_avg) / max(last_avg, FLOOR)) * 100
                wow_str = f"{wow_pct:+.1f}%"

            # Option C: Absolute tokens
            abs_str = f"{delta_tokens:+d}"

            delta_str = f"{delta_pct:+.1f}%"
            breach_str = "🔴 BREACH" if breached else "✅ OK"

            db.log_drift(aname, comp, current, week_avg, delta_pct, breached, method="rolling")
            db.log_drift(aname, comp, current, week_avg, float(delta_tokens), abs(delta_tokens) > 50, method="absolute")
            if old_entries and len(old_entries) >= 2:
                old_vals = [e.get(f"{comp}_tokens" if comp != "guidance" else "guidance_tokens", 0)
                           for e in old_entries]
                last_avg = int(sum(old_vals) / max(len(old_vals), 1))
                wow_pct = ((week_avg - last_avg) / max(last_avg, FLOOR)) * 100
                db.log_drift(aname, comp, week_avg, last_avg, wow_pct, abs(week_avg - last_avg) > 50 and abs(wow_pct) > 10.0, method="wow")

            table.add_row(
                comp.capitalize(),
                str(current),
                str(week_avg),
                delta_str,
                wow_str,
                abs_str,
                breach_str,
            )

        console.print(table)
