"""Dashboard server — FastAPI + htmx single-pane agent observability.

Spec: specs/unified-dashboard.md
  §5 Color System, §6 Layout Wireframe, §7 Conversion Funnel, §7.1 Locked Tiles,
  §7.2 Token Bar, §7.3 Responsive, §7.4 Error States, §8 First-Run Experience,
  §4.2.7 Framework-Specific Display, §6.3 Agent Detail, §6.4 Alerts, §6.5 Error Timeline
"""

from __future__ import annotations

import json
import os
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from observeco.billing import add_billing_endpoints
from observeco.dashboard.otel import router as otel_router
from observeco.dashboard.licenses_api import router as licenses_router
from observeco.db import Database
from observeco.api import router as api_router
from observeco.realtime import router as realtime_router
from observeco.dirs import get_data_dir

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
from observeco.dashboard.auth import init_auth as _init_auth, get_cached_secret as _get_secret
_dash_secret = _init_auth(app)
app.state.dashboard_secret = _dash_secret

# --- Auth setup ---
import secrets as _secrets
from observeco.auth.oauth2 import OAuth2Provider
auth_provider = OAuth2Provider()

# Register billing + OTel + feedback + license endpoints
add_billing_endpoints(app)
app.include_router(otel_router)
app.include_router(api_router)
app.include_router(realtime_router)
app.include_router(licenses_router)

# --- Startup: ensure trial token if first run ---
@app.on_event("startup")
async def startup_license_check():
    from observeco import license as lic
    state = lic.load()
    if state.license_type == "free" and not state.key and not state.trial_token:
        lic.ensure_trial(state)
        _log_license = f"auto-trial started ({state.remains_days}d remaining)"
    elif state.license_type == "trial":
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
    """Detect onboarding phase per §8 — 3-phase progressive loading."""
    agents = db.get_agents()
    pulses = db.get_recent_pulses(limit=5)
    now = int(time.time())

    has_agents = len(agents) > 0
    has_data = len(pulses) > 0
    recent_data = any(now - p.get("timestamp", 0) < 300 for p in pulses)  # within 5m

    if not has_agents and not has_data:
        # Phase 0 — Fresh install, nothing detected
        return HTMLResponse("""<div class="phase-banner">
    <div class="phase-banner-inner">
        <span class="phase-banner-icon">🔍</span>
        <div class="phase-banner-body">
            <strong class="phase-banner-title">Observing your system...</strong>
            <div class="phase-banner-text">
                Auto-discovering your agents from config files and common agent paths.
                Agents will appear here automatically or run
                <code class="inline-code-sm">observeco agents discover</code>
                to check manually.
            </div>
        </div>
    </div>
</div>""")

    if has_agents and not recent_data:
        # Phase 1 — Agents found, waiting for data
        count = len(agents)
        return HTMLResponse(f"""<div class="phase-banner" style="border-left-color:#eab308;background:rgba(234,179,8,0.08);">
    <div class="phase-banner-inner">
        <span class="phase-banner-icon">⏳</span>
        <div class="phase-banner-body">
            <strong class="phase-banner-title">{count} agent{'s' if count != 1 else ''} discovered — collecting health data...</strong>
            <div class="phase-banner-text">
                Run <code class="inline-code-sm">observeco watch</code>
                to start monitoring, or wait for background collection.
                Status dots will fill in as data arrives.
            </div>
        </div>
    </div>
</div>""")

    # Phase 2 — System stabilized
    # Show a brief confirmation banner that auto-fades
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
            action="Run `observeco agents add <name> --check <url>` or auto-discover with `observeco pulse check`.",
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
    max_delay = max(d[1] for d in delays)
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
                <a href="/api/checkout?plan={plan.lower()}&trial=30"
                   class="pro-cta-link">
                    Start Free Trial
                </a>
                <button onclick="closeProPreview()"
                        class="pro-cta-btn">
                    Not now
                </button>
            </div>
        </div>
    </div>
</div>""")


@app.get("/api/checkout")
async def api_checkout(plan: str = "solo", trial: int = 30):
    """Redirect to Stripe checkout — §7.1 state 4."""
    from observeco.billing import create_checkout_session
    # Use a default email — real email captured during checkout flow
    result = create_checkout_session(email="checkout@observeco.app", plan=plan)
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

    if tab == "health":
        return _detail_health_tab(name, pulses, errors, circuit, framework)
    elif tab == "guard":
        return _detail_guard_tab(name, errors, circuit, framework)
    elif tab == "errors":
        return _detail_errors_tab(name, errors, framework)
    elif tab == "tokens":
        return _detail_tokens_tab(name, trims, drift, framework)
    elif tab == "garden" or tab == "memory":
        return _detail_garden_tab(name, garden, profile, framework)
    return HTMLResponse("<div>Unknown tab</div>")


def _detail_health_tab(name: str, pulses: list, errors: list, circuit: dict, framework: str) -> str:
    now = int(time.time())

    # ── Section 1: Pulse timeline (all dots with legend) ──
    dot_row = []
    for p in pulses[:48]:
        dot = "🟢" if p["status"] == "alive" else "🔴" if p["status"] == "dead" else "🟡"
        ts = _fmt_ts(p["timestamp"])
        dot_row.append(f'<span title="{p["status"]} @ {ts}" class="pulse-dot">{dot}</span>')
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
    if total_errs == 0:
        verdict_text = "All checks passed in the last 24 hours. No issues detected."
    elif total_errs == 1:
        verdict_text = "This agent had 1 issue in the last 24 hours. Likely transient — monitor."
    elif total_errs <= 3:
        verdict_text = f"This agent had <strong>{total_errs} issues</strong> in the last 24 hours. Possibly unstable — check the error details above."
    else:
        # Determine status-based verdict
        if any(p["status"] in ("dead", "error") for p in pulses[:24]):
            verdict_text = f"This agent had <strong>{total_errs} issues</strong> in the last 24 hours. It needs attention — try restarting it."
        else:
            verdict_text = f"This agent had <strong>{total_errs} issues</strong> in the last 24 hours. Issues appear resolved for now — monitor the next few checks."

    summary_html = "<br>".join(summary_parts) if summary_parts else "All checks passed — no issues detected this period."

    # ── Section 4: Latest check ──
    last_pulse = pulses[0] if pulses else {}
    last_status = last_pulse.get("status", "unknown")
    last_ts = _fmt_ts(last_pulse.get("timestamp", 0)) if last_pulse else "—"
    last_latency = last_pulse.get("latency", "—") if last_pulse else "—"
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
            <span class="pulse-legend-dot ok">🟢 OK</span>
            <span class="pulse-legend-dot warn">🟡 Warning</span>
            <span class="pulse-legend-dot err">🔴 Error</span>
        </div>
    </div>
    <div class="modal-section">
        <h4>What happened — annotated timeline</h4>
        <table class="data-table">
            <tr><th style="width:70px;">Time</th><th style="width:80px;">Status</th><th>What happened</th></tr>
            {error_rows}
        </table>
    </div>
    <div class="modal-section">
        <h4>Summary</h4>
        <div class="health-summary-body">
            {summary_html}
        </div>
        <div class="health-verdict">
            <strong>Verdict:</strong> {verdict_text}
        </div>
    </div>
    <div class="modal-section">
        <h4>Latest check</h4>
        <table class="data-table">
            <tr><th style="width:70px;">Time</th><th style="width:80px;">Result</th><th>Latency</th></tr>
            <tr><td>{last_ts}</td><td class="{latest_cls}">{latest_result}</td><td>{last_latency}</td></tr>
        </table>
    </div>
    {circuit_html}
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

    if framework == "hermes":
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
            bars.append(f"""<div class="token-row-detail">
    <span class="token-row-label">{comp_label}</span>
    <div class="token-bar-bg">
        <div class="token-bar-fill-dynamic" style="width:{pct:.1f}%;background:{col};"></div>
    </div>
    <span class="token-row-value token-value">{val:,} tok ({pct:.0f}%)</span>
</div>""")

        savings = latest_trim.get("savings_ratio", 0)
        savings_html = f"""<div class="savings-badge">
    Context optimized by {savings:.0%} this session
</div>""" if savings > 0 else ""

        drift_html = _detail_drift_html(drift, name)

        return HTMLResponse(f"""<div class="detail-content">
    <div class="detail-section">
        <div class="token-header"><div class="uppercase-label">Token Breakdown</div>
        <div class="text-lg font-semibold font-mono token-total-display">{total_display:,} <span class="text-sm text-muted font-normal">total</span></div>
    </div>
    {"".join(bars)}
    {savings_html}
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
    <span class="token-row-label">{comp}</span>
    <div class="token-bar-bg">
        <div class="token-bar-fill-dynamic" style="width:{pct:.1f}%;background:{col};"></div>
    </div>
    <span class="token-row-value token-value">{val:,} tok</span>
</div>""")

            loads = db.get_loads(agent_name=name)
            total_saved = sum(l.get("tokens_saved", 0) for l in loads[:20])
            savings_html = f"""<div class="savings-badge">
    ClawForge saved ~{total_saved:,} tokens across {len(loads)} turns
</div>""" if total_saved > 0 else ""

            return HTMLResponse(f"""<div class="detail-content">
    <div class="detail-section">
        <div class="token-header"><div class="uppercase-label">Source Breakdown</div>
        <div class="text-lg font-semibold font-mono token-total-display">{total_est:,} <span class="text-sm text-muted font-normal">estimated tokens</span></div>
    </div>
    {"".join(bars)}
    {savings_html}
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


def _detail_guard_tab(name: str, errors: list, circuit: dict, framework: str) -> str:
    """Guard detail — 5 sections: status, failure timeline, explanation, savings, settings."""
    now = int(time.time())
    is_tripped = circuit.get("tripped", False)

    # Section 1: Status
    if is_tripped:
        status_html = """
        <div style="font-size:13px;color:#ef4444;font-weight:600;margin-bottom:8px;">
            🔴 Guard is STOPPED — not checking this agent
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            The safety guard detected <strong>3 consecutive failures</strong> from this agent and stopped checking
            to prevent noise. It will automatically resume in <strong>~4 hours</strong> (cooldown period).
        </div>"""
    else:
        status_html = """
        <div style="font-size:13px;color:#22c55e;font-weight:600;margin-bottom:8px;">
            ✅ Guard is OK — monitoring normally
        </div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            The safety guard has detected <strong>0 consecutive failures</strong>. It continues monitoring every 30 seconds.
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
        <tr><td>Failures before stop</td><td>3</td></tr>
        <tr><td>Cooldown period</td><td>~4 hours{cooldown_remaining}</td></tr>
        <tr><td>Auto-retry after cooldown</td><td class="good">Yes</td></tr>
    </table>"""

    return HTMLResponse(f"""<div class="detail-content">
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
</div>""")


def _detail_errors_tab(name: str, errors: list, framework: str) -> str:
    """Error history — timeline table + categorized verdict + Pro upsell."""
    error_rows = ""
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
    if total == 0:
        verdict_msg = 'No errors means this agent has been running cleanly for the last 24 hours.'
    elif total == 1:
        verdict_msg = 'One error in 24 hours is usually transient — network hiccup or temporary overload.'
    else:
        verdict_msg = 'Multiple errors suggest an ongoing problem. Check the guard status to see if monitoring has been stopped automatically.'

    return HTMLResponse(f"""<div class="detail-content">
    <div class="modal-section">
        <h4>Last 24 hours</h4>
        <table class="data-table">
            <tr><th style="width:70px;">Time</th><th>What happened</th></tr>
            {error_rows}
        </table>
    </div>
    <div class="modal-section">
        <h4>What this means</h4>
        <div class="health-summary-body">{verdict_msg}</div>
    </div>
    <div class="modal-section pro-preview" style="border:1px dashed #3730a3;border-radius:10px;padding:14px;cursor:pointer;" onclick="openProModal('{_html_escape(name)} - Error History')">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <h4 style="margin-bottom:4px;font-size:13px;">🔒 More history unlocks patterns</h4>
                <div style="font-size:11px;color:#64748b;line-height:1.6;">
                    Free: last 24h only. Pro keeps every day from install — so next week you can see if errors are getting
                    <strong style="color:#f97316;">better or worse</strong>.<br>
                    <span style="color:#a5b4fc;">Weekly trend charts · regression alerts · never pruned</span>
                </div>
            </div>
        </div>
    </div>
</div>""")


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

    # No garden data — explain that data accumulates as the daemon watches
    return HTMLResponse(f"""<div class="detail-content">
    <div class="modal-section">
        <h4>💾 Memory & Context</h4>
        <div style="font-size:13px;color:#94a3b8;margin-bottom:12px;line-height:1.6;">
            Memory quality data appears automatically after the <code>observeco watch</code> daemon
            has been running for some time — it tracks duplicate detection, contradiction scanning,
            and stale entry reporting for this agent's knowledge base.
        </div>
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px;margin-top:8px;">
            <div style="font-size:12px;font-weight:600;color:#e2e8f0;margin-bottom:8px;">Prerequisites:</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;">
                <div style="background:var(--surface);border-radius:8px;padding:12px;">
                    <div style="color:#94a3b8;font-size:11px;margin-bottom:4px;">① Daemon running</div>
                    <div style="color:#22c55e;font-weight:600;">observeco watch --daemon</div>
                    <div style="color:#64748b;font-size:11px;margin-top:4px;">Collects agent data automatically</div>
                </div>
                <div style="background:var(--surface);border-radius:8px;padding:12px;">
                    <div style="color:#94a3b8;font-size:11px;margin-bottom:4px;">② Agent activity</div>
                    <div style="color:#eab308;font-weight:600;">⏳ Agent runs tasks</div>
                    <div style="color:#64748b;font-size:11px;margin-top:4px;">Data builds up as agents produce output</div>
                </div>
                <div style="background:var(--surface);border-radius:8px;padding:12px;">
                    <div style="color:#94a3b8;font-size:11px;margin-bottom:4px;">③ Inspect here</div>
                    <div style="color:#6366f1;font-weight:600;">↩ Return to this tab</div>
                    <div style="color:#64748b;font-size:11px;margin-top:4px;">Debt score, duplicates, contradictions appear here</div>
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


@app.get("/api/reset-circuit/{agent_name}")
async def api_reset_circuit(agent_name: str):
    """Reset a tripped circuit breaker."""
    db.reset_breaker(agent_name)
    return HTMLResponse(f'<span class="circuit-result">Circuit reset for {agent_name}</span>')


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
    drift_color = "#f97316" if avg_drift > 10 else "#22c55e" if avg_drift < 0 else "#94a3b8"
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
# § Skills Audit endpoint
# ---------------------------------------------------------------------------

@app.get("/api/skills-audit")
async def api_skills_audit(agent: str = "all"):
    """Ranked skill audit — token cost, drift, yearly estimate per skill."""
    # Simulated skills data based on the mockup structure
    skills = [
        {"rank": 1, "name": "weather", "category": "devops", "tokens": 4200, "drift_pct": 12, "drift_dir": "up", "last_used_days": 90, "yearly_cost": 22.80, "breach": True, "comps": {"identity": 8, "skills": 12, "memory": 5, "tools": 55, "guidance": 20}},
        {"rank": 2, "name": "database", "category": "devops", "tokens": 3100, "drift_pct": 58, "drift_dir": "up", "last_used_days": 14, "yearly_cost": 16.80, "breach": False, "comps": {"identity": 6, "skills": 30, "memory": 8, "tools": 40, "guidance": 16}},
        {"rank": 3, "name": "github-code-review", "category": "github", "tokens": 2850, "drift_pct": 3, "drift_dir": "flat", "last_used_days": 1, "yearly_cost": 15.40, "breach": False, "comps": {"identity": 5, "skills": 15, "memory": 10, "tools": 50, "guidance": 20}},
        {"rank": 4, "name": "second-brain-wiki", "category": "knowledge", "tokens": 2100, "drift_pct": -8, "drift_dir": "down", "last_used_days": 0, "yearly_cost": 11.40, "breach": False, "comps": {"identity": 10, "skills": 25, "memory": 15, "tools": 35, "guidance": 15}},
        {"rank": 5, "name": "imessage", "category": "apple", "tokens": 1800, "drift_pct": 0, "drift_dir": "flat", "last_used_days": 3, "yearly_cost": 9.70, "breach": False, "comps": {"identity": 12, "skills": 20, "memory": 8, "tools": 45, "guidance": 15}},
        {"rank": 6, "name": "dspy", "category": "research", "tokens": 1650, "drift_pct": 2, "drift_dir": "flat", "last_used_days": 7, "yearly_cost": 8.90, "breach": False, "comps": {"identity": 8, "skills": 35, "memory": 5, "tools": 40, "guidance": 12}},
        {"rank": 7, "name": "stealth-web-scraper", "category": "devops", "tokens": 1420, "drift_pct": 22, "drift_dir": "up", "last_used_days": 2, "yearly_cost": 7.70, "breach": False, "comps": {"identity": 10, "skills": 18, "memory": 12, "tools": 38, "guidance": 22}},
    ]
    total_tokens = sum(s["tokens"] for s in skills)
    return JSONResponse({
        "skills": skills,
        "summary": {
            "total_skills": 132,
            "tokens_per_session": 44700,
            "yearly_cost": 124.0,
            "after_manual_save": 73.0,
            "after_pro_save": 47.0,
            "pro_savings": 77.0,
        },
        "categories": {
            "devops": {"skills": 12, "tokens": 8720},
            "github": {"skills": 8, "tokens": 6540},
            "knowledge": {"skills": 6, "tokens": 4210},
            "apple": {"skills": 5, "tokens": 3880},
            "research": {"skills": 10, "tokens": 5100},
            "others": {"skills": 91, "tokens": 16250},
        },
    })


@app.get("/api/chisel-preview")
async def api_chisel_preview(agent: str = "all", mode: str = "lite"):
    """Chisel compression preview — real trim data from DB."""
    trims = db.get_trims(limit=20)
    latest = {}
    for t in trims:
        if t["agent_name"] not in latest:
            latest[t["agent_name"]] = t
    result = {}
    for name, t in latest.items():
        raw = t["total_tokens"]
        lite = int(raw * 0.78)
        full_val = int(raw * 0.65)
        result[name] = {
            "raw_tokens": raw, "lite_tokens": lite, "full_tokens": full_val,
            "savings_ratio": t.get("savings_ratio", 0.22),
            "components": {"identity": t.get("identity_tokens",0), "skills": t.get("skills_tokens",0),
                           "memory": t.get("memory_tokens",0), "tools": t.get("tools_tokens",0),
                           "guidance": t.get("guidance_tokens",0)},
        }
    return JSONResponse({"agents": result, "agent_count": len(result), "mode": mode,
        "compression_examples": [{"before": "When using tools, you MUST:\n1. Call exactly one tool per turn\n2. Pass all required parameters\n3. Do not add extra text",
         "after_lite": "Call one tool per turn with exact params. No extra text.",
         "after_full": "One tool per turn, exact params. Report errors.", "blocks_compressed": 9, "tokens_saved": 924}]})


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
        "recent_loads": [{"source": l.get("intent_class","unknown"), "loaded": l.get("sources_loaded",0),
                          "skipped": l.get("sources_skipped",0), "saved": l.get("tokens_saved",0)} for l in loads[:5]],
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
            if s.get("status") == status:
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

    total_agent_count = len(all_agent_names)
    alive_count = sum(1 for n in all_agent_names if summary.get(n, {}).get("status") == "alive")
    dead_count = sum(1 for n in all_agent_names if summary.get(n, {}).get("status") == "dead")
    error_count = sum(1 for n in all_agent_names if summary.get(n, {}).get("status") == "error")

    sections_html = []

    for sec_key, sec_label, sec_color, sec_icon in section_configs:
        names = sections[sec_key]
        if not names:
            continue

        cards_html = []
        for name in names:
            s = summary.get(name, {})
            status = s.get("status", "unknown")
            ts = s.get("timestamp", 0)
            cb = breakers.get(name, {})
            tripped = cb.get("tripped", 0)
            agent_type = name_type.get(name, "workflow")

            status_text = {"alive": "Healthy", "dead": "Dead", "error": "Warning"}.get(status, "Unknown")
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

            # Circuit/guard
            guard_label = "🔴 Stopped (failed 3x)" if tripped else "✅ Guard OK"
            guard_color = "var(--danger)" if tripped else "var(--accent)"

            # Error row label
            err_label = f"⚠️ {recent_error_count} in last 24h" if recent_error_count > 0 else "- No errors"
            err_color = "var(--warn)" if recent_error_count > 0 else "var(--muted)"

            # Status label with staleness indicator
            stale = ts and (now - ts) > 3600  # stale if last pulse > 1h ago
            status_label = {'alive': '● Running', 'dead': '● Down', 'error': '● Warning'}.get(status, '○ Unknown')
            if stale and status == 'alive':
                status_label = '● Running (stale)'
            if stale and status == 'error':
                status_label = '● Warning (stale)'

            cards_html.append(f"""<div class="agent-card" data-agent="{name}">
      <button class="agent-toggle" onclick="event.stopPropagation();toggleHide('{name}')" title="Hide agent"></button>
      <button class="agent-delete" onclick="event.stopPropagation();deleteAgent('{name}')" title="Remove agent">✕</button>
      <div class="card-top">
        <span class="agent-status {status}" title="{status_text}"></span>
        <div class="agent-info">
          <div class="agent-name">{_html_escape(name)}</div>
          <div class="agent-meta">{role_label}</div>
        </div>
        <div class="agent-last-seen">{last_check_str}</div>
      </div>
      {f'<div style="margin-bottom:6px;">{gap_badges_str}</div>' if gap_badges_str else ''}
      <div class="metric-row" onclick="loadTab('{name}','health')">
        <span class="label">Health</span>
        <span class="value" style="color:{'var(--accent)' if status == 'alive' else 'var(--danger)' if status == 'dead' else 'var(--warn)'};font-weight:600;">{status_label}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      <div class="metric-row" onclick="loadTab('{name}','guard')">
        <span class="label">Guard</span>
        <span class="value" style="color:{guard_color};font-weight:600;">{guard_label}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      <div class="metric-row" onclick="loadTab('{name}','errors')">
        <span class="label">Errors</span>
        <span class="value" style="color:{err_color};">{err_label}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      <div class="metric-row" onclick="loadTab('{name}','tokens')">
        <span class="label">Brain size</span>
        <span class="value" style="color:#94a3b8;">{drift_str}</span>
        <span class="click-hint">See details</span><span class="arrow">›</span>
      </div>
      <div class="metric-row">
        <span class="label">Composition</span>
        <span class="value" class="u-flex-1">{token_bar}</span>
      </div>
    </div>""")

        if cards_html:
            count = len(cards_html)
            total_t = sum(len(c) for c in cards_html)  # rough total
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
        clear_link = f" onclick=\"clearFilters()\" style=\"color:#818cf8;cursor:pointer;\""
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
    <button hx-get="/api/agents?page={clamped_page - 1}&per_page={clamped_pp}{q_param}{s_param}{h_param}" hx-target="#fleetContainer" hx-swap="innerHTML" {prev_disabled} class="page-btn">◀</button>
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
    skills_active = [dict(s) for s in skill_rows if s["triggered"] > 0]
    guidance_zero = [dict(g) for g in guidance_rows if g["fire_count"] == 0]
    guidance_active = [dict(g) for g in guidance_rows if g["fire_count"] > 0]

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
        "projected_savings": {
            "lite": -22,
            "full": -35,
            "optimiser_min": -43,
            "optimiser_max": -47,
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
        "one_liner": "The colored dot shows whether an agent is alive, dead, or in error state — based on the most recent pulse check.",
        "detail": """<div class="glossary-card-grid">
    <div class="glossary-card"><div class="glossary-card-icon">🟢</div><div class="glossary-card-title" style="color:#22c55e;">Alive</div><div class="glossary-card-body">Responded to last pulse check within expected interval. Typically checked every 30s.</div></div>
    <div class="glossary-card"><div class="glossary-card-icon">🔴</div><div class="glossary-card-title" style="color:#ef4444;">Dead</div><div class="glossary-card-body">Process not found, health endpoint timeout, or no response after N retries. Circuit breaker may have tripped.</div></div>
    <div class="glossary-card"><div class="glossary-card-icon">🟡</div><div class="glossary-card-title" style="color:#f59e0b;">Error</div><div class="glossary-card-body">Agent is reachable but returning errors (e.g. HTTP 5xx, process exit code != 0). Needs investigation.</div></div>
    <div class="glossary-card"><div class="glossary-card-icon">⚪</div><div class="glossary-card-title" style="color:#64748b;">Unknown</div><div class="glossary-card-body">No pulse data yet. Agent was registered but never checked. Run <code>observeco pulse check</code> to start.</div></div>
</div>""",
        "faq": [
            ("Why is my agent orange but circuit OK?", "The agent is running but returning errors (e.g. HTTP 500). The circuit breaker only trips after N consecutive failures — orange means it's failing but hasn't reached the threshold yet. Check the Error timeline for details."),
            ("What do I do when the dot turns red?", "Run `observeco heal --agent <name>` to auto-diagnose. Common causes: process crashed, port changed, config file moved. The heal command checks process existence, port availability, and config path."),
            ("How often are agents checked?", "Every 30 seconds by default. Configure with `observeco watch --interval <seconds>`."),
        ],
    },
    "circuit": {
        "title": "Circuit Breaker",
        "icon": "⚡",
        "one_liner": "A safety guard that stops checking a dead agent after N consecutive failures, preventing alert fatigue and wasted resources.",
        "detail": """<div class="glossary-detail">
    <strong>How it works:</strong> After 3 consecutive failures, the circuit breaker trips and enters cooldown (5 minutes by default). During cooldown, the agent is not checked. After cooldown expires, it tries again automatically.<br><br>
    <strong>What it saves:</strong> Without this guard, a single dead agent would generate 2,880 error checks per day. With it, you see ~8. That's a <strong style="color:#22c55e;">99.7% reduction</strong> in log noise.
</div>""",
        "faq": [
            ("How do I reset a tripped circuit?", "Click the Guard metric row on the agent card, then click 'Reset Circuit'. Or run `observeco pulse circuit --reset <agent_name>`."),
            ("Can I change the failure threshold?", "Yes: `observeco pulse circuit --threshold <agent>:<n>`. Default is 3 failures before trip."),
        ],
    },
    "token-bar": {
        "title": "Token Bar",
        "icon": "📊",
        "one_liner": "Visual breakdown of your agent's system prompt by component — shows what's consuming tokens in each session.",
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
        "one_liner": "Measures how much your agent's system prompt size has changed over 7 days — positive drift means it's growing (and costing more).",
        "detail": """<div class="glossary-detail">
    <strong>Drift +10%</strong> means the system prompt is 10% larger than it was 7 days ago. Common causes: memory accumulation, skill additions, tool descriptions growing.<br><br>
    <strong>When to act:</strong> Drift >20% triggers a warning. Run <code>observeco chisel trim</code> to see exact token breakdown and identify which component is growing fastest.
</div>""",
        "faq": [
            ("What causes positive drift?", "Most commonly: agent memory accumulation (every conversation adds context), new skills being added, or tool descriptions growing. Check the component breakdown to identify the source."),
            ("Is drift always bad?", "Not necessarily. Controlled growth from adding genuine capabilities is expected. Runaway drift (30%+ in a week) indicates memory bloat or skill sprawl."),
        ],
    },
    "error-badge": {
        "title": "Error Badge",
        "icon": "⚠️",
        "one_liner": "Shows the number of errors detected in the last 24 hours for a specific agent.",
        "detail": """<div class="glossary-detail">
    Badges appear in two colors:<br>
    <strong style="color:#ef4444;">🔴 Red badge</strong> — Agent is Dead or Error state with recent errors. Needs immediate attention.<br>
    <strong style="color:#f59e0b;">🟡 Yellow badge</strong> — Agent has errors but is still responding. Investigate when convenient.<br><br>
    Click the metric row on the agent card to see full error details and timeline.
</div>""",
        "faq": [
            ("Why does an agent have errors but is still alive?", "The agent process is running but returning error responses (e.g. HTTP 500, Python traceback). The pulse check got a response — it just wasn't a healthy one."),
            ("What's the difference between error badge and status dot?", "The status dot reflects the <em>latest</em> pulse. The error badge shows <em>cumulative</em> errors in 24h. An agent can be alive but have errors."),
        ],
    },
    "pulse-check": {
        "title": "Pulse Check",
        "icon": "💓",
        "one_liner": "A lightweight health probe that checks if your agent is alive, dead, or in error state every 30 seconds.",
        "detail": """<div class="glossary-detail">
    <strong>How it works:</strong> Pulse check sends a request to the agent's health endpoint (HTTP GET) or checks if the process exists (process name match). Results are stored in SQLite and rendered on the dashboard.<br><br>
    <strong>Three outcomes:</strong><br>
    🟢 <strong style="color:#22c55e;">Alive</strong> — Health endpoint responded OK or process found<br>
    🔴 <strong style="color:#ef4444;">Dead</strong> — No response or process not found<br>
    🟡 <strong style="color:#f59e0b;">Error</strong> — Reached but returned error<br><br>
    Run <code>observeco pulse check</code> from the CLI to see current status for all agents.
</div>""",
        "faq": [
            ("Do I need to set up health endpoints for every agent?", "No. ObserveCo auto-detects agents from config files (Hermes, OpenClaw, and others). For custom agents, use `observeco agents add <name> --health-check <url_or_command>` to register manually."),
            ("What happens if pulse.db doesn't exist?", "First run creates it automatically. The dashboard shows a phase banner guiding you through the first discovery."),
        ],
    },
    "heal-button": {
        "title": "Heal Button",
        "icon": "🔧",
        "one_liner": "Automatically diagnoses and fixes common agent problems — restart dead processes, clear tripped circuits, trim bloated contexts.",
        "detail": """<div class="glossary-detail">
    <strong>What it checks:</strong><br>
    • <strong>Process existence</strong> — Is the agent process running?<br>
    • <strong>Port availability</strong> — Is the configured port open?<br>
    • <strong>Config file integrity</strong> — Does the config path still exist?<br>
    • <strong>Circuit breaker state</strong> — Is it tripped? Should it be reset?<br><br>
    <strong>Pro:</strong> Auto-heal runs on a schedule and fixes issues without manual intervention. Free tier requires manual trigger.
</div>""",
        "faq": [
            ("What does the heal command actually do?", "Run `observeco heal --agent <name>` to see a diagnostic report. Use `--auto-heal` to execute fixes. The command explains what it found and what it fixed."),
            ("Is auto-heal dangerous?", "No. It only executes fixes that are reversible (restart process, reset circuit, clean memory). It won't delete configs or remove agents."),
        ],
    },
    "alerts-panel": {
        "title": "Alerts Panel",
        "icon": "⚠️",
        "one_liner": "A real-time feed of critical events — tripped circuits, drift breaches, heartbeat anomalies — prioritized by severity.",
        "detail": """<div class="glossary-detail">
    Three severity levels:<br>
    🔴 <strong style="color:#ef4444;">Critical</strong> — Circuit breaker tripped, agent dead. Action required.<br>
    🟡 <strong style="color:#f59e0b;">Warning</strong> — Drift exceeding 10%, error state. Monitor closely.<br>
    🔵 <strong style="color:#3b82f6;">Info</strong> — Heartbeat anomalies, unusual patterns. Investigate when convenient.<br><br>
    <strong>Pro:</strong> Push notifications via Telegram, webhook, or CLI. Free tier shows alerts in-dashboard only.
</div>""",
        "faq": [
            ("How far back do alerts go?", "Free tier: 7 days. Pro: 90 days with trend analysis."),
            ("Can I get alerts on Telegram?", "Yes — that's a Pro feature. In the free tier, alerts are visible in the dashboard right rail."),
        ],
    },
}

@app.get("/api/glossary/{topic}", response_class=HTMLResponse)
async def api_glossary(topic: str):
    """Return glossary content for a topic — §3.20."""
    entry = GLOSSARY_DATA.get(topic)
    if not entry:
        return HTMLResponse('<div class="glossary-not-found">Topic not found. Available: status-dot, circuit, token-bar, drift, error-badge, pulse-check, heal-button, alerts-panel.</div>')

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
            injection = (
                f'<meta name="observeco-token" content="{token}">\n'
                f'<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n'
                f'<meta http-equiv="Pragma" content="no-cache">\n'
                f'<meta http-equiv="Expires" content="0">\n'
                f'<script>window.__OBSERVECO_TOKEN = "{token}";</script>\n'
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
    summary_parts = [f'<span class="pathway-scan-item">🔍 Scan complete</span>']
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
    from observeco.telemetry_client import is_telemetry_enabled, _OPT_IN_FILE
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
        '<span style="font-size:16px;flex-shrink:0;">📊</span>'
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


# ── Onboarding overlay endpoint (Layer F / F2) ─────────────────
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

    import subprocess, sys

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

    if show_token:
        print(f"Dashboard access token: {dashboard_secret}")
        print("Use this with: curl -H 'X-ObserveCo-Token: <token>' http://localhost:{port}/api/agents")
        return

    if static:
        _generate_static(host, port)
        return

    # Auto-launch the independent watch daemon if not running.
    _ensure_watch_running()

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
    now = int(time.time())

    if not summary:
        return HTMLResponse('<div class="restart-empty">No restart data yet. Restart data is collected during pulse checks.</div>')

    # Fleet-level totals
    total_healthy = sum(s["healthy"] for s in summary.values())
    total_toctou = sum(s["toctou"] for s in summary.values())
    total_crash = sum(s["crash"] for s in summary.values())
    total_all = total_healthy + total_toctou + total_crash

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

    now = int(time.time())
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
async def api_glossary():
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
        from observeco.risk_engine import RiskLevel, RISK_EMOJI
        from observeco.session_log import SessionLogger

        # Get recent session logs
        from observeco.platform import get_data_dir
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
    from observeco.heal.l2 import run_l2_scan, get_l2_metrics
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
    from observeco.heal.l2 import get_l2_summary, get_l2_metrics
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
    """Show alert subscriptions as HTML snippet."""
    from observeco.db import Database
    db = Database()
    subs = db.get_alert_subscriptions()
    items = []
    for s in subs:
        icon = {"telegram": "📱", "webhook": "🔗", "email": "📧"}
        items.append(f"""<div class="heal-entry info">
    <div class="heal-entry-header">
        <span class="heal-action">{icon.get(s['channel'],'?')} {s['channel']} → {_html_escape(s['target'][:50])}</span>
        <span class="heal-time">{'✅ Enabled' if s['enabled'] else '❌ Disabled'}</span>
    </div>
    <div class="heal-detail">Events: {s['event_types']}</div>
</div>""")
    if not items:
        html = '<div class="empty-state">📭 No alert subscriptions. Add one via CLI: <code>observeco alerts subscribe telegram &lt;chat_id&gt;</code></div>'
    else:
        html = "".join(items)
    return HTMLResponse(html)


@app.get("/api/alert-log", response_class=HTMLResponse)
async def api_alert_log():
    """Show alert delivery log as HTML snippet."""
    from observeco.db import Database
    db = Database()
    log = db.get_alert_log(limit=15)
    items = []
    for l in log:
        icon = "✅" if l["delivered"] else "❌"
        items.append(f"""<div class="heal-entry {'success' if l['delivered'] else 'fail'}">
    <div class="heal-entry-header">
        <span class="heal-action">{icon} {l['channel']} → {_html_escape(l['target'][:40])}</span>
        <span class="heal-time">{l['event_type']}</span>
    </div>
    <div class="heal-detail">{_html_escape(l['message'][:80])}</div>
</div>""")
    if not items:
        html = '<div class="empty-state">📭 No alerts delivered yet.</div>'
    else:
        html = "".join(items)
    return HTMLResponse(html)


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
    from observeco.clawforge.plugin import get_plugin_stats, seed_demo_data
    seed_demo_data()  # Seed demo data if empty
    stats = get_plugin_stats(agent)
    return JSONResponse(stats)


@app.get("/api/plugin-hooks", response_class=HTMLResponse)
async def api_plugin_hooks(agent: str = ""):
    """Show recent plugin hooks as HTML snippet."""
    from observeco.clawforge.plugin import get_recent_hooks, seed_demo_data
    seed_demo_data()
    hooks = get_recent_hooks(agent, limit=10)
    items = []
    for h in hooks:
        red_pct = round((h["sources_skipped"] / max(h["sources_loaded"] + h["sources_skipped"], 1)) * 100, 1)
        icon = {"bootstrap": "📥", "ingest": "🔍", "pre_response": "📊"}
        items.append(f"""<div class="heal-entry info">
    <div class="heal-entry-header">
        <span class="heal-action">{icon.get(h['hook_point'],'?')} {h['agent_name']} · {_html_escape(h.get('intent_class','') or h['hook_point'])}</span>
        <span class="heal-time">{h['hook_point']}</span>
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
    from observeco.tracking.baselines import compute_baselines, compute_all_baselines
    if agent:
        result = compute_baselines(agent, days)
    else:
        result = compute_all_baselines(days)
    return JSONResponse(result)


@app.get("/api/l2/baselines", response_class=HTMLResponse)
async def api_l2_baselines_html(agent: str = "", days: int = 7):
    """Show L2 baselines as HTML snippet."""
    from observeco.tracking.baselines import compute_baselines, compute_all_baselines
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
