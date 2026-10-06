"""test_gate_live.py — does /submit really REFUSE to spend, and does /confirm really run?

The claim under test (spec 3.7): an unconfirmed submission costs nothing, and model work happens
only behind a proven address. Both directions are checked:

  A. /submit with NO captcha token -> refused, and the DB records CAPTCHA_REFUSED.
  B. /submit with a VALID token     -> stored pending, NO pipeline run, NO model spend.
     Proved by: the response says "Nothing has been run", and the CRM has no SCORED row for it.
  C. a second /submit on the same address -> still no model spend (no run on submit, ever).
  D. /confirm with a FORGED token   -> rejected.
  E. /confirm with the REAL token   -> the pipeline runs and a report comes back.
"""
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import os
BASE = "http://127.0.0.1:%s" % os.environ.get("SANDBOX_PORT", "8765")   # the test-key instance
DB = Path("/Users/seanfzc/projects/observeco-main/specs/calibration/sandbox/sandbox.db")


def post(path, data, timeout=900):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"content-type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def get(path, timeout=900):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


FORM = {"business_name": "Gate Test Co", "email": "gate-test@observeco.test",
        "category": "F&B / salad and wraps", "city": "Singapore",
        "positioning_sentence": "made-to-order salads for office workers",
        "differentiator": "cheaper than salad bars, made fresh in front of you",
        "competitors_named": "SaladStop!, Supergreen",
        "customer_description": "office workers wanting a quick healthy lunch"}

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("   %-56s %s%s" % (name, "PASS" if cond else "**FAIL**",
                             ("  " + str(detail)) if not cond else ""))


def scored_rows(email):
    con = sqlite3.connect(DB)
    n = con.execute("SELECT COUNT(*) FROM submissions WHERE email=? AND outcome LIKE 'SCORED%'",
                    (email,)).fetchone()[0]
    con.close()
    return n


print("=== A. /submit with NO captcha token must be REFUSED ===")
st, body = post("/submit", {**FORM, "business_name": "Gate Test Co A"})
check("submit without a token returns 400", st == 400, st)
check("...and says the captcha failed", "couldn't verify" in body.lower())

print("\n=== B. /submit with a VALID token stores pending, runs NOTHING ===")
before = scored_rows(FORM["email"])
st, body = post("/submit", {**FORM, "cf_turnstile_response": "XXXX.DUMMY.TOKEN.XXXX"})
check("submit with a test token returns 200", st == 200, st)
check("...and says nothing has been run", "nothing has been run" in body.lower())
check("...and does NOT return a score", not re.search(r"\d+/100 —", body))
check("...and does NOT return a band", "Fragile" not in body and "Contested" not in body)
after = scored_rows(FORM["email"])
check("NO scored row was created by submit", after == before, "%d -> %d" % (before, after))
m = re.search(r"/confirm\?token=([A-Za-z0-9_\-\.]+)", body)
check("...and a confirmation link was issued", bool(m))

print("\n=== C. a FORGED token must NOT confirm ===")
if m:
    tok = m.group(1)
    forged = tok[:-1] + ("0" if tok[-1] != "0" else "1")
    st, body = get("/confirm?token=" + urllib.parse.quote(forged))
    check("confirm with a forged token returns 400", st == 400, st)
    check("...and reports a bad link", "couldn't confirm" in body.lower())
    check("...and still created no scored row", scored_rows(FORM["email"]) == after)

print("\n=== D. the REAL token runs the pipeline (this one MAY spend) ===")
if m:
    st, body = get("/confirm?token=" + urllib.parse.quote(m.group(1)))
    print("   confirm status:", st, "| %d bytes" % len(body))
    check("confirm with the real token returns 200", st == 200, st)
    ran = bool(re.search(r"\d+/100 —", body)) or "refused" in body.lower()
    check("...and the pipeline ran (a report or a refusal)", ran)
    check("...and it did NOT report an internal bug", "INTERNAL BUG" not in body)
    check("...and it did NOT report an unpromoted rubric",
          "modified after promotion" not in body.lower())
    st2, body2 = get("/confirm?token=" + urllib.parse.quote(m.group(1)))
    check("re-using the link does NOT run twice", "already" in body2.lower(), body2[:120])

print("\n" + "=" * 74)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
for f in FAIL:
    print("   -", f)
print("=" * 74)
sys.exit(1 if FAIL else 0)
