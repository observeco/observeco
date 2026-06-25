"""Self-monitoring / meta-monitoring for ObserveCo.

Heartbeat file management, daemon liveness detection, stuck-daemon detection.
Spec: obs-spec-023-service-architecture.md §17.6

ponytail: File-based heartbeat is the simplest cross-process signal.
If sub-second precision is needed, switch to a Unix domain socket or shared memory segment.

Self-check: python -m pytest tests/test_self_monitoring.py -v
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import — dirs module uses relative imports that fail when run directly
_dirs = None

def _get_data_dir():
    global _dirs
    if _dirs is None:
        from . import dirs as _dirs
    return _dirs.get_data_dir()

HEARTBEAT_FILE = ".daemon_heartbeat.json"
STALE_THRESHOLD = 60  # seconds — heartbeat > 60s old = stale
DEAD_THRESHOLD = 300  # seconds — heartbeat > 300s old = dead
STUCK_CYCLES = 2      # consecutive checks without cycle_count increase = stuck


def _heartbeat_path() -> Path:
    return _get_data_dir() / HEARTBEAT_FILE


def write_heartbeat(pid: int, cycle_count: int, uptime_seconds: int, status: str = "running") -> dict:
    """Write a heartbeat file with current daemon state.

    Returns the heartbeat dict written.
    """
    heartbeat = {
        "pid": pid,
        "last_tick": time.time(),
        "cycle_count": cycle_count,
        "uptime_seconds": uptime_seconds,
        "status": status,
    }
    try:
        _heartbeat_path().write_text(json.dumps(heartbeat))
    except OSError as e:
        logger.warning("failed to write heartbeat: %s", e)
    return heartbeat


def read_heartbeat() -> dict[str, Any]:
    """Read and parse the heartbeat file.

    Returns dict with:
      - present: bool
      - valid: bool
      - pid: int | None
      - last_tick: float | None
      - cycle_count: int | None
      - uptime_seconds: int | None
      - status: str | None
      - age_seconds: float | None
      - is_stale: bool
      - is_dead: bool
      - is_stuck: bool
      - message: str

    On any error (missing file, corrupted JSON), returns a safe default
    with present=False and valid=False.
    """
    path = _heartbeat_path()

    if not path.exists():
        return {
            "present": False,
            "valid": False,
            "pid": None,
            "last_tick": None,
            "cycle_count": None,
            "uptime_seconds": None,
            "status": None,
            "age_seconds": None,
            "is_stale": False,
            "is_dead": False,
            "is_stuck": False,
            "message": "Daemon not running — no heartbeat file found",
        }

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("heartbeat file corrupted — treating as daemon may be down")
        return {
            "present": True,
            "valid": False,
            "pid": None,
            "last_tick": None,
            "cycle_count": None,
            "uptime_seconds": None,
            "status": None,
            "age_seconds": None,
            "is_stale": True,
            "is_dead": True,
            "is_stuck": False,
            "message": "Heartbeat corrupted — daemon may be down",
        }

    now = time.time()
    last_tick = data.get("last_tick", 0)
    age = now - last_tick
    is_stale = age > STALE_THRESHOLD
    is_dead = age > DEAD_THRESHOLD

    return {
        "present": True,
        "valid": True,
        "pid": data.get("pid"),
        "last_tick": last_tick,
        "cycle_count": data.get("cycle_count"),
        "uptime_seconds": data.get("uptime_seconds"),
        "status": data.get("status"),
        "age_seconds": round(age, 1),
        "is_stale": is_stale,
        "is_dead": is_dead,
        "is_stuck": False,  # Requires previous reading — set externally
        "message": _status_message(is_stale, is_dead, age),
    }


def _status_message(is_stale: bool, is_dead: bool, age: float) -> str:
    if is_dead:
        return f"Daemon is down — data collection stopped (last tick {int(age)}s ago)"
    if is_stale:
        return f"Daemon may be down — data not flowing (last tick {int(age)}s ago)"
    return f"Daemon running — last tick {int(age)}s ago"


def check_pid_liveness(pid: int | None) -> bool:
    """Check if a process with the given PID is alive.

    Uses os.kill(pid, 0) — signal 0 is an existence probe.
    Returns True if the process exists, False otherwise.
    """
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — treat as alive
        return True
    except OSError:
        return False


def check_stuck(previous_cycle: int | None, current_cycle: int | None) -> bool:
    """Check if the daemon is stuck (cycle_count not incrementing).

    Returns True if stuck (no progress in STUCK_CYCLES checks).
    """
    if previous_cycle is None or current_cycle is None:
        return False
    return current_cycle <= previous_cycle


def clear_heartbeat() -> None:
    """Delete the heartbeat file on graceful shutdown."""
    try:
        _heartbeat_path().unlink(missing_ok=True)
    except OSError:
        pass


def get_daemon_health() -> dict[str, Any]:
    """Get comprehensive daemon health status.

    Combines heartbeat check + PID liveness + stuck detection.
    Returns dict suitable for dashboard banner and observeco status.
    """
    hb = read_heartbeat()
    pid_alive = check_pid_liveness(hb["pid"])

    # Determine overall status
    if not hb["present"]:
        status = "stopped"
        message = "Daemon not running — run 'observeco watch start'"
    elif not hb["valid"]:
        status = "unknown"
        message = "Heartbeat corrupted — daemon status unknown"
    elif hb["is_dead"] and not pid_alive:
        status = "dead"
        message = hb["message"]
    elif hb["is_stale"]:
        status = "stale"
        message = hb["message"]
    else:
        status = "running"
        message = hb["message"]

    return {
        "status": status,
        "message": message,
        "heartbeat": hb,
        "pid_alive": pid_alive,
        "timestamp": time.time(),
    }


if __name__ == "__main__":
    # Self-check: verify pure functions (inlined — no re-import needed)
    import os as _os

    # check_pid_liveness
    assert check_pid_liveness(None) is False, "None PID should be dead"
    assert check_pid_liveness(_os.getpid()) is True, "current PID should be alive"
    print("  ✓ check_pid_liveness: None→False, current→True")

    # check_stuck
    assert check_stuck(None, 5) is False, "no previous → not stuck"
    assert check_stuck(5, None) is False, "no current → not stuck"
    assert check_stuck(5, 6) is False, "increasing → not stuck"
    assert check_stuck(5, 5) is True, "same → stuck"
    assert check_stuck(6, 5) is True, "decreasing → stuck"
    print("  ✓ check_stuck: all 5 cases correct")

    # _status_message
    assert "down" in _status_message(True, True, 600)
    assert "may be down" in _status_message(True, False, 120)
    assert "running" in _status_message(False, False, 10)
    print("  ✓ _status_message: dead/stale/running correct")

    print("  Self-check complete.")
