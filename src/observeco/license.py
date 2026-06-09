"""Local license/trial token manager for ObserveCo Pro.

Reads/writes ~/.observeco/license.json.
Supports:
- Trial tokens generated on explicit "Start Free Trial" or Pro feature access (works offline, 30-day)
- Pro license key entry + online validation (cached 24h)
- Fallback to cached validation when offline
- Fresh install starts on Free tier; trial only starts on explicit action
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
from dataclasses import dataclass

from observeco.dirs import get_data_dir

CONFIG_DIR = get_data_dir()
LICENSE_FILE = CONFIG_DIR / "license.json"
CACHE_TTL = 86400  # 24h validation cache

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class LicenseState:
    license_type: str = "free"       # "free" | "trial" | "pro"
    key: str | None = None           # Pro license key (lic_xxx)
    trial_token: str | None = None   # Auto-generated trial token
    trial_start: int | None = None   # Unix ts
    trial_end: int | None = None     # Unix ts
    trial_consumed: bool = False     # True if trial was cancelled or expired
    past_due_at: int | None = None   # Unix ts when trial entered grace period
    validated_at: int | None = None  # Last successful online validation
    expires_at: int | None = None    # Unix ts when pro key expires (from CRM)
    customer_email: str | None = None
    plan: str | None = None          # "solo" | "team" | None
    provisioning_source: str | None = None  # "stripe" | "admin_key" | None
    first_run_at: int | None = None  # Unix ts of very first dashboard launch

    GRACE_PERIOD_SECS = 3 * 86400  # 3 days
    NEW_USER_LLM_GRACE_DAYS = 30   # Tier 1 (deep) LLM always-on for new users

    @property
    def is_trial_active(self) -> bool:
        if self.license_type != "trial" or not self.trial_end:
            return False
        return int(time.time()) < self.trial_end

    @property
    def is_in_grace(self) -> bool:
        """True if trial expired but within 3-day grace period."""
        if self.license_type != "trial" or not self.trial_end or not self.past_due_at:
            return False
        if int(time.time()) < self.trial_end:
            return False  # not yet expired
        return int(time.time()) - self.past_due_at < self.GRACE_PERIOD_SECS

    @property
    def is_pro(self) -> bool:
        if self.license_type == "pro" and self.key:
            if self.expires_at and int(time.time()) >= self.expires_at:
                return False  # key expired
            if self.validated_at:
                # Validation cache is fresh — trust it
                if int(time.time()) - self.validated_at < CACHE_TTL:
                    return True
            # No fresh validation — trust key presence but flag stale
            return True
        if self.is_trial_active:
            return True
        if self.is_in_grace:
            return True  # grace period still counts as Pro
        return False

    @property
    def remains_days(self) -> int:
        if self.license_type == "trial" and self.trial_end:
            remaining = self.trial_end - int(time.time())
            return max(0, remaining // 86400)
        return 0

    @property
    def is_new_user_llm_grace(self) -> bool:
        """True if user is within the first 30 days (Tier 1 deep LLM always-on)."""
        if not self.first_run_at:
            return True  # hasn't been set yet — we're in setup, count as grace
        elapsed = int(time.time()) - self.first_run_at
        return elapsed < self.NEW_USER_LLM_GRACE_DAYS * 86400

    @property
    def new_user_grace_days_remaining(self) -> int:
        """Days remaining in the 30-day new-user LLM grace period."""
        if not self.first_run_at:
            return self.NEW_USER_LLM_GRACE_DAYS
        elapsed = int(time.time()) - self.first_run_at
        remaining = self.NEW_USER_LLM_GRACE_DAYS - (elapsed // 86400)
        return max(0, remaining)

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
            "past_due_at": self.past_due_at,
            "is_in_grace": self.is_in_grace,
            "validation_stale": self.validation_stale,
            "plan": self.plan,
            "provisioning_source": self.provisioning_source,
            "customer_email": self.customer_email,
            "expires_at": self.expires_at,
            "first_run_at": self.first_run_at,
            "new_user_llm_grace": self.is_new_user_llm_grace,
            "new_user_grace_days_remaining": self.new_user_grace_days_remaining,
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
        past_due_at=raw.get("past_due_at"),
        validated_at=raw.get("validated_at"),
        expires_at=raw.get("expires_at"),
        customer_email=raw.get("customer_email"),
        plan=raw.get("plan"),
        provisioning_source=raw.get("provisioning_source"),
        first_run_at=raw.get("first_run_at"),
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
        "past_due_at": state.past_due_at,
        "validated_at": state.validated_at,
        "expires_at": state.expires_at,
        "customer_email": state.customer_email,
        "plan": state.plan,
        "provisioning_source": state.provisioning_source,
        "first_run_at": state.first_run_at,
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


def _valid_key_format(key: str) -> bool:
    """Check if key matches OBS-PRO-XXXXXXXX-XXXX format."""
    import re
    return bool(re.match(r"^OBS-PRO-[A-F0-9]{8}-[A-F0-9]{6}$", key.strip()))


def activate_key(key: str, email: str = "", plan: str = "solo") -> dict:
    """Activate a Pro license key.

    Validates key format (OBS-PRO-XXXXXXXX-XXXX) before attempting
    online validation. Junk keys are rejected immediately.
    Falls back to optimistic activation if offline.
    """
    import re
    key = key.strip()
    if not _valid_key_format(key):
        return {"status": "error",
                "message": "Invalid key format. Expected format: OBS-PRO-XXXXXXXX-XXXX"}

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
        state.provisioning_source = result.get("source", "admin_key")
        if result.get("email"):
            state.customer_email = result["email"]
        if result.get("plan"):
            state.plan = result["plan"]
        if result.get("expires_at"):
            try:
                exp = result["expires_at"]
                if isinstance(exp, str):
                    from datetime import datetime, timezone
                    state.expires_at = int(datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp())
                elif isinstance(exp, (int, float)):
                    state.expires_at = int(exp)
            except (ValueError, TypeError):
                state.expires_at = None
        # If no expires_at from CRM, check if trial_ends_at means perpetual
        elif result.get("status") == "active" and not result.get("trial_ends_at"):
            state.expires_at = None  # perpetual
        save(state)
        return {"status": "activated", "plan": state.plan or plan, "expires_at": state.expires_at}

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


def _validate_online(key: str, machine_id: str = "") -> dict:
    """Validate a Pro license key.

    Priority:
    1. Local admin key store (works offline, for keys you generate)
    2. CRM API (Vercel, when Supabase is live)
    Falls back to optimistic activation if both unavailable.
    """
    # First check local admin key store
    from observeco.billing import validate_admin_key
    local = validate_admin_key(key)
    if local.get("valid"):
        # Mark who activated it
        from observeco.billing import _load_config, _save_config
        cfg = _load_config()
        if cfg.issued_keys and key in cfg.issued_keys:
            cfg.issued_keys[key]["activated_by"] = "dashboard_user"
            cfg.issued_keys[key]["activated_at"] = int(time.time())
            _save_config(cfg)
        return local

    # Fall back to CRM API — validate AND sync instance info
    import urllib.error
    import urllib.request

    url = os.environ.get(
        "OBSERVECO_LICENSE_API",
        "https://observeco-license-crm.vercel.app/api/licenses/validate"
    )
    # Include email if available in current license state
    current = load()
    payload = json.dumps({
        "license_key": key,
        "email": current.customer_email or "",
        "machine_id": machine_id or _get_machine_id(),
    }).encode()
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


def _get_machine_id() -> str:
    """Return a stable machine identifier for CRM tracking."""
    import hashlib
    import platform
    raw = "-".join([
        platform.node() or "unknown",
        platform.machine() or "unknown",
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _revalidate_key(state: LicenseState | None = None) -> None:
    """Re-validate a pro key against CRM. Updates local state on change.

    Called when validation cache is stale (>24h). Will silently:
    - Downgrade to free if CRM says invalid/expired/cancelled
    - Update expires_at if CRM returns a new value
    - Refresh validated_at on success
    """
    if state is None:
        state = load()
    if not state.key or state.license_type != "pro":
        return  # nothing to revalidate

    result = _validate_online(state.key)
    if result.get("offline"):
        logger.info("License revalidation skipped — offline")
        return  # keep cached state

    if result.get("valid"):
        # CRM says it's still valid — refresh cache and expiry
        state.validated_at = int(time.time())
        if result.get("expires_at"):
            try:
                exp = result["expires_at"]
                if isinstance(exp, str):
                    from datetime import datetime, timezone
                    state.expires_at = int(datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp())
                elif isinstance(exp, (int, float)):
                    state.expires_at = int(exp)
            except (ValueError, TypeError):
                pass
        if result.get("email"):
            state.customer_email = result["email"]
        save(state)
        logger.info("License revalidated — valid until %s", state.expires_at)
    else:
        # CRM revoked or expired. Downgrade to free.
        logger.warning("License revalidation failed — key no longer valid. Downgrading to free.")
        state.license_type = "free"
        state.key = None
        state.validated_at = None
        state.expires_at = None
        state.past_due_at = None
        save(state)


def start_trial() -> dict:
    """Start or restart the 30-day trial.

    Returns error if trial was previously consumed (trial hardening).
    Syncs the trial record to CRM when reachable.
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

    # Sync trial to CRM (fire-and-forget — never fail local operation)
    _sync_trial_to_crm(state.trial_token, state.customer_email or "", state.trial_end)

    return {
        "status": "trial_started",
        "trial_end": state.trial_end,
        "days": 30,
    }


def _sync_trial_to_crm(trial_token: str, email: str, trial_end: int) -> None:
    """Fire-and-forget sync of trial record to CRM."""
    import urllib.error
    import urllib.request

    url = os.environ.get(
        "OBSERVECO_LICENSE_API_BASE",
        "https://observeco-license-crm.vercel.app"
    ).rstrip("/") + "/api/commercial/trials/start"

    payload = json.dumps({
        "email": email,
        "name": "",
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            logger.info("Trial synced to CRM: %s", data.get("license_key", "unknown"))
    except Exception:
        logger.warning("Could not sync trial to CRM (non-fatal)")


def _sync_cancel_to_crm(email: str) -> None:
    """Fire-and-forget sync of trial cancellation to CRM."""
    import urllib.error
    import urllib.request

    if not email:
        logger.info("No email to sync cancellation to CRM")
        return

    url = os.environ.get(
        "OBSERVECO_LICENSE_API_BASE",
        "https://observeco-license-crm.vercel.app"
    ).rstrip("/") + "/api/commercial/trials/cancel"

    payload = json.dumps({
        "email": email,
        "name": "",
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            logger.info("Cancellation synced to CRM: %s", data.get("status", "unknown"))
    except Exception:
        logger.warning("Could not sync cancellation to CRM (non-fatal)")


def cancel_trial() -> dict:
    """Cancel the current trial. Sets license_type back to free and marks trial consumed.

    Data is preserved. Only Pro features are locked. The user can resubscribe
    via Stripe Checkout at any time (Stripe enforces single-trial-per-customer).
    Also updates billing.json simulated customer records to reflect cancellation.
    Syncs cancellation to CRM when reachable.
    """
    from observeco.billing import _load_config as _load_billing, _save_config as _save_billing

    state = load()
    if state.license_type != "trial":
        return {"status": "error", "message": "No active trial to cancel"}

    email = state.customer_email or ""

    state.license_type = "free"
    state.trial_consumed = True
    state.trial_token = None
    state.trial_start = None
    state.trial_end = None
    save(state)

    # Also update billing.json simulated customers to match
    try:
        billing_cfg = _load_billing()
        updated = False
        for c in billing_cfg.customers:
            if c.get("status") == "trialing" and c.get("session_id", "").startswith("cs_demo_"):
                c["status"] = "cancelled"
                updated = True
        if updated:
            _save_billing(billing_cfg)
    except Exception:
        logger.warning("Could not update billing.json simulated customers", exc_info=True)

    # Sync cancellation to CRM (fire-and-forget — never fail local operation)
    _sync_cancel_to_crm(email)

    return {
        "status": "cancelled",
        "message": "Trial cancelled. Pro features locked. Your data is safe — subscribe anytime to unlock them.",
    }


def deactivate_license() -> dict:
    """Remove the current license key and downgrade to Free.

    Does NOT touch trial data or billing.json — only clears the local
    license key and resets to free state. User can activate a new key later.
    """
    state = load()
    if state.license_type != "pro" or not state.key:
        return {"status": "error", "message": "No active license key to deactivate"}

    state.license_type = "free"
    state.key = None
    state.validated_at = None
    state.expires_at = None
    state.plan = None
    state.provisioning_source = None
    save(state)

    return {
        "status": "deactivated",
        "message": "License key removed. Pro features locked. Your data is preserved. You can activate a new key at any time.",
    }


def validate_cached() -> bool:
    """Check if the current license is valid, using cache.

    Called on startup. Returns True if Pro features should be enabled.

    Also checks for revoked key scenario — if validation_stale and on next
    access we detect revocation, downgrade is handled in require_pro().
    Enters 3-day grace period when trial expires before auto-consuming.
    Also auto-expires stale trials after grace period ends.
    Sets first_run_at on first-ever startup (used for new-user LLM grace).
    If a pro key is cached and validation is stale, re-validates against CRM.
    """
    state = load()

    # Track first run for new-user LLM grace period
    if state.first_run_at is None:
        state.first_run_at = int(time.time())
        save(state)

    # Pro key with stale cache — attempt online revalidation
    if state.license_type == "pro" and state.key and state.validation_stale:
        _revalidate_key(state)

    # Reload state after possible revalidation
    state = load()
    if state.is_pro:
        return True
    # Check if grace period has expired — consume the trial
    if state.is_in_grace:
        assert state.past_due_at is not None  # guaranteed by is_in_grace
        if int(time.time()) - state.past_due_at >= LicenseState.GRACE_PERIOD_SECS:
            state.license_type = "free"
            state.trial_consumed = True
            state.trial_token = None
            state.past_due_at = None
            save(state)
            return False
        return True  # still in grace
    # Trial has ended — enter grace period
    if state.license_type == "trial" and state.trial_end:
        now = int(time.time())
        if now >= state.trial_end:
            if state.past_due_at is None:
                # Check if trial ended so long ago that grace would already be expired
                if now - state.trial_end >= LicenseState.GRACE_PERIOD_SECS:
                    state.license_type = "free"
                    state.trial_consumed = True
                    state.trial_token = None
                    save(state)
                    return False
                state.past_due_at = now
                save(state)
            return True  # first time entering grace — still valid
    # No license, no trial — stay Free. Trial starts on Pro feature access
    # or explicit "Start Free Trial" click. See commercial-scope.md §7.
    return False


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
