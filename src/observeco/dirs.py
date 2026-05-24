"""ObserveCo data directory — single source of truth for storage paths."""
from __future__ import annotations

from pathlib import Path

from platformdirs import user_data_dir

_OLD_DIR = Path.home() / ".observeco"
_DIR = Path(user_data_dir("observeco", "observeco"))


def get_data_dir() -> Path:
    """Return the canonical ObserveCo data directory (platformdirs-based)."""
    _DIR.mkdir(parents=True, exist_ok=True)
    return _DIR


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
                shutil.copy2(item, dest)
    # Remove old dir after migration
    import shutil
    shutil.rmtree(_OLD_DIR)


def _find_pulse_db() -> Path:
    """Find the pulse.db — checks platformdirs first, then old location."""
    p = _DIR / "pulse.db"
    if p.exists():
        return p
    old = _OLD_DIR / "pulse.db"
    if old.exists():
        # Migrate it
        import shutil
        shutil.copy2(old, p)
        return p
    return p
