#!/usr/bin/env python3
"""Lifecycle stall detection — flags features stuck in one state for 14+ days."""

import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from watchdog_flag_writer import write_flag

STATE_FILE = Path.home() / ".observeco" / "lifecycle.json"
STALL_THRESHOLD_DAYS = 14


def main():
    if not STATE_FILE.exists():
        return

    data = json.loads(STATE_FILE.read_text())
    features = data.get("features", {})
    now = time.time()

    stalled = []
    for name, feat in features.items():
        updated = feat.get("updated_at", 0)
        state = feat.get("state", "unknown")
        days = (now - updated) / 86400 if updated else 999

        if days >= STALL_THRESHOLD_DAYS and state != "maintain":
            stalled.append({
                "name": name,
                "state": state,
                "days": int(days),
                "owner": feat.get("owner", "unassigned"),
            })

    if stalled:
        lines = ["⏰ LIFECYCLE STALL DETECTION", ""]
        for s in sorted(stalled, key=lambda x: -x["days"]):
            lines.append(f"  🔴 {s['name']}: stuck in '{s['state']}' for {s['days']} days (owner: {s['owner']})")
        lines.append("")
        lines.append(f"{len(stalled)} feature(s) stalled beyond {STALL_THRESHOLD_DAYS}-day threshold.")
        print("\n".join(lines))

        for s in stalled:
            write_flag(
                source="check_stall",
                severity="warning",
                summary=f"{s['name']} stuck in '{s['state']}' for {s['days']} days",
                investigation_type="stall",
                context={
                    "feature": s["name"],
                    "state": s["state"],
                    "days_stalled": s["days"],
                    "owner": s["owner"],
                },
                proposed_action=(
                    f"{s['name']} stalled {s['days']} days in '{s['state']}'. "
                    f"Check if blocked, reprioritised, or abandoned. "
                    f"If abandoned, archive. If blocked, identify blocker and propose unblock."
                ),
            )


if __name__ == "__main__":
    main()
