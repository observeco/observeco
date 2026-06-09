#!/usr/bin/env python3
"""CI-enforceable F2 and F9 checks for the Master Fidelity Gate.

Runs against the local TestClient — no server needed.
Exits 0 if all pass, 1 on any failure.
"""
import sys

sys.path.insert(0, "src")

from fastapi.testclient import TestClient

from observeco.dashboard.server import app

client = TestClient(app)

failures = []

r = client.get("/")

# Skip massive inline CSS in <head>
body_idx = r.text.lower().find("<body")
body_text = r.text[body_idx:].lower() if body_idx >= 0 else r.text.lower()

# F2 — first-run keywords in /
f2_keywords = ["guided", "setup", "first time", "add an agent", "detect agents"]
f2_hits = [kw for kw in f2_keywords if kw in body_text]
if not f2_hits:
    failures.append("F2: No first-run experience keywords in page body")

# F9 — telemetry/security/privacy notice
f9_keywords = ["telemetry", "localhost", "warning", "opt.in", "privacy", "local only"]
f9_hits = [kw for kw in f9_keywords if kw in body_text]
if not f9_hits:
    failures.append("F9: No telemetry/security/privacy notice in page body")

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)

print(f"F2 OK: first-run keywords found: {f2_hits}")
print(f"F9 OK: security keywords found: {f9_hits}")
print("All CI checks passed.")
sys.exit(0)
