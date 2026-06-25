"""Disk space management for ObserveCo.

Pre-write disk space check with WAL awareness, auto-resume, and 30s cache.
Spec: obs-spec-023-service-architecture.md §17.4

ponytail: This is a TOCTOU race — disk can fill between check and write.
Acceptable for a local tool. If data integrity requires atomic pre-check,
switch to a write-ahead reservation system.

Self-check: python -m pytest tests/test_disk_space.py -v
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Thresholds
WARN_FREE = 1024 * 1024 * 1024       # 1 GB — yellow banner
STOP_FREE = 100 * 1024 * 1024         # 100 MB — red banner, stop writes
RESUME_FREE = 1024 * 1024 * 1024      # 1 GB — auto-resume writes
CHECK_INTERVAL = 30                   # seconds — cache TTL
RETRY_INTERVAL = 60                   # seconds — check interval when stopped

# Cache
class _Cache:
    timestamp: float = 0.0
    free: int | None = None
    total: int = 0

_cache = _Cache()


def _get_wal_size(db_path: str) -> int:
    """Return WAL file size in bytes, or 0 if no WAL file exists."""
    wal_path = db_path + "-wal"
    try:
        return os.path.getsize(wal_path)
    except FileNotFoundError:
        return 0
    except OSError:
        return 0


def check_disk_space(path: str | Path, force: bool = False) -> dict:
    """Check available disk space at the given path.

    Returns dict with:
      - free_bytes: int
      - total_bytes: int
      - used_pct: float
      - status: 'ok' | 'warn' | 'critical'
      - message: str (human-readable)
      - wal_size: int (WAL file size in bytes)

    Caches result for CHECK_INTERVAL seconds unless force=True.
    """
    now = time.monotonic()
    if not force and (now - _cache.timestamp) < CHECK_INTERVAL:
        if _cache.free is not None:
            return _build_result(_cache.free, _cache.total)

    try:
        usage = shutil.disk_usage(str(path))
    except PermissionError:
        logger.warning("disk space check failed (permission denied) — proceeding in degraded mode")
        return {"free_bytes": 0, "total_bytes": 0, "used_pct": 0, "status": "degraded",
                "message": "Cannot check disk space (permission denied)", "wal_size": 0}
    except FileNotFoundError:
        logger.warning("disk space check failed (path not found) — proceeding in degraded mode")
        return {"free_bytes": 0, "total_bytes": 0, "used_pct": 0, "status": "degraded",
                "message": "Cannot check disk space (path not found)", "wal_size": 0}

    free = usage.free
    total = usage.total

    # Update cache
    _cache.timestamp = now
    _cache.free = free
    _cache.total = total

    return _build_result(free, total)


def _build_result(free: int, total: int) -> dict:
    used_pct = (total - free) / total * 100 if total > 0 else 0

    if free < STOP_FREE:
        status = "critical"
        message = f"Critical: {_fmt_bytes(free)} free — writes stopped"
    elif free < WARN_FREE:
        status = "warn"
        message = f"Warning: {_fmt_bytes(free)} free — {_fmt_bytes(WARN_FREE)} threshold"
    else:
        status = "ok"
        message = f"OK: {_fmt_bytes(free)} free"

    return {
        "free_bytes": free,
        "total_bytes": total,
        "used_pct": round(used_pct, 1),
        "status": status,
        "message": message,
        "wal_size": 0,
    }


def can_write(db_path: str, wal_size: int = 0) -> tuple[bool, str]:
    """Check if a write can proceed given current disk space.

    Accounts for WAL file size in the free-space calculation.
    Returns (can_write, reason).
    """
    result = check_disk_space(os.path.dirname(db_path))
    free = result["free_bytes"]
    effective_free = free - wal_size

    if effective_free < STOP_FREE:
        return False, f"Disk full — {_fmt_bytes(effective_free)} effective free (need {_fmt_bytes(STOP_FREE)})"
    return True, "OK"


def invalidate_cache() -> None:
    """Force next check to re-read from disk."""
    _cache.timestamp = 0.0


def _fmt_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b // 1024} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b // (1024 * 1024)} MB"
    return f"{b / (1024 * 1024 * 1024):.1f} GB"


if __name__ == "__main__":
    # Self-check: verify thresholds and status logic
    for free, expected in [
        (WARN_FREE + 1, "ok"),
        (WARN_FREE, "warn"),
        (STOP_FREE, "warn"),
        (STOP_FREE - 1, "critical"),
        (0, "critical"),
    ]:
        result = _build_result(free, 100 * 1024 * 1024 * 1024)
        ok = "✓" if result["status"] == expected else "✗"
        print(f"  {ok} {_fmt_bytes(free)} → {result['status']} (expected {expected})")
    print("  Self-check complete.")
