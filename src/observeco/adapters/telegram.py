"""Telegram adapter — send/receive ObserveCo events via Telegram.

Supports:
- Sending alerts to Telegram chats via Bot API
- Receiving Telegram updates via getUpdates or webhook
- Inline keyboards for approval workflows
- Rich HTML notifications

Environment variables:
    OBSERVECO_TG_BOT_TOKEN — Telegram bot token (from @BotFather)
    OBSERVECO_TG_CHAT_ID — Default chat ID for alerts
    OBSERVECO_WEBHOOK_SECRET — Secret for webhook verification
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import urllib.request
from typing import Optional

from observeco.rate_limiter import get_rate_limiter

from .oef import OEFEvent

logger = logging.getLogger(__name__)


class TelegramAdapter:
    """Telegram channel adapter for ObserveCo."""

    def __init__(
        self,
        bot_token: str = "",
        chat_id: str = "",
        webhook_secret: str = "",
    ):
        self.bot_token = bot_token or os.environ.get("OBSERVECO_TG_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("OBSERVECO_TG_CHAT_ID", "")
        self.webhook_secret = webhook_secret or os.environ.get("OBSERVECO_WEBHOOK_SECRET", "")
        self._base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    # --- Sending ---

    def send_event(self, event: OEFEvent, chat_id: str = "") -> bool:
        """Send an ObserveCo event as a Telegram message."""
        if not self.bot_token:
            logger.warning("Telegram send skipped — no bot token")
            return False

        target = chat_id or self.chat_id
        text = self._event_to_text(event)
        parse_mode = "HTML"
        reply_markup = self._event_to_keyboard(event)

        payload = {
            "chat_id": target,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        return self._api_call("sendMessage", payload)

    def _event_to_text(self, event: OEFEvent) -> str:
        """Convert OEF event to Telegram HTML message."""
        emoji = {
            "tool_call": "🔧",
            "risk_alert": "⚠️",
            "error": "🔴",
            "heartbeat": "💓",
            "feedback": "💬",
            "response": "💬",
        }.get(event.event_type, "📋")

        header = f"<b>{emoji} {event.event_type.replace('_', ' ').title()}</b>"
        context = f"<i>Agent:</i> {event.agent_id} | <i>Runtime:</i> {event.runtime}"

        if event.event_type == "tool_call":
            tool = event.payload.get("tool_name", "unknown")
            risk = event.payload.get("risk_level", "unknown")
            decision = event.payload.get("decision", "unknown")
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(risk, "⚪")
            body = (
                f"<b>Tool:</b> <code>{tool}</code>\n"
                f"<b>Risk:</b> {risk_emoji} {risk.upper()}\n"
                f"<b>Decision:</b> {decision}"
            )
        elif event.event_type == "risk_alert":
            tool = event.payload.get("tool_name", "unknown")
            risk = event.payload.get("risk_level", "unknown")
            reason = event.payload.get("reason", "")
            body = (
                f"<b>⚠️ Risk Alert</b>\n"
                f"<b>Tool:</b> <code>{tool}</code>\n"
                f"<b>Level:</b> {risk.upper()}\n"
                f"<b>Reason:</b> {reason}"
            )
        elif event.event_type == "error":
            error_type = event.payload.get("error_type", "unknown")
            error_msg = event.payload.get("error_message", "")[:500]
            body = (
                f"<b>🔴 Error</b>\n"
                f"<b>Type:</b> {error_type}\n"
                f"<b>Message:</b> {error_msg}"
            )
        elif event.event_type == "heartbeat":
            status = event.payload.get("status", "unknown")
            latency = event.payload.get("latency_ms", 0)
            status_emoji = "🟢" if status == "alive" else "🔴"
            body = (
                f"<b>Heartbeat</b>\n"
                f"<b>Status:</b> {status_emoji} {status}\n"
                f"<b>Latency:</b> {latency:.0f}ms"
            )
        else:
            body = f"<pre>{json.dumps(event.payload, indent=2)[:1000]}</pre>"

        return f"{header}\n{context}\n\n{body}"

    def _event_to_keyboard(self, event: OEFEvent) -> Optional[dict]:
        """Build inline keyboard for approval workflows."""
        if event.event_type == "risk_alert":
            return {
                "inline_keyboard": [
                    [
                        {"text": "✓ Approve", "callback_data": f"approve:{event.event_id}"},
                        {"text": "✗ Deny", "callback_data": f"deny:{event.event_id}"},
                    ],
                    [
                        {"text": "📋 Details", "callback_data": f"details:{event.event_id}"},
                    ],
                ]
            }
        return None

    # --- Receiving ---

    def receive_event(self, raw: dict) -> Optional[OEFEvent]:
        """Parse a raw Telegram update into OEF format."""
        message = raw.get("message") or raw.get("callback_query")
        if not message:
            return None

        # Handle callback queries (button presses)
        if "data" in message:
            return self._parse_callback(message)

        # Handle messages
        text = message.get("text", "")
        user = message.get("from", {})
        chat = message.get("chat", {})

        # Check for bot commands
        if text.startswith("/"):
            return self._parse_command(text, user, chat)

        return None

    def _parse_callback(self, query: dict) -> Optional[OEFEvent]:
        """Parse a callback query (button press)."""
        data = query.get("data", "")
        user = query.get("from", {})

        if ":" not in data:
            return None

        action, event_id = data.split(":", 1)

        return OEFEvent(
            event_type="approval",
            agent_id=user.get("username", str(user.get("id", ""))),
            runtime="telegram",
            channel="telegram",
            payload={
                "action": action,
                "event_id": event_id,
                "user": user.get("username", ""),
            },
        )

    def _parse_command(self, text: str, user: dict, chat: dict) -> Optional[OEFEvent]:
        """Parse a bot command."""
        parts = text.split()
        command = parts[0].split("@")[0]  # Remove @botname
        args = parts[1:] if len(parts) > 1 else []

        return OEFEvent(
            event_type="command",
            agent_id=user.get("username", str(user.get("id", ""))),
            runtime="telegram",
            channel="telegram",
            payload={
                "command": command,
                "args": args,
                "chat_id": chat.get("id"),
                "user": user.get("username", ""),
            },
        )

    # --- Webhook ---

    def verify_webhook(self, headers: dict, body: str) -> bool:
        """Verify Telegram webhook request.

        Telegram uses a secret token in X-Telegram-Bot-Api-Secret-Token header.
        Returns False if no secret is configured (never trust unverified requests).
        """
        if not self.webhook_secret:
            logger.warning("Telegram webhook verification skipped — no secret configured")
            return False

        token = headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not token:
            return False

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(token, self.webhook_secret)

    def set_webhook(self, url: str, secret: str = "") -> bool:
        """Set the webhook URL for the bot."""
        payload = {"url": url}
        if secret:
            payload["secret_token"] = secret
        return self._api_call("setWebhook", payload)

    # --- API ---

    def _api_call(self, method: str, payload: dict) -> bool:
        """Make a Telegram Bot API call with rate limiting and retry."""
        if not self.bot_token:
            return False

        limiter = get_rate_limiter()
        host = "api.telegram.org"

        for attempt in range(3):
            limiter.wait_if_needed(host)
            try:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    f"{self._base_url}/{method}",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read())
                    if not result.get("ok"):
                        desc = result.get("description", "unknown")
                        if "Too Many Requests" in desc or "retry after" in desc.lower():
                            limiter.record_response(host, 429)
                            continue
                        logger.error(f"Telegram API error: {desc}")
                        return False
                    limiter.record_response(host, 200)
                    return True
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = e.headers.get("Retry-After", "")
                    limiter.record_response(host, 429, {"Retry-After": retry_after})
                    continue
                logger.error(f"Telegram API call failed: {e}")
                return False
            except Exception as e:
                logger.error(f"Telegram API call failed: {e}")
                return False

        logger.error("Telegram API call failed after 3 attempts (rate limited)")
        return False

    def test_connection(self) -> dict:
        """Test Telegram connection and return bot info."""
        if not self.bot_token:
            return {"ok": False, "error": "no_bot_token"}
        try:
            req = urllib.request.Request(f"{self._base_url}/getMe")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if result.get("ok"):
                    bot = result["result"]
                    return {"ok": True, "username": bot.get("username"), "id": bot.get("id")}
                return {"ok": False, "error": result.get("description", "unknown")}
        except Exception as e:
            return {"ok": False, "error": str(e)}
