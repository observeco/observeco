#!/usr/bin/env python3
"""Code complexity tracker — monitors server.py size and function counts.

Outputs only when thresholds are breached (watchdog pattern).
"""

import json
import re
import sys
from pathlib import Path

# Add hermes scripts dir to path for shared flag writer
sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from watchdog_flag_writer import write_flag

SERVER_PY = Path.home() / "projects/observeco/src/observeco/dashboard/server.py"
STATE_FILE = Path.home() / ".observeco" / "complexity_history.json"
THRESHOLDS = {
    "lines_warn": 4000,
    "lines_critical": 5500,
    "functions_warn": 80,
    "functions_critical": 120,
}


def measure():
    """Measure server.py complexity."""
    if not SERVER_PY.exists():
        return None

    content = SERVER_PY.read_text()
    lines = len(content.splitlines())
    functions = len(re.findall(r"^\s*def ", content, re.MULTILINE))
    classes = len(re.findall(r"^\s*class ", content, re.MULTILINE))

    return {
        "lines": lines,
        "functions": functions,
        "classes": classes,
    }


def load_history():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"entries": []}


def save_history(history):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(history, indent=2))


def main():
    stats = measure()
    if not stats:
        return

    history = load_history()

    # Record today's measurement
    import time
    today = time.strftime("%Y-%m-%d")
    entry = {"date": today, **stats}

    # Deduplicate by date
    history["entries"] = [e for e in history["entries"] if e["date"] != today]
    history["entries"].append(entry)

    # Keep last 90 days
    history["entries"] = history["entries"][-90:]
    save_history(history)

    # Check thresholds
    alerts = []
    if stats["lines"] >= THRESHOLDS["lines_critical"]:
        alerts.append(f"🔴 server.py: {stats['lines']} lines (critical: {THRESHOLDS['lines_critical']})")
    elif stats["lines"] >= THRESHOLDS["lines_warn"]:
        alerts.append(f"🟡 server.py: {stats['lines']} lines (warn: {THRESHOLDS['lines_warn']})")

    if stats["functions"] >= THRESHOLDS["functions_critical"]:
        alerts.append(f"🔴 Functions: {stats['functions']} (critical: {THRESHOLDS['functions_critical']})")
    elif stats["functions"] >= THRESHOLDS["functions_warn"]:
        alerts.append(f"🟡 Functions: {stats['functions']} (warn: {THRESHOLDS['functions_warn']})")

    # Trend check — compare to 30 days ago
    old_entries = [e for e in history["entries"] if e["date"] != today]
    if len(old_entries) >= 2:
        oldest = old_entries[0]
        line_growth = stats["lines"] - oldest["lines"]
        func_growth = stats["functions"] - oldest["functions"]
        if line_growth > 500:
            alerts.append(f"📈 +{line_growth} lines in 30 days ({oldest['lines']} → {stats['lines']})")
        if func_growth > 20:
            alerts.append(f"📈 +{func_growth} functions in 30 days ({oldest['functions']} → {stats['functions']})")

    if alerts:
        lines = ["📐 CODE COMPLEXITY", ""]
        lines.extend(alerts)
        lines.append(f"\nCurrent: {stats['lines']} lines, {stats['functions']} functions, {stats['classes']} classes")
        print("\n".join(lines))

        # Write flag for Hound
        severity = "critical" if any("🔴" in a for a in alerts) else "warning"
        write_flag(
            source="check_complexity",
            severity=severity,
            summary=f"server.py: {stats['lines']} lines, {stats['functions']} functions",
            investigation_type="code_smell",
            context={
                "lines": stats["lines"],
                "functions": stats["functions"],
                "classes": stats["classes"],
                "thresholds": THRESHOLDS,
                "trend": [e for e in history["entries"][-5:]],
            },
            proposed_action=(
                f"Analyse server.py and propose module extraction plan. "
                f"Threshold: {THRESHOLDS['lines_critical']} lines, currently {stats['lines']}. "
                f"Identify self-contained feature areas and propose FastAPI router extraction."
            ),
        )


if __name__ == "__main__":
    main()
