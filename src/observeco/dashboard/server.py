"""Dashboard server — FastAPI + htmx single-pane agent observability.

Spec: specs/unified-dashboard.md
  §5 Color System, §6 Layout Wireframe, §7 Conversion Funnel, §7.1 Locked Tiles,
  §7.2 Token Bar, §7.3 Responsive, §7.4 Error States, §8 First-Run Experience,
  §4.2.7 Framework-Specific Display, §6.3 Agent Detail, §6.4 Alerts, §6.5 Error Timeline
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from observeco.api import router as api_router
from observeco.billing import add_billing_endpoints
from observeco.config import hermes_home
from observeco.dashboard.commercial_api import router as commercial_router
from observeco.dashboard.licenses_api import router as licenses_router
from observeco.dashboard.otel import router as otel_router
from observeco.db import Database
from observeco.dirs import get_data_dir
from observeco.realtime import router as realtime_router

# Shared heartbeat path — watch daemon writes this every 30s.
# Dashboard reads it to detect if the daemon is alive.
_HEARTBEAT_PATH = get_data_dir() / ".watch_heartbeat.json"

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
app.include_router(realtime_router)
app.include_router(licenses_router)
app.include_router(commercial_router)

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
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
        resp.set_cookie("observeco_token", session.token, httponly=True, secure=True, samesite="lax", max_age=604800)
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
    resp.set_cookie("observeco_token", session.token, httponly=True, secure=True, samesite="lax", max_age=604800)
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
        if _HEARTBEAT_PATH.exists():
            hb_data = json.loads(_HEARTBEAT_PATH.read_text())
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
        pass

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


_ALERTS_VIEW_PATH = get_data_dir() / ".alerts_last_viewed"

def _get_alerts_last_viewed() -> int:
    try:
        return int(_ALERTS_VIEW_PATH.read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return int(time.time())

def _set_alerts_last_viewed() -> None:
    try:
        _ALERTS_VIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ALERTS_VIEW_PATH.write_text(str(int(time.time())))
    except Exception:
        pass


@app.get("/api/alerts", response_class=HTMLResponse)
async def api_alerts():
    """Generate alerts panel content per §6.4 — right rail, severity-coded,
    with discovery gap badges and cumulative delay summary.
    """
    db.get_errors(limit=50)
    circuit = db.get_circuit_breakers()
    drift = db.get_drift()
    now = int(time.time())
    last_viewed = _get_alerts_last_viewed()

    alerts: list[dict] = []

    # 🔴 Critical: tripped circuit breakers
    for cb in circuit:
        if cb.get("tripped"):
            name = cb["agent_name"]
            failures = cb.get("failure_count", 0)
            ts = cb.get("cooldown_until") or (now - 300)
            gap_s = now - ts
            alerts.append({
                "severity": "critical",
                "severity_label": "CRITICAL",
                "icon": "🔴",
                "agent": name,
                "message": f"Circuit breaker tripped ({failures} failures)",
                "timestamp": ts,
                "gap_seconds": gap_s,
                "is_new": ts > last_viewed,
                "severity_color": "#ef4444",
                "severity_bg": "#450a0a",
            })

    # 🟡 Warning: drift > 10%
    drift_breaches = [d for d in drift if d.get("breached")]
    for d in drift_breaches[:5]:
        agent = d["agent_name"]
        comp = d.get("component", "system prompt")
        pct = d.get("delta_pct", 0)
        ts = d.get("timestamp", now - 600)
        gap_s = now - ts
        alerts.append({
            "severity": "warning",
            "severity_label": "WARNING",
            "icon": "🟡",
            "agent": agent,
            "message": f"Drift {pct:+.1f}% in {comp}",
            "timestamp": ts,
            "gap_seconds": gap_s,
            "is_new": ts > last_viewed,
            "severity_color": "#eab308",
            "severity_bg": "#422006",
        })

    # 🔴 Critical / 🟡 Warning: pulse-based agent status
    pulses = db.get_recent_pulses(limit=100)
    seen_agents = set()
    for p in pulses:
        aname = p["agent_name"]
        if aname in seen_agents:
            continue
        seen_agents.add(aname)
        status = p.get("status", "")
        ts = p.get("timestamp", now - 300)
        gap_s = now - ts
        if status == "dead":
            alerts.append({
                "severity": "critical",
                "severity_label": "CRITICAL",
                "icon": "🔴",
                "agent": aname,
                "message": "Agent is dead — no recent heartbeat",
                "timestamp": ts,
                "gap_seconds": gap_s,
                "is_new": ts > last_viewed,
                "severity_color": "#ef4444",
                "severity_bg": "#450a0a",
            })
        elif status == "error":
            err_msg = p.get("error_message", "") or "Error state detected"
            alerts.append({
                "severity": "warning",
                "severity_label": "WARNING",
                "icon": "🟡",
                "agent": aname,
                "message": f"Error: {err_msg[:80]}",
                "timestamp": ts,
                "gap_seconds": gap_s,
                "is_new": ts > last_viewed,
                "severity_color": "#eab308",
                "severity_bg": "#422006",
            })

    # 🔵 Info: heartbeat anomalies
    from collections import Counter
    pulse_counts = Counter(p["agent_name"] for p in pulses)
    for agent in sorted(pulse_counts):
        if pulse_counts[agent] < 3:  # less than 3 pulses = possible anomaly
            agent_pulses = [p for p in pulses if p["agent_name"] == agent]
            if agent_pulses:
                last_ts = agent_pulses[0].get("timestamp", 0)
                if now - last_ts > 3600:
                    alerts.append({
                        "severity": "info",
                        "severity_label": "INFO",
                        "icon": "🔵",
                        "agent": agent,
                        "message": f"Heartbeat anomaly — only {pulse_counts[agent]} pulses recorded",
                        "timestamp": last_ts,
                        "gap_seconds": now - last_ts,
                        "is_new": last_ts > last_viewed,
                        "severity_color": "#3b82f6",
                        "severity_bg": "#172554",
                    })

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["severity"], 99), -a["timestamp"]))

    if not alerts:
        empty_status = "" if _ALERTS_VIEW_PATH.exists() else 'first-load'
        _set_alerts_last_viewed()
        return HTMLResponse(f'<div class="empty-state" style="color:#6b7280;font-size:13px;text-align:center;padding:24px 20px;">✅ All clear — no alerts</div><div data-alerts-viewed="{empty_status}" style="display:none;"></div>')

    # Compute cumulative undiscovered downtime
    total_gap_minutes = sum(a["gap_seconds"] for a in alerts) // 60
    new_count = sum(1 for a in alerts if a.get("is_new"))
    discovery_alert_count = len(alerts)

    # Build cumulative gap banner
    gap_banner = f"""<div class="gap-banner" style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;gap:12px;">
    <div style="font-size:20px;font-weight:700;color:#f97316;">{total_gap_minutes}m</div>
    <div style="font-size:11px;color:var(--fg-2);line-height:1.5;">
        Total <strong style="color:#e2e8f0;">undiscovered downtime</strong> across {discovery_alert_count} alert(s) in the last 24h
        {f' — <span style="color:#ef4444;font-weight:600;">{new_count} new since your last view</span>' if new_count else ''}
    </div>
</div>"""

    items = [gap_banner]
    for a in alerts[:10]:
        ts_str = _fmt_ts(a["timestamp"])
        # Discovery gap badge
        gap_s = a.get("gap_seconds", 0)
        is_new = a.get("is_new", False)
        gap_label = ""
        if gap_s > 300:  # Only show gap if >5 min
            gap_m = gap_s // 60
            gap_h = gap_m // 60
            if gap_h > 0:
                gap_label = f"🕐 Happened {_fmt_ts(a['timestamp'])} · <strong style='color:#fca5a5;'>{gap_h}h {gap_m % 60}m gap</strong>"
            else:
                gap_label = f"🕐 Happened {_fmt_ts(a['timestamp'])} · <strong style='color:#fca5a5;'>{gap_m}m gap</strong>"
        new_badge = '<span style="background:#7f1d1d;color:#fca5a5;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:4px;">NEW</span>' if is_new else ""

        items.append(f"""<div class="alert-row severity-{a['severity']}" style="border-left:3px solid {a['severity_color']};background:{a['severity_bg']};">
    <div class="heal-entry-header">
        <span><strong style="color:{a['severity_color']}">{a['severity_label']}{new_badge}</strong></span>
        <span class="heal-time">{ts_str}</span>
    </div>
    <div class="text-secondary" class="u-mt-2">
        <span style="color:#38bdf8;font-weight:600;">{_html_escape(a['agent'])}</span>
        <span> — {_html_escape(a['message'])}</span>
    </div>
    {f'<div class="discovery-gap" style="font-size:10px;color:#94a3b8;margin-top:2px;">{gap_label}</div>' if gap_label else ''}
    <div class="alerts-action-bar" style="margin-top:4px;">
        <span class="heal-time" style="font-size:10px;color:#64748b;">
            🔇 Dashboard only · <span onclick="showProPreview('alert-relay')" style="cursor:pointer;color:#a5b4fc;text-decoration:underline;">Enable push alerts (Pro)</span>
        </span>
    </div>
</div>""")

    # Add Pro locked tiles below alerts
    pro_tiles_html = _pro_locked_tiles()
    items.append(pro_tiles_html)

    # Record that user has now seen these alerts
    _set_alerts_last_viewed()

    html = "\n".join(items)
    return HTMLResponse(html)


def _pro_locked_tiles() -> str:
    """Generate Pro locked tile grid per §7.1 — returns empty string if Pro active."""
    from observeco import license as lic
    if lic.require_pro():
        return ""

    tiles = []
    for feat in PRO_FEATURES:
        # Compute preview data from real state
        errors = db.get_errors(limit=50)
        circuit = db.get_circuit_breakers()
        drift = db.get_drift()
        agents = db.get_agents()

        alert_count = len(errors)
        drift_breaches = len([d for d in drift if d.get("breached")])
        circuit_trips = sum(1 for c in circuit if c.get("tripped"))

        # Build alert list for preview
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

        tiles.append(f"""<div class="pro-tile" id="pro-tile-{feat['id']}"
     onclick="showProPreview('{feat['id']}')">
    <div class="pro-tile-header">
        <span class="pro-tile-name">
            {feat['icon']} {feat['name']}
        </span>
        <span class="pro-tile-price">
            {feat['price']}
        </span>
    </div>
    <div class="pro-tile-desc">
        {feat['description'][:80]}…
    </div>
    <div class="u-hidden" id="preview-data-{feat['id']}">{_html_escape(preview)}</div>
</div>""")
    return '<div class="pro-tiles-section" class="u-mt-16"><div class="pro-tile-section-label">🔒 Pro Features</div>' + "\n".join(tiles) + "</div>"


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
    result = create_checkout_session(email=email, phone=phone, name=name, plan=plan)
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
        return _detail_errors_tab(name, errors, framework, agent_status, conf)
    elif tab == "tokens":
        return _detail_tokens_tab(name, trims, drift, framework)
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
    """Render a small confidence badge for agent cards — level only, no FP/FN."""
    emoji = {"high": "🟢", "medium": "🟡", "low": "⚪"}.get(conf["level"], "⚪")
    level_label = conf["level"].capitalize()
    return f'''
        <div class="conf-badge" style="font-size:10px;color:#94a3b8;margin-top:2px;display:flex;gap:8px;flex-wrap:wrap;">
            <span title="Confidence: {level_label} — {conf['sources_agree']}">{emoji} {level_label} Confidence</span>
        </div>'''


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
    stale = pulses and (now - pulses[0].get("timestamp", 0)) > 3600

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


def _detail_errors_tab(name: str, errors: list, framework: str, agent_status: str = "unknown", conf: dict = None) -> str:
    """Error history — timeline table + categorized verdict + Pro upsell."""
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
    <div class="modal-section" id="historyRange_{name}" style="border:1px dashed #3730a3;border-radius:10px;padding:14px;">
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
    </div>
</div>
<script>
setTimeout(function() {{
    // Check Pro and replace upsell with range selector
    fetch('/api/licenses/status')
        .then(r => r.json())
        .then(data => {{
            if (data.is_pro) {{
                const container = document.getElementById('historyRangeContent_{name}');
                if (container) {{
                    container.innerHTML = `
                        <h4 style="margin-bottom:6px;font-size:13px;">📅 Extended History</h4>
                        <div style="display:flex;gap:6px;margin-bottom:8px;">
                            <button onclick="loadAgentErrorHistory('{name}', 1)" class="range-btn active" id="range1d_{name}" style="background:var(--accent-on);color:#86efac;border:1px solid rgba(34,197,94,0.2);border-radius:6px;padding:4px 10px;font-size:10px;font-weight:600;cursor:pointer;">24h</button>
                            <button onclick="loadAgentErrorHistory('{name}', 7)" class="range-btn" id="range7d_{name}" style="background:var(--surface);color:#94a3b8;border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:10px;cursor:pointer;">7d</button>
                            <button onclick="loadAgentErrorHistory('{name}', 30)" class="range-btn" id="range30d_{name}" style="background:var(--surface);color:#94a3b8;border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:10px;cursor:pointer;">30d</button>
                            <button onclick="loadAgentErrorHistory('{name}', 90)" class="range-btn" id="range90d_{name}" style="background:var(--surface);color:#94a3b8;border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:10px;cursor:pointer;">90d</button>
                        </div>
                        <div id="extendedHistory_{name}" style="font-size:11px;color:#64748b;">Click a range above to load.</div>
                    `;
                    document.getElementById('historyRange_{name}').style.border = '1px solid var(--border)';
                }}
            }}
        }})
        .catch(function() {{}});
}}, 100);
function loadAgentErrorHistory(agent, days) {{
    // Update active button
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
      <button class="feedback-btn u-ml-8" onclick="openSkillsAuditModal('all')">🧩 Skill Audit</button>
      <button class="feedback-btn u-ml-8" onclick="openPathwayModal()">🕸️ Pathway map</button>
      <button class="feedback-btn u-ml-8" onclick="loadPlatforms()">🔌 Platforms</button>
      <span id="platformStatus"></span>
</div>""")


@app.get("/api/fleet-compare", response_class=HTMLResponse)
async def api_fleet_compare():
    """Side-by-side fleet comparison — § Fleet Comparison."""
    summary = db.get_agent_status_summary()
    agents = db.get_agents()
    trims_all = db.get_trims(limit=30)
    drift_all = db.get_drift()
    circuit = db.get_circuit_breakers()
    all_errors = db.get_errors(limit=100)

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
    all_names = sorted(set(
        list(summary.keys()) + list(agent_cfg.keys()) +
        list(latest_trims.keys()) + list(drift_latest.keys())
    ))

    rows = []
    for name in all_names:
        s = summary.get(name, {})
        status = s.get("status", "unknown")
        status_color = {"alive": "#22c55e", "dead": "#ef4444", "error": "#eab308", "unknown": "#64748b"}.get(status, "#64748b")
        status_dot = f'<span style="color:{status_color}">●</span>'

        # Framework
        fw = agent_cfg.get(name, {}).get("framework", "") or ""
        fw_display = fw.capitalize() if fw else "-"

        # Tokens — latest trim total
        trim = latest_trims.get(name, {})
        tok_total = trim.get("total_tokens", 0)

        # Component bars
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

        # Drift
        dr = drift_latest.get(name, {})
        drift_pct = dr.get("delta_pct", 0)
        drift_breached = dr.get("breached", False)
        drift_label = f"{drift_pct:+.1f}%" if drift_pct else "-"
        drift_color = "#ef4444" if drift_breached else "#22c55e" if abs(drift_pct) > 5 else "#64748b"

        # Errors (24h)
        recent_errors = [e for e in all_errors if e.get("agent_name") == name and now - e.get("timestamp", 0) < 86400]
        err_count = len(recent_errors)
        err_label = f'{err_count} <span style="color:var(--danger);font-size:10px;">⚠</span>' if err_count > 0 else "0"

        # Circuit
        cb = breakers.get(name, {})
        cb_status = "🔴 Tripped" if cb.get("tripped") else "✅ OK"

        # Last seen
        ts = s.get("timestamp", 0)
        last_seen = _fmt_ts(ts) if ts else "-"

        rows.append(f"""<tr>
    <td style="padding:10px 12px;font-weight:600;white-space:nowrap;"><span class="agent-status {status}" style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;"></span>{name}</td>
    <td style="padding:10px 12px;font-size:11px;color:#94a3b8;">{fw_display}</td>
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
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Agent</th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Framework</th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Tokens</th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Composition</th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Drift</th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Errors</th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Circuit</th>
                <th style="padding:10px 12px;text-align:left;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Last</th>
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
        r = _httpx.get("http://127.0.0.1:1234/", timeout=3)
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
        lite_tokens = int(raw_tokens * 0.78)
        full_tokens = int(raw_tokens * 0.65)

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
            # Default drift if none available
            drift = [
                {"component": c, "points": [10]*7, "pct": "0%", "direction": "flat"}
                for c in BRAIN_COMP_ORDER if c in components
            ]

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
        # Scale: each pulse check = ~ some token usage. If no data, use default pattern
        if sum(turns) == 0:
            turns = [max(1, raw_tokens // 10 + (i % 5) * 200) for i in range(24)]
        else:
            turns = [t * max(1, raw_tokens // max(sum(turns), 1)) for t in turns]

        fw = framework.capitalize() if framework else "Custom"
        name_label = fw

        result[name] = {
            "framework": name_label,
            "total_tokens": raw_tokens,
            "components": components,
            "raw_tokens": raw_tokens,
            "lite_tokens": lite_tokens,
            "full_tokens": full_tokens,
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
            lite_sum += data["lite_tokens"]
            full_sum += data["full_tokens"]
            for c, v in data["components"].items():
                all_comps[c] = all_comps.get(c, 0) + v
            for i in range(24):
                fleet_turns[i] += data["turn_timeline"][i]
            for d in data["drift"]:
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

        fleet = {
            "framework": f"{len(result)} agents",
            "total_tokens": raw_sum,
            "components": all_comps,
            "raw_tokens": raw_sum,
            "lite_tokens": lite_sum,
            "full_tokens": full_sum,
            "drift": list(fleet_drift.values())[:5],
            "turn_timeline": fleet_turns,
        }
        result["fleet"] = fleet

    return JSONResponse(result)


# ---------------------------------------------------------------------------
# § Budget Planner — fleet-level cost estimation widget
# ---------------------------------------------------------------------------

@app.get("/api/budget-planner", response_class=HTMLResponse)
async def api_budget_planner():
    """Fleet-level budget planner: estimate daily token spend and recommend allocation."""
    from observeco.tracking.tokens import get_token_summary
    from observeco import license as lic
    is_pro = lic.require_pro()

    # Read fleet data
    agents = db.get_agents()
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
    # Standard pricing assumptions
    PROVIDER_RATES = {"DeepSeek v4 Flash": 0.15, "Ollama Pro": 0.15, "Zhipu": 0.10, "Local (Free)": 0.0}
    provider_name = "Ollama Pro"
    rate = 0.15

    daily_cost = daily_input_tokens * rate / 1_000_000
    monthly_cost = daily_cost * 30

    # Find top spenders
    ranked = sorted(latest_trims.items(), key=lambda x: x[1].get("total_tokens", 0), reverse=True)
    top_agents = []
    for name, trim in ranked[:3]:
        tok = trim.get("total_tokens", 0)
        pct = tok / total_tokens * 100 if total_tokens > 0 else 0
        top_agents.append((name, tok, pct))

    # Lite vs Full savings projections
    lite_save_pct = 22
    full_save_pct = 35
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
        <div style="font-size:10px;color:#64748b;margin-top:2px;">-{lite_save_pct}% via guidance compression</div>
    </div>
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">Full Saves</div>
        <div style="font-size:16px;font-weight:700;color:#a5b4fc;margin-top:4px;">-${full_save:.2f}/day</div>
        <div style="font-size:10px;color:#64748b;margin-top:2px;">-{full_save_pct}% with Full + Optimiser</div>
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


@app.get("/api/token-summary")
async def api_token_summary_alias(agent: str = "", days: int = 7):
    """Alias for /api/tokens/summary — static HTML export compatibility."""
    from observeco.tracking.tokens import get_token_summary
    return JSONResponse(get_token_summary(agent, days))


@app.get("/api/drift-summary")
async def api_drift_summary():
    """Fleet-wide drift summary across all agents."""
    drift = db.get_drift()
    if not drift:
        return JSONResponse({"agents": [], "total_breached": 0, "avg_delta_pct": 0})
    agents = {}
    for d in drift:
        name = d["agent_name"]
        if name not in agents:
            agents[name] = {"agent_name": name, "components": {}, "breached": 0}
        agents[name]["components"][d["component"]] = {
            "current": d["current_tokens"],
            "week_avg": d["week_avg_tokens"],
            "delta_pct": round(d["delta_pct"], 1),
            "breached": bool(d["breached"]),
        }
        if d["breached"]:
            agents[name]["breached"] += 1
    total_breached = sum(a["breached"] for a in agents.values())
    deltas = [d["delta_pct"] for d in drift]
    avg_delta = round(sum(deltas) / len(deltas), 1) if deltas else 0
    return JSONResponse({
        "agents": sorted(agents.values(), key=lambda x: x["agent_name"]),
        "total_agents": len(agents),
        "total_breached": total_breached,
        "avg_delta_pct": avg_delta,
    })


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
        pass

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
                skills.append({
                    "name": name,
                    "category": cat,
                    "tokens": tokens,
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
                skills.append({"name": str(name), "category": cat, "tokens": tokens})
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
        pass

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
    result = {}
    for name, t in latest.items():
        raw = t["total_tokens"]
        guidance_t = t.get("guidance_tokens", 0)
        skills_t = t.get("skills_tokens", 0)
        memory_t = t.get("memory_tokens", 0)
        tools_t = t.get("tools_tokens", 0)
        identity_t = t.get("identity_tokens", 0)

        # Lite: compress only the guidance section
        lite_savings_ratio = min(0.25, max(0.0, guidance_t / max(raw, 1)))
        lite = max(0, raw - int(guidance_t * 0.7))  # Compress guidance by ~70%

        # Full: compress guidance + memory + skills (preserve identity + tools)
        full_targets = guidance_t + memory_t + skills_t
        full_savings_ratio = min(0.50, max(0.0, full_targets / max(raw, 1)))
        full_val = max(0, raw - int(full_targets * 0.6))  # Compress target sections by ~60%

        result[name] = {
            "raw_tokens": raw,
            "lite_tokens": lite,
            "full_tokens": full_val,
            "lite_savings_pct": round((1 - lite / max(raw, 1)) * 100, 1),
            "full_savings_pct": round((1 - full_val / max(raw, 1)) * 100, 1),
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
            brain_row = ''
            comp_row = ''
            if is_agent:
                guard_row = '<div class="metric-row" onclick="loadTab(' + repr(name)[1:-1] + ',\'guard\')">'
                guard_row += '\n        <span class="label">Guard<span class="glossary-hint" onclick="event.stopPropagation();showGlossary(\'circuit\', event)">?</span></span>'
                guard_row += '\n        <span class="value" style="color:' + guard_color + ';font-weight:600;">' + guard_label + '</span>'
                guard_row += '\n        <span class="click-hint">See details</span><span class="arrow">\u203a</span>\n      </div>'
                brain_row = '<div class="metric-row" onclick="loadTab(' + repr(name)[1:-1] + ',\'tokens\')">'
                brain_row += '\n        <span class="label">Brain size<span class="glossary-hint" onclick="event.stopPropagation();showGlossary(\'drift\', event)">?</span></span>'
                brain_row += '\n        <span class="value" style="color:#94a3b8;">' + drift_str + '</span>'
                brain_row += '\n        <span class="click-hint">See details</span><span class="arrow">\u203a</span>\n      </div>'
                comp_row = '<div class="metric-row">'
                comp_row += '\n        <span class="label">Composition<span class="glossary-hint" onclick="event.stopPropagation();showGlossary(\'token-bar\', event)">?</span></span>'
                comp_row += '\n        <span class="value" class="u-flex-1">' + token_bar + '</span>\n      </div>'

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
      <div class="metric-row" onclick="loadTab('{name}','health')">
        <span class="label">Health<span class="glossary-hint" onclick="event.stopPropagation();showGlossary('status-dot', event)">?</span></span>
        <span class="value" style="color:{'var(--accent)' if agent_status == 'alive' else 'var(--danger)' if agent_status == 'dead' else 'var(--muted)' if agent_status == 'not_running' else 'var(--warn)'};font-weight:600;">{status_label}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      {conf_badge if is_agent else ''}
      {guard_row}
      <div class="metric-row" onclick="loadTab('{name}','errors')">
        <span class="label">Errors<span class="glossary-hint" onclick="event.stopPropagation();showGlossary('error-badge', event)">?</span></span>
        <span class="value" style="color:{err_color};">{err_label}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      {brain_row}
      {comp_row}
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
        # No agents at all (first run) — return empty so first-run banners show
        return HTMLResponse("")

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


@app.post("/api/chisel/compress")
async def api_chisel_compress(request: Request):
    """Compress an agent's SOUL.md via the dashboard.

    Accepts JSON: {"agent": "name", "mode": "lite"|"full"}
    Returns: {"status": "ok", "message": "...", "backup": "...", "before_tokens": N, "after_tokens": N, "savings": N, "savings_pct": N}
    """
    try:
        body = await request.json()
        agent_name = body.get("agent", "").strip()
        mode = body.get("mode", "lite").strip().lower()
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
        result = run_compress(agent_name=agent_name, mode=mode)
        # Also log to database
        from observeco.db import Database
        local_db = Database()
        conn = local_db._get_conn()
        conn.execute(
            "INSERT INTO compress_log (agent_name, mode, before_tokens, after_tokens, savings, "
            "savings_pct, backup_path, triggered_by, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (result["agent"], result["mode"], result["before_tokens"], result["after_tokens"],
             result["savings"], result["savings_pct"], result.get("backup", ""),
             "dashboard", int(__import__("time").time())),
        )
        conn.commit()
        return JSONResponse(result)
    except FileNotFoundError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)
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

    # Compute actual savings from compress_log averages
    lite_avg = conn.execute(
        "SELECT ROUND(ABS(AVG(savings_pct)), 0) as avg_pct FROM compress_log WHERE mode='lite' AND savings_pct IS NOT NULL"
    ).fetchone()
    full_avg = conn.execute(
        "SELECT ROUND(ABS(AVG(savings_pct)), 0) as avg_pct FROM compress_log WHERE mode='full' AND savings_pct IS NOT NULL"
    ).fetchone()
    lite_savings = int(lite_avg["avg_pct"]) if lite_avg and lite_avg["avg_pct"] else 22
    full_savings = int(full_avg["avg_pct"]) if full_avg and full_avg["avg_pct"] else 35
    opt_min = min(43, lite_savings + 21)
    opt_max = min(47, full_savings + 12)

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
    • Cross-reference with the <strong>Health timeline</strong> to see whether the agent is currently alive or dead.<br><br>
    <span style="color:#64748b;">Pro keeps a full history from install date, with weekly trend charts so you can see if errors are getting better or worse over time.</span>
</div>""",
        "faq": [
            ("Why do I see errors but the agent is running fine?", "Because errors are shown for the last 24 hours. If the agent had a hiccup 12 hours ago and has been clean since, you'll still see that error until it falls out of the 24h window. The status dot reflects the <em>current</em> state."),
            ("How far back do errors go on free tier?", "24 hours max. Errors older than 24h are pruned automatically. Pro retains everything from install date."),
            ("Can I see if an error is getting worse?", "Not on free tier — you only see the raw list. Pro shows weekly trend charts so you can tell if the same error is happening more or less often."),
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
    <strong>Pro:</strong> Auto-heal runs on a schedule. Free tier requires manual trigger.
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
    <strong>Pro:</strong> Push notifications via Telegram. Free tier shows alerts in-dashboard.
</div>""",
        "faq": [
            ("How far back do alerts go?", "Free tier: 7 days. Pro: 90 days with trend analysis."),
            ("Can I get alerts on Telegram?", "Yes — that's a Pro feature. In the free tier, alerts are visible in the dashboard right rail."),
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
}

@app.get("/api/glossary/{topic}", response_class=HTMLResponse)
async def api_glossary(topic: str):
    """Return glossary content for a topic — §3.20."""
    entry = GLOSSARY_DATA.get(topic)
    if not entry:
        return HTMLResponse('<div class="glossary-not-found">Topic not found. Available: status-dot, circuit, token-bar, drift, error-badge, error-tab, pulse-check, heal-button, alerts-panel, confidence, fp, fn.</div>')

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

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard</h1><p>Template not found.</p>")
    html = index_path.read_text(encoding="utf-8")
    # Inject dashboard token into htmx via hx-headers attribute on <body> tag.
    # hx-headers is parsed by htmx at DOM processing time — zero JS timing dependency,
    # no event handler race, no setTimeout poll needed.
    # Also inject cache-busting meta and __OBSERVECO_TOKEN for fetch interceptor.
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
    count = db.pathway_scan()
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
    return HTMLResponse(PATHWAY_TEMPLATE.read_text(encoding="utf-8"))


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
    from observeco.telemetry_client import _OPT_IN_FILE, is_telemetry_enabled
    opted_in = is_telemetry_enabled()
    opt_file_exists = _OPT_IN_FILE.exists()
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
    from observeco.telemetry_client import _OPT_IN_FILE
    if _OPT_IN_FILE.exists():
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
    hb = _HEARTBEAT_PATH
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
        pass


def serve(host: str = "127.0.0.1", port: int = 9119, static: bool = False,
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
    _hermes_scripts = str(hermes_home() / "scripts")
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
    summary = db.get_restart_summary()
    if not summary:
        return HTMLResponse('''<div class="restart-empty" style="padding:24px;text-align:center;">
  <div style="font-size:32px;margin-bottom:12px;">🔌</div>
  <div style="font-size:15px;font-weight:600;color:var(--fg);margin-bottom:8px;">No restart data yet</div>
  <div style="font-size:12px;color:var(--fg-2);margin-bottom:16px;">Restart quality data is collected during pulse checks. Run a scan to start collecting.</div>
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


# ---------------------------------------------------------------------------
# §obs-glossary — Glossary & FAQ Panel
# ---------------------------------------------------------------------------

GLOSSARY_ITEMS = [
    ("What is a pulse?", "A heartbeat check — `observeco pulse check` sends a health request to each agent and records alive/dead/error status. Green = healthy, yellow = degraded, red = unreachable."),
    ("What is a circuit breaker?", "When an agent fails N times in a row (default 3), the circuit trips — further checks are blocked until a cooldown expires or you manually reset. Prevents cascading failures."),
    ("What is drift?", "Token composition change over time. If an agent's system prompt grows +15% in a week, that's drift. Tracked per component (identity, skills, memory, tools, guidance)."),
    ("What is context compression?", "ObserveCo's system prompt compression. Decomposes the prompt by component, measures tokens per section, and saves 15-30% per session via intelligent trimming. Run `observeco context trim` to see breakdown."),
    ("What is memory gardening?", "Memory hygiene automation: scans agent memory for duplicates, contradictions, and stale entries. Assigns a health score (A-F). Run `observeco memory garden` to audit any agent."),
    ("What is Pro?", "Paid tier ($9/mo Solo, $49/mo Team) with push alerts via Telegram/webhook, never-pruned error history, fleet comparison, drift alerts, circuit auto-recovery, and multi-machine relay. 30-day free trial."),
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
        pass

    if not daemon_running:
        daemon_btn = """
        <div class="empty-state" style="margin-bottom:12px;">
            🔴 Heal daemon not running — auto-heal requires `observeco watch` to be running.
            <div style="margin-top:8px;">
                <code style="background:#1e293b;padding:4px 8px;border-radius:4px;font-size:11px;">observeco watch</code>
            </div>
        </div>"""

    # Get all agents and their heal configs
    from observeco.db import Database
    d = Database()
    agents = d.get_agents()
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

        status = "idle"
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

        agent_rows += f"""
        <div class="heal-agent-row" style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <div style="font-size:13px;font-weight:600;color:var(--fg);">{name}</div>
                    <div style="font-size:11px;color:#64748b;margin-top:2px;">{status_label}</div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;">
                    <label class="toggle-switch" title="Enable auto-heal L1">
                        <input type="checkbox" {toggle_checked} onchange="toggleHeal('{name}', this.checked, document.getElementById('l2_{name}').checked)">
                        <span class="toggle-slider"></span>
                    </label>
                    <span style="font-size:10px;color:#64748b;">L1</span>
                </div>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid var(--border);">
                <div style="display:flex;gap:16px;font-size:11px;color:#94a3b8;">
                    <span>Max restarts/h: <strong id="maxR_{name}">{max_r}</strong></span>
                    <span>Drift threshold: <strong id="driftT_{name}">{drift_t}%</strong></span>
                    <span>Memory debt: <strong id="debtT_{name}">{debt_t}</strong></span>
                </div>
                <div id="healEventSummary_{name}" style="font-size:10px;color:#64748b;">
                    {heal_count} events
                </div>
            </div>
            <div style="margin-top:8px;display:flex;align-items:center;gap:12px;">
                <label class="toggle-switch" style="opacity:0.6;">
                    <input type="checkbox" id="l2_{name}" {l2_checked} onchange="toggleHealL2('{name}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
                <span style="font-size:10px;color:#64748b;">L2 Proactive (drift/memory)</span>
                <button onclick="editHealThresholds('{name}')" style="margin-left:auto;background:none;border:1px solid #334155;border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer;color:#94a3b8;">⚙️ Thresholds</button>
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
    from observeco import license as lic
    from observeco.alerts.push import push_alert
    from observeco.db import Database
    d = Database()
    is_pro = lic.require_pro()
    subs = d.get_alert_subscriptions()
    now = int(time.time())

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
            enabled = s.get("enabled", 1)
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
                <button onclick="showAddChannel('{ch}')" style="background:var(--accent-on);border:none;border-radius:4px;padding:4px 12px;font-size:10px;font-weight:600;cursor:pointer;color:#052e16;">+ Add</button>
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
    <!-- Add channel modal (hidden until triggered) -->
    <div class="modal-overlay" id="addChannelModal" style="display:none;" onclick="if(event.target===this)closeAddChannel()">
        <div class="modal" style="max-width:420px;">
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
                        setTimeout(() => {{ closeAddChannel(); htmx.trigger('#alertPanel', 'load') }}, 1500);
                    }})
                    .catch(() => {{ setTimeout(() => {{ closeAddChannel(); htmx.trigger('#alertPanel', 'load') }}, 1500); }});
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
                if (data.status === 'ok') htmx.trigger('#alertPanel', 'load');
            }})
            .catch(() => {{}});
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


# ---------------------------------------------------------------------------
# § OpenClaw Plugin tracking
# ---------------------------------------------------------------------------


@app.get("/api/plugin-stats")
async def api_plugin_stats(agent: str = ""):
    """Get plugin tracking stats as JSON."""
    from observeco.clawforge.plugin import get_plugin_stats
    stats = get_plugin_stats(agent)
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
            ts_display = f"just now"
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


@app.get("/api/config-health", response_class=HTMLResponse)
async def api_config_health():
    """Config hygiene widget — Pro gated. Returns HTML card or upsell."""
    from observeco.chisel.config_widget import generate_widget_html
    return _pro_response(generate_widget_html())


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
        pass

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

    import signal
    import subprocess
    try:
        # Find agent process
        result = subprocess.run(
            ["pgrep", "-f", agent_name],
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
        ts = e["created_at"]
        success = "✅" if e["success"] else "❌"
        signal_txt = e["signal_sent"]
        error = f' <span style="color:#ef4444;">({e["error_message"]})</span>' if e["error_message"] else ""
        rows += f'<tr><td style="padding:4px 8px;font-size:11px;">{success}</td><td style="padding:4px 8px;font-size:11px;">{signal_txt}{error}</td></tr>'
    return f'<table class="data-table"><tr><th style="padding:4px 8px;font-size:11px;">Result</th><th style="padding:4px 8px;font-size:11px;">Signal</th></tr>{rows}</table>'
