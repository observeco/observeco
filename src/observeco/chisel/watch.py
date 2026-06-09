"""observeco chisel watch — Auto-compression daemon.

Monitors SOUL.md files for changes and auto-compresses them.
Uses fswatch for file system events.

Two modes:
  - Daemon mode: background process with PID file (run via CLI)
  - Foreground mode: attached to terminal (debug/testing)

Usage:
  observeco chisel watch start    # Start daemon
  observeco chisel watch stop     # Stop daemon
  observeco chisel watch status   # Is it running?
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

_DATA_DIR = Path.home() / ".observeco"
_HEARTBEAT_PATH = _DATA_DIR / ".chisel_watch_heartbeat.json"
_PID_PATH = _DATA_DIR / ".chisel_watch.pid"
_LOG_PATH = _DATA_DIR / ".chisel_watch.log"

# SOUL.md directories to watch
_PROFILES_DIR = Path.home() / ".hermes" / "profiles"
_ROOT_SOUL = Path.home() / ".hermes" / "SOUL.md"

# ── Timing ───────────────────────────────────────────────────────────────────

DEBOUNCE_SECONDS = 2  # Wait this long after last modification before compressing
HEARTBEAT_INTERVAL = 60  # Write heartbeat every 60s


def _find_all_souls() -> list[Path]:
    """Discover all SOUL.md files across profiles and root."""
    souls = []
    if _ROOT_SOUL.exists():
        souls.append(_ROOT_SOUL)
    if _PROFILES_DIR.is_dir():
        for p in _PROFILES_DIR.rglob("SOUL.md"):
            souls.append(p)
    return souls


def _agent_name_from_soul(soul_path: Path) -> str:
    """Derive agent name from SOUL.md file path."""
    # Root SOUL → "hermes"
    if soul_path == _ROOT_SOUL:
        return "hermes"
    # Profile SOUL → profile directory name
    if "profiles" in soul_path.parts:
        idx = soul_path.parts.index("profiles")
        if idx + 1 < len(soul_path.parts):
            return soul_path.parts[idx + 1]
    # Fallback: parent directory name
    return soul_path.parent.name


def _get_mode_for_agent(agent_name: str) -> str:
    """Determine compression mode for an agent.

    Checks config file for per-agent mode preference.
    Defaults to 'lite' if not configured.
    """
    config_path = _DATA_DIR / "chisel_config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            return config.get(agent_name, {}).get("mode", "lite")
        except (json.JSONDecodeError, OSError):
            pass
    return "lite"


def compress_soul_file(soul_path: Path, triggered_by: str = "daemon") -> Optional[dict]:
    """Compress a single SOUL.md file and log the result."""
    agent = _agent_name_from_soul(soul_path)
    mode = _get_mode_for_agent(agent)


    try:
        from observeco.chisel.skill_compress import run_compress
        result = run_compress(agent_name=agent, mode=mode, filepath=str(soul_path))
        # Log to compress_log
        from observeco.db import Database
        db = Database()
        conn = db._get_conn()
        conn.execute(
            "INSERT INTO compress_log (agent_name, mode, before_tokens, after_tokens, savings, "
            "savings_pct, file_path, backup_path, triggered_by, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (agent, mode, result["before_tokens"], result["after_tokens"],
             result["savings"], result["savings_pct"], str(soul_path),
             result.get("backup", ""), triggered_by, int(time.time())),
        )
        conn.commit()
        return result
    except Exception as e:
        logger.error(f"Auto-compress failed for {agent}: {e}")
        return None


def _write_heartbeat(cycle: int, status: str = "running") -> None:
    """Write heartbeat file for external monitors."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _HEARTBEAT_PATH.write_text(json.dumps({
            "pid": os.getpid(),
            "cycle": cycle,
            "status": status,
            "timestamp": int(time.time()),
        }))
    except Exception:
        pass


def _pid_file() -> Optional[int]:
    """Read PID file. Returns PID or None."""
    try:
        return int(_PID_PATH.read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _is_pid_alive(pid: int) -> bool:
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def status() -> dict:
    """Return structured status of the daemon."""
    pid = _pid_file()
    alive = pid is not None and _is_pid_alive(pid)
    age = None
    try:
        if _HEARTBEAT_PATH.exists():
            data = json.loads(_HEARTBEAT_PATH.read_text())
            age = time.time() - data.get("timestamp", 0)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {"running": alive, "pid": pid, "heartbeat_age": age}


def start_daemon() -> None:
    """Start the auto-compression daemon as a background process."""
    pid = _pid_file()
    if pid and _is_pid_alive(pid):
        print(f"Chisel watch daemon already running (PID {pid})")
        return

    import subprocess as sp
    kwargs: dict = {
        "stdout": sp.DEVNULL,
        "stderr": sp.DEVNULL,
        "stdin": sp.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = sp.DETACHED_PROCESS | sp.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    sp.Popen(
        [sys.executable, "-m", "observeco", "chisel", "watch", "foreground"],
        **kwargs,
    )
    time.sleep(1)
    pid = _pid_file()
    if pid and _is_pid_alive(pid):
        print(f"Chisel watch daemon started (PID {pid})")
    else:
        print("Failed to start chisel watch daemon")


def stop_daemon() -> None:
    """Stop the auto-compression daemon."""
    pid = _pid_file()
    if pid is None:
        print("No PID file found. Daemon not running.")
        return
    if not _is_pid_alive(pid):
        print(f"Daemon (PID {pid}) is not running. Cleaning up PID file.")
        _PID_PATH.unlink(missing_ok=True)
        return
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for graceful shutdown
        for _ in range(10):
            if not _is_pid_alive(pid):
                break
            time.sleep(0.5)
        if _is_pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
        _PID_PATH.unlink(missing_ok=True)
        print(f"Chisel watch daemon (PID {pid}) stopped.")
    except Exception as e:
        print(f"Error stopping daemon: {e}")


def _run_foreground() -> None:
    """Run the auto-compression loop in the foreground."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write PID file
    _PID_PATH.write_text(str(os.getpid()))

    # Find all SOUL.md files
    souls = _find_all_souls()
    print(f"Chisel watch: monitoring {len(souls)} SOUL.md files")
    for s in souls:
        print(f"  {_agent_name_from_soul(s):>20} → {s}")

    if not souls:
        print("No SOUL.md files found. Nothing to watch.")
        return

    # Initial compressed set
    soul_mtimes: dict[str, float] = {}
    last_compress: dict[str, float] = {}
    cycle = 0

    def _handle_signal(sig, frame):
        print("\nChisel watch daemon shutting down...")
        _PID_PATH.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    print(f"Chisel watch daemon running (PID {os.getpid()})")
    print(f"Mode: Lite (Free) compression, debounce: {DEBOUNCE_SECONDS}s")
    print("---")

    while True:
        now = time.time()
        cycle += 1

        for soul_path in souls:
            if not soul_path.exists():
                continue
            mtime = soul_path.stat().st_mtime
            key = str(soul_path)
            prev_mtime = soul_mtimes.get(key)

            if prev_mtime is not None and mtime != prev_mtime:
                # File modified — check debounce
                last_c = last_compress.get(key, 0)
                if now - last_c > DEBOUNCE_SECONDS:
                    agent = _agent_name_from_soul(soul_path)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {agent} SOUL.md modified — compressing...")
                    result = compress_soul_file(soul_path)
                    if result:
                        print(f"  ✅ {result['before_tokens']} → {result['after_tokens']} tok ({result['savings_pct']:+.1f}%)")
                        if result.get("backup"):
                            print(f"  Backup: {result['backup']}")
                        last_compress[key] = now
                    else:
                        print("  ❌ Compression failed")

            soul_mtimes[key] = mtime

        # Write heartbeat every 60s
        if cycle % 2 == 0:  # Every ~2s = write heartbeat roughly every 60s with 30s poll
            _write_heartbeat(cycle)

        time.sleep(DEBOUNCE_SECONDS)  # Poll every 2 seconds
