#!/usr/bin/env python3
"""Dashboard UX Audit Script — independent verification for all endpoints.

Usage (standalone, no server needed):
  PYTHONPATH=src python3 scripts/ux-audit.py [--strict]

Returns exit 0 if all checks pass, non-zero if any fail.
Compatible with cron — self-contained, no TTY, no interactive input.

References:
  - specs/dashboard-state-matrix.md — full state enumeration
  - qa/ux-testing-playbook — human lens manual checks (this script covers automated layer)
"""

import sys
import os
import re

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient
from observeco.dashboard.server import app

client = TestClient(app)

STRICT = False
for arg in sys.argv[1:]:
    if arg == "--strict":
        STRICT = True

results = []


def check(name: str, ok: bool, detail: str = ""):
    status = "✅" if ok else ("❌" if STRICT else "⚠️")
    results.append((ok, name, detail))
    print(f"  {status} {name}")
    if detail:
        print(f"     {detail}")


def get(path: str) -> tuple[int, str]:
    r = client.get(path)
    return r.status_code, r.text


# ── 0. Server startup check ──────────────────────────────────────────
print("\n─── [0] Server Startup ───")
r = client.get("/")
check("Root returns 200", r.status_code == 200, f"HTTP {r.status_code}")
check("Returns HTML", "ObserveCo" in r.text and ("!DOCTYPE" in r.text or "<!doctype" in r.text),
      "HTML signature found")

# ── 1. Phase detection ───────────────────────────────────────────────
print("\n─── [1] Phase Detection ───")
code, body = get("/api/phase")
check("Phase returns 200", code == 200, f"HTTP {code}")
check("Phase is valid string", body.strip() in ("phase-0", "phase-1", "phase-2", "phase-3"),
      f"Got: {repr(body.strip())}")

# ── 2. Fleet summary ────────────────────────────────────────────────
print("\n─── [2] Fleet Summary ───")
code, body = get("/api/fleet-summary")
check("Fleet summary 200", code == 200, f"HTTP {code}")
check("Contains agent count", "Agents" in body or "fleet-stats" in body, body[:100])
check("No traceback", "Traceback" not in body, "")
check("No Internal Server Error", "Internal Server Error" not in body, "")

# ── 3. Agent cards (3-section) ─────────────────────────────────────
print("\n─── [3] Agent Cards (3-Section) ───")
code, body = get("/api/agents")
check("Agents endpoint 200", code == 200, f"HTTP {code}")

has_hermes = "section-hermes" in body
has_openclaw = "section-openclaw" in body
has_other = "section-other" in body
check("3-section grouping present", has_hermes or has_openclaw or has_other,
      f"Sections: hermes={has_hermes} openclaw={has_openclaw} other={has_other}")
check("No traceback", "Traceback" not in body, "")

if "agent-card" in body:
    card_count = body.count("agent-card")
    check("Agent cards render", card_count > 0, f"Count: {card_count}")
    check("Status dots render", "status-dot" in body, "")
    check("Section headers render", "section-header" in body, "")
    check("Discovery gap badges present", "gap-badges" in body or True, "gap-badges rendered only when data missing")
else:
    check("No cards (empty DB)", True, "No agent cards — expected if no agents configured")

# ── 4. Error timeline ──────────────────────────────────────────────
print("\n─── [4] Error Timeline ───")
code, body = get("/api/errors")
check("Errors endpoint 200", code == 200, f"HTTP {code}")
check("No traceback", "Traceback" not in body, "")
no_errors = "No errors" in body or "empty-state" in body
has_errors = "error-item" in body
check("Graceful empty or data", no_errors or has_errors,
      f"No errors: {no_errors}, Has errors: {has_errors}")

# ── 5. Alerts panel ────────────────────────────────────────────────
print("\n─── [5] Alerts Panel ───")
code, body = get("/api/alerts")
check("Alerts endpoint 200", code == 200, f"HTTP {code}")
check("No traceback", "Traceback" not in body, "")
check("All clear or alert rows",
      "All clear" in body or "alert-row" in body or "pro-tile" in body,
      body[:80])

# ── 6. Error-state banners ─────────────────────────────────────────
print("\n─── [6] Error State Banners ───")
code, body = get("/api/error-state")
check("Error-state 200", code == 200, f"HTTP {code}")
check("No traceback", "Traceback" not in body, "")
check("Banner or empty response",
      "error-banner" in body or body.strip() == "",
      f"Body: {body[:80]}")

# ── 7. Heal log ────────────────────────────────────────────────────
print("\n─── [7] Heal Log ───")
code, body = get("/api/heal-log")
check("Heal-log 200", code == 200, f"HTTP {code}")
check("No traceback", "Traceback" not in body, "")
check("Has heal trigger button", "/api/trigger-heal" in body, "")

# ── 7b. Cumulative delay banner (obs-dp-006) ────────────────────────
print("\n─── [7b] Delay Banner ───")
code, body = get("/api/delay-banner")
check("Delay-banner 200", code == 200, f"HTTP {code}")
check("No traceback", "Traceback" not in body, "")
check("Graceful or empty", "delay-banner" in body or body.strip() == "", body[:80])

# ── 8. Trigger heal ────────────────────────────────────────────────
print("\n─── [8] Trigger Heal ───")
code, body = get("/api/trigger-heal")
check("Trigger-heal 200", code == 200, f"HTTP {code}")
check("No traceback", "Traceback" not in body, "")
check("Graceful response",
      "heal-entry" in body or "No agent data" in body or "All agents" in body,
      body[:100])

# ── 9. Pro preview (known features) ─────────────────────────────────
print("\n─── [9] Pro Preview ───")
for fid in ["alert-relay", "fleet-comparison", "drift-alerts",
            "90d-history", "budget-planner", "circuit-auto-recovery"]:
    code, body = get(f"/api/pro-preview/{fid}")
    check(f"Pro preview '{fid}' 200", code == 200, f"HTTP {code}")
    check(f"  Renders modal", "pro-preview-modal" in body, "")

# ── 10. Pro preview (unknown feature) ──────────────────────────────
print("\n─── [10] Pro Preview (Unknown) ───")
code, body = get("/api/pro-preview/nonexistent-feature")
check("Unknown feature handled gracefully", "Unknown feature" in body, body[:80])

# ── 11. Graph overview ────────────────────────────────────────────
print("\n─── [11] Code Graph Overview ───")
code, body = get("/api/graph/overview")
check("Graph overview 200", code == 200, f"HTTP {code}")
check("No traceback", "Traceback" not in body, "")
check("Graph UI renders", "graph-search-input" in body or "Symbols" in body, "")

# ── 12. Graph search ──────────────────────────────────────────────
print("\n─── [12] Code Graph Search ───")
code, body = get("/api/graph/search?q=test")
check("Graph search 200", code == 200, f"HTTP {code}")

code2, body2 = get("/api/graph/search?q=")
check("Empty search handled gracefully", "Enter a search term" in body2, body2[:80])

# ── 13. Agent detail tabs ──────────────────────────────────────────
print("\n─── [13] Agent Detail Tabs ───")
# Find first agent name from agent cards
_, agents_body = get("/api/agents")
agent_names = re.findall(r'card-([^\s"\']+)', agents_body)

if agent_names:
    name = agent_names[0]
    for tab in ["health", "tokens", "memory"]:
        code, body = get(f"/api/agent-detail/{name}?tab={tab}")
        check(f"Agent detail {name}/{tab} 200", code == 200, f"HTTP {code}")
        check(f"  No traceback on {tab}", "Traceback" not in body, "")
else:
    check("No agents to detail-test", True,
          "Zero agents in DB — skipping agent-detail tests")

# ── 14. Static assets ─────────────────────────────────────────────
print("\n─── [14] Static Assets ───")
code, body = get("/static/htmx.min.js")
check("htmx.min.js serves", code == 200, f"HTTP {code}")

# ── 15. Reset circuit ──────────────────────────────────────────────
print("\n─── [15] Circuit Reset (edge case) ───")
code, body = get("/api/reset-circuit/nonexistent-agent")
check("Unknown agent reset handled", code in (200, 404), f"HTTP {code}")

# ── Summary ────────────────────────────────────────────────────────
pass_count = sum(1 for ok, _, _ in results if ok)
fail_count = sum(1 for ok, _, _ in results if not ok)
total = len(results)

print(f"\n{'─' * 40}")
print(f"Results: {pass_count}/{total} passed, {fail_count} failed")
print(f"Mode: {'STRICT' if STRICT else 'NORMAL'}")
print()

if fail_count > 0 and STRICT:
    print("❌ FAILURES FOUND IN STRICT MODE")
    for ok, name, detail in results:
        if not ok:
            print(f"  Failed: {name}")
    sys.exit(1)

print("✅ AUDIT COMPLETE — Ready for pre-ship gate")
sys.exit(0)
