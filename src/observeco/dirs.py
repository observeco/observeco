"""ObserveCo data directory — single source of truth for storage paths.

Supports shared-mode via env var OBSERVECO_SHARED_DB or --shared flag.
Also provides framework home directory resolution for Hermes and OpenClaw.
"""

from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

from platformdirs import user_data_dir

_OLD_DIR = Path.home() / ".observeco"
_DIR = Path(user_data_dir("observeco", "observeco"))


def _get_home_override() -> str:
    return os.environ.get("OBSERVECO_HOME", "")


def _get_shared_db_env() -> str:
    return os.environ.get("OBSERVECO_SHARED_DB", "")


def get_data_dir() -> Path:
    """Return the canonical ObserveCo data directory.

    Override via OBSERVECO_HOME env var for isolated test environments.
    Falls back to platformdirs-based default.
    """
    override = _get_home_override()
    if override:
        p = Path(override).expanduser().resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass  # ponytail: fall through to _DIR if we can't create the override path
        if p.exists():
            return p
    _DIR.mkdir(parents=True, exist_ok=True)
    return _DIR


def get_shared_db_path(shared_arg: str | None = None) -> Path | None:
    """Resolve the shared database path.

    Priority: explicit --shared arg > OBSERVECO_SHARED_DB env var > None (local mode).
    Returns None if no shared path is configured or the path is invalid/unwritable.
    Graceful fallback for Layer F first-run safety — if the path's parent is not
    writable, returns None so the system falls back to local mode.
    """
    raw = shared_arg or _get_shared_db_env() or ""
    if raw.strip():
        try:
            p = Path(raw.strip()).expanduser().resolve()
            # Check parent directory writability (don't create the file, just check)
            parent = p.parent
            if not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
            test_file = parent / ".observeco_write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError):
                return None
            return p
        except (OSError, PermissionError, RuntimeError):
            return None
    return None


def is_shared_mode(shared_arg: str | None = None) -> bool:
    """Return True if a shared DB path is configured."""
    return get_shared_db_path(shared_arg) is not None


def get_instance_id() -> str:
    """Return a stable-but-unique instance identifier for shared-mode tracking.

    Format: hostname:dashboard_port (or hostname:cli if no dashboard).
    """
    host = socket.gethostname()
    port = os.environ.get("OBSERVECO_DASHBOARD_PORT", "cli")
    return f"{host}:{port}"


def migrate_old_data() -> None:
    """Migrate data from ~/.observeco to platformdirs if the old path exists."""
    if not _OLD_DIR.exists():
        return
    for item in _OLD_DIR.iterdir():
        dest = _DIR / item.name
        if not dest.exists():
            if item.is_dir():
                import shutil
                shutil.copytree(item, dest)
            else:
                import shutil
                shutil.copy2(item, dest)
    import shutil
    shutil.rmtree(_OLD_DIR)


def _find_pulse_db() -> Path:
    """Find the pulse.db — checks platformdirs first, then old location."""
    p = _DIR / "pulse.db"
    if p.exists():
        return p
    old = _OLD_DIR / "pulse.db"
    if old.exists():
        import shutil
        shutil.copy2(old, p)
        return p
    return p


# ── Framework home directory resolution ───────────────────────────────


def hermes_home() -> Path | None:
    """Return the configured Hermes home directory, or None if not found.

    Resolution order:
    1. OBSERVECO_HERMES_HOME env var
    2. ~/.hermes/ (default)
    3. XDG config (~/.config/hermes/)
    4. `hermes config path` CLI command
    5. Returns None if none found

    Returns None (not a default path) so callers can distinguish
    "Hermes not installed" from "Hermes at default location."
    """
    # 1. Env var override
    override = os.environ.get("OBSERVECO_HERMES_HOME")
    if override:
        p = Path(override).expanduser().resolve()
        if p.exists():
            return p

    # 2. Default ~/.hermes/
    default = Path.home() / ".hermes"
    if default.exists():
        return default

    # 3. XDG config
    xdg = Path.home() / ".config" / "hermes"
    if xdg.exists():
        return xdg

    # 4. CLI command
    try:
        import subprocess
        result = subprocess.run(
            ["hermes", "config", "path"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            p = Path(result.stdout.strip()).expanduser().resolve()
            if p.exists():
                return p
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return None


def openclaw_home() -> Path | None:
    """Return the configured OpenClaw home directory, or None if not found.

    Resolution order:
    1. OBSERVECO_OPENCLAW_HOME env var
    2. ~/.openclaw/ (default)
    3. Returns None if none found
    """
    override = os.environ.get("OBSERVECO_OPENCLAW_HOME")
    if override:
        p = Path(override).expanduser().resolve()
        if p.exists():
            return p

    default = Path.home() / ".openclaw"
    if default.exists():
        return default

    return None


def is_hermes_active() -> bool:
    """Return True if Hermes is actively used on this machine.

    A directory check is not a user check. These scenarios all pass
    a naive directory-exists check but are NOT active Hermes users:
    - Installed Hermes once, never configured an agent
    - Uninstalled Hermes but left ~/.hermes/ directory
    - Primarily runs OpenClaw but has Hermes installed for a side project
    - Has a stale ~/.hermes/ from a previous machine migration

    This function verifies at least one of:
    1. ~/.hermes/profiles/ is non-empty (at least one agent profile exists)
    2. Recent Hermes agent activity in observeco.db (within 30 days)
    3. config.yaml exists and is readable

    Returns True only if Hermes is genuinely in use.
    """
    hh = hermes_home()
    if hh is None:
        return False

    # Check 1: profiles/ directory is non-empty
    profiles_dir = hh / "profiles"
    if profiles_dir.exists():
        try:
            for entry in profiles_dir.iterdir():
                if entry.is_dir() and (entry / "SOUL.md").exists():
                    return True
        except OSError:
            pass

    # Check 2: recent agent activity in observeco.db
    try:
        from observeco.db import Database
        db = Database()
        conn = db._get_conn()
        rows = conn.execute(
            "SELECT 1 FROM agents WHERE framework = 'hermes' "
            "AND last_seen >= datetime('now', '-30 days') LIMIT 1"
        ).fetchall()
        db.close()
        if rows:
            return True
    except Exception:
        pass

    # Check 3: config.yaml exists and is readable
    config_yaml = hh / "config.yaml"
    if config_yaml.exists():
        try:
            config_yaml.read_text()
            return True
        except OSError:
            pass

    return False
