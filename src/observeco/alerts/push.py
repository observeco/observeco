"""Push alert delivery engine — Telegram, webhook, email.

Subscriptions stored in alert_subscriptions table.
Delivery log in alert_log table.

Fire-and-forget: push_alert returns immediately. Deliveries that fail
are logged with error; subscriptions with repeated failures can be disabled.

Alert enrichment: LLM classifies alerts as duplicate (suppress) vs novel
(enrichment body). Falls back to raw message if LLM unavailable.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import NamedTuple, Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Alert enrichment result types
# ---------------------------------------------------------------------------

SUPPRESS = "suppress"
RAW_FALLBACK = "raw"
ENRICHED = "enriched"


class _EnrichResult(NamedTuple):
    status: str  # SUPPRESS | RAW_FALLBACK | ENRICHED
    text: str    # populated only when status == ENRICHED


# ---------------------------------------------------------------------------
# Alert enrichment prompt
# ---------------------------------------------------------------------------

ALERT_ENRICHMENT_PROMPT = """\
You are an alert analyst for ObserveCo. You receive a new alert event and \
recent alert history for the same agent. Your job is to decide:

1. SUPPRESS — if this is the same crash pattern / duplicate as one or more \
recent alerts. Do NOT send a separate notification for repeated failures.
2. ENRICHED: <enriched message> — if this is a novel or significantly \
different failure mode. Provide a concise, actionable enriched message that \
explains the likely root cause and any suggested next steps.
3. CANNOT_DETERMINE — if you cannot make a confident classification.

Format your response as exactly ONE of these three lines (no extra text):

- SUPPRESS
- ENRICHED: <your enriched message here>
- CANNOT_DETERMINE

Current alert:
- Event type: {event_type}
- Message: {message}
- Agent: {agent_name}

Recent alerts for this agent (most recent first):
{recent_alerts}
"""


def _enrich_alert(
    event_type: str,
    message: str,
    agent_name: str,
    db: "Database",
) -> _EnrichResult:
    """Classify and optionally enrich an alert via LLM.

    Returns:
        _EnrichResult with status:
        - SUPPRESS: duplicate pattern, caller should skip delivery
        - RAW_FALLBACK: LLM unavailable or unsure, use original message
        - ENRICHED: novel failure, text field contains enriched message
    """
    try:
        from observeco.llm_service import ask as llm_ask
    except ImportError:
        logger.debug("llm_service not available; passing alert through raw")
        return _EnrichResult(RAW_FALLBACK, "")

    # Fetch recent alert_log entries for this agent (limit 5)
    recent_entries = db.get_alert_log(limit=5)
    if agent_name:
        recent_entries = [
            r for r in recent_entries
            if agent_name.lower() in (r.get("message", "") + " " + r.get("event_type", "")).lower()
        ]

    if not recent_entries:
        recent_lines = "  (no recent alerts for this agent)"
    else:
        lines = []
        for entry in recent_entries[:5]:
            ts = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(entry.get("created_at", 0)),
            )
            lines.append(
                f"  [{ts}] event={entry.get('event_type', '?')} "
                f"msg={entry.get('message', '')[:120]}"
            )
        recent_lines = "\n".join(lines)

    user_context = ALERT_ENRICHMENT_PROMPT.format(
        event_type=event_type,
        message=message,
        agent_name=agent_name or "(unknown)",
        recent_alerts=recent_lines,
    )

    try:
        response = llm_ask(
            system_prompt="You are an ObserveCo alert analyst. Be concise.",
            user_context=user_context,
            consumer="alert_enrichment",
            max_cost_cents=0.005,
            cache_ttl_secs=3600,
            tier=2,
        )
    except Exception as exc:
        logger.warning("LLM enrichment call failed: %s — using raw message", exc)
        return _EnrichResult(RAW_FALLBACK, "")

    if response is None:
        logger.debug("LLM returned None (gated/budget); using raw message")
        return _EnrichResult(RAW_FALLBACK, "")

    response = response.strip()

    # --- Classify LLM response ---
    upper = response.upper()

    if upper == "SUPPRESS":
        logger.info("Alert suppressed by LLM (duplicate pattern): %s", event_type)
        return _EnrichResult(SUPPRESS, "")

    if upper == "CANNOT_DETERMINE":
        logger.debug("LLM returned CANNOT_DETERMINE; using raw message")
        return _EnrichResult(RAW_FALLBACK, "")

    if response.upper().startswith("ENRICHED:"):
        enriched = response[len("ENRICHED:"):].strip()
        if enriched:
            logger.info("Alert enriched by LLM: %s", enriched[:80])
            return _EnrichResult(ENRICHED, enriched)
        # Empty enrichment — fall through to raw

    # Unknown format — pass through raw
    logger.debug("LLM returned unrecognized format; using raw message")
    return _EnrichResult(RAW_FALLBACK, "")


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

    # --- Alert enrichment: classify & optionally enrich before delivery ---
    original_message = message
    try:
        result = _enrich_alert(event_type, message, agent_name, db)
    except Exception as exc:
        logger.debug("Alert enrichment failed, using raw: %s", exc)
        result = _EnrichResult(RAW_FALLBACK, "")

    if result.status == SUPPRESS:
        logger.info("Alert suppressed (duplicate pattern): %s", event_type)
        return []  # skip delivery entirely

    if result.status == ENRICHED and result.text:
        message = result.text

    # RAW_FALLBACK or empty ENRICHED → use original_message as-is

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
