"""Static contract test: every API path in the frontend must have a backend route,
and every response must contain the fields the frontend expects.

Parses index.html to extract all literal fetch() paths and htmx attribute paths,
then compares against FastAPI's route table. Also checks response shapes for
key JSON endpoints using FastAPI's in-process TestClient.

KNOWN_MISSING documents paths the frontend calls that intentionally have no
backend route yet. Adding a path here is a TODO, not a permanent exemption.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from observeco.dashboard.auth import load_or_generate_secret
from observeco.dashboard.server import app

client = TestClient(app)
_dash_secret = load_or_generate_secret()


def _auth_get(path: str):
    """GET with dashboard auth token as query param."""
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}token={_dash_secret}")


# ── Paths the frontend calls that intentionally have no backend route ──
# Each entry is a TODO: implement the route or remove the frontend call.
KNOWN_MISSING: set[str] = set()
# All gaps filled — keep this set for future additions.

# ── Paths that use dynamic segments (/{id}, /{name}) — matched by prefix ──
# These can't be exact-matched, so we check the prefix exists in backend routes.
DYNAMIC_PREFIXES: set[str] = {
    "/api/agent-detail/",
    "/api/agent/",
    "/api/reset-circuit/",
    "/api/circuit-breaker/",
    "/api/alert-test/",
    "/api/alert-subscribe/",
    "/api/provider-config/",
    "/api/billing/admin/cancel/",
    "/api/agents/",
    "/api/pro-preview/",
}

# ── Response shape registry ──
RESPONSE_SHAPES: dict[str, set[str]] = {
    # Static JSON endpoints — checked for 200 + expected keys
    "/api/tokens/chart": {"data", "summary", "granularity", "component"},
    "/api/tokens/agents": {"agents"},
    "/api/tokens/providers": {"providers"},
    "/api/tokens/breakdown": {"data", "dimension"},
    "/api/compress-log": set(),  # returns a list, no top-level keys
    "/api/migration-status": {"has_failure"},
    "/api/pipeline/health": {"tier", "otel_stale", "sources", "upgrade_path"},
    "/api/token-history": {"has_real_data", "snapshots", "summary"},
    "/api/watch-daemon-status": set(),
    "/api/phase/state": set(),
    "/api/optimiser/stats": set(),
    "/api/garden-summary": set(),
    "/api/skills-audit": set(),
    "/api/alerts-subs": set(),
    "/api/l2-trends": set(),
    "/api/l2-scan": set(),
    "/api/trigger-heal": set(),
    "/api/restart-quality/scan": set(),
    "/api/brain": set(),
    "/api/platforms": set(),
    "/api/error-state": set(),
    "/api/delay-banner": set(),
    "/api/alerts": set(),
    "/api/errors": set(),
    "/api/instances": set(),
    "/api/shared-warning": set(),
    "/api/telemetry-prompt": set(),
    "/api/fleet-summary": set(),
    "/api/licenses/badge": set(),
    "/api/onboarding": set(),
    "/api/phase": set(),
    "/api/onboarding-guide": set(),
    "/api/self-monitor-summary": set(),
    "/api/config-health": set(),
    "/api/restart-quality": set(),
    "/api/heal-config": set(),
    "/api/alert-dashboard": set(),
    "/api/alert-log": set(),
    "/api/fleet-compare": set(),
    "/api/budget-planner": set(),
    "/api/licenses/status": set(),
    "/api/telemetry-status": set(),
}


def _get_backend_routes() -> set[str]:
    """Extract all registered FastAPI routes (method + path)."""
    routes: set[str] = set()
    for r in app.routes:
        if hasattr(r, "path") and hasattr(r, "methods"):
            for method in r.methods:  # type: ignore[attr-defined]
                routes.add(f"{method} {r.path}")  # type: ignore[attr-defined]
    return routes


def _extract_fetch_paths(html: str) -> set[str]:
    """Extract literal string paths from fetch() calls.

    Handles: fetch('/api/foo'), fetch('/api/foo?' + params)
    Skips:   fetch('/api/foo/' + dynamicVar)
    """
    paths: set[str] = set()

    for m in re.finditer(r"fetch\(([^)]+)\)", html):
        arg = m.group(1).strip()
        for quote in ("'", '"', "`"):
            if arg.startswith(quote):
                end = arg.find(quote, 1)
                if end > 0:
                    path = arg[1:end].split("?")[0].split("{")[0]
                    if path.startswith("/api/"):
                        paths.add(path)
                break
        if "?" in arg and "+" in arg:
            parts = arg.split("+", 1)
            lhs = parts[0].strip()
            for quote in ("'", '"', "`"):
                if lhs.startswith(quote) and lhs.endswith(quote):
                    path = lhs[1:-1].split("?")[0]
                    if path.startswith("/api/"):
                        paths.add(path)
                    break

    return paths


def _extract_htmx_paths(html: str) -> set[str]:
    """Extract literal paths from hx-get/hx-post/hx-put/hx-delete/hx-patch attributes."""
    paths: set[str] = set()
    for attr in ("hx-get", "hx-post", "hx-put", "hx-delete", "hx-patch"):
        for m in re.finditer(rf'{attr}="([^"]+)"', html):
            path = m.group(1).split("?")[0].split("{")[0].rstrip("/")
            if path.startswith("/api/") or path.startswith("/auth/"):
                paths.add(path)
    return paths


def _path_matches_backend(frontend_path: str, backend_routes: set[str]) -> bool:
    """Check if a frontend path has a matching backend route.

    Handles exact matches, dynamic segments, and trailing-slash normalization.
    """
    for prefix in DYNAMIC_PREFIXES:
        if frontend_path.startswith(prefix):
            for br in backend_routes:
                if prefix in br:
                    return True
            return False

    for br in backend_routes:
        br_path = br.split(" ", 1)[1] if " " in br else br
        if frontend_path == br_path or frontend_path.rstrip("/") == br_path.rstrip("/"):
            return True

    return False


# ── Tests ──


def test_all_fetch_paths_have_backend_routes():
    html = Path("src/observeco/dashboard/templates/index.html").read_text()
    backend = _get_backend_routes()
    frontend = _extract_fetch_paths(html)

    missing: list[str] = []
    for path in sorted(frontend):
        if path in KNOWN_MISSING:
            continue
        if not _path_matches_backend(path, backend):
            missing.append(path)

    assert not missing, (
        "Frontend calls these paths but no backend route exists:\n"
        + "\n".join(f"  {p}" for p in missing)
        + "\n\nEither add the backend route or add the path to KNOWN_MISSING."
    )


def test_all_htmx_paths_have_backend_routes():
    html = Path("src/observeco/dashboard/templates/index.html").read_text()
    backend = _get_backend_routes()
    frontend = _extract_htmx_paths(html)

    missing: list[str] = []
    for path in sorted(frontend):
        if path in KNOWN_MISSING:
            continue
        if not _path_matches_backend(path, backend):
            missing.append(path)

    assert not missing, (
        "Frontend htmx attributes reference these paths but no backend route exists:\n"
        + "\n".join(f"  {p}" for p in missing)
        + "\n\nEither add the backend route or add the path to KNOWN_MISSING."
    )


def test_response_shapes():
    """Every endpoint in RESPONSE_SHAPES returns 200 and contains expected keys.

    This catches field-name mismatches between frontend expectations and backend
    responses — the same class of bug as path mismatches, but at the field level.
    """
    for path, expected_keys in sorted(RESPONSE_SHAPES.items()):
        # Dynamic routes need a path parameter — skip them in shape checks
        if "{" in path or any(path.startswith(p) for p in DYNAMIC_PREFIXES):
            continue

        resp = _auth_get(path)
        assert resp.status_code == 200, (
            f"{path} returned {resp.status_code}, expected 200"
        )

        if not expected_keys:
            continue

        data = resp.json()
        missing = expected_keys - set(data.keys())
        assert not missing, (
            f"{path} response missing expected keys: {missing}. "
            f"Got keys: {list(data.keys())}"
        )
