"""Commercial API endpoints — license validation, trials, telemetry, admin, Stripe webhooks.

All endpoints route through Supabase REST API (httpx, no supabase-py dependency).
Registered in server.py on startup.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from observeco.dashboard.supabase_client import (
    is_configured,
    select,
    insert,
    update,
    count,
)

router = APIRouter(prefix="/api/commercial", tags=["commercial"])


# ── Request models ─────────────────────────────────────────────

class ValidateRequest(BaseModel):
    license_key: str
    email: str = ""


class TrialRequest(BaseModel):
    email: str
    name: str = ""


class TelemetryRequest(BaseModel):
    event: str
    version: str = ""
    machine_id: str = ""
    os: str = ""
    python_version: str = ""
    payload: dict = {}


class AdminIssueRequest(BaseModel):
    email: str
    name: str = ""
    product_slug: str = "solo"


# ── Helpers ────────────────────────────────────────────────────

def _get_admin_key() -> str:
    return os.environ.get("OBSERVECO_ADMIN_KEY", "observeco-admin-2026")


def _require_admin(x_admin_key: str | None = None) -> None:
    expected = _get_admin_key()
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _check_configured() -> None:
    if not is_configured():
        raise HTTPException(status_code=503, detail="Supabase not configured")


# ── Endpoints ──────────────────────────────────────────────────

@router.get("/health")
async def commercial_health():
    """Return whether Supabase is configured."""
    return {"configured": is_configured()}


@router.get("/products")
async def list_products():
    """List available products from Supabase."""
    _check_configured()
    return select("products", columns="*") or []


# ── License Validation ─────────────────────────────────────────

@router.post("/licenses/validate")
async def validate_license(req: ValidateRequest):
    """Validate a license key against Supabase.

    Returns {valid, product, status, expires_at, ...}
    Auto-expires trialing/active licenses past expiry.
    """
    _check_configured()

    rows = select(
        "licenses",
        columns="*",
        filters={"license_key": req.license_key},
        limit=1,
    )
    if not rows:
        return {"valid": False, "error": "License not found"}
    row = rows[0]

    now = datetime.now(timezone.utc)
    valid = False
    new_status = row.get("status", "")

    if row["status"] == "active":
        expires_at = row.get("expires_at")
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at)
                valid = exp > now
            except (ValueError, TypeError):
                valid = True  # no expiry set
        else:
            valid = True  # no expiry = perpetual
        if not valid:
            update("licenses", {"status": "expired"}, {"id": row["id"]})
            new_status = "expired"

    elif row["status"] == "trialing":
        trial_ends = row.get("trial_ends_at")
        if trial_ends:
            try:
                tend = datetime.fromisoformat(trial_ends)
                valid = tend > now
            except (ValueError, TypeError):
                valid = False
        else:
            valid = False
        if not valid:
            update("licenses", {"status": "expired"}, {"id": row["id"]})
            new_status = "expired"

    # Update email if provided and different
    if req.email and req.email != row.get("email", ""):
        update("licenses", {"email": req.email}, {"id": row["id"]})

    return {
        "valid": valid,
        "product": row.get("product_slug", ""),
        "status": new_status,
        "expires_at": row.get("expires_at"),
        "trial_ends_at": row.get("trial_ends_at"),
        "created_at": row.get("created_at"),
    }


# ── Trials ─────────────────────────────────────────────────────

@router.post("/trials/start")
async def start_trial(req: TrialRequest):
    """Start a 30-day trial, creating a license record in Supabase."""
    _check_configured()

    import secrets
    trial_token = f"OBS-TRIAL-{secrets.token_hex(6).upper()}"

    rows = insert("licenses", {
        "email": req.email,
        "name": req.name or None,
        "product_slug": "solo",
        "license_key": trial_token,
        "status": "trialing",
        "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "issued_by": "self",
    })

    return {
        "license_key": trial_token,
        "product": "solo",
        "status": "trialing",
        "trial_ends_at": rows[0].get("trial_ends_at") if rows else None,
    }


# ── Telemetry ──────────────────────────────────────────────────

@router.post("/telemetry")
async def record_telemetry(req: TelemetryRequest):
    """Fire-and-forget telemetry event recording."""
    _check_configured()

    try:
        payload = req.payload if isinstance(req.payload, dict) else {}
        insert("telemetry_events", {
            "event": req.event,
            "version": req.version,
            "machine_id": req.machine_id,
            "os": req.os,
            "python_version": req.python_version,
            "payload": payload,
        })
    except Exception:
        # Fire-and-forget — never fail client for telemetry
        pass

    return {"received": True}


# ── Admin Endpoints ────────────────────────────────────────────

@router.get("/admin/licenses")
async def admin_list_licenses(
    status: str = "",
    email: str = "",
    x_admin_key: str | None = Header(None),
):
    """List licenses with optional filters. Admin auth required."""
    _require_admin(x_admin_key)
    _check_configured()

    rows = select("licenses", columns="*", order="created_at.desc")
    if status:
        rows = [r for r in (rows or []) if r.get("status") == status]
    if email:
        rows = [r for r in (rows or []) if email.lower() in (r.get("email", "") or "").lower()]
    return rows or []


@router.post("/admin/licenses")
async def admin_issue_license(
    req: AdminIssueRequest,
    x_admin_key: str | None = Header(None),
):
    """Issue a new license manually. Admin auth required."""
    _require_admin(x_admin_key)
    _check_configured()

    import secrets
    license_key = f"OBS-ADMIN-{secrets.token_hex(4).upper()}"

    rows = insert("licenses", {
        "email": req.email,
        "name": req.name or None,
        "product_slug": req.product_slug,
        "license_key": license_key,
        "status": "active",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "issued_by": "admin",
    })

    return rows[0] if rows else {"license_key": license_key}


@router.get("/admin/stats")
async def admin_stats(x_admin_key: str | None = Header(None)):
    """Aggregate license and telemetry stats. Admin auth required."""
    _require_admin(x_admin_key)
    _check_configured()

    total = count("licenses")
    active = count("licenses", {"status": "active"})
    trialing = count("licenses", {"status": "trialing"})
    expired = count("licenses", {"status": "expired"})
    cancelled = count("licenses", {"status": "cancelled"})
    telemetry_total = count("telemetry_events")

    return {
        "total": total,
        "active": active,
        "trialing": trialing,
        "expired": expired,
        "cancelled": cancelled,
        "telemetry_events": telemetry_total,
    }


# ── Stripe Webhook ─────────────────────────────────────────────

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe checkout.session.completed events.

    Verifies the webhook signature, then creates a license in Supabase.
    Requires STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET env vars.
    """
    _check_configured()

    stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if not stripe_secret or not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    try:
        import stripe as stripe_lib
        stripe_lib.api_key = stripe_secret
    except ImportError:
        raise HTTPException(status_code=503, detail="Stripe library not installed")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_lib.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe_lib.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event.type == "checkout.session.completed":
        session = event.data.object
        import secrets
        license_key = f"OBS-{secrets.token_hex(4).upper()}-{secrets.token_hex(2).upper()}"

        insert("licenses", {
            "email": getattr(session, "customer_email", None)
                      or (getattr(session, "customer_details", None) or {}).get("email", "unknown"),
            "name": (getattr(session, "customer_details", None) or {}).get("name"),
            "product_slug": "solo",
            "license_key": license_key,
            "status": "active",
            "stripe_subscription_id": getattr(session, "subscription", None),
            "stripe_customer_id": getattr(session, "customer", None),
            "issued_by": "stripe",
            "trial_ends_at": None,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "metadata": {"session_id": getattr(session, "id", "")},
        })

    elif event.type == "customer.subscription.deleted":
        """Handle subscription cancellation — mark license as cancelled."""
        sub = event.data.object
        sub_id = getattr(sub, "id", None)
        customer_id = getattr(sub, "customer", None)
        if sub_id:
            update("licenses", {
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, {"stripe_subscription_id": sub_id})
        elif customer_id:
            # Fallback: match by stripe_customer_id
            update("licenses", {
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, {"stripe_customer_id": customer_id})

    elif event.type == "customer.subscription.updated":
        """Handle subscription status/plan changes — sync license status."""
        sub = event.data.object
        sub_id = getattr(sub, "id", None)
        status = getattr(sub, "status", None)
        if sub_id and status:
            db_status = status  # Stripe: active/past_due/canceled/incomplete/trialing
            if status == "active":
                db_status = "active"
            elif status == "past_due":
                db_status = "past_due"
            elif status in ("canceled", "incomplete_expired"):
                db_status = "cancelled"
            elif status == "trialing":
                db_status = "trialing"
            update("licenses", {
                "status": db_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, {"stripe_subscription_id": sub_id})

    elif event.type == "invoice.payment_failed":
        """Handle failed payment — mark as past_due with grace period."""
        invoice = event.data.object
        sub_id = getattr(invoice, "subscription", None)
        customer_id = getattr(invoice, "customer", None)
        if sub_id:
            update("licenses", {
                "status": "past_due",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, {"stripe_subscription_id": sub_id})
        elif customer_id:
            update("licenses", {
                "status": "past_due",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, {"stripe_customer_id": customer_id})

    return {"received": True}