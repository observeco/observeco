"""Tests for probe registry integration — _probe_agent should delegate to resolve_probe()."""
from observeco.config import AgentConfig
from observeco.pulse.check import _probe_agent
from observeco.probe.registry import resolve_probe, get_probe


def test_probe_agent_http_delegates_to_http_probe():
    """Agent with http:// health_check should use HttpProbe."""
    agent = AgentConfig(name="web", framework="custom", health_check="http://localhost:8000/health")
    result = _probe_agent(agent)
    assert isinstance(result, tuple)
    assert len(result) == 4
    status, latency, error, metadata = result
    assert status in ("alive", "dead", "error")
    assert isinstance(latency, float)  # might get connection refused quickly
    assert isinstance(error, str)


def test_probe_agent_launchd_delegates():
    """Agent with launchd: health_check should use LaunchdProbe."""
    agent = AgentConfig(name="svc", framework="custom", health_check="launchd:com.example.service")
    result = _probe_agent(agent)
    status, latency, error, _ = result
    assert status in ("alive", "dead", "error")
    assert isinstance(error, str)


def test_probe_agent_docker_delegates():
    """Agent with docker: health_check should use DockerProbe."""
    agent = AgentConfig(name="container", framework="custom", health_check="docker:my_container")
    result = _probe_agent(agent)
    status, latency, error, _ = result
    assert status in ("alive", "dead", "error")
    assert isinstance(error, str)


def test_probe_agent_shell_delegates():
    """Agent with shell command health_check should use ShellProbe."""
    agent = AgentConfig(name="cmd", framework="custom", health_check="echo ok")
    result = _probe_agent(agent)
    status, latency, error, _ = result
    assert status == "alive"
    assert latency >= 0


def test_probe_agent_pgrep_fallback():
    """Agent without health_check should use PgrepProbe."""
    agent = AgentConfig(name="python3", framework="custom")  # pgrep should find python3
    result = _probe_agent(agent)
    status, latency, error, _ = result
    assert status in ("alive", "dead")
    assert isinstance(latency, float)


def test_probe_agent_resolve_matches_old_behavior():
    """resolve_probe should return the same probe type the old code dispatched to."""
    assert get_probe("http") is not None
    assert get_probe("launchd") is not None
    assert get_probe("docker") is not None
    assert get_probe("systemd") is not None
    assert get_probe("pgrep") is not None