"""OAuth2 authentication for ObserveCo dashboard.

Supports:
- Google OAuth2
- GitHub OAuth2
- Generic OIDC providers
- Local session tokens (for self-hosted)

Environment variables:
    OBSERVECO_OAUTH_PROVIDER — google | github | oidc | local
    OBSERVECO_OAUTH_CLIENT_ID — OAuth client ID
    OBSERVECO_OAUTH_CLIENT_SECRET — OAuth client secret
    OBSERVECO_OAUTH_REDIRECT_URI — Callback URL
    OBSERVECO_JWT_SECRET — Secret for signing local session tokens
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """Authenticated user."""
    id: str
    email: str
    name: str
    avatar_url: str = ""
    provider: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class Session:
    """User session."""
    token: str
    user: User
    expires_at: float
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "user_id": self.user.id,
            "email": self.user.email,
            "name": self.user.name,
            "expires_at": self.expires_at,
        }


class OAuth2Provider:
    """OAuth2 authentication provider."""

    PROVIDERS = {
        "google": {
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
            "scopes": ["openid", "email", "profile"],
        },
        "github": {
            "authorization_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "scopes": ["user:email"],
        },
    }

    def __init__(
        self,
        provider: str = "",
        client_id: str = "",
        client_secret: str = "",
        redirect_uri: str = "",
        jwt_secret: str = "",
    ):
        self.provider = provider or os.environ.get("OBSERVECO_OAUTH_PROVIDER", "local")
        self.client_id = client_id or os.environ.get("OBSERVECO_OAUTH_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("OBSERVECO_OAUTH_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.environ.get("OBSERVECO_OAUTH_REDIRECT_URI", "")
        self.jwt_secret = jwt_secret or os.environ.get("OBSERVECO_JWT_SECRET", secrets.token_hex(32))
        self._sessions: dict[str, Session] = {}
        self._pending_states: dict[str, float] = {}  # state -> creation timestamp

    def is_configured(self) -> bool:
        return self.provider != "local" and bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str = "") -> str:
        """Get the OAuth2 authorization URL."""
        if self.provider == "local":
            return ""

        if self.provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {self.provider}")

        config = self.PROVIDERS[self.provider]

        # Generate and store state for CSRF protection
        if not state:
            state = secrets.token_urlsafe(16)
        self._pending_states[state] = time.time()

        import urllib.parse
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config["scopes"]),
            "state": state,
        }

        query = urllib.parse.urlencode(params)
        return f"{config['authorization_url']}?{query}"

    def exchange_code(self, code: str, state: str = "") -> Optional[Session]:
        """Exchange authorization code for access token and create session."""
        if self.provider == "local":
            return self._create_local_session("local@local.local", "Local User")

        if self.provider not in self.PROVIDERS:
            return None

        # Verify state parameter (CSRF protection) — check dict and clean stale entries
        if state:
            # Purge states older than 10 minutes
            cutoff = time.time() - 600
            self._pending_states = {s: t for s, t in self._pending_states.items() if t > cutoff}
            if state not in self._pending_states:
                logger.warning(f"OAuth state not found or expired: {state}")
                return None
            del self._pending_states[state]

        config = self.PROVIDERS[self.provider]

        # Exchange code for token
        token_data = self._exchange_code(config["token_url"], code)
        if not token_data:
            return None

        access_token = token_data.get("access_token", "")
        if not access_token:
            return None

        # Get user info
        user_info = self._get_user_info(config["userinfo_url"], access_token)
        if not user_info:
            return None

        user = User(
            id=user_info.get("id", user_info.get("sub", "")),
            email=user_info.get("email", ""),
            name=user_info.get("name", user_info.get("login", "")),
            avatar_url=user_info.get("picture", user_info.get("avatar_url", "")),
            provider=self.provider,
        )

        return self._create_session(user)

    def _exchange_code(self, token_url: str, code: str) -> Optional[dict]:
        """Exchange authorization code for token."""
        try:
            data = json.dumps({
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }).encode()

            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            req = urllib.request.Request(token_url, data=data, headers=headers)

            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception:
            return None

    def _get_user_info(self, userinfo_url: str, access_token: str) -> Optional[dict]:
        """Get user info from provider."""
        try:
            req = urllib.request.Request(userinfo_url)
            req.add_header("Authorization", f"Bearer {access_token}")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception:
            return None

    def _create_session(self, user: User) -> Session:
        """Create a new session for a user — persisted to SQLite."""
        import secrets as _sec
        token = _sec.token_urlsafe(32)
        now = time.time()
        session = Session(
            token=token,
            user=user,
            expires_at=now + 86400 * 7,  # 7 days
        )
        # Persist to database
        try:
            from observeco.db import Database
            db = Database()
            db.save_session(
                token=token, user_id=user.id, email=user.email,
                name=user.name, avatar_url=user.avatar_url,
                provider=user.provider, expires_at=session.expires_at,
                created_at=now,
            )
        except Exception:
            pass  # Graceful degradation — in-memory fallback still works
        self._sessions[token] = session
        return session

    def _create_local_session(self, email: str, name: str) -> Session:
        """Create a local session (no OAuth)."""
        user = User(id="local", email=email, name=name, provider="local")
        return self._create_session(user)

    def validate_session(self, token: str) -> Optional[Session]:
        """Validate a session token — checks database first, then in-memory."""
        # Try database first (survives restart)
        try:
            from observeco.db import Database
            db = Database()
            row = db.get_session(token)
            if row:
                user = User(
                    id=row["user_id"], email=row["email"], name=row["name"],
                    avatar_url=row.get("avatar_url", ""),
                    provider=row.get("provider", "local"),
                )
                session = Session(
                    token=token, user=user,
                    expires_at=row["expires_at"],
                    created_at=row.get("created_at", time.time()),
                )
                self._sessions[token] = session  # Cache in-memory
                return session
        except Exception:
            pass
        # Fallback to in-memory
        session = self._sessions.get(token)
        if session and not session.is_expired:
            return session
        if session and session.is_expired:
            del self._sessions[token]
        return None

    def destroy_session(self, token: str) -> bool:
        """Destroy a session — removes from both database and memory."""
        try:
            from observeco.db import Database
            db = Database()
            db.delete_session(token)
        except Exception:
            pass
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def get_current_user(self, request_headers: dict) -> Optional[User]:
        """Extract user from request headers (Authorization: Bearer <token>)."""
        auth_header = request_headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        session = self.validate_session(token)
        return session.user if session else None
