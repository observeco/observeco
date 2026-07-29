"""ObserveCo CLI — runtime observability for AI agent systems."""

import json
import os
from typing import Optional

import typer

from observeco.cli_harness import harness_app

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

# -- Turn-capture hook handler --

@app.command(name="capture-turn")
def capture_turn() -> None:
    """Hermes shell-hook handler: capture a turn/skill event into pulse.db.

    Reads one hook payload (JSON) from stdin and enqueues it for batched
    write. Designed to be called by Hermes' post_tool_call / on_session_end
    hooks. Never raises; exits 0 on any failure so the agent turn is never
    affected. See observeco.turn_capture for the blast-radius contract.
    """
    from observeco.turn_capture import run
    run()


@app.command(name="selfcheck")
def selfcheck(
    write_alert: bool = typer.Option(True, "--alert/--no-alert", help="On failure, write a row into ObserveCo's alert_log (dashboard Alerts tab)."),
) -> None:
    """Run the turn-capture self-check end-to-end and report.

    The check feeds real sample payloads through the live `capture-turn`
    handler and asserts rows land in pulse.db. It is the watchdog for the
    silent-failure blast-radius contract: if capture breaks, the handler still
    exits 0 and the dashboard shows zeros — only this check proves the pipeline
    actually writes.

    On failure it writes one `self_check_failure` row into alert_log (cooldown:
    at most one per 24h) so it surfaces in the ObserveCo Alerts tab instead of
    Telegram. On success it prints PASS and writes nothing.
    """
    import subprocess
    import sys
    import time as _time

    # abspath(cli.py)=.../src/observeco/cli.py -> dirname x2 = .../src
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src
    repo_root = os.path.dirname(here)  # .../projects/observeco
    test_path = os.path.join(repo_root, "tests", "test_turn_capture.py")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(repo_root, "src") + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.run(
        [sys.executable, test_path], capture_output=True, text=True,
        cwd=here, timeout=60, env=env,
    )

    if proc.returncode == 0:
        typer.echo("PASS: turn_capture self-check OK")
        raise typer.Exit(0)

    # Failure path.
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
    msg = "turn_capture self-check FAILED: " + " | ".join(tail[-1:]) if tail else "turn_capture self-check FAILED"
    typer.echo(msg, err=True)

    if write_alert:
        try:
            from observeco.db import Database
            db = Database()
            # Cooldown: don't re-spam if a failure was already logged <24h ago.
            recent = db.get_alert_log(limit=20)
            now = int(_time.time())
            for r in recent:
                if r.get("event_type") == "self_check_failure" and now - r.get("created_at", 0) < 86400:
                    break
            else:
                db.log_alert_delivery(
                    channel="dashboard", target="selfcheck",
                    event_type="self_check_failure", message=msg[:500],
                    delivered=0, error=(proc.stderr or "")[:500],
                )
            db.close()
        except Exception:
            pass  # alert write must never crash the check report

    raise typer.Exit(1)


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
    """Compress an agent's SOUL.md — Lite (guidance only) or Full (guidance + memory + skills)."""
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

# Harness optimization loop (obs-spec-056 + obs-spec-061). CLI was implemented in
# cli_harness.py but never registered here — the dashboard "Run Optimization" button
# and any `observeco harness optimize` invocation were dead until this wiring.
app.add_typer(harness_app, name="harness")


@watch_app.command(name="start")
def watch_start(
    db_path: Optional[str] = typer.Option(None, "--db-path", help="Override DB path (use if default is unwritable)"),
) -> None:
    """Start the watch daemon as an independent background process.

    Runs pulse check (every 30s), token trim (every pulse),
    drift scan (every 5min), garden sweep (every 15min),
    and pathway discovery (every 15min). Survives dashboard restarts.
    """
    from pathlib import Path

    from observeco.dirs import get_data_dir
    from observeco.startup_validation import run_checks

    _data_dir = get_data_dir()
    _db_path = Path(db_path) if db_path else _data_dir / "pulse.db"
    run_checks(data_dir=_data_dir, db_path=_db_path, ports=[])

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
    db_path: Optional[str] = typer.Option(None, "--db-path", help="Override DB path (use if default is unwritable)"),
) -> None:
    """Launch the ObserveCo dashboard (FastAPI + htmx)."""
    from pathlib import Path

    from observeco.dirs import get_data_dir
    from observeco.startup_validation import run_checks

    _data_dir = get_data_dir()
    _db_path = Path(db_path) if db_path else _data_dir / "pulse.db"
    run_checks(data_dir=_data_dir, db_path=_db_path, ports=[port])

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


# -- Proxy subcommands (Task 4.6) --

proxy_app = typer.Typer(help="Transparent API proxy — captures real token usage from LLM calls", no_args_is_help=True)
app.add_typer(proxy_app, name="proxy")

@proxy_app.command(name="start")
def proxy_start(
    port: int = typer.Option(9200, "--port", "-p", help="Proxy port"),
    upstream: str = typer.Option("https://api.openai.com", "--upstream", "-u", help="Upstream LLM provider URL"),
    agent_name: str = typer.Option("proxy-agent", "--agent", "-a", help="Agent name for logging"),
    no_browser: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground (not daemonized)"),
    track_local: bool = typer.Option(False, "--track-local", help="Also proxy local LLM providers (ollama, llama.cpp)"),
) -> None:
    """Start the API proxy — sits between agents and LLM providers."""
    from observeco.proxy.process import ensure_proxy_alive

    alive, actual_port = ensure_proxy_alive(port)
    if alive:
        print(f"✓ Proxy running on port {actual_port}")
        # Wire Hermes config to use this proxy
        try:
            from observeco.proxy.service import auto_configure_hermes
            ac = auto_configure_hermes(port=actual_port)
            if ac.get("changed"):
                print(f"  Configured {len(ac['changes'])} provider(s)")
        except Exception:
            pass
    else:
        print(f"✗ Proxy failed to start on port {port}")

@proxy_app.command(name="stop")
def proxy_stop() -> None:
    """Stop the API proxy."""
    from observeco.proxy.process import stop_proxy
    stopped = stop_proxy(9200)
    if stopped:
        print("✓ Proxy stopped")
    else:
        print("ℹ Nothing running on port 9200")

@proxy_app.command(name="status")
def proxy_status() -> None:
    """Show proxy status and captured token counts."""
    from observeco.proxy.service import get_proxy_status
    result = get_proxy_status()
    if result["state"] == "running":
        health = result.get("health", {})
        proxy_stats = health.get("proxy", {})
        print("✓ Proxy running")
        print(f"  PID: {result['pid']}")
        print(f"  Port: {result['port']}")
        print(f"  Requests: {proxy_stats.get('requests', '?')}")
        print(f"  Errors: {proxy_stats.get('errors', '?')}")
        print(f"  Tokens captured: {proxy_stats.get('total_tokens_captured', '?')}")
    else:
        print(f"ℹ Proxy not running: {result.get('message', '')}")

@proxy_app.command(name="configure")
def proxy_configure(
    revert: bool = typer.Option(False, "--revert", help="Revert Hermes config to original"),
) -> None:
    """Auto-configure Hermes providers to route through proxy (Task 4.7)."""
    from observeco.proxy.service import auto_configure_hermes, revert_hermes_config

    if revert:
        result = revert_hermes_config()
        if result["changed"]:
            print(f"✓ Reverted {len(result['changes'])} provider(s):")
            for c in result["changes"]:
                print(f"  {c}")
        else:
            print("ℹ Nothing to revert")
        return

    result = auto_configure_hermes()
    if result["changed"]:
        print(f"✓ Configured {len(result['changes'])} provider(s) to use proxy:")
        for c in result["changes"]:
            print(f"  {c}")
        print(f"\n  Backup: {result.get('backup', 'none')}")
        print("\n  Restart Hermes gateway to apply changes.")
    else:
        print(f"ℹ {result.get('message', 'No changes needed')}")


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


# -- Prevention skill subcommand (L3 Learning Loop, #81) --

prevention_app = typer.Typer(help="Incident skill auto-creation — manage learned prevention skills", no_args_is_help=True)
app.add_typer(prevention_app, name="prevention")


@prevention_app.command(name="list")
def prevention_list(agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent")):
    """List all prevention skills."""
    from rich.console import Console
    from rich.table import Table

    from observeco.heal import prevention as prev

    skills = prev.list_skills(agent)
    console = Console()
    if not skills:
        console.print("[yellow]No prevention skills yet.[/yellow]")
        console.print("Enable learning with: observeco heal --learn (or set heal_config.learn=1)")
        return
    table = Table(title="Prevention Skills")
    table.add_column("ID", style="cyan")
    table.add_column("Agent", style="bold")
    table.add_column("Success", style="green")
    table.add_column("Fail", style="red")
    table.add_column("Deprecated", style="yellow")
    table.add_column("Created", style="dim")
    for s in skills:
        table.add_row(
            str(s["id"]), s["agent_name"], str(s["success_count"]),
            str(s["fail_count"]), "yes" if s["deprecated"] else "no",
            str(s["created_at"]),
        )
    console.print(table)


@prevention_app.command(name="show")
def prevention_show(skill_id: int = typer.Argument(..., help="Prevention skill ID")):
    """Show a prevention skill's contents."""
    from rich.console import Console

    from observeco.heal import prevention as prev

    skill = prev.get_skill(skill_id)
    console = Console()
    if not skill:
        console.print(f"[red]No skill with ID {skill_id}.[/red]")
        raise typer.Exit(1)
    console.print(f"[bold]{skill['agent_name']}[/bold] — {skill['diagnosis']}")
    console.print(f"[dim]Success: {skill['success_count']}  Fail: {skill['fail_count']}  "
                  f"Deprecated: {'yes' if skill['deprecated'] else 'no'}[/dim]")
    console.print("\n[cyan]Remediation:[/cyan]")
    console.print(skill["remediation"])
    path = skill.get("skill_path")
    if path:
        console.print(f"\n[dim]SKILL.md: {path}[/dim]")


@prevention_app.command(name="remove")
def prevention_remove(skill_id: int = typer.Argument(..., help="Prevention skill ID")):
    """Delete a prevention skill (file + DB + FTS5 index)."""
    from rich.console import Console

    from observeco.heal import prevention as prev

    console = Console()
    if prev.remove_skill(skill_id):
        console.print(f"[green]Removed skill {skill_id}.[/green]")
    else:
        console.print(f"[red]No skill with ID {skill_id}.[/red]")
        raise typer.Exit(1)


@prevention_app.command(name="enable")
def prevention_enable(agent: str = typer.Argument(..., help="Agent name")):
    """Enable L3 learning for an agent (writes prevention skills after heal)."""
    from rich.console import Console

    from observeco.db import Database

    db = Database()
    db.set_heal_config(agent, learn=True)
    Console().print(f"[green]Learning enabled for {agent}. Prevention skills will be "
                    f"created after successful heals.[/green]")


@prevention_app.command(name="disable")
def prevention_disable(agent: str = typer.Argument(..., help="Agent name")):
    """Disable L3 learning for an agent."""
    from rich.console import Console

    from observeco.db import Database

    db = Database()
    db.set_heal_config(agent, learn=False)
    Console().print(f"[yellow]Learning disabled for {agent}.[/yellow]")


# -- SDK auto-instrumentation subcommand --

sdk_app = typer.Typer(help="SDK auto-instrumentation — detect and patch AI SDKs for token logging", no_args_is_help=True)
app.add_typer(sdk_app, name="sdk")

@sdk_app.command(name="detect")
def sdk_detect() -> None:
    """Detect installed AI SDKs."""
    from rich.console import Console
    from rich.table import Table

    from observeco.tracking.sdk.detector import detect_sdks

    detected = detect_sdks()
    console = Console()

    if not detected:
        console.print("[yellow]No AI SDKs detected.[/yellow]")
        console.print("Install one: pip install openai anthropic langchain")
        return

    table = Table(title="Detected AI SDKs")
    table.add_column("SDK", style="cyan")
    table.add_column("Package", style="white")
    table.add_column("Version", style="green")
    table.add_column("Description", style="dim")

    for sdk in detected:
        table.add_row(sdk.name, sdk.package, sdk.version or "unknown", sdk.description)

    console.print(table)
    console.print(f"\n[green]Found {len(detected)} SDK(s).[/green] Run [bold]observeco sdk install[/bold] to enable token logging.")


@sdk_app.command(name="install")
def sdk_install(
    sdk_name: str = typer.Argument("", help="Specific SDK to patch (empty = all detected)"),
) -> None:
    """Apply token-logging patches to detected SDKs."""
    from rich.console import Console

    from observeco.tracking.sdk.patcher_registry import apply_all_patchers, apply_patcher

    console = Console()

    if sdk_name:
        success = apply_patcher(sdk_name)
        if success:
            console.print(f"[green]✓ {sdk_name} patcher applied.[/green]")
        else:
            console.print(f"[red]✗ {sdk_name} patcher failed (SDK not installed?).[/red]")
    else:
        results = apply_all_patchers()
        for name, ok in results.items():
            status = "[green]✓[/green]" if ok else "[red]✗[/red]"
            console.print(f"  {status} {name}")

        applied = sum(1 for v in results.values() if v)
        console.print(f"\n[green]{applied}/{len(results)} patchers applied.[/green]")


@sdk_app.command(name="enable")
def sdk_enable() -> None:
    """Enable auto-patching on Python startup via env var + .pth file."""
    import shutil
    import site
    from pathlib import Path

    from rich.console import Console

    console = Console()

    # Set env var persistently
    env_file = Path.home() / ".observeco" / "env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_content = ""
    if env_file.exists():
        env_content = env_file.read_text()
    if "OBSERVECO_AUTO_PATCH=1" not in env_content:
        with open(env_file, "a") as f:
            f.write("\nOBSERVECO_AUTO_PATCH=1\n")
    os.environ["OBSERVECO_AUTO_PATCH"] = "1"

    # Install .pth file to site-packages
    pth_src = Path(__file__).parent / "tracking" / "sdk" / "sdk_auto.pth"
    if not pth_src.exists():
        console.print("[red]✗ sdk_auto.pth not found at %s[/red]" % pth_src)
        raise typer.Exit(code=1)

    # Find the first writable site-packages directory
    site_packages = None
    for sp in site.getsitepackages():
        sp_path = Path(sp)
        if sp_path.exists() and os.access(str(sp_path), os.W_OK):
            site_packages = sp_path
            break

    if not site_packages:
        # Fallback: user site-packages
        user_sp = Path(site.getusersitepackages())
        user_sp.mkdir(parents=True, exist_ok=True)
        site_packages = user_sp

    dest = site_packages / "sdk_auto.pth"
    shutil.copy2(str(pth_src), str(dest))
    console.print(f"[green]✓ sdk_auto.pth installed to {dest}[/green]")
    console.print("[green]✓ OBSERVECO_AUTO_PATCH=1 set[/green]")
    console.print("\nAuto-patching will activate on next Python startup.")
    console.print("To verify: [bold]python -c \"import observeco.tracking.sdk; print('OK')\"[/bold]")


@sdk_app.command(name="providers")
def sdk_providers() -> None:
    """Detect provider configs from installed tools."""
    from rich.console import Console
    from rich.table import Table

    from observeco.tracking.sdk.provider_registry import detect_and_report

    report = detect_and_report()
    console = Console()

    if not report["providers"]:
        console.print("[yellow]No provider configs detected.[/yellow]")
        return

    table = Table(title="Detected Provider Configurations")
    table.add_column("Tool", style="cyan")
    table.add_column("Provider", style="white")
    table.add_column("Base URL", style="green")
    table.add_column("Local?", style="yellow")
    table.add_column("Needs Proxy?", style="red")
    table.add_column("Config Path", style="dim")

    for p in report["providers"]:
        table.add_row(
            p["tool"],
            p["provider"],
            p["base_url"],
            "✓" if p["is_local"] else "✗",
            "✓" if p["needs_proxy"] else "✗",
            p["config_path"],
        )

    console.print(table)
    console.print(f"\nTotal: {report['total_providers']} provider(s), {report['need_proxy']} need proxy, {report['local']} local")

    if report["instructions"]:
        console.print("\n[bold]Wiring Instructions:[/bold]")
        for inst in report["instructions"]:
            console.print(f"  [cyan]{inst['tool']}[/cyan]: {inst['current']} → [green]{inst['new']}[/green]")
            if inst["notes"]:
                console.print(f"    [dim]{inst['notes']}[/dim]")


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
    data_health: bool = typer.Option(False, "--data-health", help="Run data continuity health checks only"),
) -> None:
    """Diagnose environment issues and get AI-powered fixes."""
    from observeco.doctor.cli import doctor_run as _run
    _run(auto_fix=auto_fix, provider=provider, json_output=json_output, data_health=data_health)

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


# -- Setup command --

@app.command(name="setup")
def setup_command() -> None:
    """Check and configure the OTEL pipeline for real token data.

    Walks through: OTEL plugin enabled? → Listener running? → Data flowing?
    Prints current tier (Estimated / Accurate / Full) and next steps.
    """
    from rich.console import Console

    console = Console()
    console.print("[bold]ObserveCo Pipeline Setup[/bold]\n")

    # 1. Check hermes plugin
    from observeco.pipeline.health import (
        _check_hermes_otel_plugin_enabled,
        _check_otel_listener_running,
        check_pipeline_health,
    )

    plugin_enabled = _check_hermes_otel_plugin_enabled()
    listener_running = _check_otel_listener_running()

    if plugin_enabled:
        console.print("[green]✓[/green] Hermes OTEL plugin enabled")
    else:
        console.print("[yellow]✗[/yellow] Hermes OTEL plugin not enabled")
        console.print("  → Run: [bold]hermes plugins enable observability/otel[/bold]")
        console.print("  → Then restart Hermes and re-run [bold]observeco setup[/bold]")

    if listener_running:
        console.print("[green]✓[/green] OTEL listener running on port 4318")
    else:
        console.print("[yellow]✗[/yellow] OTEL listener not running")
        console.print("  → Run: [bold]observeco otel listen start[/bold]")

    health = check_pipeline_health()
    tier = health["tier"]
    tier_labels = {"estimated": "Estimated (watch only, ±80%)", "accurate": "Accurate (OTEL, ±5%)", "full": "Full (SDK/proxy, ±1%)"}
    tier_colors = {"estimated": "yellow", "accurate": "green", "full": "cyan"}
    color = tier_colors.get(tier, "white")
    label = tier_labels.get(tier, tier)

    console.print(f"\nCurrent tier: [{color}][bold]{label}[/bold][/{color}]")

    sources = health.get("sources", {})
    console.print("\n[bold]Source activity (last 24h):[/bold]")
    for src_name, src in sources.items():
        rows = src.get("rows_24h", 0)
        active_icon = "[green]✓[/green]" if src.get("active") else "[dim]○[/dim]"
        console.print(f"  {active_icon} {src_name}: {rows} rows")

    if health.get("upgrade_path"):
        console.print(f"\n[dim]Next step:[/dim] {health['upgrade_path']}")

    if tier == "accurate" or tier == "full":
        console.print("\n[green]✓ Pipeline is healthy — real token data flowing.[/green]")


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


# -- Service subcommands --

service_app = typer.Typer(help="Service management (start/stop/status)", no_args_is_help=True)
app.add_typer(service_app, name="service")


@service_app.command(name="start")
def service_start(
    port: int = typer.Option(8787, "--port", "-p", help="Dashboard port"),
    otel_port: int = typer.Option(4318, "--otel-port", help="OTEL listener port"),
) -> None:
    """Start ObserveCo service (OTEL listener + Dashboard)."""

    from observeco.service import start_service

    result = start_service(port=port, otel_port=otel_port)

    otel = result.get("otel_listener", {})
    dashboard = result.get("dashboard", {})

    if otel.get("state") == "running" and dashboard.get("state") == "running":
        print("✓ Service started")
        print(f"  OTEL listener: PID {otel.get('pid')} on port {otel_port}")
        print(f"  Dashboard: PID {dashboard.get('pid')} on port {port}")
        print("  Token: show with `observeco dashboard --show-token`")
    else:
        print("✗ Service failed to start")
        if otel.get("error"):
            print(f"  OTEL: {otel['error']}")
        if dashboard.get("error"):
            print(f"  Dashboard: {dashboard['error']}")


@service_app.command(name="stop")
def service_stop() -> None:
    """Stop ObserveCo service."""
    from observeco.service import stop_service

    stop_service()
    print("✓ Service stopped")


@service_app.command(name="status")
def service_status() -> None:
    """Show ObserveCo service status."""
    from observeco.dirs import get_data_dir
    from observeco.health import HealthChecker
    from observeco.process_supervision import get_status as get_supervisor_status
    from observeco.service import get_service_status

    # Get component status
    status = get_service_status()

    print("ObserveCo Service Status\n")

    # Process supervisor status (launchd / systemd / PID-file)
    sup = get_supervisor_status()
    sup_icon = "✓" if sup.get("running") else "○"
    sup_installed = "installed" if sup.get("installed") else "not installed"
    sup_state = "running" if sup.get("running") else "stopped"
    print(f"Supervisor ({sup['platform']}): {sup_icon} {sup_state} [{sup_installed}]")
    if sup.get("detail"):
        print(f"  {sup['detail']}")
    print()

    if not status:
        print("No components running")
        print("\nStart with: observeco service start")
        return

    # Show component status
    for name, info in status.items():
        state = info.get("state", "unknown")
        pid = info.get("pid")
        port = info.get("port")
        uptime = info.get("uptime")

        if state == "running":
            icon = "✓"
        elif state == "failed":
            icon = "✗"
        else:
            icon = "●"

        print(f"{icon} {name}: {state}")
        if pid:
            print(f"  PID: {pid}")
        if port:
            print(f"  Port: {port}")
        if uptime:
            print(f"  Uptime: {int(uptime)}s")

    # Run health check
    print("\nHealth Check:")
    try:
        db_path = get_data_dir() / "pulse.db"
        checker = HealthChecker(db_path=db_path)
        health = checker.check_all()

        overall = health.overall.value
        if overall == "healthy":
            icon = "✓"
        elif overall == "degraded":
            icon = "⚠"
        else:
            icon = "✗"

        print(f"{icon} Overall: {overall}")

        # Show L1 checks
        for check, status in health.level1.items():
            icon = "✓" if status.value == "up" else "✗"
            print(f"  {icon} {check}: {status.value}")

        # Show L2 checks
        for check, status in health.level2.items():
            icon = "✓" if status.value == "up" else "⚠" if status.value == "degraded" else "✗"
            print(f"  {icon} {check}: {status.value}")

        # Show resources
        if health.resources:
            print("\nResources:")
            if "disk_percent" in health.resources:
                print(f"  Disk: {health.resources['disk_percent']:.1f}%")
            if "cpu_percent" in health.resources:
                print(f"  CPU: {health.resources['cpu_percent']:.1f}%")
            if "memory_mb" in health.resources:
                print(f"  Memory: {health.resources['memory_mb']:.1f} MB")

    except Exception as e:
        print(f"  Health check failed: {e}")


@service_app.command(name="install")
def service_install() -> None:
    """Install ObserveCo as a system service (launchd on macOS, systemd on Linux)."""
    from observeco.process_supervision import install

    ok, msg = install()
    print(msg)
    if not ok:
        raise typer.Exit(code=1)


@service_app.command(name="uninstall")
def service_uninstall() -> None:
    """Remove the ObserveCo system service."""
    from observeco.process_supervision import uninstall

    ok, msg = uninstall()
    print(msg)
    if not ok:
        raise typer.Exit(code=1)


@service_app.command(name="restart")
def service_restart(
    port: int = typer.Option(8787, "--port", "-p", help="Dashboard port"),
    otel_port: int = typer.Option(4318, "--otel-port", help="OTEL listener port"),
) -> None:
    """Restart ObserveCo service."""
    from observeco.service import start_service, stop_service

    print("Stopping service...")
    stop_service()

    print("Starting service...")
    result = start_service(port=port, otel_port=otel_port)

    otel = result.get("otel_listener", {})
    dashboard = result.get("dashboard", {})

    if otel.get("state") == "running" and dashboard.get("state") == "running":
        print("✓ Service restarted")
        print(f"  OTEL listener: PID {otel.get('pid')} on port {otel_port}")
        print(f"  Dashboard: PID {dashboard.get('pid')} on port {port}")
    else:
        print("✗ Service failed to restart")


# -- Run launcher (capability tier 1 — crash-safe env injection) --

@app.command(
    name="run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_agent(
    ctx: typer.Context,
    no_probe: bool = typer.Option(False, "--no-probe", help="Skip env probe, pick random port"),
    mode: str = typer.Option("lite", "--mode", "-m", help="Run mode: lite (env injection) or proxy-config (config-rewrite reconciler)"),
) -> None:
    """Launch an agent with ObserveCo observability via env injection (crash-safe).

    Usage: observeco run -- hermes start
           observeco run -- openclaw --config ~/.config/openclaw.yaml

    Injects *_BASE_URL env vars pointing at an ephemeral ObserveCo proxy into
    the child process only. Nothing is written to disk — crash-safe by construction.

    With --mode proxy-config, starts a reconciler daemon that writes base_url
    directly into the agent's config file.
    """
    import subprocess

    agent_cmd = ctx.args
    if not agent_cmd:
        typer.echo("Usage: observeco run -- <agent command>", err=True)
        raise typer.Exit(code=1)

    config_path = ""
    existing = {}
    providers = ["openai", "anthropic"]

    if no_probe:
        import socket as _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        runtime = None
    else:
        from observeco.capability.probe import probe_environment
        snap = probe_environment()
        port = snap.chosen_port
        runtime = snap.runtime
        if port is None:
            typer.echo("observeco run: could not bind an ephemeral port — aborting", err=True)
            raise typer.Exit(code=1)
        config_path = snap.config_path or ""
        existing = snap.existing_proxies

    proxy_url = f"http://127.0.0.1:{port}/v1"

    # Inject env vars for common LLM SDKs — child process only, nothing on disk
    child_env = os.environ.copy()
    child_env["OPENAI_BASE_URL"] = proxy_url
    child_env["ANTHROPIC_BASE_URL"] = proxy_url
    child_env["OBSERVECO_PROXY_PORT"] = str(port)
    if runtime:
        child_env["OBSERVECO_RUNTIME"] = runtime

    if mode == "proxy-config" and not no_probe:
        from observeco.proxy.process import ensure_proxy_alive
        from observeco.proxy.reconciler import reconcile_loop

        if runtime == "hermes":
            from observeco.capability.adapters.hermes import HermesSchemaV16 as Adapter
            # Extract provider names from config for Hermes v16 (profiles dict)
            if snap.config_parsed:
                profiles = snap.config_parsed.get("profiles", {})
                providers = list(dict.fromkeys(
                    p for profile in profiles.values()
                    if isinstance(profile, dict)
                    for p in (profile.get("providers", []) if isinstance(profile.get("providers"), list) else [])
                )) or providers
        else:
            from observeco.capability.adapters.hermes import HermesSchemaV14 as Adapter
            # For v14 or unknown, extract providers list directly
            if snap.config_parsed and isinstance(snap.config_parsed.get("providers"), list):
                providers = [p["name"] for p in snap.config_parsed["providers"] if isinstance(p, dict) and p.get("name")]

        if config_path:
            reconcile_loop(
                config_path=config_path,
                our_port=port,
                providers=providers,
                runtime=runtime or "hermes",
                adapter=Adapter,
                existing_proxies=existing,
                ensure_proxy_alive=ensure_proxy_alive,
            )
            typer.echo("observeco run: reconciler started (mode=proxy-config, tick=10s)")
        else:
            typer.echo("observeco run: no config_path detected, reconciler skipped", err=True)

    try:
        result = subprocess.run(agent_cmd, env=child_env)
        raise typer.Exit(code=result.returncode)
    except FileNotFoundError:
        typer.echo(f"observeco run: command not found: {agent_cmd[0]}", err=True)
        raise typer.Exit(code=127)


# -- Benchmark subcommand --

benchmark_app = typer.Typer(help="Agent quality benchmarks — lm-eval-harness via Hermes agent adapter")
app.add_typer(benchmark_app, name="benchmark")


@benchmark_app.command(name="create-task")
def benchmark_create_task(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
    name: str = typer.Option(..., "--name", "-n", help="Task name"),
    input: str = typer.Option(..., "--input", "-i", help="Task description / input text"),
    context: str = typer.Option("", "--context", "-c", help="File path or inline context"),
    expected: str = typer.Option("", "--expected", "-e", help="Expected output description"),
) -> None:
    """Create a user-defined benchmark task."""
    from pathlib import Path

    from observeco.benchmark import BenchmarkEngine

    ctx_text = context
    if context and Path(context).exists():
        ctx_text = Path(context).read_text(encoding="utf-8")

    engine = BenchmarkEngine()
    result = engine.create_task(agent, name, input, ctx_text, expected)
    if result.get("ok"):
        print(f"✅ Task created: {name} (agent={agent}, id={result['task_id']})")
    else:
        print(f"❌ Failed: {result.get('error', 'unknown error')}")


@benchmark_app.command(name="list")
def benchmark_list(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
) -> None:
    """List benchmark tasks for an agent."""
    from observeco.benchmark import BenchmarkEngine

    engine = BenchmarkEngine()
    tasks = engine.list_tasks(agent)
    if not tasks:
        print(f"No tasks for agent '{agent}'")
        return
    print(f"Tasks for {agent}:")
    for t in tasks:
        print(f"  [{t['id']}] {t['task_name']}")
        print(f"       input: {t['input_text'][:60]}...")
        if t.get("expected_output"):
            print(f"       expected: {t['expected_output'][:60]}...")


@benchmark_app.command(name="delete")
def benchmark_delete(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
    name: str = typer.Option(..., "--name", "-n", help="Task name"),
) -> None:
    """Delete a benchmark task."""
    from observeco.benchmark import BenchmarkEngine

    engine = BenchmarkEngine()
    result = engine.delete_task(agent, name)
    if result.get("ok"):
        print(f"✅ Deleted: {name}")
    else:
        print(f"❌ Failed: {result.get('error', 'unknown error')}")


@benchmark_app.command(name="run")
def benchmark_run(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
    suite: str = typer.Option("", "--suite", "-s",
        help="Pre-built suite: canary, full"),
    tasks: str = typer.Option("", "--tasks", "-t",
        help="Comma-separated task names or YAML file paths"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n",
        help="Max samples per task (default: suite-dependent)"),
    task_path: Optional[str] = typer.Option(None, "--task-path",
        help="Directory for custom YAML task files"),
    direct: bool = typer.Option(False, "--direct",
        help="Call model API directly — bypasses agent harness to establish true model ceiling"),
    litellm: bool = typer.Option(False, "--litellm",
        help="Use LiteLLM with real logprobs from local llama-server for MC scoring"),
) -> None:
    """Run benchmarks through lm-eval-harness.

    Default: routes through agent harness (hermes chat).
    Use --direct to call the model API directly.
    Use --litellm for real logprobs via local llama-server (fixes MC scoring).

    Examples:
        observeco benchmark run --agent hermes-main --suite canary
        observeco benchmark run --agent hermes-main --suite canary --litellm
        observeco benchmark run --agent hermes-main --tasks mmlu --limit 20
    """
    from observeco.benchmark import BenchmarkEngine

    engine = BenchmarkEngine()
    task_list = [t.strip() for t in tasks.split(",") if t.strip()] if tasks else None

    result = engine.run_lm_eval(
        agent_name=agent,
        tasks=task_list,
        suite=suite,
        limit=limit,
        task_include_path=task_path,
        direct=direct,
        litellm=litellm,
    )

    if not result.get("ok"):
        print(f"❌ {result.get('error', 'unknown error')}")
        return

    print(f"\n📊 Benchmark Results — {agent}")
    print(f"   Suite: {result['suite_name']}")
    print(f"   Model: {result['model_used']}")
    print()

    task_results = result.get("results", {})
    if not task_results:
        print("   No task results returned.")
        return

    for task_name, metrics in task_results.items():
        # Print primary metric
        primary = None
        for key, val in sorted(metrics.items()):
            if not key.endswith("_stderr") and isinstance(val, (int, float)):
                primary = (key, val)
                break
        if primary:
            pct = f"{primary[1]:.1%}" if primary[1] <= 1.0 else f"{primary[1]:.2f}"
            print(f"  {task_name}: {primary[0]}={pct}")


@benchmark_app.command(name="results")
def benchmark_results(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent results"),
) -> None:
    """Show recent benchmark results for an agent."""
    from observeco.benchmark import BenchmarkEngine

    engine = BenchmarkEngine()
    results = engine.get_results(agent, limit)
    if not results:
        print(f"No results for agent '{agent}'")
        return
    print(f"Recent results for {agent}:")
    for r in results:
        from datetime import datetime
        ts = datetime.fromtimestamp(r["run_at"]).strftime("%Y-%m-%d %H:%M")
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} {r['task_name']} — {r['score']:.0%} ({ts}, model={r['model_used']})")


@benchmark_app.command(name="compare")
def benchmark_compare(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
    task: Optional[str] = typer.Option(None, "--task", help="Single task to compare"),
    threshold: float = typer.Option(0.05, "--threshold", help="Degradation threshold (default 0.05)"),
) -> None:
    """Compare latest benchmark results to baseline. Flags degradation."""
    from observeco.benchmark import BenchmarkEngine

    engine = BenchmarkEngine()
    result = engine.compare_baseline(
        agent_name=agent,
        task_name=task,
        degradation_threshold=threshold,
    )

    if not result.get("ok"):
        print(f"❌ {result.get('error', 'unknown error')}")
        return

    print(f"\n📊 Baseline Comparison — {agent}")
    print(f"   Tasks: {result['total_tasks']}")
    print(f"   Stable: {result['stable']}")
    print(f"   Degraded: {result['degraded']}")
    print()

    for c in result["comparisons"]:
        icon = "🔴" if c["degraded"] else "🟢"
        if c["baseline_score"] is None:
            print(f"  ⬜ {c['task_name']}: {c['latest_score']:.1%} (no baseline)")
        else:
            delta_str = f"+{c['delta']:.1%}" if c['delta'] >= 0 else f"{c['delta']:.1%}"
            print(f"  {icon} {c['task_name']}: {c['latest_score']:.1%} (Δ {delta_str}) — {c['reason']}")


@benchmark_app.command(name="grid")
def benchmark_grid(
    env: str = typer.Option("retail", "--env", "-e", help="τ-bench environment (retail, airline)"),
    models: str = typer.Option("flash,pro", "--models", "-m", help="Comma-separated model keys"),
    configs: str = typer.Option("baseline", "--configs", "-c", help="Comma-separated config names"),
    tasks: str = typer.Option("0-4", "--tasks", "-t", help="Task range (e.g. 0-4) or comma-separated IDs"),
    trials: int = typer.Option(3, "--trials", "-n", help="Number of trials per cell"),
    max_steps: int = typer.Option(30, "--max-steps", help="Max steps per task"),
) -> None:
    """Run grid evaluation: models × harness configs × tasks."""
    from observeco.benchmark.grid.configs import ALL_CONFIGS
    from observeco.benchmark.grid.runner import MODELS as GRID_MODELS
    from observeco.benchmark.grid.runner import GridRunner

    # Parse models
    model_keys = [m.strip() for m in models.split(",")]
    model_dict = {k: GRID_MODELS[k] for k in model_keys if k in GRID_MODELS}

    # Parse configs
    config_names = [c.strip() for c in configs.split(",")]
    config_list = [c for c in ALL_CONFIGS if c.name in config_names]

    # Parse task IDs
    if "-" in tasks:
        parts = tasks.split("-")
        task_ids = list(range(int(parts[0]), int(parts[1]) + 1))
    else:
        task_ids = [int(t.strip()) for t in tasks.split(",")]

    if not model_dict:
        print(f"❌ No valid models. Available: {list(GRID_MODELS.keys())}")
        return
    if not config_list:
        print(f"❌ No valid configs. Available: {[c.name for c in ALL_CONFIGS]}")
        return

    print("\n🧪 Grid Evaluation")
    print(f"   Environment: {env}")
    print(f"   Models: {list(model_dict.keys())}")
    print(f"   Configs: {[c.name for c in config_list]}")
    print(f"   Tasks: {task_ids} ({len(task_ids)} tasks)")
    print(f"   Trials: {trials}")
    print()

    runner = GridRunner(
        models=model_dict,
        configs=config_list,
        num_trials=trials,
    )

    result = runner.run_tau_bench(
        env_name=env,
        task_ids=task_ids,
        max_steps=max_steps,
    )

    print(f"\n📊 Grid Results — {env}")
    print(f"   Cells: {len(result.cells)}")
    print()

    for cell in result.cells:
        ci = cell.reward_ci
        print(
            f"  {cell.model_name:>8} | {cell.config_name:<20} | "
            f"reward={cell.mean_reward:.3f} "
            f"[{ci[0]:.3f}, {ci[1]:.3f}] | "
            f"calls={cell.total_calls} "
            f"timeouts={cell.total_timeouts} "
            f"hang={cell.hang_rate:.1%} "
            f"recover={cell.recovery_rate:.1%}"
        )
        for flag in cell.flags:
            print(f"    ⚠️  {flag}")

    print("\nResults saved to ~/.observeco/grid/")


# ── Canary Commands ──────────────────────────────────────────────────────────

canary_app = typer.Typer(help="Capability monitoring canary — regression tripwire", no_args_is_help=True)
app.add_typer(canary_app, name="canary")


@canary_app.command(name="suggest-tasks")
def canary_suggest_tasks(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile to mine sessions for"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max number of task drafts to propose"),
    source: str = typer.Option("telegram", "--source", help="Session source filter (telegram/cli/cron/all)"),
    approve_all: bool = typer.Option(False, "--approve-all", help="Skip review, auto-approve all drafts (not recommended)"),
) -> None:
    """Mine agent conversations and propose canary task drafts for review.

    Drafts are saved as pending. Review them in the dashboard
    (Capability → Task Library → Pending) and approve the ones you want.
    """
    from observeco.capability.canary import CanaryRunner
    from observeco.capability.history_tasks import generate_drafts, save_drafts_as_pending
    from observeco.db import Database

    print(f"\n🔍 Mining sessions from ~/.hermes/state.db (source={source})...")
    drafts = generate_drafts(limit=limit)
    if not drafts:
        print("   No qualifying sessions found. Use the agent for a few days to build history.")
        return

    if approve_all:
        print("⚠️  --approve-all: skipping human review (defeats ground-truth anchor)")
        db = Database()
        runner = CanaryRunner(db=db)
        approved = 0
        for d in drafts:
            res = runner.create_task(d)
            if res.get("ok"):
                approved += 1
        print(f"✅ Auto-approved {approved}/{len(drafts)} drafts as active tasks.")
        return

    saved = save_drafts_as_pending(drafts)
    print(f"✅ {saved} task drafts saved as pending review.")
    print("   Review in dashboard: Capability → Task Library → Pending")
    print("   Or approve all: observeco canary suggest-tasks --approve-all")


@canary_app.command(name="run")
def canary_run(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    tasks: Optional[str] = typer.Option(None, "--tasks", "-t", help="Comma-separated task IDs (default: all)"),
    trials: Optional[int] = typer.Option(None, "--trials", "-n", help="Override per-task trial count"),
    config_label: Optional[str] = typer.Option(None, "--label", "-l", help="Config label for this run"),
    direct: bool = typer.Option(False, "--direct",
        help="Call model API directly — bypasses agent harness (faster, no profile loading)"),
) -> None:
    """Run the canary suite — execute all tasks and compare against baseline."""
    from observeco.capability.baseline import BaselineManager
    from observeco.capability.canary import CanaryRunner
    from observeco.capability.drift import DriftDetector
    from observeco.db import Database

    db = Database()
    db._get_conn().execute("PRAGMA busy_timeout=30000")

    if direct:
        from observeco.capability.adapters.direct_model import DirectModelAdapter
        adapter = DirectModelAdapter("ollama-cloud/deepseek-v4-flash", timeout=120)
        runner = CanaryRunner(db=db, adapter=adapter)
    else:
        runner = CanaryRunner(db=db)

    task_ids = None
    if tasks:
        task_ids = [t.strip() for t in tasks.split(",")]

    print(f"\n🔬 Canary Run — agent={agent}")
    report = runner.run(
        agent_name=agent,
        task_ids=task_ids,
        trials=trials,
        config_label=config_label,
    )

    if report.total_tasks == 0:
        print("❌ No tasks found. Create tasks with 'observeco task create'.")
        return

    # Print report
    print(f"\n📊 Canary Report — {report.run_id[:8]}")
    print(f"   Config hash: {report.config_hash}")
    print(f"   Overall: {report.overall_accuracy:.1%} "
          f"[{report.ci_lower:.1%}, {report.ci_upper:.1%}] 95% CI")
    print(f"   Pass: {report.pass_count} | Hang: {report.hang_count} | Fail: {report.fail_count}")
    print(f"   Cost: ${report.total_cost:.4f} | Tokens: {report.total_tokens}")
    print()

    for tr in report.per_task:
        status_icon = "✅" if tr["fails"] == 0 and tr["hangs"] == 0 else "❌"
        print(f"  {status_icon} {tr['task_name']}")
        print(f"     Pass: {tr['passes']} | Hang: {tr['hangs']} | Fail: {tr['fails']}")
        print(f"     Accuracy: {tr['accuracy']:.1%} [{tr['ci_lower']:.1%}, {tr['ci_upper']:.1%}]")
        print(f"     Cost: ${tr['cost']:.4f}")

    # Check drift
    baseline_mgr = BaselineManager(db=db)
    drift_result = baseline_mgr.compare(
        run_id=report.run_id,
        agent_name=agent,
        config_hash=report.config_hash,
        current_pass=report.pass_count,
        current_fail=report.fail_count,
        per_task_results=report.per_task,
    )

    if drift_result:
        sev_icon = {"breach": "🔴", "warning": "🟡", "info": "🔵"}.get(drift_result.severity, "⚪")
        print(f"\n{sev_icon} Drift: {drift_result.drift_pct:+.1f}% (p={drift_result.p_value:.4f}, {drift_result.severity})")
        if drift_result.breached_tasks:
            print(f"   Breached tasks: {', '.join(drift_result.breached_tasks)}")

        # Store drift event
        detector = DriftDetector(db=db)
        detector.check(
            run_id=report.run_id,
            agent_name=agent,
            config_hash=report.config_hash,
            config_label=config_label,
            pass_count=report.pass_count,
            fail_count=report.fail_count,
            per_task_results=report.per_task,
        )
    else:
        print("\n⚪ No baseline yet — needs 3+ runs with same config to enable drift detection.")


@canary_app.command(name="list")
def canary_list(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of runs to show"),
) -> None:
    """List recent canary runs with pass rates."""
    from observeco.capability.canary import CanaryRunner
    from observeco.db import Database

    runner = CanaryRunner(db=Database())
    runs = runner.list_runs(agent_name=agent, limit=limit)

    if not runs:
        print(f"No canary runs for agent '{agent}'. Run 'observeco canary run'.")
        return

    print(f"\n📋 Canary Runs — {agent} ({len(runs)} runs)")
    print(f"{'Run ID':<10} {'Date':<20} {'Status':<12} {'Pass':>6} {'Fail':>6} {'Hang':>6} {'Accuracy':>10}")
    print("-" * 72)
    for r in runs:
        total = (r["pass_count"] or 0) + (r["fail_count"] or 0)
        acc = f"{r['pass_count'] / total:.1%}" if total > 0 else "N/A"
        print(f"{r['id'][:8]:<10} {r['started_at'][:19]:<20} "
              f"{r['status']:<12} {r['pass_count'] or 0:>6} {r['fail_count'] or 0:>6} "
              f"{r['hang_count'] or 0:>6} {acc:>10}")


@canary_app.command(name="baseline")
def canary_baseline(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recompute baseline"),
) -> None:
    """Compute or recompute the baseline from recent canary runs."""
    from observeco.capability.baseline import BaselineManager
    from observeco.capability.canary import CanaryRunner
    from observeco.db import Database

    db = Database()
    runner = CanaryRunner(db=db)

    # Get last run's config hash
    runs = runner.list_runs(agent_name=agent, limit=1)
    if not runs:
        print(f"No canary runs for agent '{agent}'. Run 'observeco canary run' first.")
        return

    config_hash = runs[0]["config_hash"]

    mgr = BaselineManager(db=db)
    if force:
        print(f"🔄 Force-recomputing baseline for {agent} (config: {config_hash[:12]})...")
    else:
        print(f"📏 Computing baseline for {agent} (config: {config_hash[:12]})...")

    result = mgr.compute_baseline(
        agent_name=agent,
        config_hash=config_hash,
        min_runs=1 if force else 3,
    )

    if result:
        print(f"✅ Baseline created: {result['accuracy']:.1%} "
              f"[{result['ci_lower']:.1%}, {result['ci_upper']:.1%}] "
              f"from {result['run_count']} runs")
    else:
        print("❌ Not enough runs for baseline. Need 3+ completed runs with same config.")


# ── Grid Commands ────────────────────────────────────────────────────────────

grid_cap_app = typer.Typer(help="Capability grid — model × config comparison matrix", no_args_is_help=True)
app.add_typer(grid_cap_app, name="grid")


@grid_cap_app.command(name="run")
def grid_cap_run(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    models: Optional[str] = typer.Option(None, "--models", "-m",
                                          help="Comma-separated model specs (default: flash,pro,ornith)"),
    configs: Optional[str] = typer.Option(None, "--configs", "-c",
                                           help="Comma-separated config labels (default: baseline-v3,baseline-v2)"),
    task_ids: Optional[str] = typer.Option(None, "--tasks", "-t",
                                            help="Comma-separated task IDs (default: all)"),
    trials: int = typer.Option(3, "--trials", "-n", help="Trials per task per cell"),
) -> None:
    """Run full grid: all models × configs × tasks using DirectModelAdapter.

    Calls each model's chat API directly (bypasses agent harness) to measure
    raw model capability on canary tasks. Results stored in grid_runs/grid_results.
    """
    from observeco.capability.grid import CapabilityGridRunner

    # Resolve models
    model_list = ["custom-ollama/deepseek-v4-flash", "custom-ollama/deepseek-v4-pro", "custom-ollama/ornith:latest"]
    if models:
        model_list = [m.strip() for m in models.split(",")]

    # Resolve configs
    config_list = ["baseline-v3", "baseline-v2"]
    if configs:
        config_list = [c.strip() for c in configs.split(",")]

    # Resolve tasks
    task_id_list = None
    if task_ids:
        task_id_list = [t.strip() for t in task_ids.split(",")]

    print("\n🧪 Capability Grid")
    print(f"   Agent: {agent}")
    print(f"   Models: {model_list}")
    print(f"   Configs: {config_list}")
    print(f"   Tasks: {task_id_list or 'all'}")
    print(f"   Trials: {trials}")
    print()

    runner = CapabilityGridRunner()
    result = runner.run(
        agent_name=agent,
        models=model_list,
        configs=config_list,
        task_ids=task_id_list,
        trials=trials,
    )

    if result.get("error"):
        print(f"❌ {result['error']}")
        return

    cells = result.get("cells", [])
    print(f"✅ Grid complete — {len(cells)} cells")
    print(f"   Run ID: {result['run_id']}")
    print(f"   Total cost: ${result.get('total_cost', 0):.4f}")
    print()

    # Print summary table
    task_names = list(dict.fromkeys(c["task_name"] for c in cells))
    for task_name in task_names:
        print(f"  {task_name}")
        for cell in cells:
            if cell["task_name"] == task_name:
                acc = cell["accuracy"] * 100 if cell["accuracy"] is not None else 0
                ci = f"[{cell['ci_lower']*100:.0f}–{cell['ci_upper']*100:.0f}]" if cell["ci_lower"] is not None else ""
                cost = f"${cell['cost']:.4f}" if cell.get("cost") else "—"
                hang = " ⏰" if cell.get("hang") else ""
                print(f"    {cell['model']:<40} {cell['config']:<15} {acc:.0f}% {ci:<12} {cost}{hang}")
        print()
    print("   View results: observeco grid list")


@grid_cap_app.command(name="list")
def grid_cap_list(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of runs to show"),
) -> None:
    """List recent grid runs."""
    from observeco.db import Database

    conn = Database()._get_conn()
    rows = conn.execute(
        "SELECT id, agent_name, started_at, completed_at, status, total_cells, total_cost "
        "FROM grid_runs WHERE agent_name = ? ORDER BY started_at DESC LIMIT ?",
        (agent, limit),
    ).fetchall()

    if not rows:
        print(f"No grid runs for agent '{agent}'. Run 'observeco grid run'.")
        return

    print(f"\n📊 Grid Runs — {agent} ({len(rows)} runs)")
    print(f"{'Run ID':<10} {'Started':<20} {'Status':<12} {'Cells':>8} {'Cost':>10}")
    print("-" * 62)
    for r in rows:
        print(f"{r['id'][:8]:<10} {r['started_at'][:19]:<20} "
              f"{r['status']:<12} {r['total_cells']:>8} ${r['total_cost'] or 0:>9.4f}")


@grid_cap_app.command(name="compare")
def grid_cap_compare(
    run_id: Optional[str] = typer.Option(None, "--run-id", "-r", help="Grid run ID to display"),
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    baseline: bool = typer.Option(False, "--baseline", "-b", help="Compare against baseline"),
) -> None:
    """Display grid results or compare two runs."""
    import json

    from observeco.db import Database

    conn = Database()._get_conn()

    # Get latest run if not specified
    if not run_id:
        row = conn.execute(
            "SELECT id FROM grid_runs WHERE agent_name = ? AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT 1",
            (agent,),
        ).fetchone()
        if not row:
            print(f"No completed grid runs for '{agent}'. Run 'observeco grid run' first.")
            return
        run_id = row["id"]

    cells = conn.execute(
        "SELECT gr.task_id, ct.name as task_name, gr.model, gr.config, "
        "gr.accuracy, gr.ci_lower, gr.ci_upper, gr.cost, gr.flags, gr.hang "
        "FROM grid_results gr JOIN canary_tasks ct ON gr.task_id = ct.id "
        "WHERE gr.grid_run_id = ? ORDER BY ct.id, gr.model, gr.config",
        (run_id,),
    ).fetchall()

    if not cells:
        print(f"No results for grid run {run_id[:8]}")
        return

    # Organize by task
    cells_by_task = {}
    for c in cells:
        task = c["task_name"]
        if task not in cells_by_task:
            cells_by_task[task] = []
        cells_by_task[task].append(c)

    print(f"\n📊 Grid Report — {run_id[:8]}")
    print()

    for task_name, task_cells in cells_by_task.items():
        print(f"📋 {task_name}")
        print(f"   {'Model':<22} {'Config':<15} {'Accuracy':>10} {'CI':>16} {'Flags':>10}")
        print(f"   {'-'*22} {'-'*15} {'-'*10} {'-'*16} {'-'*10}")
        for c in task_cells:
            flags = json.loads(c["flags"]) if c["flags"] else []
            flag_str = ",".join(flags) if flags else "—"
            acc_str = f"{c['accuracy']:.1%}" if c["accuracy"] is not None else "Hang"
            ci_str = f"[{c['ci_lower']:.1%}, {c['ci_upper']:.1%}]" if c["ci_lower"] is not None else "—"
            print(f"   {c['model']:<22} {c['config']:<15} {acc_str:>10} {ci_str:>16} {flag_str:>10}")
        print()


# ── Task Commands ────────────────────────────────────────────────────────────

task_app = typer.Typer(help="Canary task management", no_args_is_help=True)
app.add_typer(task_app, name="task")


@task_app.command(name="list")
def task_list(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent (not used for task list)"),
) -> None:
    """List all canary tasks with status indicators."""
    from observeco.capability.canary import CanaryRunner
    from observeco.db import Database

    runner = CanaryRunner(db=Database())
    tasks = runner.list_tasks()

    if not tasks:
        print("No tasks defined. Create with 'observeco task create'.")
        return

    print(f"\n📋 Canary Tasks ({len(tasks)})")
    print(f"{'ID':<32} {'Name':<32} {'Assertions':>5} {'Timeout':>8} {'Trials':>7}")
    print("-" * 88)
    for t in tasks:
        try:
            assertions = json.loads(t["assertions"]) if isinstance(t["assertions"], str) else t["assertions"]
            a_count = len(assertions) if isinstance(assertions, list) else 0
        except Exception:
            a_count = 0
        print(f"{t['id']:<32} {t['name']:<32} {a_count:>5} {t['timeout']:>8}s {t['trials']:>7}")


@task_app.command(name="create")
def task_create(
    yaml_file: Optional[str] = typer.Option(None, "--yaml", "-f", help="Path to task YAML file"),
) -> None:
    """Create a new canary task from YAML or interactive prompt."""
    import json

    from observeco.capability.canary import CanaryRunner
    from observeco.db import Database

    if yaml_file:
        import yaml
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
    else:
        # Interactive mode
        print("Interactive task creation (Ctrl+C to cancel)")
        name = input("Task name (slug, e.g., 'chart-interpretation'): ").strip()
        if not name:
            print("❌ Task name required")
            return
        display_name = input("Display name: ").strip() or name
        description = input("Description (optional): ").strip()
        prompt = input("Prompt template: ").strip()
        if not prompt:
            print("❌ Prompt required")
            return

        print("\nAssertion types: exact_match, contains, numeric_range, regex, llm_judge, json_schema, ordering, tool_call_validation")
        a_type = input("Assertion type: ").strip()

        assertions = []
        if a_type == "exact_match":
            target = input("Expected exact output: ")
            assertions = [{"type": "exact_match", "target": target}]
        elif a_type == "contains":
            keywords_str = input("Keywords (comma-separated): ")
            keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
            assertions = [{"type": "contains", "keywords": keywords}]
        elif a_type == "numeric_range":
            lo = float(input("Min value: ") or "0")
            hi = float(input("Max value: ") or "100")
            assertions = [{"type": "numeric_range", "min": lo, "max": hi}]
        elif a_type == "regex":
            pattern = input("Regex pattern: ")
            assertions = [{"type": "regex", "pattern": pattern}]
        elif a_type == "llm_judge":
            criteria = input("Evaluation criteria: ")
            assertions = [{"type": "llm_judge", "criteria": criteria}]
        elif a_type == "json_schema":
            print("Enter JSON Schema (as JSON dict, then Ctrl+D on empty line):")
            schema_lines = []
            try:
                while True:
                    line = input()
                    schema_lines.append(line)
            except EOFError:
                pass
            schema_str = "\n".join(schema_lines)
            try:
                import json
                schema = json.loads(schema_str) if schema_str else {}
            except json.JSONDecodeError:
                print("⚠️  Invalid JSON, using empty schema")
                schema = {}
            assertions = [{"type": "json_schema", "schema": schema}]
        elif a_type == "ordering":
            steps_str = input("Steps in order (comma-separated): ")
            steps = [s.strip() for s in steps_str.split(",") if s.strip()]
            assertions = [{"type": "ordering", "steps": steps}]
        elif a_type == "tool_call_validation":
            tool = input("Expected tool name: ")
            args_str = input("Expected args as key=value pairs (comma-separated, optional): ").strip()
            args = {}
            if args_str:
                for pair in args_str.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        args[k.strip()] = v.strip()
            assertions = [{"type": "tool_call_validation", "expected_tool": tool}]
            if args:
                assertions[0]["expected_args"] = args
        else:
            print(f"❌ Unknown assertion type: {a_type}")
            return

        timeout_str = input("Timeout (seconds, default 60): ").strip()
        timeout = int(timeout_str) if timeout_str else 60

        trials_str = input("Trials (default 3): ").strip()
        trials = int(trials_str) if trials_str else 3

        data = {
            "id": name,
            "name": display_name,
            "description": description,
            "prompt": prompt,
            "assertions": assertions,
            "timeout": timeout,
            "trials": trials,
        }

    runner = CanaryRunner(db=Database())
    result = runner.create_task(data)
    if result["ok"]:
        print(f"✅ Task created: {result['task_id']}")
    else:
        print(f"❌ Failed: {result['error']}")


@task_app.command(name="delete")
def task_delete(
    task_id: str = typer.Argument(..., help="Task ID to delete"),
) -> None:
    """Delete a canary task."""
    from observeco.capability.canary import CanaryRunner
    from observeco.db import Database

    runner = CanaryRunner(db=Database())
    result = runner.delete_task(task_id)
    if result["ok"]:
        print(f"✅ Task deleted: {task_id}")
    else:
        print(f"❌ Failed: {result['error']}")


@task_app.command(name="validate")
def task_validate(
    yaml_file: str = typer.Argument(..., help="Path to task YAML file to validate"),
) -> None:
    """Validate a task YAML file without saving."""
    import yaml

    try:
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        # Required fields
        required = ["name", "prompt", "assertions"]
        missing = [f for f in required if f not in data]
        if missing:
            print(f"❌ Missing required fields: {missing}")
            return

        # Validate assertion types
        valid_types = {"exact_match", "contains", "numeric_range", "regex", "llm_judge"}
        for i, a in enumerate(data.get("assertions", [])):
            if a.get("type") not in valid_types:
                print(f"❌ Assertion {i}: unknown type '{a.get('type')}'. Valid: {valid_types}")
                return

        print(f"✅ YAML valid — task '{data['name']}' with {len(data['assertions'])} assertion(s)")
    except Exception as exc:
        print(f"❌ Validation failed: {exc}")


if __name__ == "__main__":
    app()
