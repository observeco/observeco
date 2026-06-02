"""Tests for Phase 7.4 — Probe Driver Registry."""
from observeco.config import AgentConfig
from observeco.probe.registry import BaseProbe, register, get_probe, list_probe_types, ProbeResult


def test_register_decorator():
    """@register should map a scheme to a probe class."""
    @register("test_scheme")
    class TestProbe(BaseProbe):
        def probe(self, agent, timeout=10):
            return ProbeResult(status="alive", latency_ms=1.0)

    assert "test_scheme" in list_probe_types()
    probe_cls = get_probe("test_scheme")
    assert probe_cls is TestProbe


def test_get_probe_http():
    """HTTP probe should be registered."""
    probe_cls = get_probe("http")
    assert probe_cls is not None
    assert issubclass(probe_cls, BaseProbe)


def test_get_probe_launchd():
    """launchd probe should be registered."""
    probe_cls = get_probe("launchd")
    assert probe_cls is not None


def test_get_probe_docker():
    """Docker probe should be registered."""
    probe_cls = get_probe("docker")
    assert probe_cls is not None


def test_base_probe_abstraction():
    """BaseProbe should enforce probe() method."""
    class Incomplete(BaseProbe):
        pass

    try:
        Incomplete().probe(AgentConfig(name="test", framework="custom"))
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass


def test_probe_result_defaults():
    """ProbeResult should have sensible defaults."""
    r = ProbeResult(status="alive", latency_ms=5.0)
    assert r.status == "alive"
    assert r.latency_ms == 5.0
    assert r.error == ""
    assert r.metadata == ""


def test_probe_result_properties():
    """ProbeResult should support all status fields."""
    r = ProbeResult(status="dead", latency_ms=100.0, error="not found", metadata='{"pid": 123}')
    assert r.is_alive is False
    assert "not found" in r.error
    assert r.metadata == '{"pid": 123}'


def test_probe_resolver_resolves_http():
    """resolve_probe should return the right probe for an http health_check."""
    from observeco.probe.registry import resolve_probe
    agent = AgentConfig(name="web", framework="custom", health_check="http://localhost:8000/health")
    probe = resolve_probe(agent)
    assert probe is not None
    assert probe.__class__.__name__ in ("HttpProbe",)


def test_probe_resolver_resolves_launchd():
    from observeco.probe.registry import resolve_probe
    agent = AgentConfig(name="svc", framework="custom", health_check="launchd:com.example.service")
    probe = resolve_probe(agent)
    assert probe is not None


def test_probe_resolver_falls_back_to_pgrep():
    """Agents with no health_check should resolve to pgrep probe."""
    from observeco.probe.registry import resolve_probe
    agent = AgentConfig(name="my-agent", framework="custom")
    probe = resolve_probe(agent)
    assert probe is not None


def test_probe_resolver_unknown_scheme_falls_back():
    """Unknown schemes should fall back to shell or pgrep."""
    from observeco.probe.registry import resolve_probe
    agent = AgentConfig(name="test", framework="custom", health_check="unknown://something")
    probe = resolve_probe(agent)
    assert probe is not None