"""Tests for config_io — atomic config writes with clobber guard.

Uses real tmp_path YAML files and HermesSchemaV14 adapter.
Monkeypatches set_last_write_hash to avoid DB dependency.
"""

from __future__ import annotations

import os

import pytest

from observeco.capability.adapters.hermes import HermesSchemaV14
from observeco.proxy import config_io
from observeco.proxy.snapshot_store import sha256_file

CONFIG_V14 = """\
providers:
  - name: deepseek
    base_url: https://api.deepseek.com/v1
    api_key: sk-abc123
  - name: ollama
    base_url: http://localhost:11434/v1
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config_path(tmp_path):
    f = tmp_path / "config.yaml"
    f.write_text(CONFIG_V14)
    return str(f)


@pytest.fixture
def adapter():
    return HermesSchemaV14


@pytest.fixture
def mock_db(monkeypatch):
    """Avoid real DB calls from set_last_write_hash."""
    monkeypatch.setattr(config_io, "set_last_write_hash", lambda path, provider, fh: None)


# ---------------------------------------------------------------------------
# atomic_write_base_url
# ---------------------------------------------------------------------------


class TestAtomicWriteBaseURL:
    def test_writes_base_url(self, config_path, adapter, mock_db):
        """Writes a local proxy URL into the config file."""
        config_io.atomic_write_base_url(config_path, "deepseek", "http://127.0.0.1:9200/v1", adapter)
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:9200/v1"

    def test_preserves_unrelated_fields(self, config_path, adapter, mock_db):
        """Other providers and api_key are unchanged."""
        config_io.atomic_write_base_url(config_path, "deepseek", "http://127.0.0.1:9200/v1", adapter)
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "ollama") == "http://localhost:11434/v1"
        # api_key should still be there
        providers = doc.get("providers", [])
        ds = next(p for p in providers if p["name"] == "deepseek")
        assert ds["api_key"] == "sk-abc123"

    def test_clobber_guard_hash_written(self, config_path, adapter, monkeypatch):
        """sha256 of written file is recorded via set_last_write_hash."""
        written = []

        def _fake_set(path, provider, file_hash):
            written.append((path, provider, file_hash))

        monkeypatch.setattr(config_io, "set_last_write_hash", _fake_set)
        config_io.atomic_write_base_url(config_path, "deepseek", "http://127.0.0.1:9200/v1", adapter)

        assert len(written) == 1
        _, provider, file_hash = written[0]
        assert provider == "deepseek"
        # Verify the hash is the actual sha256 of the final file
        expected = sha256_file(config_path)
        assert file_hash == expected

    def test_atomic_rename_no_partial_write(self, config_path, adapter, mock_db, monkeypatch):
        """If dump succeeds but rename fails, the original file is unmodified."""
        original_content = os.path.getsize(config_path)

        def _broken_rename(*args, **kwargs):
            raise OSError("rename failed")

        monkeypatch.setattr(os, "replace", _broken_rename)

        with pytest.raises(OSError, match="rename failed"):
            config_io.atomic_write_base_url(config_path, "deepseek", "http://127.0.0.1:9200/v1", adapter)

        # ponytail: this only tests the atomicity of rename — full crash-safety
        # would need to survive a power loss at every point in the write path.
        # The temp file cleans up on exception but the OSError path is tested.
        assert os.path.getsize(config_path) == original_content
        # Temp file should be cleaned up
        assert not os.path.exists(f"{config_path}.observeco.tmp")

    def test_fsync_called(self, config_path, adapter, mock_db, monkeypatch):
        """os.fsync is called on the temp file descriptor."""
        fsynced = []
        original_fsync = os.fsync

        def _tracking_fsync(fd):
            fsynced.append(True)
            return original_fsync(fd)

        monkeypatch.setattr(os, "fsync", _tracking_fsync)
        config_io.atomic_write_base_url(config_path, "deepseek", "http://127.0.0.1:9200/v1", adapter)
        assert len(fsynced) >= 1, "fsync was not called"
        # Verify the write still happened
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:9200/v1"

    def test_raises_on_truncated_key(self, config_path, adapter, mock_db):
        """Config containing '...' in any value raises ValueError."""
        config_path2 = config_path.rsplit("/", 1)[0] + "/bad_config.yaml"
        with open(config_path2, "w") as f:
            f.write("""\
providers:
  - name: anthropic
    base_url: https://api.anthropic.com/v1
    api_key: sk-ant-...abc123def
""")
        # base_url is set clean — but api_key is truncated; validator catches it
        with pytest.raises(ValueError, match="Truncated"):
            config_io.atomic_write_base_url(config_path2, "anthropic", "http://127.0.0.1:9200/v1", adapter)

    def test_cleanup_temp_file_on_failure(self, config_path, adapter, mock_db, monkeypatch):
        """Temp file is cleaned up if the write fails midway."""
        def _broken_dump(*args, **kwargs):
            raise ValueError("dump failed")

        monkeypatch.setattr(adapter, "dump", _broken_dump)

        with pytest.raises(ValueError, match="dump failed"):
            config_io.atomic_write_base_url(config_path, "deepseek", "http://127.0.0.1:9200/v1", adapter)

        assert not os.path.exists(f"{config_path}.observeco.tmp")
