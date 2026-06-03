"""License API endpoints for the ObserveCo dashboard.

Registers:
  GET  /api/licenses/status        — current license state
  POST /api/licenses/activate      — activate a Pro key
  POST /api/licenses/trial         — start trial
  POST /api/licenses/validate      — ping validation server
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from observeco import license as lic

router = APIRouter(prefix="/api/licenses", tags=["licenses"])


class ActivateRequest(BaseModel):
    key: str
    email: str = ""
    plan: str = "solo"


class TrialRequest(BaseModel):
    confirm: bool = True


@router.get("/status")
async def license_status():
    """Return current license state."""
    return lic.status()


@router.get("/badge", response_class=HTMLResponse)
async def license_badge():
    """Return an HTML badge showing the current tier.
    Wire with: hx-get="/api/licenses/badge" hx-trigger="load, every 30s" hx-swap="outerHTML"
    """
    # Auto-consume expired trials on badge load
    lic.validate_cached()
    state = lic.load()
    is_pro = state.is_pro
    is_trial = state.license_type == "trial"
    is_consumed = state.trial_consumed
    days = state.remains_days
    plan = state.plan or "Solo"
    now_ts = int(time.time())

    if is_pro and is_trial:
        # Active trial
        label = f"TRIAL ({days}d)"
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#1e1b4b;border:1px solid #3730a3;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">🚀</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#c7d2fe;">{plan} plan — <span style="color:#a5b4fc;">{days}d left</span></span>
    <span style="font-size:10px;color:#64748b;">No charge until trial ends. Cancel anytime.</span>
  </div>
  <a href="/api/checkout?plan={plan.lower()}&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Subscribe $9/mo</a>
  <button onclick="showCancelTrialConfirm()" class="header-btn" style="background:transparent;border:1px solid #475569;color:#94a3b8;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;">Cancel Trial</button>
</div>""")
    elif is_pro and not is_trial:
        # Paid Pro subscriber
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#064e3b;border:1px solid #059669;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">✅</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#86efac;">Pro · {plan} plan</span>
    <span style="font-size:10px;color:#64748b;">Active subscription</span>
  </div>
  <button onclick="showManageBilling()" class="header-btn" style="background:#059669;color:white;padding:5px 14px;border-radius:6px;border:none;cursor:pointer;font-weight:600;font-size:11px;">Manage Billing →</button>
</div>""")
    elif is_consumed:
        # Trial was cancelled or expired and consumed
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#1c1917;border:1px solid #44403c;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">🔓</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#a8a29e;">Free · Trial ended</span>
    <span style="font-size:10px;color:#78716c;">Your data is safe. Subscribe to unlock Pro.</span>
  </div>
  <a href="/api/checkout?plan={plan.lower()}&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Subscribe $9/mo</a>
</div>""")
    elif state.license_type == "free" and state.trial_end and state.trial_end < now_ts:
        # Trial expired but not yet consumed (grace period)
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#1c1917;border:1px solid #dc2626;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">⚠️</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#fca5a5;">Free · Trial expired</span>
    <span style="font-size:10px;color:#a8a29e;">Pro features are now locked.</span>
  </div>
  <a href="/api/checkout?plan={plan.lower()}&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Restart $9/mo</a>
</div>""")
    else:
        # Fresh free — no trial yet
        return HTMLResponse("""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:var(--surface);border:1px solid var(--border);border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">🔓</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:var(--fg);">Free</span>
    <span style="font-size:10px;color:var(--muted);">No trial started</span>
  </div>
  <a href="/api/checkout?plan=solo&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Start Trial $9/mo</a>
</div>""")


@router.post("/activate")
async def activate_license(req: ActivateRequest):
    """Activate a Pro license key."""
    result = lic.activate_key(req.key, email=req.email, plan=req.plan)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/trial")
async def start_trial(req: TrialRequest):
    """Start 30-day trial."""
    if not req.confirm:
        raise HTTPException(400, "Must confirm trial start")
    result = lic.start_trial()
    return result


@router.post("/validate")
async def revalidate():
    """Force re-validation of the current license key."""
    state = lic.load()
    if not state.key:
        raise HTTPException(400, "No license key configured")
    from observeco.license import _validate_online
    result = _validate_online(state.key)
    if result.get("valid"):
        state.validated_at = int(time.time())
        lic.save(state)
        return {"status": "validated", "plan": result.get("plan", state.plan)}
    return {"status": "error", "message": result.get("error", "Validation failed")}


# ── Cancel Trial ──────────────────────────────────────────────

@router.post("/cancel-trial")
async def cancel_trial():
    """Cancel the current trial. Pro features lock, data preserved."""
    result = lic.cancel_trial()
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result
