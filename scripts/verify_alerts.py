#!/usr/bin/env python3
"""Verify alerts routes (/api/alerts/live, /api/alerts) against raw DB.

Usage:
    python3 scripts/verify_alerts.py

Exits 0 if all checks pass, 1 if any mismatch found.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from observeco.db import Database

PASS = "✓"
FAIL = "✗"
db = Database()


def build_raw_alerts(now: int) -> list[dict]:
    """Replicate alerts.py build_alerts(mode='center') logic."""
    try:
        circuit = db.get_circuit_breakers()
        drift = db.get_drift()
        pulses = db.get_recent_pulses(limit=100)
        errors = db.get_errors(limit=50)
    except Exception:
        return []

    alerts = []

    # CRITICAL: tripped circuit breakers
    for cb in circuit:
        if cb.get("tripped"):
            name = cb["agent_name"]
            failures = cb.get("failure_count", 0)
            ts = cb.get("cooldown_until") or (now - 300)
            alerts.append({
                "severity": "critical",
                "group": "CRITICAL",
                "agent": name,
                "category": "circuit",
                "message": f"Circuit breaker tripped ({failures} failures)",
                "timestamp": ts,
            })

    # WARNING: drift breaches >10%
    drift_breaches = [d for d in drift if d.get("breached") and d.get("delta_pct", 0) > 10]
    for d in drift_breaches[:5]:
        agent = d["agent_name"]
        comp = d.get("component", "system prompt")
        pct = d.get("delta_pct", 0)
        ts = d.get("timestamp", now - 600)
        alerts.append({
            "severity": "warning",
            "group": "WARNING",
            "agent": agent,
            "category": "drift",
            "message": f"Drift {pct:+.1f}% in {comp}",
            "timestamp": ts,
        })

    # CRITICAL/WARNING: pulse-based
    seen_agents = set()
    for p in pulses:
        aname = p["agent_name"]
        if aname in seen_agents:
            continue
        seen_agents.add(aname)
        status = p.get("status", "")
        ts = p.get("timestamp", now - 300)
        if status == "dead":
            alerts.append({
                "severity": "critical",
                "group": "CRITICAL",
                "agent": aname,
                "category": "dead",
                "message": "Agent is dead — no recent heartbeat",
                "timestamp": ts,
            })
        elif status == "error":
            err_msg = p.get("error_message", "") or "Error state detected"
            alerts.append({
                "severity": "warning",
                "group": "WARNING",
                "agent": aname,
                "category": "error",
                "message": f"Error: {err_msg[:60]}",
                "timestamp": ts,
            })

    # Sort: severity order, ts desc
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["group"], 9), -a["timestamp"]))
    return alerts


def extract_live_alert_count(html: str) -> int:
    """Extract active alert count from live rail."""
    m = re.search(r'(\d+)\s*active', html)
    if m:
        return int(m.group(1))
    # "0 active" or "All clear"
    if "All clear" in html or "0 active" in html:
        return 0
    return -1


def extract_center_alert_count(html: str) -> int:
    """Extract alert count from center view."""
    # Count alert-row divs
    return len(re.findall(r'class="alert-row', html))


def main():
    now = int(time.time())

    print("Verifying /api/alerts/live + /api/alerts")
    print()

    # 1. Get raw alerts
    print("Querying raw DB...")
    raw = build_raw_alerts(now)
    critical = [a for a in raw if a["severity"] == "critical"]
    warning = [a for a in raw if a["severity"] == "warning"]
    print(f"  {len(raw)} total alerts: {len(critical)} critical, {len(warning)} warning")
    print()

    # 2. Hit the routes
    print("Fetching routes...")
    import urllib.request

    def fetch(path: str) -> str:
        url = f"http://127.0.0.1:8899{path}"
        req = urllib.request.Request(url)
        req.add_header("X-ObserveCo-Token", "FxrXunlGzEHN6mtX550m6okEgSjfe5xnI84YOIDLLFk")
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            return resp.read().decode()
        except Exception as e:
            print(f"  {FAIL} Failed to fetch {path}: {e}")
            return ""

    live_html = fetch("/api/alerts/live")
    center_html = fetch("/api/alerts")

    if not live_html or not center_html:
        sys.exit(1)

    print(f"  Live: {len(live_html)} bytes")
    print(f"  Center: {len(center_html)} bytes")
    print()

    all_pass = True

    print("=== Live Incidents Rail ===")
    live_count = extract_live_alert_count(live_html)
    # Live shows only CRITICAL + WARNING (no INFO)
    expected_live = len(critical) + len(warning)
    if live_count == expected_live:
        print(f"  {PASS} live_alert_count: {live_count}")
    else:
        print(f"  {FAIL} live_alert_count: got={live_count}, expected={expected_live}")
        all_pass = False

    print()
    print("=== Alert Center ===")
    center_count = extract_center_alert_count(center_html)
    # Center shows all alerts (CRITICAL + WARNING + INFO)
    expected_center = len(raw)
    if center_count == expected_center:
        print(f"  {PASS} center_alert_count: {center_count}")
    else:
        print(f"  {FAIL} center_alert_count: got={center_count}, expected={expected_center}")
        all_pass = False

    # Verify specific alert messages appear
    print()
    print("=== Alert Content Spot-Checks ===")
    for a in raw[:3]:
        if a["agent"] in center_html and a["message"][:20] in center_html:
            print(f"  {PASS} Alert present: {a['agent']} — {a['message'][:40]}")
        else:
            print(f"  {FAIL} Alert missing: {a['agent']} — {a['message'][:40]}")
            all_pass = False

    print()
    if all_pass:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED — see above")
        sys.exit(1)


if __name__ == "__main__":
    main()
