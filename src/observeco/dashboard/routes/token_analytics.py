"""Token Analytics — Chart.js time-series, cost breakdown, cache efficiency, attribution gap.

Design: Claude Design Token Analytics (v2) — 268 lines.
Answers Q4: Where is the money going? (attribution)
"""

from __future__ import annotations

import json
import time
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from observeco.db import Database

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
db = Database()


def _fmt_tok(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return str(n)

def _fmt_dollar(c: float) -> str:
    if c >= 100:
        return f"${c:.0f}"
    if c >= 1:
        return f"${c:.2f}"
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


def _query_agents(conn, since: int, agent: str) -> list[dict]:
    """Per-agent aggregates via SQL GROUP BY (returns <50 rows)."""
    cur = conn.execute("""
        SELECT
            agent_name,
            COALESCE(SUM(cost), 0) as cost,
            COALESCE(SUM(total_tokens), 0) as tokens,
            COALESCE(SUM(input_tokens), 0) as input,
            COALESCE(SUM(output_tokens), 0) as output,
            COALESCE(SUM(cache_creation_tokens), 0) as cache_create,
            COALESCE(SUM(cache_read_tokens), 0) as cache_read,
            COALESCE(SUM(identity_tokens), 0) as identity,
            COALESCE(SUM(skills_tokens), 0) as skills,
            COALESCE(SUM(memory_tokens), 0) as memory,
            COALESCE(SUM(tools_tokens), 0) as tools,
            COALESCE(SUM(guidance_tokens), 0) as guidance,
            COUNT(*) as count,
            MAX(CASE WHEN source IN ('otel','sdk','proxy') THEN 1 ELSE 0 END) as has_accurate
        FROM token_logs WHERE recorded_at >= ?
        GROUP BY agent_name
        ORDER BY SUM(cost) DESC
    """, (since,))
    rows = [dict(r) for r in cur.fetchall()]
    if agent != "__all__":
        rows = [r for r in rows if r["agent_name"] == agent]
    # Patch model: most common model per agent (MIN() gives alphabetically first — wrong)
    latest = _query_most_common_model(conn, since, agent)
    for r in rows:
        r["model"] = latest.get(r["agent_name"], "")
    return rows


def _query_most_common_model(conn, since: int, agent: str) -> dict[str, str]:
    """Most frequently used model per agent (replaces MIN(model) which is wrong)."""
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT agent_name, model, COUNT(*) as cnt
        FROM token_logs
        WHERE recorded_at >= ? AND model IS NOT NULL AND model != '' {agent_clause}
        GROUP BY agent_name, model
        ORDER BY agent_name, cnt DESC
    """, params)
    result = {}
    seen = set()
    for r in cur.fetchall():
        if r["agent_name"] not in seen:
            seen.add(r["agent_name"])
            result[r["agent_name"]] = r["model"]
    return result


def _query_buckets(conn, since: int, bucket_sec: int, agent: str) -> list[dict]:
    """Time-bucket aggregates via SQL GROUP BY (returns <1000 rows)."""
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (bucket_sec, bucket_sec, since)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            (recorded_at / ?) * ? as bucket_start,
            COALESCE(SUM(cost), 0) as cost,
            COALESCE(SUM(total_tokens), 0) as total,
            COALESCE(SUM(input_tokens), 0) as input,
            COALESCE(SUM(output_tokens), 0) as output,
            COALESCE(SUM(cache_read_tokens), 0) as cache,
            COALESCE(SUM(cache_creation_tokens), 0) as cache_create,
            COALESCE(SUM(CASE WHEN source NOT IN ('otel','sdk','proxy') THEN input_tokens + output_tokens ELSE 0 END), 0) as est,
            COUNT(*) as count
        FROM token_logs WHERE recorded_at >= ? {agent_clause}
        GROUP BY bucket_start
        ORDER BY bucket_start
    """, params)
    return [dict(r) for r in cur.fetchall()]


def _query_timeline(conn, since: int, agent: str) -> list[tuple]:
    """Last 500 calls for the per-turn timeline bars.
    Samples across the full time range (not just the most recent 500 calls)
    so the timeline reflects the entire selected period.
    Anomaly = token count spike (>2x median) — marks real outliers.
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)

    # First, get total count in range to decide if we need to sample
    cur = conn.execute(f"""
        SELECT COUNT(*) as cnt FROM token_logs WHERE recorded_at >= ? {agent_clause}
    """, params)
    total = cur.fetchone()["cnt"]

    if total <= 500:
        # Small dataset — just return everything
        cur = conn.execute(f"""
            SELECT recorded_at, total_tokens
            FROM token_logs WHERE recorded_at >= ? {agent_clause}
            ORDER BY recorded_at ASC
        """, params)
        rows = [dict(r) for r in cur.fetchall()]
    else:
        # Large dataset — sample evenly across the full time range
        # Use a subquery with row_number to get evenly-spaced samples
        cur = conn.execute(f"""
            SELECT recorded_at, total_tokens FROM (
                SELECT recorded_at, total_tokens,
                    ROW_NUMBER() OVER (ORDER BY recorded_at) as rn,
                    COUNT(*) OVER () as cnt
                FROM token_logs WHERE recorded_at >= ? {agent_clause}
            ) WHERE rn % MAX(1, cnt / 500) = 0
            ORDER BY recorded_at ASC
            LIMIT 500
        """, params)
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return []

    # Statistical anomaly: token count > 2x the median
    token_vals = sorted([r["total_tokens"] or 0 for r in rows])
    median = token_vals[len(token_vals) // 2]
    threshold = median * 2

    timeline = [
        (r["recorded_at"], r["total_tokens"] or 0, (r["total_tokens"] or 0) > threshold)
        for r in rows
    ]
    return timeline


def _query_attribution(conn, since: int, agent: str) -> tuple[int, int]:
    """Attribution totals (attributed vs unattributed tokens)."""
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN source IN ('otel','sdk','proxy') THEN total_tokens ELSE 0 END), 0) as attributed,
            COALESCE(SUM(CASE WHEN source NOT IN ('otel','sdk','proxy') THEN total_tokens ELSE 0 END), 0) as unattributed
        FROM token_logs WHERE recorded_at >= ? {agent_clause}
    """, params)
    r = cur.fetchone()
    return (r["attributed"], r["unattributed"])


def _query_effective_spend(conn, since: int, agent: str) -> dict:
    """Corrected spend from v_token_effective (migration 71-73).

    Resolves the hermes/otel overlap at the token level (otel wins where
    nonzero, hermes backfills) so the headline no longer double-counts the
    same session from both sources. Returns three numbers that must NOT be
    summed blindly:

      measured   — effective joinable spend + clean orphans (overlap_suspect=0)
      suspect    — orphan spans flagged as duplicates of hermes rows (±12h
                   model+time); excluded from measured, shown as a footnote
      simulated  — watch rows (benchmark fleet, estimates by construction);
                   a separate traffic class, never summed with measured

    Cost is reported_cost from the winning source per session — audit-only
    claims, not a cross-source aggregate (see migration 71 docstring).
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE
                WHEN traffic_class = 'measured' THEN reported_cost
                WHEN traffic_class = 'measured_orphan' AND overlap_suspect = 0 THEN reported_cost
                ELSE 0 END), 0) as measured,
            COALESCE(SUM(CASE WHEN overlap_suspect = 1 THEN reported_cost ELSE 0 END), 0) as suspect
        FROM v_token_effective WHERE recorded_at >= ? {agent_clause}
    """, params)
    r = cur.fetchone()
    measured = float(r["measured"] or 0)
    suspect = float(r["suspect"] or 0)
    # Simulated = watch rows, entirely outside the precedence view.
    cur = conn.execute(f"""
        SELECT COALESCE(SUM(cost), 0) as sim
        FROM token_logs WHERE recorded_at >= ? AND source = 'watch' {agent_clause}
    """, params)
    sim = float(cur.fetchone()["sim"] or 0)
    return {"measured": measured, "suspect": suspect, "simulated": sim}


@router.get("/tokens", response_class=HTMLResponse)
async def token_analytics(days: int = 7, agent: str = "__all__", hours: int = 0):
    """Token Analytics view — cost time-series, per-agent breakdown, cache efficiency.
    GET /api/analytics/tokens?days=7&agent=__all__  (or &hours=1 for the 1h view)
    """
    now = int(time.time())

    # Adaptive time bucketing
    if hours > 0:
        if hours <= 2:
            bucket_sec = 300
            label_fmt = "%H:%M"
        else:
            bucket_sec = 3600
            label_fmt = "%H:00"
        n_buckets = max(1, -(-hours * 3600 // bucket_sec))
    else:
        bucket_sec = 86400
        label_fmt = "%m/%d"
        n_buckets = days
    since = now - n_buckets * bucket_sec
    range_label = f"{hours}h" if hours else f"{days}d"

    # ── SQL aggregation (3 queries instead of materializing all rows) ──
    try:
        conn = db._get_conn()

        # Query 1: Per-agent aggregates
        agent_rows = _query_agents(conn, since, agent)
        if not agent_rows:
            return HTMLResponse(empty_html())

        agent_data = {}
        total_cost = total_input = total_output = 0
        total_cache_read = total_cache_create = total_tokens = 0

        for r in agent_rows:
            aname = r["agent_name"]
            d = {
                "cost": r["cost"],
                "tokens": r["tokens"],
                "input": r["input"],
                "output": r["output"],
                "cache_read": r["cache_read"],
                "cache_create": r["cache_create"],
                "model": r["model"] or "",
                "provider": "",
                "source": "otel" if r["has_accurate"] else "watch",
                "count": r["count"],
                "identity": r["identity"],
                "skills": r["skills"],
                "memory": r["memory"],
                "tools": r["tools"],
                "guidance": r["guidance"],
            }
            agent_data[aname] = d
            total_cost += d["cost"]
            total_input += d["input"]
            total_output += d["output"]
            total_cache_read += d["cache_read"]
            total_cache_create += d["cache_create"]
            total_tokens += d["tokens"]

        # Query 2: Per-bucket time-series (pre-initialized for gaps)
        buckets_raw = _query_buckets(conn, since, bucket_sec, agent)

        first_bucket = (since // bucket_sec) * bucket_sec
        last_bucket = (now // bucket_sec) * bucket_sec
        day_buckets = {}
        bk = first_bucket
        while bk <= last_bucket:
            day_buckets[bk] = {"cost": 0, "total": 0, "input": 0, "output": 0, "cache": 0, "cache_create": 0, "est": 0, "count": 0}
            bk += bucket_sec
        for r in buckets_raw:
            bk = r["bucket_start"]
            day_buckets[bk] = {
                "cost": r["cost"],
                "total": r["total"],
                "input": r["input"],
                "output": r["output"],
                "cache": r["cache"],
                "cache_create": r["cache_create"],
                "est": r["est"],
                "count": r["count"],
            }

        # Attribution stats
        total_attributed, total_unattributed = _query_attribution(conn, since, agent)
        total_all = total_attributed + total_unattributed
        attr_pct = round(total_attributed / total_all * 100) if total_all else 0

        # Corrected spend (v_token_effective): measured headline, suspect
        # footnote, simulated (watch) kept separate — never summed together.
        eff = _query_effective_spend(conn, since, agent)

        # Query 3: Timeline (last 500 calls)
        timeline = _query_timeline(conn, since, agent)

    except Exception:
        return HTMLResponse(error_html())

    sorted_agents = sorted(agent_data.items(), key=lambda x: -x[1]["cost"])

    # Build chart data arrays
    sorted_keys = sorted(day_buckets.keys())
    labels = [datetime.fromtimestamp(k).strftime(label_fmt) for k in sorted_keys]
    cost_data = [round(day_buckets[k]["cost"], 4) for k in sorted_keys]
    input_data = [day_buckets[k]["input"] // 1000 for k in sorted_keys]
    output_data = [day_buckets[k]["output"] // 1000 for k in sorted_keys]
    cache_data = [day_buckets[k]["cache"] // 1000 for k in sorted_keys]
    total_data = [day_buckets[k]["total"] // 1000 for k in sorted_keys]

    def _eff(val_fn, k):
        return val_fn(k) if day_buckets[k]["count"] > 0 else None

    tokens_per_turn = [_eff(lambda k: round(day_buckets[k]["total"] / day_buckets[k]["count"]), k) for k in sorted_keys]
    output_input_ratio = [_eff(lambda k: round(day_buckets[k]["output"] / max(day_buckets[k]["input"], 1), 2), k) for k in sorted_keys]
    cache_rate_data = [_eff(lambda k: round(day_buckets[k]["cache"] / max(day_buckets[k]["cache"] + day_buckets[k]["cache_create"], 1) * 100, 1), k) for k in sorted_keys]
    cost_per_turn = [_eff(lambda k: round(day_buckets[k]["cost"] / day_buckets[k]["count"], 5), k) for k in sorted_keys]
    est_effective = [
        0 if (day_buckets[k]["input"] > 0 or day_buckets[k]["output"] > 0 or day_buckets[k]["cache"] > 0)
        else day_buckets[k]["est"]
        for k in sorted_keys
    ]
    suppressed_est = any(
        day_buckets[k]["est"] > 0 and est_effective[i] == 0
        for i, k in enumerate(sorted_keys)
    )
    stacked_total_k = sum(
        day_buckets[k]["input"] + day_buckets[k]["output"] + day_buckets[k]["cache"] + est_effective[i]
        for i, k in enumerate(sorted_keys)
    ) // 1000
    target_cost = round(sum(cost_data) / max(len(cost_data), 1), 2)

    # Timeline
    turn_ts = [t for t, _, _ in timeline]
    turn_tokens = [n for _, n, _ in timeline]
    turn_anom = [a for _, _, a in timeline]
    if len(turn_tokens) > 500:
        turn_ts = turn_ts[-500:]
        turn_tokens = turn_tokens[-500:]
        turn_anom = turn_anom[-500:]
    max_tok = max(turn_tokens) or 1

    # Component composition
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

    # Cache chart data
    cache_chart_agents = [a for a, _ in sorted_agents]
    cache_chart_rates = [
        round(d["cache_read"] / max(d["cache_read"] + d["cache_create"], 1) * 100)
        for _, d in sorted_agents
    ]

    # So What insight — computed against CORRECTED measured spend (not the
    # raw token_logs total, which double-counts hermes/otel overlap).
    measured_cost = eff["measured"]
    suspect_cost = eff["suspect"]
    simulated_cost = eff["simulated"]
    top_agent = sorted_agents[0][0] if sorted_agents else ""
    top_cost = sorted_agents[0][1]["cost"] if sorted_agents else 0
    # Top-spender % is relative to the raw source-level total (total_cost):
    # the per-agent table below shows raw rows, so its share must use the
    # same basis. Against corrected measured_cost it can exceed 100% (the
    # top agent's raw rows include both sides of the hermes/otel overlap).
    top_spender_pct = round(top_cost / max(total_cost, 1) * 100)
    turn_count = sum(d["count"] for _, d in sorted_agents)
    agents_with_cache = [d for _, d in sorted_agents if d["cache_read"] + d["cache_create"] > 0]
    cache_eligible_read = sum(d["cache_read"] for d in agents_with_cache)
    cache_eligible_create = sum(d["cache_create"] for d in agents_with_cache)
    overall_cache_rate = round(cache_eligible_read / max(cache_eligible_read + cache_eligible_create, 1) * 100)
    cache_coverage = f"{len(agents_with_cache)}/{len(sorted_agents)} agents"
    confidence_pct = attr_pct
    if confidence_pct < 50:
        rec = f"Only {confidence_pct}% of cost is accurately attributed — enable the telemetry plugin to close the gap."
    elif top_spender_pct > 50:
        rec = f"{_html_escape(top_agent)} alone is {top_spender_pct}% of spend — review its system-prompt size first."
    elif overall_cache_rate < 20:
        rec = f"Fleet cache hit rate is {overall_cache_rate}% — prompt caching is barely engaged; enable cache_control on stable prefixes."
    else:
        rec = "Token mix looks healthy — cost is well-distributed and caching is engaged."
    if suspect_cost > 0:
        rec += f" −{_fmt_dollar(suspect_cost)} suspected duplicate spans excluded from the headline."
    badge_cls = "good" if confidence_pct > 80 else "warn" if confidence_pct > 50 else "bad"
    top_cls = "bad" if top_spender_pct > 50 else "warn" if top_spender_pct > 25 else "good"
    cache_cls = "good" if overall_cache_rate > 20 else "warn" if overall_cache_rate > 5 else "bad"
    suspect_note = (
        f'<div class="vc-note">−{_fmt_dollar(suspect_cost)} suspected duplicate spans '
        f'excluded · {_fmt_dollar(simulated_cost)} simulated (watch, estimates)</div>'
        if suspect_cost > 0 else
        f'<div class="vc-note">{_fmt_dollar(simulated_cost)} simulated (watch, estimates) kept separate</div>'
    )
    insight_html = f"""<div class="verdict-card" style="margin-bottom:var(--space-4)">
    <div class="vc-head"><span class="mark">$</span><span class="lead">SPEND VERDICT</span>
        <span class="vc-badge {badge_cls}">{confidence_pct}% accurate</span></div>
    <div class="vc-stats">
        <div class="vc-stat"><span class="vc-num">{_fmt_dollar(measured_cost)}</span><span class="vc-lab">measured spend · {turn_count} calls</span></div>
        <div class="vc-stat"><span class="vc-num {top_cls}">{top_spender_pct}%</span><span class="vc-lab">{_html_escape(top_agent)} top spender</span></div>
        <div class="vc-stat"><span class="vc-num {cache_cls}">{overall_cache_rate}%</span><span class="vc-lab">fleet cache hit</span></div>
        <div class="vc-stat"><span class="vc-num">{attr_pct}%</span><span class="vc-lab">attributed</span></div>
    </div>
    <div class="vc-rec">{rec}</div>
    {suspect_note}
</div>"""

    agent_count = len(sorted_agents)

    html = f"""<div id="analyticsContent" hx-swap-oob="true">
<div class="page-title">
        <h1>Token Analytics</h1>
        <span class="sub">{agent_count} agents · {_fmt_tok(total_all)} tokens · {turn_count:,} calls</span>
        <select id="agentFilter" class="rbtn" style="margin-left:8px" onchange="var _t=new URLSearchParams(location.search).get('token')||''; htmx.ajax('GET', '/api/analytics/tokens?days={days}&hours={hours}&agent='+this.value+(_t?'&token='+_t:''), {{target:'#analyticsContent', swap:'innerHTML'}})">
            <option value="__all__"{' selected' if agent == '__all__' else ''}>All agents</option>
            {''.join(f'<option value="{_html_escape(a)}"{" selected" if agent == a else ""}>{_html_escape(a)}</option>' for a, _ in sorted_agents)}
        </select>
        <div class="range">
            <button class="rbtn {'on' if hours==1 and days==7 else ''}" onclick="var _t=new URLSearchParams(location.search).get('token')||''; htmx.ajax('GET', '/api/analytics/tokens?hours=1'+(_t?'&token='+_t:''), {{target:'#analyticsContent', swap:'innerHTML'}})">1h</button>
            <button class="rbtn {'on' if hours==24 and days==7 else ''}" onclick="var _t=new URLSearchParams(location.search).get('token')||''; htmx.ajax('GET', '/api/analytics/tokens?hours=24'+(_t?'&token='+_t:''), {{target:'#analyticsContent', swap:'innerHTML'}})">24h</button>
            <button class="rbtn {'on' if days==7 and hours==0 else ''}" onclick="var _t=new URLSearchParams(location.search).get('token')||''; htmx.ajax('GET', '/api/analytics/tokens?days=7'+(_t?'&token='+_t:''), {{target:'#analyticsContent', swap:'innerHTML'}})">7d</button>
            <button class="rbtn {'on' if days==30 and hours==0 else ''}" onclick="var _t=new URLSearchParams(location.search).get('token')||''; htmx.ajax('GET', '/api/analytics/tokens?days=30'+(_t?'&token='+_t:''), {{target:'#analyticsContent', swap:'innerHTML'}})">30d</button>
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
        <div class="cc-head"><h2>Output / Input</h2><span class="cc-val mono">{round(total_output / max(total_input, 1), 2)}</span><span class="cc-lab">ratio &#183; higher better</span></div>
        <div class="chart-box"><canvas id="oirChart"></canvas></div>
    </div>
    <div class="panel chart-card">
        <div class="cc-head"><h2>Cache Hit Rate</h2><span class="cc-val mono">{overall_cache_rate}%</span><span class="cc-lab">{cache_coverage} · higher better</span></div>
        <div class="chart-box"><canvas id="cacheRateChart"></canvas></div>
    </div>
    <div class="panel chart-card">
        <div class="cc-head"><h2>Cost / Turn</h2><span class="cc-val mono">${_fmt_dollar(total_cost / max(turn_count, 1))}</span><span class="cc-lab">lower better · source-level</span></div>
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
