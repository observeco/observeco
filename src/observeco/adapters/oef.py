"""Standardized Event Format (OEF) — universal event schema for ObserveCo.

All channel adapters translate events into this format.
This is the single source of truth for event structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib
import hmac
import json
import uuid


@dataclass
class OEFEvent:
    """ObserveCo Event Format — standardized event structure."""
    event_type: str  # "tool_call" | "response" | "error" | "heartbeat" | "risk_alert" | "feedback"
    agent_id: str
    runtime: str  # "openclaw" | "claude-code" | "cursor" | "codex" | "crewai" | "langgraph" | "unknown"
    channel: str  # "slack" | "discord" | "telegram" | "webhook" | "cli" | "mcp"
    payload: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "observeco"

    def to_dict(self) -> dict:
        return {
            "version": "1.0",
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "runtime": self.runtime,
            "channel": self.channel,
            "payload": self.payload,
            "context": self.context,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OEFEvent":
        return cls(
            event_type=data.get("event_type", "unknown"),
            agent_id=data.get("agent_id", ""),
            runtime=data.get("runtime", "unknown"),
            channel=data.get("channel", "webhook"),
            payload=data.get("payload", {}),
            context=data.get("context", {}),
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            source=data.get("source", "unknown"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, data: str) -> "OEFEvent":
        return cls.from_dict(json.loads(data))

    def signature_payload(self) -> str:
        """Payload for HMAC signature (excludes event_id and timestamp)."""
        return json.dumps({
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "runtime": self.runtime,
            "channel": self.channel,
            "payload": self.payload,
        }, sort_keys=True, separators=(",", ":"))

    def sign(self, secret: str) -> str:
        """Compute HMAC-SHA256 signature."""
        return hashlib.sha256(
            f"{secret}{self.signature_payload()}".encode()
        ).hexdigest()

    @classmethod
    def verify_signature(cls, event_data: str, signature: str, secret: str) -> bool:
        """Verify HMAC-SHA256 signature.

        Args:
            event_data: The canonical signature_payload() string (not raw JSON)
            signature: The signature to verify (with or without 'sha256=' prefix)
            secret: The shared secret
        """
        # Strip prefix if present
        if signature.startswith("sha256="):
            signature = signature[7:]
        expected = hashlib.sha256(
            f"{secret}{event_data}".encode()
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


# --- Convenience constructors ---

def make_tool_call_event(
    agent_id: str,
    tool_name: str,
    tool_args: dict,
    risk_level: str,
    decision: str,
    runtime: str = "unknown",
    channel: str = "cli",
) -> OEFEvent:
    return OEFEvent(
        event_type="tool_call",
        agent_id=agent_id,
        runtime=runtime,
        channel=channel,
        payload={
            "tool_name": tool_name,
            "tool_args": tool_args,
            "risk_level": risk_level,
            "decision": decision,
        },
    )


def make_risk_alert_event(
    agent_id: str,
    tool_name: str,
    risk_level: str,
    reason: str,
    runtime: str = "unknown",
    channel: str = "cli",
) -> OEFEvent:
    return OEFEvent(
        event_type="risk_alert",
        agent_id=agent_id,
        runtime=runtime,
        channel=channel,
        payload={
            "tool_name": tool_name,
            "risk_level": risk_level,
            "reason": reason,
        },
    )


def make_error_event(
    agent_id: str,
    error_type: str,
    error_message: str,
    runtime: str = "unknown",
    channel: str = "cli",
) -> OEFEvent:
    return OEFEvent(
        event_type="error",
        agent_id=agent_id,
        runtime=runtime,
        channel=channel,
        payload={
            "error_type": error_type,
            "error_message": error_message,
        },
    )


def make_heartbeat_event(
    agent_id: str,
    status: str = "alive",
    latency_ms: float = 0,
    runtime: str = "unknown",
    channel: str = "cli",
) -> OEFEvent:
    return OEFEvent(
        event_type="heartbeat",
        agent_id=agent_id,
        runtime=runtime,
        channel=channel,
        payload={
            "status": status,
            "latency_ms": latency_ms,
        },
    )
