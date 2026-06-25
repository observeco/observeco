"""Tests for data integrity verification module.

Spec: obs-spec-023-service-architecture.md §17.5
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from observeco.data_integrity import (
    run_integrity_check,
    run_foreign_key_check,
    verify_backup,
    initialize_db,
    get_db_size,
    FULL_CHECK_LIMIT,
)


def test_get_db_size_nonexistent():
    """Non-existent DB should return 0."""
    assert get_db_size("/tmp/nonexistent.db") == 0


def test_get_db_size_existing():
    """Existing DB should return its size."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"x" * 1000)
        path = f.name
    try:
        size = get_db_size(path)
        assert size == 1000
    finally:
        os.unlink(path)


def test_integrity_check_skipped_no_db():
    """No DB file should return passed with skipped method."""
    result = run_integrity_check("/tmp/nonexistent.db")
    assert result["passed"] is True
    assert result["method"] == "skipped"


def test_integrity_check_passes():
    """Fresh DB should pass integrity check."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.commit()
        conn.close()
        result = run_integrity_check(path)
        assert result["passed"] is True
        assert result["method"] in ("integrity_check", "quick_check")
    finally:
        os.unlink(path)


def test_integrity_check_uses_quick_check_for_large_db():
    """DB > 100MB should use quick_check."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        # Create a DB that appears > 100MB by padding
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        conn.close()
        # Pad the file to appear > 100MB
        with open(path, "r+b") as f:
            f.seek(0, 2)  # Seek to end
            current = f.tell()
            if current < FULL_CHECK_LIMIT + 1:
                f.write(b"\x00" * (FULL_CHECK_LIMIT + 1 - current))
        result = run_integrity_check(path)
        assert result["method"] == "quick_check", f"Expected quick_check, got {result['method']} (size={get_db_size(path)})"
    finally:
        os.unlink(path)


def test_foreign_key_check_passes():
    """DB with no orphaned rows should pass."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))")
        conn.execute("INSERT INTO parent VALUES (1)")
        conn.execute("INSERT INTO child VALUES (1, 1)")
        conn.commit()
        conn.close()
        result = run_foreign_key_check(path)
        assert result["passed"] is True
        assert result["orphaned_count"] == 0
    finally:
        os.unlink(path)


def test_foreign_key_check_finds_orphans():
    """DB with orphaned rows should report them."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys=OFF")  # Allow orphan insert for testing
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))")
        conn.execute("INSERT INTO child VALUES (1, 999)")  # Orphan — no parent with id=999
        conn.commit()
        conn.close()
        result = run_foreign_key_check(path)
        assert result["passed"] is False
        assert result["orphaned_count"] > 0
    finally:
        os.unlink(path)


def test_verify_backup_nonexistent():
    """Non-existent backup should return invalid."""
    result = verify_backup("/tmp/nonexistent_backup.db")
    assert result["valid"] is False


def test_verify_backup_valid():
    """Valid backup should pass verification."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        result = verify_backup(path)
        assert result["valid"] is True
    finally:
        os.unlink(path)


def test_initialize_db_creates_new():
    """Initialize should create a new DB with WAL mode."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    os.unlink(path)  # Remove so initialize creates it
    try:
        result = initialize_db(path)
        assert result["created"] is True
        assert os.path.exists(path)
        # Verify WAL mode
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()
        assert mode == "wal"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_initialize_db_already_exists():
    """Initialize on existing DB should not overwrite."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        result = initialize_db(path)
        assert result["created"] is False
    finally:
        os.unlink(path)


def test_integrity_check_corrupted_db():
    """Corrupted DB should return passed=False."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
        f.write(b"SQLite format 3\x00" + b"\x00" * 100)
    try:
        result = run_integrity_check(path)
        assert result["passed"] is False
        assert len(result["errors"]) > 0
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_verify_backup_corrupted():
    """Corrupted backup should return valid=False."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
        f.write(b"garbage data")
    try:
        result = verify_backup(path)
        assert result["valid"] is False
        assert "corrupted" in result["message"]
    finally:
        if os.path.exists(path):
            os.unlink(path)
