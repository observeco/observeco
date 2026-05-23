"""ObserveCo CLI — runtime observability for AI agent systems."""

import typer
from typing import Optional

app = typer.Typer(
    name="observeco",
    help="Runtime observability for AI agent systems — pulse, circuit breaker, token compression, dashboard",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# -- Pulse subcommands --

pulse_app = typer.Typer(help="Agent health monitoring & circuit breakers", no_args_is_help=True)
app.add_typer(pulse_app, name="pulse")

@pulse_app.command(name="check")
def pulse_check(
    watch: bool = typer.Option(False, "--watch", "-w", help="Poll every 5s for 3 cycles"),
):
    """Check agent liveness — alive/dead/error status per agent."""
    from observeco.pulse.check import run_check
    run_check(watch=watch)

@pulse_app.command(name="circuit")
def pulse_circuit(
    reset: Optional[str] = typer.Option(None, "--reset", "-r", help="Reset circuit breaker for agent"),
    threshold: Optional[str] = typer.Option(None, "--threshold", "-t", help="Set max retries for agent (format: <agent>:<n>)"),
):
    """Show circuit breaker state or reset/trip thresholds."""
    from observeco.pulse.circuit import run_circuit
    run_circuit(reset=reset, threshold=threshold)

# -- Chisel subcommands --

chisel_app = typer.Typer(help="System prompt compression & token monitoring", no_args_is_help=True)
app.add_typer(chisel_app, name="chisel")

@chisel_app.command(name="trim")
def chisel_trim():
    """Compress system prompt from stdin — token breakdown & savings ratio."""
    from observeco.chisel.trim import run_trim
    run_trim()

@chisel_app.command(name="drift")
def chisel_drift(
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent name"),
):
    """Show 7-day token allocation drift per component."""
    from observeco.chisel.drift import run_drift
    run_drift(agent=agent_name)

# -- ClawForge subcommands --

clawforge_app = typer.Typer(help="OpenClaw context profiler & memory hygiene", no_args_is_help=True)
app.add_typer(clawforge_app, name="clawforge")

@clawforge_app.command(name="profile")
def clawforge_profile(
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to profile"),
):
    """Show context composition for OpenClaw agents (MEMORY.md, skills, workspace)."""
    from observeco.clawforge.profile import run_profile
    run_profile(agent_name=agent_name)

@clawforge_app.command(name="load")
def clawforge_load(
    probe: bool = typer.Option(False, "--probe", help="Dry-run intent-aware classifier"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to classify"),
):
    """Test intent-aware context classification."""
    from observeco.clawforge.load import run_load
    run_load(probe=probe, message=message)

@clawforge_app.command(name="garden")
def clawforge_garden(
    apply: bool = typer.Option(False, "--apply", help="Execute suggested memory hygiene actions"),
    agent_name: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to audit"),
):
    """Scan MEMORY.md for duplicates, contradictions, stale entries."""
    from observeco.clawforge.garden import run_garden
    run_garden(apply=apply, agent_name=agent_name)

# -- Watch subcommand --

@app.command(name="watch")
def watch_daemon(
    interval: int = typer.Option(30, "--interval", "-i", help="Poll interval in seconds"),
    once: bool = typer.Option(False, "--once", help="Single pass and exit"),
):
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
):
    """Launch the ObserveCo dashboard (FastAPI + htmx)."""
    from observeco.dashboard.server import serve
    serve(host=host, port=port, static=static)


# -- Agents subcommands --

agents_app = typer.Typer(help="Manage agent registration & discovery", no_args_is_help=True)
app.add_typer(agents_app, name="agents")

@agents_app.command(name="discover")
def agents_discover():
    """Auto-discover agents from Hermes, OpenClaw, and other configs."""
    from observeco.auto_detect import run_discover
    run_discover(show_all=True)

@agents_app.command(name="list")
def agents_list():
    """List all registered agents."""
    from observeco.auto_detect import run_list
    run_list()

@agents_app.command(name="add")
def agents_add(
    name: str = typer.Argument(..., help="Agent name"),
    framework: str = typer.Option("custom", "--framework", "-f", help="Agent framework (hermes, openclaw, custom)"),
    health_check: str = typer.Option("", "--health-check", "-c", help="Health check URL or command"),
):
    """Manually add an agent."""
    from observeco.auto_detect import run_add
    run_add(name=name, framework=framework, health_check=health_check)


def main():
    app()


if __name__ == "__main__":
    app()
