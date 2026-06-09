"""Discord adapter — send/receive ObserveCo events via Discord.

Supports:
- Sending alerts to Discord channels via Bot API
- Receiving Discord events via Interactions Endpoint (slash commands, messages)
- Verifying Discord request signatures (Ed25519)
- Rich embed notifications

Environment variables:
    OBSERVECO_DISCORD_BOT_TOKEN — Discord bot token
    OBSERVECO_DISCORD_PUBLIC_KEY — Application public key for signature verification
    OBSERVECO_DISCORD_ALERT_CHANNEL — Default channel ID for alerts
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Optional

from observeco.rate_limiter import get_rate_limiter

from .oef import OEFEvent

logger = logging.getLogger(__name__)


class DiscordAdapter:
    """Discord channel adapter for ObserveCo."""

    def __init__(
        self,
        bot_token: str = "",
        public_key: str = "",
        alert_channel: str = "",
    ):
        self.bot_token = bot_token or os.environ.get("OBSERVECO_DISCORD_BOT_TOKEN", "")
        self.public_key = public_key or os.environ.get("OBSERVECO_DISCORD_PUBLIC_KEY", "")
        self.alert_channel = alert_channel or os.environ.get("OBSERVECO_DISCORD_ALERT_CHANNEL", "")

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.public_key)

    # --- Sending ---

    def send_event(self, event: OEFEvent, channel_id: str = "") -> bool:
        """Send an ObserveCo event as a Discord embed."""
        if not self.bot_token:
            logger.warning("Discord send skipped — no bot token")
            return False

        target = channel_id or self.alert_channel
        if not target:
            logger.warning("Discord send skipped — no alert channel")
            return False

        embed = self._event_to_embed(event)
        payload = {"embeds": [embed]}

        return self._api_call(f"/channels/{target}/messages", payload, method="POST")

    def _event_to_embed(self, event: OEFEvent) -> dict:
        """Convert OEF event to Discord embed."""
        color_map = {
            "tool_call": 0x6366F1,     # Indigo
            "risk_alert": 0xF59E0B,    # Amber
            "error": 0xEF4444,         # Red
            "heartbeat": 0x10B981,     # Emerald
            "feedback": 0x8B5CF6,      # Violet
            "response": 0x8B5CF6,      # Violet
        }
        color = color_map.get(event.event_type, 0x6B7280)

        title = event.event_type.replace("_", " ").title()
        embed = {
            "title": f"📋 {title}",
            "color": color,
            "timestamp": event.timestamp,
            "footer": {"text": f"ObserveCo • {event.runtime}"},
        }

        fields = []
        fields.append({"name": "Agent", "value": event.agent_id, "inline": True})
        fields.append({"name": "Channel", "value": event.channel, "inline": True})

        if event.event_type == "tool_call":
            tool = event.payload.get("tool_name", "unknown")
            risk = event.payload.get("risk_level", "unknown")
            decision = event.payload.get("decision", "unknown")

            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(risk, "⚪")
            fields.append({"name": "Tool", "value": f"`{tool}`", "inline": True})
            fields.append({"name": "Risk", "value": f"{risk_emoji} {risk.upper()}", "inline": True})
            fields.append({"name": "Decision", "value": decision, "inline": True})

            args = event.payload.get("tool_args", {})
            if args:
                args_str = json.dumps(args, indent=2)[:1024]
                fields.append({"name": "Arguments", "value": f"```{args_str}```", "inline": False})

        elif event.event_type == "risk_alert":
            tool = event.payload.get("tool_name", "unknown")
            risk = event.payload.get("risk_level", "unknown")
            reason = event.payload.get("reason", "")
            fields.append({"name": "Tool", "value": f"`{tool}`", "inline": True})
            fields.append({"name": "Risk Level", "value": risk.upper(), "inline": True})
            fields.append({"name": "Reason", "value": reason, "inline": False})

        elif event.event_type == "error":
            error_type = event.payload.get("error_type", "unknown")
            error_msg = event.payload.get("error_message", "")[:1024]
            fields.append({"name": "Error Type", "value": error_type, "inline": True})
            fields.append({"name": "Message", "value": error_msg, "inline": False})

        elif event.event_type == "heartbeat":
            status = event.payload.get("status", "unknown")
            latency = event.payload.get("latency_ms", 0)
            status_emoji = "🟢" if status == "alive" else "🔴"
            fields.append({"name": "Status", "value": f"{status_emoji} {status}", "inline": True})
            fields.append({"name": "Latency", "value": f"{latency:.0f}ms", "inline": True})

        else:
            payload_str = json.dumps(event.payload, indent=2)[:1024]
            fields.append({"name": "Payload", "value": f"```{payload_str}```", "inline": False})

        embed["fields"] = fields
        return embed

    # --- Receiving ---

    def receive_event(self, raw: dict) -> Optional[OEFEvent]:
        """Parse a raw Discord interaction into OEF format."""
        interaction_type = raw.get("type", 0)

        # PING interaction (type 1)
        if interaction_type == 1:
            return None  # Handled separately (respond with PONG)

        # APPLICATION_COMMAND interaction (type 2)
        if interaction_type == 2:
            return self._parse_slash_command(raw)

        # MESSAGE_CREATE (via gateway, not interaction)
        if raw.get("t") == "MESSAGE_CREATE":
            return self._parse_message(raw.get("d", {}))

        return None

    def _parse_slash_command(self, raw: dict) -> Optional[OEFEvent]:
        """Parse a slash command interaction."""
        data = raw.get("data", {})
        command = data.get("name", "")
        options = data.get("options", [])
        user = raw.get("member", {}).get("user", {})
        channel_id = raw.get("channel_id", "")

        # Extract agent_id from options
        agent_id = "unknown"
        for opt in options:
            if opt.get("name") == "agent":
                agent_id = opt.get("value", "unknown")
                break

        return OEFEvent(
            event_type="command",
            agent_id=agent_id,
            runtime="discord",
            channel="discord",
            payload={
                "command": command,
                "options": options,
                "user": user.get("username", ""),
                "channel_id": channel_id,
            },
        )

    def _parse_message(self, raw: dict) -> Optional[OEFEvent]:
        """Parse a message event."""
        author = raw.get("author", {})
        if author.get("bot"):
            return None

        return OEFEvent(
            event_type="message",
            agent_id=author.get("id", "unknown"),
            runtime="discord",
            channel="discord",
            payload={
                "text": raw.get("content", ""),
                "user": author.get("username", ""),
                "channel_id": raw.get("channel_id", ""),
            },
        )

    def verify_webhook(self, headers: dict, body: str) -> bool:
        """Verify Discord request signature (Ed25519).

        Uses pynacl for proper Ed25519 verification.
        FAILS CLOSED: if pynacl is not installed, requests are rejected.
        """
        if not self.public_key:
            logger.warning("Discord signature verification skipped — no public key")
            return False

        signature = headers.get("X-Signature-Ed25519", "")
        timestamp = headers.get("X-Signature-Timestamp", "")

        if not signature or not timestamp:
            return False

        try:
            from nacl.exceptions import BadSignatureError
            from nacl.signing import VerifyKey

            verify_key = VerifyKey(bytes.fromhex(self.public_key))
            message = f"{timestamp}{body}".encode()
            verify_key.verify(message, bytes.fromhex(signature))
            return True
        except ImportError:
            # FAIL CLOSED — do not accept unverified requests
            logger.error("pynacl not installed — Discord webhook verification IMPOSSIBLE. Rejecting request. Install with: pip install pynacl")
            return False
        except BadSignatureError:
            logger.warning("Discord signature verification failed: bad signature")
            return False
        except Exception as e:
            logger.error(f"Discord signature verification error: {e}")
            return False

    # --- API ---

    def _api_call(self, path: str, payload: dict, method: str = "POST") -> bool:
        """Make a Discord API call with rate limiting and retry."""
        limiter = get_rate_limiter()
        host = "discord.com"

        for attempt in range(3):
            limiter.wait_if_needed(host)
            try:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    f"https://{host}/api/v10{path}",
                    data=data,
                    headers={
                        "Authorization": f"Bot {self.bot_token}",
                        "Content-Type": "application/json",
                    },
                    method=method,
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    limiter.record_response(host, resp.status)
                    return resp.status in (200, 201)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = e.headers.get("Retry-After", "")
                    limiter.record_response(host, 429, {"Retry-After": retry_after})
                    continue
                logger.error(f"Discord API call failed: {e}")
                return False
            except Exception as e:
                logger.error(f"Discord API call failed: {e}")
                return False

        logger.error("Discord API call failed after 3 attempts (rate limited)")
        return False

    def test_connection(self) -> dict:
        """Test Discord connection and return bot info."""
        if not self.bot_token:
            return {"ok": False, "error": "no_bot_token"}
        try:
            req = urllib.request.Request(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {self.bot_token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return {"ok": True, "username": data.get("username"), "id": data.get("id")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def build_interaction_response(self, interaction_id: int, content: str) -> dict:
        """Build a Discord interaction response payload."""
        return {
            "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {"content": content},
        }

    def build_pong_response(self, interaction_id: int) -> dict:
        """Build a Discord PONG response for ping interactions."""
        return {"type": 1}  # PONG
