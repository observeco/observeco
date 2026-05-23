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
import os
import time
from dataclasses import dataclass
from typing import Optional

from pathlib import Path

CONFIG_DIR = Path.home() / ".observeco"
CONFIG_FILE = CONFIG_DIR / "billing.json"


@dataclass
class BillingConfig:
    stripe_publishable_key: str = ""
    stripe_secret_key: str = ""
    solo_price_id: str = "price_solo_monthly"
    team_price_id: str = "price_team_monthly"
    trial_days: int = 30
    is_active: bool = False
    customers: list[dict] = None

    def __post_init__(self):
        if self.customers is None:
            self.customers = []


def _load_config() -> BillingConfig:
    """Load billing config from disk."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return BillingConfig(**data)
        except Exception:
            pass
    return BillingConfig()


def _save_config(config: BillingConfig) -> None:
    """Save billing config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({
        "stripe_publishable_key": config.stripe_publishable_key,
        "stripe_secret_key": config.stripe_secret_key,
        "solo_price_id": config.solo_price_id,
        "team_price_id": config.team_price_id,
        "trial_days": config.trial_days,
        "is_active": config.is_active,
        "customers": config.customers,
    }, indent=2))


def get_price_id(plan: str = "solo") -> str:
    """Get the Stripe price ID for a plan."""
    config = _load_config()
    return config.solo_price_id if plan == "solo" else config.team_price_id


def configure(stripe_secret: str, stripe_publishable: str,
              solo_price: str = "", team_price: str = "") -> None:
    """Configure Stripe integration."""
    config = _load_config()
    config.stripe_secret_key = stripe_secret
    config.stripe_publishable_key = stripe_publishable
    if solo_price:
        config.solo_price_id = solo_price
    if team_price:
        config.team_price_id = team_price
    config.is_active = True
    _save_config(config)


def create_checkout_session(email: str, plan: str = "solo",
                            success_url: str = "http://localhost:9119/billing/success",
                            cancel_url: str = "http://localhost:9119/billing/cancel") -> dict:
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
        event = stripe.Webhook.construct_event(payload, sig_header, "whsec_observeco")

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
    from fastapi import Request, HTTPException

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

    @app.post("/api/billing/webhook")
    async def billing_webhook(request: Request):
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        return handle_webhook(payload, sig)
