"""Per-turn token tracking — webhook ingestion, budget thresholds, anomaly detection, trend analysis.

POST /api/tokens/log — receive token usage data from agents
GET  /api/tokens/summary — aggregate stats per agent
GET  /api/tokens/trends — component growth trends
POST /api/tokens/budget — set per-agent budgets
CLI: observeco tokens log / status / budget / trends
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

# Per-agent cost rates (per million input tokens)
PROVIDER_RATES = {
    "deepseek": 0.15,
    "claude": 3.00,
    "claude-sonnet": 3.00,
    "claude-haiku": 0.25,
    "openai": 2.50,
    "gpt-4": 10.00,
    "gpt-4o": 2.50,
    "gemini": 0.15,
    "ollama": 0.0,
    "custom": 0.15,
}


def compute_cost(total_tokens: int, provider: str) -> float:
    """Compute cost from token count and provider rate."""
    rate = PROVIDER_RATES.get(provider.lower(), 0.15)
    return round((total_tokens / 1_000_000) * rate, 6)


def compute_anomaly(total_tokens: int, agent_name: str,
                    db: Optional[Database] = None) -> Optional[float]:
    """Compute anomaly score: deviation from rolling avg in sigma units.
    Returns None if insufficient data, or float z-score."""
    if db is None:
        db = Database()

    # Get rolling average from last 50 turns
    turns = db.get_token_turns(agent_name, limit=50)
    if len(turns) < 5:
        return None  # Not enough data yet

    vals = [t["total_tokens"] for t in turns]
    avg = sum(vals) / len(vals)
    variance = sum((v - avg) ** 2 for v in vals) / len(vals)
    stddev = variance ** 0.5

    if stddev == 0:
        return None
    z_score = (total_tokens - avg) / stddev
    return round(z_score, 2)


def log_token_turn(agent_name: str, turn_id: str, total_tokens: int,
                   identity_tokens: int = 0, skills_tokens: int = 0,
                   memory_tokens: int = 0, tools_tokens: int = 0,
                   guidance_tokens: int = 0, provider: str = "",
                   db: Optional[Database] = None) -> dict:
    """Log a single turn's token usage. Computes cost and anomaly score."""
    if db is None:
        db = Database()

    cost = compute_cost(total_tokens, provider) if provider else 0
    anomaly = compute_anomaly(total_tokens, agent_name, db)

    result = db.log_token_turn(
        agent_name=agent_name, turn_id=turn_id,
        total_tokens=total_tokens,
        identity_tokens=identity_tokens, skills_tokens=skills_tokens,
        memory_tokens=memory_tokens, tools_tokens=tools_tokens,
        guidance_tokens=guidance_tokens,
        provider=provider, cost=cost, anomaly_score=anomaly,
    )

    # Check budget thresholds
    budgets = db.get_token_budgets(agent_name)
    triggered = []
    if budgets:
        b = budgets[0]
        if b.get("enabled"):
            if b.get("max_turn_cost") > 0 and cost > b["max_turn_cost"]:
                triggered.append(f"Turn cost ${cost:.4f} exceeds ${b['max_turn_cost']:.4f} limit")
            if anomaly and b.get("anomaly_threshold_sigma") > 0:
                if abs(anomaly) > b["anomaly_threshold_sigma"]:
                    triggered.append(f"Anomaly score {anomaly:.1f}σ exceeds {b['anomaly_threshold_sigma']:.1f}σ threshold")
            # Daily token check
            if b.get("max_daily_tokens") > 0:
                today_start = int(time.time()) - 86400
                today_tokens = db.get_token_summary(agent_name, since=today_start).get("total_tokens", 0)
                if today_tokens > b["max_daily_tokens"]:
                    triggered.append(f"Daily tokens {today_tokens} exceed {b['max_daily_tokens']} limit")

    return {
        "id": result["id"],
        "cost": cost,
        "anomaly_score": anomaly,
        "budget_alerts": triggered,
    }


def get_token_summary(agent_name: str = "", days: int = 7,
                      db: Optional[Database] = None) -> dict:
    """Get aggregate token summary for display."""
    if db is None:
        db = Database()
    since = int(time.time()) - days * 86400 if days > 0 else 0
    stats = db.get_token_summary(agent_name, since)

    # Component trends
    trends = db.get_token_trends(agent_name, days)
    stats["components"] = trends.get("components", {})
    stats["avg_per_turn"] = trends.get("avg_per_turn", 0)
    stats["turns"] = trends.get("turns", stats.get("turns", 0))

    return stats


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
