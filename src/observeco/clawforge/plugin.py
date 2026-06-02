"""OpenClaw Runtime Plugin tracking — intent-aware context loading stats.

The actual plugin (@observeco/clawforge-plugin) runs inside OpenClaw's
ContextEngine. This module provides the backend API that stores and serves
per-turn loading stats to the ObserveCo dashboard.

Three hooks in OpenClaw's lifecycle:
  - bootstrap:   load minimal context at session start
  - ingest:      classify intent → load matching files
  - pre_response: estimate tokens → demote low-value content
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

INTENT_CLASSES = [
    "debug/error-fix",
    "status/health-check",
    "feature/build",
    "general/conversation",
    "research/explore",
    "config/setup",
]


def log_plugin_hook(agent_name: str, hook_point: str, intent_class: str = "",
                    sources_loaded: int = 0, sources_skipped: int = 0,
                    tokens_saved: int = 0, context_window_pct: float = 0,
                    plugin_name: str = "clawforge",
                    db: Optional[Database] = None) -> dict:
    """Log a plugin hook event from OpenClaw's ContextEngine.

    Args:
        agent_name: Which agent recorded this hook
        hook_point: 'bootstrap', 'ingest', or 'pre_response'
        intent_class: Classified intent (e.g. 'debug/error-fix')
        sources_loaded: Number of context sources loaded
        sources_skipped: Number of sources skipped by intent-aware loading
        tokens_saved: Estimated tokens saved by skipping
        context_window_pct: % of context window used (pre_response only)
        plugin_name: Plugin identifier
        db: Reuse existing DB connection

    Returns:
        The plugin tracking record dict
    """
    if db is None:
        db = Database()

    db.log_plugin_tracking(
        agent_name=agent_name,
        plugin_name=plugin_name,
        hook_point=hook_point,
        intent_class=intent_class,
        sources_loaded=sources_loaded,
        sources_skipped=sources_skipped,
        tokens_saved=tokens_saved,
        context_window_pct=context_window_pct,
    )

    return {
        "agent": agent_name,
        "hook": hook_point,
        "intent": intent_class,
        "loaded": sources_loaded,
        "skipped": sources_skipped,
        "saved": tokens_saved,
        "reduction_pct": round((sources_skipped / max(sources_loaded + sources_skipped, 1)) * 100, 1),
    }


def get_plugin_stats(agent_name: str = "",
                     db: Optional[Database] = None) -> dict:
    """Get aggregate plugin statistics."""
    if db is None:
        db = Database()
    return db.get_plugin_stats(agent_name)


def get_recent_hooks(agent_name: str = "", limit: int = 20,
                     db: Optional[Database] = None) -> list[dict]:
    """Get recent plugin hook records."""
    if db is None:
        db = Database()
    return db.get_plugin_tracking(agent_name, limit)


def seed_demo_data(db: Optional[Database] = None) -> int:
    """Seed demo plugin tracking data for the dashboard when real data is empty.

    Returns number of records seeded.
    """
    if db is None:
        db = Database()

    existing = db.get_plugin_stats()
    if existing.get("turns", 0) > 0:
        return 0  # Already has real data

    now = int(time.time())
    demo_agents = ["kepler", "hound"]
    demo_intents = [
        ("debug/error-fix", 2, 18, 4200, 15, 80),
        ("status/health-check", 1, 22, 6800, 8, 92),
        ("feature/build", 5, 15, 3100, 40, 60),
        ("general/conversation", 8, 10, 1800, 55, 45),
    ]
    count = 0
    for agent in demo_agents:
        for intent, loaded, skipped, saved, win_pct, red_pct in demo_intents:
            db.log_plugin_tracking(
                agent_name=agent,
                plugin_name="clawforge",
                hook_point="ingest",
                intent_class=intent,
                sources_loaded=loaded,
                sources_skipped=skipped,
                tokens_saved=saved,
                context_window_pct=win_pct,
            )
            count += 1
            time.sleep(0.001)  # Ensure distinct timestamps

    return count
