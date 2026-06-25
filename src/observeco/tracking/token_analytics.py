"""Token analytics — time-series aggregation, chart data, breakdown, system prompts.

Phase 1: Schema migration + aggregation
Phase 2: API endpoints
"""
from __future__ import annotations

import logging
import math
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

# Granularity buckets in seconds
GRANULARITY_SECONDS = {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,
}

# Component columns for breakdown
TOKEN_COMPONENTS = [
    "identity_tokens",
    "skills_tokens",
    "memory_tokens",
    "tools_tokens",
    "guidance_tokens",
]

# New §10 components for input/output/cache breakdown
TOKEN_IO_COMPONENTS = [
    "input_tokens",
    "output_tokens",
    "cache_creation_tokens",
    "cache_read_tokens",
]


def _bucket_start(ts: int, granularity: str) -> int:
    """Round timestamp down to the start of its bucket."""
    secs = GRANULARITY_SECONDS.get(granularity, 3600)
    return (ts // secs) * secs


def _build_where(
    agent: str = "",
    provider: str = "",
    workflow: str = "",
    service: str = "",
    from_ts: int = 0,
    to_ts: int = 0,
    exclude_source: str = "",
    include_source: str = "",
) -> tuple[str, list]:
    """Build WHERE clause and params for token_logs queries.

    include_source: comma-separated list of sources to include (e.g. 'proxy,otel').
                   If set, only rows with source IN (...) are returned.
    exclude_source: single source to exclude (legacy, kept for backward compat).
    """
    conditions: list[str] = []
    params: list = []
    if agent:
        conditions.append("agent_name = ?")
        params.append(agent)
    if provider:
        conditions.append("provider = ?")
        params.append(provider)
    if workflow:
        conditions.append("workflow_name = ?")
        params.append(workflow)
    if service:
        conditions.append("service_name = ?")
        params.append(service)
    if from_ts:
        conditions.append("recorded_at >= ?")
        params.append(from_ts)
    if to_ts:
        conditions.append("recorded_at <= ?")
        params.append(to_ts)
    if exclude_source:
        conditions.append("source != ?")
        params.append(exclude_source)
    if include_source:
        sources = [s.strip() for s in include_source.split(",") if s.strip()]
        if sources:
            placeholders = ",".join("?" for _ in sources)
            conditions.append(f"source IN ({placeholders})")
            params.extend(sources)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


# ---------------------------------------------------------------------------
# Phase 1: Aggregation
# ---------------------------------------------------------------------------

def aggregate_tokens(
    db: Optional[Database] = None,
    agent: str = "",
    provider: str = "",
    workflow: str = "",
    service: str = "",
    from_ts: int = 0,
    to_ts: int = 0,
    granularity: str = "hour",
    include_source: str = "",
) -> list[dict]:
    """Aggregate token_logs by time bucket. Returns list of bucket dicts."""
    if db is None:
        db = Database()
    conn = db._get_conn()

    where, params = _build_where(agent, provider, workflow, service, from_ts, to_ts, include_source=include_source)

    # Fetch raw data
    query = f"""
        SELECT agent_name, provider, total_tokens, identity_tokens, skills_tokens,
               memory_tokens, tools_tokens, guidance_tokens,
               input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens,
               cost, cache_savings, recorded_at, source
        FROM token_logs {where}
        ORDER BY recorded_at
    """
    rows = conn.execute(query, params).fetchall()
    if not rows:
        return []

    # Source priority for dominant_source: sdk/proxy > otel > watch > unknown
    _SOURCE_PRIORITY = {"sdk": 4, "proxy": 4, "otel": 3, "watch": 1, "unknown": 0}

    # Bucket by granularity
    buckets: dict[int, dict] = {}
    for r in rows:
        rd = dict(r)
        bucket = _bucket_start(rd["recorded_at"], granularity)
        if bucket not in buckets:
            buckets[bucket] = {
                "bucket_start": bucket,
                "total_tokens": 0,
                "identity_tokens": 0,
                "skills_tokens": 0,
                "memory_tokens": 0,
                "tools_tokens": 0,
                "guidance_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "cost": 0.0,
                "cache_savings": 0.0,
                "turn_count": 0,
                "max_tokens": 0,
                "min_tokens": math.inf,
                "_source_counts": {},
            }
        b = buckets[bucket]
        b["total_tokens"] += rd.get("total_tokens", 0) or 0
        for comp in TOKEN_COMPONENTS:
            b[comp] += rd.get(comp, 0) or 0
        b["cost"] += rd.get("cost", 0) or 0
        b["cache_savings"] += rd.get("cache_savings", 0) or 0
        for comp in TOKEN_IO_COMPONENTS:
            b[comp] += rd.get(comp, 0) or 0
        b["turn_count"] += 1
        tok = rd.get("total_tokens", 0) or 0
        if tok > b["max_tokens"]:
            b["max_tokens"] = tok
        if tok < b["min_tokens"]:
            b["min_tokens"] = tok
        src = rd.get("source") or "unknown"
        b["_source_counts"][src] = b["_source_counts"].get(src, 0) + 1

    secs = GRANULARITY_SECONDS.get(granularity, 3600)
    # Only apply 30% output estimation in sizing mode (source=watch exclusively).
    # For "All Data" or "Actual Cost" views, use raw values — estimation inflates
    # output when watch data (output=0) dominates the bucket.
    apply_output_estimation = (include_source == "watch")
    result = []
    for bucket in sorted(buckets.keys()):
        b = buckets[bucket]
        b["bucket_end"] = b["bucket_start"] + secs
        # Estimate output tokens for watch.py rows (output_tokens=0, input_tokens>0)
        # Only in sizing mode — not in All Data or Actual Cost views
        if apply_output_estimation and b["output_tokens"] == 0 and b["input_tokens"] > 0:
            b["output_tokens"] = int(b["input_tokens"] * 0.3)
        b["avg_tokens"] = round(b["total_tokens"] / max(b["turn_count"], 1), 1)
        if b["min_tokens"] == math.inf:
            b["min_tokens"] = 0
        # Determine dominant source for this bucket (highest priority wins)
        src_counts = b.pop("_source_counts", {})
        dominant = max(src_counts, key=lambda s: (_SOURCE_PRIORITY.get(s, 0), src_counts[s])) if src_counts else "unknown"
        b["dominant_source"] = dominant
        result.append(b)

    return result


def compute_summary(data: list[dict]) -> dict:
    """Compute summary stats from aggregated data."""
    total_tokens = sum(d["total_tokens"] for d in data)
    total_cost = sum(d["cost"] for d in data)
    total_turns = sum(d["turn_count"] for d in data)
    avg_per_turn = round(total_tokens / max(total_turns, 1), 1)
    return {
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
        "avg_per_turn": avg_per_turn,
        "turn_count": total_turns,
    }


# ---------------------------------------------------------------------------
# Phase 2: API data builders
# ---------------------------------------------------------------------------

def get_chart_data(
    agent: str = "",
    provider: str = "",
    workflow: str = "",
    service: str = "",
    from_ts: int = 0,
    to_ts: int = 0,
    granularity: str = "hour",
    component: str = "total",
    db: Optional[Database] = None,
    include_source: str = "",
) -> dict:
    """Build chart response: time-series data + summary."""
    if db is None:
        db = Database()
    data = aggregate_tokens(db, agent, provider, workflow, service, from_ts, to_ts, granularity, include_source=include_source)

    # If requesting a specific component, project it as total_tokens
    all_components = [c.replace("_tokens", "") for c in TOKEN_COMPONENTS + TOKEN_IO_COMPONENTS]
    if component != "total" and component in all_components:
        comp_col = f"{component}_tokens" if not component.endswith("_tokens") else component
        for d in data:
            d["total_tokens"] = d.get(comp_col, 0)
            d["avg_tokens"] = round(d["total_tokens"] / max(d["turn_count"], 1), 1)
    elif component == "total":
        # OpenAI total_tokens = prompt + completion (excludes cache_read).
        # Recompute to include all dimensions for accurate totals.
        for d in data:
            true_total = (
                (d.get("input_tokens", 0) or 0)
                + (d.get("output_tokens", 0) or 0)
                + (d.get("cache_read_tokens", 0) or 0)
                + (d.get("cache_creation_tokens", 0) or 0)
            )
            if true_total > 0:
                d["total_tokens"] = true_total
                d["avg_tokens"] = round(true_total / max(d["turn_count"], 1), 1)

    summary = compute_summary(data)
    # Determine dominant source across all returned data (for chart labeling)
    all_sources: dict[str, int] = {}
    _SOURCE_PRIORITY_TOP = {"sdk": 4, "proxy": 4, "otel": 3, "watch": 1, "unknown": 0}
    for b in data:
        src = b.get("dominant_source", "unknown")
        all_sources[src] = all_sources.get(src, 0) + b.get("turn_count", 1)
    overall_source = max(all_sources, key=lambda s: (_SOURCE_PRIORITY_TOP.get(s, 0), all_sources[s])) if all_sources else "unknown"
    source_label_map = {"otel": "OTEL (accurate)", "sdk": "SDK (full)", "proxy": "Proxy (full)", "watch": "Watch (estimated)", "unknown": "Unknown"}
    return {
        "granularity": granularity,
        "agent": agent,
        "component": component,
        "data": data,
        "summary": summary,
        "dominant_source": overall_source,
        "dominant_source_label": source_label_map.get(overall_source, overall_source),
    }


def get_breakdown(
    dimension: str = "agent",
    from_ts: int = 0,
    to_ts: int = 0,
    db: Optional[Database] = None,
    include_source: str = "",
) -> dict:
    """Build breakdown response: slice by dimension."""
    if db is None:
        db = Database()
    conn = db._get_conn()

    dim_map = {
        "agent": "agent_name",
        "provider": "provider",
        "workflow": "workflow_name",
        "service": "service_name",
    }

    # Token type dimension: pivot input/output/cache from rows
    if dimension == "token_type":
        conditions = []
        params = []
        if from_ts:
            conditions.append("recorded_at >= ?")
            params.append(from_ts)
        if to_ts:
            conditions.append("recorded_at <= ?")
            params.append(to_ts)
        if include_source:
            sources = [s.strip() for s in include_source.split(",") if s.strip()]
            if sources:
                placeholders = ",".join("?" for _ in sources)
                conditions.append(f"source IN ({placeholders})")
                params.extend(sources)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"""
            SELECT
                SUM(input_tokens) as input_total,
                SUM(output_tokens) as output_total,
                SUM(cache_creation_tokens) as cache_creation_total,
                SUM(cache_read_tokens) as cache_read_total,
                MAX(0, SUM(total_tokens) - SUM(input_tokens) - SUM(output_tokens)) as other_total
            FROM token_logs {where}
        """
        row = conn.execute(query, params).fetchone()
        if not row:
            return {"dimension": dimension, "data": []}
        rd = dict(row)
        data = [
            {"name": "input", "total_tokens": rd.get("input_total", 0) or 0,
             "cost": 0, "turn_count": 0, "avg_per_turn": 0},
            {"name": "output", "total_tokens": rd.get("output_total", 0) or 0,
             "cost": 0, "turn_count": 0, "avg_per_turn": 0},
            {"name": "cache_creation", "total_tokens": rd.get("cache_creation_total", 0) or 0,
             "cost": 0, "turn_count": 0, "avg_per_turn": 0},
            {"name": "cache_read", "total_tokens": rd.get("cache_read_total", 0) or 0,
             "cost": 0, "turn_count": 0, "avg_per_turn": 0},
        ]
        # Filter out zero entries
        data = [d for d in data if d["total_tokens"] > 0]
        return {"dimension": dimension, "data": data}

    col = dim_map.get(dimension)
    if not col:
        return {"dimension": dimension, "data": []}

    conditions = []
    params = []
    if from_ts:
        conditions.append("recorded_at >= ?")
        params.append(from_ts)
    if to_ts:
        conditions.append("recorded_at <= ?")
        params.append(to_ts)
    if include_source:
        sources = [s.strip() for s in include_source.split(",") if s.strip()]
        if sources:
            placeholders = ",".join("?" for _ in sources)
            conditions.append(f"source IN ({placeholders})")
            params.extend(sources)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT {col} as name,
               SUM(input_tokens) + SUM(output_tokens) + SUM(cache_read_tokens) + SUM(cache_creation_tokens) as total_tokens,
               SUM(cost) as cost,
               COUNT(*) as turn_count,
               ROUND(AVG(input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens), 0) as avg_per_turn
        FROM token_logs {where}
        GROUP BY {col}
        ORDER BY cost DESC
    """
    rows = conn.execute(query, params).fetchall()
    data = [dict(r) for r in rows]
    return {"dimension": dimension, "data": data}


def get_system_prompts(
    from_ts: int = 0,
    to_ts: int = 0,
    limit: int = 20,
    db: Optional[Database] = None,
) -> dict:
    """Build system prompts response: top prompts by token usage."""
    if db is None:
        db = Database()
    conn = db._get_conn()

    conditions = ["system_prompt_hash != ''"]
    params: list = []
    if from_ts:
        conditions.append("recorded_at >= ?")
        params.append(from_ts)
    if to_ts:
        conditions.append("recorded_at <= ?")
        params.append(to_ts)
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT system_prompt_hash,
               SUM(input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens) as total_tokens,
               COUNT(*) as turn_count,
               GROUP_CONCAT(DISTINCT agent_name) as agents
        FROM token_logs {where}
        GROUP BY system_prompt_hash
        ORDER BY total_tokens DESC
        LIMIT ?
    """
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    data = []
    for r in rows:
        rd = dict(r)
        rd["avg_per_turn"] = round(rd["total_tokens"] / max(rd["turn_count"], 1), 0)
        rd["agents"] = rd.get("agents", "").split(",") if rd.get("agents") else []
        data.append(rd)

    return {"data": data}


def get_verdict(
    from_ts: int = 0,
    to_ts: int = 0,
    db: Optional[Database] = None,
) -> dict:
    """Build one-sentence cost health verdict using existing data.

    Combines total cost, top spender, cache trend, and a recommendation
    into a single human-readable summary.
    """
    if db is None:
        db = Database()
    conn = db._get_conn()

    conditions = []
    params: list = []
    if from_ts:
        conditions.append("recorded_at >= ?")
        params.append(from_ts)
    if to_ts:
        conditions.append("recorded_at <= ?")
        params.append(to_ts)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Total cost + turns
    row = conn.execute(
        f"SELECT SUM(cost) as cost, COUNT(*) as turns, "
        f"SUM(input_tokens) as inp, SUM(cache_read_tokens) as cr "
        f"FROM token_logs {where}", params
    ).fetchone()
    total_cost = row["cost"] or 0
    total_turns = row["turns"] or 0
    total_input = row["inp"] or 0
    total_cache_read = row["cr"] or 0

    # Top spender
    rows = conn.execute(
        f"SELECT agent_name, SUM(cost) as cost FROM token_logs {where} "
        f"GROUP BY agent_name ORDER BY cost DESC LIMIT 1", params
    ).fetchall()
    top_agent = dict(rows[0]) if rows else {}
    top_agent_name = top_agent.get("agent_name", "")
    top_agent_cost = top_agent.get("cost", 0)
    top_agent_pct = round(top_agent_cost / total_cost * 100, 1) if total_cost > 0 else 0

    # Cache trend: compare first half vs second half by time
    if from_ts and to_ts and total_input > 0:
        mid = from_ts + (to_ts - from_ts) // 2
        first_half = conn.execute(
            "SELECT SUM(cache_read_tokens) as cr, SUM(input_tokens) as inp "
            "FROM token_logs WHERE recorded_at >= ? AND recorded_at < ?",
            [from_ts, mid]
        ).fetchone()
        second_half = conn.execute(
            "SELECT SUM(cache_read_tokens) as cr, SUM(input_tokens) as inp "
            "FROM token_logs WHERE recorded_at >= ? AND recorded_at <= ?",
            [mid, to_ts]
        ).fetchone()
        first_rate = (first_half["cr"] or 0) / max(first_half["inp"] or 0, 1) * 100
        second_rate = (second_half["cr"] or 0) / max(second_half["inp"] or 0, 1) * 100
        cache_delta = round(second_rate - first_rate, 1)
    else:
        cache_delta = 0
        second_rate = total_cache_read / max(total_input, 1) * 100

    # Source confidence
    src_rows = conn.execute(
        f"SELECT source, SUM(cost) as cost FROM token_logs {where} GROUP BY source", params
    ).fetchall()
    accurate_cost = sum(r["cost"] or 0 for r in src_rows if r["source"] in ("otel", "sdk", "proxy"))
    confidence_pct = round(accurate_cost / total_cost * 100, 0) if total_cost > 0 else 0

    # Build recommendation
    recommendation = ""
    if total_cost == 0:
        recommendation = "No spend in this period."
    elif top_agent_pct > 50:
        recommendation = f"{top_agent_name} accounts for {top_agent_pct:.0f}% of spend — investigate if expected."
    if cache_delta < -5:
        recommendation += f" Cache hit rate dropped {abs(cache_delta):.0f}% — check if prompt caching is still enabled."
    elif second_rate < 5 and total_input > 100000:
        recommendation += " Cache hit rate near 0% — enable prompt caching to save on input tokens."

    return {
        "total_cost": round(total_cost, 4),
        "total_turns": total_turns,
        "top_agent": top_agent_name,
        "top_agent_pct": top_agent_pct,
        "cache_rate": round(second_rate, 1),
        "cache_delta": cache_delta,
        "confidence_pct": int(confidence_pct),
        "recommendation": recommendation.strip(),
    }


def get_cache_by_agent(
    from_ts: int = 0,
    to_ts: int = 0,
    db: Optional[Database] = None,
) -> dict:
    """Per-agent cache hit rate — surfaces agents with 0% cache."""
    if db is None:
        db = Database()
    conn = db._get_conn()

    conditions = []
    params: list = []
    if from_ts:
        conditions.append("recorded_at >= ?")
        params.append(from_ts)
    if to_ts:
        conditions.append("recorded_at <= ?")
        params.append(to_ts)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = conn.execute(
        f"SELECT agent_name, "
        f"SUM(input_tokens) as inp, SUM(cache_read_tokens) as cr "
        f"FROM token_logs {where} "
        f"GROUP BY agent_name ORDER BY inp DESC", params
    ).fetchall()

    data = []
    for r in rows:
        inp = r["inp"] or 0
        cr = r["cr"] or 0
        rate = round(cr / inp * 100, 1) if inp > 0 else 0
        data.append({
            "agent": r["agent_name"],
            "input_tokens": inp,
            "cache_read_tokens": cr,
            "hit_rate": rate,
        })
    return {"data": data}


def detect_cache_savings(agent_name: str, system_prompt_hash: str,
                         turn_number: int, input_tokens: int,
                         provider: str, db: Optional[Database] = None) -> dict:
    """Estimate cache savings when provider doesn't report cache metadata.

    Returns dict with cache_read, estimated_savings, confidence.
    """
    from observeco.tracking.tokens import PROVIDER_PRICING

    if turn_number <= 1:
        return {"cache_read": 0, "estimated_savings": 0, "confidence": "unknown"}

    # Adaptive prompt percentage: starts at 70%, floors at 30%
    estimated_prompt_pct = max(0.3, 0.7 - (turn_number * 0.02))
    estimated_prompt_tokens = int(input_tokens * estimated_prompt_pct)

    pricing = PROVIDER_PRICING.get(provider.lower(), PROVIDER_PRICING.get("custom", {}))
    cache_read_rate = pricing.get("cache_read", 0)
    input_rate = pricing.get("input", 0)

    if input_rate > 0 and cache_read_rate < input_rate:
        savings_pct = 1 - (cache_read_rate / input_rate)
        estimated_savings = (estimated_prompt_tokens / 1_000_000) * input_rate * savings_pct
        return {
            "cache_read": int(estimated_prompt_tokens * 0.9),
            "estimated_savings": round(estimated_savings, 6),
            "confidence": "estimated",
        }

    return {"cache_read": 0, "estimated_savings": 0, "confidence": "unknown"}
