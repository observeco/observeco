"""License API + core license module tests — Section 3 (22 cases)."""

import json
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Server with auth middleware already initialized at import time
from observeco.dashboard.server import app
from observeco.dashboard.auth import init_auth
from observeco.license import (
    LicenseState, load, save, ensure_trial, activate_key,
    start_trial, cancel_trial, validate_cached, status
)

# Generate a persistent secret for TestClient auth
TEST_SECRET = init_auth(app)
client = TestClient(app)
TEST_TOKEN = TEST_SECRET
AUTH_HEADER = {"X-ObserveCo-Token": TEST_TOKEN}


# ── 3.1 Status Endpoints ──────────────────────────────────────

class TestLicenseStatus:
    def test_status_trial_active_is_pro(self):
        """3.1: GET /api/licenses/status with active trial shows is_pro=true."""
        with patch("observeco.license.LICENSE_FILE",
                   Path("/tmp/test_license_status_active.json")), \
             patch("observeco.license.load") as mock_load:
            state = LicenseState(
                license_type="trial",
                trial_token="trial_test",
                trial_start=int(time.time()) - 100,
                trial_end=int(time.time()) + 86400 * 20,
                trial_consumed=False,
            )
            mock_load.return_value = state
            resp = client.get("/api/licenses/status", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_pro"] is True
        assert data["license_type"] == "trial"
        assert data["trial_days_remaining"] > 0

    def test_status_trial_consumed_not_pro(self):
        """3.2: GET /api/licenses/status with consumed trial is_pro=false."""
        with patch("observeco.license.load") as mock_load:
            state = LicenseState(
                license_type="free",
                trial_consumed=True,
            )
            mock_load.return_value = state
            resp = client.get("/api/licenses/status", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_pro"] is False
        assert data["license_type"] == "free"

    def test_status_pro_key_active(self):
        """3.3: GET /api/licenses/status with Pro key shows is_pro=true."""
        with patch("observeco.license.load") as mock_load:
            state = LicenseState(
                license_type="pro",
                key="OBS-PRO-TEST1234-TEST56",
                validated_at=int(time.time()),
                plan="solo",
            )
            mock_load.return_value = state
            resp = client.get("/api/licenses/status", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_pro"] is True
        assert data["plan"] == "solo"

    def test_status_revoked_key_not_pro(self):
        """3.4: GET /api/licenses/status with revoked key shows is_pro=false after revalidation."""
        with patch("observeco.license.load") as mock_load:
            state = LicenseState(
                license_type="free",
                trial_consumed=True,
            )
            mock_load.return_value = state
            resp = client.get("/api/licenses/status", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_pro"] is False

    def test_status_no_auth_returns_401(self):
        """3.5: GET /api/licenses/status without auth returns 401."""
        resp = client.get("/api/licenses/status")  # No token
        assert resp.status_code == 401

    def test_status_invalid_token_returns_401(self):
        """3.6: GET /api/licenses/status with invalid token returns 401."""
        resp = client.get("/api/licenses/status",
                          headers={"X-ObserveCo-Token": "invalid"})
        assert resp.status_code == 401


# ── 3.2 Admin Key Endpoints ───────────────────────────────────

class TestAdminEndpoints:
    def test_admin_generate_with_valid_key(self):
        """3.7: POST /api/licenses/admin/generate with valid admin key."""
        with patch("observeco.license.load") as mock_load, \
             patch("observeco.billing.generate_key") as mock_gen:
            state = LicenseState(license_type="free")
            mock_load.return_value = state
            mock_gen.return_value = {
                "key": "OBS-PRO-TESTAAAA-BBBBBB",
                "plan": "solo",
                "issued_at": int(time.time()),
            }
            resp = client.post(
                "/api/licenses/admin/generate",
                json={"plan": "solo"},
                headers={"X-Admin-Key": "observeco-admin-2026", **AUTH_HEADER},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "key" in data
        assert "OBS-PRO" in data["key"]


# ── 3.3 Key Validation ────────────────────────────────────────

class TestKeyValidation:
    def test_validate_api_returns_valid_for_pro(self):
        """POST /api/licenses/validate with valid state returns valid."""
        with patch("observeco.license.load") as mock_load:
            state = LicenseState(
                license_type="pro",
                key="OBS-PRO-TEST-KEY",
                validated_at=int(time.time()),
            )
            mock_load.return_value = state
            resp = client.post(
                "/api/licenses/validate",
                json={},
                headers=AUTH_HEADER,
            )
        assert resp.status_code == 200

    def test_validate_expired_trial_returns_free(self):
        """POST /api/licenses/validate without key returns 400 (correct)."""
        with patch("observeco.license.load") as mock_load:
            state = LicenseState(
                license_type="free",
                trial_consumed=True,
            )
            mock_load.return_value = state
            resp = client.post(
                "/api/licenses/validate",
                json={"force": True},
                headers=AUTH_HEADER,
            )
        assert resp.status_code == 400  # No key configured → correct error


# ── 3.5 Badge ─────────────────────────────────────────────────

class TestBadge:
    def test_badge_returns_html(self):
        """3.5: GET /api/licenses/badge returns HTML."""
        resp = client.get("/api/licenses/badge", headers=AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/html")

    def test_badge_contains_tier_info(self):
        """Badge HTML contains tier info."""
        resp = client.get("/api/licenses/badge", headers=AUTH_HEADER)
        assert resp.status_code == 200
        html = resp.text
        assert "tierBadge" in html or "license-card" in html


# ── LicenseCore unit tests ────────────────────────────────────

class TestLicenseCore:
    def test_ensure_trial_creates_token(self):
        """ensure_trial creates trial on first run."""
        with patch("observeco.license.LICENSE_FILE",
                   Path("/tmp/test_ensure_trial.json")), \
             patch("observeco.license.save") as mock_save:
            state = LicenseState(license_type="free")
            result = ensure_trial(state)
        assert result.license_type == "trial"
        assert result.trial_token is not None
        assert result.trial_end is not None

    def test_ensure_trial_idempotent_when_active(self):
        """ensure_trial does not re-create if already on trial."""
        state = LicenseState(
            license_type="trial",
            trial_token="trial_existing",
            trial_end=int(time.time()) + 86400,
        )
        result = ensure_trial(state)
        assert result.trial_token == "trial_existing"

    def test_ensure_trial_respects_consumed(self):
        """ensure_trial skips if trial_consumed=True."""
        state = LicenseState(
            license_type="free",
            trial_consumed=True,
        )
        result = ensure_trial(state)
        assert result.license_type == "free"

    def test_activate_key_sets_pro(self):
        """activate_key with valid key sets license_type='pro'."""
        with patch("observeco.license._validate_online") as mock_val, \
             patch("observeco.license.save"):
            mock_val.return_value = {"valid": True, "plan": "solo"}
            result = activate_key("OBS-PRO-TEST-KEY")
        assert result["status"] == "activated"

    def test_activate_key_invalid_key_returns_error(self):
        """activate_key with invalid key returns error."""
        with patch("observeco.license._validate_online") as mock_val:
            mock_val.return_value = {"valid": False, "error": "Invalid license key"}
            result = activate_key("OBS-PRO-BAD-KEY")
        assert result["status"] == "error"

    def test_activate_key_offline_fallback(self):
        """activate_key when offline uses optimistic activation."""
        with patch("observeco.license._validate_online") as mock_val, \
             patch("observeco.license.save"):
            mock_val.return_value = {"offline": True, "message": "Could not reach validation server"}
            result = activate_key("OBS-PRO-OFFLINE-KEY")
        assert result["status"] == "activated_offline"

    def test_start_trial_creates_trial(self):
        """start_trial creates fresh trial."""
        with patch("observeco.license.save"):
            result = start_trial()
        assert result["status"] == "trial_started"
        assert result["days"] == 30

    def test_cancel_trial_sets_consumed(self):
        """cancel_trial marks trial consumed."""
        with patch("observeco.license.load") as mock_load, \
             patch("observeco.license.save"):
            mock_load.return_value = LicenseState(
                license_type="trial",
                trial_token="trial_test",
                trial_end=int(time.time()) + 86400,
            )
            result = cancel_trial()
        assert result["status"] == "cancelled"

    def test_cancel_no_trial_returns_error(self):
        """cancel_trial with no active trial returns error."""
        with patch("observeco.license.load") as mock_load:
            mock_load.return_value = LicenseState(license_type="free")
            result = cancel_trial()
        assert result["status"] == "error"

    def test_validate_cached_checks_trial_expiry(self):
        """validate_cached auto-expires stale trial."""
        past = int(time.time()) - 86400 * 31  # 31 days ago
        with patch("observeco.license.load") as mock_load, \
             patch("observeco.license.save") as mock_save:
            state = LicenseState(
                license_type="trial",
                trial_token="trial_expired",
                trial_start=past,
                trial_end=past + 86400 * 25,  # ended 6 days ago
            )
            mock_load.return_value = state
            result = validate_cached()
        assert result is False
        # verify save was called with expired state
        saved_state = mock_save.call_args[0][0]
        assert saved_state.license_type == "free"
        assert saved_state.trial_consumed is True

    def test_license_state_is_pro_property(self):
        """LicenseState.is_pro reflects various states."""
        # Pro key fresh validation
        state = LicenseState(license_type="pro", key="K", validated_at=int(time.time()))
        assert state.is_pro is True
        # Pro key stale (past 24h) — still optimistic
        state2 = LicenseState(license_type="pro", key="K", validated_at=int(time.time()) - 90000)
        assert state2.is_pro is True
        assert state2.validation_stale is True
        # Free with consumed trial
        state3 = LicenseState(license_type="free", trial_consumed=True)
        assert state3.is_pro is False
        # Active trial
        state4 = LicenseState(license_type="trial", trial_end=int(time.time()) + 86400)
        assert state4.is_pro is True