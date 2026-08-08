#!/usr/bin/env python3
"""Backfill `model` on historical hermes-source token_logs rows.

Context: the hermes bridge (tracking/hermes_bridge.py) only started writing
`model` in commit 1e4aac5. Historical hermes rows have model='', which makes
v_token_effective.overlap_suspect unable to match orphan otel spans to hermes
rows — the ~$291 of double-counted orphan cost stays invisible (verify script
shows suspect=$0.00 pre-backfill).

This script joins hermes token_logs rows to Hermes session_model_usage on
session_id and writes the dominant model per session (highest token sum; where
tied, first alphabetically and logs a warning). It is idempotent: rows with
model already set are skipped.

Usage:
  observeco tokens-backfill-models [--db PATH] [--dry-run] [--hermes-state PATH]

  --db PATH        observeco pulse.db path (default: live DB)
  --hermes-state   Hermes state.db path (default ~/.hermes/state.db)
  --dry-run        report only, no writes
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

DEFAULT_PULSE = str(Path.home() / "Library/Application Support/observeco/pulse.db")
DEFAULT_HERMES = str(Path.home() / ".hermes/state.db")


def dominant_model_per_session(hermes_state: str) -> dict[str, str]:
    """session_id -> dominant model (by input+output tokens) from Hermes."""
    if not Path(hermes_state).exists():
        print(f"WARN: Hermes state.db not found at {hermes_state}", file=sys.stderr)
        return {}
    conn = sqlite3.connect(hermes_state)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT session_id, model,
               SUM(input_tokens + output_tokens + cache_read_tokens + cache_write_tokens) as toks
        FROM session_model_usage
        WHERE model IS NOT NULL AND model != ''
        GROUP BY session_id, model
        """
    ).fetchall()
    conn.close()
    best: dict[str, tuple[str, int]] = {}
    ties: dict[str, list[str]] = {}
    for r in rows:
        sid, model, toks = r["session_id"], r["model"], r["toks"] or 0
        if sid not in best or toks > best[sid][1] or (toks == best[sid][1] and model < best[sid][0]):
            best[sid] = (model, toks)
            ties.pop(sid, None)
        elif toks == best[sid][1] and model != best[sid][0]:
            ties.setdefault(sid, [best[sid][0]]).append(model)
    for sid, models in ties.items():
        print(f"WARN: tie for session {sid}: {models} — picked {best[sid][0]}", file=sys.stderr)
    return {sid: m for sid, (m, _) in best.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DEFAULT_PULSE)
    ap.add_argument("--hermes-state", default=DEFAULT_HERMES)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not Path(args.db).exists():
        print(f"ERROR: pulse.db not found at {args.db}", file=sys.stderr)
        return 1

    models = dominant_model_per_session(args.hermes_state)
    print(f"Loaded {len(models)} session->model mappings from Hermes", flush=True)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, session_id FROM token_logs "
        "WHERE source='hermes' AND (model IS NULL OR model = '')"
    ).fetchall()
    print(f"Found {len(rows)} historical hermes rows without model", flush=True)

    upd = 0
    missing = 0
    for r in rows:
        model = models.get(r["session_id"], "")
        if not model:
            missing += 1
            continue
        if args.dry_run:
            upd += 1
            continue
        conn.execute("UPDATE token_logs SET model=? WHERE id=?", (model, r["id"]))
        upd += 1
    conn.commit()
    conn.close()

    print(f"DRY-RUN: would update {upd}" if args.dry_run else f"Updated {upd} rows")
    print(f"Skipped {missing} rows with no session_model_usage mapping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
