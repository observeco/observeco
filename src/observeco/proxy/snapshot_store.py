"""proxy_config_snapshots table — ObserveCo-owned revert state.

Revert and routing data live here, never in the user's config.
This is the source of truth for the multi-upstream routing table.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _get_db_path() -> Path:
    from observeco.db import DB_PATH
    return DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table() -> None:
    """Create proxy_config_snapshots and proxy_reconciler_state if missing."""
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS proxy_config_snapshots (
                id                  INTEGER PRIMARY KEY,
                config_path         TEXT NOT NULL,
                runtime             TEXT NOT NULL,
                provider            TEXT NOT NULL,
                original_base_url   TEXT NOT NULL,
                original_blob       TEXT NOT NULL,
                our_last_write_hash TEXT,
                active              INTEGER NOT NULL DEFAULT 1,
                created_at          REAL NOT NULL,
                UNIQUE(config_path, provider)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS proxy_reconciler_state (
                id             INTEGER PRIMARY KEY CHECK (id = 1),
                cooldown_until REAL NOT NULL DEFAULT 0.0
            )
        """)
        conn.commit()
    finally:
        conn.close()


def snapshot_provider(
    config_path: str,
    runtime: str,
    provider: str,
    original_base_url: str,
    original_blob: str,
) -> None:
    """Capture the original state for a provider (insert or ignore if already present)."""
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO proxy_config_snapshots
                (config_path, runtime, provider, original_base_url, original_blob, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (config_path, runtime, provider, original_base_url, original_blob, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def get_snapshot(config_path: str, provider: str) -> Optional[sqlite3.Row]:
    """Return the snapshot row for a provider, or None."""
    conn = _connect()
    try:
        return conn.execute(
            "SELECT * FROM proxy_config_snapshots WHERE config_path=? AND provider=? AND active=1",
            (config_path, provider),
        ).fetchone()
    finally:
        conn.close()


def set_last_write_hash(config_path: str, provider: str, file_hash: str) -> None:
    """Record the sha256 of the file after our last write (clobber guard)."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE proxy_config_snapshots SET our_last_write_hash=? WHERE config_path=? AND provider=?",
            (file_hash, config_path, provider),
        )
        conn.commit()
    finally:
        conn.close()


def deactivate_snapshot(config_path: str, provider: str) -> None:
    """Mark a snapshot inactive (provider reverted, tracking off)."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE proxy_config_snapshots SET active=0 WHERE config_path=? AND provider=?",
            (config_path, provider),
        )
        conn.commit()
    finally:
        conn.close()


def active_providers(config_path: str) -> list[sqlite3.Row]:
    """Return all active snapshots for a config path."""
    conn = _connect()
    try:
        return conn.execute(
            "SELECT * FROM proxy_config_snapshots WHERE config_path=? AND active=1",
            (config_path,),
        ).fetchall()
    finally:
        conn.close()


def sha256_file(path: str) -> str:
    """SHA-256 of a file's contents (used for clobber-guard hash)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Circuit-breaker state persistence
# ---------------------------------------------------------------------------


def get_reconciler_cooldown() -> float:
    """Return persisted cooldown_until, or 0.0 if no row exists."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT cooldown_until FROM proxy_reconciler_state WHERE id=1"
        ).fetchone()
        return float(row["cooldown_until"]) if row else 0.0
    finally:
        conn.close()


def set_reconciler_cooldown(cooldown_until: float) -> None:
    """Upsert the cooldown_until value."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO proxy_reconciler_state (id, cooldown_until) VALUES (1, ?)",
            (cooldown_until,),
        )
        conn.commit()
    finally:
        conn.close()
