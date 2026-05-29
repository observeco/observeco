"""Real-time streaming — WebSocket endpoint for live event streaming.

Provides:
- WebSocket connection for live event streaming
- Filtered streams (by agent, risk level, event type)
- SSE fallback for environments without WebSocket support
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class EventBroadcaster:
    """Broadcast events to connected WebSocket clients."""

    def __init__(self):
        self._clients: list[WebSocket] = []
        self._event_buffer: list[dict] = []
        self._max_buffer = 1000

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self._clients.append(websocket)
        logger.info(f"WebSocket client connected ({len(self._clients)} total)")

        # Send recent events to new client
        for event in self._event_buffer[-50:]:
            try:
                await websocket.send_json(event)
            except Exception:
                break

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client."""
        if websocket in self._clients:
            self._clients.remove(websocket)
        logger.info(f"WebSocket client disconnected ({len(self._clients)} total)")

    async def broadcast(self, event: dict):
        """Broadcast an event to all connected clients."""
        self._event_buffer.append(event)
        if len(self._event_buffer) > self._max_buffer:
            self._event_buffer = self._event_buffer[-self._max_buffer:]

        disconnected = []
        for client in self._clients:
            try:
                await client.send_json(event)
            except Exception:
                disconnected.append(client)

        for client in disconnected:
            self._clients.remove(client)

    @property
    def client_count(self) -> int:
        return len(self._clients)


# Global broadcaster instance
broadcaster = EventBroadcaster()


@router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    agent: Optional[str] = Query(None, description="Filter by agent ID"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """WebSocket endpoint for real-time event streaming.

    Query parameters for filtering:
    - agent: Filter by agent ID
    - risk_level: Filter by risk level (low, medium, high, critical)
    - event_type: Filter by event type (tool_call, risk_alert, error, heartbeat)
    """
    await broadcaster.connect(websocket)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # Client can send filter updates
                if msg.get("type") == "subscribe":
                    # Store filter preferences (future enhancement)
                    pass
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        broadcaster.disconnect(websocket)


@router.get("/api/v1/stream/sse")
async def sse_events(
    agent: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
):
    """Server-Sent Events endpoint for environments without WebSocket support."""
    async def event_generator():
        last_index = 0
        while True:
            # Check for new events
            if last_index < len(broadcaster._event_buffer):
                for event in broadcaster._event_buffer[last_index:]:
                    # Apply filters
                    if agent and event.get("agent_id") != agent:
                        continue
                    if risk_level and event.get("risk_level") != risk_level:
                        continue
                    if event_type and event.get("event_type") != event_type:
                        continue

                    yield f"data: {json.dumps(event)}\n\n"
                last_index = len(broadcaster._event_buffer)

            await asyncio.sleep(1)  # Poll every second

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/v1/stream/status")
async def stream_status():
    """Get streaming status."""
    return {
        "websocket_clients": broadcaster.client_count,
        "buffer_size": len(broadcaster._event_buffer),
        "buffer_limit": broadcaster._max_buffer,
    }


async def emit_event(event: dict):
    """Emit an event to all connected clients.

    Call this from anywhere in the app when an event occurs.
    """
    await broadcaster.broadcast(event)
