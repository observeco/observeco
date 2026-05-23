"""Tests for auto_detect and dashboard modules."""
import os
import tempfile
from observeco.auto_detect import run_discover, run_add
from observeco.dashboard.server import serve


def test_auto_detect_discover_runs():
    """run_discover should not crash."""
    try:
        run_discover()
    except SystemExit:
        pass  # typer may call sys.exit
    except Exception as e:
        # Acceptable if it errors on no config
        assert "config" in str(e).lower() or "not found" in str(e).lower()


def test_auto_detect_add():
    """run_add should not crash on basic call."""
    try:
        run_add("test-agent-ci", "custom", "echo ok")
    except Exception as e:
        if "config" in str(e).lower() or "not found" in str(e).lower():
            pass  # acceptable
        else:
            assert False, f"run_add raised: {e}"


def test_dashboard_serve_accepts_params():
    """serve should accept host and port params (not tested live)."""
    assert serve is not None
    # Verify function signature
    import inspect
    sig = inspect.signature(serve)
    params = list(sig.parameters.keys())
    assert "host" in params
    assert "port" in params
    assert "static" in params
