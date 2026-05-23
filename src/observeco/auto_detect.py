"""3-tier agent auto-discovery system.

Tier 1: Framework configs (Hermes ~/.hermes/, OpenClaw SOUL.md, Ollama ~/.ollama/)
Tier 2: Explicit observeco.yml in cwd
Tier 3: Manual add via `observeco agents add <name>`

Never shows an error without a next action.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from observeco.config import load_config, write_agent, AgentConfig
from observeco.db import Database

console = Console()
db = Database()


def run_discover(show_all: bool = False) -> None:
    """Run auto-discovery and display found agents."""
    config = load_config()

    if not config.agents:
        console.print("[yellow]No agents detected automatically.[/yellow]")
        console.print()
        console.print("Next steps:")
        console.print("  1. Run [bold]observeco agents add <name>[/bold] to manually add an agent")
        console.print("  2. Create an [bold]observeco.yml[/bold] in your project directory")
        console.print("  3. Ensure your Hermes config is at [bold]~/.hermes/config.yaml[/bold]")
        return

    # Register all detected agents in DB
    for agent in config.agents:
        db.register_agent(agent.name, agent.framework, agent.health_check or "")

    table = Table(title="Auto-Discovered Agents", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Agent Name", style="bold")
    table.add_column("Framework")
    table.add_column("Source")

    for agent in config.agents:
        source = str(agent.config_path or "auto-detected")
        table.add_row(agent.name, agent.framework, source)

    console.print(table)
    console.print(f"\n[dim]{len(config.agents)} agents detected[/dim]")

    if show_all:
        registered = db.get_agents()
        extra = [r for r in registered if r["agent_name"] not in {a.name for a in config.agents}]
        if extra:
            console.print("\n[dim]Also in database:[/dim]")
            for r in extra:
                console.print(f"  {r['agent_name']} ({r['framework']})")


def run_add(name: str, framework: str = "custom", health_check: str = "") -> None:
    """Manually add an agent to the config."""
    agent = AgentConfig(name=name, framework=framework, health_check=health_check)
    write_agent(agent)
    db.register_agent(name, framework, health_check)
    console.print(f"[green]Added agent [bold]{name}[/bold] ({framework})[/green]")
    console.print(f"[dim]Config saved to ~/.observeco/agents.json[/dim]")


def run_list() -> None:
    """List all registered agents from the database."""
    agents = db.get_agents()
    if not agents:
        console.print("[yellow]No agents registered. Run [bold]observeco agents discover[/bold] or [bold]observeco agents add <name>[/bold][/yellow]")
        return

    table = Table(title="Registered Agents", box=box.ROUNDED, header_style="bold blue")
    table.add_column("Name", style="bold")
    table.add_column("Framework")
    table.add_column("Health Check")
    table.add_column("Active")
    table.add_column("Last Seen")

    for a in agents:
        active_str = "✅" if a.get("is_active") else "❌"
        last_seen = str(a.get("last_seen", "-"))
        table.add_row(a["agent_name"], a["framework"],
                      a.get("health_check", "") or "-",
                      active_str, last_seen)

    console.print(table)
