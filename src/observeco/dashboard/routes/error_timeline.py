"""Error timeline route — reverse-chronological feed with Gantt-style duration bars.

DPA Reference: Section 1 Q1.
Design: All States (v2) Strong-Fit — timeline rows with severity colors + Gantt bars.
"""

from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from observeco.db import Database

router = APIRouter(prefix="/api/timeline", tags=["timeline"])
db = Database()


def _fmt_short_ts(ts: int) -> str:
    """Format timestamp to HH:MM."""
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M")


def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


def _severity_for(error_type: str) -> str:
    """Map error type to severity for timeline classification."""
    critical_types = {"timeout", "connection_refused", "process_not_found", "crash"}
    warning_types = {"drift_breach", "http_5xx", "build_failed", "resource_not_found"}
    if error_type in critical_types:
        return "critical"
    if error_type in warning_types:
        return "warning"
    return "info"


def _header_html(count_label: str = "") -> str:
    """Column header row — sits directly above .tl-rows so columns align.

    count_label: optional right-aligned caption (e.g. 'last 24h · 57 events').
    """
    caption = f'<span class="tl-header-count">{count_label}</span>' if count_label else ""
    return f"""<div class="tl-header-row">
  <span class="tl-header-cell">Time</span>
  <span class="tl-header-cell">Agent</span>
  <span class="tl-header-cell">Message</span>
  <span class="tl-header-cell tl-header-track">Timeline</span>
  <span class="tl-header-cell tl-header-dur">Duration</span>
  {caption}
</div>"""


def _loading_html() -> str:
    """Return skeleton loading state for the error timeline."""
    return f"""{_header_html()}
<div class="tl-rows">
  <div class="skel-line" style="padding:12px 16px"><div class="skel" style="width:48px;height:12px"></div><div class="skel" style="width:80px;height:12px"></div><div class="skel" style="flex:1;height:12px"></div></div>
  <div class="skel-line" style="padding:12px 16px"><div class="skel" style="width:48px;height:12px"></div><div class="skel" style="width:80px;height:12px"></div><div class="skel" style="flex:1;height:12px"></div></div>
  <div class="tl-loading">Loading events…</div>
</div>"""


def _empty_html(days: int) -> str:
    """Return empty state for the error timeline."""
    return f"""{_header_html()}
<div class="tl-rows"><div class="tl-empty">No errors in the selected range.</div></div>"""


def _error_html() -> str:
    """Return error state for the error timeline."""
    return f"""{_header_html()}
<div class="tl-rows"><div class="tl-empty" style="color:var(--status-critical)">Failed to load error timeline. The daemon may be offline.</div></div>"""


@router.get("/errors", response_class=HTMLResponse)
async def error_timeline(days: int = 1, agent: str = "", severity: str = ""):
    """DPA §3: GET /api/timeline/errors — error timeline HTML partial.

    Returns reverse-chronological error feed with Gantt-style duration bars.
    Answers Q1: What did the agent actually do? (behavior)
    """
    try:
        now = int(time.time())
        since = now - (days * 86400)

        errors = db.get_errors(limit=200)

        # Filter by time window
        errors = [e for e in errors if e.get("timestamp", 0) >= since]

        # Filter by agent
        if agent:
            errors = [e for e in errors if e["agent_name"] == agent]

        # Classify each error
        rows = []
        for e in errors:
            sev = _severity_for(e.get("error_type", "other"))
            if severity and sev != severity:
                continue

            ts = e.get("timestamp", now)
            agent_name = e.get("agent_name", "?")
            msg = e.get("error_message", "") or e.get("error_type", "unknown error")

            # Compute Gantt-like duration: errors cluster within ~10m window
            # For simplicity, assign a pseudo-duration based on severity
            dur_min = 15 if sev == "critical" else 8 if sev == "warning" else 3
            dur_min * 60 * 1000

            rows.append({
                "time": _fmt_short_ts(ts),
                "agent": agent_name,
                "message": msg[:80],
                "type": e.get("error_type", ""),
                "severity": sev,
                "timestamp": ts,
                "dur_min": dur_min,
            })

        # Sort reverse chronological
        rows.sort(key=lambda r: -r["timestamp"])

        if not rows:
            return HTMLResponse(content=_empty_html(days))

        # Pseudo-axis: compute time range from data
        min_ts = min(r["timestamp"] for r in rows)
        max_ts = max(r["timestamp"] for r in rows)
        range_s = max(max_ts - min_ts, 1)

        rows_html = ""
        for r in rows:
            # Gantt bar: position determined by how far from start of range
            offset_pct = ((r["timestamp"] - min_ts) / range_s) * 100
            width_pct = (r["dur_min"] * 60 / max(range_s, 60)) * 100
            width_pct = max(width_pct, 2)  # minimum visible bar

            dur_label = f"{r['dur_min']}m"

            sev_cls = r["severity"]

            rows_html += f"""<div class="tl-row {sev_cls}" onclick="htmx.ajax('GET', '/api/fleet/modal/{_html_escape(r['agent'])}', {{target:'#modalContainer', swap:'innerHTML'}})" style="cursor:pointer">
    <span class="tl-time">{r['time']}</span>
    <span class="tl-agent">{_html_escape(r['agent'])}</span>
    <span class="tl-msg">{_html_escape(r['message'])} <span class="type">· {_html_escape(r['type'].replace('_', ' '))}</span></span>
    <span class="tl-track"><i class="{sev_cls}" style="left:{offset_pct:.0f}%;width:{width_pct:.0f}%"></i></span>
    <span class="tl-dur {sev_cls}">{dur_label}</span>
</div>"""

        event_count = len(rows)
        return HTMLResponse(f"""{_header_html(f"last {days}d · {event_count} events")}
<div class="tl-rows">
    {rows_html}
</div>""")

    except Exception:
        return HTMLResponse(content=_error_html(), status_code=200)
