"""Tests for probe_environment() and individual probe functions.

Uses mocks to avoid touching real processes, files, or ports.
"""

from __future__ import annotations

import io
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from observeco.capability.env_snapshot import EnvSnapshot
from observeco.capability import probe as probe_module
from observeco.capability.probe import (
    _check_fda,
    _check_keychain,
    _check_launchagent,
    _check_store_location,
    _find_ports,
    _find_process,
    _find_session_store,
    _fingerprint,
    _read_config,
    probe_environment,
)

# ---------------------------------------------------------------------------
# Fixtures: Hermes config files
# ---------------------------------------------------------------------------

V014_CONFIG = """\
providers:
  - name: deepseek
    base_url: https://api.deepseek.com/v1
    api_key: sk-abc
  - name: ollama
    base_url: http://localhost:11434/v1
"""

V016_CONFIG = """\
profiles:
  default:
    providers:
      - name: anthropic
        base_url: https://api.anthropic.com/v1
        api_key: sk-ant-def
"""

EMPTY_CONFIG = """\
{}
"""


@pytest.fixture
def v014_config_file(tmp_path):
    f = tmp_path / "config_v014.yaml"
    f.write_text(V014_CONFIG)
    return str(f)


@pytest.fixture
def v016_config_file(tmp_path):
    f = tmp_path / "config_v016.yaml"
    f.write_text(V016_CONFIG)
    return str(f)


# ---------------------------------------------------------------------------
# _find_process
# ---------------------------------------------------------------------------


def test_find_process_hermes(monkeypatch):
    """Detects a running hermes process and its config path."""
    mock_proc = MagicMock()
    mock_proc.info = {"name": "hermes", "cmdline": ["hermes", "start"]}
    mock_proc.pid = 42
    mock_file = MagicMock()
    mock_file.path = "/home/user/.hermes/config.yaml"
    mock_proc.open_files.return_value = [mock_file]

    monkeypatch.setattr(probe_module.psutil, "process_iter", lambda attrs: [mock_proc])
    monkeypatch.setattr(probe_module.os.path, "exists", lambda p: False)

    snap = EnvSnapshot()
    _find_process(snap)

    assert snap.agent_pids.get("hermes") == 42
    assert snap.config_path == "/home/user/.hermes/config.yaml"


def test_find_process_no_agent(monkeypatch):
    """No agent found → config_path falls back to candidates."""
    monkeypatch.setattr(probe_module.psutil, "process_iter", lambda attrs: [])
    monkeypatch.setattr(probe_module.os.path, "exists", lambda p: False)

    snap = EnvSnapshot()
    _find_process(snap)

    assert snap.agent_pids == {}
    assert snap.config_path is None


def test_find_process_candidate_fallback(monkeypatch, v014_config_file):
    """Falls back to candidate paths when process inspection finds nothing."""
    monkeypatch.setattr(probe_module.psutil, "process_iter", lambda attrs: [])

    # Patch _get_hermes_candidates to point at our fixture
    monkeypatch.setattr(probe_module, "_get_hermes_candidates", lambda: (v014_config_file,))
    monkeypatch.setattr(probe_module.os.path, "realpath", lambda p: p)
    monkeypatch.setattr(probe_module.os.path, "expanduser", lambda p: p)
    monkeypatch.setattr(probe_module.os.path, "exists", lambda p: p == v014_config_file)

    snap = EnvSnapshot()
    _find_process(snap)
    assert snap.config_path == v014_config_file


# ---------------------------------------------------------------------------
# _read_config
# ---------------------------------------------------------------------------


def test_read_config_v014(v014_config_file):
    snap = EnvSnapshot(config_path=v014_config_file)
    _read_config(snap)

    assert snap.config_parsed is not None
    assert "providers" in snap.config_parsed
    assert snap.config_error is None


def test_read_config_v016(v016_config_file):
    snap = EnvSnapshot(config_path=v016_config_file)
    _read_config(snap)

    assert snap.config_parsed is not None
    assert "profiles" in snap.config_parsed


def test_read_config_no_path():
    snap = EnvSnapshot()
    _read_config(snap)
    assert snap.config_parsed is None
    assert snap.config_error is None


def test_read_config_invalid_yaml(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(": : : :")
    snap = EnvSnapshot(config_path=str(bad))
    _read_config(snap)
    assert snap.config_error is not None
    assert "corrupt" in snap.config_error


def test_read_config_missing_file():
    snap = EnvSnapshot(config_path="/does/not/exist/config.yaml")
    _read_config(snap)
    assert snap.config_error is not None
    assert "unreadable" in snap.config_error


# ---------------------------------------------------------------------------
# _fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_v016():
    snap = EnvSnapshot(config_parsed={"profiles": {}}, agent_pids={"hermes": 1})
    _fingerprint(snap)
    assert snap.runtime_version == "0.16"
    assert snap.runtime == "hermes"


def test_fingerprint_v014():
    snap = EnvSnapshot(config_parsed={"providers": []}, agent_pids={"openclaw": 2})
    _fingerprint(snap)
    assert snap.runtime_version == "0.14"
    assert snap.runtime == "openclaw"


def test_fingerprint_unknown():
    snap = EnvSnapshot(config_parsed={"something_else": True})
    _fingerprint(snap)
    assert snap.runtime_version == "unknown"
    assert snap.runtime is None


# ---------------------------------------------------------------------------
# _find_ports
# ---------------------------------------------------------------------------


def test_find_ports_binds_ephemeral(monkeypatch):
    """Should pick an ephemeral port > 0."""
    monkeypatch.setattr(probe_module.psutil, "net_connections", lambda kind: [])

    snap = EnvSnapshot()
    _find_ports(snap)

    assert snap.chosen_port is not None
    assert snap.chosen_port > 0


def test_find_ports_known_listener(monkeypatch):
    """Detects known port listeners in existing_proxies."""
    mock_conn = MagicMock()
    mock_conn.status = "LISTEN"
    mock_conn.laddr.port = 30000

    monkeypatch.setattr(probe_module.psutil, "net_connections", lambda kind: [mock_conn])

    snap = EnvSnapshot()
    _find_ports(snap)

    assert snap.existing_proxies.get("skillclaw") == 30000


# ---------------------------------------------------------------------------
# _check_store_location
# ---------------------------------------------------------------------------


def test_store_location_safe(monkeypatch):
    monkeypatch.setattr(probe_module.os.path, "realpath", lambda p: p)
    monkeypatch.setattr(probe_module.os.path, "expanduser", lambda p: p)
    snap = EnvSnapshot()
    _check_store_location(snap)
    # ~/.observeco is not under any sync root by default
    assert isinstance(snap.store_location_safe, bool)


# ---------------------------------------------------------------------------
# _find_session_store
# ---------------------------------------------------------------------------


def test_find_session_store_found(tmp_path, monkeypatch):
    sessions = tmp_path / "sessions"
    sessions.mkdir()

    monkeypatch.setattr("observeco.dirs.hermes_home", lambda: tmp_path)
    monkeypatch.setattr("observeco.dirs.openclaw_home", lambda: None)
    monkeypatch.setattr(probe_module.os.path, "isdir", lambda p: p == str(sessions))
    monkeypatch.setattr(probe_module.os, "access", lambda p, mode: True)

    snap = EnvSnapshot()
    _find_session_store(snap)

    assert snap.session_store_path == str(sessions)
    assert snap.framework_emits_usage is True


def test_find_session_store_not_found(monkeypatch):
    monkeypatch.setattr("observeco.dirs.hermes_home", lambda: None)
    monkeypatch.setattr("observeco.dirs.openclaw_home", lambda: None)
    monkeypatch.setattr(probe_module.os.path, "isdir", lambda p: False)

    snap = EnvSnapshot()
    _find_session_store(snap)

    assert snap.session_store_path is None
    assert snap.framework_emits_usage is False


# ---------------------------------------------------------------------------
# probe_environment() orchestration
# ---------------------------------------------------------------------------


def test_probe_environment_returns_snapshot(monkeypatch):
    """Full probe call returns an EnvSnapshot with probed_at set."""
    monkeypatch.setattr(probe_module.psutil, "process_iter", lambda attrs: [])
    monkeypatch.setattr(probe_module.psutil, "net_connections", lambda kind: [])
    monkeypatch.setattr(probe_module.os.path, "exists", lambda p: False)

    snap = probe_environment()

    assert isinstance(snap, EnvSnapshot)
    assert snap.probed_at > 0


def test_probe_environment_failure_isolation(monkeypatch):
    """A single probe failure doesn't abort the whole pass."""

    def bad_process(snap):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(probe_module, "_find_process", bad_process)
    monkeypatch.setattr(probe_module.psutil, "net_connections", lambda kind: [])
    monkeypatch.setattr(probe_module.os.path, "exists", lambda p: False)

    snap = probe_environment()

    assert "process" in snap.probe_errors
    assert "simulated failure" in snap.probe_errors["process"]
    # Other probes should still have run (snapshot exists)
    assert isinstance(snap, EnvSnapshot)
