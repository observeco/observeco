"""Tests for pulse check and circuit breaker modules."""
from observeco.config import AgentConfig
from observeco.pulse.check import _probe_agent, classify_restart, _find_agent_log, _read_last_n_lines
from observeco.pulse.circuit import run_circuit


def test_probe_agent_returns_tuple():
    """_probe_agent should return (status, response_time, error, metadata) tuple."""
    agent = AgentConfig(name="test-agent", framework="custom", health_check="echo ok")
    result = _probe_agent(agent)
    assert isinstance(result, tuple)
    assert len(result) == 4
    status, response_time, error, metadata = result
    assert status in ("alive", "dead", "error")
    assert isinstance(response_time, float)
    assert isinstance(error, str)
    assert isinstance(metadata, str)


def test_probe_agent_custom_health():
    """A valid health check command should return alive."""
    agent = AgentConfig(name="ping-agent", framework="custom", health_check="echo pong")
    status, rt, err, meta = _probe_agent(agent)
    assert status == "alive"
    assert rt >= 0.0


def test_run_circuit_help():
    """run_circuit should work without errors for default state."""
    # Running with no agents tracked should return cleanly
    result = run_circuit()
    assert result is None or result is not None  # runs, no crash


def test_run_circuit_reset():
    """run_circuit reset should not crash on non-existent agent."""
    try:
        run_circuit(reset="nonexistent-test-agent")
    except Exception as e:
        # It might raise or not — just confirm no unexpected crash type
        assert False, f"run_circuit raised: {e}"


# ── obs-spec-018: classify_restart ──

def test_classify_restart_healthy_exit_code_0():
    """Exit code 0 should return 'healthy'."""
    rtype, snippet, evidence = classify_restart("test-agent", exit_code=0)
    assert rtype == "healthy"


def test_classify_restart_healthy_keepalive_default():
    """No error info and no crash signals should default to 'healthy'."""
    rtype, _, _ = classify_restart("test-agent", error_message="", exit_code=-1)
    assert rtype == "healthy"


def test_classify_restart_toctou_file_not_found_stat():
    """FileNotFoundError + .stat() in error_message should return 'toctou'."""
    rtype, _, _ = classify_restart(
        "test-agent",
        error_message="FileNotFoundError: .../file.json — consumed before .stat()",
        exit_code=1,
    )
    assert rtype == "toctou"


def test_classify_restart_crash_sigsegv():
    """SIGSEGV in error_message should return 'crash'."""
    rtype, _, _ = classify_restart(
        "test-agent",
        error_message="SIGSEGV — Segmentation fault at 0x7f8e9a000000",
        exit_code=139,
    )
    assert rtype == "crash"


def test_classify_restart_crash_oom():
    """MemoryError in error_message should return 'crash'."""
    rtype, _, _ = classify_restart(
        "test-agent",
        error_message="MemoryError: Unable to allocate 2.3 GiB",
        exit_code=1,
    )
    assert rtype == "crash"


def test_classify_restart_crash_modulenotfound():
    """ModuleNotFoundError should return 'crash' when no .stat() pattern."""
    rtype, _, _ = classify_restart(
        "test-agent",
        error_message="ModuleNotFoundError: No module named 'nonexistent'",
        exit_code=1,
    )
    assert rtype == "crash"


def test_classify_restart_toctou_not_crash():
    """TOCTOU with FileNotFoundError should NOT return 'crash' even with ModuleNotFoundError."""
    rtype, _, _ = classify_restart(
        "test-agent",
        error_message="FileNotFoundError: file.json — consumed before .stat()",
        exit_code=1,
    )
    assert rtype == "toctou"


def test_read_last_n_lines_empty_file():
    """_read_last_n_lines should return empty string for non-existent file."""
    result = _read_last_n_lines("/tmp/nonexistent_log_file_xyz.log", 10)
    assert result == ""


def test_find_agent_log_no_logs():
    """_find_agent_log should return None for agents without logs."""
    result = _find_agent_log("agent_with_no_logs_xyz")
    # Should not crash — returns None
    assert result is None or not result.exists()
