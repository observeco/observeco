"""Token tracking — logging, summaries, trends, cost estimation."""
from typing import Optional
import time
from observeco.db import Database


def _estimate_cost(tokens_saved: int) -> float:
    """Estimate cost savings at $0.15/M tokens (DeepSeek rates)."""
    return tokens_saved * 0.15 / 1_000_000


def compute_cost(total_tokens: int, provider: str) -> float:
    """Compute estimated cost for a provider at its rate."""
    rates = {
        "anthropic": 3.00,
        "openai": 2.50,
        "openrouter": 0.50,
        "deepseek": 0.15,
        "ollama": 0.02,
    }
    return total_tokens * rates.get(provider.lower(), 0.15) / 1_000_000


def compute_cost_tiered(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    provider: str = "anthropic",
    model: str = "",
) -> float:
    """Compute cost for a token turn using model-specific per-token pricing.

    ponytail: covers top 5 models only. Upgrade path: add more models
    or fetch from a pricing API.
    """
    # Per-token prices in USD (input, output)
    model_pricing: dict[str, tuple[float, float]] = {
        "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
        "claude-sonnet": (3.00 / 1_000_000, 15.00 / 1_000_000),
        "claude-haiku": (0.25 / 1_000_000, 1.25 / 1_000_000),
        "deepseek-chat": (0.14 / 1_000_000, 0.28 / 1_000_000),
    }
    # Fallback: use provider-level flat rate
    provider_rates = {
        "anthropic": 3.00 / 1_000_000,
        "openai": 2.50 / 1_000_000,
        "deepseek": 0.15 / 1_000_000,
        "ollama": 0.0,
    }

    model_key = model.lower().strip()
    pricing = model_pricing.get(model_key)
    if pricing:
        input_price, output_price = pricing
    else:
        rate = provider_rates.get(provider.lower(), 0.15 / 1_000_000)
        input_price = rate
        output_price = rate * 4  # rough output multiplier

    # Cache reads are ~90% cheaper than input
    cache_read_price = input_price * 0.1
    # Cache creation is same as input
    cache_creation_price = input_price

    return (
        input_tokens * input_price
        + output_tokens * output_price
        + cache_read_tokens * cache_read_price
        + cache_creation_tokens * cache_creation_price
    )


def compute_anomaly(total_tokens: int, agent_name: str,
                     db: Optional[Database] = None) -> Optional[float]:
    return None


def log_token_turn(agent_name: str, turn_id: str, total_tokens: int,
                   input_tokens: int = 0, output_tokens: int = 0,
                   cache_read_tokens: int = 0, cache_creation_tokens: int = 0,
                   identity_tokens: int = 0, skills_tokens: int = 0,
                   memory_tokens: int = 0, tools_tokens: int = 0,
                   guidance_tokens: int = 0,
                   provider: str = "", cost: float = 0,
                   anomaly_score: Optional[float] = None,
                   db: Optional[Database] = None) -> None:
    """Log a token turn to the database."""
    if db is None:
        db = Database()
    db.log_token_turn(
        agent_name=agent_name, turn_id=turn_id, total_tokens=total_tokens,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens, cache_creation_tokens=cache_creation_tokens,
        identity_tokens=identity_tokens, skills_tokens=skills_tokens,
        memory_tokens=memory_tokens, tools_tokens=tools_tokens,
        guidance_tokens=guidance_tokens,
        provider=provider, cost=cost, anomaly_score=anomaly_score
    )


def get_token_summary(agent_name: str = "", days: int = 7,
                       db: Optional[Database] = None) -> dict:
    """Get summary of token usage over recent period."""
    if db is None:
        db = Database()
    return db.get_token_summary(agent_name, since=int(time.time()) - days * 86400)


def get_trend_analysis(agent_name: str = "", db: Optional[Database] = None) -> dict:
    """Compare recent period vs baseline period for trend detection."""
    if db is None:
        db = Database()
    now = int(time.time())

    # Recent: last 24h
    recent_since = now - 86400
    # Baseline: 7-14 days ago (before the recent window)
    baseline_since = now - 14 * 86400

    recent = db.get_token_summary(agent_name, since=recent_since)
    baseline = db.get_token_summary(agent_name, since=baseline_since)

    # Compute growth
    growth_pct = 0
    if baseline.get("avg_tokens", 0) > 0:
        growth_pct = round(
            ((recent.get("avg_tokens", 0) - baseline.get("avg_tokens", 0))
             / baseline.get("avg_tokens", 0)) * 100, 1
        )

    # Component growth
    comp_growth = {}
    if baseline.get("components"):
        for comp, val in recent.get("components", {}).items():
            bval = baseline.get("components", {}).get(comp, 0)
            if bval > 0:
                comp_growth[comp] = round((val - bval) / bval * 100, 1)
            else:
                comp_growth[comp] = 0

    return {
        "recent_avg": recent.get("avg_tokens", 0),
        "baseline_avg": baseline.get("avg_tokens", 0),
        "growth_pct": growth_pct,
        "component_growth": comp_growth,
        "recent_turns": recent.get("turns", 0),
        "baseline_turns": baseline.get("turns", 0),
    }


def get_daily_trends(agent_name: str = "", days: int = 14) -> list[dict]:
    """Get per-day aggregated token usage. Returns list of {label, total, components...}."""
    import datetime
    db = Database()
    conn = db._get_conn()
    now = int(time.time())
    since = now - days * 86400

    if agent_name:
        rows = conn.execute(
            "SELECT skills_tokens, memory_tokens, tools_tokens, guidance_tokens, "
            "identity_tokens, input_tokens, output_tokens, cache_read_tokens, "
            "cache_creation_tokens, recorded_at "
            "FROM token_logs WHERE agent_name=? AND recorded_at>=? ORDER BY recorded_at",
            (agent_name, since)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT skills_tokens, memory_tokens, tools_tokens, guidance_tokens, "
            "identity_tokens, input_tokens, output_tokens, cache_read_tokens, "
            "cache_creation_tokens, recorded_at "
            "FROM token_logs WHERE recorded_at>=? ORDER BY recorded_at",
            (since,)
        ).fetchall()

    if not rows:
        return []

    # Bucket by day
    from collections import defaultdict
    day_buckets = defaultdict(lambda: {
        "total": 0, "skills": 0, "memory": 0, "tools": 0,
        "guidance": 0, "identity": 0, "turns": 0
    })

    for r in rows:
        rd = dict(r) if hasattr(r, 'keys') else r
        ts = rd["recorded_at"]
        # Convert to date string
        day = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

        comp_total = (
            (rd.get("input_tokens", 0) or 0)
            + (rd.get("output_tokens", 0) or 0)
            + (rd.get("cache_read_tokens", 0) or 0)
            + (rd.get("cache_creation_tokens", 0) or 0)
        )
        day_buckets[day]["total"] += comp_total
        day_buckets[day]["skills"] += rd.get("skills_tokens", 0) or 0
        day_buckets[day]["memory"] += rd.get("memory_tokens", 0) or 0
        day_buckets[day]["tools"] += rd.get("tools_tokens", 0) or 0
        day_buckets[day]["guidance"] += rd.get("guidance_tokens", 0) or 0
        day_buckets[day]["identity"] += rd.get("identity_tokens", 0) or 0
        day_buckets[day]["turns"] += 1

    # Fill gaps and sort
    result = []
    first = datetime.datetime.fromtimestamp(rows[0]["recorded_at"])
    last = datetime.datetime.fromtimestamp(rows[-1]["recorded_at"])
    current = first
    while current <= last:
        day_key = current.strftime("%Y-%m-%d")
        b = day_buckets.get(day_key, {
            "total": 0, "skills": 0, "memory": 0, "tools": 0,
            "guidance": 0, "identity": 0, "turns": 0
        })
        # Day label like "Mon 12" or "Jun 10"
        short_label = current.strftime("%a %d")
        result.append({
            "label": short_label,
            "date": day_key,
            "total": b["total"],
            "skills": b["skills"],
            "memory": b["memory"],
            "tools": b["tools"],
            "guidance": b["guidance"],
            "identity": b["identity"],
            "turns": b["turns"],
        })
        current += datetime.timedelta(days=1)

    return result