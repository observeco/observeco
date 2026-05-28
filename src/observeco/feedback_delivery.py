"""Feedback delivery — Telegram push + Email relay for user feedback."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import urllib.request
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration from env (set these on the server/self-hosted instance)
# ---------------------------------------------------------------------------

def _get_tg_config() -> dict:
    """Return Telegram config from env or empty dict."""
    return {
        "bot_token": os.environ.get("OBSERVECO_TG_BOT_TOKEN", ""),
        "chat_id": os.environ.get("OBSERVECO_TG_CHAT_ID", ""),
    }


def _get_email_config() -> dict:
    """Return email config from env or empty dict."""
    return {
        "smtp_host": os.environ.get("OBSERVECO_SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("OBSERVECO_SMTP_PORT", "587")),
        "smtp_user": os.environ.get("OBSERVECO_SMTP_USER", ""),
        "smtp_pass": os.environ.get("OBSERVECO_SMTP_PASS", ""),
        "from_addr": os.environ.get("OBSERVECO_FROM_EMAIL", "feedback@observeco.dev"),
        "to_addr": os.environ.get("OBSERVECO_TO_EMAIL", ""),
        "use_tls": os.environ.get("OBSERVECO_SMTP_TLS", "1") == "1",
    }


# ---------------------------------------------------------------------------
# Telegram delivery
# ---------------------------------------------------------------------------

def deliver_telegram(payload: dict) -> bool:
    """Send feedback to a Telegram chat via Bot API.

    Requires OBSERVECO_TG_BOT_TOKEN and OBSERVECO_TG_CHAT_ID env vars.
    Returns True if sent successfully, False otherwise (logs failure).
    """
    cfg = _get_tg_config()
    if not cfg["bot_token"] or not cfg["chat_id"]:
        logger.debug("Telegram delivery skipped — missing OBSERVECO_TG_BOT_TOKEN or OBSERVECO_TG_CHAT_ID")
        return False

    fb_type = payload.get("type_label", "Feedback")
    summary = payload.get("summary", "(no summary)")
    severity = payload.get("severity", "")
    detail = payload.get("detail", "")
    env = payload.get("environment", {})

    lines = [
        f"📬 **{fb_type}**",
        f"**Severity:** {severity}",
        "",
        f"**{summary}**",
    ]
    if detail:
        # Truncate long detail for Telegram
        truncated = detail[:1500] + "..." if len(detail) > 1500 else detail
        lines += ["", f"```\n{truncated}\n```"]
    lines += [
        "",
        f"`v{env.get('observeco_version', '?')} · {env.get('os', '?')} · {env.get('install_method', '?')}`",
    ]

    text = "\n".join(lines)

    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    data = json.dumps({
        "chat_id": cfg["chat_id"],
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read())
        if body.get("ok"):
            logger.info("Feedback delivered to Telegram")
            return True
        else:
            logger.warning("Telegram API returned error: %s", body.get("description"))
            return False
    except Exception as exc:
        logger.warning("Telegram delivery failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

def deliver_email(payload: dict) -> bool:
    """Send feedback to an email address via SMTP.

    Requires OBSERVECO_SMTP_HOST and OBSERVECO_TO_EMAIL env vars.
    Falls back silently if not configured.
    """
    cfg = _get_email_config()
    if not cfg["smtp_host"] or not cfg["to_addr"]:
        logger.debug("Email delivery skipped — missing SMTP config")
        return False

    fb_type = payload.get("type_label", "Feedback")
    summary = payload.get("summary", "(no summary)")
    detail = payload.get("detail", "")
    severity = payload.get("severity", "N/A")
    env = payload.get("environment", {})

    body_parts = [
        f"Type: {fb_type}",
        f"Severity: {severity}",
        f"Summary: {summary}",
        "",
        f"Details:\n{detail}" if detail else "Details: (none)",
        "",
        "--- Environment ---",
        f"Version: {env.get('observeco_version', '?')}",
        f"OS: {env.get('os', '?')}",
        f"Python: {env.get('python', '?')}",
        f"Install: {env.get('install_method', '?')}",
    ]

    msg = MIMEText("\n".join(body_parts), "plain", "utf-8")
    msg["Subject"] = f"[ObserveCo Feedback] {summary[:80]}"
    msg["From"] = cfg["from_addr"]
    msg["To"] = cfg["to_addr"]

    try:
        if cfg["use_tls"]:
            server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=15)

        if cfg["smtp_user"] and cfg["smtp_pass"]:
            server.login(cfg["smtp_user"], cfg["smtp_pass"])

        server.sendmail(cfg["from_addr"], [cfg["to_addr"]], msg.as_string())
        server.quit()
        logger.info("Feedback delivered via email to %s", cfg["to_addr"])
        return True
    except Exception as exc:
        logger.warning("Email delivery failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Unified delivery — try Telegram then Email, returns which succeeded
# ---------------------------------------------------------------------------

def deliver_feedback(payload: dict) -> dict:
    """Try all configured delivery channels.

    Returns dict with per-channel results, e.g.:
    {"telegram": True, "email": False}
    """
    result = {
        "telegram": deliver_telegram(payload),
        "email": deliver_email(payload),
    }
    return result
