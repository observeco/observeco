"""test_turnstile_live.py — verify the REAL Turnstile keys against Cloudflare's siteverify.

This is the one test that needs the network, and it is the one that proves the key pair is live
and correctly formed:
  * a GARBAGE token must be rejected  -> proves the secret is being accepted by Cloudflare
    (a wrong secret returns `invalid-input-secret`; a right secret with a bad token returns
    `invalid-input-response`). The error CODE is what distinguishes the two.
  * the documented always-pass TEST secret + a dummy token must succeed -> proves the request
    shape (POST form-encoded, secret+response) is correct.

⚠ The secret itself is never printed. Only a fingerprint is, so this output is safe to paste.
"""
import hashlib
import os
import sys
from pathlib import Path

HERE = Path("/Users/seanfzc/projects/observeco-main/specs/calibration/sandbox")
sys.path.insert(0, str(HERE))
import confirmation_gate as g                                          # noqa: E402

# the keys Sean supplied, read from env if exported, else from the .env file
os.environ.setdefault("TURNSTILE_SITE_KEY", "0x4AAAAAAFPD30SG4OI7CkHW")
os.environ.setdefault("TURNSTILE_SECRET_KEY", "0x4AAAAAAFPD3wWTa4g1amFeaiY_8tKCgMA")

sk = g.secret_key()
print("site key :", g.site_key())
print("secret   : sha256:%s... (len %d, not printed)" % (
    hashlib.sha256(sk.encode()).hexdigest()[:16], len(sk)))
print("configured:", g.turnstile_configured())
print()

print("=== A. garbage token against the REAL secret ===")
r = g.verify_turnstile("definitely-not-a-real-turnstile-token")
print("   ok     :", r["ok"])
print("   reason :", r["reason"])
wrong_secret = "invalid-input-secret" in r["reason"]
wrong_token = "invalid-input-response" in r["reason"]
print("   -> secret REJECTED by Cloudflare   :", wrong_secret)
print("   -> token rejected (secret accepted):", wrong_token)
print()

print("=== B. the documented always-pass TEST secret, same request shape ===")
os.environ["TURNSTILE_SECRET_KEY"] = g.TEST_SECRET
r2 = g.verify_turnstile("XXXX.DUMMY.TOKEN.XXXX")
print("   ok     :", r2["ok"])
print("   reason :", r2["reason"])
print()

verdict = ("REAL KEYS WORK -- Cloudflare accepts the secret; only the token was bad"
           if wrong_token else
           "CHECK -- see the reason above")
print("VERDICT:", verdict)
print()
if r2["ok"]:
    print("The request shape is correct (the test pair passes end to end).")
else:
    print("⚠ The test pair did NOT pass -- the request shape itself may be wrong.")
