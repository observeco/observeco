"""test_gate_real.py — final end-to-end against the REAL instance (real keys, port 8765).

The happy path cannot be exercised here because Cloudflare's test token only passes the TEST
secret pair -- which is proof the real keys are being enforced. So this checks:
  A. the widget renders with the REAL sitekey, and the page does NOT carry the test-key warning;
  B. a submission with NO token is refused (the captcha is live);
  C. a submission with a bogus token is refused BY CLOUDFLARE;
  D. /confirm with a forged token is refused;
  E. the CRM still records refusals, so abuse attempts are visible rather than silent.
"""
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765"
DB = Path("/Users/seanfzc/projects/observeco-main/specs/calibration/sandbox/sandbox.db")
REAL_SITEKEY = "0x4AAAAAAFPD30SG4OI7CkHW"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("   %-56s %s%s" % (name, "PASS" if cond else "**FAIL**",
                             ("  " + str(detail)) if not cond else ""))


def get(path, timeout=120):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def post(path, data, timeout=120):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"content-type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


print("=== A. the widget renders with the REAL key, and no false test-key warning ===")
st, page = get("/")
check("GET / returns 200", st == 200, st)
check("the Turnstile widget is present", 'class="cf-turnstile"' in page)
check("...carrying the REAL sitekey", REAL_SITEKEY in page, "sitekey missing")
check("...loading Cloudflare's script", "challenges.cloudflare.com/turnstile" in page)
check("the pre-submit gate copy is shown", "Nothing is run until you click it" in page)
check("the test-key warning is ABSENT (real keys are set)",
      "RUNNING ON ITS PUBLIC" not in page)
check("no unrendered placeholder leaked", "{turnstile_widget}" not in page
      and "function turnstile_widget" not in page)

print("\n=== B/C. the captcha refuses a missing and a bogus token ===")
FORM = {"business_name": "Real Gate Test", "email": "real-gate@observeco.test",
        "category": "F&B / salad and wraps", "city": "Singapore",
        "positioning_sentence": "made-to-order salads for office workers",
        "competitors_named": "SaladStop!", "customer_description": "office workers"}
st1, b1 = post("/submit", FORM)
check("no token -> 400", st1 == 400, st1)
st2, b2 = post("/submit", {**FORM, "cf_turnstile_response": "XXXX.DUMMY.TOKEN.XXXX"})
check("a test token against REAL keys -> 400 (keys are enforced)", st2 == 400, st2)
check("...and the reason names the failed challenge", "couldn't verify" in b2.lower())

print("\n=== D. a forged confirmation link is refused ===")
st3, b3 = get("/confirm?token=Zm9yZ2Vk.9999999999.deadbeefdeadbeefdeadbeefdeadbeef")
check("forged token -> 400", st3 == 400, st3)
check("...and says the link is bad", "couldn't confirm" in b3.lower())

print("\n=== E. refusals are recorded, not silent ===")
con = sqlite3.connect(DB)
n = con.execute("SELECT COUNT(*) FROM submissions WHERE outcome='CAPTCHA_REFUSED'").fetchone()[0]
con.close()
check("the captcha refusals left a row in the CRM", n >= 1, "count=%d" % n)

print("\n" + "=" * 74)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
for f in FAIL:
    print("   -", f)
print("=" * 74)
sys.exit(1 if FAIL else 0)
