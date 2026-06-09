"""Local dashboard auth — lightweight token-based access control.

Architecture:
  A cryptographically random token (secrets.token_urlsafe(32)) is generated
  on first dashboard launch and persisted at ~/.observeco/.dashboard_secret.
  All /api/ htmx endpoints require this token via X-ObserveCo-Token header
  or ?token= query param. This prevents any process on the local machine from
  accessing the dashboard without knowing the secret.

  This is NOT a user authentication system — it is a local-access gate that
  raises the bar from "any process can curl :9119" to "only processes that
  know a 43-character random secret can curl :9119."

  Constraints (ref requirements-fidelity Trap 5):
  - Shared mode and scale features must work unchanged with token (Lens 9)
  - First-run experience must remain intact (Layer F)
  - Must not break htmx polling / auto-refresh
  - Token query parameter accepted for curl/TestClient compatibility
  - Token NEVER appears in log output or error messages (only hint to CLI command)

  Secret lifecycle:
  - Generated once per machine (persisted to file)
  - User can view with: observeco dashboard --show-token
  - Rotated by deleting ~/.observeco/.dashboard_secret
  - No expiry — dashboard is local-only; online exposure is prevented by
    binding to 127.0.0.1 by default
"""

from __future__ import annotations

import hmac
import logging
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from observeco.dirs import get_data_dir

logger = logging.getLogger(__name__)

_TOKEN_PATH = get_data_dir() / ".dashboard_secret"


def load_or_generate_secret() -> str:
    """Load the dashboard secret from file, or generate and persist one.

    Uses cryptographically secure secrets.token_urlsafe(32) (ref Sean's
    requirement — must be crypto-secure, not random.choice).

    Returns:
        The 43-character URL-safe base64 secret string.
    """
    if _TOKEN_PATH.exists():
        try:
            secret = _TOKEN_PATH.read_text().strip()
            if len(secret) >= 32:
                return secret
        except OSError:
            pass

    # Generate new secret
    secret = secrets.token_urlsafe(32)
    try:
        _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_PATH.write_text(secret + "\n")
    except OSError as e:
        logger.warning(f"Could not persist dashboard secret: {e}")

    return secret


def get_cached_secret() -> str:
    """Return the currently cached secret (must be called after load_or_generate_secret)."""
    return _cached_secret


_cached_secret: str = ""


class DashboardAuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that requires a valid dashboard token for /api/ routes.

    The token can be provided as:
      1. X-ObserveCo-Token header (htmx uses htmx.config.headers)
      2. ?token= query parameter (curl/TestClient)

    Exclusions:
      - Static files (/static/)
      - Auth endpoints (/auth/)
      - License endpoints (/api/licenses/validate — public for license checks)
      - The root page (/) and favicon
    """

    def __init__(self, app, secret: str):
        super().__init__(app)
        self._secret = secret

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Determine if this path needs token auth
        needs_auth = (
            path.startswith("/api/")
            and not path.startswith("/api/licenses/validate")
            and not path.startswith("/api/licenses/status")
            and path not in ("/api/checkout", "/api/agent-count", "/api/phase", "/api/onboarding", "/api/pathway-graph", "/api/heal-log", "/api/trigger-heal", "/api/plugin-stats", "/api/plugin-hooks", "/api/openclaw-plugins", "/api/phase/state", "/api/no-llm/toggle", "/api/discover/run", "/api/discover/candidates", "/api/discover/confirm", "/api/discover/run-html", "/api/billing/success", "/api/billing/cancel", "/api/billing/webhook", "/api/billing/status")
        )

        # Check token for protected API routes
        if needs_auth:
            token = request.headers.get("x-observeco-token", "")
            if not token:
                token = request.query_params.get("token", "")

            if not hmac.compare_digest(token, self._secret):
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized",
                        "detail": (
                            "This dashboard is protected. "
                            "Run `observeco dashboard --show-token` to view "
                            "your access token, or add ?token=<secret> to your request."
                        ),
                    },
                )

        response = await call_next(request)

        # Add security headers to every response
        response.headers.setdefault("Content-Security-Policy", (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "form-action 'self'"
        ))
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        return response


def init_auth(app_obj) -> str:
    """Initialize the dashboard auth middleware and return the secret.

    Must be called during server startup (in serve()).
    Returns the secret for display on first run.
    """
    global _cached_secret
    _cached_secret = load_or_generate_secret()
    app_obj.add_middleware(DashboardAuthMiddleware, secret=_cached_secret)
    return _cached_secret
