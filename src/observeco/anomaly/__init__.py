"""T3 Behavioral Monitoring — Anomaly Detection Engine.

Scans existing data sources (pulse_log, errors, token_logs, trace_spans)
for four anomaly types defined in §3.T3a:

- no_tools: Agent session had API calls but zero tool invocations
- high_cost: Token cost spike >3σ above 7d rolling average
- long_gaps: Gap between consecutive pulses >15 minutes
- retry_loops: Same error type for same agent >3 times in 10 minutes

(context_pressure deferred to v0.5.0 — needs model→window_size mapping)

Returns a list of anomaly dicts with: type, agent_name, severity,
description, timestamp, evidence.
"""

from __future__ import annotations

import math
import time
from typing import Optional

from observeco.db import DB_PATH, Database


def detect_anomalies(db: Optional[Database] = None, lookback_minutes: int = 60) -> list[dict]:
    """Run all anomaly detectors and return a unified list.

    Args:
        db: Database instance (creates one if not provided).
        lookback_minutes: How far back to scan (default: 60 minutes).

    Returns:
        List of anomaly dicts sorted by severity (critical > warning).
    """
    if db is None:
        db = Database(DB_PATH)
    close_on_exit = db is None

    try:
        now = int(time.time())
        lookback = now - (lookback_minutes * 60)
        anomalies: list[dict] = []

        # Each detector adds to the list
        anomalies.extend(_detect_agent_dead(db, lookback, now))
        anomalies.extend(_detect_error_bursts(db, lookback, now))
        anomalies.extend(_detect_cost_spikes(db, lookback, now))
        anomalies.extend(_detect_retry_loops(db, lookback, now))

        # Sort by severity: critical first, then warning
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        anomalies.sort(key=lambda a: severity_order.get(a.get("severity", "info"), 3))

        return anomalies
    finally:
        if close_on_exit and db is not None:
            db.close()


def _detect_agent_dead(db: Database, lookback: int, now: int) -> list[dict]:
    """Detect agents that are dead or have been dead recently.

    Filter: only flag agents that have EVER been seen alive (excludes
    never-running background services that exist in config but aren't active).

    Class-aware (obs-spec-092 §3.4):
    - profile-class agents → skip (activity-based monitoring, idle != dead)
    - test-class agents → skip (test entities excluded from monitoring)
    """
    conn = db._get_conn()

    # Get excluded classes
    excluded = set()
    for row in conn.execute(
        "SELECT agent_name FROM agent_configs WHERE class IN ('profile', 'test')"
    ).fetchall():
        excluded.add(row["agent_name"])
    if not excluded:
        excluded = set()  # ensure iterable

    # Find agents that were alive at some point but now dead
    rows = conn.execute(
        "SELECT p.agent_name, p.status, MAX(p.timestamp) as last_ts, COUNT(*) as cnt "
        "FROM pulse_log p "
        "INNER JOIN ("
        "  SELECT DISTINCT agent_name FROM pulse_log "
        "  WHERE status = 'alive' AND timestamp >= ? - 86400"
        ") a ON p.agent_name = a.agent_name "
        "WHERE p.timestamp >= ? AND p.status = 'dead' "
        "GROUP BY p.agent_name HAVING cnt >= 3 "
        "ORDER BY cnt DESC LIMIT 10",
        (lookback, lookback),
    ).fetchall()

    anomalies = []
    for agent, status, last_ts, cnt in rows:
        if agent in excluded:
            continue
        severity = "critical" if cnt >= 10 else "warning"
        anomalies.append({
            "type": "agent_dead",
            "agent_name": agent,
            "severity": severity,
            "description": f"Agent {agent} detected as dead in {cnt} pulse checks",
            "timestamp": last_ts,
            "evidence": {"dead_pulses": cnt, "last_dead_at": last_ts},
        })
    return anomalies


def _detect_error_bursts(db: Database, lookback: int, now: int) -> list[dict]:
    """Detect sudden spikes in error rates per agent."""
    conn = db._get_conn()
    # Compare error count in last 10 minutes vs previous 50 minutes
    window1_start = now - 600   # last 10 min
    window2_start = now - 3600  # last 60 min

    rows = conn.execute(
        "SELECT agent_name, "
        "SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as recent, "
        "SUM(CASE WHEN timestamp >= ? AND timestamp < ? THEN 1 ELSE 0 END) as baseline, "
        "COUNT(*) as total "
        "FROM errors WHERE timestamp >= ? "
        "GROUP BY agent_name HAVING recent >= 5 AND recent > baseline * 3 "
        "ORDER BY recent DESC LIMIT 10",
        (window1_start, window2_start, window1_start, window2_start),
    ).fetchall()

    anomalies = []
    for agent, recent, baseline, total in rows:
        anomalies.append({
            "type": "error_burst",
            "agent_name": agent,
            "severity": "critical",
            "description": f"{recent} errors in last 10min vs {baseline} in previous 50min ({total} total)",
            "timestamp": now,
            "evidence": {"recent_errors": recent, "baseline_errors": baseline, "total_errors": total},
        })
    return anomalies


def _detect_cost_spikes(db: Database, lookback: int, now: int) -> list[dict]:
    """Detect token cost spikes >3σ above 7d rolling average."""
    conn = db._get_conn()

    # Get per-agent cost stats for the last 7 days
    seven_days_ago = now - 7 * 86400
    rows = conn.execute(
        "SELECT agent_name, "
        "AVG(cost) as avg_cost, "
        "AVG(cost * cost) - AVG(cost) * AVG(cost) as var_cost, "
        "MAX(cost) as max_cost, "
        "COUNT(*) as n "
        "FROM token_logs "
        "WHERE recorded_at >= ? AND cost > 0 "
        "GROUP BY agent_name HAVING n >= 10",
        (seven_days_ago,),
    ).fetchall()

    anomalies = []
    for agent, avg_cost, var_cost, max_cost, n in rows:
        if avg_cost is None or var_cost is None:
            continue
        std_dev = math.sqrt(max(var_cost, 0.001))
        threshold_3sigma = avg_cost + 3 * std_dev

        # Check recent turns for spikes
        recent_rows = conn.execute(
            "SELECT turn_id, cost, model, recorded_at "
            "FROM token_logs WHERE agent_name=? AND recorded_at >= ? AND cost > ? "
            "ORDER BY cost DESC LIMIT 5",
            (agent, now - 3600, threshold_3sigma),
        ).fetchall()

        for turn_id, cost, model, recorded_at in recent_rows:
            ratio = cost / avg_cost if avg_cost > 0 else 999
            anomalies.append({
                "type": "high_cost",
                "agent_name": agent,
                "severity": "warning",
                "description": f"Turn cost ${cost:.4f} ({ratio:.1f}x avg ${avg_cost:.4f}) — model: {model or 'unknown'}",
                "timestamp": recorded_at,
                "evidence": {
                    "turn_cost": cost,
                    "avg_cost_7d": avg_cost,
                    "ratio": round(ratio, 1),
                    "model": model,
                    "threshold_3sigma": round(threshold_3sigma, 4),
                },
            })
    return anomalies


def _detect_retry_loops(db: Database, lookback: int, now: int) -> list[dict]:
    """Detect repeated tool failures — same error for same agent >3x in 10min.

    Class-aware: skips profile and test entities.
    """
    conn = db._get_conn()

    # Excluded classes
    excluded = set()
    for row in conn.execute(
        "SELECT agent_name FROM agent_configs WHERE class IN ('profile', 'test')"
    ).fetchall():
        excluded.add(row["agent_name"])

    ten_min_ago = now - 600

    rows = conn.execute(
        "SELECT agent_name, error_type, COUNT(*) as cnt, "
        "MAX(timestamp) as last_at, MIN(timestamp) as first_at "
        "FROM errors WHERE timestamp >= ? "
        "GROUP BY agent_name, error_type HAVING cnt >= 4 "
        "ORDER BY cnt DESC LIMIT 10",
        (ten_min_ago,),
    ).fetchall()

    anomalies = []
    for agent, error_type, cnt, last_at, first_at in rows:
        if agent in excluded:
            continue
        duration = last_at - first_at if last_at and first_at else 0
        anomalies.append({
            "type": "retry_loop",
            "agent_name": agent,
            "severity": "warning",
            "description": f"{cnt} '{error_type}' errors in {duration}s — possible retry storm",
            "timestamp": last_at,
            "evidence": {"error_type": error_type, "count": cnt, "duration_s": duration},
        })
    return anomalies
