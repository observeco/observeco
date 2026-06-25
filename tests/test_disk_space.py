"""Tests for disk space management module.

Spec: obs-spec-023-service-architecture.md §17.4
"""

from __future__ import annotations

import os
import tempfile
from observeco.disk_space import (
    check_disk_space,
    can_write,
    invalidate_cache,
    _get_wal_size,
    _build_result,
    WARN_FREE,
    STOP_FREE,
    RESUME_FREE,
)


def test_check_disk_space_returns_ok():
    """Normal disk should return ok status."""
    result = check_disk_space("/", force=True)
    assert "status" in result
    assert "free_bytes" in result
    assert "message" in result
    assert result["free_bytes"] > 0


def test_check_disk_space_caches():
    """Second call within interval should use cache."""
    result1 = check_disk_space("/", force=True)
    result2 = check_disk_space("/")
    assert result2["free_bytes"] == result1["free_bytes"]


def test_invalidate_cache():
    """Invalidate should force re-read."""
    result1 = check_disk_space("/", force=True)
    invalidate_cache()
    result2 = check_disk_space("/", force=True)
    assert result2["free_bytes"] > 0


def test_can_write_returns_true():
    """Normal disk should allow writes."""
    ok, msg = can_write("/")
    assert ok is True


def test_get_wal_size_nonexistent():
    """Non-existent WAL file should return 0."""
    assert _get_wal_size("/tmp/nonexistent.db") == 0


def test_get_wal_size_existing():
    """Existing WAL file should return its size."""
    with tempfile.NamedTemporaryFile(suffix=".db-wal", delete=False) as f:
        f.write(b"x" * 100)
        wal_path = f.name
    db_path = wal_path.replace("-wal", "")
    try:
        size = _get_wal_size(db_path)
        assert size == 100
    finally:
        os.unlink(wal_path)


def test_check_disk_space_nonexistent_path():
    """Non-existent path should return degraded status."""
    result = check_disk_space("/nonexistent/path", force=True)
    assert result["status"] == "degraded"


def test_warn_threshold():
    """WARN_FREE should be 1 GB."""
    assert WARN_FREE == 1024 * 1024 * 1024


def test_stop_threshold():
    """STOP_FREE should be 100 MB."""
    assert STOP_FREE == 100 * 1024 * 1024


def test_resume_threshold():
    """RESUME_FREE should be 1 GB."""
    assert RESUME_FREE == 1024 * 1024 * 1024


def test_build_result_ok():
    """Free > WARN_FREE should return ok status."""
    result = _build_result(WARN_FREE + 1, 100 * 1024 * 1024 * 1024)
    assert result["status"] == "ok"


def test_build_result_warn():
    """Free between STOP_FREE and WARN_FREE should return warn status."""
    result = _build_result(STOP_FREE, 100 * 1024 * 1024 * 1024)
    assert result["status"] == "warn"


def test_build_result_critical():
    """Free < STOP_FREE should return critical status."""
    result = _build_result(STOP_FREE - 1, 100 * 1024 * 1024 * 1024)
    assert result["status"] == "critical"


def test_build_result_zero_total():
    """Zero total should not divide by zero."""
    result = _build_result(0, 0)
    assert result["used_pct"] == 0


def test_can_write_returns_false_when_full():
    """can_write should return False when effective free < STOP_FREE."""
    ok, msg = can_write("/tmp", wal_size=10**15)  # 1 PB — guaranteed to exceed free space
    assert ok is False
    assert "Disk full" in msg
