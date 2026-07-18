"""Tests for startup_validation — spec obs-spec-023 §17.2."""

import socket
import sqlite3
from pathlib import Path

import pytest

from observeco.startup_validation import (
    check_config,
    check_data_dir,
    check_db_writable,
    check_port,
    run_checks,
)

# ---------------------------------------------------------------------------
# check_data_dir
# ---------------------------------------------------------------------------


def test_data_dir_created_when_missing(tmp_path):
    """First-run: missing directory is created, check returns ok."""
    target = tmp_path / "new_subdir" / "observeco"
    assert not target.exists()

    result = check_data_dir(target)

    assert result.ok
    assert result.fatal
    assert target.exists()


def test_data_dir_existing_dir_passes(tmp_path):
    result = check_data_dir(tmp_path)
    assert result.ok


def test_data_dir_unwritable_returns_fatal_error(tmp_path, monkeypatch):
    """Simulate mkdir failure — check is fatal with correct message format."""

    def _bad_mkdir(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", _bad_mkdir)

    result = check_data_dir(tmp_path / "no_perms")

    assert not result.ok
    assert result.fatal
    assert result.message.startswith("Error:")
    assert "Fix:" in result.fix
    assert "mkdir" in result.fix


# ---------------------------------------------------------------------------
# check_db_writable
# ---------------------------------------------------------------------------


def test_db_writable_creates_db_on_first_run(tmp_path):
    """First-run: no DB file → SQLite creates it, check passes."""
    db = tmp_path / "pulse.db"
    assert not db.exists()

    result = check_db_writable(db)

    assert result.ok
    assert result.fatal
    assert db.exists()


def test_db_writable_existing_db_passes(tmp_path):
    db = tmp_path / "pulse.db"
    sqlite3.connect(str(db)).close()

    result = check_db_writable(db)

    assert result.ok


def test_db_writable_unreadable_returns_fatal(tmp_path, monkeypatch):
    """sqlite3.connect failure → fatal error with spec-compliant message."""

    def _bad_connect(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(sqlite3, "connect", _bad_connect)

    result = check_db_writable(tmp_path / "bad.db")

    assert not result.ok
    assert result.fatal
    assert result.message.startswith("Error: Cannot write to")
    assert "Fix:" in result.fix
    assert "mkdir" in result.fix


# ---------------------------------------------------------------------------
# check_port
# ---------------------------------------------------------------------------


def _bind_free_port() -> tuple[socket.socket, int]:
    """Bind a free OS port and return the socket + port (caller must close)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    return s, s.getsockname()[1]


def test_port_free_passes():
    s, port = _bind_free_port()
    s.close()  # release before check

    result = check_port(port)

    assert result.ok
    assert result.fatal


def test_port_in_use_returns_fatal_error():
    """Port held by another socket → fatal, message and fix match spec templates."""
    s, port = _bind_free_port()
    try:
        result = check_port(port)

        assert not result.ok
        assert result.fatal
        assert result.message.startswith(f"Error: Port {port} is in use")
        assert "--port" in result.fix
        assert str(port + 1) in result.fix  # alt_port suggestion
    finally:
        s.close()


def test_port_fix_includes_alt_port():
    """Fix instruction always suggests port + 1."""
    s, port = _bind_free_port()
    try:
        result = check_port(port)
        assert str(port + 1) in result.fix
    finally:
        s.close()


# ---------------------------------------------------------------------------
# check_config
# ---------------------------------------------------------------------------


def test_config_missing_is_ok(tmp_path):
    """First-run: no config file → use defaults, not an error."""
    result = check_config(tmp_path / "config.yaml")

    assert result.ok
    assert not result.fatal  # warnings are not fatal


def test_config_valid_yaml_passes(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("log_level: info\n")

    result = check_config(cfg)

    assert result.ok
    assert not result.fatal


def test_config_invalid_yaml_is_warning(tmp_path):
    """Malformed YAML → not ok but NOT fatal (warning only)."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("log_level: [\nbad yaml here\n")

    result = check_config(cfg)

    assert not result.ok
    assert not result.fatal  # WARNING, not fatal
    assert "Warning:" in result.message


def test_config_invalid_value_is_warning(tmp_path):
    """Valid YAML but bad key value → warning with spec-format fix."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("log_level: verbose\n")  # "verbose" not in valid set

    result = check_config(cfg)

    assert not result.ok
    assert not result.fatal
    assert "log_level" in result.message
    assert "verbose" in result.fix
    assert "Expected one of" in result.fix


# ---------------------------------------------------------------------------
# run_checks — orchestration
# ---------------------------------------------------------------------------


def test_run_checks_first_run_creates_dir(tmp_path):
    """run_checks on a fresh tmp_path creates the data dir."""
    target = tmp_path / "fresh_install"
    assert not target.exists()

    result = run_checks(
        data_dir=target,
        db_path=target / "pulse.db",
        ports=[],
        config_path=target / "config.yaml",
        print_output=False,
        exit_on_fatal=False,
    )

    assert target.exists()
    assert result.passed


def test_run_checks_fatal_vs_warning_distinction(tmp_path):
    """Checks 1-3 are fatal; check 4 is a warning."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("log_level: bad_value\n")

    result = run_checks(
        data_dir=tmp_path,
        db_path=tmp_path / "pulse.db",
        ports=[],
        config_path=cfg,
        print_output=False,
        exit_on_fatal=False,
    )

    # data_dir and db_writable are fatal=True; config is fatal=False
    fatal_names = {c.name for c in result.checks if c.fatal}
    warn_names = {c.name for c in result.checks if not c.fatal}
    assert "data_dir" in fatal_names
    assert "db_writable" in fatal_names
    assert "config" in warn_names
    # Config is the only warning, overall still passes (no fatal failures)
    assert result.passed
    assert len(result.warnings) == 1


def test_run_checks_port_override(tmp_path):
    """Passing an explicit free port to ports= validates that port."""
    s, free_port = _bind_free_port()
    s.close()

    result = run_checks(
        data_dir=tmp_path,
        db_path=tmp_path / "pulse.db",
        ports=[free_port],
        config_path=tmp_path / "config.yaml",
        print_output=False,
        exit_on_fatal=False,
    )

    port_check = next(c for c in result.checks if c.name == f"port_{free_port}")
    assert port_check.ok
    assert result.passed


def test_run_checks_exits_on_fatal_port_failure(tmp_path):
    """A busy port causes exit(1) when exit_on_fatal=True."""
    s, port = _bind_free_port()
    try:
        with pytest.raises(SystemExit) as exc_info:
            run_checks(
                data_dir=tmp_path,
                db_path=tmp_path / "pulse.db",
                ports=[port],
                config_path=tmp_path / "config.yaml",
                print_output=False,
                exit_on_fatal=True,
            )
        assert exc_info.value.code == 1
    finally:
        s.close()


def test_run_checks_does_not_exit_on_warning_only(tmp_path):
    """A config warning alone must NOT trigger sys.exit."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("log_level: bad\n")

    # Must not raise SystemExit
    result = run_checks(
        data_dir=tmp_path,
        db_path=tmp_path / "pulse.db",
        ports=[],
        config_path=cfg,
        print_output=False,
        exit_on_fatal=True,
    )

    assert result.passed
    assert result.warnings
