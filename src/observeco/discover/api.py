"""Discover API — ecosystem gap scanning endpoints.

GET  /api/discover/coverage   — HTML for Coverage tab (obs-spec-082)
POST /api/discover/add        — register a gap as a tracked agent
POST /api/discover/add-all    — batch register gaps
POST /api/discover/dismiss    — dismiss a gap (never show again)
POST /api/discover/dismiss-all — dismiss all gaps
GET  /api/discover/count      — lightweight JSON badge count
GET  /api/discover/learning   — HTML partial for L3 learning loop stats
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from observeco.discover.scanner import add_gap, scan_cached
from observeco.db import Database

router = APIRouter(prefix="/api/discover", tags=["discover"])
db = Database()

# ── Pydantic models ────────────────────────────────────────────────

class AddGapRequest(BaseModel):
    name: str
    framework: str = "custom"
    health_check: str = ""

class BatchGapRequest(BaseModel):
    names: list[str]

class DismissGapRequest(BaseModel):
    name: str

# ── Helpers ────────────────────────────────────────────────────────

def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


def _get_dismissed() -> set[str]:
    """Get set of dismissed gap names from DB."""
    try:
        conn = db._get_conn()
        rows = conn.execute("SELECT gap_name FROM dismissed_gaps").fetchall()
        return {r[0].lower() for r in rows}
    except Exception:
        return set()


def _classify_gaps(gaps: list[dict]) -> dict:
    """Classify gaps into groups, filtering dismissed ones."""
    dismissed = _get_dismissed()
    active = [g for g in gaps if g["name"].lower() not in dismissed]
    return {
        "never_seen": active,
        "dismissed_count": len(gaps) - len(active),
    }


def _render_gap_table(gaps: list[dict], limit: int = 20) -> str:
    """Render gap items as table rows for the Coverage tab."""
    show_all = limit > 0 and len(gaps) > limit
    items = gaps[:limit] if show_all else gaps
    rows = []
    for g in items:
        name = _html_escape(g["name"])
        fw = _html_escape(g.get("suggested_framework", "custom"))
        hc = _html_escape(g.get("health_check", ""))
        rows.append(
            f'<div class="gap-row" data-name="{name}">'
            f'<span class="gap-name">{name}</span>'
            f'<span class="gap-framework">{fw}</span>'
            f'<span class="gap-status">\u25cf</span>'
            f'<span class="gap-actions">'
            f'<button class="btn add" hx-post="/api/discover/add" '
            f'hx-vals=\'{{"name":"{name}","framework":"{fw}","health_check":"{hc}"}}\' '
            f'hx-target="#coverageContainer" hx-swap="innerHTML">+ Add</button>'
            f'<button class="btn dismiss" hx-post="/api/discover/dismiss" '
            f'hx-vals=\'{{"name":"{name}"}}\' '
            f'hx-target="#coverageContainer" hx-swap="innerHTML">\u2715</button>'
            f'</span>'
            f'</div>'
        )
    html = "".join(rows)
    if show_all:
        remaining = len(gaps) - limit
        html += (
            f'<div class="show-all" style="text-align:center;padding:8px;font-size:12px;color:#3b82f6;cursor:pointer" '
            f'onclick="this.remove();htmx.ajax(\'GET\',\'/api/discover/coverage?all=1\','
            f'{{target:\'#coverageContainer\',swap:\'innerHTML\'}})\">Show all {remaining} more &#9662;</div>'
        )
    return html


def _render_coverage(all_gaps: bool = False) -> str:
    """Return full Coverage tab HTML as a plain string."""
    gaps = scan_cached()

    if not gaps:
        return """<div class="coverage-header">
    <h2>Coverage</h2>
    <span class="coverage-meta">0 untracked · 0 dismissed</span>
  </div>
  <div class="coverage-table">
    <div class="coverage-empty" style="padding:32px;text-align:center;color:#64748b;">
      <span style="font-size:24px;">&#9989;</span>
      <p style="margin:8px 0 0;font-size:13px;">Everything running is tracked</p>
    </div>
  </div>"""

    classified = _classify_gaps(gaps)
    total = len(gaps)
    active = classified["never_seen"]
    dismissed_count = classified["dismissed_count"]

    limit = 0 if all_gaps else 20
    table_html = _render_gap_table(active, limit=limit)

    learning_data = _get_learning_html()
    now_str = datetime.now().strftime("%H:%M")

    add_all_js = (
        "js:{names: Array.from(document.querySelectorAll('#coverageTable .gap-row'))"
        ".map(function(r){return r.dataset.name})}"
    )

    return f"""<div class="coverage-header">
    <h2>Coverage</h2>
    <span class="coverage-meta">{len(active)} untracked &middot; {dismissed_count} dismissed &middot; Updated {now_str}</span>
  </div>
  <div class="coverage-toolbar">
    <input type="text" placeholder="Search gaps..." class="coverage-search" id="coverageSearch">
    <div class="coverage-filters">
      <button class="filter-btn active">All</button>
      <button class="filter-btn">Dismissed</button>
    </div>
  </div>
  <div class="coverage-bulk">
    <button class="bulk-btn primary" hx-post="/api/discover/add-all"
      hx-vals=\"{add_all_js}\"
      hx-target="#coverageContainer" hx-swap="innerHTML">+ Add all</button>
    <button class="bulk-btn" hx-post="/api/discover/dismiss-all"
      hx-target="#coverageContainer" hx-swap="innerHTML">Dismiss all</button>
  </div>
  <div id="coverageTable" class="coverage-table">
    {table_html}
  </div>
  <div class="coverage-learning">
    {learning_data['html']}
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
        total_applied = sum(s[2] + s[3] for s in skills)
        total_deprecated = sum(1 for s in skills if s[4])
        total_success = sum(s[2] for s in skills)
        cost_saved = total_success * 0.02

        skill_rows = []
        for s in skills:
            agent = _html_escape(s[0])
            success = s[2]
            fail = s[3]
            dep = s[4]
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

        if skill_rows:
            skills_html = "".join(skill_rows)
        else:
            skills_html = (
                '<div class="empty-state">'
                '<p style="color:#64748b;font-size:12px;">No prevention skills yet. '
                'The L3 learning loop creates skills automatically after healing novel failures. '
                'Enable with <code style="color:#22c55e;">observeco heal --learn</code>.</p>'
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


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/count")
def get_count():
    """Return gap count as JSON for badge refresh."""
    gaps = scan_cached()
    classified = _classify_gaps(gaps)
    return {"count": len(classified["never_seen"])}


@router.get("/coverage", response_class=HTMLResponse)
def get_coverage(all: bool = False):
    """HTML for the Coverage tab (full page content)."""
    return _render_coverage(all_gaps=all)


@router.get("/learning", response_class=HTMLResponse)
def get_learning():
    """HTML partial for L3 learning loop stats (htmx target)."""
    data = _get_learning_html()
    return data["html"]


@router.post("/add", response_class=HTMLResponse)
def add_gap_endpoint(req: AddGapRequest):
    """Register a gap item as a tracked agent."""
    result = add_gap(req.name, req.framework, health_check=req.health_check)
    if result["status"] == "exists":
        raise HTTPException(status_code=409, detail=result["message"])
    return _render_coverage()


@router.post("/add-all", response_class=HTMLResponse)
def add_all_gaps(req: BatchGapRequest):
    """Batch register multiple gaps."""
    for name in req.names:
        add_gap(name)
    return _render_coverage()


@router.post("/dismiss", response_class=HTMLResponse)
def dismiss_gap(req: DismissGapRequest):
    """Dismiss a gap (never show again)."""
    try:
        conn = db._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO dismissed_gaps (gap_name, dismissed_at) VALUES (?, datetime('now'))",
            (req.name.lower(),)
        )
        conn.commit()
    except Exception:
        pass
    from observeco.discover.scanner import _cache
    _cache["gaps"] = None
    return _render_coverage()


@router.post("/dismiss-all", response_class=HTMLResponse)
def dismiss_all_gaps():
    """Dismiss all current gaps."""
    gaps = scan_cached()
    try:
        conn = db._get_conn()
        for g in gaps:
            conn.execute(
                "INSERT OR REPLACE INTO dismissed_gaps (gap_name, dismissed_at) VALUES (?, datetime('now'))",
                (g["name"].lower(),)
            )
        conn.commit()
    except Exception:
        pass
    return _render_coverage()
