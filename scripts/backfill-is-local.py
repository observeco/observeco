#!/usr/bin/env python3
"""Per-instance backfill: mark known-local providers and zero their cost.

This is a ONE-TIME migration for existing data. It uses an explicit provider
name list because provider names are instance-specific (your config's names).
Shipped code uses the general classifier (base_url + user override); this
script is the per-instance historical fix.

Usage:
    python scripts/backfill-is-local.py

Dry run (no changes):
    python scripts/backfill-is-local.py --dry-run
"""
import sys
import argparse

# ── CONFIGURE THIS LIST ──────────────────────────────────────────────────────
# Add the provider names from YOUR config that point at localhost/self-hosted.
# These are the names that appear in token_logs.provider for local models.
# Example: ["ollama-local", "custom-ollama", "ollama-cloud", "deepinfra"]
LOCAL_PROVIDERS: list[str] = [
    "ollama-local",
    "custom-ollama",
    "ollama-cloud",
    "deepinfra",
]
# ────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill is_local for known-local providers")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without modifying")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from observeco.db import Database

    db = Database()
    conn = db._get_conn()

    placeholders = ",".join("?" for _ in LOCAL_PROVIDERS)
    rows = conn.execute(
        f"SELECT COUNT(*) as cnt, SUM(cost) as tot_cost FROM token_logs "
        f"WHERE provider IN ({placeholders})",
        LOCAL_PROVIDERS,
    ).fetchone()
    count = rows["cnt"]
    current_cost = rows["tot_cost"] or 0.0

    if count == 0:
        print(f"No rows found for providers: {LOCAL_PROVIDERS}")
        print("Nothing to backfill.")
        return

    print(f"Found {count} rows with total cost ${current_cost:.4f}")
    print(f"Providers: {LOCAL_PROVIDERS}")

    if args.dry_run:
        print("DRY RUN — no changes made.")
        return

    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            f"UPDATE token_logs SET is_local = 1, cost = 0 "
            f"WHERE provider IN ({placeholders})",
            LOCAL_PROVIDERS,
        )
        conn.execute("COMMIT")
        print(f"Updated {count} rows: is_local=1, cost=0")
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    from pathlib import Path
    main()
