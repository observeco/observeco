#!/usr/bin/env python3
"""Health trigger check — reads fleet data from pulse DB, runs enforcer checks.

Run via cron every 15 min. Outputs only when new flags are created (watchdog pattern).
"""

import json
import sys
import time
from pathlib import Path

# Add project src to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from observeco.lifecycle.enforcer import LifecycleEnforcer
from observeco.db import Database


def get_fleet_health() -> dict:
    """Read fleet health from pulse DB and return enforcer-compatible format."""
    db_path = Path.home() / ".observeco" / "pulse.db"
    if not db_path.exists():
        return {}

    db = Database()
    status = db.get_agent_status_summary()
    now = time.time()

    health = {}
    for agent_name, info in status.items():
        # Skip test stubs — never real agents
        if agent_name.startswith("test-"):
            continue
        entry = {
            "status": info.get("status", "unknown"),
            "drift_pct": 0.0,
            "error_count": 0,
            "check_count": 1,
        }

        # Dead agent — calculate how long
        if info.get("status") != "alive":
            ts = info.get("timestamp", 0)
            entry["dead_since"] = ts if ts else now
        else:
            entry["dead_since"] = 0

        # Error count from recent pulses
        try:
            pulses = db.get_recent_pulses(agent_name, limit=50)
            alive_count = sum(1 for p in pulses if p.get("status") == "alive")
            total = len(pulses) if pulses else 1
            entry["error_count"] = total - alive_count
            entry["check_count"] = total
        except Exception:
            pass

        # Drift — from latest pulse if available
        try:
            pulses = db.get_recent_pulses(agent_name, limit=1)
            if pulses and pulses[0].get("latency_ms"):
                entry["drift_pct"] = 0.0  # baseline; drift tracked separately
        except Exception:
            pass

        health[agent_name] = entry

    return health


def main():
    enforcer = LifecycleEnforcer()
    health = get_fleet_health()

    if not health:
        # No fleet data — nothing to check
        return

    new_flags = enforcer.check_health_triggers(health)

    if new_flags:
        # New flags created — output for delivery
        lines = ["⚠️ HEALTH FLAGS DETECTED", ""]
        for flag in new_flags:
            icon = "🔴" if flag.severity == "critical" else "🟡"
            lines.append(f"{icon} **{flag.agent}**: {flag.trigger}")
            lines.append(f"   {flag.details}")
            lines.append("")
        lines.append(f"Run `python -m observeco.lifecycle.enforcer flags` to see all active flags.")
        print("\n".join(lines))
    else:
        # No new flags — silent (watchdog pattern)
        pass


if __name__ == "__main__":
    main()
