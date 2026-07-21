"""Discover API — ecosystem gap scanning endpoints.

GET  /api/discover/gaps      — list gaps (cached 5min)
POST /api/discover/add       — register a gap as a tracked agent
POST /api/discover/add-all   — batch register gaps
POST /api/discover/dismiss   — dismiss a gap (never show again)
POST /api/discover/dismiss-all — dismiss all gaps
GET  /api/discover/panel     — HTML partial for discover panel (htmx target)
GET  /api/discover/learning  — HTML partial for L3 learning loop stats
"""

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
        "newly_stopped": [],
        "changed_behavior": [],
        "never_seen": active,
        "dismissed_count": len(gaps) - len(active),
    }


def _render_gap_items(gaps: list[dict], limit: int = 0) -> str:
    """Render a list of gap items as HTML rows. If limit > 0, truncate and add 'show all'."""
    show_all = limit > 0 and len(gaps) > limit
    items = gaps[:limit] if show_all else gaps
    rows = []
    for g in items:
        name = _html_escape(g["name"])
        reason = _html_escape(g.get("reason", "Not monitored"))
        fw = _html_escape(g.get("suggested_framework", "custom"))
        hc = _html_escape(g.get("health_check", ""))
        rows.append(
            f'<div class="item" id="gap-{name}" onclick="htmx.ajax(\'GET\', \'/api/agent/{name}/profile\', {{target:\'#modalContainer\', swap:\'innerHTML\'}})" style="cursor:pointer">'
            f'<span class="name">{name}</span>'
            f'<span class="meta">{reason}</span>'
            f'<button class="btn add" hx-post="/api/discover/add" '
            f'hx-vals=\'{{"name":"{name}","framework":"{fw}","health_check":"{hc}"}}\' '
            f'hx-target="#gap-{name}" hx-swap="outerHTML" onclick="event.stopPropagation()">+ Add</button>'
            f'<button class="btn dismiss" hx-post="/api/discover/dismiss" '
            f'hx-vals=\'{{"name":"{name}"}}\' '
            f'hx-target="#gap-{name}" hx-swap="outerHTML" onclick="event.stopPropagation()">✕</button>'
            f'</div>'
        )
    html = "".join(rows)
    if show_all:
        remaining = len(gaps) - limit
        html += f'<div class="show-all" onclick="this.previousElementSibling.previousElementSibling?this.previousElementSibling.insertAdjacentHTML(\'beforebegin\',\'<div>loading…</div>\'):null;htmx.ajax(\'GET\',\'/api/discover/gaps-html?all=true\',{{target:this.parentElement,swap:\'innerHTML\'}});this.remove()" style="text-align:center;padding:8px;font-size:12px;color:#3b82f6;cursor:pointer">Show all {remaining} more ▾</div>'
    return html


def _render_section(icon: str, label: str, count: int, items_html: str, count_cls: str = "", expanded: bool = True) -> str:
    """Render a collapsible section."""
    return f"""<div class="section">
    <div class="section-h" onclick="var n=this.nextElementSibling;if(n&&n.classList.contains('items')){{var d=n.style.display;n.style.display=d==='none'?'block':'none';this.querySelector('.chev').classList.toggle('open')}}">
      <span class="icon">{icon}</span>
      <span class="label">{label}</span>
      <span class="count-badge {count_cls}">{count}</span>
      <span class="action" onclick="event.stopPropagation();var items=this.closest('.section').querySelectorAll('.item');items.forEach(function(it){{var btn=it.querySelector('.btn.add');if(btn)btn.click()}})">Add all</span>
      <span class="chev{' open' if expanded else ''}">▶</span>
    </div>
    <div class="items" style="display:{'block' if expanded else 'none'}">
      {items_html}
    </div>
  </div>"""


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/gaps")
def get_gaps():
    """Return ecosystem gaps (what's running but not tracked)."""
    return {"gaps": scan_cached()}


@router.get("/gaps-html", response_class=HTMLResponse)
def get_gaps_html(all: bool = False):
    """Return just the gap items HTML (for lazy loading 'show all')."""
    gaps = scan_cached()
    classified = _classify_gaps(gaps)
    never_seen = classified["never_seen"]
    if all:
        return _render_gap_items(never_seen, limit=0)
    return _render_gap_items(never_seen, limit=20)


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
    active = classified["never_seen"]
    dismissed_count = classified["dismissed_count"]

    # Build sections — only "Never seen" since we have no history tracking yet
    sections = ""
    if active:
        sections += _render_section(
            "●", "Never seen", len(active),
            _render_gap_items(active, limit=20),
            "", True  # expanded by default
        )

    # Learning section
    learning_html = _get_learning_html()

    return f"""<div class="discover-panel" id="discoverPanel">
  <div class="panel-h">
    <h3>Discover</h3>
    <span class="count">{total} gaps{f' · {dismissed_count} dismissed' if dismissed_count else ''}</span>
    <span class="close" onclick="document.getElementById('discoverPanel').style.display='none'">✕</span>
  </div>
  <div class="mode-tabs">
    <div class="mode-tab active" onclick="document.querySelectorAll('.mode-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active');document.getElementById('discoverGaps').style.display='block';document.getElementById('discoverLearning').style.display='none'">Gaps <span class="badge all">{len(active)}</span></div>
    <div class="mode-tab" onclick="document.querySelectorAll('.mode-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active');document.getElementById('discoverGaps').style.display='none';document.getElementById('discoverLearning').style.display='block'">Learning <span class="badge green">{len(learning_html['skills'])}</span></div>
  </div>
  <div class="bulk-bar">
    <button class="bulk-btn primary" hx-post="/api/discover/add-all" hx-vals='{{"names":{_html_escape(str([g['name'] for g in active]))}}}' hx-target="#discoverGaps" hx-swap="innerHTML">+ Add all</button>
    <button class="bulk-btn" hx-post="/api/discover/dismiss-all" hx-target="#discoverGaps" hx-swap="innerHTML">Dismiss all</button>
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


@router.get("/learning", response_class=HTMLResponse)
def get_learning():
    """HTML partial for L3 learning loop stats (htmx target)."""
    data = _get_learning_html()
    return data["html"]


@router.post("/add")
def add_gap_endpoint(req: AddGapRequest):
    """Register a gap item as a tracked agent."""
    result = add_gap(req.name, req.framework, health_check=req.health_check)
    if result["status"] == "exists":
        raise HTTPException(status_code=409, detail=result["message"])
    html = (
        f'<div class="item" id="gap-{req.name}" style="opacity:0.5;">'
        f'<span class="name">{req.name}</span>'
        f'<span class="meta" style="color:#22c55e;">✓ added</span></div>'
    )
    return Response(content=html, media_type="text/html")


@router.post("/add-all")
def add_all_gaps(req: BatchGapRequest):
    """Batch register multiple gaps."""
    results = []
    for name in req.names:
        result = add_gap(name)
        results.append({"name": name, "status": result["status"]})
    # Return updated gaps view
    return get_panel()


@router.post("/dismiss")
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
    html = (
        f'<div class="item" id="gap-{req.name}" style="opacity:0.3;">'
        f'<span class="name" style="text-decoration:line-through;">{req.name}</span>'
        f'<span class="meta" style="color:#64748b;">dismissed</span></div>'
    )
    return Response(content=html, media_type="text/html")


@router.post("/dismiss-all")
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
    return '<div class="empty-state" style="text-align:center;padding:24px;color:#64748b;font-size:12px;">✅ All gaps dismissed. <button class="bulk-btn" style="margin-top:8px;" onclick="document.getElementById(\'discoverBadge\')?.click()">Undo</button></div>'
