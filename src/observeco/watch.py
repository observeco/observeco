"""`observeco watch` — background auto-collection daemon.

Polls registered agents' health endpoints on a configurable interval.
Auto-discovers new agents from Hermes/OpenClaw/other configs.
Writes results to SQLite so the dashboard auto-populates.
"""

from __future__ import annotations

import signal
import time

from observeco.config import load_config
from observeco.db import Database
from observeco.pulse.check import _probe_agent


def run_watch(
    interval: int = 30,
    daemon: bool = False,
    once: bool = False,
) -> None:
    """Run the auto-collection loop.

    Args:
        interval: Seconds between polls (default 30)
        daemon: Run continuously (background mode)
        once: Single pass and exit
    """
    db = Database()
    running = True

    def handle_signal(sig, frame):
        nonlocal running
        print(f"\nObserveCo watch: received signal {sig}, shutting down...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    cycle = 0

    print(f"ObserveCo watch: starting (interval={interval}s, daemon={daemon})")

    while running:
        cycle += 1
        timestamp = int(time.time())

        # 1. Load config — picks up new agents automatically
        config = load_config()

        # 2. Auto-discover new agents (Hermes, OpenClaw, etc.)
        try:
            from observeco.auto_detect import run_discover
            run_discover(show_all=False)
        except Exception:
            pass  # Discovery is best-effort

        # 3. Re-load config after discovery
        config = load_config()
        agents = getattr(config, "agents", [])

        if not agents:
            if cycle == 1:
                print("  No agents found. Run 'observeco agents add <name> --health-check <cmd>'")
                print("  Or: ensure Hermes config exists at ~/.hermes/config.yaml")
        else:
            results = []
            for agent in agents:
                try:
                    status, latency, error = _probe_agent(agent)
                    db.log_pulse(
                        agent_name=agent.name,
                        agent_framework=getattr(agent, "framework", "custom"),
                        status=status,
                        latency_ms=latency * 1000,
                    )
                    results.append((agent.name, status, latency))
                except Exception as e:
                    db.log_pulse(
                        agent_name=agent.name,
                        agent_framework=getattr(agent, "framework", "custom"),
                        status="error",
                        latency_ms=0,
                    )
                    db.log_error(
                        agent_name=agent.name,
                        error_type="watch_probe_failed",
                        error_message=str(e),
                        severity="error",
                    )
                    results.append((agent.name, "error", 0))

            # Print summary every cycle
            alive = sum(1 for _, s, _ in results if s == "alive")
            dead = sum(1 for _, s, _ in results if s == "dead")
            error = sum(1 for _, s, _ in results if s == "error")
            print(f"  [{timestamp}] Cycle {cycle}: {len(results)} agents — {alive} alive, {dead} dead, {error} errors")

        if once:
            break

        # Sleep in short intervals so we respond to signals quickly
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    print("ObserveCo watch: stopped.")
