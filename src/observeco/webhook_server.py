"""Webhook ingestion server — translates platform webhooks into OEF events.

Receives webhooks from:
- Slack Events API (app_mention, message, etc.)
- Discord Interactions Endpoint (slash commands, PING)
- Telegram Bot API (messages, callback queries)

Each platform's webhook is translated to OEF format, then fed into the
event processing pipeline (risk engine → session log → alerts).

Environment variables:
    OBSERVECO_WEBHOOK_PORT — Port for the webhook server (default: 9120)
    OBSERVECO_WEBHOOK_HOST — Bind address (default: 0.0.0.0)
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from observeco.adapters.discord import DiscordAdapter
from observeco.adapters.oef import OEFEvent
from observeco.adapters.slack import SlackAdapter
from observeco.adapters.telegram import TelegramAdapter
from observeco.db import Database

logger = logging.getLogger(__name__)

app = FastAPI(title="ObserveCo Webhook Ingestion")
db = Database()

# Adapter instances (lazy-init from env)
_slack: Optional[SlackAdapter] = None
_discord: Optional[DiscordAdapter] = None
_telegram: Optional[TelegramAdapter] = None


def _get_slack() -> SlackAdapter:
    global _slack
    if _slack is None:
        _slack = SlackAdapter()
    return _slack


def _get_discord() -> DiscordAdapter:
    global _discord
    if _discord is None:
        _discord = DiscordAdapter()
    return _discord


def _get_telegram() -> TelegramAdapter:
    global _telegram
    if _telegram is None:
        _telegram = TelegramAdapter()
    return _telegram


# ---------------------------------------------------------------------------
# Event processing pipeline (§2.15 — processes OEF events end-to-end)
# ---------------------------------------------------------------------------

def process_event(event: OEFEvent) -> dict:
    """Process an OEF event through the full pipeline:
    1. Risk classification (if tool_call)
    2. Session log write
    3. Alert dispatch (if high/critical risk)
    4. Circuit breaker update (if error)

    Returns processing summary.
    """
    result = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "processed_at": int(time.time()),
        "steps": [],
    }

    # 1. Risk classification for tool calls
    risk_level = None
    if event.event_type == "tool_call":
        try:
            from observeco.risk_engine import ToolCall, classify_tool_call
            tool_name = event.payload.get("tool_name", "")
            tool_args = event.payload.get("tool_args", {})
            tc = ToolCall(name=tool_name, arguments=tool_args)
            classification = classify_tool_call(tc)
            risk_level = classification.level.value
            event.payload["risk_level"] = risk_level
            event.payload["decision"] = classification.action
            result["steps"].append(f"risk:{risk_level}")
        except Exception as e:
            logger.error(f"Risk classification failed: {e}")
            result["steps"].append("risk:error")

    # 2. Session log write
    try:
        from observeco.session_log import SessionLogger
        logger_inst = SessionLogger()
        logger_inst.log(
            event_type=event.event_type,
            data=event.payload,
            agent_id=event.agent_id,
            risk_level=risk_level or "",
        )
        result["steps"].append("session:logged")
    except Exception as e:
        logger.error(f"Session log write failed: {e}")
        result["steps"].append("session:error")
        # Save to DLQ
        try:
            db.dlq_add(
                event_type=event.event_type,
                agent_id=event.agent_id,
                payload=event.payload,
                error=str(e),
            )
            result["steps"].append("dlq:saved")
        except Exception:
            pass

    # 3. Alert dispatch for high/critical risk
    if risk_level in ("high", "critical"):
        try:
            _dispatch_alert(event, risk_level)
            result["steps"].append("alert:dispatched")
        except Exception as e:
            logger.error(f"Alert dispatch failed: {e}")
            result["steps"].append("alert:error")

    # 4. Circuit breaker update for errors
    if event.event_type == "error":
        try:
            _update_circuit_breaker(event)
            result["steps"].append("circuit:updated")
        except Exception as e:
            logger.error(f"Circuit breaker update failed: {e}")
            result["steps"].append("circuit:error")

    result["risk_level"] = risk_level
    return result


def _dispatch_alert(event: OEFEvent, risk_level: str) -> None:
    """Dispatch alert to all configured channels."""
    # Slack
    slack = _get_slack()
    if slack.is_configured():
        try:
            slack.send_event(event)
        except Exception as e:
            logger.error(f"Slack alert failed: {e}")

    # Discord
    discord = _get_discord()
    if discord.is_configured():
        try:
            discord.send_event(event)
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")

    # Telegram
    telegram = _get_telegram()
    if telegram.is_configured():
        try:
            telegram.send_event(event)
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")


def _update_circuit_breaker(event: OEFEvent) -> None:
    """Update circuit breaker state for error events."""
    agent_id = event.agent_id
    if not agent_id:
        return

    conn = db._get_conn()
    # Increment failure count
    conn.execute(
        """INSERT INTO circuit_breakers (agent_name, failure_count, last_failure, last_failure_error)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(agent_name) DO UPDATE SET
            failure_count = failure_count + 1,
            last_failure = excluded.last_failure,
            last_failure_error = excluded.last_failure_error""",
        (agent_id, event.timestamp, event.payload.get("error_message", "")),
    )

    # Check if breaker should trip (3 failures)
    row = conn.execute(
        "SELECT failure_count, max_retries FROM circuit_breakers WHERE agent_name=?",
        (agent_id,),
    ).fetchone()

    if row and row["failure_count"] >= row["max_retries"]:
        cooldown_until = int(time.time()) + 300  # 5 min cooldown
        conn.execute(
            "UPDATE circuit_breakers SET tripped=1, cooldown_until=? WHERE agent_name=?",
            (cooldown_until, agent_id),
        )
        logger.warning(f"Circuit breaker TRIPPED for {agent_id} (failures: {row['failure_count']})")

    conn.commit()


# ---------------------------------------------------------------------------
# Slack webhook endpoint
# ---------------------------------------------------------------------------

@app.post("/webhook/slack")
async def slack_webhook(request: Request):
    """Receive Slack Events API webhook."""
    body = await request.body()
    body_str = body.decode("utf-8")
    headers = {k: v for k, v in request.headers.items()}

    slack = _get_slack()

    # Handle URL verification challenge
    try:
        data = json.loads(body_str)
        if data.get("type") == "url_verification":
            return JSONResponse({"challenge": data.get("challenge", "")})
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Verify signature
    if not slack.verify_webhook(headers, body_str):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse event
    event = slack.receive_event(data)
    if event is None:
        return JSONResponse({"status": "ignored"})

    # Process through pipeline
    result = process_event(event)
    return JSONResponse({"status": "ok", "event_id": event.event_id, "pipeline": result})


# ---------------------------------------------------------------------------
# Discord webhook endpoint
# ---------------------------------------------------------------------------

@app.post("/webhook/discord")
async def discord_webhook(request: Request):
    """Receive Discord Interactions Endpoint webhook."""
    body = await request.body()
    body_str = body.decode("utf-8")
    headers = {k: v for k, v in request.headers.items()}

    discord = _get_discord()

    # Verify signature (Ed25519)
    if not discord.verify_webhook(headers, body_str):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(body_str)

    # Handle PING interaction
    if data.get("type") == 1:
        return JSONResponse(discord.build_pong_response(data.get("id", 0)))

    # Parse interaction
    event = discord.receive_event(data)
    if event is None:
        return JSONResponse({"status": "ignored"})

    # Process through pipeline
    result = process_event(event)
    return JSONResponse({"status": "ok", "event_id": event.event_id, "pipeline": result})


# ---------------------------------------------------------------------------
# Telegram webhook endpoint
# ---------------------------------------------------------------------------

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Receive Telegram Bot API webhook."""
    body = await request.body()
    body_str = body.decode("utf-8")
    headers = {k: v for k, v in request.headers.items()}

    telegram = _get_telegram()

    # Verify webhook secret
    if not telegram.verify_webhook(headers, body_str):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = json.loads(body_str)

    # Parse update
    event = telegram.receive_event(data)
    if event is None:
        return JSONResponse({"status": "ignored"})

    # Process through pipeline
    result = process_event(event)
    return JSONResponse({"status": "ok", "event_id": event.event_id, "pipeline": result})


# ---------------------------------------------------------------------------
# Generic webhook (OEF format)
# ---------------------------------------------------------------------------

@app.post("/webhook/oef")
async def oef_webhook(request: Request, authorization: str = Header(None)):
    """Receive events in OEF format from any source."""
    # Verify Bearer token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization[7:]
    try:
        from observeco.api import API_TOKENS
        if token not in API_TOKENS:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ImportError:
        pass

    body = await request.json()

    # Validate OEF format
    required = ["event_type", "agent_id"]
    for field in required:
        if not body.get(field):
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")

    event = OEFEvent.from_dict(body)

    # Process through pipeline
    result = process_event(event)
    return JSONResponse({"status": "ok", "event_id": event.event_id, "pipeline": result})


# ---------------------------------------------------------------------------
# Health + status
# ---------------------------------------------------------------------------

@app.get("/webhook/health")
async def webhook_health():
    """Webhook server health check."""
    return {
        "status": "ok",
        "adapters": {
            "slack": _get_slack().is_configured(),
            "discord": _get_discord().is_configured(),
            "telegram": _get_telegram().is_configured(),
        },
        "dlq": db.dlq_stats(),
    }


def run_webhook_server(host: str = "0.0.0.0", port: int = 9120):
    """Run the webhook ingestion server."""
    import uvicorn
    logger.info(f"Starting webhook ingestion server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
