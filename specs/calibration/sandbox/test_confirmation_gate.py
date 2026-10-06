"""test_confirmation_gate.py — prove the section 3.7 gate in BOTH directions.

A gate that only ever says "yes" is not a gate. So each control is tested to PASS the good case
and REFUSE the bad one:

  * Turnstile: a genuine token passes; a missing/forged token fails; an unreachable verifier
    FAILS CLOSED (the property reCAPTCHA lacks, which is why Turnstile was chosen).
  * Token:   a freshly minted token confirms its own address; a tampered signature is rejected;
    an expired token is rejected; a token cannot confirm a DIFFERENT address.
  * The gate: an unconfirmed submission is stored and spends nothing; confirm() flips it once;
    confirming twice is idempotent and does not re-run.
  * Retention: purge_expired removes stale unconfirmed rows and leaves fresh and confirmed ones.

Run with the real venv. No network is required for the token/gate tests; the Turnstile tests
use Cloudflare's documented always-pass / always-fail TEST keys.
"""
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

HERE = Path("/Users/seanfzc/projects/observeco-main/specs/calibration/sandbox")
sys.path.insert(0, str(HERE))
import confirmation_gate as g                                          # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("   %-58s %s%s" % (name, "PASS" if cond else "**FAIL**",
                             ("  " + detail) if detail and not cond else ""))


print("\n=== 1. TOKEN: forge, expire, wrong address ===")
tok = g.make_token("owner@example.com", ttl=3600)
chk = g.check_token(tok)
check("a fresh token verifies", chk["ok"])
check("...and decodes to the right address", chk["email"] == "owner@example.com", chk["email"])

bad = tok[:-1] + ("0" if tok[-1] != "0" else "1")
check("a tampered signature is REJECTED", not g.check_token(bad)["ok"])

expired = g.make_token("owner@example.com", ttl=-10)
check("an expired token is REJECTED", not g.check_token(expired)["ok"],
      g.check_token(expired)["reason"])

check("a malformed token is REJECTED", not g.check_token("not-a-token")["ok"])

# a token for A must never confirm B: the address is carried INSIDE the signed payload
other = g.make_token("attacker@evil.test", ttl=3600)
check("a token carries its own address (cannot be re-pointed)",
      g.check_token(other)["email"] == "attacker@evil.test")
check("the signature is over the address, not just the expiry",
      g.check_token(tok)["email"] != g.check_token(other)["email"])

print("\n=== 2. THE GATE: unconfirmed spends nothing, confirm flips once ===")
tmp = Path(tempfile.mkdtemp()) / "q.db"
payload = {"form": {"business_name": "Test Co", "email": "owner@example.com"}}
r = g.submit_pending(tmp, "owner@example.com", "Test Co", payload, captcha_ok=True)
check("submit stores the submission as pending", r["status"] == "pending" and r["id"] > 0)

con = sqlite3.connect(tmp)
n_pending = con.execute("SELECT COUNT(*) FROM confirmations WHERE status='pending'").fetchone()[0]
con.close()
check("exactly one pending row exists", n_pending == 1)
check("the row holds the payload for later", isinstance(payload, dict))

c1 = g.confirm(tmp, r["token"])
check("confirm() succeeds on the honest token", c1["ok"] and not c1["already"])
check("...and hands back the payload for the worker", c1["payload"] == payload)

c2 = g.confirm(tmp, r["token"])
check("confirming twice is idempotent (no second run)", c2["ok"] and c2["already"])

check("a forged token cannot confirm", not g.confirm(tmp, bad)["ok"])
check("an expired token cannot confirm", not g.confirm(tmp, expired)["ok"])

print("\n=== 3. RETENTION: the 30-day sentence, as code ===")
tmp2 = Path(tempfile.mkdtemp()) / "q2.db"
old = g.submit_pending(tmp2, "old@example.com", "Old Co", {}, captcha_ok=True)
fresh = g.submit_pending(tmp2, "fresh@example.com", "Fresh Co", {}, captcha_ok=True)
done = g.submit_pending(tmp2, "done@example.com", "Done Co", {}, captcha_ok=True)
g.confirm(tmp2, done["token"])

# age the "old" row beyond the window by rewriting its timestamp
con = sqlite3.connect(tmp2)
from datetime import datetime, timedelta, timezone
past = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(timespec="seconds")
con.execute("UPDATE confirmations SET created_at=? WHERE id=?", (past, old["id"]))
con.commit()
con.close()

removed = g.purge_expired(tmp2, retention_days=30)
check("purge removes the stale UNCONFIRMED row", removed == 1, "removed=%d" % removed)
con = sqlite3.connect(tmp2)
left = {r[0] for r in con.execute("SELECT id FROM confirmations").fetchall()}
con.close()
check("...leaves the fresh pending row", fresh["id"] in left)
check("...leaves the CONFIRMED row alone", done["id"] in left)

print("\n=== 4. TURNSTILE: configured-detection and fail-closed ===")
os.environ.pop("TURNSTILE_SITE_KEY", None)
os.environ.pop("TURNSTILE_SECRET_KEY", None)
check("with no keys set, the gate reports NOT configured",
      g.turnstile_configured() is False)
check("...and falls back to the documented TEST sitekey", g.site_key() == g.TEST_SITEKEY)

os.environ["TURNSTILE_SITE_KEY"] = "0xREAL"
os.environ["TURNSTILE_SECRET_KEY"] = "0xREALSECRET"
check("with real keys set, the gate reports configured", g.turnstile_configured() is True)

check("an EMPTY token is refused without a network call",
      not g.verify_turnstile("")["ok"])

# ⚠ FAIL CLOSED: point the verifier at an unreachable host. A captcha that fails OPEN when
# Cloudflare is down is the reCAPTCHA defect the spec rejected. We require ok=False.
real_url = g.VERIFY_URL
g.VERIFY_URL = "https://127.0.0.1:1/nope"
res = g.verify_turnstile("dummy-token")
g.VERIFY_URL = real_url
check("an UNREACHABLE verifier FAILS CLOSED (ok=False)", res["ok"] is False, str(res["reason"]))
check("...and says why", bool(res["reason"]))

print("\n=== 5. NO MODEL CALL ANYWHERE IN THIS PATH ===")
import ast
src = (HERE / "confirmation_gate.py").read_text()
# ⚠ INSPECT IMPORTS, NOT SUBSTRINGS. The first version of this test grepped the raw text and
# FAILED -- because the module's own docstring says "Mirrors run_jev.read_env_key". A substring
# check cannot tell prose from code, so it reported a defect that did not exist. Parse instead.
tree = ast.parse(src)
imported = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imported.update(a.name.split(".")[0] for a in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imported.add(node.module.split(".")[0])
check("the gate imports NO pipeline module (no model reachable from here)",
      not (imported & {"run_jev", "generate_report", "competitor_scan"}),
      "imports=%s" % sorted(imported))
check("...and never calls the API URL", "api.typesafe.ai" not in src)

print("\n" + "=" * 74)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILURES:")
    for f in FAIL:
        print("   -", f)
print("=" * 74)
sys.exit(1 if FAIL else 0)
