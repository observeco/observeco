"""Dashboard server — FastAPI + htmx single-pane agent observability.

Spec: specs/unified-dashboard.md
  §5 Color System, §6 Layout Wireframe, §7 Conversion Funnel, §7.1 Locked Tiles,
  §7.2 Token Bar, §7.3 Responsive, §7.4 Error States, §8 First-Run Experience,
  §4.2.7 Framework-Specific Display, §6.3 Agent Detail, §6.4 Alerts, §6.5 Error Timeline
"""

from __future__ import annotations

import json
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
from observeco.db import Database

app = FastAPI(title="ObserveCo Dashboard")
db = Database()

# Register billing + OTel + feedback endpoints
add_billing_endpoints(app)
app.include_router(otel_router)


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
        return HTMLResponse("""<div class="phase-banner" style="padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:16px;border-left:3px solid #38bdf8;background:rgba(59,130,246,0.08);color:#94a3b8;">
    <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:20px;">🔍</span>
        <div>
            <strong style="color:#e2e8f0;">Observing your system...</strong>
            <div style="margin-top:4px;font-size:12px;color:#64748b;">
                Auto-discovering agents from Hermes, OpenClaw, and custom configs.
                Agents will appear here automatically or run
                <code style="background:#0f172a;padding:1px 5px;border-radius:4px;font-size:11px;">observeco agents discover</code>
                to check manually.
            </div>
        </div>
    </div>
</div>""")

    if has_agents and not recent_data:
        # Phase 1 — Agents found, waiting for data
        count = len(agents)
        return HTMLResponse(f"""<div class="phase-banner" style="padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:16px;border-left:3px solid #eab308;background:rgba(234,179,8,0.08);color:#94a3b8;">
    <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:20px;">⏳</span>
        <div>
            <strong style="color:#e2e8f0;">{count} agent{'s' if count != 1 else ''} discovered — collecting health data...</strong>
            <div style="margin-top:4px;font-size:12px;color:#64748b;">
                Run <code style="background:#0f172a;padding:1px 5px;border-radius:4px;font-size:11px;">observeco watch</code>
                to start monitoring, or wait for background collection.
                Status dots will fill in as data arrives.
            </div>
        </div>
    </div>
</div>""")

    # Phase 2 — System stabilized
    # Show a brief confirmation banner that auto-fades
    return HTMLResponse("""<div class="phase-banner" style="padding:10px 16px;border-radius:8px;font-size:13px;margin-bottom:16px;border-left:3px solid #22c55e;background:rgba(34,197,94,0.06);color:#94a3b8;transition:opacity 1s;" id="phase-done">
    <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:16px;">✅</span>
        <span style="color:#22c55e;font-weight:500;">All agents monitored — system stabilised</span>
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
    return f"""<div class="error-banner" style="background:{bg};border-left:4px solid {border};padding:10px 16px;margin-bottom:12px;border-radius:6px;font-size:13px;">
    <span>{icon}</span>
    <span style="margin-left:6px;">{_html_escape(message)}</span>
    <code style="background:#0f172a;color:#e2e8f0;padding:2px 6px;border-radius:4px;margin-left:8px;font-size:12px;">{_html_escape(action)}</code>
</div>"""


# ---------------------------------------------------------------------------
# §obs-dp-006 — Cumulative Delay Banner
# ---------------------------------------------------------------------------

DELAY_WARNING_SEC = 600    # 10m → banner turns yellow
DELAY_CRITICAL_SEC = 3600  # 1h  → banner turns red


@app.get("/api/delay-banner", response_class=HTMLResponse)
async def api_delay_banner():
    """Compute cumulative agent delay and return a banner if any agents are overdue."""
    agents = db.get_agents()
    now = int(time.time())

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
        return HTMLResponse("")

    # Summarize
    max_delay = max(d[1] for d in delays)
    overdue_agents = [d for d in delays if d[1] > DELAY_WARNING_SEC]
    critical_agents = [d for d in delays if d[1] > DELAY_CRITICAL_SEC]

    if not overdue_agents:
        return HTMLResponse("")

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

    html = f"""<div class="delay-banner" style="background:{bg};border-left:4px solid {border};padding:10px 16px;margin-bottom:12px;border-radius:6px;font-size:13px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    <span>{icon} <strong>{summary}</strong></span>
    <span style="color:#64748b;">{" · ".join(agent_list)}</span>
</div>"""

    return HTMLResponse(html)


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


@app.get("/api/alerts", response_class=HTMLResponse)
async def api_alerts():
    """Generate alerts panel content per §6.4 — right rail, severity-coded."""
    db.get_errors(limit=50)
    circuit = db.get_circuit_breakers()
    drift = db.get_drift()
    now = int(time.time())

    alerts: list[dict] = []

    # 🔴 Critical: tripped circuit breakers
    for cb in circuit:
        if cb.get("tripped"):
            name = cb["agent_name"]
            failures = cb.get("failure_count", 0)
            alerts.append({
                "severity": "critical",
                "severity_label": "CRITICAL",
                "icon": "🔴",
                "agent": name,
                "message": f"Circuit breaker tripped ({failures} failures)",
                "timestamp": cb.get("cooldown_until") or (now - 300),
                "severity_color": "#ef4444",
                "severity_bg": "#450a0a",
            })

    # 🟡 Warning: drift > 10%
    drift_breaches = [d for d in drift if d.get("breached")]
    for d in drift_breaches[:5]:
        agent = d["agent_name"]
        comp = d.get("component", "system prompt")
        pct = d.get("delta_pct", 0)
        alerts.append({
            "severity": "warning",
            "severity_label": "WARNING",
            "icon": "🟡",
            "agent": agent,
            "message": f"Drift {pct:+.1f}% in {comp}",
            "timestamp": d.get("timestamp", now - 600),
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
        if status == "dead":
            alerts.append({
                "severity": "critical",
                "severity_label": "CRITICAL",
                "icon": "🔴",
                "agent": aname,
                "message": "Agent is dead — no recent heartbeat",
                "timestamp": p.get("timestamp", now - 300),
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
                "timestamp": p.get("timestamp", now - 300),
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
                        "severity_color": "#3b82f6",
                        "severity_bg": "#172554",
                    })

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["severity"], 99), -a["timestamp"]))

    if not alerts:
        return HTMLResponse('<div class="empty-state" style="color:#6b7280;font-size:13px;text-align:center;padding:20px;">✅ All clear — no alerts</div>')

    items = []
    for a in alerts[:10]:
        ts_str = _fmt_ts(a["timestamp"])
        items.append(f"""<div class="alert-row severity-{a['severity']}" style="border-left:3px solid {a['severity_color']};background:{a['severity_bg']};padding:8px 10px;margin-bottom:6px;border-radius:4px;font-size:12px;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span><strong style="color:{a['severity_color']}">{a['severity_label']}</strong></span>
        <span style="color:#64748b;font-size:11px;">{ts_str}</span>
    </div>
    <div style="margin-top:2px;">
        <span style="color:#38bdf8;font-weight:600;">{_html_escape(a['agent'])}</span>
        <span style="color:#94a3b8;"> — {_html_escape(a['message'])}</span>
    </div>
    <div style="margin-top:4px;display:flex;gap:8px;align-items:center;">
        <span style="color:#6b7280;font-size:11px;">[📡 Push]</span>
        <span style="color:#6b7280;font-size:11px;cursor:pointer;" onclick="showProPreview('alert-relay')">[🔒 Pro]</span>
    </div>
</div>""")

    # Add Pro locked tiles below alerts
    pro_tiles_html = _pro_locked_tiles()
    items.append(pro_tiles_html)

    return HTMLResponse("\n".join(items))


def _pro_locked_tiles() -> str:
    """Generate Pro locked tile grid per §7.1."""
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
     onmouseenter="this.style.opacity='0.8'"
     onmouseleave="this.style.opacity='0.5'"
     onclick="showProPreview('{feat['id']}')"
     style="opacity:0.5;filter:grayscale(1);background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 12px;margin-top:8px;cursor:pointer;transition:opacity 0.2s;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:13px;font-weight:600;color:#94a3b8;">
            {feat['icon']} {feat['name']}
        </span>
        <span style="font-size:11px;color:#64748b;background:#0f172a;padding:2px 8px;border-radius:4px;">
            {feat['price']}
        </span>
    </div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px;">
        {feat['description'][:80]}…
    </div>
    <div style="display:none;" id="preview-data-{feat['id']}">{_html_escape(preview)}</div>
</div>""")
    return '<div class="pro-tiles-section" style="margin-top:16px;"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">🔒 Pro Features</div>' + "\n".join(tiles) + "</div>"


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

    return HTMLResponse(f"""<div class="pro-preview-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:1000;display:flex;align-items:center;justify-content:center;"
     onclick="if(event.target===this) closeProPreview()">
    <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;max-width:480px;width:90%;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <h3 style="color:#f8fafc;font-size:16px;margin:0;">{feat['icon']} {feat['name']}</h3>
            <span style="color:#64748b;cursor:pointer;font-size:18px;" onclick="closeProPreview()">✕</span>
        </div>
        <div style="color:#94a3b8;font-size:14px;margin-bottom:16px;">
            {feat['description']}
        </div>
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;margin-bottom:16px;font-size:13px;color:#e2e8f0;">
            <strong style="color:#38bdf8;">Your data preview:</strong><br>
            {_html_escape(preview)}
        </div>
        <div style="background:rgba(59,130,246,0.1);border:1px solid #3b82f6;border-radius:8px;padding:16px;text-align:center;">
            <div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:8px;">
                Start your 30-day free trial
            </div>
            <div style="color:#94a3b8;font-size:13px;margin-bottom:12px;">
                {plan} plan — {full_price} after trial. No charge today.
            </div>
            <div style="display:flex;gap:8px;justify-content:center;">
                <a href="/api/checkout?plan={plan.lower()}&trial=30"
                   style="background:#3b82f6;color:white;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
                    Start Free Trial
                </a>
                <button onclick="closeProPreview()"
                        style="background:transparent;color:#64748b;border:1px solid #334155;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;">
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
    <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;text-align:center;">
        <h3 style="color:#f8fafc;font-size:16px;margin-bottom:8px;">✨ Pro Licensing Coming Soon</h3>
        <p style="color:#94a3b8;font-size:13px;margin-bottom:16px;">Leave your email to be notified when Pro billing is available. First 30 days free.</p>
        <form action="/api/waitlist" method="post" style="display:flex;gap:8px;flex-direction:column;">
            <input type="email" name="email" placeholder="you@example.com" required
                   style="background:#0f172a;border:1px solid #334155;padding:10px 14px;border-radius:6px;color:#e2e8f0;font-size:14px;">
            <input type="hidden" name="plan" value="{plan}">
            <button type="submit" style="background:#3b82f6;color:white;border:none;padding:10px;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;">
                Notify me when Pro launches
            </button>
        </form>
        <p style="color:#64748b;font-size:11px;margin-top:12px;">No spam. We'll only email you once.</p>
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
        return HTMLResponse(f"""<div class="detail-content" style="padding:20px;text-align:center;">
    <div style="font-size:32px;margin-bottom:8px;">🔍</div>
    <div style="color:#f8fafc;font-size:14px;font-weight:600;">Agent not found</div>
    <div style="color:#64748b;font-size:12px;margin-top:4px;">No agent named "{_html_escape(name)}" is registered. Run <code style="background:#1e293b;padding:2px 6px;border-radius:4px;">observeco agents discover</code> to scan.</div>
</div>""")

    pulses = db.get_recent_pulses(agent_name=name, limit=24)
    errors = db.get_errors(agent_name=name, limit=20)
    trims = db.get_trims(agent_name=name, limit=20)
    drift = db.get_drift(agent_name=name)
    garden = db.get_gardens(agent_name=name)

    circuit = {b["agent_name"]: b for b in db.get_circuit_breakers()}.get(name, {})
    profile = db.get_profiles(agent_name=name)

    # Determine framework
    agents_cfg = {a["agent_name"]: a for a in db.get_agents()}
    framework = agents_cfg.get(name, {}).get("framework", "hermes") if agents_cfg else "hermes"

    if tab == "health":
        return _detail_health_tab(name, pulses, errors, circuit, framework)
    elif tab == "tokens":
        return _detail_tokens_tab(name, trims, drift, framework)
    elif tab == "garden" or tab == "memory":
        return _detail_garden_tab(name, garden, profile, framework)
    return HTMLResponse("<div>Unknown tab</div>")


def _detail_health_tab(name: str, pulses: list, errors: list, circuit: dict, framework: str) -> str:
    now = int(time.time())

    # Pulse history — last 24h as dots
    dot_row = []
    for p in pulses[:24]:
        dot = "🟢" if p["status"] == "alive" else "🔴" if p["status"] == "dead" else "🟡"
        ts = _fmt_ts(p["timestamp"])
        dot_row.append(f'<span title="{p["status"]} @ {ts}" style="cursor:help;">{dot}</span>')

    circuit_html = ""
    if circuit.get("tripped"):
        cd = circuit.get("cooldown_until", 0)
        remaining = max(0, cd - now) if cd else 0
        circuit_html = f"""
        <div class="detail-row">
            <span style="color:#94a3b8;">Circuit</span>
            <span style="color:#ef4444;font-weight:600;">🔴 TRIPPED ({circuit.get('failure_count',0)} failures)</span>
        </div>
        <div class="detail-row">
            <span style="color:#94a3b8;">Cooldown remaining</span>
            <span style="color:#e2e8f0;">{remaining // 60}m {remaining % 60}s</span>
        </div>
        <div style="margin-top:8px;">
            <button onclick="resetCircuit('{name}')" style="background:#ef4444;color:white;border:none;padding:6px 16px;border-radius:6px;font-size:12px;cursor:pointer;">Reset circuit</button>
        </div>"""
    else:
        circuit_html = f"""
        <div class="detail-row">
            <span style="color:#94a3b8;">Circuit</span>
            <span style="color:#22c55e;font-weight:600;">✅ OK</span>
        </div>
        <div class="detail-row">
            <span style="color:#94a3b8;">Max retries</span>
            <span style="color:#e2e8f0;">{circuit.get('max_retries', 3)}</span>
        </div>"""

    errors_html = ""
    for e in errors[:10]:
        sev = e.get("severity", "warning")
        ts_str = _fmt_ts(e["timestamp"])
        col = {"error": "#ef4444", "critical": "#ef4444", "warning": "#eab308", "info": "#3b82f6"}.get(sev, "#6b7280")
        errors_html += f"""<div class="detail-error" style="border-left:2px solid {col};padding:4px 8px;margin-bottom:4px;font-size:12px;">
    <span style="color:#64748b;font-family:monospace;">{ts_str}</span>
    <span style="color:{col};font-weight:600;">{e['error_type']}</span>
    <span style="color:#94a3b8;">{_html_escape(e.get('error_message','')[:100])}</span>
</div>"""

    if not errors_html:
        errors_html = '<div style="color:#6b7280;font-size:13px;padding:8px;">No errors recorded — your agents are running clean. Errors appear here automatically when pulse checks detect failures or when agents log error events.</div>'

    framework_label = "Hermes" if framework == "hermes" else "OpenClaw"

    return HTMLResponse(f"""<div class="detail-content health-tab" style="padding:12px;">
    <div style="margin-bottom:12px;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">Agent Framework</div>
        <div style="color:#38bdf8;font-weight:600;font-size:14px;">{framework_label}</div>
    </div>
    <div style="margin-bottom:12px;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Pulse History (last 24h)</div>
        <div style="font-size:16px;letter-spacing:2px;">{"".join(dot_row) or '<span style="color:#64748b;font-size:13px;letter-spacing:0;">No pulses recorded yet</span>'}</div>
    </div>
    {circuit_html}
    <div style="margin-top:12px;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Last 10 Errors</div>
        {errors_html}
    </div>
</div>""")


def _detail_tokens_tab(name: str, trims: list, drift: list, framework: str) -> str:
    if framework == "hermes":
        # Hermes token breakdown
        latest_trim = trims[0] if trims else None
        if latest_trim:
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
                bars.append(f"""<div class="token-detail-row" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:12px;">
    <span style="width:70px;color:#94a3b8;">{comp_label}</span>
    <div style="flex:1;height:12px;background:#0f172a;border-radius:6px;overflow:hidden;">
        <div style="width:{pct:.1f}%;height:100%;background:{col};border-radius:6px;"></div>
    </div>
    <span style="width:80px;text-align:right;color:#e2e8f0;font-family:monospace;">{val:,} tok ({pct:.0f}%)</span>
</div>""")

            savings = latest_trim.get("savings_ratio", 0)
            savings_html = f"""<div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px 12px;margin-top:8px;font-size:12px;color:#22c55e;">
    CHISEL saved {savings:.0%} this session
</div>""" if savings > 0 else ""

            drift_html = _detail_drift_html(drift, name)

            return HTMLResponse(f"""<div class="detail-content tokens-tab" style="padding:12px;">
    <div style="margin-bottom:8px;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">Token Breakdown</div>
        <div style="color:#e2e8f0;font-size:24px;font-weight:700;font-family:monospace;margin-top:4px;">{total_display:,} <span style="font-size:14px;color:#64748b;font-weight:400;">total</span></div>
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
                bars.append(f"""<div class="token-detail-row" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:12px;">
    <span style="width:80px;color:#94a3b8;">{comp}</span>
    <div style="flex:1;height:12px;background:#0f172a;border-radius:6px;overflow:hidden;">
        <div style="width:{pct:.1f}%;height:100%;background:{col};border-radius:6px;"></div>
    </div>
    <span style="width:80px;text-align:right;color:#e2e8f0;font-family:monospace;">{val:,} tok</span>
</div>""")

            loads = db.get_loads(agent_name=name)
            total_saved = sum(l.get("tokens_saved", 0) for l in loads[:20])
            savings_html = f"""<div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px 12px;margin-top:8px;font-size:12px;color:#22c55e;">
    ClawForge saved ~{total_saved:,} tokens across {len(loads)} turns
</div>""" if total_saved > 0 else ""

            return HTMLResponse(f"""<div class="detail-content tokens-tab" style="padding:12px;">
    <div style="margin-bottom:8px;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">Source Breakdown</div>
        <div style="color:#e2e8f0;font-size:24px;font-weight:700;font-family:monospace;margin-top:4px;">{total_est:,} <span style="font-size:14px;color:#64748b;font-weight:400;">estimated tokens</span></div>
    </div>
    {"".join(bars)}
    {savings_html}
</div>""")
        return HTMLResponse('<div style="padding:12px;color:#6b7280;">No profile data — run `observeco clawforge profile`</div>')


def _detail_drift_html(drift: list, name: str) -> str:
    agent_drift = [d for d in drift if d["agent_name"] == name]
    if not agent_drift:
        return "<div style='color:#6b7280;font-size:13px;margin-top:12px;'>No drift data yet</div>"

    items = []
    for d in agent_drift[:7]:
        comp = d.get("component", "system prompt")
        pct = d.get("delta_pct", 0)
        breached = d.get("breached", 0)
        color = "#ef4444" if breached else "#22c55e" if pct < 0 else "#f97316"
        icon = "📈" if pct > 0 else "📉"
        items.append(f"""<div class="drift-detail-row" style="display:flex;gap:12px;font-size:12px;padding:4px 0;border-bottom:1px solid #1e293b;">
    <span>{icon}</span>
    <span style="color:#94a3b8;width:80px;">{_html_escape(comp)}</span>
    <span style="color:{color};font-weight:600;width:60px;">{pct:+.1f}%</span>
    <span style="color:#6b7280;">{'⛔ Breach' if breached else ''}</span>
</div>""")

    return f"""<div style="margin-top:12px;">
    <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Drift Trend</div>
    {"".join(items)}
</div>"""


def _detail_garden_tab(name: str, garden: list, profile: list, framework: str) -> str:
    if framework != "openclaw" and framework != "clawforge":
        # Hermes agents use chisel trim for memory optimization, not clawforge garden
        # But if garden data exists, show it anyway
        if garden and garden[0].get("memory_debt_score") is not None:
            pass  # fall through to garden rendering below
        else:
            return HTMLResponse(f"""<div class="detail-content garden-tab" style="padding:12px;">
    <div style="color:#6b7280;font-size:13px;line-height:1.6;">
        <div style="margin-bottom:12px;font-size:14px;font-weight:600;color:#94a3b8;">💾 Memory & Context</div>
        <div>This Hermes agent uses <strong>CHISEL</strong> for context optimization — check the <strong>📊 Tokens</strong> tab for trim savings and token breakdown.</div>
        <div style="margin-top:10px;padding:8px 12px;background:#0f172a;border-radius:8px;border-left:3px solid #3b82f6;">
            <div style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">💡 Did you know?</div>
            <div style="color:#e2e8f0;font-size:12px;">The <strong>🧠 Memory</strong> tab shows garden/consciousness data for OpenClaw agents. For Hermes agents, memory optimization is tracked via CHISEL in the Tokens tab.</div>
        </div>
        <div style="margin-top:12px;color:#64748b;font-size:11px;">
            <code style="background:#1e293b;padding:2px 6px;border-radius:4px;">observeco clawforge garden</code> — runs garden analysis for OpenClaw agents
        </div>
    </div>
</div>""")
    
    if not garden:
        return HTMLResponse('<div style="padding:12px;color:#6b7280;">No garden data yet — run `observeco clawforge garden`.</div>')

    g = garden[0]
    score = g.get("memory_debt_score", 0)
    grade = "A" if score < 20 else "B" if score < 40 else "C" if score < 60 else "D" if score < 80 else "F"
    grade_color = "#22c55e" if grade == "A" else "#eab308" if grade in ("B", "C") else "#ef4444"

    return HTMLResponse(f"""<div class="detail-content garden-tab" style="padding:12px;">
    <div style="display:flex;gap:16px;align-items:center;margin-bottom:16px;">
        <div style="text-align:center;">
            <div style="font-size:36px;font-weight:700;color:{grade_color};">{score:.0f}</div>
            <div style="font-size:11px;color:#64748b;">Debt Score</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:36px;font-weight:700;color:{grade_color};">{grade}</div>
            <div style="font-size:11px;color:#64748b;">Grade</div>
        </div>
    </div>
    <div class="garden-metrics" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px;text-align:center;">
            <div style="color:#ef4444;font-size:18px;font-weight:700;">{g['duplicates_found']}</div>
            <div style="color:#64748b;font-size:11px;">Duplicates</div>
        </div>
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px;text-align:center;">
            <div style="color:#f97316;font-size:18px;font-weight:700;">{g['contradictions_found']}</div>
            <div style="color:#64748b;font-size:11px;">Contradictions</div>
        </div>
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px;text-align:center;">
            <div style="color:#6b7280;font-size:18px;font-weight:700;">{g['stale_entries']}</div>
            <div style="color:#64748b;font-size:11px;">Stale Entries</div>
        </div>
    </div>
</div>""")


# ── NEW: /api/errors —— Error Timeline ──────────────────────────────

@app.get("/api/errors", response_class=HTMLResponse)
async def api_errors():
    """Error timeline — §6.5. Categorized + plain-English verdict."""
    errors = db.get_errors(limit=50)
    if not errors:
        return HTMLResponse('<div style="color:#6b7280;font-size:13px;text-align:center;padding:20px;">✅ No errors in the last 24h. Errors appear here automatically when pulse checks detect failures or when agents log error events.</div>')
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
        parts.append(f"""<span style="color:#f59e0b;">⏱ {categories["timeout"]} timeout{'s' if categories["timeout"] > 1 else ''}</span> — agent was running but didn't respond in time. Usually overloaded or stuck.""")
    if categories["connection"]:
        parts.append(f"""<span style="color:#ef4444;">🔗 {categories["connection"]} connection refused</span> — the agent endpoint is down or unreachable.""")
    if categories["resource"]:
        parts.append(f"""<span style="color:#f97316;">🔍 {categories["resource"]} resource{'s' if categories["resource"] > 1 else ''} not found</span> — a dependency the agent needs is missing.""")
    if categories["http_5xx"]:
        parts.append(f"""<span style="color:#ef4444;">🌐 {categories["http_5xx"]} HTTP 5xx</span> — the server returned an internal error.""")
    if categories["other"]:
        parts.append(f"""<span style="color:#64748b;">❓ {categories["other"]} other error{'s' if categories["other"] > 1 else ''}</span> — check the full list below.""")

    # Verdict
    if total == 1:
        verdict = '<span style="color:#eab308;">🟡 1 error in 24h — likely transient. Monitor but no action needed unless it reappears.</span>'
    elif total <= 3:
        verdict = f'<span style="color:#f97316;">🟠 {total} errors in 24h — agent may be unstable. Check the categories below.</span>'
    else:
        verdict = f'<span style="color:#ef4444;">🔴 {total} errors in 24h — ongoing problem detected. Check guard status and agent health.</span>'

    # Summary banner
    html = f"""
<div class="error-summary" style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;margin-bottom:12px;">
    <div style="font-size:13px;color:#e2e8f0;font-weight:600;margin-bottom:8px;">📊 Error Summary — {total} in last 24h</div>
    <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">
        {"<br>".join(parts) if parts else "No issues detected."}
    </div>
    <div style="font-size:13px;margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;">
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
        items.append(f"""<div class="error-item severity-{sev}" style="border-left:3px solid {col};padding:8px 10px;margin-bottom:4px;border-radius:6px;background:rgba(15,23,42,0.5);font-size:12px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
        <span style="color:{col};font-weight:600;">{icon} {_html_escape(e.get('error_type','error'))}</span>
        <span style="color:#64748b;font-size:11px;">{ts}</span>
    </div>
    <div style="color:#94a3b8;">{_html_escape(msg[:120])}</div>
    <div style="margin-top:2px;">
        <span style="color:#38bdf8;font-weight:500;font-size:11px;">{_html_escape(agent)}</span>
    </div>
</div>""")

    return HTMLResponse(html + "\n".join(items))


@app.get("/api/reset-circuit/{agent_name}")
async def api_reset_circuit(agent_name: str):
    """Reset a tripped circuit breaker."""
    db.reset_breaker(agent_name)
    return HTMLResponse(f'<span style="color:#22c55e;font-size:13px;">Circuit reset for {agent_name}</span>')


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

    trip_badge = f'<span style="background:#ef4444;color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">⚠️ {tripped} tripped</span>' if tripped else ""

    return HTMLResponse(f"""<div class="fleet-stats" style="display:flex;gap:12px;flex-wrap:wrap;">
    <div class="stat-box total" style="padding:12px 20px;border-radius:8px;background:#1e293b;border:1px solid #334155;">
        <span class="stat-num" style="font-size:28px;font-weight:700;display:block;color:#38bdf8;">{total}</span>
        <span style="color:#94a3b8;font-size:14px;">Agents</span>
    </div>
    <div class="stat-box alive" style="padding:12px 20px;border-radius:8px;background:#1e293b;border:1px solid #334155;">
        <span class="stat-num" style="font-size:28px;font-weight:700;display:block;color:#22c55e;">{alive}</span>
        <span style="color:#94a3b8;font-size:14px;">🟢 Alive</span>
    </div>
    <div class="stat-box dead" style="padding:12px 20px;border-radius:8px;background:#1e293b;border:1px solid #334155;">
        <span class="stat-num" style="font-size:28px;font-weight:700;display:block;color:#ef4444;">{dead}</span>
        <span style="color:#94a3b8;font-size:14px;">🔴 Dead</span>
    </div>
    <div class="stat-box error" style="padding:12px 20px;border-radius:8px;background:#1e293b;border:1px solid #334155;">
        <span class="stat-num" style="font-size:28px;font-weight:700;display:block;color:#f59e0b;">{error_count}</span>
        <span style="color:#94a3b8;font-size:14px;">🟡 Errors</span>
    </div>
    {trip_badge}
    {f'<div class="stat-box drift" style="padding:12px 20px;border-radius:8px;background:#1e293b;border:1px solid #334155;"><span style="font-size:14px;color:{drift_color};">{drift_text}</span></div>' if drift_text else ""}
</div>""")


# ---------------------------------------------------------------------------
# §6.2 — Agent Cards (click-to-expand)
# ---------------------------------------------------------------------------

@app.get("/api/agents", response_class=HTMLResponse)
async def api_agents():
    """Agent cards with token bars, drift, expandable — §6.2."""
    summary = db.get_agent_status_summary()
    agents = db.get_agents()
    breakers = {b["agent_name"]: b for b in db.get_circuit_breakers()}
    trims = db.get_trims(limit=30)

    all_agent_names = set(a["agent_name"] for a in agents)
    for name in summary:
        all_agent_names.add(name)

    trimmed_agents = {}
    for t in trims:
        if t["agent_name"] not in trimmed_agents:
            trimmed_agents[t["agent_name"]] = t

    now = int(time.time())

    # Build agent-to-framework mapping
    agent_cfg = {a["agent_name"]: a for a in agents}
    name_fw = {}
    for name in all_agent_names:
        fw = agent_cfg.get(name, {}).get("framework", "hermes") if agent_cfg else "hermes"
        name_fw[name] = fw

    # Type grouping: derive agent type from health metadata
    # - "agent" = has SOUL.md source or is Hermes/OpenClaw framework
    # - "service" = has health_check but no SOUL.md (cron, daemon)
    # - "workflow" = custom framework, no health check
    name_type = {}
    for name in all_agent_names:
        a = agent_cfg.get(name, {})
        fw = a.get("framework", "custom")
        hc = a.get("health_check", "") or ""
        cfg_path = a.get("config_path", "") or ""
        if fw in ("hermes", "openclaw") or "SOUL.md" in cfg_path:
            name_type[name] = "agent"
        elif hc or fw == "service":
            name_type[name] = "service"
        else:
            name_type[name] = "workflow"

    # Group names by type
    sections = {"agent": [], "service": [], "workflow": []}
    for name in sorted(all_agent_names):
        t = name_type.get(name, "workflow")
        sections[t].append(name)

    # Render each section
    sections_html = []
    section_configs = [
        ("agent", "Agents", "#38bdf8", "🤖"),
        ("service", "Services", "#a78bfa", "⚙️"),
        ("workflow", "Workflows", "#6b7280", "🔄"),
    ]

    for sec_key, sec_label, sec_color, sec_icon in section_configs:
        names = sections[sec_key]
        if not names:
            continue

        cards_html = []
        for name in names:
            fw = name_fw[name]
            s = summary.get(name, {})
            status = s.get("status", "unknown")
            ts = s.get("timestamp", 0)
            cb = breakers.get(name, {})
            tripped = cb.get("tripped", 0)
            agent_type = name_type.get(name, "workflow")

            dot_color = {"alive": "#22c55e", "dead": "#ef4444", "error": "#f59e0b"}.get(status, "#6b7280")
            status_text = {"alive": "Alive", "dead": "Dead", "error": "Error"}.get(status, "Unknown")

            fw_label = {"agent": "Agent", "service": "Service", "workflow": "Workflow"}.get(agent_type, "Workflow")
            fw_color = {"agent": "#38bdf8", "service": "#a78bfa", "workflow": "#6b7280"}.get(agent_type, "#6b7280")

            # Error count badge
            errors = db.get_errors(agent_name=name, limit=50)
            error_count = len(errors)
            recent_errors = [e for e in errors if now - e.get("timestamp", 0) < 86400]
            recent_error_count = len(recent_errors)
            if recent_error_count > 0:
                badge_text = f"{recent_error_count} {'error' if recent_error_count==1 else 'errors'}"
                badge_class = "red" if status in ("dead", "error") else "yellow"
                error_badge = f"<span class=\"agent-error-badge {badge_class}\">! {badge_text}</span>"
            else:
                error_badge = ""

            # Discovery gap badges per §obs-dp-006
            gap_badges = []
            pulses = db.get_recent_pulses(agent_name=name, limit=5)
            if not pulses:
                gap_badges.append('<span style="font-size:10px;color:#64748b;background:#0f172a;padding:1px 5px;border-radius:4px;border:1px solid #334155;" title="No heartbeat data collected yet">🔍 No pulses</span>')
            trims = db.get_trims(agent_name=name, limit=1)
            if not trims:
                gap_badges.append('<span style="font-size:10px;color:#64748b;background:#0f172a;padding:1px 5px;border-radius:4px;border:1px solid #334155;" title="No token profile data — run agent to generate">🔍 No tokens</span>')
            drift = db.get_drift(agent_name=name)
            if not drift:
                gap_badges.append('<span style="font-size:10px;color:#64748b;background:#0f172a;padding:1px 5px;border-radius:4px;border:1px solid #334155;" title="No drift data — needs 7d+ of token history">🔍 No drift</span>')
            gap_badges_html = " <span style=\"color:#334155;font-size:9px;\">|</span> ".join(gap_badges) if gap_badges else ""

            # Token bar
            trim_data = trimmed_agents.get(name)
            token_bar_html = ""
            total_tok = 0
            if trim_data:
                comps = [
                    ("identity", trim_data.get("identity_tokens", 0)),
                    ("skills", trim_data.get("skills_tokens", 0)),
                    ("memory", trim_data.get("memory_tokens", 0)),
                    ("tools", trim_data.get("tools_tokens", 0)),
                    ("guidance", trim_data.get("guidance_tokens", 0)),
                ]
                comps_sorted = sorted(comps, key=lambda x: -x[1])
                total_tok = max(trim_data.get("total_tokens", 1), 1)
                segments = ""
                for comp, val in comps_sorted:
                    pct = val / total_tok * 100
                    col = {"identity": "#6366f1", "skills": "#8b5cf6", "memory": "#ec4899",
                           "tools": "#14b8a6", "guidance": "#f97316"}.get(comp, "#6b7280")
                    segments += f'<span style="display:inline-block;height:100%;width:{pct:.1f}%;background:{col};" title="{comp}: {val:,} tok"></span>'
                token_bar_html = f"""<div style="margin-top:6px;">
        <div style="height:8px;background:#0f172a;border-radius:4px;overflow:hidden;display:flex;">{segments}</div>
        <div style="display:flex;justify-content:space-between;margin-top:2px;">
            <span style="color:#64748b;font-size:10px;">{total_tok:,} total</span>
        </div>
    </div>"""

            # Drift sparkline (simple inline SVG)
            drift_data = db.get_drift(agent_name=name)
            drift_sparkline = ""
            avg_drift = 0
            if drift_data:
                vals = [d.get("delta_pct", 0) for d in drift_data[-7:]]
                if vals:
                    mn, mx = min(vals), max(vals)
                    rng = max(abs(mx - mn), 1)
                    pts = " ".join(f"{i * 10},{30 - (v - mn) / rng * 25}" for i, v in enumerate(vals))
                    avg_drift = sum(vals) / len(vals)
                    drift_color = "#22c55e" if avg_drift < 0 else "#f97316" if avg_drift > 5 else "#94a3b8"
                    drift_sparkline = f"""<div style="display:flex;align-items:center;gap:4px;margin-top:4px;">
        <span style="font-size:11px;color:{drift_color};">{avg_drift:+.1f}%</span>
        <svg width="60" height="20" viewBox="0 0 60 30">
            <polyline points="{pts}" fill="none" stroke="{drift_color}" stroke-width="2"/>
        </svg>
    </div>"""

            # Circuit indicator
            circuit_badge = "🔴 Circuit" if tripped else "✅ Circuit OK"

            last_checkin = _fmt_ts(ts) if ts else "—"

            # Build metric row labels
            status_label = {"alive": "🟢 Healthy", "dead": "🔴 Dead", "error": "🟡 Error"}.get(status, "⚫ Unknown")
            guard_label = "🔴 Stopped (failed 3x)" if tripped else "✅ Guard OK"
            error_row_label = f"⚠️ {recent_error_count} error{'s' if recent_error_count != 1 else ''} in 24h" if recent_error_count > 0 else "- No errors"

            # Brain size / drift
            avg_drift_val = avg_drift if 'avg_drift' in dir() else 0
            drift_label = "📈 Learning..." if not drift_sparkline else f"📊 {avg_drift:+.1f}%" if drift_data else "📊 - Drift stable"

            cards_html.append(f"""<div class="agent-card" id="card-{name}" data-agent="{name}"\n         style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;position:relative;">
        <div class="card-header" style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span class="status-dot" style="width:10px;height:10px;border-radius:50%;background:{dot_color};flex-shrink:0;" title="{status_text}"></span>
            <span class="agent-name" style="font-weight:600;font-size:14px;color:#e2e8f0;">{_html_escape(name)}</span>
            {error_badge}
            <span style="font-size:11px;color:{fw_color};background:#1e293b;padding:2px 6px;border-radius:4px;margin-left:auto;">{fw_label}</span>
            <span class="dismiss-btn" onclick="event.stopPropagation();dismissAgent('{name}')"
                  style="color:#64748b;cursor:pointer;font-size:14px;margin-left:4px;padding:0 4px;border-radius:4px;"
                  onmouseenter="this.style.background='#1e293b';this.style.color='#ef4444';"
                  onmouseleave="this.style.background='transparent';this.style.color='#64748b';"
                  title="Hide agent card">×</span>
        </div>
        {f'<div class="gap-badges" style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px;padding:0 4px;">{gap_badges_html}</div>' if gap_badges_html else ''}
        <div class="metric-rows">
            <div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for Health details">
                <span style="color:#64748b;font-size:13px;">Health</span>
                <span style="display:flex;align-items:center;gap:6px;">
                    <span style="color:#e2e8f0;font-size:13px;">{status_label} — {last_checkin}</span>
                    <span class="see-details" style="color:#38bdf8;font-size:11px;opacity:0;">See details ›</span>
                </span>
            </div>
            <div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for Guard details">
                <span style="color:#64748b;font-size:13px;">Guard</span>
                <span style="display:flex;align-items:center;gap:6px;">
                    <span style="color:{'#ef4444' if tripped else '#22c55e'};font-size:13px;">{guard_label}</span>
                    <span class="see-details" style="color:#38bdf8;font-size:11px;opacity:0;">See details ›</span>
                </span>
            </div>
            <div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for Error details">
                <span style="color:#64748b;font-size:13px;">Errors</span>
                <span style="display:flex;align-items:center;gap:6px;">
                    <span style="color:{'#f59e0b' if recent_error_count > 0 else '#6b7280'};font-size:13px;">{error_row_label}</span>
                    <span class="see-details" style="color:#38bdf8;font-size:11px;opacity:0;">See details ›</span>
                </span>
            </div>
            <div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for Brain size / drift details">
                <span style="color:#64748b;font-size:13px;">Brain size</span>
                <span style="display:flex;align-items:center;gap:6px;">
                    <span style="color:#e2e8f0;font-size:13px;">{drift_label}</span>
                    <span class="see-details" style="color:#38bdf8;font-size:11px;opacity:0;">See details ›</span>
                </span>
            </div>
            <div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for Token composition details">
                <span style="color:#64748b;font-size:13px;">Composition</span>
                <span style="display:flex;align-items:center;gap:6px;">
                        {token_bar_html if trim_data else '<span style="color:#6b7280;font-size:13px;">No token data</span>'}
                    <span class="see-details" style="color:#38bdf8;font-size:11px;opacity:0;">See details ›</span>
                </span>
            </div>
        </div>
        <div class="agent-detail" id="detail-{name}">
            <div style="margin-top:10px;border-top:1px solid #1e293b;padding-top:10px;">
                <div style="display:flex;gap:8px;margin-bottom:8px;">
                    <button onclick="event.stopPropagation();loadAgentTab('{name}','health')" class="tab-btn active" id="tab-{name}-health">Health</button>
                    <button onclick="event.stopPropagation();loadAgentTab('{name}','tokens')" class="tab-btn" id="tab-{name}-tokens">📊 Tokens</button>
                    <button onclick="event.stopPropagation();loadAgentTab('{name}','garden')" class="tab-btn" id="tab-{name}-memory">🧠 Memory</button>
                </div>
                <div id="detail-content-{name}" style="font-size:13px;color:#94a3b8;">Loading health data...</div>
            </div>
        </div>
    </div>""")

        # Wrap cards in section
        count = len(cards_html)
        cards_str = "\n".join(cards_html)
        sections_html.append(f"""<div class="agent-section" id="section-{sec_key}">
    <div class="section-header" onclick="toggleSection('{sec_key}')"
         style="display:flex;align-items:center;gap:8px;padding:10px 0;cursor:pointer;user-select:none;border-bottom:1px solid var(--border);margin-bottom:12px;">
        <span style="font-size:16px;">{sec_icon}</span>
        <span style="color:{sec_color};font-size:16px;font-weight:700;">{sec_label}</span>
        <span style="background:#1e293b;color:#64748b;padding:1px 8px;border-radius:10px;font-size:11px;">{count}</span>
        <span style="margin-left:auto;color:#64748b;font-size:12px;transition:transform 0.2s;" class="section-toggle" id="toggle-{sec_key}">▼</span>
    </div>
    <div class="section-cards" id="cards-{sec_key}">
        {cards_str}
    </div>
</div>""")

    return HTMLResponse("\n".join(sections_html))


# ---------------------------------------------------------------------------
# §4.6 — Code Graph Panel
# ---------------------------------------------------------------------------

@app.get("/api/graph/overview", response_class=HTMLResponse)
async def api_graph_overview():
    """Code graph overview panel — stats + quick search."""
    from observeco.graph.db import GraphDB
    gdb = GraphDB()
    stats = gdb.get_stats()
    return HTMLResponse(f"""<div class="graph-overview" style="padding:4px;">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;">
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px;text-align:center;">
            <div style="color:#38bdf8;font-size:20px;font-weight:700;">{stats.get('nodes', 0)}</div>
            <div style="color:#64748b;font-size:11px;">Symbols</div>
        </div>
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px;text-align:center;">
            <div style="color:#22c55e;font-size:20px;font-weight:700;">{stats.get('edges', 0)}</div>
            <div style="color:#64748b;font-size:11px;">Relations</div>
        </div>
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px;text-align:center;">
            <div style="color:#a78bfa;font-size:20px;font-weight:700;">{stats.get('files', 0)}</div>
            <div style="color:#64748b;font-size:11px;">Files Indexed</div>
        </div>
    </div>
    <div style="display:flex;gap:8px;margin-bottom:8px;">
        <input id="graph-search-input" placeholder="Search symbols..." style="flex:1;background:#0f172a;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;outline:none;"
               onkeyup="if(event.key==='Enter') searchGraph()" />
        <button onclick="searchGraph()" style="background:#2563eb;color:white;border:none;border-radius:6px;padding:8px 16px;font-size:13px;cursor:pointer;">Search</button>
    </div>
    <div id="graph-results" style="max-height:300px;overflow-y:auto;"></div>
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
        return HTMLResponse('<div style="color:#6b7280;font-size:13px;">Enter a search term</div>')
    from observeco.graph.db import GraphDB
    gdb = GraphDB()
    results = gdb.search_nodes(q, limit=limit)
    if not results:
        return HTMLResponse('<div style="color:#6b7280;font-size:13px;">No results</div>')
    items = []
    for r in results:
        kind = r["kind"]
        icon = {"function": "\u0192", "method": "\u0192", "class": "\u00a7", "import": "\u21e2", "variable": "\u2205"}.get(kind, "\u00b7")
        color = {"function": "#22c55e", "method": "#22c55e", "class": "#38bdf8",
                 "import": "#a78bfa", "variable": "#f59e0b"}.get(kind, "#94a3b8")
        items.append(f"""<div class="graph-result" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-bottom:1px solid #1e293b;font-size:12px;cursor:pointer;"
     onclick="toggleGraphDetail('{r['qualified_name']}')">
    <span style="color:{color};font-weight:700;font-family:monospace;width:20px;">{icon}</span>
    <span style="color:#e2e8f0;flex:1;">{r['qualified_name']}</span>
    <span style="color:#64748b;">{r.get('file_path','').split('/')[-1]}:{r.get('start_line','')}</span>
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
        return HTMLResponse(f'<div style="color:#ef4444;font-size:13px;">Symbol not found: {name}</div>')

    callers = gdb.get_callers(node["id"])
    callees = gdb.get_callees(node["id"])
    arr_left = "\u2190"
    arr_right = "\u2192"

    html = f"""<div class="graph-symbol-detail" style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px;margin-top:8px;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="color:#38bdf8;font-weight:600;">{name}</span>
        <span style="color:#64748b;font-size:11px;">{node['file_path'].split('/')[-1]}:{node['start_line']}</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div>
            <div style="color:#64748b;font-size:11px;text-transform:uppercase;margin-bottom:4px;">Called by ({len(callers)})</div>
            {''.join(f'<div style="padding:3px 0;font-size:11px;color:#22c55e;">{arr_left} {c["qualified_name"]} [{c["file_path"].split("/")[-1]}:{c["start_line"]}]</div>' for c in callers) if callers else '<div style="color:#6b7280;font-size:11px;">No callers</div>'}
        </div>
        <div>
            <div style="color:#64748b;font-size:11px;text-transform:uppercase;margin-bottom:4px;">Calls ({len(callees)})</div>
            {''.join(f'<div style="padding:3px 0;font-size:11px;color:#a78bfa;">{arr_right} {c["qualified_name"]} [{c["file_path"].split("/")[-1]}:{c["start_line"]}]</div>' for c in callees) if callees else '<div style="color:#6b7280;font-size:11px;">No callees</div>'}
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
        "detail": """<div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:8px;">
    <div style="background:#0f172a;padding:8px;border-radius:6px;text-align:center;"><div style="font-size:20px;">🟢</div><div style="font-size:12px;color:#22c55e;font-weight:600;">Alive</div><div style="font-size:11px;color:#64748b;">Responded to last pulse check within expected interval. Typically checked every 30s.</div></div>
    <div style="background:#0f172a;padding:8px;border-radius:6px;text-align:center;"><div style="font-size:20px;">🔴</div><div style="font-size:12px;color:#ef4444;font-weight:600;">Dead</div><div style="font-size:11px;color:#64748b;">Process not found, health endpoint timeout, or no response after N retries. Circuit breaker may have tripped.</div></div>
    <div style="background:#0f172a;padding:8px;border-radius:6px;text-align:center;"><div style="font-size:20px;">🟡</div><div style="font-size:12px;color:#f59e0b;font-weight:600;">Error</div><div style="font-size:11px;color:#64748b;">Agent is reachable but returning errors (e.g. HTTP 5xx, process exit code != 0). Needs investigation.</div></div>
    <div style="background:#0f172a;padding:8px;border-radius:6px;text-align:center;"><div style="font-size:20px;">⚪</div><div style="font-size:12px;color:#64748b;font-weight:600;">Unknown</div><div style="font-size:11px;color:#64748b;">No pulse data yet. Agent was registered but never checked. Run <code>observeco pulse check</code> to start.</div></div>
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
        "detail": """<div style="margin-top:8px;padding:10px;background:#0f172a;border-radius:6px;font-size:12px;line-height:1.6;color:#94a3b8;">
    <strong style="color:#e2e8f0;">How it works:</strong> After 3 consecutive failures, the circuit breaker trips and enters cooldown (5 minutes by default). During cooldown, the agent is not checked. After cooldown expires, it tries again automatically.<br><br>
    <strong style="color:#e2e8f0;">What it saves:</strong> Without this guard, a single dead agent would generate 2,880 error checks per day. With it, you see ~8. That's a <strong style="color:#22c55e;">99.7% reduction</strong> in log noise.
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
        "detail": """<div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:8px;">
    <div style="background:#0f172a;padding:8px;border-radius:6px;"><div style="font-size:12px;color:#6366f1;font-weight:600;">Identity</div><div style="font-size:11px;color:#64748b;">Agent's role, personality, and behavioral contract. Usually stable.</div></div>
    <div style="background:#0f172a;padding:8px;border-radius:6px;"><div style="font-size:12px;color:#8b5cf6;font-weight:600;">Skills</div><div style="font-size:11px;color:#64748b;">Instructions for tools and capabilities. Grows as skills are added.</div></div>
    <div style="background:#0f172a;padding:8px;border-radius:6px;"><div style="font-size:12px;color:#ec4899;font-weight:600;">Memory</div><div style="font-size:11px;color:#64748b;">Conversation history, learned patterns. The most dynamic component.</div></div>
    <div style="background:#0f172a;padding:8px;border-radius:6px;"><div style="font-size:12px;color:#14b8a6;font-weight:600;">Tools</div><div style="font-size:11px;color:#64748b;">API descriptions, function schemas. Grows with tool count.</div></div>
    <div style="background:#0f172a;padding:8px;border-radius:6px;"><div style="font-size:12px;color:#f97316;font-weight:600;">Guidance</div><div style="font-size:11px;color:#64748b;">Framework instructions, routing rules. Often the largest component.</div></div>
</div>""",
        "faq": [
            ("Why is Guidance always the biggest?", "Because it includes the framework's system-level instructions (Hermes routing, tool dispatch rules). This is normal. Run `observeco chisel trim` to see compression opportunities."),
            ("What should I do if tokens keep growing?", "Run `observeco chisel skills` to find bloated skills. Skills are the most common source of token bloat. Each skill description is loaded into every session."),
        ],
    },
    "drift": {
        "title": "Drift",
        "icon": "📈",
        "one_liner": "Measures how much your agent's system prompt size has changed over 7 days — positive drift means it's growing (and costing more).",
        "detail": """<div style="margin-top:8px;padding:10px;background:#0f172a;border-radius:6px;font-size:12px;line-height:1.6;color:#94a3b8;">
    <strong style="color:#e2e8f0;">Drift +10%</strong> means the system prompt is 10% larger than it was 7 days ago. Common causes: memory accumulation, skill additions, tool descriptions growing.<br><br>
    <strong style="color:#e2e8f0;">When to act:</strong> Drift >20% triggers a warning. Run <code>observeco chisel trim</code> to see exact token breakdown and identify which component is growing fastest.
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
        "detail": """<div style="margin-top:8px;padding:10px;background:#0f172a;border-radius:6px;font-size:12px;line-height:1.6;color:#94a3b8;">
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
        "detail": """<div style="margin-top:8px;padding:10px;background:#0f172a;border-radius:6px;font-size:12px;line-height:1.6;color:#94a3b8;">
    <strong style="color:#e2e8f0;">How it works:</strong> Pulse check sends a request to the agent's health endpoint (HTTP GET) or checks if the process exists (process name match). Results are stored in SQLite and rendered on the dashboard.<br><br>
    <strong style="color:#e2e8f0;">Three outcomes:</strong><br>
    🟢 <strong style="color:#22c55e;">Alive</strong> — Health endpoint responded OK or process found<br>
    🔴 <strong style="color:#ef4444;">Dead</strong> — No response or process not found<br>
    🟡 <strong style="color:#f59e0b;">Error</strong> — Reached but returned error<br><br>
    Run <code>observeco pulse check</code> from the CLI to see current status for all agents.
</div>""",
        "faq": [
            ("Do I need to set up health endpoints for every agent?", "No. ObserveCo auto-detects Hermes and OpenClaw agents. For custom agents, use `observeco agents add <name> --health-check <url_or_command>` or let the auto-discovery find them."),
            ("What happens if pulse.db doesn't exist?", "First run creates it automatically. The dashboard shows a phase banner guiding you through the first discovery."),
        ],
    },
    "heal-button": {
        "title": "Heal Button",
        "icon": "🔧",
        "one_liner": "Automatically diagnoses and fixes common agent problems — restart dead processes, clear tripped circuits, trim bloated contexts.",
        "detail": """<div style="margin-top:8px;padding:10px;background:#0f172a;border-radius:6px;font-size:12px;line-height:1.6;color:#94a3b8;">
    <strong style="color:#e2e8f0;">What it checks:</strong><br>
    • <strong>Process existence</strong> — Is the agent process running?<br>
    • <strong>Port availability</strong> — Is the configured port open?<br>
    • <strong>Config file integrity</strong> — Does the config path still exist?<br>
    • <strong>Circuit breaker state</strong> — Is it tripped? Should it be reset?<br><br>
    <strong style="color:#e2e8f0;">Pro:</strong> Auto-heal runs on a schedule and fixes issues without manual intervention. Free tier requires manual trigger.
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
        "detail": """<div style="margin-top:8px;padding:10px;background:#0f172a;border-radius:6px;font-size:12px;line-height:1.6;color:#94a3b8;">
    Three severity levels:<br>
    🔴 <strong style="color:#ef4444;">Critical</strong> — Circuit breaker tripped, agent dead. Action required.<br>
    🟡 <strong style="color:#f59e0b;">Warning</strong> — Drift exceeding 10%, error state. Monitor closely.<br>
    🔵 <strong style="color:#3b82f6;">Info</strong> — Heartbeat anomalies, unusual patterns. Investigate when convenient.<br><br>
    <strong style="color:#e2e8f0;">Pro:</strong> Push notifications via Telegram, webhook, or CLI. Free tier shows alerts in-dashboard only.
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
        return HTMLResponse('<div style="color:#6b7280;font-size:13px;padding:10px;">Topic not found. Available: status-dot, circuit, token-bar, drift, error-badge, pulse-check, heal-button, alerts-panel.</div>')

    faq_html = ""
    if entry.get("faq"):
        faq_items = []
        for q, a in entry["faq"]:
            faq_items.append(f'''<details style="margin-top:6px;padding:8px;background:#0f172a;border-radius:6px;font-size:12px;">
    <summary style="color:#38bdf8;font-weight:500;cursor:pointer;">❓ {q}</summary>
    <div style="margin-top:6px;color:#94a3b8;line-height:1.5;">{a}</div>
</details>''')
        faq_html = '<div style="margin-top:12px;"><div style="font-size:12px;font-weight:600;color:#e2e8f0;margin-bottom:4px;">FAQ</div>' + "\n".join(faq_items) + "</div>"

    return HTMLResponse(f"""<div style="padding:4px;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-size:22px;">{entry["icon"]}</span>
        <span style="font-size:15px;font-weight:600;color:#e2e8f0;">{entry["title"]}</span>
    </div>
    <div style="font-size:14px;color:#94a3b8;line-height:1.5;">{entry["one_liner"]}</div>
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
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


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
    summary_parts = [f'<span style="color:#64748b;font-size:12px;">🔍 Scan complete</span>']
    for s, cnt in sorted(by_status.items()):
        icon = {"green": "🟢", "yellow": "🟡", "red": "🔴", "teal": "🔵"}.get(s, "⚪")
        summary_parts.append(f'<span style="color:#64748b;font-size:12px;">{icon} {s}: {cnt}</span>')
    
    red_edges = [e for e in graph["edges"] if e["status"] == "red"]
    red_html = ""
    if red_edges:
        red_html = '<div style="margin-top:8px;padding:6px;background:#450a0a;border-radius:6px;font-size:12px;">'
        for e in red_edges:
            red_html += f'<div style="color:#ef4444;margin:2px 0;">🔴 Dead end: {e["source_name"]} → ∅</div>'
        red_html += "</div>"
    
    return HTMLResponse(f'<div style="padding:8px;">{" ".join(summary_parts)}{red_html}</div>')


# §3.19 — Communication Pathway Map page
PATHWAY_TEMPLATE = TEMPLATES_DIR / "pathway.html"

@app.get("/pathway", response_class=HTMLResponse)
async def pathway_page():
    """Serve the Cytoscape.js pathway map page."""
    if not PATHWAY_TEMPLATE.exists():
        return HTMLResponse("<h1>Pathway Map</h1><p>Template not found.</p>")
    return HTMLResponse(PATHWAY_TEMPLATE.read_text(encoding="utf-8"))


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


def serve(host: str = "127.0.0.1", port: int = 9119, static: bool = False, no_browser: bool = False) -> None:
    """Start the dashboard server."""
    if static:
        _generate_static(host, port)
        return

    actual_port = _find_free_port(host, port)
    url = f"http://{host}:{actual_port}"
    if not no_browser:
        webbrowser.open(url)
    if actual_port != port:
        print(f"ObserveCo Dashboard: {url} (port {port} was in use)")
    else:
        print(f"ObserveCo Dashboard: {url}")
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
        return HTMLResponse('<div class="empty-state" style="color:#64748b;font-size:13px;text-align:center;padding:20px;">No restart data yet. Restart data is collected during pulse checks.</div>')

    # Fleet-level totals
    total_healthy = sum(s["healthy"] for s in summary.values())
    total_toctou = sum(s["toctou"] for s in summary.values())
    total_crash = sum(s["crash"] for s in summary.values())
    total_all = total_healthy + total_toctou + total_crash

    # Fleet summary cards
    fleet_html = f"""<div class="fleet-summary" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
    <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;text-align:center;">
        <div style="font-size:24px;font-weight:700;color:#22c55e;">{total_healthy}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">Healthy Restarts</div>
    </div>
    <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;text-align:center;">
        <div style="font-size:24px;font-weight:700;color:#eab308;">{total_toctou}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">TOCTOU Races</div>
    </div>
    <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;text-align:center;">
        <div style="font-size:24px;font-weight:700;color:#ef4444;">{total_crash}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">Real Crashes</div>
    </div>
</div>"""

    # Legend
    legend_html = """<div style="display:flex;gap:16px;margin-bottom:16px;font-size:11px;color:#94a3b8;">
    <div style="display:flex;align-items:center;gap:4px;"><div style="width:8px;height:8px;border-radius:2px;background:#22c55e;"></div> Healthy restart — sub-second KeepAlive, no data loss</div>
    <div style="display:flex;align-items:center;gap:4px;"><div style="width:8px;height:8px;border-radius:2px;background:#eab308;"></div> TOCTOU race — file consumed between fsnotify and .stat()</div>
    <div style="display:flex;align-items:center;gap:4px;"><div style="width:8px;height:8px;border-radius:2px;background:#ef4444;"></div> Real crash — SIGSEGV, OOM, config error</div>
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

        border = ""
        if crash > 0:
            border = ' style="border-left:3px solid #ef4444;"'

        cards.append(f"""<div class="agent-card" id="rq-card-{agent_name}"{border}>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <div>
            <span style="font-weight:600;font-size:14px;color:#e2e8f0;">{_html_escape(agent_name)}</span>
        </div>
        <div>
            <span style="color:{far_color};font-size:11px;background:#0f172a;padding:2px 8px;border-radius:12px;">{far_icon} {far_text}</span>
        </div>
    </div>
    <div style="display:flex;gap:16px;margin-bottom:8px;font-size:12px;">
        <div><span style="color:#64748b;">Restarts:</span> <span style="font-weight:600;">{total}</span></div>
        <div><span style="color:#22c55e;">KeepAlive:</span> <span style="font-weight:600;">{healthy}</span></div>
        <div><span style="color:#eab308;">TOCTOU:</span> <span style="font-weight:600;">{toctou}</span></div>
        <div><span style="color:#ef4444;">Crashes:</span> <span style="font-weight:600;">{crash}</span></div>
    </div>
    <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-bottom:2px;">
            <span>Restart quality breakdown</span>
        </div>
        <div style="height:20px;background:#0f172a;border-radius:4px;display:flex;overflow:hidden;">
            {f'<div style="width:{green_pct:.0f}%;background:#166534;color:#22c55e;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;">{healthy}</div>' if healthy > 0 else ''}
            {f'<div style="width:{amber_pct:.0f}%;background:#713f12;color:#eab308;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;">{toctou}</div>' if toctou > 0 else ''}
            {f'<div style="width:{red_pct:.0f}%;background:#7f1d1d;color:#ef4444;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;">{crash}</div>' if crash > 0 else ''}
        </div>
    </div>
    <div style="font-size:11px;color:#64748b;cursor:pointer;" onclick="toggleRestartDetail('{agent_name}')">▶ View restart timeline</div>
    <div id="rq-detail-{agent_name}" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;">
        <div id="rq-detail-content-{agent_name}" style="font-size:12px;color:#64748b;">Loading...</div>
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
        return HTMLResponse('<div style="color:#6b7280;font-size:12px;padding:8px;">No restart data for this agent.</div>')

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
        snippet_html = f'<div style="color:#94a3b8;font-size:11px;background:#1e293b;padding:4px 8px;border-radius:4px;margin-top:2px;font-family:monospace;white-space:pre-wrap;">{_html_escape(snippet)}</div>' if snippet else ""

        items.append(f"""<div class="rtimeline-item" style="margin-bottom:8px;position:relative;padding-left:16px;">
    <div style="position:absolute;left:0;top:4px;width:8px;height:8px;border-radius:50%;background:{color};"></div>
    <div style="margin-bottom:2px;">
        <span style="color:#64748b;font-size:11px;">{ts_str}</span>
        <span style="color:{color};font-weight:600;margin-left:4px;font-size:12px;">{label}</span>
        {f'<span style="color:#64748b;font-size:11px;margin-left:8px;">{duration_str}</span>' if duration_str else ''}
    </div>
    {snippet_html}
    {f'<div style="color:#6b7280;font-size:10px;margin-top:1px;">{_html_escape(evidence)}</div>' if evidence else ''}
</div>""")

    return HTMLResponse(f"""<div style="position:relative;padding-left:0;">
    <div style="border-left:2px solid #334155;padding-left:0;">
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
    ("What is CHISEL?", "ObserveCo's system prompt compression for Hermes agents. Decomposes the prompt by component, measures tokens per section, and saves 15-30% per session via intelligent trimming."),
    ("What is ClawForge?", "Context optimizer for OpenClaw agents. Includes intent-aware loading (load only relevant sources), memory gardening (dedup, archive, flag contradictions), and skill usage intelligence."),
    ("What is Pro?", "Paid tier ($9/mo Solo, $49/mo Team) with push alerts via Telegram/webhook, never-pruned error history, fleet comparison, drift alerts, circuit auto-recovery, and multi-machine relay. 30-day free trial."),
    ("What do the gauge colors mean?", "🟢 Green = healthy. 🟡 Yellow = warning (1-2 missed heartbeats, drift >10%). 🔴 Red = critical (dead agent, tripped circuit). 🟠 Orange = token growth. 🔵 Blue = info/baseline."),
]

@app.get("/api/glossary", response_class=HTMLResponse)
async def api_glossary():
    items_html = []
    for i, (q, a) in enumerate(GLOSSARY_ITEMS):
        items_html.append(f"""
<div class="glossary-item" style="margin-bottom:4px;border:1px solid #334155;border-radius:8px;overflow:hidden;">
    <div class="glossary-q" onclick="toggleGlossary({i})"
         style="background:#0f172a;padding:10px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-size:13px;color:#e2e8f0;user-select:none;"
         onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='#0f172a'">
        <span>{q}</span>
        <span id="glossary-icon-{i}" style="color:#64748b;font-size:12px;transition:transform 0.2s;">▼</span>
    </div>
    <div id="glossary-answer-{i}" style="display:none;padding:10px 14px;font-size:12px;color:#94a3b8;line-height:1.6;">
        {a}
    </div>
</div>""")

    html = """
<div class="glossary-panel" style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;margin-top:16px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <div style="font-size:14px;font-weight:600;color:#e2e8f0;">📖 Glossary &amp; FAQ</div>
        <span onclick="toggleGlossarySection()" style="color:#64748b;font-size:12px;cursor:pointer;user-select:none;" id="glossary-toggle-label">▼ Show</span>
    </div>
    <div id="glossary-body" style="display:none;">
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
    <div class="heal-info" style="display:flex;justify-content:space-between;align-items:center;">
        <span class="heal-action">🔴 Tripped Circuit — {cb['agent_name']}</span>
    </div>
    <div class="heal-detail">{cb.get('failure_count',0)} failures — cooldown {remaining // 60}m remaining</div>
</div>""")

        if active_issues:
            html = """
<div style="margin-bottom:12px;font-size:13px;color:var(--sec);">
    <strong style="color:var(--red);">⚠️ Active Issues</strong> — agents with problems that need attention.
</div>""" + "\n".join(active_issues)
        else:
            html = '<div class="empty-state">✅ No self-heal events recorded yet. Run <code>observeco heal --diagnose</code> to start.</div>'

        # Add running heal button
        html += """
<div style="margin-top:16px;text-align:center;">
    <a href="/api/trigger-heal"
       style="display:inline-block;background:#22c55e;color:#000;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;"
       onclick="event.preventDefault();fetch(this.href).then(r=>r.text()).then(t=>document.getElementById('heal-log').innerHTML=t+'<div style=\\\"text-align:center;margin-top:12px;\\\">Refreshing...</div>');setTimeout(()=>{document.getElementById('heal-log').innerHTML='<div class=\\\"empty-state\\\">Refreshing heal data...</div>';},100);">
        ⚡ Run Heal Check Now
    </a>
</div>"""
        return HTMLResponse(html)

    items = []
    for e in entries[:20]:
        icon = "✅" if e["status"] == "success" else "❌" if e["status"] == "fail" else "🔍"
        items.append(f"""
<div class="heal-entry {e['status']}">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span class="heal-action">{icon} {e['agent']}</span>
        <span class="heal-time">{e['timestamp']}</span>
    </div>
    <div class="heal-detail">
        <strong>Diagnosis:</strong> {e['diagnosis']}<br>
        <strong>Action:</strong> {e['action']}
    </div>
</div>""")

    html = "\n".join(items)

    # Add trigger button
    html += """
<div style="margin-top:16px;text-align:center;">
    <a href="/api/trigger-heal"
       style="display:inline-block;background:#22c55e;color:#000;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;"
       onclick="event.preventDefault();fetch(this.href).then(function(r){return r.text()}).then(function(t){var el=document.getElementById('heal-log');if(el){el.innerHTML=t+'<div style=\\\"text-align:center;margin-top:12px;font-size:13px;color:#64748b;\\\">Heal check complete — refreshing data...</div>';}});">
        ⚡ Run Heal Check Now
    </a>
</div>"""

    return HTMLResponse(html)


@app.get("/api/trigger-heal", response_class=HTMLResponse)
async def api_trigger_heal():
    """Diagnose agents and return results as HTML."""
    d = Database()
    breakers = d.get_circuit_breakers()
    pulses = d.get_recent_pulses(limit=10)

    if not pulses and not breakers:
        return HTMLResponse('<div style="color:#64748b;font-size:13px;text-align:center;padding:20px;">No agent data to diagnose. Run <code>observeco pulse check</code> first.</div>')

    items = []
    now = int(time.time())

    # Check each breaker
    for cb in breakers:
        if cb.get("tripped"):
            cooldown = cb.get("cooldown_until", now)
            _ = max(0, cooldown - now)  # unused — will use in cooldown display
            items.append(f"""
<div class="heal-entry fail">
    <div class="heal-info" style="display:flex;justify-content:space-between;align-items:center;">
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
    <div class="heal-info" style="display:flex;justify-content:space-between;align-items:center;">
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
    <div class="heal-info" style="display:flex;justify-content:space-between;align-items:center;">
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
    <div class="heal-info" style="display:flex;justify-content:space-between;align-items:center;">
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
        items.append('<div style="color:#22c55e;font-size:13px;text-align:center;padding:20px;">✅ All agents appear healthy</div>')

    html = """
<div style="margin-bottom:8px;font-size:12px;color:#64748b;">Heal check completed at """ + __import__('datetime').datetime.now().strftime("%H:%M:%S") + """</div>
""" + "\n".join(items)

    return HTMLResponse(html)
