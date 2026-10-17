#!/usr/bin/env python3
"""mailer.py -- spec 095 section 3.7.1. THE CONFIRMATION EMAIL'S MISSING SENDER.

WHY THIS EXISTS
---------------
The confirmation gate is built and proved: a submission is stored as `pending` at ZERO model
cost, and nothing reaches enrichment or Jev until the address is proven (section 3.7). But the
gate has no way to SEND the proof. The sandbox says so out loud -- "there is no mail client here,
so the link is shown instead of emailed" -- and showing the link is the correct SANDBOX behaviour
and an impossible PRODUCTION one: if the link is displayed rather than emailed, the gate stops
being a spend control, because anyone can submit and then continue.

So this module is the sender, and its contract is deliberately small.

THE THREE OUTCOMES, AND WHY SILENCE IS NOT ONE OF THEM
------------------------------------------------------
    emailed  -- configured and sent. The link went to the address.
    display  -- NOT configured. The caller MUST show the link on the page instead. This is the
                sandbox path, and it is safe ONLY because the instance is loopback-only.
    failed   -- configured but the send failed. ⚠ THE SUBMISSION MUST NOT PROCEED SILENTLY.
                A confirmation that was never delivered leaves a `pending` row that can never be
                confirmed, and if the caller treats that as success the user waits forever.

⚠ THE DANGEROUS STATE IS NOT "not configured", IT IS "configured and broken". An unconfigured
mailer visibly falls back to displaying the link. A misconfigured one would look like it worked.

CONFIGURATION (Sean's to set; nothing is invented here)
-------------------------------------------------------
Reuses the SMTP variable names already used by src/observeco/feedback_delivery.py so the project
has ONE convention rather than two:

    OBSERVECO_SMTP_HOST   e.g. smtp.postmarkapp.com / smtp.sendgrid.net / email-smtp.ap-southeast-1.amazonaws.com
    OBSERVECO_SMTP_PORT   default 587
    OBSERVECO_SMTP_USER
    OBSERVECO_SMTP_PASS
    OBSERVECO_SMTP_TLS    "1" (default) = STARTTLS on 587; "0" = implicit TLS (SMTP_SSL, port 465)
    OBSERVECO_FROM_EMAIL  the From address, e.g. reports@observeco.com

⚠ NOT PROVABLE FROM HERE: no credentials exist in this repository, so the `emailed` path cannot
be exercised by me. It is reported as UNVERIFIED, not as working. What IS proved is the contract:
the fallbacks, the failure mode, and that a broken configuration never reports success.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

SUBJECT = "Confirm your email — your business review is waiting"
DEFAULT_PORT = 587

# The body is deliberately transactional: purpose 1 only (section 3.2 / 3.7.1). No marketing
# line, no unsubscribe link -- those belong to purpose 2's stream, not to this gate.
BODY = """\
You asked us to produce a business review for {business}.

Click this link to confirm your email address:

    {link}

⚠ Nothing has been run yet. No research, no scoring, no cost. The confirmation is what starts it,
and it is what stops a stranger's submission from spending our budget. The link works for 24 hours.

If you did not ask for this, ignore this email — nothing will happen, and no report will be
produced about anyone.
"""


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or "").strip() or default


def is_configured() -> bool:
    """Configured means: a host AND a from-address. Either alone cannot send."""
    return bool(_env("OBSERVECO_SMTP_HOST")) and bool(_env("OBSERVECO_FROM_EMAIL"))


def status() -> dict:
    return {
        "configured": is_configured(),
        "host": _env("OBSERVECO_SMTP_HOST") or None,
        "port": int(_env("OBSERVECO_SMTP_PORT", str(DEFAULT_PORT)) or DEFAULT_PORT),
        "from": _env("OBSERVECO_FROM_EMAIL") or None,
        "auth": bool(_env("OBSERVECO_SMTP_USER")),
        "tls": _env("OBSERVECO_SMTP_TLS", "1") == "1",
    }


def send_confirmation(email: str, link: str, business: str) -> dict:
    """Send the confirmation link. Returns {ok, mode, reason}.

    mode is one of "emailed", "display", "failed". The CALLER decides what to render:
      display -> MUST show the link on the page (the sandbox path)
      failed  -> MUST NOT proceed as if the mail arrived
    """
    st = status()
    if not st["configured"]:
        return {"ok": False, "mode": "display",
                "reason": "no mail provider configured (OBSERVECO_SMTP_HOST / OBSERVECO_FROM_EMAIL unset)"}

    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["From"] = st["from"]
    msg["To"] = email
    msg.set_content(BODY.format(business=business or "your business", link=link))

    try:
        if st["tls"]:
            with smtplib.SMTP(st["host"], st["port"], timeout=20) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                if st["auth"]:
                    s.login(_env("OBSERVECO_SMTP_USER"), _env("OBSERVECO_SMTP_PASS"))
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(st["host"], st["port"], timeout=20,
                                  context=ssl.create_default_context()) as s:
                if st["auth"]:
                    s.login(_env("OBSERVECO_SMTP_USER"), _env("OBSERVECO_SMTP_PASS"))
                s.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        # ⚠ CONFIGURED BUT BROKEN -- the state that must never look like success.
        return {"ok": False, "mode": "failed",
                "reason": "%s: %s" % (type(exc).__name__, str(exc)[:160])}
    return {"ok": True, "mode": "emailed", "reason": "sent to " + email}


def _selftest() -> int:
    fails = []

    def check(name, got, want):
        ok = got == want
        print(("PASS  " if ok else "FAIL  ") + name, "->", got if ok else "got %r want %r" % (got, want))
        if not ok:
            fails.append(name)

    print("1. UNCONFIGURED -> mode=display, ok=False (the caller MUST show the link)")
    saved = {k: os.environ.pop(k, None) for k in
             ("OBSERVECO_SMTP_HOST", "OBSERVECO_FROM_EMAIL", "OBSERVECO_SMTP_USER",
              "OBSERVECO_SMTP_PORT", "OBSERVECO_SMTP_TLS")}
    r = send_confirmation("a@x.test", "http://x/confirm?token=t", "Acme")
    check("mode", r["mode"], "display")
    check("ok", r["ok"], False)
    check("is_configured", is_configured(), False)

    print("2. HALF-CONFIGURED IS NOT CONFIGURED (host alone, or from alone)")
    os.environ["OBSERVECO_SMTP_HOST"] = "smtp.example.test"
    check("host only -> not configured", is_configured(), False)
    os.environ["OBSERVECO_FROM_EMAIL"] = "reports@observeco.com"
    check("host + from -> configured", is_configured(), True)

    print("3. ⚠ CONFIGURED BUT UNREACHABLE -> mode=failed, ok=False (never a silent success)")
    os.environ["OBSERVECO_SMTP_HOST"] = "127.0.0.1"
    os.environ["OBSERVECO_SMTP_PORT"] = "9"          # discard port: guaranteed refused
    r = send_confirmation("a@x.test", "http://x/confirm?token=t", "Acme")
    check("mode is failed, NOT emailed", r["mode"], "failed")
    check("ok is False", r["ok"], False)
    print("      reason:", r["reason"][:100])

    print("4. the 24-hour claim in the body matches the gate's TTL constant")
    import confirmation_gate as cg
    check("body says 24 hours and TTL is 24h", cg.DEFAULT_LINK_TTL, 24 * 3600)

    print("5. the body carries no marketing line and no unsubscribe link (purpose 1 only)")
    low = BODY.lower()
    check("no 'unsubscribe'", "unsubscribe" in low, False)
    check("says nothing was run yet", "nothing has been run yet" in low, True)

    for k, v in saved.items():
        os.environ.pop(k, None)
        if v is not None:
            os.environ[k] = v

    print("\nSELF-TEST: %d failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
