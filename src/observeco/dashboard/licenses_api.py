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
    Wire with: hx-get="/api/licenses/badge" hx-trigger="load" hx-swap="outerHTML"
    """
    state = lic.load()
    is_pro = state.is_pro
    if is_pro:
        days = state.remains_days
        label = "PRO"
        if state.license_type == "trial":
            label = f"TRIAL ({days}d)"
        plan = state.plan or "Solo"
        return HTMLResponse(
            f'<span class="tier-badge" id="tierBadge" style="background:#3730a3;color:#a5b4fc;">🔒 {label}</span>'
        )
    return HTMLResponse(
        '<span class="tier-badge" id="tierBadge">🔓 FREE</span>'
    )


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
