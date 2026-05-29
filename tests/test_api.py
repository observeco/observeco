"""Tests for the observeco public API module."""

from observeco.api import router


def test_router_has_routes():
    assert len(router.routes) > 0, "Router has no routes"


def test_health_route_exists():
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert any("health" in str(p) for p in paths), f"No health route in {paths}"


def test_api_has_multiple_endpoints():
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert len(paths) >= 5, f"Expected 5+ endpoints, got {len(paths)}: {paths}"
