"""Waterfall trace view — per-agent span timeline with tree rendering.

Renders as an HTML fragment suitable for htmx injection into the dashboard.
"""

from __future__ import annotations

import json
from typing import Optional

from observeco.db import Database


def render_waterfall(agent_name: str, db: Optional[Database] = None) -> str:
    """Render a waterfall view of trace spans for an agent.

    Returns an HTML fragment string.
    """
    if db is None:
        db = Database()

    sessions = db.get_trace_sessions(agent_name=agent_name, limit=5)
    if not sessions:
        return _empty_state()

    html = ['<div class="waterfall">']

    for session in sessions:
        trace_id = session["trace_id"]
        spans = db.get_trace_spans(trace_id=trace_id, limit=200)
        if not spans:
            continue

        # Compute timing
        root_start = min(s["start_time_ns"] for s in spans)
        root_end = max(s["end_time_ns"] for s in spans)
        total_ns = max(root_end - root_start, 1)

        # Time window for display
        session_ts = session.get("first_span", 0)
        from datetime import datetime
        try:
            ts_display = datetime.fromtimestamp(session_ts / 1_000_000_000).strftime("%H:%M:%S")
        except (ValueError, OSError):
            ts_display = "unknown"

        html.append(f'<div class="waterfall-session">')
        html.append(f'<div class="waterfall-session-header">'
                    f'🔍 Trace {trace_id[:12]}… · {len(spans)} spans · {ts_display}'
                    f'</div>')
        html.append(f'<div class="waterfall-spans">')

        for span in spans:
            span_start = span.get("start_time_ns", 0)
            span_end = span.get("end_time_ns", 0)
            duration_ns = max(span_end - span_start, 1)

            left_pct = ((span_start - root_start) / total_ns) * 100
            width_pct = max(duration_ns / total_ns * 100, 0.5)

            depth = _span_depth(span, spans)
            indent = depth * 20

            status_class = {
                "OK": "waterfall-ok",
                "ERROR": "waterfall-error",
                "UNSET": "waterfall-unset",
            }.get(span.get("status", "UNSET"), "waterfall-unset")

            duration_ms = duration_ns / 1_000_000

            html.append(
                f'<div class="waterfall-span {status_class}" '
                f'style="margin-left:{indent}px">'
                f'<div class="waterfall-span-name">{span["span_name"]}</div>'
                f'<div class="waterfall-bar-track">'
                f'<div class="waterfall-bar" style="left:{left_pct:.1f}%;width:{width_pct:.1f}%"></div>'
                f'</div>'
                f'<div class="waterfall-span-time">{duration_ms:.1f}ms</div>'
                f'</div>'
            )

        html.append('</div></div>')

    html.append('</div>')
    return "\n".join(html)


def _span_depth(span: dict, all_spans: list[dict]) -> int:
    """Compute the tree depth of a span by walking parent chain."""
    depth = 0
    current = span
    visited = set()
    while current.get("parent_span_id"):
        parent_id = current["parent_span_id"]
        if parent_id in visited:
            break
        visited.add(parent_id)
        parent = next((s for s in all_spans if s["span_id"] == parent_id), None)
        if parent is None:
            break
        depth += 1
        current = parent
    return depth


def _empty_state() -> str:
    return """<div class="waterfall-empty">
    <div class="waterfall-empty-icon">🔍</div>
    <div class="waterfall-empty-title">No trace data yet</div>
    <div class="waterfall-empty-msg">
        Enable the Hermes OTEL plugin to start tracing.
        Run <code>hermes plugins enable observability/otel</code>
        and restart the gateway.
    </div>
</div>"""
