"""agent_profile_service.py — Four-Pillar Agent Profile (§3.1–§3.6).

Provides get_agent_profile() returning the composite payload for
GET /api/agent/<name>/profile. Each pillar is an independent failure mode.

Design authority: mockups/agent-profile-v4.html (operator layer)
                  mockups/agent-profile-v2.html (technical tab internals)

Raw DB queries delegated to T4 service (src/observeco/agent_profile_service.py)
for reliability, usage, and memory pillars. Only quality-pillar canary queries
remain here because T4 does not expose canary data. The drawer reliability
function keeps one targeted errors query for guard-event filtering (T4 exposes
only the error count, not raw error rows).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

# In-memory cache: {agent_name: (timestamp, payload)}
_profile_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 5.0

# Inner cache: carries T4-aggregated data from _build_profile into the
# individual assembly/drawer functions WITHOUT changing their signatures.
# Populated at the start of _build_profile, cleared after assembly.
_t4_cache: dict[str, dict] = {}


# ── Helpers ────────────────────────────────────────────────────────────


def _fmt_relative(ts: int) -> str:
    """Human relative timestamp, no 'ago ago' duplication (fixes §3.6 #2)."""
    now = int(time.time())
    delta = now - ts
    if delta < 0:
        return "just now"
    if delta < 60:
        return f"{delta}s ago"
    elif delta < 3600:
        return f"{delta // 60}m ago"
    elif delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def _fmt_human_number(val: float | int) -> str:
    """Human numbers: 34.0s, 41s, 2.2K (§3.6 #1)."""
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    if val == int(val):
        return str(int(val))
    return f"{val:.1f}"


def _fmt_latency(ms: float) -> str:
    """Format latency per design: >=10s -> '34.0s', <10s -> '340ms'."""
    if ms >= 10_000:
        return f"{ms / 1000:.1f}s"
    return f"{int(ms)}ms"


def _fmt_drift_pct(pct: float) -> str:
    """Format drift percentage per language rules: +408% -> 'grew 4x'."""
    return f"{pct:+.1f}%"


def _fmt_token_breakdown(total: int, components: dict) -> str:
    """Short token composition description for Usage sub text."""
    if not total:
        return "no token data"
    top = max(components, key=lambda k: components.get(k, 0))
    top_pct = round(components.get(top, 0) / total * 100) if total else 0
    return f"mostly its {top.replace('_', ' ')}" if top_pct > 50 else "distributed across components"


def _days_since(ts: int) -> int:
    return max(0, (int(time.time()) - ts) // 86400)


# ── Pillar Assembly ────────────────────────────────────────────────────
#
# Each assembly function keeps its original (agent_name, db, now, conn)
# signature for backward compatibility with callers. DB queries for
# reliability, usage, and memory are delegated to the T4 service via
# _t4_cache, populated by _build_profile before assembly runs.


def _assemble_quality(agent_name: str, db: Database, now: int, conn) -> dict:
    """Quality pillar: 'Is the work good?' <-- canary_runs.

    Raw query retained here: T4 service does not expose canary data.
    """
    run = conn.execute(
        "SELECT id, pass_count, fail_count, hang_count, total_tasks, "
        "started_at, total_cost, total_tokens FROM canary_runs "
        "WHERE agent_name=? AND status='completed' AND pass_count IS NOT NULL "
        "ORDER BY started_at DESC LIMIT 1",
        (agent_name,),
    ).fetchone()

    running = conn.execute(
        "SELECT 1 FROM canary_runs WHERE agent_name=? AND status='running' LIMIT 1",
        (agent_name,),
    ).fetchone()

    if running:
        return {
            "key": "quality",
            "label": "Quality",
            "value": "check running\u2026",
            "sub": "benchmark in progress",
            "state": "unknown",
            "modifier": None,
            "sources": ["canary_runs"],
        }

    if not run:
        return {
            "key": "quality",
            "label": "Quality",
            "value": "No checks yet",
            "sub": 'No quality checks yet \u2014 set one up \u2192',
            "state": "unset",
            "modifier": None,
            "sources": ["canary_runs"],
        }

    run = dict(run)
    total = (run["pass_count"] or 0) + (run["fail_count"] or 0)
    passed = run["pass_count"] or 0
    failed = run["fail_count"] or 0
    hung = run["hang_count"] or 0
    tasks = run["total_tasks"] or total

    state = "ok"
    if failed > 0 or hung > 0:
        state = "attention"
    elif passed == 0 and total == 0:
        state = "unknown"

    value = f"{passed} of {tasks}"

    parts = []
    if passed == tasks:
        parts.append("all tasks passed in the last check")
    elif failed > 0 and hung == 0:
        parts.append("test tasks passed in the last check")
    elif failed > 0 and hung > 0:
        parts.append(f"test tasks passed ({hung} hung)")
    else:
        parts.append("test tasks passed on last check")

    return {
        "key": "quality",
        "label": "Quality",
        "value": value,
        "sub": parts[0],
        "state": state,
        "modifier": None,
        "sources": ["canary_runs"],
        "_raw": {
            "run_id": run["id"],
            "passed": passed,
            "failed": failed,
            "hung": hung,
            "total_tasks": tasks,
            "started_at": run.get("started_at", ""),
            "total_cost": run.get("total_cost", 0),
            "total_tokens": run.get("total_tokens", 0),
        },
    }


def _assemble_reliability(agent_name: str, db: Database, now: int, conn) -> dict:
    """Reliability pillar: 'Is it up?' <-- delegated to T4 health data."""
    t4 = _t4_cache.get(agent_name, {})
    t4_health = t4.get("health", {})
    pulses = t4_health.get("pulse_history_24h", [])
    errors_24h = t4_health.get("error_count_24h", 0)
    circuit = t4_health.get("circuit_breaker") or {}

    if not pulses:
        return {
            "key": "reliability",
            "label": "Reliability",
            "value": "Unknown",
            "sub": "No health data yet",
            "state": "unknown",
            "modifier": None,
            "sources": ["pulse_log", "guard", "errors", "l2_trending"],
        }

    last_pulse = pulses[0]
    last_ts = last_pulse.get("timestamp", 0)
    status = last_pulse.get("status", "")
    delta = now - last_ts if last_ts else 999999
    tripped = circuit.get("tripped", False)

    state = "ok"
    value = "100%"
    sub = "health checks passing, all day"

    if delta > 14400 or status == "dead":
        state = "attention"
        value = "Down"
        sub = "unreachable \u2014 needs investigation"
    elif tripped:
        state = "attention"
        value = "Stopped"
        sub = "guard tripped after repeated failures"
    elif status == "error":
        state = "attention"
        value = "Degraded"
        sub = "recent checks failing"
    else:
        alive_count = sum(1 for p in pulses[:24] if p.get("status") == "alive")
        passing_pct = round(alive_count / min(len(pulses), 24) * 100) if pulses else 100
        value = f"{passing_pct}%"
        if passing_pct == 100:
            sub = "health checks passing, all day"
        elif passing_pct >= 80:
            sub = f"{passing_pct}% checks passing in last 24h"
            state = "ok"
        else:
            sub = f"only {passing_pct}% checks passing"
            state = "attention"

    return {
        "key": "reliability",
        "label": "Reliability",
        "value": value,
        "sub": sub,
        "state": state,
        "modifier": None,
        "sources": ["pulse_log", "guard", "errors", "l2_trending"],
        "_raw": {
            "last_status": status,
            "last_ts": last_ts,
            "latency_ms": last_pulse.get("latency_ms", 0),
            "errors_24h": errors_24h,
            "circuit_tripped": tripped,
            "circuit_failures": circuit.get("failure_count", 0),
        },
    }


def _assemble_usage(agent_name: str, db: Database, now: int, conn) -> dict:
    """Usage pillar: 'What's it costing?' <-- delegated to T4 tokens data."""
    t4 = _t4_cache.get(agent_name, {})
    t4_tokens = t4.get("tokens", {})
    breakdown = t4_tokens.get("latest_breakdown", {})
    drift = t4_tokens.get("drift_trends", [])
    token_summary = t4_tokens.get("token_summary", {})

    if not breakdown and not token_summary:
        return {
            "key": "usage",
            "label": "Usage today",
            "value": "N/A",
            "sub": "no usage data collected",
            "state": "unset",
            "modifier": None,
            "sources": ["token_logs", "chisel_drift"],
        }

    identity = breakdown.get("identity", 0) or 0
    skills = breakdown.get("skills", 0) or 0
    memory_t = breakdown.get("memory", 0) or 0
    tools = breakdown.get("tools", 0) or 0
    guidance = breakdown.get("guidance", 0) or 0
    total = identity + skills + memory_t + tools + guidance
    if total == 0:
        total = breakdown.get("total", 0) or 0

    # Find guidance drift as modifier
    guidance_drift = next(
        (d for d in drift if d.get("component", "").lower() == "guidance"),
        None,
    )
    if not guidance_drift:
        guidance_drift = next(
            (d for d in drift if d.get("delta_pct") and abs(d["delta_pct"]) > 5),
            None,
        )

    modifier = None
    if guidance_drift:
        dp = guidance_drift.get("delta_pct", 0)
        if abs(dp) > 10:
            fold = abs(round(dp / 100))
            mod = f"\u2197 grew {fold}\u00d7 this week" if fold >= 2 else f"\u2197 grew {abs(dp):.0f}% this week"
            modifier = mod

    daily_tokens = token_summary.get("total_tokens", 0) if token_summary else total
    total_cost = token_summary.get("total_cost", 0) if token_summary else 0
    if daily_tokens == 0:
        daily_tokens = total

    value = _fmt_human_number(daily_tokens) if daily_tokens > 0 else (_fmt_human_number(total) if total else "\u2014")

    components = {
        "guidance": guidance,
        "identity": identity,
        "skills": skills,
        "memory": memory_t,
        "tools": tools,
    }
    sub = _fmt_token_breakdown(total if total else daily_tokens, components)

    state = "attention" if modifier else "ok"

    return {
        "key": "usage",
        "label": "Usage today",
        "value": value,
        "sub": sub,
        "state": state,
        "modifier": modifier,
        "sources": ["token_logs", "chisel_drift"],
        "_raw": {
            "total_tokens": total,
            "daily_tokens": daily_tokens,
            "total_cost": total_cost,
            "components": components,
            "drift": guidance_drift,
        },
    }


def _assemble_memory(agent_name: str, db: Database, now: int, conn) -> dict:
    """Memory pillar: 'Is it forgetting?' <-- delegated to T4 memory data."""
    t4 = _t4_cache.get(agent_name, {})
    t4_memory = t4.get("memory", {})
    garden = t4_memory.get("garden")

    if not garden:
        return {
            "key": "memory",
            "label": "Memory",
            "value": "Never scanned",
            "sub": "No cleanup has run \u2014 set one up \u2192",
            "state": "unset",
            "modifier": None,
            "sources": ["clawforge_garden"],
        }

    debt = garden.get("debt_score", 0) or 0
    scan_ts = garden.get("scanned_at", 0)
    days = _days_since(scan_ts) if scan_ts else 0

    if days > 7:
        return {
            "key": "memory",
            "label": "Memory",
            "value": f"{days}d",
            "sub": "since its last cleanup \u2014 health unknown until one runs",
            "state": "unknown",
            "modifier": None,
            "sources": ["clawforge_garden"],
            "_raw": {
                "debt": debt,
                "duplicates": garden.get("duplicates", 0),
                "contradictions": garden.get("contradictions", 0),
                "stale_entries": garden.get("stale_entries", 0),
                "last_scan_ts": scan_ts,
                "auto_scan": garden.get("auto_scan", False),
            },
        }

    state = "attention" if debt >= 30 else "ok"
    value = f"{debt}/100"
    sub = "clean \u2014 no issues found" if debt == 0 else "memory debt score"

    return {
        "key": "memory",
        "label": "Memory",
        "value": value,
        "sub": sub,
        "state": state,
        "modifier": None,
        "sources": ["clawforge_garden"],
        "_raw": {
            "debt": debt,
            "duplicates": garden.get("duplicates", 0),
            "contradictions": garden.get("contradictions", 0),
            "stale_entries": garden.get("stale_entries", 0),
            "last_scan_ts": scan_ts,
            "auto_scan": garden.get("auto_scan", False),
        },
    }


# ── Drawer Rows ────────────────────────────────────────────────────────


def _drawer_quality(agent_name: str, db: Database, conn) -> list[dict]:
    """Drawer rows for Quality pillar. Named sources + raw values per §3.5."""
    run = conn.execute(
        "SELECT id, pass_count, fail_count, hang_count, total_tasks, "
        "started_at, total_cost, total_tokens FROM canary_runs "
        "WHERE agent_name=? AND status='completed' AND pass_count IS NOT NULL "
        "ORDER BY started_at DESC LIMIT 1",
        (agent_name,),
    ).fetchone()
    if not run:
        return []

    run = dict(run)
    total = (run["pass_count"] or 0) + (run["fail_count"] or 0)
    tasks = run["total_tasks"] or total
    acc = round(run["pass_count"] / total * 100) if total > 0 else 0

    fleet_row = conn.execute(
        "SELECT AVG(CAST(pass_count AS FLOAT) / NULLIF(pass_count + fail_count, 0)) * 100 as avg_acc "
        "FROM canary_runs WHERE status='completed' AND pass_count IS NOT NULL "
        "AND id IN (SELECT MAX(id) FROM canary_runs WHERE status='completed' "
        "AND pass_count IS NOT NULL GROUP BY agent_name)"
    ).fetchone()
    fleet_avg = round(fleet_row["avg_acc"]) if fleet_row and fleet_row["avg_acc"] else None

    rows = [
        {
            "label": "Latest benchmark run",
            "value": f"{run['id'][:8]} \u00b7 pass {run['pass_count']} \u00b7 fail {run['fail_count']} \u00b7 hang {run['hang_count']} \u00b7 {tasks} tasks",
            "warn": run["fail_count"] > 0,
        },
    ]
    if fleet_avg is not None:
        outlier = acc < fleet_avg - 20
        rows.append({
            "label": "Fleet context",
            "value": f"main averages {fleet_avg}% \u2014 {agent_name}'s {acc}% is {'an outlier' if outlier else 'within range'}",
            "warn": outlier,
        })
    if run["total_cost"]:
        rows.append({
            "label": "Run cost",
            "value": f"${run['total_cost']:.2f} \u00b7 {_fmt_human_number(run['total_tokens'])} tokens",
            "warn": False,
        })
    return rows


def _drawer_reliability(agent_name: str, db: Database, now: int, conn) -> list[dict]:
    """Drawer rows for Reliability pillar. Delegated to T4 for most data;
    keeps one targeted errors query for guard-event filtering (T4 exposes
    only error count, not raw error rows).
    """
    t4 = _t4_cache.get(agent_name, {})
    t4_health = t4.get("health", {})
    pulses = t4_health.get("pulse_history_24h", [])[:5]
    circuit = t4_health.get("circuit_breaker") or {}

    # Keep targeted errors query for guard-event detection (T4 provides
    # only error_count_24h, not raw error rows with error_type/message).
    try:
        errors = db.get_errors(agent_name=agent_name, limit=10)
    except Exception:
        errors = []

    rows = []
    if pulses:
        lat_str = " \u00b7 ".join(_fmt_latency(p.get("latency_ms", 0)) for p in pulses)
        cadence = 30
        rows.append({
            "label": "Pulse latency (last 5)",
            "value": f"{lat_str} @ {cadence}s cadence",
            "warn": any(p.get("latency_ms", 0) > 20000 for p in pulses),
        })

    guard_events = [
        e for e in errors
        if "guard" in str(e.get("error_type", "")).lower()
        or "watch_probe" in str(e.get("error_message", "")).lower()
    ]
    if guard_events:
        ge = guard_events[0]
        rows.append({
            "label": f"Guard event {datetime.fromtimestamp(ge['timestamp']).strftime('%H:%M')}",
            "value": f"watch_probe_failed \u2014 {ge.get('error_message', 'database is locked')[:60]} (SQLite contention)",
            "warn": True,
        })

    errors_24h = t4_health.get("error_count_24h", 0)
    if errors_24h > 0:
        rows.append({
            "label": "Errors (24h)",
            "value": f"{errors_24h} \u2014 same event, self-recovered" if errors_24h == 1 else f"{errors_24h} events",
            "warn": errors_24h > 3,
        })
    else:
        rows.append({
            "label": "Errors (24h)",
            "value": "0 \u2014 clean",
            "warn": False,
        })

    fail_count = circuit.get("failure_count", 0)
    tripped = circuit.get("tripped", False)
    cb_text = "tripped" if tripped else f"{fail_count}/3" if fail_count > 0 else "closed"
    rows.append({
        "label": "Circuit breaker",
        "value": cb_text,
        "warn": tripped or fail_count > 0,
    })

    return rows


def _drawer_usage(agent_name: str, db: Database, now: int, conn) -> list[dict]:
    """Drawer rows for Usage pillar. Delegated to T4 tokens data."""
    t4 = _t4_cache.get(agent_name, {})
    t4_tokens = t4.get("tokens", {})
    breakdown = t4_tokens.get("latest_breakdown", {})
    drift = t4_tokens.get("drift_trends", [])

    identity = breakdown.get("identity", 0) or 0
    skills = breakdown.get("skills", 0) or 0
    memory_t = breakdown.get("memory", 0) or 0
    tools = breakdown.get("tools", 0) or 0
    guidance = breakdown.get("guidance", 0) or 0
    total = identity + skills + memory_t + tools + guidance
    if total == 0:
        total = breakdown.get("total", 0) or 0

    rows = []

    if total > 0:
        comps = [
            ("guidance", guidance),
            ("identity", identity),
            ("skills", skills),
            ("memory", memory_t),
            ("tools", tools),
        ]
        comps = sorted(comps, key=lambda x: -x[1])
        comp_str = " \u00b7 ".join(
            f"{name} {_fmt_human_number(val)} ({round(val / total * 100)}%)"
            for name, val in comps if val > 0
        )
        rows.append({
            "label": "Composition",
            "value": comp_str,
            "warn": guidance > total * 0.5,
        })

    drift_vals = [d for d in drift if d.get("delta_pct") is not None]
    for d in drift_vals[:5]:
        dp = d["delta_pct"]
        method = d.get("method", "rolling")
        rows.append({
            "label": f"{d.get('component', 'system prompt').capitalize()} drift ({method}, 7d)",
            "value": f"{dp:+.1f}%",
            "warn": abs(dp) > 10,
        })

    return rows


def _drawer_memory(agent_name: str, db: Database, now: int, conn) -> list[dict]:
    """Drawer rows for Memory pillar. Delegated to T4 memory data."""
    t4 = _t4_cache.get(agent_name, {})
    t4_memory = t4.get("memory", {})
    garden = t4_memory.get("garden")

    if not garden:
        return [{
            "label": "Last scan",
            "value": "Never \u2014 auto-scan off",
            "warn": False,
        }]

    scan_ts = garden.get("scanned_at", 0)
    days = _days_since(scan_ts) if scan_ts else 0

    rows = []
    scan_str = f"{datetime.fromtimestamp(scan_ts).strftime('%b %d')} ({days}d ago)" if scan_ts else "Never"
    auto_scan = garden.get("auto_scan", False)
    auto_str = "on" if auto_scan else "off"
    rows.append({
        "label": "Last scan",
        "value": f"{scan_str} \u00b7 auto-scan {auto_str}",
        "warn": days > 7,
    })

    debt = garden.get("debt_score", 0) or 0
    rows.append({
        "label": "Reported debt",
        "value": f"{debt}/100" + (" \u2014 stale, not verified clean" if days > 7 else ""),
        "warn": debt >= 30,
    })

    dups = garden.get("duplicates", 0) or 0
    cons = garden.get("contradictions", 0) or 0
    stale = garden.get("stale_entries", 0) or 0
    if dups or cons:
        rows.append({
            "label": "Issues",
            "value": f"{dups} dup \u00b7 {cons} con \u00b7 {stale} stale",
            "warn": True,
        })

    return rows


# ── Status Line Synthesis ──────────────────────────────────────────────


def _synthesize_status_line(agent_name: str, pillars: list[dict]) -> tuple[str, str, str]:
    """Template-generate the status line and sub from pillar states.

    Returns (status_line, status_sub, severity_class).
    Severity: 'healthy' | 'warning' | 'critical' | 'unknown'
    """
    state_map = {p["key"]: p["state"] for p in pillars}
    values = {p["key"]: p["value"] for p in pillars}

    if state_map.get("reliability") == "attention" and values.get("reliability") in ("Down", "Stopped"):
        line = f"{agent_name} is down \u2014 it needs attention now."
        sub = "Has been unreachable; check the agent process"
        return line, sub, "critical"

    attention_pillars = [k for k, v in state_map.items() if v == "attention"]
    if attention_pillars:
        parts = []
        if "quality" in attention_pillars and values.get("quality"):
            parts.append("its work quality needs attention")
        if "reliability" in attention_pillars and values.get("reliability") not in ("Down", "Stopped"):
            parts.append("its health is degraded")
        if "usage" in attention_pillars:
            parts.append("usage is growing")
        if "memory" in attention_pillars:
            parts.append("memory needs cleanup")

        if parts:
            line = f"{agent_name} is running \u2014 but {' and '.join(parts)}."
        else:
            line = f"{agent_name} has items needing attention."
        sub = "Review the tiles below for details"
        return line, sub, "warning"

    unknown_pillars = [k for k, v in state_map.items() if v == "unknown"]
    if unknown_pillars:
        if state_map.get("memory") == "unknown" and values.get("memory", "").endswith("d"):
            line = f"{agent_name} is running \u2014 but we're not sure about its memory."
            sub = "Memory cleanup hasn't run in over a week"
        else:
            line = f"{agent_name} is running \u2014 some areas need setup."
            unset = [k for k, v in state_map.items() if v == "unset"]
            if unset:
                line = f"{agent_name} is running \u2014 set up {', '.join(unset)} checks."
            else:
                line = f"{agent_name} is running, but some data is incomplete."
        return line, sub or "Health unknown in some areas", "warning"

    has_modifier = any(p.get("modifier") for p in pillars)
    if has_modifier:
        line = f"{agent_name} is up and running \u2014 all clear."
        sub = "Usage is changing but nothing needs attention right now"
    else:
        line = f"{agent_name} is up and running \u2014 everything looks good."
        sub = "All systems nominal"

    return line, sub, "healthy"


def _generate_needs_attention(pillars: list[dict], agent_name: str) -> list[dict]:
    """Generate needs-attention issue cards from pillar data."""
    issues = []

    for p in pillars:
        if p["state"] != "attention":
            continue

        raw = p.get("_raw", {})

        if p["key"] == "quality":
            passed = raw.get("passed", 0)
            failed = raw.get("failed", 0)
            tasks = raw.get("total_tasks", 0)
            issues.append({
                "icon": "\U0001f4c9",
                "title": "Work quality dropped",
                "why": f"In its latest quality check, {agent_name} passed only <b>{passed} of {tasks}</b> test tasks. It's running fine \u2014 it's the answers that got worse.",
                "actions": [
                    {"label": "See what failed \u2192", "action": "view_benchmark"},
                    {"label": "Run a new check", "action": "run_benchmark", "ghost": True},
                ],
            })

        if p["key"] == "usage" and p.get("modifier"):
            mod_text = p["modifier"]
            if mod_text:
                mod_text = mod_text.replace("\u2197 ", "grew ")
            issues.append({
                "icon": "\U0001f4dd",
                "title": f"Its instruction file {mod_text}",
                "why": "Bigger instructions follow it into every conversation \u2014 each reply gets slower and costs more.",
                "actions": [
                    {"label": "Shrink instructions \u2192", "action": "shrink_guidance"},
                    {"label": "Not now", "action": "dismiss", "ghost": True},
                ],
            })

        if p["key"] == "reliability" and p["value"] in ("Down", "Stopped"):
            issues.append({
                "icon": "\u26a0\ufe0f" if p["value"] == "Down" else "\U0001f527",
                "title": f"{agent_name} is {'down' if p['value'] == 'Down' else 'stopped'}",
                "why": "The agent stopped responding. Check the process and restart it.",
                "actions": [
                    {"label": "View health \u2192", "action": "view_health"},
                    {"label": "Restart agent", "action": "restart_agent", "ghost": True},
                ],
            })

        if p["key"] == "reliability" and p["value"] == "Degraded":
            issues.append({
                "icon": "\U0001f4c8",
                "title": "Health checks are failing",
                "why": f"Recent pulse checks for {agent_name} are showing errors.",
                "actions": [
                    {"label": "View health \u2192", "action": "view_health"},
                ],
            })

    return issues


def _generate_worth_knowing(pillars: list[dict], agent_name: str) -> list[dict]:
    """Generate worth-knowing items (info, not action-required)."""
    items = []

    for p in pillars:
        raw = p.get("_raw", {})

        if p["key"] == "memory" and p["state"] == "unknown":
            days = p["value"].rstrip("d")
            items.append({
                "icon": "\U0001f9f9",
                "title": "Memory cleanup hasn't run in a while",
                "why": f"The cleanup job that keeps {agent_name}'s memory tidy last ran {days} days ago. Nothing is broken yet \u2014 it just hasn't had its tidy.",
                "actions": [
                    {"label": "Run cleanup now", "action": "run_garden", "ghost": True},
                ],
            })

        if p["key"] == "reliability" and p["state"] == "ok":
            lat_ms = raw.get("latency_ms", 0)
            if lat_ms > 20000:
                items.append({
                    "icon": "\U0001f40c",
                    "title": "Health checks are running slow",
                    "why": f"The monitor itself got briefly stuck and checks now take up to {_fmt_latency(lat_ms)}. <b>{agent_name} was never down</b> \u2014 this is about the watchdog, not the agent.",
                    "actions": [],
                })

        if p["state"] == "unset":
            if p["key"] == "memory":
                items.append({
                    "icon": "\U0001f9f9",
                    "title": "Memory cleanup hasn't been configured",
                    "why": f"{agent_name} has no memory garden scanner. Set one up to detect duplicates, contradictions, and stale entries before they accumulate.",
                    "actions": [
                        {"label": "Set up scanner \u2192", "action": "setup_garden", "ghost": True},
                    ],
                })

    return items


def _generate_doing_well(pillars: list[dict]) -> list[str]:
    """Generate 'doing well' badges from pillar data."""
    badges = []

    for p in pillars:
        if p["state"] != "ok":
            continue

        if p["key"] == "reliability":
            badges.append("Responding normally")
            raw = p.get("_raw", {})
            if raw.get("errors_24h", 0) == 0:
                badges.append("No errors in the last 24h")
            if raw.get("circuit_tripped") is False or raw.get("circuit_failures", 0) == 0:
                badges.append("Self-recovering from any issues")

        if p["key"] == "quality":
            raw = p.get("_raw", {})
            if raw and raw.get("failed", 0) == 0 and raw.get("hung", 0) == 0:
                badges.append("All quality checks passing")

        if p["key"] == "memory":
            raw = p.get("_raw", {})
            if raw and raw.get("debt", 10) == 0:
                if raw.get("duplicates", 0) == 0 and raw.get("contradictions", 0) == 0:
                    badges.append("Memory is clean")

    return badges if badges else ["Operating normally"]


# ── Public API ─────────────────────────────────────────────────────────


def get_agent_profile(
    agent_name: str,
    db: Optional[Database] = None,
    use_cache: bool = True,
    cache_ttl: float = CACHE_TTL,
) -> dict:
    """Return a unified four-pillar profile for a single agent."""
    if use_cache and agent_name in _profile_cache:
        ts, payload = _profile_cache[agent_name]
        if time.monotonic() - ts < cache_ttl:
            return payload

    close_on_exit = db is None
    if db is None:
        db = Database()

    try:
        profile = _build_profile(agent_name, db)
        if use_cache:
            _profile_cache[agent_name] = (time.monotonic(), profile)
        return profile
    finally:
        if close_on_exit:
            db.close()


def invalidate_cache(agent_name: Optional[str] = None) -> None:
    """Invalidate the profile cache."""
    if agent_name:
        _profile_cache.pop(agent_name, None)
    else:
        _profile_cache.clear()


def _build_profile(agent_name: str, db: Database) -> dict:
    """Assemble the composite four-pillar profile from all data sources.

    Delegates bulk DB queries for reliability/usage/memory to the T4
    service, keeping only quality-pillar canary queries and the guard-event
    errors query in this layer.
    """
    now = int(time.time())
    conn = db._get_conn()

    # ── Agent existence check ──
    agents = db.get_agents()
    agent_info = next((a for a in agents if a["agent_name"] == agent_name), None)
    if agent_info is None:
        return {"error": "agent_not_found", "agent_name": agent_name}

    # ── Delegate bulk raw-data fetch to T4 service ──
    from observeco.agent_profile_service import _build_profile as _t4_build
    t4_data = _t4_build(agent_name, db)
    if "error" not in t4_data:
        _t4_cache[agent_name] = t4_data

    try:
        # ── Assemble four pillars ──
        quality = _assemble_quality(agent_name, db, now, conn)
        reliability = _assemble_reliability(agent_name, db, now, conn)
        usage = _assemble_usage(agent_name, db, now, conn)
        memory = _assemble_memory(agent_name, db, now, conn)
        pillars = [quality, reliability, usage, memory]

        # ── Status line ──
        status_line, status_sub, severity = _synthesize_status_line(agent_name, pillars)

        # ── Sections ──
        needs_attention = _generate_needs_attention(pillars, agent_name)
        worth_knowing = _generate_worth_knowing(pillars, agent_name)
        doing_well = _generate_doing_well(pillars)

        # ── Drawer rows ──
        drawer = {
            "quality": _drawer_quality(agent_name, db, conn),
            "reliability": _drawer_reliability(agent_name, db, now, conn),
            "usage": _drawer_usage(agent_name, db, now, conn),
            "memory": _drawer_memory(agent_name, db, now, conn),
        }

        # ── Meta ──
        raw_fw = (agent_info.get("framework", "") or "")
        fw_parts = [p.strip().capitalize() for p in raw_fw.split("+")] if raw_fw else []
        framework = " + ".join(fw_parts) if fw_parts else ""

        meta = {
            "agent_name": agent_name,
            "framework": framework,
            "agent_type": agent_info.get("class", "service"),
            "profile_generated_at": int(time.time()),
        }

        return {
            "status_line": status_line,
            "status_sub": status_sub,
            "severity": severity,
            "pillars": pillars,
            "needs_attention": needs_attention,
            "worth_knowing": worth_knowing,
            "doing_well": doing_well,
            "drawer": drawer,
            "meta": meta,
        }
    finally:
        _t4_cache.pop(agent_name, None)
