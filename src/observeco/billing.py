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

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from observeco.dirs import get_data_dir

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ponytail: lazy — evaluated at first call, not import time, so get_data_dir() failure
# doesn't crash the import. Upgrade path: make configurable via observeco.yml.
_CONFIG_DIR: Path | None = None
_CONFIG_FILE: Path | None = None
_BILLING_LOG: Path | None = None
_BILLING_LOCK_FILE: Path | None = None

def _get_config_dir() -> Path:
    global _CONFIG_DIR, _CONFIG_FILE, _BILLING_LOG, _BILLING_LOCK_FILE
    if _CONFIG_DIR is None:
        _CONFIG_DIR = get_data_dir()
        _CONFIG_FILE = _CONFIG_DIR / "billing.json"
        _BILLING_LOG = _CONFIG_DIR / "billing.log"
        _BILLING_LOCK_FILE = _CONFIG_DIR / ".billing.lock"
    return _CONFIG_DIR

def _get_config_file() -> Path:
    _get_config_dir()
    return _CONFIG_FILE  # type: ignore[return-value]

def _get_billing_log() -> Path:
    _get_config_dir()
    return _BILLING_LOG  # type: ignore[return-value]

def _get_billing_lock_file() -> Path:
    _get_config_dir()
    return _BILLING_LOCK_FILE  # type: ignore[return-value]

# Thread lock for safe concurrent access to billing.json
_billing_lock = threading.Lock()

_FILE_LOCK_RETRIES = 10
_FILE_LOCK_DELAY = 0.05  # 50ms between retries


def _acquire_file_lock() -> bool:
    """Acquire a cross-process advisory lock via atomic file creation.

    Uses O_CREAT|O_EXCL which is atomic on POSIX and NTFS (Windows).
    Returns True if lock acquired, False if contention persists.
    """
    lock_path = str(_get_billing_lock_file())
    for attempt in range(_FILE_LOCK_RETRIES):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except OSError:
            # Check if existing lock is stale (>30s old from a crashed process)
            try:
                age = time.time() - os.path.getmtime(_get_billing_lock_file())
                if age > 30:
                    os.unlink(lock_path)
                    continue  # Retry immediately after clearing stale lock
            except OSError:
                pass  # Race: another process cleared it
            if attempt == _FILE_LOCK_RETRIES - 1:
                return False
            time.sleep(_FILE_LOCK_DELAY)
    return False


def _release_file_lock() -> None:
    """Release the cross-process lock file."""
    try:
        os.unlink(str(_get_billing_lock_file()))
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
    resend_api_key: str = ""
    sender_email: str = "noreply@observeco.com"
    sender_name: str = "ObserveCo"
    support_email: str = "support@observeco.com"

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
            _get_config_dir().mkdir(parents=True, exist_ok=True)

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
                "resend_api_key": config.resend_api_key,
                "sender_email": config.sender_email,
                "sender_name": config.sender_name,
                "support_email": config.support_email,
            }

            # Encrypt sensitive fields
            SENSITIVE = ["stripe_secret_key", "webhook_secret", "resend_api_key"]
            encrypt_dict(data, SENSITIVE)

            # Atomic write: write to temp, then rename
            tmp = _get_config_file().with_suffix(".billing.tmp")
            # Retry loop for concurrent access safety
            for attempt in range(3):
                try:
                    tmp.write_text(json.dumps(data, indent=2))
                    tmp.chmod(0o600)
                    tmp.replace(_get_config_file())
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
            if _get_config_file().exists():
                try:
                    logger.info("[billing] Config found, loading from %s", _get_config_file())
                    data = json.loads(_get_config_file().read_text())

                    from .crypto import decrypt_dict

                    SENSITIVE = ["stripe_secret_key", "webhook_secret", "resend_api_key"]
                    decrypt_dict(data, SENSITIVE)

                    config = BillingConfig(**data)
                    # Overlay: env var > macOS Keychain > billing.json
                    _stripe_secret = (
                        os.environ.get("STRIPE_SECRET_KEY")
                        or _keychain_get("observeco")
                        or config.stripe_secret_key
                    )
                    config.stripe_secret_key = _stripe_secret

                    # ponytail: Keychain fetch spawns a subprocess per call.
                    # If this becomes a hot path, cache the result in a module-level var.
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


def _keychain_get(service: str) -> str | None:
    """Read a password from the default macOS Keychain via `security` CLI.

    Returns None if not found or not on macOS — no dependencies, no exceptions.
    """
    import subprocess
    import sys
    if sys.platform != "darwin":
        return None
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except (subprocess.SubprocessError, OSError):
        return None


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
                            trial_days: int | None = None,
success_url: str = None,
    cancel_url: str = None) -> dict:
    """Create a Stripe Checkout Session.

    trial_days override: pass 0 for no trial (cancelled/expired users),
    pass None (default) to use config.trial_days (e.g. 30 for fresh trials).

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

        effective_trial = config.trial_days if trial_days is None else trial_days
        live_success = (success_url or "http://localhost:9121/api/billing/success") + \
                       "?session_id={CHECKOUT_SESSION_ID}"
        sub_data = {"metadata": {"plan": plan}}
        if effective_trial > 0:
            sub_data["trial_period_days"] = effective_trial
        session = stripe.checkout.Session.create(
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=live_success,
            cancel_url=cancel_url or "http://localhost:9121/api/billing/cancel",
            metadata=metadata,
            subscription_data=sub_data,
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
    """Handle Stripe webhook events.

    Gap #5 fix: reject webhooks in demo mode (no signature verification possible).
    Gap #15 fix: handle invoice.paid and customer.subscription.updated for trial→paid conversion.
    """
    config = _load_config()
    if not config.is_active or not config.stripe_secret_key:
        # Gap #5 fix: reject webhook in demo mode — can't verify signature
        return {"status": "rejected", "message": "Stripe not configured — webhook rejected (demo mode)"}

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
            # Also start the trial so license.json reflects Pro status
            from observeco.license import start_trial as _start_trial
            _start_trial()
            logger.info("Webhook checkout.session.completed: customer=%s, trial started", customer_email)
            return {"status": "success", "action": "customer_created"}

        # Gap #15 fix: handle subscription updates → activate Pro from Stripe
        if event["type"] in ("invoice.paid", "customer.subscription.updated", "customer.subscription.created"):
            subscription = event["data"]["object"]
            sub_id = subscription.get("id") or subscription.get("subscription")
            customer_id = subscription.get("customer")
            status = subscription.get("status")
            logger.info("Webhook %s: sub=%s customer=%s status=%s", event["type"], sub_id, customer_id, status)

            # If subscription is active, activate Pro for this customer
            if status in ("active", "trialing"):
                from observeco.license import load as _load_license, save as _save_license, LicenseState
                lic = _load_license()
                if lic.license_type != "pro":
                    # Find customer email from billing config
                    cust_email = ""
                    for c in config.customers:
                        if c.get("stripe_customer_id") == customer_id:
                            cust_email = c.get("email", "")
                            break
                    # Update customer status in billing config
                    for c in config.customers:
                        if c.get("stripe_customer_id") == customer_id or c.get("subscription_id") == sub_id:
                            c["status"] = "active"
                            c["subscription_id"] = sub_id
                    _save_config(config)
                    # Activate Pro in license.json
                    lic.license_type = "pro"
                    lic.provisioning_source = "stripe"
                    lic.customer_email = lic.customer_email or cust_email
                    lic.validated_at = int(time.time())
                    lic.downgraded_at = None
                    lic.downgraded_reason = None
                    _save_license(lic)
                    logger.info("Activated Pro from Stripe subscription: customer=%s", cust_email)

                    # Send welcome email (fire-and-forget — never fail local operation)
                    if cust_email:
                        try:
                            from observeco.emails import send_email
                            send_email(cust_email, "welcome", {
                                "first_name": cust_email.split("@")[0].title(),
                                "trial_days_left": "N/A",
                                "subscribe_url": "http://localhost:9121/",
                                "support_email": "support@observeco.com",
                            })
                        except Exception:
                            logger.warning("Could not send welcome email (non-fatal)")

                    return {"status": "success", "action": "pro_activated_from_subscription"}

            if status in ("canceled", "unpaid", "past_due"):
                # Subscription ended — downgrade
                from observeco.license import load as _load_license, save as _save_license
                lic = _load_license()
                if lic.license_type == "pro" and lic.provisioning_source == "stripe":
                    lic.license_type = "free"
                    lic.key = None
                    lic.validated_at = None
                    lic.expires_at = None
                    lic.downgraded_at = int(time.time())
                    lic.downgraded_reason = f"Stripe subscription {status}"
                    _save_license(lic)
                    logger.info("Downgraded Pro from Stripe subscription %s: status=%s", sub_id, status)

                    # Find customer email for cancellation email
                    cust_email = ""
                    for c in config.customers:
                        if c.get("stripe_customer_id") == customer_id or c.get("subscription_id") == sub_id:
                            cust_email = c.get("email", "")
                            break

                    # Send cancellation confirmed email (fire-and-forget — never fail local operation)
                    if cust_email:
                        try:
                            from observeco.emails import send_email
                            send_email(cust_email, "cancellation_confirmed", {
                                "first_name": cust_email.split("@")[0].title(),
                                "subscribe_url": "http://localhost:9121/",
                                "support_email": "support@observeco.com",
                            })
                        except Exception:
                            logger.warning("Could not send cancellation email (non-fatal)")

                    return {"status": "success", "action": "pro_downgraded_from_subscription"}

        # Handle invoice.payment_failed — send payment failure notification
        if event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            customer_id = invoice.get("customer")
            # Find customer email from billing config
            cust_email = ""
            for c in config.customers:
                if c.get("stripe_customer_id") == customer_id:
                    cust_email = c.get("email", "")
                    break

            # Send payment_failed email (fire-and-forget — never fail local operation)
            if cust_email:
                try:
                    from observeco.emails import send_email
                    send_email(cust_email, "payment_failed", {
                        "first_name": cust_email.split("@")[0].title(),
                        "manage_url": "http://localhost:9121/api/billing/status",
                        "support_email": "support@observeco.com",
                    })
                except Exception:
                    logger.warning("Could not send payment_failed email (non-fatal)")

            logger.info("Webhook invoice.payment_failed: customer=%s", customer_id)
            return {"status": "success", "action": "payment_failed_notified"}

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
        result = create_checkout_session(email, phone, name, plan, trial_days=None, success_url=success_url, cancel_url=cancel_url)
        result["customer_name"] = name
        return result

    @app.get("/api/billing/success")
    async def billing_success(request: Request):
        """Stripe checkout success page — starts trial, redirects to dashboard."""
        session_id = request.query_params.get("session_id", "")

        # Simulated mode: start trial and record customer on confirmed checkout
        # Gap #14 fix: verify demo session exists in billing.json before activating
        if session_id and session_id.startswith("cs_demo_"):
            config = _load_config()
            # Check if this session was already recorded (prevents replay)
            existing = [c for c in config.customers if c.get("session_id") == session_id]
            if not existing:
                # Unknown demo session — reject (prevents URL crafting attack)
                return HTMLResponse("""<!DOCTYPE html><html><head>
                <script>setTimeout(function() { window.location.href = '/'; }, 2000);</script>
                </head><body style="background:#0f172a;color:#e2e8f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;gap:12px;">
                <div style="font-size:48px;">⚠️</div>
                <h2 style="margin:0;">Invalid checkout session</h2>
                <p style="color:#64748b;font-size:12px;">Redirecting to dashboard...</p></body></html>""")
            from observeco.license import start_trial as start_license_trial
            trial_result = start_license_trial()
            if trial_result.get("status") == "trial_started":
                # Mark existing customer as trialing
                for c in config.customers:
                    if c.get("session_id") == session_id:
                        c["status"] = "trialing"
                        c["trial_end"] = int(time.time()) + config.trial_days * 86400
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
                        meta = getattr(session, "metadata", {}) or {}
                        customer_details = getattr(session, "customer_details", None) or {}
                        # Save record BEFORE start_trial — webhook saves first too
                        config.customers.append({
                            "email": getattr(session, "customer_email", None) or meta.get("customer_email", "unknown"),
                            "phone": getattr(customer_details, "phone", "") or meta.get("customer_phone", ""),
                            "name": getattr(customer_details, "name", "") or meta.get("customer_name", ""),
                            "plan": meta.get("plan", "solo"),
                            "session_id": session_id,
                            "status": "trialing",
                            "subscription_id": getattr(session, "subscription", None),
                            "stripe_customer_id": getattr(session, "customer", None),
                            "trial_end": int(time.time()) + config.trial_days * 86400,
                            "created_at": int(time.time()),
                        })
                        _save_config(config)
                        from observeco.license import start_trial as start_license_trial
                        trial_result = start_license_trial()
                except Exception as e:
                    logger.warning("Could not verify live Stripe session %s: %s", session_id, e)

        return HTMLResponse("""<!DOCTYPE html><html><head>
        <script>
        // Auto-reload the tab that opened Stripe (if any), so Pro features light up
        try { if (window.opener && !window.opener.closed) window.opener.location.reload(); } catch(e) {}
        setTimeout(function() { window.location.href = '/'; }, 1500);
        </script>
        </head><body style="background:#0f172a;color:#e2e8f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;gap:12px;">
        <div style="font-size:48px;">✅</div>
        <h2 style="margin:0;">Payment successful!</h2>
        <p style="color:#94a3b8;font-size:14px;">Your Pro license is being activated...</p>
        <p style="color:#64748b;font-size:12px;">Redirecting to dashboard...</p></body></html>""")

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

    @app.get('/api/billing/admin/subscriptions')
    async def admin_list_subscriptions():
        """Admin: list all active/trialing Stripe subscriptions."""
        config = _load_config()
        if not config.is_active or not config.stripe_secret_key.startswith('sk_'):
            return JSONResponse({'subscriptions': [], 'error': 'Stripe not configured'})
        try:
            import stripe as stripe_lib
            stripe_lib.api_key = config.stripe_secret_key
            subs = []
            for s in stripe_lib.Subscription.list(limit=100).auto_paging_iter():
                if s.status in ('active', 'trialing', 'past_due'):
                    subs.append({
                        'id': s.id,
                        'status': s.status,
                        'customer_id': s.customer,
                        'trial_end': s.trial_end,
                        'created': s.created,
                        'current_period_end': getattr(s, 'current_period_end', None),
                        'cancel_at_period_end': getattr(s, 'cancel_at_period_end', False),
                    })
            return JSONResponse({'subscriptions': subs})
        except ImportError:
            return JSONResponse({'subscriptions': [], 'error': 'Stripe not installed'})
        except Exception as e:
            return JSONResponse({'subscriptions': [], 'error': str(e)})

    @app.post('/api/billing/admin/cancel/{sub_id}')
    async def admin_cancel_subscription(sub_id: str):
        """Admin: cancel a Stripe subscription directly via API."""
        config = _load_config()
        if not config.is_active or not config.stripe_secret_key.startswith('sk_'):
            return JSONResponse({'error': 'Stripe not configured'}, status_code=400)
        try:
            import stripe as stripe_lib
            stripe_lib.api_key = config.stripe_secret_key
            # Cancel immediately (not at period end)
            stripe_lib.Subscription.delete(sub_id, prorate=False)
            # Also update billing.json if the sub is tracked there
            for c in config.customers:
                if c.get('subscription_id') == sub_id:
                    c['status'] = 'cancelled'
            _save_config(config)
            return JSONResponse({'ok': True, 'subscription_id': sub_id, 'status': 'cancelled'})
        except ImportError:
            return JSONResponse({'error': 'Stripe not installed'}, status_code=400)
        except Exception as e:
            return JSONResponse({'error': str(e)}, status_code=400)
