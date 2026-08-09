#!/usr/bin/env python3
"""Backfill dropped hermes.* span attrs from trace_spans into token_logs.

The otel listener was written against an older span schema: it read 6 of
the 14 attributes the Hermes OTEL plugin emits, dropping latency,
finish_reason, api_call_count, tool_name, reasoning_tokens. The raw spans
were retained in trace_spans.attributes (38,527 LLM spans) with everything
intact — this joins them back on the exact key
  token_logs.turn_id = 'otel_' || trace_spans.span_id
(73.5% coverage; the missing 26.5% are pre-retention rows before Jun 29).

Usage:
  python scripts/backfill_hermes_span_attrs.py --dry-run
  python scripts/backfill_hermes_span_attrs.py            # real run
  python scripts/backfill_hermes_span_attrs.py --db COPY  # against a copy
"""
import argparse
import json
import os
import sqlite3

DEFAULT_DB = os.path.expanduser("~/Library/Application Support/observeco/pulse.db")

# column -> span attribute key
FIELDS = {
    "latency_ms": "hermes.api_duration_ms",
    "finish_reason": "hermes.finish_reason",
    "api_call_count": "hermes.api_call_count",
    "tool_name": "hermes.tool_name",
    "reasoning_tokens": "hermes.reasoning_tokens",
}
_INT_COLS = {"latency_ms", "api_call_count", "reasoning_tokens"}


def _norm(attr_key: str, raw) -> int | str:
    """Normalize a span attribute to the column type; default when absent."""
    if raw is None:
        return 0 if attr_key in _INT_COLS else ""
    if attr_key in _INT_COLS:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0
    return str(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="backfill only first N rows (test)")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    limit_sql = f"LIMIT {int(args.limit)}" if args.limit else ""
    rows = conn.execute(f"""
        SELECT t.id, t.turn_id, s.attributes
        FROM token_logs t
        JOIN trace_spans s ON 'otel_' || s.span_id = t.turn_id
        WHERE t.source = 'otel'
          AND (t.latency_ms = 0 OR t.finish_reason = '' OR t.api_call_count = 0
               OR t.tool_name = '' OR t.reasoning_tokens = 0)
        {limit_sql}
    """).fetchall()
    print(f"rows to backfill: {len(rows)}", flush=True)

    updates = []  # (col_values dict, row_id)
    skipped = 0
    for r in rows:
        try:
            attrs = json.loads(r["attributes"] or "{}")
        except (ValueError, TypeError):
            skipped += 1
            continue
        vals = {}
        for col, attr in FIELDS.items():
            vals[col] = _norm(attr, attrs.get(attr))
        updates.append((vals, r["id"]))
        if args.dry_run and len(updates) <= 5:
            print(f"  [{r['turn_id']}] {vals}", flush=True)

    print(f"updates prepared: {len(updates)} (skipped parse: {skipped})", flush=True)
    if args.dry_run:
        print("DRY_RUN: no writes", flush=True)
        return

    # Row-by-row UPDATE (one-time backfill; ~38k rows is fine).
    cols = list(FIELDS.keys())
    set_sql = ", ".join(f"{c} = ?" for c in cols)
    conn.execute("BEGIN")
    try:
        for vals, rid in updates:
            conn.execute(
                f"UPDATE token_logs SET {set_sql} WHERE id = ?",
                [vals[c] for c in cols] + [rid],
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    print(f"BACKFILL_SPAN_ATTRS_DONE: {len(updates)} rows updated", flush=True)

    # Verify: how many otel rows now have each field set?
    for col in FIELDS:
        nz = conn.execute(
            f"SELECT COUNT(*) AS n FROM token_logs WHERE source='otel' AND {col} != 0 AND {col} != ''"
        ).fetchone()["n"]
        print(f"  otel rows with {col} set: {nz}", flush=True)


if __name__ == "__main__":
    main()
