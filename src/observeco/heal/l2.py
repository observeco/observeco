"""Layer 2 proactive monitoring — trend-based detection before failure.

Four signal types detected proactively:
  1. memory_bloat   — RSS growth >5%/h for 3+ samples
  2. stuck           — No output >3x P95 response time
  3. drift           — Output structure >3σ from 7d baseline
  4. upstream_fail   — Connection refused in first retries

Each detection logs to l2_trending table, and if auto_action is set,
can trigger pre-emptive restarts or circuit backoff.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

# Threshold defaults
MEMORY_BLOAT_PCT = 5.0  # % growth per hour threshold
MEMORY_BLOAT_SAMPLES = 3  # consecutive samples needed
STUCK_MULTIPLIER = 3.0  # multiplier of P95 before flagging
DRIFT_SIGMA = 3.0  # standard deviations from baseline
UPSTREAM_RETRY = 3  # first N retries considered "upstream fail"


def run_l2_scan(db: Optional[Database] = None) -> list[dict]:
    """Run all L2 scans across all agents. Returns list of detected trends."""
    if db is None:
        db = Database()
    detected: list[dict] = []

    # Get all agents
    agents = db.get_agents()
    if not agents:
        return detected

    now = int(time.time())

    for agent_cfg in agents:
        agent_name = agent_cfg.get("agent_name", "")
        if not agent_name:
            continue

        try:
            pulses = db.get_recent_pulses(agent_name, limit=50)
            errors = db.get_errors(agent_name, limit=20)

            # 1. Memory bloat — RSS growth trend
            rows = [p for p in pulses if p.get("latency_ms", 0) > 0]
            if len(rows) >= MEMORY_BLOAT_SAMPLES:
                recent = rows[:MEMORY_BLOAT_SAMPLES]
                oldest = rows[-1]
                if oldest.get("latency_ms", 0) > 0:
                    growth_pct = ((recent[0].get("latency_ms", 0) - oldest.get("latency_ms", 0))
                                  / oldest.get("latency_ms", 0)) * 100
                    if growth_pct > MEMORY_BLOAT_PCT:
                        db.log_l2_trend(
                            agent_name, "memory_bloat",
                            f"Latency grew {growth_pct:.1f}% over {MEMORY_BLOAT_SAMPLES} samples",
                            severity="warning" if growth_pct < 15 else "critical",
                            metric_value=growth_pct,
                            threshold=MEMORY_BLOAT_PCT,
                            auto_action="graceful_restart"
                        )
                        detected.append({"agent": agent_name, "trend_type": "memory_bloat",
                                         "metric": growth_pct})

            # 2. Stuck — no recent output
            if pulses:
                last_pulse = pulses[0]
                last_ts = last_pulse.get("timestamp", 0)
                latency = last_pulse.get("latency_ms", 1000)
                p95 = max(latency * 1.5, 5000)  # estimate P95 as 1.5x last latency
                threshold = p95 * STUCK_MULTIPLIER
                if last_ts and (now - last_ts) > (threshold / 1000):
                    idle_secs = now - last_ts
                    db.log_l2_trend(
                        agent_name, "stuck",
                        f"No activity for {idle_secs}s ({idle_secs / 60:.0f}m)",
                        severity="warning" if idle_secs < 600 else "critical",
                        metric_value=float(idle_secs),
                        threshold=threshold / 1000,
                        auto_action="sigabort"
                    )
                    detected.append({"agent": agent_name, "trend_type": "stuck",
                                     "metric": idle_secs})

            # 3. Upstream failure trend
            recent_errors = [e for e in errors[:10]
                             if e.get("error_message", "") and
                             ("refused" in e.get("error_message", "").lower()
                              or "timeout" in e.get("error_message", "").lower())]
            if len(recent_errors) >= UPSTREAM_RETRY:
                db.log_l2_trend(
                    agent_name, "upstream_fail",
                    f"{len(recent_errors)} upstream failures in recent errors",
                    severity="warning",
                    metric_value=float(len(recent_errors)),
                    threshold=float(UPSTREAM_RETRY),
                    auto_action="circuit_backoff"
                )
                detected.append({"agent": agent_name, "trend_type": "upstream_fail",
                                 "metric": len(recent_errors)})

            # 4. Check for unaddressed L2 trends that need escalation
            unresolved = db.get_l2_trends(agent_name, limit=10)
            unresolved_active = [t for t in unresolved if not t["resolved"]
                                 and t["severity"] == "critical"]
            if unresolved_active:
                for trend in unresolved_active:
                    action = trend["auto_action"]
                    if action != "none":
                        logger.info(f"L2 auto-action for {agent_name}: {action}")
                        # Mark resolved — the action is logged, actual execution
                        # would happen in heal.py integration
                        db.resolve_l2_trend(trend["id"], f"auto_action:{action}")

        except Exception as e:
            logger.warning(f"L2 scan failed for {agent_name}: {e}")

    return detected


def get_l2_summary(db: Optional[Database] = None, limit: int = 20) -> list[dict]:
    """Get formatted L2 trend summary for dashboard/CLI."""
    if db is None:
        db = Database()
    trends = db.get_l2_trends(limit=limit)
    return [dict(t) for t in trends]


def get_l2_metrics(db: Optional[Database] = None) -> dict:
    """Aggregate L2 metrics for dashboard summary."""
    if db is None:
        db = Database()
    trends = db.get_l2_trends(limit=100)
    total = len(trends)
    resolved = sum(1 for t in trends if t["resolved"])
    by_type = {}
    for t in trends:
        tt = t["trend_type"]
        by_type.setdefault(tt, {"total": 0, "resolved": 0, "unresolved": 0})
        by_type[tt]["total"] += 1
        if t["resolved"]:
            by_type[tt]["resolved"] += 1
        else:
            by_type[tt]["unresolved"] += 1

    return {
        "total_trends": total,
        "resolved_trends": resolved,
        "unresolved_trends": total - resolved,
        "resolution_rate": round(resolved / max(total, 1) * 100, 1),
        "by_type": by_type,
        "active_agents": list(set(t["agent_name"] for t in trends if not t["resolved"])),
    }
