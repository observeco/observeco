"""Process supervision for ObserveCo — launchd (macOS), systemd (Linux), PID-file fallback.

Dispatch table:
    macOS   → ~/Library/LaunchAgents/com.observeco.daemon.plist + launchctl
    Linux   → ~/.config/systemd/user/observeco.service + systemctl --user
    other   → PID-file + restart-counter (Docker, CI, Windows)

ponytail: templates are inline strings — no template engine needed.
Upgrade: if templates grow conditionals, move to Jinja2 (already a dep).

ponytail: PID-file fallback is single-process, best-effort. If multi-process
supervision is needed (e.g., supervisord-lite), extract a Supervisor class.

Self-check: python -m observeco.process_supervision
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .dirs import get_data_dir

logger = logging.getLogger(__name__)

LAUNCHD_LABEL = "com.observeco.daemon"
SYSTEMD_UNIT = "observeco"
RESTART_MAX = 3
RESTART_WINDOW = 300  # 5 minutes — spec §17.1 §9.2
UNSUPPORTED_MSG = "Platform not supported for service installation — use PID-file fallback"


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform() -> str:
    """Returns 'macos', 'linux', or 'other'."""
    s = platform.system()
    if s == "Darwin":
        return "macos"
    if s == "Linux":
        return "linux"
    return "other"


# ---------------------------------------------------------------------------
# Template rendering (inline strings, not files)
# ---------------------------------------------------------------------------

def render_plist(python_path: str, log_dir: Path) -> str:
    """Render launchd plist content for macOS."""
    # ponytail: python_path is the current interpreter — ties the service to this venv.
    # Upgrade: accept a --python-path flag for system-wide installs.
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>observeco</string>
        <string>watch</string>
        <string>foreground</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir}/observeco.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/observeco.log</string>
</dict>
</plist>
"""


def render_systemd_unit(python_path: str) -> str:
    """Render systemd user unit content for Linux."""
    return f"""[Unit]
Description=ObserveCo watch daemon
After=network.target

[Service]
ExecStart={python_path} -m observeco watch foreground
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""


# ---------------------------------------------------------------------------
# Path helpers (functions so tests can monkeypatch)
# ---------------------------------------------------------------------------

def _plist_path() -> Path:
    """~/Library/LaunchAgents/com.observeco.daemon.plist"""
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def _systemd_unit_path() -> Path:
    """~/.config/systemd/user/observeco.service"""
    return Path.home() / ".config" / "systemd" / "user" / f"{SYSTEMD_UNIT}.service"


def _template_path() -> Optional[Path]:
    """Return platform-appropriate template install path, or None on unsupported."""
    plat = detect_platform()
    if plat == "macos":
        return _plist_path()
    if plat == "linux":
        return _systemd_unit_path()
    return None


def _log_dir() -> Path:
    d = get_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Install / Uninstall
# ---------------------------------------------------------------------------

def install() -> tuple[bool, str]:
    """Install and start the ObserveCo service.

    Returns (success, message).
    Failure paths from spec §17.1:
    - Already installed  → (True, "Service already installed")
    - Unsupported platform → (True, UNSUPPORTED_MSG)
    - launchctl/systemctl fails → (False, error + fix instruction)
    """
    plat = detect_platform()

    if plat == "other":
        return True, UNSUPPORTED_MSG

    tpl = _template_path()
    if tpl is None:  # shouldn't happen given plat check above, but defensive
        return True, UNSUPPORTED_MSG

    if tpl.exists():
        return True, "Service already installed"

    tpl.parent.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable

    if plat == "macos":
        tpl.write_text(render_plist(python_path, _log_dir()))
        ok, msg = _launchd_load(tpl)
    else:
        tpl.write_text(render_systemd_unit(python_path))
        ok, msg = _systemd_enable()

    if not ok:
        # Clean up orphaned template on failure so re-run works
        tpl.unlink(missing_ok=True)

    return ok, msg


def uninstall() -> tuple[bool, str]:
    """Stop and remove the ObserveCo service.

    Stops before removing per spec §17.1.
    Returns (success, message).
    Failure paths:
    - Not installed → (True, "Service not installed")
    - Unsupported → (True, UNSUPPORTED_MSG)
    - launchctl/systemctl stop fails → (False, error message)
    """
    plat = detect_platform()

    if plat == "other":
        return True, UNSUPPORTED_MSG

    tpl = _template_path()
    if tpl is None:
        return True, UNSUPPORTED_MSG

    if not tpl.exists():
        return True, "Service not installed"

    # Stop first, then remove
    if plat == "macos":
        ok, msg = _launchd_unload(tpl)
    else:
        ok, msg = _systemd_disable()

    if not ok:
        return False, msg

    tpl.unlink(missing_ok=True)
    return True, "Service uninstalled"


# ---------------------------------------------------------------------------
# launchd helpers
# ---------------------------------------------------------------------------

def _launchd_load(plist: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["launchctl", "load", str(plist)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout).strip()
        return False, (
            f"launchctl load failed: {err}\n"
            f"Fix: check permissions on {plist} or run 'launchctl list {LAUNCHD_LABEL}'"
        )
    return True, f"Service installed and started (launchd label: {LAUNCHD_LABEL})"


def _launchd_unload(plist: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["launchctl", "unload", str(plist)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout).strip()
        return False, f"launchctl unload failed: {err}"
    return True, "Service stopped"


def _launchd_status() -> dict:
    result = subprocess.run(
        ["launchctl", "list", LAUNCHD_LABEL],
        capture_output=True, text=True,
    )
    installed = _plist_path().exists()
    running = result.returncode == 0
    return {
        "platform": "macos",
        "installed": installed,
        "running": running,
        "detail": (result.stdout if running else result.stderr).strip(),
    }


# ---------------------------------------------------------------------------
# systemd helpers
# ---------------------------------------------------------------------------

def _systemd_enable() -> tuple[bool, str]:
    r1 = subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        capture_output=True, text=True,
    )
    if r1.returncode != 0:
        err = r1.stderr.strip()
        return False, (
            f"systemctl daemon-reload failed: {err}\n"
            f"Fix: ensure systemd user session is available (loginctl enable-linger $USER)"
        )
    r2 = subprocess.run(
        ["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT],
        capture_output=True, text=True,
    )
    if r2.returncode != 0:
        err = r2.stderr.strip()
        return False, (
            f"systemctl enable failed: {err}\n"
            f"Fix: check unit file at {_systemd_unit_path()}"
        )
    return True, f"Service installed and started (systemd unit: {SYSTEMD_UNIT})"


def _systemd_disable() -> tuple[bool, str]:
    # stop may fail if already stopped — ignore its exit code
    subprocess.run(
        ["systemctl", "--user", "stop", SYSTEMD_UNIT],
        capture_output=True, text=True,
    )
    r = subprocess.run(
        ["systemctl", "--user", "disable", SYSTEMD_UNIT],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        err = r.stderr.strip()
        return False, f"systemctl disable failed: {err}"
    return True, "Service stopped and disabled"


def _systemd_status() -> dict:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", SYSTEMD_UNIT],
        capture_output=True, text=True,
    )
    installed = _systemd_unit_path().exists()
    running = result.stdout.strip() == "active"
    return {
        "platform": "linux",
        "installed": installed,
        "running": running,
        "detail": result.stdout.strip(),
    }


# ---------------------------------------------------------------------------
# Unified status
# ---------------------------------------------------------------------------

def get_status() -> dict:
    """Return service status dict appropriate to the current platform."""
    plat = detect_platform()
    if plat == "macos":
        return _launchd_status()
    if plat == "linux":
        return _systemd_status()
    return _pid_fallback_status()


# ---------------------------------------------------------------------------
# PID-file fallback (Docker, CI/CD, Windows, other platforms)
# ---------------------------------------------------------------------------

def _pid_file() -> Path:
    return get_data_dir() / ".supervisor.pid"


def _counter_file() -> Path:
    return get_data_dir() / ".supervisor.restarts.json"


def _pid_fallback_status() -> dict:
    """Check daemon liveness via PID file."""
    pf = _pid_file()
    if not pf.exists():
        return {"platform": "other", "installed": False, "running": False, "detail": "No PID file"}
    try:
        pid = int(pf.read_text().strip())
        os.kill(pid, 0)  # signal 0 = existence probe, raises if process is gone
        return {"platform": "other", "installed": True, "running": True, "pid": pid}
    except ProcessLookupError:
        return {"platform": "other", "installed": True, "running": False, "detail": "Process not found"}
    except PermissionError:
        # Process exists but we can't signal it — treat as running
        return {"platform": "other", "installed": True, "running": True, "detail": "Permission denied (assuming alive)"}
    except (ValueError, OSError):
        return {"platform": "other", "installed": False, "running": False, "detail": "Invalid PID file"}


def _load_restart_counter() -> list[float]:
    cf = _counter_file()
    if not cf.exists():
        return []
    try:
        return json.loads(cf.read_text()).get("restarts", [])
    except (json.JSONDecodeError, OSError):
        return []


def _save_restart_counter(timestamps: list[float]) -> None:
    _counter_file().write_text(json.dumps({"restarts": timestamps}))


def _can_restart() -> bool:
    """Return True if fewer than RESTART_MAX restarts occurred in the last RESTART_WINDOW seconds."""
    now = time.time()
    recent = [t for t in _load_restart_counter() if (now - t) < RESTART_WINDOW]
    return len(recent) < RESTART_MAX


def _record_restart() -> None:
    now = time.time()
    recent = [t for t in _load_restart_counter() if (now - t) < RESTART_WINDOW]
    recent.append(now)
    _save_restart_counter(recent)


def pid_fallback_maybe_restart() -> tuple[bool, str]:
    """Check if the daemon is dead and restart it within crash-loop limits.

    Called by: dashboard startup, watch daemon monitor.
    Returns (restarted, message).

    ponytail: Popen with start_new_session=True detaches the child immediately.
    The child's PID is written before any liveness checks — there is a brief
    window where the PID file exists but the process hasn't fully started.
    Upgrade: use a socketpair handshake if <1s startup confirmation is required.
    """
    status = _pid_fallback_status()
    if status["running"]:
        return False, "Daemon already running"

    if not _can_restart():
        return False, (
            f"Restart limit reached (max {RESTART_MAX} in {RESTART_WINDOW}s) — "
            "manual restart required: observeco watch start"
        )

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "observeco", "watch", "foreground"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        _pid_file().write_text(str(proc.pid))
        _record_restart()
        return True, f"Daemon restarted (PID {proc.pid})"
    except Exception as e:
        return False, f"Failed to restart daemon: {e}"


# ---------------------------------------------------------------------------
# Self-check (runnable via: python -m observeco.process_supervision)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Platform: {detect_platform()}")
    status = get_status()
    print(f"Installed: {status.get('installed')}")
    print(f"Running:   {status.get('running')}")
    if status.get("detail"):
        print(f"Detail:    {status['detail']}")
    if status.get("pid"):
        print(f"PID:       {status['pid']}")
    can = _can_restart()
    print(f"Can restart (PID fallback): {can}")
