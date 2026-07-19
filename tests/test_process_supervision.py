"""Tests for process_supervision.py — P0-7: Process Supervision.

Covers:
- Template rendering (plist and systemd unit content)
- install/uninstall state machine (already installed, not installed, unsupported platform)
- Restart counter (max 3 in 5 min; window expiry)
- Platform detection (mocked platform.system())
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import observeco.process_supervision as ps

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


def test_detect_platform_macos():
    with patch("platform.system", return_value="Darwin"):
        assert ps.detect_platform() == "macos"


def test_detect_platform_linux():
    with patch("platform.system", return_value="Linux"):
        assert ps.detect_platform() == "linux"


def test_detect_platform_other_windows():
    with patch("platform.system", return_value="Windows"):
        assert ps.detect_platform() == "other"


def test_detect_platform_other_unknown():
    with patch("platform.system", return_value="FreeBSD"):
        assert ps.detect_platform() == "other"


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def test_render_plist_contains_label():
    content = ps.render_plist("/usr/bin/python3", Path("/tmp/logs"))
    assert ps.LAUNCHD_LABEL in content
    assert "/usr/bin/python3" in content
    assert "observeco" in content
    assert "watch" in content
    assert "foreground" in content
    assert "/tmp/logs/observeco.log" in content


def test_render_plist_is_valid_xml():
    """Basic structure check — starts with XML declaration and has plist root."""
    content = ps.render_plist("/usr/bin/python3", Path("/tmp/logs"))
    assert content.strip().startswith("<?xml")
    assert "<plist" in content
    assert "</plist>" in content


def test_render_systemd_unit_contains_exec():
    content = ps.render_systemd_unit("/usr/bin/python3")
    assert "/usr/bin/python3 -m observeco watch foreground" in content
    assert "[Unit]" in content
    assert "[Service]" in content
    assert "[Install]" in content
    assert "Restart=on-failure" in content


def test_render_systemd_unit_restart_on_failure():
    content = ps.render_systemd_unit("/some/python")
    assert "Restart=on-failure" in content
    assert "RestartSec=10" in content


# ---------------------------------------------------------------------------
# Template path helpers
# ---------------------------------------------------------------------------


def test_template_path_macos():
    with patch("observeco.process_supervision.detect_platform", return_value="macos"):
        tpl = ps._template_path()
    assert tpl is not None
    assert "LaunchAgents" in str(tpl)
    assert tpl.suffix == ".plist"


def test_template_path_linux():
    with patch("observeco.process_supervision.detect_platform", return_value="linux"):
        tpl = ps._template_path()
    assert tpl is not None
    assert "systemd" in str(tpl)
    assert tpl.suffix == ".service"


def test_template_path_other():
    with patch("observeco.process_supervision.detect_platform", return_value="other"):
        tpl = ps._template_path()
    assert tpl is None


# ---------------------------------------------------------------------------
# install() state machine
# ---------------------------------------------------------------------------


def test_install_unsupported_platform():
    with patch("observeco.process_supervision.detect_platform", return_value="other"):
        ok, msg = ps.install()
    assert ok is True
    assert msg == ps.UNSUPPORTED_MSG


def test_install_already_installed(tmp_path):
    """If template file exists, install() is idempotent."""
    fake_plist = tmp_path / "com.observeco.daemon.plist"
    fake_plist.write_text("<plist/>")

    with (
        patch("observeco.process_supervision.detect_platform", return_value="macos"),
        patch("observeco.process_supervision._template_path", return_value=fake_plist),
    ):
        ok, msg = ps.install()

    assert ok is True
    assert msg == "Service already installed"


def test_install_macos_success(tmp_path):
    """install() writes plist and calls launchctl load, returns success."""
    fake_plist = tmp_path / "com.observeco.daemon.plist"

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    with (
        patch("observeco.process_supervision.detect_platform", return_value="macos"),
        patch("observeco.process_supervision._plist_path", return_value=fake_plist),
        patch("observeco.process_supervision._template_path", return_value=fake_plist),
        patch("observeco.process_supervision._log_dir", return_value=tmp_path),
        patch("subprocess.run", side_effect=fake_run),
    ):
        ok, msg = ps.install()

    assert ok is True
    assert "installed" in msg.lower()
    assert fake_plist.exists()


def test_install_macos_launchctl_failure(tmp_path):
    """install() returns (False, error+fix) when launchctl load fails, removes orphan."""
    fake_plist = tmp_path / "com.observeco.daemon.plist"

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 1
        m.stdout = ""
        m.stderr = "Permission denied"
        return m

    with (
        patch("observeco.process_supervision.detect_platform", return_value="macos"),
        patch("observeco.process_supervision._plist_path", return_value=fake_plist),
        patch("observeco.process_supervision._template_path", return_value=fake_plist),
        patch("observeco.process_supervision._log_dir", return_value=tmp_path),
        patch("subprocess.run", side_effect=fake_run),
    ):
        ok, msg = ps.install()

    assert ok is False
    assert "launchctl load failed" in msg
    assert "Fix:" in msg
    # Orphaned template removed on failure
    assert not fake_plist.exists()


def test_install_linux_success(tmp_path):
    """install() writes unit file and calls systemctl, returns success."""
    fake_unit = tmp_path / "observeco.service"
    call_log: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        call_log.append(cmd)
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    with (
        patch("observeco.process_supervision.detect_platform", return_value="linux"),
        patch("observeco.process_supervision._systemd_unit_path", return_value=fake_unit),
        patch("observeco.process_supervision._template_path", return_value=fake_unit),
        patch("subprocess.run", side_effect=fake_run),
    ):
        ok, msg = ps.install()

    assert ok is True
    assert fake_unit.exists()
    # Both daemon-reload and enable --now should have been called
    assert any("daemon-reload" in " ".join(c) for c in call_log)
    assert any("enable" in " ".join(c) for c in call_log)


def test_install_linux_systemctl_failure(tmp_path):
    """install() returns (False, error+fix) when systemctl daemon-reload fails."""
    fake_unit = tmp_path / "observeco.service"

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 1
        m.stdout = ""
        m.stderr = "Failed to connect"
        return m

    with (
        patch("observeco.process_supervision.detect_platform", return_value="linux"),
        patch("observeco.process_supervision._systemd_unit_path", return_value=fake_unit),
        patch("observeco.process_supervision._template_path", return_value=fake_unit),
        patch("subprocess.run", side_effect=fake_run),
    ):
        ok, msg = ps.install()

    assert ok is False
    assert "Fix:" in msg
    # Orphaned template removed on failure
    assert not fake_unit.exists()


# ---------------------------------------------------------------------------
# uninstall() state machine
# ---------------------------------------------------------------------------


def test_uninstall_unsupported_platform():
    with patch("observeco.process_supervision.detect_platform", return_value="other"):
        ok, msg = ps.uninstall()
    assert ok is True
    assert msg == ps.UNSUPPORTED_MSG


def test_uninstall_not_installed(tmp_path):
    """uninstall() when template doesn't exist is a no-op."""
    fake_plist = tmp_path / "com.observeco.daemon.plist"
    # Do NOT create the file

    with (
        patch("observeco.process_supervision.detect_platform", return_value="macos"),
        patch("observeco.process_supervision._template_path", return_value=fake_plist),
    ):
        ok, msg = ps.uninstall()

    assert ok is True
    assert msg == "Service not installed"


def test_uninstall_macos_success(tmp_path):
    """uninstall() stops service and removes plist."""
    fake_plist = tmp_path / "com.observeco.daemon.plist"
    fake_plist.write_text("<plist/>")

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    with (
        patch("observeco.process_supervision.detect_platform", return_value="macos"),
        patch("observeco.process_supervision._plist_path", return_value=fake_plist),
        patch("observeco.process_supervision._template_path", return_value=fake_plist),
        patch("subprocess.run", side_effect=fake_run),
    ):
        ok, msg = ps.uninstall()

    assert ok is True
    assert "uninstalled" in msg.lower()
    assert not fake_plist.exists()


def test_uninstall_macos_launchctl_failure(tmp_path):
    """If launchctl unload fails, uninstall() returns (False, error) and keeps plist."""
    fake_plist = tmp_path / "com.observeco.daemon.plist"
    fake_plist.write_text("<plist/>")

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 1
        m.stdout = ""
        m.stderr = "Could not find specified service"
        return m

    with (
        patch("observeco.process_supervision.detect_platform", return_value="macos"),
        patch("observeco.process_supervision._plist_path", return_value=fake_plist),
        patch("observeco.process_supervision._template_path", return_value=fake_plist),
        patch("subprocess.run", side_effect=fake_run),
    ):
        ok, msg = ps.uninstall()

    assert ok is False
    assert "launchctl unload failed" in msg
    # plist should still be present since stop failed
    assert fake_plist.exists()


def test_uninstall_linux_success(tmp_path):
    """uninstall() on Linux stops and disables the unit, removes file."""
    fake_unit = tmp_path / "observeco.service"
    fake_unit.write_text("[Unit]\n")
    call_log: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        call_log.append(cmd)
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    with (
        patch("observeco.process_supervision.detect_platform", return_value="linux"),
        patch("observeco.process_supervision._systemd_unit_path", return_value=fake_unit),
        patch("observeco.process_supervision._template_path", return_value=fake_unit),
        patch("subprocess.run", side_effect=fake_run),
    ):
        ok, msg = ps.uninstall()

    assert ok is True
    assert not fake_unit.exists()
    assert any("stop" in " ".join(c) for c in call_log)
    assert any("disable" in " ".join(c) for c in call_log)


# ---------------------------------------------------------------------------
# Restart counter (PID-file fallback)
# ---------------------------------------------------------------------------


def test_restart_counter_empty_can_restart(tmp_path):
    """Fresh counter → can restart."""
    with patch("observeco.process_supervision._counter_file", return_value=tmp_path / "restarts.json"):
        assert ps._can_restart() is True


def test_restart_counter_below_limit(tmp_path):
    cf = tmp_path / "restarts.json"
    with patch("observeco.process_supervision._counter_file", return_value=cf):
        for _ in range(ps.RESTART_MAX - 1):
            ps._record_restart()
        assert ps._can_restart() is True


def test_restart_counter_at_limit(tmp_path):
    """After RESTART_MAX restarts, _can_restart() returns False."""
    cf = tmp_path / "restarts.json"
    with patch("observeco.process_supervision._counter_file", return_value=cf):
        for _ in range(ps.RESTART_MAX):
            ps._record_restart()
        assert ps._can_restart() is False


def test_restart_counter_fourth_restart_blocked(tmp_path):
    """4th restart within window is blocked."""
    cf = tmp_path / "restarts.json"
    with patch("observeco.process_supervision._counter_file", return_value=cf):
        for _ in range(ps.RESTART_MAX):
            ps._record_restart()
        # 4th restart attempt — should be denied
        assert ps._can_restart() is False


def test_restart_counter_window_expiry(tmp_path):
    """Timestamps outside RESTART_WINDOW don't count toward the limit."""
    cf = tmp_path / "restarts.json"
    # Write RESTART_MAX timestamps all older than the window
    old_ts = time.time() - ps.RESTART_WINDOW - 10
    cf.write_text(json.dumps({"restarts": [old_ts] * ps.RESTART_MAX}))

    with patch("observeco.process_supervision._counter_file", return_value=cf):
        assert ps._can_restart() is True


def test_restart_counter_mixed_window(tmp_path):
    """Only recent timestamps count — mix of old and new."""
    cf = tmp_path / "restarts.json"
    now = time.time()
    # 2 recent + 3 old (old should be ignored)
    old_ts = now - ps.RESTART_WINDOW - 10
    ts = [old_ts, old_ts, old_ts, now - 1, now - 2]
    cf.write_text(json.dumps({"restarts": ts}))

    with patch("observeco.process_supervision._counter_file", return_value=cf):
        assert ps._can_restart() is True  # only 2 recent, below limit of 3


# ---------------------------------------------------------------------------
# PID-file fallback status
# ---------------------------------------------------------------------------


def test_pid_fallback_status_no_file(tmp_path):
    with patch("observeco.process_supervision._pid_file", return_value=tmp_path / ".supervisor.pid"):
        status = ps._pid_fallback_status()
    assert status["running"] is False
    assert status["installed"] is False


def test_pid_fallback_status_dead_pid(tmp_path):
    """PID file exists but points to a non-existent process."""
    pf = tmp_path / ".supervisor.pid"
    # Use a PID that is almost certainly not running (max PID on macOS is 99998)
    pf.write_text("99997")
    with (
        patch("observeco.process_supervision._pid_file", return_value=pf),
        patch("os.kill", side_effect=ProcessLookupError),
    ):
        status = ps._pid_fallback_status()
    assert status["running"] is False
    assert status["installed"] is True


def test_pid_fallback_status_valid_pid(tmp_path):
    """PID file points to the current process — should be running."""
    pf = tmp_path / ".supervisor.pid"
    pf.write_text(str(os.getpid()))
    with patch("observeco.process_supervision._pid_file", return_value=pf):
        status = ps._pid_fallback_status()
    assert status["running"] is True
    assert status["pid"] == os.getpid()


def test_pid_fallback_status_invalid_pid_file(tmp_path):
    """Corrupt PID file is treated as not installed."""
    pf = tmp_path / ".supervisor.pid"
    pf.write_text("not-a-number")
    with patch("observeco.process_supervision._pid_file", return_value=pf):
        status = ps._pid_fallback_status()
    assert status["running"] is False
    assert status["installed"] is False


# ---------------------------------------------------------------------------
# pid_fallback_maybe_restart
# ---------------------------------------------------------------------------


def test_pid_fallback_maybe_restart_already_running(tmp_path):
    """No restart attempted if daemon is alive."""
    pf = tmp_path / ".supervisor.pid"
    pf.write_text(str(os.getpid()))

    with patch("observeco.process_supervision._pid_file", return_value=pf):
        restarted, msg = ps.pid_fallback_maybe_restart()

    assert restarted is False
    assert "already running" in msg


def test_pid_fallback_maybe_restart_at_limit(tmp_path):
    """Restart blocked when limit is hit."""
    pf = tmp_path / ".supervisor.pid"
    cf = tmp_path / "restarts.json"
    # No PID file → daemon is down
    now = time.time()
    cf.write_text(json.dumps({"restarts": [now - 1] * ps.RESTART_MAX}))

    with (
        patch("observeco.process_supervision._pid_file", return_value=pf),
        patch("observeco.process_supervision._counter_file", return_value=cf),
    ):
        restarted, msg = ps.pid_fallback_maybe_restart()

    assert restarted is False
    assert "limit" in msg.lower()


def test_pid_fallback_maybe_restart_launches_process(tmp_path):
    """Restart is attempted when daemon is down and under limit."""
    pf = tmp_path / ".supervisor.pid"
    cf = tmp_path / "restarts.json"

    mock_proc = MagicMock()
    mock_proc.pid = 12345

    with (
        patch("observeco.process_supervision._pid_file", return_value=pf),
        patch("observeco.process_supervision._counter_file", return_value=cf),
        patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
    ):
        restarted, msg = ps.pid_fallback_maybe_restart()

    assert restarted is True
    assert "12345" in msg
    assert pf.read_text() == "12345"
    mock_popen.assert_called_once()
    # start_new_session=True must be set to properly detach
    _, kwargs = mock_popen.call_args
    assert kwargs.get("start_new_session") is True
