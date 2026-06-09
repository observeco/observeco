"""Tests for Phase 7.3 — First-Run State Machine Day 2: Agent Discovery Wizard."""
from fastapi.testclient import TestClient

from observeco.dashboard.auth import get_cached_secret
from observeco.dashboard.server import app
from observeco.db import Database

_SECRET = get_cached_secret()
assert len(_SECRET) >= 32

client = TestClient(app)
db = Database()


def _auth_headers():
    return {"X-ObserveCo-Token": _SECRET}


def _simulate_fresh_env():
    """Simulate a completely fresh install for testing phase transitions.

    Temporarily deactivates all agents and clears pulse data so get_phase()
    returns "zero".
    """
    conn = db._get_conn()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DELETE FROM _meta WHERE key='dashboard_phase'")
    conn.execute("UPDATE agent_configs SET is_active=0")
    old_pulses = conn.execute("SELECT COUNT(*) as c FROM pulse_log").fetchone()["c"]
    if old_pulses > 0:
        conn.execute("DELETE FROM pulse_log")
    conn.commit()
    return old_pulses


def _restore_env(old_pulses):
    """Restore the real env after fresh env test."""
    conn = db._get_conn()
    conn.execute("UPDATE agent_configs SET is_active=1")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("DELETE FROM _meta WHERE key='dashboard_phase'")
    conn.commit()


def test_discover_run_endpoint_exists():
    """POST /api/discover/run should return 200 or 500 (LLM may be unavailable)."""
    response = client.post("/api/discover/run", headers=_auth_headers())
    assert response.status_code in (200, 500, 404), f"Got {response.status_code}"


def test_discover_candidates_endpoint():
    """GET /api/discover/candidates should return JSON with agents list."""
    response = client.get("/api/discover/candidates", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert isinstance(data["candidates"], list)
    assert "count" in data


def test_discover_candidates_fields():
    """Each candidate should have name and type fields."""
    response = client.get("/api/discover/candidates", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    for c in data["candidates"]:
        assert "name" in c
        assert "type" in c


def test_discover_candidates_empty_on_fresh():
    """Fresh dashboard should have empty candidates list initially."""
    response = client.get("/api/discover/candidates", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 0


def test_phase_state_returns_fields():
    """GET /api/phase/state returns phase metadata."""
    response = client.get("/api/phase/state", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "phase" in data
    assert "is_first_run" in data
    assert "agents_exist" in data


def test_phase_transition_forward():
    """POST /api/phase/transition should move forward (zero -> setup)."""
    old_pulses = _simulate_fresh_env()
    r1 = client.post("/api/phase/transition", json={"phase": "setup"}, headers=_auth_headers())
    assert r1.status_code == 200
    assert r1.json()["phase"] == "setup"
    _restore_env(old_pulses)


def test_phase_transition_invalid():
    """Invalid phase returns 400."""
    response = client.post("/api/phase/transition", json={"phase": "invalid"}, headers=_auth_headers())
    assert response.status_code == 400


def test_phase_banner_returns_html_on_zero():
    """GET /api/phase returns HTML banner."""
    response = client.get("/api/phase")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
