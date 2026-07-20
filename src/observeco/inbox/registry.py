"""Detector Registry — maps 9 source tables to normalized inbox items.

Each adapter: reads from one source table, returns normalized dicts.
Read-side only — detectors keep their own tables. No detector rewrites.

Obs-Spec ref: obs-spec-092 §3.2
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from observeco.db import Database
from observeco.inbox.store import InboxStore, _now_iso, _make_id, fmt_why_source

logger = logging.getLogger(__name__)

# ── Tone constants ──────────────────────────────────────────────────

TONE_ALERT = "alert"
TONE_WATCH = "watch"
TONE_INSIGHT = "insight"

# ── Pillar constants ────────────────────────────────────────────────

PILLAR_QUALITY = "quality"
PILLAR_RELIABILITY = "reliability"
PILLAR_USAGE = "usage"
PILLAR_MEMORY = "memory"


class AdapterContext:
    """Shared context for all adapters — DB, store, and helpers."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.store = InboxStore(self.db)
        self.now_iso = _now_iso()
        self.now_ts = int(time.time())
        # Class-aware exclusion set (obs-spec-092 §3.4)
        self._excluded: set[str] | None = None

    def get_excluded_agents(self) -> set[str]:
        """Returns set of agent names excluded from monitoring (profile, test)."""
        if self._excluded is None:
            self._excluded = set()
            try:
                conn = self.db._get_conn()
                for row in conn.execute(
                    "SELECT agent_name FROM agent_configs WHERE class IN ('profile', 'test')"
                ).fetchall():
                    self._excluded.add(row["agent_name"])
            except Exception:
                pass
        return self._excluded


# ── Adapter 1: L2 Trending ─────────────────────────────────────────

def run_l2_adapter(ctx: AdapterContext) -> list[dict]:
    """Read l2_trending → stuck→alert, stuck·warning→watch, upstream_fail→watch."""
    conn = ctx.db._get_conn()
    items = []
    rows = conn.execute(
        "SELECT * FROM l2_trending WHERE resolved = 0 "
        "ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    rows = [dict(r) for r in rows]
    excluded = ctx.get_excluded_agents()
    for r in rows:
        agent = r["agent_name"]
        if agent in excluded:
            continue
        trend_type = r["trend_type"]
        severity = r["severity"]
        metric = r.get("metric_value", 0) or 0
        threshold = r.get("threshold", 0) or 0
        signal_label = r.get("signal_label", "") or ""

        if trend_type == "stuck" and severity == "critical":
            tone = TONE_ALERT
            pillar = PILLAR_RELIABILITY
            title = f"{agent} — no activity for {int(metric)}s. Process alive but unresponsive."
            attribution = f"L2 trending flagged it critical at {int(metric)}s of silence."
            actions = [
                {"label": "Open agent →", "href": f"/api/agent-detail/{agent}", "kind": "primary"},
                {"label": "Restart", "cmd": f"restart {agent}", "kind": "warn"},
            ]
        elif trend_type == "stuck":
            tone = TONE_WATCH
            pillar = PILLAR_RELIABILITY
            title = f"{agent} — stuck for {int(metric)}s (warning threshold crossed)."
            attribution = "L2 trending: stuck·warning — early signal before critical."
            actions = [{"label": "Open agent →", "href": f"/api/agent-detail/{agent}", "kind": "primary"}]
        elif trend_type == "upstream_fail":
            tone = TONE_WATCH
            pillar = PILLAR_RELIABILITY
            title = f"{agent} — {int(metric)} upstream failures in recent errors."
            attribution = "Upstream = the provider/gateway, not your agent's logic."
            actions = [
                {"label": "Open errors →", "href": f"/api/errors?agent={agent}", "kind": "primary"},
            ]
        else:
            continue  # don't emit unknown L2 signals

        items.append({
            "class": trend_type,
            "agent_name": agent,
            "dedupe_key": f"{trend_type}::{r.get('timestamp', 0)}",
            "tone": tone,
            "pillar": pillar,
            "title": title,
            "attribution": attribution,
            "evidence": {"metrics": {"value": metric, "threshold": threshold, "signal": signal_label},
                         "source_table": "l2_trending", "detector": "heal/l2.py"},
            "actions": actions,
            "why_source": fmt_why_source("l2_trending", "heal/l2.py run_l2_scan()"),
        })
    return items


# ── Adapter 2: Drift Detection ──────────────────────────────────────

def run_drift_adapter(ctx: AdapterContext) -> list[dict]:
    """Read chisel_drift → 7d Δ >20%→watch; >50%→alert."""
    conn = ctx.db._get_conn()
    items = []
    rows = conn.execute(
        "SELECT * FROM chisel_drift WHERE breached = 1 "
        "ORDER BY delta_pct DESC LIMIT 50"
    ).fetchall()
    excluded = ctx.get_excluded_agents()
    for r in rows:
        agent = r["agent_name"]
        if agent in excluded:
            continue
        component = r["component"]
        delta = abs(r["delta_pct"])
        breach_count = conn.execute(
            "SELECT COUNT(*) as c FROM drift_events WHERE agent_name = ?",
            (agent,),
        ).fetchone()
        breach_count = breach_count["c"] if breach_count else 0
        peak = conn.execute(
            "SELECT MAX(drift_pct) as mx FROM drift_events WHERE agent_name = ?",
            (agent,),
        ).fetchone()
        peak_val = abs(peak["mx"]) if peak and peak["mx"] else delta

        tone = TONE_ALERT if delta > 50 else TONE_WATCH
        pillar = PILLAR_MEMORY if "memory" in component.lower() else PILLAR_USAGE

        title = f"{agent} — {component} grew {delta:+.1f}% in 7 days ({breach_count} breaches)."
        attribution = f"drift_events shows sustained climb — accumulation pattern."
        actions = [
            {"label": "Open drift detail →", "href": f"/api/drift/{agent}", "kind": "primary"},
        ]

        items.append({
            "class": "drift_breach",
            "agent_name": agent,
            "dedupe_key": f"drift::{component}",
            "tone": tone,
            "pillar": pillar,
            "title": title,
            "attribution": attribution,
            "evidence": {"metrics": {"delta_pct": delta, "breaches": breach_count, "peak_pct": peak_val},
                         "source_table": "chisel_drift", "detector": "chisel/drift.py"},
            "actions": actions,
            "why_source": fmt_why_source("chisel_drift, drift_events", "chisel/drift.py (7-day rolling)"),
        })
    return items


# ── Adapter 3: Canary Regression ────────────────────────────────────

def run_canary_adapter(ctx: AdapterContext) -> list[dict]:
    """Read canary_runs → pass-rate step-change → alert."""
    conn = ctx.db._get_conn()
    items = []
    # Get agents with at least 2 completed runs
    agents = conn.execute(
        "SELECT DISTINCT agent_name FROM canary_runs WHERE status = 'completed' "
        "AND pass_count IS NOT NULL ORDER BY agent_name"
    ).fetchall()
    excluded = ctx.get_excluded_agents()

    for a in agents:
        agent = a["agent_name"]
        if agent in excluded:
            continue
        runs = conn.execute(
            "SELECT started_at, pass_count, fail_count, total_tasks "
            "FROM canary_runs WHERE agent_name = ? AND status = 'completed' "
            "AND pass_count IS NOT NULL ORDER BY started_at DESC LIMIT 4",
            (agent,),
        ).fetchall()
        if len(runs) < 2:
            continue

        latest = runs[0]
        prev = runs[1]
        latest_total = (latest["pass_count"] or 0) + (latest["fail_count"] or 0)
        prev_total = (prev["pass_count"] or 0) + (prev["fail_count"] or 0)

        if latest_total == 0:
            continue

        latest_rate = (latest["pass_count"] or 0) / latest_total
        prev_rate = (prev["pass_count"] or 0) / prev_total if prev_total > 0 else 1.0

        # Step-change: was ≥60%, now ≤10%, or two consecutive all-fail
        two_all_fail = (
            latest["pass_count"] == 0 and latest_total > 0
            and prev["pass_count"] == 0 and prev_total > 0
        )
        step_change = prev_rate >= 0.6 and latest_rate <= 0.1

        if not (two_all_fail or step_change):
            continue

        tone = TONE_ALERT
        pillar = PILLAR_QUALITY
        title = f"{agent} — canary went {latest['pass_count']}/{latest_total} on {latest['started_at'][:10]} run."
        attribution = f"Two consecutive all-fail runs" if two_all_fail else \
            f"Step change: {prev_rate:.0%} → {latest_rate:.0%} pass rate."

        actions = [
            {"label": "View judge reasoning →", "href": f"/api/canary-card/{agent}", "kind": "primary"},
            {"label": "Open canary detail →", "href": f"/api/fleet/canary-card/{agent}", "kind": "primary"},
        ]

        items.append({
            "class": "canary_regress",
            "agent_name": agent,
            "dedupe_key": f"canary::{agent}",
            "tone": tone,
            "pillar": pillar,
            "title": title,
            "attribution": attribution,
            "evidence": {"metrics": {"latest_pass": latest["pass_count"],
                                     "latest_total": latest_total,
                                     "prev_pass": prev["pass_count"],
                                     "prev_total": prev_total,
                                     "latest_run": latest["started_at"]},
                         "source_table": "canary_runs", "detector": "capability/canary.py"},
            "actions": actions,
            "why_source": fmt_why_source("canary_runs, canary_results, canary_judge_cache",
                                         "capability/canary.py"),
        })
    return items


# ── Adapter 4: Circuit Breakers ─────────────────────────────────────

def run_circuit_adapter(ctx: AdapterContext) -> list[dict]:
    """Read circuit_breakers → tripped <7d→watch; >7d→auto-triage."""
    conn = ctx.db._get_conn()
    items = []
    rows = conn.execute(
        "SELECT * FROM circuit_breakers WHERE tripped = 1 "
        "ORDER BY failure_count DESC LIMIT 50"
    ).fetchall()
    excluded = ctx.get_excluded_agents()
    for r in rows:
        agent = r["agent_name"]
        if agent in excluded:
            continue
        failures = r["failure_count"]
        cooldown = r.get("cooldown_until", 0)
        days_tripped = (ctx.now_ts - cooldown) / 86400 if cooldown else 0

        if days_tripped > 7:
            # Stale circuit >7d → auto-triage
            items.append({
                "class": "circuit_event",
                "agent_name": agent,
                "dedupe_key": f"circuit_stale::{agent}",
                "tone": TONE_WATCH,
                "pillar": PILLAR_RELIABILITY,
                "title": f"{agent} — circuit tripped ({failures:,} failures, >7d). Stale — needs reset.",
                "attribution": f"Circuit tripped {days_tripped:.0f} days ago with no recovery attempt.",
                "evidence": {"metrics": {"failure_count": failures, "days_tripped": round(days_tripped, 1)},
                             "source_table": "circuit_breakers", "detector": "inbox/circuit_adapter"},
                "actions": [
                    {"label": "Reset circuit", "cmd": f"reset_circuit {agent}", "kind": "warn"},
                    {"label": "Open agent →", "href": f"/api/agent-detail/{agent}?tab=guard", "kind": "neutral"},
                ],
                "why_source": fmt_why_source("circuit_breakers", "inbox/circuit_adapter (staleness check)"),
                "auto_triage": "stale circuit — tripped >7d with no recovery attempt",
            })
        else:
            # Active circuit <7d → watch
            items.append({
                "class": "circuit_event",
                "agent_name": agent,
                "dedupe_key": f"circuit_active::{agent}",
                "tone": TONE_WATCH,
                "pillar": PILLAR_RELIABILITY,
                "title": f"{agent} — circuit tripped ({failures:,} failures). Active incident.",
                "attribution": f"Tripped {days_tripped:.1f}d ago · {failures} failures accumulated.",
                "evidence": {"metrics": {"failure_count": failures, "days_tripped": round(days_tripped, 1)},
                             "source_table": "circuit_breakers", "detector": "heal/circuit.py"},
                "actions": [
                    {"label": "Open guard →", "href": f"/api/agent-detail/{agent}?tab=guard", "kind": "primary"},
                    {"label": "Reset circuit", "cmd": f"reset_circuit {agent}", "kind": "neutral"},
                ],
                "why_source": fmt_why_source("circuit_breakers", "heal/circuit.py"),
            })
    return items


# ── Adapter 5: Anomaly Module ───────────────────────────────────────

def run_anomaly_adapter(ctx: AdapterContext) -> list[dict]:
    """Read anomaly/ output → dead/retry_loop items subject to class rules."""
    from observeco.anomaly import detect_anomalies
    # Filter out profile-class agents (they get activity-based monitoring)
    conn = ctx.db._get_conn()
    profile_agents = {r["agent_name"] for r in conn.execute(
        "SELECT agent_name FROM agent_configs WHERE class = 'profile'"
    ).fetchall()}
    test_agents = {r["agent_name"] for r in conn.execute(
        "SELECT agent_name FROM agent_configs WHERE class = 'test'"
    ).fetchall()}

    anomalies = detect_anomalies(ctx.db, lookback_minutes=60)
    items = []
    for a in anomalies:
        agent = a.get("agent_name", "")
        if agent in profile_agents or agent in test_agents:
            continue  # skip profile/test entities

        atype = a.get("type", "unknown")
        severity = a.get("severity", "info")
        description = a.get("description", "")
        evidence = a.get("evidence", {})

        tone = TONE_ALERT if severity == "critical" else TONE_WATCH
        pillar = PILLAR_RELIABILITY if atype in ("agent_dead", "retry_loop") else PILLAR_USAGE

        items.append({
            "class": atype,
            "agent_name": agent,
            "dedupe_key": f"{atype}::{a.get('timestamp', 0)}",
            "tone": tone,
            "pillar": pillar,
            "title": f"{agent} — {description}",
            "attribution": None,
            "evidence": {"metrics": evidence,
                         "source_table": "anomaly_detect", "detector": "anomaly/__init__.py"},
            "actions": [
                {"label": "Open agent →", "href": f"/api/agent-detail/{agent}", "kind": "primary"},
            ],
            "why_source": fmt_why_source("pulse_log, errors, token_logs",
                                         "anomaly/__init__.py detect_anomalies()"),
        })
    return items


# ── Adapter 6: Spend Anomaly ────────────────────────────────────────

def run_spend_adapter(ctx: AdapterContext) -> list[dict]:
    """Read token_logs → >3σ daily spend or >70% fleet concentration → insight."""
    conn = ctx.db._get_conn()
    items = []

    # Fleet concentration: find agent with highest spend share
    seven_days_ago = ctx.now_ts - 7 * 86400
    total_spend = conn.execute(
        "SELECT COALESCE(SUM(cost), 0) as total FROM token_logs "
        "WHERE recorded_at >= ? AND cost > 0",
        (seven_days_ago,),
    ).fetchone()
    total = total_spend["total"] if total_spend else 0
    if total == 0:
        return items

    # Agent concentration
    top_agents = conn.execute(
        "SELECT agent_name, COALESCE(SUM(cost), 0) as spend, "
        "COALESCE(SUM(total_tokens), 0) as tokens, COUNT(DISTINCT turn_id) as calls "
        "FROM token_logs WHERE recorded_at >= ? AND cost > 0 "
        "GROUP BY agent_name ORDER BY spend DESC LIMIT 5",
        (seven_days_ago,),
    ).fetchall()

    for r in top_agents:
        pct = r["spend"] / total * 100
        if pct > 70:
            items.append({
                "class": "spend_anomaly",
                "agent_name": r["agent_name"],
                "dedupe_key": "spend_concentration",
                "tone": TONE_INSIGHT,
                "pillar": PILLAR_USAGE,
                "title": f"{r['agent_name']} is {pct:.0f}% of ${total:.0f} fleet spend ({r['calls']:,} calls).",
                "attribution": f"One agent's system prompt drives your entire token bill.",
                "evidence": {"metrics": {"spend_pct": round(pct, 1),
                                         "total_spend": round(total, 2),
                                         "agent_spend": round(r["spend"], 2),
                                         "agent_calls": r["calls"]},
                             "source_table": "token_logs", "detector": "inbox/spend_adapter"},
                "actions": [
                    {"label": "Open token analytics →", "href": "/api/token-analytics", "kind": "primary"},
                    {"label": "Preview compression →", "href": f"/api/brain/{r['agent_name']}?mode=preview",
                     "kind": "primary"},
                ],
                "why_source": fmt_why_source("token_logs, token_pricing",
                                             "inbox/spend_adapter (token_logs rollup)"),
            })
    return items


# ── Adapter 7: Data Quality Gap ─────────────────────────────────────

def run_dq_adapter(ctx: AdapterContext) -> list[dict]:
    """Read token_logs.source → Tier-1 coverage <50% → insight (one standing item)."""
    conn = ctx.db._get_conn()
    total_agents = conn.execute(
        "SELECT COUNT(*) as c FROM agent_configs WHERE is_active = 1"
    ).fetchone()
    total = total_agents["c"] if total_agents else 0
    if total == 0:
        return []

    # Agents with otel source data in last 24h
    otel_agents = conn.execute(
        "SELECT COUNT(DISTINCT agent_name) as c FROM token_logs "
        "WHERE source = 'otel' AND recorded_at >= ?",
        (ctx.now_ts - 86400,),
    ).fetchone()
    tier1 = otel_agents["c"] if otel_agents else 0
    pct = round(tier1 / total * 100)

    if pct >= 50:
        return []  # no gap

    return [{
        "class": "dq_gap",
        "agent_name": None,  # fleet-wide
        "dedupe_key": "dq_otel_coverage",
        "tone": TONE_INSIGHT,
        "pillar": PILLAR_QUALITY,
        "title": f"{pct}% OTEL coverage — {total - tier1} of {total} agents are watch-only.",
        "attribution": "Every token number on this dashboard is currently an estimate (±80%).",
        "evidence": {"metrics": {"otel_pct": pct, "tier1": tier1, "total_agents": total},
                     "source_table": "token_logs.source", "detector": "DPA §2-D tiering"},
        "actions": [
            {"label": "Install telemetry plugin →", "cmd": "observeco setup telemetry", "kind": "primary"},
        ],
        "why_source": fmt_why_source("token_logs.source distribution", "DPA §2-D tiering"),
    }]


# ── Adapter 8: Garden Staleness ─────────────────────────────────────

def run_garden_adapter(ctx: AdapterContext) -> list[dict]:
    """Read clawforge_garden freshness → stale source insight (cadence×3)."""
    conn = ctx.db._get_conn()
    items = []

    # Get latest garden scan per agent
    agents = conn.execute(
        "SELECT DISTINCT agent_name FROM clawforge_garden"
    ).fetchall()
    for a in agents:
        agent = a["agent_name"]
        latest = conn.execute(
            "SELECT MAX(timestamp) as last_scan FROM clawforge_garden WHERE agent_name = ?",
            (agent,),
        ).fetchone()
        if not latest or not latest["last_scan"]:
            continue
        last_scan = latest["last_scan"]
        days_since = (ctx.now_ts - last_scan) / 86400

        if days_since >= 3:  # cadence × 3 (daily cadence assumed)
            items.append({
                "class": "stale_source",
                "agent_name": agent,
                "dedupe_key": f"garden_stale::{agent}",
                "tone": TONE_INSIGHT,
                "pillar": PILLAR_MEMORY,
                "title": f"{agent} — memory garden last scanned {days_since:.0f} days ago.",
                "attribution": "Garden scanner may not be running — debt scores running on stale data.",
                "evidence": {"metrics": {"days_since_scan": round(days_since, 1),
                                         "last_scan_ts": last_scan},
                             "source_table": "clawforge_garden", "detector": "inbox/staleness check"},
                "actions": [
                    {"label": "Run garden scan →", "cmd": f"garden scan {agent}", "kind": "primary"},
                ],
                "why_source": fmt_why_source("clawforge_garden freshness",
                                             "inbox/garden_adapter (staleness check)"),
            })

    # Also check fleet-wide: if no garden rows at all, raise fleet-wide stale
    count = conn.execute(
        "SELECT COUNT(*) as c FROM clawforge_garden WHERE timestamp >= ?",
        (ctx.now_ts - 3 * 86400,),
    ).fetchone()
    if count and count["c"] == 0:
        items.append({
            "class": "stale_source",
            "agent_name": None,
            "dedupe_key": "garden_fleet_stale",
            "tone": TONE_INSIGHT,
            "pillar": PILLAR_MEMORY,
            "title": "Memory garden hasn't scanned anything in 3+ days — scanner may be down.",
            "attribution": "No garden data means no memory debt, no contradiction detection, no compression advice.",
            "evidence": {"metrics": {"days_no_scan": 3},
                         "source_table": "clawforge_garden", "detector": "inbox/staleness check"},
            "actions": [
                {"label": "Verify garden service", "cmd": "observeco status garden", "kind": "neutral"},
            ],
            "why_source": fmt_why_source("clawforge_garden freshness",
                                         "inbox/garden_adapter (fleet-wide staleness check)"),
        })
    return items


# ── Adapter 9: Config Snapshots ─────────────────────────────────────

def run_config_adapter(ctx: AdapterContext) -> list[dict]:
    """Read config_snapshots — never emits items, only attribution joins."""
    return []


# ── Master runner ───────────────────────────────────────────────────

ADAPTERS = {
    "l2": run_l2_adapter,
    "drift": run_drift_adapter,
    "canary": run_canary_adapter,
    "circuit": run_circuit_adapter,
    "anomaly": run_anomaly_adapter,
    "spend": run_spend_adapter,
    "dq": run_dq_adapter,
    "garden": run_garden_adapter,
    "config": run_config_adapter,
}


def run_all_adapters(ctx: AdapterContext | None = None) -> list[dict]:
    """Run all detector adapters and return normalized item dicts.

    Items are NOT persisted here — call store.upsert() separately
    or use build_and_store().
    """
    if ctx is None:
        ctx = AdapterContext()
    all_items: list[dict] = []
    for name, adapter in ADAPTERS.items():
        try:
            items = adapter(ctx)
            all_items.extend(items)
        except Exception:
            logger.exception("Adapter %s failed", name)
    return all_items


def build_and_store(ctx: AdapterContext | None = None) -> int:
    """Run all adapters, upsert results into inbox_items. Returns count."""
    if ctx is None:
        ctx = AdapterContext()
    items = run_all_adapters(ctx)
    count = 0
    for item in items:
        auto_triage = item.pop("auto_triage", None)
        item_id = ctx.store.upsert(
            item_class=item["class"],
            agent_name=item["agent_name"],
            dedupe_key=item["dedupe_key"],
            tone=item["tone"],
            title=item["title"],
            evidence=item["evidence"],
            actions=item["actions"],
            why_source=item["why_source"],
            pillar=item.get("pillar"),
            attribution=item.get("attribution"),
            now_iso=ctx.now_iso,
        )
        if auto_triage:
            ctx.store.auto_triage(item_id, auto_triage)
        count += 1
    return count
