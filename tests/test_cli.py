"""Tests for observeco CLI."""
import subprocess

OBSERVECO = "observeco"


def test_cli_help():
    result = subprocess.run([OBSERVECO, "--help"],
                           capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "pulse" in result.stdout
    assert "chisel" in result.stdout
    assert "clawforge" in result.stdout
    assert "dashboard" in result.stdout


def test_pulse_check_help():
    result = subprocess.run([OBSERVECO, "pulse", "check", "--help"],
                           capture_output=True, text=True)
    assert result.returncode == 0
    assert "alive" in result.stdout.lower() or "watch" in result.stdout.lower()


def test_pulse_circuit_help():
    result = subprocess.run([OBSERVECO, "pulse", "circuit", "--help"],
                           capture_output=True, text=True)
    assert result.returncode == 0
    assert "reset" in result.stdout.lower()


def test_chisel_help():
    result = subprocess.run([OBSERVECO, "chisel", "--help"],
                           capture_output=True, text=True)
    assert result.returncode == 0
    assert "trim" in result.stdout.lower()


def test_clawforge_help():
    result = subprocess.run([OBSERVECO, "clawforge", "--help"],
                           capture_output=True, text=True)
    assert result.returncode == 0
    assert "profile" in result.stdout.lower()


def test_trim_stdin():
    result = subprocess.run(
        [OBSERVECO, "chisel", "trim"],
        input="You are a helpful assistant with access to web search and file tools.",
        capture_output=True, text=True, timeout=10
    )
    assert "Token" in result.stdout or "Chisel" in result.stdout


def test_clawforge_load_probe():
    result = subprocess.run(
        [OBSERVECO, "clawforge", "load", "--probe"],
        capture_output=True, text=True, timeout=10
    )
    assert "Intent" in result.stdout or "debug" in result.stdout.lower() or "query" in result.stdout.lower()


def test_dashboard_help():
    result = subprocess.run([OBSERVECO, "dashboard", "--help"],
                           capture_output=True, text=True)
    assert result.returncode == 0
    assert "port" in result.stdout.lower()


def test_db_module():
    """Test that db module initializes cleanly."""
    import os
    import tempfile

    from observeco.db import Database
    db = Database(db_path=os.path.join(tempfile.gettempdir(), "test_observeco.db"))
    assert db is not None
    db.close()
    os.remove(os.path.join(tempfile.gettempdir(), "test_observeco.db"))


def test_config_auto_detect():
    from observeco.config import load_config
    config = load_config()
    assert config is not None
    assert hasattr(config, "agents")
