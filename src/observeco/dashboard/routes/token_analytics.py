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


def _fmt_ms(ms: int) -> str:
    """Format milliseconds as a human duration (e.g. 5.1s, 820ms)."""
    if ms <= 0:
        return "—"
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{ms}ms"


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
    """Per-agent aggregates via SQL GROUP BY (returns <50 rows).

    Reads from v_token_effective (migration 71-73) — MEASURED rows only
    (traffic_class='measured' or clean orphans), precedence-resolved and
    deduplicated. Watch rows are excluded: they are synthetic benchmark
    estimates and would inflate the table (e.g. 7d raw table $101.51 vs
    $18.08 measured headline). Component fields (identity/skills/...)
    live only on raw otel rows, so they're fetched separately by
    _query_components; here they default to 0.
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            agent_name,
            COALESCE(SUM(reported_cost), 0) as cost,
            COALESCE(SUM(total_tokens), 0) as tokens,
            COALESCE(SUM(input_tokens), 0) as input,
            COALESCE(SUM(output_tokens), 0) as output,
            COALESCE(SUM(cache_creation_tokens), 0) as cache_create,
            COALESCE(SUM(cache_read_tokens), 0) as cache_read,
            MAX(CASE WHEN winning_source = 'otel' THEN 1 ELSE 0 END) as has_accurate,
            COUNT(*) as count
        FROM v_token_effective
        WHERE recorded_at >= ?
          AND (traffic_class = 'measured'
               OR (traffic_class = 'measured_orphan' AND overlap_suspect = 0))
          {agent_clause}
        GROUP BY agent_name
        ORDER BY SUM(reported_cost) DESC
    """, params)
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r.update({"identity": 0, "skills": 0, "memory": 0, "tools": 0, "guidance": 0})
    # Patch model: most common model per agent (MIN() gives alphabetically first — wrong)
    latest = _query_most_common_model(conn, since, agent)
    for r in rows:
        r["model"] = latest.get(r["agent_name"], "")
    return rows


def _query_components(conn, since: int, agent: str) -> dict[str, int]:
    """Component token composition from raw otel rows only.

    identity/skills/memory/tools/guidance exist only on otel spans; the
    precedence view doesn't carry them. Summed per agent across the fleet
    for the composition panel (otels only — the only source with a real
    breakdown; hermes bridge writes session aggregates, watch is synthetic).
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            COALESCE(SUM(identity_tokens), 0) as identity,
            COALESCE(SUM(skills_tokens), 0) as skills,
            COALESCE(SUM(memory_tokens), 0) as memory,
            COALESCE(SUM(tools_tokens), 0) as tools,
            COALESCE(SUM(guidance_tokens), 0) as guidance
        FROM token_logs
        WHERE recorded_at >= ? AND source = 'otel' {agent_clause}
    """, params)
    r = cur.fetchone()
    return {"identity": r["identity"] or 0, "skills": r["skills"] or 0,
            "memory": r["memory"] or 0, "tools": r["tools"] or 0,
            "guidance": r["guidance"] or 0}


def _query_simulated_agents(conn, since: int, agent: str) -> list[dict]:
    """Per-agent watch rows (simulated benchmark estimates).

    Kept as a SEPARATE section from the measured table — watch is a
    distinct population (100% output_tokens=0, burst-clustered, no
    session_id), never summed into measured spend.
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            agent_name,
            COALESCE(SUM(cost), 0) as cost,
            COALESCE(SUM(total_tokens), 0) as tokens,
            COALESCE(SUM(cache_read_tokens), 0) as cache_read,
            COALESCE(SUM(cache_creation_tokens), 0) as cache_create,
            COUNT(*) as count
        FROM token_logs
        WHERE recorded_at >= ? AND source = 'watch' {agent_clause}
        GROUP BY agent_name
        ORDER BY SUM(cost) DESC
    """, params)
    return [dict(r) for r in cur.fetchall()]


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
    """Time-bucket aggregates via SQL GROUP BY (returns <1000 rows).

    Reads from v_token_effective (migration 71-73) — MEASURED rows only
    (traffic_class='measured' or clean orphans), precedence-resolved and
    deduplicated. Watch rows are excluded entirely: they are synthetic
    benchmark estimates (output_tokens=0) and would pollute cache rate,
    output/input ratio, and tokens/turn with a 98% non-measured sample.
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (bucket_sec, bucket_sec, since)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            (recorded_at / ?) * ? as bucket_start,
            COALESCE(SUM(reported_cost), 0) as cost,
            COALESCE(SUM(total_tokens), 0) as total,
            COALESCE(SUM(input_tokens), 0) as input,
            COALESCE(SUM(output_tokens), 0) as output,
            COALESCE(SUM(cache_read_tokens), 0) as cache,
            COALESCE(SUM(cache_creation_tokens), 0) as cache_create,
            0 as est,
            COUNT(*) as count
        FROM v_token_effective
        WHERE recorded_at >= ?
          AND (traffic_class = 'measured'
               OR (traffic_class = 'measured_orphan' AND overlap_suspect = 0))
          {agent_clause}
        GROUP BY bucket_start
        ORDER BY bucket_start
    """, params)
    return [dict(r) for r in cur.fetchall()]


def _query_timeline(conn, since: int, agent: str) -> list[tuple]:
    """Last 500 calls for the per-turn timeline bars.
    Samples across the full time range (not just the most recent 500 calls)
    so the timeline reflects the entire selected period.
    Anomaly = token count spike (>2x median) — marks real outliers.

    Returns (recorded_at, total_tokens, is_anomaly, cause_dict) where
    cause_dict carries the per-call attribution used to explain WHY a red
    bar is red: agent, model, source, finish_reason, tool_name, provider,
    session_id. Without it, a red bar says "anomaly" but not what the
    anomalous call actually was.

    MEASURED ONLY and OVERLAP-RESOLVED: filters to otel/hermes rows, and
    drops the hermes side of any session that also has otel rows (otel wins
    precedence — the same rule as v_token_effective). Without this, the
    timeline shows both sides of the 733 overlapping sessions (~47% of 7d
    hermes rows), re-importing the double-count the precedence view exists
    to eliminate, and the anomaly detector then flags those duplicates as
    spikes. Watch rows are synthetic estimates and are excluded entirely.
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    source_clause = "AND source IN ('otel','hermes')"
    # Precedence: exclude hermes rows whose session also has otel rows.
    overlap_clause = """
        AND NOT (source = 'hermes' AND session_id != '' AND EXISTS (
            SELECT 1 FROM token_logs o
            WHERE o.source = 'otel' AND o.session_id = token_logs.session_id
              AND o.recorded_at >= ?
        ))
    """
    params = params + (since,)  # for the EXISTS subquery

    # First, get total count in range to decide if we need to sample
    cur = conn.execute(f"""
        SELECT COUNT(*) as cnt FROM token_logs WHERE recorded_at >= ? {source_clause} {overlap_clause} {agent_clause}
    """, params)
    total = cur.fetchone()["cnt"]

    select_cols = """recorded_at, total_tokens, agent_name, model, source,
                     finish_reason, tool_name, provider, session_id,
                     input_tokens, output_tokens, cache_read_tokens"""
    if total <= 500:
        # Small dataset — just return everything
        cur = conn.execute(f"""
            SELECT {select_cols}
            FROM token_logs WHERE recorded_at >= ? {source_clause} {overlap_clause} {agent_clause}
            ORDER BY recorded_at ASC
        """, params)
        rows = [dict(r) for r in cur.fetchall()]
    else:
        # Large dataset — sample evenly across the full time range
        # Use a subquery with row_number to get evenly-spaced samples
        cur = conn.execute(f"""
            SELECT {select_cols} FROM (
                SELECT {select_cols},
                    ROW_NUMBER() OVER (ORDER BY recorded_at) as rn,
                    COUNT(*) OVER () as cnt
                FROM token_logs WHERE recorded_at >= ? {source_clause} {overlap_clause} {agent_clause}
            ) WHERE rn % MAX(1, cnt / 500) = 0
            ORDER BY recorded_at ASC
            LIMIT 500
        """, params)
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return []

    # Per-source anomaly thresholds. The two sources are DIFFERENT UNITS:
    # otel rows are single LLM calls (median 115K, ceiling ~621K); hermes
    # rows are session aggregates — one row per session summing every call
    # (median 30K, no ceiling — max 327M). A mixed threshold flags hermes
    # session totals as 'anomaly' when they're just a different unit, and
    # misses real otel spikes. Threshold per source so 'anomaly' means
    # 'spike within your own population'.
    otel_vals = sorted(r["total_tokens"] or 0 for r in rows if r["source"] == "otel")
    hermes_vals = sorted(r["total_tokens"] or 0 for r in rows if r["source"] == "hermes")

    def _double_median(vals) -> float | None:
        if not vals:
            return None
        return (vals[len(vals) // 2] or 0) * 2

    otel_threshold = _double_median(otel_vals)
    hermes_threshold = _double_median(hermes_vals)

    # Enrichment for anomaly rows: fetch the diagnostic context that
    # actually explains WHY a bar is large. For hermes session aggregates,
    # that's the session's message/tool/user-message counts + duration (from
    # Hermes state.db). For otel single calls, that's the span duration (from
    # trace_spans) and the input-token share (already in the row). Only
    # anomaly rows get enriched — bounded cost on a subset.
    import os as _os
    import sqlite3 as _sqlite3
    _state_db = _os.path.expanduser("~/.hermes/state.db")

    def _enrich(cause: dict) -> dict:
        c = dict(cause)
        if c["source"] == "hermes" and c["session"]:
            try:
                sc = _sqlite3.connect(_state_db)
                sc.row_factory = _sqlite3.Row
                m = sc.execute("""
                    SELECT COUNT(*) AS n,
                           SUM(CASE WHEN tool_name IS NOT NULL AND tool_name != '' THEN 1 ELSE 0 END) AS tools,
                           SUM(CASE WHEN role='user' THEN 1 ELSE 0 END) AS user_msgs,
                           MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts
                    FROM messages WHERE session_id = ?
                """, (c["session"],)).fetchone()
                sc.close()
                if m and m["n"]:
                    c["session_msgs"] = m["n"]
                    c["session_tools"] = m["tools"] or 0
                    c["session_user"] = m["user_msgs"] or 0
                    dur = (m["max_ts"] or 0) - (m["min_ts"] or 0)
                    c["session_dur_s"] = int(dur) if dur and dur > 0 else None
            except Exception:
                pass
        elif c["source"] == "otel" and c["session"]:
            # otel single call: no session detail (it IS one call); the span
            # duration is the useful addition but requires a trace_spans join
            # keyed on turn_id. skip — input share already tells the story.
            pass
        return c

    timeline = []
    for r in rows:
        src = r["source"] or "?"
        thr = otel_threshold if src == "otel" else hermes_threshold
        is_anom = thr is not None and (r["total_tokens"] or 0) > thr
        cause = {
            "agent": r["agent_name"] or "?",
            "model": r["model"] or "?",
            "source": src,
            "unit": "session total" if src == "hermes" else "single call",
            "finish_reason": r["finish_reason"] or "—",
            "tool": r["tool_name"] or "",
            "provider": r["provider"] or "?",
            "session": (r["session_id"] or "")[:24],
            "input": r["input_tokens"] or 0,
            "output": r["output_tokens"] or 0,
            "cache_read": r["cache_read_tokens"] or 0,
            "recorded_at": r["recorded_at"] or 0,
        }
        if is_anom:
            cause = _enrich(cause)
        timeline.append((r["recorded_at"], r["total_tokens"] or 0, is_anom, cause))
    return timeline


def _query_latency(conn, since: int, agent: str) -> dict:
    """Per-call latency stats from measured otel rows (latency_ms backfilled).

    Coverage note: latency_ms was only populated from span retention start
    (Jun 29, migration-74 backfill). Rows before that are 0 — the caller
    must render the coverage sentence, not imply those calls were fast.
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            COUNT(*) AS n,
            SUM(CASE WHEN latency_ms > 0 THEN 1 ELSE 0 END) AS n_with_latency,
            AVG(CASE WHEN latency_ms > 0 THEN latency_ms END) AS avg_ms,
            MIN(CASE WHEN latency_ms > 0 THEN latency_ms END) AS min_ms,
            MAX(CASE WHEN latency_ms > 0 THEN latency_ms END) AS max_ms,
            MIN(recorded_at) AS first_ts,
            MAX(recorded_at) AS last_ts
        FROM token_logs
        WHERE recorded_at >= ? AND source = 'otel' {agent_clause}
    """, params)
    r = cur.fetchone()
    if not r or not r["n"]:
        return {"n": 0, "n_with_latency": 0, "avg_ms": 0, "min_ms": 0,
                "max_ms": 0, "first_ts": 0, "last_ts": 0, "coverage_pct": 0.0}
    cov = (r["n_with_latency"] or 0) / max(r["n"], 1) * 100
    return {"n": r["n"], "n_with_latency": r["n_with_latency"] or 0,
            "avg_ms": round(r["avg_ms"] or 0), "min_ms": r["min_ms"] or 0,
            "max_ms": r["max_ms"] or 0, "first_ts": r["first_ts"] or 0,
            "last_ts": r["last_ts"] or 0, "coverage_pct": round(cov, 1)}


def _query_tool_vs_conversation(conn, since: int, agent: str) -> dict:
    """Structural split: tool-invoking vs conversational spend.

    finish_reason='tool_calls' is a per-call, 100%-coverage structural
    indicator (backfilled from trace_spans, migration 74). No heuristic —
    a call either terminated requesting a tool or it didn't. Answers
    "how much spend is agentic loop traffic vs conversation" without any
    tool names.
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)
    cur = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN finish_reason = 'tool_calls' THEN cost ELSE 0 END), 0) AS tool_cost,
            COALESCE(SUM(CASE WHEN finish_reason = 'tool_calls' THEN 1 ELSE 0 END), 0) AS tool_n,
            COALESCE(SUM(CASE WHEN finish_reason NOT IN ('tool_calls', '') THEN cost ELSE 0 END), 0) AS conv_cost,
            COALESCE(SUM(CASE WHEN finish_reason NOT IN ('tool_calls', '') THEN 1 ELSE 0 END), 0) AS conv_n,
            COALESCE(SUM(CASE WHEN finish_reason = '' THEN cost ELSE 0 END), 0) AS unk_cost,
            COALESCE(SUM(cost), 0) AS total_cost,
            COALESCE(COUNT(*), 0) AS total_n
        FROM token_logs
        WHERE recorded_at >= ? AND source = 'otel' {agent_clause}
    """, params)
    r = cur.fetchone()
    return {k: (r[k] or 0) for k in ("tool_cost", "tool_n", "conv_cost", "conv_n",
                                     "unk_cost", "total_cost", "total_n")}


def _query_tool_mix(conn, since: int, agent: str, state_db: str | None = None) -> dict:
    """Tool-mix apportionment (session-level, honest label).

    ATTRIBUTES PROPORTIONALLY, NOT CAUSALLY: hermes rows in a session are
    attributed to that session's tool-message distribution. A session that
    used terminal 40x and read_file 10x spreads its spend 80/20 across all
    its calls. This answers "which tools did sessions use", not "which
    step consumed which tokens". Coverage: hermes rows in tool-message
    sessions only (~38% of measured spend all-time).
    """
    agent_clause = "AND agent_name = ?" if agent != "__all__" else ""
    params = (since,)
    if agent != "__all__":
        params = params + (agent,)

    # hermes rows in this window, by session
    rows = conn.execute(f"""
        SELECT session_id, SUM(cost) AS cost, COUNT(*) AS n
        FROM token_logs
        WHERE recorded_at >= ? AND source = 'hermes' AND session_id != '' {agent_clause}
        GROUP BY session_id
    """, params).fetchall()
    if not rows:
        return {"tools": {}, "attributable_cost": 0.0, "total_cost": 0.0, "coverage_pct": 0.0,
                "n_sessions": 0, "n_tool_sessions": 0}

    total_cost = sum(r["cost"] or 0 for r in rows)
    session_ids = [r["session_id"] for r in rows]

    # tool message counts per session from Hermes state.db
    if state_db is None:
        import os
        state_db = os.path.expanduser("~/.hermes/state.db")
    import sqlite3
    sconn = sqlite3.connect(state_db)
    sconn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(session_ids))
    tm = sconn.execute(f"""
        SELECT session_id, tool_name, COUNT(*) AS n
        FROM messages
        WHERE tool_name IS NOT NULL AND tool_name != ''
          AND session_id IN ({placeholders})
        GROUP BY session_id, tool_name
    """, session_ids).fetchall()
    sconn.close()

    # session -> {tool: count}
    sess_tools: dict[str, dict[str, int]] = {}
    for x in tm:
        sess_tools.setdefault(x["session_id"], {})[x["tool_name"]] = x["n"]

    tool_cost: dict[str, float] = {}
    attr_cost = 0.0
    n_tool_sessions = 0
    for r in rows:
        tools = sess_tools.get(r["session_id"])
        if not tools:
            continue
        n_tool_sessions += 1
        total_n = sum(tools.values())
        for tool, n in tools.items():
            tool_cost[tool] = tool_cost.get(tool, 0.0) + (r["cost"] or 0) * n / total_n
        attr_cost += r["cost"] or 0

    coverage = attr_cost / max(total_cost, 1) * 100
    return {"tools": dict(sorted(tool_cost.items(), key=lambda kv: -kv[1])),
            "attributable_cost": round(attr_cost, 2),
            "total_cost": round(total_cost, 2),
            "coverage_pct": round(coverage, 1),
            "n_sessions": len(session_ids),
            "n_tool_sessions": n_tool_sessions}


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

        # Query 1: Per-agent aggregates (measured-only from v_token_effective)
        agent_rows = _query_agents(conn, since, agent)
        if not agent_rows:
            return HTMLResponse(empty_html())

        # Component composition (otel-only breakdown) + simulated watch table
        comp_totals = _query_components(conn, since, agent)
        sim_rows = _query_simulated_agents(conn, since, agent)

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

        # Query 4: Latency (measured otel only; backfilled from spans)
        latency = _query_latency(conn, since, agent)

        # Query 5: Tool vs conversation (structural, finish_reason)
        tvc = _query_tool_vs_conversation(conn, since, agent)
        # In-window (post-Jun-29) cost-weighted split — the headline. The
        # unlabeled (pre-retention) share is excluded and shown as a note.
        _tw = tvc["tool_cost"] + tvc["conv_cost"]
        tvc_tool_pct = tvc["tool_cost"] / max(_tw, 1) * 100
        tvc_conv_pct = tvc["conv_cost"] / max(_tw, 1) * 100
        _tn = tvc["tool_n"] + tvc["conv_n"]
        tvc_tool_n_pct = tvc["tool_n"] / max(_tn, 1) * 100
        tvc_conv_n_pct = tvc["conv_n"] / max(_tn, 1) * 100
        tvc_unk_pct = tvc["unk_cost"] / max(tvc["total_cost"], 1) * 100

        # Query 6: Tool-mix apportionment (session-level, honest label)
        tmix = _query_tool_mix(conn, since, agent)

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

    # Timeline (tuples now carry cause dict for tooltip/detail)
    turn_ts = [t for t, _, _, _ in timeline]
    turn_tokens = [n for _, n, _, _ in timeline]
    turn_anom = [a for _, _, a, _ in timeline]
    turn_cause = [c for _, _, _, c in timeline]
    if len(turn_tokens) > 500:
        turn_ts = turn_ts[-500:]
        turn_tokens = turn_tokens[-500:]
        turn_anom = turn_anom[-500:]
        turn_cause = turn_cause[-500:]
    max_tok = max(turn_tokens) or 1

    # Build per-column HTML: hover tooltip carries the call's cause; click
    # pins it to the detail box below. Red (anomaly) columns explain WHY —
    # agent, model, source, unit (single call vs session total), composition
    # (input/cache %) — so a spike is diagnosable without leaving the tab.
    def _cause_parts(c: dict, t: int, a: bool) -> str:
        parts = [f"{_fmt_tok(t)} tok", c["agent"], c["model"], c["unit"]]
        if c["tool"]:
            parts.append(f"tool: {c['tool']}")
        if c["finish_reason"] and c["finish_reason"] != "—":
            parts.append(c["finish_reason"])
        elif c["source"] == "otel":
            # otel rows with no finish_reason: label by DERIVED cause, not
            # asserted. Pre-retention (before Jun 29 span retention start)
            # rows genuinely have no span. But in-window rows with null
            # finish_reason are a mapper miss or a span with no finish
            # reason — calling them 'pre-Jun 29' would be a false
            # explanation. Distinguish by the actual timestamp.
            if c["recorded_at"] < 1782744531:
                parts.append("no finish_reason (pre-Jun 29, no span)")
            else:
                parts.append("no finish_reason (no span recorded)")
        # Composition: input dominates? cache engaged? -> the 'why'
        inp, out, cr = c["input"], c["output"], c["cache_read"]
        if inp or out:
            inp_pct = inp / max(inp + out, 1) * 100
            parts.append(f"{inp_pct:.0f}% input")
            if cr and inp > 0:
                parts.append(f"{cr / inp * 100:.0f}% cached")
            elif cr and inp == 0:
                # degenerate: cache tokens without input tokens — label raw
                parts.append(f"{_fmt_tok(cr)} cache")
        if a:
            parts.append("spike vs same-source median")
        return " · ".join(parts)

    # Enriched detail for the click-to-inspect box: session context (message/
    # tool/user counts + duration) for hermes aggregates; input-token context
    # for otel calls. This is the actual 'why' behind a red bar.
    def _cause_detail(c: dict, t: int) -> str:
        lines = [f"{_fmt_tok(t)} tok", f"{c['unit']} · {c['agent']} · {c['model']}"]
        if c["tool"]:
            lines.append(f"tool: {c['tool']}")
        if c["finish_reason"] and c["finish_reason"] != "—":
            lines.append(f"finish: {c['finish_reason']}")
        inp, out, cr = c["input"], c["output"], c["cache_read"]
        if inp or out:
            lines.append(f"composition: {inp:,} input / {out:,} output"
                         f"{' / ' + f'{cr:,} cached' if cr else ''}")
        if c.get("session_msgs"):
            dur = c.get("session_dur_s")
            lines.append(f"session: {c['session_msgs']} msgs · {c['session_tools']} tools · "
                         f"{c['session_user']} user msgs" + (f" · {dur/3600:.1f}h long" if dur else ""))
        elif c["source"] == "otel" and (inp or out):
            inp_pct = inp / max(inp + out, 1) * 100
            lines.append(f"input context is {inp_pct:.0f}% of this call — large prompt/context re-send")
        if c.get("session"):
            lines.append(f"session_id: {c['session']}")
        if c["provider"] and c["provider"] != "?":
            lines.append(f"provider: {c['provider']}")
        lines.append("flagged: spike vs same-source median (>2x)")
        return "\n".join(lines)

    timeline_html = (
        ''.join(
            f'<div class="timeline-col{" anomaly" if a else ""}" '
            f'style="height:max(4px, {t / max_tok * 100}%)" '
            f'title="{_html_escape(_cause_parts(c, t, a))}" '
            f'data-cause="{_html_escape(_cause_detail(c, t) if a else _cause_parts(c, t, a))}" '
            f'onclick="showTimelineDetail(this)"></div>'
            for t, a, c in zip(turn_tokens, turn_anom, turn_cause)
        )
        if turn_tokens
        else '<span style="color:var(--fg-3);font-size:var(--text-sm)">No call data</span>'
    )

    # Component composition
    COMP_ORDER = [
        ("identity", "var(--token-identity)", "identity"),
        ("skills", "var(--token-skills)", "skills"),
        ("memory", "var(--token-memory)", "memory"),
        ("tools", "var(--token-tools)", "tools"),
        ("guidance", "var(--token-guidance)", "guidance"),
    ]
    fleet_comp = {k: comp_totals.get(k, 0) for k, _, _ in COMP_ORDER}
    comp_max = max(fleet_comp.values()) or 1
    comp_rows = ""
    if sum(fleet_comp.values()) > 0:
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
        rec += f" −{_fmt_dollar(suspect_cost)} suspected duplicate spans excluded (heuristic)."
    badge_cls = "good" if confidence_pct > 80 else "warn" if confidence_pct > 50 else "bad"
    top_cls = "bad" if top_spender_pct > 50 else "warn" if top_spender_pct > 25 else "good"
    cache_cls = "good" if overall_cache_rate > 20 else "warn" if overall_cache_rate > 5 else "bad"
    suspect_note = (
        f'<div class="vc-note">−{_fmt_dollar(suspect_cost)} suspected duplicate spans '
        f'excluded (heuristic) · {_fmt_dollar(simulated_cost)} simulated (watch, estimates)</div>'
        if suspect_cost > 0 else
        f'<div class="vc-note">{_fmt_dollar(simulated_cost)} simulated (watch, estimates) kept separate</div>'
    )
    insight_html = f"""<div class="verdict-card" style="margin-bottom:var(--space-4)">
    <div class="vc-head"><span class="mark">$</span><span class="lead">SPEND VERDICT</span>
        <span class="vc-badge {badge_cls}">{confidence_pct}% accurate</span></div>
    <div class="vc-stats">
        <div class="vc-stat"><span class="vc-num">{_fmt_dollar(measured_cost)}</span><span class="vc-lab">estimated · computed from token counts, not billed · {turn_count} calls</span></div>
        <div class="vc-stat"><span class="vc-num {top_cls}">{top_spender_pct}%</span><span class="vc-lab">{_html_escape(top_agent)} top spender</span></div>
        <div class="vc-stat"><span class="vc-num {cache_cls}">{overall_cache_rate}%</span><span class="vc-lab">fleet cache hit</span></div>
        <div class="vc-stat"><span class="vc-num">{attr_pct}%</span><span class="vc-lab">attributed</span></div>
    </div>
    <div class="vc-rec">{rec}</div>
    {suspect_note}
</div>"""

    agent_count = len(sorted_agents)

    # Simulated (watch) per-agent rows — separate section, never summed
    sim_rows_html = ""
    for s in sim_rows:
        s_cost = _fmt_dollar(s["cost"])
        s_tok = _fmt_tok(s["tokens"])
        s_cache = round(s["cache_read"] / max(s["cache_read"] + s["cache_create"], 1) * 100)
        sim_rows_html += f"""<tr>
    <td><span class="ag">{_html_escape(s["agent_name"])}</span></td>
    <td class="mono r">{s_cost}</td>
    <td class="mono r">{s_tok}</td>
    <td class="mono">—</td>
    <td><span class="dq est">Sim</span></td>
    <td class="r"><span class="mono" style="color:var(--fg-3)">{s_cache}%</span></td>
</tr>"""
    sim_section = ""
    if sim_rows_html:
        sim_total = _fmt_dollar(sum(s["cost"] for s in sim_rows))
        sim_section = f"""
<div class="section-h" style="margin-top:var(--space-4)"><h2>Simulated (watch)</h2><span class="count">{len(sim_rows)} agents · {sim_total} estimates</span></div>
<div class="tblwrap">
    <table class="tbl">
        <tr><th>Agent</th><th class="r">Cost</th><th class="r">Tokens</th><th>Model</th><th>Data</th><th class="r">Cache</th></tr>
        {sim_rows_html}
    </table>
</div>"""

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
    <div class="panel chart-card">
        <div class="cc-head"><h2>Latency / Call</h2>
            <span class="cc-val mono">{_fmt_ms(latency['avg_ms'])}</span>
            <span class="cc-lab">avg · measured</span>
        </div>
        <div class="chart-box" style="min-height:64px">
            <div class="latency-range">
                <div class="latency-fill" style="left:0%;width:100%"></div>
                <div class="latency-marker" style="left:0%" title="min"></div>
                <div class="latency-marker" style="left:50%" title="avg"></div>
                <div class="latency-marker" style="left:100%" title="max"></div>
            </div>
            <div class="latency-labels">
                <span class="mono">min {_fmt_ms(latency['min_ms'])}</span>
                <span class="mono">avg {_fmt_ms(latency['avg_ms'])}</span>
                <span class="mono">max {_fmt_ms(latency['max_ms'])}</span>
            </div>
            <div class="latency-stats">
                <span class="stat"><span class="k">calls</span> <span class="v mono">{latency['n_with_latency']:,}</span></span>
                <span class="stat"><span class="k">coverage</span> <span class="v mono">{latency['coverage_pct']}%</span></span>
            </div>
            <div class="coverage-note">Latency captured from <strong>Jun 29</strong> (span retention start). Earlier calls were not captured — the {100 - latency['coverage_pct']:.0f}% gap is the pre-retention period, not fast calls.</div>
        </div>
    </div>
    <div class="panel chart-card">
        <div class="cc-head"><h2>Tool vs Conversation</h2>
            <span class="cc-val mono">{tvc_tool_pct:.0f}%</span>
            <span class="cc-lab">of labeled spend · tool-invoking</span>
        </div>
        <div class="chart-box" style="min-height:64px">
            <div class="split-bar">
                <div class="seg tool" style="width:{tvc_tool_pct:.0f}%">{tvc_tool_pct:.0f}%</div>
                <div class="seg conv" style="width:{tvc_conv_pct:.0f}%">{tvc_conv_pct:.0f}%</div>
            </div>
            <div class="split-legend">
                <span class="item"><span class="swatch" style="background:var(--tool)"></span>
                    Tool-invoking <span class="amt">{_fmt_dollar(tvc['tool_cost'])}</span> <span class="pct">{tvc_tool_pct:.0f}%</span></span>
                <span class="item"><span class="swatch" style="background:var(--conv)"></span>
                    Conversational <span class="amt">{_fmt_dollar(tvc['conv_cost'])}</span> <span class="pct">{tvc_conv_pct:.0f}%</span></span>
            </div>
            <div style="margin-top:12px;font-size:11px;color:var(--fg-3)">
                By call count: <span class="mono">{tvc_tool_n_pct:.0f}%</span> tool · <span class="mono">{tvc_conv_n_pct:.0f}%</span> conv
            </div>
            <div class="coverage-note">Headline is <strong>cost-weighted, in-window</strong> — it answers "where does the money go" for the calls we can see. <strong>{tvc_unk_pct:.0f}% of all-time spend is unlabeled</strong> (pre-Jun 29, no span) and excluded here; that share shrinks toward zero as the retention window rolls forward.</div>
        </div>
    </div>
</div>

<div class="section-h"><h2>Per-Agent Spend</h2><span class="count">{len(sorted_agents)} agents</span></div>
<div class="tblwrap">
    <table class="tbl">
        <tr><th>Agent</th><th class="r">Cost</th><th class="r">Tokens</th><th>Model</th><th>Data</th><th class="r">Cache</th></tr>
        {agent_rows}
    </table>
</div>
{sim_section}

<div class="section-h"><h2>Component Composition</h2><span class="count">per agent average</span></div>
<div class="panel" style="margin-bottom:var(--space-6)">
    {comp_rows if comp_rows else '<span style="color:var(--fg-3);font-size:var(--text-sm)">No component data collected — enable the telemetry plugin to populate identity/skills/memory/tools/guidance breakdown.</span>'}
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

<div class="section-h"><h2>Tool Mix (apportioned)</h2><span class="count">{tmix['n_tool_sessions']} of {tmix['n_sessions']} sessions · {tmix['coverage_pct']}% of hermes spend attributed</span></div>
<div class="panel" style="margin-bottom:var(--space-6)">
    <p style="font-size:12px;color:var(--fg-3);margin-bottom:10px;">Tool spend is apportioned at session level: each session's spend is spread across its tool-message distribution (terminal 40x + read_file 10x → spend split 80/20). This answers <em>which tools sessions used</em>, not which step consumed which tokens. <span style="color:var(--fg-3)">Covers {_fmt_dollar(tmix['attributable_cost'])} of {_fmt_dollar(tmix['total_cost'])} hermes spend ({tmix['coverage_pct']}%) — tool-message sessions only; otel-side spend and non-agentic sessions are unlabeled.</span></p>
    {(''.join(
        f'<div style="display:flex;justify-content:space-between;font-size:var(--text-sm);padding:3px 0;border-bottom:1px solid var(--border, rgba(128,128,128,.15))">'
        f'<span>{tool}</span><span class="mono">{_fmt_dollar(cost)}</span></div>'
        for tool, cost in list(tmix['tools'].items())[:15]
    )) if tmix['tools'] else '<span style="color:var(--fg-3);font-size:var(--text-sm)">No tool-message sessions in this window.</span>'}
</div>

<div class="section-h"><h2>Per-Turn Timeline</h2><span class="count">{len(turn_tokens)} calls{'' if len(turn_tokens) <= 500 else ' · showing last 500'}</span></div>
<div class="panel" style="margin-bottom:var(--space-6)">
    <p style="font-size:12px;color:var(--fg-3);margin-bottom:10px;">Each column = one LLM call (otel) or one session total (hermes, marked in tooltip). Height = total tokens. <span style="color:var(--danger)">Red columns</span> = spike vs that source's own median. Hover a column for what that call/session was and its composition; click to pin the detail below.</p>
    <div class="timeline-bar" id="timelineBar">
        {timeline_html}
    </div>
    <div id="timelineDetail" style="margin-top:10px;padding:10px 12px;border:1px solid var(--border, rgba(128,128,128,.25));border-radius:8px;background:var(--bg-2, rgba(255,255,255,.03));font-size:12px;color:var(--fg-1);display:none;white-space:pre-line;line-height:1.6">Click a column to inspect that call.</div>
</div>
<script>
function showTimelineDetail(el) {{
    var detail = document.getElementById('timelineDetail');
    if (!detail) return;
    var d = el.getAttribute('data-cause') || el.getAttribute('title') || '';
    detail.style.display = 'block';
    detail.textContent = d;
}}
</script>

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
