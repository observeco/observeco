"""Local license/trial token manager for ObserveCo Pro.

Reads/writes ~/.observeco/license.json.
Supports:
- Auto-generated trial tokens (works offline, 30-day)
- Pro license key entry + online validation (cached 24h)
- Fallback to cached validation when offline
- Startup auto-detect: free → trial if no license exists
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from observeco.dirs import get_data_dir

CONFIG_DIR = get_data_dir()
LICENSE_FILE = CONFIG_DIR / "license.json"
CACHE_TTL = 86400  # 24h validation cache


@dataclass
class LicenseState:
    license_type: str = "free"       # "free" | "trial" | "pro"
    key: str | None = None           # Pro license key (lic_xxx)
    trial_token: str | None = None   # Auto-generated trial token
    trial_start: int | None = None   # Unix ts
    trial_end: int | None = None     # Unix ts
    trial_consumed: bool = False     # True if trial was cancelled or expired
    validated_at: int | None = None  # Last successful online validation
    customer_email: str | None = None
    plan: str | None = None          # "solo" | "team" | None

    @property
    def is_trial_active(self) -> bool:
        if self.license_type != "trial" or not self.trial_end:
            return False
        return int(time.time()) < self.trial_end

    @property
    def is_pro(self) -> bool:
        if self.license_type == "pro" and self.key:
            if self.validated_at:
                # Validation cache is fresh — trust it
                if int(time.time()) - self.validated_at < CACHE_TTL:
                    return True
            # No fresh validation — trust key presence but flag stale
            return True
        return self.is_trial_active  # trial counts as pro for feature access

    @property
    def remains_days(self) -> int:
        if self.license_type == "trial" and self.trial_end:
            remaining = self.trial_end - int(time.time())
            return max(0, remaining // 86400)
        return 0

    @property
    def validation_stale(self) -> bool:
        if not self.validated_at or not self.key:
            return False
        return int(time.time()) - self.validated_at >= CACHE_TTL

    def to_dict(self) -> dict:
        return {
            "license_type": self.license_type,
            "is_pro": self.is_pro,
            "has_key": bool(self.key),
            "has_trial": bool(self.trial_token),
            "trial_days_remaining": self.remains_days,
            "trial_end": self.trial_end,
            "trial_consumed": self.trial_consumed,
            "validation_stale": self.validation_stale,
            "plan": self.plan,
            "customer_email": self.customer_email,
        }


def _load_raw() -> dict:
    """Load raw license.json or return empty dict."""
    if LICENSE_FILE.exists():
        try:
            return json.loads(LICENSE_FILE.read_text())
        except (json.JSONDecodeError, PermissionError, OSError):
            pass
    return {}


def _save_raw(data: dict) -> None:
    """Write license.json atomically."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LICENSE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(LICENSE_FILE)


def load() -> LicenseState:
    """Load current license state from disk."""
    raw = _load_raw()
    return LicenseState(
        license_type=raw.get("license_type", "free"),
        key=raw.get("key"),
        trial_token=raw.get("trial_token"),
        trial_start=raw.get("trial_start"),
        trial_end=raw.get("trial_end"),
        trial_consumed=raw.get("trial_consumed", False),
        validated_at=raw.get("validated_at"),
        customer_email=raw.get("customer_email"),
        plan=raw.get("plan"),
    )


def save(state: LicenseState) -> None:
    """Persist license state to disk."""
    _save_raw({
        "license_type": state.license_type,
        "key": state.key,
        "trial_token": state.trial_token,
        "trial_start": state.trial_start,
        "trial_end": state.trial_end,
        "trial_consumed": state.trial_consumed,
        "validated_at": state.validated_at,
        "customer_email": state.customer_email,
        "plan": state.plan,
    })


def ensure_trial(state: LicenseState | None = None) -> LicenseState:
    """Auto-generate a trial token on first run if no license exists.

    Idempotent — only generates if no trial_token, no key, and type is 'free'.
    Will NOT generate a new trial if trial_consumed is True (trial hardening).
    """
    if state is None:
        state = load()
    if state.license_type != "free":
        return state
    if state.key or state.trial_token:
        return state
    # Trial hardening — skip if trial was previously consumed (cancelled/expired)
    if state.trial_consumed:
        return state

    now = int(time.time())
    state.license_type = "trial"
    state.trial_token = "trial_" + secrets.token_hex(16)
    state.trial_start = now
    state.trial_end = now + 30 * 86400  # 30 days
    state.trial_consumed = False
    save(state)
    return state


def activate_key(key: str, email: str = "", plan: str = "solo") -> dict:
    """Activate a Pro license key.

    Performs online validation (POST to /api/licenses/validate).
    Falls back to optimistic activation if offline.
    """
    state = load()

    if state.key == key and state.license_type == "pro":
        # Same key already active — refresh validation
        pass

    # Attempt online validation
    result = _validate_online(key)
    if result.get("valid"):
        state.license_type = "pro"
        state.key = key
        state.validated_at = int(time.time())
        if result.get("email"):
            state.customer_email = result["email"]
        if result.get("plan"):
            state.plan = result["plan"]
        save(state)
        return {"status": "activated", "plan": state.plan or plan}

    # Online validation failed or offline
    if result.get("offline"):
        # Optimistic activation — cache for revalidation
        state.license_type = "pro"
        state.key = key
        state.validated_at = int(time.time())
        state.plan = plan
        if email:
            state.customer_email = email
        save(state)
        return {"status": "activated_offline", "plan": plan,
                "message": "License saved. Will validate when online."}

    return {"status": "error", "message": result.get("error", "Invalid license key")}


def _validate_online(key: str) -> dict:
    """POST to the ObserveCo validation API."""
    import urllib.request
    import urllib.error

    url = os.environ.get(
        "OBSERVECO_LICENSE_API",
        "https://observeco-license-crm.vercel.app/api/licenses/validate"
    )
    payload = json.dumps({"license_key": key}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data
    except urllib.error.URLError:
        return {"offline": True, "message": "Could not reach validation server"}
    except (json.JSONDecodeError, OSError) as e:
        return {"offline": True, "message": str(e)}


def start_trial() -> dict:
    """Start or restart the 30-day trial.

    Returns error if trial was previously consumed (trial hardening).
    """
    state = load()
    if state.trial_consumed:
        return {
            "status": "error",
            "message": "Trial already used. Trial is a one-time offer. Subscribe via Stripe to unlock Pro features.",
        }
    now = int(time.time())
    state.license_type = "trial"
    state.trial_token = "trial_" + secrets.token_hex(16)
    state.trial_start = now
    state.trial_end = now + 30 * 86400
    state.trial_consumed = False
    save(state)
    return {
        "status": "trial_started",
        "trial_end": state.trial_end,
        "days": 30,
    }


def cancel_trial() -> dict:
    """Cancel the current trial. Sets license_type back to free and marks trial consumed.

    Data is preserved. Only Pro features are locked. The user can resubscribe
    via Stripe Checkout at any time (Stripe enforces single-trial-per-customer).
    """
    state = load()
    if state.license_type != "trial":
        return {"status": "error", "message": "No active trial to cancel"}
    state.license_type = "free"
    state.trial_consumed = True
    state.trial_token = None
    state.trial_start = None
    state.trial_end = None
    save(state)
    return {
        "status": "cancelled",
        "message": "Trial cancelled. Pro features locked. Your data is safe — subscribe anytime to unlock them.",
    }


def validate_cached() -> bool:
    """Check if the current license is valid, using cache.

    Called on startup. Returns True if Pro features should be enabled.
    Also auto-expires stale trials (sets trial_consumed after expiry).
    """
    state = load()
    if state.is_pro:
        return True
    # Auto-expire trial that has ended
    if state.license_type == "trial" and state.trial_end:
        if int(time.time()) >= state.trial_end:
            state.license_type = "free"
            state.trial_consumed = True
            state.trial_token = None
            save(state)
            return False
    # No license at all — start trial
    state = ensure_trial(state)
    return state.is_pro


def status() -> dict:
    """Public status endpoint payload."""
    state = load()
    return state.to_dict()


def require_pro() -> bool:
    """Check if Pro features are unlocked. Returns True if Pro or trial active.
    
    Use this to gate backend endpoints and frontend sections.
    """
    state = load()
    return state.is_pro
