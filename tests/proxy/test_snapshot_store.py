"""Tests for snapshot_store — SQLite-backed proxy config snapshots.

Uses real SQLite on a temp file (monkeypatches _get_db_path).
sha256_file tests are file-based, no DB needed.
"""

from __future__ import annotations

import hashlib
import sqlite3

import pytest

from observeco.proxy import snapshot_store

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Temp file to serve as the SQLite database."""
    return tmp_path / "observeco.db"


@pytest.fixture
def patch_db(db_path, monkeypatch):
    """Redirect _get_db_path to a temp file so DB ops are real but isolated."""
    monkeypatch.setattr(snapshot_store, "_get_db_path", lambda: db_path)
    return db_path


def _snapshot_row(conn, config_path: str, provider: str):
    """Helper: read a snapshot row directly from conn."""
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT * FROM proxy_config_snapshots WHERE config_path=? AND provider=?",
        (config_path, provider),
    ).fetchone()


# ---------------------------------------------------------------------------
# ensure_table
# ---------------------------------------------------------------------------


class TestEnsureTable:
    def test_creates_table(self, patch_db, monkeypatch):
        """Table doesn't exist → ensure_table creates it."""
        snapshot_store.ensure_table()
        conn = sqlite3.connect(str(patch_db))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='proxy_config_snapshots'"
            ).fetchall()
            assert len(rows) == 1
            assert rows[0]["name"] == "proxy_config_snapshots"
        finally:
            conn.close()

    def test_idempotent(self, patch_db):
        """Calling ensure_table twice is safe."""
        snapshot_store.ensure_table()
        snapshot_store.ensure_table()  # should not raise
        conn = sqlite3.connect(str(patch_db))
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='proxy_config_snapshots'"
            ).fetchall()
            assert len(rows) == 1
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# snapshot_provider / get_snapshot
# ---------------------------------------------------------------------------


class TestSnapshotProviderAndGet:
    def test_snapshot_and_retrieve(self, patch_db):
        """Insert a snapshot, then read it back with get_snapshot."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider(
            config_path="/path/to/config.yaml",
            runtime="hermes",
            provider="deepseek",
            original_base_url="https://api.deepseek.com/v1",
            original_blob="api_key: sk-abc\n",
        )
        row = snapshot_store.get_snapshot("/path/to/config.yaml", "deepseek")
        assert row is not None
        assert row["provider"] == "deepseek"
        assert row["original_base_url"] == "https://api.deepseek.com/v1"
        assert row["active"] == 1
        assert isinstance(row["created_at"], float)

    def test_insert_or_ignore(self, patch_db):
        """Second insert for same (config_path, provider) is ignored."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider(
            config_path="/cfg", runtime="hermes", provider="ollama",
            original_base_url="http://localhost:11434/v1",
            original_blob="url: foo\n",
        )
        snapshot_store.snapshot_provider(
            config_path="/cfg", runtime="hermes", provider="ollama",
            original_base_url="http://other:8080/v1",  # different URL, ignored
            original_blob="url: bar\n",
        )
        row = snapshot_store.get_snapshot("/cfg", "ollama")
        assert row is not None
        assert row["original_base_url"] == "http://localhost:11434/v1"

    def test_get_snapshot_returns_none_for_missing(self, patch_db):
        """No snapshot → returns None."""
        snapshot_store.ensure_table()
        assert snapshot_store.get_snapshot("/nope", "nobody") is None

    def test_get_snapshot_returns_none_for_inactive(self, patch_db):
        """Deactivated snapshot is not returned by get_snapshot."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider("/x", "hermes", "p1", "http://a", "blob")
        snapshot_store.deactivate_snapshot("/x", "p1")
        assert snapshot_store.get_snapshot("/x", "p1") is None


# ---------------------------------------------------------------------------
# set_last_write_hash
# ---------------------------------------------------------------------------


class TestSetLastWriteHash:
    def test_updates_hash(self, patch_db):
        """set_last_write_hash updates our_last_write_hash on the row."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider("/cfg", "hermes", "p1", "http://a", "blob")
        snapshot_store.set_last_write_hash("/cfg", "p1", "abc123")
        row = snapshot_store.get_snapshot("/cfg", "p1")
        assert row is not None
        assert row["our_last_write_hash"] == "abc123"


# ---------------------------------------------------------------------------
# deactivate_snapshot
# ---------------------------------------------------------------------------


class TestDeactivateSnapshot:
    def test_deactivates(self, patch_db):
        """Deactivated row has active=0."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider("/cfg", "hermes", "p1", "http://a", "blob")
        snapshot_store.deactivate_snapshot("/cfg", "p1")
        conn = sqlite3.connect(str(patch_db))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT active FROM proxy_config_snapshots WHERE config_path=? AND provider=?",
                ("/cfg", "p1"),
            ).fetchone()
            assert row is not None
            assert row["active"] == 0
        finally:
            conn.close()

    def test_deactivate_missing_is_noop(self, patch_db):
        """Deactivating a non-existent snapshot does not raise."""
        snapshot_store.ensure_table()
        snapshot_store.deactivate_snapshot("/nope", "missing")  # should not raise


# ---------------------------------------------------------------------------
# active_providers
# ---------------------------------------------------------------------------


class TestActiveProviders:
    def test_returns_only_active(self, patch_db):
        """active_providers returns only rows with active=1."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider("/cfg", "hermes", "p1", "http://a", "blob1")
        snapshot_store.snapshot_provider("/cfg", "hermes", "p2", "http://b", "blob2")
        snapshot_store.snapshot_provider("/other_cfg", "hermes", "p3", "http://c", "blob3")
        snapshot_store.deactivate_snapshot("/cfg", "p1")

        rows = snapshot_store.active_providers("/cfg")
        assert len(rows) == 1
        assert rows[0]["provider"] == "p2"

    def test_empty_when_none_active(self, patch_db):
        """No active snapshots → empty list."""
        snapshot_store.ensure_table()
        rows = snapshot_store.active_providers("/empty")
        assert rows == []


# ---------------------------------------------------------------------------
# sha256_file
# ---------------------------------------------------------------------------


class TestSha256File:
    def test_computes_sha256(self, tmp_path):
        """sha256_file returns the correct hex digest."""
        f = tmp_path / "test.txt"
        content = b"hello world"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert snapshot_store.sha256_file(str(f)) == expected

    def test_handles_empty_file(self, tmp_path):
        """Empty file → sha256 of empty bytes."""
        f = tmp_path / "empty.txt"
        f.write_text("")
        expected = hashlib.sha256(b"").hexdigest()
        assert snapshot_store.sha256_file(str(f)) == expected

    def test_raises_on_missing_file(self, tmp_path):
        """Missing file → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            snapshot_store.sha256_file(str(tmp_path / "does_not_exist"))
