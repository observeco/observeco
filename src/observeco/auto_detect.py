"""3-tier agent auto-discovery system with LLM-powered fallback.

Tier 1: Framework configs (Hermes ~/.hermes/, OpenClaw SOUL.md, Ollama ~/.ollama/)
Tier 2: Explicit observeco.yml in cwd
Tier 3: LLM discovery — scans ps aux / lsof -i / common ports when static returns < 2 agents
Tier 4: Manual add via `observeco agents add <name>`

Never shows an error without a next action.
"""

from __future__ import annotations

import os
import subprocess

from rich import box
from rich.console import Console
from rich.table import Table

from observeco.config import (
    _AGENTS_JSON,  # noqa: E402
    AgentConfig,
    hermes_home,
    load_config,
    write_agent,
)
from observeco.db import Database
from observeco.llm_service import ask

console = Console()
db = Database()


LLM_DISCOVERY_PROMPT = """You are an agent discovery assistant. Given the output of system commands (ps aux, lsof -i, docker ps, common port scans), identify running processes that look like AI agents or agent frameworks.

Look for:
- Python processes running agent frameworks (hermes, openclaw, crewai, langchain, autogen, etc.)
- Node.js processes running bot or agent services
- Ollama models
- Any process listening on common agent ports (3000-9999)
- Processes named after known agents
- Docker containers (listed under "=== Docker containers ===") — these are potential agents running inside containers

For each candidate, provide:
NAME: <short descriptive name>
TYPE: <python|node|ollama|docker|other>
PORT: <port if applicable, or 0>
EVIDENCE: <what command output shows this>
CONFIDENCE: <high|medium|low>

For Docker containers, set TYPE to "docker" and use the container name as NAME.
The EVIDENCE should include the image name.

If nothing looks like an agent, respond with: NONE_FOUND"""


def run_llm_discovery() -> list[dict]:
    """Use LLM to discover agents from running processes.

    Called when static discovery returns < 2 agents.
    Returns list of candidate agent dicts with name, type, port, evidence.
    """
    # Collect system context
    context_parts = []

    try:
        ps = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        # Filter to interesting processes only (Python, Node, agents, servers)
        lines = ps.stdout.split("\n")
        interesting = []
        keywords = ["python", "node", "agent", "ollama", "hermes", "bot",
                    "server", "worker", "daemon", "chat", "llm", "langchain"]
        for line in lines:
            if any(k in line.lower() for k in keywords):
                interesting.append(line)
        if interesting:
            context_parts.append("=== Running processes (filtered) ===")
            context_parts.extend(interesting[:60])  # cap at 60 lines
    except Exception as e:
        # ponytail: process scan is best-effort context. Log so we know it
        # failed (not just "empty"). Upgrade: surface scan failures in output.
        print(f"[WARN] auto_detect: process scan failed: {e}")

    try:
        lsof = subprocess.run(
            ["lsof", "-i", "-P"], capture_output=True, text=True, timeout=5
        )
        # Filter to LISTEN + common ports
        lines = lsof.stdout.split("\n")
        listening = [line for line in lines if "LISTEN" in line]
        context_parts.append("=== Listening ports ===")
        context_parts.extend(listening[:30])  # cap at 30 lines
    except Exception as e:
        # ponytail: port scan is best-effort context. Log so we know it
        # failed (not just "empty"). Upgrade: surface scan failures in output.
        print(f"[WARN] auto_detect: port scan failed: {e}")

    # Check common Hermes paths (using configured home)
    hermes_base = hermes_home()
    hermes_paths = []
    if hermes_base is not None:
        hermes_paths = [
            str(hermes_base / "config.yaml"),
            str(hermes_base / "hermes-agent" / "venv" / "bin"),
        ]
    context_parts.append("=== Hermes paths ===")
    for p in hermes_paths:
        if os.path.exists(p):
            context_parts.append(f"EXISTS: {p}")

    # Check Docker containers — running containers are potential agents
    try:
        docker_ps = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=5,
        )
        if docker_ps.returncode == 0 and docker_ps.stdout.strip():
            context_parts.append("=== Docker containers ===")
            context_parts.extend(docker_ps.stdout.strip().split("\n")[:30])
    except FileNotFoundError:
        pass  # Docker not installed
    except Exception as e:
        # ponytail: docker ps failed (daemon down, perms). Log so we know it
        # failed (not just "no containers"). Upgrade: surface in output.
        print(f"[WARN] auto_detect: docker ps failed: {e}")

    user_context = "\n".join(context_parts)

    response = ask(
        LLM_DISCOVERY_PROMPT,
        user_context,
        consumer="agent_discovery",
        max_cost_cents=0.02,
        cache_ttl_secs=600,  # cache 10min — process state changes slowly
        tier=1,
    )

    if response is None or "NONE_FOUND" in response:
        return []

    # Parse candidates
    candidates = []
    current = {}
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("NAME:"):
            if current:
                candidates.append(current)
            current = {"name": line[5:].strip(), "port": "0"}
        elif line.startswith("TYPE:"):
            current["type"] = line[5:].strip().lower()
        elif line.startswith("PORT:"):
            try:
                current["port"] = int(line[5:].strip())
            except ValueError:
                current["port"] = 0
        elif line.startswith("EVIDENCE:"):
            current["evidence"] = line[9:].strip()
        elif line.startswith("CONFIDENCE:"):
            current["confidence"] = line[11:].strip().lower()

    if current:
        candidates.append(current)

    return candidates


def run_discover(show_all: bool = False) -> None:
    """Run auto-discovery and display found agents."""
    config = load_config()

    if not config.agents or len(config.agents) < 2:
        # Try LLM discovery if static returned few/no agents
        llm_candidates = run_llm_discovery()
        if llm_candidates:
            console.print("[bold cyan]🔍 LLM discovered running processes:[/bold cyan]")
            for c in llm_candidates:
                confidence_color = {"high": "green", "medium": "yellow", "low": "dim"}
                color = confidence_color.get(c.get("confidence", "low"), "dim")
                port_str = f" port {c['port']}" if c.get("port") else ""
                console.print(
                    f"  [{color}]• {c.get('name', '?')} ({c.get('type', '?')}){port_str}[/{color}]"
                )
            console.print()
            console.print("[dim]Run [bold]observeco agents add <name>[/bold] to add any of the above.[/dim]")
            console.print()

    if not config.agents:
        console.print("[yellow]No agents detected automatically.[/yellow]")
        console.print()
        console.print("Next steps:")
        console.print("  1. Run [bold]observeco agents add <name>[/bold] to manually add an agent")
        console.print("  2. Create an [bold]observeco.yml[/bold] in your project directory")
        console.print("  3. Ensure your agent config is at a supported path "
                      "(e.g. ~/.hermes/config.yaml, set via $OBSERVECO_HERMES_HOME)")
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
    console.print(f"[dim]Config saved to {_AGENTS_JSON}[/dim]")


def run_list() -> None:
    """List all registered agents from the database."""
    agents = db.get_agents()
    if not agents:
        console.print("[yellow]No agents registered. Run [bold]observeco agents discover[/bold] "  # noqa: E501
                       "or [bold]observeco agents add <name>[/bold][/yellow]")
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
