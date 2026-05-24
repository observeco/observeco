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
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from observeco.billing import add_billing_endpoints
from observeco.dashboard.otel import router as otel_router
from observeco.db import Database

app = FastAPI(title="ObserveCo Dashboard")
db = Database()

# Register billing + OTel endpoints
add_billing_endpoints(app)
app.include_router(otel_router)

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
        "preview_template": "90-day history — {(90-7)} more days available with Pro",
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

        preview = feat["preview_template"].format(
            alert_count=alert_count,
            alert_list=alert_list,
            drift_count=drift_breaches,
            circuit_count=circuit_trips,
            agent_count=len(agents),
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

    preview = feat["preview_template"].format(
        alert_count=alert_count,
        alert_list=alert_list,
        drift_count=drift_breaches,
        circuit_count=circuit_trips,
        agent_count=len(agents),
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
        errors_html = '<div style="color:#6b7280;font-size:13px;padding:8px;">No errors recorded</div>'

    framework_label = "Hermes" if framework == "hermes" else "OpenClaw"

    return HTMLResponse(f"""<div class="detail-content health-tab" style="padding:12px;">
    <div style="margin-bottom:12px;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">Agent Framework</div>
        <div style="color:#38bdf8;font-weight:600;font-size:14px;">{framework_label}</div>
    </div>
    <div style="margin-bottom:12px;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Pulse History (last 24h)</div>
        <div style="font-size:16px;letter-spacing:2px;">{"".join(dot_row) or "—"}</div>
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
        return HTMLResponse('<div style="padding:12px;color:#6b7280;">Memory garden is available for OpenClaw agents. Run `observeco clawforge garden`.</div>')

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
    """Error timeline — §6.5."""
    errors = db.get_errors(limit=50)
    if not errors:
        return HTMLResponse('<div class="empty-state">✅ No errors in the last 24h</div>')
    now = int(time.time())
    items = []
    for e in errors[:30]:
        ts = _fmt_ts(e.get("timestamp", now))
        agent = e.get("agent_name", e.get("agent", "?"))
        msg = e.get("error_type", e.get("message", "?"))
        sev = e.get("severity", "warning")
        items.append(f"""<div class="error-item severity-{sev}">
    <span class="error-ts">{ts}</span>
    <span class="error-agent">{_html_escape(agent)}</span>
    <span class="error-msg">{_html_escape(msg)}</span>
</div>""")
    return HTMLResponse("\n".join(items))


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

    cards = []
    for name in sorted(all_agent_names):
        s = summary.get(name, {})
        status = s.get("status", "unknown")
        s.get("latency_ms", 0)
        ts = s.get("timestamp", 0)
        cb = breakers.get(name, {})
        tripped = cb.get("tripped", 0)

        dot_color = {"alive": "#22c55e", "dead": "#ef4444", "error": "#f59e0b"}.get(status, "#6b7280")
        status_text = {"alive": "Alive", "dead": "Dead", "error": "Error"}.get(status, "Unknown")

        # Framework label
        agent_cfg = {a["agent_name"]: a for a in agents}
        fw = agent_cfg.get(name, {}).get("framework", "hermes") if agent_cfg else "hermes"
        fw_label = "Hermes" if fw == "hermes" else "OpenClaw"
        fw_color = "#38bdf8" if fw == "hermes" else "#a78bfa"

        # Token bar
        trim_data = trimmed_agents.get(name)
        token_bar_html = ""
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

        cards.append(f"""<div class="agent-card" id="card-{name}"
     onclick="toggleAgentDetail('{name}')"
     style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;cursor:pointer;position:relative;">
    <div class="card-header" style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span class="status-dot" style="width:10px;height:10px;border-radius:50%;background:{dot_color};flex-shrink:0;" title="{status_text}"></span>
        <span class="agent-name" style="font-weight:600;font-size:14px;color:#e2e8f0;">{_html_escape(name)}</span>
        <span style="font-size:11px;color:{fw_color};background:#1e293b;padding:2px 6px;border-radius:4px;margin-left:auto;">{fw_label}</span>
    </div>
    <div style="display:flex;gap:12px;font-size:12px;color:#64748b;">
        <span>{last_checkin}</span>
        <span>{circuit_badge}</span>
    </div>
    {token_bar_html}
    {drift_sparkline}
    <div style="display:none;" class="agent-detail" id="detail-{name}">
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

    return HTMLResponse("".join(cards))


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
# §§§ — Main Page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard</h1><p>Template not found.</p>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# §8 — Phase Detection (progressive loading)
# ---------------------------------------------------------------------------

@app.get("/api/phase", response_class=HTMLResponse)
async def api_phase():
    """Detect which phase the user is in — §8 progressive loading."""
    db_path = db.db_path
    if not db_path.exists() or db_path.stat().st_size == 0:
        return HTMLResponse("phase-0")  # Pre-install

    pulses = db.get_recent_pulses(limit=10)
    if not pulses:
        return HTMLResponse("phase-1")  # Discovering

    # Check if we have enough data for stable status
    now = int(time.time())
    recent = [p for p in pulses if now - p.get("timestamp", 0) < 600]  # 10min window for seeded/batch data
    trims = db.get_trims(limit=5)

    if not recent:
        return HTMLResponse("phase-1")  # Still learning baseline
    if not trims:
        return HTMLResponse("phase-2")  # Has health data, no token data yet

    return HTMLResponse("phase-3")  # Full data


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
