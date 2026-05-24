"""Circuit breaker — N-failure state machine."""

from __future__ import annotations

from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table

from observeco.db import Database

console = Console()
db = Database()


def run_circuit(reset: Optional[str] = None, threshold: Optional[str] = None) -> None:
    """Display circuit breaker state or modify breakers."""
    if reset:
        db.reset_breaker(reset)
        cb = db.get_circuit_breakers()
        for b in cb:
            if b["agent_name"] == reset:
                console.print(f"[green]Reset circuit breaker for [bold]{reset}[/bold][/green]")
                return
        console.print(f"[green]Reset circuit breaker for [bold]{reset}[/bold] (new)[/green]")
        return

    if threshold:
        if ":" not in threshold:
            console.print("[red]Usage: --threshold <agent>:<n>[/red]")
            return
        agent, n_str = threshold.split(":", 1)
        try:
            n = int(n_str)
        except ValueError:
            console.print("[red]Threshold must be an integer[/red]")
            return
        db.set_threshold(agent, n)
        console.print(f"[green]Set threshold for [bold]{agent}[/bold] to {n} failures[/green]")
        return

    # Display all breakers
    breakers = db.get_circuit_breakers()
    if not breakers:
        console.print("[dim]No circuit breakers recorded yet. Run `observeco pulse check` first.[/dim]")
        return

    table = Table(title="Circuit Breakers", box=box.ROUNDED, header_style="bold yellow")
    table.add_column("Agent", style="bold")
    table.add_column("Failures", justify="center")
    table.add_column("Max Retries", justify="center")
    table.add_column("Tripped", justify="center")
    table.add_column("Cooldown Until")
    table.add_column("Last Error")

    for b in breakers:
        tripped_str = "🔴 TRIPPED" if b["tripped"] else "✅ OK"
        cooldown = b["cooldown_until"]
        cooldown_str = str(cooldown) if cooldown else "-"
        error = (b.get("last_failure_error") or "")[:60]
        table.add_row(
            b["agent_name"],
            str(b["failure_count"]),
            str(b["max_retries"]),
            tripped_str,
            cooldown_str,
            error,
        )

    console.print(table)
