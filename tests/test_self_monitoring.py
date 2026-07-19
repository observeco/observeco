"""Tests for self-monitoring / meta-monitoring module.

Spec: obs-spec-023-service-architecture.md §17.6
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from observeco.self_monitoring import (
    DEAD_THRESHOLD,
    STALE_THRESHOLD,
    check_pid_liveness,
    check_stuck,
    clear_heartbeat,
    get_daemon_health,
    read_heartbeat,
    write_heartbeat,
)


def test_write_heartbeat_creates_file():
    """write_heartbeat should create a valid heartbeat file."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("observeco.self_monitoring._heartbeat_path", return_value=Path(tmp) / ".daemon_heartbeat.json"):
            hb = write_heartbeat(pid=1234, cycle_count=1, uptime_seconds=0)
            assert hb["pid"] == 1234
            assert hb["cycle_count"] == 1
            assert hb["status"] == "running"
            assert "last_tick" in hb


def test_read_heartbeat_no_file():
    """No heartbeat file should return present=False."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("observeco.self_monitoring._heartbeat_path", return_value=Path(tmp) / ".daemon_heartbeat.json"):
            result = read_heartbeat()
            assert result["present"] is False
            assert "no heartbeat file found" in result["message"]


def test_read_heartbeat_valid():
    """Valid heartbeat file should return correct data."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            write_heartbeat(pid=1234, cycle_count=5, uptime_seconds=120)
            result = read_heartbeat()
            assert result["present"] is True
            assert result["valid"] is True
            assert result["pid"] == 1234
            assert result["cycle_count"] == 5
            assert result["is_stale"] is False


def test_read_heartbeat_corrupted():
    """Corrupted heartbeat file should return valid=False."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        hb_path.write_text("not valid json")
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            result = read_heartbeat()
            assert result["present"] is True
            assert result["valid"] is False
            assert "corrupted" in result["message"]


def test_read_heartbeat_stale():
    """Heartbeat older than STALE_THRESHOLD should be stale."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        hb_path.write_text(json.dumps({
            "pid": 1234,
            "last_tick": time.time() - STALE_THRESHOLD - 10,
            "cycle_count": 5,
            "uptime_seconds": 120,
            "status": "running",
        }))
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            result = read_heartbeat()
            assert result["is_stale"] is True


def test_read_heartbeat_dead():
    """Heartbeat older than DEAD_THRESHOLD should be dead."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        hb_path.write_text(json.dumps({
            "pid": 1234,
            "last_tick": time.time() - DEAD_THRESHOLD - 10,
            "cycle_count": 5,
            "uptime_seconds": 120,
            "status": "running",
        }))
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            result = read_heartbeat()
            assert result["is_dead"] is True


def test_check_pid_liveness_none():
    """None PID should return False."""
    assert check_pid_liveness(None) is False


def test_check_pid_liveness_current_process():
    """Current process PID should return True."""
    assert check_pid_liveness(os.getpid()) is True


def test_check_stuck_no_previous():
    """No previous cycle should not be stuck."""
    assert check_stuck(None, 5) is False


def test_check_stuck_no_current():
    """No current cycle should not be stuck."""
    assert check_stuck(5, None) is False


def test_check_stuck_not_stuck():
    """Increasing cycle count should not be stuck."""
    assert check_stuck(5, 6) is False


def test_check_stuck_is_stuck():
    """Same cycle count should be stuck."""
    assert check_stuck(5, 5) is True


def test_clear_heartbeat_removes_file():
    """clear_heartbeat should delete the heartbeat file."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            write_heartbeat(pid=1234, cycle_count=1, uptime_seconds=0)
            assert hb_path.exists()
            clear_heartbeat()
            assert not hb_path.exists()


def test_get_daemon_health_no_file():
    """No heartbeat should return stopped status."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("observeco.self_monitoring._heartbeat_path", return_value=Path(tmp) / ".daemon_heartbeat.json"):
            health = get_daemon_health()
            assert health["status"] == "stopped"


def test_get_daemon_health_running():
    """Fresh heartbeat should return running status."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            write_heartbeat(pid=os.getpid(), cycle_count=1, uptime_seconds=0)
            health = get_daemon_health()
            assert health["status"] == "running"


def test_get_daemon_health_stale():
    """Stale heartbeat should return stale status."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        hb_path.write_text(json.dumps({
            "pid": 99999,
            "last_tick": time.time() - STALE_THRESHOLD - 10,
            "cycle_count": 5,
            "uptime_seconds": 120,
            "status": "running",
        }))
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            health = get_daemon_health()
            assert health["status"] in ("stale", "dead")


def test_get_daemon_health_corrupted():
    """Corrupted heartbeat should return unknown status."""
    with tempfile.TemporaryDirectory() as tmp:
        hb_path = Path(tmp) / ".daemon_heartbeat.json"
        hb_path.write_text("not valid json")
        with patch("observeco.self_monitoring._heartbeat_path", return_value=hb_path):
            health = get_daemon_health()
            assert health["status"] == "unknown"
