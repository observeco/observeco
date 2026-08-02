"""Hermes token bridge — export Hermes state.db usage into observeco.

Synergy design (2026-08-01):
observeco owns the token analytics platform (token_logs table, dashboard,
aggregation, cost computation). Its `watch` source (95% of rows) only captures
system-prompt-size estimates with output_tokens=0. Real API usage arrives
only via OTel spans (~5% of rows).

Hermes records TRUE usage in its own state.db sessions table:
  input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
  reasoning_tokens, actual_cost_usd, billing_provider.

This module reads Hermes sessions and writes real usage into observeco's
existing token_logs table (source='hermes') via Database.log_token_turn().
It complements watch/otel — it does NOT duplicate them.

Usage (via CLI):
  observeco tokens-sync              # incremental sync (since last cursor)
  observeco tokens-sync --full       # full resync (all sessions)
  observeco tokens-sync --dry-run    # report only, no writes

Idempotent: dedups on session_id (skips sessions already synced, tracked in
a state file). Requires read access to ~/.hermes/state.db (Hermes sessions).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

HERMES_STATE_DB = Path(os.path.expanduser("~/.hermes/state.db"))
STATE_FILE = Path(os.path.expanduser("~/.hermes/state/hermes_tokens_bridge.json"))
BATCH_SIZE = 200
SGT = timezone(timedelta(hours=8))


def _log(msg: str) -> None:
    ts = datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_synced_session_rowid": 0, "synced_count": 0, "last_sync": ""}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def read_hermes_sessions(min_rowid: int, full: bool = False) -> Iterator[sqlite3.Row]:
    """Yield sessions with real token usage from Hermes state.db.

    Uses rowid as monotonic cursor (sessions table has no reliable timestamp
    column for ordering; started_at is used for recorded_at only).
    """
    if not HERMES_STATE_DB.exists():
        return
    conn = sqlite3.connect(str(HERMES_STATE_DB))
    conn.row_factory = sqlite3.Row
    try:
        # ponytail: the token filter lives in the base WHERE (parenthesized);
        # the cursor filter is appended separately so SQL precedence stays
        # correct (a bare `a>0 OR b>0 AND rowid>N` swallows the cursor for
        # input-bearing sessions). Upgrade: parameterized query.
        base_where = "WHERE (input_tokens > 0 OR output_tokens > 0)"
        if not full:
            base_where += f" AND rowid > {int(min_rowid)}"
        cur = conn.execute(f"""
            SELECT rowid, id, input_tokens, output_tokens,
                   cache_read_tokens, cache_write_tokens, reasoning_tokens,
                   started_at, billing_provider, estimated_cost_usd, actual_cost_usd
            FROM sessions
            {base_where}
            ORDER BY rowid ASC
        """)
        for row in cur:
            yield row
    finally:
        conn.close()


def _derive_agent(session_id: str) -> str:
    """Derive agent name from session id prefix (cron_xxx → cron)."""
    for sep in ["_", "-"]:
        if sep in session_id:
            return session_id.split(sep)[0]
    return session_id


def sync_hermes_tokens(full: bool = False, dry_run: bool = False) -> dict:
    """Sync Hermes session usage into observeco token_logs (source=hermes)."""
    from observeco.db import Database

    state = load_state()
    cursor = 0 if full else state.get("last_synced_session_rowid", 0)

    _log(f"Reading Hermes sessions (rowid > {cursor})...")
    rows = list(read_hermes_sessions(cursor, full=full))
    total = len(rows)
    _log(f"Found {total} session(s) with token usage")
    if not total:
        return {"status": "noop", "written": 0, "skipped": 0, "total": 0}

    db = Database()
    written = 0
    skipped = 0
    conn = db._get_conn()
    try:
        for row in rows:
            sid = row["id"]
            total_tokens = (row["input_tokens"] or 0) + (row["output_tokens"] or 0)
            if total_tokens == 0:
                continue
            existing = conn.execute(
                "SELECT 1 FROM token_logs WHERE session_id = ? AND source = 'hermes' LIMIT 1",
                (sid,),
            ).fetchone()
            if existing:
                skipped += 1
                continue
            if dry_run:
                written += 1
                continue
            provider = row["billing_provider"] or (
                "deepseek" if (row["input_tokens"] or 0) > 100000 else "local"
            )
            cost = float(row["actual_cost_usd"] or row["estimated_cost_usd"] or 0)
            db.log_token_turn(
                agent_name=_derive_agent(sid),
                turn_id=f"hermes_{sid}",
                total_tokens=total_tokens,
                input_tokens=row["input_tokens"] or 0,
                output_tokens=row["output_tokens"] or 0,
                cache_creation_tokens=row["cache_write_tokens"] or 0,
                cache_read_tokens=row["cache_read_tokens"] or 0,
                provider=provider,
                cost=cost,
                source="hermes",
                session_id=sid,
                model="",
                latency_ms=0,
                recorded_at=int(row["started_at"] or time.time()),
            )
            written += 1
            if written % BATCH_SIZE == 0:
                conn.commit()
        conn.commit()
    finally:
        db.close()

    if not dry_run and written:
        last_rowid = max(r["rowid"] for r in rows)
        state["last_synced_session_rowid"] = max(state.get("last_synced_session_rowid", 0), last_rowid)
        state["synced_count"] = state.get("synced_count", 0) + written
        state["last_sync"] = datetime.now(SGT).isoformat()
        save_state(state)

    return {"status": "ok", "written": written, "skipped": skipped, "total": total}
