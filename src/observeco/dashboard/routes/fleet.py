"""Fleet routes — verdict bar, agent cards, fleet comparison.

DPA Reference: Section 1 Q1/Q3, Section 2-A/B/D, Section 3 endpoints.
Design: All States (v2) Strong-Fit — verdict bar + agent card grid.
"""

from __future__ import annotations

import logging
import sqlite3 as _sqlite3
import time

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from observeco.db import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fleet", tags=["fleet"])
db = Database()

# ── Helpers ─────────────────────────────────────────────────────────────

def _fmt_ts(ts: int) -> str:
    """Relative timestamp like '12s ago', '3m ago', '2h ago'."""
    now = int(time.time())
    delta = now - ts
    if delta < 60:
        return f"{delta}s ago"
    elif delta < 3600:
        return f"{delta // 60}m ago"
    elif delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"

def _fmt_tokens(n: int) -> str:
    """Format token count: 12400 → '12.4K'."""
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)

def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


# ── Canary row for fleet grid cards ───────────────────────────────────────────


def _canary_row(agent_name: str, canary_row, canary_running: bool = False) -> str:
    """Render compact canary % for a fleet card row (pass count shown separately near chevron)."""
    if canary_running:
        return '<span class="row-val" style="color:var(--warn)">⏳</span>'
    if not canary_row:
        return '<span class="row-val" style="color:var(--muted)">no data</span>'
    total = (canary_row["pass_count"] or 0) + (canary_row["fail_count"] or 0)
    # If all results are provider errors, show that instead of 0%
    provider_errs = (dict(canary_row).get("provider_error_count") if hasattr(canary_row, "keys") else canary_row.get("provider_error_count", 0)) or 0
    acc = (canary_row["pass_count"] / total * 100) if total > 0 else 0
    if provider_errs > 0 and canary_row["pass_count"] == 0 and total == 0:
        return f'<span class="row-val" style="color:var(--muted)">⚠️ provider</span>'
    color = "var(--accent)" if acc >= 80 else "var(--warn)" if acc >= 60 else "var(--danger)"
    canary_dict = dict(canary_row) if hasattr(canary_row, "keys") else canary_row
    cost_str = f' · ${canary_dict["total_cost"]:.2f}' if canary_dict.get("total_cost") else ""
    return f'<span class="row-val" style="color:{color}">{acc:.0f}%</span><span class="row-sub-cost">{cost_str}</span>'


def _canary_pass_sub(agent_name: str, canary_row, canary_running: bool = False, drift_row=None) -> str:
    """Pass count + Run trigger for the chevron row-sub (obs-spec-057 Variant C)."""
    if canary_running:
        return 'running'
    if not canary_row:
        return f'<button class="qb-run-btn" onclick="event.stopPropagation();openQualityBenchmark(\'{_html_escape(agent_name)}\')">▶ Run</button>'
    (canary_row["pass_count"] or 0) + (canary_row["fail_count"] or 0)
    hangs = canary_row["hang_count"] or 0
    hang_str = f" · ⚠️{hangs} hang{'s' if hangs != 1 else ''}" if hangs else ""
    parts = f'{canary_row["pass_count"]}/{canary_row["total_tasks"]} pass{hang_str}'
    canary_r = dict(canary_row) if hasattr(canary_row, "keys") else canary_row
    cost_str = f' · ${canary_r["total_cost"]:.2f}' if canary_r.get("total_cost") else ""
    parts += cost_str
    # Quality drift indicator from drift_events
    if drift_row:
        drift_pct = drift_row["drift_pct"]
        dir_sign = "▼" if drift_pct < 0 else "▲" if drift_pct > 0 else "◆"
        parts += f' <span style="font-size:10px;color:{"var(--danger)" if abs(drift_pct) > 10 else "var(--warn)" if abs(drift_pct) > 5 else "var(--fg-3)"}">{dir_sign} {abs(drift_pct):.0f}% drift</span>'
    return parts


# ── So What insight generation ────────────────────────────────────────

def _so_what_insights(agent_name: str, cls: str, drift: list, trims: list,
                       errors: list, total_tokens: int) -> str:
    """Generate So What insight cards for an agent per DPA §5."""
    cards = []

    # Drift insight
    max_drift = max((d.get("delta_pct", 0) for d in drift if d.get("breached")), default=0)
    if max_drift > 5:
        comps_with_drift = [d for d in drift if d.get("breached") and abs(d.get("delta_pct", 0)) > 5]
        if comps_with_drift:
            comp = comps_with_drift[0].get("component", "system prompt")
            pct = comps_with_drift[0].get("delta_pct", 0)
            tone = "alert" if pct > 15 else "watch"
            mark = "!" if tone == "alert" else "⚠"
            label = "DEGRADING" if tone == "alert" else "WATCH"
            cards.append(f"""<div class="swc {tone}">
    <span class="mark">{mark}</span>
    <div class="body">
        <span class="lead">{label}</span>
        <div class="txt"><b>{comp}</b> grew <span class="num">{pct:+.1f}%</span> this week. Consider compression.</div>
    </div>
</div>""")

    # Token insight (if enough data)
    if total_tokens > 10000:
        skills_pct = round((trims[0].get("skills_tokens", 0) / total_tokens * 100)) if trims and total_tokens else 0
        if skills_pct > 30:
            cards.append(f"""<div class="swc insight">
    <span class="mark">i</span>
    <div class="body">
        <span class="lead">INSIGHT</span>
        <div class="txt">Skills is <span class="num">{skills_pct}%</span> of context. Compressing unused skills could save ~<span class="num">{(total_tokens * skills_pct // 200):,}</span> tokens/turn.</div>
    </div>
</div>""")

    # Error insight
    recent_errors = len([e for e in errors if e.get("timestamp", 0) > int(time.time()) - 86400])
    if recent_errors > 0:
        tone = "alert" if recent_errors > 3 else "watch"
        mark = "!" if tone == "alert" else "⚠"
        label = "ERRORS" if tone == "alert" else "WATCH"
        cards.append(f"""<div class="swc {tone}">
    <span class="mark">{mark}</span>
    <div class="body">
        <span class="lead">{label}</span>
        <div class="txt"><span class="num">{recent_errors}</span> error{'s' if recent_errors != 1 else ''} in last 24h. {errors[0].get('error_message','')[:50]}.</div>
    </div>
</div>""")

    return "\n".join(cards)

# ── DPA §2-A: Agent Health State Machine ─────────────────────────────

def _classify_agent(pulse: dict, drift: list, circuit: dict, errors: list, now: int) -> str:
    """Classify agent health per DPA §2-A rules. First match wins."""
    status = pulse.get("status", "") if pulse else ""
    last_ts = pulse.get("timestamp", 0) if pulse else 0
    delta = now - last_ts if last_ts else 999999

    # No pulse for >4h → UNKNOWN
    if not pulse or delta > 14400:
        return "unknown"

    # pulse=dead + last_seen >5m → CRITICAL
    if status == "dead" and delta > 300:
        return "critical"

    # pulse=error + consecutive >=3 → WARNING
    # (approximate: count recent errors in > 0)
    if status == "error":
        # Check if we have 3+ consecutive errors — use recent pulse count
        return "warning"

    # pulse=alive + drift >10% → WARNING
    max_drift = max((d.get("delta_pct", 0) for d in drift if d.get("breached")), default=0)
    if status == "alive" and max_drift > 10:
        return "warning"

    # pulse=alive + errors_24h >5 → WARNING
    recent_errors = len([e for e in errors if e.get("timestamp", 0) > now - 86400])
    if status == "alive" and recent_errors > 5:
        return "warning"

    # pulse=alive + all clear → HEALTHY
    if status == "alive":
        return "healthy"

    return "unknown"


# ── DPA §2-B: Fleet Verdict ──────────────────────────────────────────

def _fleet_verdict(state_counts: dict) -> dict:
    """Return verdict label, icon class, and sentence per DPA §2-B."""
    crit = state_counts.get("critical", 0)
    warn = state_counts.get("warning", 0)
    healthy = state_counts.get("healthy", 0)
    unknown = state_counts.get("unknown", 0)
    total = sum(state_counts.values())

    if crit > 0:
        return {
            "severity": "crit",
            "icon": "●",
            "text": f"{crit} agent{'s' if crit != 1 else ''} need attention",
            "sub": f"1 of {total} operating normally",
            "cls": "crit",
        }
    if warn > 0:
        return {
            "severity": "warn",
            "icon": "●",
            "text": "All agents operational — signs detected",
            "sub": f"{warn} agent{'s' if warn != 1 else ''} showing warning signs",
            "cls": "warn",
        }
    if healthy > 0 and unknown > 0:
        return {
            "severity": "info",
            "icon": "✓",
            "text": f"All monitored agents healthy — {unknown} with unknown status",
            "sub": "",
            "cls": "info",
        }
    if healthy > 0:
        return {
            "severity": "info",
            "icon": "✓",
            "text": f"Fleet healthy — all {total} agents operating normally",
            "sub": "",
            "cls": "info",
        }
    return {
        "severity": "neutral",
        "icon": "⬡",
        "text": "No agents discovered yet",
        "sub": "nothing to monitor on this machine",
        "cls": "neutral",
    }


# ── DPA §2-D: Data Quality Tier ──────────────────────────────────────

def _data_quality_chip(agents: list) -> str:
    """Render data quality chip for verdict bar per DPA §2-D."""
    # Count agents with any source info
    total = len(agents)
    if total == 0:
        return ""

    # Simple heuristic: if agent has otel or watch data
    tier1 = sum(1 for a in agents if a.get("dq", "") == "acc")
    pct = round(tier1 / total * 100)
    full_bars = pct // 34  # 0-3 segments
    full_bars = min(full_bars, 3)
    segs = ""
    for i in range(3):
        cls = "seg full" if i < full_bars else "seg"
        segs += f'<i class="{cls}"></i>'

    otel_count = tier1
    watch_count = total - tier1

    return f"""<div class="dqchip">
    <div class="top"><span>data quality</span> <b>{pct}%</b></div>
    <div class="bar">{segs}</div>
    <div style="font-size:9px;color:var(--fg-3);margin-top:2px">{otel_count} otel · {watch_count} watch-only</div>
</div>"""


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/verdict", response_class=HTMLResponse)
async def fleet_verdict():
    """DPA §3: GET /api/fleet/verdict — returns verdict bar HTML partial.
    Answers Q3: Is my fleet OK? (trajectory)"""
    now = int(time.time())

    try:
        summary = db.get_agent_status_summary()
        circuit = db.get_circuit_breakers()
        drift_all = db.get_drift_latest_per_agent()
        errors_all = db.get_errors(limit=100)
        db.get_agents()

        # Pre-index for O(1) lookups
        circuit_by_agent = {c["agent_name"]: c for c in circuit}
        drift_by_agent = {d["agent_name"]: d for d in drift_all}
        errors_by_agent: dict[str, list] = {}
        for e in errors_all:
            errors_by_agent.setdefault(e["agent_name"], []).append(e)
    except Exception:
        # Error state — daemon down or DB unavailable
        return HTMLResponse("""<div class="verdict warn daemon">
    <div class="verdict-icon">⚠</div>
    <div class="verdict-main">
        <div class="verdict-text"><span style="color:var(--status-warning)">Monitoring stopped — daemon offline.</span> <span class="sub">Data may be stale or unavailable.</span></div>
        <div class="verdict-sub2">watch daemon not responding · pulse_log not advancing</div>
    </div>
    <div class="verdict-meta"><span class="daemon-tag">ERROR</span><span class="cmd" style="font-size:11px;padding:4px 10px">observeco start</span></div>
</div>""")

    if not summary:
        # Empty state
        return HTMLResponse("""<div class="verdict neutral">
    <div class="verdict-icon">⬡</div>
    <div class="verdict-main">
        <div class="verdict-text"><span class="sub">No agents discovered yet.</span></div>
        <div class="verdict-sub2">nothing to monitor on this machine</div>
    </div>
    <div class="verdict-meta">
        <div class="vchip"><b>0</b>agents</div>
    </div>
</div>""")

    # Classify each agent
    agents_data = []
    state_counts = {"critical": 0, "warning": 0, "healthy": 0, "unknown": 0}
    tripped_count = 0
    agent_names_critical = []
    agent_names_warning = []

    for name, s in summary.items():
        status = s.get("status", "")
        last_ts = s.get("timestamp", 0)
        circuit_state = circuit_by_agent.get(name)
        agent_drift = drift_by_agent.get(name)
        agent_drift_list = [agent_drift] if agent_drift else []
        agent_errors = errors_by_agent.get(name, [])

        cls = _classify_agent(
            {"status": status, "timestamp": last_ts},
            agent_drift_list,
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

        agents_data.append({
            "name": name,
            "status": cls,
            "last_seen": _fmt_ts(last_ts) if last_ts and last_ts < now else "—",
            "circuit_tripped": circuit_state.get("tripped", False) if circuit_state else False,
        })

    # Verdict sentence
    verdict = _fleet_verdict(state_counts)
    total = sum(state_counts.values())

    # Build agent list for verdict sentence — as pills, not inline text
    verdict_detail = ""
    if agent_names_critical:
        parts = []
        for n in agent_names_critical:
            parts.append(f'<span class="agent-pill dead">{_html_escape(n)}</span>')
        verdict_detail = " " + " ".join(parts)
    elif agent_names_warning:
        parts = []
        for n in agent_names_warning:
            parts.append(f'<span class="agent-pill deg">{_html_escape(n)}</span>')
        verdict_detail = " " + " ".join(parts)

    sub2_parts = []
    if tripped_count:
        sub2_parts.append(f"circuit tripped on {tripped_count} agent{'s' if tripped_count != 1 else ''}")
    sub2 = " · ".join(sub2_parts) if sub2_parts else ""

    # Data quality chip
    dq_chip = _data_quality_chip(agents_data)

    # Data quality warning banner (prominent when 0%)
    dq_warning = ""
    if total > 0:
        # Recalculate from actual data
        pct = 0
        if total > 0:
            # Count agents with any source info
            from observeco.db import Database
            _db = Database()
            try:
                conn = _db._get_conn()
                row = conn.execute("SELECT COUNT(*) FROM agent_configs WHERE source IS NOT NULL AND source != ''").fetchone()
                with_source = row[0] if row else 0
                pct = round(with_source / total * 100)
            except Exception:
                pct = 0
        if pct == 0:
            dq_warning = f"""<div class="dq-warning">
    <span class="dq-w-icon">⚠</span>
    <span class="dq-w-text"><b>No telemetry data</b> — all {total} agents are watch-only. Add OpenTelemetry instrumentation for real-time health data.</span>
</div>"""

    # Discovery gap (compute from circuit_breakers + drift breaches)
    gap_cumulative = 0
    max_gap = 0
    gap_agents = []
    for cb in circuit:
        if cb.get("tripped") and cb.get("cooldown_until"):
            gap = now - cb["cooldown_until"]
            if gap > 0:
                gap_cumulative += gap
                max_gap = max(max_gap, gap)
                gap_agents.append(cb.get("agent_name", ""))
    gap_hours = gap_cumulative // 3600
    gap_minutes = (gap_cumulative % 3600) // 60
    gap_text = f"{gap_hours}h{gap_minutes:02d}m" if gap_cumulative > 0 else ""

    return HTMLResponse(f"""<div class="verdict {verdict['cls']}">
    <div class="verdict-icon">{verdict['icon']}</div>
    <div class="verdict-main">
        <div class="verdict-text">
            <span class="{'dead' if verdict['severity']=='crit' else 'deg' if verdict['severity']=='warn' else ''}">{_html_escape(verdict['text'])}</span>
            {f'— {verdict_detail}' if verdict_detail else ''}
            <span class="sub"> {verdict['sub']}</span>
        </div>
        {dq_warning}
        {f'<div class="verdict-sub2">{_html_escape(sub2)}</div>' if sub2 else ''}
    </div>
    <div class="verdict-meta">
        <div class="vchip"><b>{total}</b>agents</div>
        {f'<div class="vchip crit"><b>{tripped_count}</b>tripped</div>' if tripped_count else ''}
        {f'<div class="vchip gap"><b>{gap_text}</b>undiscov.</div>' if gap_text else ''}
        {dq_chip}
    </div>
</div>""")


# ── Canary Report Card ─────────────────────────────────────────────


def _canary_card(agent_name: str) -> str:
    """Render a canary report card (Variant A) for an agent.

    Shows pass rate, accuracy, hangs, recovery, and drift vs baseline.
    Empty state when no canary runs exist.
    """
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()

    # Get latest completed run
    run = conn.execute(
        "SELECT id, pass_count, fail_count, hang_count, total_tasks, "
        "started_at, config_hash, "
        "COALESCE(total_cost, 0.0) as total_cost, "
        "COALESCE(total_tokens, 0) as total_tokens FROM canary_runs "
        "WHERE agent_name = ? AND status = 'completed' AND pass_count IS NOT NULL "
        "ORDER BY started_at DESC LIMIT 1",
        (agent_name,),
    ).fetchone()

    if not run:
        return f"""<div class="canary-card">
  <div class="canary-empty">🔬 No canary baseline yet <button onclick="runCanaryFor('{agent_name}')">Run Canary</button></div>
</div>"""

    total = (run["pass_count"] or 0) + (run["fail_count"] or 0)
    pass_rate = f"{run['pass_count']}/{run['total_tasks']}" if run["total_tasks"] else "0/0"
    accuracy = f"{run['pass_count'] / total:.0%}" if total > 0 else "0%"
    hangs = run["hang_count"] or 0
    recovery = "100%" if hangs == 0 else "0%"

    # Color coding
    acc_pct = run["pass_count"] / total if total > 0 else 0
    acc_color = "green" if acc_pct >= 0.7 else "yellow" if acc_pct >= 0.4 else "red"
    hang_color = "green" if hangs == 0 else "yellow" if hangs <= 2 else "red"

    # Drift vs baseline
    baseline = conn.execute(
        "SELECT accuracy FROM canary_baselines "
        "WHERE agent_name = ? AND expires_at IS NULL ORDER BY created_at DESC LIMIT 1",
        (agent_name,),
    ).fetchone()

    drift_html = ""
    if baseline and total > 0:
        baseline_acc = baseline["accuracy"]
        current_acc = run["pass_count"] / total
        drift_pct = (current_acc - baseline_acc) * 100
        drift_dir = "up" if drift_pct >= 0 else "down"
        drift_icon = "▲" if drift_pct >= 0 else "▼"
        drift_html = f'<div class="drift-indicator {drift_dir}">{drift_icon} {abs(drift_pct):.1f}% vs baseline</div>'
    else:
        drift_html = '<div style="color:var(--muted);font-size:10px;">No baseline</div>'

    return f"""<div class="canary-card">
  <div class="canary-card-header">
    <div class="canary-card-title">
      <span class="status-dot {acc_color}"></span>
      Canary
      <span class="canary-card-meta">Last run: {run['started_at'][:10]}</span>
    </div>
  </div>
  <div class="canary-card-stats">
    <div class="canary-stat">
      <div class="canary-stat-num {acc_color}">{pass_rate}</div>
      <div class="canary-stat-label">Pass Rate</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num {acc_color}">{accuracy}</div>
      <div class="canary-stat-label">Accuracy</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num {hang_color}">{hangs}</div>
      <div class="canary-stat-label">Hangs</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num green">{recovery}</div>
      <div class="canary-stat-label">Recovery</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num">${run['total_cost']:.4f}</div>
      <div class="canary-stat-label">Cost</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num">{_fmt_tokens(run['total_tokens'])}</div>
      <div class="canary-stat-label">Tokens</div>
    </div>
  </div>
  <div class="canary-card-footer">
    {drift_html}
    <span class="action-link" onclick="switchTab('capability', document.querySelector('.tab-btn:nth-child(11)'))">View details →</span>
  </div>
</div>"""


@router.get("/canary-card/{agent_name}", response_class=HTMLResponse)
async def api_canary_card(agent_name: str):
    """GET /api/fleet/canary-card/{agent} — canary card HTML for the Quality Benchmark modal."""
    return HTMLResponse(_canary_card(agent_name))


@router.post("/circuits/{agent_name}/reset", response_class=HTMLResponse)
async def reset_circuit(agent_name: str):
    """POST /api/fleet/circuits/{agent}/reset — reset a circuit breaker.

    Sets tripped=0, failure_count=0 so the next genuine failure starts fresh.
    Returns the guard row fragment for htmx swap.
    """
    conn = db._get_conn()
    conn.execute(
        "UPDATE circuit_breakers SET tripped = 0, failure_count = 0, cooldown_until = NULL "
        "WHERE agent_name = ?",
        (agent_name,),
    )
    conn.commit()
    return HTMLResponse(
        f'<span style="color:var(--accent);font-size:12px;">Circuit reset for {agent_name}</span>'
    )


@router.get("/agents", response_class=HTMLResponse)
async def fleet_agents(status_filter: str = "", q: str = "", page: int = 1):
    """DPA §3: GET /api/fleet/agents — returns agent card grid partial.
    Answers Q1: What did the agent do? / Q2: Why did it do that?"""
    now = int(time.time())

    try:
        summary = db.get_agent_status_summary()
        agents_cfg = db.get_agents()
        circuit = db.get_circuit_breakers()
        drift_all = db.get_drift_latest_per_agent()
        errors_all = db.get_errors(limit=100)

        # ── Pre-index everything by agent_name (N+1 → O(1)) ──
        # Batch trims: one query instead of 41
        all_trims = db.get_trims(limit=500)
        trims_by_agent: dict[str, dict] = {}
        for t in all_trims:
            if t["agent_name"] not in trims_by_agent:
                trims_by_agent[t["agent_name"]] = dict(t)

        # Batch gardens: one query instead of 41
        all_gardens = db.get_gardens()
        gardens_by_agent: dict[str, list] = {}
        for g in all_gardens:
            gardens_by_agent.setdefault(g["agent_name"], []).append(g)

        # Pre-index drift by agent_name
        drift_by_agent = {d["agent_name"]: d for d in drift_all}

        # Pre-index circuit breakers by agent_name
        circuit_by_agent = {c["agent_name"]: c for c in circuit}

        # Pre-index errors by agent_name
        errors_by_agent: dict[str, list] = {}
        for e in errors_all:
            errors_by_agent.setdefault(e["agent_name"], []).append(e)

        # Batch recent pulses: one query instead of 41
        all_pulses = db.get_recent_pulses(limit=200)
        pulses_by_agent: dict[str, list] = {}
        for p in all_pulses:
            pulses_by_agent.setdefault(p["agent_name"], []).append(p)

        # Batch token_logs freshness check
        has_otel: dict[str, bool] = {}
        conn_main = db._get_conn()
        now_ts = int(time.time())
        try:
            for row in conn_main.execute(
                "SELECT DISTINCT agent_name FROM token_logs WHERE recorded_at > ?",
                (now_ts - 86400,),
            ).fetchall():
                has_otel[row["agent_name"]] = True
        except Exception:
            pass  # table may not exist — default to estimate

        # Canary data for grid cards
        conn = db._get_conn()
        # Non-critical cleanup — use db._write() (retry-on-lock) so a collision
        # with the watch daemon's writes doesn't 500 the whole tab.
        try:
            db._write(
                "UPDATE canary_runs SET status = 'failed' "
                "WHERE status = 'running' AND started_at < datetime('now', '-30 minutes')",
                (),
            )
        except _sqlite3.OperationalError:
            pass  # skip cleanup if DB locked right now
        canary_latest = {}
        for row in conn.execute(
            "SELECT r.agent_name, r.pass_count, r.fail_count, r.hang_count, r.total_tasks, "
            "r.started_at, COALESCE(r.total_cost, 0.0) as total_cost, "
            "COALESCE(r.total_tokens, 0) as total_tokens, "
            "(SELECT SUM(CASE WHEN cr.status = 'provider_error' THEN 1 ELSE 0 END) "
            " FROM canary_results cr WHERE cr.run_id = r.id) as provider_errors "
            "FROM canary_runs r "
            "WHERE r.status = 'completed' AND r.pass_count IS NOT NULL "
            "ORDER BY r.started_at DESC"
        ).fetchall():
            if row["agent_name"] not in canary_latest:
                # Skip runs where all failures were provider errors
                prov = row["provider_errors"] or 0
                if row["pass_count"] == 0 and row["fail_count"] > 0 and prov >= row["fail_count"]:
                    continue
                canary_latest[row["agent_name"]] = row
        # Track agents with running canaries — exclude stuck ones (running >5min with no results)
        canary_running = set()
        for row in conn.execute(
            "SELECT cr.id, cr.agent_name, cr.started_at, "
            "(SELECT COUNT(*) FROM canary_results WHERE run_id = cr.id) as result_count "
            "FROM canary_runs cr WHERE cr.status = 'running'"
        ).fetchall():
            # Skip stuck runs: no results after 5 minutes
            if row["result_count"] == 0 and row["started_at"]:
                from datetime import datetime, timezone
                started = datetime.fromisoformat(row["started_at"])
                # Handle both tz-aware and tz-naive datetimes
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - started).total_seconds() > 300:
                    continue  # stuck, don't show as running
            canary_running.add(row["agent_name"])
        # Quality drift from drift_events (latest per agent)
        quality_drift = {}
        for row in conn.execute(
            "SELECT agent_name, drift_pct, severity FROM drift_events "
            "ORDER BY created_at DESC"
        ).fetchall():
            if row["agent_name"] not in quality_drift:
                quality_drift[row["agent_name"]] = row
    except Exception as _fleet_err:
        logger.exception("fleet_agents failed: %s", _fleet_err)
        # Error state — daemon down or DB unavailable
        return HTMLResponse("""<div class="section-h"><h2>Fleet</h2><span class="count">error</span></div>
<div class="grid">
    <div class="state-msg err">
        <div class="ico">⚠</div>
        <h3>Fleet data unavailable</h3>
        <p>The watch daemon is not responding. Start it with <span class="mono" style="color:var(--fg)">observeco start</span> to resume monitoring.</p>
        <span class="cmd">observeco start</span>
    </div>
</div>""")

    if not summary:
        # Empty state
        return HTMLResponse("""<div class="section-h"><h2>Fleet</h2><span class="count">0 agents</span></div>
<div class="grid">
    <div class="empty-card">
        <div class="ico">⬡</div>
        <h3>No agents discovered</h3>
        <p>Run <span class="mono" style="color:var(--fg)">observeco agents discover</span> or add one manually.</p>
        <span class="cmd">observeco agents discover</span>
    </div>
</div>""")

    # Classify and build cards, grouped by framework (or status as fallback)
    groups: dict[str, list[str]] = {}
    state_counts = {"critical": 0, "warning": 0, "healthy": 0, "unknown": 0}

    # Classify: read declared class from agent_configs (migration 58).
    # Brain (trim data) + memory (garden data) are DISPLAY signals, not the
    # classifier — a real agent that hasn't collected garden data yet must not
    # flip to "service". The class field is the source of truth.
    cfg_class = {a["agent_name"]: a.get("class", "service") for a in agents_cfg}
    name_type = {}
    for name, s in summary.items():
        trim = trims_by_agent.get(name, {})
        has_brain = any(trim.get(k, 0) for k in ("identity_tokens", "skills_tokens", "memory_tokens", "tools_tokens", "guidance_tokens"))
        gardens = gardens_by_agent.get(name, [])
        has_memory = bool(gardens)
        # Declared class wins; fall back to inference only if undeclared (null).
        declared = cfg_class.get(name, "service")
        if declared in ("agent", "service"):
            name_type[name] = declared
        else:
            name_type[name] = "agent" if has_brain and has_memory else "service"
        # Stash display signals for the template
        s["has_brain"] = has_brain
        s["has_memory"] = has_memory

    # Sort: agents first, then services
    type_order = {"agent": 0, "service": 1}
    sorted_names = sorted(summary.keys(), key=lambda n: (type_order.get(name_type.get(n, "service"), 9), n.lower()))

    # ── Paginate: 20 agents per page ──
    PAGE_SIZE = 20
    total_agents = len(sorted_names)
    total_pages = max(1, (total_agents + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))  # clamp to valid range
    start = (page - 1) * PAGE_SIZE
    page_names = sorted_names[start:start + PAGE_SIZE]

    for name in page_names:
        s = summary[name]
        # Apply name search filter (case-insensitive)
        if q and q.strip() and q.strip().lower() not in name.lower():
            continue

        status = s.get("status", "")
        last_ts = s.get("timestamp", 0)
        circuit_state = circuit_by_agent.get(name)
        agent_drift = drift_by_agent.get(name)
        agent_drift_list = [agent_drift] if agent_drift else []
        agent_errors = errors_by_agent.get(name, [])

        cls = _classify_agent(
            {"status": status, "timestamp": last_ts},
            agent_drift_list,
            circuit_state or {},
            agent_errors,
            now,
        )
        state_counts[cls] = state_counts.get(cls, 0) + 1

        # Apply status filter
        if status_filter:
            filter_map = {"alive": "healthy", "error": "warning", "dead": "critical", "unknown": "unknown"}
            if cls != filter_map.get(status_filter, ""):
                continue

        # Get latest trim for token breakdown
        trim = trims_by_agent.get(name, {})

        # Error count in last 24h
        errors_24h = len([e for e in agent_errors if e.get("timestamp", 0) > now - 86400])
        last_error = agent_errors[0] if agent_errors else None
        last_err_msg = last_error.get("error_message", "")[:40] if last_error else ""
        last_err_ts = _fmt_ts(last_error.get("timestamp", 0)) if last_error else ""

        # Circuit state
        circuit_tripped = circuit_state.get("tripped", False) if circuit_state else False
        circuit_fails = circuit_state.get("failure_count", 0) if circuit_state else 0
        circuit_text = "closed"
        circuit_color = "var(--fg-2)"
        if circuit_tripped:
            circuit_text = "tripped"
            circuit_color = "var(--status-critical)"
        elif circuit_fails > 0:
            circuit_text = f"{circuit_fails}/3 fails"
            circuit_color = "var(--status-warning)"

        # Token composition
        identity = trim.get("identity_tokens", 0)
        skills = trim.get("skills_tokens", 0)
        memory = trim.get("memory_tokens", 0)
        tools = trim.get("tools_tokens", 0)
        guidance = trim.get("guidance_tokens", 0)
        total_tokens = identity + skills + memory + tools + guidance
        has_token_data = True
        if total_tokens == 0 and trim.get("total_tokens", 0) == 0:
            # No real brain/trim data collected. Do NOT fabricate a default
            # composition — that misleads (services show "100 tok" as if real).
            # Render "—" instead so the absence of data is honest.
            has_token_data = False
            identity = skills = memory = tools = guidance = 0
            total_tokens = 0
        elif total_tokens == 0:
            total_tokens = trim.get("total_tokens", 0)

        comp_pct = [
            round(skills / total_tokens * 100) if total_tokens else 0,
            round(memory / total_tokens * 100) if total_tokens else 0,
            round(identity / total_tokens * 100) if total_tokens else 0,
            round(tools / total_tokens * 100) if total_tokens else 0,
            round(guidance / total_tokens * 100) if total_tokens else 0,
        ]

        # Drift
        max_drift = abs(agent_drift.get("delta_pct", 0)) if agent_drift else 0

        # Data quality — check if OTEL data exists in token_logs
        dq = "acc" if has_otel.get(name) else "est"
        dq_dot_cls = "acc" if dq == "acc" else "est"
        dq_title = "Accurate (otel + watch)" if dq == "acc" else "Estimated (watch only)"

        # Error badge
        err_badge = f'<span class="errbadge">{errors_24h}</span>' if errors_24h > 0 else ""

        dot_cls = cls if cls != "unknown" else "gray"
        card_cls = "open" + (" crit" if cls == "critical" else " warn" if cls == "warning" else "")
        drift_up = max_drift > 0
        drift_dir = "up" if drift_up else ""
        drift_str = f'{"+ " if drift_up else ""}{max_drift:.0f}%' if max_drift > 0 else "0%"

        # Pulse mini (6 dots)
        pulse_dots = ""
        recent_pulses = pulses_by_agent.get(name, [])[:6]
        for p in recent_pulses:
            ps = p.get("status", "alive")
            pc = "a" if ps == "alive" else "e" if ps == "error" else "d"
            pulse_dots += f'<i class="{pc}"></i>'

        # Health panel — 6 pulse bars with latency
        hp_bars = ""
        max_lat = max((p.get("latency_ms", 0) for p in recent_pulses[:6]), default=1)
        if max_lat == 0:
            max_lat = 1
        alive_count = 0
        error_count = 0
        dead_count = 0
        for p in recent_pulses[:6]:
            ps = p.get("status", "alive")
            lat = p.get("latency_ms", 0)
            if ps == "alive":
                alive_count += 1
            elif ps == "error":
                error_count += 1
            else:
                dead_count += 1
            # Bar height: dead=6px, otherwise proportional to latency
            h = 6 if ps == "dead" else max(10, (lat / max_lat) * 36)
            # Label: dead shows '—', otherwise show latency
            lbl = "—" if ps == "dead" else f"{lat:.0f}" if lat < 1000 else f"{lat / 1000:.1f}s"
            hp_bars += f'<div class="p"><div class="bar {ps}" style="height:{h:.0f}px"></div><div class="lat">{lbl}</div></div>'

        # Confidence badge

        # Token bar segments
        comp_labels = ["skills", "memory", "identity", "tools", "guidance"]
        tokbar_segs = ""
        for i, cls_name in enumerate(comp_labels):
            if i < len(comp_pct) and comp_pct[i] > 0:
                tokbar_segs += f'<i class="{cls_name}" style="width:{comp_pct[i]}%"></i>'

        # Framework - handle potential missing keys safely
        framework = s.get("agent_framework") or s.get("framework") or "Hermes"
        fw_badge = f'<span class="fw-badge">{framework}</span>'

        # ── Confidence badge (FP/FN risk) ──
        # lazy import to avoid circular with server.py
        from observeco.dashboard.server import _compute_confidence
        conf = _compute_confidence(
            s.get("status", ""),
            recent_pulses,
            agent_errors,
            circuit_state or {},
            s.get("timestamp", 0),
            now,
        )
        fp_icon = {"low": "✅", "moderate": "⚠️", "high": "❌"}.get(conf["fp_risk"], "⚠️")
        fn_icon = {"low": "✅", "moderate": "⚠️", "high": "❌"}.get(conf["fn_risk"], "⚠️")
        fp_label = conf["fp_risk"].capitalize()
        fn_label = conf["fn_risk"].capitalize()
        level_label = conf["level"].capitalize()
        level_emoji = {"high": "🟢", "medium": "🟡", "low": "⚪"}.get(conf["level"], "⚪")
        conf_badge = f"""<div class="conf-badge" style="font-size:10px;color:#94a3b8;margin-top:2px;display:flex;gap:8px;flex-wrap:wrap;">
            <span title="Confidence: {level_label} — {conf['sources_agree']}">{level_emoji} {level_label}</span>
            <span title="False positive risk: {fp_label}">{fp_icon} FP {fp_label}</span>
            <span title="False negative risk: {fn_label}">{fn_icon} FN {fn_label}</span>
        </div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">{conf['recommendation']}</div>"""

        # Memory debt + cost from garden data
        gardens = gardens_by_agent.get(name, [])
        debt = 0
        dups_found = 0
        contra_found = 0
        has_garden = bool(gardens)
        if gardens:
            debt = int(gardens[0].get("memory_debt_score", 0))
            dups_found = int(gardens[0].get("duplicates_found", 0))
            contra_found = int(gardens[0].get("contradictions_found", 0))
        debt_str = f"debt {debt}" if debt > 0 else "debt —"
        # Memory row display values (honest when no garden scan has run)
        mem_val = f"{debt}/100" if has_garden else "—"
        if not has_garden:
            mem_sub = "no scan"
        elif debt == 0:
            mem_sub = "clean"
        else:
            mem_sub = f"{dups_found} dup · {contra_found} con"

        # State word for health row
        state_word = "down" if cls == "critical" else "warning" if cls == "warning" else "running" if cls == "healthy" else "unknown"

        # Group key: agent vs service
        is_agent = name_type.get(name, "service") == "agent"
        group_key = "Agents" if is_agent else "Services"

        # Quality BM row only for agents
        qb_row = ""
        if is_agent:
            qb_row = f"""<div class="crow tappable" onclick="toggleQbDetail('{_html_escape(name)}'); return false;" tabindex="0" role="button" aria-label="View {name} quality benchmark" data-qb="{_html_escape(name)}">
                <span class="row-label">QUALITY BENCHMARK</span>
                {_canary_row(name, canary_latest.get(name), name in canary_running)}
                <span class="row-sub">{_canary_pass_sub(name, canary_latest.get(name), name in canary_running, quality_drift.get(name))} <span class="row-chev">▼</span></span>
            </div>
            <div class="qb-expanded" id="qb-detail-{_html_escape(name)}">
                <div style="text-align:center;color:var(--fg-3);font-size:11px;padding:8px;">
                    <span class="spinner"></span> Loading per-category breakdown...
                </div>
            </div>"""

        # Brain + Memory rows only for agents
        agent_rows = ""
        if is_agent:
            agent_rows = f"""<div class="crow tappable" onclick="htmx.ajax('GET', '/api/agent/{_html_escape(name)}/profile?focus=usage', {{target: '#modalContainer', swap: 'innerHTML'}});setTimeout(function(){{var d=document.getElementById('techDrawer');if(d){{d.classList.add('open');var c=d.querySelector('.chev');if(c)c.textContent='▼';var t=document.getElementById('drawer-usage');if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}})}}}},200)" tabindex="0" role="button" aria-label="View {name} profile">
                <span class="row-label">Brain</span>
                <span class="row-val">{_fmt_tokens(total_tokens) if has_token_data else '—'}</span>
                <span class="row-sub">{debt_str} <span class="row-chev">▸</span></span>
            </div>
            <div class="crow tappable" onclick="htmx.ajax('GET', '/api/agent/{_html_escape(name)}/profile?focus=memory', {{target: '#modalContainer', swap: 'innerHTML'}});setTimeout(function(){{var d=document.getElementById('techDrawer');if(d){{d.classList.add('open');var c=d.querySelector('.chev');if(c)c.textContent='▼';var t=document.getElementById('drawer-memory');if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}})}}}},200)" tabindex="0" role="button" aria-label="View {name} profile">
                <span class="row-label">Memory<span class="glossary-hint" onclick="event.stopPropagation();showGlossary('memory-garden', event)" style="font-size:10px;cursor:pointer;background:#334155;border-radius:3px;padding:0 5px;color:#94a3b8;font-weight:400;margin-left:3px;">?</span></span>
                <span class="row-val" style="color:{'var(--accent)' if debt < 20 else 'var(--warn)' if debt < 50 else 'var(--danger)'}">{mem_val}</span>
                <span class="row-sub">{mem_sub} <span class="row-chev">▸</span></span>
            </div>"""
        groups.setdefault(group_key, []).append(f"""<article class="card {card_cls}">
    <div class="card-collapsed" data-toggle role="button" tabindex="0" aria-label="Toggle {name} details">
        <span class="dot {dot_cls}"></span>
        <span class="card-name">{_html_escape(name)}</span>
        {err_badge}
        <div class="collapsed-meta">
            <span class="collapsed-tok">{_fmt_tokens(total_tokens) if has_token_data else '—'}<span class="{drift_dir}"> {drift_str}</span></span>
            <span class="dqdot {dq_dot_cls}" title="{dq_title}"></span>
            <span class="collapsed-conf" title="Confidence: {level_label} (FP {fp_label} / FN {fn_label})">{level_emoji}{fp_icon}{fn_icon}</span>
            <span class="chev">▸</span>
        </div>
    </div>
    <div class="card-detail">
        <div class="rows">
            {qb_row}
            <div class="crow tappable" onclick="htmx.ajax('GET', '/api/agent/{_html_escape(name)}/profile?focus=reliability', {{target: '#modalContainer', swap: 'innerHTML'}});setTimeout(function(){{var d=document.getElementById('techDrawer');if(d){{d.classList.add('open');var c=d.querySelector('.chev');if(c)c.textContent='▼';var t=document.getElementById('drawer-reliability');if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}})}}}},200)" tabindex="0" role="button" aria-label="View {name} profile">
                <span class="row-label">Health</span>
                <div class="pulse-mini">{pulse_dots}</div>
                <span class="row-sub">{_fmt_ts(last_ts) if last_ts > 0 else '—'} · {state_word} <span class="row-chev">▸</span></span>
            </div>
            <div class="crow tappable" onclick="htmx.ajax('GET', '/api/agent/{_html_escape(name)}/profile?focus=reliability', {{target: '#modalContainer', swap: 'innerHTML'}});setTimeout(function(){{var d=document.getElementById('techDrawer');if(d){{d.classList.add('open');var c=d.querySelector('.chev');if(c)c.textContent='▼';var t=document.getElementById('drawer-reliability');if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}})}}}},200)" tabindex="0" role="button" aria-label="View {name} profile">
                <span class="row-label">Guard</span>
                <span class="row-val" style="color:{circuit_color}">{circuit_text}</span>
                <span class="row-sub">{fw_badge} <span class="row-chev">▸</span></span>
            </div>
            <div class="crow" style="cursor:default;">
                <span class="row-label">Confidence</span>
                {conf_badge}
            </div>
            <div class="crow tappable" onclick="htmx.ajax('GET', '/api/agent/{_html_escape(name)}/profile?focus=reliability', {{target: '#modalContainer', swap: 'innerHTML'}});setTimeout(function(){{var d=document.getElementById('techDrawer');if(d){{d.classList.add('open');var c=d.querySelector('.chev');if(c)c.textContent='▼';var t=document.getElementById('drawer-reliability');if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}})}}}},200)" tabindex="0" role="button" aria-label="View {name} profile">
                <span class="row-label">Errors</span>
                <span class="row-val" style="color:{'var(--status-critical)' if errors_24h > 0 else 'var(--fg-2)'}">{errors_24h}</span>
                <span class="row-sub">{f'{_html_escape(last_err_msg)} · {last_err_ts}' if last_err_msg else 'none 24h'} <span class="row-chev">▸</span></span>
            </div>
            {agent_rows}
        </div>
        {_so_what_insights(name, cls, [agent_drift] if agent_drift else [], [trim] if trim else [], agent_errors, total_tokens)}
    </div>
</article>""")

    total_agents = len(sorted_names)

    # Build grouped grid: section headers only when >1 group
    # ponytail: groups sorted alphabetically by key. If custom sort order needed later,
    # pass an ordered list of keys instead of sorted().
    if len(groups) <= 1:
        grid_html = "\n".join(next(iter(groups.values())))
    else:
        sections = []
        for gk in sorted(groups):
            cards = groups[gk]
            sections.append(
                f'<div class="section-h"><h2>{_html_escape(gk)}</h2>'
                f'<span class="count mono">{len(cards)}</span></div>'
                f'{"".join(cards)}'
            )
        grid_html = "\n".join(sections)

    # Build hint for collapsed/expanded state
    hint = "▸ click a card to expand"

    # Pagination bar
    pagination = ""
    if total_pages > 1:
        page_label = f'<span style="color:#64748b;font-size:11px;">page {page}/{total_pages}</span>'
        p_parts = []
        for p in range(1, total_pages + 1):
            active = 'active' if p == page else ''
            p_parts.append(
                f'<button class="paginate-btn {active}" data-page="{p}" '
                f'onclick="htmx.ajax(\'GET\', \'/api/fleet/agents?page={p}\', '
                f'{{target:\'#fleetGrid\', swap:\'innerHTML\'}});return false;">{p}</button>'
            )
        pagination = (
            f'<div class="pagination-bar" style="display:flex;justify-content:center;gap:4px;'
            f'padding:12px 0;align-items:center;">'
            f'{page_label}'
        )
        # Prev button
        if page > 1:
            pagination += (
                f'<button class="paginate-btn" data-page="{page - 1}" '
                f'onclick="htmx.ajax(\'GET\', \'/api/fleet/agents?page={page - 1}\', '
                f'{{target:\'#fleetGrid\', swap:\'innerHTML\'}});return false;">◀ Prev</button>'
            )
        pagination += "".join(p_parts)
        # Next button
        if page < total_pages:
            pagination += (
                f'<button class="paginate-btn" data-page="{page + 1}" '
                f'onclick="htmx.ajax(\'GET\', \'/api/fleet/agents?page={page + 1}\', '
                f'{{target:\'#fleetGrid\', swap:\'innerHTML\'}});return false;">Next ▶</button>'
            )
        pagination += '</div>'

    return HTMLResponse(f"""<div class="section-h" id="fleetSectionHeader" hx-swap-oob="true"><h2>Fleet</h2><span class="count">{total_agents} agents</span><span class="hint">{hint}</span><span id="fleetUpdated" style="font-size:12px;color:#64748b;margin-left:8px;">{time.strftime('Updated %H:%M:%S', time.localtime(now))}</span></div>
{grid_html}
{pagination}""")
