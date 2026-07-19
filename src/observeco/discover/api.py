"""Discover API — ecosystem gap scanning endpoints.

GET  /api/discover/gaps  — list gaps (cached 5min)
POST /api/discover/add   — register a gap as a tracked agent
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from observeco.discover.scanner import add_gap, scan_cached

router = APIRouter(prefix="/api/discover", tags=["discover"])


class AddGapRequest(BaseModel):
    name: str
    framework: str = "custom"
    health_check: str = ""


@router.get("/gaps")
def get_gaps():
    """Return ecosystem gaps (what's running but not tracked)."""
    return {"gaps": scan_cached()}


@router.get("/panel")
def get_panel():
    """HTML partial for the discover panel (htmx target)."""
    gaps = scan_cached()
    if not gaps:
        return (
            '<div class="discover-empty">✅ No gaps found — everything is being monitored</div>'
        )
    rows = []
    for g in gaps:
        name = g["name"]
        fw = g.get("suggested_framework", "custom")
        hc = g.get("health_check", "")
        reason = g.get("reason", "Not monitored")
        rows.append(
            f'<div class="discover-row" id="gap-{name}">'
            f'<span class="gap-name">{name}</span>'
            f'<span class="gap-reason">{reason}</span>'
            f'<button class="gap-add" hx-post="/api/discover/add" '
            f'hx-vals=\'{{"name":"{name}","framework":"{fw}","health_check":"{hc}"}}\' '
            f'hx-target="#gap-{name}" hx-swap="outerHTML">Add</button></div>'
        )
    body = "".join(rows)
    return (
        f'<div class="discover-head">{len(gaps)} gap(s) found — click Add to monitor</div>'
        f'{body}'
    )


@router.post("/add")
def add_gap_endpoint(req: AddGapRequest):
    """Register a gap item as a tracked agent.

    Returns HTML for htmx (row replaced with 'added' state) or JSON
    for API callers (Accept: application/json).
    """
    result = add_gap(req.name, req.framework, health_check=req.health_check)
    if result["status"] == "exists":
        raise HTTPException(status_code=409, detail=result["message"])
    # HTML for htmx swap (row -> "added" line)
    html = (
        f'<div class="discover-row gap-added-row" id="gap-{req.name}">'
        f'<span class="gap-name">{req.name}</span>'
        f'<span class="gap-added">✓ added</span></div>'
    )
    return Response(content=html, media_type="text/html")
