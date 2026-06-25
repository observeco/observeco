"""Data integrity verification for ObserveCo.

SQLite integrity checks, degraded mode, foreign key validation, backup verification.
Spec: obs-spec-023-service-architecture.md §17.5

ponytail: PRAGMA integrity_check reads every page — O(n) on DB size.
For DBs > 100MB, use PRAGMA quick_check instead (checks header + first page only, ~100x faster).
For DBs < 100MB, use full integrity_check.
Upgrade path: switch to sqlite3's built-in incremental integrity checking for zero-downtime verification.

Self-check: python -m pytest tests/test_data_integrity.py -v
"""

from __future__ import annotations

import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

# Size threshold for full vs quick check (bytes)
FULL_CHECK_LIMIT = 100 * 1024 * 1024  # 100 MB


def get_db_size(db_path: str) -> int:
    """Return DB file size in bytes, or 0 if file doesn't exist."""
    try:
        return os.path.getsize(db_path)
    except FileNotFoundError:
        return 0
    except OSError:
        return 0


def run_integrity_check(db_path: str) -> dict:
    """Run integrity check on the given SQLite database.

    Returns dict with:
      - passed: bool
      - method: 'integrity_check' | 'quick_check' | 'skipped'
      - errors: list[str] (empty if passed)
      - db_size: int
      - message: str
    """
    db_size = get_db_size(db_path)

    if db_size == 0:
        return {
            "passed": True,
            "method": "skipped",
            "errors": [],
            "db_size": 0,
            "message": "No database file — nothing to check",
        }

    method = "quick_check" if db_size > FULL_CHECK_LIMIT else "integrity_check"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA {method}")
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == "ok":
            return {
                "passed": True,
                "method": method,
                "errors": [],
                "db_size": db_size,
                "message": f"Database integrity verified ({method})",
            }
        else:
            errors = [str(result[0])] if result else ["Unknown integrity error"]
            return {
                "passed": False,
                "method": method,
                "errors": errors,
                "db_size": db_size,
                "message": f"Database integrity FAILED ({method}): {errors[0]}",
            }
    except sqlite3.Error as e:
        return {
            "passed": False,
            "method": method,
            "errors": [str(e)],
            "db_size": db_size,
            "message": f"Database integrity check error: {e}",
        }


def run_foreign_key_check(db_path: str) -> dict:
    """Run foreign key check on the given SQLite database.

    Returns dict with:
      - passed: bool
      - orphaned_count: int
      - details: list[dict]
      - message: str
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"passed": True, "orphaned_count": 0, "details": [], "message": "No orphaned rows"}

        details = []
        for row in rows:
            details.append({
                "table": row[0],
                "rowid": row[1],
                "parent": row[2],
                "fkid": row[3],
            })

        return {
            "passed": False,
            "orphaned_count": len(rows),
            "details": details,
            "message": f"Found {len(rows)} orphaned row(s) — run 'observeco db repair' if data integrity is a concern",
        }
    except sqlite3.Error as e:
        return {"passed": False, "orphaned_count": 0, "details": [], "message": f"Foreign key check error: {e}"}


def verify_backup(backup_path: str) -> dict:
    """Verify a backup file before restoring.

    Returns dict with:
      - valid: bool
      - message: str
    """
    if not os.path.exists(backup_path):
        return {"valid": False, "message": "Backup file not found"}

    result = run_integrity_check(backup_path)
    if result["passed"]:
        return {"valid": True, "message": "Backup verified — integrity check passed"}
    else:
        return {"valid": False, "message": f"Backup is corrupted — no valid restore point available: {result['message']}"}


def initialize_db(db_path: str) -> dict:
    """Initialize a new SQLite database with WAL mode.

    Returns dict with:
      - created: bool
      - message: str
    """
    if os.path.exists(db_path):
        return {"created": False, "message": "Database already exists"}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA schema_version")
        conn.commit()
        conn.close()
        logger.info("New database initialized at %s", db_path)
        return {"created": True, "message": "New database initialized with WAL mode"}
    except sqlite3.Error as e:
        return {"created": False, "message": f"Failed to initialize database: {e}"}


if __name__ == "__main__":
    # Self-check: verify integrity check logic
    import tempfile
    # Test 1: nonexistent DB
    r = run_integrity_check("/tmp/nonexistent_check.db")
    assert r["passed"] and r["method"] == "skipped", f"Expected skipped, got {r['method']}"
    print("  ✓ nonexistent DB → skipped")

    # Test 2: fresh DB passes
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        p = f.name
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    r = run_integrity_check(p)
    assert r["passed"], f"Expected passed, got {r}"
    print(f"  ✓ fresh DB → {r['method']} passed")
    os.unlink(p)

    # Test 3: foreign key check
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        p = f.name
    conn = sqlite3.connect(p)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("CREATE TABLE p (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE c (id INTEGER PRIMARY KEY, pid INTEGER REFERENCES p(id))")
    conn.execute("INSERT INTO c VALUES (1, 999)")
    conn.commit()
    conn.close()
    r = run_foreign_key_check(p)
    assert not r["passed"], f"Expected orphaned rows, got {r}"
    print(f"  ✓ orphaned rows detected ({r['orphaned_count']} found)")
    os.unlink(p)

    print("  Self-check complete.")
