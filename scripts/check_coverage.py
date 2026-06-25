#!/usr/bin/env python3
"""Test coverage tracker — runs pytest --cov, tracks trend, alerts on drops."""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from watchdog_flag_writer import write_flag

PROJECT_ROOT = Path.home() / "projects/observeco"
STATE_FILE = Path.home() / ".observeco" / "coverage_history.json"
COVERAGE_WARN = 70
COVERAGE_CRITICAL = 50


def run_coverage():
    """Run pytest with coverage and parse output."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--cov=src/observeco", "--cov-report=term", "-q"],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_ROOT),
        )
        output = result.stdout + result.stderr

        # Parse "TOTAL" line: TOTAL    1234    56    95%"
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            return int(match.group(1))

        # Try alternative format
        match = re.search(r"coverage:\s+(\d+)%", output)
        if match:
            return int(match.group(1))

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def load_history():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"entries": []}


def save_history(history):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(history, indent=2))


def main():
    coverage = run_coverage()
    if coverage is None:
        return  # couldn't run — silent

    history = load_history()
    today = time.strftime("%Y-%m-%d")
    entry = {"date": today, "coverage": coverage}

    # Deduplicate by date
    history["entries"] = [e for e in history["entries"] if e["date"] != today]
    history["entries"].append(entry)
    history["entries"] = history["entries"][-90:]
    save_history(history)

    alerts = []

    # Threshold check
    if coverage <= COVERAGE_CRITICAL:
        alerts.append(f"🔴 Coverage: {coverage}% (critical threshold: {COVERAGE_CRITICAL}%)")
    elif coverage <= COVERAGE_WARN:
        alerts.append(f"🟡 Coverage: {coverage}% (warn threshold: {COVERAGE_WARN}%)")

    # Trend check — compare to last 7 entries
    recent = [e["coverage"] for e in history["entries"][-8:]]
    if len(recent) >= 2:
        old_avg = sum(recent[:-1]) / len(recent[:-1])
        current = recent[-1]
        drop = old_avg - current
        if drop >= 5:
            alerts.append(f"📉 Coverage dropped {drop:.0f}pp from rolling avg ({old_avg:.0f}% → {current}%)")

    if alerts:
        lines = ["🧪 TEST COVERAGE", ""]
        lines.extend(alerts)
        lines.append(f"\nCurrent: {coverage}%")
        if len(recent) >= 2:
            lines.append(f"Rolling avg (last 7 runs): {sum(recent)/len(recent):.0f}%")
        print("\n".join(lines))

        severity = "critical" if coverage <= COVERAGE_CRITICAL else "warning"
        write_flag(
            source="check_coverage",
            severity=severity,
            summary=f"Test coverage: {coverage}%",
            investigation_type="code_smell",
            context={
                "coverage": coverage,
                "threshold_warn": COVERAGE_WARN,
                "threshold_critical": COVERAGE_CRITICAL,
                "trend": recent[-5:] if len(recent) >= 5 else recent,
            },
            proposed_action=(
                f"Coverage at {coverage}%. "
                + ("Critical — add tests to core modules." if coverage <= COVERAGE_CRITICAL
                   else "Below warning threshold — review untested code paths.")
            ),
        )


if __name__ == "__main__":
    main()
