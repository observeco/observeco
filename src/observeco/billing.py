"""Stripe Checkout + Pro billing integration.

Implements:
- /checkout endpoint for Stripe Checkout Session creation
- Webhook handler for checkout.session.completed
- Customer creation + subscription management
- Trial period: 30 days
- Plans: Solo $9/mo, Team $49/mo
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from observeco.dirs import get_data_dir

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CONFIG_DIR = get_data_dir()
CONFIG_FILE = CONFIG_DIR / "billing.json"

# Persistent file log for billing operations (rotating: 1MB × 3 backups)
_BILLING_LOG = CONFIG_DIR / "billing.log"
_handler = logging.handlers.RotatingFileHandler(
    str(_BILLING_LOG), maxBytes=1_048_576, backupCount=3
)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_handler)

# Thread lock for safe concurrent access to billing.json
_billing_lock = threading.Lock()

# File-level lock for multi-process safety (used alongside thread lock)
_BILLING_LOCK_FILE = CONFIG_DIR / ".billing.lock"
_FILE_LOCK_RETRIES = 10
_FILE_LOCK_DELAY = 0.05  # 50ms between retries


def _acquire_file_lock() -> bool:
    """Acquire a cross-process advisory lock via atomic file creation.

    Uses O_CREAT|O_EXCL which is atomic on POSIX and NTFS (Windows).
    Returns True if lock acquired, False if contention persists.
    """
    lock_path = str(_BILLING_LOCK_FILE)
    for attempt in range(_FILE_LOCK_RETRIES):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except OSError:
            if attempt == _FILE_LOCK_RETRIES - 1:
                return False
            time.sleep(_FILE_LOCK_DELAY)
    return False


def _release_file_lock() -> None:
    """Release the cross-process lock file."""
    try:
        os.unlink(str(_BILLING_LOCK_FILE))
    except OSError:
        pass


@dataclass
class BillingConfig:
    stripe_publishable_key: str = ""
    stripe_secret_key: str = ""
    webhook_secret: str = ""
    solo_price_id: str = "price_solo_monthly"
    team_price_id: str = "price_team_monthly"
    trial_days: int = 30
    is_active: bool = False
    customers: list[dict] = None
    issued_keys: dict = None  # {key: {issued_at, issued_to, revoked, plan}}

    def __post_init__(self):
        if self.customers is None:
            self.customers = []
        if self.issued_keys is None:
            self.issued_keys = {}
        # Allow OBSERVECO_TRIAL_DAYS env var to override for testing
        env_trial = os.environ.get("OBSERVECO_TRIAL_DAYS")
        if env_trial is not None:
            try:
                self.trial_days = int(env_trial)
            except (ValueError, TypeError):
                pass


def _save_config(config: BillingConfig) -> None:
    """Save billing config to disk with encrypted secrets (atomic write, thread-safe, multi-process-safe)."""
    if not _acquire_file_lock():
        logger.error("Failed to acquire file lock for billing write after %d retries", _FILE_LOCK_RETRIES)
        raise OSError("Could not acquire billing file lock — another process is writing")
    try:
        with _billing_lock:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            from .crypto import encrypt_dict

            data = {
                "stripe_publishable_key": config.stripe_publishable_key,
                "stripe_secret_key": config.stripe_secret_key,
                "webhook_secret": config.webhook_secret,
                "solo_price_id": config.solo_price_id,
                "team_price_id": config.team_price_id,
                "trial_days": config.trial_days,
                "is_active": config.is_active,
                "customers": config.customers,
                "issued_keys": config.issued_keys,
            }

            # Encrypt sensitive fields
            SENSITIVE = ["stripe_secret_key", "webhook_secret"]
            encrypt_dict(data, SENSITIVE)

            # Atomic write: write to temp, then rename
            tmp = CONFIG_FILE.with_suffix(".billing.tmp")
            # Retry loop for concurrent access safety
            for attempt in range(3):
                try:
                    tmp.write_text(json.dumps(data, indent=2))
                    tmp.chmod(0o600)
                    tmp.replace(CONFIG_FILE)
                    break
                except OSError as e:
                    if attempt == 2:
                        logger.error("Failed to save billing config after 3 retries: %s", e)
                        raise
                    logger.warning("Billing write attempt %d/3 failed: %s", attempt + 1, e)
                    time.sleep(0.1)
    finally:
        _release_file_lock()


def _load_config() -> BillingConfig:
    """Load billing config from disk with decryption (thread-safe, multi-process-safe)."""
    if not _acquire_file_lock():
        logger.error("Failed to acquire file lock for billing read after %d retries", _FILE_LOCK_RETRIES)
        return BillingConfig()
    try:
        with _billing_lock:
            if CONFIG_FILE.exists():
                try:
                    logger.info("[billing] Config found, loading from %s", CONFIG_FILE)
                    data = json.loads(CONFIG_FILE.read_text())

                    from .crypto import decrypt_dict

                    SENSITIVE = ["stripe_secret_key", "webhook_secret"]
                    decrypt_dict(data, SENSITIVE)

                    config = BillingConfig(**data)
                    if config.is_active:
                        logger.info(
                            "[billing] Stripe configured from disk — %s, %d-day trial, mode=%s",
                            "live" if config.stripe_secret_key.startswith("sk_live") else "test",
                            config.trial_days,
                            "live" if config.stripe_secret_key.startswith("sk_live") else "test",
                        )
                    return config
                except Exception as e:
                    logger.error("Failed to load billing config: %s", e)
            return BillingConfig()
    finally:
        _release_file_lock()


def get_price_id(plan: str = "solo") -> str:
    """Get the Stripe price ID for a plan."""
    config = _load_config()
    return config.solo_price_id if plan == "solo" else config.team_price_id


def configure(stripe_secret: str, stripe_publishable: str,
              solo_price: str = "", team_price: str = "",
              webhook_secret: str = "") -> dict:
    """Configure Stripe integration."""
    config = _load_config()
    config.stripe_secret_key = stripe_secret
    config.stripe_publishable_key = stripe_publishable
    if solo_price:
        config.solo_price_id = solo_price
    if team_price:
        config.team_price_id = team_price
    if webhook_secret:
        config.webhook_secret = webhook_secret
    config.is_active = True
    _save_config(config)
    logger.info("Billing configured: stripe_active=True")
    return {"status": "configured", "is_active": True}


def create_checkout_session(email: str, phone: str = "", name: str = "", plan: str = "solo",
                            success_url: str = "http://localhost:9121/api/billing/success",
                            cancel_url: str = "http://localhost:9121/api/billing/cancel") -> dict:
    """Create a Stripe Checkout Session.

    In demo/probe mode when Stripe is not configured, returns a simulated session.
    """
    config = _load_config()

    if not config.is_active:
        # billing.json explicitly disabled or key invalid — use simulated mode
        pass
    elif not config.stripe_secret_key.startswith("sk_"):
        # Decryption failed or key corrupted — fall back to simulated
        config.is_active = False

    if not config.is_active or not config.stripe_secret_key.startswith("sk_"):
        # Simulated mode — return demo session
        # Customer + trial creation happens in billing_success callback,
        # so the user must complete the redirect before anything activates.
        session_id = f"cs_demo_{int(time.time())}"
        return {
            "url": f"{success_url}?session_id={session_id}&email={email}&phone={phone}&name={name}",
            "session_id": session_id,
            "mode": "simulated",
        }

    # Real Stripe integration
    try:
        import stripe
        stripe.api_key = config.stripe_secret_key
        price_id = config.solo_price_id if plan == "solo" else config.team_price_id

        metadata = {"plan": plan}
        if email:
            metadata["customer_email"] = email
        if phone:
            metadata["customer_phone"] = phone
        if name:
            metadata["customer_name"] = name

        session = stripe.checkout.Session.create(
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            subscription_data={
                "trial_period_days": config.trial_days,
                "metadata": {"plan": plan},
            },
        )
        return {
            "url": session.url,
            "session_id": session.id,
            "mode": "live",
        }
    except ImportError:
        logger.error("Checkout session failed: stripe package not installed")
        return {
            "error": "stripe package not installed. Install with: pip install stripe",
            "mode": "error",
        }
    except Exception as e:
        logger.error("Checkout session failed: %s", e)
        return {
            "error": str(e),
            "mode": "error",
        }


def handle_webhook(payload: bytes, sig_header: str = "") -> dict:
    """Handle Stripe webhook events."""
    config = _load_config()
    if not config.is_active or not config.stripe_secret_key:
        return {"status": "demo", "message": "Stripe not configured, webhook skipped"}

    try:
        import stripe
        stripe.api_key = config.stripe_secret_key
        event = stripe.Webhook.construct_event(payload, sig_header, config.webhook_secret)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            meta = session.get("metadata", {})
            customer_email = session.get("customer_email") or meta.get("customer_email", "unknown")
            customer_phone = session.get("customer_phone") or meta.get("customer_phone", "") or \
                session.get("customer_details", {}).get("phone", "")
            customer_name = session.get("customer_details", {}).get("name", "") or meta.get("customer_name", "")
            config.customers.append({
                "email": customer_email,
                "phone": customer_phone,
                "name": customer_name,
                "plan": meta.get("plan", "solo"),
                "session_id": session["id"],
                "status": "active",
                "subscription_id": session.get("subscription"),
                "stripe_customer_id": session.get("customer"),
                "created_at": int(time.time()),
            })
            _save_config(config)
            return {"status": "success", "action": "customer_created"}

        return {"status": "ignored", "event": event["type"]}
    except ImportError:
        logger.error("Webhook handling failed: stripe package not installed")
        return {"error": "stripe package not installed"}
    except Exception as e:
        logger.error("Webhook handling failed: %s", e)
        return {"error": str(e)}


def get_billing_status() -> dict:
    """Get current billing configuration status."""
    config = _load_config()
    return {
        "configured": config.is_active,
        "trial_days": config.trial_days,
        "customers": len(config.customers),
        "active_subscriptions": sum(1 for c in config.customers if c.get("status") == "active"),
        "trialing": sum(1 for c in config.customers if c.get("status") == "trialing"),
        "issued_keys": len(config.issued_keys or {}),
        "active_keys": sum(1 for v in (config.issued_keys or {}).values() if not v.get("revoked")),
    }


# ── Admin License Key Management ──────────────────────────────

_ADMIN_KEY = None

def _get_admin_key() -> str:
    global _ADMIN_KEY
    if _ADMIN_KEY is None:
        import os
        _ADMIN_KEY = os.environ.get("OBSERVECO_ADMIN_KEY", "observeco-admin-2026")
    return _ADMIN_KEY


def generate_key(issued_to: str = "", plan: str = "solo") -> dict:
    """Generate a new Pro license key. Stores in billing.json for offline validation."""
    import secrets
    config = _load_config()
    key = f"OBS-PRO-{secrets.token_hex(4).upper()}-{secrets.token_hex(3).upper()}"
    now = int(time.time())
    if config.issued_keys is None:
        config.issued_keys = {}
    config.issued_keys[key] = {
        "issued_at": now,
        "issued_to": issued_to,
        "revoked": False,
        "revoked_at": None,
        "plan": plan,
        "activated_by": None,
        "activated_at": None,
    }
    _save_config(config)
    logger.info("Key generated: %s -> %s (plan=%s)", key, issued_to or "unnamed", plan)
    return {"key": key, "plan": plan, "issued_at": now}


def revoke_key(key: str) -> dict:
    """Revoke a previously issued license key."""
    config = _load_config()
    if not config.issued_keys or key not in config.issued_keys:
        return {"status": "error", "message": "Key not found"}
    config.issued_keys[key]["revoked"] = True
    config.issued_keys[key]["revoked_at"] = int(time.time())
    _save_config(config)
    logger.info("Key revoked: %s", key)
    return {"status": "revoked", "key": key}


def list_keys() -> list[dict]:
    """List all issued license keys with their status."""
    config = _load_config()
    if not config.issued_keys:
        return []
    result = []
    for key, meta in config.issued_keys.items():
        result.append({
            "key": key,
            "plan": meta.get("plan", "solo"),
            "issued_at": meta.get("issued_at"),
            "issued_to": meta.get("issued_to", ""),
            "revoked": meta.get("revoked", False),
            "revoked_at": meta.get("revoked_at"),
            "activated_by": meta.get("activated_by"),
            "activated_at": meta.get("activated_at"),
        })
    return sorted(result, key=lambda x: x.get("issued_at", 0), reverse=True)


def validate_admin_key(key: str) -> dict:
    """Validate a Pro license key against the local store.

    Checks: key exists, not revoked. Returns same format as CRM validation.
    """
    config = _load_config()
    if not config.issued_keys or key not in config.issued_keys:
        logger.warning("Key validation failed: %s — not found", key)
        return {"valid": False, "error": "License key not found"}
    entry = config.issued_keys[key]
    if entry.get("revoked"):
        logger.warning("Key validation failed: %s — revoked", key)
        return {"valid": False, "error": "License key has been revoked"}
    logger.info("Key validated: %s (plan=%s)", key, entry.get("plan", "solo"))
    return {
        "valid": True,
        "product": entry.get("plan", "solo"),
        "status": "active",
        "plan": entry.get("plan", "solo"),
        "source": "admin_key",
    }


def add_billing_endpoints(app) -> None:
    """Add Stripe billing endpoints to a FastAPI app (for dashboard integration)."""

    @app.get("/api/billing/status")
    async def billing_status():
        return get_billing_status()

    @app.post("/api/billing/checkout")
    async def billing_checkout(request: Request):
        data = await request.json()
        email = data.get("email", "")
        name = data.get("name", "")
        phone = data.get("phone", "")
        plan = data.get("plan", "solo")
        if not email:
            return {"error": "Email is required", "mode": "error"}
        # Derive success/cancel URLs from the request's own host
        base = str(request.base_url).rstrip("/")
        success_url = f"{base}/api/billing/success"
        cancel_url = f"{base}/api/billing/cancel"
        result = create_checkout_session(email, phone, name, plan, success_url, cancel_url)
        result["customer_name"] = name
        return result

    @app.get("/api/billing/success")
    async def billing_success(request: Request):
        """Stripe checkout success page — starts trial, redirects to dashboard."""
        session_id = request.query_params.get("session_id", "")

        # Simulated mode: start trial and record customer on confirmed checkout
        if session_id and session_id.startswith("cs_demo_"):
            from observeco.license import start_trial as start_license_trial
            trial_result = start_license_trial()
            if trial_result.get("status") == "trial_started":
                # Record simulated customer in billing.json
                config = _load_config()
                config.customers.append({
                    "email": request.query_params.get("email", "checkout@observeco.app"),
                    "phone": request.query_params.get("phone", ""),
                    "name": request.query_params.get("name", ""),
                    "plan": "solo",
                    "session_id": session_id,
                    "status": "trialing",
                    "trial_end": int(time.time()) + config.trial_days * 86400,
                    "created_at": int(time.time()),
                })
                _save_config(config)

        # Live Stripe mode: verify and activate trial from redirect
        elif session_id and session_id.startswith("cs_live_"):
            config = _load_config()
            if config.is_active and config.stripe_secret_key:
                try:
                    import stripe
                    stripe.api_key = config.stripe_secret_key
                    session = stripe.checkout.Session.retrieve(session_id)
                    if session.status == "complete" or session.payment_status == "paid":
                        from observeco.license import start_trial as start_license_trial
                        trial_result = start_license_trial()
                        if trial_result.get("status") == "trial_started":
                            meta = getattr(session, "metadata", {}) or {}
                            customer_details = getattr(session, "customer_details", None) or {}
                            config.customers.append({
                                "email": getattr(session, "customer_email", None) or meta.get("customer_email", "unknown"),
                                "phone": getattr(customer_details, "phone", "") or meta.get("customer_phone", ""),
                                "name": getattr(customer_details, "name", "") or meta.get("customer_name", ""),
                                "plan": meta.get("plan", "solo"),
                                "session_id": session_id,
                                "status": "trialing",
                                "subscription_id": getattr(session, "subscription", None),
                                "trial_end": int(time.time()) + config.trial_days * 86400,
                                "created_at": int(time.time()),
                            })
                            _save_config(config)
                except Exception:
                    logger.warning("Could not verify live Stripe session %s", session_id)

        return HTMLResponse("""<!DOCTYPE html><html><head><meta http-equiv="refresh" content="2;url=/"></head><body style="background:#0f172a;color:#e2e8f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;gap:12px;">
        <div style="font-size:48px;">✅</div>
        <h2 style="margin:0;">Payment successful!</h2>
        <p style="color:#94a3b8;font-size:14px;">Your Pro license is being activated...</p>
        <p style="color:#64748b;font-size:12px;">Redirecting to dashboard...</p>
        <script>
        setTimeout(function() { window.location.href = '/'; }, 2000);
        </script></body></html>""")

    @app.get("/api/billing/cancel")
    async def billing_cancel():
        """Stripe checkout cancelled — redirect back to dashboard."""
        return RedirectResponse(url="/")

    @app.post("/api/billing/webhook")
    async def billing_webhook(request: Request):
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        return handle_webhook(payload, sig)

    @app.post("/api/billing/portal")
    async def billing_portal(request: Request):
        """Create a Stripe Customer Portal session for self-serve billing management.

        Returns a redirect URL to the Stripe-hosted portal where users can:
        - View/update payment method
        - Cancel subscription
        - View invoices
        - Update billing info
        """
        try:
            import stripe as stripe_lib
            config = _load_config()
            if not config.is_active or not config.stripe_secret_key:
                return {"error": "Stripe not configured", "mode": "error"}
            stripe_lib.api_key = config.stripe_secret_key

            data = await request.json()
            customer_id = data.get("customer_id", "") or data.get("customer", "")
            # If no customer_id provided, look up from saved config
            if not customer_id:
                for c in config.customers:
                    if c.get("stripe_customer_id"):
                        customer_id = c["stripe_customer_id"]
                        break
            if not customer_id:
                # No Stripe customer — user activated via license key, not subscription
                from observeco.license import load as _load_license
                lic = _load_license()
                if lic.key or lic.is_pro:
                    return {"error": "Your account uses a license key, not a Stripe subscription. There are no billing settings to manage here.", "mode": "license_key"}
                return {"error": "customer_id is required", "mode": "error"}

            session = stripe_lib.billing_portal.Session.create(
                customer=customer_id,
                return_url=data.get("return_url", "http://localhost:9121/"),
            )
            return {"url": session.url, "mode": "live"}
        except ImportError:
            logger.error("Portal session failed: stripe package not installed")
            return {"error": "Stripe not installed", "mode": "error"}
        except Exception as e:
            logger.error("Portal session failed: %s", e)
            return {"error": str(e), "mode": "error"}
