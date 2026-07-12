"""Token Analytics — Chart.js time-series, cost breakdown, cache efficiency, attribution gap.

Design: Claude Design Token Analytics (v2) — 268 lines.
Answers Q4: Where is the money going? (attribution)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from observeco.db import Database

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
db = Database()


def _fmt_tok(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1000: return f"{n/1000:.1f}K"
    return str(n)

def _fmt_dollar(c: float) -> str:
    if c >= 100: return f"${c:.0f}"
    if c >= 1: return f"${c:.2f}"
    return f"${c:.4f}"

def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


def loading_html() -> str:
    """Return skeleton loading state for token analytics."""
    return """<div id="analyticsContent">
<div class="page-title">
    <h1>Token Analytics</h1>
    <span class="sub mono">loading…</span>
    <div class="range">
        <button class="rbtn on">7d</button>
    </div>
</div>
<div class="skel" style="height:58px;margin-bottom:16px"></div>
<div class="grid2">
    <div class="panel">
        <div class="skel" style="width:120px;height:13px;margin-bottom:14px"></div>
        <div class="skel" style="height:240px"></div>
    </div>
    <div>
        <div class="panel" style="margin-bottom:var(--space-4)">
            <div class="skel" style="width:120px;height:13px;margin-bottom:14px"></div>
            <div class="skel" style="height:100px"></div>
        </div>
        <div class="panel">
            <div class="skel" style="width:120px;height:13px;margin-bottom:14px"></div>
            <div class="skel" style="height:80px"></div>
        </div>
    </div>
</div>
<div class="skel" style="width:160px;height:13px;margin:24px 0 12px"></div>
<div class="tblwrap" style="padding:0">
    <div class="skel" style="height:40px;margin:1px"></div>
    <div class="skel" style="height:40px;margin:1px"></div>
    <div class="skel" style="height:40px;margin:1px"></div>
    <div class="skel" style="height:40px;margin:1px"></div>
</div>
</div>"""


def error_html() -> str:
    """Return error state for token analytics."""
    return """<div id="analyticsContent">
    <div class="page-title"><h1>Token Analytics</h1><span class="sub">error</span></div>
    <div class="state-msg err">
        <div class="ico">⚠</div>
        <h3>Token data unavailable</h3>
        <p>The database is not responding. Token analytics require the watch daemon to be running.</p>
        <span class="cmd">observeco start</span>
    </div>
</div>"""


def empty_html() -> str:
    """Return empty state for token analytics."""
    return """<div id="analyticsContent">
    <div class="page-title"><h1>Token Analytics</h1><span class="sub">No data</span></div>
    <div class="state-msg"><div class="ico">📊</div><h3>No token data yet</h3><p>Token data appears after agents make LLM calls with the Hermes telemetry plugin enabled.</p></div>
</div>"""


@router.get("/tokens", response_class=HTMLResponse)
async def token_analytics(days: int = 7, agent: str = "__all__", hours: int = 0):
    """Token Analytics view — cost time-series, per-agent breakdown, cache efficiency.
    GET /api/analytics/tokens?days=7&agent=__all__  (or &hours=1 for the 1h view)
    """
    now = int(time.time())

    # Adaptive time bucketing: days mode (bucket by day) or hours mode (bucket by 5min / hour)
    # ponytail: 1h view needs sub-day resolution or it collapses to a single useless bar.
    # <=2h -> 5-min buckets (12 pts); >2h -> hourly buckets. Upgrade: pass bucket size from UI.
    if hours > 0:
        if hours <= 2:
            bucket_sec = 300
            label_fmt = "%H:%M"
        else:
            bucket_sec = 3600
            label_fmt = "%H:00"
        n_buckets = max(1, -(-hours * 3600 // bucket_sec))  # ceil division
    else:
        bucket_sec = 86400
        label_fmt = "%m/%d"
        n_buckets = days
    since = now - n_buckets * bucket_sec
    range_label = f"{hours}h" if hours else f"{days}d"

    # Get all token logs
    all_logs = []
    try:
        conn = db._get_conn()
        cur = conn.execute(
            "SELECT agent_name, total_tokens, input_tokens, output_tokens, "
            "cache_creation_tokens, cache_read_tokens, model, provider, "
            "cost, identity_tokens, skills_tokens, memory_tokens, "
            "tools_tokens, guidance_tokens, source, recorded_at, anomaly_score "
            "FROM token_logs WHERE recorded_at >= ? ORDER BY recorded_at",
            (since,)
        )
        all_logs = [dict(r) for r in cur.fetchall()]
    except Exception:
        # Error state — DB unavailable
        return HTMLResponse(f"""<div id="analyticsContent" hx-swap-oob="true">
    <div class="page-title"><h1>Token Analytics</h1><span class="sub">error</span></div>
    <div class="state-msg err">
        <div class="ico">⚠</div>
        <h3>Token data unavailable</h3>
        <p>The database is not responding. Token analytics require the watch daemon to be running.</p>
        <span class="cmd">observeco start</span>
    </div>
</div>""")

    agents_cfg = db.get_agents()
    agent_names = [a["agent_name"] for a in agents_cfg]

    # If no token data, show empty state
    if not all_logs:
        return HTMLResponse(f"""<div id="analyticsContent" hx-swap-oob="true">
    <div class="page-title"><h1>Token Analytics</h1><span class="sub">No data</span></div>
    <div class="state-msg"><div class="ico">📊</div><h3>No token data yet</h3><p>Token data appears after agents make LLM calls with the Hermes telemetry plugin enabled.</p></div>
</div>""")

    # Apply agent filter (v0.2.0 dropdown)
    filtered_logs = [
        log for log in all_logs
        if agent == "__all__" or log.get("agent_name") == agent
    ]
    if filtered_logs:
        all_logs = filtered_logs

    # Per-agent aggregation
    agent_data = {}
    total_cost = 0
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_create = 0
    total_attributed = 0
    total_unattributed = 0
    agents_with_data = set()

    # Buckets derived from actual row timestamps (integer-divided epoch), NOT from
    # since//bucket_sec — anchoring to `since` drops "today so far" and shows the
    # wrong calendar day for sub-day/daily windows. Same approach as tracking/token_analytics._bucket_start.
    day_buckets = {}

    for log in all_logs:
        aname = log.get("agent_name", "unknown")
        if aname not in agent_data:
            agent_data[aname] = {
                "cost": 0, "tokens": 0, "input": 0, "output": 0,
                "cache_read": 0, "cache_create": 0, "model": "",
                "provider": "", "source": log.get("source", "unknown"),
                "count": 0,
                "identity": 0, "skills": 0, "memory": 0, "tools": 0, "guidance": 0,
            }
        d = agent_data[aname]
        d["cost"] += log.get("cost", 0) or 0
        d["tokens"] += log.get("total_tokens", 0) or 0
        d["input"] += log.get("input_tokens", 0) or 0
        d["output"] += log.get("output_tokens", 0) or 0
        d["cache_read"] += log.get("cache_read_tokens", 0) or 0
        d["cache_create"] += log.get("cache_creation_tokens", 0) or 0
        d["identity"] += log.get("identity_tokens", 0) or 0
        d["skills"] += log.get("skills_tokens", 0) or 0
        d["memory"] += log.get("memory_tokens", 0) or 0
        d["tools"] += log.get("tools_tokens", 0) or 0
        d["guidance"] += log.get("guidance_tokens", 0) or 0
        d["model"] = log.get("model", d["model"]) or d["model"]
        d["provider"] = log.get("provider", d["provider"]) or d["provider"]
        d["count"] += 1
        agents_with_data.add(aname)

        total_cost += log.get("cost", 0) or 0
        total_input += log.get("input_tokens", 0) or 0
        total_output += log.get("output_tokens", 0) or 0
        total_cache_read += log.get("cache_read_tokens", 0) or 0
        total_cache_create += log.get("cache_creation_tokens", 0) or 0

        if log.get("source") == "otel":
            total_attributed += log.get("total_tokens", 0) or 0
        else:
            total_unattributed += log.get("total_tokens", 0) or 0

        # Bucket by integer-divided epoch of the row's own timestamp (true calendar alignment)
        bk = (log.get("recorded_at", 0) // bucket_sec) * bucket_sec
        if bk not in day_buckets:
            day_buckets[bk] = {"cost": 0, "total": 0, "input": 0, "output": 0, "cache": 0, "cache_create": 0, "est": 0, "count": 0}
        day_buckets[bk]["cost"] += log.get("cost", 0) or 0
        day_buckets[bk]["total"] += log.get("total_tokens", 0) or 0
        day_buckets[bk]["input"] += log.get("input_tokens", 0) or 0
        day_buckets[bk]["output"] += log.get("output_tokens", 0) or 0
        day_buckets[bk]["cache"] += log.get("cache_read_tokens", 0) or 0
        day_buckets[bk]["cache_create"] += log.get("cache_creation_tokens", 0) or 0
        day_buckets[bk]["count"] += 1
        # ponytail: 'est' = estimated (source != otel) tokens for this bucket, used to
        # shade estimate-vs-accurate. 'acc' is implied (total - est). Upgrade: track per-bucket acc too.
        if log.get("source") != "otel":
            day_buckets[bk]["est"] += (log.get("input_tokens", 0) or 0) + (log.get("output_tokens", 0) or 0)

    # Sort agents by cost descending
    sorted_agents = sorted(agent_data.items(), key=lambda x: -x[1]["cost"])

    # Attribution gap
    total_all = total_attributed + total_unattributed
    attr_pct = round(total_attributed / total_all * 100) if total_all else 0

    # Build chart data arrays (epoch keys, sorted ascending so the timeline reads left→right)
    sorted_keys = sorted(day_buckets.keys())
    labels = [datetime.fromtimestamp(k).strftime(label_fmt) for k in sorted_keys]
    cost_data = [round(day_buckets[k]["cost"], 4) for k in sorted_keys]
    input_data = [day_buckets[k]["input"] // 1000 for k in sorted_keys]
    output_data = [day_buckets[k]["output"] // 1000 for k in sorted_keys]
    cache_data = [day_buckets[k]["cache"] // 1000 for k in sorted_keys]
    est_data = [round(day_buckets[k]["est"] / 1000) for k in sorted_keys]
    # Total = authoritative total_tokens per bucket (K) — not input+output (which misses cache
    # and collapses to input-only for watch-estimated rows where output=0).
    total_data = [day_buckets[k]["total"] // 1000 for k in sorted_keys]
    # ── Efficiency time-series (v0.3.1 design: 4 ratio charts, each with benchmark bands) ──
    # All divide by max(count,1) so empty buckets → 0 (not divide-by-zero / inf).
    tokens_per_turn = [round(day_buckets[k]["total"] / max(day_buckets[k]["count"], 1)) for k in sorted_keys]
    output_input_ratio = [
        round(day_buckets[k]["output"] / max(day_buckets[k]["input"], 1), 2) for k in sorted_keys
    ]
    cache_rate_data = [
        round(day_buckets[k]["cache"] / max(day_buckets[k]["input"], 1) * 100, 1) for k in sorted_keys
    ]
    cost_per_turn = [round(day_buckets[k]["cost"] / max(day_buckets[k]["count"], 1), 5) for k in sorted_keys]
    # Double-count flag: Estimated is a proxy for total when real totals are missing.
    # When a bucket ALSO has real input/output/cache, Estimated + real overlap →
    # total_data already counts real tokens; stacking Estimated on top double-counts.
    # Mark buckets where est > 0 AND real input|output|cache > 0 (overlap case).
    double_count = [
        1 if (day_buckets[k]["est"] > 0 and
              (day_buckets[k]["input"] > 0 or day_buckets[k]["output"] > 0 or day_buckets[k]["cache"] > 0))
        else 0 for k in sorted_keys
    ]
    has_double_count = any(double_count)
    # Real fix for the double-count: where a bucket has real input/output/cache, the
    # Estimated stack is suppressed (set to 0) so it can't inflate the total on top of
    # real counts. Estimated is only shown in buckets with NO real breakdown (pure proxy).
    est_effective = [
        0 if (day_buckets[k]["input"] > 0 or day_buckets[k]["output"] > 0 or day_buckets[k]["cache"] > 0)
        else day_buckets[k]["est"]
        for k in sorted_keys
    ]
    suppressed_est = any(
        day_buckets[k]["est"] > 0 and est_effective[i] == 0
        for i, k in enumerate(sorted_keys)
    )
    # Stacked token total (K) the chart actually shows — uses est_effective so it never
    # double-counts. Header shows this, matching the visual stack.
    stacked_total_k = sum(
        day_buckets[k]["input"] + day_buckets[k]["output"] + day_buckets[k]["cache"] + est_effective[i]
        for i, k in enumerate(sorted_keys)
    ) // 1000
    # Target cost line for Chart 1 (Cost): mean daily cost of the window. ponytail: a real
    # budget threshold from billing config is the right source; mean-of-window is a sane
    # default until that exists. Upgrade: read OBSERVECO_TOKEN_BUDGET from config.
    target_cost = round(sum(cost_data) / max(len(cost_data), 1), 2)

    # Per-turn timeline (real total_tokens per call, time-ordered)
    timeline = sorted(
        [(log.get("recorded_at", 0), log.get("total_tokens", 0) or 0, log.get("anomaly_score", 0) or 0)
         for log in all_logs],
        key=lambda x: x[0],
    )
    turn_ts = [t for t, _, _ in timeline]
    turn_tokens = [n for _, n, _ in timeline]
    turn_anom = [bool(a) for _, _, a in timeline]
    # ponytail: 106K+ calls would OOM the browser with one <div> per call.
    # Cap displayed timeline to last 500; full count still shown in the header.
    # Upgrade path: bucket/aggregate if per-call resolution needed at scale.
    if len(turn_tokens) > 500:
        turn_ts = turn_ts[-500:]
        turn_tokens = turn_tokens[-500:]
        turn_anom = turn_anom[-500:]
    max_tok = max(turn_tokens) or 1
    # Data-quality flag: is this window 100% watch-estimated (no otel/sdk/proxy source)?
    window_has_real = any(
        (log.get("source") in ("otel", "sdk", "proxy")) for log in all_logs
    )
    estimated_only = (len(all_logs) > 0) and not window_has_real

    COMP_ORDER = [
        ("identity", "var(--token-identity)", "identity"),
        ("skills", "var(--token-skills)", "skills"),
        ("memory", "var(--token-memory)", "memory"),
        ("tools", "var(--token-tools)", "tools"),
        ("guidance", "var(--token-guidance)", "guidance"),
    ]
    fleet_comp = {k: sum(d[k] for _, d in sorted_agents) for k, _, _ in COMP_ORDER}
    comp_max = max(fleet_comp.values()) or 1
    comp_rows = ""
    for key, color, label in COMP_ORDER:
        val = fleet_comp[key]
        pct = round(val / comp_max * 100)
        tok = _fmt_tok(val)
        comp_rows += f"""<div class="comp-row">
    <span class="ag">{label}</span>
    <div class="comp-stack"><i class="ci" style="width:{pct}%;background:{color}"></i></div>
    <span class="mono" style="color:var(--fg-2);min-width:56px;text-align:right">{tok}</span>
</div>"""
    agent_rows = ""
    for aname, d in sorted_agents:
        dq_cls = "acc" if d["source"] == "otel" else "est"
        dq_label = "Acc" if d["source"] == "otel" else "Est"
        cache_rate = round(d["cache_read"] / max(d["cache_read"] + d["cache_create"], 1) * 100)
        cache_pct_cls = "var(--accent)" if cache_rate > 60 else "var(--warn)" if cache_rate > 30 else "var(--fg-3)"
        cost_str = _fmt_dollar(d["cost"])
        tok_str = _fmt_tok(d["tokens"])
        model_short = d["model"][:20] if d["model"] else "—"
        agent_rows += f"""<tr onclick="htmx.ajax('GET', '/api/fleet/modal/{_html_escape(aname)}', {{target:'#modalContainer', swap:'innerHTML'}})" style="cursor:pointer">
    <td><span class="ag">{_html_escape(aname)}</span></td>
    <td class="mono r">{cost_str}</td>
    <td class="mono r">{tok_str}</td>
    <td class="mono">{model_short}</td>
    <td><span class="dq {dq_cls}">{dq_label}</span></td>
    <td class="r">
        <div class="cache-cell">
            <span class="mono" style="color:{cache_pct_cls}">{cache_rate}%</span>
            <div class="cache-mini"><i class="read" style="width:{cache_rate}%"></i><i class="create" style="width:{100-cache_rate}%"></i></div>
        </div>
    </td>
</tr>"""

    # Cache per agent
    cache_rows = ""
    for aname, d in sorted_agents[:6]:
        cr = round(d["cache_read"] / max(d["cache_read"] + d["cache_create"], 1) * 100)
        cache_rows += f"""<div class="cache-row">
    <span class="ag">{_html_escape(aname)}</span>
    <div class="cache-track"><i class="read" style="width:{cr}%"></i><i class="create" style="width:{100-cr}%"></i></div>
    <span class="pct" style="color:{"var(--accent)" if cr>60 else "var(--warn)" if cr>30 else "var(--fg-3)"}">{cr}%</span>
</div>"""

    # Per-agent cache hit-rate chart data (obs-spec-020 §5.5): horizontal bars, one
    # per agent, sorted by rate ascending so the worst offenders sit at the top.
    # cache_rate definition matches the per-agent table cell (line 295) for consistency.
    cache_chart_agents = [a for a, _ in sorted_agents]
    cache_chart_rates = [
        round(d["cache_read"] / max(d["cache_read"] + d["cache_create"], 1) * 100)
        for _, d in sorted_agents
    ]


    # So What insight — Verdict Card (obs-spec-020 §5.3)
    top_agent = sorted_agents[0][0] if sorted_agents else ""
    top_cost = sorted_agents[0][1]["cost"] if sorted_agents else 0
    top_spender_pct = round(top_cost / max(total_cost, 1) * 100)
    turn_count = sum(d["count"] for _, d in sorted_agents)
    overall_cache_rate = round(total_cache_read / max(total_cache_read + total_cache_create, 1) * 100)
    # confidence badge = % of cost from accurate (otel/sdk/proxy) sources
    confidence_pct = attr_pct
    # one-sentence recommendation
    if confidence_pct < 50:
        rec = f"Only {confidence_pct}% of cost is accurately attributed — enable the telemetry plugin to close the gap."
    elif top_spender_pct > 50:
        rec = f"{_html_escape(top_agent)} alone is {top_spender_pct}% of spend — review its system-prompt size first."
    elif overall_cache_rate < 20:
        rec = f"Fleet cache hit rate is {overall_cache_rate}% — prompt caching is barely engaged; enable cache_control on stable prefixes."
    else:
        rec = "Token mix looks healthy — cost is well-distributed and caching is engaged."
    badge_cls = "good" if confidence_pct > 80 else "warn" if confidence_pct > 50 else "bad"
    top_cls = "bad" if top_spender_pct > 50 else "warn" if top_spender_pct > 25 else "good"
    cache_cls = "good" if overall_cache_rate > 20 else "warn" if overall_cache_rate > 5 else "bad"
    insight_html = f"""<div class="verdict-card" style="margin-bottom:var(--space-4)">
    <div class="vc-head"><span class="mark">$</span><span class="lead">SPEND VERDICT</span>
        <span class="vc-badge {badge_cls}">{confidence_pct}% accurate</span></div>
    <div class="vc-stats">
        <div class="vc-stat"><span class="vc-num">{_fmt_dollar(total_cost)}</span><span class="vc-lab">total cost · {turn_count} calls</span></div>
        <div class="vc-stat"><span class="vc-num {top_cls}">{top_spender_pct}%</span><span class="vc-lab">{_html_escape(top_agent)} top spender</span></div>
        <div class="vc-stat"><span class="vc-num {cache_cls}">{overall_cache_rate}%</span><span class="vc-lab">fleet cache hit</span></div>
        <div class="vc-stat"><span class="vc-num">{attr_pct}%</span><span class="vc-lab">attributed</span></div>
    </div>
    <div class="vc-rec">{rec}</div>
</div>"""

    total_tok = _fmt_tok(sum(d["tokens"] for _, d in sorted_agents))
    agent_count = len(sorted_agents)

    html = f"""<div id="analyticsContent" hx-swap-oob="true">
<div class="page-title">
    <h1>Token Analytics</h1>
    <span class="sub">{agent_count} agents · {_fmt_tok(total_all)} calls indexed</span>
    <select id="agentFilter" class="rbtn" style="margin-left:8px" onchange="htmx.ajax('GET', '/api/analytics/tokens?days={days}&hours={hours}&agent='+this.value, {{target:'#analyticsContent', swap:'innerHTML'}})">
        <option value="__all__"{' selected' if agent == '__all__' else ''}>All agents</option>
        {''.join(f'<option value="{_html_escape(a)}"{"" if agent != a else " selected"}>{_html_escape(a)}</option>' for a, _ in sorted_agents)}
    </select>
    <div class="range">
        <button class="rbtn {'on' if hours==1 and days==7 else ''}" onclick="htmx.ajax('GET', '/api/analytics/tokens?hours=1', {{target:'#analyticsContent', swap:'innerHTML'}})">1h</button>
        <button class="rbtn {'on' if days==1 and hours==0 else ''}" onclick="htmx.ajax('GET', '/api/analytics/tokens?days=1', {{target:'#analyticsContent', swap:'innerHTML'}})">24h</button>
        <button class="rbtn {'on' if days==7 and hours==0 else ''}" onclick="htmx.ajax('GET', '/api/analytics/tokens?days=7', {{target:'#analyticsContent', swap:'innerHTML'}})">7d</button>
        <button class="rbtn {'on' if days==30 and hours==0 else ''}" onclick="htmx.ajax('GET', '/api/analytics/tokens?days=30', {{target:'#analyticsContent', swap:'innerHTML'}})">30d</button>
    </div>
</div>

{insight_html}

<div class="tok4-grid">
    <div class="panel chart-card">
        <div class="cc-head"><h2>Token Composition</h2><span class="cc-val mono">{_fmt_tok(stacked_total_k * 1000)}</span><span class="cc-lab">input · output · cache · est</span></div>
        <div class="cc-legend">
            <span class="lg lg-input">Input</span><span class="lg lg-output">Output</span><span class="lg lg-cache">Cache reads</span><span class="lg lg-est">Estimated</span>
        </div>
        {('<div class="cc-note">Estimated is shown only where real component counts are absent; it is suppressed in periods that already have real input/output/cache to avoid double-counting the total.</div>') if suppressed_est else ''}
        <div class="chart-box"><canvas id="costChart"></canvas></div>
    </div>
    <div class="panel chart-card">
        <div class="cc-head"><h2>Tokens / Turn</h2><span class="cc-val mono">{_fmt_tok(sum(d['tokens'] for _, d in sorted_agents) // max(turn_count, 1))}</span><span class="cc-lab">lower better</span></div>
        <div class="chart-box"><canvas id="tptChart"></canvas></div>
    </div>
    <div class="panel chart-card">
        <div class="cc-head"><h2>Output / Input</h2><span class="cc-val mono">{round(total_output / max(total_input, 1), 2)}</span><span class="cc-lab">ratio · higher better</span></div>
        <div class="chart-box"><canvas id="oirChart"></canvas></div>
    </div>
    <div class="panel chart-card">
        <div class="cc-head"><h2>Cache Hit Rate</h2><span class="cc-val mono">{overall_cache_rate}%</span><span class="cc-lab">higher better</span></div>
        <div class="chart-box"><canvas id="cacheRateChart"></canvas></div>
    </div>
    <div class="panel chart-card">
        <div class="cc-head"><h2>Cost / Turn</h2><span class="cc-val mono">${_fmt_dollar(total_cost / max(turn_count, 1))}</span><span class="cc-lab">lower better</span></div>
        <div class="chart-box"><canvas id="cptChart"></canvas></div>
    </div>
</div>

<div class="section-h"><h2>Per-Agent Spend</h2><span class="count">{len(sorted_agents)} agents</span></div>
<div class="tblwrap">
    <table class="tbl">
        <tr><th>Agent</th><th class="r">Cost</th><th class="r">Tokens</th><th>Model</th><th>Data</th><th class="r">Cache</th></tr>
        {agent_rows}
    </table>
</div>

<div class="section-h"><h2>Component Composition</h2><span class="count">per agent average</span></div>
<div class="panel" style="margin-bottom:var(--space-6)">
    {comp_rows if comp_rows else '<span style="color:var(--fg-3);font-size:var(--text-sm)">No composition data</span>'}
    <div class="tokleg">
        <span><i class="ci"></i> identity</span>
        <span><i class="cs"></i> skills</span>
        <span><i class="cm"></i> memory</span>
        <span><i class="ct"></i> tools</span>
        <span><i class="cg"></i> guidance</span>
    </div>
</div>

<div class="section-h"><h2>Cache Efficiency</h2><span class="count">read vs create · hit rate by agent</span></div>
<div class="panel" style="margin-bottom:var(--space-6)">
    <div class="chart-box" style="height:max(180px, calc({len(sorted_agents)} * 26px))"><canvas id="cacheChart"></canvas></div>
    {cache_rows if cache_rows else '<span style="color:var(--fg-3);font-size:var(--text-sm)">No cache data</span>'}
</div>

<div class="section-h"><h2>Per-Turn Timeline</h2><span class="count">{len(turn_tokens)} calls{'' if len(turn_tokens) <= 500 else ' · showing last 500'}</span></div>
<div class="panel" style="margin-bottom:var(--space-6)">
    <p style="font-size:12px;color:var(--fg-3);margin-bottom:10px;">Each column = one LLM call. Height = total tokens. <span style="color:var(--danger)">Red columns</span> = anomaly flagged.</p>
    <div class="timeline-bar">
        {''.join(
            f'<div class="timeline-col{" anomaly" if a else ""}" style="height:max(4px, {t / max_tok * 100}%)" title="{_fmt_tok(t)} tok{" — anomaly" if a else ""}"></div>'
            for t, a in zip(turn_tokens, turn_anom)
        ) if turn_tokens else '<span style="color:var(--fg-3);font-size:var(--text-sm)">No call data</span>'}
    </div>
</div>

<script>
// ponytail: render is triggered HERE (not via htmx:afterSwap) to avoid the
// script-vs-afterSwap race. htmx DOES execute inline scripts in swapped content,
// so setting window._tokenChart then calling renderTokenChart() synchronously is
// race-free: data is fresh, canvas is in the DOM. The afterSwap listener in app.js
// is a no-op fallback now (target.id check fails for OOB swaps anyway).
window._tokenChart = {json.dumps({"labels": labels, "cost_data": cost_data, "total_data": total_data, "input_data": input_data, "output_data": output_data, "cache_data": cache_data, "est_data": est_effective, "suppressed_est": suppressed_est, "range_label": range_label})};
if (typeof renderTokenChart === 'function') renderTokenChart();
window._tptChart = {json.dumps({"labels": labels, "data": tokens_per_turn})};
if (typeof renderTptChart === 'function') renderTptChart();
window._oirChart = {json.dumps({"labels": labels, "data": output_input_ratio})};
if (typeof renderOirChart === 'function') renderOirChart();
window._cacheRateChart = {json.dumps({"labels": labels, "data": cache_rate_data})};
if (typeof renderCacheRateChart === 'function') renderCacheRateChart();
window._cptChart = {json.dumps({"labels": labels, "data": cost_per_turn})};
if (typeof renderCptChart === 'function') renderCptChart();
window._cacheChart = {json.dumps({"agents": cache_chart_agents, "rates": cache_chart_rates, "target": target_cost})};
if (typeof renderCacheChart === 'function') renderCacheChart();
</script>
</div>"""

    return HTMLResponse(html)
