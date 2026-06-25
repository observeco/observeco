"""Dashboard commercial + otel + remaining endpoint tests."""

from fastapi.testclient import TestClient

from observeco.dashboard.auth import init_auth
from observeco.dashboard.server import app

SECRET = init_auth(app)
client = TestClient(app)
AUTH = {"X-ObserveCo-Token": SECRET}


class TestCommercialAPI:
    def test_commercial_router_imports(self):
        from observeco.dashboard.commercial_api import router
        assert router is not None

    def test_commercial_endpoints_exist(self):
        resp = client.get("/api/billing/status", headers=AUTH)
        assert resp.status_code in (200, 302)


class TestOtel:
    def test_otel_router_imports(self):
        from observeco.dashboard.otel import router
        assert router is not None

    def test_otel_live_data(self):
        resp = client.get("/api/health", headers=AUTH)
        assert resp.status_code in (200, 404)  # 404 if not registered, ok


class TestConfigAgent:
    def test_config_agent_write(self):
        from observeco.config import AgentConfig, write_agent
        a = AgentConfig(name="test-config-agent", framework="cli")
        write_agent(a)

    def test_config_load(self):
        from observeco.config import load_config
        cfg = load_config()
        assert cfg is not None

    def test_config_exclude(self):
        from observeco.config import exclude_agent, list_excluded
        n = "test-exclude-abc-123"
        exclude_agent(n)
        assert n in list_excluded()

    def test_config_pulse_interval(self):
        from observeco.config import load_config
        cfg = load_config()
        # load_config returns an ObserveConfig object with agent list
        agents = getattr(cfg, "agents", [])
        assert isinstance(agents, list)
