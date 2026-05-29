"""Tests for the observeco public API."""

import inspect
from observeco.api import app


def test_health_endpoint_exists():
    """Verify the health route is registered."""
    routes = [r.path for r in app.routes]
    assert "/api/v1/health" in routes or any("health" in str(r.path) for r in app.routes), \
        f"Health route not found. Routes: {routes}"


def test_app_is_configured():
    """Verify the app has routes registered."""
    assert len(app.routes) > 0, "App has no routes"


def test_api_has_version_info():
    """Check api module exports version metadata."""
    from observeco import __version__
    assert __version__ == "0.1.0"
