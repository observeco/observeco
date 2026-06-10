"""Push alert delivery engine — Telegram, webhook, email.

Subscriptions stored in alert_subscriptions table.
Delivery log in alert_log table.

Fire-and-forget: push_alert returns immediately. Deliveries that fail
are logged with error; subscriptions with repeated failures can be disabled.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)


def push_alert(event_type: str, message: str,
               agent_name: str = "", db: Optional[Database] = None) -> list[dict]:
    """Deliver a push alert to all matching subscriptions.

    Args:
        event_type: One of 'heal_failure', 'drift', 'circuit_trip',
                    'agent_death', 'l2_trend', 'system'
        message: Human-readable alert text
        agent_name: Optional agent that triggered this alert
        db: Reuse existing DB connection

    Returns:
        List of delivery results: [{channel, target, delivered, error}]
    """
    if db is None:
        db = Database()

    results: list[dict] = []
    subs = db.get_alert_subscriptions()
    active_subs = [s for s in subs if s.get("enabled", 1)]

    if not active_subs:
        return results

    for sub in active_subs:
        channel = sub["channel"]
        target = sub["target"] or ""
        sub_events = sub.get("event_types", "all")

        # Filter by event type
        if sub_events == "critical_only":
            if event_type not in ("heal_failure", "circuit_trip", "agent_death"):
                continue
        elif sub_events != "all" and event_type != sub_events:
            continue

        delivered = False
        error = ""

        try:
            if channel == "telegram":
                delivered, error = _deliver_telegram(target, message)
            elif channel == "discord":
                delivered, error = _deliver_discord(target, message)
            elif channel == "webhook":
                delivered, error = _deliver_webhook(target, message)
            elif channel == "email":
                delivered, error = _deliver_email(target, message)

            if delivered:
                logger.info(f"Alert delivered via {channel} -> {target}")
            else:
                logger.warning(f"Alert delivery failed via {channel}: {error}")
        except Exception as e:
            delivered = False
            error = str(e)
            logger.error(f"Alert exception via {channel}: {e}")

        db.log_alert_delivery(channel, target, event_type, message, delivered, error)
        results.append({
            "channel": channel,
            "target": target,
            "delivered": delivered,
            "error": error,
        })

    return results


def _deliver_telegram(target: str, message: str) -> tuple[bool, str]:
    """Deliver via Telegram using a configured bot token."""
    bot_token_path = __import__("pathlib").Path.home() / ".observeco" / "telegram_bot_token"
    if not bot_token_path.exists():
        # Try using Hermes send_message as fallback
        try:
            import requests
            # No bot token configured — log and skip
            return False, "No Telegram bot token configured at ~/.observeco/telegram_bot_token"
        except Exception:
            return False, "Telegram delivery not configured"

    token = bot_token_path.read_text().strip()
    if not token:
        return False, "Empty Telegram bot token"

    # Split target into chat_id and optional thread_id
    parts = target.split(":", 1)
    chat_id = parts[0]

    try:
        import requests
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=15,
        )
        if resp.status_code == 200:
            return True, ""
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)


def _deliver_discord(target: str, message: str) -> tuple[bool, str]:
    """Deliver via Discord webhook URL with embed format.

    Colour-coded embeds based on message content prefix:
    - 🔴 error/🔴/critical → red (#ef4444)
    - 🟡 warning/🟡/warning → yellow (#eab308)
    - 🟢 recovery/✅/success → green (#22c55e)
    - Default → blue (#6366f1)
    """
    try:
        import requests
        # Determine embed color from message
        color = 0x6366f1  # default blue
        msg_lower = message.lower()
        if "🔴" in message or "critical" in msg_lower or msg_lower.startswith("error"):
            color = 0xef4444  # red
        elif "🟡" in message or "warning" in msg_lower:
            color = 0xeab308  # yellow
        elif "🟢" in message or "✅" in message or "recover" in msg_lower or "success" in msg_lower:
            color = 0x22c55e  # green

        payload = {
            "embeds": [{
                "title": "🤖 ObserveCo Alert",
                "description": message[:4000],
                "color": color,
                "footer": {"text": "ObserveCo Pro"},
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            }]
        }
        resp = requests.post(target, json=payload, timeout=15)
        if 200 <= resp.status_code < 300:
            return True, ""
        # Fallback to plain text if embed fails (e.g. old webhook format)
        if resp.status_code == 400:
            resp2 = requests.post(target, json={"content": message[:2000], "username": "ObserveCo"}, timeout=15)
            if 200 <= resp2.status_code < 300:
                return True, ""
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)


def _deliver_webhook(target: str, message: str) -> tuple[bool, str]:
    """Deliver via HTTP webhook POST."""
    try:
        import requests
        resp = requests.post(
            target,
            json={"event": "alert", "message": message, "timestamp": int(time.time())},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if 200 <= resp.status_code < 300:
            return True, ""
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)


def _deliver_email(target: str, message: str) -> tuple[bool, str]:
    """Deliver via configured SMTP. Falls back to sendmail only if Postfix is running."""
    # First, try configured SMTP (preferred — reliable delivery)
    smtp_config = __import__("pathlib").Path.home() / ".observeco" / "smtp.json"
    if smtp_config.exists():
        try:
            cfg = json.loads(smtp_config.read_text())
            import smtplib
            from email.message import EmailMessage
            msg = EmailMessage()
            msg.set_content(message)
            msg["Subject"] = "ObserveCo Alert"
            msg["From"] = cfg.get("from", "alerts@observeco.local")
            msg["To"] = target
            with smtplib.SMTP(cfg["host"], cfg.get("port", 587), timeout=15) as server:
                if cfg.get("tls", True):
                    server.starttls()
                if cfg.get("user"):
                    server.login(cfg["user"], cfg.get("password", ""))
                server.send_message(msg)
            return True, ""
        except Exception as e:
            return False, f"SMTP delivery failed: {e}"

    # Fallback: sendmail — but only claim success if Postfix is actually running
    try:
        # Verify Postfix is running by checking the master process
        _pf = subprocess.run(["pgrep", "-x", "master"], capture_output=True, timeout=5)
        if _pf.returncode != 0:
            return False, "Postfix not running. Configure SMTP via ~/.observeco/smtp.json for reliable delivery."

        proc = subprocess.run(
            ["sendmail", "-t"],
            input=f"To: {target}\nSubject: ObserveCo Alert\n\n{message}\n",
            text=True, timeout=15, capture_output=True,
        )
        if proc.returncode == 0:
            return True, ""
        return False, proc.stderr[:200]
    except FileNotFoundError:
        return False, "No sendmail or SMTP config found. Configure SMTP via ~/.observeco/smtp.json"
    except Exception as e:
        return False, str(e)


def add_subscription(channel: str, target: str,
                     event_types: str = "all",
                     db: Optional[Database] = None) -> dict:
    """Add a new alert subscription."""
    if db is None:
        db = Database()
    return db.add_alert_subscription(channel, target, event_types)


def remove_subscription(sub_id: int, db: Optional[Database] = None) -> None:
    """Remove an alert subscription."""
    if db is None:
        db = Database()
    db.delete_alert_subscription(sub_id)


def list_subscriptions(db: Optional[Database] = None) -> list[dict]:
    """List all alert subscriptions."""
    if db is None:
        db = Database()
    return db.get_alert_subscriptions()


def get_delivery_log(limit: int = 20, db: Optional[Database] = None) -> list[dict]:
    """Get recent delivery log."""
    if db is None:
        db = Database()
    return db.get_alert_log(limit=limit)
