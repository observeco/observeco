"""Tests for EnvSnapshot dataclass."""

import time

from observeco.capability.env_snapshot import EnvSnapshot


def test_defaults():
    snap = EnvSnapshot()
    assert snap.runtime is None
    assert snap.runtime_version is None
    assert snap.agent_pids == {}
    assert snap.config_path is None
    assert snap.config_writable is False
    assert snap.config_parsed is None
    assert snap.config_error is None
    assert snap.chosen_port is None
    assert snap.existing_proxies == {}
    assert snap.keychain_available is False
    assert snap.full_disk_access is False
    assert snap.can_install_launchagent is False
    assert snap.store_location_safe is False
    assert snap.framework_emits_usage is False
    assert snap.session_store_path is None
    assert snap.host_fingerprint == ""
    assert snap.probe_errors == {}
    assert snap.anomalies == []
    assert snap.config_summary is None


def test_probed_at_is_recent():
    before = time.time()
    snap = EnvSnapshot()
    after = time.time()
    assert before <= snap.probed_at <= after


def test_explicit_probed_at():
    t = 1234567890.0
    snap = EnvSnapshot(probed_at=t)
    assert snap.probed_at == t


def test_field_mutation():
    snap = EnvSnapshot()
    snap.runtime = "hermes"
    snap.runtime_version = "0.16"
    snap.agent_pids["hermes"] = 12345
    snap.config_path = "/home/user/.hermes/config.yaml"
    snap.config_writable = True
    snap.config_parsed = {"profiles": {}}
    snap.chosen_port = 51877
    snap.existing_proxies["skillclaw"] = 30000
    snap.keychain_available = True
    snap.full_disk_access = False
    snap.store_location_safe = True
    snap.session_store_path = "/home/user/.hermes/sessions"
    snap.framework_emits_usage = True
    snap.host_fingerprint = "abc123"
    snap.probe_errors["ports"] = "Access denied"
    snap.anomalies.append("stale base_url detected")
    snap.config_summary = "Hermes v0.16 with deepseek provider"

    assert snap.runtime == "hermes"
    assert snap.runtime_version == "0.16"
    assert snap.agent_pids["hermes"] == 12345
    assert snap.chosen_port == 51877
    assert snap.existing_proxies["skillclaw"] == 30000
    assert snap.keychain_available is True
    assert snap.store_location_safe is True
    assert snap.framework_emits_usage is True
    assert snap.probe_errors["ports"] == "Access denied"
    assert len(snap.anomalies) == 1
    assert snap.config_summary == "Hermes v0.16 with deepseek provider"


def test_independent_collections():
    """Each EnvSnapshot instance gets its own mutable collections."""
    a = EnvSnapshot()
    b = EnvSnapshot()
    a.agent_pids["hermes"] = 1
    b.existing_proxies["skillclaw"] = 30000
    assert "hermes" not in b.agent_pids
    assert "skillclaw" not in a.existing_proxies


def test_probe_errors_accumulate():
    snap = EnvSnapshot()
    snap.probe_errors["process"] = "Access denied"
    snap.probe_errors["config"] = "File not found"
    assert len(snap.probe_errors) == 2
