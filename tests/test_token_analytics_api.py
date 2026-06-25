"""One runnable check: token analytics endpoints return correct JSON structure.

No fixtures, no mocks. Just assert statements that fail if the logic breaks.
Runs against the real DB (empty is fine — we check structure, not data).
"""

from fastapi.testclient import TestClient
from observeco.dashboard.server import app
from observeco.dashboard.auth import load_or_generate_secret

client = TestClient(app)
_dash_secret = load_or_generate_secret()


def _auth_get(path):
    """GET with dashboard auth token as query param."""
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}token={_dash_secret}")


def test_chart_endpoint_returns_json():
    resp = _auth_get("/api/tokens/chart")
    assert resp.status_code == 200
    data = resp.json()
    assert "granularity" in data
    assert "data" in data
    assert "summary" in data
    assert data["granularity"] == "hour"


def test_chart_endpoint_with_params():
    resp = _auth_get("/api/tokens/chart?granularity=day&component=skills")
    assert resp.status_code == 200
    data = resp.json()
    assert data["granularity"] == "day"
    assert data["component"] == "skills"


def test_breakdown_endpoint_returns_json():
    resp = _auth_get("/api/tokens/breakdown?dimension=agent")
    assert resp.status_code == 200
    data = resp.json()
    assert "dimension" in data
    assert "data" in data
    assert data["dimension"] == "agent"


def test_breakdown_invalid_dimension():
    resp = _auth_get("/api/tokens/breakdown?dimension=invalid")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


def test_system_prompts_endpoint_returns_json():
    resp = _auth_get("/api/tokens/system-prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


def test_system_prompts_with_limit():
    resp = _auth_get("/api/tokens/system-prompts?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


def test_patcher_startup_noop_when_no_sdks():
    """Verify apply_all_patchers() doesn't crash when no SDKs are installed."""
    from observeco.tracking.sdk.patcher_registry import apply_all_patchers
    results = apply_all_patchers()
    assert isinstance(results, dict)
