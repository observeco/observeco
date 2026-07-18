#!/usr/bin/env python3
"""Verify error timeline route (/api/timeline/errors) against raw DB.

Usage:
    python3 scripts/verify_error_timeline.py

Exits 0 if all checks pass, 1 if any mismatch found.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from observeco.db import Database

PASS = "✓"
FAIL = "✗"
db = Database()


def get_raw_errors(now: int, days: int = 1) -> list[dict]:
    """Query raw errors from DB matching the route's logic."""
    since = now - (days * 86400)
    errors = db.get_errors(limit=200)
    errors = [e for e in errors if e.get("timestamp", 0) >= since]
    return errors


def extract_error_count(html: str) -> int:
    """Count error rows in the timeline HTML."""
    return len(re.findall(r'class="tl-row\b', html))


def main():
    now = int(time.time())

    print("Verifying /api/timeline/errors")
    print()

    # 1. Get raw errors
    print("Querying raw DB...")
    raw = get_raw_errors(now, days=1)
    print(f"  {len(raw)} errors in last 24h")
    print()

    # 2. Hit the route
    print("Fetching route...")
    import urllib.request
    url = "http://127.0.0.1:8899/api/timeline/errors?days=1"
    req = urllib.request.Request(url)
    req.add_header("X-ObserveCo-Token", "FxrXunlGzEHN6mtX550m6okEgSjfe5xnI84YOIDLLFk")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode()
    except Exception as e:
        print(f"  {FAIL} Failed to fetch route: {e}")
        sys.exit(1)
    print(f"  {len(html)} bytes received")
    print()

    all_pass = True

    print("=== Error Timeline ===")
    route_count = extract_error_count(html)
    if route_count == len(raw):
        print(f"  {PASS} error_count: {route_count}")
    else:
        print(f"  {FAIL} error_count: got={route_count}, expected={len(raw)}")
        all_pass = False

    # Spot-check: first error message appears
    if raw:
        first_msg = raw[0].get("error_message", "")[:30]
        if first_msg and first_msg in html:
            print(f"  {PASS} First error message present: {first_msg}...")
        else:
            print(f"  {FAIL} First error message missing: {first_msg}...")
            all_pass = False

    print()
    if all_pass:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED — see above")
        sys.exit(1)


if __name__ == "__main__":
    main()
