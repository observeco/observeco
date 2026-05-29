"""ObserveCo CLI — runtime observability for AI agent systems."""

from typing import Optional

import typer

app = typer.Typer(
    name="observeco",
    help="Runtime observability for AI agent systems — pulse, circuit breaker, token compression, dashboard",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

def _version_callback(value: bool) -> None:
    if value:
        from observeco import __version__
        print(f"observeco v{__version__}")
        raise typer.Exit()

@app.callback()
def main_callback(
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit", callback=_version_callback),
) -> None:
    """ObserveCo — Runtime observability for AI agent systems."""
    pass

# -- Pulse subcommands --

pulse_app = typer.Typer(help="Agent health monitoring & circuit breakers", no_args_is_help=True)
app.add_typer(pulse_app, name="pulse")

@pulse_app.command(name="check")
def pulse_check(
    watch: bool = typer.Option(False, "--watch", "-w", help="Poll every 5s for 3 cycles"),
) -> None:
    """Check agent liveness — alive/dead/error status per agent."""
    from observeco.pulse.check import run_check
    run_check(watch=watch)

@pulse_app.command(name="circuit")
def pulse_circuit(
    reset: Optional[str] = typer.Option(None, "--reset", "-r", help="Reset circuit breaker for agent"),
    threshold: Optional[str] = typer.Option(None, "--threshold", "-t", help="Set max retries for agent (format: <agent>:<n>)"),
) -> None:
    """Show circuit breaker state or reset/trip thresholds."""
    from observeco.pulse.circuit import run_circuit
    run_circuit(reset=reset, threshold=threshold)

# -- Chisel subcommands --

chisel_app = typer.Typer(help="System prompt compression & token monitoring", no_args_is_help=True)
app.add_typer(chisel_app, name="chisel")

@chisel_app.command(name="trim")
def chisel_trim() -> None:
    """Compress system prompt from stdin — token breakdown & savings ratio."""
    from observeco.chisel.trim import run_trim
    run_trim()

@chisel_app.command(name="drift")
def chisel_drift(
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent name"),
) -> None:
    """Show 7-day token allocation drift per component."""
    from observeco.chisel.drift import run_drift
    run_drift(agent=agent_name)


@chisel_app.command(name="skills")
def chisel_skills() -> None:
    """Audit all Hermes skill files — token cost ranked by total tokens."""
    from observeco.chisel.trim import run_skills
    run_skills()

# -- ClawForge subcommands --

clawforge_app = typer.Typer(help="OpenClaw context profiler & memory hygiene", no_args_is_help=True)
app.add_typer(clawforge_app, name="clawforge")

@clawforge_app.command(name="profile")
def clawforge_profile(
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to profile"),
) -> None:
    """Show context composition for OpenClaw agents (MEMORY.md, skills, workspace)."""
    from observeco.clawforge.profile import run_profile
    run_profile(agent_name=agent_name)

@clawforge_app.command(name="load")
def clawforge_load(
    probe: bool = typer.Option(False, "--probe", help="Dry-run intent-aware classifier"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to classify"),
) -> None:
    """Test intent-aware context classification."""
    from observeco.clawforge.load import run_load
    run_load(probe=probe, message=message)

@clawforge_app.command(name="garden")
def clawforge_garden(
    apply: bool = typer.Option(False, "--apply", help="Execute suggested memory hygiene actions"),
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to audit"),
) -> None:
    """Scan MEMORY.md for duplicates, contradictions, stale entries."""
    from observeco.clawforge.garden import run_garden
    run_garden(apply=apply, agent_name=agent_name)

# -- Generic aliases (framework-agnostic naming) --
#
# These alias internal-branded commands to generic names so users
# don't need to know what "chisel" or "clawforge" means.
#
#   observeco context trim    -> chisel trim
#   observeco context drift   -> chisel drift
#   observeco context skills  -> chisel skills
#   observeco context profile -> clawforge profile
#   observeco context load    -> clawforge load
#   observeco memory garden   -> clawforge garden

context_app = typer.Typer(help="System prompt management — trim, drift, profile, load", no_args_is_help=True)
app.add_typer(context_app, name="context")

@context_app.command(name="trim")
def context_trim() -> None:
    """Compress system prompt — token breakdown & savings ratio."""
    from observeco.chisel.trim import run_trim
    run_trim()

@context_app.command(name="drift")
def context_drift(
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent name"),
) -> None:
    """Show 7-day token allocation drift per component."""
    from observeco.chisel.drift import run_drift
    run_drift(agent=agent_name)

@context_app.command(name="skills")
def context_skills() -> None:
    """Audit all skill files — token cost ranked by total tokens."""
    from observeco.chisel.trim import run_skills
    run_skills()

@context_app.command(name="profile")
def context_profile(
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to profile"),
) -> None:
    """Show context composition per agent (MEMORY.md, skills, workspace)."""
    from observeco.clawforge.profile import run_profile
    run_profile(agent_name=agent_name)

@context_app.command(name="load")
def context_load(
    probe: bool = typer.Option(False, "--probe", help="Dry-run intent-aware classifier"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to classify"),
) -> None:
    """Test intent-aware context classification."""
    from observeco.clawforge.load import run_load
    run_load(probe=probe, message=message)

memory_app = typer.Typer(help="Memory hygiene — audit and clean agent memory", no_args_is_help=True)
app.add_typer(memory_app, name="memory")

@memory_app.command(name="garden")
def memory_garden(
    apply: bool = typer.Option(False, "--apply", help="Execute suggested memory hygiene actions"),
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to audit"),
) -> None:
    """Scan MEMORY.md for duplicates, contradictions, stale entries."""
    from observeco.clawforge.garden import run_garden
    run_garden(apply=apply, agent_name=agent_name)

# -- Graph subcommands --

from observeco.graph.cli import graph_app

app.add_typer(graph_app, name="graph")

# -- Watch subcommand --

@app.command(name="watch")
def watch_daemon(
    interval: int = typer.Option(30, "--interval", "-i", help="Poll interval in seconds"),
    once: bool = typer.Option(False, "--once", help="Single pass and exit"),
) -> None:
    """Auto-collect agent health data — runs in background.

    Polls registered agents every N seconds, auto-discovers new agents,
    writes to SQLite. Dashboard auto-populates within 60s.
    """
    from observeco.watch import run_watch
    run_watch(interval=interval, once=once)


# -- Dashboard subcommand --

@app.command(name="dashboard")
def serve_dashboard(
    port: int = typer.Option(9119, "--port", "-p", help="Dashboard port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Dashboard bind address"),
    static: bool = typer.Option(False, "--static", help="Generate static HTML and exit"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser (headless/server mode)"),
) -> None:
    """Launch the ObserveCo dashboard (FastAPI + htmx)."""
    from observeco.dashboard.server import serve
    serve(host=host, port=port, static=static, no_browser=no_browser)


# -- Heal command (v1.1) --

@app.command(name="heal")
def heal_command(
    auto_heal: bool = typer.Option(False, "--auto-heal", help="Auto-execute fixes without prompting"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Target specific agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
) -> None:
    """Auto-heal agents — detect, diagnose, and fix common failure modes."""
    from observeco.heal import run_heal
    run_heal(auto_heal=auto_heal, agent_name=agent, dry_run=dry_run)


# -- Snapshot command (v1.1) --

@app.command(name="snapshot")
def snapshot_command(
    name: str = typer.Argument(..., help="Snapshot name/slug"),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output directory"),
) -> None:
    """Generate living documentation from your agent ecosystem data."""
    from observeco.snapshot import run_snapshot
    run_snapshot(snapshot_name=name, output_dir=out)


# -- Feedback command (v1.1) --

@app.command(name="feedback")
def feedback_command(
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Feedback type (bug|feature|ux|docs|performance|other)"),
    summary: Optional[str] = typer.Option(None, "--summary", "-s", help="One-line summary"),
    detail: Optional[str] = typer.Option(None, "--detail", "-d", help="Detailed description or logs"),
    severity: Optional[str] = typer.Option(None, "--severity", help="blocked|annoying|minor|suggestion"),
    non_interactive: bool = typer.Option(False, "--yes", "-y", help="Skip interactive prompts"),
    send: bool = typer.Option(False, "--send", help="Force send even if previously saved"),
) -> None:
    """Send feedback — bug report, feature suggestion, or UX issue."""
    from observeco.feedback import run_feedback
    run_feedback(
        fb_type=type,
        summary=summary,
        detail=detail,
        severity=severity,
        interactive=not non_interactive,
        send=send,
    )


# -- Telemetry subcommand --
telemetry_app = typer.Typer(help="Central feedback telemetry server")
app.add_typer(telemetry_app, name="telemetry")


@telemetry_app.command(name="serve")
def telemetry_serve(
    port: int = typer.Option(9120, "--port", "-p", help="Telemetry server port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Telemetry server bind address"),
) -> None:
    """Start the central feedback collector (runs alongside dashboard)."""
    from observeco.telemetry_server import serve
    serve()


# -- MCP subcommands (v1.1) --

mcp_app = typer.Typer(help="MCP protocol server for agent queries")
app.add_typer(mcp_app, name="mcp")

@mcp_app.command(name="serve")
def mcp_serve(
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port for HTTP bridge (default: stdio mode)"),
) -> None:
    """Start MCP server — expose agent data via Model Context Protocol."""
    from observeco.mcp_server import run_mcp_server
    run_mcp_server(port=port)


# -- Adapters subcommands --

adapters_app = typer.Typer(help="Communication channel adapters (Slack, Discord, etc.)", no_args_is_help=True)
app.add_typer(adapters_app, name="adapters")

@adapters_app.command(name="test")
def adapters_test(
    channel: str = typer.Argument(..., help="Channel to test: slack, discord, all"),
) -> None:
    """Test channel adapter connection."""
    from rich.console import Console
    console = Console()

    if channel in ("slack", "all"):
        from observeco.adapters.slack import SlackAdapter
        adapter = SlackAdapter()
        if not adapter.is_configured():
            console.print("[yellow]Slack not configured — set OBSERVECO_SLACK_BOT_TOKEN and OBSERVECO_SLACK_SIGNING_SECRET[/yellow]")
        else:
            result = adapter.test_connection()
            if result.get("ok"):
                console.print(f"[green]✓ Slack connected as {result.get('username', '?')}[/green]")
            else:
                console.print(f"[red]✗ Slack error: {result.get('error', 'unknown')}[/red]")

    if channel in ("discord", "all"):
        from observeco.adapters.discord import DiscordAdapter
        adapter = DiscordAdapter()
        if not adapter.is_configured():
            console.print("[yellow]Discord not configured — set OBSERVECO_DISCORD_BOT_TOKEN and OBSERVECO_DISCORD_PUBLIC_KEY[/yellow]")
        else:
            result = adapter.test_connection()
            if result.get("ok"):
                console.print(f"[green]✓ Discord connected as {result.get('username', '?')} (ID: {result.get('id', '?')})[/green]")
            else:
                console.print(f"[red]✗ Discord error: {result.get('error', 'unknown')}[/red]")

@adapters_app.command(name="send")
def adapters_send(
    channel: str = typer.Argument(..., help="Channel to send to: slack, discord"),
    event_type: str = typer.Option("heartbeat", help="Event type: tool_call, risk_alert, error, heartbeat"),
    agent_id: str = typer.Option("test-agent", help="Agent ID"),
    message: str = typer.Option("Test message from ObserveCo", help="Message text"),
) -> None:
    """Send a test event to a channel."""
    from rich.console import Console
    from observeco.adapters.oef import OEFEvent, make_heartbeat_event
    console = Console()

    event = OEFEvent(
        event_type=event_type,
        agent_id=agent_id,
        runtime="observeco",
        channel=channel,
        payload={"status": "alive", "latency_ms": 42, "message": message},
    )

    if channel == "slack":
        from observeco.adapters.slack import SlackAdapter
        adapter = SlackAdapter()
        if not adapter.is_configured():
            console.print("[red]Slack not configured[/red]")
            return
        ok = adapter.send_event(event)
        console.print(f"[{'green' if ok else 'red'}]{'✓' if ok else '✗'} Slack send{' succeeded' if ok else ' failed'}[/{'green' if ok else 'red'}]")

    elif channel == "discord":
        from observeco.adapters.discord import DiscordAdapter
        adapter = DiscordAdapter()
        if not adapter.is_configured():
            console.print("[red]Discord not configured[/red]")
            return
        ok = adapter.send_event(event)
        console.print(f"[{'green' if ok else 'red'}]{'✓' if ok else '✗'} Discord send{' succeeded' if ok else ' failed'}[/{'green' if ok else 'red'}]")

    else:
        console.print(f"[red]Unknown channel: {channel}[/red]")


# -- Agents subcommands --

agents_app = typer.Typer(help="Manage agent registration & discovery", no_args_is_help=True)
app.add_typer(agents_app, name="agents")

@agents_app.command(name="discover")
def agents_discover() -> None:
    """Auto-discover agents from Hermes, OpenClaw, and other configs."""
    from observeco.auto_detect import run_discover
    run_discover(show_all=True)

@agents_app.command(name="list")
def agents_list() -> None:
    """List all registered agents."""
    from observeco.auto_detect import run_list
    run_list()

@agents_app.command(name="add")
def agents_add(
    name: str = typer.Argument(..., help="Agent name"),
    framework: str = typer.Option("custom", "--framework", "-f", help="Agent framework (hermes, openclaw, custom)"),
    health_check: str = typer.Option("", "--health-check", "-c", help="Health check URL or command"),
) -> None:
    """Manually add an agent."""
    from observeco.auto_detect import run_add
    run_add(name=name, framework=framework, health_check=health_check)


# -- Pathway subcommands --

pathway_app = typer.Typer(help="Communication Pathway Map — trace message delivery paths", no_args_is_help=True)
app.add_typer(pathway_app, name="pathway")

@pathway_app.command(name="scan")
def pathway_scan() -> None:
    """Auto-discover communication pathways from agents, crons, and infrastructure."""
    from observeco.db import Database
    db = Database()
    count = db.pathway_scan()
    graph = db.pathway_get_graph()
    print(f"🔍 Pathway scan complete: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges scanned")

    # Count by status
    by_status = {}
    for e in graph["edges"]:
        s = e["status"]
        by_status[s] = by_status.get(s, 0) + 1
    for status, cnt in sorted(by_status.items()):
        icon = {"green": "🟢", "yellow": "🟡", "red": "🔴", "teal": "🔵"}.get(status, "⚪")
        print(f"  {icon} {status}: {cnt}")

    # Show red/dead ends
    red_edges = [e for e in graph["edges"] if e["status"] == "red"]
    for e in red_edges:
        print(f'  🔴 Dead end: {e["source_name"]} → ∅')

@pathway_app.command(name="list")
def pathway_list() -> None:
    """List all pathways with status."""
    from observeco.db import Database
    from rich import box
    from rich.console import Console
    from rich.table import Table

    db = Database()
    graph = db.pathway_get_graph()
    console = Console()

    table = Table(title="Communication Pathways", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Source", style="bold")
    table.add_column("→")
    table.add_column("Target")
    table.add_column("Status")
    table.add_column("Mechanism")
    table.add_column("Confidence")

    for e in graph["edges"]:
        target = e.get("target_name", "∅")
        icon = {"green": "🟢", "yellow": "🟡", "red": "🔴", "teal": "🔵"}.get(e["status"], "⚪")
        table.add_row(
            e["source_name"], "→",
            target, f"{icon} {e['status']}",
            e.get("mechanism", "-"),
            str(e.get("confidence", "-")),
        )
    console.print(table)

@pathway_app.command(name="add")
def pathway_add(
    name: str = typer.Argument(..., help="Node name"),
    node_type: str = typer.Option("agent", "--type", "-t", help="Node type (cron, agent, platform, consumer, router)"),
    source: str = typer.Option("manual", "--source", "-s", help="Data source (auto, manual)"),
    target: str = typer.Option("", "--target", help="Target node ID (omit for dead end)"),
    status: str = typer.Option("green", "--status", help="Edge status (green, yellow, red, teal)"),
) -> None:
    """Manually add a pathway node + optional edge."""
    from observeco.db import Database
    from rich.console import Console

    db = Database()
    console = Console()
    node_id = f"{node_type}-{name.lower().replace(' ', '-')}"

    db.pathway_add_node(node_id, name, node_type, source=source)
    console.print(f"[green]Added node [bold]{node_id}[/bold] ({node_type})[/green]")

    if target:
        edge_id = db.pathway_add_edge(node_id, target, status=status, mechanism="manual")
        console.print(f"[green]Added edge [bold]{node_id}[/bold] → [bold]{target}[/bold] ({status})[/green]")
    else:
        edge_id = db.pathway_add_edge(node_id, None, status="red", scenario="manual_dead_end")
        console.print(f"[yellow]Added dead-end edge: [bold]{node_id}[/bold] → ∅[/yellow]")

@pathway_app.command(name="clear")
def pathway_clear() -> None:
    """Reset all auto-detected pathway data for fresh scan."""
    from observeco.db import Database
    db = Database()
    count = db.pathway_clear()
    from rich.console import Console
    Console().print(f"[yellow]Cleared {count} auto-detected pathway items[/yellow]")

@pathway_app.command(name="graph")
def pathway_graph_export() -> None:
    """Export pathway graph as JSON (for rendering)."""
    from observeco.db import Database
    import json
    db = Database()
    graph = db.pathway_get_graph()
    print(json.dumps(graph, indent=2, default=str))


def main():
    """CLI entry point with automatic telemetry and error capture."""
    import sys
    import traceback as tb_module

    # Fire usage telemetry in background (fire-and-forget, never blocks)
    _fire_usage_ping(sys.argv)

    try:
        app()
    except typer.Exit:
        pass  # Normal typer exit (--help, --version)
    except SystemExit:
        raise  # Let system exits propagate normally
    except Exception:
        # Automatic crash capture
        error_type = type(sys.exc_info()[1]).__name__
        error_msg = str(sys.exc_info()[1])
        stack = tb_module.format_exc()

        # Fire-and-forget crash report
        _fire_crash_report(error_type, error_msg, stack)


def _fire_usage_ping(argv: list[str]) -> None:
    """Send anonymous usage ping in background thread. Never raises."""
    try:
        from observeco.telemetry_client import send_usage
        cmd = " ".join(argv[1:3]) if len(argv) > 1 else "help"
        send_usage(cmd)
    except Exception:
        pass


def _fire_crash_report(error_type: str, error_msg: str, stack: str) -> None:
    """Send crash report in background thread. Never raises."""
    try:
        from observeco.telemetry_client import send_error
        cmd = " ".join(__import__("sys").argv[1:3]) if len(__import__("sys").argv) > 1 else "unknown"
        send_error(error_type, error_msg, stack, command=cmd)
    except Exception:
        pass


if __name__ == "__main__":
    app()
