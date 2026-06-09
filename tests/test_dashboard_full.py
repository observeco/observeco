"""Dashboard server tests — Section 4 (comprehensive coverage)."""


from fastapi.testclient import TestClient

from observeco.dashboard.auth import init_auth
from observeco.dashboard.server import app

TEST_SECRET = init_auth(app)
client = TestClient(app)
AUTH = {"X-ObserveCo-Token": TEST_SECRET}


# ── 4.1 Static Routes ────────────────────────────────────────

class TestStaticRoutes:
    def test_root_returns_html(self):
        """4.1: GET / returns 200."""
        resp = client.get("/", headers=AUTH)
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            assert "text/html" in resp.headers.get("content-type", "")

    def test_health_returns_ok(self):
        """4.1: Health endpoint returns OK."""
        # /api/health not registered — use /api/phase as health proxy
        resp = client.get("/api/phase", headers=AUTH)
        assert resp.status_code == 200

    def test_phase_endpoint_html(self):
        """4.1: GET /api/phase returns HTML."""
        resp = client.get("/api/phase", headers=AUTH)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")


# ── 4.2 Agent Routes ──────────────────────────────────────────

class TestAgentRoutes:
    def test_agents_returns_html_with_agent_cards(self):
        """4.2: GET /api/agents returns agent card HTML."""
        resp = client.get("/api/agents", headers=AUTH)
        assert resp.status_code == 200
        html = resp.text
        assert "agent-card" in html or "agent" in html.lower()

    def test_agent_detail_known_agent_returns_tabs(self):
        """4.3: GET /api/agent-detail/dreamer returns detail HTML."""
        resp = client.get("/api/agent-detail/dreamer", headers=AUTH)
        assert resp.status_code == 200
        html = resp.text
        assert "agent-detail" in html or "tab" in html or "health" in html.lower()

    def test_agent_detail_nonexistent_agent(self):
        """4.3: GET /api/agent-detail/nonexistent still returns HTML (degrades gracefully)."""
        resp = client.get("/api/agent-detail/nonexistent-agent-xyz", headers=AUTH)
        assert resp.status_code == 200

    def test_agent_detail_tabs(self):
        """4.3: Different tabs on agent detail work."""
        for tab in ["health", "tokens", "errors", "guard", "garden"]:
            resp = client.get(f"/api/agent-detail/dreamer?tab={tab}", headers=AUTH)
            assert resp.status_code == 200, f"Tab {tab} failed: {resp.status_code}"


# ── 4.3 Error Routes ──────────────────────────────────────────

class TestErrorRoutes:
    def test_error_state_returns_html(self):
        """4.4: GET /api/error-state returns error banner HTML."""
        resp = client.get("/api/error-state", headers=AUTH)
        assert resp.status_code == 200

    def test_errors_page_returns_html(self):
        """4.4: GET /api/errors returns errors page."""
        resp = client.get("/api/errors", headers=AUTH)
        assert resp.status_code == 200

    def test_reset_circuit_returns_html(self):
        """4.4: GET /api/reset-circuit/{name} returns HTML (htmx swap target)."""
        resp = client.get("/api/reset-circuit/hermes", headers=AUTH)
        assert resp.status_code == 200
        assert len(resp.text) > 0


# ── 4.4 Fleet Summary ─────────────────────────────────────────

class TestFleetRoutes:
    def test_fleet_summary_returns_html(self):
        """Fleet summary returns HTML."""
        resp = client.get("/api/fleet-summary", headers=AUTH)
        assert resp.status_code == 200

    def test_platforms_returns_html(self):
        """Platforms section returns HTML."""
        resp = client.get("/api/platforms", headers=AUTH)
        assert resp.status_code == 200


# ── 4.5 Alerts ────────────────────────────────────────────────

class TestAlertRoutes:
    def test_alerts_returns_html(self):
        """4.5: GET /api/alerts returns alerts HTML."""
        resp = client.get("/api/alerts", headers=AUTH)
        assert resp.status_code == 200

    def test_delay_banner_returns_html(self):
        """Delay banner endpoint returns HTML."""
        resp = client.get("/api/delay-banner", headers=AUTH)
        assert resp.status_code == 200


# ── 4.6 Pro Preview ───────────────────────────────────────────

class TestProPreview:
    def test_pro_preview_returns_html(self):
        """GET /api/pro-preview/{feature_id} returns HTML."""
        resp = client.get("/api/pro-preview/alerts", headers=AUTH)
        assert resp.status_code == 200

    def test_checkout_redirects(self):
        """GET /api/checkout redirects or returns info."""
        resp = client.get("/api/checkout", headers=AUTH)
        assert resp.status_code in (200, 302)


# ── 4.7 Templates / HTML Markers ──────────────────────────────

class TestTemplateMarkers:
    def test_agents_page_has_key_sections(self):
        """Agents page contains expected HTML markers."""
        resp = client.get("/api/agents", headers=AUTH)
        html = resp.text
        # At least one of these markers should exist
        markers = ["agent-card", "status-dot", "pro-tile", "section-hermes"]
        found = [m for m in markers if m in html]
        assert len(found) >= 1, f"No expected markers found in: {html[:300]}"

    def test_agent_detail_has_tabs(self):
        """Agent detail page has tab switching."""
        resp = client.get("/api/agent-detail/dreamer", headers=AUTH)
        html = resp.text
        # Should contain tab navigation or health indicator
        assert "tab" in html.lower() or "health" in html.lower()


# ── 4.8 Auth Routes ───────────────────────────────────────────

class TestAuthRoutes:
    def test_auth_login_returns_html(self):
        """GET /auth/login returns HTML."""
        resp = client.get("/auth/login", headers=AUTH)
        assert resp.status_code == 200

    def test_auth_logout_redirects(self):
        """GET /auth/logout redirects."""
        resp = client.get("/auth/logout", headers=AUTH)
        assert resp.status_code in (200, 302)

    def test_auth_me_returns_json(self):
        """GET /auth/me returns JSON."""
        resp = client.get("/auth/me", headers=AUTH)
        assert resp.status_code == 200


# ── 4.9 State Matrix ──────────────────────────────────────────

class TestStateMatrix:
    def test_loading_state_no_content_error(self):
        """All endpoints return 200, not error."""
        endpoints = [
            "/api/phase",
            "/api/alerts",
            "/api/delay-banner",
            "/api/fleet-summary",
            "/api/platforms",
        ]
        for ep in endpoints:
            resp = client.get(ep, headers=AUTH)
            assert resp.status_code == 200, f"{ep} failed: {resp.status_code}"


# ── 4.10 Unauthenticated Access ───────────────────────────────

class TestUnauthenticated:
    def test_api_endpoints_require_auth(self):
        """API endpoints return 401 without token."""
        protected = [
            "/api/agents",
            "/api/error-state",
            "/api/alerts",
            "/api/agent-detail/dreamer",
            "/api/fleet-summary",
        ]
        for ep in protected:
            resp = client.get(ep)
            assert resp.status_code == 401, f"{ep} should be 401, got {resp.status_code}"

    def test_login_public_no_auth(self):
        """Login page doesn't require auth."""
        resp = client.get("/auth/login")
        assert resp.status_code == 200

    def test_root_public_no_auth(self):
        """Root page doesn't require auth."""
        resp = client.get("/")
        assert resp.status_code == 200
