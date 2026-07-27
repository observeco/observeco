#!/usr/bin/env python3
"""Verify agent detail modal route (/api/fleet/modal/{agent}) against raw DB.

Usage:
    python3 scripts/verify_agent_modal.py [--agent hermes-agent]

Exits 0 if all checks pass, 1 if any mismatch found.
"""

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from observeco.db import Database

PASS = "✓"
FAIL = "✗"
db = Database()


def _fmt_ts(ts: int) -> str:
    now = int(time.time())
    delta = now - ts
    if delta < 60: return f"{delta}s ago"
    elif delta < 3600: return f"{delta // 60}m ago"
    elif delta < 86400: return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def get_raw_agent_state(name: str, now: int) -> dict:
    """Query raw DB for an agent's state."""
    conn = db._get_conn()

    agents = db.get_agents()
    known = {a["agent_name"]: a for a in agents}
    agent_cfg = known.get(name, {})
    is_agent = agent_cfg.get("class") == "agent"

    pulses = db.get_recent_pulses(agent_name=name, limit=48)
    errors_raw = db.get_errors(agent_name=name, limit=50)
    circuit_list = db.get_circuit_breakers()
    circuit = next((c for c in circuit_list if c.get("agent_name") == name), {})
    trims = db.get_trims(agent_name=name, limit=30)
    drift = db.get_drift(agent_name=name)

    # Agent state
    status = "alive"
    cls = "healthy"
    if pulses:
        status = pulses[0].get("status", "alive")
        last_ts = pulses[0].get("timestamp", 0)
        delta = now - last_ts
    else:
        last_ts = 0
        delta = 999999

    if status == "dead" and delta > 300: cls = "critical"
    elif status == "error": cls = "warning"
    elif status != "alive": cls = "unknown"

    framework = agent_cfg.get("framework", "Hermes")
    errors_24h = len([e for e in errors_raw if e.get("timestamp", 0) > now - 86400])

    # Token composition
    trim = trims[0] if trims else {}
    t_identity = trim.get("identity_tokens", 0)
    t_skills = trim.get("skills_tokens", 0)
    t_memory = trim.get("memory_tokens", 0)
    t_tools = trim.get("tools_tokens", 0)
    t_guidance = trim.get("guidance_tokens", 0)
    t_total = t_identity + t_skills + t_memory + t_tools + t_guidance
    if not t_total:
        t_total = trim.get("total_tokens", 0)

    # Circuit
    tripped = circuit.get("tripped", False)
    fails = circuit.get("failure_count", 0)

    # Garden
    garden = []
    try:
        garden = db.get_recent_garden(agent_name=name, limit=10) if hasattr(db, 'get_recent_garden') else []
    except Exception:
        pass

    debt = 0
    duplicates = 0
    contradictions = 0
    stale = 0
    if garden:
        g = garden[0]
        debt = g.get("memory_debt_score", 0) or 0
        duplicates = g.get("duplicates_found", 0) or 0
        contradictions = g.get("contradictions_found", 0) or 0
        stale = g.get("stale_entries", 0) or 0

    return {
        "name": name,
        "cls": cls,
        "status": status,
        "last_ts": last_ts,
        "framework": framework,
        "is_agent": is_agent,
        "errors_24h": errors_24h,
        "t_total": t_total,
        "tripped": tripped,
        "fails": fails,
        "debt": debt,
        "duplicates": duplicates,
        "contradictions": contradictions,
        "stale": stale,
        "pulse_count": len(pulses),
        "error_count": len(errors_raw),
        "drift_count": len(drift),
    }


def extract_modal_values(html: str) -> dict:
    """Extract key values from modal HTML."""
    result = {}

    # Agent name in m-head
    m = re.search(r'<span class="m-name">([^<]+)</span>', html)
    if m:
        result["name"] = m.group(1)

    # Badge text (HEALTHY, CRITICAL, etc.)
    m = re.search(r'<span class="m-badge[^"]*">([^<]+)</span>', html)
    if m:
        result["badge"] = m.group(1)

    # Framework
    m = re.search(r'<span class="m-fw">([^<]+)</span>', html)
    if m:
        result["framework"] = m.group(1)

    # Error count in errors tab
    m = re.search(r'last 24h · (\d+) events', html)
    if m:
        result["errors_24h"] = int(m.group(1))

    # Token total
    m = re.search(r'Total: <span class="num">([^<]+)</span> tokens', html)
    if m:
        result["t_total_str"] = m.group(1)

    # Memory debt
    m = re.search(r'<div class="debt-score"[^>]*>(\d+)</div>', html)
    if m:
        result["debt"] = int(m.group(1))

    # Duplicates
    m = re.search(r'<div class="n">(\d+)</div><div class="l">Duplicates</div>', html)
    if m:
        result["duplicates"] = int(m.group(1))

    # Contradictions
    m = re.search(r'<div class="n">(\d+)</div><div class="l">Contradictions</div>', html)
    if m:
        result["contradictions"] = int(m.group(1))

    # Stale
    m = re.search(r'<div class="n">(\d+)</div><div class="l">Stale Entries</div>', html)
    if m:
        result["stale"] = int(m.group(1))

    # Guard status
    m = re.search(r'Guard is <b[^>]*>([^<]+)</b>', html)
    if m:
        result["guard_status"] = m.group(1)

    return result


def main():
    parser = argparse.ArgumentParser(description="Verify agent detail modal against raw DB")
    parser.add_argument("--agent", type=str, default="hermes-agent", help="Agent name to verify")
    args = parser.parse_args()

    now = int(time.time())
    name = args.agent

    print(f"Verifying /api/fleet/modal/{name}")
    print()

    # 1. Get raw DB state
    print("Querying raw DB...")
    raw = get_raw_agent_state(name, now)
    print(f"  {raw['name']}: cls={raw['cls']}, status={raw['status']}, is_agent={raw['is_agent']}")
    print(f"  tokens={raw['t_total']}, errors_24h={raw['errors_24h']}, debt={raw['debt']}")
    print()

    # 2. Hit the route
    print("Fetching route...")
    import urllib.request
    url = f"http://127.0.0.1:8899/api/fleet/modal/{name}?tab=health"
    req = urllib.request.Request(url)
    req.add_header("X-ObserveCo-Token", "FxrXunlGzEHN6mtX550m6okEgSjfe5xnI84YOIDLLFk")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode()
    except Exception as e:
        print(f"  {FAIL} Failed to fetch route: {e}")
        sys.exit(1)
    print(f"  {len(html)} bytes received")
    print()

    # 3. Extract and compare
    all_pass = True
    m = extract_modal_values(html)

    print("=== Agent Modal Verification ===")

    # Name
    if "name" in m:
        if m["name"] == name:
            print(f"  {PASS} name: {m['name']}")
        else:
            print(f"  {FAIL} name: got={m['name']}, expected={name}")
            all_pass = False

    # Badge (class)
    if "badge" in m:
        expected_badge = raw["cls"].upper()
        if m["badge"] == expected_badge:
            print(f"  {PASS} badge: {m['badge']}")
        else:
            print(f"  {FAIL} badge: got={m['badge']}, expected={expected_badge}")
            all_pass = False

    # Framework
    if "framework" in m:
        if m["framework"] == raw["framework"]:
            print(f"  {PASS} framework: {m['framework']}")
        else:
            print(f"  {FAIL} framework: got={m['framework']}, expected={raw['framework']}")
            all_pass = False

    # Errors 24h
    if "errors_24h" in m:
        if m["errors_24h"] == raw["errors_24h"]:
            print(f"  {PASS} errors_24h: {m['errors_24h']}")
        else:
            print(f"  {FAIL} errors_24h: got={m['errors_24h']}, expected={raw['errors_24h']}")
            all_pass = False

    # Guard status
    if "guard_status" in m:
        expected_guard = "STOPPED" if raw["tripped"] else "OK" if raw["fails"] == 0 else f"ARMED ({raw['fails']}/3)"
        if m["guard_status"] == expected_guard:
            print(f"  {PASS} guard_status: {m['guard_status']}")
        else:
            print(f"  {FAIL} guard_status: got={m['guard_status']}, expected={expected_guard}")
            all_pass = False

    # Memory debt (only for agents)
    if raw["is_agent"] and "debt" in m:
        if m["debt"] == raw["debt"]:
            print(f"  {PASS} debt: {m['debt']}")
        else:
            print(f"  {FAIL} debt: got={m['debt']}, expected={raw['debt']}")
            all_pass = False

    if raw["is_agent"] and "duplicates" in m:
        if m["duplicates"] == raw["duplicates"]:
            print(f"  {PASS} duplicates: {m['duplicates']}")
        else:
            print(f"  {FAIL} duplicates: got={m['duplicates']}, expected={raw['duplicates']}")
            all_pass = False

    if raw["is_agent"] and "contradictions" in m:
        if m["contradictions"] == raw["contradictions"]:
            print(f"  {PASS} contradictions: {m['contradictions']}")
        else:
            print(f"  {FAIL} contradictions: got={m['contradictions']}, expected={raw['contradictions']}")
            all_pass = False

    if raw["is_agent"] and "stale" in m:
        if m["stale"] == raw["stale"]:
            print(f"  {PASS} stale: {m['stale']}")
        else:
            print(f"  {FAIL} stale: got={m['stale']}, expected={raw['stale']}")
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
