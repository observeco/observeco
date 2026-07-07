"""Alerts — single source of truth for fleet alerting.

Two consumers, one builder:
- GET /api/alerts2  -> right rail on Fleet tab ("Live Incidents": active CRITICAL/WARNING only, compact, no config)
- GET /api/alerts   -> Alerts tab ("Alert Center": full feed incl. INFO + heartbeat anomalies, gap banner, Pro push config)

build_alerts() collects the raw alert list once; renderers shape it per surface.
This kills the prior duplication (server.api_alerts mirrored this logic).
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from observeco.db import Database
from observeco.dirs import get_data_dir

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
db = Database()

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


def _fmt_gap(gap_seconds: int) -> str:
    """Format a gap in seconds to human-readable: '3h 45m', '12m'."""
    if gap_seconds < 60:
        return f"{gap_seconds}s"
    elif gap_seconds < 3600:
        return f"{gap_seconds // 60}m"
    h = gap_seconds // 3600
    m = (gap_seconds % 3600) // 60
    return f"{h}h {m:02d}m" if m else f"{h}h"


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_alerts(mode: str = "live", acks: dict | None = None) -> list[dict] | None:
    """Collect raw alert dicts from the DB. Single source of truth.

    mode="live"  -> CRITICAL + WARNING only (operational triage, rail)
    mode="center"-> CRITICAL + WARNING + INFO (heartbeat anomalies, tab)
    acks={(agent, category): acked_at} -> alerts with acked_at >= timestamp are suppressed
    """
    now = int(time.time())
    last_viewed = _get_alerts_last_viewed()

    try:
        circuit = db.get_circuit_breakers()
        drift = db.get_drift()
        pulses = db.get_recent_pulses(limit=100)
        errors = db.get_errors(limit=50)
    except Exception:
        return None  # caller renders the daemon-offline state

    alerts: list[dict] = []

    # ── CRITICAL: tripped circuit breakers ──────────────────────────
    for cb in circuit:
        if cb.get("tripped"):
            name = cb["agent_name"]
            failures = cb.get("failure_count", 0)
            ts = cb.get("cooldown_until") or (now - 300)
            gap = now - ts
            alerts.append({
                "severity": "critical",
                "group": "CRITICAL",
                "icon": "🔴",
                "agent": name,
                "category": "circuit",
                "message": f"Circuit breaker tripped ({failures} failures)",
                "timestamp": ts,
                "gap_seconds": max(0, gap),
                "is_new": ts > last_viewed,
            })

    # ── WARNING: drift breaches >10% ────────────────────────────────
    drift_breaches = [d for d in drift if d.get("breached") and d.get("delta_pct", 0) > 10]
    # Cap to avoid rail flooding (tab shows all via "center" mode too)
    for d in drift_breaches[:5]:
        agent = d["agent_name"]
        comp = d.get("component", "system prompt")
        pct = d.get("delta_pct", 0)
        ts = d.get("timestamp", now - 600)
        gap = now - ts
        alerts.append({
            "severity": "warning",
            "group": "WARNING",
            "icon": "🟡",
            "agent": agent,
            "category": "drift",
            "message": f"Drift {pct:+.1f}% in {comp}",
            "timestamp": ts,
            "gap_seconds": max(0, gap),
            "is_new": ts > last_viewed,
        })

    # ── CRITICAL/WARNING: pulse-based agent status ──────────────────
    seen_agents = set()
    for p in pulses:
        aname = p["agent_name"]
        if aname in seen_agents:
            continue
        seen_agents.add(aname)
        status = p.get("status", "")
        ts = p.get("timestamp", now - 300)
        gap = now - ts
        if status == "dead":
            alerts.append({
                "severity": "critical",
                "group": "CRITICAL",
                "icon": "🔴",
                "agent": aname,
                "category": "dead",
                "message": "Agent is dead — no recent heartbeat",
                "timestamp": ts,
                "gap_seconds": max(0, gap),
                "is_new": ts > last_viewed,
            })
        elif status == "error":
            err_msg = p.get("error_message", "") or "Error state detected"
            alerts.append({
                "severity": "warning",
                "group": "WARNING",
                "icon": "🟡",
                "agent": aname,
                "category": "error",
                "message": f"Error: {_html_escape(err_msg)[:60]}",
                "timestamp": ts,
                "gap_seconds": max(0, gap),
                "is_new": ts > last_viewed,
            })

    # ── INFO: heartbeat anomalies (center mode only) ────────────────
    if mode == "center":
        from collections import Counter
        pulse_counts = Counter(p["agent_name"] for p in pulses)
        for agent in sorted(pulse_counts):
            if pulse_counts[agent] < 3:
                agent_pulses = [p for p in pulses if p["agent_name"] == agent]
                if agent_pulses:
                    last_ts = agent_pulses[0].get("timestamp", 0)
                    if now - last_ts > 3600:
                        alerts.append({
                            "severity": "info",
                            "group": "INFO",
                            "icon": "🔵",
                            "agent": agent,
                            "category": "heartbeat",
                            "message": f"Heartbeat anomaly — only {pulse_counts[agent]} pulses recorded",
                            "timestamp": last_ts,
                            "gap_seconds": now - last_ts,
                            "is_new": last_ts > last_viewed,
                        })

    # Suppress acknowledged incidents (ack timestamp >= alert timestamp)
    if acks:
        alerts = [
            a for a in alerts
            if acks.get((a["agent"], a["category"]), 0) < a["timestamp"]
        ]

    # Sort: severity order (critical first, then warning, then info), ts desc
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["group"], 9), -a["timestamp"]))
    return alerts


def _render_daemon_offline() -> str:
    return """<div class="panel" id="alertsContainer" hx-swap-oob="true">
    <div class="panel-h"><h3>Alerts</h3><span class="pcount mono">error</span></div>
    <div class="state-msg err" style="min-height:auto;padding:var(--space-6)">
        <div class="ico">⚠</div>
        <h3>Alerts unavailable</h3>
        <p>Alert delivery paused — daemon offline. Start it to resume monitoring.</p>
        <span class="cmd" style="font-size:11px;padding:4px 10px">observeco start</span>
    </div>
</div>"""


def _render_live(alerts: list[dict]) -> str:
    """Right rail — 'Live Incidents'. Active CRITICAL/WARNING only, compact."""
    active_count = len(alerts)
    if not alerts:
        return """<div class="panel" id="alertsContainer" hx-swap-oob="true">
    <div class="panel-h"><h3>Live Incidents</h3><span class="pcount mono">0 active</span></div>
    <div class="allclear">
        <div class="ico">✓</div>
        <h4>All clear</h4>
        <p>No active incidents.</p>
    </div>
</div>"""

    # Cumulative undiscovered downtime (max gap across active incidents)
    max_gap = max((a.get("gap_seconds", 0) for a in alerts), default=0)
    max_gap_agent = next((a["agent"] for a in alerts if a.get("gap_seconds", 0) == max_gap), "")
    max_gap_str = _fmt_gap(max_gap)

    groups = {"CRITICAL": [], "WARNING": []}
    for a in alerts:
        if a["group"] in groups:
            groups[a["group"]].append(a)

    alerts_html = ""
    for grp_name, grp_items in groups.items():
        if not grp_items:
            continue
        sw_class = "crit" if grp_name == "CRITICAL" else "warn"
        alerts_html += f"""<div class="agroup-h"><span class="sw {sw_class}"></span>{grp_name} · {len(grp_items)}</div>"""
        for a in grp_items:
            sev_cls = a["severity"]
            gap_fmt = _fmt_gap(a["gap_seconds"])
            new_tag = '<span class="new">New</span>' if a.get("is_new") else ""
            agent = _html_escape(a["agent"])
            cat = a["category"]
            alerts_html += f"""<div class="alert {sev_cls}" onclick="htmx.ajax('GET', '/api/fleet/modal/{agent}', {{target:'#modalContainer', swap:'innerHTML'}})" style="cursor:pointer">
    <div class="alert-body">
        <div class="alert-top">
            <span class="alert-agent">{agent}</span>
            {new_tag}
        </div>
        <div class="alert-msg">{_html_escape(a['message'])}</div>
        <div class="alert-gap"><b>{gap_fmt} gap</b></div>
        <span class="dismiss-btn" hx-post="/api/alerts/ack/{agent}/{cat}" hx-target="closest .alert" hx-swap="outerHTML" hx-on-click="event.stopPropagation()" style="cursor:pointer;color:#64748b;font-size:11px;padding:2px 6px;border-radius:4px;float:right;" title="Acknowledge &amp; dismiss">✕</span>
    </div>
</div>"""

    _set_alerts_last_viewed()
    return f"""<div class="panel" id="alertsContainer" hx-swap-oob="true">
    {f'''<div class="gap-banner">
        <span class="big mono">{max_gap_str}</span>
        <span class="lbl"><b>worst active gap</b><br>{active_count} incident{'s' if active_count != 1 else ''} · {_html_escape(max_gap_agent)}</span>
    </div>''' if max_gap > 0 else ''}
    <div class="panel-h"><h3>Live Incidents</h3><span class="pcount mono">{active_count} active</span></div>
    {alerts_html}
</div>"""


def _render_center(alerts: list[dict] | None) -> str:
    """Alerts tab — 'Alert Center'. Full feed + history + Pro push config."""
    if not alerts:
        empty_status = "" if _ALERTS_VIEW_PATH.exists() else "first-load"
        _set_alerts_last_viewed()
        return (f'<div class="empty-state" style="color:#6b7280;font-size:13px;text-align:center;padding:24px 20px;">'
                f'✅ All clear — no alerts</div>'
                f'<div data-alerts-viewed="{empty_status}" style="display:none;"></div>')

    now = int(time.time())
    last_viewed = _get_alerts_last_viewed()
    total_gap_minutes = sum(a["gap_seconds"] for a in alerts) // 60
    new_count = sum(1 for a in alerts if a.get("is_new"))
    discovery_alert_count = len(alerts)

    gap_banner = f"""<div class="gap-banner" style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;gap:12px;">
    <div style="font-size:20px;font-weight:700;color:#f97316;">{total_gap_minutes}m</div>
    <div style="font-size:11px;color:var(--fg-2);line-height:1.5;">
        Total <strong style="color:#e2e8f0;">undiscovered downtime</strong> across {discovery_alert_count} alert(s) in the last 24h
        {f' — <span style="color:#ef4444;font-weight:600;">{new_count} new since your last view</span>' if new_count else ''}
    </div>
</div>"""

    severity_color = {"critical": "#ef4444", "warning": "#eab308", "info": "#3b82f6"}
    severity_bg = {"critical": "#450a0a", "warning": "#422006", "info": "#172554"}

    items = [gap_banner]
    for a in alerts:
        ts_str = _fmt_ts(a["timestamp"]) if (ts := a["timestamp"]) else ""
        gap_s = a.get("gap_seconds", 0)
        is_new = a.get("is_new", False)
        gap_label = ""
        if gap_s > 300:
            gap_m = gap_s // 60
            gap_h = gap_m // 60
            if gap_h > 0:
                gap_label = f"🕐 Happened {ts_str} · <strong style='color:#fca5a5;'>{gap_h}h {gap_m % 60}m gap</strong>"
            else:
                gap_label = f"🕐 Happened {ts_str} · <strong style='color:#fca5a5;'>{gap_m}m gap</strong>"
        new_badge = '<span style="background:#7f1d1d;color:#fca5a5;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:4px;">NEW</span>' if is_new else ""
        sev = a["severity"]
        agent = _html_escape(a["agent"])
        cat = a["category"]
        items.append(f"""<div class="alert-row severity-{sev}" style="border-left:3px solid {severity_color.get(sev, '#64748b')};background:{severity_bg.get(sev, '#1e293b')};">
    <div class="heal-entry-header">
        <span><strong style="color:{severity_color.get(sev, '#64748b')}">{a['group']}{new_badge}</strong></span>
        <span class="heal-time">{ts_str}</span>
    </div>
    <div class="text-secondary" class="u-mt-2">
        <span style="color:#38bdf8;font-weight:600;">{agent}</span>
        <span> — {_html_escape(a['message'])}</span>
    </div>
    {f'<div class="discovery-gap" style="font-size:10px;color:#94a3b8;margin-top:2px;">{gap_label}</div>' if gap_label else ''}
    <div class="alerts-action-bar" style="margin-top:4px;display:flex;justify-content:space-between;align-items:center;">
        <span class="heal-time" style="font-size:10px;color:#64748b;">
            🔇 Dashboard only · <span onclick="showProPreview('alert-relay')" style="cursor:pointer;color:#a5b4fc;text-decoration:underline;">Enable push alerts (Pro)</span>
        </span>
        <span class="dismiss-btn" hx-post="/api/alerts/ack/{agent}/{cat}" hx-target="closest .alert-row" hx-swap="outerHTML" style="cursor:pointer;color:#64748b;font-size:11px;padding:2px 6px;border-radius:4px;" title="Acknowledge &amp; dismiss">✕ dismiss</span>
    </div>
</div>""")

    # Pro locked tiles (history/config upsell)
    items.append(_pro_locked_tiles())

    _set_alerts_last_viewed()
    return "\n".join(items)


def _fmt_ts(ts: int) -> str:
    """Relative-ish timestamp. Reuse server's helper if available, else fallback."""
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%b %d %H:%M")


def _pro_locked_tiles() -> str:
    """Generate Pro locked tile grid per §7.1 — returns empty string if Pro active."""
    from observeco import license as lic
    if lic.require_pro():
        return ""
    from observeco.dashboard.server import PRO_FEATURES
    tiles = []
    for feat in PRO_FEATURES:
        errors = db.get_errors(limit=50)
        circuit = db.get_circuit_breakers()
        drift = db.get_drift()
        agents = db.get_agents()
        alert_count = len(errors)
        drift_breaches = len([d for d in drift if d.get("breached")])
        circuit_trips = sum(1 for c in circuit if c.get("tripped"))
        alert_list = "; ".join(
            [f"{e.get('error_type', 'error')} at {_fmt_ts(e['timestamp'])}" for e in errors[:3]]
        ) or "no recent alerts"
        days_available = max(0, 90 - 7)
        preview = feat["preview_template"].format(
            alert_count=alert_count,
            alert_list=alert_list,
            drift_count=drift_breaches,
            circuit_count=circuit_trips,
            agent_count=len(agents),
            days_available=days_available,
        )
        tiles.append(f"""<div class="pro-tile" onclick="showProPreview('{feat['id']}')">
    <div class="pro-tile-lock">🔒</div>
    <div class="pro-tile-title">{_html_escape(feat['name'])}</div>
    <div class="pro-tile-preview">{_html_escape(preview)}</div>
</div>""")
    return f'<div class="pro-tile-grid">{"".join(tiles)}</div>'


# ── Routes ──────────────────────────────────────────────────────────

@router.get("/live", response_class=HTMLResponse)
async def alerts_rail():
    """Right rail on Fleet tab — 'Live Incidents'."""
    acks = db.get_alert_acks()
    alerts = build_alerts(mode="live", acks=acks)
    if alerts is None:  # daemon offline
        return HTMLResponse(_render_daemon_offline())
    return HTMLResponse(_render_live(alerts))


@router.get("", response_class=HTMLResponse)
async def alerts_center():
    """Alerts tab — 'Alert Center' (full feed + history + Pro config)."""
    acks = db.get_alert_acks()
    alerts = build_alerts(mode="center", acks=acks)
    if alerts is None:  # daemon offline -> center view shows error state too
        return HTMLResponse(_render_daemon_offline())
    return HTMLResponse(_render_center(alerts))


@router.post("/ack/{agent}/{category}", response_class=HTMLResponse)
async def ack_alert_endpoint(agent: str, category: str):
    """Acknowledge/dismiss an alert incident. Returns 200 on success."""
    db.ack_alert(agent, category)
    return HTMLResponse("", status_code=200)

