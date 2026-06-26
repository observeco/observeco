"""Layer 2 proactive monitoring — trend-based detection before failure.

Three signal types detected proactively:
  1. latency_growth — Latency growth >5%/h for 3+ samples
  2. stuck           — No output >3x P95 response time
  3. upstream_fail   — Connection refused in first retries

(Component-level drift is tracked separately in chisel/drift.py.)

Each detection logs to l2_trending table. When auto_heal_l2 is enabled
in heal_config, auto-actions execute via the heal engine (restart/cooldown).
When disabled, trends are logged but not resolved — resolution_rate reflects
only actually-executed actions.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from observeco.db import Database
from observeco.tracking.baselines import load_cached_baselines

logger = logging.getLogger(__name__)

# Threshold defaults
LATENCY_GROWTH_PCT = 5.0  # % growth per hour threshold
LATENCY_GROWTH_SAMPLES = 3  # consecutive samples needed
STUCK_MULTIPLIER = 3.0  # multiplier of P95 before flagging
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

            # 1. Latency growth trend
            rows = [p for p in pulses if p.get("latency_ms", 0) > 0]
            if len(rows) >= LATENCY_GROWTH_SAMPLES:
                recent = rows[:LATENCY_GROWTH_SAMPLES]
                oldest = rows[-1]
                if oldest.get("latency_ms", 0) > 0:
                    growth_pct = ((recent[0].get("latency_ms", 0) - oldest.get("latency_ms", 0))
                                  / oldest.get("latency_ms", 0)) * 100
                    if growth_pct > LATENCY_GROWTH_PCT:
                        db.log_l2_trend(
                            agent_name, "latency_growth",
                            f"Latency grew {growth_pct:.1f}% over {LATENCY_GROWTH_SAMPLES} samples",
                            severity="warning" if growth_pct < 15 else "critical",
                            metric_value=growth_pct,
                            threshold=LATENCY_GROWTH_PCT,
                            auto_action="graceful_restart"
                        )
                        detected.append({"agent": agent_name, "trend_type": "latency_growth",
                                         "metric": growth_pct})

            # 2. Stuck — no recent output
            if pulses:
                last_pulse = pulses[0]
                last_ts = last_pulse.get("timestamp", 0)
                latency = last_pulse.get("latency_ms", 1000)
                # Use cached baseline P95 if available, otherwise estimate
                baselines = load_cached_baselines()
                agent_baseline = baselines.get(agent_name, {})
                p95 = agent_baseline.get("p95_latency_ms", 0) or max(latency * 1.5, 5000)
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

            # 4. Execute L2 auto-actions (gated by heal_config.auto_heal_l2)
            unresolved = db.get_l2_trends(agent_name, limit=10)
            unresolved_active = [t for t in unresolved if not t["resolved"]
                                 and t["severity"] == "critical"]
            if unresolved_active:
                heal_configs = db.get_heal_config(agent_name)
                cfg = heal_configs[0] if heal_configs else {}
                l2_enabled = cfg.get("auto_heal_l2", 0) == 1
                for trend in unresolved_active:
                    action = trend["auto_action"]
                    if action == "none":
                        continue
                    if l2_enabled:
                        # Map L2 auto_action to heal _execute_action action names
                        action_map = {
                            "graceful_restart": "restart",
                            "sigabort": "restart",
                            "circuit_backoff": "cooldown",
                        }
                        heal_action = action_map.get(action, action) or action
                        from observeco.heal import _execute_action
                        success, msg = _execute_action(heal_action, {"agent_name": agent_name})
                        if success:
                            logger.info(f"L2 auto-action for {agent_name}: {action} — {msg}")
                            db.resolve_l2_trend(trend["id"], f"auto_action:{action}")
                        else:
                            logger.warning(f"L2 auto-action FAILED for {agent_name}: {action} — {msg}")
                    else:
                        # L2 auto-heal disabled — log but don't resolve
                        logger.info(f"L2 trend for {agent_name}: {action} (auto-heal disabled, would {action})")

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
