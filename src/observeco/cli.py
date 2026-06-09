"""ObserveCo CLI — runtime observability for AI agent systems."""

import os
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
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM-powered features entirely"),
) -> None:
    """ObserveCo — Runtime observability for AI agent systems."""
    if no_llm:
        os.environ["OBSERVECO_NO_LLM"] = "true"
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

# -- Gate subcommands --

gate_app = typer.Typer(help="Playbook Golden Gates — verify code, UX, and architecture compliance", no_args_is_help=True)
app.add_typer(gate_app, name="gate")

@gate_app.command(name="full")
def gate_full(
    json_output: bool = typer.Option(False, "--json", help="JSON output for machine parsing"),
) -> None:
    """Run ALL Golden Gates — full compliance check before shipping."""
    from observeco.gate.runner import run_gate
    results = run_gate(full=True, json_output=json_output)
    if json_output:
        import json as _json
        print(_json.dumps([r.to_dict() for r in results], indent=2))
    failed = sum(1 for r in results if r.status == "FAIL")
    raise typer.Exit(code=1 if failed > 0 else 0)

@gate_app.command(name="coding")
def gate_coding(
    json_output: bool = typer.Option(False, "--json", help="JSON output for machine parsing"),
) -> None:
    """Run Coding Fidelity Golden Gate only."""
    from observeco.gate.runner import run_gate
    results = run_gate(full=False, json_output=json_output)
    if json_output:
        import json as _json
        print(_json.dumps([r.to_dict() for r in results], indent=2))
    failed = sum(1 for r in results if r.status == "FAIL")
    raise typer.Exit(code=1 if failed > 0 else 0)

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
def chisel_skills(
    compress: bool = typer.Option(False, "--compress", help="Apply compression to skill bodies"),
    limit: int = typer.Option(0, "--limit", "-n", help="Number of top skills to compress (0 = all compressible)"),
    dry_run: bool = typer.Option(True, "--dry-run", help="Preview savings without applying (default: true)"),
    apply: bool = typer.Option(False, "--apply", help="Apply compression immediately (overrides --dry-run)"),
) -> None:
    """Audit all Hermes skill files — token cost ranked by total tokens."""
    from observeco.chisel.trim import run_skills
    run_skills(compress=compress or apply, compress_limit=limit if limit > 0 else 0, dry_run=not apply)


@chisel_app.command(name="cards")
def chisel_cards() -> None:
    """Show skill cards (metadata catalog) — compact view of all skills."""
    from observeco.config import hermes_home

    cards_path = hermes_home() / "skills" / "cards.json"
    if not cards_path.exists():
        print("No cards.json found. Run 'observeco chisel artifacts --refresh' first.")
        return
    import json
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    cards.sort(key=lambda c: c.get("total_tokens", 0), reverse=True)
    print(f"Skill Cards — {len(cards)} skills, token cost ranked")
    print(f"{'Name':<35} {'Cat':<18} {'Body tok':>10} {'Saved%':>7} {'Tags':<20}")
    print("-" * 95)
    for c in cards[:30]:
        name = c.get("name", "?")[:34]
        cat = c.get("category", "")[:17]
        tok = c.get("total_tokens", 0)
        pct = f"{c.get('savings_pct', 0):+.1f}%" if c.get("savings_pct") else "0%"
        tags = ", ".join(c.get("tags", [])[:4])
        print(f"{name:<35} {cat:<18} {tok:>10} {pct:>7} {tags:<20}")
    print(f"\n... {len(cards)} total cards. Use 'observeco chisel artifacts' to refresh.")


@chisel_app.command(name="artifacts")
def chisel_artifacts(
    refresh: bool = typer.Option(False, "--refresh", help="Regenerate compressed artifacts and cards"),
    caveman: bool = typer.Option(False, "--caveman", help="Use LLM caveman compression (slower, higher savings)"),
    workers: int = typer.Option(3, "--workers", help="Parallel workers for caveman mode"),
) -> None:
    """Manage compressed skill artifacts (.md.compressed, cards.json, manifests.json)."""
    import json

    from observeco.chisel.skill_compress import (
        batch_compress_skills,
        export_manifest_json,
        generate_cards_json,
    )
    from observeco.config import hermes_home

    skills_dir = hermes_home() / "skills"

    if refresh:
        engine = "caveman" if caveman else "rule"
        print(f"Regenerating skill artifacts (engine={engine})...")
        results = batch_compress_skills(limit=0, engine=engine)

        # Write consolidated cards.json
        cards_json = generate_cards_json()
        cards = json.loads(cards_json)
        (skills_dir / "cards.json").write_text(cards_json)
        print(f"  Written cards.json ({len(cards)} cards)")

        # Write manifests
        manifests_json = export_manifest_json()
        manifests = json.loads(manifests_json)
        (skills_dir / "manifests.json").write_text(manifests_json)
        print(f"  Written manifests.json ({len(manifests)} manifests)")

        total_before = sum(r["original_tokens"] for r in results)
        total_after = sum(r["compressed_tokens"] for r in results)
        saved = total_before - total_after
        print(f"\n  Total: {total_before} → {total_after} tok (saved {saved}, {round(saved/max(total_before,1)*100,1)}%)")
    else:
        compressed = list(skills_dir.rglob("SKILL.md.compressed"))
        manifests = list(skills_dir.rglob("SKILL.md.manifest"))
        cards = list(skills_dir.rglob("SKILL.md.card"))
        cards_json_path = skills_dir / "cards.json"
        print(f"Compressed artifacts:  {len(compressed)} files")
        print(f"Manifests:             {len(manifests)} files")
        print(f"Cards (individual):    {len(cards)} files")
        print(f"Cards (consolidated):  {'✅' if cards_json_path.exists() else '❌'} {'exists' if cards_json_path.exists() else 'missing'}")

        if manifests:
            import json
            total_saved = 0
            total_before = 0
            for mf in manifests:
                try:
                    m = json.loads(mf.read_text(encoding="utf-8"))
                    total_before += m.get("original_tokens", 0)
                    total_saved += m.get("savings_tokens", 0)
                except Exception:
                    pass
            pct = round(total_saved / max(total_before, 1) * 100, 1)
            print(f"\nTotal savings: {total_saved:,} tokens ({pct}%)")
            print("Run --refresh to regenerate.")


@chisel_app.command(name="compress")
def chisel_compress(
    agent_name: str = typer.Option("", "--agent", "-a", help="Agent name to compress"),
    mode: str = typer.Option("lite", "--mode", "-m", help="Compression mode: lite or full"),
    filepath: Optional[str] = typer.Option(None, "--file", "-f", help="Explicit path to SOUL.md"),
) -> None:
    """Compress an agent's SOUL.md — Lite (22% guidance) or Full (35% + memory + skills)."""
    if not agent_name and not filepath:
        print("Usage: observeco chisel compress --agent <name> [--mode lite|full]")
        return
    from observeco.chisel.trim import run_compress
    result = run_compress(agent_name=agent_name, mode=mode, filepath=filepath)
    print(f"Status: {result['status']}")
    print(f"Agent: {result['agent']}")
    print(f"Mode: {result['mode']}")
    print(f"Before: {result['before_tokens']} tok")
    print(f"After:  {result['after_tokens']} tok")
    print(f"Saved:  {result['savings']} tok ({result['savings_pct']:+.1f}%)")
    print(f"Backup: {result['backup']}")


@chisel_app.command(name="config")
def chisel_config(
    hermes_home: Optional[str] = typer.Option(None, "--hermes-home", help="Custom Hermes home path"),
    json_output: bool = typer.Option(False, "--json", help="JSON output for machine parsing"),
    fix: bool = typer.Option(False, "--fix", help="Apply auto-fixable findings"),
) -> None:
    """Scan Hermes config for token-waste patterns (duplicate prompts, low cache TTL, stale refs)."""
    from observeco.chisel.config_scanner import run_scan
    run_scan(hermes_home=hermes_home, json_output=json_output, fix=fix)


# -- Chisel Watch subcommands --
chisel_watch_app = typer.Typer(help="Auto-compression watchdog daemon", no_args_is_help=True)
chisel_app.add_typer(chisel_watch_app, name="watch")


@chisel_watch_app.command(name="start")
def chisel_watch_start() -> None:
    """Start the auto-compression daemon."""
    from observeco.chisel.watch import start_daemon
    start_daemon()


@chisel_watch_app.command(name="stop")
def chisel_watch_stop() -> None:
    """Stop the auto-compression daemon."""
    from observeco.chisel.watch import stop_daemon
    stop_daemon()


@chisel_watch_app.command(name="status")
def chisel_watch_status() -> None:
    """Check if the auto-compression daemon is running."""
    from observeco.chisel.watch import status
    s = status()
    if s["running"]:
        print(f"Chisel watch daemon running (PID {s['pid']})")
        if s["heartbeat_age"] is not None:
            print(f"Last heartbeat: {s['heartbeat_age']:.0f}s ago")
    else:
        print("Chisel watch daemon not running")


@chisel_watch_app.command(name="foreground")
def chisel_watch_foreground() -> None:
    """Run the auto-compression daemon in the foreground (for testing)."""
    from observeco.chisel.watch import _run_foreground
    _run_foreground()

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

from observeco.graph.cli import graph_app  # noqa: E402 - late import avoids circular

app.add_typer(graph_app, name="graph")

# -- Watch subcommands (daemon lifecycle) --

watch_app = typer.Typer(
    name="watch",
    help="Agent health auto-collection daemon — start/stop/status",
    no_args_is_help=True,
)
app.add_typer(watch_app)


@watch_app.command(name="start")
def watch_start() -> None:
    """Start the watch daemon as an independent background process.

    Runs pulse check (every 30s), token trim (every pulse),
    drift scan (every 5min), garden sweep (every 15min),
    and pathway discovery (every 15min). Survives dashboard restarts.
    """
    from observeco.watch import start
    start()


@watch_app.command(name="stop")
def watch_stop() -> None:
    """Stop the watch daemon by signalling its PID."""
    from observeco.watch import stop
    stop()


@watch_app.command(name="status")
def watch_status() -> None:
    """Show whether the watch daemon is running and how fresh its data is."""
    from observeco.watch import status as daemon_status

    s = daemon_status()
    if s["running"]:
        age_str = f"{s['heartbeat_age']:.0f}s ago" if s["heartbeat_age"] is not None else "unknown"
        print(f"● ObserveCo watch is running (PID {s['pid']}). Heartbeat: {age_str}")
    else:
        age_str = f"{s['heartbeat_age']:.0f}s ago" if s["heartbeat_age"] is not None else "never"
        print(f"○ ObserveCo watch is NOT running. Last heartbeat: {age_str}")


@watch_app.command(name="foreground")
def watch_foreground(
    interval: int = typer.Option(30, "--interval", "-i", help="Poll interval in seconds"),
) -> None:
    """Run the watch loop attached to this terminal (debug/testing)."""
    from observeco.watch import run_watch
    run_watch(interval=interval, once=False)


@watch_app.command(name="once")
def watch_once(
    daemon: bool = typer.Option(False, "--daemon", help="Daemon flag for CI compatibility (one-shot mode)"),
) -> None:
    """Single pulse cycle and exit (one-shot)."""
    from observeco.watch import run_watch
    run_watch(once=True)


# -- Dashboard subcommand --

@app.command(name="dashboard")
def serve_dashboard(
    port: int = typer.Option(9119, "--port", "-p", help="Dashboard port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Dashboard bind address"),
    static: bool = typer.Option(False, "--static", help="Generate static HTML and exit"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser (headless/server mode)"),
    shared: Optional[str] = typer.Option(None, "--shared", help="Path to shared SQLite DB for team fleet view"),
    show_token: bool = typer.Option(False, "--show-token", help="Print the dashboard access token and exit"),
) -> None:
    """Launch the ObserveCo dashboard (FastAPI + htmx)."""
    from observeco.dashboard.server import serve
    serve(host=host, port=port, static=static, no_browser=no_browser, shared=shared, show_token=show_token)


@app.command(name="desktop")
def desktop_launch(
    port: int = typer.Option(9119, "--port", "-p", help="Dashboard port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Dashboard bind address"),
    no_tray: bool = typer.Option(False, "--no-tray", help="Skip system tray icon"),
    shared: Optional[str] = typer.Option(None, "--shared", help="Path to shared SQLite DB for team fleet view"),
) -> None:
    """Launch the ObserveCo desktop app (native window via pywebview)."""
    from observeco.desktop import launch
    launch(port=port, host=host, no_tray=no_tray, shared=shared)


@app.command(name="webhook")
def serve_webhook(
    port: int = typer.Option(9120, "--port", "-p", help="Webhook server port"),
    host: str = typer.Option("0.0.0.0", "--host", help="Webhook server bind address"),
) -> None:
    """Launch the webhook ingestion server (receives Slack/Discord/Telegram webhooks)."""
    from observeco.webhook_server import run_webhook_server
    run_webhook_server(host=host, port=port)


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


# -- L2 monitoring subcommand --

l2_app = typer.Typer(help="Layer 2 proactive trend detection (memory bloat, stuck, drift, upstream)", no_args_is_help=True)
app.add_typer(l2_app, name="l2")

@l2_app.command(name="scan")
def l2_scan() -> None:
    """Run one L2 trend scan across all agents."""
    from observeco.heal.l2 import run_l2_scan
    results = run_l2_scan()
    from rich.console import Console
    console = Console()
    if not results:
        console.print("[green]No L2 trends detected — all agents look healthy.[/green]")
    else:
        console.print(f"[yellow]{len(results)} L2 trend(s) detected:[/yellow]")
        for r in results:
            console.print(f"  [{r['trend_type']}] {r['agent']} — metric={r['metric']:.1f}")

@l2_app.command(name="status")
def l2_status() -> None:
    """Show current L2 trends."""
    from rich import box
    from rich.console import Console
    from rich.table import Table

    from observeco.heal.l2 import get_l2_metrics, get_l2_summary
    console = Console()
    metrics = get_l2_metrics()
    table = Table(title=f"L2 Trending — {metrics['total_trends']} total, {metrics['resolution_rate']}% resolved",
                  box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Agent")
    table.add_column("Type")
    table.add_column("Severity")
    table.add_column("Signal")
    table.add_column("Resolved")
    for t in get_l2_summary(limit=15):
        icon = "✅" if t["resolved"] else "⚠️"
        table.add_row(t["agent_name"], t["trend_type"], t["severity"],
                      t["signal_label"][:60], icon)
    console.print(table)


# -- Alerts subcommand --

alerts_app = typer.Typer(help="Push alert subscriptions (Telegram, webhook, email)", no_args_is_help=True)
app.add_typer(alerts_app, name="alerts")

@alerts_app.command(name="subscribe")
def alerts_subscribe(
    channel: str = typer.Argument(..., help="Channel: telegram, webhook, email"),
    target: str = typer.Argument(..., help="Target: chat_id, webhook URL, or email address"),
    event_types: str = typer.Option("all", "--events", "-e",
                                    help="Filter: all, critical_only, heal_failure, drift, circuit_trip, agent_death"),
) -> None:
    """Subscribe to push alerts on a delivery channel."""
    from rich.console import Console

    from observeco.alerts.push import add_subscription
    console = Console()
    result = add_subscription(channel, target, event_types)
    console.print(f"[green]Subscribed: {channel} -> {target} (events: {event_types})[/green]")
    console.print(f"[dim]Subscription ID: {result['id']}[/dim]")

@alerts_app.command(name="unsubscribe")
def alerts_unsubscribe(
    sub_id: int = typer.Argument(..., help="Subscription ID to remove"),
) -> None:
    """Remove an alert subscription."""
    from rich.console import Console

    from observeco.alerts.push import remove_subscription
    console = Console()
    remove_subscription(sub_id)
    console.print(f"[green]Subscription {sub_id} removed.[/green]")

@alerts_app.command(name="list")
def alerts_list() -> None:
    """List all alert subscriptions."""
    from rich import box
    from rich.console import Console
    from rich.table import Table

    from observeco.alerts.push import list_subscriptions
    console = Console()
    subs = list_subscriptions()
    if not subs:
        console.print("[dim]No alert subscriptions. Use `observeco alerts subscribe <channel> <target>` to add one.[/dim]")
        return
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("ID")
    table.add_column("Channel")
    table.add_column("Target")
    table.add_column("Events")
    table.add_column("Enabled")
    for s in subs:
        table.add_row(str(s["id"]), s["channel"], s["target"],
                      s["event_types"], "✅" if s["enabled"] else "❌")
    console.print(table)

@alerts_app.command(name="log")
def alerts_log() -> None:
    """Show recent alert delivery log."""
    from rich import box
    from rich.console import Console
    from rich.table import Table

    from observeco.alerts.push import get_delivery_log
    console = Console()
    log = get_delivery_log(limit=10)
    if not log:
        console.print("[dim]No alert deliveries yet.[/dim]")
        return
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Channel")
    table.add_column("Event")
    table.add_column("Delivered")
    table.add_column("Message")
    for entry in log:
        icon = "✅" if entry["delivered"] else "❌"
        table.add_row(entry["channel"], entry["event_type"], icon, entry["message"][:70])
    console.print(table)


# -- Plugin tracking subcommand --

plugin_app = typer.Typer(help="OpenClaw plugin context-loading tracking", no_args_is_help=True)
app.add_typer(plugin_app, name="plugin")

@plugin_app.command(name="log")
def plugin_log(
    agent_name: str = typer.Argument(..., help="Agent name"),
    hook_point: str = typer.Argument(..., help="Hook point: bootstrap, ingest, pre_response"),
    intent_class: str = typer.Option("", "--intent", "-i", help="Classified intent"),
    loaded: int = typer.Option(0, "--loaded", "-l", help="Sources loaded"),
    skipped: int = typer.Option(0, "--skipped", "-s", help="Sources skipped"),
    saved: int = typer.Option(0, "--saved", help="Tokens saved"),
) -> None:
    """Log a plugin hook event (for OpenClaw plugin integration)."""
    from rich.console import Console

    from observeco.clawforge.plugin import log_plugin_hook
    console = Console()
    result = log_plugin_hook(agent_name, hook_point, intent_class, loaded, skipped, saved)
    console.print(f"[green]Logged {hook_point} for {agent_name}: {result['reduction_pct']}% reduction[/green]")

@plugin_app.command(name="stats")
def plugin_stats(
    agent_name: str = typer.Option("", "--agent", "-a", help="Filter by agent"),
) -> None:
    """Show plugin tracking statistics."""
    from rich.console import Console

    from observeco.clawforge.plugin import get_plugin_stats
    console = Console()
    stats = get_plugin_stats(agent_name)
    if stats["turns"] == 0:
        console.print("[dim]No plugin data recorded yet.[/dim]")
        return
    console.print(f"[bold]Plugin Stats[/bold] {'for ' + agent_name if agent_name else '(all agents)'}")
    console.print(f"  Turns tracked: {stats['turns']}")
    console.print(f"  Sources loaded: {stats['loaded']}")
    console.print(f"  Sources skipped (saved): {stats['skipped']}")
    console.print(f"  Avg reduction: {stats['avg_reduction_pct']}%")


# -- Token tracking subcommand --

tokens_app = typer.Typer(help="Per-turn token tracking, budget thresholds, trend analysis", no_args_is_help=True)
app.add_typer(tokens_app, name="tokens")

@tokens_app.command(name="log")
def tokens_log(
    agent_name: str = typer.Argument(..., help="Agent name"),
    turn_id: str = typer.Argument(..., help="Turn ID (e.g. turn_001)"),
    total_tokens: int = typer.Argument(..., help="Total tokens used"),
    identity: int = typer.Option(0, "--identity", help="Identity tokens"),
    skills: int = typer.Option(0, "--skills", help="Skills tokens"),
    memory: int = typer.Option(0, "--memory", help="Memory tokens"),
    tools: int = typer.Option(0, "--tools", help="Tools tokens"),
    guidance: int = typer.Option(0, "--guidance", help="Guidance tokens"),
    provider: str = typer.Option("custom", "--provider", help="Provider name (deepseek, claude, etc.)"),
) -> None:
    """Log a single turn's token usage (anomaly detection + budget check)."""
    from rich.console import Console

    from observeco.tracking.tokens import log_token_turn
    console = Console()
    result = log_token_turn(agent_name, turn_id, total_tokens, identity, skills,
                            memory, tools, guidance, provider)
    parts = [f"Cost: ${result['cost']:.6f}"]
    if result['anomaly_score'] is not None:
        parts.append(f"Anomaly: {result['anomaly_score']:.1f}σ")
    if result['budget_alerts']:
        parts.append(f"⚠️ {', '.join(result['budget_alerts'])}")
    console.print(f"[green]Logged turn {turn_id} for {agent_name} — {' · '.join(parts)}[/green]")

@tokens_app.command(name="status")
def tokens_status(
    agent_name: str = typer.Option("", "--agent", "-a", help="Filter by agent"),
    days: int = typer.Option(7, "--days", "-d", help="Lookback window"),
) -> None:
    """Show token tracking summary per agent."""
    from rich import box
    from rich.console import Console
    from rich.table import Table

    from observeco.tracking.tokens import get_token_summary
    console = Console()
    stats = get_token_summary(agent_name, days)
    if stats["turns"] == 0:
        console.print("[dim]No token data recorded yet.[/dim]")
        return
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Turns", str(stats["turns"]))
    table.add_row("Total tokens", f"{stats['total_tokens']:,}")
    table.add_row("Total cost", f"${stats['total_cost']:.4f}")
    table.add_row("Avg per turn", f"{stats['avg_tokens']:.0f}")
    table.add_row("Max turn", f"{stats['max_tokens']:,}")
    console.print(table)

@tokens_app.command(name="trends")
def tokens_trends(
    agent_name: str = typer.Option("", "--agent", "-a", help="Filter by agent"),
    days: int = typer.Option(7, "--days", "-d", help="Lookback window"),
) -> None:
    """Show component growth trends over time."""
    from rich import box
    from rich.console import Console
    from rich.table import Table

    from observeco.tracking.tokens import get_trend_analysis
    console = Console()
    analysis = get_trend_analysis(agent_name)
    console.print(f"[bold]Trend Analysis[/bold] for {agent_name or 'all agents'}")
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Component")
    table.add_column("Growth")
    table.add_column("Recent avg")
    table.add_column("Baseline avg")
    for comp, growth in analysis.get("component_growth", {}).items():
        color = "green" if growth < 0 else "yellow" if growth < 10 else "red"
        table.add_row(comp, f"[{color}]{growth:+.1f}%[/{color}]",
                      str(analysis.get("recent_avg", 0)),
                      str(analysis.get("baseline_avg", 0)))
    table.add_row("Total", f"{analysis.get('growth_pct', 0):+.1f}%",
                  str(analysis.get("recent_avg", 0)),
                  str(analysis.get("baseline_avg", 0)))
    console.print(table)

@tokens_app.command(name="budget")
def tokens_budget(
    agent_name: str = typer.Argument(..., help="Agent name"),
    max_daily_tokens: int = typer.Option(0, "--max-daily", help="Max tokens per day"),
    max_turn_cost: float = typer.Option(0, "--max-turn-cost", help="Max cost per turn in $"),
    anomaly_sigma: float = typer.Option(3.0, "--anomaly-sigma", help="Anomaly detection sigma threshold"),
) -> None:
    """Set per-agent token budget thresholds."""
    from rich.console import Console

    from observeco.db import Database
    console = Console()
    db = Database()
    db.set_token_budget(agent_name, max_daily_tokens, max_turn_cost,
                        anomaly_threshold_sigma=anomaly_sigma)
    console.print(f"[green]Budget set for {agent_name}: daily={max_daily_tokens}, turn_cost=${max_turn_cost:.4f}, anomaly={anomaly_sigma}σ[/green]")


# -- Prune subcommand --

@app.command(name="prune")
def prune_command(
    data_type: str = typer.Option("all", "--type", "-t", help="Data type: pulse, error, drift, token, l2, or all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be pruned"),
) -> None:
    """Prune old data per retention policy."""
    from rich.console import Console

    from observeco.tracking.prune import run_prune
    console = Console()
    result = run_prune()
    if result.get("status") == "disabled":
        console.print("[yellow]Pruning is disabled. Run `observeco config set pruning_enabled 1`[/yellow]")
    elif result.get("status") == "pro_never_prune":
        console.print("[green]Pro tier — never prunes data. No action taken.[/green]")
    elif result.get("status") == "ok":
        total = sum(v for k, v in result.items() if k != "status")
        console.print(f"[green]Pruned {total} rows across {len(result) - 1} data types.[/green]")
        for dt, count in result.items():
            if dt != "status":
                console.print(f"  {dt}: {count} rows deleted")
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

    if channel in ("telegram", "all"):
        from observeco.adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        if not adapter.is_configured():
            console.print("[yellow]Telegram not configured — set OBSERVECO_TG_BOT_TOKEN and OBSERVECO_TG_CHAT_ID[/yellow]")
        else:
            result = adapter.test_connection()
            if result.get("ok"):
                console.print(f"[green]✓ Telegram connected as @{result.get('username', '?')}[/green]")
            else:
                console.print(f"[red]✗ Telegram error: {result.get('error', 'unknown')}[/red]")

@adapters_app.command(name="send")
def adapters_send(
    channel: str = typer.Argument(..., help="Channel to send to: slack, discord"),
    event_type: str = typer.Option("heartbeat", help="Event type: tool_call, risk_alert, error, heartbeat"),
    agent_id: str = typer.Option("test-agent", help="Agent ID"),
    message: str = typer.Option("Test message from ObserveCo", help="Message text"),
) -> None:
    """Send a test event to a channel."""
    from rich.console import Console

    from observeco.adapters.oef import OEFEvent
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

    elif channel == "telegram":
        from observeco.adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        if not adapter.is_configured():
            console.print("[red]Telegram not configured[/red]")
            return
        ok = adapter.send_event(event)
        console.print(f"[{'green' if ok else 'red'}]{'✓' if ok else '✗'} Telegram send{' succeeded' if ok else ' failed'}[/{'green' if ok else 'red'}]")

    else:
        console.print(f"[red]Unknown channel: {channel}[/red]")


@adapters_app.command(name="openclaw")
def adapters_openclaw() -> None:
    """List and validate OpenClaw hooks."""
    from rich.console import Console
    from rich.table import Table

    from observeco.adapters.openclaw import get_hook_config, list_hooks, validate_hooks

    console = Console()

    hooks = list_hooks()
    if not hooks:
        console.print("[yellow]No OpenClaw hooks found in hooks/ directory[/yellow]")
        return

    # List hooks table
    table = Table(title="OpenClaw Hooks")
    table.add_column("Name", style="cyan")
    table.add_column("File", style="white")
    table.add_column("Version", style="green")
    table.add_column("Exports", style="yellow")

    for h in hooks:
        exports = ", ".join(h.get("exports", []))
        table.add_row(h.get("name", "?"), h.get("file", "?"), h.get("version", "?"), exports)

    console.print(table)

    # Validation results
    validation = validate_hooks()
    console.print("\n[bold]Validation:[/bold]")
    for v in validation:
        if v.get("status") == "critical":
            console.print(f"  [red]✗ {v['name']} — {', '.join(v.get('issues', []))}[/red]")
        elif v.get("status") == "missing":
            console.print(f"  [yellow]○ {v['name']} — optional, not present[/yellow]")
        elif v.get("status") == "partial":
            console.print(f"  [yellow]⚠ {v['name']} — {', '.join(v.get('issues', []))}[/yellow]")
        else:
            console.print(f"  [green]✓ {v['name']}[/green]")

    # Config summary
    config = get_hook_config()
    if config.get("validation", {}).get("status") == "failed":
        console.print(f"\n[red]⚠ Missing required hooks: {', '.join(config['validation']['missing_required'])}[/red]")
    else:
        console.print(f"\n[green]✓ All required hooks present ({config['hooks_dir']})[/green]")


# -- Doctor subcommands --

doctor_app = typer.Typer(help="Intelligent environment troubleshooter with LLM-powered diagnostics")
app.add_typer(doctor_app, name="doctor")

@doctor_app.command(name="run")
def doctor_run(
    auto_fix: bool = typer.Option(False, "--auto-fix", "-y", help="Apply fixes automatically"),
    provider: str = typer.Option("auto", "--provider", "-p", help="LLM provider: auto, openai, anthropic, google, ollama, none"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Diagnose environment issues and get AI-powered fixes."""
    from observeco.doctor.cli import doctor_run as _run
    _run(auto_fix=auto_fix, provider=provider, json_output=json_output)

@doctor_app.command(name="diagnose")
def doctor_diagnose() -> None:
    """Quick health check — diagnostics only."""
    from observeco.doctor.cli import doctor_diagnose as _diagnose
    _diagnose()

@doctor_app.command(name="providers")
def doctor_providers() -> None:
    """List available LLM providers."""
    from observeco.doctor.cli import doctor_providers as _providers
    _providers()


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
    health_check: str = typer.Option("", "--health-check", "-c", help="Health check URL, docker:containername, or launchd:label"),
) -> None:
    """Manually add an agent."""
    from observeco.auto_detect import run_add
    run_add(name=name, framework=framework, health_check=health_check)

    # LLM-powered health check suggestion (Tier 2 shallow)
    if not health_check:
        try:
            import subprocess

            from observeco.llm_service import ask
            lsof = subprocess.run(["lsof", "-i", "-P"], capture_output=True, text=True, timeout=5)
            listening = [ln for ln in lsof.stdout.split("\n") if "LISTEN" in ln][:10]
            if listening:
                port_context = "\n".join(listening)
                suggestion = ask(
                    """You are a health check advisor. Given listening ports and the agent name, suggest an appropriate health check URL or command.

Format: SUGGESTION: <health check URL or command>
If nothing obvious, respond: NO_SUGGESTION""",
                    f"Agent: {name}\nFramework: {framework}\n\nListening ports:\n{port_context}",
                    consumer="health_check_suggestion",
                    max_cost_cents=0.005,
                    cache_ttl_secs=3600,
                    tier=2,
                )
                if suggestion and "NO_SUGGESTION" not in suggestion:
                    for line in suggestion.split("\n"):
                        if line.startswith("SUGGESTION:"):
                            suggested_hc = line[11:].strip()
                            console = __import__('rich').console.Console()
                            console.print(f"[dim]💡 LLM suggests: [bold]--health-check '{suggested_hc}'[/bold][/dim]")
        except Exception:
            pass


# -- OTel subcommands --

otel_app = typer.Typer(help="OpenTelemetry bridge — export events as OTel spans")
app.add_typer(otel_app, name="otel")

@otel_app.command(name="export")
def otel_export(
    session_id: str = typer.Option("", "--session", "-s", help="Session ID to export"),
    format: str = typer.Option("otlp", "--format", "-f", help="Export format: otlp, jaeger"),
) -> None:
    """Export session events as OTel-compatible trace."""
    from rich.console import Console

    from observeco.otel_bridge import OTelBridge
    from observeco.session_log import SessionLogger

    console = Console()
    bridge = OTelBridge()
    logger = SessionLogger(session_id) if session_id else SessionLogger()
    entries = logger.get_entries(limit=100)

    if not entries:
        console.print("[yellow]No events to export[/yellow]")
        return

    # Convert entries to OEF events
    from observeco.adapters.oef import OEFEvent
    events = []
    for entry in entries:
        event = OEFEvent(
            event_type=entry.get("event_type", "unknown"),
            agent_id=entry.get("agent_id", "unknown"),
            runtime="observeco",
            channel="cli",
            payload=entry.get("data", {}),
        )
        events.append(event)

    if format == "jaeger":
        result = bridge.export_to_jaeger(events)
    else:
        result = bridge.export_events(events)

    import json
    print(json.dumps(result, indent=2))


@otel_app.command(name="listen")
def otel_listen(
    action: str = typer.Argument("status", help="start, stop, status, or --once"),
    port: int = typer.Option(4318, "--port", "-p", help="OTLP listen port"),
) -> None:
    """Standalone OTLP listener on port 4318 — accepts spans from OpenInference-instrumented agents."""
    from observeco.otel_listener import cli_main
    cli_main([action, str(port)])


# -- Fleet subcommands --

fleet_app = typer.Typer(help="Fleet dashboard — multi-agent, multi-channel overview", no_args_is_help=True)
app.add_typer(fleet_app, name="fleet")

@fleet_app.command(name="status")
def fleet_status() -> None:
    """Show fleet status — all agents, health, token usage."""
    from rich.console import Console
    from rich.table import Table

    from observeco.db import Database

    db = Database()
    agents = db.get_agents()
    summary = db.get_agent_status_summary()

    console = Console()
    table = Table(title="Fleet Status")
    table.add_column("Agent", style="cyan")
    table.add_column("Framework")
    table.add_column("Status")
    table.add_column("Latency")
    table.add_column("Circuit")

    alive = dead = 0
    for agent in agents:
        name = agent.get("agent_name", agent.get("name", ""))
        s = summary.get(name, {})
        status = s.get("status", "unknown")
        if status == "alive":
            alive += 1
            status_style = "[green]alive[/green]"
        elif status == "dead":
            dead += 1
            status_style = "[red]dead[/red]"
        else:
            status_style = f"[yellow]{status}[/yellow]"
        table.add_row(
            name,
            agent.get("framework", "?"),
            status_style,
            f"{s.get('latency_ms', 0):.0f}ms",
            "tripped" if s.get("circuit_tripped") else "ok",
        )

    console.print(table)
    console.print(f"\n  Total: {len(agents)} | Alive: {alive} | Dead: {dead}")


# -- Risk subcommands --

risk_app = typer.Typer(help="ML-based risk prediction and profiling", no_args_is_help=True)
app.add_typer(risk_app, name="risk")

@risk_app.command(name="predict")
def risk_predict(
    tool: str = typer.Argument(..., help="Tool name to predict risk for"),
    agent: str = typer.Option("", "--agent", "-a", help="Agent ID for agent-specific prediction"),
) -> None:
    """Predict risk for a tool call based on historical patterns."""
    from rich.console import Console

    from observeco.risk_predictor import RiskPredictor

    predictor = RiskPredictor()
    prediction = predictor.predict(tool, agent_id=agent)

    console = Console()
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
    emoji = risk_emoji.get(prediction.predicted_risk, "⚪")

    console.print(f"\n{emoji} Risk Prediction for `{tool}`")
    console.print(f"  Predicted: {prediction.predicted_risk.upper()}")
    console.print(f"  Confidence: {prediction.confidence:.0%}")
    console.print(f"  Reason: {prediction.reason}")
    console.print(f"  Pattern: {prediction.pattern}")
    if prediction.historical_total > 0:
        console.print(f"  History: {prediction.historical_failures}/{prediction.historical_total} failures")

@risk_app.command(name="profile")
def risk_profile(
    entity: str = typer.Argument(..., help="Agent ID or tool name"),
    entity_type: str = typer.Option("auto", "--type", "-t", help="Entity type: agent, tool, auto"),
) -> None:
    """Show risk profile for an agent or tool."""
    from rich.console import Console

    from observeco.risk_predictor import RiskPredictor

    predictor = RiskPredictor()

    if entity_type == "agent" or (entity_type == "auto" and "/" not in entity):
        profile = predictor.get_agent_profile(entity)
    else:
        profile = predictor.get_tool_profile(entity)

    console = Console()
    trend_emoji = {"improving": "📈", "stable": "➡️", "degrading": "📉"}

    console.print(f"\n📊 Risk Profile: {profile.entity}")
    console.print(f"  Type: {profile.entity_type}")
    console.print(f"  Total calls: {profile.total_calls}")
    console.print(f"  Failures: {profile.failures}")
    console.print(f"  Failure rate: {profile.failure_rate:.1%}")
    console.print(f"  Trend: {trend_emoji.get(profile.recent_trend, '?')} {profile.recent_trend}")
    if profile.last_failure:
        console.print(f"  Last failure: {profile.last_failure}")
    if profile.risk_distribution:
        console.print(f"  Risk distribution: {profile.risk_distribution}")

@risk_app.command(name="fleet")
def risk_fleet() -> None:
    """Show risk profiles for all agents."""
    from rich.console import Console
    from rich.table import Table

    from observeco.risk_predictor import RiskPredictor

    predictor = RiskPredictor()
    profiles = predictor.get_fleet_profiles()

    console = Console()
    table = Table(title="Fleet Risk Profiles")
    table.add_column("Agent", style="cyan")
    table.add_column("Calls")
    table.add_column("Failures")
    table.add_column("Rate")
    table.add_column("Trend")

    for p in profiles:
        trend_emoji = {"improving": "📈", "stable": "➡️", "degrading": "📉"}
        rate_style = "[red]" if p.failure_rate > 0.2 else "[yellow]" if p.failure_rate > 0.1 else "[green]"
        table.add_row(
            p.entity,
            str(p.total_calls),
            str(p.failures),
            f"{rate_style}{p.failure_rate:.1%}[/]",
            f"{trend_emoji.get(p.recent_trend, '?')} {p.recent_trend}",
        )

    console.print(table)


# -- Pathway subcommands --

pathway_app = typer.Typer(help="Communication Pathway Map — trace message delivery paths", no_args_is_help=True)
app.add_typer(pathway_app, name="pathway")

@pathway_app.command(name="scan")
def pathway_scan() -> None:
    """Auto-discover communication pathways from agents, crons, and infrastructure."""
    from observeco.db import Database
    db = Database()
    db.pathway_scan()
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
    from rich import box
    from rich.console import Console
    from rich.table import Table

    from observeco.db import Database

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
    from rich.console import Console

    from observeco.db import Database

    db = Database()
    console = Console()
    node_id = f"{node_type}-{name.lower().replace(' ', '-')}"

    db.pathway_add_node(node_id, name, node_type, source=source)
    console.print(f"[green]Added node [bold]{node_id}[/bold] ({node_type})[/green]")

    if target:
        db.pathway_add_edge(node_id, target, status=status, mechanism="manual")
        console.print(f"[green]Added edge [bold]{node_id}[/bold] → [bold]{target}[/bold] ({status})[/green]")
    else:
        db.pathway_add_edge(node_id, None, status="red", scenario="manual_dead_end")
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
    import json

    from observeco.db import Database
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


# -- PA Brief subcommand --

pa_app = typer.Typer(help="PA brief operations (evening snapshot / morning delta)")
app.add_typer(pa_app, name="pa")

@pa_app.command(name="brief")
def pa_brief(
    mode: str = typer.Option("morning", "--mode", "-m", help="Brief mode: 'morning' (diff against evening) or 'evening' (take snapshot)"),
) -> None:
    """PA brief — morning diffs against evening snapshot, evening takes a baseline snapshot."""
    from observeco.pa_brief_diff import run_brief
    result = run_brief(mode)
    print(result)


if __name__ == "__main__":
    app()
