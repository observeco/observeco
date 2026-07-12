"""Agent Detail Modal — 5-tab drill-down per agent (Health/Guard/Errors/Tokens/Memory).

Design: Claude Design Agent Detail Modal (v2) — 367 lines of HTML.
Supports all 4 states: loading → data → empty → error.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

from observeco.db import Database

router = APIRouter(prefix="/api/fleet", tags=["fleet"])
db = Database()


def _fmt_ts(ts: int) -> str:
    now = int(time.time())
    delta = now - ts
    if delta < 60: return f"{delta}s ago"
    elif delta < 3600: return f"{delta // 60}m ago"
    elif delta < 86400: return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"

def _fmt_tok(n: int) -> str:
    if n >= 1000: return f"{n / 1000:.1f}K"
    return str(n)

def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


@router.get("/modal/{agent_name}", response_class=HTMLResponse)
async def agent_modal(agent_name: str, tab: str = "health"):
    """Agent Detail Modal with 5-tab drill-down. Returns full HTML modal.
    GET /api/fleet/modal/raven?tab=health
    """
    name = agent_name
    now = int(time.time())

    try:
        agents = db.get_agents()
    except Exception:
        return HTMLResponse(f"""<div class="scrim"><div class="modal">
    <div class="m-head">
        <span class="m-name" style="color:var(--fg-3)">Error</span>
        <span class="m-close" onclick="this.closest('.scrim').remove()">✕</span>
    </div>
    <div class="m-body">
        <div class="state-msg err">
            <div class="ico">⚠</div>
            <h3>Agent data unavailable</h3>
            <p>The database is not responding. Start the watch daemon to resume monitoring.</p>
            <span class="cmd">observeco start</span>
        </div>
    </div>
</div></div>""")

    known = {a["agent_name"]: a for a in agents}
    is_agent = known.get(name, {}).get("class") == "agent"

    if name not in known:
        return HTMLResponse(f"""<div class="scrim"><div class="modal">
    <div class="m-head">
        <span class="m-name" style="color:var(--fg-3)">Not found</span>
        <span class="m-close" onclick="this.closest('.scrim').remove()">✕</span>
    </div>
    <div class="m-body">
        <div class="state-msg"><div class="ico">🔍</div><h3>Agent not found</h3><p>No agent named "{_html_escape(name)}" is registered.</p></div>
    </div>
</div></div>""")

    pulses = db.get_recent_pulses(agent_name=name, limit=48)
    errors_raw = db.get_errors(agent_name=name, limit=50)
    circuit_list = db.get_circuit_breakers()
    circuit = next((c for c in circuit_list if c.get("agent_name") == name), {})
    trims = db.get_trims(agent_name=name, limit=30)
    drift = db.get_drift(agent_name=name)
    garden = []
    try:
        garden = db.get_recent_garden(agent_name=name, limit=10) if hasattr(db, 'get_recent_garden') else []
    except Exception:
        logger.exception("failed to load garden for %s", name)

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

    framework = known[name].get("framework", "Hermes")
    last_seen = _fmt_ts(last_ts) if last_ts else "never"

    # Error count
    errors_24h = len([e for e in errors_raw if e.get("timestamp",0) > now - 86400])

    # Build tab HTML
    tabs_html = ""
    panes_html = ""

    # Health tab
    pulse_dots = ""
    for i in range(48):
        p = pulses[i] if i < len(pulses) else None
        c = "a"
        if p:
            ps = p.get("status","")
            c = "d" if ps == "dead" else "e" if ps == "error" else "a"
            if c == "d": c = "d"
        else:
            c = "n"
        pulse_dots += f'<i class="{c}"></i>'

    lat_bars = ""
    if pulses:
        max_lat = max((p.get("latency_ms",0) for p in pulses[:24]), default=1)
        for p in pulses[:24]:
            lat = p.get("latency_ms",0)
            h = max(2, int(lat / max_lat * 44)) if max_lat else 2
            ps = p.get("status","")
            lc = "d" if ps=="dead" else "e" if ps=="error" else ""
            lat_bars += f'<i style="height:{h}px" class="{lc}"></i>'

    health_html = f"""<div class="panel-pane{' show' if tab == 'health' else ''}" data-pane="health">
    <div class="swc insight" style="margin-bottom:var(--space-4)">
        <span class="mark">i</span>
        <div class="body">
            <span class="lead">HEALTH STATUS</span>
            <div class="txt">Agent is <b>{cls}</b>. Last pulse <b>{last_seen}</b>. {status.capitalize()} — {_fmt_ts(pulses[0]['timestamp'])} ago.</div>
        </div>
    </div>
    <div class="sec-h">48-Pulse Timeline <span class="hint">last 24h · 30s cadence</span></div>
    <div class="pulse48">{pulse_dots}</div>
    <div class="pulse-axis"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>now</span></div>
    <div class="sec-h" style="margin-top:var(--space-4)">Latency (ms) per beat</div>
    <div class="latline">{lat_bars if lat_bars else '<span style="color:var(--fg-3);font-size:12px">No latency data</span>'}</div>
    <div class="sec-h">Latest Check</div>
    <table class="tbl">
        <tr><th class="mono">Time</th><th class="mono">Result</th><th class="mono r">Latency</th></tr>
        {''.join(f'<tr><td>{_fmt_short_ts(p["timestamp"])}</td><td><span style="color:{chr(103)+chr(114)+chr(101)+chr(101)+chr(110) if p.get("status")=="alive" else chr(114)+chr(101)+chr(100)}">{p.get("status","?")}</span></td><td class="mono r">{p.get("latency_ms",0)}ms</td></tr>' for p in pulses[:5])}
    </table>
</div>"""

    # Guard tab
    tripped = circuit.get("tripped", False)
    fails = circuit.get("failure_count", 0)
    guard_status = "STOPPED" if tripped else "OK" if fails == 0 else f"ARMED ({fails}/3)"
    guard_color = "var(--status-critical)" if tripped else "var(--accent)" if fails == 0 else "var(--warn)"

    failure_timeline = ""
    if errors_raw:
        for e in errors_raw[:5]:
            et = _fmt_short_ts(e.get("timestamp",now))
            em = e.get("error_message","")[:60]
            etp = e.get("error_type","")
            failure_timeline += f'<div class="ev trip"><span class="t">{et}</span><div class="m">🔴 <b>{_html_escape(etp)}</b> — {_html_escape(em)}</div></div>'

    guard_html = f"""<div class="panel-pane{' show' if tab == 'guard' else ''}" data-pane="guard">
    <div class="swc {"alert" if tripped else "insight"}">
        <span class="mark">{"!" if tripped else "✓"}</span>
        <div class="body">
            <span class="lead">{"STOPPED" if tripped else "OK" if fails == 0 else "ARMED"}</span>
            <div class="txt">Guard is <b style="color:{guard_color}">{guard_status}</b>. {"Agent stopped checking after 3 failures." if tripped else "Monitoring normally."}</div>
        </div>
    </div>
    <div class="sec-h">Failure Timeline</div>
    <div class="ftl">{failure_timeline if failure_timeline else '<div class="ev"><div class="m" style="color:var(--fg-3)">No failures recorded.</div></div>'}</div>
    <div class="sec-h">What the Guard Does</div>
    <div class="card2"><div class="kv"><span class="k">Failures before stop</span><span class="v">3</span></div><div class="kv"><span class="k">Cooldown period</span><span class="v">~4 hours</span></div><div class="kv"><span class="k">Auto-retry</span><span class="v">Yes</span></div></div>
</div>"""

    # Errors tab
    err_rows = ""
    for e in errors_raw[:10]:
        et = _fmt_short_ts(e.get("timestamp",now))
        em = e.get("error_message","")[:80]
        sev = e.get("severity","")
        sev_c = "var(--status-critical)" if sev in ("critical","error") else "var(--status-warning)" if sev == "warning" else "var(--fg-2)"
        err_rows += f'<tr><td class="mono">{et}</td><td><span style="color:{sev_c}">{sev.capitalize() if sev else "Error"}</span></td><td>{_html_escape(em)}</td></tr>'

    err_verdict = ""
    if errors_24h == 0:
        err_verdict = "No errors in last 24h — clean."
    elif errors_24h == 1:
        err_verdict = "1 error in 24h — likely transient."
    else:
        err_verdict = f"{errors_24h} errors in 24h — ongoing issue suspected."

    errors_html = f"""<div class="panel-pane{' show' if tab == 'errors' else ''}" data-pane="errors">
    <div class="swc {"alert" if errors_24h > 3 else "watch" if errors_24h > 0 else "insight"}">
        <span class="mark">{"!" if errors_24h > 3 else "⚠" if errors_24h > 0 else "i"}</span>
        <div class="body">
            <span class="lead">{"CRITICAL" if errors_24h > 3 else "WATCH" if errors_24h > 0 else "CLEAN"}</span>
            <div class="txt">{err_verdict}</div>
        </div>
    </div>
    <div class="sec-h">Recent Errors <span class="hint">last 24h · {errors_24h} events</span></div>
    <table class="tbl">{'<tr><th class="mono">Time</th><th class="mono">Severity</th><th>Message</th></tr>' + err_rows if err_rows else '<div style="color:var(--fg-3);padding:var(--space-3)">No errors in range.</div>'}</table>
</div>"""

    # Tokens tab
    trim = trims[0] if trims else {}
    t_identity = trim.get("identity_tokens",0)
    t_skills = trim.get("skills_tokens",0)
    t_memory = trim.get("memory_tokens",0)
    t_tools = trim.get("tools_tokens",0)
    t_guidance = trim.get("guidance_tokens",0)
    t_total = t_identity + t_skills + t_memory + t_tools + t_guidance
    if not t_total: t_total = trim.get("total_tokens",0)

    comps = [
        ("skills", t_skills, "bs"),
        ("memory", t_memory, "bm"),
        ("identity", t_identity, "bi"),
        ("tools", t_tools, "bt"),
        ("guidance", t_guidance, "bg"),
    ]
    comps.sort(key=lambda x: -x[1])

    comp_bars = ""
    for name_c, val, cls_c in comps:
        pct = round(val / t_total * 100) if t_total else 0
        comp_bars += f'<div class="cb"><span class="lab">{name_c}</span><div class="track"><i class="{cls_c}" style="width:{pct}%"></i></div><span class="val">{_fmt_tok(val)} ({pct}%)</span></div>'

    tokens_html = f"""<div class="panel-pane{' show' if tab == 'tokens' else ''}" data-pane="tokens">
    <div class="swc {"alert" if t_total > 30000 else "insight"}">
        <span class="mark">{"!" if t_total > 30000 else "i"}</span>
        <div class="body">
            <span class="lead">{'BLOAT' if t_total > 30000 else 'OK'}</span>
            <div class="txt">Total: <span class="num">{_fmt_tok(t_total)}</span> tokens. {('Skills dominates at ' + str(comps[0][1]*100//t_total) + '%' + ' — compress target') if t_total > 30000 else 'Within normal range.'}</div>
        </div>
    </div>
    <div class="sec-h">Component Breakdown <span class="hint">{_fmt_tok(t_total)} total</span></div>
    <div class="compbar">{comp_bars}</div>
    <div class="sec-h">Drift <span class="hint">7-day · {'+'+str(round(max((d.get('delta_pct',0) for d in drift), default=0),1))+'%' if drift else 'No data'}</span></div>
    <div class="card2">
        {' '.join(f'<div class="kv"><span class="k">{d["component"]}</span><span class="v" style="color:{"var(--status-critical)" if d.get("breached") else "var(--fg)"}">{d.get("delta_pct","0%"):+.1f}%</span></div>' for d in drift[:5] if d.get("component")) if drift else '<span style="color:var(--fg-3)">No drift data for this period.</span>'}
    </div>
</div>"""

    # Memory tab
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

    debt_color = "var(--accent)" if debt < 30 else "var(--warn)" if debt < 60 else "var(--status-critical)"

    memory_html = f"""<div class="panel-pane{' show' if tab == 'memory' else ''}" data-pane="memory">
    <div class="debt-head">
        <div class="debt-score" style="color:{debt_color}">{debt}</div>
        <div class="debt-of">/ 100</div>
    </div>
    <div class="mstat">
        <div class="ms {"crit" if duplicates > 3 else ""}"><div class="n">{duplicates}</div><div class="l">Duplicates</div></div>
        <div class="ms {"crit" if contradictions > 0 else ""}"><div class="n">{contradictions}</div><div class="l">Contradictions</div></div>
        <div class="ms {"warn" if stale > 3 else ""}"><div class="n">{stale}</div><div class="l">Stale Entries</div></div>
    </div>
    {''.join(f'<div class="arch"><span class="ix">#1</span><div class="desc">Duplicate: <b>"{_html_escape(str(g.get("duplicates","")).split(",")[0])}"</b></div><span class="btn">View</span></div>') if duplicates > 0 else ''}
    {f'<div class="pro"><span class="pico">🧠</span><div><h4>Memory Garden Auto-Scan</h4><p>Schedule automatic garden scans to catch memory bloat before it grows.</p></div></div>' if debt < 60 else '<div style="margin-top:var(--space-3)"><div class="swc watch"><span class="mark">⚠</span><div class="body"><span class="lead">ATTENTION</span><div class="txt">Debt score <b>{debt}</b> — run a garden scan to resolve duplicates and contradictions.</div></div></div></div>'}
</div>"""

    # Efficiency pane — lazy-loaded via htmx (scans Hermes sessions)
    # ponytail: Hermes sessions have no agent_name field, so this lists recent
    # sessions globally, not filtered by the modal's agent. Phase 3 adds the filter.
    efficiency_html = f"""<div class="panel-pane{' show' if tab == 'efficiency' else ''}" data-pane="efficiency"
        hx-get="/api/efficiency/sessions"
        hx-trigger="load"
        hx-swap="innerHTML">
        <div class="state-msg"><div class="ico">⏳</div><p>Loading sessions…</p></div>
    </div>"""

    # Tab bar
    tokens_tab = f"<span class=\"m-tab{' active' if tab == 'tokens' else ''}\" data-tab=\"tokens\" onclick=\"switchModalTab('{name}','tokens',this)\">Tokens</span>" if is_agent else ""
    memory_tab = f"<span class=\"m-tab{' active' if tab == 'memory' else ''}\" data-tab=\"memory\" onclick=\"switchModalTab('{name}','memory',this)\">Memory</span>" if is_agent else ""
    efficiency_tab = f"<span class=\"m-tab{' active' if tab == 'efficiency' else ''}\" data-tab=\"efficiency\" onclick=\"switchModalTab('{name}','efficiency',this)\">Efficiency</span>" if is_agent else ""
    tabs_html = f"""
    <span class="m-tab{' active' if tab == 'health' else ''}" data-tab="health" onclick="switchModalTab('{name}','health',this)">Health</span>
    <span class="m-tab{' active' if tab == 'guard' else ''}" data-tab="guard" onclick="switchModalTab('{name}','guard',this)">Guard</span>
    <span class="m-tab{' active' if tab == 'errors' else ''}" data-tab="errors" onclick="switchModalTab('{name}','errors',this)">{'' if errors_24h == 0 else '⚠ '}Errors</span>
    {tokens_tab}
    {memory_tab}
    {efficiency_tab}
"""

    mhead_cls = cls
    badge_text = cls.upper()
    agent_fw = framework

    html = f"""<div class="scrim" id="modalScrim" onclick="if(event.target===this)this.remove()">
<div class="modal">
    <div class="m-head {mhead_cls}">
        <span class="m-dot {mhead_cls}"></span>
        <span class="m-name">{_html_escape(name)}</span>
        <span class="m-badge {mhead_cls}">{badge_text}</span>
        <span class="m-fw">{_html_escape(agent_fw)}</span>
        <span class="m-sub">{last_seen}</span>
        <span class="m-close" onclick="this.closest('.scrim').remove()">✕</span>
    </div>
    <div class="m-tabs" id="modalTabs">{tabs_html}</div>
    <div class="m-body" id="modalBody">
        {health_html}
        {guard_html}
        {errors_html}
        {tokens_html if is_agent else ""}
        {memory_html if is_agent else ""}
        {efficiency_html if is_agent else ""}
    </div>
</div>
</div>
<script>
function switchModalTab(name, tab, btn) {{
    document.querySelectorAll('#modalTabs .m-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('#modalBody .panel-pane').forEach(p => p.classList.remove('show'));
    var pane = document.querySelector('#modalBody .panel-pane[data-pane="'+tab+'"]');
    if (pane) pane.classList.add('show');
}}
</script>"""

    return HTMLResponse(html)


def _fmt_short_ts(ts: int) -> str:
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M")
