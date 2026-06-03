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
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from observeco.dirs import get_data_dir

CONFIG_DIR = get_data_dir()
CONFIG_FILE = CONFIG_DIR / "billing.json"


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

    def __post_init__(self):
        if self.customers is None:
            self.customers = []


def _save_config(config: BillingConfig) -> None:
    """Save billing config to disk with encrypted secrets."""
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
    }

    # Encrypt sensitive fields
    SENSITIVE = ["stripe_secret_key", "webhook_secret"]
    encrypt_dict(data, SENSITIVE)

    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    CONFIG_FILE.chmod(0o600)


def _load_config() -> BillingConfig:
    """Load billing config from disk with decryption."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())

            from .crypto import decrypt_dict

            SENSITIVE = ["stripe_secret_key", "webhook_secret"]
            decrypt_dict(data, SENSITIVE)

            return BillingConfig(**data)
        except Exception:
            pass
    return BillingConfig()


def get_price_id(plan: str = "solo") -> str:
    """Get the Stripe price ID for a plan."""
    config = _load_config()
    return config.solo_price_id if plan == "solo" else config.team_price_id


def configure(stripe_secret: str, stripe_publishable: str,
              solo_price: str = "", team_price: str = "",
              webhook_secret: str = "") -> None:
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


def create_checkout_session(email: str, plan: str = "solo",
                            success_url: str = "http://localhost:9121/api/billing/success",
                            cancel_url: str = "http://localhost:9121/api/billing/cancel") -> dict:
    """Create a Stripe Checkout Session.

    In demo/probe mode when Stripe is not configured, returns a simulated session.
    """
    config = _load_config()

    if not config.is_active or not config.stripe_secret_key:
        # Simulated mode — return demo session
        session_id = f"cs_demo_{int(time.time())}"
        _save_config(config)

        # Record simulated customer
        config.customers.append({
            "email": email,
            "plan": plan,
            "session_id": session_id,
            "status": "trialing",
            "trial_end": int(time.time()) + config.trial_days * 86400,
            "created_at": int(time.time()),
        })
        _save_config(config)

        return {
            "url": f"{success_url}?session_id={session_id}",
            "session_id": session_id,
            "mode": "simulated",
        }

    # Real Stripe integration
    try:
        import stripe
        stripe.api_key = config.stripe_secret_key
        price_id = config.solo_price_id if plan == "solo" else config.team_price_id

        session = stripe.checkout.Session.create(
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=email,
            metadata={"plan": plan},
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
        return {
            "error": "stripe package not installed. Install with: pip install stripe",
            "mode": "error",
        }
    except Exception as e:
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
            config.customers.append({
                "email": session.get("customer_email", "unknown"),
                "plan": session.get("metadata", {}).get("plan", "solo"),
                "session_id": session["id"],
                "status": "active",
                "subscription_id": session.get("subscription"),
                "created_at": int(time.time()),
            })
            _save_config(config)
            return {"status": "success", "action": "customer_created"}

        return {"status": "ignored", "event": event["type"]}
    except ImportError:
        return {"error": "stripe package not installed"}
    except Exception as e:
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
        plan = data.get("plan", "solo")
        if not email:
            raise HTTPException(400, "Email is required")
        result = create_checkout_session(email, plan)
        return result

    @app.get("/api/billing/success")
    async def billing_success(request: Request):
        """Stripe checkout success page — redirects back to dashboard with toast."""
        session_id = request.query_params.get("session_id", "")
        return HTMLResponse(f"""<!DOCTYPE html><html><head><meta http-equiv="refresh" content="2;url=/"></head><body style="background:#0f172a;color:#e2e8f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;gap:12px;">
        <div style="font-size:48px;">✅</div>
        <h2 style="margin:0;">Payment successful!</h2>
        <p style="color:#94a3b8;font-size:14px;">Your Pro license is being activated...</p>
        <p style="color:#64748b;font-size:12px;">Redirecting to dashboard...</p>
        <script>
        fetch('/api/licenses/validate', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{force: true}})}}).then(() => {{ window.location.href = '/'; }}).catch(() => {{ window.location.href = '/'; }});
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
            customer_id = data.get("customer_id", "")
            if not customer_id:
                return {"error": "customer_id is required", "mode": "error"}

            session = stripe_lib.billing_portal.Session.create(
                customer=customer_id,
                return_url=data.get("return_url", "http://localhost:9121/"),
            )
            return {"url": session.url, "mode": "live"}
        except ImportError:
            return {"error": "stripe package not installed", "mode": "error"}
        except Exception as e:
            return {"error": str(e), "mode": "error"}
