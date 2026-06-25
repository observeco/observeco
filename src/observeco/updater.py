"""Update system for ObserveCo.

Checks GitHub releases for updates and provides one-click upgrade.
Also handles offline fallback and caching.

GS-019: Data & Observability Continuity
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from .dirs import get_data_dir

logger = logging.getLogger(__name__)

# Update constants
GITHUB_REPO = "observeco/observeco"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_CHECK_TIMEOUT = 5.0  # seconds
UPDATE_CACHE_FILE = get_data_dir() / ".update_cache.json"
UPDATE_CACHE_MAX_AGE = 3600  # 1 hour


@dataclass
class UpdateInfo:
    """Information about an available update."""
    current: str
    latest: str
    download_url: str
    release_notes: Optional[str] = None
    published_at: Optional[str] = None
    is_update_available: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "current": self.current,
            "latest": self.latest,
            "download_url": self.download_url,
            "release_notes": self.release_notes,
            "published_at": self.published_at,
            "is_update_available": self.is_update_available,
        }


class UpdateChecker:
    """Checks for updates from GitHub releases."""

    def __init__(self):
        self._cache: Optional[dict] = None

    def check_for_updates(self) -> UpdateInfo:
        """Check GitHub for latest release."""
        # Try to get from cache first
        cached = self._get_cached_update()
        if cached:
            return cached

        # Fetch from GitHub
        try:
            response = httpx.get(
                GITHUB_API_URL,
                timeout=UPDATE_CHECK_TIMEOUT,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            response.raise_for_status()

            data = response.json()
            latest = data.get("tag_name", "").lstrip("v")
            current = self._get_current_version()

            if not latest or not current:
                return UpdateInfo(
                    current=current or "unknown",
                    latest="unknown",
                    download_url="",
                    is_update_available=False,
                )

            is_available = self._compare_versions(latest, current) > 0

            update_info = UpdateInfo(
                current=current,
                latest=latest,
                download_url=data.get("html_url", ""),
                release_notes=data.get("body", ""),
                published_at=data.get("published_at"),
                is_update_available=is_available,
            )

            # Cache the result
            self._cache_update(update_info)

            return update_info

        except httpx.TimeoutException:
            logger.warning("Update check timed out — network unavailable")
            return self._get_offline_fallback()
        except httpx.RequestError as e:
            logger.warning(f"Update check failed: {e}")
            return self._get_offline_fallback()
        except Exception as e:
            logger.error(f"Unexpected error checking for updates: {e}")
            return UpdateInfo(
                current=self._get_current_version() or "unknown",
                latest="unknown",
                download_url="",
                is_update_available=False,
            )

    def apply_update(self) -> dict:
        """Apply the update by running pip install."""
        try:
            # Get the current version before update
            current = self._get_current_version()

            # Run pip install
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", f"git+https://github.com/{GITHUB_REPO}.git"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if result.returncode == 0:
                # Get new version
                new_version = self._get_current_version()
                return {
                    "success": True,
                    "message": f"Updated from {current} to {new_version}",
                    "previous_version": current,
                    "new_version": new_version,
                }
            else:
                return {
                    "success": False,
                    "message": f"Update failed: {result.stderr}",
                    "error": result.stderr,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Update timed out after 5 minutes",
                "error": "timeout",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Update failed: {e}",
                "error": str(e),
            }

    def _get_current_version(self) -> Optional[str]:
        """Get the current installed version."""
        try:
            import observeco
            return getattr(observeco, "__version__", None)
        except ImportError:
            return None

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings.

        Returns:
            1 if v1 > v2
            -1 if v1 < v2
            0 if v1 == v2
        """
        try:
            from packaging.version import Version
            ver1 = Version(v1)
            ver2 = Version(v2)
            if ver1 > ver2:
                return 1
            elif ver1 < ver2:
                return -1
            else:
                return 0
        except Exception:
            # Fallback: simple string comparison
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
            else:
                return 0

    def _get_cached_update(self) -> Optional[UpdateInfo]:
        """Get cached update info if still valid."""
        if not UPDATE_CACHE_FILE.exists():
            return None

        try:
            data = json.loads(UPDATE_CACHE_FILE.read_text())
            cached_at = data.get("cached_at", 0)

            # Check if cache is still valid
            if (time.time() - cached_at) > UPDATE_CACHE_MAX_AGE:
                return None

            return UpdateInfo(
                current=data.get("current", ""),
                latest=data.get("latest", ""),
                download_url=data.get("download_url", ""),
                release_notes=data.get("release_notes"),
                published_at=data.get("published_at"),
                is_update_available=data.get("is_update_available", False),
            )
        except Exception:
            return None

    def _cache_update(self, update_info: UpdateInfo) -> None:
        """Cache update info."""
        try:
            data = {
                "current": update_info.current,
                "latest": update_info.latest,
                "download_url": update_info.download_url,
                "release_notes": update_info.release_notes,
                "published_at": update_info.published_at,
                "is_update_available": update_info.is_update_available,
                "cached_at": time.time(),
            }
            UPDATE_CACHE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to cache update info: {e}")

    def _get_offline_fallback(self) -> UpdateInfo:
        """Return offline fallback when network is unavailable."""
        # Try to use cached info
        cached = self._get_cached_update()
        if cached:
            cached.release_notes = "(cached — check again later)"
            return cached

        return UpdateInfo(
            current=self._get_current_version() or "unknown",
            latest="unknown",
            download_url="",
            release_notes="Update check failed — no internet connection",
            is_update_available=False,
        )


# --- Singleton instance ---
_update_checker: Optional[UpdateChecker] = None


def get_update_checker() -> UpdateChecker:
    """Get the singleton update checker instance."""
    global _update_checker
    if _update_checker is None:
        _update_checker = UpdateChecker()
    return _update_checker


def check_for_updates() -> UpdateInfo:
    """Check for updates (convenience function)."""
    return get_update_checker().check_for_updates()


def apply_update() -> dict:
    """Apply update (convenience function)."""
    return get_update_checker().apply_update()
