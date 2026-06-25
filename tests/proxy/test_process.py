"""Tests for process — proxy process lifecycle.

All real subprocess/socket calls are mocked.
Covers ensure_proxy_alive (4 paths), stop_proxy (3 paths), and _self_check.
"""

from __future__ import annotations

import os
import signal
import subprocess

import pytest

from observeco.proxy import process

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_port_alive(monkeypatch):
    """Control _port_alive return values."""
    values = iter([])

    def set_values(vals):
        nonlocal values
        values = iter(vals)

    def _port_alive(host, port):
        return next(values, False)

    monkeypatch.setattr(process, "_port_alive", _port_alive)
    return type("MockPortAlive", (), {"set_values": staticmethod(set_values)})()


@pytest.fixture
def mock_resolve_db_path(monkeypatch):
    """Control _resolve_db_path return values."""
    monkeypatch.setattr(process, "_resolve_db_path", lambda: "/tmp/observeco.db")
    return None


@pytest.fixture
def mock_popen(monkeypatch):
    """Mock subprocess.Popen."""
    class FakeProc:
        pid = 12345
        returncode = None

        def poll(self):
            return self.returncode

    def _popen(cmd, **kwargs):
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", _popen)
    return None


# ---------------------------------------------------------------------------
# ensure_proxy_alive
# ---------------------------------------------------------------------------


class TestEnsureProxyAlive:
    def test_none_port_returns_false_none(self):
        """None port → (False, None), no subprocess attempted."""
        alive, port = process.ensure_proxy_alive(None)
        assert (alive, port) == (False, None)

    def test_already_running(self, mock_port_alive):
        """Port alive → (True, port), no subprocess spawn."""
        mock_port_alive.set_values([True])  # _port_alive will return True immediately
        alive, port = process.ensure_proxy_alive(9200)
        assert (alive, port) == (True, 9200)

    def test_launch_success(self, mock_port_alive, mock_resolve_db_path, mock_popen):
        """Port dead → subprocess spawned → port becomes alive → (True, port)."""
        mock_port_alive.set_values([False, True])  # first check fails, after spawn succeeds
        alive, port = process.ensure_proxy_alive(9200)
        assert (alive, port) == (True, 9200)

    def test_launch_failure_port_stays_dead(self, mock_port_alive, mock_resolve_db_path, mock_popen):
        """Port dead → subprocess spawned → still dead → (False, None)."""
        mock_port_alive.set_values([False, False])  # both checks fail
        alive, port = process.ensure_proxy_alive(9200)
        assert (alive, port) == (False, None)

    def test_popen_oserror_returns_false(self, mock_port_alive, monkeypatch):
        """Subprocess spawn OSError → (False, None)."""
        mock_port_alive.set_values([False])

        def _broken_popen(*args, **kwargs):
            raise OSError("exec format error")

        monkeypatch.setattr(subprocess, "Popen", _broken_popen)
        alive, port = process.ensure_proxy_alive(9200)
        assert (alive, port) == (False, None)

    def test_launch_failure_polls_rc(self, mock_port_alive, mock_resolve_db_path, monkeypatch):
        """When port stays dead after spawn, poll() is called (exercised by FakeProc)."""
        mock_port_alive.set_values([False, False])

        class FakeProc:
            pid = 999
            returncode = 1

            def poll(self):
                return self.returncode

        monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kwargs: FakeProc())
        alive, port = process.ensure_proxy_alive(9200)
        assert (alive, port) == (False, None)


# ---------------------------------------------------------------------------
# stop_proxy
# ---------------------------------------------------------------------------


class TestStopProxy:
    def test_lsof_returns_pids(self, monkeypatch):
        """lsof finds PIDs → sends SIGTERM + SIGKILL → returns True."""
        killed = []

        def _fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="12345\n67890\n", stderr="")

        def _fake_kill(pid, sig):
            killed.append((pid, sig))

        monkeypatch.setattr(subprocess, "run", _fake_run)
        monkeypatch.setattr(os, "kill", _fake_kill)

        result = process.stop_proxy(9200)
        assert result is True
        # Should have killed both PIDs with SIGTERM then SIGKILL
        assert (12345, signal.SIGTERM) in killed
        assert (67890, signal.SIGTERM) in killed
        assert (12345, signal.SIGKILL) in killed
        assert (67890, signal.SIGKILL) in killed

    def test_lsof_returns_nothing(self, monkeypatch):
        """lsof exits 0 but no PIDs → returns False, no kill attempted."""
        killed = []

        def _fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        def _fake_kill(pid, sig):
            killed.append((pid, sig))

        monkeypatch.setattr(subprocess, "run", _fake_run)
        monkeypatch.setattr(os, "kill", _fake_kill)

        result = process.stop_proxy(65535)
        assert result is False
        assert len(killed) == 0

    def test_lsof_not_found(self, monkeypatch):
        """lsof not installed (FileNotFoundError) → returns False."""
        monkeypatch.setattr(
            subprocess, "run",
            lambda cmd, **kwargs: (_ for _ in ()).throw(FileNotFoundError("lsof not found")),
        )
        result = process.stop_proxy(9200)
        assert result is False

    def test_lsof_timeout(self, monkeypatch):
        """lsof times out → returns False."""
        monkeypatch.setattr(
            subprocess, "run",
            lambda cmd, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd, 5)),
        )
        result = process.stop_proxy(9200)
        assert result is False

    def test_process_lookup_error_skipped(self, monkeypatch):
        """kill raises ProcessLookupError (race: process died) → no crash."""
        def _fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="12345\n", stderr="")

        def _fake_kill(pid, sig):
            raise ProcessLookupError(f"pid {pid} not found")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        monkeypatch.setattr(os, "kill", _fake_kill)

        result = process.stop_proxy(9200)
        assert result is True  # at least one PID was processed


# ---------------------------------------------------------------------------
# _self_check
# ---------------------------------------------------------------------------


class TestSelfCheck:
    def test_self_check_passes(self, monkeypatch):
        """_self_check exercises None port contract and stop_proxy on empty port."""
        # mock lsof to return nothing so stop_proxy(65535) returns False
        monkeypatch.setattr(
            subprocess, "run",
            lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
        )
        process._self_check()  # should not raise
