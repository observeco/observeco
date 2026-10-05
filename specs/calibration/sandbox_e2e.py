#!/usr/bin/env python3
"""End-to-end sandbox smoke test on the promoted 1.22.0.

Submits a real form over HTTP to the running sandbox and confirms the report RENDERS --
specifically that the rivals section is present and that the competitive_room change is visible.
No model call is faked: this exercises the live pipeline the owner would use.
"""
import urllib.request
import urllib.parse

DATA = {
    "business_name": "Stuff'd",
    "category": "F&B / salad and wraps",
    "positioning_sentence": "fresh made-to-order salads and wraps, prepared in front of you",
    "differentiator": "made-to-order freshness at a lower price than salad bars",
    "competitors_named": "SaladStop!, Supergreen, Six Hands",
    "customer_description": "office workers wanting a quick healthy lunch",
    "city": "Singapore",
    "website": "",
    "search_web": "on",
}

body = urllib.parse.urlencode(DATA).encode()
req = urllib.request.Request("http://127.0.0.1:8765/submit", data=body,
                             headers={"content-type": "application/x-www-form-urlencoded"})
with urllib.request.urlopen(req, timeout=900) as r:
    page = r.read().decode("utf-8", "replace")

print("HTTP 200, %d bytes" % len(page))
low = page.lower()

checks = [
    ("refusal shown",        "refus" in low),
    ("INTERNAL BUG (bad)",   "internal bug" in low),
    ("unpromoted (bad)",     "modified after promotion" in low),
    ("rivals section",       "rival" in low),
    ("a band word",          any(b in low for b in ("fragile", "contested", "viable", "strong"))),
    ("competitive room",     "competitive room" in low or "competitive_room" in low),
]
for label, ok in checks:
    print("   %-22s %s" % (label, "YES" if ok else "no"))

open("/tmp/sandbox_e2e.html", "w").write(page)
print("\nfull HTML -> /tmp/sandbox_e2e.html")
