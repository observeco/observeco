"""Alerts panel route — severity-coded feed with discovery gap badges.

DPA Reference: Section 1 Q2, Section 2-C (discovery gap rules).
Design: All States (v2) Strong-Fit — alerts rail with severity groups + gap badges.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from observeco.db import Database
from observeco.dirs import get_data_dir

router = APIRouter(prefix="/api/alerts2", tags=["alerts"])
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


@router.get("", response_class=HTMLResponse)
async def alerts_panel():
    """DPA §3: GET /api/alerts — alerts panel HTML partial.
    Answers Q2: Why did it do that? (causation)

    Returns severity-coded feed with:
    - Cumulative discovery gap banner
    - Groups: CRITICAL, WARNING, INFO
    - Per-alert discovery gap badge per DPA §2-C
    """
    now = int(time.time())
    last_viewed = _get_alerts_last_viewed()

    try:
        circuit = db.get_circuit_breakers()
        drift = db.get_drift()
        pulses = db.get_recent_pulses(limit=100)
        errors = db.get_errors(limit=50)
    except Exception:
        # Error state — daemon down
        return HTMLResponse(f"""<div class="panel" id="alertsContainer" hx-swap-oob="true">
    <div class="panel-h"><h3>Alerts</h3><span class="pcount mono">error</span></div>
    <div class="state-msg err" style="min-height:auto;padding:var(--space-6)">
        <div class="ico">⚠</div>
        <h3>Alerts unavailable</h3>
        <p>Alert delivery paused — daemon offline. Start it to resume monitoring.</p>
        <span class="cmd" style="font-size:11px;padding:4px 10px">observeco start</span>
    </div>
</div>""")

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
                "message": f"Circuit breaker tripped ({failures} failures)",
                "timestamp": ts,
                "gap_seconds": max(0, gap),
                "is_new": ts > last_viewed,
            })

    # ── WARNING: drift breaches >10% ────────────────────────────────
    for d in drift:
        if d.get("breached") and d.get("delta_pct", 0) > 10:
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
                "message": f"Error: {_html_escape(err_msg)[:60]}",
                "timestamp": ts,
                "gap_seconds": max(0, gap),
                "is_new": ts > last_viewed,
            })

    # Sort: severity order (critical first, then warning), then by timestamp desc
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["group"], 9), -a["timestamp"]))

    # Compute cumulative discovery gap
    total_gap = sum(a.get("gap_seconds", 0) for a in alerts)
    max_gap = max((a.get("gap_seconds", 0) for a in alerts), default=0)
    max_gap_agent = ""
    for a in alerts:
        if a.get("gap_seconds", 0) == max_gap:
            max_gap_agent = a.get("agent", "")
            break
    total_gap_hrs = total_gap // 3600
    total_gap_mins = (total_gap % 3600) // 60
    total_gap_str = f"{total_gap_hrs}h {total_gap_mins:02d}m" if total_gap_hrs > 0 else f"{total_gap_mins}m"

    max_gap_str = _fmt_gap(max_gap)

    # Mark as viewed
    _set_alerts_last_viewed()

    # Build HTML
    active_count = len(alerts)

    # Alert groups
    groups = {"CRITICAL": [], "WARNING": [], "INFO": []}
    for a in alerts:
        g = a["group"]
        if g in groups:
            groups[g].append(a)

    alerts_html = ""
    for grp_name, grp_items in groups.items():
        if not grp_items:
            continue
        sw_class = "crit" if grp_name == "CRITICAL" else "warn" if grp_name == "WARNING" else "info"
        alerts_html += f"""<div class="agroup-h"><span class="sw {sw_class}"></span>{grp_name} · {len(grp_items)}</div>"""
        for a in grp_items:
            sev_cls = a["severity"]
            gap_fmt = _fmt_gap(a["gap_seconds"])
            new_tag = '<span class="new">New</span>' if a.get("is_new") else ""
            alerts_html += f"""<div class="alert {sev_cls}" onclick="htmx.ajax('GET', '/api/fleet/modal/{_html_escape(a['agent'])}', {{target:'#modalContainer', swap:'innerHTML'}})" style="cursor:pointer">
    <div class="alert-body">
        <div class="alert-top">
            <span class="alert-agent">{_html_escape(a['agent'])}</span>
            {new_tag}
        </div>
        <div class="alert-msg">{_html_escape(a['message'])}</div>
        <div class="alert-gap"><b>{gap_fmt} gap</b></div>
    </div>
</div>"""

    # If no alerts, show "all clear"
    if not alerts_html:
        alerts_html = f"""<div class="allclear">
    <div class="ico">✓</div>
    <h4>All clear</h4>
    <p>No active alerts.</p>
</div>"""

    return HTMLResponse(f"""<div class="panel" id="alertsContainer" hx-swap-oob="true">
    {f'''<div class="gap-banner">
        <span class="big mono">{total_gap_str}</span>
        <span class="lbl"><b>undiscovered downtime</b><br>across {active_count} active alert{'s' if active_count != 1 else ''} · biggest gap {max_gap_str} on {_html_escape(max_gap_agent)}</span>
    </div>''' if total_gap > 0 else ''}
    <div class="panel-h"><h3>Alerts</h3><span class="pcount mono">{active_count} active</span></div>
    {alerts_html}
</div>""")
