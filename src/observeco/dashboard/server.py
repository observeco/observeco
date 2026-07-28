"""Dashboard server — FastAPI + htmx single-pane agent observability.

Spec: specs/unified-dashboard.md
  §5 Color System, §6 Layout Wireframe, §7 Conversion Funnel, §7.1 Locked Tiles,
  §7.2 Token Bar, §7.3 Responsive, §7.4 Error States, §8 First-Run Experience,
  §4.2.7 Framework-Specific Display, §6.3 Agent Detail, §6.4 Alerts, §6.5 Error Timeline
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sqlite3 as _sqlite3
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from observeco.api import router as api_router
from observeco.billing import add_billing_endpoints
from observeco.config import hermes_home
from observeco.dashboard.commercial_api import router as commercial_router
from observeco.dashboard.config import PORTS
from observeco.dashboard.licenses_api import router as licenses_router
from observeco.dashboard.otel import router as otel_router
from observeco.dashboard.routes.alerts import router as alerts_router
from observeco.dashboard.routes.capability import router as capability_router
from observeco.dashboard.routes.detail import router as detail_router
from observeco.dashboard.routes.efficiency import router as efficiency_router
from observeco.dashboard.routes.error_timeline import router as timeline_router
from observeco.dashboard.routes.fleet import router as fleet_router
from observeco.dashboard.routes.fleet_qb import router as fleet_qb_router
from observeco.dashboard.routes.harness_opt import router as harness_opt_router
from observeco.dashboard.routes.inbox import router as inbox_router
from observeco.dashboard.routes.token_analytics import router as analytics_router
from observeco.db import Database
from observeco.dirs import get_data_dir
from observeco.discover.api import router as discover_router
from observeco.realtime import router as realtime_router

logger = logging.getLogger(__name__)


# Shared heartbeat path — watch daemon writes this every 30s.
# Dashboard reads it to detect if the daemon is alive.
# ponytail: lazy property to avoid crash on import when data dir is unwritable
def _get_heartbeat_path() -> Path:
    return get_data_dir() / ".watch_heartbeat.json"

# Token component colors (matching mockup design system)
COMP_COLORS = {"identity": "#6366f1", "skills": "#8b5cf6", "memory": "#ec4899",
               "tools": "#14b8a6", "guidance": "#f97316"}
COMP_NAMES = {"identity": "Identity", "skills": "Skills", "memory": "Memory",
              "tools": "Tools", "guidance": "Guidance"}
COMP_ORDER = ["skills", "tools", "memory", "guidance", "identity"]

app = FastAPI(title="ObserveCo Dashboard")
db = Database()

# Initialize dashboard auth at module level (for TestClient compatibility).
# serve() re-initializes with the persisted secret on actual launch.
from observeco.dashboard.auth import init_auth as _init_auth  # noqa: E402

_dash_secret = _init_auth(app)
app.state.dashboard_secret = _dash_secret

# --- Auth setup ---
from observeco.auth.oauth2 import OAuth2Provider  # noqa: E402

auth_provider = OAuth2Provider()

# Register billing + OTel + feedback + license endpoints
add_billing_endpoints(app)
app.include_router(otel_router)
app.include_router(api_router)
app.include_router(efficiency_router)
app.include_router(realtime_router)
app.include_router(licenses_router)
app.include_router(commercial_router)
app.include_router(discover_router)
app.include_router(inbox_router)
app.include_router(fleet_router)
app.include_router(fleet_qb_router)
app.include_router(alerts_router)
app.include_router(timeline_router)
app.include_router(detail_router)
app.include_router(analytics_router)
app.include_router(capability_router)
app.include_router(harness_opt_router)

# --- Startup: initialise first_run_at, log license state ---
# Trial is NOT auto-started here. It starts on explicit Pro feature access
# or when the user clicks "Start Free Trial". See commercial-scope.md §7.
@app.on_event("startup")
async def startup_license_check():
    from observeco import license as lic
    state = lic.load()
    if state.first_run_at is None:
        state.first_run_at = int(time.time())
        lic.save(state)
    if state.license_type == "trial":
        _log_license = f"trial mode ({state.remains_days}d remaining)"
    elif state.license_type == "pro":
        _log_license = "pro mode"
    else:
        _log_license = f"free mode ({state.license_type})"
    print(f"[license] {_log_license}")


# ---------------------------------------------------------------------------
# § Feedback ingestion endpoint
# ---------------------------------------------------------------------------


@app.post("/v1/feedback")
async def ingest_feedback(request: Request):
    """Accept feedback from the CLI or GitHub issues and deliver it."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    required = ["summary"]
    for field in required:
        if not body.get(field):
            return JSONResponse({"error": f"missing field: {field}"}, status_code=400)

    from observeco.feedback_delivery import deliver_feedback
    delivery_result = deliver_feedback(body)
    db.save_feedback(body, delivered_tg=delivery_result.get("telegram", False),
                    delivered_email=delivery_result.get("email", False))

    return JSONResponse({
        "status": "ok",
        "delivery": delivery_result,
    })


@app.get("/v1/feedback")
async def list_feedback(limit: int = 50):
    """List recent feedback entries (for dashboard)."""
    items = db.get_feedback(limit=limit)
    return JSONResponse({"count": len(items), "items": items})

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_ts(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta.total_seconds() < 60:
        return f"{int(delta.total_seconds())}s ago"
    elif delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() / 60)}m ago"
    elif delta.total_seconds() < 86400:
        return f"{int(delta.total_seconds() / 3600)}h ago"
    return f"{int(delta.total_seconds() / 86400)}d ago"


def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


# ---------------------------------------------------------------------------
# § Auth endpoints — OAuth2 login/logout/callback
# ---------------------------------------------------------------------------


@app.get("/auth/login")
async def auth_login(provider: str = ""):
    """Initiate OAuth2 login."""
    if provider:
        auth_provider.provider = provider
    if not auth_provider.is_configured():
        # Local mode — create session directly
        session = auth_provider._create_local_session("local@local.local", "Local User")
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse(url="/")
        resp.set_cookie("observeco_token", session.token, httponly=True, secure=os.environ.get("OBSERVECO_HTTPS") == "1", samesite="lax", max_age=604800)
        return resp
    url = auth_provider.get_authorization_url(state=secrets.token_urlsafe(16))
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)


@app.get("/auth/callback")
async def auth_callback(code: str = "", state: str = ""):
    """OAuth2 callback — exchange code for session."""
    if not code:
        return HTMLResponse("<h1>Missing authorization code</h1>", status_code=400)
    session = auth_provider.exchange_code(code, state=state)
    if not session:
        return HTMLResponse("<h1>Authentication failed</h1>", status_code=401)
    from fastapi.responses import RedirectResponse
    resp = RedirectResponse(url="/")
    resp.set_cookie("observeco_token", session.token, httponly=True, secure=os.environ.get("OBSERVECO_HTTPS") == "1", samesite="lax", max_age=604800)
    return resp


@app.get("/auth/logout")
async def auth_logout(request: Request):
    """Destroy session."""
    token = request.cookies.get("observeco_token", "")
    if token:
        auth_provider.destroy_session(token)
    from fastapi.responses import RedirectResponse
    resp = RedirectResponse(url="/")
    resp.delete_cookie("observeco_token")
    return resp


@app.get("/auth/me")
async def auth_me(request: Request):
    """Get current user info."""
    token = request.cookies.get("observeco_token", "")
    user = auth_provider.get_current_user({"authorization": f"Bearer {token}"})
    if user:
        return JSONResponse({"authenticated": True, "user": user.__dict__})
    return JSONResponse({"authenticated": False})


# ---------------------------------------------------------------------------
# §8 — First-Run Experience: 3-Phase Onboarding Banner
# ---------------------------------------------------------------------------

@app.get("/api/phase", response_class=HTMLResponse)
async def api_phase():
    """Detect onboarding phase per §8 — 3-phase progressive loading (backed by DB persistence)."""
    phase = db.get_phase()
    agents = db.get_agents()
    pulses = db.get_recent_pulses(limit=5)
    now = int(time.time())
    has_agents = len(agents) > 0
    has_data = len(pulses) > 0
    recent_data = any(now - p.get("timestamp", 0) < 300 for p in pulses)

    # Persist detected phase if none set yet
    if not db.get_phase() or db.get_phase() == "zero":
        if has_data:
            db.set_phase("live")
            phase = "live"
        elif has_agents:
            db.set_phase("setup")
            phase = "setup"

    if phase == "zero" or (not has_agents and not has_data):
        # Phase 0 — Fresh install, nothing detected
        return HTMLResponse("""<div class="phase-banner" id="phaseBanner">
    <div class="phase-banner-inner">
        <span class="phase-banner-icon">🔍</span>
        <div class="phase-banner-body">
            <strong class="phase-banner-title">Welcome to ObserveCo</strong>
            <div class="phase-banner-text">
                Let's find your agents. Click below to auto-discover agents from
                your system, or add them manually.
            </div>
            <div class="phase-banner-actions" style="margin-top:10px;display:flex;gap:8px;align-items:center;">
                <button class="phase-banner-btn"
                    hx-post="/api/discover/run-html"
                    hx-target="#discoverResults"
                    hx-swap="innerHTML"
                    hx-indicator="#discoverSpinner">
                    🔍 Let's find your agents
                </button>
                <span id="discoverSpinner" class="htmx-indicator" style="font-size:12px;color:#64748b;">Discovering...</span>
            </div>
            <div id="discoverResults" style="margin-top:10px;"></div>
        </div>
    </div>
</div>""")

    if phase == "setup" or (has_agents and not recent_data):
        # Phase 1 — Agents found, waiting for data
        count = len(agents)
        pulse_count = len(pulses)
        has_any_pulse = pulse_count > 0
        db.set_phase("setup")
        # Determine which step we're on in the 4-stage progress
        steps = [
            ("Discovered", True),
            ("Watched", db.is_first_run() is False),
            ("Pulse arriving", has_any_pulse),
            ("Dashboard live", False),
        ]
        progress_html = '<div class="setup-progress" style="margin:10px 0 6px;">'
        for i, (label, done) in enumerate(steps):
            icon = "✅" if done else "⏳" if i == next((j for j, (_, d) in enumerate(steps) if not d), 3) else "◻️"
            progress_html += f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;font-size:11px;color:{"#22c55e" if done else "#94a3b8"};">{icon} {label}</span>'
            if i < len(steps) - 1:
                progress_html += '<span style="color:#334155;font-size:10px;">──</span>'
        progress_html += "</div>"
        guide_section = """<div id="setupGuide" class="setup-guide" style="margin-top:8px;padding:8px 12px;background:rgba(59,130,246,0.06);border-radius:6px;border-left:2px solid #3b82f6;">
    <div style="font-size:11px;font-weight:600;color:#93c5fd;margin-bottom:4px;">💡 Your personalized guide</div>
    <div id="onboardingGuideContainer" hx-get="/api/onboarding-guide" hx-trigger="load" hx-swap="innerHTML" style="font-size:11px;color:#94a3b8;line-height:1.5;"></div>
</div>"""
        uses = "s" if count != 1 else ""
        return HTMLResponse(f"""<div class="phase-banner" id="phaseBanner" style="border-left-color:#eab308;background:rgba(234,179,8,0.08);">
    <div class="phase-banner-inner">
        <span class="phase-banner-icon">⏳</span>
        <div class="phase-banner-body">
            <strong class="phase-banner-title">{count} agent{uses} discovered — collecting health data...</strong>
            <div class="phase-banner-text">
                Your agent{uses} are registered. Health data will appear within 60 seconds.
                Run <code class="inline-code-sm">observeco watch</code> to start monitoring immediately.
            </div>
            {progress_html}
            {guide_section}
        </div>
    </div>
</div>""")

    # Phase 2 / Live — System stabilized
    db.set_phase("live")
    if db.is_first_run():
        db.set_first_run_complete()
    return HTMLResponse("""<div class="phase-done" id="phase-done">
    <div class="phase-done-inner">
        <span class="phase-done-icon">✅</span>
        <span class="phase-done-text">All agents monitored — system stabilised</span>
    </div>
</div>
<script>
setTimeout(function() {
    var el = document.getElementById('phase-done');
    if (el) { el.style.opacity = '0'; setTimeout(function() { if (el) el.style.display = 'none'; }, 1000); }
}, 8000);
</script>""")

# ---------------------------------------------------------------------------
# §7.4 — Error State Detection
# ---------------------------------------------------------------------------

ERROR_WARNING_BG = "#fefce8"
ERROR_CRITICAL_BG = "#fef2f2"
ERROR_WARNING_BORDER = "#eab308"
ERROR_CRITICAL_BORDER = "#ef4444"


@app.get("/api/error-state", response_class=HTMLResponse)
async def api_error_state():
    """Detect error states and return banners per §7.4."""
    banners = []

    # Check DB exists and readable
    db_path = db.db_path
    if not db_path.exists():
        banners.append(_error_banner(
            icon="⚠️",
            message="No monitoring data yet. Agents will appear here once discovered.",
            action="Run `observeco pulse check` to start collecting.",
            severity="warning",
        ))
    elif db_path.stat().st_size == 0:
        banners.append(_error_banner(
            icon="⚠️",
            message="Health database is empty — monitoring may not have started yet.",
            action="Run `observeco start` to begin monitoring.",
            severity="warning",
        ))

    # Check if monitor daemon heartbeat is stale
    last_pulse = db.get_recent_pulses(limit=1)
    now = int(time.time())
    if last_pulse:
        last_ts = last_pulse[0].get("timestamp", 0)
        if now - last_ts > 7200:  # 2h stale
            hours = (now - last_ts) // 3600
            banners.append(_error_banner(
                icon="⚠️",
                message=f"Monitoring stopped {hours}h ago. Data shown is from last checkpoint.",
                action="Run `observeco start` to resume.",
                severity="warning",
            ))

    # Check if no agents configured
    agents = db.get_agents()
    if not agents:
        banners.append(_error_banner(
            icon="ℹ️",
            message="No agents discovered yet.",
            action="Run `observeco agents add <name> --health-check <url>` (or use `--health-check docker:containername` for Docker containers) or auto-discover with `observeco pulse check`.",
            severity="info",
        ))

    # Check config readability
    from observeco.dirs import get_data_dir
    config_path = get_data_dir() / "agents.json"
    if config_path.exists():
        try:
            json.loads(config_path.read_text())
        except (json.JSONDecodeError, PermissionError):
            banners.append(_error_banner(
                icon="❌",
                message="Could not read config file — check permissions.",
                action=f"Fix: `chmod 644 {config_path}`",
                severity="critical",
            ))

    if not banners:
        return HTMLResponse("")

    return HTMLResponse("\n".join(banners))


def _error_banner(icon: str, message: str, action: str, severity: str) -> str:
    if severity == "critical":
        bg = ERROR_CRITICAL_BG
        border = ERROR_CRITICAL_BORDER
    elif severity == "info":
        bg = "#f0f9ff"  # blue-50
        border = "#3b82f6"
    else:
        bg = ERROR_WARNING_BG
        border = ERROR_WARNING_BORDER
    return f"""<div class="delay-banner" style="background:{bg};border-left-color:{border};">
    <span>{icon}</span>
    <span class="u-ml-6">{_html_escape(message)}</span>
    <code class="inline-code">{_html_escape(action)}</code>
</div>"""


# ---------------------------------------------------------------------------
# §obs-dp-006 — Cumulative Delay Banner
# ---------------------------------------------------------------------------

DELAY_WARNING_SEC = 600    # 10m → banner turns yellow
DELAY_CRITICAL_SEC = 3600  # 1h  → banner turns red


@app.get("/api/delay-banner", response_class=HTMLResponse)
async def api_delay_banner():
    """Compute cumulative agent delay and return a banner if any agents are overdue.
    Also checks watch daemon health (Layer F7).
    """
    agents = db.get_agents()
    now = int(time.time())

    # ── Daemon health check (F7) ────────────────────────────────────
    daemon_warning = ""
    try:
        hb_data = None
        if _get_heartbeat_path().exists():
            hb_data = json.loads(_get_heartbeat_path().read_text())
        daemon_alive = False
        if hb_data:
            hb_age = now - hb_data.get("timestamp", 0)
            pid = hb_data.get("pid")
            if hb_age < 90 and pid:
                try:
                    os.kill(pid, 0)
                    daemon_alive = True
                except (OSError, ProcessLookupError):
                    pass
        if not daemon_alive:
            daemon_warning = (
                '<div class="daemon-warning delay-banner" style="background:#fefce8;border-left-color:#eab308;'
                'padding:8px 14px;margin-bottom:8px;border-radius:8px;border-left:3px solid;font-size:12px;">'
                '<span>⚠️ Watch daemon not running — agent data may be stale</span>'
                '<code class="inline-code" style="margin-left:8px;background:#0f172a;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">observeco watch start</code>'
                '</div>'
            )
    except Exception:
        logger.exception("swallowed exception in server.py")

    delays = []
    for a in agents:
        name = a["agent_name"]
        pulses = db.get_recent_pulses(agent_name=name, limit=1)
        if pulses:
            last_ts = pulses[0].get("timestamp", 0)
            delay = now - last_ts
        else:
            delay = now - a.get("created_at", now) if a.get("created_at") else 999999
        delays.append((name, delay))

    if not delays:
        return HTMLResponse(daemon_warning)

    # Summarize
    overdue_agents = [d for d in delays if d[1] > DELAY_WARNING_SEC]
    critical_agents = [d for d in delays if d[1] > DELAY_CRITICAL_SEC]

    if not overdue_agents:
        return HTMLResponse(daemon_warning)

    # Build banner
    total = len(delays)
    overdue_count = len(overdue_agents)
    critical_count = len(critical_agents)

    # Top delayed agents
    top = sorted(delays, key=lambda x: -x[1])[:3]
    agent_list = []
    for name, sec in top:
        if sec < 60:
            agent_list.append(f"{name} ({sec}s)")
        elif sec < 3600:
            agent_list.append(f"{name} ({sec // 60}m)")
        else:
            h = sec // 3600
            m = (sec % 3600) // 60
            agent_list.append(f"{name} ({h}h {m}m)")

    sev = "critical" if critical_count > 0 else "warning"
    icon = "🔴" if sev == "critical" else "🟡"
    bg = "#fef2f2" if sev == "critical" else "#fefce8"
    border = "#ef4444" if sev == "critical" else "#eab308"

    summary = f"{overdue_count} of {total} agent{'s' if total != 1 else ''} overdue"
    if critical_count:
        summary += f" ({critical_count} critical)"

    html = f"""<div class="delay-banner" style="background:{bg};border-left-color:{border};">
    <span>{icon} <strong>{summary}</strong></span>
    <span class="delay-agent-list">{" · ".join(agent_list)}</span>
</div>"""

    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# § Pro Feature Gating — helpers used by backend endpoints
# ---------------------------------------------------------------------------


def _pro_response(html: str) -> HTMLResponse:
    """Return an HTML response wrapped with license-aware headers."""
    from observeco import license as lic
    is_pro = lic.require_pro()
    if isinstance(html, str) and 'data-pro-state' not in html:
        html = html.replace('<div', '<div data-pro-state="' + ('unlocked' if is_pro else 'locked') + '"', 1) if '<div' in html else html
    return HTMLResponse(html)


def _pro_or_upsell(pro_html: str, feature_name: str = "Pro feature") -> str:
    """Return Pro content if licensed, otherwise return an upsell block."""
    from observeco import license as lic
    if lic.require_pro():
        return pro_html
    return f"""<div class="pro-upsell-block" style="border:1px dashed #3730a3;border-radius:10px;padding:20px;text-align:center;margin:8px 0;">
    <div style="font-size:28px;margin-bottom:8px;">🔒</div>
    <div style="font-size:14px;font-weight:600;color:#a5b4fc;margin-bottom:4px;">{feature_name}</div>
    <div style="font-size:12px;color:#64748b;margin-bottom:12px;">Unlock with Pro — start your free trial</div>
    <button onclick="showBrainPro()" style="background:#6366f1;border:none;color:white;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">Start Free Trial →</button>
</div>"""


# ---------------------------------------------------------------------------
# §6.4 / §7 — Alerts Panel + Pro Locked Tiles
# ---------------------------------------------------------------------------

PRO_FEATURES = [
    {
        "id": "alert-relay",
        "icon": "📡",
        "name": "Alert Relay",
        "price": "$9/mo",
        "plan": "Solo",
        "description": "Push notifications via Telegram, webhook, or CLI when circuits trip or drift exceeds thresholds.",
        "preview_template": "In the last 24h, {alert_count} alerts would have pushed to you: {alert_list}",
    },
    {
        "id": "90d-history",
        "icon": "🕰️",
        "name": "90-Day History",
        "price": "$9/mo",
        "plan": "Solo",
        "description": "Error timeline, drift trends, pulse history extended to 90 days.",
        "preview_template": "90-day history — {days_available} more days available with Pro",
    },
    {
        "id": "fleet-comparison",
        "icon": "📋",
        "name": "Fleet Comparison",
        "price": "$49/mo",
        "plan": "Team",
        "description": "Side-by-side token profiles across all agents. See which agent needs optimization first.",
        "preview_template": "{agent_count} agents in your fleet — compare all with Pro",
    },
    {
        "id": "budget-planner",
        "icon": "🎯",
        "name": "Budget Planner",
        "price": "$49/mo",
        "plan": "Team",
        "description": "Recommended allocation per agent based on fleet-aggregated calibration data.",
        "preview_template": "Pro unlocks the recommendation based on fleet calibration data",
    },
    {
        "id": "drift-alerts",
        "icon": "🚨",
        "name": "Drift Alerts",
        "price": "$9/mo",
        "plan": "Solo",
        "description": "Proactive notification when any agent's system prompt grows beyond configurable threshold.",
        "preview_template": "{drift_count} drift events would have been pushed to you immediately instead of waiting for manual check",
    },
    {
        "id": "circuit-auto-recovery",
        "icon": "⚡",
        "name": "Circuit Auto-Recovery",
        "price": "$49/mo",
        "plan": "Team",
        "description": "Configurable auto-reset after N minutes of cooldown (vs manual reset in free).",
        "preview_template": "Auto-recovery would have resolved {circuit_count} circuit trips automatically",
    },
]



@app.get("/api/pro-preview/{feature_id}", response_class=HTMLResponse)
async def api_pro_preview(feature_id: str):
    """Preview modal for a Pro feature — §7.1 state 3."""
    feat = next((f for f in PRO_FEATURES if f["id"] == feature_id), None)
    if not feat:
        return HTMLResponse("<div>Unknown feature</div>")

    # Compute real user data for the preview
    errors = db.get_errors(limit=50)
    circuit = db.get_circuit_breakers()
    drift = db.get_drift()
    agents = db.get_agents()

    alert_count = len(errors)
    drift_breaches = len([d for d in drift if d.get("breached")])
    circuit_trips = sum(1 for c in circuit if c.get("tripped"))
    alert_list = "; ".join([f"{e.get('error_type','error')} at {_fmt_ts(e['timestamp'])}" for e in errors[:3]]) or "no recent alerts"

    days_available = max(0, 90 - 7)  # 90-day Pro minus 7-day free window
    preview = feat["preview_template"].format(
        alert_count=alert_count,
        alert_list=alert_list,
        drift_count=drift_breaches,
        circuit_count=circuit_trips,
        agent_count=len(agents),
        days_available=days_available,
    )

    plan = feat["plan"]
    price = feat["price"]
    plan_price = {"Solo": "$9/mo", "Team": "$49/mo"}
    full_price = plan_price.get(plan, price)

    return HTMLResponse(f"""<div class="pro-preview-modal"
     onclick="if(event.target===this) closeProPreview()">
    <div class="pro-preview-card">
        <div class="pro-preview-header">
            <h3 class="pro-preview-h3">{feat['icon']} {feat['name']}</h3>
            <span class="pro-preview-close" onclick="closeProPreview()">✕</span>
        </div>
        <div class="pro-preview-desc">
            {feat['description']}
        </div>
        <div class="pro-preview-data">
            <strong>Your data preview:</strong><br>
            {_html_escape(preview)}
        </div>
        <div class="pro-preview-cta">
            <div class="pro-preview-cta-title">
                Start your 30-day free trial
            </div>
            <div class="pro-preview-cta-sub">
                {plan} plan — {full_price} after trial. No charge today.
            </div>
            <div class="pro-preview-cta-row">
                <span onclick="event.preventDefault();var e=prompt('Enter your email to start the 30-day free trial:');if(e)window.location.href='/api/checkout?plan={plan.lower()}&trial=30&email='+encodeURIComponent(e);"
                      class="pro-cta-link" style="cursor:pointer;display:inline-block;">
                    Start Free Trial
                </span>
                <button onclick="closeProPreview()"
                        class="pro-cta-btn">
                    Not now
                </button>
            </div>
        </div>
    </div>
</div>""")


@app.get("/api/checkout")
async def api_checkout(plan: str = "solo", trial: int = 30, email: str = "", phone: str = "", name: str = ""):
    """Redirect to Stripe checkout — §7.1 state 4."""
    from observeco.billing import create_checkout_session
    if not email:
        email = "checkout@observeco.app"
    result = create_checkout_session(email=email, phone=phone, name=name, plan=plan, trial_days=trial if trial > 0 else 0)
    if result and result.get("url"):
        return RedirectResponse(url=result["url"])
    # Fallback if Stripe not configured — show email capture
    return HTMLResponse(f"""<div class="pro-checkout-fallback" style="margin:20px auto;max-width:400px;">
    <div class="pro-checkout-card">
        <h3 class="pro-checkout-h3">✨ Pro Licensing Coming Soon</h3>
        <p class="pro-checkout-p">Leave your email to be notified when Pro billing is available. First 30 days free.</p>
        <form action="/api/waitlist" method="post" class="pro-checkout-form">
            <input type="email" name="email" placeholder="you@example.com" required
                   class="pro-email-input">
            <input type="hidden" name="plan" value="{plan}">
            <button type="submit" class="pro-checkout-submit">
                Notify me when Pro launches
            </button>
        </form>
        <p class="pro-checkout-footnote">No spam. We'll only email you once.</p>
    </div>
</div>""")


# ---------------------------------------------------------------------------
# §6.3 — Agent Detail Expansion
# ---------------------------------------------------------------------------

@app.get("/api/agent-detail/{agent_name}", response_class=HTMLResponse)
async def api_agent_detail(agent_name: str, tab: str = "health"):
    """Expanded agent card per §6.3."""
    name = agent_name

    # Check agent exists — return clear "not found" if missing
    all_agents = db.get_agents()
    known_names = [a["agent_name"] for a in all_agents]
    if name not in known_names:
        return HTMLResponse(f"""<div class="agent-not-found">
    <div class="agent-not-found-icon">🔍</div>
    <div class="agent-not-found-title">Agent not found</div>
    <div class="agent-not-found-msg">No agent named "{_html_escape(name)}" is registered. Run <code class="inline-code">observeco agents discover</code> to scan.</div>
</div>""")

    pulses = db.get_recent_pulses(agent_name=name, limit=24)
    errors = db.get_errors(agent_name=name, limit=20)
    now_ts = int(time.time())
    errors = [e for e in errors if now_ts - e.get("timestamp", 0) < 86400]  # only last 24h for confidence
    trims = db.get_trims(agent_name=name, limit=20)
    drift = db.get_drift(agent_name=name)
    garden = db.get_gardens(agent_name=name)

    circuit = {b["agent_name"]: b for b in db.get_circuit_breakers()}.get(name, {})
    profile = db.get_profiles(agent_name=name)

    # Determine framework — pass through actual DB value, never hardcode default
    agents_cfg = {a["agent_name"]: a for a in db.get_agents()}
    raw_fw = (agents_cfg.get(name, {}).get("framework", "") or "") if agents_cfg else ""
    # Handle composite frameworks like "hermes + openclaw"
    fw_parts = [p.strip().capitalize() for p in raw_fw.split("+")] if raw_fw else []
    framework = " + ".join(fw_parts) if fw_parts else ""

    from observeco.dashboard.server import _compute_confidence

    # Derive agent status from recent pulses
    agent_status = "unknown"
    ever_alive = False
    if pulses:
        agent_status = pulses[0].get("status", "unknown")
        # Check if this agent has EVER been seen alive
        all_pulses = db.get_recent_pulses(agent_name=name, limit=1000)
        ever_alive = any(p.get("status") == "alive" for p in all_pulses)

    # Distinguish "dead" (was running, went down) from "not running" (never seen alive)
    if agent_status == "dead" and not ever_alive:
        agent_status = "not_running"

    # Compute confidence for the agent's current state
    state_since = pulses[0].get("timestamp", int(time.time())) if pulses else int(time.time()) - 86400
    conf = _compute_confidence(agent_status, pulses, errors, circuit, state_since, now_ts)

    if tab == "health":
        return _detail_health_tab(name, pulses, errors, circuit, framework, agent_status, conf)
    if tab == "guard":
        return _detail_guard_tab(name, pulses, errors, circuit, framework, agent_status, conf)
    elif tab == "errors":
        from observeco import license as lic
        return _detail_errors_tab(name, errors, framework, agent_status, conf, is_pro=lic.require_pro())
    elif tab == "tokens":
        return _detail_tokens_tab(name, trims, drift, framework)
    elif tab == "drift":
        return _detail_drift_tab(name, drift, framework)
    elif tab == "garden" or tab == "memory":
        return _detail_garden_tab(name, garden, profile, framework)
    return HTMLResponse("<div>Unknown tab</div>")


# ── Confidence, Risk & Recommendation Engine (§3.29) ──


def _compute_confidence(status: str, pulses: list, errors: list,
                         circuit: dict, state_since: int, now: int) -> dict:
    """Score confidence, FP/FN risk, and produce recommendation for a signal.

    Uses 4 independent signals:
      1. Duration — how long in current state
      2. Consecutive count — how many checks in a row agree
      3. Source agreement — do pulse + errors + circuit breaker agree?
      4. Pattern stability — are error messages consistent?

    Returns dict with: level, fp_risk, fn_risk, recommendation, sources_agree.
    """
    # ── Signal 1: Duration ──
    duration = max(0, now - state_since)
    sig_duration = 1 if duration > 7200 else 0  # >2h = strong

    # ── Signal 2: Consecutive count ──
    consecutive = 0
    for p in pulses:
        if p.get("status") == status:
            consecutive += 1
        else:
            break
    sig_consecutive = 2 if consecutive >= 3 else 1 if consecutive >= 2 else 0

    # ── Signal 3: Source agreement ──
    has_errors = len(errors) > 0
    is_tripped = circuit.get("tripped", False)
    is_dead = status == "dead"
    is_alive = status == "alive"
    is_unknown = status == "unknown"

    # How many sources agree with the current status
    sources = 0
    total_sources = 3  # pulse status, error presence, circuit breaker

    if is_dead:
        if has_errors:
            sources += 1  # errors confirm problem
        if not is_tripped:
            sources += 1  # circuit not tripped = still checking = dead confirmed
    elif is_alive:
        if not has_errors:
            sources += 1  # no errors confirms health
        if not is_tripped:
            sources += 1  # circuit not tripped = healthy
    elif is_unknown:
        # Unknown status — no pulse data to evaluate
        sources = 0  # no sources can agree on an unknown state
    else:  # error/warning
        if has_errors:
            sources += 1
        if is_tripped:
            sources += 1

    # Pulse itself always counts as 1 source
    if pulses:
        sources += 1

    sig_source = 0
    if sources == total_sources:
        sig_source = 2  # all agree
    elif sources >= total_sources - 1:
        sig_source = 1  # most agree
    # else: 0 — disagree

    # ── Signal 4: Pattern stability ──
    if has_errors and len(errors) > 1:
        unique_msgs = len(set(e.get("error_message", "")[:30] for e in errors))
        sig_stable = 1 if unique_msgs <= 2 else 0
    else:
        sig_stable = 1  # no errors or single error = stable

    # ── Aggregate score ──
    score = (sig_duration * 1) + (sig_consecutive * 1) + (sig_source * 1) + (sig_stable * 1)
    # Max possible: 1 + 2 + 2 + 1 = 6

    if score >= 5:
        level = "high"
    elif score >= 3:
        level = "medium"
    else:
        level = "low"

    # ── FP risk (how likely is this flag to be a false alarm?) ──
    if is_unknown:
        # Unknown status = no data to evaluate — neither FP nor FN applies
        fp_risk = "moderate"
    elif is_dead or is_tripped or has_errors:
        # Red/yellow flags — FP risk depends on duration + consecutive + source agreement
        if duration > 7200 and consecutive >= 3 and sources >= total_sources - 1:
            fp_risk = "low"
        elif duration > 600 and consecutive >= 2:
            fp_risk = "moderate"
        else:
            fp_risk = "high"
    else:
        # Green flags — FP risk is naturally low if no issues detected
        fp_risk = "low"

    # ── FN risk (how likely is green to be missing something?) ──
    if is_unknown:
        fn_risk = "high"  # can't verify anything without data
    elif is_alive:
        if not pulses or consecutive < 3:
            fn_risk = "high"  # too few checks to be confident
        elif duration > 3600:
            fn_risk = "high"  # last check was >1h ago — could have died
        else:
            fn_risk = "low"
    else:
        fn_risk = "low"  # non-green flags can't be false negatives

    # ── Sources agreement text ──
    if is_dead:
        if sources >= total_sources - 1:
            sources_agree = "pulse + errors + circuit all agree"
        elif has_errors:
            sources_agree = "pulse + errors agree"
        else:
            sources_agree = "pulse only"
    elif is_alive:
        if not has_errors and not is_tripped:
            sources_agree = "pulse + errors + circuit all agree"
        elif not pulses:
            sources_agree = "no recent data"
        else:
            sources_agree = "pulse only"
    elif is_unknown:
        sources_agree = "no pulse data — agent may not support pulse monitoring"
    else:
        sources_agree = "mixed signals"

    # ── Recommendation ──
    recommendation = _recommendation_for(status, errors, circuit, pulses,
                                          duration, is_dead, is_alive, is_tripped,
                                          is_unknown=is_unknown)

    return {
        "level": level,
        "fp_risk": fp_risk,
        "fn_risk": fn_risk,
        "recommendation": recommendation,
        "sources_agree": sources_agree,
    }


def _recommendation_for(status: str, errors: list, circuit: dict,
                        pulses: list, duration: int,
                        is_dead: bool, is_alive: bool, is_tripped: bool,
                        is_unknown: bool = False) -> str:
    """Return actionable recommendation based on agent state."""
    err_count = len(errors)
    stale = pulses and (pulses[0].get("timestamp", 0) < int(time.time()) - 3600)

    if is_unknown:
        return "➤ No pulse data — this agent may not be monitored via pulse checks. Configure a health check or use platform-specific monitoring."

    if is_dead:
        days = max(1, duration // 86400)
        if duration > 86400:
            return f"➤ Agent has been down for {days}d. Start it manually: <code>observeco start</code>"
        if err_count > 3:
            return f"➤ Agent is down — all {err_count} errors are from failed reach attempts. Restart to stop the noise."
        return "➤ Agent may be down. Run <code>observeco pulse check</code> to confirm."

    if is_tripped:
        return "➤ Guard stopped after 3 failures. Wait ~4h for cooldown, or restart the agent manually."

    if is_alive:
        if stale and len(pulses) >= 3:
            return "➤ Last check was hours ago. Agent could have died since. Run <code>observeco pulse check</code>."
        if stale:
            return "➤ Only a few checks recorded — not yet conclusive. Continue monitoring."
        if err_count == 0:
            if len(pulses) >= 10:
                return "➤ All clear — all checks passed."
            return f"➤ No issues yet — but only {len(pulses)} checks recorded. Continue monitoring."
        if err_count == 1:
            return "➤ Single error — likely transient. No action needed unless it repeats."
        return f"➤ {err_count} errors — could be transient or ongoing. Run <code>observeco heal --diagnose</code>."

    # Error/warning state
    if err_count >= 3:
        return f"➤ {err_count} errors — may need attention. Check agent logs or restart."
    if err_count >= 1:
        return "➤ Warning state — monitor for next 5 minutes before acting."
    return "➤ Unstable state — check agent configuration."


def _confidence_badge(conf: dict) -> str:
    """Render a small confidence badge for agent cards — level + FP/FN risk + recommendation."""
    emoji = {"high": "🟢", "medium": "🟡", "low": "⚪"}.get(conf["level"], "⚪")
    fp_icon = {"low": "✅", "moderate": "⚠️", "high": "❌"}.get(conf["fp_risk"], "⚠️")
    fn_icon = {"low": "✅", "moderate": "⚠️", "high": "❌"}.get(conf["fn_risk"], "⚠️")
    fp_label = conf["fp_risk"].capitalize()
    fn_label = conf["fn_risk"].capitalize()
    level_label = conf["level"].capitalize()
    return f'''
        <div class="conf-badge" style="font-size:10px;color:#94a3b8;margin-top:2px;display:flex;gap:8px;flex-wrap:wrap;">
            <span title="Confidence: {level_label} — {conf['sources_agree']}">{emoji} {level_label}</span>
            <span title="False positive risk: {fp_label}">{fp_icon} FP {fp_label}</span>
            <span title="False negative risk: {fn_label}">{fn_icon} FN {fn_label}</span>
        </div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">{conf['recommendation']}</div>'''


# ── Canary Report Card ─────────────────────────────────────────────


def _canary_card(agent_name: str) -> str:
    """Render a canary report card (Variant A) for an agent.

    Shows pass rate, accuracy, hangs, recovery, and drift vs baseline.
    Empty state when no canary runs exist.
    """
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()

    # Cleanup: mark runs stuck in 'running' for >30min as 'failed'.
    # Use db._write() (retry-on-lock) — the watch daemon writes pulse.db constantly.
    try:
        db._write(
            "UPDATE canary_runs SET status = 'failed' "
            "WHERE status = 'running' AND started_at < datetime('now', '-30 minutes')",
            (),
        )
    except _sqlite3.OperationalError:
        pass  # cleanup is best-effort

    # Get latest completed run
    run = conn.execute(
        "SELECT id, pass_count, fail_count, hang_count, total_tasks, "
        "started_at, config_hash FROM canary_runs "
        "WHERE agent_name = ? AND status = 'completed' AND pass_count IS NOT NULL "
        "ORDER BY started_at DESC LIMIT 1",
        (agent_name,),
    ).fetchone()

    if not run:
        return f"""<div class="canary-card">
  <div class="canary-empty">🔬 No canary baseline yet <button onclick="runCanaryFor('{agent_name}')">Run Canary</button></div>
</div>"""

    total = (run["pass_count"] or 0) + (run["fail_count"] or 0)
    pass_rate = f"{run['pass_count']}/{run['total_tasks']}" if run["total_tasks"] else "0/0"
    accuracy = f"{run['pass_count'] / total:.0%}" if total > 0 else "0%"
    hangs = run["hang_count"] or 0
    recovery = "100%" if hangs == 0 else "0%"

    # Color coding
    acc_pct = run["pass_count"] / total if total > 0 else 0
    acc_color = "green" if acc_pct >= 0.7 else "yellow" if acc_pct >= 0.4 else "red"
    hang_color = "green" if hangs == 0 else "yellow" if hangs <= 2 else "red"

    # Drift vs baseline
    baseline = conn.execute(
        "SELECT accuracy FROM canary_baselines "
        "WHERE agent_name = ? AND expires_at IS NULL ORDER BY created_at DESC LIMIT 1",
        (agent_name,),
    ).fetchone()

    drift_html = ""
    if baseline and total > 0:
        baseline_acc = baseline["accuracy"]
        current_acc = run["pass_count"] / total
        drift_pct = (current_acc - baseline_acc) * 100
        drift_dir = "up" if drift_pct >= 0 else "down"
        drift_icon = "▲" if drift_pct >= 0 else "▼"
        drift_html = f'<div class="drift-indicator {drift_dir}">{drift_icon} {abs(drift_pct):.1f}% vs baseline</div>'
    else:
        drift_html = '<div style="color:var(--muted);font-size:10px;">No baseline</div>'

    return f"""<div class="canary-card">
  <div class="canary-card-header">
    <div class="canary-card-title">
      <span class="status-dot {acc_color}"></span>
      Canary
      <span class="canary-card-meta">Last run: {run['started_at'][:10]}</span>
    </div>
  </div>
  <div class="canary-card-stats">
    <div class="canary-stat">
      <div class="canary-stat-num {acc_color}">{pass_rate}</div>
      <div class="canary-stat-label">Pass Rate</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num {acc_color}">{accuracy}</div>
      <div class="canary-stat-label">Accuracy</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num {hang_color}">{hangs}</div>
      <div class="canary-stat-label">Hangs</div>
    </div>
    <div class="canary-stat">
      <div class="canary-stat-num green">{recovery}</div>
      <div class="canary-stat-label">Recovery</div>
    </div>
  </div>
  <div class="canary-card-footer">
    {drift_html}
    <span class="action-link" onclick="switchTab('capability', document.querySelector('.tab-btn:nth-child(11)'))">View details →</span>
  </div>
</div>"""


def _confidence_header(conf: dict) -> str:
    """Render confidence header section for detail tabs."""
    emoji = {"high": "🟢", "medium": "🟡", "low": "⚪"}.get(conf["level"], "⚪")
    level_label = conf["level"].capitalize()
    return f'''<div class="modal-section" style="background:rgba(255,255,255,0.03);border-radius:8px;padding:12px;margin-bottom:8px;">
        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;font-size:12px;">
            <span><strong>{emoji} Confidence:</strong> {level_label}</span>
            <span style="color:{'#22c55e' if conf['fp_risk']=='low' else '#eab308' if conf['fp_risk']=='moderate' else '#ef4444'};">
                <strong>FP risk:</strong> {conf['fp_risk'].capitalize()}
            </span>
            <span style="color:{'#22c55e' if conf['fn_risk']=='low' else '#eab308' if conf['fn_risk']=='moderate' else '#ef4444'};">
                <strong>FN risk:</strong> {conf['fn_risk'].capitalize()}
            </span>
            <span style="color:#64748b;">Sources: {conf['sources_agree']}</span>
        </div>
        <div style="font-size:12px;color:#94a3b8;margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.05);">
            {conf['recommendation']}
        </div>
    </div>'''


def _detail_health_tab(name: str, pulses: list, errors: list, circuit: dict, framework: str,
                       agent_status: str = "unknown", conf: dict = None) -> str:
    now = int(time.time())

    # ── Section 0: Confidence header ──
    conf_header = _confidence_header(conf) if conf else ""

    # ── Section 1: Pulse timeline (all dots with legend) ──
    dot_row = []
    for p in pulses[:48]:
        cls = "ok" if p["status"] == "alive" else "err" if p["status"] == "dead" else "warn"
        ts = _fmt_ts(p["timestamp"])
        dot_row.append(f'<span title="{p["status"]} @ {ts}" class="pulse-dot {cls}"></span>')
    dots_html = "\n".join(dot_row) if dot_row else '<span class="text-muted">No pulses recorded yet</span>'

    # ── Section 2: Annotated timeline (errors as table) ──
    error_rows = ""
    if errors:
        for e in errors[:20]:
            sev = e.get("severity", "warning")
            ts_str = _fmt_ts(e["timestamp"])
            col = {"critical": "#ef4444", "error": "#ef4444", "warning": "#eab308", "info": "#3b82f6"}.get(sev, "#6b7280")
            status_icon = "🔴" if sev in ("critical", "error") else "🟡"
            status_label = "Down" if sev in ("critical", "error") else "Warning"
            msg = _html_escape(e.get("error_message", "") or e.get("message", "") or e.get("error_type", "?")[:100])
            error_rows += f"""<tr>
    <td class="error-tl-time">{ts_str}</td>
    <td class="error-tl-status" style="color:{col};">{status_icon} {status_label}</td>
    <td class="error-tl-msg">{msg}</td>
</tr>"""
    else:
        error_rows = '<tr><td colspan="3" class="empty-table-msg">No errors — all checks passed</td></tr>'

    # ── Section 3: Categorized summary + plain-English verdict ──
    categories = {"timeout": 0, "connection": 0, "resource": 0, "http_5xx": 0, "other": 0}
    for e in errors:
        msg = (e.get("error_type", "") + " " + e.get("error_message", "")).lower()
        etype = e.get("error_type", "").lower()
        if "timeout" in msg or "timed out" in msg or etype == "timeout":
            categories["timeout"] += 1
        elif "connection" in msg or "refused" in msg or etype == "connection_refused":
            categories["connection"] += 1
        elif "not found" in msg or "missing" in msg or "dependency" in msg:
            categories["resource"] += 1
        elif ("5" in etype and ("00" in etype or "03" in etype)) or "500" in msg or "503" in msg:
            categories["http_5xx"] += 1
        else:
            categories["other"] += 1

    summary_parts = []
    if categories["timeout"]:
        summary_parts.append(f'🕐 <strong>{categories["timeout"]}</strong> timeout{"s" if categories["timeout"] > 1 else ""} — the agent was running but didn\'t respond. Usually overloaded or stuck.')
    if categories["connection"]:
        summary_parts.append(f'🔌 <strong>{categories["connection"]}</strong> connection refused — the agent process may have crashed or the port changed.')
    if categories["resource"]:
        summary_parts.append(f'🔍 <strong>{categories["resource"]}</strong> resource{"s" if categories["resource"] > 1 else ""} not found — a dependency, file, or endpoint is missing.')
    if categories["http_5xx"]:
        summary_parts.append(f'🌐 <strong>{categories["http_5xx"]}</strong> HTTP 5xx error{"s" if categories["http_5xx"] > 1 else ""} — agent is running but returning server errors.')
    if categories["other"]:
        summary_parts.append(f'❓ <strong>{categories["other"]}</strong> other error{"s" if categories["other"] > 1 else ""} — check the full list.')

    total_errs = len(errors)
    is_dead = agent_status == "dead"
    is_not_running = agent_status == "not_running"
    is_unknown = agent_status == "unknown"

    if is_dead:
        if total_errs == 0:
            verdict_text = (
                "The agent is <strong>down</strong> (last probe failed). "
                "No errors were logged separately — dead pulse records aren't written to the error table. "
                "Check the agent's process or start it manually."
            )
        else:
            verdict_text = (
                f"The agent is <strong>down</strong> — all {total_errs} error{'s' if total_errs > 1 else ''} "
                f"are from the system trying (and failing) to reach it. "
                f"The agent will not recover on its own."
            )
    elif is_not_running:
        if total_errs == 0:
            verdict_text = (
                "This agent has <strong>never been seen running</strong> by the monitoring system. "
                "It's registered but hasn't responded to any pulse checks. "
                "Verify the agent is actually started — if it's intentional, ignore this alert."
            )
        else:
            verdict_text = (
                f"This agent has <strong>never been seen running</strong>. "
                f"The {total_errs} error{'s' if total_errs > 1 else ''} "
                f"are from the system trying to reach it since registration."
            )
    elif is_unknown:
        verdict_text = (
            "No pulse data available — this agent is not pulse-monitored. "
            "Configure a health check (e.g. <code>http:port/health</code> or <code>docker:containername</code>) "
            "to enable automatic status tracking."
        )
    elif total_errs == 0:
        verdict_text = "All checks passed in the last 24 hours. No issues detected."
    elif total_errs == 1:
        verdict_text = "This agent had 1 issue in the last 24 hours. Likely transient — monitor."
    elif total_errs <= 3:
        verdict_text = f"This agent had <strong>{total_errs} issues</strong> in the last 24 hours. Possibly unstable — check the error details above."
    else:
        if any(p["status"] in ("dead", "error") for p in pulses[:24]):
            verdict_text = f"This agent had <strong>{total_errs} issues</strong> in the last 24 hours. It needs attention — try restarting it."
        else:
            verdict_text = f"This agent had <strong>{total_errs} issues</strong> in the last 24 hours. Issues appear resolved for now — monitor the next few checks."

    summary_html = "<br>".join(summary_parts) if summary_parts else "All checks passed — no issues detected this period."
    if is_dead or is_not_running or is_unknown:
        if not summary_parts:
            summary_html = "No errors logged separately — pulse-level status reflects the actual agent state. See the verdict below."

    # ── Section 4: Latest check ──
    last_pulse = pulses[0] if pulses else {}
    if not pulses:
        last_ts = "—"
        last_latency = "—"
        latest_result = "⚪ No pulse data"
        latest_cls = ""
    else:
        last_status = last_pulse.get("status", "unknown")
        last_ts = _fmt_ts(last_pulse.get("timestamp", 0))
        last_latency = last_pulse.get("latency", "—")
        if last_status == "alive":
            latest_result = "✅ OK"
            latest_cls = "good"
        elif last_status == "error":
            latest_result = "🟡 Warning"
            latest_cls = "warn"
        else:
            latest_result = "🔴 Down"
            latest_cls = "bad"

    # ── Circuit section (compact) ──
    circuit_html = ""
    if circuit.get("tripped"):
        cd = circuit.get("cooldown_until", 0)
        remaining = max(0, cd - now) if cd else 0
        circuit_html = f"""
    <div class="modal-section">
        <h4>Safety Guard</h4>
        <div style="font-size:13px;color:#ef4444;font-weight:600;margin-bottom:6px;">🔴 Guard is STOPPED — not checking this agent</div>
        <div style="font-size:12px;color:#64748b;">{circuit.get("failure_count", 0)} consecutive failures. Cooldown: {remaining // 60}m {remaining % 60}s remaining.</div>
    </div>"""

    return HTMLResponse(f"""<div class="detail-content">
    <div class="modal-section">
        <h4>Last 24 hours (every 30s)</h4>
        <div class="pulse-timeline">{dots_html}</div>
        <div class="pulse-legend">
            <span class="pulse-legend-dot"><span class="pulse-dot ok"></span> OK</span>
            <span class="pulse-legend-dot"><span class="pulse-dot warn"></span> Warning</span>
            <span class="pulse-legend-dot"><span class="pulse-dot err"></span> Down</span>
        </div>
    </div>
    <div class="modal-section">
        <h4>Signal Analysis</h4>
        {conf_header}
        <div class="modal-section">
            <h5>Annotated timeline</h5>
            <table class="data-table">
                <tr><th style="width:70px;">Time</th><th style="width:80px;">Status</th><th>What happened</th></tr>
                {error_rows}
            </table>
        </div>
        <div class="modal-section">
            <h5>Summary</h5>
            <div class="health-summary-body">
                {summary_html}
            </div>
            <div class="health-verdict">
                <strong>Verdict:</strong> {verdict_text}
            </div>
        </div>
        <div class="modal-section">
            <h5>Latest check</h5>
            <table class="data-table">
                <tr><th style="width:70px;">Time</th><th style="width:80px;">Result</th><th>Latency</th></tr>
                <tr><td>{last_ts}</td><td class="{latest_cls}">{latest_result}</td><td>{last_latency}</td></tr>
            </table>
        </div>
        {circuit_html}
    </div>
</div>""")


def _detail_drift_tab(name: str, drift: list, framework: str) -> str:
    """Drift detail — 14-day trend with component breakdown."""
    if not drift:
        return HTMLResponse("""<div class="detail-content">
    <div class="empty-state">
        <div class="empty-state-title">📈 No drift data yet</div>
        <div class="empty-state-body">Drift appears after the agent has been monitored for at least 24 hours.</div>
    </div>
</div>""")

    vals = [d.get("delta_pct", 0) for d in drift[-7:]]
    avg = sum(vals) / len(vals) if vals else 0
    trend = "📈" if avg > 0.1 else "📉" if avg < -0.1 else "➡️"
    direction = "increasing" if avg > 0.1 else "decreasing" if avg < -0.1 else "stable"

    rows = ""
    breaches = 0
    for d in drift[-14:]:
        raw_ts = d.get("timestamp", 0)
        # Convert Unix timestamp to readable date
        ts = datetime.fromtimestamp(raw_ts).strftime("%b %d") if raw_ts else ""
        pct = d.get("delta_pct", 0)
        breached = d.get("breached", False)
        if breached:
            breaches += 1
        bar_w = min(abs(pct) * 2, 100)
        bar_col = "#ef4444" if breached else ("#f59e0b" if abs(pct) > 5 else "#22c55e")
        rows += f"""<div class="drift-row" style="display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid rgba(30,41,59,0.3);">
    <span style="font-size:11px;color:#64748b;flex:1;font-family:var(--font-mono);">{ts}</span>
    <div style="flex:1;height:6px;background:#1e293b;border-radius:3px;">
        <div style="width:{bar_w}%;height:6px;background:{bar_col};border-radius:3px;"></div>
    </div>
    <span style="font-size:11px;font-family:var(--font-mono);color:{bar_col};flex:1;font-weight:600;">{pct:+.1f}%</span>
    {'<span style="font-size:11px;color:#ef4444;" title="Breach">⛔</span>' if breached else ''}
</div>"""

    # Summary cards
    max_pct = max(abs(v) for v in vals) if vals else 0
    risk_color = "#ef4444" if breaches > 0 else ("#f59e0b" if max_pct > 5 else "#22c55e")
    risk_label = "High" if breaches > 0 else ("Moderate" if max_pct > 5 else "Low")

    return HTMLResponse(f"""<div class="detail-content">
    <div class="detail-section" style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px;">
        <div class="modal-section-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <h4 style="font-size:13px;font-weight:600;color:#e2e8f0;margin:0;">📈 Drift — 14-Day Trend</h4>
            <span style="font-size:11px;background:{risk_color}20;color:{risk_color};padding:2px 10px;border-radius:999px;font-weight:600;">{risk_label} Risk</span>
        </div>
        <div style="font-size:12px;color:#94a3b8;margin-bottom:12px;">
            {trend} Drift is <strong>{direction}</strong> at <strong>{avg:+.1f}%</strong> avg over last 7 days
        </div>
        <div>
            <div style="display:flex;align-items:center;gap:10px;padding:4px 0 6px;border-bottom:1px solid var(--border);font-size:10px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
                <span style="flex:1;text-align:left;">Date</span>
                <span style="flex:1;text-align:left;">Change</span>
                <span style="flex:1;text-align:left;">Delta</span>
            </div>
            {rows}
        </div>
    </div>
</div>""")


def _detail_tokens_tab(name: str, trims: list, drift: list, framework: str) -> str:
    # Determine if we have data
    latest_trim = trims[0] if trims else None
    if not latest_trim:
        # No trim data — show helpful empty state
        fw_hint = f" ({framework.capitalize()} agent)" if framework else ""
        return HTMLResponse(f"""<div class="detail-content">
    <div class="empty-state">
        <div class="empty-state-title">📊 No token data yet</div>
        <div class="empty-state-body">Token breakdown appears after the agent participates in conversations or runs tasks{fw_hint}.</div>
        <div class="empty-state-actions">
            Run <code class="inline-code">observeco context trim</code> to see per-component breakdown.
        </div>
    </div>
</div>""")

    if "hermes" in framework.lower():
        # Hermes token breakdown
        comps = [
            ("identity", latest_trim.get("identity_tokens", 0)),
            ("skills", latest_trim.get("skills_tokens", 0)),
            ("memory", latest_trim.get("memory_tokens", 0)),
            ("tools", latest_trim.get("tools_tokens", 0)),
            ("guidance", latest_trim.get("guidance_tokens", 0)),
        ]
        comps_sorted = sorted(comps, key=lambda x: -x[1])
        total = max(sum(c[1] for c in comps_sorted), 1)
        total_display = latest_trim.get("total_tokens", total)

        bars = []
        for comp, val in comps_sorted:
            pct = val / total * 100
            col = {"identity": "#6366f1", "skills": "#8b5cf6", "memory": "#ec4899",
                   "tools": "#14b8a6", "guidance": "#f97316"}.get(comp, "#6b7280")
            comp_label = comp.capitalize()
            # Estimate yearly cost at $0.15/M tokens
            bars.append(f"""<div class="token-row-detail">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span class="token-row-label" style="font-weight:600;color:#e2e8f0;font-size:12px;">{comp_label}</span>
        <span style="font-size:11px;color:#94a3b8;font-family:var(--font-mono);">{val:,} <span style="color:#64748b;">tok</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
        <div class="token-bar-bg" style="flex:1;height:6px;">
            <div class="token-bar-fill-dynamic" style="width:{pct:.1f}%;background:{col};height:6px;border-radius:3px;"></div>
        </div>
        <span class="token-row-value" style="font-size:11px;color:#94a3b8;min-width:40px;text-align:right;font-family:var(--font-mono);">{pct:.0f}%</span>
    </div>
</div>""")

        savings = latest_trim.get("savings_ratio", 0)
        savings_html = f"""<div class="savings-badge" style="display:inline-flex;align-items:center;gap:4px;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.2);border-radius:6px;padding:6px 10px;font-size:11px;color:#22c55e;margin-top:8px;">
    📉 Compressed {savings:.0%} this session
</div>""" if savings > 0 else ""

        yearly_est_total = total * 365 * 0.15 / 1_000_000
        cost_line = f"""<div style="display:flex;align-items:center;gap:8px;margin-top:8px;padding:8px 12px;background:var(--surface);border-radius:6px;font-size:11px;">
    <span style="color:#64748b;">Estimated yearly cost</span>
    <span style="color:#e2e8f0;font-family:var(--font-mono);font-weight:600;">${yearly_est_total:.2f}</span>
    <span style="color:#475569;font-size:10px;">(at $0.15/M tok, DeepSeek rates)</span>
</div>"""

        drift_html = _detail_drift_html(drift, name)

        return HTMLResponse(f"""<div class="detail-content">
    <div class="detail-section">
        <div class="token-header"><div class="uppercase-label">Token Breakdown</div>
        <div class="text-lg font-semibold font-mono token-total-display">{total_display:,} <span class="text-sm text-muted font-normal">total</span></div>
    </div>
    {"".join(bars)}
    {savings_html}
    {cost_line}
    {drift_html}
</div>""")
    else:
        # OpenClaw — ClawForge source breakdown
        profiles = db.get_profiles(agent_name=name)
        if profiles:
            p = profiles[0]
            memory = p.get("memory_md_size", 0) // 100
            skills_count = p.get("skill_count", 0)
            total_est = p.get("total_estimated_tokens", 0)

            comps = [
                ("MEMORY.md", memory),
                ("Skills", skills_count * 200),
                ("Workspace", p.get("workspace_files", 0) * 150),
                ("History", p.get("history_depth", 0) * 50),
                ("Bootstrap", 500),
            ]
            total = max(sum(c[1] for c in comps), 1)

            bars = []
            for comp, val in comps:
                pct = val / total * 100
                col = {"MEMORY.md": "#ec4899", "Skills": "#8b5cf6", "Workspace": "#14b8a6",
                       "History": "#6366f1", "Bootstrap": "#f97316"}.get(comp, "#6b7280")
                bars.append(f"""<div class="token-row-detail">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span class="token-row-label" style="font-weight:600;color:#e2e8f0;font-size:12px;">{comp}</span>
        <span style="font-size:11px;color:#94a3b8;font-family:var(--font-mono);">{val:,} <span style="color:#64748b;">tok</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
        <div class="token-bar-bg" style="flex:1;height:6px;">
            <div class="token-bar-fill-dynamic" style="width:{pct:.1f}%;background:{col};height:6px;border-radius:3px;"></div>
        </div>
        <span class="token-row-value" style="font-size:11px;color:#94a3b8;min-width:40px;text-align:right;font-family:var(--font-mono);">{pct:.0f}%</span>
    </div>
</div>""")

            loads = db.get_loads(agent_name=name)
            total_saved = sum(ld.get("tokens_saved", 0) for ld in loads[:20])
            savings_html = f"""<div class="savings-badge" style="display:inline-flex;align-items:center;gap:4px;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.2);border-radius:6px;padding:6px 10px;font-size:11px;color:#22c55e;margin-top:8px;">
    📉 ClawForge saved ~{total_saved:,} tokens across {len(loads)} turns
</div>""" if total_saved > 0 else ""

            yearly_est_total = (total_est or total) * 365 * 0.15 / 1_000_000
            cost_line = f"""<div style="display:flex;align-items:center;gap:8px;margin-top:8px;padding:8px 12px;background:var(--surface);border-radius:6px;font-size:11px;">
    <span style="color:#64748b;">Estimated yearly cost</span>
    <span style="color:#e2e8f0;font-family:var(--font-mono);font-weight:600;">${yearly_est_total:.2f}</span>
    <span style="color:#475569;font-size:10px;">(at $0.15/M tok, DeepSeek rates)</span>
</div>"""

            return HTMLResponse(f"""<div class="detail-content">
    <div class="detail-section">
        <div class="token-header"><div class="uppercase-label">Source Breakdown</div>
        <div class="text-lg font-semibold font-mono token-total-display">{total_est:,} <span class="text-sm text-muted font-normal">estimated tokens</span></div>
    </div>
    {"".join(bars)}
    {savings_html}
    {cost_line}
</div>""")
        return HTMLResponse('<div class="empty-state">No profile data — run `observeco clawforge profile`</div>')


def _detail_drift_html(drift: list, name: str) -> str:
    agent_drift = [d for d in drift if d["agent_name"] == name]
    if not agent_drift:
        return '<div style="color:#6b7280;font-size:12px;margin-top:12px;">No drift data yet</div>'

    items = []
    for d in agent_drift[:7]:
        comp = d.get("component", "system prompt")
        pct = d.get("delta_pct", 0)
        breached = d.get("breached", 0)
        color = "#ef4444" if breached else "#22c55e" if pct < 0 else "#f97316"
        icon = "📈" if pct > 0 else "📉"
        items.append(f"""<div class="drift-detail-row">
    <span>{icon}</span>
    <span class="drift-comp">{_html_escape(comp)}</span>
    <span class="drift-pct drift-value" style="color:{color};">{pct:+.1f}%</span>
    <span class="drift-status">{'⛔ Breach' if breached else ''}</span>
</div>""")

    return f"""<div class="drift-section">
    <div class="section-title"><span class="uppercase-label">Drift Trend</span></div>
    {"".join(items)}
</div>"""


def _detail_guard_tab(name: str, pulses: list, errors: list, circuit: dict, framework: str, agent_status: str = "unknown", conf: dict = None) -> str:
    """Guard detail — 5 sections: status, failure timeline, explanation, savings, settings."""
    if conf is None:
        conf = {}
    now = int(time.time())
    is_tripped = circuit.get("tripped", False)
    stale_alive = agent_status == "alive" and pulses and (now - pulses[0].get("timestamp", 0)) > 3600

    # Section 0: Confidence header
    conf_header = _confidence_header(conf) if conf else ""

    # Section 1: Status — acknowledge agent's pulse status + stale-dependent factor
    is_dead = agent_status == "dead"
    is_not_running = agent_status == "not_running"
    is_unknown = agent_status == "unknown"
    if is_not_running:
        status_html = """
        <div style="font-size:13px;color:#94a3b8;font-weight:600;margin-bottom:8px;">
            ○ Agent not started
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            This agent has <strong>never been seen running</strong> by the monitoring system.
            The guard shows "0 failures" because it hasn't had anything to check — not because
            the agent is healthy. It's registered but hasn't responded to any pulse checks.
            Verify the agent is actually started.
        </div>"""
    elif is_unknown:
        status_html = """
        <div style="font-size:13px;color:#94a3b8;font-weight:600;margin-bottom:8px;">
            ⚪ No pulse data
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            This agent is <strong>not pulse-monitored</strong>. The guard has no data to check against.
            Configure a health check (e.g. <code>http:port/health</code> or <code>docker:containername</code>)
            to enable automatic status tracking.
        </div>"""
    elif is_dead:
        status_html = """
        <div style="font-size:13px;color:#eab308;font-weight:600;margin-bottom:8px;">
            ⚠️ Agent is down
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            This agent is <strong>not running</strong>. The guard says "0 failures" but that's because
            there's nothing to check — not because it's healthy. The guard will start monitoring again
            once the agent comes back online.
        </div>"""
    elif is_tripped:
        status_html = """
        <div style="font-size:13px;color:#ef4444;font-weight:600;margin-bottom:8px;">
            🔴 Guard stopped — not checking this agent anymore
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            The guard found <strong>3 failures in a row</strong> and stepped back to avoid noise.
            It will automatically try again in <strong>~4 hours</strong>.
        </div>"""
    elif stale_alive:
        status_html = """
        <div style="font-size:13px;color:#eab308;font-weight:600;margin-bottom:8px;">
            ⚠️ Last check was over an hour ago
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            The agent <strong>was alive</strong> at its last check, but that was <strong>more than an hour ago</strong>.
            The guard shows 0 failures because nothing went wrong back then — but the agent
            could have died since. The dashboard already flags this as <strong>"Running (stale)"</strong>.
            Run <code>observeco pulse check</code> to get a fresh reading.
        </div>"""
    else:
        status_html = """
        <div style="font-size:13px;color:#22c55e;font-weight:600;margin-bottom:8px;">
            ✅ Guard is OK
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            The guard has detected <strong>0 failures</strong>. It checks every 30 seconds.
        </div>"""

    # Section 2: Failure timeline
    failure_rows = ""
    failure_summary = ""
    if errors:
        for e in errors[:10]:
            sev = e.get("severity", "warning")
            ts_str = _fmt_ts(e["timestamp"])
            msg = _html_escape(e.get("error_message", "") or e.get("message", "") or "?")[:100]
            is_bad = sev in ("critical", "error") or any(kw in msg.lower() for kw in ["timeout", "refused", "not found", "500", "503"])
            icon = "🔴" if is_bad else "🟡"
            failure_rows += f"""<tr><td class="error-tl-time">{ts_str}</td><td class="error-tl-status" style="color:{'#ef4444' if is_bad else '#eab308'};">{icon}</td><td class="error-tl-msg">{msg}</td></tr>"""

        if is_tripped:
            failure_summary = f"The guard triggered after <strong>3 consecutive failures</strong>. In total, <strong>{len(errors)} error{'s' if len(errors) > 1 else ''}</strong> were logged before it stopped checking."
        elif is_dead:
            failure_summary = f"<strong>{len(errors)} error{'s' if len(errors) > 1 else ''}</strong> logged from this agent — but the agent <strong>has been down</strong> throughout. The guard never tripped because the errors are spaced across gap-detection checks, not 3+ in a row."
        elif is_not_running or is_unknown:
            failure_summary = f"<strong>{len(errors)} error{'s' if len(errors) > 1 else ''}</strong> logged — the agent has never responded successfully so every check is logged as an error."
        else:
            failure_summary = f"{len(errors)} error{'s' if len(errors) > 1 else ''} detected but fewer than 3 in a row — the guard has not tripped."
    else:
        failure_rows = '<tr><td colspan="3" class="empty-table-msg">No failures recorded</td></tr>'
        failure_summary = "No failures. The guard has never tripped for this agent."

    # Section 3: Settings
    cooldown_remaining = ""
    if is_tripped:
        cd = circuit.get("cooldown_until", 0)
        rem = max(0, cd - now) if cd else 0
        cooldown_remaining = f" ({rem // 60}m {rem % 60}s remaining)"

    settings_html = f"""<table class="data-table">
        <tr><td>Failures before stop</td><td>
          <span id="circuitMaxRetries">{circuit.get("max_retries", 3)}</span>
          <button onclick="editCircuitRetries('{name}')" style="background:none;border:1px solid #334155;border-radius:4px;padding:2px 8px;font-size:10px;cursor:pointer;color:#94a3b8;margin-left:6px;">✏️</button>
        </td></tr>
        <tr><td>Max turns/min (activity threshold)</td><td>
          <span id="circuitMaxTurns">{conf.get("metadata", {}).get("max_turns_per_min", "— (off)") if isinstance(conf.get("metadata"), dict) else "— (off)"}</span>
          <button onclick="editCircuitTurns('{name}')" style="background:none;border:1px solid #334155;border-radius:4px;padding:2px 8px;font-size:10px;cursor:pointer;color:#94a3b8;margin-left:6px;">✏️</button>
        </td></tr>
        <tr><td>Cooldown period</td><td>
          <span id="circuitCooldown_{name}">{conf.get("metadata", {}).get("cooldown_minutes", 240) if isinstance(conf.get("metadata"), dict) else 240} min</span>
          <button onclick="editCircuitCooldown('{name}')" style="background:none;border:1px solid #334155;border-radius:4px;padding:2px 8px;font-size:10px;cursor:pointer;color:#94a3b8;margin-left:6px;">✏️</button>
          {cooldown_remaining}</td></tr>
        <tr><td>Auto-retry after cooldown</td><td class="good">Yes</td></tr>
        <tr><td>Current turn rate</td><td id="turnRate_{name}">—</td></tr>
    </table>
    <div id="circuitEditResult_{name}" style="font-size:11px;color:var(--fg-2);margin-top:4px;"></div>"""

    # Section 4: Recommendations (for dead/tripped/error agents)
    rec_html = ""
    if is_dead:
        rec_html = f"""<div class="modal-section">
        <h4>Recommended actions</h4>
        <div class="health-summary-body">
            • <strong>Restart the agent:</strong> <code>observeco start {name}</code><br>
            • <strong>Diagnose failure:</strong> <code>observeco heal --diagnose {name}</code><br>
            • <strong>Check logs:</strong> <code>observeco logs {name}</code>
        </div>
    </div>"""
    elif is_tripped:
        rec_html = f"""<div class="modal-section">
        <h4>Recommended actions</h4>
        <div class="health-summary-body">
            • <strong>Wait for cooldown</strong> — guard auto-retries after{cooldown_remaining}.<br>
            • <strong>Speed up recovery:</strong> Restart the agent manually to clear the error state.<br>
            • <strong>Reset guard:</strong> <code>observeco heal --reset {name}</code>
        </div>
    </div>"""
    elif errors and not is_tripped:
        rec_html = f"""<div class="modal-section">
        <h4>Recommended actions</h4>
        <div class="health-summary-body">
            • <strong>Monitor</strong> — errors detected but guard has not tripped yet.<br>
            • <strong>Run diagnostics:</strong> <code>observeco heal --diagnose {name}</code>
        </div>
    </div>"""

    return HTMLResponse(f"""<div class="detail-content">
    {conf_header}
    <div class="modal-section">
        <h4>Status</h4>
        {status_html}
    </div>
    <div class="modal-section">
        <h4>Failures that triggered the guard</h4>
        <table class="data-table">
            <tr><th style="width:70px;">Time</th><th style="width:50px;"></th><th>What happened</th></tr>
            {failure_rows}
        </table>
        <div class="health-summary-body">{failure_summary}</div>
    </div>
    <div class="modal-section">
        <h4>What the guard does</h4>
        <div class="health-summary-body">
            Without this guard, a dead agent gets checked every 30 seconds — generating error messages,
            filling your logs, and wasting resources. After <strong>3 failures in a row</strong>, the guard
            <strong>stops checking</strong> and enters cooldown. After cooldown expires, it tries again automatically.
            This prevents alert fatigue from a single downed agent.
        </div>
    </div>
    <div class="modal-section">
        <h4>Settings</h4>
        {settings_html}
    </div>
    {rec_html}
</div>""")


def _detail_errors_tab(name: str, errors: list, framework: str, agent_status: str = "unknown", conf: dict = None, is_pro: bool = False) -> str:
    """Error history — timeline table + categorized verdict + Pro upsell (or range selector for Pro)."""
    error_rows = ""
    is_dead = agent_status == "dead"
    is_not_running = agent_status == "not_running"
    is_unknown = agent_status == "unknown"
    conf_header = _confidence_header(conf) if conf else ""
    if errors:
        for e in errors[:20]:
            ts_str = _fmt_ts(e["timestamp"])
            sev = e.get("severity", "warning")
            msg = _html_escape(e.get("error_message", "") or e.get("message", "") or e.get("error_type", "?")[:120])
            col = {"critical": "#ef4444", "error": "#ef4444", "warning": "#eab308", "info": "#3b82f6"}.get(sev, "#6b7280")
            error_rows += f"""<tr><td>{ts_str}</td><td style="color:{col};">{msg}</td></tr>"""
    else:
        error_rows = '<tr><td colspan="2" class="empty-table-msg">No errors in the last 24 hours</td></tr>'

    total = len(errors)
    if total == 0 and is_dead:
        verdict_msg = (
            'Agent is <strong>down</strong>. No errors were logged because dead pulse records '
            'go to the health timeline, not the error table. Start the agent manually.'
        )
    elif total == 0 and is_not_running:
        verdict_msg = (
            'This agent has <strong>never been seen running</strong>. It\'s registered but hasn\'t '
            'responded to any pulse checks. If this is intentional, you can ignore this status.'
        )
    elif total == 0 and is_unknown:
        verdict_msg = (
            'No pulse data — this agent is not monitored by pulse checks. No errors have been '
            'logged, but we can\'t verify its health either.'
        )
    elif total == 0:
        verdict_msg = 'No errors means this agent has been running cleanly for the last 24 hours.'
    elif is_dead:
        verdict_msg = (
            f'This agent has been <strong>dead</strong> throughout — all {total} error{"s" if total > 1 else ""} '
            f'are from the system trying (and failing) to reach its process. '
            f'The agent will not recover on its own. Start it manually or check its configuration.'
        )
    elif total == 1:
        verdict_msg = 'One error in 24 hours is usually transient — network hiccup or temporary overload.'
    else:
        verdict_msg = 'Multiple errors suggest an ongoing problem. Check the guard status to see if monitoring has been stopped automatically.'

    # Server-side decide: Pro gets range buttons, Free gets upsell
    history_section = ""
    if is_pro:
        history_section = f"""<div class="modal-section" id="historyRange_{name}" style="border:1px solid var(--border);border-radius:10px;padding:14px;">
        <h4 style="margin-bottom:6px;font-size:13px;">📅 Extended History</h4>
        <div style="display:flex;gap:6px;margin-bottom:8px;">
            <button onclick="loadAgentErrorHistory('{name}', 1)" class="range-btn active" id="range1d_{name}" style="background:var(--accent-on);color:#86efac;border:1px solid rgba(34,197,94,0.2);border-radius:6px;padding:4px 10px;font-size:10px;font-weight:600;cursor:pointer;">24h</button>
            <button onclick="loadAgentErrorHistory('{name}', 7)" class="range-btn" id="range7d_{name}" style="background:var(--surface);color:#94a3b8;border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:10px;cursor:pointer;">7d</button>
            <button onclick="loadAgentErrorHistory('{name}', 30)" class="range-btn" id="range30d_{name}" style="background:var(--surface);color:#94a3b8;border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:10px;cursor:pointer;">30d</button>
            <button onclick="loadAgentErrorHistory('{name}', 90)" class="range-btn" id="range90d_{name}" style="background:var(--surface);color:#94a3b8;border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:10px;cursor:pointer;">90d</button>
        </div>
        <div id="extendedHistory_{name}" style="font-size:11px;color:#64748b;">Click a range above to load.</div>
    </div>"""
    else:
        history_section = f"""<div class="modal-section" id="historyRange_{name}" style="border:1px dashed #3730a3;border-radius:10px;padding:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div id="historyRangeContent_{name}">
                <h4 style="margin-bottom:4px;font-size:13px;">🔒 More history unlocks patterns</h4>
                <div style="font-size:11px;color:#64748b;line-height:1.6;">
                    Free: last 24h only. Pro keeps every day from install — so next week you can see if errors are getting
                    <strong style="color:#f97316;">better or worse</strong>.<br>
                    <span style="color:#a5b4fc;">Weekly trend charts · regression alerts · never pruned</span>
                </div>
            </div>
        </div>
    </div>"""

    return HTMLResponse(f"""<div class="detail-content">
    {conf_header}
    <div class="modal-section">
        <h4>Last 24 hours <span class="glossary-hint" onclick="event.stopPropagation();showGlossary('error-tab', event)" style="font-size:11px;cursor:pointer;background:#334155;border-radius:4px;padding:1px 6px;color:#94a3b8;font-weight:400;margin-left:6px;">?</span></h4>
        <table class="data-table">
            <tr><th style="width:70px;">Time</th><th>What happened</th></tr>
            {error_rows}
        </table>
    </div>
    <div class="modal-section">
        <h4>What this means</h4>
        <div class="health-summary-body">{verdict_msg}</div>
    </div>
    {history_section}
</div>
<script>
function loadAgentErrorHistory(agent, days) {{
    document.querySelectorAll('#historyRangeContent_' + agent + ' .range-btn').forEach(b => b.style.background = 'var(--surface)');
    document.querySelectorAll('#historyRangeContent_' + agent + ' .range-btn').forEach(b => b.style.color = '#94a3b8');
    const active = document.getElementById('range' + days + 'd_' + agent);
    if (active) {{ active.style.background = 'var(--accent-on)'; active.style.color = '#86efac'; }}
    fetch('/api/agent/' + encodeURIComponent(agent) + '/errors?days=' + days)
        .then(r => r.text())
        .then(html => {{
            const el = document.getElementById('extendedHistory_' + agent);
            if (el) el.innerHTML = html;
        }})
        .catch(function() {{}});
}}
</script>""")


def _detail_garden_tab(name: str, garden: list, profile: list, framework: str) -> str:
    if garden and garden[0].get("memory_debt_score") is not None and garden[0]["memory_debt_score"] > 0:
        g = garden[0]
        score = g.get("memory_debt_score", 0)
        grade = "A" if score < 20 else "B" if score < 40 else "C" if score < 60 else "D" if score < 80 else "F"
        grade_color = "#22c55e" if grade == "A" else "#eab308" if grade in ("B", "C") else "#ef4444"

        return HTMLResponse(f"""<div class="detail-content">
    <div class="score-display">
        <div class="score-box">
            <div class="score-num score-value" style="color:{grade_color};">{score:.0f}</div>
            <div class="score-label">Debt Score</div>
        </div>
        <div class="score-box">
            <div class="score-num score-value" style="color:{grade_color};">{grade}</div>
            <div class="score-label">Grade</div>
        </div>
    </div>
    <div class="garden-grid">
        <div class="garden-metric-card">
            <span class="garden-metric-num metric-red" style="color:#ef4444;">{g['duplicates_found']}</span>
            <span class="garden-metric-label">Duplicates</span>
        </div>
        <div class="garden-metric-card">
            <span class="garden-metric-num metric-amber" style="color:#f97316;">{g['contradictions_found']}</span>
            <span class="garden-metric-label">Contradictions</span>
        </div>
        <div class="garden-metric-card">
            <span class="garden-metric-num metric-dim" style="color:#6b7280;">{g['stale_entries']}</span>
            <span class="garden-metric-label">Stale Entries</span>
        </div>
    </div>
</div>""")

    # No garden data — explain that data accumulates as the daemon watches, quantify uptime
    # Check if watch daemon is actually running and for how long
    import os
    watch_pid_path = os.path.expanduser("~/.observeco/.watch.pid")
    daemon_status = ""
    try:
        if os.path.exists(watch_pid_path):
            pid = int(Path(watch_pid_path).read_text().strip())
            alive = False
            try:
                os.kill(pid, 0)
                alive = True
            except (OSError, ProcessLookupError):
                pass
            if alive:
                mtime = os.path.getmtime(watch_pid_path)
                uptime_seconds = int(time.time()) - mtime
                if uptime_seconds < 3600:
                    uptime_str = f"{uptime_seconds // 60}m"
                elif uptime_seconds < 86400:
                    uptime_str = f"{uptime_seconds // 3600}h {uptime_seconds % 3600 // 60}m"
                else:
                    uptime_str = f"{uptime_seconds // 86400}d {uptime_seconds % 86400 // 3600}h"
                daemon_status = """<div class="garden-metric-card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
                    <span class="garden-metric-num" style="color:#22c55e;">""" + uptime_str + """</span>
                    <span class="garden-metric-label">Watch daemon uptime</span>
                </div>"""
            else:
                daemon_status = """<div class="garden-metric-card" style="background:rgba(234,179,8,0.08);border:1px solid rgba(234,179,8,0.2);">
                    <span class="garden-metric-num" style="color:#eab308;">Not running</span>
                    <span class="garden-metric-label">Watch daemon</span>
                </div>"""
        else:
            daemon_status = """<div class="garden-metric-card" style="background:var(--surface);border:1px solid var(--border);">
                <span class="garden-metric-num" style="color:#64748b;">—</span>
                <span class="garden-metric-label">Watch daemon (never started)</span>
            </div>"""
    except Exception:
        daemon_status = ""

    return HTMLResponse(f"""<div class="detail-content">
    <div class="modal-section">
        <h4>💾 Memory & Context</h4>
        <div style="font-size:13px;color:#94a3b8;margin-bottom:12px;line-height:1.6;">
            Memory quality data builds up over time. Results appear here after the watch daemon
            has collected enough data through active monitoring.
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;">
            <div class="garden-metric-card" style="background:var(--surface);border:1px solid var(--border);">
                <span class="garden-metric-num" style="color:#6366f1;">24h+</span>
                <span class="garden-metric-label">Minimum monitoring</span>
            </div>
            <div class="garden-metric-card" style="background:var(--surface);border:1px solid var(--border);">
                <span class="garden-metric-num" style="color:#6366f1;">50+</span>
                <span class="garden-metric-label">Interactions needed</span>
            </div>
            <div class="garden-metric-card" style="background:var(--surface);border:1px solid var(--border);">
                <span class="garden-metric-num" style="color:#6366f1;">~7d</span>
                <span class="garden-metric-label">For stable scores</span>
            </div>
            {daemon_status}
        </div>
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px;margin-top:8px;">
            <div style="font-size:12px;font-weight:600;color:#e2e8f0;margin-bottom:8px;">
                🚀 Start monitoring your agents now:
            </div>
            <div style="background:var(--surface);border-radius:8px;padding:12px;font-family:var(--font-mono);font-size:12px;line-height:1.8;">
                <span style="color:#64748b;"># One command in terminal</span><br>
                <span style="color:var(--accent);font-weight:600;">observeco watch start</span><br>
                <span style="color:#64748b;font-size:11px;">Starts the watch daemon in the background. It'll begin collecting pulse data immediately.</span><br><br>
                <span style="color:#64748b;"># Check status</span><br>
                <span style="color:#94a3b8;">observeco watch status</span>
            </div>
            <div style="font-size:12px;color:#64748b;margin-top:10px;line-height:1.6;">
                No config needed. The daemon auto-discovers agents from Hermes profiles/agents or the active OpenClaw config, pings them every 30s, and logs pulses to the database. As data accumulates, this tab fills with memory quality scores, drift analysis, and token recommendations.
            </div>
        </div>
            </div>
        </div>
    </div>
</div>""")


# ── NEW: /api/errors —— Error Timeline ──────────────────────────────

@app.get("/api/errors", response_class=HTMLResponse)
async def api_errors():
    """Error timeline — §6.5. Categorized + plain-English verdict."""
    errors = db.get_errors(limit=50)
    if not errors:
        return HTMLResponse('<div class="empty-state">No errors in the last 24h. Errors appear here automatically when pulse checks detect failures or when agents log error events.</div>')
    now = int(time.time())

    # Categorize errors
    categories = {"timeout": 0, "connection": 0, "resource": 0, "http_5xx": 0, "other": 0}
    for e in errors:
        msg = (e.get("error_type", "") + " " + e.get("error_message", "")).lower()
        etype = e.get("error_type", "").lower()
        if "timeout" in msg or "timed out" in msg or etype == "timeout":
            categories["timeout"] += 1
        elif "connection" in msg or "refused" in msg or etype == "connection_refused" or "connection refused" in msg:
            categories["connection"] += 1
        elif "not found" in msg or "missing" in msg or "resource" in msg or "dependency" in msg:
            categories["resource"] += 1
        elif "5" in etype and ("00" in etype or "03" in etype):  # 500, 502, 503
            categories["http_5xx"] += 1
        else:
            categories["other"] += 1

    total = len(errors)

    # Build plain-English summary
    parts = []
    if categories["timeout"]:
        parts.append(f"""<span class="error-category">⏱ {categories["timeout"]} timeout{'s' if categories["timeout"] > 1 else ''}</span> — agent was running but didn't respond in time. Usually overloaded or stuck.""")
    if categories["connection"]:
        parts.append(f"""<span class="error-category connection">🔗 {categories["connection"]} connection refused</span> — the agent endpoint is down or unreachable.""")
    if categories["resource"]:
        parts.append(f"""<span class="error-category resource">🔍 {categories["resource"]} resource{'s' if categories["resource"] > 1 else ''} not found</span> — a dependency the agent needs is missing.""")
    if categories["http_5xx"]:
        parts.append(f"""<span class="error-category http">🌐 {categories["http_5xx"]} HTTP 5xx</span> — the server returned an internal error.""")
    if categories["other"]:
        parts.append(f"""<span class="error-category other">❓ {categories["other"]} other error{'s' if categories["other"] > 1 else ''}</span> — check the full list below.""")

    # Verdict
    if total == 1:
        verdict = '<span class="verdict-1">🟡 1 error in 24h — likely transient. Monitor but no action needed unless it reappears.</span>'
    elif total <= 3:
        verdict = f'<span class="verdict-2">🟠 {total} errors in 24h — agent may be unstable. Check the categories below.</span>'
    else:
        verdict = f'<span class="verdict-3">🔴 {total} errors in 24h — ongoing problem detected. Check guard status and agent health.</span>'

    # Summary banner
    html = f"""
<div class="error-summary-card">
    <div class="error-summary-title">📊 Error Summary — {total} in last 24h</div>
    <div class="error-summary-body">
        {"<br>".join(parts) if parts else "No issues detected."}
    </div>
    <div class="error-summary-verdict">
        {verdict}
    </div>
</div>
"""

    # Annotated timeline
    items = []
    for e in errors[:50]:
        ts = _fmt_ts(e.get("timestamp", now))
        agent = e.get("agent_name", e.get("agent", "?"))
        msg = e.get("error_message", "") or e.get("message", "") or e.get("error_type", "?")
        sev = e.get("severity", "warning")
        col = {"critical": "#ef4444", "error": "#ef4444", "warning": "#eab308", "info": "#3b82f6"}.get(sev, "#6b7280")
        icon = {"critical": "🔴", "error": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
        items.append(f"""<div class="error-timeline-item" style="border-left-color:{sev}" style="border-left:3px solid {col};padding:8px 10px;margin-bottom:4px;border-radius:6px;background:rgba(15,23,42,0.5);font-size:12px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
        <span class="error-timeline-type" style="color:{col};font-weight:600;">{icon} {_html_escape(e.get('error_type','error'))}</span>
        <span class="error-timeline-ts">{ts}</span>
    </div>
    <div class="error-timeline-msg">{_html_escape(msg[:120])}</div>
    <div class="error-timeline-agent">{_html_escape(agent)}</div>
</div>""")

    return HTMLResponse(html + "\n".join(items))


@app.get("/api/agent/{agent_name}/errors", response_class=HTMLResponse)
async def api_agent_errors_range(agent_name: str, days: int = 1):
    """Extended error history for a specific agent over N days — Pro feature."""
    from observeco import license as lic
    if not lic.require_pro():
        return HTMLResponse('<div style="color:#64748b;font-size:11px;padding:8px;">🔒 Extended history requires Pro</div>')

    now = int(time.time())
    since = now - (days * 86400)
    errors = db.get_errors_since(agent_name, since, limit=200)

    if not errors:
        return HTMLResponse(f'<div style="color:#64748b;font-size:11px;padding:8px;">No errors in the last {days} day(s) for this agent.</div>')

    items = []
    for e in errors[:100]:
        ts = _fmt_ts(e.get("timestamp", now))
        msg = e.get("error_message", "") or e.get("message", "") or e.get("error_type", "?")
        sev = e.get("severity", "warning")
        col = {"critical": "#ef4444", "error": "#ef4444", "warning": "#eab308", "info": "#3b82f6"}.get(sev, "#6b7280")
        icon = {"critical": "🔴", "error": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
        items.append(f"""<div style="border-left:3px solid {col};padding:6px 10px;margin-bottom:3px;border-radius:4px;background:rgba(15,23,42,0.5);font-size:11px;">
    <div style="display:flex;justify-content:space-between;">
        <span style="color:{col};font-weight:600;">{icon} {_html_escape(e.get('error_type','error'))}</span>
        <span style="color:#64748b;">{ts}</span>
    </div>
    <div style="color:#94a3b8;margin-top:2px;">{_html_escape(msg[:120])}</div>
</div>""")

    return HTMLResponse(f"""<div style="font-size:10px;color:#64748b;margin-bottom:6px;">{len(errors)} error(s) in last {days}d</div>
{"".join(items)}""")


@app.get("/api/reset-circuit/{agent_name}")
async def api_reset_circuit(agent_name: str):
    """Reset a tripped circuit breaker."""
    db.reset_breaker(agent_name)
    return HTMLResponse(f'<span class="circuit-result">Circuit reset for {agent_name}</span>')


@app.post("/api/circuit-breaker/{agent_name}/config")
async def api_circuit_breaker_config(agent_name: str, max_retries: int = None, max_turns_per_min: int = None, cooldown_minutes: int = None):
    """G1.3: Update circuit breaker config (max retries + activity threshold + cooldown)."""
    try:
        db.update_circuit_breaker_config(agent_name, max_retries=max_retries, max_turns_per_min=max_turns_per_min, cooldown_minutes=cooldown_minutes)
        return JSONResponse({"ok": True, "message": "Updated"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/agents/{agent_name}/turn-rate")
async def api_agent_turn_rate(agent_name: str):
    """G1.4: Estimate turn rate from recent pulse data."""
    try:
        pulses = db.get_recent_pulses(agent_name, limit=50)
        if not pulses or len(pulses) < 2:
            return JSONResponse({"turns_per_min": None, "status": "insufficient_data"})
        # Use time between pulses to estimate frequency
        now = int(time.time())
        recent = [p for p in pulses if now - p.get("timestamp", 0) < 3600]
        if len(recent) >= 2:
            timespan = recent[-1]["timestamp"] - recent[0]["timestamp"]
            if timespan > 0:
                turns_per_min = round((len(recent) / timespan) * 60, 1)
                threshold = 30
                alerted = turns_per_min > threshold
                return JSONResponse({
                    "turns_per_min": turns_per_min,
                    "pulses_in_last_hour": len(recent),
                    "threshold": threshold,
                    "alerted": alerted,
                    "status": "alerted" if alerted else "normal",
                })
        return JSONResponse({"turns_per_min": 0, "pulses_in_last_hour": len(recent), "status": "normal"})
    except Exception as e:
        return JSONResponse({"turns_per_min": None, "status": "error", "error": str(e)})


# ---------------------------------------------------------------------------
# §6.1 — Fleet Header with drift
# ---------------------------------------------------------------------------

@app.get("/api/fleet-summary", response_class=HTMLResponse)
async def api_fleet_summary():
    """Fleet header with drift — §6.1."""
    summary = db.get_agent_status_summary()
    circuit = db.get_circuit_breakers()
    drift = db.get_drift()

    total = len(summary) if summary else len(db.get_agents())
    alive = sum(1 for s in summary.values() if s.get("status") == "alive")
    dead = sum(1 for s in summary.values() if s.get("status") == "dead")
    error_count = sum(1 for s in summary.values() if s.get("status") == "error")
    tripped = sum(1 for c in circuit if c.get("tripped"))

    # Compute average drift
    drift_vals = [d.get("delta_pct", 0) for d in drift if d.get("breached")]
    avg_drift = sum(drift_vals) / len(drift_vals) if drift_vals else 0
    drift_arrow = "📈" if avg_drift > 0 else "📉" if avg_drift < 0 else ""
    drift_text = f"Tokens: {avg_drift:+.1f}% this week {drift_arrow}" if drift_vals else ""

    trip_badge = f'<span class="trip-badge">⚠️ {tripped} tripped</span>' if tripped else ""

    return HTMLResponse(f"""<div class="status-row" id="statusRow">
    <span class="status-stat"><span class="status-dot alive"></span><strong>{alive}</strong> alive</span>
    <span class="status-stat"><span class="status-dot error"></span><strong>{error_count}</strong> warning</span>
    <span class="status-stat"><span class="status-dot dead"></span><strong>{dead}</strong> down</span>
    <span class="status-stat"><strong>{total}</strong> agents</span>
    {f'<span class="status-stat"><strong>{drift_text}</strong></span>' if drift_text else ''}
    {trip_badge}
      <button class="feedback-btn" onclick="toggleFeedback()">+ Missing an agent?</button>
      <button class="feedback-btn u-ml-8" onclick="openPathwayModal()">🕸️ Pathway map</button>
      <button class="feedback-btn u-ml-8" onclick="loadPlatforms()">🔌 Platforms</button>
      <span id="platformStatus"></span>
</div>""")


@app.get("/api/fleet-compare", response_class=HTMLResponse)
async def api_fleet_compare(sort: str = "name", order: str = "asc"):
    """Side-by-side fleet comparison — § Fleet Comparison. Supports sort column + order."""
    summary = db.get_agent_status_summary()
    agents = db.get_agents()
    trims_all = db.get_trims(limit=30)
    drift_all = db.get_drift()
    circuit = db.get_circuit_breakers()
    all_errors = db.get_errors(limit=100)

    order_asc = order.lower() != "desc"

    # Build per-agent data
    agent_cfg = {a["agent_name"]: a for a in agents}
    latest_trims = {}
    for t in trims_all:
        if t["agent_name"] not in latest_trims:
            latest_trims[t["agent_name"]] = t

    drift_latest = {}
    for d in drift_all:
        if d["agent_name"] not in drift_latest:
            drift_latest[d["agent_name"]] = d

    breakers = {b["agent_name"]: b for b in circuit}

    now = int(time.time())

    # Build agent data dicts
    agent_data = {}
    all_names = set(summary.keys()) | set(agent_cfg.keys()) | set(latest_trims.keys()) | set(drift_latest.keys())

    for name in all_names:
        s = summary.get(name, {})
        fw = agent_cfg.get(name, {}).get("framework", "") or ""
        trim = latest_trims.get(name, {})
        tok_total = trim.get("total_tokens", 0)
        dr = drift_latest.get(name, {})
        drift_pct = dr.get("delta_pct", 0)
        drift_breached = dr.get("breached", False)
        recent_errors = [e for e in all_errors if e.get("agent_name") == name and now - e.get("timestamp", 0) < 86400]
        err_count = len(recent_errors)
        cb = breakers.get(name, {})
        ts = s.get("timestamp", 0)

        agent_data[name] = {
            "status": s.get("status", "unknown"),
            "framework": fw.capitalize() if fw else "-",
            "tokens": tok_total,
            "drift_pct": drift_pct,
            "drift_breached": drift_breached,
            "errors": err_count,
            "circuit_tripped": cb.get("tripped", False),
            "last_seen": ts,
        }

    # Sort by requested column
    sort_key_map = {
        "name": lambda n: n.lower(),
        "framework": lambda n: agent_data[n]["framework"],
        "tokens": lambda n: agent_data[n]["tokens"],
        "drift": lambda n: agent_data[n]["drift_pct"],
        "errors": lambda n: agent_data[n]["errors"],
        "circuit": lambda n: 1 if agent_data[n]["circuit_tripped"] else 0,
        "last": lambda n: agent_data[n]["last_seen"],
    }
    key_fn = sort_key_map.get(sort, sort_key_map["name"])
    sorted_names = sorted(all_names, key=key_fn, reverse=not order_asc)

    rows = []
    for name in sorted_names:
        d = agent_data[name]
        status = d["status"]

        trim = latest_trims.get(name, {})
        tok_total = trim.get("total_tokens", 0)
        comps = [
            ("identity", trim.get("identity_tokens", 0), "#6366f1"),
            ("skills", trim.get("skills_tokens", 0), "#8b5cf6"),
            ("memory", trim.get("memory_tokens", 0), "#ec4899"),
            ("tools", trim.get("tools_tokens", 0), "#14b8a6"),
            ("guidance", trim.get("guidance_tokens", 0), "#f97316"),
        ]
        comp_bars = ""
        for cname, ctok, ccolor in comps:
            pct = (ctok / tok_total * 100) if tok_total > 0 else 0
            if pct > 0:
                comp_bars += f'<span style="display:inline-block;width:{pct:.0f}%;height:6px;background:{ccolor};border-radius:2px;margin-right:1px;" title="{cname}: {ctok}tok ({pct:.0f}%)"></span>'

        tok_label = f"{tok_total:,}" if tok_total else "-"
        drift_pct = d["drift_pct"]
        drift_label = f"{drift_pct:+.1f}%" if drift_pct else "-"
        drift_color = "#ef4444" if d["drift_breached"] else "#22c55e" if abs(drift_pct) > 5 else "#64748b"
        err_label = f'{d["errors"]} <span style="color:var(--danger);font-size:10px;">⚠</span>' if d["errors"] > 0 else "0"
        cb_status = "🔴 Tripped" if d["circuit_tripped"] else "✅ OK"
        ts = d["last_seen"]
        last_seen = _fmt_ts(ts) if ts else "-"

        rows.append(f"""<tr onclick="htmx.ajax('GET', '/api/fleet/modal/{name}', {{target:'#modalContainer', swap:'innerHTML'}})" style="cursor:pointer">
    <td style="padding:10px 12px;font-weight:600;white-space:nowrap;"><span class="agent-status {status}" style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;"></span>{name}</td>
    <td style="padding:10px 12px;font-size:11px;color:#94a3b8;">{d["framework"]}</td>
    <td style="padding:10px 12px;font-family:var(--font-mono);font-size:12px;">{tok_label}</td>
    <td style="padding:10px 12px;min-width:120px;"><div style="display:flex;gap:1px;align-items:center;height:6px;">{comp_bars if comp_bars else '<span style="color:#64748b;font-size:10px;">no data</span>'}</div></td>
    <td style="padding:10px 12px;font-family:var(--font-mono);font-size:12px;color:{drift_color};">{drift_label}</td>
    <td style="padding:10px 12px;font-family:var(--font-mono);font-size:12px;">{err_label}</td>
    <td style="padding:10px 12px;font-size:11px;">{cb_status}</td>
    <td style="padding:10px 12px;font-size:11px;color:#64748b;">{last_seen}</td>
</tr>""")

    if not rows:
        return HTMLResponse("""<div class="empty-state" style="text-align:center;padding:40px;color:#64748b;">
    <div style="font-size:32px;margin-bottom:12px;">📊</div>
    <div style="font-weight:600;margin-bottom:4px;">No agents to compare</div>
    <div style="font-size:12px;">Agents will appear here once they're discovered and monitored.</div>
</div>""")

    return HTMLResponse(f"""<div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead>
            <tr style="border-bottom:1px solid var(--border);">
                <th onclick="sortCompare('name')" style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;cursor:pointer;user-select:none;">Agent <span id="sortIndicator_name" class="sort-indicator"></span></th>
                <th onclick="sortCompare('framework')" style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;cursor:pointer;user-select:none;">Framework <span id="sortIndicator_framework" class="sort-indicator"></span></th>
                <th onclick="sortCompare('tokens')" style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;cursor:pointer;user-select:none;">Tokens <span id="sortIndicator_tokens" class="sort-indicator"></span></th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Composition</th>
                <th onclick="sortCompare('drift')" style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;cursor:pointer;user-select:none;">Drift <span id="sortIndicator_drift" class="sort-indicator"></span></th>
                <th onclick="sortCompare('errors')" style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;cursor:pointer;user-select:none;">Errors <span id="sortIndicator_errors" class="sort-indicator"></span></th>
                <th onclick="sortCompare('circuit')" style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;cursor:pointer;user-select:none;">Circuit <span id="sortIndicator_circuit" class="sort-indicator"></span></th>
                <th onclick="sortCompare('last')" style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;cursor:pointer;user-select:none;">Last <span id="sortIndicator_last" class="sort-indicator"></span></th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
</div>""")


# ---------------------------------------------------------------------------
# § Platform Connectivity — live probe of messaging platforms
# ---------------------------------------------------------------------------


@app.get("/api/platforms", response_class=HTMLResponse)
async def api_platforms():
    """Probe local platforms and return their connectivity status."""
    import httpx as _httpx
    platforms = {}
    now = int(time.time())

    # 1. Hermes gateway
    try:
        r = _httpx.get("http://127.0.0.1:8642/health", timeout=3)
        platforms["gateway"] = {"status": "up", "latency_ms": int(r.elapsed.total_seconds() * 1000)} if r.status_code == 200 else {"status": "error", "http": r.status_code}
    except Exception as e:
        platforms["gateway"] = {"status": "down", "error": str(e)[:60]}

    # 2. ObserveCo webhook
    try:
        r = _httpx.get("http://127.0.0.1:9120/health", timeout=3)
        platforms["webhook"] = {"status": "up", "latency_ms": int(r.elapsed.total_seconds() * 1000)} if r.status_code == 200 else {"status": "error", "http": r.status_code}
    except Exception as e:
        platforms["webhook"] = {"status": "down", "error": str(e)[:60]}

    # 3. iMessage (BlueBubbles)
    try:
        r = _httpx.get(f"http://127.0.0.1:{PORTS.imessage}/", timeout=3)
        platforms["imessage"] = {"status": "up"} if r.status_code == 200 else {"status": "error", "http": r.status_code}
    except Exception:
        platforms["imessage"] = {"status": "down"}

    # 4. Telegram API (public reachability)
    try:
        r = _httpx.get("https://api.telegram.org/botINVALID/getMe", timeout=5)
        platforms["telegram"] = {"status": "reachable", "latency_ms": int(r.elapsed.total_seconds() * 1000)}
    except Exception:
        platforms["telegram"] = {"status": "down"}

    # 5. WhatsApp bridge
    try:
        r = _httpx.get("http://127.0.0.1:3000/", timeout=3)
        platforms["whatsapp"] = {"status": "up"} if r.status_code == 200 else {"status": "error", "http": r.status_code}
    except Exception:
        platforms["whatsapp"] = {"status": "down"}

    # Render connectivity badges as a compact modal card
    platform_icons = {"gateway": "🌐", "webhook": "🔗", "imessage": "💬", "telegram": "✈️", "whatsapp": "📱"}
    platform_desc = {"gateway": "Hermes API Gateway", "webhook": "ObserveCo Webhook Server", "imessage": "BlueBubbles (iMessage)", "telegram": "Telegram Bot API", "whatsapp": "WhatsApp Bridge"}
    rows = ""
    for name, info in sorted(platforms.items()):
        label = f"{info['status'].capitalize()}"
        if "latency_ms" in info and info["status"] == "up":
            label += f" — {info['latency_ms']}ms"
        elif "latency_ms" in info and info["status"] == "reachable":
            label += f" ({info['latency_ms']}ms)"
        if info["status"] == "error" and "http" in info:
            label += f" (HTTP {info['http']})"
        status_color = {"up": "#22c55e", "reachable": "#22c55e", "error": "#eab308", "down": "#ef4444"}.get(info["status"], "#6b7280")
        plt_icon = platform_icons.get(name, "🔌")
        desc = platform_desc.get(name, name)

        rows += f"""<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--surface);border:1px solid var(--border);border-radius:8px;">
    <div style="width:32px;height:32px;border-radius:8px;background:{status_color}18;display:flex;align-items:center;justify-content:center;font-size:16px;">{plt_icon}</div>
    <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:13px;font-weight:600;color:#e2e8f0;">{name}</span>
            <span style="font-size:10px;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{desc}</span>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
        <span style="width:8px;height:8px;border-radius:50%;background:{status_color};"></span>
        <span style="font-size:12px;color:{status_color};font-weight:500;">{label}</span>
    </div>
</div>"""

    return HTMLResponse(f"""<div id="platformModal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:1000;display:flex;align-items:center;justify-content:center;" onclick="if(event.target===this)this.style.display='none'">
    <div style="background:var(--bg);border:1px solid var(--border);border-radius:14px;width:480px;max-width:90vw;max-height:80vh;overflow-y:auto;padding:20px;box-shadow:0 20px 60px rgba(0,0,0,0.4);" onclick="event.stopPropagation()">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
            <div>
                <div style="font-size:15px;font-weight:700;color:#e2e8f0;">🔌 Platform Connectivity</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">Live health check of messaging gateways and APIs</div>
            </div>
            <button onclick="document.getElementById('platformModal').style.display='none'" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;width:30px;height:30px;cursor:pointer;color:#94a3b8;font-size:16px;">✕</button>
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;">
            {rows}
        </div>
        <div style="font-size:10px;color:#475569;margin-top:10px;text-align:center;">Last checked: {datetime.fromtimestamp(now).strftime('%H:%M:%S')}</div>
    </div>
</div>""")


# ---------------------------------------------------------------------------
# § Agent count for pagination/search state
# ---------------------------------------------------------------------------

@app.get("/api/agent-count")
async def api_agent_count():
    """Return agent count for pagination state (used by frontend)."""
    agents = db.get_agents()
    return JSONResponse({"total": len(agents)})


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# § Brain Analysis endpoint — mockup brain-analysis.html
# ---------------------------------------------------------------------------

BRAIN_COMP_COLORS = {"identity": "#6366f1", "skills": "#8b5cf6", "memory": "#ec4899",
                     "tools": "#14b8a6", "guidance": "#f97316"}
BRAIN_COMP_ORDER = ["skills", "tools", "memory", "guidance", "identity"]
BRAIN_COMP_NAMES = {"identity": "Identity", "skills": "Skills", "memory": "Memory",
                    "tools": "Tools", "guidance": "Guidance"}

@app.get("/api/brain")
async def api_brain(agent: str = "all"):
    """Brain analysis data — token breakdown, savings, drift, timeline per agent or fleet."""
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row

    agents = [dict(r) for r in conn.execute(
        "SELECT * FROM agent_configs WHERE agent_name NOT IN ('stdin','test-agent-ci') ORDER BY agent_name"
    ).fetchall()]

    result = {}

    for a in agents:
        name = a["agent_name"]
        framework = a.get("framework", "hermes")

        # Latest trim data
        trim = conn.execute(
            "SELECT * FROM chisel_trims WHERE agent_name=? ORDER BY timestamp DESC LIMIT 1",
            (name,)
        ).fetchone()

        total_tokens = dict(trim)["total_tokens"] if trim else 0
        comps_raw = {
            "skills": dict(trim)["skills_tokens"] if trim else 0,
            "tools": dict(trim)["tools_tokens"] if trim else 0,
            "memory": dict(trim)["memory_tokens"] if trim else 0,
            "guidance": dict(trim)["guidance_tokens"] if trim else 0,
            "identity": dict(trim)["identity_tokens"] if trim else 0,
        } if trim else {"skills": 0, "tools": 0, "memory": 0, "guidance": 0, "identity": 0}

        # Only include non-zero components
        components = {k: v for k, v in comps_raw.items() if v > 0}

        raw_tokens = total_tokens if total_tokens > 0 else sum(components.values())
        # Potential savings from fleet-wide compress_log averages (if any real runs exist)
        guidance_pct = (components.get("guidance", 0) / max(raw_tokens, 1)) * 100
        memory_pct = (components.get("memory", 0) / max(raw_tokens, 1)) * 100
        skills_pct = (components.get("skills", 0) / max(raw_tokens, 1)) * 100

        # Fleet-wide compress_log averages — real data from any agent that's been compressed
        fleet_lite_avg = conn.execute(
            "SELECT ROUND(AVG(savings_pct), 1) as avg_pct FROM compress_log WHERE mode='lite' AND savings_pct IS NOT NULL"
        ).fetchone()
        fleet_full_avg = conn.execute(
            "SELECT ROUND(AVG(savings_pct), 1) as avg_pct FROM compress_log WHERE mode='full' AND savings_pct IS NOT NULL"
        ).fetchone()
        fleet_lite_pct = float(fleet_lite_avg["avg_pct"]) if fleet_lite_avg and fleet_lite_avg["avg_pct"] is not None else None
        fleet_full_pct = float(fleet_full_avg["avg_pct"]) if fleet_full_avg and fleet_full_avg["avg_pct"] is not None else None

        # Per-agent actual compression data
        has_compress = conn.execute(
            "SELECT COUNT(*) as c FROM compress_log WHERE agent_name=? AND savings_pct IS NOT NULL",
            (name,)
        ).fetchone()
        has_real_compress = has_compress and has_compress["c"] > 0
        lite_tokens = None
        full_tokens = None
        lite_potential_pct = None
        full_potential_pct = None

        if has_real_compress:
            # Use this agent's actual compress data
            lite_row = conn.execute(
                "SELECT ROUND(AVG(savings_pct), 1) as avg_pct FROM compress_log WHERE agent_name=? AND mode='lite' AND savings_pct IS NOT NULL",
                (name,)
            ).fetchone()
            full_row = conn.execute(
                "SELECT ROUND(AVG(savings_pct), 1) as avg_pct FROM compress_log WHERE agent_name=? AND mode='full' AND savings_pct IS NOT NULL",
                (name,)
            ).fetchone()
            lite_avg = float(lite_row["avg_pct"]) if lite_row and lite_row["avg_pct"] is not None else None
            full_avg = float(full_row["avg_pct"]) if full_row and full_row["avg_pct"] is not None else None
            if lite_avg is not None and lite_avg > 0:
                lite_tokens = int(raw_tokens * (1 - lite_avg / 100))
            if full_avg is not None and full_avg > 0:
                full_tokens = int(raw_tokens * (1 - full_avg / 100))
            savings_source = "actual"
        elif fleet_lite_pct is not None and fleet_lite_pct > 0:
            # No per-agent data, but fleet-wide compress averages exist — apply real % to composition
            # Lite compresses only guidance, Full compresses guidance + memory + skills
            lite_potential_pct = round(guidance_pct * (fleet_lite_pct / 100), 1)
            full_potential_pct = round(
                guidance_pct * (fleet_lite_pct / 100) +
                (memory_pct + skills_pct) * (fleet_full_pct / 100),
                1
            ) if fleet_full_pct else lite_potential_pct
            savings_source = "potential"
        else:
            # No compression has ever been run — derive estimates from composition
            # Lite: ~60% of guidance is compressible (guidance blocks are verbose)
            # Full: ~60% guidance + ~40% of memory+skills
            lite_potential_pct = round(guidance_pct * 0.6, 1)
            full_potential_pct = round(
                guidance_pct * 0.6 + (memory_pct + skills_pct) * 0.4,
                1
            )
            savings_source = "potential"

        # Drift data
        drift_rows = [dict(r) for r in conn.execute(
            "SELECT * FROM chisel_drift WHERE agent_name=? ORDER BY component",
            (name,)
        ).fetchall()]

        drift = []
        seen_comps = set()
        for d in drift_rows:
            comp = d["component"]
            if comp not in seen_comps:
                seen_comps.add(comp)
                delta = d.get("delta_pct", 0) or 0
                direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
                # Build 7-point weekly data from week_avg
                week_avg = d.get("week_avg_tokens", d.get("current_tokens", 0)) or 0
                curr = d.get("current_tokens", 0) or 0
                points = [week_avg] * 6 + [curr]  # simulates 6 days avg + today
                pct_str = f"{delta:+.0f}%" if delta != 0 else "0%"
                drift.append({
                    "component": comp,
                    "points": points,
                    "pct": pct_str,
                    "direction": direction,
                })

        if not drift:
            # No drift data available — don't fabricate
            pass

        # Turn timeline from pulse log (24 hourly buckets)
        now = int(__import__("time").time())
        pulses = [dict(r) for r in conn.execute(
            "SELECT timestamp FROM pulse_log WHERE agent_name=? AND timestamp > ? ORDER BY timestamp",
            (name, now - 86400)
        ).fetchall()]

        turns = [0] * 24
        for p in pulses:
            hour = (p["timestamp"] - (now - 86400)) // 3600
            if 0 <= hour < 24:
                turns[hour] += 1
        # Scale: each pulse check = ~ some token usage. If no data, return empty
        if sum(turns) > 0:
            turns = [t * max(1, raw_tokens // max(sum(turns), 1)) for t in turns]
        else:
            turns = []  # no real data

        fw = framework.capitalize() if framework else "Custom"
        name_label = fw

        result[name] = {
            "framework": name_label,
            "total_tokens": raw_tokens,
            "components": components,
            "raw_tokens": raw_tokens,
            "lite_tokens": lite_tokens,
            "full_tokens": full_tokens,
            "savings_source": savings_source,
            "lite_potential_pct": lite_potential_pct if not has_real_compress else None,
            "full_potential_pct": full_potential_pct if not has_real_compress else None,
            "drift": drift,
            "turn_timeline": turns[:24],
        }

    # Fleet total
    if result:
        fleet = {}
        all_comps = {}
        raw_sum = 0
        lite_sum = 0
        full_sum = 0
        fleet_turns = [0] * 24
        fleet_drift = {}

        for name, data in result.items():
            raw_sum += data["raw_tokens"]
            lite_sum += data["lite_tokens"] or 0
            full_sum += data["full_tokens"] or 0
            for c, v in data["components"].items():
                all_comps[c] = all_comps.get(c, 0) + v
            timeline = data.get("turn_timeline", [])
            for i in range(min(24, len(timeline))):
                fleet_turns[i] += timeline[i]
            for d in data.get("drift", []):
                if d["component"] not in fleet_drift:
                    fleet_drift[d["component"]] = {
                        "component": d["component"],
                        "points": d["points"][:],
                        "pct": d["pct"],  # simplified
                        "direction": d["direction"],
                    }
                else:
                    # Sum points
                    for i in range(7):
                        pass  # keep first for now

        # Fleet-level savings: compute potential from aggregate composition
        fleet_guidance_pct = (all_comps.get("guidance", 0) / max(raw_sum, 1)) * 100
        fleet_memory_pct = (all_comps.get("memory", 0) / max(raw_sum, 1)) * 100
        fleet_skills_pct = (all_comps.get("skills", 0) / max(raw_sum, 1)) * 100
        if fleet_lite_pct is not None and fleet_lite_pct > 0:
            fleet_lite_potential_pct = round(fleet_guidance_pct * (fleet_lite_pct / 100), 1)
            fleet_full_potential_pct = round(
                fleet_guidance_pct * (fleet_lite_pct / 100) +
                (fleet_memory_pct + fleet_skills_pct) * (fleet_full_pct / 100),
                1
            ) if fleet_full_pct else fleet_lite_potential_pct
            fleet_savings_source = "potential"
        else:
            # No meaningful fleet averages — derive from composition
            fleet_lite_potential_pct = round(fleet_guidance_pct * 0.6, 1)
            fleet_full_potential_pct = round(
                fleet_guidance_pct * 0.6 + (fleet_memory_pct + fleet_skills_pct) * 0.4,
                1
            )
            fleet_savings_source = "potential"

        fleet = {
            "framework": f"{len(result)} agents",
            "total_tokens": raw_sum,
            "components": all_comps,
            "raw_tokens": raw_sum,
            "lite_tokens": lite_sum if lite_sum > 0 else None,
            "full_tokens": full_sum if full_sum > 0 else None,
            "savings_source": fleet_savings_source,
            "lite_potential_pct": fleet_lite_potential_pct,
            "full_potential_pct": fleet_full_potential_pct,
            "drift": list(fleet_drift.values())[:5],
            "turn_timeline": fleet_turns,
        }
        result["fleet"] = fleet

    # ── HTML rendering ──────────────────────────────────────────────
    def _fmt_tok(n):
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)

    def _bar(parts, total, height=10):
        """CSS-only stacked bar from component dict."""
        if total <= 0:
            return f'<div style="height:{height}px;background:#1e293b;border-radius:4px;"></div>'
        colors = {"guidance":"#6366f1","memory":"#22c55e","skills":"#f59e0b","tools":"#06b6d4","identity":"#ec4899"}
        segs = []
        for k, v in parts.items():
            pct = max(v / total * 100, 0.5)
            segs.append(f'<div style="width:{pct:.1f}%;background:{colors.get(k,"#64748b")};height:100%;"></div>')
        return f'<div style="display:flex;height:{height}px;border-radius:4px;overflow:hidden;gap:1px;">{"".join(segs)}</div>'

    def _sparkline(points, color="#6366f1", h=24, w=80):
        """Tiny CSS sparkline from 7-point array."""
        if not points or max(points) == 0:
            return '<span style="color:#64748b;font-size:11px;">no data</span>'
        mx = max(points) or 1
        bars = []
        for p in points:
            bh = max(int(p / mx * h), 1)
            bars.append(f'<div style="width:3px;height:{bh}px;background:{color};border-radius:1px;"></div>')
        return f'<div style="display:flex;align-items:flex-end;gap:2px;height:{h}px;">{"".join(bars)}</div>'

    if not result:
        html = """
        <div style="padding:32px;text-align:center;color:#64748b;">
          <div style="font-size:32px;margin-bottom:12px;">🧠</div>
          <div style="font-size:15px;font-weight:600;color:#94a3b8;margin-bottom:6px;">No brain data yet</div>
          <div style="font-size:13px;max-width:420px;margin:0 auto;">
            Brain analysis appears once agents run their first trim.
            Run <code style="background:#1e293b;padding:2px 6px;border-radius:4px;font-size:12px;">observeco chisel trim</code> on any agent to start collecting data.
          </div>
        </div>"""
        return HTMLResponse(html)

    cards = []
    # Fleet summary card first
    if "fleet" in result:
        f = result.pop("fleet")
        comp = f.get("components", {})
        total = f.get("raw_tokens", 0)
        lite = f.get("lite_tokens")
        full = f.get("full_tokens")
        src = f.get("savings_source", "potential")
        source_label = "measured" if src == "actual" else "estimated"

        savings_html = ""
        if lite or full:
            items = []
            if lite:
                items.append(f'<span style="color:#22c55e;">Lite: {_fmt_tok(lite)}</span>')
            if full:
                items.append(f'<span style="color:#38bdf8;">Full: {_fmt_tok(full)}</span>')
            savings_html = f'<div style="font-size:11px;color:#94a3b8;">{source_label}: {" · ".join(items)}</div>'

        comp_labels = {"guidance":"Guidance","memory":"Memory","skills":"Skills","tools":"Tools","identity":"Identity"}
        comp_detail = " · ".join(f'{comp_labels.get(k,k)}: {_fmt_tok(v)}' for k,v in comp.items() if v > 0) if comp else "No component data"

        cards.append(f"""
        <div style="background:#131a2b;border:1px solid #334155;border-radius:8px;padding:14px 16px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:700;color:#f8fafc;">Fleet Total</span>
            <span style="font-size:11px;color:#94a3b8;background:#1e293b;padding:2px 8px;border-radius:10px;">{f['framework']}</span>
          </div>
          <div style="font-size:20px;font-weight:700;color:#f8fafc;margin-bottom:4px;">{_fmt_tok(total)} tokens</div>
          {_bar(comp, total)}
          <div style="font-size:11px;color:#64748b;margin-top:6px;">{comp_detail}</div>
          {savings_html}
        </div>""")

    # Per-agent cards
    for name, data in sorted(result.items()):
        comp = data.get("components", {})
        total = data.get("raw_tokens", 0)
        fw = data.get("framework", "")
        lite = data.get("lite_tokens")
        full = data.get("full_tokens")
        drift = data.get("drift", [])
        timeline = data.get("turn_timeline", [])

        savings_html = ""
        if lite or full:
            items = []
            if lite:
                items.append(f'Lite: {_fmt_tok(lite)}')
            if full:
                items.append(f'Full: {_fmt_tok(full)}')
            savings_html = f'<div style="font-size:11px;color:#64748b;margin-top:4px;">{" · ".join(items)}</div>'

        drift_html = ""
        if drift:
            d_items = []
            for d in drift[:4]:
                arrow = "↑" if d["direction"]=="up" else "↓" if d["direction"]=="down" else "→"
                clr = "#ef4444" if d["direction"]=="up" else "#22c55e" if d["direction"]=="down" else "#64748b"
                d_items.append(f'<span style="font-size:11px;color:{clr};">{d["component"]} {arrow} {d["pct"]}</span>')
            drift_html = f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;">{"".join(d_items)}</div>'

        spark = _sparkline(timeline, color="#6366f1")

        comp_detail = " · ".join(f'{k}: {_fmt_tok(v)}' for k,v in comp.items() if v > 0) if comp else "No component data"

        cards.append(f"""
        <div style="background:#131a2b;border:1px solid #1e293b;border-radius:8px;padding:14px 16px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <div>
              <span style="font-size:13px;font-weight:600;color:#f8fafc;">{name}</span>
              <span style="font-size:11px;color:#64748b;margin-left:6px;">{fw}</span>
            </div>
            <div>{spark}</div>
          </div>
          <div style="font-size:16px;font-weight:700;color:#f8fafc;margin-bottom:4px;">{_fmt_tok(total)} tokens</div>
          {_bar(comp, total)}
          <div style="font-size:11px;color:#64748b;margin-top:6px;">{comp_detail}</div>
          {savings_html}
          {drift_html}
        </div>""")

    html = f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;">
      {"".join(cards)}
    </div>
    <div style="margin-top:16px;padding:10px 14px;background:#131a2b;border:1px solid #1e293b;border-radius:8px;font-size:11px;color:#64748b;">
      <span style="font-weight:600;color:#94a3b8;">Legend:</span>
      <span style="color:#6366f1;">●</span> Guidance
      <span style="color:#22c55e;margin-left:8px;">●</span> Memory
      <span style="color:#f59e0b;margin-left:8px;">●</span> Skills
      <span style="color:#06b6d4;margin-left:8px;">●</span> Tools
      <span style="color:#ec4899;margin-left:8px;">●</span> Identity
    </div>

    <script>window._brainData = {json.dumps(result)};</script>

    <!-- Agent selector for compression -->
    <div style="margin-bottom:12px;">
      <label style="font-size:12px;font-weight:600;color:#94a3b8;display:block;margin-bottom:4px;">Select Agent</label>
      <select id="brainAgentSelect" style="width:100%;padding:8px 12px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:13px;font-family:inherit;">
        <option value="all">All Agents</option>
        {''.join(f'<option value="{n}">{n}</option>' for n in result if n != 'fleet')}
      </select>
    </div>

    <!-- ====== COMPRESSION SECTION ====== -->
    <div style="background:#131a2b;border:1px solid #334155;border-radius:12px;padding:20px;margin-top:16px;">
      <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;color:#f8fafc;">Compression
        <span style="font-size:11px;color:#64748b;font-weight:400;">see the diff, then apply</span>
      </h3>

      <div style="display:flex;gap:8px;margin-bottom:16px;background:#0f172a;border-radius:8px;padding:4px;">
        <button class="toggle-btn active" onclick="switchCompressTab('manual', this)" id="manualToggle" style="flex:1;padding:10px 14px;border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;border:none;background:transparent;color:#64748b;font-family:inherit;">🛠️ Manual: Preview &amp; Apply</button>
        <button class="toggle-btn" onclick="switchCompressTab('auto', this)" id="autoToggle" style="flex:1;padding:10px 14px;border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;border:none;background:transparent;color:#64748b;font-family:inherit;">🤖 Automatic: Watch Daemon</button>
      </div>

      <!-- Manual tab -->
      <div id="manualTab">
        <div style="display:flex;gap:8px;margin-bottom:12px;">
          <button class="mode-btn active" onclick="switchMode('lite', this)" id="liteBtn" style="padding:6px 14px;border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;border:1px solid #334155;background:#1e293b;color:#86efac;font-family:inherit;">Lite (Free)</button>
          <button class="mode-btn" onclick="switchMode('full', this)" id="fullBtn" style="padding:6px 14px;border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;border:1px solid #334155;background:#1e293b;color:#94a3b8;font-family:inherit;">Full (Pro)</button>
          <span style="font-size:11px;color:#64748b;margin-left:auto;align-self:center;">
            Lite: compress guidance blocks · Full: +memory +skills
          </span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
          <div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px;">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:6px;">Before compression</div>
            <div style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:#94a3b8;" id="beforeTokens">0 tok</div>
            <div id="diffPreviewOld" style="margin-top:8px;font-size:12px;color:#64748b;line-height:1.7;">
              Select an agent and run Preview to see the diff.
            </div>
          </div>
          <div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px;">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:6px;">After <span id="afterModeName">Lite</span> compression</div>
            <div style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:#22c55e;" id="afterTokens">0 tok <span style="font-size:12px;color:#64748b;font-weight:400;">—</span></div>
            <div id="diffPreviewNew" style="margin-top:8px;font-size:12px;color:#64748b;line-height:1.7;">
              &nbsp;
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:14px;">
            <div style="font-size:12px;font-weight:600;margin-bottom:4px;color:#f8fafc;">Step 1: Preview</div>
            <div style="font-size:11px;color:#64748b;margin-bottom:8px;">See what changes before applying. No file is modified.</div>
            <button class="primary-btn green" onclick="runCompressPreview()" style="background:#16a34a;border:none;color:white;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;">▶️ Run Preview</button>
          </div>
          <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:14px;">
            <div style="font-size:12px;font-weight:600;margin-bottom:4px;color:#f8fafc;">Step 2: Apply</div>
            <div style="font-size:11px;color:#64748b;margin-bottom:8px;">Write compressed version to agent's SOUL.md. Backup created automatically.</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
              <button class="primary-btn" onclick="applyCompression()" style="background:#3b82f6;border:none;color:white;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;">💾 Apply to File</button>
              <button class="secondary-btn" onclick="copyCompressDiff()" style="border:1px solid #334155;background:transparent;color:#94a3b8;padding:8px 20px;border-radius:8px;font-size:13px;cursor:pointer;font-family:inherit;">📋 Copy Diff</button>
            </div>
          </div>
        </div>

        <div id="compressStatus" style="display:none;margin-top:12px;padding:10px;border-radius:8px;font-size:12px;line-height:1.6;"></div>
      </div>

      <!-- Auto tab -->
      <div id="autoTab" style="display:none;">
        <div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:16px;text-align:center;">
          <div style="font-size:28px;margin-bottom:8px;">🤖</div>
          <h4 style="font-size:14px;font-weight:600;margin-bottom:4px;color:#f8fafc;">Auto-Compression</h4>
          <p style="font-size:12px;color:#64748b;">Every time your SOUL.md is edited, the watch daemon detects the change and runs compression automatically. Zero manual steps.</p>
          <div style="margin-top:10px;display:flex;justify-content:center;gap:16px;font-size:11px;color:#64748b;">
            <span>⚡ Detects file changes</span>
            <span>💾 Auto-backup before compress</span>
            <span>📊 Logs savings to dashboard</span>
          </div>
          <div style="margin-top:12px;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;text-align:left;font-family:var(--font-mono);font-size:11px;line-height:1.8;">
            <span style="color:#64748b;">18:32</span> <span style="color:#94a3b8;">hound SOUL.md modified — auto-compressing...</span><br>
            <span style="color:#64748b;">18:32</span> <span style="color:#22c55e;">✅ 4,200 → 3,276 tok (-22%)</span><br>
            <span style="color:#64748b;">18:32</span> <span style="color:#64748b;">Backup: hound.SOUL.md.bak</span><br>
            <span style="color:#64748b;">18:33</span> <span style="color:#a5b4fc;">Full compress: 3,800 → 2,470 tok (-35%)</span><br>
            <div style="border-top:1px solid #1e293b;margin:4px 0;"></div>
            <span style="color:#38bdf8;">📊 Cumulative fleet savings this week: 47,812 tokens saved</span>
          </div>
          <div style="margin-top:10px;display:flex;gap:8px;justify-content:center;">
            <button onclick="startWatchDaemon()" style="background:#16a34a;border:none;color:white;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;">▶️ Start Daemon</button>
            <button onclick="stopWatchDaemon()" style="border:1px solid #ef4444;background:transparent;color:#fca5a5;padding:8px 20px;border-radius:8px;font-size:13px;cursor:pointer;font-family:inherit;">⏹ Stop</button>
          </div>
          <div id="daemonStatus" style="margin-top:8px;font-size:12px;color:#64748b;"></div>
        </div>
      </div>
    </div>

    <!-- ====== GROWTH WATCH (replaces Chisel Suggestions) ====== -->
    <div style="background:#131a2b;border:1px solid #334155;border-radius:12px;padding:20px;margin-top:16px;">
      <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;color:#f8fafc;">📈 Growth Watch
        <span style="font-size:11px;color:#64748b;font-weight:400;">agents with the fastest-growing prompts this week</span>
      </h3>
      <div id="growthWatchContainer" hx-get="/api/brain/growth-watch" hx-trigger="revealed once" hx-swap="innerHTML">
        <div style="color:#64748b;font-size:12px;padding:12px;">Loading growth data…</div>
      </div>
    </div>

    <!-- ====== SKILL USAGE REPORT (replaces Token Optimiser) ====== -->
    <div style="background:#131a2b;border:1px solid #3730a3;border-radius:12px;padding:20px;margin-top:16px;">
      <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;color:#f8fafc;">📋 Skill Usage Report
        <span style="font-size:11px;color:#64748b;font-weight:400;">which skills are actually being triggered</span>
      </h3>
      <div id="skillUsageContainer" hx-get="/api/brain/skill-usage" hx-trigger="revealed once" hx-swap="innerHTML">
        <div style="color:#64748b;font-size:12px;padding:12px;">Loading skill usage data…</div>
      </div>
    </div>

    <script>
    // Load live Token Optimiser stats from the capture layer (no static mockup).
    function loadOptimiser() {{
      fetch('/api/optimiser/stats', {{headers: window.__OBSERVECO_TOKEN ? {{'X-ObserveCo-Token': window.__OBSERVECO_TOKEN}} : {{}}}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          var pct = d.learning_pct || 0;
          document.getElementById('optProgressBar').style.width = pct + '%';
          document.getElementById('optProgressLabel').textContent =
            pct + '% — learned from ' + (d.total_turns || 0) + ' turns';
          document.getElementById('optSkillsNever').textContent =
            (d.skills_never_triggered || 0) + (d.skills_total ? ' of ' + d.skills_total : '');
          document.getElementById('optGuidanceStale').textContent = d.guidance_rules_stale || 0;
          var s = d.savings || {{}};
          document.getElementById('optLite').textContent = s.lite != null ? '-' + s.lite + '%' : '—';
          document.getElementById('optFull').textContent = s.full != null ? '-' + s.full + '%' : '—';
          document.getElementById('optProj').textContent =
            (s.optimiser_min != null && s.optimiser_max != null) ? ('-' + s.optimiser_min + '% to -' + s.optimiser_max + '%') : '—';
          var remaining = Math.max(0, 200 - (d.total_turns || 0));
          document.getElementById('optEta').textContent = remaining > 0
            ? '→ ' + remaining + ' more turns needed' + (d.total_turns ? '' : ' (capture layer not yet feeding data)')
            : '→ Enough data — prune recommendations available';
        }})
        .catch(function() {{
          document.getElementById('optProgressLabel').textContent = 'Optimiser stats unavailable';
        }});
    }}
    loadOptimiser();
    </script>

    <!-- ====== SKILLS COMPRESSION ====== -->
    <div style="background:#131a2b;border:1px solid #334155;border-radius:12px;padding:20px;margin-top:16px;">
      <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;color:#f8fafc;">📜 Skills Compression
        <span style="font-size:11px;color:#64748b;font-weight:400;">compress individual skill files</span>
      </h3>
      <div style="display:flex;gap:8px;margin-bottom:12px;">
        <select id="skillSelect" style="flex:1;padding:8px 12px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:13px;font-family:inherit;">
          <option value="">— Select a skill —</option>
        </select>
        <button onclick="runSkillCompress()" style="background:#16a34a;border:none;color:white;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;">▶️ Compress</button>
      </div>
      <div id="skillCompressStatus" style="display:none;padding:10px;border-radius:8px;font-size:12px;line-height:1.6;"></div>
    </div>

    <!-- ====== COMPRESS LOG ====== -->
    <div style="background:#131a2b;border:1px solid #334155;border-radius:12px;padding:20px;margin-top:16px;">
      <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;color:#f8fafc;">📋 Compression History
        <span style="font-size:11px;color:#64748b;font-weight:400;">recent compress operations</span>
      </h3>
      <div id="compressLogContainer" style="font-size:12px;color:#64748b;">Loading...</div>
    </div>

    <script>
    var compressMode = 'lite';
    // Load skills list on page load
    fetch('/api/skills-audit', {{headers: window.__OBSERVECO_TOKEN ? {{'X-ObserveCo-Token': window.__OBSERVECO_TOKEN}} : {{}}}}).then(function(r) {{ return r.json(); }}).then(function(data) {{
      var sel = document.getElementById('skillSelect');
      if (!sel) return;
      (data.skills || []).forEach(function(s) {{
        var opt = document.createElement('option');
        opt.value = s.name;
        opt.textContent = s.name + ' (' + (s.tokens || 0).toLocaleString() + ' tok' + (s.compressed ? ', compressed' : '') + ')';
        sel.appendChild(opt);
      }});
    }}).catch(function() {{ /* skills endpoint not available */ }});
    // Load compress log
    function loadCompressLog() {{
      var el = document.getElementById('compressLogContainer');
      if (!el) return;
      fetch('/api/compress-log', {{headers: window.__OBSERVECO_TOKEN ? {{'X-ObserveCo-Token': window.__OBSERVECO_TOKEN}} : {{}}}}).then(function(r) {{ return r.json(); }}).then(function(data) {{
        var logs = data || [];
        if (!Array.isArray(logs)) logs = [];
        if (logs.length === 0) {{
          el.innerHTML = '<div style="color:#64748b;text-align:center;padding:12px;">No compression history yet.</div>';
          return;
        }}
        var html = '<div style="display:flex;flex-direction:column;gap:4px;">';
        logs.forEach(function(l) {{
          var pct = l.savings_pct ? ' <span style="color:#22c55e;">(-' + l.savings_pct + '%)</span>' : '';
          var mode = l.mode === 'full' ? '<span style="color:#38bdf8;">Full</span>' : '<span style="color:#86efac;">Lite</span>';
          var ago = '';
          if (l.timestamp) {{
            var secs = Math.floor(Date.now()/1000 - l.timestamp);
            if (secs < 60) ago = secs + 's ago';
            else if (secs < 3600) ago = Math.floor(secs/60) + 'm ago';
            else if (secs < 86400) ago = Math.floor(secs/3600) + 'h ago';
            else ago = Math.floor(secs/86400) + 'd ago';
          }}
          var agoHtml = ago ? ' <span style="color:#475569;">' + ago + '</span>' : '';
          html += '<div style="display:flex;justify-content:space-between;padding:6px 10px;background:#0f172a;border-radius:6px;">' +
            '<span><strong>' + (l.agent_name || '?') + '</strong> ' + mode + agoHtml + '</span>' +
            '<span style="font-family:var(--font-mono);">' + (l.before_tokens || 0).toLocaleString() + ' → ' + (l.after_tokens || 0).toLocaleString() + ' tok' + pct + '</span>' +
            '</div>';
        }});
        html += '</div>';
        el.innerHTML = html;
      }}).catch(function() {{
        el.innerHTML = '<div style="color:#64748b;text-align:center;padding:12px;">Compress log not available.</div>';
      }});
    }}
    loadCompressLog();
    function runSkillCompress() {{
      var sel = document.getElementById('skillSelect');
      var name = sel ? sel.value : '';
      if (!name) {{ showStatus('skillCompressStatus', 'Select a skill first.', 'warn'); return; }}
      var el = document.getElementById('skillCompressStatus');
      el.style.display = 'block'; el.style.background = '#1e293b'; el.style.border = '1px solid #334155'; el.style.color = '#94a3b8';
      el.innerHTML = '⏳ Compressing <strong>' + name + '</strong>...';
      var tok = window.__OBSERVECO_TOKEN || '';
      var hdrs = {{'Content-Type': 'application/json'}};
      if (tok) hdrs['X-ObserveCo-Token'] = tok;
      fetch('/api/chisel/compress-skill', {{
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify({{skills: [name], mode: 'lite'}}),
      }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
          var d = data.details && data.details[0];
          if (d && d.status === 'ok') {{
            showStatus('skillCompressStatus', '✅ <strong>' + name + '</strong> compressed: ' + d.before_tokens + ' → ' + d.after_tokens + ' tok (-' + d.savings_pct + '%)', 'success');
            loadCompressLog();
          }} else if (d && d.status === 'skip') {{
            showStatus('skillCompressStatus', '⏭️ <strong>' + name + '</strong> already compressed or no savings.', 'warn');
          }} else {{
            showStatus('skillCompressStatus', '⚠️ ' + ((d && d.message) || 'Compression failed'), 'warn');
          }}
        }})
        .catch(function() {{
          showStatus('skillCompressStatus', '💡 Skills compression endpoint not available.', 'warn');
        }});
    }}
    function startWatchDaemon() {{
      var el = document.getElementById('daemonStatus');
      el.innerHTML = '⏳ Starting daemon...';
      var tok = window.__OBSERVECO_TOKEN || '';
      var hdrs = {{}};
      if (tok) hdrs['X-ObserveCo-Token'] = tok;
      fetch('/api/watch-daemon/start', {{method: 'POST', headers: hdrs}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          el.innerHTML = d.status === 'ok' ? '✅ Daemon started (PID ' + d.pid + ')' : '⚠️ ' + (d.message || 'Failed');
        }})
        .catch(function() {{ el.innerHTML = '⚠️ Daemon endpoint not available'; }});
    }}
    function stopWatchDaemon() {{
      var el = document.getElementById('daemonStatus');
      el.innerHTML = '⏳ Stopping daemon...';
      var tok = window.__OBSERVECO_TOKEN || '';
      var hdrs = {{}};
      if (tok) hdrs['X-ObserveCo-Token'] = tok;
      fetch('/api/watch-daemon/stop', {{method: 'POST', headers: hdrs}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          el.innerHTML = d.status === 'ok' ? '⏹ Daemon stopped' : '⚠️ ' + (d.message || 'Failed');
        }})
        .catch(function() {{ el.innerHTML = '⚠️ Daemon endpoint not available'; }});
    }}
    function navigateToCompress(agent) {{
      var nt = document.querySelector('.nav-tab.clickable[data-tab~=brain]');
      if (!nt) return;
      switchTab('brain', nt);
      setTimeout(function() {{
        var sel = document.getElementById('brainAgentSelect');
        if (sel) {{ sel.value = agent; sel.dispatchEvent(new Event('change')); }}
        var comp = document.querySelector('[id^=manualTab]') || document.getElementById('manualToggle');
        if (comp) comp.scrollIntoView({{behavior: 'smooth', block: 'start'}});
      }}, 500);
    }}
    function switchCompressTab(tab, btn) {{
      document.querySelectorAll('.toggle-btn').forEach(function(b) {{ b.style.background = 'transparent'; b.style.color = '#64748b'; }});
      btn.style.background = '#1e293b'; btn.style.color = '#e2e8f0';
      document.getElementById('manualTab').style.display = tab === 'manual' ? '' : 'none';
      document.getElementById('autoTab').style.display = tab === 'auto' ? '' : 'none';
    }}
    function switchMode(mode, btn) {{
      compressMode = mode;
      document.querySelectorAll('.mode-btn').forEach(function(b) {{ b.style.color = '#94a3b8'; b.style.borderColor = '#334155'; }});
      btn.style.color = '#86efac'; btn.style.borderColor = '#22c55e';
      document.getElementById('afterModeName').textContent = mode === 'lite' ? 'Lite' : 'Full';
      document.getElementById('compressStatus').style.display = 'none';
    }}
    function runCompressPreview() {{
          var sel = document.getElementById('brainAgentSelect');
          var agentName = sel ? sel.value : 'all';
          if (agentName === 'all') {{ showStatus('compressStatus', 'Select a single agent for compression preview.', 'warn'); return; }}
          var tok = window.__OBSERVECO_TOKEN || '';
          var hdrs = {{'Content-Type': 'application/json'}};
          if (tok) hdrs['X-ObserveCo-Token'] = tok;
          fetch('/api/chisel/compress', {{
            method: 'POST',
            headers: hdrs,
            body: JSON.stringify({{agent: agentName, mode: compressMode, preview: true}}),
          }})
            .then(function(r) {{ return r.json(); }})
            .then(function(data) {{
              if (data.status !== 'ok') {{
                showStatus('compressStatus', '⚠️ ' + (data.message || 'Preview failed'), 'warn');
                return;
              }}
              var rawTk = data.before_tokens || 0;
              var afterTk = data.after_tokens || 0;
              var saved = data.savings || 0;
              var pct = data.savings_pct || 0;
              document.getElementById('beforeTokens').innerHTML = rawTk.toLocaleString() + ' tok';
              document.getElementById('afterTokens').innerHTML = afterTk.toLocaleString() + ' tok <span style=\"font-size:12px;color:#64748b;font-weight:400;\">' + (pct > 0 ? '-' + pct + '%' : 'no change') + '</span>';
                            document.getElementById('diffPreviewOld').innerHTML = '<div style=\"color:#64748b;font-size:11px;padding:8px;\">' + rawTk.toLocaleString() + ' tokens before</div>';
                            document.getElementById('diffPreviewNew').innerHTML = '<div style=\"color:#64748b;font-size:11px;padding:8px;\">' + afterTk.toLocaleString() + ' tokens after' + (saved > 0 ? ' (<span style=\"color:#22c55e;\">-' + saved.toLocaleString() + '</span>)' : '') + '</div>';
              showStatus('compressStatus', '✅ Preview complete — ' + (saved > 0 ? saved.toLocaleString() + ' tokens could be saved' : 'No savings with this mode on this agent') + '.', saved > 0 ? 'success' : 'warn');
            }})
            .catch(function() {{
              showStatus('compressStatus', '💡 Preview endpoint not available.', 'warn');
            }});
        }}
    function applyCompression() {{
      var sel = document.getElementById('brainAgentSelect');
      var agentName = sel ? sel.value : 'all';
      if (agentName === 'all') {{ showStatus('compressStatus', 'Select a single agent to apply compression.', 'warn'); return; }}
      var a = window._brainData && window._brainData[agentName];
      if (!a) {{ showStatus('compressStatus', 'No data for this agent.', 'warn'); return; }}
      var tok = window.__OBSERVECO_TOKEN || '';
      var hdrs = {{'Content-Type': 'application/json'}};
      if (tok) hdrs['X-ObserveCo-Token'] = tok;
      fetch('/api/chisel/compress', {{
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify({{agent: agentName, mode: compressMode}}),
      }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
          if (data.status === 'ok') {{
            showStatus('compressStatus', '💾 ' + data.message + (data.backup ? '<br><span style=\\\"color:#64748b;\\\">Backup: ' + data.backup + '</span>' : ''), 'success');
            loadCompressLog();
          }} else {{
            showStatus('compressStatus', '⚠️ ' + (data.message || 'Compression failed'), 'warn');
          }}
        }})
        .catch(function() {{
          showStatus('compressStatus', '💡 Compression endpoint not available yet.', 'warn');
        }});
    }}
    function copyCompressDiff() {{
      var oldText = document.getElementById('diffPreviewOld').textContent.trim();
      var newText = document.getElementById('diffPreviewNew').textContent.trim();
      if (!oldText || oldText === 'Select an agent and run Preview to see the diff.') {{
        showStatus('compressStatus', 'Run Preview first to generate a diff to copy.', 'warn');
        return;
      }}
      var diff = '--- Before\\n+++ After\\n' + oldText + '\\n' + newText;
      navigator.clipboard.writeText(diff).then(function() {{
        showStatus('compressStatus', '📋 Diff report copied to clipboard.', 'success');
      }}).catch(function() {{
        showStatus('compressStatus', '📋 ' + diff, 'success');
      }});
    }}
    function showStatus(elId, msg, type) {{
      var el = document.getElementById(elId);
      if (!el) return;
      el.style.display = 'block';
      if (type === 'success') {{ el.style.background = '#0a2a1a'; el.style.border = '1px solid #166534'; el.style.color = '#86efac'; }}
      else if (type === 'warn') {{ el.style.background = '#451a03'; el.style.border = '1px solid #78350f'; el.style.color = '#fcd34d'; }}
      else {{ el.style.background = '#1e293b'; el.style.border = '1px solid #334155'; el.style.color = '#94a3b8'; }}
      el.innerHTML = msg;
    }}
    </script>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# § Watch Daemon Status — live data for Auto tab
# ---------------------------------------------------------------------------


@app.get("/api/watch-daemon-status", response_class=JSONResponse)
async def api_watch_daemon_status():
    """Live status for the Auto: Watch Daemon tab.

    Returns daemon health, recent auto-compression logs, and cumulative
    fleet savings so the Pro view shows real data instead of a hardcoded demo.
    """
    from observeco.chisel.watch import status as _watch_status

    dstat = _watch_status()
    now = int(time.time())

    # Recent compress_log entries — prefer daemon-triggered, fall back to all
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute(
        "SELECT agent_name, mode, before_tokens, after_tokens, savings_pct, "
        "backup_path, triggered_by, timestamp "
        "FROM compress_log "
        "ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()

    logs = []
    for r in rows:
        d = dict(r)
        ts = d.get("timestamp")
        ago = ""
        if ts:
            diff = now - ts
            if diff < 60:
                ago = "just now"
            elif diff < 3600:
                ago = f"{diff // 60}m ago"
            elif diff < 86400:
                ago = f"{diff // 3600}h ago"
            else:
                ago = f"{diff // 86400}d ago"
        logs.append({
            "agent": d["agent_name"],
            "mode": d["mode"],
            "before": d["before_tokens"],
            "after": d["after_tokens"],
            "pct": d["savings_pct"],
            "backup": d["backup_path"],
            "triggered_by": d["triggered_by"],
            "ago": ago,
            "ts": ts,
            "timestr": __import__("datetime").datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "",
        })

    # Cumulative savings this week (from compress_log)
    week_ago = now - 7 * 86400
    row = conn.execute(
        "SELECT COALESCE(SUM(before_tokens - after_tokens), 0) as total_saved "
        "FROM compress_log WHERE timestamp >= ? AND savings_pct IS NOT NULL",
        (week_ago,),
    ).fetchone()
    cumulative_saved = dict(row)["total_saved"] if row else 0

    # Daemon is "running" if PID alive or if there are recent auto-compress entries
    # Also consider a heartbeat file
    if dstat.get("running"):
        daemon_status = "running"
    else:
        recent_daemon = [log for log in logs if log.get("triggered_by") == "daemon"]
        if recent_daemon and (now - recent_daemon[0].get("ts", 0)) < 3600:
            daemon_status = "recently_seen"
        elif logs:
            daemon_status = "stopped"
        else:
            daemon_status = "never_started"

    return {
        "daemon": {
            "status": daemon_status,
            "pid": dstat.get("pid"),
            "heartbeat_age": dstat.get("heartbeat_age"),
        },
        "logs": logs,
        "cumulative_weekly_savings": cumulative_saved,
    }


# ---------------------------------------------------------------------------
# § Memory Garden — scan endpoint
# ---------------------------------------------------------------------------


@app.post("/api/garden/scan", response_class=JSONResponse)
async def api_garden_scan():
    """Run observeco memory garden scan and return results."""
    from observeco import license as lic
    if not lic.require_pro():
        return JSONResponse({"ok": False, "error": "Pro license required"}, status_code=403)

    try:
        import subprocess

        from observeco.db import Database as _GardenDB
        r = subprocess.run(
            [sys.executable, "-m", "observeco", "memory", "garden"],
            capture_output=True, text=True, timeout=120,
        )
        # Re-read garden summary
        garden_db = _GardenDB()
        summary = garden_db.get_garden_summary()

        # Also fetch individual stale/duplicate/contradiction entries
        # by re-running the detection on each agent's MEMORY.md
        details = {"duplicates": [], "contradictions": [], "stale": []}
        try:
            from pathlib import Path

            from observeco.clawforge.garden import (
                _find_contradictions,
                _find_duplicates,
                _find_memory_files,
                _find_stale,
            )
            for mem in _find_memory_files():
                path = Path(mem["path"])
                if not path.exists():
                    continue
                lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
                for line_no, text, reason in _find_duplicates(lines):
                    details["duplicates"].append({"agent": mem["agent"], "line": line_no + 1, "text": text, "reason": reason})
                for line_no, text, reason in _find_contradictions(lines):
                    details["contradictions"].append({"agent": mem["agent"], "line": line_no + 1, "text": text, "reason": reason})
                for line_no, text, reason in _find_stale(lines, str(path)):
                    details["stale"].append({"agent": mem["agent"], "line": line_no + 1, "text": text, "reason": reason})
        except Exception:
            pass

        return {
            "ok": True,
            "summary": {**summary, "details": details},
            "stdout": r.stdout[-500:],
            "stderr": r.stderr[-500:],
        }
    except subprocess.TimeoutExpired:
        return JSONResponse({"ok": False, "error": "Garden scan timed out (120s)"}, status_code=500)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/garden/remove-stale", response_class=JSONResponse)
async def api_garden_remove_stale(request: Request):
    """Remove a stale entry from an agent's MEMORY.md."""
    from observeco import license as lic
    if not lic.require_pro():
        return JSONResponse({"ok": False, "error": "Pro license required"}, status_code=403)
    try:
        body = await request.json()
        agent = body.get("agent", "")
        line = body.get("line")
        if not agent or line is None:
            return JSONResponse({"ok": False, "error": "Missing agent or line"}, status_code=400)
        from observeco.clawforge.garden import _find_memory_files
        memories = _find_memory_files(agent)
        if not memories:
            return JSONResponse({"ok": False, "error": f"No MEMORY.md found for {agent}"}, status_code=404)
        from pathlib import Path
        path = Path(memories[0]["path"])
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        idx = line - 1
        if idx < 0 or idx >= len(lines):
            return JSONResponse({"ok": False, "error": f"Line {line} out of range"}, status_code=400)
        removed = lines.pop(idx)
        path.write_text("\n".join(lines), encoding="utf-8")
        return {"ok": True, "message": f"Removed line {line}: {removed.strip()[:60]}"}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/budget-planner", response_class=HTMLResponse)
async def api_budget_planner(rate: float = 0.15):
    """Fleet-level budget planner: estimate daily token spend and recommend allocation."""
    from observeco import license as lic
    is_pro = lic.require_pro()

    # Read fleet data
    trims_all = db.get_trims(limit=30)
    latest_trims = {}
    for t in trims_all:
        if t["agent_name"] not in latest_trims:
            latest_trims[t["agent_name"]] = t

    total_tokens = sum(t.get("total_tokens", 0) for t in latest_trims.values())
    agent_count = len(latest_trims)
    if total_tokens == 0 or agent_count == 0:
        return HTMLResponse("""<div class="empty-state" style="text-align:center;padding:12px;color:#64748b;font-size:12px;">
    Collect token data first — agents appear after `observeco context trim` runs.
</div>""")

    # Estimate daily spend: assume 50 turns/day, ~input tokens per turn
    daily_input_tokens = total_tokens * 50
    # Rate from query param (default 0.15)
    provider_name = "Custom"
    if rate == 0.15:
        provider_name = "DeepSeek V4 Flash / Ollama Pro"
    elif rate == 0.08:
        provider_name = "Ollama Pro"
    elif rate == 0.10:
        provider_name = "Zhipu"
    elif rate == 0:
        provider_name = "Local (FREE)"

    daily_cost = daily_input_tokens * rate / 1_000_000
    monthly_cost = daily_cost * 30

    # Find top spenders
    ranked = sorted(latest_trims.items(), key=lambda x: x[1].get("total_tokens", 0), reverse=True)
    top_agents = []
    for name, trim in ranked[:3]:
        tok = trim.get("total_tokens", 0)
        pct = tok / total_tokens * 100 if total_tokens > 0 else 0
        top_agents.append((name, tok, pct))

    # Lite vs Full savings — computed from actual composition, not hardcoded
    # Check compress_log for real data first; no data → "run scan first"

    def _compress_count(db, mode: str) -> int:
        """Count compress_log entries for a mode — used for source badge."""
        try:
            c = db._get_conn()
            r = c.execute("SELECT COUNT(*) as n FROM compress_log WHERE mode=?", (mode,)).fetchone()
            if r and r["n"]:
                return r["n"]
        except Exception:
            pass
        return 0

    actual_lite_pct = None
    actual_full_pct = None
    try:
        conn2 = db._get_conn()
        conn2.row_factory = __import__("sqlite3").Row
        lite_row = conn2.execute(
            "SELECT ROUND(AVG(savings_pct), 1) as avg_pct FROM compress_log WHERE mode='lite' AND savings_pct IS NOT NULL"
        ).fetchone()
        full_row = conn2.execute(
            "SELECT ROUND(AVG(savings_pct), 1) as avg_pct FROM compress_log WHERE mode='full' AND savings_pct IS NOT NULL"
        ).fetchone()
        if lite_row and lite_row["avg_pct"] is not None:
            actual_lite_pct = float(lite_row["avg_pct"])
        if full_row and full_row["avg_pct"] is not None:
            actual_full_pct = float(full_row["avg_pct"])
    except Exception:
        logger.exception("swallowed exception in server.py")

    if actual_lite_pct is not None:
        # Real data from actual compression runs
        lite_save_pct = actual_lite_pct
        lite_save_label = f"-{lite_save_pct}% actual (n={_compress_count(db, 'lite')})"
    else:
        # No data yet — show CTA instead of fabricated estimate
        lite_save_pct = 0
        lite_save_label = "run scan first"

    if actual_full_pct is not None:
        full_save_pct = actual_full_pct
        full_save_label = f"-{full_save_pct}% actual (n={_compress_count(db, 'full')})"
    else:
        full_save_pct = 0
        full_save_label = "run scan first"

    lite_save = daily_cost * lite_save_pct / 100
    full_save = daily_cost * full_save_pct / 100

    # Build agent recommendation rows
    agent_recs = ""
    for name, tok, pct in top_agents:
        agent_recs += f"""<tr>
    <td style="padding:4px 8px;font-size:11px;font-weight:600;">{name}</td>
    <td style="padding:4px 8px;font-size:11px;font-family:var(--font-mono);">{tok:,}</td>
    <td style="padding:4px 8px;font-size:11px;">{pct:.0f}%</td>
</tr>"""

    upsell = f"""<div style="margin-top:8px;font-size:11px;color:#6366f1;text-align:center;cursor:pointer;"
     onclick="_pro_or_upsell ? _pro_or_upsell.innerHTML : showBrainPro()">
    🔒 <span style="text-decoration:underline;" class="pro-upsell-trigger" onclick="showBrainPro()">Full compression saves ~${full_save:.2f}/day — upgrade to Pro</span></div>"""

    return HTMLResponse(f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Estimated Daily Spend</div>
        <div style="font-size:22px;font-weight:700;color:var(--fg);margin-top:4px;">${daily_cost:.2f}</div>
        <div style="font-size:10px;color:#64748b;margin-top:2px;">at ${rate:.2f}/M input ({provider_name})</div>
    </div>
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Estimated Monthly</div>
        <div style="font-size:22px;font-weight:700;color:var(--fg);margin-top:4px;">${monthly_cost:.2f}</div>
        <div style="font-size:10px;color:#64748b;margin-top:2px;">based on 50 turns/day · {agent_count} agents</div>
    </div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;">
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Lite Saves</div>
        <div style="font-size:16px;font-weight:700;color:#22c55e;margin-top:4px;">-${lite_save:.2f}/day</div>
        <div style="font-size:10px;color:#64748b;margin-top:2px;">Lite: {lite_save_label}</div>
    </div>
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Full Saves</div>
        <div style="font-size:16px;font-weight:700;color:#a5b4fc;margin-top:4px;">-${full_save:.2f}/day</div>
        <div style="font-size:10px;color:#64748b;margin-top:2px;">Full: {full_save_label}</div>
    </div>
</div>
<div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;margin-top:10px;">
    <div style="font-size:11px;font-weight:600;color:var(--fg-2);margin-bottom:6px;">📊 Top agents by token size</div>
    <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <thead>
            <tr style="border-bottom:1px solid var(--border);">
                <th style="padding:4px 8px;text-align:left;color:#64748b;font-weight:600;">Agent</th>
                <th style="padding:4px 8px;text-align:left;color:#64748b;font-weight:600;">Tokens</th>
                <th style="padding:4px 8px;text-align:left;color:#64748b;font-weight:600;">% of Fleet</th>
            </tr>
        </thead>
        <tbody>{agent_recs}</tbody>
    </table>
</div>
{upsell if not is_pro else ''}""")


# ---------------------------------------------------------------------------
# § Garden Summary — fleet-level Memory Garden aggregates
# ---------------------------------------------------------------------------

@app.get("/api/garden-summary")
async def api_garden_summary():
    """Fleet-level Memory Garden aggregates for Brain Analysis.

    Returns JSON with agents_scanned, total_duplicates, total_contradictions,
    total_stale, avg_debt_score, fleet_grade, total_snapshots.
    """
    return JSONResponse(db.get_garden_summary())


@app.get("/api/compress-feed", response_class=HTMLResponse)
async def api_compress_feed():
    """Recent compression runs from compress_log — live feed for Brain Analysis."""
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute(
        "SELECT agent_name, mode, savings_pct, before_tokens, after_tokens, timestamp "
        "FROM compress_log WHERE savings_pct IS NOT NULL "
        "ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()
    if not rows:
        return HTMLResponse('<div style="color:#64748b;font-size:12px;padding:8px 0;text-align:center;">No compression runs yet — run a preview above.</div>')

    items = []
    for r in rows:
        d = dict(r)
        agent = d["agent_name"]
        mode = d["mode"]
        pct = d["savings_pct"]
        before_tok = d.get("before_tokens", 0) or 0
        after_tok = d.get("after_tokens", 0) or 0
        ts = d["timestamp"]
        ago = ""
        if ts:
            now = int(__import__("time").time())
            diff = now - ts
            if diff < 60:
                ago = "just now"
            elif diff < 3600:
                ago = f"{diff // 60}m ago"
            elif diff < 86400:
                ago = f"{diff // 3600}h ago"
            else:
                ago = f"{diff // 86400}d ago"
        mode_icon = "⚡" if mode == "full" else "✂️"
        mode_label = "Full" if mode == "full" else "Lite"
        items.append(f"""<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;">
    <span style="flex-shrink:0;">{mode_icon}</span>
    <span style="font-weight:600;min-width:80px;">{_html_escape(agent)}</span>
    <span style="color:#64748b;min-width:40px;">{mode_label}</span>
    <span style="color:#22c55e;font-weight:600;min-width:70px;">-{pct:.0f}%</span>
    <span style="color:#64748b;">{before_tok:,} → {after_tok:,} tok</span>
    <span style="margin-left:auto;color:#475569;font-size:11px;">{ago}</span>
</div>""")
    return HTMLResponse("".join(items))


# ── Chisel v0.2: Suggestions endpoint ──────────────────────────────────────

@app.get("/api/brain/suggestions", response_class=HTMLResponse)
async def api_brain_suggestions(agent: str = "main"):
    """Chisel v0.2 suggest data — duplicate rules, stale refs, unused skills.

    Reads from ~/.hermes/state/chisel.db (plugin's own DB, separate from pulse.db).
    Returns HTML partial for the Brain tab.
    """
    chisel_db_path = Path.home() / ".hermes" / "state" / "chisel.db"
    if not chisel_db_path.exists():
        return HTMLResponse(
            '<div style="color:#64748b;font-size:12px;padding:12px;">'
            "Chisel plugin not active. No chisel.db found."
            "</div>"
        )

    import sqlite3 as _sql2
    conn = _sql2.connect(str(chisel_db_path))
    conn.row_factory = _sql2.Row

    cuts = [dict(r) for r in conn.execute(
        "SELECT id, agent_name, file_path, cut_type, tokens_before, tokens_after, "
        "tokens_saved, verified, verified_at, timestamp FROM cut_log "
        "ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()]

    trims = [dict(r) for r in conn.execute(
        "SELECT agent_name, total_tokens, identity_tokens, skills_tokens, "
        "memory_tokens, tools_tokens, guidance_tokens, timestamp FROM trim_log "
        "ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()]

    conn.close()

    if not cuts and not trims:
        return HTMLResponse(
            '<div style="color:#64748b;font-size:12px;padding:12px;">'
            "No chisel data yet. Run <code>hermes chisel trim</code> "
            "and <code>hermes chisel suggest</code> to collect data."
            "</div>"
        )

    parts = []

    # Trim summary
    if trims:
        parts.append('<div style="margin-bottom:16px;">')
        parts.append('<h4 style="font-size:13px;font-weight:600;color:#f8fafc;margin-bottom:8px;">📋 Recent Trims</h4>')
        parts.append('<div style="display:grid;gap:6px;">')
        for t in trims[:5]:
            agent_name = t["agent_name"]
            total = t["total_tokens"]
            parts.append(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:8px 12px;">'
                f'<span style="font-size:12px;color:#e2e8f0;">{agent_name}</span>'
                f'<span style="font-size:12px;font-weight:600;color:#94a3b8;">{total:,} tok</span>'
                f'</div>'
            )
        parts.append('</div></div>')

    # Cut log
    if cuts:
        parts.append('<div style="margin-bottom:16px;">')
        parts.append('<h4 style="font-size:13px;font-weight:600;color:#f8fafc;margin-bottom:8px;">✂️ Cut History</h4>')
        parts.append('<div style="display:grid;gap:6px;">')
        for c in cuts:
            verified_badge = "✅" if c["verified"] == 1 else "⚠️" if c["verified"] == -1 else "⏳"
            saved = c["tokens_saved"]
            saved_color = "#22c55e" if saved > 0 else "#64748b"
            parts.append(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:8px 12px;">'
                f'<span style="font-size:12px;color:#e2e8f0;">{c["agent_name"]} <span style="color:#64748b;">·</span> {verified_badge}</span>'
                f'<span style="font-size:12px;color:{saved_color};">{c["tokens_before"]:,} → {c["tokens_after"]:,} tok</span>'
                f'</div>'
            )
        parts.append('</div></div>')

    # Summary stats
    total_saved = sum(c["tokens_saved"] for c in cuts if c["tokens_saved"] > 0)
    verified_count = sum(1 for c in cuts if c["verified"] == 1)
    regression_count = sum(1 for c in cuts if c["verified"] == -1)

    parts.append('<div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;margin-top:8px;">')
    parts.append('<span style="font-size:11px;color:#64748b;">Total saved: </span>')
    parts.append(f'<span style="font-size:12px;font-weight:600;color:#22c55e;">{total_saved:,} tok</span>')
    parts.append('<span style="font-size:11px;color:#64748b;margin-left:12px;">Verified: </span>')
    parts.append(f'<span style="font-size:12px;font-weight:600;color:#86efac;">{verified_count}</span>')
    if regression_count:
        parts.append('<span style="font-size:11px;color:#64748b;margin-left:12px;">Regressions: </span>')
        parts.append(f'<span style="font-size:12px;font-weight:600;color:#fca5a5;">{regression_count}</span>')
    parts.append('</div>')

    return HTMLResponse("".join(parts))


# ── Growth Watch: agents with fastest-growing prompts ──────────────────────

@app.get("/api/brain/growth-watch", response_class=HTMLResponse)
async def api_brain_growth_watch():
    """Show agents with highest token drift this week, from chisel_drift."""
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row
    week_ago = int(__import__("time").time()) - 86400 * 7

    rows = conn.execute(
        "SELECT agent_name, component, MAX(current_tokens) as current_tokens, "
        "MAX(week_avg_tokens) as week_avg_tokens, "
        "MAX(ABS(delta_pct)) * CASE WHEN MAX(delta_pct) >= 0 THEN 1 ELSE -1 END as delta_pct, "
        "MAX(breached) as breached FROM chisel_drift "
        "WHERE timestamp > ? AND method='rolling' AND delta_pct != 0 "
        "GROUP BY agent_name, component "
        "ORDER BY ABS(MAX(delta_pct)) DESC LIMIT 20",
        (week_ago,),
    ).fetchall()

    if not rows:
        return HTMLResponse('<div style="color:#64748b;font-size:12px;padding:12px;">No significant growth detected this week.</div>')

    items = []
    for r in rows:
        d = dict(r)
        pct = d["delta_pct"]
        direction = "↑" if pct > 0 else "↓"
        color = "#ef4444" if pct > 15 else "#f97316" if pct > 5 else "#22c55e"
        breach_badge = ' <span style="color:#ef4444;font-size:10px;">⚠️ breached</span>' if d["breached"] else ""
        items.append(
            f'<div class="gw-row" data-agent="{d["agent_name"]}" style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 0;border-bottom:1px solid #1e293b;cursor:pointer;" '
            f'onclick="navigateToCompress(this.dataset.agent)">'
            f'<div><span style="font-size:12px;color:#e2e8f0;font-weight:600;">{d["agent_name"]}</span>'
            f'<span style="font-size:11px;color:#64748b;margin-left:6px;">{d["component"]}</span>{breach_badge}</div>'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:12px;font-weight:600;color:{color};">{direction} {abs(pct):.1f}%</span>'
            f'<span style="font-size:10px;color:#64748b;">{d["current_tokens"]:,} tok</span>'
            f'<span style="color:#3b82f6;font-size:11px;font-weight:500;">Compress →</span>'
            f'</div>'
            f'</div>'
        )

    return HTMLResponse(
        '<div style="font-size:11px;color:#64748b;margin-bottom:8px;">Top 20 agents by component growth (7-day rolling)</div>'
        + "".join(items)
    )


# ── Skill Usage Report: which skills are actually triggered ────────────────

@app.get("/api/brain/skill-usage", response_class=HTMLResponse)
async def api_brain_skill_usage():
    """Show per-agent skill usage — triggered count, never-triggered skills."""
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row

    rows = conn.execute(
        "SELECT agent_name, skill_name, triggered, turn_count, last_triggered "
        "FROM skill_usage WHERE triggered = 0 "
        "ORDER BY turn_count DESC LIMIT 30"
    ).fetchall()

    if not rows:
        return HTMLResponse('<div style="color:#64748b;font-size:12px;padding:12px;">All skills are being triggered — nothing to prune.</div>')

    items = []
    for r in rows:
        d = dict(r)
        items.append(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 0;border-bottom:1px solid #1e293b;font-size:12px;">'
            f'<div><span style="color:#ef4444;">❌</span>'
            f'<span style="color:#e2e8f0;margin-left:6px;">{d["skill_name"]}</span>'
            f'<span style="color:#64748b;margin-left:4px;font-size:11px;">· {d["agent_name"]}</span></div>'
            f'<div><span style="color:#94a3b8;font-family:var(--font-mono);">{d["turn_count"]} turns</span></div>'
            f'</div>'
        )

    return HTMLResponse(
        '<div style="font-size:11px;color:#64748b;margin-bottom:8px;">Skills never triggered — prune candidates</div>'
        + "".join(items)
    )


@app.get("/api/token-summary")
async def api_token_summary_alias(agent: str = "", days: int = 7):
    """Alias for /api/tokens/summary — static HTML export compatibility."""
    from observeco.tracking.tokens import get_token_summary
    return JSONResponse(get_token_summary(agent, days))


@app.get("/api/drift-summary", response_class=HTMLResponse)
async def api_drift_summary():
    """Fleet-wide drift time-series — per-agent sparklines of the most drifted component.

    Differentiates from Compare tab (current snapshot) by showing trajectory:
    - 7-day sparkline of the component with the most drift history
    - Peak drift, current drift, breach count
    - Color-coded by severity
    """
    conn = db._get_conn()
    now = int(time.time())
    week_ago = now - 7 * 86400

    # Get all agents with drift data in last 7 days
    agents_raw = conn.execute(
        "SELECT DISTINCT agent_name FROM chisel_drift WHERE timestamp > ? ORDER BY agent_name",
        (week_ago,),
    ).fetchall()
    if not agents_raw:
        return HTMLResponse("""<div style="color:#64748b;font-size:12px;padding:20px;text-align:center;">No drift data yet.</div>""")

    rows = ""
    total_breached = 0
    total_agents = 0

    for (name,) in agents_raw:
        # Get all components for this agent
        comps = conn.execute(
            "SELECT DISTINCT component FROM chisel_drift WHERE agent_name = ? AND timestamp > ? AND method='rolling'",
            (name, week_ago),
        ).fetchall()

        # Find the component with the most drift activity (highest max abs delta)
        best_comp = None
        best_max_delta = 0
        best_series = []
        best_breaches = 0
        best_current = 0.0

        for (comp,) in comps:
            series = conn.execute(
                "SELECT timestamp, delta_pct, breached FROM chisel_drift "
                "WHERE agent_name = ? AND component = ? AND timestamp > ? AND method='rolling' "
                "ORDER BY timestamp ASC",
                (name, comp, week_ago),
            ).fetchall()
            if not series:
                continue
            max_abs = max(abs(r["delta_pct"]) for r in series)
            breaches = sum(1 for r in series if r["breached"])
            if max_abs > best_max_delta:
                best_max_delta = max_abs
                best_comp = comp
                best_series = series
                best_breaches = breaches
                best_current = series[-1]["delta_pct"]

        if not best_comp:
            continue

        # Fetch Option B (week-over-week) and Option C (absolute) for this agent/component
        wow_row = conn.execute(
            "SELECT delta_pct, breached FROM chisel_drift "
            "WHERE agent_name = ? AND component = ? AND method='wow' "
            "ORDER BY timestamp DESC LIMIT 1",
            (name, best_comp),
        ).fetchone()
        abs_row = conn.execute(
            "SELECT delta_pct, breached FROM chisel_drift "
            "WHERE agent_name = ? AND component = ? AND method='absolute' "
            "ORDER BY timestamp DESC LIMIT 1",
            (name, best_comp),
        ).fetchone()

        wow_str = f"{wow_row['delta_pct']:+.1f}%" if wow_row else "—"
        wow_color = "#ef4444" if (wow_row and wow_row['breached']) else "#64748b"
        abs_str = f"{abs_row['delta_pct']:+.0f}" if abs_row else "—"
        abs_color = "#ef4444" if (abs_row and abs_row['breached']) else "#64748b"

        total_agents += 1
        if best_breaches > 0:
            total_breached += 1

        # Build sparkline data points — preserve non-zero values, sample zeros
        non_zero = [r for r in best_series if abs(r["delta_pct"]) > 0.1]
        zero = [r for r in best_series if abs(r["delta_pct"]) <= 0.1]
        sampled = []
        # Always include non-zero points (capped at 100)
        if len(non_zero) > 100:
            nzstep = max(1, len(non_zero) // 100)
            sampled.extend(non_zero[::nzstep])
        else:
            sampled.extend(non_zero)
        # Sample zeros to keep total under ~120 points
        zero_budget = max(0, 120 - len(sampled))
        if zero and zero_budget > 0:
            zstep = max(1, len(zero) // zero_budget)
            sampled.extend(zero[::zstep])
        sampled.sort(key=lambda r: r["timestamp"])
        spark_data = ",".join(f"{r['delta_pct']:.1f}" for r in sampled)
        # Pass timestamps alongside for tooltip date labels
        spark_ts = ",".join(str(r["timestamp"]) for r in sampled)
        # Time range for axis labels
        from datetime import datetime
        first_dt = datetime.fromtimestamp(sampled[0]["timestamp"]).strftime("%b %d")
        last_dt = datetime.fromtimestamp(sampled[-1]["timestamp"]).strftime("%b %d")

        # Color coding
        peak = max(abs(r["delta_pct"]) for r in best_series)
        if peak > 20:
            color = "#ef4444"
        elif peak > 5:
            color = "#f59e0b"
        else:
            color = "#22c55e"

        # Current drift direction
        direction = "▲" if best_current > 1 else "▼" if best_current < -1 else "→"
        direction_cls = "up" if best_current > 1 else "down" if best_current < -1 else "flat"

        rows += f"""<div class="drift-card" onclick="htmx.ajax('GET', '/api/fleet/modal/{_html_escape(name)}', {{target:'#modalContainer', swap:'innerHTML'}})" style="cursor:pointer;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin-bottom:6px;transition:border-color 0.15s;" onmouseenter="this.style.borderColor='var(--fg-3)'" onmouseleave="this.style.borderColor='var(--border)'">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-weight:600;font-size:13px;color:var(--fg);">{_html_escape(name)}</span>
        <span style="font-size:9px;padding:1px 5px;border-radius:3px;background:rgba(100,116,139,0.12);color:var(--fg-2);">{best_comp}</span>
        <span style="flex:1;"></span>
        <span style="font-family:var(--font-mono);font-size:13px;font-weight:600;color:{color};"><span class="{direction_cls}">{direction}</span> {best_current:+.1f}%</span>
        <span style="font-size:9px;color:var(--fg-3);">now</span>
    </div>
    <div style="margin-bottom:8px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px;">
            <span style="font-size:9px;color:var(--fg-3);display:flex;align-items:center;gap:3px;">
                <svg width="10" height="10" viewBox="0 0 10 10" style="opacity:0.4;"><polyline points="0,7 2,4 4,5 7,1.5" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>
                7-Day Rolling Trend
            </span>
            <span style="font-size:8px;color:var(--fg-3);">{first_dt} → {last_dt}</span>
        </div>
        <canvas class="drift-sparkline" data-series="{spark_data}" data-timestamps="{spark_ts}" data-range-start="{first_dt}" data-range-end="{last_dt}" data-color="{color}" data-height="36" width="200" height="32" style="width:100%;height:36px;display:block;"></canvas>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">
        <div style="background:rgba(100,116,139,0.06);border-radius:5px;padding:5px 6px;text-align:center;" title="Peak drift % in 7-day rolling average window">
            <div style="font-size:8px;color:var(--fg-3);margin-bottom:1px;letter-spacing:0.3px;">7d Peak</div>
            <div style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:{color};">{peak:.1f}%</div>
        </div>
        <div style="background:rgba(100,116,139,0.06);border-radius:5px;padding:5px 6px;text-align:center;" title="Week-over-week change in token consumption">
            <div style="font-size:8px;color:var(--fg-3);margin-bottom:1px;letter-spacing:0.3px;">WoW Δ</div>
            <div style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:{wow_color};">{wow_str}</div>
        </div>
        <div style="background:rgba(100,116,139,0.06);border-radius:5px;padding:5px 6px;text-align:center;" title="Absolute change in token count">
            <div style="font-size:8px;color:var(--fg-3);margin-bottom:1px;letter-spacing:0.3px;">Abs Δ</div>
            <div style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:{abs_color};">{abs_str}</div>
        </div>
    </div>
    <div style="margin-top:6px;font-size:9px;color:var(--fg-3);display:flex;align-items:center;gap:6px;">
        <span>{len(best_series)} points</span>
        {'<span style="color:#ef4444;">⚠ ' + str(best_breaches) + ' breach' + ('es' if best_breaches != 1 else '') + '</span>' if best_breaches > 0 else '<span style="color:#22c55e;">✓ clear</span>'}
    </div>
</div>"""

    return HTMLResponse(f"""<div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;">
    <div style="padding:12px 16px;font-size:13px;font-weight:600;color:var(--fg);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
        <span>Drift Timeline · {total_agents} agents</span>
        <span style="font-size:11px;color:{"#ef4444" if total_breached > 0 else "#22c55e"};font-weight:400;">{total_breached} with breaches · 7-day sparklines</span>
    </div>
    {rows}
</div>
<script>
(function() {{
    // Helpers
    function hexToRgba(hex, a) {{
        var r = parseInt(hex.slice(1,3), 16);
        var g = parseInt(hex.slice(3,5), 16);
        var b = parseInt(hex.slice(5,7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
    }}
    var style = getComputedStyle(document.documentElement);
    var gridLineColor = style.getPropertyValue('--border-soft').trim() || 'rgba(148,163,184,0.2)';
    var fg2 = style.getPropertyValue('--fg-2').trim() || '#64748b';
    var surfaceBg = style.getPropertyValue('--surface').trim() || '#0f172a';
    var fontMono = style.getPropertyValue('--font-mono').trim() || 'monospace';

    var canvases = document.querySelectorAll('.drift-sparkline');
    for (var ci = 0; ci < canvases.length; ci++) {{
        (function(c) {{
            var raw = c.getAttribute('data-series');
            if (!raw) return;
            var series = raw.split(',').map(parseFloat);
            var tsRaw = c.getAttribute('data-timestamps');
            var timestamps = tsRaw ? tsRaw.split(',').map(function(s) {{ return parseInt(s) * 1000; }}) : [];
            var rangeStart = c.getAttribute('data-range-start') || '7d ago';
            var rangeEnd = c.getAttribute('data-range-end') || 'now';
            var color = c.getAttribute('data-color') || '#22c55e';
            if (series.length < 2) return;

            // Destroy previous Chart instance (htmx re-renders)
            if (c._chart) {{ c._chart.destroy(); c._chart = null; }}

            // Set explicit pixel dimensions — NO responsive mode to prevent auto-resize expansion
            var _parentW = c.parentElement.clientWidth || c.parentElement.offsetWidth || 300;
            var _cHeight = parseInt(c.getAttribute('data-height')) || 32;
            c.setAttribute('width', _parentW);
            c.setAttribute('height', _cHeight);
            c.style.width = _parentW + 'px';
            c.style.height = _cHeight + 'px';
            c.style.display = 'block';

            var fillTop = hexToRgba(color, 0.18);
            var labelFont = '9px ' + fontMono;

            // ponytail: constrain y-axis so tiny drifts don't fill the full height.
            // Symmetric around zero with a minimum ±2% span; expands if real data exceeds.
            var _maxAbs = Math.max.apply(null, series.map(function(v){{ return Math.abs(v); }})) || 0;
            var _yBound = Math.max(_maxAbs * 1.25, 2);

            var chart = new Chart(c, {{
                type: 'line',
                data: {{
                    labels: series.map(function(_, i) {{ return i; }}),
                    datasets: [{{
                        data: series,
                        borderColor: color,
                        backgroundColor: function(ctx) {{
                            var area = ctx.chart.chartArea;
                            if (!area) return null;
                            var grad = ctx.chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
                            grad.addColorStop(0, fillTop);
                            grad.addColorStop(1, 'transparent');
                            return grad;
                        }},
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: color,
                        pointHoverBorderColor: surfaceBg,
                        pointHoverBorderWidth: 2,
                        tension: 0.35,
                        fill: true,
                    }}]
                }},
                options: {{
                    responsive: false,
                    maintainAspectRatio: false,
                    animation: false,
                    interaction: {{
                        mode: 'index',
                        intersect: false,
                    }},
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            enabled: false,
                            external: function(context) {{
                                // HTML tooltip — renders outside canvas so it's never clipped
                                var tooltipEl = document.getElementById('chartjs-tooltip');
                                if (!tooltipEl) {{
                                    tooltipEl = document.createElement('div');
                                    tooltipEl.id = 'chartjs-tooltip';
                                    tooltipEl.style.cssText = 'position:fixed;pointer-events:none;z-index:9999;background:rgba(15,23,42,0.95);border:1px solid rgba(148,163,184,0.2);border-radius:6px;padding:6px 10px;font-family:' + fontMono + ';transition:opacity 0.15s;opacity:0;';
                                    document.body.appendChild(tooltipEl);
                                }}
                                var tooltip = context.tooltip;
                                if (tooltip.opacity === 0) {{
                                    tooltipEl.style.opacity = '0';
                                    return;
                                }}
                                var data = tooltip.dataPoints[0];
                                var v = data.raw;
                                var sign = v >= 0 ? '+' : '';
                                var dateLabel = '';
                                if (timestamps.length > data.dataIndex) {{
                                    var d = new Date(timestamps[data.dataIndex]);
                                    dateLabel = d.toDateString().slice(4, 10) + ' ';
                                }}
                                tooltipEl.innerHTML = '<div style="font-size:10px;color:' + fg2 + ';margin-bottom:2px;">' + dateLabel + '</div><div style="font-size:13px;font-weight:bold;color:' + color + ';">' + sign + v.toFixed(1) + '%</div>';
                                var rect = c.getBoundingClientRect();
                                var pos = rect.left + tooltip.caretX;
                                var top = rect.top + tooltip.caretY;
                                tooltipEl.style.left = Math.min(pos + 12, window.innerWidth - 160) + 'px';
                                tooltipEl.style.top = Math.max(top - 50, 10) + 'px';
                                tooltipEl.style.opacity = '1';
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ display: false }},
                        y: {{ display: false, min: -_yBound, max: _yBound }}
                    }},
                    layout: {{
                        padding: {{ top: 2, bottom: 4, left: 2, right: 2 }}
                    }},
                    elements: {{
                        line: {{
                            borderJoinStyle: 'round',
                            borderCapStyle: 'round',
                        }}
                    }}
                }},
                plugins: [{{
                    id: 'sparklineExtras',
                    afterDraw: function(chart) {{
                        var ctx = chart.ctx;
                        var xS = chart.scales.x;
                        var yS = chart.scales.y;
                        var left = chart.chartArea.left;
                        var right = chart.chartArea.right;
                        var btm = chart.chartArea.bottom;

                        ctx.save();

                        // Dashed zero line
                        var zy = yS.getPixelForValue(0);
                        ctx.beginPath();
                        ctx.strokeStyle = gridLineColor;
                        ctx.lineWidth = 1;
                        ctx.setLineDash([3, 4]);
                        ctx.moveTo(left, zy);
                        ctx.lineTo(right, zy);
                        ctx.stroke();
                        ctx.setLineDash([]);

                        // End dot with ring
                        var lastI = series.length - 1;
                        var lx = xS.getPixelForValue(lastI);
                        var ly = yS.getPixelForValue(series[lastI]);
                        ctx.beginPath();
                        ctx.fillStyle = color;
                        ctx.arc(lx, ly, 3.5, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.beginPath();
                        ctx.strokeStyle = surfaceBg;
                        ctx.lineWidth = 2;
                        ctx.arc(lx, ly, 3.5, 0, Math.PI * 2);
                        ctx.stroke();

                        // Time-axis labels
                        ctx.font = labelFont;
                        ctx.fillStyle = fg2;
                        ctx.textBaseline = 'bottom';
                        ctx.textAlign = 'start';
                        ctx.fillText(rangeStart, left, btm + 1);
                        ctx.textAlign = 'end';
                        ctx.fillText(rangeEnd, right, btm + 1);

                        ctx.restore();
                    }}
                }}]
            }});

            c._chart = chart;
        }})(canvases[ci]);
    }}
}})();
</script>""")


@app.get("/api/communication-map")
async def api_communication_map():
    """Alias for /api/pathway-graph — static HTML export compatibility."""
    graph = db.pathway_get_graph()
    return JSONResponse({"nodes": graph.get("nodes", []), "edges": graph.get("edges", [])})


@app.get("/api/phase/state")
async def api_phase_state():
    """Return the current dashboard phase as JSON (complements HTML /api/phase banner)."""
    return JSONResponse({
        "phase": db.get_phase(),
        "is_first_run": db.is_first_run(),
        "agents_exist": len(db.get_agents()) > 0,
        "no_llm": db.get_no_llm(),
    })


@app.post("/api/no-llm/toggle")
async def api_no_llm_toggle(request: Request):
    """Toggle LLM-powered features on/off."""
    try:
        body = await request.json()
        enabled = body.get("enabled", True)
        disabled = not enabled
        db.set_no_llm(disabled)
        # Sync the runtime flag so gates in other processes see the change
        from observeco.llm_service.gate import set_runtime_opt_out
        set_runtime_opt_out(disabled)
        return JSONResponse({"no_llm": disabled, "llm_enabled": enabled})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/phase/transition")
async def api_phase_transition(request: Request):
    """Transition to a new phase. Only forward progression allowed."""
    try:
        body = await request.json()
        phase = body.get("phase", "")
        if phase not in ("zero", "setup", "live"):
            return JSONResponse({"error": f"Invalid phase: {phase}"}, status_code=400)
        current = db.get_phase()
        db.set_phase(phase)
        if phase == "setup" and current == "zero":
            db.set_first_run_complete()
        return JSONResponse({"phase": db.get_phase(), "transitioned": phase != current})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ── Agent Discovery Wizard ─────────────────────────────────────────

@app.post("/api/discover/run")
async def api_discover_run():
    """Run agent discovery and cache results. Returns list of found candidates."""
    try:
        from observeco.auto_detect import run_discover as _run_disc
        from observeco.auto_detect import run_llm_discovery

        # Run static discovery first
        _run_disc(show_all=False)

        # Get current agents from config
        from observeco.config import load_config
        config = load_config()
        candidates = []

        # Static agents from config
        for agent in (config.agents or []):
            candidates.append({
                "name": agent.name,
                "type": agent.framework or "custom",
                "source": "config",
                "confidence": "high",
            })

        # If few found, try LLM discovery
        if len(candidates) < 2:
            try:
                llm_candidates = run_llm_discovery()
                for c in llm_candidates:
                    # Deduplicate by name
                    if not any(ex["name"].lower() == c.get("name", "").lower() for ex in candidates):
                        candidates.append({
                            "name": c.get("name", "unknown"),
                            "type": c.get("type", "unknown"),
                            "source": "llm",
                            "confidence": c.get("confidence", "low"),
                        })
            except Exception:
                pass

        db.set_discovery_candidates(candidates)
        return JSONResponse({"candidates": candidates, "count": len(candidates)})
    except Exception as e:
        return JSONResponse({"error": str(e), "candidates": [], "count": 0}, status_code=500)


@app.get("/api/discover/candidates")
async def api_discover_candidates():
    """Return cached discovery candidates."""
    return JSONResponse({"candidates": db.get_discovery_candidates(), "count": len(db.get_discovery_candidates())})


@app.post("/api/discover/run-html", response_class=HTMLResponse)
async def api_discover_run_html():
    """Run agent discovery and return HTML results for htmx."""
    try:
        from observeco.auto_detect import run_discover as _run_disc
        from observeco.auto_detect import run_llm_discovery

        # Run static discovery
        _run_disc(show_all=False)

        from observeco.config import load_config
        config = load_config()
        candidates = []

        for agent in (config.agents or []):
            candidates.append({
                "name": agent.name,
                "type": agent.framework or "custom",
                "source": "config",
                "confidence": "high",
            })

        if len(candidates) < 2:
            try:
                llm_candidates = run_llm_discovery()
                for c in llm_candidates:
                    if not any(ex["name"].lower() == c.get("name", "").lower() for ex in candidates):
                        candidates.append({
                            "name": c.get("name", "unknown"),
                            "type": c.get("type", "unknown"),
                            "source": "llm",
                            "confidence": c.get("confidence", "low"),
                        })
            except Exception:
                pass

        db.set_discovery_candidates(candidates)
    except Exception:
        logger.exception("swallowed exception in server.py")

    candidates = db.get_discovery_candidates()

    if not candidates:
        return HTMLResponse("""<div class="discover-results-empty" style="padding:8px 0;font-size:12px;color:#94a3b8;">
    <span>No agents found automatically.</span>
    <div style="margin-top:6px;">Add one manually with the field below, or check that your agents are running.</div>
</div>""")

    rows = "".join(
        f'''<div class="discover-result-row" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;background:rgba(255,255,255,0.04);margin-bottom:4px;">
    <span style="font-size:12px;font-weight:600;color:#e2e8f0;flex:1;">{c["name"]}</span>
    <span style="font-size:10px;color:#64748b;padding:1px 6px;border-radius:4px;background:rgba(100,116,139,0.15);">{c.get("type", "custom")}</span>
    <span style="font-size:10px;color:{"#22c55e" if c.get("confidence") == "high" else "#eab308"};">
        {"●" if c.get("confidence") == "high" else "◐"}
    </span>
</div>'''
        for c in candidates
    )

    return HTMLResponse(f"""<div class="discover-results" style="margin-top:8px;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <span style="font-size:13px;font-weight:600;color:#e2e8f0;">Found {len(candidates)} agent{"s" if len(candidates) != 1 else ""}</span>
        <button class="discover-confirm-btn"
            hx-post="/api/discover/confirm"
            hx-target="#discoverResults"
            hx-swap="innerHTML"
            hx-trigger="click"
            hx-on::after-request="setTimeout(function(){{ window.location.reload(); }}, 500);"
            style="background:#22c55e;color:#0c1628;border:none;border-radius:6px;padding:5px 12px;font-size:11px;font-weight:600;cursor:pointer;">
            ✓ Confirm & Continue
        </button>
    </div>
    {rows}
</div>""")


@app.post("/api/discover/confirm")
async def api_discover_confirm():
    """Confirm discovery results — register all candidates as agents."""
    candidates = db.get_discovery_candidates()
    if not candidates:
        return JSONResponse({"error": "No candidates to confirm. Run discovery first."}, status_code=400)

    # Before registering, check if we already have agents
    existing_agents = db.get_agents()
    had_agents = len(existing_agents) > 0

    registered = 0
    for c in candidates:
        try:
            db.register_agent(c["name"], c.get("type", "custom"), "")
            registered += 1
        except Exception:
            pass

    # Clear candidates after confirmation
    db.clear_discovery_candidates()

    # Transition phase if this is the first batch of agents
    if not had_agents and registered > 0:
        db.set_phase("setup")

    return JSONResponse({"registered": registered, "total": len(candidates)})


# § Skills Audit endpoint
# ---------------------------------------------------------------------------

@app.get("/api/skills-audit")
async def api_skills_audit(agent: str = "all"):
    """Ranked skill audit — real data from cards.json + chisel_drift table."""
    skills_dir = Path.home() / ".hermes" / "skills"
    cards_path = skills_dir / "cards.json"

    skills = []
    categories = {}
    total_tokens = 0

    # 1. Read real skills from cards.json
    if cards_path.exists():
        try:
            cards = json.loads(cards_path.read_text())
            for card in cards:
                name = card.get("name", "unknown")
                cat = card.get("category", "uncategorized")
                tokens = card.get("total_tokens", 0)

                # Skip .archive and .hermes — internal categories
                if cat.startswith("."):
                    continue

                total_tokens += tokens
                # Check if .bak exists → skill is compressed
                compressed = False
                try:
                    bak_path = skills_dir / cat / name / "SKILL.md.bak"
                    if bak_path.exists():
                        compressed = True
                except Exception:
                    pass

                skills.append({
                    "name": name,
                    "category": cat,
                    "tokens": tokens,
                    "compressed": compressed,
                })

                if cat not in categories:
                    categories[cat] = {"skills": 0, "tokens": 0}
                categories[cat]["skills"] += 1
                categories[cat]["tokens"] += tokens
        except Exception:
            pass

    # 2. Fallback: walk filesystem if cards.json missing
    if not skills and skills_dir.is_dir():
        try:
            from observeco.chisel.trim import _count_tokens, _parse_skill_yaml
            for sf in sorted(skills_dir.rglob("SKILL.md")):
                try:
                    meta = _parse_skill_yaml(sf)
                except Exception:
                    meta = None
                body = sf.read_text(encoding="utf-8")
                desc_text, body_text = "", body
                if body.startswith("---"):
                    parts = body.split("---", 2)
                    desc_text = parts[1] if len(parts) >= 2 else ""
                    body_text = parts[2] if len(parts) >= 3 else ""
                desc_tokens = _count_tokens(desc_text)
                body_tokens = _count_tokens(body_text)
                tokens = desc_tokens + body_tokens

                cat = sf.parent.parent.name if sf.parent.parent.name != "skills" else "uncategorized"
                if cat.startswith("."):
                    continue
                name = (meta or {}).get("name", sf.parent.name)

                total_tokens += tokens
                # Check if .bak exists → skill is compressed
                compressed = sf.with_suffix(".md.bak").exists()
                skills.append({"name": str(name), "category": cat, "tokens": tokens, "compressed": compressed})
                if cat not in categories:
                    categories[cat] = {"skills": 0, "tokens": 0}
                categories[cat]["skills"] += 1
                categories[cat]["tokens"] += tokens
        except Exception:
            pass

    # 3. Sort by tokens descending, assign ranks
    skills.sort(key=lambda s: s["tokens"], reverse=True)
    for i, s in enumerate(skills, 1):
        s["rank"] = i

    # 4. Query drift data if available
    drift_available = False
    drift_rows = {}
    try:
        drift_data = db.get_drift()
        if drift_data:
            drift_available = True
            for r in drift_data:
                agent_name = r.get("agent_name", "")
                comp = r.get("component", "")
                drift_rows.setdefault(agent_name, {})[comp] = {
                    "delta_pct": r.get("delta_pct", 0),
                    "breached": r.get("breached", False),
                }
    except Exception:
        logger.exception("swallowed exception in server.py")

    # 5. Build summary
    # Rough cost: assume 250 sessions/mo × skill_tokens × ~$0.00015 per K tokens (DeepSeek V3)
    SESSIONS_PER_MONTH = 250
    COST_PER_1M_TOKENS = 0.15  # DeepSeek V3 input pricing
    monthly_tokens = total_tokens * SESSIONS_PER_MONTH
    monthly_cost = (monthly_tokens / 1_000_000) * COST_PER_1M_TOKENS
    yearly_cost = monthly_cost * 12

    summary = {
        "total_skills": len(skills),
        "tokens_per_session": total_tokens,
        "monthly_tokens_burned": monthly_tokens,
        "yearly_tokens_burned": monthly_tokens * 12,
        "monthly_cost": round(monthly_cost, 2),
        "yearly_cost": round(yearly_cost, 2),
        "drift_available": drift_available,
        "model_pricing": f"DeepSeek V3 @ ${COST_PER_1M_TOKENS}/M tokens",
        "sessions_per_month": SESSIONS_PER_MONTH,
    }

    return JSONResponse({
        "skills": skills,
        "summary": summary,
        "categories": dict(sorted(categories.items(), key=lambda x: -x[1]["tokens"])),
    })


@app.get("/api/chisel-preview")
async def api_chisel_preview(agent: str = "all", mode: str = "lite"):
    """Chisel compression preview — real trim data from DB.

    Lite = guidance-only compression (savings varies per agent).
    Full = guidance + memory + skills compression.
    Savings percentages are computed from actual component breakdown per agent.
    """
    trims = db.get_trims(limit=20)
    latest = {}
    for t in trims:
        if t["agent_name"] not in latest:
            latest[t["agent_name"]] = t

    # Query actual savings from compress_log
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row
    actual_lite = {}
    actual_full = {}
    try:
        for row in conn.execute(
            "SELECT agent_name, mode, savings_pct FROM compress_log ORDER BY timestamp DESC LIMIT 200"
        ).fetchall():
            if row["mode"] == "lite" and row["agent_name"] not in actual_lite:
                actual_lite[row["agent_name"]] = row["savings_pct"]
            if row["mode"] == "full" and row["agent_name"] not in actual_full:
                actual_full[row["agent_name"]] = row["savings_pct"]
    except Exception:
        logger.exception("swallowed exception in server.py")

    result = {}
    for name, t in latest.items():
        raw = t["total_tokens"]
        guidance_t = t.get("guidance_tokens", 0)
        skills_t = t.get("skills_tokens", 0)
        memory_t = t.get("memory_tokens", 0)
        tools_t = t.get("tools_tokens", 0)
        identity_t = t.get("identity_tokens", 0)

        # Lite: compress guidance @ 70% — fast lightweight reduction
        lite_savings_ratio = min(0.25, max(0.0, guidance_t / max(raw, 1)))
        lite = max(0, raw - int(guidance_t * 0.7))  # Compress guidance by ~70%

        # Full: guidance @ 70% (same as Lite) + memory + skills @ 40%
        # Full always >= Lite because it applies Lite's aggressive rate on guidance,
        # then adds gentler compression on the remainder.
        base = int(guidance_t * 0.7)
        extra = int((memory_t + skills_t) * 0.4)
        full_val = max(0, raw - base - extra)
        full_targets = guidance_t + memory_t + skills_t
        full_savings_ratio = min(0.50, max(0.0, full_targets / max(raw, 1)))

        result[name] = {
            "raw_tokens": raw,
            "lite_tokens": lite,
            "full_tokens": full_val,
            "lite_savings_pct": round((1 - lite / max(raw, 1)) * 100, 1),
            "full_savings_pct": round((1 - full_val / max(raw, 1)) * 100, 1),
            "actual_lite_pct": actual_lite.get(name),
            "actual_full_pct": actual_full.get(name),
            "savings_ratio": round(lite_savings_ratio, 3),
            "full_savings_ratio": round(full_savings_ratio, 3),
            "components": {"identity": identity_t, "skills": skills_t,
                           "memory": memory_t, "tools": tools_t,
                           "guidance": guidance_t},
        }
    return JSONResponse({"agents": result, "agent_count": len(result), "mode": mode})


@app.get("/api/openclaw-plugins")
async def api_openclaw_plugins():
    """OpenClaw plugin install/runtime status."""
    loads = db.get_loads()
    agents = [a for a in db.get_agents() if a.get("framework","").lower() == "openclaw"]
    result = {"agents": [a["agent_name"] for a in agents],
        "plugin_sources": [
            {"name": "clawforge_garden", "status": "active", "icon": "🧠", "intents": ["memory_garden", "profile_scan"]},
            {"name": "signal_router", "status": "active", "icon": "🔀", "intents": ["signal_deliver", "inbox_poll"]},
            {"name": "intent_classifier", "status": "active", "icon": "🏷️", "intents": ["classify", "route"]},
            {"name": "file_watcher", "status": "idle", "icon": "👀", "intents": ["watch", "notify"]}],
        "recent_loads": [{"source": ld.get("intent_class","unknown"), "loaded": ld.get("sources_loaded",0),
                          "skipped": ld.get("sources_skipped",0), "saved": ld.get("tokens_saved",0)} for ld in loads[:5]],
            "profiles_count": len(db.get_profiles())}
    return JSONResponse(result)


# §6.2 — Agent Cards (mockup fleet-dashboard format)
# ---------------------------------------------------------------------------

@app.get("/api/agents", response_class=HTMLResponse)
async def api_agents(
    hidden: str = "",
    q: str = "",
    status: str = "",
    page: int = 1,
    per_page: int = 25,
):
    """Agent cards with search, filter, pagination — 100+ agents supported.

    Query params:
        hidden: Comma-separated agent names to hide.
        q: Text search — matches agent name and framework (case-insensitive).
        status: Filter by status — 'alive', 'dead', 'error', '' (all).
        page: 1-indexed page number (default 1).
        per_page: Agents per page (default 25, max 100).
    """
    summary = db.get_agent_status_summary()
    agents = db.get_agents()
    breakers = {b["agent_name"]: b for b in db.get_circuit_breakers()}
    trims_all = db.get_trims(limit=30)

    all_agent_names = set(a["agent_name"] for a in agents)
    for name in summary:
        all_agent_names.add(name)

    # Filter hidden agents
    hidden_set = set(n.strip() for n in hidden.split(",") if n.strip())
    if hidden_set:
        all_agent_names = {n for n in all_agent_names if n not in hidden_set}

    trimmed_agents = {}
    for t in trims_all:
        if t["agent_name"] not in trimmed_agents:
            trimmed_agents[t["agent_name"]] = t

    now = int(time.time())
    agent_cfg = {a["agent_name"]: a for a in agents}

    # Type grouping
    name_type = {}
    for name in all_agent_names:
        a = agent_cfg.get(name, {})
        fw = a.get("framework", "custom")
        hc = a.get("health_check", "") or ""
        cfg_path = a.get("config_path", "") or ""
        if fw in ("hermes", "openclaw", "agent") or "SOUL.md" in cfg_path:
            name_type[name] = "agent"
        elif any(w in fw.lower() for w in ("hermes", "openclaw")):
            name_type[name] = "agent"
        elif fw == "service" or hc:
            name_type[name] = "service"
        elif fw == "custom":
            name_type[name] = "other"
        else:
            name_type[name] = "workflow"

    # ── Search (q=) filter ───────────────────────────────────────
    q_lower = q.strip().lower()
    q_is_active = bool(q_lower)
    if q_lower:
        filtered_names = set()
        for name in all_agent_names:
            a = agent_cfg.get(name, {})
            fw = (a.get("framework", "") or "").lower()
            if q_lower in name.lower() or q_lower in fw:
                filtered_names.add(name)
        all_agent_names = filtered_names

    # Track whether any filter is active (for no-match state)
    filter_is_active = bool(q_is_active) or bool(status)

    # ── Status filter ────────────────────────────────────────────
    if status:
        status_names = set()
        for name in all_agent_names:
            s = summary.get(name, {})
            agent_status = s.get("status") or "unknown"
            if agent_status == status:
                status_names.add(name)
        all_agent_names = status_names

    # ── Pagination ───────────────────────────────────────────────
    clamped_page = max(1, page)
    clamped_pp = max(1, min(per_page, 100))
    sorted_names = sorted(all_agent_names)
    total_filtered = len(sorted_names)
    total_pages = max(1, (total_filtered + clamped_pp - 1) // clamped_pp)
    clamped_page = min(clamped_page, total_pages)
    start_idx = (clamped_page - 1) * clamped_pp
    end_idx = start_idx + clamped_pp
    page_names = sorted_names[start_idx:end_idx]

    sections = {"agent": [], "service": [], "workflow": [], "other": []}
    for name in page_names:
        t = name_type.get(name, "workflow")
        sections[t].append(name)

    section_configs = [
        ("agent", "Agents", "#22c55e", "🤖"),
        ("service", "Services", "#3b82f6", "⚙️"),
        ("workflow", "Workflows", "#64748b", "📦"),
        ("other", "Others", "#6b7280", "📂"),
    ]


    sections_html = []

    for sec_key, sec_label, sec_color, sec_icon in section_configs:
        names = sections[sec_key]
        if not names:
            continue

        cards_html = []
        for name in names:
            s = summary.get(name, {})
            agent_status = s.get("status", "unknown")
            ever_alive = s.get("ever_alive", False)
            ts = s.get("timestamp", 0)
            cb = breakers.get(name, {})
            tripped = cb.get("tripped", 0)
            agent_type = name_type.get(name, "workflow")

            # Distinguish "dead" (was running, went down) from "not running" (never seen alive)
            if agent_status == 'dead' and not ever_alive:
                agent_status = 'not_running'
            status_text = {"alive": "Running", "dead": "Down", "not_running": "Not running", "error": "Warning"}.get(agent_status, "Unknown")

            fw_agent_type = {"agent": "Agent", "service": "Service", "workflow": "Workflow"}.get(agent_type, "Workflow")
            fw = agent_cfg.get(name, {}).get("framework", "") or ""
            # Handle composite frameworks like "hermes + openclaw"
            fw_parts = [p.strip().capitalize() for p in fw.split("+")] if fw else []
            fw_display = " + ".join(fw_parts) if fw_parts else ""

            role_label = f"{fw_agent_type} · {fw_display}" if fw_display else fw_agent_type

            # Last seen: prefix with "last pulse" when data is stale
            last_check_str = _fmt_ts(ts) if ts else "—"
            if ts and (now - ts) > 3600:
                last_check_str = f"last pulse {_fmt_ts(ts)}"

            # Error badge
            errors = db.get_errors(agent_name=name, limit=50)
            recent_errors = [e for e in errors if now - e.get("timestamp", 0) < 86400]
            recent_error_count = len(recent_errors)

            # Discovery gap badges
            gap_badges = []
            pulses = db.get_recent_pulses(agent_name=name, limit=5)
            if not pulses:
                gap_badges.append('<span class="gap-badge">🔍 No pulses</span>')
            t_check = db.get_trims(agent_name=name, limit=1)
            if not t_check:
                gap_badges.append('<span class="gap-badge">🔍 No tokens</span>')
            drift_check = db.get_drift(agent_name=name)
            if not drift_check:
                gap_badges.append('<span class="gap-badge">🔍 No drift</span>')
            gap_badges_str = " <span class=\"sep-pipe\">|</span> ".join(gap_badges) if gap_badges else ""

            # Token bar inside card
            trim_data = trimmed_agents.get(name)
            token_bar = ""
            total_comp = 0
            if trim_data:
                comps = [
                    ("identity", trim_data.get("identity_tokens", 0)),
                    ("skills", trim_data.get("skills_tokens", 0)),
                    ("memory", trim_data.get("memory_tokens", 0)),
                    ("tools", trim_data.get("tools_tokens", 0)),
                    ("guidance", trim_data.get("guidance_tokens", 0)),
                ]
                comps = sorted(comps, key=lambda x: -x[1])
                total_comp = max(trim_data.get("total_tokens", 1), 1)
                segs = ""
                for comp_key, val in comps:
                    pct = val / total_comp * 100
                    col = COMP_COLORS.get(comp_key, "#6b7280")
                    segs += f'<span class="seg" style="width:{pct:.1f}%;background:{col};" title="{COMP_NAMES.get(comp_key,comp_key)}: {val:,}"></span>'
                token_bar = f'<div class="token-bar">{segs}</div><div class="token-count">{total_comp:,} total</div>'
            else:
                token_bar = '<div class="token-count" style="color:#475569;">No brain data</div>'

            # Drift
            drift_data = db.get_drift(agent_name=name)
            drift_val = 0
            drift_str = "📈 Learning..."
            if drift_data:
                vals = [d.get("delta_pct", 0) for d in drift_data[-7:]]
                if vals:
                    drift_val = sum(vals) / len(vals)
                    drift_str = f"{'📈' if drift_val > 0 else '📉' if drift_val < 0 else '➡️'} {drift_val:+.1f}% this week" if abs(drift_val) > 0.1 else "➡️ 0.0% this week"

            # Circuit/guard — acknowledge dead agent status + stale-alive window
            stale = ts and (now - ts) > 3600  # same stale as status row
            if agent_status in ('dead', 'not_running'):
                guard_label = "⚠️ Agent is down" if agent_status == 'dead' else "○ Agent not started"
                guard_color = "var(--warn)" if agent_status == 'dead' else "var(--muted)"
            elif agent_status == 'unknown':
                guard_label = "⚪ No data (not pulse-monitored)"
                guard_color = "var(--muted)"
            elif tripped:
                guard_label = "🔴 Stopped (failed 3x)"
                guard_color = "var(--danger)"
            elif stale and agent_status == 'alive':
                guard_label = "⚠️ Guard: possible stale"
                guard_color = "var(--warn)"
            else:
                guard_label = "✅ Guard OK"
                guard_color = "var(--accent)"

            # Error row label
            if agent_status == 'unknown':
                err_label = "⚪ Not monitored by pulse"
                err_color = "var(--muted)"
            elif recent_error_count > 0:
                err_label = f"⚠️ {recent_error_count} in last 24h"
                err_color = "var(--warn)"
            else:
                err_label = "- No errors"
                err_color = "var(--muted)"

            # Status label with staleness indicator
            stale = ts and (now - ts) > 3600  # stale if last pulse > 1h ago
            status_label = {'alive': '● Running', 'dead': '● Down', 'not_running': '○ Not running', 'error': '● Warning'}.get(agent_status, '○ Unknown')
            if agent_status == 'unknown':
                status_label = '○ Not pulse-monitored'
            elif stale and agent_status == 'alive':
                status_label = '● Running (stale)'
            if stale and agent_status == 'error':
                status_label = '● Warning (stale)'

            # Confidence & Recommendation (§3.29)
            state_since = ts if ts else (now - 86400)  # approximate
            conf = _compute_confidence(agent_status, pulses, recent_errors, cb, state_since, now)
            conf_badge = _confidence_badge(conf)

# Conditional rows — agent-only features hidden for services/workflows/others
            is_agent = agent_type == 'agent'
            guard_row = ''
            if is_agent:
                guard_row = f'<div class="metric-row" onclick="loadTab(\'{name}\',\'guard\',\'agent\')">'
                guard_row += '\n        <span class="label">Guard<span class="glossary-hint" onclick="event.stopPropagation();showGlossary(\'circuit\', event)">?</span></span>'
                guard_row += '\n        <span class="value" style="color:' + guard_color + ';font-weight:600;">' + guard_label + '</span>'
                guard_row += '\n        <span class="click-hint">See details</span><span class="arrow">\u203a</span>\n      </div>'

            # Token & Drift rows — agent-only
            token_row = ''
            drift_row = ''
            if is_agent:
                token_row = f'<div class="metric-row" onclick="loadTab(\'{name}\',\'tokens\',\'agent\')">'
                token_row += '\n        <span class="label">Tokens<span class="glossary-hint" onclick="event.stopPropagation();showGlossary(\'tokens\', event)">?</span></span>'
                token_row += '\n        <span class="value">' + token_bar + '</span>'
                token_row += '\n        <span class="click-hint">See details</span><span class="arrow">\u203a</span>\n      </div>'
                drift_row = f'<div class="metric-row" onclick="loadTab(\'{name}\',\'drift\',\'agent\')">'
                drift_row += '\n        <span class="label">Drift<span class="glossary-hint" onclick="event.stopPropagation();showGlossary(\'drift\', event)">?</span></span>'
                drift_row += '\n        <span class="value" style="color:var(--muted);">' + drift_str + '</span>'
                drift_row += '\n        <span class="click-hint">See details</span><span class="arrow">\u203a</span>\n      </div>'

            cards_html.append(f"""<div class="agent-card" data-agent="{name}">
      <button class="agent-toggle" onclick="event.stopPropagation();toggleHide('{name}')" title="Hide agent"></button>
      <button class="agent-delete" onclick="event.stopPropagation();deleteAgent('{name}')" title="Remove agent">✕</button>
      <div class="card-top">
        <span class="agent-status {agent_status}" title="{status_text}"></span>
        <div class="agent-info">
          <div class="agent-name">{_html_escape(name)}</div>
          <div class="agent-meta">{role_label}</div>
        </div>
        <div class="agent-last-seen">{last_check_str}</div>
      </div>
      {f'<div style="margin-bottom:6px;">{gap_badges_str}</div>' if gap_badges_str else ''}
      <div class="metric-row" onclick="loadTab('{name}','health','{agent_type}')">
        <span class="label">Health<span class="glossary-hint" onclick="event.stopPropagation();showGlossary('status-dot', event)">?</span></span>
        <span class="value" style="color:{'var(--accent)' if agent_status == 'alive' else 'var(--danger)' if agent_status == 'dead' else 'var(--muted)' if agent_status == 'not_running' else 'var(--warn)'};font-weight:600;">{status_label}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      {conf_badge if is_agent else ''}
      {guard_row}
      {token_row}
      {drift_row}
      <div class="metric-row" onclick="loadTab('{name}','errors')">
        <span class="label">Errors<span class="glossary-hint" onclick="event.stopPropagation();showGlossary('error-badge', event)">?</span></span>
        <span class="value" style="color:{err_color};">{err_label}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      {_canary_card(name)}
    </div>""")

        if cards_html:
            count = len(cards_html)
            cards_str = "\n".join(cards_html)
            sections_html.append(f"""<div class="section">
    <div class="section-header" onclick="toggleSection(this)">
      <span class="chevron">▼</span>
      <span class="section-name">{sec_label}</span>
      <span class="section-count">{count} / {len(names)}</span>
    </div>
    <div class="section-body">
      {cards_str}
    </div>
  </div>""")

    if not sections_html and filter_is_active:
        # Search/filter returned no matching agents
        clear_link = " onclick=\"clearFilters()\" style=\"color:#818cf8;cursor:pointer;\""
        return HTMLResponse(
            f'<div class="empty-state" style="color:#6b7280;font-size:13px;text-align:center;padding:24px;">'
            f'No agents match filter'
            f'<br><span{clear_link}>Clear filters</span></div>'
        )

    if not sections_html:
        # No agents at all (first run) — show setup guidance
        return HTMLResponse(
            '<div class="empty-state" style="text-align:center;padding:40px 20px;color:#6b7280;">'
            '<div style="font-size:48px;margin-bottom:12px;">🔍</div>'
            '<div style="font-size:16px;font-weight:600;margin-bottom:8px;color:#94a3b8;">No agents detected</div>'
            '<div style="font-size:13px;line-height:1.6;">'
            'Add your first agent to start monitoring.<br>'
            'Use <code style="background:#1e293b;padding:2px 6px;border-radius:4px;">observeco discover</code> to scan for running agents,<br>'
            'or <code style="background:#1e293b;padding:2px 6px;border-radius:4px;">observeco add &lt;name&gt;</code> to register one manually.'
            '</div>'
            '</div>'
        )

    count = sum(len(sections[sk]) for sk, _, _, _ in section_configs if sections.get(sk))

    # Build pagination controls
    pagination_html = ""
    if total_pages > 1:
        prev_disabled = "style=\"opacity:0.4;pointer-events:none;\"" if clamped_page <= 1 else ""
        next_disabled = "style=\"opacity:0.4;pointer-events:none;\"" if clamped_page >= total_pages else ""
        q_param = f"&q={q}" if q else ""
        s_param = f"&status={status}" if status else ""
        h_param = f"&hidden={hidden}" if hidden else ""
        pagination_html = f"""
<div class="pagination-bar" id="paginationBar" style="display:flex;align-items:center;justify-content:center;gap:8px;padding:12px 0;font-size:12px;color:#94a3b8;">
    <button hx-get="/api/agents?page=1&per_page={clamped_pp}{q_param}{s_param}{h_param}" hx-target="#fleetContainer" hx-swap="innerHTML" {prev_disabled} class="page-btn">⏮</button>
    <button hx-get="/api/agents?page={max(1, clamped_page - 1)}&per_page={clamped_pp}{q_param}{s_param}{h_param}" hx-target="#fleetContainer" hx-swap="innerHTML" {prev_disabled} class="page-btn">◀</button>
    <span style="color:#e2e8f0;">{clamped_page} / {total_pages}</span>
    <button hx-get="/api/agents?page={clamped_page + 1}&per_page={clamped_pp}{q_param}{s_param}{h_param}" hx-target="#fleetContainer" hx-swap="innerHTML" {next_disabled} class="page-btn">▶</button>
    <button hx-get="/api/agents?page={total_pages}&per_page={clamped_pp}{q_param}{s_param}{h_param}" hx-target="#fleetContainer" hx-swap="innerHTML" {next_disabled} class="page-btn">⏭</button>
    <span style="margin-left:8px;">Showing {start_idx + 1}–{min(end_idx, total_filtered)} of {total_filtered}</span>
</div>"""

    sections_html.append(pagination_html)

    return HTMLResponse("\n".join(sections_html))


@app.post("/api/agents/add")
async def api_add_agent(request: Request):
    """Register a new agent via the feedback bar. §6.2."""
    try:
        body = await request.json()
        name = body.get("name", "").strip()
        fw_type = body.get("framework", "custom")
        if not name:
            return JSONResponse({"ok": False, "error": "Name required"}, status_code=400)

        existing_dict = {a["agent_name"]: a for a in db.get_agents()}

        if name in existing_dict:
            existing_fw = existing_dict[name].get("framework", "")

            # Case 1: user selected a type classifier ("Agent", "Service", "Workflow")
            # → they're trying to re-add something already visible. Reject.
            if fw_type in ("agent", "service", "workflow", "custom"):
                return JSONResponse({
                    "ok": False,
                    "error": f"'{name}' already displayed as card",
                    "reason": "already_visible",
                })

            # Case 2: user typed a real framework name — check if it's already tracked
            existing_parts = set(p.strip().lower() for p in existing_fw.split("+"))
            if fw_type.lower().strip() in existing_parts:
                return JSONResponse({
                    "ok": False,
                    "error": f"'{name}' already has '{fw_type}' in its card label",
                    "reason": "already_visible",
                })

            # Case 3: legitimate new framework to merge (e.g. Kepler + Hermes)
            composite = existing_fw + " + " + fw_type
            db.register_agent(name, framework=composite)
            return JSONResponse({
                "ok": True,
                "merged": True,
                "framework": composite,
                "message": f"Merged {fw_type} into {name}'s identity",
            })

        # New agent — register with type as framework
        db.register_agent(name, framework=fw_type)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.delete("/api/agents/{agent_name}")
async def api_delete_agent(agent_name: str):
    """Remove an agent and all its data from the dashboard."""
    try:
        # Check if agent exists first
        existing = {a["agent_name"] for a in db.get_agents()}
        if agent_name not in existing:
            return JSONResponse({"ok": False, "error": f"Agent '{agent_name}' not found"}, status_code=404)
        db.remove_agents([agent_name])
        # Also exclude from auto-discovery so it doesn't reappear
        from observeco.config import exclude_agent
        exclude_agent(agent_name)
        return JSONResponse({"ok": True, "message": f"Removed {agent_name}"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/agent/{agent_name}/profile")
async def api_agent_profile(request: Request, agent_name: str, focus: str = ""):
    """Four-pillar agent profile modal (OBS-SPEC-093).

    Returns the c-modal-profile.html partial with status line, pillar tiles,
    issue cards, and technical drawer. Replaces the T4 JSON endpoint with
    the dashboard's presentation-layer synthesizer.

    Optional ?focus= param scrolls to a specific pillar section on open:
      reliability, quality, usage, memory

    For raw T4 JSON data, call get_agent_profile() from
    observeco.agent_profile_service directly.
    """
    from observeco.dashboard.services.agent_profile_service import get_agent_profile

    try:
        profile = get_agent_profile(agent_name, use_cache=False)
    except Exception:
        logger.exception("agent_profile failed for %s", agent_name)
        return templates.TemplateResponse(request, "partials/c57.html", {"html": """<div class="scrim"><div class="modal">
    <div class="m-head">
        <span class="m-name" style="color:var(--fg-3)">Error</span>
        <span class="m-close" onclick="this.closest('.scrim').remove()">✕</span>
    </div>
    <div class="m-body">
        <div class="state-msg err">
            <div class="ico">⚠</div>
            <h3>Agent data unavailable</h3>
            <p>The profile service encountered an error.</p>
        </div>
    </div>
</div></div>"""})

    if "error" in profile:
        return templates.TemplateResponse(request, "partials/c57.html", {"html": f"""<div class="scrim"><div class="modal">
    <div class="m-head">
        <span class="m-name" style="color:var(--fg-3)">Not found</span>
        <span class="m-close" onclick="this.closest('.scrim').remove()">✕</span>
    </div>
    <div class="m-body">
        <div class="state-msg"><div class="ico">🔍</div><h3>Agent not found</h3>
        <p>No agent named "{_html_escape(agent_name)}" is registered.</p></div>
    </div>
</div></div>"""})

    return templates.TemplateResponse(request, "partials/c-modal-profile.html", {"profile": profile, "focus": focus})


@app.get("/api/agent/{agent_name}/traces")
async def api_agent_traces(agent_name: str, trace_id: str = "", limit: int = 200):
    """Get trace spans for an agent (T1 Tracing Layer)."""
    try:
        spans = db.get_trace_spans(agent_name=agent_name, trace_id=trace_id, limit=limit)
        return {"ok": True, "agent_name": agent_name, "spans": spans, "count": len(spans)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/agent/{agent_name}/sessions")
async def api_agent_sessions(agent_name: str, limit: int = 20):
    """Get trace sessions for an agent (T1 Tracing Layer)."""
    try:
        sessions = db.get_trace_sessions(agent_name=agent_name, limit=limit)
        return {"ok": True, "agent_name": agent_name, "sessions": sessions, "count": len(sessions)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/anomalies")
async def api_anomalies(lookback_minutes: int = 60):
    """Get fleet-wide anomaly feed (T3 Behavioral Monitoring)."""
    try:
        from observeco.anomaly import detect_anomalies
        anomalies = detect_anomalies(db=db, lookback_minutes=lookback_minutes)
        return {"ok": True, "anomalies": anomalies, "count": len(anomalies)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/anomaly-feed", response_class=HTMLResponse)
async def api_anomaly_feed(lookback_minutes: int = 120):
    """HTML fragment for the anomaly feed tab (T3)."""
    try:
        from observeco.anomaly import detect_anomalies
        anomalies = detect_anomalies(db=db, lookback_minutes=lookback_minutes)
    except Exception as e:
        return f'<div style="color:#ef4444;font-size:13px;">Error: {e}</div>'

    if not anomalies:
        return '<div style="color:#94a3b8;font-size:13px;padding:20px;text-align:center;">✅ No anomalies detected in the last {lookback_minutes} minutes.</div>'

    html = f'<div style="font-size:12px;color:#64748b;margin-bottom:12px;">{len(anomalies)} anomalies in last {lookback_minutes} min</div>'
    for a in anomalies:
        severity_color = {"critical": "#ef4444", "warning": "#eab308", "info": "#3b82f6"}.get(a.get("severity", "info"), "#64748b")
        severity_icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(a.get("severity", "info"), "•")
        html += f'''<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px;border-left:3px solid {severity_color};">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span>{severity_icon}</span>
            <span style="font-size:13px;font-weight:600;color:var(--fg);">{a.get("type", "unknown")}</span>
            <span style="font-size:11px;color:var(--fg-2);">{a.get("agent_name", "")}</span>
          </div>
          <div style="font-size:12px;color:var(--fg-2);margin-left:24px;">{a.get("description", "")}</div>
        </div>'''
    return HTMLResponse(html)


@app.post("/api/chisel/compress")
async def api_chisel_compress(request: Request):
    """Compress an agent's SOUL.md via the dashboard.

    Accepts JSON: {"agent": "name", "mode": "lite"|"full", "preview": true|false}
    preview=true: dry-run, no files modified.
    Returns: {"status": "ok", "message": "...", "backup": "...", "before_tokens": N, "after_tokens": N, "savings": N, "savings_pct": N}
    """
    try:
        body = await request.json()
        agent_name = body.get("agent", "").strip()
        mode = body.get("mode", "lite").strip().lower()
        preview = body.get("preview", False)
        if not agent_name:
            return JSONResponse({"status": "error", "message": "Agent name required"}, status_code=400)
        if mode not in ("lite", "full"):
            return JSONResponse({"status": "error", "message": "Mode must be 'lite' or 'full'"}, status_code=400)

        # Gate: full compression requires Pro
        if mode == "full":
            from observeco import license as lic
            if not lic.require_pro():
                return JSONResponse({"status": "error", "message": "Full compression requires Pro — start a free trial"}, status_code=402)

        from observeco.chisel.trim import run_compress
        result = run_compress(agent_name=agent_name, mode=mode, dry_run=preview)

        if preview:
            return JSONResponse(result)

        # Also log to database
        from observeco.db import Database
        local_db = Database()
        # Use db._write() (retry-on-lock) — the watch daemon writes pulse.db constantly.
        try:
            local_db._write(
                "INSERT INTO compress_log (agent_name, mode, before_tokens, after_tokens, savings, "
                "savings_pct, backup_path, triggered_by, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (result["agent"], result["mode"], result["before_tokens"], result["after_tokens"],
                 result["savings"], result["savings_pct"], result.get("backup", ""),
                 "dashboard", int(__import__("time").time())),
            )
        except _sqlite3.OperationalError:
            logger.warning("compress_log insert failed (db locked): %s", result.get("agent"))
        return JSONResponse(result)
    except FileNotFoundError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/token-history")
async def api_token_history(days: int = 90, agent: str = ""):
    """90-day token trend data — aggregated from token_logs (consistent with Token Analytics tab)."""
    from observeco.tracking.token_analytics import aggregate_tokens, compute_summary
    now = int(time.time())
    from_ts = now - days * 86400
    data = aggregate_tokens(agent=agent, from_ts=from_ts, to_ts=now, granularity="day", include_source="sdk,otel,watch")
    if not data:
        return {"has_real_data": False, "snapshots": [], "summary": {}}
    snapshots = [{
        "date": d["bucket_start"],
        "input_tokens": d.get("input_tokens", 0),
        "output_tokens": d.get("output_tokens", 0),
        "cache_creation": d.get("cache_creation_tokens", 0),
        "cache_read": d.get("cache_read_tokens", 0),
        "total_tokens": d.get("total_tokens", 0),
        "turn_count": d.get("turn_count", 0),
    } for d in data]
    summary = compute_summary(data)
    return {"has_real_data": True, "snapshots": snapshots, "summary": summary}


@app.get("/api/token-analytics", response_class=HTMLResponse)
async def api_token_analytics(days: int = 7):
    """Token Analytics page — v2 Strong-Fit HTML with Chart.js cost trend, attribution gap,
    per-agent cost table, composition bars, and cache efficiency bars.
    GET /api/token-analytics?days=7
    """
    from observeco.dashboard.routes.token_analytics import (
        error_html,
        token_analytics,
    )
    try:
        return await token_analytics(days)
    except Exception:
        return HTMLResponse(error_html())


@app.get("/api/tokens/chart")
async def api_tokens_chart(
    granularity: str = "hour",
    component: str = "total",
    from_ts: int = 0,
    to_ts: int = 0,
    agent: str = "",
    provider: str = "",
    include_source: str = "sdk,otel,watch",
):
    """Chart data for Token Analytics tab — matches frontend fetchTokenData() expectations."""
    from observeco.tracking.token_analytics import aggregate_tokens, compute_summary
    data = aggregate_tokens(
        agent=agent, provider=provider,
        from_ts=from_ts, to_ts=to_ts,
        granularity=granularity, include_source=include_source,
    )
    if not data:
        return {"data": [], "summary": {"total_tokens": 0, "total_cost": 0, "avg_per_turn": 0, "turn_count": 0}, "granularity": granularity, "component": component}
    summary = compute_summary(data)
    return {
        "data": data,
        "summary": summary,
        "granularity": granularity,
        "component": component,
    }


@app.get("/api/tokens/verdict")
async def api_tokens_verdict(from_ts: int = 0, to_ts: int = 0):
    """One-sentence cost health verdict — top spender, cache trend, recommendation."""
    from observeco.tracking.token_analytics import get_verdict
    return JSONResponse(get_verdict(from_ts=from_ts, to_ts=to_ts))


@app.get("/api/tokens/cache-by-agent")
async def api_tokens_cache_by_agent(from_ts: int = 0, to_ts: int = 0):
    """Per-agent cache hit rate — surfaces agents with 0% cache."""
    from observeco.tracking.token_analytics import get_cache_by_agent
    return JSONResponse(get_cache_by_agent(from_ts=from_ts, to_ts=to_ts))


@app.get("/api/tokens/agents")
async def api_tokens_agents():
    """Distinct agent names from token_logs for the Token Analytics dropdown."""
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()
    rows = conn.execute("SELECT DISTINCT agent_name FROM token_logs ORDER BY agent_name").fetchall()
    return {"agents": [r["agent_name"] for r in rows]}


@app.get("/api/tokens/providers")
async def api_tokens_providers():
    """Distinct provider names from token_logs for the Token Analytics dropdown."""
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()
    rows = conn.execute("SELECT DISTINCT provider FROM token_logs WHERE provider != '' ORDER BY provider").fetchall()
    return {"providers": [r["provider"] for r in rows]}


@app.get("/api/tokens/breakdown")
async def api_tokens_breakdown(
    dimension: str = "agent",
    from_ts: int = 0,
    to_ts: int = 0,
):
    """Token breakdown by dimension (agent/provider/workflow/service)."""
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row

    dim_col = {"agent": "agent_name", "provider": "provider", "workflow": "workflow_name", "service": "service_name"}
    col = dim_col.get(dimension, "agent_name")

    where = "WHERE 1=1"
    params: list = []
    if from_ts:
        where += " AND recorded_at >= ?"
        params.append(from_ts)
    if to_ts:
        where += " AND recorded_at <= ?"
        params.append(to_ts)

    rows = conn.execute(
        f"SELECT {col} as name, SUM(total_tokens) as total_tokens, SUM(input_tokens) as input, "
        f"SUM(output_tokens) as output, SUM(cache_creation_tokens) as cache_create, "
        f"SUM(cache_read_tokens) as cache_read, COUNT(*) as turn_count, "
        f"SUM(cost) as cost "
        f"FROM token_logs {where} GROUP BY {col} ORDER BY total_tokens DESC LIMIT 50",
        params,
    ).fetchall()

    data = []
    for r in rows:
        rd = dict(r)
        rd["avg_per_turn"] = round(rd["total_tokens"] / max(rd["turn_count"], 1))
        data.append(rd)
    return {"data": data, "dimension": dimension}


@app.get("/api/tokens/system-prompts")
async def api_tokens_system_prompts(
    from_ts: int = 0,
    to_ts: int = 0,
    limit: int = 20,
):
    """Top system prompts by token usage."""
    from observeco.tracking.token_analytics import get_system_prompts
    return JSONResponse(get_system_prompts(from_ts=from_ts, to_ts=to_ts, limit=limit))


@app.get("/api/compress-log")
async def api_compress_log(limit: int = 5):
    """Recent compression log entries."""
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute(
        "SELECT agent_name, mode, before_tokens, after_tokens, savings_pct, "
        "backup_path, triggered_by, timestamp "
        "FROM compress_log ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/migration-status")
async def api_migration_status():
    """Check if a schema migration failed and needs attention."""
    from observeco.db import get_migration_failure
    fail = get_migration_failure()
    if fail:
        return {
            "has_failure": True,
            "restored": fail.get("restored", False),
            "restored_from": fail.get("restored_from", ""),
            "error": fail.get("error", ""),
            "failed_at": fail.get("failed_at", 0),
        }
    return {"has_failure": False}


@app.get("/api/pipeline/health")
async def api_pipeline_health():
    """Data quality tier and pipeline health for the Data Quality bar."""
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()

    # Determine data quality tier
    otel_count = conn.execute(
        "SELECT COUNT(*) as c FROM token_logs WHERE source='otel'"
    ).fetchone()["c"]
    sdk_count = conn.execute(
        "SELECT COUNT(*) as c FROM token_logs WHERE source='sdk' OR source='proxy'"
    ).fetchone()["c"]
    watch_count = conn.execute(
        "SELECT COUNT(*) as c FROM token_logs WHERE source='watch'"
    ).fetchone()["c"]

    if sdk_count > 0:
        tier = "full"
    elif otel_count > 0:
        tier = "accurate"
    else:
        tier = "estimated"

    # Check if OTEL data is stale (> 1 hour since last OTEL record)
    otel_stale = False
    if otel_count > 0:
        last_otel = conn.execute(
            "SELECT MAX(recorded_at) as ts FROM token_logs WHERE source='otel'"
        ).fetchone()
        if last_otel and last_otel["ts"]:
            otel_stale = (int(__import__("time").time()) - last_otel["ts"]) > 3600

    return {
        "tier": tier,
        "otel_stale": otel_stale,
        "sources": {
            "otel": otel_count,
            "sdk": sdk_count,
            "watch": watch_count,
        },
        "upgrade_path": "Add the OTEL SDK to your agents for accurate per-call data"
            if tier == "estimated" else
            "Add the ObserveCo SDK for full per-call breakdown"
            if tier == "accurate" else "",
    }


@app.post("/api/config-hygiene/fix")
async def api_config_hygiene_fix(request: Request):
    """Apply auto-fixable config hygiene findings. Accepts {check: "check_name"|"all"}."""
    try:
        body = await request.json()
        check = body.get("check", "all")
        from observeco.chisel.config_scanner import apply_fix, scan_config
        report = scan_config()
        if check == "all":
            targets = [f for f in report.findings if f.auto_fixable]
        else:
            targets = [f for f in report.findings if f.check == check and f.auto_fixable]
        fixed, failed = [], []
        for f in targets:
            try:
                if apply_fix(f):
                    fixed.append(f.check)
                else:
                    failed.append(f.check)
            except Exception:
                failed.append(f.check)
        return JSONResponse({"fixed": fixed, "failed": failed})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chisel/compress-skill")
async def api_chisel_compress_skill(request: Request):
    """Compress one or more skills by name. Accepts {skills: [name, ...], mode, provider}."""
    try:
        body = await request.json()
        skill_names = body.get("skills", [])
        mode = body.get("mode", "lite")
        provider = body.get("provider", "auto")
        if not skill_names:
            return JSONResponse({"status": "error", "message": "No skills specified"}, status_code=400)
        import json as _json

        from observeco.chisel.skill_compress import (
            _skills_dir,
            compress_skill_to_artifacts,
            generate_cards_json,
        )
        from observeco.db import Database
        from observeco.tracking.tokens import _estimate_cost
        sd = _skills_dir()
        if sd is None:
            return JSONResponse({"status": "error", "message": "Skills directory not found"}, status_code=500)
        engine = "caveman" if mode == "full" else "rule"
        details = []
        _db = Database()
        for name in skill_names:
            # Skills live in nested dirs: category/skill-name/SKILL.md
            # cards.json names may differ from directory names (e.g. "Hermes Cron Debugging" vs "hermes-cron-debugging")
            slug = name.lower().replace(" ", "-").replace("_", "-")
            skill_paths = list(sd.rglob(f"{slug}/SKILL.md"))
            if not skill_paths:
                skill_paths = list(sd.glob(f"*/{slug}/SKILL.md"))
            if not skill_paths:
                details.append({"name": name, "status": "error", "message": "SKILL.md not found"})
                continue
            skill_path = skill_paths[0]
            manifest = compress_skill_to_artifacts(skill_path, dry_run=False, engine=engine, provider=provider, apply=True)
            if manifest is None:
                details.append({"name": name, "status": "skip", "message": "Already compressed or no savings"})
            else:
                saved = manifest.get("savings_tokens", 0)
                pct = manifest.get("savings_pct", 0)
                details.append({
                    "name": name, "status": "ok",
                    "saved_tokens": saved, "savings_pct": pct,
                    "before_tokens": manifest.get("pre_compress_tokens", manifest.get("original_tokens", 0)),
                    "after_tokens": manifest.get("compressed_tokens", 0),
                    "applied": True,
                })
                # Log to compress_log
                try:
                    _db._write(
                        "INSERT INTO compress_log (agent_name, mode, before_tokens, after_tokens, "
                        "savings, savings_pct, file_path, backup_path, triggered_by, timestamp) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (name, mode,
                         manifest.get("pre_compress_tokens", manifest.get("original_tokens", 0)),
                         manifest.get("compressed_tokens", 0),
                         saved, pct,
                         str(skill_path),
                         str(skill_path.with_suffix(".md.bak")),
                         "dashboard", int(time.time())),
                    )
                except _sqlite3.OperationalError:
                    pass  # fire-and-forget
                # Log to action_log
                try:
                    _db.log_action(
                        agent_name=name,
                        action_type="skill_compress",
                        action_detail=f"{name} — compressed {manifest.get('pre_compress_tokens', 0):,} → {manifest.get('compressed_tokens', 0):,} tok ({pct:.0f}%)",
                        tokens_saved=saved,
                        cost_saved=_estimate_cost(saved),
                        status="success",
                        metadata=_json.dumps({"mode": mode, "engine": engine, "applied": True}),
                        triggered_by="dashboard",
                    )
                except Exception:
                    pass  # fire-and-forget

        # Regenerate cards.json so dashboard reads correct token counts
        try:
            cards_json = generate_cards_json()
            (sd / "cards.json").write_text(cards_json)
        except Exception:
            pass  # non-critical

        return JSONResponse({"status": "ok", "details": details})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/chisel/revert-skill")
async def api_chisel_revert_skill(request: Request):
    """Revert a compressed skill back to its original content from .bak file."""
    try:
        body = await request.json()
        skill_names = body.get("skills", [])
        if not skill_names:
            return JSONResponse({"status": "error", "message": "No skills specified"}, status_code=400)
        import json as _json

        from observeco.chisel.skill_compress import (
            _atomic_write,
            _count_tokens,
            _skills_dir,
            _text_hash,
            generate_cards_json,
        )
        from observeco.db import Database
        sd = _skills_dir()
        if sd is None:
            return JSONResponse({"status": "error", "message": "Skills directory not found"}, status_code=500)
        details = []
        _db = Database()
        for name in skill_names:
            skill_paths = list(sd.rglob(f"{name}/SKILL.md"))
            if not skill_paths:
                details.append({"name": name, "status": "error", "message": "SKILL.md not found"})
                continue
            skill_path = skill_paths[0]
            bak_path = skill_path.with_suffix(".md.bak")
            if not bak_path.exists():
                details.append({"name": name, "status": "error", "message": "No backup file found (.md.bak)"})
                continue
            try:
                original_text = bak_path.read_text(encoding="utf-8")
                # Overwrite SKILL.md with original content
                _atomic_write(skill_path, original_text)
                # Delete .bak
                bak_path.unlink()
                # Update manifest
                manifest_path = skill_path.with_suffix(".md.manifest")
                if manifest_path.exists():
                    try:
                        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                        manifest["reverted_at"] = int(time.time())
                        manifest["original_hash"] = _text_hash(original_text)
                        manifest["original_tokens"] = _count_tokens(original_text)
                        _atomic_write(manifest_path, json.dumps(manifest, indent=2))
                    except Exception:
                        pass
                # Update card
                card_path = skill_path.with_suffix(".md.card")
                if card_path.exists():
                    try:
                        card = json.loads(card_path.read_text(encoding="utf-8"))
                        card["total_tokens"] = _count_tokens(original_text)
                        _atomic_write(card_path, json.dumps(card))
                    except Exception:
                        pass
                # Log revert
                try:
                    _db.log_action(
                        agent_name=name,
                        action_type="skill_revert",
                        action_detail=f"{name} — reverted to original ({_count_tokens(original_text):,} tok)",
                        tokens_saved=0,
                        cost_saved=0,
                        status="success",
                        metadata=_json.dumps({"action": "revert"}),
                        triggered_by="dashboard",
                    )
                except Exception:
                    pass
                details.append({
                    "name": name, "status": "ok",
                    "tokens": _count_tokens(original_text),
                })
            except Exception as e:
                details.append({"name": name, "status": "error", "message": str(e)})

        # Regenerate cards.json
        try:
            cards_json = generate_cards_json()
            (sd / "cards.json").write_text(cards_json)
        except Exception:
            pass

        return JSONResponse({"status": "ok", "details": details})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── Optimiser Endpoints ───────────────────────────────────────────────────────


@app.get("/api/optimiser/stats")
async def api_optimiser_stats(agent: str = "all"):
    """Return optimiser stats: learning progress, skill usage, guidance fires."""
    conn = db._get_conn()
    conn.row_factory = __import__("sqlite3").Row

    if agent == "all" or not agent:
        # Fleet-wide stats
        turn_count = conn.execute("SELECT COUNT(*) as c FROM turn_log").fetchone()["c"]
        skill_rows = conn.execute(
            "SELECT agent_name, skill_name, triggered, turn_count FROM skill_usage ORDER BY turn_count DESC LIMIT 20"
        ).fetchall()
        guidance_rows = conn.execute(
            "SELECT agent_name, rule_text, fire_count FROM guidance_fire ORDER BY fire_count DESC LIMIT 20"
        ).fetchall()
        compress_rows = conn.execute(
            "SELECT agent_name, mode, savings_pct FROM compress_log ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
    else:
        turn_count = conn.execute(
            "SELECT COUNT(*) as c FROM turn_log WHERE agent_name=?", (agent,)
        ).fetchone()["c"]
        skill_rows = conn.execute(
            "SELECT skill_name, triggered, turn_count FROM skill_usage WHERE agent_name=? ORDER BY turn_count DESC LIMIT 20",
            (agent,),
        ).fetchall()
        guidance_rows = conn.execute(
            "SELECT rule_text, fire_count FROM guidance_fire WHERE agent_name=? ORDER BY fire_count DESC LIMIT 20",
            (agent,),
        ).fetchall()
        compress_rows = conn.execute(
            "SELECT mode, savings_pct FROM compress_log WHERE agent_name=? ORDER BY timestamp DESC LIMIT 10",
            (agent,),
        ).fetchall()

    skills_never = [dict(s) for s in skill_rows if s["triggered"] == 0]
    guidance_zero = [dict(g) for g in guidance_rows if g["fire_count"] == 0]
    guidance_active = [dict(g) for g in guidance_rows if g["fire_count"] > 0]

    # Compute actual savings from compress_log — only over rows that achieved
    # real savings (savings_pct > 0). Zero/negative rows are no-op compressions
    # (dry-runs, already-compressed files) and would flatten the signal.
    # ponytail: no hardcoded fallback (was 22/35 +21/+12). If no real compression
    # has saved tokens, lite/full stay None and the card shows "—" instead of a
    # fabricated 43-47%. The optimiser projection reflects what compression has
    # actually delivered (real lite→full range), not a placeholder estimate.
    # A true per-agent optimiser projection needs real pruning data — out of scope.
    lite_avg = conn.execute(
        "SELECT AVG(savings_pct) as avg_pct FROM compress_log WHERE mode='lite' AND savings_pct > 0"
    ).fetchone()
    full_avg = conn.execute(
        "SELECT AVG(savings_pct) as avg_pct FROM compress_log WHERE mode='full' AND savings_pct > 0"
    ).fetchone()
    lite_savings = round(lite_avg["avg_pct"], 1) if lite_avg and lite_avg["avg_pct"] is not None else None
    full_savings = round(full_avg["avg_pct"], 1) if full_avg and full_avg["avg_pct"] is not None else None
    opt_min = None
    opt_max = None
    if lite_savings is not None or full_savings is not None:
        opt_min = lite_savings if lite_savings is not None else full_savings
        opt_max = full_savings if full_savings is not None else lite_savings

    return JSONResponse({
        "agent": agent,
        "total_turns": turn_count,
        "goal_turns": 200,
        "learning_pct": round(min(100, turn_count / 200 * 100), 1) if turn_count < 200 else 100,
        "skills_never_triggered": len(skills_never),
        "skills_total": len(skill_rows),
        "skills_never": skills_never[:5],
        "guidance_rules_stale": len(guidance_zero),
        "guidance_rules_total": len(guidance_rows),
        "guidance_stale": guidance_zero[:5],
        "guidance_active": guidance_active[:5],
        "recent_compressions": [dict(c) for c in compress_rows],
        "savings": {
            "lite": lite_savings,
            "full": full_savings,
            "optimiser_min": opt_min,
            "optimiser_max": opt_max,
        },
    })


# ── Code Graph Panel ─────────────────────────────────────────────────────────

@app.get("/api/graph/overview", response_class=HTMLResponse)
async def api_graph_overview():
    """Code graph overview panel — stats + quick search."""
    from observeco.graph.db import GraphDB
    gdb = GraphDB()
    stats = gdb.get_stats()
    return HTMLResponse(f"""<div class="graph-overview">
    <div class="graph-stats-grid">
        <div class="graph-stat-card">
            <span class="graph-stat-num symbols">{stats.get('nodes', 0)}</span>
            <span class="graph-stat-label">Symbols</span>
        </div>
        <div class="graph-stat-card">
            <span class="graph-stat-num relations">{stats.get('edges', 0)}</span>
            <span class="graph-stat-label">Relations</span>
        </div>
        <div class="graph-stat-card">
            <span class="graph-stat-num files">{stats.get('files', 0)}</span>
            <span class="graph-stat-label">Files Indexed</span>
        </div>
    </div>
    <div class="graph-search-row">
        <input id="graph-search-input" placeholder="Search symbols..." class="graph-search-input"
               onkeyup="if(event.key==='Enter') searchGraph()" />
        <button onclick="searchGraph()" class="graph-search-btn">Search</button>
    </div>
    <div id="graph-results" class="graph-results"></div>
    <script>
        function searchGraph() {{
            var q = document.getElementById('graph-search-input').value.trim();
            if (!q) return;
            fetch('/api/graph/search?q=' + encodeURIComponent(q))
                .then(r => r.text())
                .then(html => document.getElementById('graph-results').innerHTML = html);
        }}
    </script>
</div>""")


@app.get("/api/graph/search", response_class=HTMLResponse)
async def api_graph_search(q: str = "", limit: int = 10):
    """Search the code graph."""
    if not q:
        return HTMLResponse('<div class="graph-results-empty">Enter a search term</div>')
    from observeco.graph.db import GraphDB
    gdb = GraphDB()
    results = gdb.search_nodes(q, limit=limit)
    if not results:
        return HTMLResponse('<div class="graph-results-empty">No results</div>')
    items = []
    for r in results:
        kind = r["kind"]
        icon = {"function": "\u0192", "method": "\u0192", "class": "\u00a7", "import": "\u21e2", "variable": "\u2205"}.get(kind, "\u00b7")
        color = {"function": "#22c55e", "method": "#22c55e", "class": "#38bdf8",
                 "import": "#a78bfa", "variable": "#f59e0b"}.get(kind, "#94a3b8")
        items.append(f"""<div class="graph-result"
     onclick="toggleGraphDetail('{r['qualified_name']}')">
    <span class="graph-result-icon" style="color:{color};">{icon}</span>
    <span class="graph-result-name">{r['qualified_name']}</span>
    <span class="graph-result-loc">{r.get('file_path','').split('/')[-1]}:{r.get('start_line','')}</span>
</div>""")
    return HTMLResponse("".join(items))


@app.get("/api/graph/symbol", response_class=HTMLResponse)
async def api_graph_symbol(name: str = ""):
    """Show callers and callees for a symbol."""
    if not name:
        return HTMLResponse('')
    from observeco.graph.db import GraphDB
    gdb = GraphDB()
    node = gdb.get_node_by_qualified_name(name)
    if not node:
        return HTMLResponse(f'<div class="graph-symbol-not-found">Symbol not found: {name}</div>')

    callers = gdb.get_callers(node["id"])
    callees = gdb.get_callees(node["id"])
    arr_left = "\u2190"
    arr_right = "\u2192"

    html = f"""<div class="graph-symbol-detail">
    <div class="graph-symbol-header">
        <span class="graph-symbol-name">{name}</span>
        <span class="graph-symbol-file">{node['file_path'].split('/')[-1]}:{node['start_line']}</span>
    </div>
    <div class="graph-symbol-grid">
        <div>
            <div class="graph-symbol-section-title">Called by ({len(callers)})</div>
            {''.join(f'<div class="graph-symbol-item caller">{arr_left} {c["qualified_name"]} [{c["file_path"].split("/")[-1]}:{c["start_line"]}]</div>' for c in callers) if callers else '<div class="graph-symbol-none">No callers</div>'}
        </div>
        <div>
            <div class="graph-symbol-section-title">Calls ({len(callees)})</div>
            {''.join(f'<div class="graph-symbol-item callee">{arr_right} {c["qualified_name"]} [{c["file_path"].split("/")[-1]}:{c["start_line"]}]</div>' for c in callees) if callees else '<div class="graph-symbol-none">No callees</div>'}
        </div>
    </div>
</div>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# §3.20 — Glossary & FAQ Panel
# ---------------------------------------------------------------------------

GLOSSARY_DATA = {
    "status-dot": {
        "title": "Status Dot",
        "icon": "🟢",
        "one_liner": "Shows if an agent is running, down, or in warning state.",
        "detail": """<div class="glossary-card-grid">
    <div class="glossary-card"><div class="glossary-card-icon">🟢</div><div class="glossary-card-title" style="color:#22c55e;">Running</div><div class="glossary-card-body">Responded to last pulse check within expected interval. Typically checked every 30s.</div></div>
    <div class="glossary-card"><div class="glossary-card-icon">🔴</div><div class="glossary-card-title" style="color:#ef4444;">Down</div><div class="glossary-card-body">Process not found, health endpoint timeout, or no response after N retries. Was previously running.</div></div>
    <div class="glossary-card"><div class="glossary-card-icon">🟡</div><div class="glossary-card-title" style="color:#f59e0b;">Warning</div><div class="glossary-card-body">Agent is reachable but returning errors (e.g. HTTP 5xx, process exit code != 0). Needs investigation.</div></div>
    <div class="glossary-card"><div class="glossary-card-icon">⚪</div><div class="glossary-card-title" style="color:#64748b;">Not running</div><div class="glossary-card-body">Registered in config but never seen alive. Likely configured but not started yet.</div></div>
    <div class="glossary-card"><div class="glossary-card-icon">⚪</div><div class="glossary-card-title" style="color:#64748b;">Unknown</div><div class="glossary-card-body">No pulse data yet. Agent was registered but never checked. Run <code>observeco pulse check</code> to start.</div></div>
</div>""",
        "faq": [
            ("Why is my agent showing Warning but circuit OK?", "The agent is running but returning errors (e.g. HTTP 500). The circuit breaker only trips after N consecutive failures — yellow means it's failing but hasn't reached the threshold yet. Check the Error timeline for details."),
            ("What do I do when the dot turns red?", "Run `observeco heal --agent <name>` to auto-diagnose. Common causes: process crashed, port changed, config file moved. The heal command checks process existence, port availability, and config path."),
            ("How often are agents checked?", "Every 30 seconds by default. Configure with `observeco watch --interval <seconds>`."),
        ],
    },
    "circuit": {
        "title": "Circuit Breaker",
        "icon": "⚡",
        "one_liner": "A safety guard that stops checking down agents after enough failures.",
        "detail": """<div class="glossary-detail">
    <strong>How it works:</strong> After 3 consecutive failures, the circuit breaker trips and enters cooldown (5 minutes by default). During cooldown, the agent is not checked. After cooldown expires, it tries again automatically.<br><br>
    <strong>What it saves:</strong> Without this guard, a single down agent would generate 2,880 error checks per day. With it, you see ~8. That's a <strong style="color:#22c55e;">99.7% reduction</strong> in log noise.
</div>""",
        "faq": [
            ("How do I reset a tripped circuit?", "Click the Guard metric row on the agent card, then click 'Reset Circuit'. Or run `observeco pulse circuit --reset <agent_name>`."),
            ("Can I change the failure threshold?", "Yes: `observeco pulse circuit --threshold <agent>:<n>`. Default is 3 failures before trip."),
        ],
    },
    "token-bar": {
        "title": "Token Bar",
        "icon": "📊",
        "one_liner": "Breaks down your system prompt into components, showing each one's token usage.",
        "detail": """<div class="glossary-card-grid">
    <div style="background:#0f172a;padding:8px;border-radius:6px;"><div style="font-size:12px;color:#6366f1;font-weight:600;">Identity</div><div style="font-size:11px;color:#64748b;">Agent's role, personality, and behavioral contract. Usually stable.</div></div>
    <div class="glossary-comp-card"><div class="glossary-comp-title" style="color:#8b5cf6;">Skills</div><div class="glossary-comp-body">Instructions for tools and capabilities. Grows as skills are added.</div></div>
    <div class="glossary-comp-card"><div class="glossary-comp-title" style="color:#ec4899;">Memory</div><div class="glossary-comp-body">Conversation history, learned patterns. The most dynamic component.</div></div>
    <div class="glossary-comp-card"><div class="glossary-comp-title" style="color:#14b8a6;">Tools</div><div class="glossary-comp-body">API descriptions, function schemas. Grows with tool count.</div></div>
    <div class="glossary-comp-card"><div class="glossary-comp-title" style="color:#f97316;">Guidance</div><div class="glossary-comp-body">Framework instructions, routing rules. Often the largest component.</div></div>
</div>""",
        "faq": [
            ("Why is Guidance always the biggest?", "Because it includes framework-level instructions (routing rules, tool dispatch logic). This is normal. Run `observeco context trim` to see compression opportunities."),
            ("What should I do if tokens keep growing?", "Run `observeco chisel skills` to find bloated skills. Skills are the most common source of token bloat. Each skill description is loaded into every session."),
        ],
    },
    "drift": {
        "title": "Drift",
        "icon": "📈",
        "one_liner": "Shows how much your prompt size changed over 7 days.",
        "detail": """<div class="glossary-detail">
    <strong>Drift +10%</strong> means the system prompt is 10% larger than it was 7 days ago. Common causes: memory accumulation, skill additions, tool descriptions growing.<br><br>
    <strong>When to act:</strong> Drift >20% triggers a warning. Run <code>observeco chisel trim</code> to see exact token breakdown and find what's growing.
</div>""",
        "faq": [
            ("What causes positive drift?", "Most commonly: agent memory accumulation (every conversation adds context), new skills being added, or tool descriptions growing. Check the component breakdown to identify the source."),
            ("Is drift always bad?", "Not necessarily. Controlled growth from adding genuine capabilities is expected. Runaway drift (30%+ in a week) indicates memory bloat or skill sprawl."),
        ],
    },
    "error-badge": {
        "title": "Error Badge",
        "icon": "⚠️",
        "one_liner": "Shows how many errors an agent had in the last 24 hours.",
        "detail": """<div class="glossary-detail">
    Badges appear in two colors:<br>
    <strong style="color:#ef4444;">🔴 Red badge</strong> — Agent is Down or Warning state with recent errors. Act now.<br>
    <strong style="color:#f59e0b;">🟡 Yellow badge</strong> — Agent has errors but is still responding. Check when you can.<br><br>
    Click the metric row to see full error details.
</div>""",
        "faq": [
            ("Why does an agent have errors but is still alive?", "The agent process is running but returning error responses (e.g. HTTP 500, Python traceback). The pulse check got a response — it just wasn't a healthy one."),
            ("What's the difference between error badge and status dot?", "The status dot reflects the <em>latest</em> pulse. The error badge shows <em>cumulative</em> errors in 24h. An agent can be alive but have errors."),
        ],
    },
    "error-tab": {
        "title": "Error History (24h window)",
        "icon": "⚠️",
        "one_liner": "Only the last 24 hours of errors are shown. Earlier errors are pruned.",
        "detail": """<div class="glossary-detail">
    <strong>This view shows the most recent 24 hours of errors only.</strong><br><br>
    <strong>⚠️ Important:</strong> These errors may already be <strong>fixed or outdated</strong>. The agent's latest pulse may show it as healthy right now, while past errors from earlier in the window still appear here. A non-empty error list <strong>does not</strong> mean the agent is currently broken — it means errors occurred at some point in the last 24 hours.<br><br>
    <strong>How to interpret:</strong><br>
    • Check the <strong>timestamps</strong> — if the most recent error is hours old and the status dot is green, the agent has recovered on its own.<br>
    • Look at the <strong>frequency</strong> — many errors close together suggest an ongoing issue. A single old error is likely transient.<br>
    • Cross-reference with the <strong>Health timeline</strong> to see whether the agent is currently alive or dead.
</div>""",
        "faq": [
            ("Why do I see errors but the agent is running fine?", "Because errors are shown for the last 24 hours. If the agent had a hiccup 12 hours ago and has been clean since, you'll still see that error until it falls out of the 24h window. The status dot reflects the <em>current</em> state."),
            ("How far back do errors go?", "24 hours max. Errors older than 24h are pruned automatically."),
            ("Can I see if an error is getting worse?", "The error list shows raw events. Check the Health timeline to see if the same error is happening more or less often."),
        ],
    },
    "pulse-check": {
        "title": "Pulse Check",
        "icon": "💓",
        "one_liner": "A health check that tests each agent every 30 seconds.",
        "detail": """<div class="glossary-detail">
    <strong>How it works:</strong> Pulse check sends a request to the agent or checks if its process exists. Results are stored and shown on the dashboard.<br><br>
    <strong>Three outcomes:</strong><br>
    🟢 <strong style="color:#22c55e;">Running</strong> — Health check passed or process found<br>
    🔴 <strong style="color:#ef4444;">Down</strong> — No response or process not found<br>
    🟡 <strong style="color:#f59e0b;">Warning</strong> — Reached but returned an error<br><br>
    Run <code>observeco pulse check</code> to see current status for all agents.
</div>""",
        "faq": [
("Do I need to set up health endpoints for every agent?", "No. ObserveCo auto-detects agents from config files (Hermes, OpenClaw, and others). For custom agents, use `observeco agents add <name> --health-check <url_or_command>` to register manually. Docker containers: `observeco agents add <name> --health-check docker:containername`."),
            ("What happens if pulse.db doesn't exist?", "First run creates it automatically. The dashboard shows a phase banner guiding you through the first discovery."),
        ],
    },
    "heal-button": {
        "title": "Heal Button",
        "icon": "🔧",
        "one_liner": "Automatically fixes down agents, tripped circuits, and bloated prompts.",
        "detail": """<div class="glossary-detail">
    <strong>What it checks:</strong><br>
    • <strong>Process</strong> — Is it running?<br>
    • <strong>Port</strong> — Is the configured port open?<br>
    • <strong>Config</strong> — Does the config file still exist?<br>
    • <strong>Circuit</strong> — Is the breaker tripped? Should it reset?<br><br>
    <strong>Auto-heal:</strong> Runs on a schedule via the watch daemon. Manual trigger available from the Fleet view.
</div>""",
        "faq": [
            ("What does the heal command actually do?", "Run `observeco heal --agent <name>` to see a diagnostic report. Use `--auto-heal` to execute fixes. The command explains what it found and what it fixed."),
            ("Is auto-heal dangerous?", "No. It only executes fixes that are reversible (restart process, reset circuit, clean memory). It won't delete configs or remove agents."),
        ],
    },
    "alerts-panel": {
        "title": "Alerts Panel",
        "icon": "⚠️",
        "one_liner": "A list of important events sorted by severity.",
        "detail": """<div class="glossary-detail">
    Three severity levels:<br>
    🔴 <strong style="color:#ef4444;">Critical</strong> — Breaker tripped, agent dead. Do something.<br>
    🟡 <strong style="color:#f59e0b;">Warning</strong> — Drift >10%, error state happening. Keep an eye on it.<br>
    🔵 <strong style="color:#3b82f6;">Info</strong> — Unusual patterns. Look when you have time.<br><br>
    Alerts are visible in the dashboard right rail. Configure push notifications via Telegram, Discord, or webhook from the Alerts tab.
</div>""",
        "faq": [
            ("How far back do alerts go?", "7 days. Alerts older than 7 days are pruned automatically."),
            ("Can I get alerts on Telegram?", "Yes — configure it from the Alerts tab. Supports Telegram, Discord, and webhook delivery."),
        ],
    },
    "confidence": {
        "title": "Confidence Score",
        "icon": "🎯",
        "one_liner": "How reliable the status is — from fresh evidence to stale guess.",
        "detail": """<div class="glossary-detail">
    <strong>4 factors that affect confidence:</strong><br><br>
    <strong>⏱ Time</strong> — How long the agent has been in its current state. >2h = strong.<br>
    <strong>🔢 Agreement</strong> — How many pulse checks in a row say the same thing. >3 = strong.<br>
    <strong>🤝 Sources</strong> — Do pulse status, error count, and circuit breaker all agree?<br>
    <strong>📊 Consistency</strong> — Are errors consistent (same cause) or varied (different issues)?<br><br>
    <strong>Score levels:</strong><br>
    🟢 <strong style="color:#22c55e;">High</strong> (5-6) — Reliable. Act on it.<br>
    🟡 <strong style="color:#eab308;">Medium</strong> (3-4) — Plausible but weak. Worth a look.<br>
    ⚪ <strong style="color:#64748b;">Low</strong> (0-2) — Not enough data yet. Wait.
</div>""",
        "faq": [
            ("How is confidence different from status?", "Status tells you WHAT the state is (alive/dead/error). Confidence tells you HOW RELIABLE that assessment is. An agent dead for 4 days has High confidence. An agent checked once 5s ago has Low confidence."),
            ("What makes confidence drop?", "Sparse pulse data, contradictory sources (pulse says alive but errors exist), or very recent status changes (<2h)."),
        ],
    },
    "fp": {
        "title": "False Positive (FP) Risk",
        "icon": "⚠️",
        "one_liner": "How likely a red flag is actually a false alarm.",
        "detail": """<div class="glossary-detail">
    <strong>FP risk = "crying wolf" — the dashboard says there's a problem but there isn't.</strong><br><br>
    🟢 <strong style="color:#22c55e;">Low FP</strong> — Multiple sources confirmed the problem over hours. It's real.<br>
    🟡 <strong style="color:#eab308;">Moderate FP</strong> — Some evidence but not enough time. Don't panic yet.<br>
    🔴 <strong style="color:#ef4444;">High FP</strong> — Single check, recent event. Could be a glitch. Verify first.<br><br>
    <strong>What makes FP less likely:</strong> Long duration (>2h), many checks agreeing, same error repeating (not random).
</div>""",
        "faq": [
            ("Why does a dead agent have Low FP risk?", "If an agent has been dead for 4 days with 48 consecutive dead checks, the odds of a false alarm are extremely low. The system is genuinely down."),
        ],
    },
    "fn": {
        "title": "False Negative (FN) Risk",
        "icon": "🔍",
        "one_liner": "How likely a green flag is missing a real problem.",
        "detail": """<div class="glossary-detail">
    <strong>FN risk = "blind spot" — the dashboard says all clear but something is broken.</strong><br><br>
    🟢 <strong style="color:#22c55e;">Low FN</strong> — Recent check confirmed the agent is healthy. Confident.<br>
    🟡 <strong style="color:#eab308;">Moderate FN</strong> — Agent is alive but only a few checks ran. Could miss something.<br>
    🔴 <strong style="color:#ef4444;">High FN</strong> — Last check was >1h ago. The agent could have died since.<br><br>
    <strong>"Green" does not mean "guaranteed."</strong> A 🟢 label just means the agent responded to its last check — not that it's still running right now.
</div>""",
        "faq": [
            ("Why does an alive agent with no recent pulses have High FN?", "Because the last known-good check was too long ago. The agent may have crashed since then. The system is giving you the benefit of the doubt but can't confirm current health."),
            ("What's the difference between FP and FN?", "FP = the dashboard says something is wrong when it's not. FN = the dashboard says everything is fine when it's not. They're opposite sides of the same accuracy question."),
        ],
    },
    "heal-savings-l1": {
        "title": "L1 Auto-Heal Savings",
        "icon": "🛡️",
        "one_liner": "How the $0.02 per-event savings is calculated.",
        "detail": """<div class="glossary-detail">
    <strong>Assumptions (per event):</strong><br>
    • <strong>Downtime cost:</strong> $0.02/min × average 2h manual recovery = $2.40<br>
    • <strong>L1 recovery:</strong> Auto-restart in ~1 min × $0.02/min = $0.02 cost<br>
    • <strong>Savings:</strong> $2.40 − $0.02 = <strong style="color:#22c55e;">$0.02 saved / event</strong> (per-event, not cumulative)<br><br>
    <strong>What this means:</strong> The $0.02 is a conservative estimate per single agent-down event. Real savings vary by fleet size, agent criticality, and how fast you manually recover.<br><br>
    <strong>How to calculate your own:</strong><br>
    <code>your_savings = (manual_recovery_time − auto_recovery_time) × cost_per_minute</code><br><br>
    <span style="color:#64748b;">These are estimates based on typical agent recovery costs. Your fleet may save more or less.</span>
</div>""",
        "faq": [
            ("Is $0.02 per event realistic?", "It assumes a $0.02/min downtime cost (roughly $1.20/hour). This is a conservative baseline — senior engineer time at $150/hr would make the number much higher. Adjust based on your team's hourly rate."),
            ("Where does $0.02/min come from?", "Roughly the cost of idle compute (e.g. a Docker container with CPU load) plus your time to SSH and restart. For larger fleets, per-event savings scale linearly."),
            ("Is this per-agent or per-fleet?", "Per event, per agent. If you have 10 agents and 2 go down daily, that's 2 events/day × $0.02 = $0.04/day savings from L1 alone."),
        ],
    },
    "skills-audit": {
        "title": "Skill Audit",
        "icon": "🧩",
        "one_liner": "Analyzes every skill your agents have loaded — ranked by token cost so you can find bloat.",
        "detail": """<div class="glossary-detail">
    <strong>What it shows:</strong> Every skill installed across your agents, sorted from most expensive (most tokens) to cheapest.<br><br>
    <strong style="color:#22c55e;">🟢 Skills ≤10K tokens</strong> — Normal size. No action needed.<br>
    <strong style="color:#ef4444;">⛔ Skills >10K tokens</strong> — Bloated. Each one adds cost to every agent session.<br><br>
    <strong>How token cost works:</strong> A skill's token count is added to the agent's system prompt on <em>every single turn</em>. A 15K-token skill means 15,000 tokens burned per session, every session. Over 250 sessions/month, that's 3.75M tokens just for one skill.<br><br>
    <strong>What to do with bloated skills:</strong> Skills >10K tokens are candidates for compression (see Compression). Skills >20K tokens should be reviewed for removal or rewrite.<br><br>
    <strong>By Category section:</strong> Groups skills by domain (devops, communication, etc.) so you can see which categories are costing you the most.
</div>""",
        "faq": [
            ("Why does token count matter?", "Every token in your skills section is paid for on every AI call. If a skill has 15K tokens and your agent makes 250 calls/month, that skill alone costs ~$0.56/month. Remove or compress it and you save that instantly."),
            ("What's a good token budget per skill?", "Aim for <5K tokens per skill. Skills between 5K–10K are acceptable but worth monitoring. Skills >10K should be compressed or split."),
            ("Does Skill Audit work across all agents?", "Yes. It scans skills from all profiles. You can filter to a single agent using the agent detail modal."),
        ],
    },
    "compression-lite": {
        "title": "Lite Compression",
        "icon": "✂️",
        "one_liner": "Compresses only the guidance section — the safest, lowest-risk compression mode.",
        "detail": """<div class="glossary-detail">
    <strong>What it compresses:</strong> Only the <strong style="color:#f97316;">guidance</strong> component — framework instructions, routing rules, do/don't lists.<br><br>
    <strong>What it preserves (unchanged):</strong><br>
    • <strong style="color:#6366f1;">Identity</strong> — Agent's role and personality (untouched)<br>
    • <strong style="color:#8b5cf6;">Skills</strong> — Tool descriptions (untouched)<br>
    • <strong style="color:#ec4899;">Memory</strong> — Conversation history (untouched)<br>
    • <strong style="color:#14b8a6;">Tools</strong> — API schemas (untouched)<br><br>
    <strong>When to use Lite:</strong> When you want safe, predictable savings without risk of breaking any functionality. Guidance is often the largest component (~40-60% of system prompt) so even compressing just this can save significantly.<br><br>
    <strong>Savings vary per agent:</strong> Actual compression % depends on guidance verbosity and composition. The result is logged after each run — no estimates, no guesswork.
</div>""",
        "faq": [
            ("Is Lite safe?", "Yes. It only compresses the guidance/rules section. Skills, memory, tools, and identity are completely untouched. Your agents will still have all their capabilities."),
            ("Why does guidance need compression?","Guidance sections contain framework-level instructions that are often verbose — redundant safety rules, repeated formatting instructions, defensive wording. Compression shortens these without losing meaning."),
        ],
    },
    "compression-full": {
        "title": "Full Compression",
        "icon": "🔬",
        "one_liner": "Compresses guidance + memory + skills for maximum savings.",
        "detail": """<div class="glossary-detail">
    <strong>What it compresses:</strong><br>
    • <strong style="color:#f97316;">Guidance</strong> — Framework instructions, routing rules, do/don't lists<br>
    • <strong style="color:#8b5cf6;">Skills</strong> — Skill descriptions and instructions<br>
    • <strong style="color:#ec4899;">Memory</strong> — Shortens recollection patterns<br><br>
    <strong>What it preserves (unchanged):</strong><br>
    • <strong style="color:#6366f1;">Identity</strong> — Never compressed<br>
    • <strong style="color:#14b8a6;">Tools</strong> — Never compressed (fragile)<br><br>
    <strong>Why it always saves more than Lite:</strong> Full does <em>everything Lite does</em> (compress guidance blocks) and adds skills + memory compression. The guidance part uses the same aggressive rate as Lite, so Full is always at least as good.
</div>""",
        "faq": [
            ("What's the risk of Full compression?","Skills and memory compression uses a gentler rate (40%) to avoid breaking functionality. The compression is structural — removing redundant wording, shortening verbose descriptions — not semantic. Your agents should behave identically after compression."),
        ],
    },
    "fleet-compare": {
        "title": "Fleet Comparison",
        "icon": "⚖️",
        "one_liner": "Side-by-side comparison of all your agents — see who's healthy, drifting, or costing too much.",
        "detail": """<div class="glossary-card-grid">
    <div class="glossary-card"><div class="glossary-card-title" style="color:#22c55e;">Composition Bars</div><div class="glossary-card-body">Colored bars showing each agent's token breakdown (identity, skills, memory, tools, guidance). Longer bars = more tokens = more cost.</div></div>
    <div class="glossary-card"><div class="glossary-card-title" style="color:#f59e0b;">Drift</div><div class="glossary-card-body">How much the system prompt has grown in the last 7 days. +5% is normal. +20%+ needs attention.</div></div>
    <div class="glossary-card"><div class="glossary-card-title" style="color:#ef4444;">Errors</div><div class="glossary-card-body">Error count in the last 24 hours. Updated on every pulse check.</div></div>
    <div class="glossary-card"><div class="glossary-card-title" style="color:#8b5cf6;">Circuit Status</div><div class="glossary-card-body">Whether the circuit breaker is tripped (not checking) or active (checking).</div></div>
    <div class="glossary-card"><div class="glossary-card-title" style="color:#64748b;">Last Seen</div><div class="glossary-card-body">When the agent last responded to a pulse check. Stale agents are candidates for cleanup.</div></div>
</div>""",
        "faq": [
            ("How do I sort the table?", "Click any column header to sort by that column. Click again to reverse order."),
            ("What should I focus on?","Look for: (1) High drift + high errors = something is wrong. (2) Tripped circuits across many agents = possible infrastructure issue. (3) Stale last-seen = dead agents to remove."),
        ],
    },
    "budget-planner": {
        "title": "Budget Planner",
        "icon": "💰",
        "one_liner": "Estimates how much your agents cost per month and what you'd save with compression.",
        "detail": """<div class="glossary-detail">
    <strong>How costs are calculated:</strong><br>
    • Based on <strong>250 sessions/month</strong> per agent (typical for active agents)<br>
    • Token pricing: <strong>DeepSeek V3 @ $0.15/M tokens</strong> (input tokens)<br>
    • Monthly burn = total tokens × 250 sessions × ($0.15 / 1,000,000)<br>
    • Yearly cost = monthly × 12<br><br>
    <strong>Lite savings:</strong> What you'd save by running Lite compression on all agents (guidance only). Conservative estimate.<br><br>
    <strong>Full savings:</strong> What you'd save by running Full compression (guidance + memory + skills). Always ≥ Lite.<br><br>
    <strong>Top spenders:</strong> Agents ranked by token count — the ones at the top are your biggest cost drivers.<br><br>
    <span style="color:#64748b;">These are estimates based on typical usage. Actual costs depend on session length, model choice, and call frequency.</span>
</div>""",
        "faq": [
            ("Is 250 sessions/month realistic?", "For most AI agents, yes — roughly 8-10 sessions per day. Heavy-use agents may hit 500+. Light-use agents may be <50. Adjust the estimate mentally based on your usage."),
            ("Can I see cost per agent?","The Top Spenders table shows each agent's token count and projected cost. Multiply by your own model's pricing for more accurate numbers."),
        ],
    },
    "drift-alerts": {
        "title": "Drift Alerts",
        "icon": "📈",
        "one_liner": "Checks every agent for abnormal prompt growth and fires a notification if found.",
        "detail": """<div class="glossary-detail">
    <strong>What it does:</strong> Scans all agents' drift data and flags any agent whose token composition has grown significantly. Within 1 hour, the same agent won't trigger again (dedup).<br><br>
    <strong>What triggers an alert:</strong><br>
    • Drift > <strong>+10%</strong> in the last 7 days = Warning<br>
    • Drift > <strong>+20%</strong> = Critical<br><br>
    <strong>What happens after:</strong> Alerts are delivered to all configured channels (Telegram, Discord, webhook, email). The alert message includes the agent name, drift %, and a link to investigate.<br><br>
    <strong>When to run it:</strong> Run once daily (or set up auto-check via cron). Frequent checks aren't useful because drift is measured over 7-day windows.
</div>""",
        "faq": [
            ("How often should I check drift?", "Once a day is plenty. Drift is measured over 7 days — checking more often will just see the same data."),
            ("Can drift alerts auto-fire?", "Yes — set up a cron job calling the check endpoint."),
        ],
    },
    "auto-heal": {
        "title": "Auto-Heal",
        "icon": "🛠️",
        "one_liner": "Auto-detects dead agents and restarts them — optional L2 layer fixes drift, memory bloat, and config issues proactively.",
        "detail": """<div class="glossary-detail">
    <strong>Two layers — both optional:</strong><br><br>
    <strong>L1 — Reactive (Auto-Restart):</strong> When pulse detects an agent is dead (process crashed, port closed), auto-heal restarts it. Max restarts per 4h prevents infinite loops. Default: 3.<br><br>
    <strong>L2 — Proactive (Drift + Memory):</strong> Checks for token composition changes (drift > threshold), memory debt accumulation, and config bloat. Triggers cleanup before it becomes a problem.<br><br>
    <strong>Per-agent configuration:</strong> Enable L1, L2, or both per agent. Thresholds control how aggressive each layer is — see Heal Thresholds glossary.<br><br>
    <strong>Requires:</strong> <code>observeco watch</code> daemon running in background.
</div>""",
        "faq": [
            ("Can I heal manually without the daemon?", "Yes. The 'Heal' button in Fleet View works independently. Auto-heal is just the automated version — it runs the same heal logic when the daemon detects a failure."),
            ("What happens if L1 and L2 both fire at once?", "L1 (restart) runs first. After the agent is back up, L2 runs its proactive checks. They don't conflict — restart happens, then cleanup happens after."),
            ("Does auto-heal work for every agent type?", "It works for any agent registered in the fleet (Hermes profiles, OpenClaw workspaces, custom). The heal logic checks process liveness and attempts restart — it doesn't need to know what kind of agent it is."),
        ],
    },
    "heal-thresholds": {
        "title": "Heal Thresholds",
        "icon": "⚙️",
        "one_liner": "Controls when auto-heal triggers for each agent — max restarts, drift % tolerance, and memory debt limit.",
        "detail": """<div class="glossary-detail">
    <strong>Three controls per agent:</strong><br><br>
    <strong>🔄 Max Restarts (per 4h)</strong> — How many times auto-heal will restart this agent in a 4-hour window. Default: 3. Prevents infinite restart loops. If an agent keeps crashing, it's better to stop trying and investigate.<br><br>
    <strong>📈 Max Drift %</strong> — How much token growth triggers a warning. Default: 20%. If the system prompt grows more than this in 7 days, auto-heal flags it. Set higher for agents you expect to grow (new skills being added).<br><br>
    <strong>🧠 Max Memory Debt</strong> — Maximum accumulated memory tokens before cleanup triggers. Default: 10,000. Agents that accumulate conversation history will eventually hit this limit and get a memory trim.<br><br>
    <strong>Pro tip:</strong> Raise max restarts for unstable but critical agents (they'll recover faster). Lower drift % for cost-sensitive agents.
</div>""",
        "faq": [
            ("What happens when max restarts is exceeded?", "The circuit breaker trips and stops auto-heal attempts for the cooldown period (default 5 minutes). The agent stays down until you manually intervene or the cooldown expires."),
            ("Should I set different thresholds per agent?", "Yes. A critical production agent might have max restarts=5 (more chances to recover). A development agent might have max restarts=1 (let it stay down so you notice)."),
            ("What is memory debt?","Memory debt is accumulated conversation history that gets stored in the agent's system prompt. Over time, this grows and increases cost. Auto-heal trims it when it exceeds the threshold."),
        ],
    },
    "token-optimiser": {
        "title": "Token Optimiser",
        "icon": "🧪",
        "one_liner": "Analyses 200+ turns of agent conversations to find which skills are never used — so you can prune them.",
        "detail": """<div class="glossary-detail">
    <strong>What it learns:</strong> The optimiser tracks which skills actually get triggered across 200+ real sessions. Any skill that never fires in 200 turns is a candidate for removal or compression.<br><br>
    <strong>What you get:</strong><br>
    • <strong>Skill usage table</strong> — Every skill ranked by how often it's triggered<br>
    • <strong>Never-triggered skills</strong> — Skills loaded but never called. Likely waste.<br>
    • <strong>Stale guidance rules</strong> — Instructions that never fire. Defensive wording that accumulated over time.<br><br>
    <strong>Why 200 turns?</strong> Below 200, the sample is too small to be statistically meaningful. A skill used once in 50 turns might be essential but rarely needed. At 200+, patterns stabilise.
</div>""",
        "faq": [
            ("How long does it take to reach 200 turns?","Depends on agent activity. A busy agent might hit 200 turns in 2-3 days. A seldom-used agent might take weeks. The optimiser shows your progress toward 200."),
            ("What happens if I remove a skill that was never triggered?","Nothing — that's the point. The skill was loaded in every session consuming tokens but never used. Removing it saves tokens with zero impact on behavior."),
        ],
    },
    "heal-savings-l2": {
        "title": "L2 Proactive Savings",
        "icon": "🧠",
        "one_liner": "How the $0.03 per-event savings is calculated.",
        "detail": """<div class="glossary-detail">
    <strong>Assumptions (per event):</strong><br>
    • <strong>L2 adds predictive detection</strong> (before failure happens, not after)<br>
    • <strong>Savings:</strong> $0.02 (L1) + $0.01 additional (no downtime at all) = <strong style="color:#fde68a;">$0.03 saved / event</strong><br>
    • <strong>True savings:</strong> Prevents entire downtime window. $0.03 is the full event cost minus any impact.<br><br>
    <strong>Key difference from L1:</strong> L1 auto-restarts after a failure. L2 predicts and rotates before failure — zero downtime, zero impact.<br><br>
    <strong>How to calculate your own:</strong><br>
    <code>proactive_savings = full_downtime_cost − 0 (no downtime at all)</code><br><br>
    <span style="color:#64748b;">These are estimates based on typical agent recovery costs. Your fleet may save more or less.</span>
</div>""",
        "faq": [
            ("How is $0.03 different from $0.02?", "L1 saves $0.02 after a failure (1 min recovery). L2 saves the full $0.03 by preventing the failure entirely — plus the $0.01 extra is the time you'd have spent investigating the failure before you knew what to fix."),
            ("Is proactive monitoring always better?", "For recurring failure patterns (memory leaks, config drift), yes. For random crashes, L1 still catches it! L2 is a safety net, not a replacement for L1."),
        ],
    },
    "brain-analysis": {
        "title": "Brain Analysis",
        "icon": "🧠",
        "one_liner": "See what feeds your agents — token composition, savings potential, drift trends, and compression tools.",
        "detail": """<div class="glossary-detail">
    <strong>What it shows:</strong> Every agent's system prompt broken down by component (identity, skills, memory, tools, guidance). See how many tokens each part uses, how much you could save with compression, and how your prompts are changing over time.<br><br>
    <strong>Sections:</strong><br>
    • <strong>Token Breakdown</strong> — Per-component token usage with visual bars<br>
    • <strong>Savings</strong> — What Lite and Full compression would save<br>
    • <strong>Drift & Usage</strong> — 7-day trend and 24h per-turn timeline<br>
    • <strong>Compression</strong> — Preview and apply compression per agent<br>
    • <strong>Token Optimiser</strong> — Learns from 200+ turns to find unused skills<br>
    • <strong>Budget Planner</strong> — Fleet-level cost estimation<br>
    • <strong>Memory Garden</strong> — Fleet-wide memory health
</div>""",
        "faq": [
            ("What should I look at first?", "Start with Token Breakdown to see which components are largest. Then check Savings to see what compression would save. Finally, look at Drift to see if any agents are growing too fast."),
            ("Why are some numbers estimates?", "Actual savings require running a compression preview. Before that, we estimate based on your agent's composition and fleet-wide compression averages."),
        ],
    },
    "token-breakdown": {
        "title": "Token Breakdown",
        "icon": "📊",
        "one_liner": "Shows how many tokens each component of your agent's system prompt uses.",
        "detail": """<div class="glossary-detail">
    <strong>Five components:</strong><br>
    <strong style="color:#8b5cf6;">Skills</strong> — Task instructions and tool descriptions. Grows as skills are added.<br>
    <strong style="color:#14b8a6;">Tools</strong> — API descriptions and function schemas. Grows with tool count.<br>
    <strong style="color:#ec4899;">Memory</strong> — User context and conversation history. The most dynamic component.<br>
    <strong style="color:#f97316;">Guidance</strong> — Behavioural rules and framework instructions. Often the largest.<br>
    <strong style="color:#6366f1;">Identity</strong> — Agent's role and personality. Usually stable.<br><br>
    <strong>Why it matters:</strong> Every token is paid for on every AI call. A 10K-token guidance section costs ~$0.0015 per call. Over 250 calls/month, that's ~$0.38 just for guidance.
</div>""",
        "faq": [
            ("Why is Guidance always the biggest?", "Because it includes framework-level instructions, routing rules, and do/don't lists. This is normal — guidance is typically 40-60% of the system prompt."),
            ("What should I do if Memory is growing?", "Memory grows naturally with conversations. If it's >20% of total, consider running compression or checking if memory retention is configured correctly."),
        ],
    },
    "savings-estimate": {
        "title": "Savings Estimate",
        "icon": "💰",
        "one_liner": "How much you'd save per turn with Lite and Full compression.",
        "detail": """<div class="glossary-detail">
    <strong>How savings are calculated:</strong><br>
    • Based on your agent's actual token composition<br>
    • Lite compresses only <strong style="color:#f97316;">guidance</strong> blocks<br>
    • Full compresses guidance + <strong style="color:#8b5cf6;">skills</strong> + <strong style="color:#ec4899;">memory</strong><br>
    • Dollar savings use your selected provider rate<br><br>
    <strong>▲ = estimate</strong> — based on composition analysis, not actual compression run. Run Preview for real numbers.<br><br>
    <strong>No ▲ = actual</strong> — from real compression runs logged in compress_log.
</div>""",
        "faq": [
            ("Why does it say 'based on composition'?", "Before you run a compression preview, we estimate savings by applying fleet-wide compression averages to your agent's specific composition. The ▲ indicator means it's an estimate."),
            ("How accurate are the estimates?", "Typically within 5-10% of actual results. The estimate uses real fleet-wide compression data, so it's grounded in actual runs — not guesswork."),
        ],
    },
    "drift-usage": {
        "title": "Drift & Usage",
        "icon": "📈",
        "one_liner": "Shows how your agent's prompt size is changing over 7 days and token usage over 24 hours.",
        "detail": """<div class="glossary-detail">
    <strong>Component Drift (7-day):</strong> Each component's token count trend over the last week. Upward drift means the component is growing — common causes are memory accumulation, new skills, or guidance additions.<br><br>
    <strong>Per-turn Timeline (24h):</strong> Shows how many tokens were used per turn in each of the last 24 hours. Helps identify peak usage periods and whether token consumption is consistent.<br><br>
    <strong>When to act:</strong><br>
    • Drift > <strong>+10%</strong> — Worth monitoring<br>
    • Drift > <strong>+20%</strong> — Needs investigation<br>
    • Spikes in per-turn timeline — Could indicate a misconfigured agent
</div>""",
        "faq": [
            ("What causes positive drift?", "Most commonly: agent memory accumulation (every conversation adds context), new skills being added, or tool descriptions growing. Check the component breakdown to identify the source."),
            ("Is drift always bad?", "Not necessarily. Controlled growth from adding genuine capabilities is expected. Runaway drift (30%+ in a week) indicates memory bloat or skill sprawl."),
        ],
    },
    "compression": {
        "title": "Compression",
        "icon": "✂️",
        "one_liner": "Preview and apply token compression to reduce your agent's system prompt size.",
        "detail": """<div class="glossary-detail">
    <strong>Two modes:</strong><br>
    <strong style="color:#22c55e;">Lite</strong> — Compresses only the guidance section. Safe, predictable, no risk of breaking functionality.<br>
    <strong style="color:#a5b4fc;">Full</strong> — Compresses guidance + memory + skills. Higher savings.<br><br>
    <strong>Workflow:</strong><br>
    1. Select an agent from the dropdown<br>
    2. Choose Lite or Full mode<br>
    3. Click <strong>Run Preview</strong> to see the diff (no files modified)<br>
    4. Click <strong>Apply to File</strong> to write the compressed version<br><br>
    <strong>Auto tab:</strong> Set up a watch daemon that auto-compresses on every SOUL.md edit.
</div>""",
        "faq": [
            ("Is compression safe?", "Lite is very safe — it only touches guidance blocks. Full is safe for most agents but modifies skill descriptions, which could theoretically affect behaviour. Always preview first."),
            ("Can I undo compression?", "Yes. Apply creates a backup automatically. You can restore from the backup file."),
        ],
    },
    "tier-summary": {
        "title": "Tier Summary",
        "icon": "🔓",
        "one_liner": "Lite vs Full compression comparison.",
        "detail": """<div class="glossary-detail">
    <strong>Lite:</strong><br>
    • Compress guidance blocks<br>
    • Per-agent breakdown & drift<br>
    • 24h per-turn timeline<br>
    • 7-day component trends<br><br>
    <strong>Full:</strong><br>
    • Full compression (memory + skills + context)<br>
    • Auto-Watch daemon (auto-compress on edit)<br>
    • Token Optimiser (learns from 200 turns)<br>
    • Never-pruned history & fleet comparison
</div>""",
        "faq": [
            ("What's the difference between Lite and Full?", "Lite compresses only guidance blocks. Full compresses guidance + memory + skills for deeper savings."),
        ],
    },
    "memory-garden": {
        "title": "Memory Garden",
        "icon": "💾",
        "one_liner": "Fleet-wide memory health summary — duplicates, contradictions, stale entries, and debt score.",
        "detail": """<div class="glossary-detail">
    <strong>What it tracks:</strong><br>
    • <strong>Duplicates</strong> — Redundant memory entries that waste tokens<br>
    • <strong>Contradictions</strong> — Conflicting information stored across agents<br>
    • <strong>Stale entries</strong> — Outdated or irrelevant memories<br>
    • <strong>Debt score</strong> — Overall memory health (lower is better)<br>
    • <strong>Fleet grade</strong> — A-F letter grade for fleet memory hygiene<br><br>
    <strong>Why it matters:</strong> Bloated memory increases token costs and can cause agents to act on outdated information. Regular garden maintenance keeps your fleet efficient.
</div>""",
        "faq": [
            ("What's a good debt score?", "Below 20 is excellent. 20-50 is acceptable. Above 50 needs attention."),
            ("How do I clean up memory?", "Run `observeco garden prune` to remove stale entries."),
        ],
    },
    "llm-warning": {
        "title": "LLM Features Warning",
        "icon": "⚠️",
        "one_liner": "Disabling LLM-powered features affects how ObserveCo monitors and heals your fleet.",
        "detail": """<div class="glossary-detail">
    <strong>What changes:</strong><br>
    • Agent discovery uses static rules instead of AI analysis<br>
    • Health insights are rule-based, not AI-driven<br>
    • Healing suggestions use predefined templates<br><br>
    <strong>Not recommended for production fleets.</strong> LLM features enable proactive detection and smarter healing. Disabling them reduces ObserveCo to a basic monitoring tool.
</div>""",
        "faq": [
            ("Why would I disable LLM features?", "If you're running on a strict budget or have privacy concerns about sending data to LLM providers. Note that token data is anonymised."),
            ("Can I re-enable later?", "Yes — toggle it back on from the Settings tab at any time."),
        ],
    },
    "brain-pro": {
        "title": "Token Optimiser",
        "icon": "🧪",
        "one_liner": "Full compression, Auto-Watch, Token Optimiser, and never-pruned history.",
        "detail": """<div class="glossary-detail">
    <strong>Full compression</strong> — Compresses guidance + memory + skills + context<br>
    • <strong>Auto-Watch Daemon</strong> — Every SOUL.md edit triggers auto-compression<br>
    • <strong>Token Optimiser</strong> — Analyses 200+ turns to prune unused skills<br>
    • <strong>Never-pruned history & fleet comparison</strong>
</div>""",
        "faq": [
            ("What's the difference between compression and Optimiser?", "Compression shortens existing content. The Optimiser learns which skills are never used and removes them entirely — deeper savings."),
        ],
    },
    "pathway-map": {
        "title": "Pathway Map",
        "icon": "🕸️",
        "one_liner": "Visual graph of your agent ecosystem — see how agents communicate and route signals.",
        "detail": """<div class="glossary-detail">
    <strong>What it shows:</strong> A directed graph of your entire agent ecosystem. Each node is an agent or service. Each edge is a communication pathway (signal, webhook, direct call).<br><br>
    <strong>Use cases:</strong><br>
    • Understand how data flows between agents<br>
    • Identify single points of failure<br>
    • Discover orphaned agents (no connections)<br>
    • Plan architecture changes<br><br>
    <strong>Interactive:</strong> Click nodes to see details, drag to rearrange, zoom in/out.
</div>""",
        "faq": [
            ("How is the map generated?", "From your agent config files, signal routing rules, and webhook subscriptions. It's auto-discovered — no manual setup needed."),
            ("Can I export the map?", "Yes — use the export button in the modal to save as PNG or SVG."),
        ],
    },
    "openclaw-plugins": {
        "title": "OpenClaw Plugins",
        "icon": "🔌",
        "one_liner": "Plugin sources, intent classifiers, and load status for OpenClaw agents.",
        "detail": """<div class="glossary-detail">
    <strong>What it shows:</strong> All plugins registered with OpenClaw — their source (local, git, registry), intent classifiers (what they handle), and current load status (loaded, failed, pending).<br><br>
    <strong>Why it matters:</strong> Plugins extend agent capabilities. A failed plugin means the agent can't handle certain intents. Monitor this to ensure all capabilities are available.
</div>""",
        "faq": [
            ("What does 'failed' mean?", "The plugin couldn't be loaded — check the error log for details. Common causes: missing dependencies, syntax errors, or incompatible versions."),
            ("How do I add a new plugin?", "Use `openclaw plugin add <source>` from the CLI, or add it to your OpenClaw config file."),
        ],
    },
    "stop-agent": {
        "title": "Stop Agent",
        "icon": "🛑",
        "one_liner": "Emergency kill switch — sends SIGTERM, then SIGKILL after 5s if the process doesn't shut down cleanly.",
        "detail": """<div class="glossary-detail">
    <strong>What it does:</strong> Stops a running agent process by sending a <code>SIGTERM</code> signal (graceful shutdown). If the process doesn't exit within 5 seconds, it sends <code>SIGKILL</code> (force kill).<br><br>
    <strong>Confirmation:</strong> You must click STOP twice — the first click prepares, the second executes. This prevents accidental kills.<br><br>
    <strong>Why it matters:</strong> Stuck or misbehaving agents can waste tokens, produce bad results, or block restarts. Use this to force-stop an agent so it can be restarted cleanly. Check the kill log below for history.
</div>""",
        "faq": [
            ("Is this safe?", "Yes. The 5-second grace period gives the agent time to save state and exit cleanly. SIGKILL is only used if SIGTERM doesn't work."),
            ("Will the agent auto-restart?", "If managed by launchd/systemd, it will restart automatically. If started manually, you'll need to start it again."),
            ("What's the difference between SIGTERM and SIGKILL?", "SIGTERM (signal 15) asks the process to shut down — it can clean up files, flush logs, etc. SIGKILL (signal 9) terminates immediately — no cleanup, no save. SIGKILL is the nuclear option."),
        ],
    },
    "restart-quality": {
        "title": "Restart Quality",
        "icon": "🔄",
        "one_liner": "Classifies each agent restart into healthy KeepAlive, TOCTOU race, or real crash.",
        "detail": """<div class="glossary-detail">
    <strong>Three restart types:</strong><br><br>
    🟢 <strong>Healthy (KeepAlive)</strong> — sub-second restart via KeepAlive protocol. No data loss, no error. This is the ideal restart path — the agent caught a signal, saved state, and came back clean.<br><br>
    🟡 <strong>TOCTOU race</strong> — file consumed between fsnotify event and .stat() check. The daemon detected a file change, but another process consumed the file before the daemon could read it. Not a crash, but indicates a timing issue in agent file watchers.<br><br>
    🔴 <strong>Real crash</strong> — SIGSEGV, OOM, config error, or unhandled exception. Requires investigation. Recorded as a circuit breaker failure.<br><br>
    <strong>What it saves:</strong> Differentiating TOCTOU from crash prevents false alarms. A TOCTOU loop looks like repeated crashes, but the fix is different (code fix vs restart).
</div>""",
        "faq": [
            ("Why does restart quality matter?", "Without classification, every dead status looks like a crash. TOCTOU races are not crashes but look identical in logs. This tab separates signal from noise, showing you which restarts are safe (KeepAlive), which need a code fix (TOCTOU), and which are real emergencies (crash)."),
            ("How is data collected?", "Every pulse check logs a restart event when an agent is found dead. The classification runs server-side by analyzing the agent's crash log, error message, and timing. Data is kept for 24 hours."),
            ("What is a healthy restart? How is it detected?", "A KeepAlive restart happens when the agent process reconnects within seconds with no crash log. The pulse check sees a brief 'dead' state followed by a 'live' response before the next check cycle. This is the normal hot-reload path."),
            ("What is a TOCTOU race?", "Time-of-check-to-time-of-use: a file watcher fires an fsnotify event, but by the time the daemon calls .stat(), the file has been consumed or replaced. Common in agents that watch directories for file-based communication. The fix is a guard + retry in the file handler."),
            ("What should I do if I see >50% crash rate?", "Investigate immediately. Run <code>observeco heal --agent &lt;name&gt;</code> for automated diagnosis, or check the Error timeline on the agent card. Common causes: OOM, missing dependencies, port conflicts."),
        ],
    },
}

@app.get("/api/glossary/{topic}", response_class=HTMLResponse)
async def api_glossary(topic: str):
    """Return glossary content for a topic — §3.20."""
    entry = GLOSSARY_DATA.get(topic)
    if not entry:
        return HTMLResponse('<div class="glossary-not-found">Topic not found. Available: status-dot, circuit, token-bar, drift, error-badge, error-tab, pulse-check, heal-button, alerts-panel, confidence, fp, fn, skills-audit, compression-lite, compression-full, fleet-compare, budget-planner, drift-alerts, heal-thresholds, token-optimiser, stop-agent, restart-quality, brain-analysis, token-breakdown, savings-estimate, drift-usage, compression, tier-summary, memory-garden, llm-warning, brain-pro, pathway-map, openclaw-plugins.</div>')

    faq_html = ""
    if entry.get("faq"):
        faq_items = []
        for q, a in entry["faq"]:
            faq_items.append(f'''<details class="faq-details">
    <summary class="faq-summary">❓ {q}</summary>
    <div class="faq-answer">{a}</div>
</details>''')
        faq_html = '<div class="glossary-faq"><div class="glossary-faq-title">FAQ</div>' + "\n".join(faq_items) + "</div>"

    return HTMLResponse(f"""<div style="padding:4px;">
    <div class="glossary-header">
        <span class="glossary-header-icon">{entry["icon"]}</span>
        <span class="glossary-header-title">{entry["title"]}</span>
    </div>
    <div class="glossary-one-liner">{entry["one_liner"]}</div>
    {entry["detail"]}
    {faq_html}
</div>""")


# ---------------------------------------------------------------------------
# §§§ — Main Page
# ---------------------------------------------------------------------------

@app.get("/new", response_class=HTMLResponse)
async def new_dashboard():
    """Serve the new Strong-Fit dashboard design (index_new.html)."""
    index_path = TEMPLATES_DIR / "index_new.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard</h1><p>Template not found.</p>")
    html = index_path.read_text(encoding="utf-8")
    from observeco import __version__
    html = html.replace("{{VERSION}}", __version__)
    token = getattr(app.state, "dashboard_secret", "")
    if token:
        body_idx = html.find("<body")
        if body_idx >= 0:
            body_close = html.index(">", body_idx)
            hx_attr = f' hx-headers=\'{{"X-ObserveCo-Token":"{token}"}}\''
            html = html[:body_close] + hx_attr + html[body_close:]
        if "</head>" in html:
            head_end = html.rindex("</head>")
            injection = (
                f'<meta name="observeco-token" content="{token}">\n'
                f'<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n'
                f'<meta http-equiv="Pragma" content="no-cache">\n'
                f'<meta http-equiv="Expires" content="0">\n'
                f'<script>window.__OBSERVECO_TOKEN = "{token}";</script>\n'
            )
            html = html[:head_end] + injection + html[head_end:]
    return HTMLResponse(html)

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = TEMPLATES_DIR / "index_new.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard</h1><p>Template not found.</p>")
    html = index_path.read_text(encoding="utf-8")
    from observeco import __version__
    html = html.replace("{{VERSION}}", __version__)
    token = getattr(app.state, "dashboard_secret", "")
    if token:
        # 1. Inject hx-headers on the <body> tag (htmx-native, zero timing dependency)
        body_idx = html.find("<body")
        if body_idx >= 0:
            body_close = html.index(">", body_idx)
            hx_attr = f' hx-headers=\'{{"X-ObserveCo-Token":"{token}"}}\''
            html = html[:body_close] + hx_attr + html[body_close:]

        # 2. Inject cache meta + __OBSERVECO_TOKEN before </head>
        if "</head>" in html:
            head_end = html.rindex("</head>")
            phase = db.get_phase()
            injection = (
                f'<meta name="observeco-token" content="{token}">\n'
                f'<meta name="observeco-phase" content="{phase}">\n'
                f'<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n'
                f'<meta http-equiv="Pragma" content="no-cache">\n'
                f'<meta http-equiv="Expires" content="0">\n'
                f'<script>window.__OBSERVECO_TOKEN = "{token}";</script>\n'
                f'<script>window.__OBSERVECO_PHASE = "{phase}";</script>\n'
                f'</head>'
            )
            html = html[:head_end] + injection + html[head_end + len("</head>"):]
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# § v2 — Domain-grouped nav partial
# ---------------------------------------------------------------------------


@app.get("/api/partials/nav", response_class=HTMLResponse)
async def api_partials_nav():
    """Return domain-grouped nav HTML partial (v2 Strong-Fit design)."""
    return HTMLResponse("""<nav class="nav" aria-label="Primary">
    <div class="nav-group">
      <span class="glabel">Monitor</span>
      <span class="nav-tab active clickable" data-tab="fleet">Fleet</span>
      <span class="nav-tab clickable" data-tab="coverage">Coverage</span>
      <span class="nav-tab clickable" data-tab="alerts">Alerts</span>
      <span class="nav-tab clickable" data-tab="timeline">Error Timeline</span>
      <span class="nav-tab clickable" data-tab="pathway">Pathway Map</span>
    </div>
    <div class="nav-group">
      <span class="glabel">Analyze</span>
      <span class="nav-tab clickable" data-tab="tokens">Tokens</span>
      <span class="nav-tab clickable" data-tab="brain">Brain</span>
      <span class="nav-tab clickable" data-tab="drift">Drift</span>
      <span class="nav-tab clickable" data-tab="compare">Compare</span>
      <span class="nav-tab clickable" data-tab="harness">Harness</span>
    </div>
    <div class="nav-group">
      <span class="glabel">Intelligence</span>
      <span class="nav-tab clickable" data-tab="capability">Capability</span>
      <span class="nav-tab clickable" data-tab="anomalies">Anomalies</span>
      <span class="nav-tab clickable" data-tab="health-score">Health Score<span class="soon">soon</span></span>
      <span class="nav-tab clickable" data-tab="traces">Traces<span class="soon">soon</span></span>
    </div>
    <div class="nav-group">
      <span class="glabel">Settings</span>
      <span class="nav-tab clickable" data-tab="config">Config</span>
      <span class="nav-tab clickable" data-tab="billing">Billing</span>
    </div>
  </nav>""")


# ---------------------------------------------------------------------------
# §3.19 — Communication Pathway Map API
# ---------------------------------------------------------------------------

@app.get("/api/pathway-graph", response_class=HTMLResponse)
async def api_pathway_graph():
    """Return pathway graph as JSON for Cytoscape.js rendering."""
    graph = db.pathway_get_graph()
    return HTMLResponse(json.dumps(graph, default=str))

@app.get("/api/pathway-scan", response_class=HTMLResponse)
async def api_pathway_scan():
    """Trigger a pathway scan and return results."""
    graph = db.pathway_get_graph()
    by_status = {}
    for e in graph["edges"]:
        s = e["status"]
        by_status[s] = by_status.get(s, 0) + 1
    summary_parts = ['<span class="pathway-scan-item">🔍 Scan complete</span>']
    for s, cnt in sorted(by_status.items()):
        icon = {"green": "🟢", "yellow": "🟡", "red": "🔴", "teal": "🔵"}.get(s, "⚪")
        summary_parts.append(f'<span class="pathway-scan-item">{icon} {s}: {cnt}</span>')

    red_edges = [e for e in graph["edges"] if e["status"] == "red"]
    red_html = ""
    if red_edges:
        red_html = '<div class="pathway-red-zone">'
        for e in red_edges:
            red_html += f'<div class="pathway-red-item">🔴 Dead end: {e["source_name"]} → ∅</div>'
        red_html += "</div>"

    return HTMLResponse(f'<div class="pathway-scan-summary">{" ".join(summary_parts)}{red_html}</div>')

@app.get("/api/pathway-snapshots", response_class=HTMLResponse)
async def api_pathway_snapshots(limit: int = 50):
    """List pathway snapshots for historical replay timeline."""
    snapshots = db.pathway_get_snapshots(limit)
    return HTMLResponse(json.dumps(snapshots, default=str))

@app.get("/api/pathway-snapshot/{snapshot_id}", response_class=HTMLResponse)
async def api_pathway_snapshot(snapshot_id: int):
    """Get full snapshot data for replay."""
    snap = db.pathway_get_snapshot(snapshot_id)
    if not snap:
        return HTMLResponse(json.dumps({"error": "Snapshot not found"}), status_code=404)
    return HTMLResponse(json.dumps(snap["data"], default=str))

@app.post("/api/pathway-snapshot", response_class=HTMLResponse)
async def api_record_pathway_snapshot():
    """Record a snapshot of the current pathway graph."""
    sid = db.pathway_record_snapshot()
    return HTMLResponse(json.dumps({"snapshot_id": sid, "ok": True}))


# §3.19 — Communication Pathway Map page
PATHWAY_TEMPLATE = TEMPLATES_DIR / "pathway.html"

@app.get("/pathway", response_class=HTMLResponse)
async def pathway_page():
    """Serve the Cytoscape.js pathway map page."""
    if not PATHWAY_TEMPLATE.exists():
        return HTMLResponse("<h1>Pathway Map</h1><p>Template not found.</p>")
    html = PATHWAY_TEMPLATE.read_text(encoding="utf-8")
    token = app.state.dashboard_secret if hasattr(app.state, "dashboard_secret") else ""
    if token and "</head>" in html:
        head_end = html.rindex("</head>")
        injection = (
            f'<script>window.__OBSERVECO_TOKEN = "{token}";</script>\n'
            f'</head>'
        )
        html = html[:head_end] + injection + html[head_end:]
    return HTMLResponse(html)


PATHWAY_TAB_TEMPLATE = TEMPLATES_DIR / "pathway_tab.html"


@app.get("/api/pathway/tab", response_class=HTMLResponse)
async def api_pathway_tab():
    """Return the pathway map partial for in-dashboard tab (htmx)."""
    if not PATHWAY_TAB_TEMPLATE.exists():
        return HTMLResponse("<div style='padding:24px;text-align:center;color:var(--muted);'>Pathway tab template not found.</div>")
    html = PATHWAY_TAB_TEMPLATE.read_text(encoding="utf-8")
    token = app.state.dashboard_secret if hasattr(app.state, "dashboard_secret") else ""
    if token:
        html = f'<script>window.__OBSERVECO_TOKEN = "{token}";</script>\n' + html
    return HTMLResponse(html)


# ── Telemetry opt-in endpoint (Layer F / F9) ────────────────────


# ---------------------------------------------------------------------------
# § Shared-Fleet — Multi-Instance Detection
# ---------------------------------------------------------------------------

@app.get("/api/instances", response_class=HTMLResponse)
async def api_instances():
    """Return a badge showing how many instances share this DB (shared mode only)."""
    shared_path = os.environ.get("OBSERVECO_SHARED_DB", "")
    if not shared_path:
        return HTMLResponse("")
    agents = db.get_agents()
    instance_ids = set()
    for a in agents:
        pulses = db.get_recent_pulses(agent_name=a["agent_name"], limit=5)
        for p in pulses:
            iid = p.get("instance_id", "")
            if iid:
                instance_ids.add(iid)
    count = len(instance_ids)
    if count <= 1:
        return HTMLResponse("")
    return HTMLResponse(
        f'<div class="shared-badge" style="display:inline-flex;align-items:center;gap:4px;'
        f'background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.2);'
        f'border-radius:6px;padding:2px 8px;font-size:11px;color:#a5b4fc;">'
        f'🌐 {count} instance{"s" if count != 1 else ""}</div>'
    )


@app.get("/api/shared-warning", response_class=HTMLResponse)
async def api_shared_warning():
    """Return a one-time warning banner on first shared-mode load (similar to F9 telemetry warning)."""
    shared_path = os.environ.get("OBSERVECO_SHARED_DB", "")
    if not shared_path:
        return HTMLResponse("")
    warned_path = get_data_dir() / ".shared_warning_shown"
    if warned_path.exists():
        return HTMLResponse("")
    warned_path.touch()
    return HTMLResponse(
        '<div id="sharedWarning" class="shared-warning" style="background:rgba(234,179,8,0.08);'
        'border:1px solid rgba(234,179,8,0.2);border-radius:8px;padding:10px 14px;'
        'margin-bottom:12px;font-size:12px;line-height:1.5;">'
        '<div style="display:flex;align-items:flex-start;gap:10px;">'
        '<span style="font-size:16px;">🛡️</span>'
        '<div style="flex:1;">'
        '<strong style="color:#fde68a;">Shared Fleet Mode Active</strong>'
        '<div style="color:#94a3b8;margin-top:2px;">'
        'Multiple instances share this database via <code style="font-size:11px;background:#0f172a;padding:1px 5px;border-radius:3px;">'
        f'{_html_escape(shared_path)}</code>. '
        'Data writes from all instances merge into one view. Ensure only trusted '
        'team members have write access to this path. Network share latency may '
        'affect dashboard responsiveness.'
        '</div></div>'
        '<button onclick="document.getElementById(\'sharedWarning\').style.display=\'none\'" '
        'style="background:transparent;border:1px solid #475569;color:#94a3b8;padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer;">✕</button>'
        '</div></div>'
    )


@app.get("/api/telemetry-status")
async def api_telemetry_status():
    """Return whether the user has opted in to telemetry.

    Returns JSON with: opted_in (bool), opted_out_file_exists (bool),
    prompt_required (bool). The dashboard uses this to decide
    whether to show the opt-in prompt.
    """
    from observeco.telemetry_client import _get_opt_in_file, is_telemetry_enabled
    opted_in = is_telemetry_enabled()
    opt_file_exists = _get_opt_in_file().exists()
    return JSONResponse({
        "opted_in": opted_in,
        "opted_out_file_exists": opt_file_exists,
        "prompt_required": not opt_file_exists,
    })


@app.get("/api/telemetry-opt-in")
async def api_telemetry_opt_in(choice: str = ""):
    """Persist the user's telemetry consent choice.

    Query param ``choice``: "yes" or "no".
    Returns an htmx-compatible HTML snippet.
    """
    from observeco.telemetry_client import set_opt_in
    if choice == "yes":
        set_opt_in(True)
        return HTMLResponse(
            '<div class="telemetry-confirmed" style="background:rgba(34,197,94,0.08);'
            'border:1px solid rgba(34,197,94,0.2);border-radius:8px;padding:8px 14px;'
            'font-size:11px;color:#86efac;">'
            '✅ Telemetry enabled — thank you. Anonymous crash/usage data helps improve ObserveCo.'
            '</div>'
        )
    elif choice == "no":
        set_opt_in(False)
        return HTMLResponse(
            '<div class="telemetry-declined" style="background:rgba(148,163,184,0.08);'
            'border:1px solid rgba(148,163,184,0.2);border-radius:8px;padding:8px 14px;'
            'font-size:11px;color:#94a3b8;">'
            '🔕 Telemetry disabled. You can change this later via Settings.'
            '</div>'
        )
    return HTMLResponse("")


@app.get("/api/telemetry-prompt", response_class=HTMLResponse)
async def api_telemetry_prompt():
    """Return the opt-in prompt banner if the user hasn't decided yet.

    This is loaded by htmx on page load.
    """
    from observeco.telemetry_client import _get_opt_in_file
    if _get_opt_in_file().exists():
        return HTMLResponse("")  # Already decided — no prompt
    return HTMLResponse(
        '<div id="telemetryPrompt" class="telemetry-prompt" style="background:rgba(99,102,241,0.08);'
        'border:1px solid rgba(99,102,241,0.2);border-radius:8px;padding:10px 14px;'
        'margin-bottom:12px;font-size:12px;line-height:1.5;">'
        '<div style="display:flex;align-items:flex-start;gap:10px;">'
        '<span style="font-size:16px;flex-shrink:0;">💬</span>'
        '<div style="flex:1;">'
        '<div style="font-weight:600;color:#e2e8f0;margin-bottom:2px;">Help improve ObserveCo</div>'
        '<div style="color:#94a3b8;margin-bottom:6px;">'
        'Send anonymous crash and usage data? No personal data collected. '
        '<a href="#" onclick="alert(\'We collect: crash reports, feature usage counts, Python version, '
        'and OS type. No code, no prompts, no personal identifiers. See privacy policy at '
        'https://observeco.ai/privacy\')" style="color:#818cf8;">Learn more</a>'
        '</div>'
        '<div style="display:flex;gap:6px;">'
        '<button hx-get="/api/telemetry-opt-in?choice=yes" hx-target="#telemetryPrompt" hx-swap="outerHTML" '
        'style="background:#6366f1;border:none;color:white;padding:5px 14px;border-radius:6px;'
        'font-size:11px;font-weight:600;cursor:pointer;">Yes, help me improve</button>'
        '<button hx-get="/api/telemetry-opt-in?choice=no" hx-target="#telemetryPrompt" hx-swap="outerHTML" '
        'style="background:transparent;border:1px solid #475569;color:#94a3b8;padding:5px 14px;'
        'border-radius:6px;font-size:11px;cursor:pointer;">No, thanks</button>'
        '</div>'
        '</div>'
        '</div>'
    )


# ── LLM-powered onboarding guide (Day 3 — §3.25) ─────────────────
ONBOARDING_GUIDE_PROMPT = """You are ObserveCo's onboarding guide. Generate a brief, personalized 3-step onboarding guide.

System context:
{system_context}

OS: {os}
Detected LLM provider: {provider}

Generate a 3-step guide. Keep it under 200 words total. Format:

TITLE: <personalized welcome title>
STEP1: <first thing user should see/do>
STEP2: <what happens next>
STEP3: <what to explore>

Focus on what's actually running on this machine, not generic instructions."""


@app.get("/api/onboarding-guide", response_class=HTMLResponse)
async def api_onboarding_guide():
    """Generate personalized onboarding guide via LLM."""
    from observeco.llm_service import ask, get_auto_provider

    # Collect system context
    agents = db.get_agents()
    agent_names = ", ".join(a["agent_name"] for a in agents[:5]) if agents else "none detected"
    agent_count = len(agents)

    pulses = db.get_recent_pulses(limit=3)
    has_data = len(pulses) > 0

    import platform
    os_name = platform.system()

    auto = get_auto_provider()
    provider_name = auto.name if auto else "none"

    system_context = f"Agents: {agent_count} ({agent_names}). Data arriving: {has_data}."

    response = ask(
        ONBOARDING_GUIDE_PROMPT.format(
            system_context=system_context,
            os=os_name,
            provider=provider_name,
        ),
        "",
        consumer="onboarding_guide",
        max_cost_cents=0.005,
        cache_ttl_secs=3600,  # cache 1h — system state changes slowly
        tier=2,
    )

    if response is None:
        # Static fallback
        return HTMLResponse("<div>Welcome to ObserveCo. Start by adding agents and running the watch daemon.</div>")

    # Parse and render
    guide = {"title": "Welcome to ObserveCo", "steps": []}
    step = ""
    for line in response.strip().split("\n"):
        line = line.strip()
        if line.startswith("TITLE:"):
            guide["title"] = line[6:].strip()
        elif line.startswith("STEP"):
            if line[5:].startswith(":"):
                if step:
                    guide["steps"].append(step)
                step = line[6:].strip()

    if step:
        guide["steps"].append(step)

    html = f"""<div class="llm-guide" style="background:linear-gradient(135deg,rgba(34,197,94,0.06),rgba(59,130,246,0.04));border:1px solid rgba(34,197,94,0.15);border-radius:12px;padding:14px 16px;margin:12px 0;">
        <div style="font-size:14px;font-weight:600;color:#e2e8f0;margin-bottom:10px;">{guide['title']}</div>
        <div style="display:flex;flex-direction:column;gap:8px;">"""
    for i, s in enumerate(guide["steps"], 1):
        html += f"""
            <div style="display:flex;gap:10px;align-items:flex-start;">
                <div style="width:22px;height:22px;min-width:22px;border-radius:50%;background:rgba(34,197,94,0.15);color:#22c55e;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;">{i}</div>
                <div style="font-size:12px;color:#94a3b8;line-height:1.5;">{s}</div>
            </div>"""
    html += """</div></div>"""
    return HTMLResponse(html)


ONBOARDING_TEMPLATE = TEMPLATES_DIR / "onboarding.html"


@app.get("/api/onboarding", response_class=HTMLResponse)
async def api_onboarding():
    """Serve the onboarding overlay template."""
    if not ONBOARDING_TEMPLATE.exists():
        return HTMLResponse("")
    return HTMLResponse(ONBOARDING_TEMPLATE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

def _find_free_port(host: str, preferred: int) -> int:
    import socket
    for port in range(preferred, preferred + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # SO_REUSEADDR lets bind() succeed over a lingering TIME_WAIT socket
            # left by a just-killed instance, so restart races don't fall back.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return preferred


def _ensure_watch_running() -> None:
    """Auto-launch the watch daemon if it's not already running.

    Checks heartbeat freshness AND PID liveness. If either is stale
    or the daemon process has died, spawns a new independent process
    via ``observeco watch start``.
    """
    hb = _get_heartbeat_path()
    now = time.time()
    stale_threshold = 90  # 3 missed cycles at 30s

    alive = False
    if hb.exists():
        try:
            data = json.loads(hb.read_text())
            age = now - data.get("timestamp", 0)
            # Only consider alive if heartbeat is fresh AND PID is actually running
            if age < stale_threshold:
                pid = data.get("pid")
                if pid:
                    try:
                        os.kill(pid, 0)
                        alive = True
                    except (OSError, ProcessLookupError):
                        pass
        except Exception:
            pass

    if alive:
        return

    import subprocess
    import sys

    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen(
            [sys.executable, "-m", "observeco", "watch", "start"],
            **kwargs,
        )
    except Exception:
        logger.exception("swallowed exception in server.py")


def serve(host: str = "127.0.0.1", port: int = PORTS.dashboard, static: bool = False,
          no_browser: bool = False, shared: str | None = None,
          show_token: bool = False) -> None:
    """Start the dashboard server.

    Args:
        host: Bind address.
        port: Preferred port.
        static: Generate static HTML and exit.
        no_browser: Don't open browser.
        shared: Path to shared SQLite DB for team fleet view.
        show_token: Print the dashboard access token and exit.
    """
    # Set shared DB path and instance ID as env vars for subprocesses
    if shared:
        os.environ["OBSERVECO_SHARED_DB"] = str(Path(shared).expanduser().resolve())
    from observeco.dirs import get_instance_id
    os.environ["OBSERVECO_INSTANCE_ID"] = get_instance_id()

    # Initialize dashboard auth (token-based middleware for /api/ routes)
    from observeco.dashboard.auth import load_or_generate_secret
    dashboard_secret = load_or_generate_secret()
    app.state.dashboard_secret = dashboard_secret

    # Load Supabase credentials for CRM backend
    _supa_env = Path(__file__).resolve().parent.parent.parent.parent / ".env.supabase"
    if _supa_env.exists():
        for _line in _supa_env.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

    # Auto-wire Stripe billing if env vars are set
    _stripe_sk = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("stripe_secret_key", "")
    _stripe_pk = os.environ.get("STRIPE_PUBLISHABLE_KEY") or os.environ.get("stripe_publishable_key", "")
    if _stripe_sk and _stripe_pk:
        from observeco.billing import configure as _configure_billing
        _configure_billing(
            stripe_secret=_stripe_sk,
            stripe_publishable=_stripe_pk,
            solo_price=os.environ.get("SOLO_PRICE_ID", ""),
            team_price=os.environ.get("TEAM_PRICE_ID", ""),
            webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
        )
        print(f"[billing] Stripe configured via env vars (pk: {_stripe_pk[:8]}...)")

    if show_token:
        print(f"Dashboard access token: {dashboard_secret}")
        print("Use this with: curl -H 'X-ObserveCo-Token: <token>' http://localhost:{port}/api/agents")
        return

    if static:
        _generate_static(host, port)
        return

    # Auto-launch the independent watch daemon if not running.
    _ensure_watch_running()

    # Prevent zombie duplicates from restart races
    _hermes_home = hermes_home()
    if _hermes_home:
        _hermes_scripts = str(_hermes_home / "scripts")
        if _hermes_scripts not in sys.path:
            sys.path.insert(0, _hermes_scripts)
    from replace_process import replace_existing
    replace_existing(f"observeco-dashboard-{port}")

    actual_port = _find_free_port(host, port)
    url = f"http://{host}:{actual_port}"
    if not no_browser:
        webbrowser.open(url)
    if actual_port != port:
        print(f"Port {port} in use — serving on {actual_port}")
    else:
        print(f"ObserveCo Dashboard: {url}")
    if shared:
        print(f"Shared fleet DB: {os.environ['OBSERVECO_SHARED_DB']}")
    uvicorn.run(app, host=host, port=actual_port, log_level="info")


def _generate_static(host: str, port: int) -> None:
    """Generate static HTML export of the dashboard."""
    out_dir = Path("observeco-static-dashboard")
    out_dir.mkdir(exist_ok=True)

    import asyncio

    import httpx

    from observeco.dashboard.server import app

    async def fetch(path: str) -> str:
        url = f"http://{host}:{port}{path}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            return r.text

    # Start server in background
    import threading
    server_thread = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": host, "port": port, "log_level": "error"},
        daemon=True,
    )
    server_thread.start()
    import time
    time.sleep(2)

    pages = {
        "index.html": "/",
        "api/agents": "/api/agents",
        "api/fleet-summary": "/api/fleet-summary",
        "api/errors": "/api/errors",
        "api/token-summary": "/api/token-summary",
        "api/drift-summary": "/api/drift-summary",
        "api/garden-summary": "/api/garden-summary",
        "api/alerts": "/api/alerts",
    }

    for filename, path in pages.items():
        try:
            content = asyncio.run(fetch(path))
            (out_dir / filename).write_text(content)
            print(f"  ✓ {filename}")
        except Exception as e:
            print(f"  ✗ {filename}: {e}")

    print(f"\nStatic dashboard exported to {out_dir.resolve()}/")
    print("Open: file://" + str((out_dir / "index.html").resolve()))

# ---------------------------------------------------------------------------
# obs-spec-018: Restart Quality — per-agent restart classification
# ---------------------------------------------------------------------------

@app.get("/api/restart-quality", response_class=HTMLResponse)
async def api_restart_quality():
    """Restart quality dashboard — per-agent restart breakdown, false-alarm ratio."""
    from observeco import license as lic
    is_pro = lic.require_pro()

    summary = db.get_restart_summary()
    if not summary:
        # Pro-aware empty state
        if is_pro:
            return HTMLResponse('''<div class="restart-empty" style="padding:24px;text-align:center;">
  <div style="font-size:32px;margin-bottom:12px;">🔌</div>
  <div style="font-size:15px;font-weight:600;color:var(--fg);margin-bottom:8px;">No restart data yet</div>
  <div style="font-size:12px;color:var(--fg-2);margin-bottom:16px;">Most agents restart cleanly. If not, this tab shows you exactly what went wrong — TOCTOU race or real crash.</div>
  <button onclick="triggerRestartScan()" style="background:var(--accent);color:#e2e8f0;border:none;border-radius:8px;padding:8px 18px;font-size:12px;font-weight:600;cursor:pointer;">
    🔄 Run Pulse Scan
  </button>
  <div id="restartScanStatus" style="font-size:11px;color:var(--muted);margin-top:8px;"></div>
  <div style="font-size:11px;color:var(--muted);margin-top:12px;border-top:1px solid var(--border);padding-top:12px;">
    Restart data is also collected automatically when the Watch Daemon is running.<br>
    Three restart types: 🟢 healthy KeepAlive · 🟡 TOCTOU race · 🔴 real crash
  </div>
</div>''')
        else:
            return HTMLResponse('''<div class="restart-empty" style="padding:24px;text-align:center;">
  <div style="font-size:32px;margin-bottom:12px;">🔌</div>
  <div style="font-size:15px;font-weight:600;color:var(--fg);margin-bottom:8px;">No restart data yet</div>
  <div style="font-size:12px;color:var(--fg-2);margin-bottom:16px;">Restart quality data is collected during pulse checks.</div>
  <div style="display:inline-block;font-size:12px;padding:8px 18px;background:var(--accent);color:#e2e8f0;border-radius:8px;font-family:var(--font-mono);margin-bottom:12px;">observeco heal --agent all</div>
  <div style="font-size:11px;color:var(--muted);margin-top:8px;">This tracks restart type (healthy KeepAlive, TOCTOU race, or crash) for each agent. Once data is available, you'll see fleet-wide restart quality, per-agent breakdowns, and false-alarm ratios.</div>
</div>''')

    # Fleet-level totals
    total_healthy = sum(s["healthy"] for s in summary.values())
    total_toctou = sum(s["toctou"] for s in summary.values())
    total_crash = sum(s["crash"] for s in summary.values())

    # Fleet summary cards
    fleet_html = f"""<div class="restart-fleet-grid">
    <div class="restart-fleet-card">
        <span class="restart-fleet-num green">{total_healthy}</span>
        <span class="restart-fleet-label">Healthy Restarts</span>
    </div>
    <div class="restart-fleet-card">
        <span class="restart-fleet-num amber">{total_toctou}</span>
        <span class="restart-fleet-label">TOCTOU Races</span>
    </div>
    <div class="restart-fleet-card">
        <span class="restart-fleet-num red">{total_crash}</span>
        <span class="restart-fleet-label">Real Crashes</span>
    </div>
</div>"""

    # Legend
    legend_html = """<div class="restart-legend">
    <div class="restart-legend-item"><span class="restart-legend-dot green"></span> Healthy restart — sub-second KeepAlive, no data loss</div>
    <div class="restart-legend-item"><span class="restart-legend-dot amber"></span> TOCTOU race — file consumed between fsnotify and .stat()</div>
    <div class="restart-legend-item"><span class="restart-legend-dot red"></span> Real crash — SIGSEGV, OOM, config error</div>
</div>"""

    # Agent cards
    cards = []
    for agent_name in sorted(summary.keys()):
        s = summary[agent_name]
        healthy = s["healthy"]
        toctou = s["toctou"]
        crash = s["crash"]
        total = s["total"]
        far = s["false_alarm_ratio"]

        green_pct = healthy / max(total, 1) * 100
        amber_pct = toctou / max(total, 1) * 100
        red_pct = crash / max(total, 1) * 100

        far_text = f"{far:.0f}% false alarm ratio" if far > 0 else "0% false alarm ratio"
        far_color = "#eab308" if far > 50 else "#22c55e" if far == 0 else "#f97316"
        far_icon = "⚠️" if far > 0 else "✅"

        border_cls = " restart-card-border crash" if crash > 0 else ""

        cards.append(f"""<div class="agent-card{border_cls}" id="rq-card-{agent_name}">
    <div class="restart-card-header">
        <span class="restart-card-name">{_html_escape(agent_name)}</span>
        <span class="restart-card-badge" style="color:{far_color};">{far_icon} {far_text}</span>
        </div>
    </div>
    <div class="restart-card-detail">
        <div class="restart-card-stat"><span class="restart-card-stat-key">Restarts:</span> <span class="restart-card-stat-val">{total}</span></div>
        <div class="restart-card-stat"><span class="restart-card-stat-key green">KeepAlive:</span> <span class="restart-card-stat-val">{healthy}</span></div>
        <div class="restart-card-stat"><span class="restart-card-stat-key amber">TOCTOU:</span> <span class="restart-card-stat-val">{toctou}</span></div>
        <div class="restart-card-stat"><span class="restart-card-stat-key red">Crashes:</span> <span class="restart-card-stat-val">{crash}</span></div>
    </div>
    <div class="restart-bar-section">
        <div class="restart-bar-header">
            <span>Restart quality breakdown</span>
        </div>
        <div class="restart-bar">
            {f'<div class="restart-bar-seg green" style="width:{green_pct:.0f}%;">{healthy}</div>' if healthy > 0 else ''}
            {f'<div class="restart-bar-seg amber" style="width:{amber_pct:.0f}%;">{toctou}</div>' if toctou > 0 else ''}
            {f'<div class="restart-bar-seg red" style="width:{red_pct:.0f}%;">{crash}</div>' if crash > 0 else ''}
        </div>
    </div>
    <div class="restart-toggle" onclick="toggleRestartDetail('{agent_name}')">▶ View restart timeline</div>
    <div class="restart-detail-panel" id="rq-detail-{agent_name}">
        <div class="restart-detail-content" id="rq-detail-content-{agent_name}">Loading...</div>
    </div>
</div>""")

    cards_html = "\n".join(cards)

    return HTMLResponse(f"""<div class="restart-quality-tab">
    {fleet_html}
    {legend_html}
    <div class="agent-restart-cards">
        {cards_html}
    </div>
</div>
<script>
function toggleRestartDetail(agentName) {{
    var el = document.getElementById('rq-detail-' + agentName);
    if (!el) return;
    var open = el.style.display !== 'none';
    el.style.display = open ? 'none' : 'block';
    if (!open) {{
        var content = document.getElementById('rq-detail-content-' + agentName);
        if (content) {{
            content.innerHTML = 'Loading...';
            fetch('/api/restart-quality/' + encodeURIComponent(agentName))
                .then(r => r.text())
                .then(html => {{ content.innerHTML = html; }});
        }}
    }}
}}
</script>""")


@app.get("/api/restart-quality/{agent_name}", response_class=HTMLResponse)
async def api_restart_quality_detail(agent_name: str):
    """Restart timeline detail for a single agent."""
    name = agent_name
    restarts = db.get_recent_restarts(agent_name=name, limit=50)
    if not restarts:
        return HTMLResponse('<div class="restart-empty">No restart data for this agent.</div>')

    items = []
    for r in restarts:
        ts_str = _fmt_ts(r["timestamp"])
        rtype = r["restart_type"]
        duration = r.get("duration_ms", 0)
        snippet = r.get("crash_log_snippet", "")[:120]
        evidence = r.get("evidence", "")

        type_colors = {
            "healthy": ("#22c55e", "Launchd KeepAlive"),
            "toctou": ("#eab308", "TOCTOU race"),
            "crash": ("#ef4444", "Crash"),
        }
        color, label = type_colors.get(rtype, ("#64748b", "Unknown"))

        duration_str = f"{duration}ms recovery" if duration else ""
        snippet_html = f'<div class="restart-snippet">{_html_escape(snippet)}</div>' if snippet else ""

        items.append(f"""<div class="restart-timeline-row">
    <span class="restart-timeline-dot" style="background:{color};left:0;"></span>
    <div class="restart-timeline-header">
        <span class="restart-timeline-ts">{ts_str}</span>
        <span class="restart-timeline-label" style="color:{color};">{label}</span>
        {f'<span class="restart-timeline-duration">{duration_str}</span>' if duration_str else ''}
    </div>
    {snippet_html}
    {f'<div class="restart-evidence">{_html_escape(evidence)}</div>' if evidence else ''}
</div>""")

    return HTMLResponse(f"""<div class="restart-timeline">
    <div class="restart-timeline-rail">
        {''.join(items)}
    </div>
</div>""")


@app.post("/api/restart-quality/scan", response_class=JSONResponse)
async def api_restart_quality_scan():
    """Run a full pulse scan to collect restart data — Pro only."""
    from observeco import license as lic
    if not lic.require_pro():
        return JSONResponse({"ok": False, "error": "Pro license required"}, status_code=403)
    try:
        from observeco.pulse.check import run_check
        run_check(watch=False)
        return JSONResponse({"ok": True, "message": "Pulse scan complete"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


# ---------------------------------------------------------------------------
# §obs-glossary — Glossary & FAQ Panel
# ---------------------------------------------------------------------------

GLOSSARY_ITEMS = [
    ("What is a pulse?", "A heartbeat check — `observeco pulse check` sends a health request to each agent and records alive/dead/error status. Green = healthy, yellow = degraded, red = unreachable."),
    ("What is a circuit breaker?", "When an agent fails N times in a row (default 3), the circuit trips — further checks are blocked until a cooldown expires or you manually reset. Prevents cascading failures."),
    ("What is drift?", "Token composition change over time. If an agent's system prompt grows +15% in a week, that's drift. Tracked per component (identity, skills, memory, tools, guidance)."),
    ("What is context compression?", "ObserveCo's system prompt compression. Decomposes the prompt by component, measures tokens per section, and saves 15-30% per session via intelligent trimming. Run `observeco context trim` to see breakdown."),
    ("What is memory gardening?", "Memory hygiene automation: scans agent memory for duplicates, contradictions, and stale entries. Assigns a health score (A-F). Run `observeco memory garden` to audit any agent."),
    ("What do the gauge colors mean?", "🟢 Green = healthy. 🟡 Yellow = warning (1-2 missed heartbeats, drift >10%). 🔴 Red = critical (dead agent, tripped circuit). 🟠 Orange = token growth. 🔵 Blue = info/baseline."),
]

@app.get("/api/glossary", response_class=HTMLResponse)
async def api_glossary_list():
    items_html = []
    for i, (q, a) in enumerate(GLOSSARY_ITEMS):
        items_html.append(f"""
<div class="glossary-item">
    <div class="glossary-q" onclick="toggleGlossary({i})">
        <span>{q}</span>
        <span class="glossary-icon" id="glossary-icon-{i}">▼</span>
    </div>
    <div class="glossary-answer" id="glossary-answer-{i}">
        {a}
    </div>
</div>""")

    html = """
<div class="glossary-panel">
    <div class="glossary-panel-header">
        <div class="glossary-panel-title">📖 Glossary &amp; FAQ</div>
        <span onclick="toggleGlossarySection()" class="glossary-panel-toggle" id="glossary-toggle-label">▼ Show</span>
    </div>
    <div id="glossary-body" class="u-hidden">
""" + "\n".join(items_html) + """
    </div>
</div>
<script>
function toggleGlossary(i) {
    var answer = document.getElementById('glossary-answer-' + i);
    var icon = document.getElementById('glossary-icon-' + i);
    if (!answer || !icon) return;
    var open = answer.style.display !== 'none';
    answer.style.display = open ? 'none' : 'block';
    icon.textContent = open ? '▶' : '▼';
}
function toggleGlossarySection() {
    var body = document.getElementById('glossary-body');
    var label = document.getElementById('glossary-toggle-label');
    if (!body || !label) return;
    var open = body.style.display !== 'none';
    body.style.display = open ? 'none' : 'block';
    label.textContent = open ? '▼ Show' : '▲ Hide';
}
</script>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Heal Log API — shows recent self-heal events
# ---------------------------------------------------------------------------

@app.get("/api/heal-log", response_class=HTMLResponse)
async def api_heal_log():
    """Show recent self-heal diagnoses and actions."""
    # Heal logs are written as investigation .md files to ~/.observeco/heal/
    from observeco.dirs import get_data_dir
    heal_dir = get_data_dir() / "heal"
    entries = []

    if heal_dir.exists():
        files = sorted(heal_dir.glob("*.investigation.md"), reverse=True)[:20]
        for f in files:
            try:
                text = f.read_text()
                # Extract diagnosis line
                diagnosis = ""
                action = ""
                status = "info"
                for line in text.split("\n"):
                    if line.startswith("## Diagnosis:"):
                        diagnosis = line.replace("## Diagnosis:", "").strip()
                    elif line.startswith("## Action taken:"):
                        action = line.replace("## Action taken:", "").strip()
                        status = "success"

                agent_name = f.name.split("-")[0]
                ts_str = f.name.replace(f"{agent_name}-", "").replace(".investigation.md", "")

                entries.append({
                    "agent": agent_name,
                    "diagnosis": diagnosis or "investigation",
                    "action": action or "none",
                    "status": status,
                    "timestamp": ts_str,
                    "file": f.name,
                })
            except Exception:
                pass

    # Also check circuit breaker state for current issues
    from observeco.db import Database
    d = Database()
    breakers = d.get_circuit_breakers()
    now = int(time.time())

    if not entries:
        # Show circuit breaker state as fallback
        active_issues = []
        for cb in breakers:
            if cb.get("tripped"):
                cooldown = cb.get("cooldown_until", now)
                remaining = max(0, cooldown - now)
                active_issues.append(f"""
<div class="heal-entry fail">
    <div class="heal-entry-header">
        <span class="heal-action">🔴 Tripped Circuit — {cb['agent_name']}</span>
    </div>
    <div class="heal-detail">{cb.get('failure_count',0)} failures — cooldown {remaining // 60}m remaining</div>
</div>""")

        if active_issues:
            html = """
<div class="heal-active">
    <div class="heal-active-title"><strong>⚠️ Active Issues</strong> — agents with problems that need attention.</div>
</div>""" + "\n".join(active_issues)
        else:
            html = '<div class="empty-state">✅ No self-heal events recorded yet.</div>'

        return HTMLResponse(html)

    items = []
    for e in entries[:20]:
        icon = "✅" if e["status"] == "success" else "❌" if e["status"] == "fail" else "🔍"
        items.append(f"""
<div class="heal-entry {e['status']}">
    <div class="heal-entry-header">
        <span class="heal-action">{icon} {e['agent']}</span>
        <span class="heal-time">{e['timestamp']}</span>
    </div>
    <div class="heal-detail">
        <strong>Diagnosis:</strong> {e['diagnosis']}<br>
        <strong>Action:</strong> {e['action']}
    </div>
</div>""")

    html = "\n".join(items)

    return HTMLResponse(html)


@app.get("/api/heal-config", response_class=HTMLResponse)
async def api_heal_config():
    """Auto-Heal Dashboard: per-agent config, status, and events."""
    # Daemon status
    daemon_running = False
    daemon_btn = ""
    try:
        import subprocess
        r = subprocess.run(["pgrep", "-f", "observeco watch"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            daemon_running = True
    except Exception:
        logger.exception("swallowed exception in server.py")

    if not daemon_running:
        daemon_btn = """
        <div class="empty-state" style="margin-bottom:12px;padding:16px;">
            <div style="font-size:13px;font-weight:600;color:#f97316;margin-bottom:6px;">⚠️ Watch Daemon Required</div>
            <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
                Auto-heal listens for pulse failures and restarts agents automatically.
                It runs inside <code style="background:#1e293b;padding:2px 6px;border-radius:4px;font-size:11px;">observeco watch</code> — the same daemon that powers pulse checks,
                drift detection, and the heal button.
            </div>
            <div style="margin-top:8px;display:flex;gap:8px;align-items:center;">
                <button onclick="startWatchDaemon()" style="background:#6366f1;border:none;color:white;border-radius:6px;padding:6px 14px;font-size:12px;cursor:pointer;">▶️ Start Watch Daemon</button>
                <span style="font-size:11px;color:#64748b;">or run <code style="background:#1e293b;padding:2px 6px;border-radius:4px;">observeco watch</code> in terminal</span>
            </div>
            <div style="margin-top:8px;font-size:11px;color:#64748b;">
                Once running, this tab refreshes every 30s and shows per-agent auto-heal controls.
                <span class="glossary-hint" onclick="event.stopPropagation();showGlossary('auto-heal', event)" style="font-size:11px;cursor:pointer;background:#334155;border-radius:4px;padding:1px 6px;color:#94a3b8;font-weight:400;margin-left:4px;">?</span>
            </div>
        </div>"""

    # Get all agents and their heal configs
    from observeco.db import Database
    # ponytail: commercial model is usage-metered, not feature-gated (commercial-scope.md).
    # Auto-heal (L1+L2) + daemon auto-start apply to ALL users, not just Pro.
    is_pro = True
    d = Database()
    agents = d.get_agents()
    configs = {c["agent_name"]: c for c in d.get_heal_config()}

    # Pro users: auto-enable L1+L2 for any agent without a config yet
    if is_pro:
        for a in agents:
            name = a["agent_name"]
            if name not in configs:
                d.set_heal_config(
                    name,
                    auto_heal=True,
                    auto_heal_l2=True,
                    max_restarts_per_hour=3,
                    drift_threshold=15.0,
                    memory_debt_threshold=60,
                )

        # --- Change 7: Migrate existing Pro users with auto_heal=0 ---
        _migration_flag = get_data_dir() / ".heal_pro_migrated"
        if not _migration_flag.exists():
            for a in agents:
                name = a["agent_name"]
                cfg = configs.get(name)
                if cfg and not cfg.get("auto_heal", 0) and not cfg.get("auto_heal_l2", 0):
                    d.set_heal_config(
                        name,
                        auto_heal=True,
                        auto_heal_l2=True,
                        max_restarts_per_hour=cfg.get("max_restarts_per_hour", 3),
                        drift_threshold=cfg.get("drift_threshold", 15.0),
                        memory_debt_threshold=cfg.get("memory_debt_threshold", 60),
                    )
            _migration_flag.touch()

        # --- Change 1: Auto-start daemon on Pro first visit ---
        if not daemon_running:
            _autostart_flag = get_data_dir() / ".watch_autostarted"
            if not _autostart_flag.exists():
                try:
                    import subprocess as _sp
                    _sp.Popen(
                        ["observeco", "watch"],
                        stdout=_sp.DEVNULL,
                        stderr=_sp.DEVNULL,
                    )
                    _autostart_flag.touch()
                    daemon_running = True
                    daemon_btn = ""  # Skip the daemon warning
                except Exception:
                    pass  # Fall through — show the daemon warning as before

    # Re-read configs (includes newly initialized/migrated rows for Pro)
    configs = {c["agent_name"]: c for c in d.get_heal_config()}

    # Build per-agent rows
    agent_rows = ""
    for a in agents:
        name = a["agent_name"]
        cfg = configs.get(name, {})
        ah = cfg.get("auto_heal", 0)
        l2 = cfg.get("auto_heal_l2", 0)
        max_r = cfg.get("max_restarts_per_hour", 3)
        drift_t = cfg.get("drift_threshold", 15.0)
        debt_t = cfg.get("memory_debt_threshold", 60)

        status_label = "🟢 Idle"
        if ah and l2:
            status_label = "🟢 L1 + L2 Active"
        elif ah:
            status_label = "🟢 L1 Active"

        # Count recent heal events
        events = d.get_heal_events(name, limit=5)
        heal_count = len(events)
        last_event = ""
        if events:
            ts = events[0]["created_at"]
            etype = events[0]["event_type"]
            estatus = events[0]["status"]
            last_event = f'<span style="font-size:10px;color:#64748b;">Last: {etype} → {estatus}</span>'

        toggle_checked = 'checked' if ah else ''
        l2_checked = 'checked' if l2 else ''

        # L2 disabled state when L1 is off
        if ah:
            l2_extra_attrs = ''
            l2_cb_style = 'accent-color:#6366f1;'
        else:
            l2_extra_attrs = 'disabled'
            l2_cb_style = 'opacity:0.4;pointer-events:none;accent-color:#6366f1;'

        agent_rows += f"""
        <div class="heal-agent-row" style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <div style="font-size:13px;font-weight:600;color:var(--fg);">{name}</div>
                    <div style="font-size:11px;color:#64748b;margin-top:2px;" class="heal-status-label">{status_label} · {heal_count} events · {last_event}</div>
                </div>
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;justify-content:flex-end;">
                    <span style="background:#1e293b;color:#94a3b8;border-radius:4px;padding:2px 8px;font-size:10px;">Restarts: {max_r}/hr</span>
                    <span style="background:#1e293b;color:#94a3b8;border-radius:4px;padding:2px 8px;font-size:10px;">Drift: {drift_t}%</span>
                    <span style="background:#1e293b;color:#94a3b8;border-radius:4px;padding:2px 8px;font-size:10px;">Debt: {debt_t}</span>
                    <button onclick="editHealThresholds('{name}')" style="background:none;border:1px solid #334155;border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer;color:#94a3b8;margin-left:2px;">Thresholds</button>
                </div>
            </div>
            <!-- hidden threshold values for JS -->
            <span id="maxR_{name}" style="display:none;">{max_r}</span>
            <span id="driftT_{name}" style="display:none;">{drift_t}</span>
            <span id="debtT_{name}" style="display:none;">{debt_t}</span>
            <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border);">
                <!-- L1: Primary toggle -->
                <label style="display:flex;align-items:flex-start;gap:6px;font-size:11px;color:#e2e8f0;cursor:pointer;">
                    <input type="checkbox" id="l1_{name}" {toggle_checked} onchange="toggleHeal('{name}', this.checked, document.getElementById('l2_{name}').checked)" style="accent-color:#6366f1;margin-top:2px;">
                    <div>
                        <strong>Auto-Restart</strong>
                        <div style="font-size:10px;color:#475569;margin-top:2px;">Restarts your agent automatically when it crashes</div>
                    </div>
                </label>
                <!-- L2: Nested sub-option, indented under L1 -->
                <div style="margin-left:22px;margin-top:8px;padding-left:12px;border-left:2px solid #334155;" class="l2-container" id="l2_container_{name}">
                    <label style="display:flex;align-items:flex-start;gap:6px;font-size:11px;color:#94a3b8;cursor:pointer;">
                        <input type="checkbox" id="l2_{name}" {l2_checked} onchange="toggleHealL2('{name}', this.checked)" style="{l2_cb_style}" {l2_extra_attrs}>
                        <div>
                            <strong style="color:#e2e8f0;">Proactive Maintenance</strong>
                            <div style="font-size:10px;color:#475569;margin-top:2px;">Fixes memory bloat, config drift, and token growth before failure</div>
                        </div>
                    </label>
                </div>
            </div>
            <div id="healResult_{name}" style="margin-top:4px;font-size:11px;"></div>
        </div>"""

    # Heal events table
    all_events = d.get_heal_events(limit=20)
    events_html = ""
    if all_events:
        for e in all_events[:10]:
            ts = e["created_at"]
            age = int(time.time()) - ts
            age_str = f"{age // 60}m ago" if age < 3600 else f"{age // 3600}h ago"
            icon = "✅" if e["status"] == "success" else "❌" if e["status"] in ("failure", "escalated") else "⏳"
            events_html += f"""<tr><td style="padding:6px 8px;font-size:11px;">{e['agent_name']}</td>
                <td style="padding:6px 8px;font-size:11px;">{e['event_type']}</td>
                <td style="padding:6px 8px;font-size:11px;">{icon} {e['status']}</td>
                <td style="padding:6px 8px;font-size:11px;color:#64748b;">{age_str}</td></tr>"""
    else:
        events_html = '<tr><td colspan="4" style="padding:12px;text-align:center;color:#64748b;font-size:12px;">No heal events recorded yet. Run a heal check or enable auto-heal.</td></tr>'

    return HTMLResponse(f"""{daemon_btn}
    <div style="margin-bottom:16px;">
        <div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:8px;">Per-Agent Configuration</div>
        {agent_rows if agent_rows else '<div class="empty-state">No agents discovered yet.</div>'}
    </div>
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:16px;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--border);font-size:12px;font-weight:600;color:var(--fg);">📋 Heal Events Log</div>
        <table class="data-table" style="width:100%;border-collapse:collapse;">
            <tr><th style="padding:6px 8px;font-size:10px;text-align:left;color:#64748b;">Agent</th>
                <th style="padding:6px 8px;font-size:10px;text-align:left;color:#64748b;">Type</th>
                <th style="padding:6px 8px;font-size:10px;text-align:left;color:#64748b;">Status</th>
                <th style="padding:6px 8px;font-size:10px;text-align:left;color:#64748b;">When</th></tr>
            {events_html}
        </table>
    </div>
    """)


@app.post("/api/heal-config/start-watch")
async def api_start_watch():
    """Start the observeco watch daemon in background."""
    try:
        import subprocess
        r = subprocess.run(["pgrep", "-f", "observeco watch"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return JSONResponse({"ok": True, "message": "Already running"})
        # Start watch in background
        subprocess.Popen(
            ["observeco", "watch"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return JSONResponse({"ok": True, "message": "Started"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@app.post("/api/heal-config/{agent_name}")
async def api_set_heal_config(agent_name: str, auto_heal: bool = False, auto_heal_l2: bool = False):
    """Toggle auto-heal for an agent."""
    try:
        d = Database()
        cfg = d.get_heal_config(agent_name)
        current = cfg[0] if cfg else {}
        d.set_heal_config(
            agent_name,
            auto_heal=auto_heal,
            auto_heal_l2=auto_heal_l2,
            max_restarts_per_hour=current.get("max_restarts_per_hour", 3),
            drift_threshold=current.get("drift_threshold", 15.0),
            memory_debt_threshold=current.get("memory_debt_threshold", 60),
        )
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/heal-config/{agent_name}/thresholds")
async def api_set_heal_thresholds(agent_name: str, max_restarts: int = 3,
                                   drift_threshold: float = 15.0,
                                   memory_debt: int = 60):
    """Update heal thresholds for an agent."""
    try:
        d = Database()
        cfg = d.get_heal_config(agent_name)
        current = cfg[0] if cfg else {}
        d.set_heal_config(
            agent_name,
            auto_heal=current.get("auto_heal", False),
            auto_heal_l2=current.get("auto_heal_l2", False),
            max_restarts_per_hour=max_restarts,
            drift_threshold=drift_threshold,
            memory_debt_threshold=memory_debt,
        )
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/trigger-heal", response_class=HTMLResponse)
async def api_trigger_heal():
    """Diagnose agents and return results as HTML."""
    d = Database()
    breakers = d.get_circuit_breakers()
    pulses = d.get_recent_pulses(limit=10)

    if not pulses and not breakers:
        return HTMLResponse('<div class="heal-result-ok">No agent data to diagnose. Run <code>observeco pulse check</code> first.</div>')

    items = []
    now = int(time.time())

    # Check each breaker
    for cb in breakers:
        if cb.get("tripped"):
            cooldown = cb.get("cooldown_until", now)
            _ = max(0, cooldown - now)  # unused — will use in cooldown display
            items.append(f"""
<div class="heal-entry fail">
    <div class="heal-entry-header">
        <span class="heal-action">🔴 {cb['agent_name']}</span>
        <span class="heal-time">now</span>
    </div>
    <div class="heal-detail">
        <strong>Diagnosis:</strong> circuit_tripped — {cb.get('failure_count',0)} failures<br>
        <strong>Recommendation:</strong> Acknowledge circuit manually or set auto-recovery (Pro)
    </div>
</div>""")

    # Check for agents with pulse issues (dead/error) and low pulses
    from collections import Counter
    agent_latest = {}
    for p in pulses:
        aname = p["agent_name"]
        if aname not in agent_latest:
            agent_latest[aname] = p

    # Flag dead/error agents first
    seen_heal = set()
    for aname, p in agent_latest.items():
        status = p.get("status", "")
        if status == "dead":
            seen_heal.add(aname)
            items.append(f"""
<div class="heal-entry fail">
    <div class="heal-entry-header">
        <span class="heal-action">🔴 {aname}</span>
        <span class="heal-time">now</span>
    </div>
    <div class="heal-detail">
        <strong>Diagnosis:</strong> agent_dead — no recent heartbeat<br>
        <strong>Recommendation:</strong> Restart agent or check agent process
    </div>
</div>""")
        elif status == "error":
            seen_heal.add(aname)
            err_msg = p.get("error_message", "") or "Error state"
            items.append(f"""
<div class="heal-entry warning">
    <div class="heal-entry-header">
        <span class="heal-action">🟡 {aname}</span>
        <span class="heal-time">now</span>
    </div>
    <div class="heal-detail">
        <strong>Diagnosis:</strong> agent_error — {err_msg[:100]}<br>
        <strong>Recommendation:</strong> Check error log for details
    </div>
</div>""")

    # Stasis detection: alive agents with no recent pulse (obs-autoheal-003)
    for aname, p in agent_latest.items():
        if aname in seen_heal:
            continue
        status = p.get("status", "")
        last_ts = p.get("timestamp", 0)
        if status == "alive" and last_ts and now - last_ts > 600:  # 10 min
            seen_heal.add(aname)
            last_check = _fmt_ts(last_ts)
            items.append(f"""
<div class="heal-entry warning">
    <div class="heal-entry-header">
        <span class="heal-action">🟡 {aname}</span>
        <span class="heal-time">{last_check}</span>
    </div>
    <div class="heal-detail">
        <strong>Diagnosis:</strong> agent_stasis — alive but no pulse for {(now - last_ts) // 60}m<br>
        <strong>Recommendation:</strong> Check if agent is stuck in a processing loop. Consider restart.
    </div>
</div>""")

    agent_counts = Counter(p.get("agent_name", "?") for p in pulses if now - p.get("timestamp", 0) < 600)

    for agent, count in agent_counts.most_common(10):
        if count < 2 and agent not in seen_heal:  # less than 2 recent pulses, not already flagged
            items.append(f"""
<div class="heal-entry warning">
    <div class="heal-info" style="display:flex;justify-content:space-between;align-items:center;">
        <span class="heal-action">🟡 {agent}</span>
        <span class="heal-time">now</span>
    </div>
    <div class="heal-detail">
        <strong>Diagnosis:</strong> low_heartbeat — {count} recent checks<br>
        <strong>Recommendation:</strong> Check if agent process is running
    </div>
</div>""")

    if not items:
        items.append('<div class="heal-result-ok">All agents appear healthy</div>')

    html = """
<div class="heal-timestamp">Heal check completed at """ + __import__('datetime').datetime.now().strftime("%H:%M:%S") + """</div>
""" + "\n".join(items)

    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# § Risk Dashboard — risk classifications + log integrity
# ---------------------------------------------------------------------------


@app.get("/api/risk", response_class=HTMLResponse)
async def api_risk():
    """Risk classification dashboard — shows risk policy + recent classifications."""
    try:
        # Get recent session logs
        from observeco.platform import get_data_dir
        from observeco.risk_engine import RISK_EMOJI, RiskLevel
        from observeco.session_log import SessionLogger
        sessions_dir = get_data_dir() / "sessions"
        sessions = []
        if sessions_dir.exists():
            for sf in sorted(sessions_dir.glob("*.jsonl"), reverse=True)[:10]:
                logger = SessionLogger(sf.stem)
                valid, error = logger.verify_chain()
                summary = logger.get_summary()
                sessions.append({
                    "id": sf.stem,
                    "events": summary["total_events"],
                    "tool_calls": summary["tool_calls"],
                    "valid": valid,
                    "decisions": summary["decisions"],
                })

        # Build risk policy display
        risk_rows = ""
        for level in RiskLevel:
            emoji = RISK_EMOJI.get(level, "?")
            if level == RiskLevel.LOW:
                desc = "Auto-approve (reads, searches, status)"
            elif level == RiskLevel.MEDIUM:
                desc = "Auto-approve configurable (edits, writes, tests)"
            elif level == RiskLevel.HIGH:
                desc = "Flag for review (push, deploy, env vars)"
            else:
                desc = "Deny (database, auth, destructive)"
            risk_rows += f"""
            <tr>
                <td>{emoji} <span class="risk-badge risk-{level.value}">{level.value.upper()}</span></td>
                <td>{desc}</td>
            </tr>"""

        # Build sessions table
        session_rows = """
        <tr><td colspan="5" style="color: var(--text-muted); padding: 16px;">No sessions recorded yet. Run <code>observeco run "task"</code> to generate data.</td></tr>"""
        if sessions:
            session_rows = ""
            for s in sessions:
                status_icon = "✓" if s["valid"] else "✗"
                status_color = "var(--green)" if s["valid"] else "var(--red)"
                decisions = _html_escape(", ".join(f"{k}: {v}" for k, v in s["decisions"].items()) or "none")
                session_rows += f"""
                <tr>
                    <td>{_html_escape(s["id"])}</td>
                    <td>{_html_escape(str(s["events"]))}</td>
                    <td>{_html_escape(str(s["tool_calls"]))}</td>
                    <td style="color: {status_color}">{status_icon} {'Valid' if s['valid'] else 'INVALID'}</td>
                    <td style="font-size: 0.85rem;">{decisions}</td>
                </tr>"""

        html = f"""
        <div class="risk-dashboard">
            <h3 style="margin-bottom: 16px;">Risk Classification Policy</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 32px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--border);">
                        <th style="text-align: left; padding: 8px;">Level</th>
                        <th style="text-align: left; padding: 8px;">Description</th>
                    </tr>
                </thead>
                <tbody>{risk_rows}</tbody>
            </table>

            <h3 style="margin-bottom: 16px;">Session Log Integrity</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--border);">
                        <th style="text-align: left; padding: 8px;">Session</th>
                        <th style="text-align: left; padding: 8px;">Events</th>
                        <th style="text-align: left; padding: 8px;">Tool Calls</th>
                        <th style="text-align: left; padding: 8px;">Chain</th>
                        <th style="text-align: left; padding: 8px;">Decisions</th>
                    </tr>
                </thead>
                <tbody>{session_rows}</tbody>
            </table>
        </div>
        """

        return HTMLResponse(html)
    except Exception as e:
        return HTMLResponse(f"<div class='error'>Risk dashboard error: {e}</div>")


# ---------------------------------------------------------------------------
# § Auto-Heal L2 — proactive trend detection
# ---------------------------------------------------------------------------


@app.get("/api/l2-scan", response_class=HTMLResponse)
async def api_l2_scan():
    """Run L2 scan and return results as HTML snippet."""
    from observeco.heal.l2 import get_l2_metrics, run_l2_scan
    results = run_l2_scan()
    metrics = get_l2_metrics()
    items = []
    for r in results:
        icon = {"memory_bloat": "📈", "stuck": "⏱️", "drift": "📋", "upstream_fail": "🌐"}
        sev_icon = {"warning": "🟡", "critical": "🔴", "info": "🔵"}
        items.append(f"""<div class="heal-entry warning">
    <div class="heal-entry-header"><span class="heal-action">{sev_icon.get('warning','⚠️')} {icon.get(r['trend_type'],'?')} {r['agent']}</span></div>
    <div class="heal-detail"><strong>{r['trend_type']}</strong> — metric: {r['metric']:.1f}</div>
</div>""")
    if not items:
        html = '<div class="heal-result-ok">✅ No L2 trends detected — all agents within normal parameters</div>'
    else:
        html = f'<div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">Detected {len(results)} trend(s)</div>' + "".join(items)
    html += f"""<div class="heal-trigger-section" style="margin-top:8px;">
    <span style="font-size:11px;color:#64748b;">{metrics['total_trends']} tracked · {metrics['resolution_rate']}% resolved</span>
</div>"""
    return HTMLResponse(html)


@app.get("/api/l2-trends", response_class=HTMLResponse)
async def api_l2_trends():
    """Show L2 trends as HTML snippet."""
    from observeco.heal.l2 import get_l2_metrics, get_l2_summary
    metrics = get_l2_metrics()
    trends = get_l2_summary(limit=20)
    items = []
    for t in trends:
        icon = "✅" if t["resolved"] else "⚠️"
        sev_c = {"warning": "#eab308", "critical": "#ef4444", "info": "#3b82f6"}
        color = sev_c.get(t["severity"], "#94a3b8")
        items.append(f"""<div class="heal-entry {'success' if t['resolved'] else 'warning'}">
    <div class="heal-entry-header">
        <span class="heal-action">{icon} {t['agent_name']} · {t['trend_type']}</span>
        <span class="heal-time" style="color:{color};">{t['severity']}</span>
    </div>
    <div class="heal-detail">{t['signal_label'][:80]}</div>
</div>""")
    if not items:
        html = '<div class="empty-state">📊 No trends recorded yet. Run L2 scan to start monitoring.</div>'
    else:
        html = "".join(items)
    html += f"""<div class="heal-trigger-section"><span style="font-size:11px;color:#64748b;">
    {metrics['total_trends']} total · {metrics['resolved_trends']} resolved · {metrics['unresolved_trends']} active</span></div>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# § Push Alerts — subscriptions + delivery log
# ---------------------------------------------------------------------------


@app.get("/api/alerts-subs", response_class=HTMLResponse)
async def api_alerts_subs():
    """Show alert subscriptions as HTML snippet - license-aware."""
    from observeco import license as lic
    from observeco.db import Database
    db = Database()
    is_pro = lic.require_pro()
    subs = db.get_alert_subscriptions()
    items = []
    for s in subs:
        icon = {"telegram": "📱", "slack": "💬", "webhook": "🔗", "email": "📧", "discord": "🎮"}
        items.append(f"""<div class="heal-entry info">
    <div class="heal-entry-header">
        <span class="heal-action">{icon.get(s['channel'],'?')} {s['channel']} → {_html_escape(s['target'][:50])}</span>
        <span class="heal-time">{'✅ Enabled' if s['enabled'] else '❌ Disabled'}</span>
    </div>
    <div class="heal-detail">Events: {s['event_types']}</div>
</div>""")
    if not items:
        if is_pro:
            html = '<div style="padding:16px;text-align:center;">' \
                '<div style="font-size:24px;margin-bottom:8px;">🔔</div>' \
                '<div style="font-size:13px;color:var(--fg-2);margin-bottom:6px;">No alert subscriptions yet.</div>' \
                '<div style="font-size:11px;color:var(--muted);margin-bottom:12px;">Set up channels via CLI or use the setup commands below.</div>' \
                '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;text-align:left;">' \
                '<div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;">' \
                '<div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:4px;">📱 Telegram</div>' \
                '<div style="font-size:10px;color:var(--muted);font-family:var(--font-mono);">observeco alerts subscribe telegram &lt;chat_id&gt;</div>' \
                '</div>' \
                '<div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;">' \
                '<div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:4px;">💬 Slack</div>' \
                '<div style="font-size:10px;color:var(--muted);font-family:var(--font-mono);">observeco alerts subscribe slack &lt;webhook_url&gt;</div>' \
                '</div>' \
                '<div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;">' \
                '<div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:4px;">📧 Email</div>' \
                '<div style="font-size:10px;color:var(--muted);font-family:var(--font-mono);">observeco alerts subscribe email &lt;address&gt;</div>' \
                '</div>' \
                '<div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;">' \
                '<div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:4px;">🎮 Discord</div>' \
                '<div style="font-size:10px;color:var(--muted);font-family:var(--font-mono);">observeco alerts subscribe discord &lt;webhook_url&gt;</div>' \
                '</div>' \
                '</div></div>'
        else:
            html = '<div class="empty-state" style="text-align:center;padding:16px;">' \
                '<div style="font-size:24px;margin-bottom:8px;">🔒</div>' \
                '<div style="font-size:13px;color:var(--fg-2);margin-bottom:6px;">Push Alerts are a Pro feature</div>' \
                '<div style="font-size:11px;color:var(--muted);margin-bottom:12px;">Free: dashboard-only alerts (you check manually). Pro adds Telegram, Slack, Email, and Discord push notifications.</div>' \
                '<div onclick="showBrainPro()" style="display:inline-block;padding:8px 20px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">Upgrade to Pro →</div>' \
                '</div>'
    else:
        html = "".join(items)
    return HTMLResponse(html)


@app.get("/api/alert-dashboard", response_class=HTMLResponse)
async def api_alert_dashboard():
    """Push Alerts Dashboard: integrated channel management with add/remove/test."""
    from observeco.db import Database
    d = Database()
    subs = d.get_alert_subscriptions()

    # Check provider config status
    _home = Path.home()
    _has_telegram_token = (_home / ".observeco" / "telegram_bot_token").exists()
    _has_smtp = (_home / ".observeco" / "smtp.json").exists()
    _telegram_token_preview = "Configured" if _has_telegram_token else ""
    _smtp_preview = ""
    if _has_smtp:
        try:
            _scfg = json.loads((_home / ".observeco" / "smtp.json").read_text())
            _smtp_preview = _scfg.get("host", "") + ":" + str(_scfg.get("port", ""))
        except Exception:
            _smtp_preview = "invalid config"

    # Channel health summary
    channel_health = {}
    recent_log = d.get_alert_log(limit=50)
    for entry in recent_log:
        ch = entry.get("channel", "")
        if ch not in channel_health:
            channel_health[ch] = {"total": 0, "failed": 0}
        channel_health[ch]["total"] += 1
        if not entry.get("delivered"):
            channel_health[ch]["failed"] += 1

    # Build subscribed channels list
    sub_rows = ""
    if subs:
        for s in subs:
            ch = s["channel"]
            tgt = s["target"]
            ch_icon = {"telegram": "📱", "discord": "🎮", "webhook": "🔗", "email": "📧"}
            health = channel_health.get(ch, {})
            fail_rate = (health.get("failed", 0) / max(health.get("total", 0), 1)) * 100
            health_icon = "🟢" if fail_rate < 20 else "🟡" if fail_rate < 50 else "🔴"
            masked = tgt[:30] + "..." if len(tgt) > 33 else tgt
            sub_rows += f"""
        <div class="heal-agent-row" style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px;margin-bottom:6px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:16px;">{ch_icon.get(ch, '?')}</span>
                    <div>
                        <div style="font-size:13px;font-weight:600;color:var(--fg);">{ch}</div>
                        <div style="font-size:10px;color:#64748b;">{_html_escape(masked)}</div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:10px;">{health_icon} {health.get("total", 0)} deliveries</span>
                    <button onclick="testAlertChannel({s['id']})" style="background:none;border:1px solid #334155;border-radius:4px;padding:3px 8px;font-size:10px;cursor:pointer;color:#94a3b8;">Test</button>
                    <button onclick="removeAlertChannel({s['id']})" style="background:none;border:1px solid #7f1d1d;border-radius:4px;padding:3px 8px;font-size:10px;cursor:pointer;color:#ef4444;">✕</button>
                </div>
            </div>
            <div id="testResult_{s['id']}" style="font-size:10px;margin-top:4px;"></div>
        </div>"""
    else:
        sub_rows = '<div class="empty-state" style="margin-bottom:8px;">No channels configured — add one below.</div>'

    # Available channels to add
    existing_channels = {s["channel"] for s in subs}
    avail = []
    for ch, icon, name in [("telegram", "📱", "Telegram Chat ID"), ("discord", "🎮", "Discord Webhook URL"),
                            ("webhook", "🔗", "Webhook URL"), ("email", "📧", "Email Address")]:
        if ch not in existing_channels:
            avail.append(f"""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:16px;">{icon}</span>
                <div style="flex:1;">
                    <div style="font-size:12px;font-weight:600;color:var(--fg);">{name}</div>
                    <div style="font-size:10px;color:#64748b;">{ch}</div>
                </div>
                <button onclick="showAddChannel('{ch}')" style="background:#6366f1;border:none;border-radius:4px;padding:4px 12px;font-size:10px;font-weight:600;cursor:pointer;color:white;">+ Add</button>
            </div>
        </div>""")

    return HTMLResponse(f"""
    <div style="margin-bottom:16px;">
        <div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:8px;">Active Channels</div>
        {sub_rows}
    </div>
    <div style="margin-bottom:16px;">
        <div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:8px;">Add Channel</div>
        {"".join(avail) if avail else '<div class="empty-state" style="font-size:11px;">All channels configured. Remove one to add a different type.</div>'}
    </div>
    <!-- Provider Settings -->
    <div style="margin-bottom:16px;">
        <div style="font-size:12px;font-weight:600;color:var(--fg);margin-bottom:8px;">⚙️ Provider Settings</div>
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:16px;">📱</span>
                <div style="flex:1;">
                    <div style="font-size:12px;font-weight:600;color:var(--fg);">Telegram Bot Token</div>
                    <div style="font-size:10px;color:#64748b;">{_telegram_token_preview if _has_telegram_token else 'Not configured — needed for Telegram alerts'}</div>
                </div>
                <button onclick="showTelegramTokenConfig()" style="background:#6366f1;border:none;border-radius:4px;padding:4px 12px;font-size:10px;font-weight:600;cursor:pointer;color:white;">{ 'Update' if _has_telegram_token else 'Set Token' }</button>
            </div>
        </div>
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:16px;">📧</span>
                <div style="flex:1;">
                    <div style="font-size:12px;font-weight:600;color:var(--fg);">SMTP Relay</div>
                    <div style="font-size:10px;color:#64748b;">{_smtp_preview if _has_smtp else 'Not configured — needed for email alerts'}</div>
                </div>
                <button onclick="showSmtpConfig()" style="background:#6366f1;border:none;border-radius:4px;padding:4px 12px;font-size:10px;font-weight:600;cursor:pointer;color:white;">{ 'Update' if _has_smtp else 'Set SMTP' }</button>
            </div>
        </div>
    </div>
    <!-- Add channel modal (hidden until triggered) -->
    <div class="modal-overlay" id="addChannelModal" style="display:none;" onclick="if(event.target===this)closeAddChannel()">
        <div class="modal" style="max-width:420px;" onmousedown="event.stopPropagation()">
            <div class="modal-body">
                <div style="font-size:15px;font-weight:600;color:var(--fg);margin-bottom:8px;" id="addChannelTitle">Add Channel</div>
                <div style="font-size:12px;color:#94a3b8;margin-bottom:12px;">Enter the target URL, chat ID, or email address.</div>
                <input id="addChannelTarget" type="text" placeholder="https://discord.com/api/webhooks/..." style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;margin-bottom:8px;font-family:inherit;">
                <div style="display:flex;gap:8px;justify-content:flex-end;">
                    <button onclick="closeAddChannel()" class="modal-close" style="font-size:12px;padding:8px 18px;width:auto;">Cancel</button>
                    <button onclick="confirmAddChannel()" class="heal-trigger-btn" style="font-size:12px;padding:8px 18px;">Test & Save</button>
                </div>
                <div id="addChannelResult" style="margin-top:8px;font-size:12px;"></div>
            </div>
        </div>
    </div>
    <!-- Telegram Bot Token modal -->
    <div class="modal-overlay" id="telegramTokenModal" style="display:none;" onclick="if(event.target===this)closeTelegramToken()">
        <div class="modal" style="max-width:420px;" onmousedown="event.stopPropagation()">
            <div class="modal-body">
                <div style="font-size:15px;font-weight:600;color:var(--fg);margin-bottom:8px;">🤖 Telegram Bot Token</div>
                <div style="font-size:12px;color:#94a3b8;margin-bottom:12px;">Paste your bot token from <a href="https://t.me/BotFather" target="_blank" style="color:#6366f1;">@BotFather</a>. It will be tested before saving.</div>
                <input id="telegramTokenInput" type="password" placeholder="123456:ABCdefGHIjklMNOpqrsTUVwxyz" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;margin-bottom:8px;font-family:var(--font-mono);">
                <div style="display:flex;gap:8px;justify-content:flex-end;">
                    <button onclick="closeTelegramToken()" class="modal-close" style="font-size:12px;padding:8px 18px;width:auto;">Cancel</button>
                    <button onclick="saveTelegramToken()" class="heal-trigger-btn" style="font-size:12px;padding:8px 18px;">Save & Verify</button>
                </div>
                <div id="telegramTokenResult" style="margin-top:8px;font-size:12px;"></div>
            </div>
        </div>
    </div>
    <!-- SMTP Config modal -->
    <div class="modal-overlay" id="smtpConfigModal" style="display:none;" onclick="if(event.target===this)closeSmtpConfig()">
        <div class="modal" style="max-width:440px;" onmousedown="event.stopPropagation()">
            <div class="modal-body">
                <div style="font-size:15px;font-weight:600;color:var(--fg);margin-bottom:8px;">📧 SMTP Relay</div>
                <div style="font-size:12px;color:#94a3b8;margin-bottom:12px;">Configure an SMTP server for email alert delivery.</div>
                <input id="smtpHost" type="text" placeholder="smtp.gmail.com" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;margin-bottom:6px;font-family:inherit;">
                <div style="display:flex;gap:6px;margin-bottom:6px;">
                    <input id="smtpPort" type="number" placeholder="587" value="587" style="flex:0 0 80px;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;font-family:inherit;">
                    <select id="smtpSecurity" style="flex:1;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;">
                        <option value="starttls">STARTTLS (587)</option>
                        <option value="ssl">SSL/TLS (465)</option>
                        <option value="none">No encryption</option>
                    </select>
                </div>
                <input id="smtpUser" type="text" placeholder="you@gmail.com" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;margin-bottom:6px;font-family:inherit;">
                <input id="smtpPassword" type="password" placeholder="App password or SMTP password" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;margin-bottom:6px;font-family:inherit;">
                <input id="smtpFrom" type="text" placeholder="From: alerts@example.com" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--fg);font-size:13px;margin-bottom:8px;font-family:inherit;">
                <div style="display:flex;gap:8px;justify-content:flex-end;">
                    <button onclick="closeSmtpConfig()" class="modal-close" style="font-size:12px;padding:8px 18px;width:auto;">Cancel</button>
                    <button onclick="saveSmtpConfig()" class="heal-trigger-btn" style="font-size:12px;padding:8px 18px;">Save & Test</button>
                </div>
                <div id="smtpConfigResult" style="margin-top:8px;font-size:12px;"></div>
            </div>
        </div>
    </div>
    <script>
    var _pendingChannel = '';
    function showAddChannel(channel) {{
        _pendingChannel = channel;
        document.getElementById('addChannelTitle').textContent = '+ Add ' + channel;
        document.getElementById('addChannelTarget').placeholder = {{
            'telegram': 'Chat ID (e.g. 123456789)',
            'discord': 'Webhook URL (https://discord.com/api/webhooks/...)',
            'webhook': 'Webhook URL (https://hooks.example.com/alerts)',
            'email': 'Email address (you@example.com)'
        }}[channel] || 'Target value';
        document.getElementById('addChannelTarget').value = '';
        document.getElementById('addChannelResult').innerHTML = '';
        document.getElementById('addChannelModal').style.display = 'flex';
    }}
    function closeAddChannel() {{
        document.getElementById('addChannelModal').style.display = 'none';
    }}
    function confirmAddChannel() {{
        var target = document.getElementById('addChannelTarget').value.trim();
        if (!target) {{ document.getElementById('addChannelResult').innerHTML = '<span style="color:#ef4444;">❌ Target required</span>'; return; }}
        document.getElementById('addChannelResult').innerHTML = '<span style="color:#64748b;">Testing...</span>';
        fetch('/api/alert-subscribe', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{channel: _pendingChannel, target: target, event_types: 'all'}})
        }})
        .then(r => r.json())
        .then(data => {{
            if (data.status === 'ok') {{
                document.getElementById('addChannelResult').innerHTML = '<span style="color:#22c55e;">✅ Saved! Sending test alert...</span>';
                fetch('/api/alert-test/' + data.subscription.id, {{method: 'POST'}})
                    .then(r => r.json())
                    .then(t => {{
                        if (t.ok) {{
                            document.getElementById('addChannelResult').innerHTML = '<span style="color:#22c55e;">✅ Channel added and test alert sent!</span>';
                        }} else {{
                            document.getElementById('addChannelResult').innerHTML = '<span style="color:#fde68a;">⚠️ Saved but test failed: ' + (t.error || '') + '</span>';
                        }}
                        setTimeout(() => {{ closeAddChannel(); htmx.ajax('GET', '/api/alert-dashboard', {{target: '#alertPanel', swap: 'innerHTML'}}) }}, 1500);
                    }})
                    .catch(() => {{ setTimeout(() => {{ closeAddChannel(); htmx.ajax('GET', '/api/alert-dashboard', {{target: '#alertPanel', swap: 'innerHTML'}}) }}, 1500); }});
            }} else {{
                document.getElementById('addChannelResult').innerHTML = '<span style="color:#ef4444;">❌ ' + (data.error || 'Failed') + '</span>';
            }}
        }})
        .catch(e => {{
            document.getElementById('addChannelResult').innerHTML = '<span style="color:#ef4444;">❌ ' + e.message + '</span>';
        }});
    }}
    function testAlertChannel(subId) {{
        var el = document.getElementById('testResult_' + subId);
        el.innerHTML = '<span style="color:#64748b;">Sending test...</span>';
        fetch('/api/alert-test/' + subId, {{method: 'POST'}})
            .then(r => r.json())
            .then(data => {{
                el.innerHTML = data.ok ? '<span style="color:#22c55e;">✅ Test alert sent</span>' : '<span style="color:#ef4444;">❌ ' + (data.error || '') + '</span>';
                setTimeout(() => {{ el.innerHTML = ''; }}, 3000);
            }})
            .catch(e => {{ el.innerHTML = '<span style="color:#ef4444;">❌ ' + e.message + '</span>'; }});
    }}
    function removeAlertChannel(subId) {{
        if (!confirm('Remove this alert channel?')) return;
        fetch('/api/alert-subscribe/' + subId, {{method: 'DELETE'}})
            .then(r => r.json())
            .then(data => {{
                if (data.status === 'ok') htmx.ajax('GET', '/api/alert-dashboard', {{target: '#alertPanel', swap: 'innerHTML'}});
            }})
            .catch(() => {{}});
    }}

    // ─── Provider Config ───
    function showTelegramTokenConfig() {{
        document.getElementById('telegramTokenInput').value = '';
        document.getElementById('telegramTokenResult').innerHTML = '';
        document.getElementById('telegramTokenModal').style.display = 'flex';
    }}
    function closeTelegramToken() {{
        document.getElementById('telegramTokenModal').style.display = 'none';
    }}
    function saveTelegramToken() {{
        var token = document.getElementById('telegramTokenInput').value.trim();
        if (!token) {{ document.getElementById('telegramTokenResult').innerHTML = '<span style="color:#ef4444;">❌ Token required</span>'; return; }}
        document.getElementById('telegramTokenResult').innerHTML = '<span style="color:#64748b;">Saving and testing...</span>';
        fetch('/api/provider-config/telegram', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{token: token}})
        }})
        .then(r => r.json())
        .then(data => {{
            if (data.ok) {{
                document.getElementById('telegramTokenResult').innerHTML = '<span style="color:#22c55e;">✅ Token saved and verified!</span>';
                setTimeout(() => {{ closeTelegramToken(); htmx.ajax('GET', '/api/alert-dashboard', {{target: '#alertPanel', swap: 'innerHTML'}}); }}, 1500);
            }} else {{
                document.getElementById('telegramTokenResult').innerHTML = '<span style="color:#ef4444;">❌ ' + (data.error || 'Failed') + '</span>';
            }}
        }})
        .catch(e => {{ document.getElementById('telegramTokenResult').innerHTML = '<span style="color:#ef4444;">❌ ' + e.message + '</span>'; }});
    }}
    function showSmtpConfig() {{
        document.getElementById('smtpHost').value = '';
        document.getElementById('smtpPort').value = '587';
        document.getElementById('smtpUser').value = '';
        document.getElementById('smtpPassword').value = '';
        document.getElementById('smtpFrom').value = '';
        document.getElementById('smtpConfigResult').innerHTML = '';
        document.getElementById('smtpConfigModal').style.display = 'flex';
    }}
    function closeSmtpConfig() {{
        document.getElementById('smtpConfigModal').style.display = 'none';
    }}
    function saveSmtpConfig() {{
        var host = document.getElementById('smtpHost').value.trim();
        var port = document.getElementById('smtpPort').value.trim() || '587';
        var security = document.getElementById('smtpSecurity').value;
        var user = document.getElementById('smtpUser').value.trim();
        var password = document.getElementById('smtpPassword').value.trim();
        var from = document.getElementById('smtpFrom').value.trim();
        if (!host) {{ document.getElementById('smtpConfigResult').innerHTML = '<span style="color:#ef4444;">❌ SMTP host required</span>'; return; }}
        document.getElementById('smtpConfigResult').innerHTML = '<span style="color:#64748b;">Saving and testing...</span>';
        fetch('/api/provider-config/smtp', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{host: host, port: parseInt(port), security: security, user: user, password: password, from: from}})
        }})
        .then(r => r.json())
        .then(data => {{
            if (data.ok) {{
                document.getElementById('smtpConfigResult').innerHTML = '<span style="color:#22c55e;">✅ SMTP saved and verified!</span>';
                setTimeout(() => {{ closeSmtpConfig(); htmx.ajax('GET', '/api/alert-dashboard', {{target: '#alertPanel', swap: 'innerHTML'}}); }}, 1500);
            }} else {{
                document.getElementById('smtpConfigResult').innerHTML = '<span style="color:#ef4444;">❌ ' + (data.error || 'Failed') + '</span>';
            }}
        }})
        .catch(e => {{ document.getElementById('smtpConfigResult').innerHTML = '<span style="color:#ef4444;">❌ ' + e.message + '</span>'; }});
    }}
    </script>
    """)


@app.post("/api/alert-test/{sub_id}")
async def api_alert_test(sub_id: int):
    """Send a test alert to a subscription."""
    from observeco.db import Database
    d = Database()
    subs = d.get_alert_subscriptions()
    sub = next((s for s in subs if s["id"] == sub_id), None)
    if not sub:
        return JSONResponse({"ok": False, "error": "Subscription not found"})
    from observeco.alerts.push import push_alert
    try:
        results = push_alert("test", f"🧪 Test alert from ObserveCo — if you see this, push alerts are working! Sent at {__import__('datetime').datetime.now().strftime('%H:%M:%S')}", db=d)
        # Check if the specific channel was delivered
        for r in results:
            if r.get("channel") == sub["channel"] and r.get("delivered"):
                return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": "Delivery failed — check your target value"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@app.get("/api/alert-log", response_class=HTMLResponse)
async def api_alert_log():
    """Show alert delivery log as HTML snippet."""
    from observeco.db import Database
    db = Database()
    log = db.get_alert_log(limit=15)
    now = int(time.time())

    if not log:
        from observeco import license as lic
        is_pro = lic.require_pro()
        if is_pro:
            return HTMLResponse('<div class="empty-state" style="padding:20px;text-align:center;"><div style="font-size:24px;margin-bottom:8px;">📭</div><div style="color:#94a3b8;font-size:13px;">No alerts delivered yet.</div><div style="color:#64748b;font-size:11px;margin-top:4px;">Set up a subscription via <code style="background:var(--surface);padding:2px 6px;border-radius:4px;">observeco alerts subscribe telegram &lt;chat_id&gt;</code> or <code style="background:var(--surface);padding:2px 6px;border-radius:4px;">observeco alerts subscribe discord &lt;webhook_url&gt;</code></div></div>')
        else:
            return HTMLResponse('<div class="empty-state" style="padding:20px;text-align:center;"><div style="font-size:24px;margin-bottom:8px;">🔒</div><div style="color:#94a3b8;font-size:13px;">Dashboard-only alerts (free tier).</div><div style="color:#64748b;font-size:11px;margin-top:4px;">Upgrade to Pro for Telegram, Slack, Email, and Discord push notifications.</div></div>')

    items = []
    for entry in log:
        icon = "✅" if entry["delivered"] else "❌"
        ts = entry.get("created_at", 0)
        age_m = (now - ts) // 60
        if age_m < 60:
            age_str = f"{age_m}m ago"
        elif age_m < 1440:
            age_str = f"{age_m // 60}h ago"
        else:
            age_str = f"{age_m // 1440}d ago"

        items.append(f"""<div class="heal-entry {'success' if entry['delivered'] else 'fail'}" style="margin-bottom:4px;">
    <div class="heal-entry-header">
        <span class="heal-action">{icon} {entry['channel']} → {_html_escape(entry['target'][:40])}</span>
        <span style="font-size:10px;color:#475569;">{age_str}</span>
    </div>
    <div class="heal-detail" style="display:flex;justify-content:space-between;">
        <span>{_html_escape(entry['message'][:80])}</span>
        <span style="font-size:9px;color:#475569;">{entry['event_type']}</span>
    </div>
</div>""")

    html = "".join(items)
    return HTMLResponse(f"""<div style="font-size:10px;color:#64748b;margin-bottom:8px;">Last {len(log)} deliveries:</div>{html}""")


@app.post("/api/check-drift-alerts")
async def api_check_drift_alerts():
    """Check drift data and push alerts for breached thresholds — Drift Alerts feature."""
    from observeco import license as lic
    if not lic.require_pro():
        return JSONResponse({"ok": False, "error": "Drift alerts require Pro"}, status_code=402)

    drift = db.get_drift()
    breached = [d for d in drift if d.get("breached")]
    if not breached:
        return JSONResponse({"ok": True, "checked": 0, "fired": 0, "detail": "No drift breaches found"})

    from observeco.alerts.push import push_alert
    # Deduplicate: one alert per agent per run, skip if logged within last hour
    now = int(time.time())
    recent = db.get_alert_log(limit=50)
    recent_agents = set()
    one_hour_ago = now - 3600
    for r in recent:
        if r.get("event_type") == "drift" and r.get("created_at", 0) > one_hour_ago:
            msg = r.get("message", "")
            # Extract agent name from "[Drift: agent_name ...]" pattern
            for part in msg.split():
                p = part.strip("📈:, ")
                if p and p not in ("Drift", "grew"):
                    recent_agents.add(p.lower())
                    break

    fired = 0
    seen_agents = set()
    for d in breached:
        agent = d.get("agent_name", "")
        if not agent or agent.lower() in seen_agents or agent.lower() in recent_agents:
            continue
        seen_agents.add(agent.lower())
        delta = d.get("delta_pct", 0)
        component = d.get("component", "unknown")
        msg = f"📈 Drift: {agent} — {component} grew {delta:+.1f}% (exceeded threshold)"
        push_alert("drift", msg, agent_name=agent, db=db)
        fired += 1

    return JSONResponse({"ok": True, "checked": len(breached), "fired": fired, "detail": f"{fired} drift alert(s) sent"})


@app.post("/api/alert-subscribe")
async def api_alert_subscribe(request: Request):
    """Subscribe to push alerts via API — Pro feature."""
    from observeco import license as lic
    if not lic.require_pro():
        return JSONResponse({"error": "Push alerts require Pro — start a free trial"}, status_code=402)
    from observeco.db import Database
    db = Database()
    try:
        body = await request.json()
        channel = body.get("channel", "telegram")
        target = body.get("target", "")
        event_types = body.get("event_types", "all")
        if not target:
            return JSONResponse({"error": "target required"}, status_code=400)
        # Validate Discord URLs — reject invite links
        if channel == "discord":
            if "discord.gg/" in target.lower() or "discord.com/invite/" in target.lower():
                return JSONResponse({"error": "That's a Discord invite link, not a webhook URL. Webhooks look like: https://discord.com/api/webhooks/123456/abc-def"}, status_code=400)
            if not target.startswith("https://discord.com/api/webhooks/"):
                return JSONResponse({"error": "Discord webhook URL must start with https://discord.com/api/webhooks/..."}, status_code=400)
        result = db.add_alert_subscription(channel, target, event_types)
        return JSONResponse({"status": "ok", "subscription": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.delete("/api/alert-subscribe/{sub_id}")
async def api_alert_unsubscribe(sub_id: int):
    """Remove an alert subscription."""
    from observeco.db import Database
    db = Database()
    db.delete_alert_subscription(sub_id)
    return JSONResponse({"status": "ok"})


# ─── Provider Config API ───


@app.post("/api/provider-config/telegram")
async def api_provider_telegram(request: Request):
    """Save and verify Telegram bot token."""
    try:
        body = await request.json()
        token = body.get("token", "").strip()
        if not token or ":" not in token:
            return JSONResponse({"ok": False, "error": "Invalid token format — get one from @BotFather"})
        # Save to file
        tok_path = Path.home() / ".observeco" / "telegram_bot_token"
        tok_path.parent.mkdir(parents=True, exist_ok=True)
        tok_path.write_text(token.strip())
        # Test by calling getMe
        import requests as _req
        resp = _req.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            bot_name = resp.json().get("result", {}).get("first_name", "Bot")
            return JSONResponse({"ok": True, "bot": bot_name})
        return JSONResponse({"ok": False, "error": f"Telegram rejected token: HTTP {resp.status_code}"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@app.post("/api/provider-config/smtp")
async def api_provider_smtp(request: Request):
    """Save and verify SMTP config."""
    try:
        body = await request.json()
        host = body.get("host", "").strip()
        port = body.get("port", 587)
        user = body.get("user", "").strip()
        password = body.get("password", "").strip()
        from_addr = body.get("from", "").strip() or user
        if not host:
            return JSONResponse({"ok": False, "error": "SMTP host required"})
        # Save to file
        cfg = {"host": host, "port": port, "user": user, "password": password, "from": from_addr}
        cfg_path = Path.home() / ".observeco" / "smtp.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(cfg, indent=2))
        # Test by connecting
        import smtplib as _smtp
        _smtp = _smtp  # bind to satisfy linter
        server = _smtp.SMTP(host, port, timeout=10)
        server.starttls()
        if user:
            server.login(user, password)
        server.quit()
        return JSONResponse({"ok": True})
    except _smtp.SMTPAuthenticationError:
        return JSONResponse({"ok": False, "error": "SMTP authentication failed — check username/password"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Connection failed: {e}"})


# ---------------------------------------------------------------------------
# § OpenClaw Plugin tracking
# ---------------------------------------------------------------------------


@app.get("/api/plugin-stats")
async def api_plugin_stats(agent: str = ""):
    """Get plugin tracking stats as JSON."""
    from observeco.clawforge.plugin import get_plugin_stats, get_recent_hooks
    stats = get_plugin_stats(agent)
    # Detect demo data: all hooks share the exact same timestamp
    hooks = get_recent_hooks(agent, limit=100)
    ts_set = {h.get("timestamp", 0) for h in hooks}
    stats["is_demo"] = len(ts_set) <= 1 and len(hooks) > 0
    return JSONResponse(stats)


@app.get("/api/plugin-hooks", response_class=HTMLResponse)
async def api_plugin_hooks(agent: str = ""):
    """Show recent plugin hooks as HTML snippet."""
    from observeco.clawforge.plugin import get_recent_hooks
    hooks = get_recent_hooks(agent, limit=10)
    items = []
    now = int(time.time())
    for h in hooks:
        red_pct = round((h["sources_skipped"] / max(h["sources_loaded"] + h["sources_skipped"], 1)) * 100, 1)
        icon = {"bootstrap": "📥", "ingest": "🔍", "pre_response": "📊"}
        # Format timestamp — show relative for recent, absolute for older
        ts = h.get("timestamp", 0)
        ts_dt = datetime.fromtimestamp(ts) if ts else None
        ts_abs = ts_dt.strftime("%b %d %H:%M") if ts_dt else "?"
        age_m = (now - ts) // 60 if ts else 999999
        if age_m < 1:
            ts_display = "just now"
        elif age_m < 60:
            ts_display = f"{age_m}m"
        elif age_m < 1440:
            ts_display = f"{age_m // 60}h"
        else:
            ts_display = ts_abs  # Show actual date for old events
        full_ts = f"{ts_abs} ({ts_display})"
        items.append(f"""<div class="heal-entry info">
    <div class="heal-entry-header">
        <span class="heal-action">{icon.get(h['hook_point'],'?')} {h['agent_name']} · {_html_escape(h.get('intent_class','') or h['hook_point'])}</span>
        <span class="heal-time" title="{ts_abs}">{full_ts}</span>
    </div>
    <div class="heal-detail">Loaded {h['sources_loaded']} · Skipped {h['sources_skipped']} · Saved {h['tokens_saved']} tok ({red_pct}%)</div>
</div>""")
    if not items:
        html = '<div class="empty-state">🔌 No plugin hooks recorded yet.</div>'
    else:
        html = "".join(items)
    return HTMLResponse(html)


@app.post("/api/plugin-log")
async def api_plugin_log(request: Request):
    """Log a plugin hook event."""
    from observeco.clawforge.plugin import log_plugin_hook
    try:
        body = await request.json()
        result = log_plugin_hook(
            agent_name=body.get("agent_name", ""),
            hook_point=body.get("hook_point", "ingest"),
            intent_class=body.get("intent_class", ""),
            sources_loaded=body.get("sources_loaded", 0),
            sources_skipped=body.get("sources_skipped", 0),
            tokens_saved=body.get("tokens_saved", 0),
            context_window_pct=body.get("context_window_pct", 0),
        )
        return JSONResponse({"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ---------------------------------------------------------------------------
# § Per-Turn Token Tracking (#14)
# ---------------------------------------------------------------------------


@app.post("/api/tokens/log")
async def api_token_log(request: Request):
    """Ingest per-turn token usage from agents."""
    from observeco.tracking.tokens import log_token_turn
    try:
        body = await request.json()
        result = log_token_turn(
            agent_name=body.get("agent_name", ""),
            turn_id=body.get("turn_id", ""),
            total_tokens=body.get("total_tokens", 0),
            identity_tokens=body.get("identity_tokens", 0),
            skills_tokens=body.get("skills_tokens", 0),
            memory_tokens=body.get("memory_tokens", 0),
            tools_tokens=body.get("tools_tokens", 0),
            guidance_tokens=body.get("guidance_tokens", 0),
            provider=body.get("provider", ""),
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/tokens/summary")
async def api_token_summary(agent: str = "", days: int = 7):
    """Get aggregate token summary per agent."""
    from observeco.tracking.tokens import get_token_summary
    stats = get_token_summary(agent, days)
    return JSONResponse(stats)


@app.get("/api/tokens/trends")
async def api_token_trends(agent: str = "", days: int = 7):
    """Get component growth trends."""
    from observeco.tracking.tokens import get_trend_analysis
    analysis = get_trend_analysis(agent)
    return JSONResponse(analysis)


@app.get("/api/tokens/recent", response_class=HTMLResponse)
async def api_token_recent(agent: str = "", days: int = 7):
    """Show recent token turns as HTML snippet."""
    from observeco.db import Database
    db = Database()
    since = int(time.time()) - days * 86400
    turns = db.get_token_turns(agent, limit=20, since=since)
    if not turns:
        return HTMLResponse('<div class="empty-state">📊 No token data recorded yet. Agents can POST /api/tokens/log to start tracking.</div>')
    items = []
    for t in turns[:15]:
        icon = "📈"
        if t.get("anomaly_score") and abs(t["anomaly_score"]) > 2:
            icon = "🔴" if abs(t["anomaly_score"]) > 3 else "🟡"
        ts = _fmt_ts(t["recorded_at"])
        cost_str = f" · ${t['cost']:.4f}" if t["cost"] else ""
        anomaly_str = f" · {t['anomaly_score']:.1f}σ" if t.get("anomaly_score") else ""
        items.append(f"""<div class="heal-entry info">
    <div class="heal-entry-header">
        <span class="heal-action">{icon} {t['agent_name']} · {t['total_tokens']:,} tok{cost_str}{anomaly_str}</span>
        <span class="heal-time">{ts}</span>
    </div>
    <div class="heal-detail">{t.get('turn_id', '?')} · Provider: {t.get('provider', '?')}</div>
</div>""")
    return HTMLResponse("".join(items))


@app.post("/api/tokens/budget")
async def api_token_budget(request: Request):
    """Set per-agent token budget."""
    from observeco.db import Database
    db = Database()
    try:
        body = await request.json()
        db.set_token_budget(
            agent_name=body.get("agent_name", ""),
            max_daily_tokens=body.get("max_daily_tokens", 0),
            max_turn_cost=body.get("max_turn_cost", 0),
            anomaly_threshold_sigma=body.get("anomaly_threshold_sigma", 3.0),
        )
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/tokens/budgets")
async def api_token_budgets(agent: str = ""):
    """List token budgets."""
    from observeco.db import Database
    db = Database()
    budgets = db.get_token_budgets(agent)
    return JSONResponse({"budgets": budgets})


# ---------------------------------------------------------------------------
# § Extended History (#18) — retention + L2 baselines
# ---------------------------------------------------------------------------


@app.get("/api/prune")
async def api_prune():
    """Run pruning operation and return result."""
    from observeco.tracking.prune import run_prune
    result = run_prune()
    return JSONResponse(result)


@app.get("/api/retention-config")
async def api_retention_config():
    """Get current retention configuration."""
    from observeco.db import Database
    db = Database()
    config = db.get_retention_config()
    return JSONResponse(config)


@app.post("/api/retention-config")
async def api_set_retention(request: Request):
    """Update retention config."""
    from observeco.db import Database
    db = Database()
    try:
        body = await request.json()
        data_type = body.get("data_type", "")
        days = body.get("days", "7")
        if data_type:
            db.set_retention_days(data_type, str(days))
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/l2/baseline")
async def api_l2_baseline(agent: str = "", days: int = 7):
    """Compute L2 baselines for an agent or all agents."""
    from observeco.tracking.baselines import compute_all_baselines, compute_baselines
    if agent:
        result = compute_baselines(agent, days)
    else:
        result = compute_all_baselines(days)
    return JSONResponse(result)


@app.get("/api/l2/baselines", response_class=HTMLResponse)
async def api_l2_baselines_html(agent: str = "", days: int = 7):
    """Show L2 baselines as HTML snippet."""
    from observeco.tracking.baselines import compute_all_baselines, compute_baselines
    if agent:
        baselines = {agent: compute_baselines(agent, days)}
    else:
        baselines = compute_all_baselines(days)
    items = []
    for name, bl in baselines.items():
        if "error" in bl:
            items.append(f"""<div class="heal-entry fail">
    <div class="heal-entry-header"><span class="heal-action">❌ {name}</span></div>
    <div class="heal-detail">Error: {bl['error']}</div>
</div>""")
        else:
            err_color = "#ef4444" if bl.get("error_rate_per_day", 0) > 1 else "#22c55e"
            items.append(f"""<div class="heal-entry info">
    <div class="heal-entry-header">
        <span class="heal-action">📊 {name}</span>
        <span class="heal-time">{bl.get('sample_days', '?')}d</span>
    </div>
    <div class="heal-detail">
        P95: {bl.get('p95_latency_ms', 0):.0f}ms · Tokens: {bl.get('avg_token_per_turn', 0):.0f}/turn · Turns: {bl.get('total_turns', 0)} ·
        <span style="color:{err_color};">Errors: {bl.get('error_rate_per_day', 0)}/day</span>
    </div>
</div>""")
    if not items:
        html = '<div class="empty-state">📊 No baseline data yet. Run pulse checks and log some tokens first.</div>'
    else:
        html = "".join(items)
    return HTMLResponse(html)


@app.get("/api/history", response_class=HTMLResponse)
async def api_history():
    """Show extended history data availability."""
    from observeco.db import Database
    db = Database()
    config = db.get_retention_config()
    counts = {}
    for dt in ["pulse_log", "errors", "chisel_drift", "token_logs", "l2_trending"]:
        try:
            row = db._get_conn().execute(f"SELECT COUNT(*) as c FROM {dt}").fetchone()
            counts[dt] = row["c"] if row else 0
        except Exception:
            counts[dt] = 0
    total = sum(counts.values())
    items = []
    for table, count in counts.items():
        days = config.get(f"{table.replace('_log','').replace('chisel_','').replace('l2_','')}_days", "7")
        items.append(f"""<div class="heal-entry info">
    <div class="heal-entry-header">
        <span class="heal-action">📁 {table}</span>
        <span class="heal-time">{count:,} rows</span>
    </div>
    <div class="heal-detail">Retention: {days}d · Pruning: {"✅ On" if config.get("pruning_enabled", "1") != "0" else "❌ Off"}</div>
</div>""")
    html = f"<div style='font-size:12px;color:#94a3b8;margin-bottom:8px;'>Total: {total:,} rows across 5 data stores</div>" + "".join(items)
    return HTMLResponse(html)


@app.get("/api/health/l1")
async def api_health_l1():
    """L1 health check — OTEL listener, dashboard, database status."""
    import socket
    otel_up = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        otel_up = s.connect_ex(("127.0.0.1", 4318)) == 0
        s.close()
    except Exception:
        logger.exception("swallowed exception in server.py")
    db_ok = True
    try:
        from observeco.db import get_engine
        with get_engine().connect() as conn:
            conn.execute(conn.default_schema_name or "SELECT 1")
    except Exception:
        db_ok = False

    components = {
        "otel_listener": "up" if otel_up else "down",
        "dashboard": "up",
        "database": "up" if db_ok else "down",
    }
    statuses = list(components.values())
    if all(s == "up" for s in statuses):
        overall = "healthy"
    elif any(s == "down" for s in statuses):
        overall = "critical"
    else:
        overall = "degraded"

    return {"overall": overall, "level1": components}


@app.get("/api/config-health", response_class=HTMLResponse)
async def api_config_health():
    """Config hygiene widget — always visible (free sees diagnostics, Pro gets fixes)."""
    from observeco.chisel.config_widget import generate_widget_html
    return HTMLResponse(generate_widget_html())


# ── Per-agent LLM summary (Tier 2 shallow — §3.25) ─────────────────
PER_AGENT_SUMMARY_PROMPT = """You are an agent observability dashboard. Given raw metrics, generate a one-paragraph plain-language summary.

Agent: {name}
Status: {status}
Latency: {latency_ms}ms
Errors (24h): {error_count}
Restarts (24h): {restart_count}
Drift: {drift}
Memory debt: {memory_debt}

Keep it under 40 words. Focus on what matters: is it healthy, what changed."""


@app.get("/api/agent-summary/{name}", response_class=HTMLResponse)
async def api_agent_summary(name: str):
    """Per-agent LLM-generated summary — Tier 2 shallow. Falls back to raw metrics."""
    from observeco.llm_service import ask

    agents = db.get_agents()
    agent = next((a for a in agents if a["agent_name"] == name), None)
    if not agent:
        return HTMLResponse("<span style='color:#64748b;font-size:12px;'>Unknown agent</span>")

    pulses = db.get_recent_pulses(name, limit=3)
    errors = db.get_errors(name, limit=10)
    restarts = db.get_recent_restarts(agent_name=name, limit=10)

    status = pulses[0].get("status", "?") if pulses else "?"
    latency = pulses[0].get("latency_ms", 0) if pulses else 0
    error_count = len(errors)
    restart_count = len(restarts)

    drift = "unknown"
    memory_debt = "unknown"
    try:
        conn = db._get_conn()
        dr = conn.execute("SELECT delta_pct, breached FROM chisel_drift WHERE agent_name=? ORDER BY timestamp DESC LIMIT 1", (name,)).fetchone()
        if dr:
            drift = f"{dr['delta_pct']:.1f}%{' ⚠️' if dr['breached'] else ''}"
        gr = conn.execute("SELECT memory_debt_score FROM clawforge_garden WHERE agent_name=? ORDER BY timestamp DESC LIMIT 1", (name,)).fetchone()
        if gr:
            memory_debt = str(round(gr['memory_debt_score']))
    except Exception:
        logger.exception("swallowed exception in server.py")

    response = ask(
        PER_AGENT_SUMMARY_PROMPT.format(name=name, status=status, latency_ms=latency,
                                        error_count=error_count, restart_count=restart_count,
                                        drift=drift, memory_debt=memory_debt),
        "",
        consumer="per_agent_summary",
        max_cost_cents=0.005,
        cache_ttl_secs=3600,
        tier=2,
    )

    if response is None:
        # Static fallback
        response = f"{status} · {latency:.0f}ms · {error_count} errors · ⚡{drift}"

    return HTMLResponse(f"<span style='font-size:12px;color:#94a3b8;'>{response}</span>")


@app.get("/api/self-monitor-summary")
async def api_self_monitor_summary():
    """G1.1: Self-monitoring budget cap — dashboard widget data."""
    from observeco.llm_service.gate import get_self_monitor
    summary = get_self_monitor().summary()
    pct = summary["usage_pct"]
    bar_color = "#22c55e" if pct < 70 else "#eab308" if pct < 90 else "#ef4444"
    bar_width = min(pct, 100)
    status = "🟢 Normal" if pct < 70 else "🟡 Approaching limit" if pct < 90 else "🔴 Near limit" if pct < 100 else "🔴 Exhausted"
    banner = ""
    if pct >= 90:
        banner = '<div class="warning-banner" style="background:#451a03;border:1px solid #ef4444;padding:8px 12px;border-radius:6px;margin-bottom:8px;font-size:12px;">⚠️ <strong>Self-diagnosis budget nearly exhausted</strong> ({:.0f}K/{:.0f}K tokens). At 100%, LLM diagnosis will pause — static fallbacks will be used. Resets at midnight.</div>'.format(
            summary["total_tokens"] / 1000, summary["ceiling"] / 1000)
    if pct >= 100:
        banner = '<div class="warning-banner" style="background:#450a03;border:1px solid #ef4444;padding:8px 12px;border-radius:6px;margin-bottom:8px;font-size:12px;">🔴 <strong>Self-diagnosis paused</strong> — daily budget exhausted ({:.0f}K/{:.0f}K tokens). Resets at midnight. All LLM diagnostics using static fallbacks.</div>'.format(
            summary["total_tokens"] / 1000, summary["ceiling"] / 1000)
    return HTMLResponse(f"""
    <div style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
            <span>{status}</span>
            <span>{summary['total_tokens']:,} / {summary['ceiling']:,} tokens ({pct}%)</span>
        </div>
        <div style="background:#1e293b;border-radius:4px;height:8px;overflow:hidden;">
            <div style="background:{bar_color};width:{bar_width}%;height:100%;border-radius:4px;transition:width 0.3s;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:#64748b;margin-top:2px;">
            <span>Calls today: {summary['call_count']}</span>
            <span>Floor: {summary['floor']:,}</span>
        </div>
    </div>
    {banner}
    """)


@app.post("/api/agents/{agent_name}/stop")
async def api_stop_agent(agent_name: str, request: Request):
    """G1.2: Manual kill switch — stop an agent process.

    2-step confirmation expected on the frontend. This endpoint is the
    confirmed execution path. Sends SIGTERM first, SIGKILL after 5s if still alive.
    """
    from observeco.dashboard.auth import require_dash_auth
    auth_error = require_dash_auth(request)
    if auth_error:
        return auth_error

    import subprocess
    try:
        # Find agent process
        result = subprocess.run(
            ["pgrep", "-f", re.escape(agent_name)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            # Process not found — might be a daemon or service
            # Check launchd
            launchd = subprocess.run(
                ["launchctl", "list"], capture_output=True, text=True, timeout=5,
            )
            if agent_name in launchd.stdout:
                subprocess.run(["launchctl", "stop", agent_name], timeout=10)
                db.log_kill(agent_name, "SIGTERM (launchd)", True)
                return JSONResponse({"ok": True, "message": f"Stopped {agent_name} via launchctl"})
            db.log_kill(agent_name, "none", False, "Process not found")
            return JSONResponse({"ok": True, "message": f"{agent_name} not running — already stopped"})

        pids = result.stdout.strip().splitlines()
        for pid in pids[:3]:  # Limit to 3 PIDs to avoid killing everything
            pid = pid.strip()
            if not pid:
                continue
            # SIGTERM first
            subprocess.run(["kill", "-TERM", pid], timeout=5)
            # Wait 5s, then SIGKILL if still alive
            import time as _time
            _time.sleep(5)
            check = subprocess.run(["kill", "-0", pid], capture_output=True, timeout=5)
            if check.returncode == 0:
                subprocess.run(["kill", "-KILL", pid], timeout=5)
                db.log_kill(agent_name, "SIGTERM→SIGKILL", True)
            else:
                db.log_kill(agent_name, "SIGTERM", True)

        return JSONResponse({"ok": True, "message": f"Stopped {agent_name} ({len(pids[:3])} processes)"})
    except Exception as e:
        db.log_kill(agent_name, "none", False, str(e))
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/agents/{agent_name}/kill-log", response_class=HTMLResponse)
async def api_agent_kill_log(agent_name: str):
    """G1.2: Kill switch audit log — HTML fragment for dashboard."""
    entries = db.get_kill_log(agent_name, limit=10)
    if not entries:
        return '<div style="color:#64748b;font-size:12px;">No kill events recorded for this agent.</div>'
    rows = ""
    for e in entries:
        success = "✅" if e["success"] else "❌"
        signal_txt = e["signal_sent"]
        error = f' <span style="color:#ef4444;">({e["error_message"]})</span>' if e["error_message"] else ""
        rows += f'<tr><td style="padding:4px 8px;font-size:11px;">{success}</td><td style="padding:4px 8px;font-size:11px;">{signal_txt}{error}</td></tr>'
    return f'<table class="data-table"><tr><th style="padding:4px 8px;font-size:11px;">Result</th><th style="padding:4px 8px;font-size:11px;">Signal</th></tr>{rows}</table>'
