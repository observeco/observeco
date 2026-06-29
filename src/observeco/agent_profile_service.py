"""agent_profile_service.py — Unified Agent Data Model (T4).

Provides a single composite query layer that reads from multiple tables
and returns a unified agent profile payload. This replaces the N+1 query
pattern where each dashboard tab makes separate API calls.

Cache: 5s TTL in-memory to avoid hammering pulse.db on rapid tab switches.
"""

import time
import threading
from typing import Optional

# In-memory cache: {agent_name: (timestamp, payload)}
_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
CACHE_TTL = 5  # seconds


def get_agent_profile(db, agent_name: str) -> dict:
    """Return a composite payload for a single agent.

    Reads from: pulse_log, errors, chisel_trims, chisel_drift,
    clawforge_garden, circuit_breakers, agent_configs, token_logs,
    heal_events.

    Returns dict with keys: health, tokens, errors, drift, garden,
    circuit, config, token_summary, heal_summary, cached_at.
    """
    cached = _cache_get(agent_name)
    if cached is not None:
        return cached

    now = int(time.time())

    # ── Health ──
    pulses = db.get_recent_pulses(agent_name=agent_name, limit=24)
    agent_status = "unknown"
    ever_alive = False
    if pulses:
        agent_status = pulses[0].get("status", "unknown")
        all_pulses = db.get_recent_pulses(agent_name=agent_name, limit=1000)
        ever_alive = any(p.get("status") == "alive" for p in all_pulses)

    if agent_status == "dead" and not ever_alive:
        agent_status = "not_running"

    health = {
        "status": agent_status,
        "last_check": pulses[0].get("timestamp", 0) if pulses else 0,
        "latency_ms": pulses[0].get("latency_ms", 0) if pulses else 0,
        "pulse_count_24h": len(pulses),
        "ever_alive": ever_alive,
        "recent_pulses": pulses[:5],  # last 5 for timeline
    }

    # ── Errors ──
    errors = db.get_errors(agent_name=agent_name, limit=20)
    errors_24h = [e for e in errors if now - e.get("timestamp", 0) < 86400]
    error_types = {}
    for e in errors_24h:
        etype = e.get("error_type", "unknown")
        error_types[etype] = error_types.get(etype, 0) + 1

    error_summary = {
        "count_24h": len(errors_24h),
        "by_type": error_types,
        "latest": errors_24h[:3],
    }

    # ── Tokens ──
    trims = db.get_trims(agent_name=agent_name, limit=5)
    drift = db.get_drift(agent_name=agent_name)

    token_breakdown = {}
    if trims:
        latest = trims[0]
        token_breakdown = {
            "identity": latest.get("identity_tokens", 0),
            "skills": latest.get("skills_tokens", 0),
            "memory": latest.get("memory_tokens", 0),
            "tools": latest.get("tools_tokens", 0),
            "guidance": latest.get("guidance_tokens", 0),
            "total": latest.get("total_tokens", 0),
        }

    drift_summary = {}
    if drift:
        drift_summary = {
            "components": {d.get("component", "unknown"): d.get("delta_pct", 0) for d in drift},
            "breached": any(d.get("breached", False) for d in drift),
        }

    # ── Token cost ──
    try:
        conn = db._get_conn()
        row = conn.execute(
            "SELECT SUM(cost) as total_cost, COUNT(*) as turn_count, "
            "MAX(created_at) as last_turn "
            "FROM token_logs WHERE agent_name = ?",
            (agent_name,),
        ).fetchone()
        token_summary = {
            "total_cost": row[0] or 0,
            "turn_count": row[1] or 0,
            "last_turn": row[2] or 0,
        }
    except Exception:
        token_summary = {"total_cost": 0, "turn_count": 0, "last_turn": 0}

    # ── Circuit ──
    circuit_breakers = {b["agent_name"]: b for b in db.get_circuit_breakers()}
    circuit = circuit_breakers.get(agent_name, {})
    circuit_summary = {
        "tripped": circuit.get("tripped", False),
        "failure_count": circuit.get("failure_count", 0),
        "cooldown_until": circuit.get("cooldown_until", 0),
    }

    # ── Garden (memory health) ──
    garden = db.get_gardens(agent_name=agent_name)
    garden_summary = {
        "scan_count": len(garden),
        "latest_debt_score": garden[0].get("debt_score", 0) if garden else 0,
        "duplicates": garden[0].get("duplicate_count", 0) if garden else 0,
        "contradictions": garden[0].get("contradiction_count", 0) if garden else 0,
    }

    # ── Heal events ──
    try:
        conn = db._get_conn()
        heals = conn.execute(
            "SELECT COUNT(*) as count, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count, "
            "AVG(duration_ms) as avg_duration "
            "FROM heal_events WHERE agent_name = ?",
            (agent_name,),
        ).fetchone()
        heal_summary = {
            "total_events": heals[0] or 0,
            "success_count": heals[1] or 0,
            "avg_duration_ms": round(heals[2] or 0, 1),
        }
    except Exception:
        heal_summary = {"total_events": 0, "success_count": 0, "avg_duration_ms": 0}

    # ── Agent config ──
    agents_cfg = {a["agent_name"]: a for a in db.get_agents()}
    cfg = agents_cfg.get(agent_name, {})
    config = {
        "framework": cfg.get("framework", ""),
        "type": cfg.get("type", "agent"),
        "health_url": cfg.get("health_url", ""),
        "health_cmd": cfg.get("health_cmd", ""),
        "source": cfg.get("source", ""),
    }

    # ── Compose ──
    payload = {
        "agent_name": agent_name,
        "health": health,
        "token_breakdown": token_breakdown,
        "drift": drift_summary,
        "errors": error_summary,
        "garden": garden_summary,
        "circuit": circuit_summary,
        "config": config,
        "token_summary": token_summary,
        "heal_summary": heal_summary,
        "cached_at": now,
    }

    _cache_set(agent_name, payload)
    return payload


def _cache_get(agent_name: str) -> Optional[dict]:
    with _cache_lock:
        entry = _cache.get(agent_name)
        if entry is None:
            return None
        ts, payload = entry
        if time.time() - ts > CACHE_TTL:
            del _cache[agent_name]
            return None
        # Return cached but mark as cached
        payload = dict(payload)
        payload["_cache_hit"] = True
        return payload


def _cache_set(agent_name: str, payload: dict) -> None:
    with _cache_lock:
        _cache[agent_name] = (time.time(), payload)


def invalidate_cache(agent_name: Optional[str] = None) -> None:
    """Invalidate the cache, optionally for a specific agent."""
    with _cache_lock:
        if agent_name:
            _cache.pop(agent_name, None)
        else:
            _cache.clear()
