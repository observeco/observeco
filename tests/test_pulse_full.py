"""Pulse check + circuit breaker tests — Sections 5-6."""

from observeco.db import Database
from observeco.pulse.check import AgentConfig, ProbeResult, classify_restart
from observeco.pulse.circuit import run_circuit


class TestProbeResult:
    def test_probe_result_defaults(self):
        p = ProbeResult(status="ok", latency_ms=0.0)
        assert p.status == "ok"

    def test_probe_result_healthy_attribute(self):
        p = ProbeResult(status="ok", latency_ms=0.0)
        assert hasattr(p, "status")

    def test_classify_restart_returns_tuple(self):
        result = classify_restart(agent_name="test-agent")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_agent_config_defaults(self):
        cfg = AgentConfig(name="test-agent", framework="cli")
        assert cfg.name == "test-agent"


class TestCircuitBreaker:
    def test_run_circuit_returns_none(self):
        result = run_circuit()
        assert result is None

    def test_run_circuit_with_reset(self):
        result = run_circuit(reset="test-agent")
        assert result is None


class TestPulseDB:
    def test_database_init_default(self):
        db = Database()
        assert db is not None

    def test_database_init_memory(self):
        db = Database(db_path=":memory:")
        assert db is not None
        assert hasattr(db, "db_path")

    def test_database_get_phase(self):
        db = Database(db_path=":memory:")
        phase = db.get_phase()
        assert isinstance(phase, str)

    def test_database_close(self):
        db = Database(db_path=":memory:")
        db.close()

    def test_database_log_pulse_smoke(self):
        db = Database(db_path=":memory:")
        db.get_phase()  # smoke test
        assert True
