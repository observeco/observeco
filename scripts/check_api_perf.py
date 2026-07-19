#!/usr/bin/env python3
"""API response time baseline — curls main endpoints, tracks p50/p95, alerts on degradation."""

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from watchdog_flag_writer import write_flag

STATE_FILE = Path.home() / ".observeco" / "api_perf_history.json"
ENDPOINTS = [
    "/",
    "/api/fleet-summary",
    "/api/agents",
    "/api/errors",
    "/api/alerts",
]
RESPONSE_WARN_MS = 2000
RESPONSE_CRITICAL_MS = 5000
ROUNDS = 3  # curl each endpoint N times


def measure_endpoint(base_url: str, path: str) -> float | None:
    """Measure response time for a single endpoint (ms)."""
    try:
        result = subprocess.run(
            ["curl", "-o", "/dev/null", "-s", "-w", "%{time_total}",
             f"{base_url}{path}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip()) * 1000  # convert to ms
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return None


def main():
    # Check if server is running
    try:
        check = subprocess.run(
            ["curl", "-o", "/dev/null", "-s", "-w", "%{http_code}",
             "http://localhost:9123/"],
            capture_output=True, text=True, timeout=5,
        )
        if check.stdout.strip() != "200":
            return  # server not running — silent
    except (subprocess.TimeoutExpired, Exception):
        return

    base_url = "http://localhost:9123"
    measurements = {}

    for path in ENDPOINTS:
        times = []
        for _ in range(ROUNDS):
            ms = measure_endpoint(base_url, path)
            if ms is not None:
                times.append(ms)
        if times:
            measurements[path] = {
                "p50": statistics.median(times),
                "p95": sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
                "max": max(times),
            }

    if not measurements:
        return

    # Save to history
    history = load_history()
    today = time.strftime("%Y-%m-%d")
    entry = {"date": today, "endpoints": measurements}
    history["entries"] = [e for e in history["entries"] if e["date"] != today]
    history["entries"].append(entry)
    history["entries"] = history["entries"][-30:]
    save_history(history)

    # Check for degradation
    alerts = []
    for path, m in measurements.items():
        if m["p95"] >= RESPONSE_CRITICAL_MS:
            alerts.append(f"🔴 {path}: p95 {m['p95']:.0f}ms (critical: {RESPONSE_CRITICAL_MS}ms)")
        elif m["p95"] >= RESPONSE_WARN_MS:
            alerts.append(f"🟡 {path}: p95 {m['p95']:.0f}ms (warn: {RESPONSE_WARN_MS}ms)")

    # Trend check — compare to 7 days ago
    old_entries = [e for e in history["entries"] if e["date"] != today]
    if old_entries:
        old = old_entries[-1]["endpoints"]
        for path, m in measurements.items():
            if path in old:
                old_p95 = old[path]["p95"]
                if m["p95"] > old_p95 * 1.5 and m["p95"] - old_p95 > 200:
                    alerts.append(f"📈 {path}: p95 degraded {old_p95:.0f}ms → {m['p95']:.0f}ms")

    if alerts:
        lines = ["⚡ API PERFORMANCE", ""]
        lines.extend(alerts)
        lines.append("")
        for path, m in sorted(measurements.items()):
            lines.append(f"  {path}: p50={m['p50']:.0f}ms p95={m['p95']:.0f}ms")
        print("\n".join(lines))

        # Write flag for Hound
        worst_endpoint = max(measurements.items(), key=lambda x: x[1]["p95"])
        write_flag(
            source="check_api_perf",
            severity="critical" if any("🔴" in a for a in alerts) else "warning",
            summary=f"API slow: worst p95={worst_endpoint[1]['p95']:.0f}ms on {worst_endpoint[0]}",
            investigation_type="performance",
            context={
                "endpoints": {k: {"p50": v["p50"], "p95": v["p95"]} for k, v in measurements.items()},
                "thresholds": {"warn_ms": RESPONSE_WARN_MS, "critical_ms": RESPONSE_CRITICAL_MS},
            },
            proposed_action=(
                f"Profile {worst_endpoint[0]} — p95 at {worst_endpoint[1]['p95']:.0f}ms. "
                f"Check for N+1 queries, missing indexes, or unoptimised templates."
            ),
        )


def load_history():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"entries": []}


def save_history(history):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(history, indent=2))


if __name__ == "__main__":
    main()
