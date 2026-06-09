"""Slack adapter — send/receive ObserveCo events via Slack.

Supports:
- Sending alerts to Slack channels via Bot API
- Receiving Slack events via Events API (bot events, app mentions)
- Verifying Slack request signatures
- Rich Block Kit notifications

Environment variables:
    OBSERVECO_SLACK_BOT_TOKEN — xoxb-... bot token
    OBSERVECO_SLACK_SIGNING_SECRET — app signing secret for webhook verification
    OBSERVECO_SLACK_ALERT_CHANNEL — default channel for alerts (e.g., "#observeco-alerts")
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import urllib.request
from typing import Optional

from observeco.rate_limiter import get_rate_limiter

from .oef import OEFEvent

logger = logging.getLogger(__name__)


class SlackAdapter:
    """Slack channel adapter for ObserveCo."""

    def __init__(
        self,
        bot_token: str = "",
        signing_secret: str = "",
        alert_channel: str = "",
    ):
        self.bot_token = bot_token or os.environ.get("OBSERVECO_SLACK_BOT_TOKEN", "")
        self.signing_secret = signing_secret or os.environ.get("OBSERVECO_SLACK_SIGNING_SECRET", "")
        self.alert_channel = alert_channel or os.environ.get("OBSERVECO_SLACK_ALERT_CHANNEL", "#observeco-alerts")

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.signing_secret)

    # --- Sending ---

    def send_event(self, event: OEFEvent, channel: str = "") -> bool:
        """Send an ObserveCo event as a Slack message."""
        if not self.bot_token:
            logger.warning("Slack send skipped — no bot token")
            return False

        target = channel or self.alert_channel
        blocks = self._event_to_blocks(event)

        payload = {
            "channel": target,
            "blocks": blocks,
            "text": f"[ObserveCo] {event.event_type}: {event.agent_id}",  # Fallback text
        }

        return self._api_call("chat.postMessage", payload)

    def _event_to_blocks(self, event: OEFEvent) -> list:
        """Convert OEF event to Slack Block Kit blocks."""
        blocks = []

        # Header
        emoji = {
            "tool_call": "🔧",
            "risk_alert": "⚠️",
            "error": "🔴",
            "heartbeat": "💓",
            "feedback": "💬",
            "response": "💬",
        }.get(event.event_type, "📋")

        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} {event.event_type.replace('_', ' ').title()}", "emoji": True},
        })

        # Context
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Agent:* {event.agent_id} | *Runtime:* {event.runtime} | *Channel:* {event.channel}"},
                {"type": "mrkdwn", "text": f"*Time:* {event.timestamp}"},
            ],
        })

        blocks.append({"type": "divider"})

        # Payload
        if event.event_type == "tool_call":
            tool = event.payload.get("tool_name", "unknown")
            risk = event.payload.get("risk_level", "unknown")
            decision = event.payload.get("decision", "unknown")
            args = json.dumps(event.payload.get("tool_args", {}), indent=2)[:500]

            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(risk, "⚪")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Tool:* `{tool}`\n*Risk:* {risk_emoji} {risk.upper()}\n*Decision:* {decision}"},
            })
            if args and args != "{}":
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"```{args}```"},
                })

        elif event.event_type == "risk_alert":
            tool = event.payload.get("tool_name", "unknown")
            risk = event.payload.get("risk_level", "unknown")
            reason = event.payload.get("reason", "")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*⚠️ Risk Alert*\n*Tool:* `{tool}`\n*Level:* {risk.upper()}\n*Reason:* {reason}"},
            })

        elif event.event_type == "error":
            error_type = event.payload.get("error_type", "unknown")
            error_msg = event.payload.get("error_message", "")[:500]
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*🔴 Error*\n*Type:* {error_type}\n*Message:* {error_msg}"},
            })

        elif event.event_type == "heartbeat":
            status = event.payload.get("status", "unknown")
            latency = event.payload.get("latency_ms", 0)
            status_emoji = "🟢" if status == "alive" else "🔴"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Heartbeat*\n*Status:* {status_emoji} {status}\n*Latency:* {latency:.0f}ms"},
            })

        else:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{json.dumps(event.payload, indent=2)[:1000]}```"},
            })

        return blocks

    # --- Receiving ---

    def receive_event(self, raw: dict) -> Optional[OEFEvent]:
        """Parse a raw Slack event into OEF format."""
        event_type = raw.get("type", "")

        # Handle url_verification challenge
        if event_type == "url_verification":
            return None  # Handled separately

        # Handle app_mention
        if event_type == "app_mention":
            return self._parse_app_mention(raw)

        # Handle message
        if event_type == "message":
            return self._parse_message(raw)

        return None

    def _parse_app_mention(self, raw: dict) -> Optional[OEFEvent]:
        """Parse an app_mention event."""
        event = raw.get("event", {})
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")

        # Extract agent_id from mention text (e.g., "@observeco check agent-1")
        parts = text.split()
        agent_id = parts[1] if len(parts) > 1 else "unknown"

        return OEFEvent(
            event_type="command",
            agent_id=agent_id,
            runtime="slack",
            channel="slack",
            payload={
                "command": text,
                "user": user,
                "channel": channel,
            },
        )

    def _parse_message(self, raw: dict) -> Optional[OEFEvent]:
        """Parse a message event."""
        event = raw.get("event", {})
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")
        subtype = event.get("subtype", "")

        # Ignore bot messages and edits
        if subtype or event.get("bot_id"):
            return None

        return OEFEvent(
            event_type="message",
            agent_id=user or "unknown",
            runtime="slack",
            channel="slack",
            payload={
                "text": text,
                "user": user,
                "channel": channel,
            },
        )

    def verify_webhook(self, headers: dict, body: str) -> bool:
        """Verify Slack request signature (v0/v2 signing)."""
        if not self.signing_secret:
            logger.warning("Slack signature verification skipped — no signing secret")
            return False

        timestamp = headers.get("X-Slack-Request-Timestamp", "")
        signature = headers.get("X-Slack-Signature", "")

        if not timestamp or not signature:
            return False

        # Reject old requests (>5 minutes)
        try:
            if abs(time.time() - float(timestamp)) > 300:
                return False
        except (ValueError, TypeError):
            return False

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body}"
        expected = "v0=" + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    # --- API ---

    def _api_call(self, method: str, payload: dict) -> bool:
        """Make a Slack API call with rate limiting and retry."""
        limiter = get_rate_limiter()
        host = "slack.com"

        for attempt in range(3):  # Max 3 attempts
            limiter.wait_if_needed(host)
            try:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    f"https://{host}/api/{method}",
                    data=data,
                    headers={
                        "Authorization": f"Bearer {self.bot_token}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read())
                    if not result.get("ok"):
                        error = result.get("error", "unknown")
                        if error == "rate_limited":
                            limiter.record_response(host, 429)
                            continue  # Retry after backoff
                        logger.error(f"Slack API error: {error}")
                        return False
                    limiter.record_response(host, 200)
                    return True
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = e.headers.get("Retry-After", "")
                    limiter.record_response(host, 429, {"Retry-After": retry_after})
                    continue  # Retry after backoff
                logger.error(f"Slack API call failed: {e}")
                return False
            except Exception as e:
                logger.error(f"Slack API call failed: {e}")
                return False

        logger.error("Slack API call failed after 3 attempts (rate limited)")
        return False

    def test_connection(self) -> dict:
        """Test Slack connection and return bot info."""
        if not self.bot_token:
            return {"ok": False, "error": "no_bot_token"}
        try:
            data = json.dumps({}).encode()
            req = urllib.request.Request(
                "https://slack.com/api/auth.test",
                data=data,
                headers={
                    "Authorization": f"Bearer {self.bot_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"ok": False, "error": str(e)}
