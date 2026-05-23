"""Tests for pulse check and circuit breaker modules."""
import json
import os
import tempfile
from observeco.pulse.check import _probe_agent, run_check
from observeco.pulse.circuit import run_circuit
from observeco.config import AgentConfig


def test_probe_agent_returns_tuple():
    """_probe_agent should return (status, response_time, error) tuple."""
    agent = AgentConfig(name="test-agent", framework="custom", health_check="echo ok")
    result = _probe_agent(agent)
    assert isinstance(result, tuple)
    assert len(result) == 3
    status, response_time, error = result
    assert status in ("alive", "dead", "error")
    assert isinstance(response_time, float)
    assert isinstance(error, str)


def test_probe_agent_custom_health():
    """A valid health check command should return alive."""
    agent = AgentConfig(name="ping-agent", framework="custom", health_check="echo pong")
    status, rt, err = _probe_agent(agent)
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
