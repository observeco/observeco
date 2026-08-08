#!/usr/bin/env python3
"""P5 scrub: de-personalize the decision log for stranger-facing publish.

The decision log contains real session prompts: "[Sean Foo]" prefixes, absolute
/Users/seanfzc paths, and real user requests. Before the technical post can be
published as a checkable case study, this must be scrubbed.

What's scrubbed (personal identifiers):
- "[Sean Foo]" / "Sean Foo" -> "[User]"
- "/Users/seanfzc" -> "~" (relative, no username)
- "seanfzc" -> "user"

What's preserved (needed by the funnel + tests):
- session_id, gate, outcome, reason (the funnel reads these)
- first_user_msg is scrubbed but kept (informational; not read back for logic)

The original is preserved as decision-log-20260804.orig.json; the scrub writes
decision-log-20260804.json in place. Run with --write to apply, --check to
verify no personal identifiers remain.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

LOG = Path(__file__).parent / "selections" / "decision-log-20260804.json"
ORIG = Path(__file__).parent / "selections" / "decision-log-20260804.orig.json"

# Personal identifiers to scrub (order matters: longer first)
REPLACEMENTS = [
    ("[Sean Foo]", "[User]"),
    ("Sean Foo", "User"),
    ("/Users/seanfzc", "~"),
    ("seanfzc", "user"),
]


def scrub_text(s: str) -> str:
    for old, new in REPLACEMENTS:
        s = s.replace(old, new)
    return s


def scrub_log(data: dict) -> dict:
    """Return a deep-scrubbed copy of the decision log."""
    import copy
    out = copy.deepcopy(data)
    for d in out.get("decisions", []):
        if "first_user_msg" in d and isinstance(d["first_user_msg"], str):
            d["first_user_msg"] = scrub_text(d["first_user_msg"])
        for k in ("reason", "gate"):
            if k in d and isinstance(d[k], str):
                d[k] = scrub_text(d[k])
    return out


def has_personal(s: str) -> bool:
    return any(p in s for p in ["Sean Foo", "seanfzc", "/Users/seanfzc"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply the scrub")
    ap.add_argument("--check", action="store_true", help="verify no personal data remains")
    args = ap.parse_args()

    data = json.load(open(LOG))

    if args.check:
        s = json.dumps(data)
        hits = [p for p in ["Sean Foo", "seanfzc", "/Users/seanfzc"] if p in s]
        if hits:
            print(f"PERSONAL DATA REMAINS: {hits}")
            return 1
        print("clean: no personal identifiers remain")
        return 0

    if args.write:
        # preserve original once
        if not ORIG.exists():
            shutil.copy2(LOG, ORIG)
            print(f"preserved original -> {ORIG.name}")
        scrubbed = scrub_log(data)
        json.dump(scrubbed, open(LOG, "w"), indent=2)
        # verify
        s = json.dumps(scrubbed)
        hits = [p for p in ["Sean Foo", "seanfzc", "/Users/seanfzc"] if p in s]
        if hits:
            print(f"SCRUB INCOMPLETE: {hits}")
            return 1
        print(f"scrubbed {LOG.name}: {len(data['decisions'])} decisions, no personal data")
        return 0

    # dry-run: show what would change
    scrubbed = scrub_log(data)
    changed = 0
    for orig, new in zip(data["decisions"], scrubbed["decisions"]):
        if orig.get("first_user_msg") != new.get("first_user_msg"):
            changed += 1
    print(f"dry-run: {changed}/{len(data['decisions'])} decisions have scrubbed first_user_msg")
    print("run with --write to apply, --check to verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
