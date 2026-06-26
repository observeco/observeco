"""L2 Baseline Engine — rolling baselines from stored history.

Computes and caches L2 baselines for trend detection.
CLI: observeco l2 baseline --agent <name> / --all
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

from observeco.db import Database
from observeco.dirs import get_data_dir

logger = logging.getLogger(__name__)

BASELINE_CACHE = get_data_dir() / "l2_baselines.json"


def compute_baselines(agent_name: str = "", days: int = 7,
                      db: Optional[Database] = None) -> dict:
    """Compute baselines and optionally cache them."""
    if db is None:
        db = Database()
    return db.compute_l2_baselines(agent_name, days)


def compute_all_baselines(days: int = 7, db: Optional[Database] = None) -> dict:
    """Compute baselines for all agents and cache to file."""
    if db is None:
        db = Database()
    agents = db.get_agents()
    results = {}
    for agent in agents:
        name = agent.get("agent_name", "")
        if name:
            try:
                results[name] = db.compute_l2_baselines(name, days)
            except Exception as e:
                results[name] = {"error": str(e)}
    # Cache
    _cache_baselines(results)
    return results


def _cache_baselines(data: dict) -> None:
    """Write baselines to cache file for L2 trigger decisions."""
    try:
        BASELINE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_CACHE.write_text(json.dumps({
            "baselines": data,
            "computed_at": int(time.time()),
        }, indent=2))
    except Exception as e:
        logger.warning(f"Failed to cache baselines: {e}")


def load_cached_baselines() -> dict:
    """Load baselines from cache file."""
    try:
        if BASELINE_CACHE.exists():
            data = json.loads(BASELINE_CACHE.read_text())
            return data.get("baselines", {})
    except Exception:
        pass
    return {}


def format_baseline_report(agent_name: str, baseline: dict) -> str:
    """Format a single agent's baseline for CLI display."""
    lines = [
        f"Agent: {agent_name}",
        f"  Samples: {baseline.get('sample_days', '?')} days",
        f"  Latency baseline: {baseline.get('latency_baseline_ms', 0):.0f}ms",
        f"  P95 latency: {baseline.get('p95_latency_ms', 0):.0f}ms",
        f"  Avg tokens/turn: {baseline.get('avg_token_per_turn', 0):.0f}",
        f"  Total turns: {baseline.get('total_turns', 0)}",
        f"  Error rate/day: {baseline.get('error_rate_per_day', 0)}",
        f"  Upstream errors: {baseline.get('upstream_error_count', 0)}",
    ]
    return "\n".join(lines)
