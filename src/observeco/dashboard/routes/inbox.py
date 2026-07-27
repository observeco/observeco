"""Inbox routes — §3.5 endpoints for the Anomalies Inbox.

Obs-Spec: obs-spec-092 §3.5, §4 Phase 2–3
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from observeco.db import Database
from observeco.inbox.correlate import split
from observeco.inbox.store import InboxStore

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
router = APIRouter(prefix="/api/inbox", tags=["inbox"])
db = Database()
store = InboxStore(db)


# ── Helpers ─────────────────────────────────────────────────────────

def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


def _fmt_when(iso_ts: str | None) -> str:
    """Format ISO timestamp to relative: 'now', '5m ago', 'Jul 19'."""
    if not iso_ts:
        return ""
    try:
        ts = int(time.mktime(time.strptime(iso_ts[:19], "%Y-%m-%dT%H:%M:%S")))
    except (ValueError, OSError):
        return iso_ts[:10] if iso_ts else ""
    now = int(time.time())
    delta = now - ts
    if delta < 60:
        return "now"
    elif delta < 3600:
        return f"{delta // 60}m ago"
    elif delta < 86400:
        return f"{delta // 3600}h ago"
    return iso_ts[:10] if iso_ts else ""


def _get_counts() -> dict:
    """Get inbox count summary for verdict sentence."""
    return store.get_counts()


def _build_verdict_sentence(counts: dict) -> str:
    """Build verdict sentence per DPA §2-B and obs-spec-092 §3.6."""
    action = counts.get("alert", 0)
    watch = counts.get("watch", 0)
    triaged = counts.get("triaged", 0)
    insight = counts.get("insight", 0)

    if action == 0:
        parts = []
        if watch:
            parts.append(f"{watch} worth watching")
        if insight:
            parts.append(f"{insight} insights")
        if triaged:
            parts.append(f"{triaged} auto-triaged as noise")
        detail = ", ".join(parts)
        return f"Fleet quiet — {detail}." if detail else "Fleet quiet — no anomalies detected."
    else:
        return (f"{action} issue{'s' if action != 1 else ''} need action — "
                f"{watch} worth watching, {triaged} auto-triaged as noise.")


def _render_item(item: dict) -> str:
    """Render a single inbox item as HTML (swc-style card with evidence drawer)."""
    item_id = item["id"]
    cls = item["class"]
    tone = item["tone"]
    title = item.get("title", "")
    attribution = item.get("attribution", "")
    evidence_raw = item.get("evidence", "{}")
    actions_raw = item.get("actions", "[]")
    why_source = item.get("why_source", "")
    state = item.get("state", "open")
    when = _fmt_when(item.get("last_seen", ""))
    pillar = item.get("pillar") or ""
    folded_count = item.get("folded_count")

    try:
        evidence = json.loads(evidence_raw) if isinstance(evidence_raw, str) else evidence_raw
    except (json.JSONDecodeError, TypeError):
        evidence = {}
    try:
        actions = json.loads(actions_raw) if isinstance(actions_raw, str) else actions_raw
    except (json.JSONDecodeError, TypeError):
        actions = []

    metrics = evidence.get("metrics", {})
    # Tone class
    tone_cls = {"alert": "crit", "watch": "watch", "insight": "insight"}.get(tone, "insight")
    mark_icon = {"alert": "!", "watch": "↗", "insight": "i"}.get(tone, "i")

    # Pillar label
    pillar_label = {"quality": "quality check", "reliability": "reliability",
                    "usage": "usage", "memory": "memory"}.get(pillar, "")
    lead_text = cls.replace("_", " ").title()
    if pillar_label:
        lead = f"{lead_text} · {pillar_label}" if tone != "insight" else f"{pillar_label} · {lead_text}"
    else:
        lead = lead_text

    acked_cls = " acked" if state == "acked" else ""

    # Actions HTML
    actions_html = ""
    for act in actions:
        act_kind = act.get("kind", "neutral")
        act_label = _html_escape(act.get("label", ""))
        act_href = act.get("href", "#")
        act_link = f'<a class="act {act_kind}" href="{act_href}">{act_label}</a>'
        actions_html += act_link + "\n            "

    # Evidence grid — render some metric keys, format epoch values
    now_ts = int(time.time())
    ev_rows = ""
    for k, v in list(metrics.items())[:4]:
        ev_val_class = ""
        if isinstance(v, (int, float)):
            # Format epoch timestamps (recent large ints) as relative time
            if 1700000000 < v < now_ts + 86400 and v > 100000:
                from observeco.dashboard.services.agent_profile_service import _fmt_relative
                v = _fmt_relative(int(v))
            elif v > 100:
                ev_val_class = "bad"
            elif v > 20:
                ev_val_class = "warn"
            if isinstance(v, float):
                v = f"{v:.1f}"
        ev_rows += f"""<div class="ev"><div class="ev-l">{k.replace('_', ' ')}</div><div class="ev-v {ev_val_class}">{v}</div></div>\n"""

    # Folded count badge
    folded_html = f' <span class="vchip" style="margin-left:4px"><b>{folded_count}</b> folded</span>' if folded_count else ""

    return f"""<div class="item {tone_cls}{acked_cls}" data-sev="{tone_cls}" data-id="{_html_escape(item_id)}">
    <div class="item-row" onclick="this.parentNode.classList.toggle('expanded')">
      <span class="mark">{mark_icon}</span>
      <div class="body">
        <span class="lead">{_html_escape(lead)}</span>
        <div class="txt">{_html_escape(title)}{folded_html}</div>
        {f'<div class="attr">{_html_escape(attribution)}</div>' if attribution else ''}
        <div class="acts">
          {actions_html}
          <a class="act neutral" href="#" onclick="event.preventDefault();event.stopPropagation();htmx.ajax('POST', '/api/inbox/{_html_escape(item_id)}/ack', {{target: '#inboxContainer', swap: 'innerHTML'}}).then(() => htmx.trigger('#inboxContainer', 'inboxRefresh'))">Ack</a>
        </div>
      </div>
      <span class="when">{when}</span>
    </div>
    <div class="evidence">
      <div class="ev-grid">{ev_rows}</div>
      <div class="why"><b>Why am I seeing this?</b> {_html_escape(why_source)}</div>
    </div>
  </div>"""


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def get_inbox(request: Request, filter: str = "all"):
    """GET /api/inbox — HTML partial. Main inbox view."""
    counts = _get_counts()
    verdict = _build_verdict_sentence(counts)
    total = sum(v for k, v in counts.items() if k != "none")

    # Build items by tone group
    tone_groups = {}

    # Filters
    state_filter = None
    tone_filter = None
    if filter == "acked":
        state_filter = "acked"
    elif filter == "crit":
        tone_filter = "alert"
    elif filter == "watch":
        tone_filter = "watch"
    elif filter == "insight":
        tone_filter = "insight"
    else:
        tone_filter = None

    if state_filter:
        items = store.list_items(state=state_filter, limit=100)
        tone_groups["acked"] = items
    elif tone_filter:
        items = store.list_items(tone=tone_filter, limit=100)
        tone_groups[tone_filter] = items
    else:
        for tone_name in ["alert", "watch", "insight"]:
            items = store.list_items(tone=tone_name, limit=200)
            if items:
                tone_groups[tone_name] = items
        # Also: triaged items go into the drawer

    # Get triaged items for the drawer
    triaged_items = store.list_items(state="triaged", limit=200)

    # Build HTML
    feed_html_parts = []

    # Verdict bar
    feed_html_parts.append(f"""<div class="verdict" role="status">
    <span class="v-icon" style="background:var(--status-{'critical' if counts['alert'] > 0 else 'warning' if counts['watch'] > 0 else 'healthy'});box-shadow:0 0 8px rgba({239 if counts['alert'] > 0 else 234 if counts['watch'] > 0 else 34},68,68,.5)"></span>
    <span class="v-text">{verdict}</span>
    <div class="v-chips">
      <span class="vchip crit"><b>{counts.get('alert', 0)}</b> action</span>
      <span class="vchip warn"><b>{counts.get('watch', 0)}</b> watch</span>
      <span class="vchip"><b>{counts.get('insight', 0)}</b> insight</span>
      <span class="vchip good"><b>{counts.get('triaged', 0)}</b> filtered</span>
    </div>
  </div>""")

    # Filters
    feed_html_parts.append(f"""<div class="filters" role="group" aria-label="Filter inbox">
    <button class="fchip{' active' if filter == 'all' else ''}" data-f="all" hx-get="/api/inbox?filter=all" hx-target="#inboxFeed" hx-swap="innerHTML" hx-trigger="click">All<span class="n">{total}</span></button>
    <button class="fchip{' active' if filter == 'crit' else ''}" data-f="crit" hx-get="/api/inbox?filter=crit" hx-target="#inboxFeed" hx-swap="innerHTML" hx-trigger="click">Needs action<span class="n">{counts.get('alert', 0)}</span></button>
    <button class="fchip{' active' if filter == 'watch' else ''}" data-f="watch" hx-get="/api/inbox?filter=watch" hx-target="#inboxFeed" hx-swap="innerHTML" hx-trigger="click">Watch<span class="n">{counts.get('watch', 0)}</span></button>
    <button class="fchip{' active' if filter == 'insight' else ''}" data-f="insight" hx-get="/api/inbox?filter=insight" hx-target="#inboxFeed" hx-swap="innerHTML" hx-trigger="click">Insight<span class="n">{counts.get('insight', 0)}</span></button>
    <button class="fchip{' active' if filter == 'acked' else ''}" data-f="acked" hx-get="/api/inbox?filter=acked" hx-target="#inboxFeed" hx-swap="innerHTML" hx-trigger="click">Acked<span class="n" id="ackCount">{len(store.list_items(state='acked'))}</span></button>
    <span class="kb-hint"><kbd>j</kbd>/<kbd>k</kbd> move · <kbd>x</kbd> ack · <kbd>e</kbd> expand</span>
  </div>""")

    # Feed sections
    for tone_key, label in [("alert", "Needs action"), ("watch", "Watch"), ("insight", "Insight")]:
        if tone_key in tone_groups:
            feed_html_parts.append(
                f'<div class="feed-h">{label} <span class="cnt">{len(tone_groups[tone_key])}</span></div>'
            )
            for item in tone_groups[tone_key]:
                feed_html_parts.append(_render_item(item))

    # Triaged drawer
    if triaged_items:
        feed_html_parts.append(f"""<div class="drawer open" id="noiseDrawer">
    <div class="drawer-h" onclick="document.getElementById('noiseDrawer').classList.toggle('open')">
      <span class="n">{len(triaged_items)}</span> auto-triaged as noise — transparent, reversible, never silent
      <span class="chev">▶</span>
    </div>
    <div class="drawer-body">""")
        for item in triaged_items:
            agent = item.get("agent_name", "") or "fleet"
            reason = item.get("triage_reason", "auto-filtered")
            feed_html_parts.append(f"""<div class="noise"><span class="nm">{_html_escape(agent)}</span><span class="rs">{_html_escape(reason)} <i>Covered by inbox classification.</i></span><a class="undo" href="#" onclick="event.preventDefault();htmx.ajax('POST', '/api/inbox/{_html_escape(item['id'])}/restore', {{target: '#inboxContainer', swap: 'innerHTML'}}).then(() => htmx.trigger('#inboxContainer', 'inboxRefresh'))">restore</a></div>""")
        feed_html_parts.append("""</div></div>""")

    # Footer
    feed_html_parts.append("""<div class="footer">
    <b>Inbox</b> reads across 9 source tables · items deduplicated and classified before surfacing.<br>
    <b>Source tables:</b> l2_trending, chisel_drift, canary_runs, circuit_breakers, anomaly/, token_logs, clawforge_garden
  </div>""")

    html = "\n".join(feed_html_parts)
    return templates.TemplateResponse(request, "partials/inbox.html", {"html": html})


@router.get("/json")
async def get_inbox_json():
    """GET /api/inbox/json — raw items for API consumers / debugging. (Pro feature)"""
    items = store.list_items(limit=200)
    counts = _get_counts()
    return JSONResponse({
        "count": len(items),
        "verdict": _build_verdict_sentence(counts),
        "items": items,
    })


@router.post("/{item_id}/ack")
async def ack_item(request: Request, item_id: str):
    """POST /api/inbox/{id}/ack — acknowledge an item."""
    ok = store.ack(item_id)
    if not ok:
        return HTMLResponse("<!-- not found or already acked -->")
    # Re-render the full inbox
    return await get_inbox(request)


@router.post("/{item_id}/snooze")
async def snooze_item(request: Request, item_id: str):
    """POST /api/inbox/{id}/snooze — snooze until tomorrow."""
    tomorrow = time.strftime("%Y-%m-%dT%H:%M:%S",
                             time.gmtime(int(time.time()) + 86400))
    store.snooze(item_id, tomorrow)
    return await get_inbox(request)


@router.post("/{item_id}/restore")
async def restore_item(request: Request, item_id: str):
    """POST /api/inbox/{id}/restore — restore a triaged/acked item."""
    store.restore(item_id)
    return await get_inbox(request)


@router.post("/{parent_id}/split")
async def split_item(request: Request, parent_id: str):
    """POST /api/inbox/{parent}/split — split a correlated parent into individual items."""
    split(parent_id)
    return await get_inbox(request)


@router.post("/refresh")
async def refresh_inbox(request: Request):
    """POST /api/inbox/refresh — run all adapters + correlation, re-render."""
    from observeco.inbox.correlate import correlate as run_correlate
    from observeco.inbox.registry import build_and_store

    count = build_and_store()
    result = run_correlate(store)
    logger.info("Inbox refresh: %d new items, %d correlated (%d folded)",
                count, result.parents_created, result.children_folded)
    return await get_inbox(request)


@router.post("/cleanup/apply")
async def apply_cleanup(request: Request):
    """POST /api/inbox/cleanup/apply — applies P0.0 classification fixes.

    Checked fixes are applied via the request body (list of fix IDs).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    fixes = body.get("fixes", [])
    results = {}

    for fix_id in fixes:
        if fix_id == "reclassify_profiles":
            # Reclassify known profile agents from 'service' to 'profile'
            conn = db._get_conn()
            profile_names = ["kanban", "workspace", "spectrum"]
            for name in profile_names:
                conn.execute(
                    "UPDATE agent_configs SET class = 'profile' WHERE agent_name = ?",
                    (name,),
                )
            conn.commit()
            results["reclassify_profiles"] = "applied"
        elif fix_id == "exclude_tests":
            # Mark test entities
            conn = db._get_conn()
            test_names = ["test-config-agent", "my_new_agent"]
            for name in test_names:
                conn.execute(
                    "UPDATE agent_configs SET class = 'test' WHERE agent_name = ?",
                    (name,),
                )
            conn.commit()
            results["exclude_tests"] = "applied"
        elif fix_id == "reset_stale_circuits":
            # Reset stale circuits (>7d)
            now = int(time.time())
            conn = db._get_conn()
            stale = conn.execute(
                "SELECT agent_name FROM circuit_breakers "
                "WHERE tripped = 1 AND cooldown_until < ?",
                (now - 7 * 86400,),
            ).fetchall()
            for row in stale:
                conn.execute(
                    "UPDATE circuit_breakers SET tripped = 0, failure_count = 0 "
                    "WHERE agent_name = ?",
                    (row["agent_name"],),
                )
            conn.commit()
            results["reset_stale_circuits"] = f"reset {len(stale)} circuits"

    # Rebuild inbox after cleanup
    from observeco.inbox.correlate import correlate as run_correlate
    from observeco.inbox.registry import build_and_store
    build_and_store()
    run_correlate()

    return JSONResponse({"status": "ok", "results": results})


# ── Index page (for nav wiring) ─────────────────────────────────────

@router.get("/page", response_class=HTMLResponse)
async def inbox_page(request: Request):
    """Full inbox page (wraps partial with header + nav breadcrumb)."""
    return await get_inbox(request)
