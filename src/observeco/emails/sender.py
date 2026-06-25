"""Resend API email sender — fire-and-forget via background threads.

Entry point: ``send_email(to, template_name, variables_dict) -> bool``

API key resolution order:
1. ``RESEND_API_KEY`` environment variable
2. ``resend_api_key`` field in ``<data_dir>/billing.json``

Never raises. Logs warnings on failure and returns False.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from typing import Any

from observeco.emails.templates import get_template

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESEND_API_URL = "https://api.resend.com/emails"

# Sender can be overridden via env; defaults to observeco.com domain
DEFAULT_SENDER = os.environ.get(
    "OBSERVECO_EMAIL_FROM",
    "ObserveCo <noreply@observeco.com>",
)

# Lazy-loaded API key (fetched once, cached)
_api_key: str | None = None
_api_key_resolved = False


def _resolve_api_key() -> str:
    """Resolve the Resend API key from env or billing.json.

    Returns empty string if not configured — never raises.
    """
    global _api_key, _api_key_resolved

    if _api_key_resolved:
        return _api_key or ""

    # 1. Environment variable (highest priority)
    env_key = os.environ.get("RESEND_API_KEY", "").strip()
    if env_key:
        _api_key = env_key
        _api_key_resolved = True
        return _api_key

    # 2. billing.json (via _load_config which handles decryption)
    try:
        from observeco.billing import _load_config

        config = _load_config()
        key = config.resend_api_key
        if key and isinstance(key, str):
            _api_key = key
            _api_key_resolved = True
            return _api_key
    except Exception:
        pass  # Never fail on config resolution

    _api_key = ""
    _api_key_resolved = True
    return ""


# ---------------------------------------------------------------------------
# Internal: raw send (called inside background thread)
# ---------------------------------------------------------------------------


def _send_via_resend(
    to: str,
    subject: str,
    html_body: str,
    from_email: str,
    api_key: str,
) -> bool:
    """POST to Resend API. Returns True on success, False on failure.

    Uses urllib.request — no extra dependencies.
    """
    payload = json.dumps({
        "from": from_email,
        "to": [to],
        "subject": subject,
        "html": html_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        RESEND_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ObserveCo/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            if 200 <= status < 300:
                return True
            body = resp.read().decode("utf-8", errors="replace")
            logger.warning(
                "[emails] Resend returned %d for %s: %s", status, to, body
            )
            return False
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        logger.warning(
            "[emails] Resend HTTP %d for %s: %s", exc.code, to, body
        )
        return False
    except Exception as exc:
        logger.warning("[emails] Resend request failed for %s: %s", to, exc)
        return False


# ---------------------------------------------------------------------------
# Background thread wrapper
# ---------------------------------------------------------------------------


def _background_send(
    to: str,
    subject: str,
    html_body: str,
    from_email: str,
    api_key: str,
) -> None:
    """Run the actual HTTP call in a daemon thread."""
    try:
        ok = _send_via_resend(to, subject, html_body, from_email, api_key)
        if ok:
            logger.info("[emails] Sent %r to %s", subject, to)
        # Failures already logged inside _send_via_resend
    except Exception as exc:
        # Absolute safety net — never let a thread crash silently
        logger.warning("[emails] Unexpected error sending to %s: %s", to, exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_email(
    to: str,
    template_name: str,
    variables: dict[str, Any] | None = None,
    *,
    from_email: str | None = None,
    dry_run: bool = False,
) -> bool:
    """Send a transactional email in a background thread.

    Parameters
    ----------
    to:
        Recipient email address.
    template_name:
        Template key (e.g. ``"welcome"``, ``"trial_reminder_7d"``).
    variables:
        Dict of template variables.  Common keys:

        - ``first_name`` — recipient's first name
        - ``trial_days_left`` — days remaining in trial
        - ``subscribe_url`` — link to subscribe page
        - ``manage_url`` — link to billing management
        - ``support_email`` — support contact address
    from_email:
        Override sender address.  Defaults to ``DEFAULT_SENDER``.
    dry_run:
        If True, resolve and render the template but skip sending.
        Useful for testing.  Logs the rendered subject and returns True.

    Returns
    -------
    bool
        True if the send was dispatched (or dry_run succeeded).
        False if configuration is missing, template not found, or
        dispatch failed.  *Never raises.*
    """
    variables = variables or {}

    # Resolve API key
    api_key = _resolve_api_key()
    if not api_key and not dry_run:
        logger.warning(
            "[emails] No Resend API key configured — "
            "set RESEND_API_KEY env or add resend_api_key to billing.json"
        )
        return False

    # Render template
    try:
        subject, html_body = get_template(template_name, variables)
    except KeyError:
        logger.warning("[emails] Unknown template: %r", template_name)
        return False
    except Exception as exc:
        logger.warning("[emails] Template render failed for %r: %s", template_name, exc)
        return False

    sender = from_email or DEFAULT_SENDER

    if dry_run:
        logger.info("[emails] DRY RUN → %s | Subject: %s", to, subject)
        return True

    # Fire-and-forget: dispatch in a daemon thread
    thread = threading.Thread(
        target=_background_send,
        args=(to, subject, html_body, sender, api_key),
        daemon=True,
        name=f"email-{template_name}",
    )
    thread.start()
    return True
