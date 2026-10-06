"""confirmation_gate.py — spec 095 section 3.7. The confirmation gate and the Turnstile captcha.

WHY THIS EXISTS, IN THE SPEC'S OWN WORDS
----------------------------------------
Section 3.7: "A captcha stops automated SUBMISSION. It does not stop LLM spend. The model calls
happen in the WORKER, and if the worker runs on unconfirmed submissions, a bot that solves one
challenge still triggers a full Jev + enrichment run -- and can do it repeatedly with different
addresses."

So the two controls do different jobs and BOTH are needed:

    Turnstile   stops a bot filling the form at machine speed.
    The gate    moves ALL model work behind a verified address, so an unconfirmed
                submission costs one row and one email and nothing else.

The captcha is the weaker of the two. The gate is the one that protects the budget.

⚠ THE ORDERING IS THE DESIGN, NOT AN IMPLEMENTATION DETAIL (spec 3.7):
    submit (captcha) -> store as `pending` -> confirmation email   [ZERO MODEL COST]
                            |
                            +-- confirmed -> queue -> enrichment -> Jev -> report
                                                                ^
                              nothing reaches this until the address is proven

⚠ NOTHING IN THIS MODULE SPENDS MONEY. `submit_pending` writes a row. `confirm` flips a flag and
returns the payload for the worker to act on. The worker is what calls the model.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── Turnstile ────────────────────────────────────────────────────────────────
# Cloudflare's documented always-pass TEST keys. Deliberately the DEFAULT so the gate is
# buildable and provable without a real account. They must never reach production, and
# `turnstile_configured()` is what lets the UI say so out loud.
TEST_SITEKEY = "1x00000000000000000000AA"
TEST_SECRET = "1x0000000000000000000000000000000AA"
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

DEFAULT_LINK_TTL = 24 * 3600          # spec 3.7.1 draft: "This link works for 24 hours"
DEFAULT_RETENTION_DAYS = 30          # spec 3.7.1 draft retention sentence


def _read_env(name: str, default: str = "") -> str:
    """Environment first, then .env files. Mirrors run_jev.read_env_key."""
    v = os.environ.get(name, "").strip()
    if v:
        return v
    for p in (HERE / ".env", Path.home() / ".hermes" / ".env"):
        try:
            if not p.exists():
                continue
            for line in p.read_text().splitlines():
                line = line.strip()
                if line.startswith(f"{name}=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:                                  # noqa: BLE001
            continue
    return default


def site_key() -> str:
    return _read_env("TURNSTILE_SITE_KEY", TEST_SITEKEY)


def secret_key() -> str:
    return _read_env("TURNSTILE_SECRET_KEY", TEST_SECRET)


def turnstile_configured() -> bool:
    """True only when a REAL key pair is set. The sandbox shows a warning when this is False,
    because a UI that silently runs on test keys would look protected and not be."""
    return (site_key() != TEST_SITEKEY) and (secret_key() != TEST_SECRET)


def verify_turnstile(token: str, remote_ip: str = "", timeout: int = 10) -> dict:
    """Ask Cloudflare whether the token is genuine.

    ⚠ FAIL CLOSED. The spec rejects reCAPTCHA precisely because it "fails open -- it can return a
    static high score when over quota, silently". A network error here therefore returns
    ok=False, never ok=True. Being briefly unavailable is recoverable; being silently open is not.
    """
    if not token:
        return {"ok": False, "reason": "no token submitted"}
    body = urllib.parse.urlencode({"secret": secret_key(), "response": token,
                                   **({"remoteip": remote_ip} if remote_ip else {})}).encode()
    req = urllib.request.Request(VERIFY_URL, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": f"verify HTTP {e.code}"}
    except Exception as e:                                  # noqa: BLE001
        return {"ok": False, "reason": f"verify unreachable: {type(e).__name__}"}
    if data.get("success"):
        return {"ok": True, "reason": "challenge passed"}
    return {"ok": False, "reason": "; ".join(data.get("error-codes") or ["challenge failed"])}


# ── token signing ────────────────────────────────────────────────────────────
def _secret() -> str:
    """The signing secret. Falls back to a per-install random so the sandbox works with no
    configuration -- but a FALLBACK SECRET IS NOT A SECRET, so `signed_with_fallback()` reports it."""
    v = _read_env("CONFIRM_SECRET")
    if v:
        return v
    marker = HERE / ".confirm_secret"
    if not marker.exists():
        marker.write_text(secrets.token_urlsafe(32))
    return marker.read_text().strip()


def signed_with_fallback() -> bool:
    return not bool(_read_env("CONFIRM_SECRET"))


def make_token(email: str, ttl: int = DEFAULT_LINK_TTL, now: int | None = None) -> str:
    """A stateless expiring confirmation token: base64(email).expiry.hmac.

    No model call, no email provider, no library. The signature is what makes it unforgeable, so
    an attacker cannot confirm an address they do not control -- which is the whole point.
    """
    import base64
    exp = (now if now is not None else int(time.time())) + ttl
    payload = f"{base64.urlsafe_b64encode(email.strip().lower().encode()).decode()}.{exp}"
    sig = hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def check_token(token: str, now: int | None = None) -> dict:
    """Verify signature then expiry. Returns {ok, email, reason}."""
    import base64
    try:
        enc, exp_s, sig = token.rsplit(".", 2)
        exp = int(exp_s)
    except Exception:                                       # noqa: BLE001
        return {"ok": False, "email": "", "reason": "malformed token"}
    payload = f"{enc}.{exp_s}"
    want = hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(want, sig):
        return {"ok": False, "email": "", "reason": "bad signature"}
    if (now if now is not None else int(time.time())) > exp:
        return {"ok": False, "email": "", "reason": "link expired"}
    try:
        email = base64.urlsafe_b64decode(enc.encode()).decode()
    except Exception:                                       # noqa: BLE001
        return {"ok": False, "email": "", "reason": "malformed payload"}
    return {"ok": True, "email": email, "reason": "ok"}


# ── the store: rows waiting on confirmation ──────────────────────────────────
QUEUE_SCHEMA = """CREATE TABLE IF NOT EXISTS confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT, email TEXT, business_name TEXT,
    payload TEXT, status TEXT, token_hash TEXT,
    confirmed_at TEXT, turnstile_ok INTEGER,
    unsubscribed_at TEXT)"""


def connect(db_path) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.execute(QUEUE_SCHEMA)
    return c


def submit_pending(db_path, email: str, business_name: str, payload: dict,
                   captcha_ok: bool) -> dict:
    """Store a submission awaiting confirmation. ⚠ ZERO MODEL COST -- this is a row and nothing else."""
    tok = make_token(email)
    c = connect(db_path)
    cur = c.execute(
        "INSERT INTO confirmations (created_at,email,business_name,payload,status,"
        "token_hash,turnstile_ok) VALUES (?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), email, business_name,
         json.dumps(payload), "pending",
         hashlib.sha256(tok.encode()).hexdigest()[:32], 1 if captcha_ok else 0))
    c.commit()
    i = int(cur.lastrowid or 0)
    c.close()
    return {"id": i, "token": tok, "status": "pending"}


def confirm(db_path, token: str) -> dict:
    """Flip a pending row to `confirmed` and hand back the payload for the worker.

    ⚠ THIS IS THE ONLY DOOR TO MODEL SPEND. A caller that runs the pipeline without a
    confirmed row here is the 3.7 defect in code form.
    """
    chk = check_token(token)
    if not chk["ok"]:
        return {"ok": False, "reason": chk["reason"]}
    th = hashlib.sha256(token.encode()).hexdigest()[:32]
    c = connect(db_path)
    row = c.execute("SELECT id,payload,status FROM confirmations WHERE token_hash=?",
                    (th,)).fetchone()
    if not row:
        c.close()
        return {"ok": False, "reason": "unknown token"}
    rid, payload, status = row
    if status == "confirmed":
        c.close()
        return {"ok": True, "already": True, "id": rid, "payload": json.loads(payload)}
    c.execute("UPDATE confirmations SET status='confirmed', confirmed_at=? WHERE id=?",
              (datetime.now(timezone.utc).isoformat(timespec="seconds"), rid))
    c.commit()
    c.close()
    return {"ok": True, "already": False, "id": rid, "payload": json.loads(payload)}


def purge_expired(db_path, retention_days: int = DEFAULT_RETENTION_DAYS,
                  now: datetime | None = None) -> int:
    """⚠ THE RETENTION COMMITMENT, AS CODE. The confirmation email tells the recipient
    "we'll delete your details within 30 days" -- this is the thing that makes that true.
    Deletes rows that were never confirmed and are older than the window."""
    from datetime import timedelta
    cutoff = ((now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
              ).isoformat(timespec="seconds")
    c = connect(db_path)
    cur = c.execute("DELETE FROM confirmations WHERE status='pending' AND created_at < ?", (cutoff,))
    n = cur.rowcount or 0
    c.commit()
    c.close()
    return n
