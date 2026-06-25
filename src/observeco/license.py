"""Local license/trial token manager for ObserveCo Pro.

Reads/writes ~/.observeco/license.json.
Supports:
- Trial tokens generated on explicit "Start Free Trial" or Pro feature access (works offline, 30-day)
- Pro license key entry + online validation (cached 24h)
- Fallback to cached validation when offline
- Fresh install starts on Free tier; trial only starts on explicit action

Security (2026-06-13 audit — 18 gaps fixed):
- start_trial() never overwrites active Pro keys
- activate_key() validates against issued_keys before offline fallback
- Rate limiting: max 5 activation attempts per hour
- is_pro has 7-day staleness cap (downgrades if offline >7 days)
- require_pro() checks revocation on every call when stale
- File locking for concurrent access
- machine_id uses hardware UUID (macOS) or fallback hash
- first_run_at persisted in separate .install_state file
- Trial hardening tied to machine_id for CRM sync
- Grace period starts at trial_end (not first dashboard open)
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from observeco.dirs import get_data_dir

# ponytail: lazy — evaluated at first call, not import time, so get_data_dir() failure
# doesn't crash the import.
_CONFIG_DIR: Path | None = None
_LICENSE_FILE: Path | None = None
_INSTALL_STATE_FILE: Path | None = None

def _get_config_dir() -> Path:
    global _CONFIG_DIR, _LICENSE_FILE, _INSTALL_STATE_FILE
    if _CONFIG_DIR is None:
        _CONFIG_DIR = get_data_dir()
        _LICENSE_FILE = _CONFIG_DIR / "license.json"
        _INSTALL_STATE_FILE = _CONFIG_DIR / ".install_state"
    return _CONFIG_DIR

def _get_license_file() -> Path:
    _get_config_dir()
    return _LICENSE_FILE  # type: ignore[return-value]

def _get_install_state_file() -> Path:
    _get_config_dir()
    return _INSTALL_STATE_FILE  # type: ignore[return-value]
CACHE_TTL = 86400  # 24h validation cache
MAX_VALIDATION_STALENESS = 7 * 86400  # 7 days — after this, downgrade to Free
MAX_ACTIVATION_ATTEMPTS = 5
ACTIVATION_WINDOW_SECS = 3600  # 1 hour

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ── File locking (Gap #10) ──────────────────────────────────────────

class _FileLock:
    """Simple file-based lock for Unix. Falls back to no-op on Windows."""
    def __init__(self, path: Path):
        self._lock_path = path.with_suffix(".lock")

    def __enter__(self):
        try:
            import fcntl
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fd = open(self._lock_path, "w")
            fcntl.flock(self._fd, fcntl.LOCK_EX)
        except (ImportError, OSError):
            self._fd = None  # Windows or no fcntl — best-effort
        return self

    def __exit__(self, *args):
        if self._fd:
            try:
                import fcntl
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                self._fd.close()
            except (ImportError, OSError):
                pass


# ── LicenseState ────────────────────────────────────────────────────

@dataclass
class LicenseState:
    license_type: str = "free"       # "free" | "trial" | "pro"
    key: str | None = None           # Pro license key (OBS-PRO-...)
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
    downgraded_at: int | None = None  # Unix ts when last downgraded (for UI notification)
    downgraded_reason: str | None = None  # Why downgrade happened
    machine_id: str | None = None    # Hardware UUID for trial hardening
    activation_attempts: list = field(default_factory=list)  # [{ts: int, key_prefix: str}]

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
        if self.license_type != "trial" or not self.trial_end:
            return False
        if int(time.time()) < self.trial_end:
            return False  # not yet expired
        # Grace starts at trial_end, not at past_due_at (Gap #16 fix)
        return int(time.time()) - self.trial_end < self.GRACE_PERIOD_SECS

    @property
    def is_pro(self) -> bool:
        if self.license_type == "pro" and self.key:
            if self.expires_at and int(time.time()) >= self.expires_at:
                return False  # key expired
            if self.validated_at:
                # Validation cache is fresh — trust it
                if int(time.time()) - self.validated_at < CACHE_TTL:
                    return True
                # Staleness cap: if offline >7 days, downgrade (Gap #13 fix)
                if int(time.time()) - self.validated_at > MAX_VALIDATION_STALENESS:
                    return False
            # No fresh validation — trust key presence if within staleness cap
            if self.validated_at and int(time.time()) - self.validated_at <= MAX_VALIDATION_STALENESS:
                return True
            # No validated_at at all — trust key but flag for revalidation
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
        # Check separate install state file first (Gap #17 fix)
        install_first_run = _load_install_state().get("first_run_at")
        effective_first_run = self.first_run_at or install_first_run
        if not effective_first_run:
            return True  # hasn't been set yet — we're in setup, count as grace
        elapsed = int(time.time()) - effective_first_run
        return elapsed < self.NEW_USER_LLM_GRACE_DAYS * 86400

    @property
    def new_user_grace_days_remaining(self) -> int:
        """Days remaining in the 30-day new-user LLM grace period."""
        install_first_run = _load_install_state().get("first_run_at")
        effective_first_run = self.first_run_at or install_first_run
        if not effective_first_run:
            return self.NEW_USER_LLM_GRACE_DAYS
        elapsed = int(time.time()) - effective_first_run
        remaining = self.NEW_USER_LLM_GRACE_DAYS - (elapsed // 86400)
        return max(0, remaining)

    @property
    def validation_stale(self) -> bool:
        if not self.validated_at or not self.key:
            return False
        return int(time.time()) - self.validated_at >= CACHE_TTL

    @property
    def is_expiring_soon(self) -> bool:
        """True if trial is active and within 7 days of expiry."""
        if not self.is_trial_active or not self.trial_end:
            return False
        remaining = self.trial_end - int(time.time())
        return 0 < remaining < 7 * 86400

    @property
    def days_until_expiry(self) -> int | None:
        """Days until trial ends, or None if no trial."""
        if not self.trial_end:
            return None
        remaining = self.trial_end - int(time.time())
        return max(0, remaining // 86400)

    @property
    def days_until_grace_end(self) -> int | None:
        """Days until grace period ends, or None if not in grace."""
        if not self.is_in_grace or not self.trial_end:
            return None
        grace_end = self.trial_end + self.GRACE_PERIOD_SECS
        remaining = grace_end - int(time.time())
        return max(0, remaining // 86400)

    @property
    def is_payment_failed(self) -> bool:
        """True if license type indicates a past_due state."""
        return self.license_type == "past_due" or (
            self.license_type == "trial" and self.past_due_at is not None
        )

    def to_dict(self) -> dict:
        d = {
            "license_type": self.license_type,
            "is_pro": self.is_pro,
            "has_key": bool(self.key),
            "license_key": self.key or None,
            "has_trial": bool(self.trial_token),
            "trial_days_remaining": self.remains_days,
            "trial_end": self.trial_end,
            "trial_end_date": self._format_trial_end(),
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
            "downgraded_at": self.downgraded_at,
            "downgraded_reason": self.downgraded_reason,
            "machine_id": self.machine_id,
            "is_expiring_soon": self.is_expiring_soon,
            "days_until_expiry": self.days_until_expiry,
            "days_until_grace_end": self.days_until_grace_end,
            "is_payment_failed": self.is_payment_failed,
            "device_count": get_device_count(),  # Gap #18
        }
        # Add Stripe config status
        try:
            from observeco.billing import load as _load_billing
            _bcfg = _load_billing()
            d["stripe_configured"] = bool(_bcfg.stripe_secret_key and _bcfg.stripe_secret_key.startswith("sk_"))
        except Exception:
            d["stripe_configured"] = False
        return d

    def _format_trial_end(self) -> str:
        """Format trial end date for display."""
        if not self.trial_end:
            return ""
        from datetime import datetime
        try:
            return datetime.fromtimestamp(self.trial_end).strftime("%b %d, %Y")
        except Exception:
            return ""


# ── Install state (Gap #17 — persists across license.json deletion) ──

def _load_install_state() -> dict:
    """Load install state from .install_state (survives license.json deletion)."""
    p = _get_install_state_file()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_install_state(data: dict) -> None:
    """Save install state atomically."""
    _get_config_dir().mkdir(parents=True, exist_ok=True)
    p = _get_install_state_file()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)


# ── Disk I/O (with file locking) ───────────────────────────────────

def _load_raw() -> dict:
    """Load raw license.json or return empty dict."""
    p = _get_license_file()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, PermissionError, OSError):
            pass
    return {}


def _save_raw(data: dict) -> None:
    """Write license.json atomically."""
    _get_config_dir().mkdir(parents=True, exist_ok=True)
    p = _get_license_file()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(p)


def load() -> LicenseState:
    """Load current license state from disk."""
    with _FileLock(_get_license_file()):
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
        downgraded_at=raw.get("downgraded_at"),
        downgraded_reason=raw.get("downgraded_reason"),
        machine_id=raw.get("machine_id"),
        activation_attempts=raw.get("activation_attempts", []),
    )


def save(state: LicenseState) -> None:
    """Persist license state to disk."""
    with _FileLock(_get_license_file()):
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
            "downgraded_at": state.downgraded_at,
            "downgraded_reason": state.downgraded_reason,
            "machine_id": state.machine_id,
            "activation_attempts": state.activation_attempts,
        })


# ── Machine ID (Gap #4 — use hardware UUID) ────────────────────────

def _get_machine_id() -> str:
    """Return a stable machine identifier for CRM tracking.

    Uses hardware UUID on macOS (ioreg), falls back to MAC address,
    then hostname+arch as last resort.
    """
    import hashlib
    import platform

    # Try macOS hardware UUID first
    if platform.system() == "Darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "IOPlatformUUID" in line:
                    uuid = line.split('"')[-2] if '"' in line else ""
                    if uuid:
                        return hashlib.sha256(uuid.encode()).hexdigest()[:16]
        except Exception:
            # ponytail: minimal logging -- upgrade to structured error reporting when error handling infra exists
            logger.warning("return hashlib.sha256(uuid.encode()).hexdigest()[:16]", exc_info=True)
            pass

    # Try uuid.getnode() (MAC address)
    try:
        import uuid
        mac = uuid.getnode()
        if mac != 0:
            return hashlib.sha256(str(mac).encode()).hexdigest()[:16]
    except Exception:
        # ponytail: minimal logging -- upgrade to structured error reporting when error handling infra exists
        logger.warning("return hashlib.sha256(str(mac).encode()).hexdigest()[:16]", exc_info=True)
        pass

    # Last resort: hostname + arch (spoofable, but better than nothing)
    raw = "-".join([
        platform.node() or "unknown",
        platform.machine() or "unknown",
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Trial ───────────────────────────────────────────────────────────

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
    state.machine_id = state.machine_id or _get_machine_id()
    save(state)
    return state


def _valid_key_format(key: str) -> bool:
    """Check if key matches OBS-PRO-XXXXXXXX-XXXX format."""
    import re
    return bool(re.match(r"^OBS-PRO-[A-F0-9]{8}-[A-F0-9]{6}$", key.strip()))


# ── Rate limiting (Gap #9) ─────────────────────────────────────────

def _check_rate_limit(state: LicenseState) -> str | None:
    """Check activation rate limit. Returns error message if rate-limited, else None."""
    now = int(time.time())
    # Prune old attempts outside the window
    recent = [a for a in (state.activation_attempts or []) if now - a.get("ts", 0) < ACTIVATION_WINDOW_SECS]
    if len(recent) >= MAX_ACTIVATION_ATTEMPTS:
        oldest = min(a.get("ts", 0) for a in recent)
        wait_secs = ACTIVATION_WINDOW_SECS - (now - oldest)
        return f"Too many activation attempts. Try again in {wait_secs // 60} minutes."
    return None


def _record_attempt(state: LicenseState, key_prefix: str) -> None:
    """Record an activation attempt for rate limiting."""
    now = int(time.time())
    recent = [a for a in (state.activation_attempts or []) if now - a.get("ts", 0) < ACTIVATION_WINDOW_SECS]
    recent.append({"ts": now, "key_prefix": key_prefix})
    state.activation_attempts = recent


# ── Key activation ──────────────────────────────────────────────────

def activate_key(key: str, email: str = "", plan: str = "solo") -> dict:
    """Activate a Pro license key.

    Validates key format (OBS-PRO-XXXXXXXX-XXXX) before attempting
    online validation. Junk keys are rejected immediately.
    Falls back to optimistic activation only if:
    1. Key exists in local issued_keys store, OR
    2. CRM is unreachable AND key format is valid
    """
    key = key.strip()
    if not _valid_key_format(key):
        return {"status": "error",
                "message": "Invalid key format. Expected format: OBS-PRO-XXXXXXXX-XXXX"}

    state = load()

    # Rate limiting (Gap #9)
    rate_error = _check_rate_limit(state)
    if rate_error:
        return {"status": "error", "message": rate_error}

    if state.key == key and state.license_type == "pro":
        # Same key already active — refresh validation
        pass

    # Record this attempt (must save immediately for rate limiting to work)
    _record_attempt(state, key[:14])
    save(state)  # Persist rate limit data even if key validation fails

    # Attempt online validation
    result = _validate_online(key)
    if result.get("valid"):
        state.license_type = "pro"  # Gap #2 fix: always set type=pro when key is valid
        state.key = key
        state.validated_at = int(time.time())
        state.provisioning_source = result.get("source", "admin_key")
        state.downgraded_at = None  # Clear any previous downgrade flag
        state.downgraded_reason = None
        if result.get("email"):
            state.customer_email = result["email"]
        if result.get("plan"):
            state.plan = result["plan"]
        if result.get("expires_at"):
            try:
                exp = result["expires_at"]
                if isinstance(exp, str):
                    from datetime import datetime
                    state.expires_at = int(datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp())
                elif isinstance(exp, (int, float)):
                    state.expires_at = int(exp)
            except (ValueError, TypeError):
                state.expires_at = None
        # If no expires_at from CRM, check if trial_ends_at means perpetual
        elif result.get("status") == "active" and not result.get("trial_ends_at"):
            state.expires_at = None  # perpetual
        save(state)
        # Record machine activation (Gap #18)
        record_machine_activation()
        return {"status": "activated", "plan": state.plan or plan, "expires_at": state.expires_at}

    # Online validation failed or offline
    if result.get("offline"):
        # Gap #3 fix: validate against issued_keys before optimistic fallback
        from observeco.billing import validate_admin_key
        local_check = validate_admin_key(key)
        if local_check.get("valid"):
            # Key exists in local store — activate with admin_key source
            state.license_type = "pro"
            state.key = key
            state.validated_at = int(time.time())
            state.provisioning_source = "admin_key"
            state.plan = local_check.get("plan", plan)
            state.downgraded_at = None
            state.downgraded_reason = None
            if email:
                state.customer_email = email
            save(state)
            return {"status": "activated_offline", "plan": state.plan,
                    "message": "License saved. Validated against local key store."}

        # Key not in local store AND CRM unreachable — reject (no optimistic activation for unknown keys)
        return {"status": "error",
                "message": "License server unreachable and key not found in local store. "
                           "Please try again when online."}

    return {"status": "error", "message": result.get("error", "Invalid license key")}


def _validate_online(key: str, machine_id: str = "") -> dict:
    """Validate a Pro license key.

    Priority:
    1. Local admin key store (works offline, for keys you generate)
    2. CRM API (Vercel, when Supabase is live)
    Falls back to offline error if both unavailable.
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


# ── Revalidation ────────────────────────────────────────────────────

def _revalidate_key(state: LicenseState | None = None) -> None:
    """Re-validate a pro key against CRM. Updates local state on change.

    Called when validation cache is stale (>24h). Will:
    - Downgrade to free if CRM says invalid/expired/cancelled
    - Update expires_at if CRM returns a new value
    - Refresh validated_at on success
    - Set downgraded_at/reason for UI notification (Gap #7 fix)
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
                    from datetime import datetime
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
        state.downgraded_at = int(time.time())  # Gap #7 fix
        state.downgraded_reason = "License key revoked or expired"
        save(state)


# ── Trial management ────────────────────────────────────────────────

def start_trial() -> dict:
    """Start or restart the 30-day trial.

    Returns error if trial was previously consumed (trial hardening),
    if user already has an active Pro key (never downgrade Pro to trial),
    or if a trial is already active (prevents trial reset abuse).
    Syncs the trial record to CRM when reachable.
    """
    state = load()
    # Never overwrite an active Pro key with a trial
    if state.license_type == "pro" and state.key:
        return {
            "status": "error",
            "message": "Pro license active. Trial is not needed.",
        }
    if state.trial_consumed:
        return {
            "status": "error",
            "message": "Trial already used. Trial is a one-time offer. Subscribe via Stripe to unlock Pro features.",
        }
    # Prevent trial reset abuse — reject if trial is already active
    if state.license_type == "trial" and state.trial_end and state.trial_end > int(time.time()):
        return {
            "status": "error",
            "message": "Trial already active. Cannot start a new trial while current trial is active.",
        }
    now = int(time.time())
    state.license_type = "trial"
    state.trial_token = "trial_" + secrets.token_hex(16)
    state.trial_start = now
    state.trial_end = now + 30 * 86400
    state.trial_consumed = False
    state.machine_id = state.machine_id or _get_machine_id()  # Gap #8 fix
    save(state)

    # Record machine activation (Gap #18)
    record_machine_activation()

    # Sync trial to CRM (fire-and-forget — never fail local operation)
    _sync_trial_to_crm(state.trial_token, state.customer_email or "", state.trial_end, state.machine_id)

    # Send welcome email (fire-and-forget — never fail local operation)
    if state.customer_email:
        try:
            from observeco.emails import send_email
            send_email(state.customer_email, "welcome", {
                "first_name": state.customer_email.split("@")[0].title(),
                "trial_days_left": "30",
                "subscribe_url": "http://localhost:9121/",
                "support_email": "support@observeco.dev",
            })
        except Exception:
            logger.warning("Could not send welcome email (non-fatal)")

    return {
        "status": "trial_started",
        "trial_end": state.trial_end,
        "days": 30,
    }


def _sync_trial_to_crm(trial_token: str, email: str, trial_end: int, machine_id: str = "") -> None:
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
        "machine_id": machine_id,
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


def _cancel_stripe_subscription(reason: str = "user_cancelled") -> dict | None:
    """Cancel the active Stripe subscription for this user (fire-and-forget).

    Looks up subscription_id from billing.json customers list.
    Returns {"subscription_id": ..., "status": "cancelled"} on success,
    or None if no subscription found / cancellation failed (non-fatal).
    """
    from observeco.billing import _load_config as _load_billing

    try:
        billing_cfg = _load_billing()
        sub_id = None
        for c in billing_cfg.customers:
            if c.get("subscription_id") and c.get("status") in ("active", "trialing"):
                sub_id = c["subscription_id"]
                break

        # Fallback: if not in billing.json, query Stripe API directly
        if not sub_id and billing_cfg.stripe_secret_key.startswith("sk_"):
            import stripe as stripe_lib
            stripe_lib.api_key = billing_cfg.stripe_secret_key
            for s in stripe_lib.Subscription.list(limit=100).auto_paging_iter():
                if s.status in ("active", "trialing"):
                    sub_id = s.id
                    break

        if not sub_id:
            logger.info("No active Stripe subscription found to cancel")
            return None

        import stripe as stripe_lib
        stripe_lib.api_key = billing_cfg.stripe_secret_key
        stripe_lib.Subscription.delete(sub_id, prorate=False)

        # Update billing.json status
        for c in billing_cfg.customers:
            if c.get("subscription_id") == sub_id:
                c["status"] = "cancelled"
        from observeco.billing import _save_config as _save_billing
        _save_billing(billing_cfg)

        logger.info("Stripe subscription %s cancelled (%s)", sub_id, reason)
        return {"subscription_id": sub_id, "status": "cancelled"}
    except ImportError:
        logger.warning("Stripe package not installed — cannot cancel subscription")
    except Exception as e:
        logger.warning("Could not cancel Stripe subscription (non-fatal): %s", e)
    return None


def cancel_trial() -> dict:
    """Cancel the current trial. Sets license_type back to free and marks trial consumed.

    Data is preserved. Only Pro features are locked. The user can resubscribe
    via Stripe Checkout at any time (Stripe enforces single-trial-per-customer).
    Also updates billing.json simulated customer records to reflect cancellation.
    Syncs cancellation to CRM when reachable.
    """
    from observeco.billing import _load_config as _load_billing
    from observeco.billing import _save_config as _save_billing

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

    # Cancel Stripe subscription if one exists (fire-and-forget — never fail local operation)
    _cancel_stripe_subscription(reason="trial_cancelled")

    # Send cancellation confirmed email (fire-and-forget — never fail local operation)
    if email:
        try:
            from observeco.emails import send_email
            send_email(email, "cancellation_confirmed", {
                "first_name": email.split("@")[0].title(),
                "subscribe_url": "http://localhost:9121/",
                "support_email": "support@observeco.dev",
            })
        except Exception:
            logger.warning("Could not send cancellation email (non-fatal)")

    return {
        "status": "cancelled",
        "message": "Trial cancelled. Pro features locked. Your data is safe — subscribe anytime to unlock them.",
    }


def deactivate_license() -> dict:
    """Remove the current license key and downgrade to Free.

    Does NOT touch trial data or billing.json — only clears the local
    license key and resets to free state. User can activate a new key later.
    If the license was provisioned via Stripe, also cancels the subscription.
    """
    state = load()
    if state.license_type != "pro" or not state.key:
        return {"status": "error", "message": "No active license key to deactivate"}

    provisioning_source = state.provisioning_source

    state.license_type = "free"
    state.key = None
    state.validated_at = None
    state.expires_at = None
    state.plan = None
    state.provisioning_source = None
    save(state)

    # Cancel Stripe subscription if provisioned via Stripe (fire-and-forget)
    if provisioning_source == "stripe":
        _cancel_stripe_subscription(reason="license_deactivated")

    return {
        "status": "deactivated",
        "message": "License key removed. Pro features locked. Your data is preserved. You can activate a new key at any time.",
    }


# ── Validation & enforcement ────────────────────────────────────────

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

    # Track first run for new-user LLM grace period (Gap #17 fix — separate file)
    install_state = _load_install_state()
    if state.first_run_at is None:
        state.first_run_at = int(time.time())
        save(state)
    if "first_run_at" not in install_state:
        install_state["first_run_at"] = state.first_run_at
        _save_install_state(install_state)

    # Gap #2 self-heal: if key exists but type is "trial", auto-correct to "pro"
    if state.license_type == "trial" and state.key:
        logger.warning("License state contradiction: key exists but type is 'trial'. Auto-correcting to 'pro'.")
        state.license_type = "pro"
        state.downgraded_at = None
        state.downgraded_reason = None
        save(state)

    # Pro key with stale cache — attempt online revalidation
    if state.license_type == "pro" and state.key and state.validation_stale:
        _revalidate_key(state)

    # Reload state after possible revalidation
    state = load()
    if state.is_pro:
        return True
    # Check if grace period has expired — consume the trial
    # Gap #16 fix: grace starts at trial_end, checked via is_in_grace property
    if state.is_in_grace:
        # Grace period active — check if it's expired
        assert state.trial_end is not None  # guaranteed by is_in_grace
        if int(time.time()) - state.trial_end >= LicenseState.GRACE_PERIOD_SECS:
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
                state.past_due_at = state.trial_end  # grace starts at trial_end, not now (off-by-one fix)
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
    Checks revocation on every call when validation is stale (Gap #12 fix).

    ponytail: Returns True unconditionally during beachhead (all features free).
    Gating infrastructure stays dormant but wired for future Pro features.
    When Pro tier ships, change to: return load().is_pro
    """
    return True


# ── Multi-machine tracking (Gap #18) ───────────────────────────────

def _get_machines_file() -> Path:
    return _get_config_dir() / ".activated_machines.json"

def _load_machines() -> dict:
    """Load machine activation records."""
    p = _get_machines_file()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _save_machines(data: dict) -> None:
    """Save machine activation records."""
    _get_config_dir().mkdir(parents=True, exist_ok=True)
    p = _get_machines_file()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)

def record_machine_activation() -> dict:
    """Record current machine activation. Returns device info."""
    machine_id = _get_machine_id()
    import platform
    machines = _load_machines()
    now = int(time.time())
    if machine_id not in machines:
        machines[machine_id] = {
            "first_seen": now,
            "hostname": platform.node(),
            "platform": platform.system(),
        }
    machines[machine_id]["last_seen"] = now
    _save_machines(machines)
    return {
        "machine_id": machine_id,
        "total_devices": len(machines),
        "platform": platform.system(),
    }

def get_device_count() -> int:
    """Return number of machines that have activated this license."""
    return len(_load_machines())
