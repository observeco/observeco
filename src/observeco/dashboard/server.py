"""Dashboard server — FastAPI + htmx single-pane agent observability."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from observeco.db import Database
from observeco.billing import add_billing_endpoints
from observeco.dashboard.otel import router as otel_router

app = FastAPI(title="ObserveCo Dashboard")
db = Database()

# Register endpoints
add_billing_endpoints(app)
app.include_router(otel_router)

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main dashboard page."""
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard</h1><p>Template not found.</p>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/api/agents", response_class=HTMLResponse)
async def api_agents():
    """Agent fleet status cards (htmx fragment)."""
    summary = db.get_agent_status_summary()
    agents = db.get_agents()
    breakers = {b["agent_name"]: b for b in db.get_circuit_breakers()}

    cards = []
    all_agent_names = set()
    for a in agents:
        all_agent_names.add(a["agent_name"])
    for name, status in summary.items():
        all_agent_names.add(name)

    for name in sorted(all_agent_names):
        s = summary.get(name, {})
        status = s.get("status", "unknown")
        latency = s.get("latency_ms", 0)
        cb = breakers.get(name, {})
        tripped = cb.get("tripped", 0)

        dot_color = {"alive": "#22c55e", "dead": "#ef4444", "error": "#f59e0b"}.get(status, "#6b7280")
        status_text = {"alive": "Alive", "dead": "Dead", "error": "Error"}.get(status, "Unknown")

        cards.append(f"""<div class="agent-card" data-agent="{name}">
    <div class="card-header">
        <span class="status-dot" style="background: {dot_color}" title="{status_text}"></span>
        <span class="agent-name">{name}</span>
        <span class="agent-framework">{s.get("agent_framework", "hermes")}</span>
    </div>
    <div class="card-body">
        <div class="metric-row">
            <span class="metric-label">Status</span>
            <span class="metric-value status-{status}">{status_text}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Latency</span>
            <span class="metric-value">{f"{latency:.0f}ms" if latency else "-"}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Circuit</span>
            <span class="metric-value">{'🔴 TRIPPED' if tripped else '✅ OK'}</span>
        </div>
    </div>
</div>""")

    return HTMLResponse("".join(cards))


@app.get("/api/errors", response_class=HTMLResponse)
async def api_errors():
    """Error timeline fragment."""
    errors = db.get_errors(limit=20)
    items = []
    for e in errors:
        sev_color = {"error": "red", "warning": "orange", "info": "gray"}.get(e["severity"], "gray")
        items.append(f"""<div class="error-item severity-{e['severity']}">
    <span class="error-ts">{e['timestamp']}</span>
    <span class="error-agent">{e['agent_name']}</span>
    <span class="error-type" style="color:{sev_color}">{e['error_type']}</span>
    <span class="error-msg">{e['error_message'][:80]}</span>
</div>""")

    if not items:
        return HTMLResponse('<div class="empty-state">No errors recorded</div>')
    return HTMLResponse("".join(items[:10]))


@app.get("/api/token-summary", response_class=HTMLResponse)
async def api_token_summary():
    """Token profile summary fragment."""
    trims = db.get_trims(limit=30)
    if not trims:
        return HTMLResponse('<div class="empty-state">No token data yet. Run <code>observeco chisel trim</code> to start collecting.</div>')

    # Latest trim per agent
    agents_trim: dict[str, dict] = {}
    for t in trims:
        aname = t["agent_name"]
        if aname not in agents_trim:
            agents_trim[aname] = t

    bars = []
    for aname, t in sorted(agents_trim.items()):
        total = t.get("total_tokens", 1)
        comps = [
            ("identity", t.get("identity_tokens", 0)),
            ("skills", t.get("skills_tokens", 0)),
            ("memory", t.get("memory_tokens", 0)),
            ("tools", t.get("tools_tokens", 0)),
            ("guidance", t.get("guidance_tokens", 0)),
        ]
        segments = "".join(
            f'<span class="token-segment seg-{comp}" style="width:{v/max(total,1)*100:.1f}%" title="{comp}: {v} tok"></span>'
            for comp, v in comps
        )
        bars.append(f"""<div class="token-bar-row">
    <span class="bar-label">{aname}</span>
    <div class="token-bar">{segments}</div>
    <span class="bar-total">{total} tok</span>
</div>""")

    return HTMLResponse("".join(bars))


@app.get("/api/drift-summary", response_class=HTMLResponse)
async def api_drift_summary():
    """Drift breach summary fragment."""
    drift = db.get_drift()
    if not drift:
        return HTMLResponse('<div class="empty-state">No drift data yet.</div>')

    breaches = [d for d in drift if d.get("breached")]
    if not breaches:
        return HTMLResponse('<div class="empty-state">✅ No drift breaches</div>')

    items = []
    for b in breaches[:5]:
        items.append(f"""<div class="drift-item">
    <span class="drift-agent">{b['agent_name']}</span>
    <span class="drift-comp">{b['component']}</span>
    <span class="drift-delta">{b['delta_pct']:+.1f}%</span>
</div>""")

    return HTMLResponse("".join(items))


@app.get("/api/garden-summary", response_class=HTMLResponse)
async def api_garden_summary():
    """Memory debt scores fragment."""
    gardens = db.get_gardens()
    if not gardens:
        return HTMLResponse('<div class="empty-state">No garden data yet. Run <code>observeco clawforge garden</code>.</div>')

    items = []
    for g in gardens[:5]:
        score = g.get("memory_debt_score", 0)
        grade = "A" if score < 20 else "B" if score < 40 else "C" if score < 60 else "D" if score < 80 else "F"
        items.append(f"""<div class="garden-item">
    <span class="garden-agent">{g['agent_name']}</span>
    <span class="garden-debt">Debt: {score:.0f}</span>
    <span class="garden-grade">Grade: {grade}</span>
    <span class="garden-details">Dup: {g['duplicates_found']} Con: {g['contradictions_found']} Stale: {g['stale_entries']}</span>
</div>""")

    return HTMLResponse("".join(items))


@app.get("/api/fleet-summary", response_class=HTMLResponse)
async def api_fleet_summary():
    """Fleet header with health counts."""
    summary = db.get_agent_status_summary()
    total = len(summary) if summary else 0
    alive = sum(1 for s in summary.values() if s.get("status") == "alive")
    dead = sum(1 for s in summary.values() if s.get("status") == "dead")
    error_count = sum(1 for s in summary.values() if s.get("status") == "error")

    return HTMLResponse(f"""<div class="fleet-stats">
    <div class="stat-box total"><span class="stat-num">{total}</span> Agents</div>
    <div class="stat-box alive"><span class="stat-num">{alive}</span> Alive</div>
    <div class="stat-box dead"><span class="stat-num">{dead}</span> Dead</div>
    <div class="stat-box error"><span class="stat-num">{error_count}</span> Errors</div>
</div>""")


def serve(host: str = "127.0.0.1", port: int = 9119, static: bool = False) -> None:
    """Start the dashboard server."""
    import webbrowser
    url = f"http://{host}:{port}"
    webbrowser.open(url)
    print(f"ObserveCo Dashboard: {url}")
    uvicorn.run(app, host=host, port=port, log_level="info")
