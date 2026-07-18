"""agent_profile_service.py — Unified Agent Data Model (§3.T4).

Provides a single get_agent_profile() function that returns a composite payload
for any agent, aggregating data from all existing tables. Powers the unified
/api/agent/{name}/profile endpoint.

Design:
- Single function, single SQLite connection, all queries in one transaction
- Optional in-memory cache with configurable TTL (default: 5s)
- Graceful degradation: missing tables or empty data → null/empty, never errors
"""

from __future__ import annotations

import time
from typing import Optional

from observeco.db import Database, DB_PATH


# In-memory cache: {agent_name: (timestamp, payload)}
_profile_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 5.0  # seconds


def get_agent_profile(
    agent_name: str,
    db: Optional[Database] = None,
    use_cache: bool = True,
    cache_ttl: float = CACHE_TTL,
) -> dict:
    """Return a unified profile payload for a single agent.

    Args:
        agent_name: The agent to query.
        db: Optional Database instance (creates one if not provided).
        use_cache: Whether to use the in-memory cache.
        cache_ttl: Cache TTL in seconds.

    Returns:
        Dict with keys: agent, health, tokens, memory, heal, alerts, meta.
        Returns {"error": "agent_not_found", "agent_name": agent_name}
        if the agent is not registered.
    """
    # --- Cache check ---
    if use_cache and agent_name in _profile_cache:
        ts, payload = _profile_cache[agent_name]
        if time.monotonic() - ts < cache_ttl:
            return payload

    # --- DB setup ---
    if db is None:
        db = Database(DB_PATH)
    close_on_exit = db is None

    try:
        profile = _build_profile(agent_name, db)

        # Cache the result
        if use_cache:
            _profile_cache[agent_name] = (time.monotonic(), profile)

        return profile
    finally:
        if close_on_exit and db is not None:
            db.close()


def invalidate_cache(agent_name: Optional[str] = None) -> None:
    """Invalidate the profile cache.

    Args:
        agent_name: If provided, only invalidate that agent.
                   If None, invalidate all.
    """
    if agent_name:
        _profile_cache.pop(agent_name, None)
    else:
        _profile_cache.clear()


def _build_profile(agent_name: str, db: Database) -> dict:
    """Assemble the composite profile from all data sources."""
    now = int(time.time())

    # --- 1. Agent existence check ---
    agents = db.get_agents()
    agent_info = next((a for a in agents if a["agent_name"] == agent_name), None)
    if agent_info is None:
        return {"error": "agent_not_found", "agent_name": agent_name}

    # --- 2. Health layer ---
    pulses = db.get_recent_pulses(agent_name=agent_name, limit=24)
    errors = db.get_errors(agent_name=agent_name, limit=20)
    circuit_breakers = db.get_circuit_breakers()
    circuit = next((c for c in circuit_breakers if c["agent_name"] == agent_name), {})

    # Filter errors to last 24h
    errors_24h = [e for e in errors if now - e.get("timestamp", 0) < 86400]

    # Derive status from most recent pulse
    agent_status = "unknown"
    if pulses:
        agent_status = pulses[0].get("status", "unknown")

    # Distinguish "dead" (was alive, went down) from "never alive"
    ever_alive = any(p.get("status") == "alive" for p in pulses)
    if agent_status == "dead" and not ever_alive:
        agent_status = "not_running"

    health = {
        "status": agent_status,
        "ever_alive": ever_alive,
        "last_pulse_at": pulses[0].get("timestamp") if pulses else None,
        "pulse_history_24h": [
            {
                "timestamp": p.get("timestamp"),
                "status": p.get("status"),
                "latency_ms": p.get("latency_ms"),
            }
            for p in pulses[:24]
        ],
        "error_count_24h": len(errors_24h),
        "error_types": _count_error_types(errors_24h),
        "circuit_breaker": {
            "tripped": circuit.get("tripped", False),
            "failures": circuit.get("failures", 0),
            "max_retries": circuit.get("max_retries", 3),
            "cooldown_until": circuit.get("cooldown_until"),
        } if circuit else None,
    }

    # --- 3. Token layer ---
    try:
        trims = db.get_trims(agent_name=agent_name, limit=10)
    except Exception:
        trims = []
    try:
        drift = db.get_drift(agent_name=agent_name)
    except Exception:
        drift = []
    try:
        token_summary = db.get_token_summary(agent_name=agent_name)
    except Exception:
        token_summary = {}

    latest_trim = trims[0] if trims else {}
    tokens = {
        "latest_breakdown": {
            "identity": latest_trim.get("identity"),
            "skills": latest_trim.get("skills"),
            "memory": latest_trim.get("memory"),
            "tools": latest_trim.get("tools"),
            "guidance": latest_trim.get("guidance"),
            "total": sum(
                latest_trim.get(k, 0) or 0
                for k in ["identity", "skills", "memory", "tools", "guidance"]
            ),
        },
        "drift_trends": [
            {
                "component": d.get("component"),
                "current_tokens": d.get("current"),
                "previous_tokens": d.get("previous"),
                "delta": d.get("delta"),
                "delta_pct": d.get("delta_pct"),
            }
            for d in drift[:5]
        ] if drift else [],
        "token_summary": token_summary,
    }

    # --- 4. Memory layer ---
    try:
        gardens = db.get_gardens(agent_name=agent_name)
    except Exception:
        gardens = []
    try:
        profiles = db.get_profiles(agent_name=agent_name)
    except Exception:
        profiles = []

    latest_garden = gardens[0] if gardens else {}
    latest_profile = profiles[0] if profiles else {}
    memory = {
        "garden": {
            "debt_score": latest_garden.get("debt_score"),
            "duplicates": latest_garden.get("duplicates"),
            "contradictions": latest_garden.get("contradictions"),
            "stale_entries": latest_garden.get("stale_entries"),
            "scanned_at": latest_garden.get("scanned_at"),
        } if latest_garden else None,
        "profile": {
            "memory_size": latest_profile.get("memory_size"),
            "skill_count": latest_profile.get("skills"),
            "identity_size": latest_profile.get("identity"),
            "recorded_at": latest_profile.get("recorded_at"),
        } if latest_profile else None,
    }

    # --- 5. Heal layer ---
    try:
        heal_events = db.get_heal_events(agent_name=agent_name, limit=20)
    except Exception:
        heal_events = []
    try:
        heal_config = db.get_heal_config(agent_name=agent_name)
    except Exception:
        heal_config = []

    heal = {
        "events": [
            {
                "timestamp": e.get("created_at"),
                "event_type": e.get("event_type"),
                "status": e.get("status"),
                "duration_ms": e.get("duration_ms"),
                "details": e.get("details"),
            }
            for e in heal_events[:20]
        ],
        "auto_heal_enabled": heal_config[0].get("auto_heal", False) if heal_config else False,
        "config": heal_config[0] if heal_config else None,
        "recent_recoveries": sum(
            1 for e in heal_events if e.get("status") == "success"
        ) if heal_events else 0,
    }

    # --- 6. Meta ---
    raw_fw = (agent_info.get("framework", "") or "")
    fw_parts = [p.strip().capitalize() for p in raw_fw.split("+")] if raw_fw else []
    framework = " + ".join(fw_parts) if fw_parts else ""

    meta = {
        "agent_name": agent_name,
        "framework": framework,
        "agent_type": agent_info.get("agent_type", "agent"),
        "first_seen": agent_info.get("first_seen"),
        "last_seen": agent_info.get("last_seen"),
        "profile_generated_at": int(time.time()),
        "data_sources": _list_available_sources(trims, drift, gardens, profiles, heal_events),
    }

    return {
        "agent": meta,
        "health": health,
        "tokens": tokens,
        "memory": memory,
        "heal": heal,
    }


def _count_error_types(errors: list[dict]) -> dict[str, int]:
    """Count errors by type."""
    counts: dict[str, int] = {}
    for e in errors:
        etype = e.get("error_type", "unknown")
        counts[etype] = counts.get(etype, 0) + 1
    return counts


def _list_available_sources(
    trims: list,
    drift: list,
    gardens: list,
    profiles: list,
    heal_events: list,
) -> dict[str, bool]:
    """Report which data sources have data."""
    return {
        "tokens": len(trims) > 0,
        "drift": len(drift) > 0,
        "garden": len(gardens) > 0,
        "profile": len(profiles) > 0,
        "heal": len(heal_events) > 0,
    }
