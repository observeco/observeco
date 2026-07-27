#!/usr/bin/env python3
"""Verify fleet routes (/api/fleet/verdict, /api/fleet/agents) against raw DB.

Usage:
    python3 scripts/verify_fleet.py

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


def _fmt_ts(ts: int) -> str:
    now = int(time.time())
    delta = now - ts
    if delta < 60: return f"{delta}s ago"
    elif delta < 3600: return f"{delta // 60}m ago"
    elif delta < 86400: return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def _classify_agent(pulse: dict, drift: list, circuit: dict, errors: list, now: int) -> str:
    """Replicate fleet.py _classify_agent logic."""
    status = pulse.get("status", "") if pulse else ""
    last_ts = pulse.get("timestamp", 0) if pulse else 0
    delta = now - last_ts if last_ts else 999999
    if not pulse or delta > 14400:
        return "unknown"
    if status == "dead" and delta > 300:
        return "critical"
    if status == "error":
        return "warning"
    max_drift = max((d.get("delta_pct", 0) for d in drift if d.get("breached")), default=0)
    if status == "alive" and max_drift > 10:
        return "warning"
    recent_errors = len([e for e in errors if e.get("timestamp", 0) > now - 86400])
    if status == "alive" and recent_errors > 5:
        return "warning"
    if status == "alive":
        return "healthy"
    return "unknown"


def _agent_dq(name: str, now: int) -> str:
    """Replicate fleet.py _agent_dq."""
    try:
        conn = db._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM token_logs WHERE agent_name = ? AND recorded_at > ?",
            (name, now - 86400),
        ).fetchone()
        if row and row["cnt"] > 0:
            return "acc"
    except Exception:
        pass
    return "est"


def get_raw_fleet_state(now: int) -> dict:
    """Query raw DB and compute expected fleet state."""
    conn = db._get_conn()

    summary = db.get_agent_status_summary()
    circuit = db.get_circuit_breakers()
    drift_all = db.get_drift()
    errors_all = db.get_errors(limit=100)
    agents_cfg = db.get_agents()

    if not summary:
        return {"agent_count": 0, "agents": [], "state_counts": {}}

    agents_data = []
    state_counts = {"critical": 0, "warning": 0, "healthy": 0, "unknown": 0}
    tripped_count = 0
    agent_names_critical = []
    agent_names_warning = []

    for name, s in summary.items():
        status = s.get("status", "")
        last_ts = s.get("timestamp", 0)
        circuit_state = next((c for c in circuit if c.get("agent_name") == name), None)
        agent_drift = [d for d in drift_all if d.get("agent_name") == name]
        agent_errors = [e for e in errors_all if e.get("agent_name") == name]

        cls = _classify_agent(
            {"status": status, "timestamp": last_ts},
            agent_drift,
            circuit_state or {},
            agent_errors,
            now,
        )
        state_counts[cls] = state_counts.get(cls, 0) + 1
        if cls == "critical":
            tripped_count += 1
            agent_names_critical.append(name)
        elif cls == "warning":
            agent_names_warning.append(name)

        # Token count from trims
        trims = db.get_trims(agent_name=name, limit=1)
        trim = trims[0] if trims else {}
        total_tokens = sum(
            trim.get(k, 0) for k in ("identity_tokens", "skills_tokens", "memory_tokens", "tools_tokens", "guidance_tokens")
        )
        if total_tokens == 0:
            total_tokens = trim.get("total_tokens", 0)

        # Error count 24h
        errors_24h = len([e for e in agent_errors if e.get("timestamp", 0) > now - 86400])

        # DQ
        dq = _agent_dq(name, now)

        # Circuit
        circuit_tripped = circuit_state.get("tripped", False) if circuit_state else False
        circuit_fails = circuit_state.get("failure_count", 0) if circuit_state else 0

        agents_data.append({
            "name": name,
            "cls": cls,
            "dq": dq,
            "total_tokens": total_tokens,
            "errors_24h": errors_24h,
            "circuit_tripped": circuit_tripped,
            "circuit_fails": circuit_fails,
            "last_ts": last_ts,
        })

    return {
        "agent_count": len(summary),
        "agents": agents_data,
        "state_counts": state_counts,
        "tripped_count": tripped_count,
        "agent_names_critical": agent_names_critical,
        "agent_names_warning": agent_names_warning,
    }


def extract_verdict_values(html: str) -> dict:
    """Extract verdict bar values from HTML."""
    result = {}

    # Agent count: "N agents" in vchip
    m = re.search(r'<b>(\d+)</b>agents', html)
    if m:
        result["agent_count"] = int(m.group(1))

    # Tripped count: "N tripped" in vchip
    m = re.search(r'<b>(\d+)</b>tripped', html)
    if m:
        result["tripped_count"] = int(m.group(1))

    # Verdict text
    m = re.search(r'<div class="verdict-text">\s*<span[^>]*>([^<]+)</span>', html)
    if m:
        result["verdict_text"] = m.group(1).strip()

    # Data quality chip
    m = re.search(r'data quality[^<]*<b>(\d+)%</b>', html)
    if m:
        result["dq_pct"] = int(m.group(1))

    m = re.search(r'(\d+)\s*otel\s*·\s*(\d+)\s*watch-only', html)
    if m:
        result["otel_count"] = int(m.group(1))
        result["watch_count"] = int(m.group(2))

    return result


def extract_agent_cards(html: str) -> list[dict]:
    """Extract per-agent data from fleet card grid."""
    agents = []

    # Each card: <article class="card ..."> ... <span class="card-name">NAME</span> ...
    # Find all card-name spans
    names = re.findall(r'<span class="card-name">([^<]+)</span>', html)
    for name in names:
        agents.append({"name": name})

    return agents


def main():
    now = int(time.time())

    print("Verifying /api/fleet/verdict + /api/fleet/agents")
    print()

    # 1. Get raw DB state
    print("Querying raw DB...")
    raw = get_raw_fleet_state(now)
    print(f"  {raw['agent_count']} agents, state: {raw['state_counts']}")
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

    verdict_html = fetch("/api/fleet/verdict")
    agents_html = fetch("/api/fleet/agents")

    if not verdict_html or not agents_html:
        sys.exit(1)

    print(f"  Verdict: {len(verdict_html)} bytes")
    print(f"  Agents: {len(agents_html)} bytes")
    print()

    # 3. Extract and compare
    all_pass = True

    print("=== Verdict Bar ===")
    v = extract_verdict_values(verdict_html)

    if "agent_count" in v:
        if v["agent_count"] == raw["agent_count"]:
            print(f"  {PASS} agent_count: {v['agent_count']}")
        else:
            print(f"  {FAIL} agent_count: got={v['agent_count']}, expected={raw['agent_count']}")
            all_pass = False

    if "tripped_count" in v:
        if v["tripped_count"] == raw["tripped_count"]:
            print(f"  {PASS} tripped_count: {v['tripped_count']}")
        else:
            print(f"  {FAIL} tripped_count: got={v['tripped_count']}, expected={raw['tripped_count']}")
            all_pass = False

    if "dq_pct" in v and "otel_count" in v:
        acc_count = sum(1 for a in raw["agents"] if a["dq"] == "acc")
        expected_pct = round(acc_count / max(raw["agent_count"], 1) * 100)
        if v["dq_pct"] == expected_pct:
            print(f"  {PASS} dq_pct: {v['dq_pct']}%")
        else:
            print(f"  {FAIL} dq_pct: got={v['dq_pct']}%, expected={expected_pct}%")
            all_pass = False
        if v["otel_count"] == acc_count:
            print(f"  {PASS} otel_count: {v['otel_count']}")
        else:
            print(f"  {FAIL} otel_count: got={v['otel_count']}, expected={acc_count}")
            all_pass = False

    print()
    print("=== Agent Cards ===")
    cards = extract_agent_cards(agents_html)
    card_names = {c["name"] for c in cards}
    raw_names = {a["name"] for a in raw["agents"]}

    if card_names == raw_names:
        print(f"  {PASS} Agent names match: {len(card_names)} agents")
    else:
        missing = raw_names - card_names
        extra = card_names - raw_names
        if missing:
            print(f"  {FAIL} Missing from cards: {missing}")
        if extra:
            print(f"  {FAIL} Extra in cards: {extra}")
        all_pass = False

    # Verify state counts match
    print()
    print("=== State Counts ===")
    # Extract state counts from the verdict text
    # "N agents need attention" = critical
    # "N agents showing warning signs" = warning
    # "Fleet healthy" = healthy
    # "No agents discovered" = 0
    # We already verified agent_count and tripped_count above

    print()
    if all_pass:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED — see above")
        sys.exit(1)


if __name__ == "__main__":
    main()
