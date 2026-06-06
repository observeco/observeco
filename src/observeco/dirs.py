"""ObserveCo data directory — single source of truth for storage paths.

Supports shared-mode via env var OBSERVECO_SHARED_DB or --shared flag.
"""
from __future__ import annotations

import os
import socket
from pathlib import Path

from platformdirs import user_data_dir

_OLD_DIR = Path.home() / ".observeco"
_DIR = Path(user_data_dir("observeco", "observeco"))
_HOME_OVERRIDE = os.environ.get("OBSERVECO_HOME", "")

# Env var override for shared database path
_SHARED_DB_ENV = os.environ.get("OBSERVECO_SHARED_DB", "")


def get_data_dir() -> Path:
    """Return the canonical ObserveCo data directory.
    
    Override via OBSERVECO_HOME env var for isolated test environments.
    Falls back to platformdirs-based default.
    """
    if _HOME_OVERRIDE:
        p = Path(_HOME_OVERRIDE).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
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
    raw = shared_arg or _SHARED_DB_ENV or ""
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
