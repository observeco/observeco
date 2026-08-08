#!/usr/bin/env python3
"""Backfill agent_name on historical hermes token_logs rows.

Context: commit 1e4aac5 fixed the bridge's agent derivation (prefer
sessions.source over the session_id prefix, which produced date names like
'20260701'). That fix only applies to rows written AFTER it landed — 3,319
of 3,734 hermes rows (89%) still carry date-derived agent names.

This mirrors scripts/backfill_hermes_models.py: re-derive agent_name from
Hermes state.db sessions.source for every date-like hermes row, using the
same _derive_agent(session_id, source) logic the fixed writer uses.

Usage:
  python scripts/backfill_hermes_agent_names.py --dry-run
  python scripts/backfill_hermes_agent_names.py            # real run
  python scripts/backfill_hermes_agent_names.py --db COPY  # against a copy
"""
import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from observeco.tracking.hermes_bridge import HERMES_STATE_DB, _derive_agent

DATE_LIKE = re.compile(r"^\d{8}$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.expanduser(
        "~/Library/Application Support/observeco/pulse.db"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # 1. Date-named hermes rows
    rows = conn.execute("""
        SELECT id, agent_name, session_id
        FROM token_logs
        WHERE source='hermes' AND agent_name GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
        ORDER BY id
    """).fetchall()
    print(f"date-named hermes rows to backfill: {len(rows)}", flush=True)
    if not rows:
        print("BACKFILL_AGENT_NOOP", flush=True)
        return

    # 2. Load Hermes sessions.source per session id (sessions.id is the
    #    session_id; the table has no session_id column)
    sdb = sqlite3.connect(str(HERMES_STATE_DB))
    sdb.row_factory = sqlite3.Row
    sid_to_source = {}
    cur = sdb.execute("SELECT id, source FROM sessions")
    for r in cur:
        if r["id"]:
            sid_to_source[r["id"]] = r["source"] or ""
    print(f"hermes sessions loaded: {len(sid_to_source)}", flush=True)

    # 3. Compute the corrected agent per row
    changes = {}
    missing_session = 0
    for r in rows:
        sid = r["session_id"] or ""
        source = sid_to_source.get(sid, "")
        if sid and sid not in sid_to_source:
            missing_session += 1
        corrected = _derive_agent(sid, source)
        old = r["agent_name"]
        if corrected != old:
            changes[r["id"]] = (old, corrected)

    print(f"rows needing change: {len(changes)} (missing sessions: {missing_session})", flush=True)

    # 4. Show the correction map (old -> new) for review
    by_pair = {}
    for old, new in changes.values():
        by_pair[(old, new)] = by_pair.get((old, new), 0) + 1
    for (old, new), n in sorted(by_pair.items(), key=lambda x: -x[1])[:15]:
        print(f"  {old!r} -> {new!r}  ({n} rows)", flush=True)

    if args.dry_run:
        print("DRY_RUN: no writes", flush=True)
        return

    # 5. Apply
    conn.executemany(
        "UPDATE token_logs SET agent_name = ? WHERE id = ?",
        [(new, rid) for rid, (old, new) in changes.items()],
    )
    conn.commit()
    print(f"BACKFILL_AGENT_DONE: {len(changes)} rows updated", flush=True)

    # 6. Verify
    still_date = conn.execute("""
        SELECT COUNT(*) AS n FROM token_logs
        WHERE source='hermes' AND agent_name GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
    """).fetchone()["n"]
    print(f"remaining date-named hermes rows: {still_date}", flush=True)
    if still_date > 0:
        print("BACKFILL_AGENT_INCOMPLETE", flush=True)
        sys.exit(1)
    print("BACKFILL_AGENT_PASS", flush=True)


if __name__ == "__main__":
    main()
