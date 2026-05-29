"""ObserveCo Telemetry Server — central feedback collector.

Expected env vars (on the server):
  OBSERVECO_TG_BOT_TOKEN, OBSERVECO_TG_CHAT_ID     # Telegram delivery to Sean
  OBSERVECO_SMTP_HOST, OBSERVECO_SMTP_PORT, ...     # Email fallback
  OBSERVECO_TELEMETRY_PORT=9120                      # default port
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from observeco.db import Database
from observeco.feedback_delivery import deliver_feedback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("observeco.telemetry")

app = FastAPI(title="ObserveCo Telemetry")
db = Database()


@app.post("/v1/feedback")
async def collect_feedback(request: Request):
    """Central feedback collector — accept from anywhere, deliver to Sean."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    if not body.get("summary"):
        return JSONResponse({"error": "missing summary"}, status_code=400)

    # Get sender IP for logging
    sender = request.client.host if request.client else "unknown"
    logger.info("Feedback from %s: %s", sender, body.get("summary", "")[:80])

    # Deliver to Sean via all configured channels
    delivery = deliver_feedback(body)

    # Persist
    db.save_feedback(
        body,
        delivered_tg=delivery.get("telegram", False),
        delivered_email=delivery.get("email", False),
    )

    logger.info(
        "Feedback stored. Delivery: Telegram=%s Email=%s",
        delivery.get("telegram", False),
        delivery.get("email", False),
    )

    return JSONResponse({
        "status": "ok",
        "delivery": delivery,
    })


@app.get("/v1/feedback")
async def list_feedback(limit: int = 50):
    """List recent feedback (for Sean to browse)."""
    items = db.get_feedback(limit=limit)
    return JSONResponse({"count": len(items), "items": items})


@app.get("/health")
async def health():
    """Simple health check for tunnel monitoring."""
    return JSONResponse({"status": "ok"})


@app.post("/v1/telemetry")
async def collect_telemetry(request: Request):
    """Central telemetry collector — automatic crash/usage/install pings."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    if not body.get("event"):
        return JSONResponse({"error": "missing event type"}, status_code=400)

    sender = request.client.host if request.client else "unknown"
    payload = body.get("payload", {})
    event = body.get("event", "unknown")
    logger.info(
        "Telemetry %s from %s: %s",
        event, sender,
        payload.get("message", payload.get("command", payload.get("feature", "")))[:60],
    )

    db.save_telemetry(body)

    # For error events, also create a feedback entry so Sean notices
    if event == "error":
        fb_payload = {
            "type": "crash",
            "type_label": "💥 Automatic Crash Report",
            "summary": f"Crash: {payload.get('type', 'Unknown')} — {payload.get('message', '')[:100]}",
            "detail": f"Command: {payload.get('command', '')}\n\nStack:\n```\n{payload.get('stack', '')}\n```",
            "severity": "🚫 Automatic — crash detected",
            "environment": {
                "observeco_version": body.get("version", ""),
                "os": body.get("os", ""),
                "machine_id": body.get("machine_id", "")[:8],
            },
        }
        delivery = deliver_feedback(fb_payload)
        db.save_feedback(
            fb_payload,
            delivered_tg=delivery.get("telegram", False),
            delivered_email=delivery.get("email", False),
        )
        logger.info("Crash feedback created. Delivery: Telegram=%s", delivery.get("telegram", False))

    return JSONResponse({"status": "ok"})


def serve() -> None:
    port = int(os.environ.get("OBSERVECO_TELEMETRY_PORT", "9120"))
    host = os.environ.get("OBSERVECO_TELEMETRY_HOST", "127.0.0.1")
    logger.info("Starting telemetry server on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
