"""ObserveCo public API — REST endpoints for third-party integrations.

API v1 endpoints:
- GET /api/v1/fleet — fleet status overview
- GET /api/v1/agents — list all agents
- GET /api/v1/agents/{id} — agent details
- GET /api/v1/agents/{id}/health — agent health history
- GET /api/v1/agents/{id}/errors — agent error history
- GET /api/v1/agents/{id}/tokens — token usage breakdown
- POST /api/v1/events — ingest events from external sources
- GET /api/v1/events — list recent events
- GET /api/v1/risks — risk classification summary
- POST /api/v1/risks/classify — classify a tool call
- GET /api/v1/doctor/diagnostics — run diagnostics
- GET /api/v1/health — API health check

Authentication: Bearer token via Authorization header.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request

from observeco.db import Database

router = APIRouter(prefix="/api/v1", tags=["v1"])
db = Database()

# Token store — persists to file for multi-process access

_API_TOKENS_FILE = Path(os.environ.get("OBSERVECO_DATA_DIR", "~/.observeco")) / ".api_tokens.json"
API_TOKENS: dict[str, dict] = {}

# Encryption key from OS keychain (or generated once)
_SERVICE_NAME = "observeco-api-tokens"
_ENCRYPTION_KEY: bytes = b""


def _keyring_get_with_timeout(service: str, key: str) -> str | None:
    """Read a keyring secret with a hard timeout.

    macOS Keychain (keyring.backends.macOS) calls Security.framework
    directly and HANGS indefinitely in headless contexts — there is no GUI
    security session to authorize the keychain unlock, so the call blocks on
    mach_msg forever. A bare try/except never fires because it doesn't raise,
    it deadlocks. We isolate the call in a child process and kill it on
    timeout so headless hosts fall through to the machine-id fallback.
    ponytail: ceiling = 3s hard kill per call; if keyring is genuinely needed
    on a headless box, mount the login keychain or set OBSERVECO_MACHINE_ID.
    """
    import multiprocessing

    def _target(q: "multiprocessing.Queue") -> None:
        try:
            import keyring
            q.put(keyring.get_password(service, key))
        except Exception:
            q.put(None)

    q: multiprocessing.Queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_target, args=(q,), daemon=True)
    p.start()
    p.join(timeout=3)
    if p.is_alive():
        p.kill()
        return None
    try:
        return q.get_nowait()
    except Exception:
        return None


def _keyring_set_with_timeout(service: str, key: str, value: str) -> bool:
    """Set a keyring secret with a hard timeout (mirror of the get guard)."""
    import multiprocessing

    def _target() -> None:
        try:
            import keyring
            keyring.set_password(service, key, value)
        except Exception:
            pass

    p = multiprocessing.Process(target=_target, daemon=True)
    p.start()
    p.join(timeout=3)
    if p.is_alive():
        p.kill()
        return False
    return True


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from OS keychain."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY:
        return _ENCRYPTION_KEY

    try:
        import keyring  # noqa: F401  (ensures backend import side-effects)
        stored = _keyring_get_with_timeout(_SERVICE_NAME, "_encryption_key")
        if stored:
            _ENCRYPTION_KEY = bytes.fromhex(stored)
            return _ENCRYPTION_KEY
        # Generate new key
        import secrets
        _ENCRYPTION_KEY = secrets.token_bytes(32)
        _keyring_set_with_timeout(_SERVICE_NAME, "_encryption_key", _ENCRYPTION_KEY.hex())
        return _ENCRYPTION_KEY
    except Exception:
        # Fallback: derive from machine-id (not truly secure, but better than plaintext)
        import hashlib
        machine_id = os.environ.get("OBSERVECO_MACHINE_ID", "observeco-default")
        _ENCRYPTION_KEY = hashlib.sha256(machine_id.encode()).digest()
        return _ENCRYPTION_KEY


def _encrypt(data: str) -> str:
    """XOR encrypt with key (simple but better than plaintext)."""
    key = _get_encryption_key()
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data.encode()))
    return encrypted.hex()


def _decrypt(data: str) -> str:
    """XOR decrypt."""
    key = _get_encryption_key()
    raw = bytes.fromhex(data)
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return decrypted.decode()


def _load_tokens():
    """Load tokens from encrypted file."""
    global API_TOKENS
    try:
        if _API_TOKENS_FILE.exists():
            encrypted = json.loads(_API_TOKENS_FILE.read_text())
            API_TOKENS = {}
            for token_key, value in encrypted.items():
                try:
                    decrypted_key = _decrypt(token_key)
                    decrypted_value = {k: _decrypt(v) if isinstance(v, str) else v
                                       for k, v in value.items()}
                    API_TOKENS[decrypted_key] = decrypted_value
                except Exception:
                    # Unencrypted fallback for migration
                    API_TOKENS[token_key] = value
    except Exception:
        pass


def _save_tokens():
    """Save tokens to encrypted file."""
    try:
        _API_TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        encrypted = {}
        for token_key, value in API_TOKENS.items():
            enc_key = _encrypt(token_key)
            enc_value = {k: _encrypt(v) if isinstance(v, str) else v
                         for k, v in value.items()}
            encrypted[enc_key] = enc_value
        _API_TOKENS_FILE.write_text(json.dumps(encrypted, indent=2))
    except Exception:
        pass


_load_tokens()


def _verify_auth(authorization: str = Header(None)) -> dict:
    """Verify Bearer token authentication."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    token = authorization[7:]
    if token not in API_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid token")
    return API_TOKENS[token]


# --- Fleet endpoints ---

@router.get("/fleet")
async def fleet_status(authorization: str = Header(None)):
    """Get fleet status overview — all agents, health, token usage."""
    _verify_auth(authorization)
    agents = db.get_agents()
    summary = db.get_agent_status_summary()

    fleet = []
    alive = dead = 0
    for agent in agents:
        name = agent.get("agent_name", agent.get("name", ""))
        s = summary.get(name, {})
        status = s.get("status", "unknown")
        if status == "alive":
            alive += 1
        elif status == "dead":
            dead += 1
        fleet.append({
            "name": name,
            "framework": agent.get("framework", "unknown"),
            "status": status,
            "latency_ms": s.get("latency_ms", 0),
            "last_check": s.get("timestamp", ""),
            "circuit_tripped": s.get("circuit_tripped", 0),
        })

    return {
        "total": len(agents),
        "alive": alive,
        "dead": dead,
        "errors": len(agents) - alive - dead,
        "agents": fleet,
    }


# --- Agent endpoints ---

@router.get("/agents")
async def list_agents(authorization: str = Header(None)):
    """List all registered agents."""
    _verify_auth(authorization)
    agents = db.get_agents()
    return {"agents": agents}


@router.get("/agents/{agent_name}")
async def get_agent(agent_name: str, authorization: str = Header(None)):
    """Get agent details."""
    _verify_auth(authorization)
    summary = db.get_agent_status_summary()
    s = summary.get(agent_name, {})
    if not s:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return {"name": agent_name, **s}


@router.get("/agents/{agent_name}/health")
async def agent_health(agent_name: str, limit: int = 50, authorization: str = Header(None)):
    """Get agent health history."""
    _verify_auth(authorization)
    pulses = db.get_recent_pulses(agent_name, limit=limit)
    return {"agent": agent_name, "pulses": pulses}


@router.get("/agents/{agent_name}/errors")
async def agent_errors(agent_name: str, limit: int = 50, authorization: str = Header(None)):
    """Get agent error history."""
    _verify_auth(authorization)
    errors = db.get_errors(agent_name, limit=limit)
    return {"agent": agent_name, "errors": errors}


@router.get("/agents/{agent_name}/tokens")
async def agent_tokens(agent_name: str, authorization: str = Header(None)):
    """Get token usage breakdown."""
    _verify_auth(authorization)
    try:
        conn = db._get_conn()
        row = conn.execute(
            "SELECT * FROM chisel_trims WHERE agent_name=? ORDER BY timestamp DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        if row:
            return {"agent": agent_name, "tokens": dict(row)}
    except Exception:
        pass
    return {"agent": agent_name, "tokens": None}


# --- Events endpoints ---

@router.post("/events")
async def ingest_event(request: Request, authorization: str = Header(None)):
    """Ingest an event from an external source (OEF format)."""
    _verify_auth(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Validate OEF format
    required = ["event_type", "agent_id"]
    for field in required:
        if not body.get(field):
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")

    # Log to session log — with DLQ fallback on failure
    try:
        from observeco.session_log import SessionLogger
        session_logger = SessionLogger()
        session_logger.log(
            event_type=body["event_type"],
            data=body.get("payload", {}),
            agent_id=body["agent_id"],
            risk_level=body.get("payload", {}).get("risk_level", ""),
        )
    except Exception as e:
        # Event failed to process — save to dead letter queue for retry
        try:
            db.dlq_add(
                event_type=body["event_type"],
                agent_id=body["agent_id"],
                payload=body.get("payload", {}),
                error=str(e),
            )
        except Exception:
            pass  # If DLQ itself fails, log and continue
        import logging as _log
        _log.getLogger(__name__).error(f"Event ingestion failed (saved to DLQ): {e}")

    return {"status": "accepted", "event_type": body["event_type"]}


@router.get("/events")
async def list_events(limit: int = 50, authorization: str = Header(None)):
    """List recent events."""
    _verify_auth(authorization)
    try:
        from observeco.session_log import SessionLogger
        logger = SessionLogger()
        entries = logger.get_entries(limit=limit)
        return {"events": entries}
    except Exception:
        return {"events": []}


# --- Risk endpoints ---

@router.get("/risks")
async def risk_summary(authorization: str = Header(None)):
    """Get risk classification summary."""
    _verify_auth(authorization)
    from observeco.risk_engine import RISK_EMOJI, RiskLevel
    levels = {}
    for level in RiskLevel:
        levels[level.value] = {"emoji": RISK_EMOJI[level], "count": 0}
    return {"risk_levels": levels, "policy": "low=auto, medium=configurable, high=flag, critical=deny"}


@router.post("/risks/classify")
async def classify_risk(request: Request, authorization: str = Header(None)):
    """Classify a tool call by risk level."""
    _verify_auth(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from observeco.risk_engine import ToolCall, classify_text_action, classify_tool_call

    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    action_text = body.get("action_text", "")

    if tool_name:
        tc = ToolCall(name=tool_name, arguments=tool_args)
        result = classify_tool_call(tc)
    elif action_text:
        result = classify_text_action(action_text)
    else:
        raise HTTPException(status_code=400, detail="Provide tool_name+tool_args or action_text")

    return {
        "risk_level": result.level.value,
        "category": result.category,
        "reason": result.reason,
        "action": result.action,
    }


# --- Doctor endpoint ---

@router.get("/doctor/diagnostics")
async def run_diagnostics(authorization: str = Header(None)):
    """Run environment diagnostics."""
    _verify_auth(authorization)
    from observeco.doctor.diagnostics import run_diagnostics as _run
    report = _run()
    return report.to_dict()


# --- Health check ---

@router.get("/health")
async def health():
    """API health check (no auth required)."""
    return {"status": "ok", "version": "0.1.0", "timestamp": int(time.time())}


# --- Dead Letter Queue ---

@router.get("/dlq")
async def dlq_list(limit: int = 50, authorization: str = Header(None)):
    """List pending dead letter queue entries."""
    _verify_auth(authorization)
    pending = db.dlq_get_pending(limit=limit)
    stats = db.dlq_stats()
    return {"stats": stats, "entries": pending}


@router.post("/dlq/{entry_id}/retry")
async def dlq_retry(entry_id: int, authorization: str = Header(None)):
    """Mark a DLQ entry as retried."""
    _verify_auth(authorization)
    db.dlq_mark_retried(entry_id)
    return {"status": "retried", "id": entry_id}


@router.post("/dlq/{entry_id}/resolve")
async def dlq_resolve(entry_id: int, authorization: str = Header(None)):
    """Mark a DLQ entry as resolved."""
    _verify_auth(authorization)
    db.dlq_mark_resolved(entry_id)
    return {"status": "resolved", "id": entry_id}


@router.post("/dlq/purge")
async def dlq_purge(older_than_days: int = 7, authorization: str = Header(None)):
    """Purge old DLQ entries."""
    _verify_auth(authorization)
    count = db.dlq_purge(older_than_days=older_than_days)
    return {"status": "purged", "count": count}
