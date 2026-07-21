"""Discover API — ecosystem gap scanning endpoints.

GET  /api/discover/gaps     — list gaps (cached 5min)
POST /api/discover/add      — register a gap as a tracked agent
GET  /api/discover/panel    — HTML partial for discover panel (htmx target)
GET  /api/discover/learning — HTML partial for L3 learning loop stats
"""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from observeco.discover.scanner import add_gap, scan_cached
from observeco.db import Database

router = APIRouter(prefix="/api/discover", tags=["discover"])
db = Database()


class AddGapRequest(BaseModel):
    name: str
    framework: str = "custom"
    health_check: str = ""


def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


def _classify_gaps(gaps: list[dict]) -> dict:
    """Classify gaps into groups: newly_stopped, changed_behavior, never_seen."""
    # For now, all gaps are "never seen" since we don't have history tracking yet.
    # Future: check a dismiss/seen table to classify.
    return {
        "newly_stopped": [],
        "changed_behavior": [],
        "never_seen": gaps,
    }


def _render_gap_items(gaps: list[dict]) -> str:
    """Render a list of gap items as HTML rows."""
    rows = []
    for g in gaps:
        name = _html_escape(g["name"])
        reason = _html_escape(g.get("reason", "Not monitored"))
        fw = _html_escape(g.get("suggested_framework", "custom"))
        hc = _html_escape(g.get("health_check", ""))
        rows.append(
            f'<div class="item" id="gap-{name}">'
            f'<span class="name">{name}</span>'
            f'<span class="meta">{reason}</span>'
            f'<button class="btn add" hx-post="/api/discover/add" '
            f'hx-vals=\'{{"name":"{name}","framework":"{fw}","health_check":"{hc}"}}\' '
            f'hx-target="#gap-{name}" hx-swap="outerHTML">+ Add</button>'
            f'<button class="btn dismiss">✕</button>'
            f'</div>'
        )
    return "".join(rows)


def _render_section(icon: str, label: str, count: int, items_html: str, count_cls: str = "", expanded: bool = True) -> str:
    """Render a collapsible section."""
    chev = "▶" if expanded else "▶"
    return f"""<div class="section">
    <div class="section-h" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none';this.querySelector('.chev').classList.toggle('open')">
      <span class="icon">{icon}</span>
      <span class="label">{label}</span>
      <span class="count-badge {count_cls}">{count}</span>
      <span class="action">Add all</span>
      <span class="chev{' open' if expanded else ''}">{chev}</span>
    </div>
    <div class="items" style="display:{'block' if expanded else 'none'}">
      {items_html}
    </div>
  </div>"""


@router.get("/gaps")
def get_gaps():
    """Return ecosystem gaps (what's running but not tracked)."""
    return {"gaps": scan_cached()}


@router.get("/panel", response_class=HTMLResponse)
def get_panel():
    """HTML partial for the discover panel (htmx target)."""
    gaps = scan_cached()
    if not gaps:
        return (
            '<div class="discover-empty">✅ No gaps found — everything is being monitored</div>'
        )

    classified = _classify_gaps(gaps)
    total = len(gaps)

    # Build sections
    sections = ""

    # Newly stopped
    if classified["newly_stopped"]:
        sections += _render_section(
            "●", "Newly stopped", len(classified["newly_stopped"]),
            _render_gap_items(classified["newly_stopped"]),
            "red", True
        )

    # Changed behavior
    if classified["changed_behavior"]:
        sections += _render_section(
            "●", "Changed behavior", len(classified["changed_behavior"]),
            _render_gap_items(classified["changed_behavior"]),
            "yellow", True
        )

    # Never seen
    if classified["never_seen"]:
        sections += _render_section(
            "●", "Never seen", len(classified["never_seen"]),
            _render_gap_items(classified["never_seen"]),
            "", False
        )

    # Learning section
    learning_html = _get_learning_html()

    return f"""<div class="discover-panel" id="discoverPanel">
  <div class="panel-h">
    <h3>Discover</h3>
    <span class="count">{total} gaps</span>
    <span class="close" onclick="document.getElementById('discoverPanel').style.display='none'">✕</span>
  </div>
  <div class="mode-tabs">
    <div class="mode-tab active" onclick="document.querySelectorAll('.mode-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active');document.getElementById('discoverGaps').style.display='block';document.getElementById('discoverLearning').style.display='none'">What's new <span class="badge new">{len(classified['newly_stopped']) + len(classified['changed_behavior'])}</span></div>
    <div class="mode-tab" onclick="document.querySelectorAll('.mode-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active');document.getElementById('discoverGaps').style.display='block';document.getElementById('discoverLearning').style.display='none'">Everything <span class="badge all">{total}</span></div>
    <div class="mode-tab" onclick="document.querySelectorAll('.mode-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active');document.getElementById('discoverGaps').style.display='none';document.getElementById('discoverLearning').style.display='block'">Learning <span class="badge green">{len(learning_html['skills'])}</span></div>
  </div>
  <div class="bulk-bar">
    <button class="bulk-btn primary">+ Add all new</button>
    <button class="bulk-btn">Dismiss all seen</button>
  </div>
  <div id="discoverGaps">
    {sections}
  </div>
  <div id="discoverLearning" style="display:none;">
    {learning_html['html']}
  </div>
</div>"""


def _get_learning_html() -> dict:
    """Get L3 learning loop data from prevention_skills table."""
    try:
        conn = db._get_conn()
        skills = conn.execute(
            "SELECT agent_name, pattern_hash, success_count, fail_count, deprecated, "
            "COALESCE(created_at, '') as created_at, COALESCE(last_used_at, '') as last_used_at "
            "FROM prevention_skills ORDER BY created_at DESC"
        ).fetchall()

        total_skills = len(skills)
        total_applied = sum(s[2] + s[3] for s in skills)  # success + fail
        total_deprecated = sum(1 for s in skills if s[4])
        # Cost saved: each successful application saves ~$0.02 LLM call
        total_success = sum(s[2] for s in skills)
        cost_saved = total_success * 0.02

        skill_rows = []
        for s in skills:
            agent = _html_escape(s[0])
            success = s[2]
            fail = s[3]
            dep = s[4]
            # Get trigger conditions for display
            trigger = conn.execute(
                "SELECT error_signature FROM prevention_skills_fts WHERE agent_name = ? LIMIT 1",
                (s[0],)
            ).fetchone()
            pattern = _html_escape(trigger[0][:60]) if trigger else "—"
            tag = "deprecated" if dep else "active"
            tag_cls = "deprecated" if dep else "active"

            skill_rows.append(
                f'<div class="learn-skill">'
                f'<span class="name">{agent}</span>'
                f'<span class="pattern">{pattern}</span>'
                f'<span class="stats"><span class="ok">✓ {success}</span> · <span class="fail">✗ {fail}</span></span>'
                f'<span class="tag {tag_cls}">{tag}</span>'
                f'</div>'
            )

        skills_html = "".join(skill_rows) if skill_rows else (
            '<div class="empty-state">'
            '<div class="ico">🧠</div>'
            '<p>No prevention skills yet. Skills are created automatically after the system heals a novel failure.</p>'
            '</div>'
        )

        html = f"""<div class="section" style="border-top:2px solid #22c55e;">
    <div class="section-h">
      <span class="icon" style="color:#22c55e;">●</span>
      <span class="label" style="color:#22c55e;">Learning</span>
      <span class="count-badge green">{total_skills} skills</span>
      <span class="chev open">▶</span>
    </div>
    <div class="learn-stat">
      <div class="stat-card">
        <div class="num green">{total_skills}</div>
        <div class="lbl">Skills created</div>
      </div>
      <div class="stat-card">
        <div class="num yellow">{total_applied}</div>
        <div class="lbl">Times applied</div>
      </div>
      <div class="stat-card">
        <div class="num green">${cost_saved:.2f}</div>
        <div class="lbl">LLM cost saved</div>
      </div>
      <div class="stat-card">
        <div class="num red">{total_deprecated}</div>
        <div class="lbl">Deprecated</div>
      </div>
    </div>
    <div class="items">
      {skills_html}
    </div>
  </div>"""

        return {"html": html, "skills": skills}

    except Exception:
        return {"html": "", "skills": []}


@router.get("/learning", response_class=HTMLResponse)
def get_learning():
    """HTML partial for L3 learning loop stats (htmx target)."""
    data = _get_learning_html()
    return data["html"]


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
        f'<div class="item" id="gap-{req.name}" style="opacity:0.5;">'
        f'<span class="name">{req.name}</span>'
        f'<span class="meta" style="color:#22c55e;">✓ added</span></div>'
    )
    return Response(content=html, media_type="text/html")
