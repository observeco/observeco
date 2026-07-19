"""Efficiency API — Phase 1: session-level scoring endpoint.

Reads Hermes session JSONL, computes 11 metrics + archetype + effectiveness.
Phase 3: optimize write-back, custom rule packs, per-archetype baselines.
Token-based metrics (context-pressure, cache-hit, yield-density) remain noop until
token_logs.session_id is populated by the logging layer (see spec §11 ponytail).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from observeco.config import hermes_home
from observeco.dirs import get_data_dir
from observeco.efficiency.metrics import (
    OPTIMIZE_MARKER_END,
    OPTIMIZE_MARKER_START,
    build_optimize_block,
    classify_archetype,
    compute_baseline,
    compute_effectiveness,
    compute_efficiency,
    evaluate_rules,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/efficiency", tags=["efficiency"])


def _sessions_dir() -> Path:
    """Hermes sessions directory. ponytail: hardcoded to ~/.hermes/sessions.
    Upgrade: use hermes_home() resolution when commercial multi-home lands."""
    home = hermes_home()
    if home:
        return home / "sessions"
    return Path.home() / ".hermes" / "sessions"


def _parse_session(session_id: str) -> list[dict] | None:
    """Parse a Hermes session JSONL into list of turn dicts.

    Verified against real data: assistant turns carry tool_calls;
    tool turns carry name + stringified-JSON content with exit_code.
    """
    path = _sessions_dir() / f"{session_id}.jsonl"
    if not path.exists():
        return None
    turns: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = obj.get("role", "")
        if role in ("assistant", "tool", "user", "session_meta"):
            turns.append(obj)
    return turns


@router.get("/session/{session_id}")
async def session_efficiency(session_id: str):
    """Full efficiency report for one session."""
    turns = _parse_session(session_id)
    if turns is None:
        raise HTTPException(status_code=404, detail="session not found")

    efficiency = compute_efficiency(turns, session_id=session_id)
    archetype = classify_archetype(turns)
    effectiveness = compute_effectiveness(turns)

    return {
        "session_id": session_id,
        "efficiency": efficiency,
        "archetype": archetype,
        "effectiveness": effectiveness,
    }


def _list_recent_sessions(limit: int = 20, max_scan: int = 500) -> list[tuple[str, str]]:
    """Scan Hermes session JSONL files, newest first.

    ponytail: scans up to max_scan files — guard against large session dirs.
    Upgrade: SQLite-backed index if scan becomes a bottleneck.
    """
    import glob
    import os

    files = sorted(
        glob.glob(str(_sessions_dir() / "*.jsonl")),
        key=os.path.getmtime,
        reverse=True,
    )[: max_scan]
    out = []
    for p in files[:limit]:
        stem = os.path.basename(p).replace(".jsonl", "")
        parts = stem.split("_")
        ts = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:]} {parts[1][:2]}:{parts[1][2:4]}" if len(parts) >= 2 else stem
        out.append((stem, ts))
    return out


@router.get("/sessions", response_class=HTMLResponse)
async def sessions_list():
    """HTML session table for the Efficiency tab (htmx target)."""

    sessions = _list_recent_sessions()
    if not sessions:
        return HTMLResponse(
            '<div class="state-msg"><div class="ico">📭</div>'
            "<h3>No sessions found</h3>"
            "<p>No Hermes session data available. Run an agent, then check back.</p></div>"
        )

    rows = []
    for sid, ts in sessions:
        turns = _parse_session(sid)
        if not turns:
            continue
        eff = compute_efficiency(turns, session_id=sid)
        arch = classify_archetype(turns)
        outcome = compute_effectiveness(turns)
        # Per-archetype baseline line
        baseline = compute_baseline(sid, arch["archetype"])
        baseline_line = ""
        if baseline.get("baseline") is not None and eff["score"] is not None:
            delta = eff["score"] - baseline["baseline"]
            cmp = f"{delta:+d}" if delta != 0 else "on par with"
            baseline_line = f"Score {eff['score']} vs your usual {baseline['baseline']} for {arch['archetype']} ({baseline['peer_count']} peers) — {cmp}"
        score = eff["score"]
        score_cls = "bad" if (score is not None and score < 50) else "warn" if (score is not None and score < 80) else "good"
        rows.append(f"""<tr class="sess-row" onclick="toggleSessionDetail('{sid}')">
    <td class="mono">{_esc(sid[:19])}</td>
    <td><span class="chip {_esc(arch['archetype'])}">{_esc(arch['archetype'])}</span></td>
    <td><span class="score {score_cls}">{score if score is not None else '—'}</span></td>
    <td><span class="chip {'ok' if outcome['verdict'] in ('succeeded','likely ok') else 'bad'}">{_esc(outcome['verdict'])}</span></td>
</tr>
<div id="{sid}-detail" class="sess-detail" style="display:none">
    {_render_efficiency_card(turns, eff, arch, outcome, sid=sid, baseline_line=baseline_line)}
</div>""")

    if not rows:
        return HTMLResponse(
            '<div class="state-msg"><div class="ico">📭</div>'
            "<h3>No sessions found</h3>"
            "<p>Could not parse any sessions.</p></div>"
        )

    return HTMLResponse(f"""<div class="sec-h">Recent Sessions</div>
<table class="tbl sess-tbl">
  <tr><th>Session</th><th>Archetype</th><th>Efficiency</th><th>Outcome</th></tr>
  {''.join(rows)}
</table>
<script>
function toggleSessionDetail(id) {{
  var el = document.getElementById(id + '-detail');
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}
function optimizeSession(sid, btn) {{
  var result = document.getElementById('opt-' + sid);
  btn.disabled = true;
  btn.textContent = 'Optimizing…';
  fetch('/api/efficiency/optimize/apply/' + sid, {{method: 'POST', headers: {{'X-ObserveCo-Token': window.__OBSERVECO_TOKEN || ''}} }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      result.style.display = 'block';
      if (data.status === 'applied') {{
        result.innerHTML = '<span class="opt-ok">✓ Written to AGENTS.md — ~' + (data.reclaimable_tokens||0).toLocaleString() + ' tokens reclaimable per run</span>';
        btn.textContent = 'Optimized ✓';
      }} else if (data.status === 'noop') {{
        result.innerHTML = '<span class="opt-ok">' + (data.message||'Nothing to optimize') + '</span>';
        btn.textContent = 'No waste';
      }} else {{
        result.innerHTML = '<span class="opt-err">Error: ' + (data.detail||'unknown') + '</span>';
        btn.textContent = 'Retry';
        btn.disabled = false;
      }}
    }})
    .catch(function(e) {{
      result.style.display = 'block';
      result.innerHTML = '<span class="opt-err">Request failed</span>';
      btn.textContent = 'Retry';
      btn.disabled = false;
    }});
}}
</script>""")


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _render_efficiency_card(turns, eff, arch, outcome, sid: str = "", baseline_line: str = "") -> str:
    """Expandable per-session efficiency card."""
    metrics_html = []
    for m in eff["metrics"]:
        if m["status"] == "noop":
            continue
        label = m["id"].replace("-", " ").title()
        detail = ""
        if isinstance(m.get("value"), dict):
            if "files" in m["value"] and isinstance(m["value"]["files"], dict):
                files = list(m["value"]["files"].keys())[:3]
                detail = ", ".join(files)
                if len(m["value"]["files"]) > 3:
                    detail += f" +{len(m['value']['files']) - 3} more"
            elif "reclaimable_tokens" in m["value"]:
                detail = f"~{m['value']['reclaimable_tokens']:,} reclaimable"
        metrics_html.append(f"""<div class="metric-row {m['status']}">
    <span class="m-dot">●</span>
    <span class="m-label">{label}</span>
    <span class="m-detail">{_esc(detail)}</span>
</div>""")

    optimize_html = ""
    if sid and eff.get("_reclaimable", 0) > 0:
        optimize_html = f"""<button class="btn-opt" onclick="optimizeSession('{sid}', this)">Optimize future runs →</button>
<div class="opt-result" id="opt-{sid}" style="display:none"></div>"""

    baseline_html = f'<div class="baseline-line">{_esc(baseline_line)}</div>' if baseline_line else ""

    return f"""<div class="efficiency-card">
    <div class="eff-score">Efficiency {eff['score']} · Outcome {outcome['score']} ({_esc(outcome['verdict'])})</div>
    {''.join(metrics_html)}
    {baseline_html}
    {optimize_html}
</div>"""


# ── Optimize Memory (Phase 3) ────────────────────────────────────────

# ponytail: writes to global ~/.hermes/AGENTS.md (created if absent).
# Per-profile targeting deferred — sessions have no agent_name field.
OPTIMIZE_TARGET = Path.home() / ".hermes" / "AGENTS.md"
OPTIMIZE_PROFILE_DIR = get_data_dir() / "efficiency"


@router.post("/optimize/preview/{session_id}")
async def optimize_preview(session_id: str):
    """Preview the optimize block that would be written."""

    turns = _parse_session(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="session not found")
    eff = compute_efficiency(turns, session_id=session_id)
    block = build_optimize_block(eff)
    if not block:
        return {"status": "noop", "message": "no waste to optimize", "block": ""}
    return {"status": "ok", "block": block,
            "reclaimable_tokens": eff.get("_reclaimable", 0),
            "target": str(OPTIMIZE_TARGET)}


@router.post("/optimize/apply/{session_id}")
async def optimize_apply(session_id: str):
    """Write the optimize block to ~/.hermes/AGENTS.md (reversible, marked)."""
    import re as _re

    turns = _parse_session(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="session not found")
    eff = compute_efficiency(turns, session_id=session_id)
    block = build_optimize_block(eff)
    if not block:
        return {"status": "noop", "message": "no waste to optimize"}

    OPTIMIZE_TARGET.parent.mkdir(parents=True, exist_ok=True)
    current = OPTIMIZE_TARGET.read_text() if OPTIMIZE_TARGET.exists() else ""
    pattern = _re.compile(
        _re.escape(OPTIMIZE_MARKER_START) + r".*?" + _re.escape(OPTIMIZE_MARKER_END) + r"\n?",
        _re.DOTALL,
    )
    if pattern.search(current):
        new_content = pattern.sub(block + "\n", current)
    else:
        new_content = current + ("\n" if current and not current.endswith("\n") else "") + block + "\n"
    OPTIMIZE_TARGET.write_text(new_content)
    return {"status": "applied", "file": str(OPTIMIZE_TARGET), "reclaimable_tokens": eff.get("_reclaimable", 0)}


@router.post("/optimize/revert/{session_id}")
async def optimize_revert(session_id: str):
    """Remove the optimize block from ~/.hermes/AGENTS.md."""
    import re as _re

    if not OPTIMIZE_TARGET.exists():
        return {"status": "noop", "message": "no AGENTS.md"}
    current = OPTIMIZE_TARGET.read_text()
    pattern = _re.compile(
        _re.escape(OPTIMIZE_MARKER_START) + r".*?" + _re.escape(OPTIMIZE_MARKER_END) + r"\n?",
        _re.DOTALL,
    )
    new_content = pattern.sub("", current)
    if new_content == current:
        return {"status": "noop", "message": "no optimize block found"}
    OPTIMIZE_TARGET.write_text(new_content)
    return {"status": "reverted", "file": str(OPTIMIZE_TARGET)}


# ── Custom Rule Packs (Phase 3) ──────────────────────────────────────

@router.get("/rules/{session_id}")
async def session_rules(session_id: str):
    """Evaluate custom rules (from ~/.observeco/efficiency/rules.json) against a session."""
    turns = _parse_session(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="session not found")
    rules_path = get_data_dir() / "efficiency" / "rules.json"
    if not rules_path.exists():
        return {"session_id": session_id, "rules_loaded": 0, "findings": []}
    try:
        rules = json.loads(rules_path.read_text()).get("rules", [])
    except (json.JSONDecodeError, OSError):
        return {"session_id": session_id, "rules_loaded": 0, "findings": [], "error": "invalid rules.json"}
    findings = evaluate_rules(turns, rules)
    return {"session_id": session_id, "rules_loaded": len(rules), "findings": findings}


# ── Per-Archetype Baseline (Phase 3) ─────────────────────────────────

@router.get("/baseline/{session_id}")
async def session_baseline(session_id: str):
    """Compare this session's efficiency to recent same-archetype peers."""
    turns = _parse_session(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="session not found")
    archetype = classify_archetype(turns)
    baseline = compute_baseline(session_id, archetype["archetype"])
    eff = compute_efficiency(turns)
    result = dict(baseline)
    result["session_id"] = session_id
    result["session_score"] = eff["score"]
    if baseline.get("baseline") is not None and eff["score"] is not None:
        result["delta"] = eff["score"] - baseline["baseline"]
    return result

