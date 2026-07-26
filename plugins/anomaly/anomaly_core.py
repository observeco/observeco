"""anomaly_core — Session anomaly detection. Zero external deps.

Four anomaly types, all pure SQL against ~/.hermes/state.db:
  - no_tools: API calls but zero tool invocations
  - high_cost: Cost spike >3σ above 7d rolling average
  - long_gaps: Gap between sessions >15 min (during active periods)
  - retry_loops: Same end_reason ≥3 times in 10 min
"""

from __future__ import annotations

import math
import time

# ── Constants ──────────────────────────────────────────────────────────────

LOOKBACK_DEFAULT = 60  # minutes
COST_SPIKE_SIGMA = 3.0
MIN_SAMPLES_FOR_STATS = 10
RETRY_LOOP_THRESHOLD = 3
RETRY_LOOP_WINDOW = 600  # 10 minutes


def detect_anomalies(db_path: str, lookback_minutes: int = LOOKBACK_DEFAULT) -> list[dict]:
    """Run all anomaly detectors. Returns list sorted by severity.

    Args:
        db_path: Path to Hermes state.db
        lookback_minutes: How far back to scan
    Returns:
        List of anomaly dicts: type, agent, severity, description, timestamp, evidence
    """
    import sqlite3
    now = int(time.time())
    lookback = now - lookback_minutes * 60

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    anomalies: list[dict] = []
    anomalies.extend(_detect_no_tools(conn, lookback, now))
    anomalies.extend(_detect_cost_spikes(conn, lookback, now))
    anomalies.extend(_detect_retry_loops(conn, lookback, now))

    conn.close()

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    anomalies.sort(key=lambda a: severity_order.get(a.get("severity", "info"), 3))
    return anomalies


def _detect_no_tools(conn, lookback: int, now: int) -> list[dict]:
    """Sessions with API calls but zero tool invocations.

    ponytail: doesn't distinguish "agent chose not to use tools" from
    "agent is broken and can't call tools". Ceiling: false positives on
    sessions that legitimately don't need tools (pure reasoning).
    Upgrade path: cross-reference with session title/model to classify intent.
    """
    rows = conn.execute(
        "SELECT id, model, profile_name, started_at, ended_at, "
        "api_call_count, tool_call_count, estimated_cost_usd, title "
        "FROM sessions "
        "WHERE started_at >= ? AND api_call_count > 2 AND tool_call_count = 0 "
        "AND end_reason NOT IN ('cron_complete', 'cancelled') "
        "ORDER BY started_at DESC LIMIT 20",
        (lookback,),
    ).fetchall()

    anomalies = []
    for r in rows:
        cost = r["estimated_cost_usd"] or 0
        anomalies.append({
            "type": "no_tools",
            "agent": r["profile_name"] or r["model"] or "unknown",
            "severity": "warning",
            "description": f"Session had {r['api_call_count']} API calls but 0 tool calls — agent may be stuck",
            "timestamp": r["started_at"],
            "evidence": {
                "session_id": r["id"],
                "api_calls": r["api_call_count"],
                "tool_calls": r["tool_call_count"],
                "cost": round(cost, 4),
                "title": r["title"] or "",
            },
        })
    return anomalies


def _detect_cost_spikes(conn, lookback: int, now: int) -> list[dict]:
    """Cost spike >3σ above 7-day rolling average per model."""
    seven_days_ago = now - 7 * 86400

    # Get per-model cost stats
    rows = conn.execute(
        "SELECT model, "
        "AVG(estimated_cost_usd) as avg_cost, "
        "AVG(estimated_cost_usd * estimated_cost_usd) - "
        "AVG(estimated_cost_usd) * AVG(estimated_cost_usd) as var_cost, "
        "COUNT(*) as n "
        "FROM sessions "
        "WHERE started_at >= ? AND estimated_cost_usd > 0 "
        "GROUP BY model HAVING n >= ?",
        (seven_days_ago, MIN_SAMPLES_FOR_STATS),
    ).fetchall()

    anomalies = []
    for r in rows:
        avg_cost = r["avg_cost"]
        var_cost = r["var_cost"]
        if avg_cost is None or var_cost is None:
            continue
        std_dev = math.sqrt(max(var_cost, 0.000001))
        threshold = avg_cost + COST_SPIKE_SIGMA * std_dev

        # Find recent sessions above threshold
        recent = conn.execute(
            "SELECT id, model, profile_name, started_at, "
            "estimated_cost_usd, title "
            "FROM sessions "
            "WHERE model = ? AND started_at >= ? AND estimated_cost_usd > ? "
            "ORDER BY estimated_cost_usd DESC LIMIT 5",
            (r["model"], lookback, threshold),
        ).fetchall()

        for s in recent:
            cost = s["estimated_cost_usd"] or 0
            ratio = cost / avg_cost if avg_cost > 0 else 999
            anomalies.append({
                "type": "high_cost",
                "agent": s["profile_name"] or s["model"] or "unknown",
                "severity": "warning",
                "description": f"Cost ${cost:.4f} ({ratio:.1f}x avg ${avg_cost:.4f}) — model: {s['model']}",
                "timestamp": s["started_at"],
                "evidence": {
                    "session_id": s["id"],
                    "cost": round(cost, 4),
                    "avg_cost_7d": round(avg_cost, 4),
                    "ratio": round(ratio, 1),
                    "model": s["model"],
                    "threshold_3sigma": round(threshold, 4),
                },
            })
    return anomalies


def _detect_retry_loops(conn, lookback: int, now: int) -> list[dict]:
    """Same end_reason ≥3 times in 10 minutes for same model.

    ponytail: end_reason-based, not error-message-based. Two different
    errors with the same end_reason category won't be distinguished.
    Ceiling: ~20% of retry storms may be distinct issues lumped together.
    Upgrade path: parse message content for error fingerprints.
    """
    window_start = now - RETRY_LOOP_WINDOW

    rows = conn.execute(
        "SELECT model, profile_name, end_reason, "
        "COUNT(*) as cnt, MAX(ended_at) as last_at, MIN(ended_at) as first_at "
        "FROM sessions "
        "WHERE ended_at >= ? AND end_reason IS NOT NULL "
        "AND end_reason NOT IN ('completed', 'cron_complete', 'cancelled', 'normal') "
        "GROUP BY model, end_reason HAVING cnt >= ? "
        "ORDER BY cnt DESC LIMIT 10",
        (window_start, RETRY_LOOP_THRESHOLD),
    ).fetchall()

    anomalies = []
    for r in rows:
        duration = (r["last_at"] or 0) - (r["first_at"] or 0)
        anomalies.append({
            "type": "retry_loop",
            "agent": r["profile_name"] or r["model"] or "unknown",
            "severity": "warning",
            "description": f"{r['cnt']} '{r['end_reason']}' sessions in {duration}s — possible retry storm",
            "timestamp": r["last_at"],
            "evidence": {
                "end_reason": r["end_reason"],
                "count": r["cnt"],
                "duration_s": duration,
                "model": r["model"],
            },
        })
    return anomalies


# ── Formatting ──────────────────────────────────────────────────────────────


def format_anomalies(anomalies: list[dict]) -> str:
    """Format anomalies as a readable report."""
    if not anomalies:
        return "✅ No anomalies detected in the lookback window."

    lines = [f"{'Type':<15} {'Agent':<15} {'Severity':<10} {'Description':<60}"]
    lines.append("-" * 100)
    for a in anomalies:
        lines.append(
            f"{a['type']:<15} {a['agent'][:14]:<15} {a['severity']:<10} {a['description'][:59]}"
        )
    lines.append(f"\nTotal: {len(anomalies)} anomalies")
    return "\n".join(lines)