"""Discover API — ecosystem gap scanning endpoints.

GET  /api/discover/gaps  — list gaps (cached 5min)
POST /api/discover/add   — register a gap as a tracked agent
"""

from fastapi import APIRouter, HTTPException
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


@router.post("/add")
def add_gap_endpoint(req: AddGapRequest):
    """Register a gap item as a tracked agent."""
    result = add_gap(req.name, req.framework, health_check=req.health_check)
    if result["status"] == "exists":
        raise HTTPException(status_code=409, detail=result["message"])
    return result