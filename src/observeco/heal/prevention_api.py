"""Prevention Skills API — dashboard htmx endpoints.

GET  /api/prevention/panel    — HTML partial: list of prevention skills
POST /api/prevention/remove/{id} — delete a prevention skill (htmx)
"""

from fastapi import APIRouter, HTTPException, Response

from observeco.heal import prevention as prev

router = APIRouter(prefix="/api/prevention", tags=["prevention"])


@router.get("/panel")
def get_panel():
    """HTML partial for the prevention panel (htmx target)."""
    skills = prev.list_skills()
    if not skills:
        return Response(
            content='<div class="discover-empty">🤖 No prevention skills yet — '
                    'they appear after successful heals with learning enabled.</div>',
            media_type="text/html",
        )

    rows = []
    for s in skills:
        sid = s["id"]
        agent = s.get("agent_name", "?")
        diag = (s.get("diagnosis", "") or "")[:50]
        s.get("created_at", "")
        ok = s.get("success_count", 0)
        fail = s.get("fail_count", 0)
        deprecated = " (deprecated)" if s.get("deprecated") else ""
        rows.append(
            f'<div class="discover-row" id="skill-{sid}">'
            f'<span class="gap-name">{agent}{deprecated}</span>'
            f'<span class="gap-reason" title="{s.get("diagnosis", "")}">{diag}</span>'
            f'<span class="gap-stats">{ok}✓ {fail}✗</span>'
            f'<button class="gap-add" hx-post="/api/prevention/remove/{sid}" '
            f'hx-target="#skill-{sid}" hx-swap="outerHTML" '
            f'style="background:#ef4444;">Delete</button></div>'
        )

    body = "".join(rows)
    return Response(
        content=(
            f'<div class="discover-head">{len(skills)} prevention skill(s) — '
            f'known failures fixed without LLM</div>{body}'
        ),
        media_type="text/html",
    )


@router.post("/remove/{skill_id}")
def remove_skill(skill_id: int):
    """Delete a prevention skill (htmx POST)."""
    # verify it exists
    skills = [s for s in prev.list_skills() if s["id"] == skill_id]
    if not skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    prev.remove_skill(skill_id)
    return Response(
        content=f'<div class="discover-row gap-added-row" id="skill-{skill_id}">'
                f'<span class="gap-name">🗑️ deleted</span></div>',
        media_type="text/html",
    )
