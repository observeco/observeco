"""Harness Optimizer dashboard routes (obs-spec-056 §8 frontend + obs-spec-088).

Read-only viewer of real optimization runs + a run trigger that spawns the
existing CLI loop (observeco harness optimize) as a detached subprocess.
Plus obs-spec-088: Phantom Guardrail gate-test button + experience bank view.

Note: the loop applies promoted edits to the live agent (apply-edit no-op
was closed in commit 2e24711). This UI shows real evaluation results,
phantom-rejection log, and experience-bank stats.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from observeco.db import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/harness", tags=["harness"])
db = Database()

# In-process guard so two run triggers don't double-spawn.
_run_lock = threading.Lock()


def _pct(v: Optional[float]) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "—"


def _runs_html(agent: Optional[str]) -> str:
    from observeco.capability.harness import HarnessOptimizer

    runs = HarnessOptimizer(db=db).list_runs(agent)
    if not runs:
        return (
            '<div class="section-h"><h2>Harness Optimizer</h2>'
            '<span class="count">0 runs</span></div>'
            '<div style="padding:20px;color:#64748b;font-size:13px;">'
            "No optimization runs yet. Run the loop to propose + evaluate harness edits "
            "against the dev/test split.</div>"
        )
    rows = []
    for r in runs:
        verdict = "PROMOTED" if r.get("promoted") else "not promoted"
        vcls = "ok" if r.get("promoted") else "warn"
        rows.append(
            f'<div class="crow tappable" onclick="htmx.ajax(\'GET\', '
            f"'/api/harness/runs/{r['id']}', {{target:'#harnessDetail', swap:'innerHTML'}})\" "
            f'tabindex="0" role="button" aria-label="View run">'
            f'<div class="cname">{_html_escape(r.get("agent_name", "?"))}</div>'
            f'<div class="cmeta">dev {_pct(r.get("candidate_dev_score"))} · '
            f'test {_pct(r.get("candidate_test_score"))}</div>'
            f'<div class="badge {vcls}">{verdict}</div></div>'
        )
    return (
        '<div class="section-h"><h2>Harness Optimizer</h2>'
        f'<span class="count">{len(runs)} runs</span></div>'
        '<div style="padding:12px 16px;color:#94a3b8;font-size:12px;line-height:1.5;">'
        "Proposes harness edits via LLM, evaluates on held-out dev/test, gates promotion. "
        "Edits are <strong>not auto-applied</strong> to the live agent (loop is evaluation-only)."
        "</div>"
        + '<div id="harnessDetail" style="margin-top:8px;"></div>'
        + "".join(rows)
    )


def _run_detail_html(run_id: str) -> str:
    from observeco.capability.harness import HarnessOptimizer

    run = HarnessOptimizer(db=db).get_run(run_id)
    if not run:
        return '<div style="padding:16px;color:#ef4444;">Run not found.</div>'
    verdict = "PROMOTED" if run.get("promoted") else "not promoted"
    vcls = "ok" if run.get("promoted") else "warn"

    # Eval breakdown table (method × split)
    evals = run.get("eval_runs", [])
    eval_rows = []
    for e in evals:
        eval_rows.append(
            f"<tr><td>{_html_escape(e.get('method', ''))}</td>"
            f"<td>{_html_escape(e.get('split', ''))}</td>"
            f"<td>{_pct(e.get('pass_at_1'))}</td>"
            f"<td>{e.get('total_rollouts', '—')}</td></tr>"
        )
    eval_html = (
        '<table class="data-table" style="width:100%;font-size:12px;margin-top:8px;">'
        "<thead><tr><th>method</th><th>split</th><th>score</th><th>rollouts</th></tr></thead>"
        "<tbody>" + "".join(eval_rows) + "</tbody></table>"
        if eval_rows else
        '<div style="color:#64748b;font-size:12px;">No eval rows.</div>'
    )

    # Proposed edits
    edits = run.get("edits", [])
    edit_cards = []
    for e in edits:
        cls = _html_escape(e.get("classification", "unclassified"))
        edit_cards.append(
            f'<div style="border:1px solid #1e293b;border-radius:6px;padding:10px;margin-top:8px;">'
            f'<div style="font-size:11px;color:#94a3b8;">iter {e.get("iteration", "?")} · '
            f'<span class="badge neutral">{cls}</span></div>'
            f'<div style="font-size:13px;margin-top:4px;white-space:pre-wrap;">'
            f'{_html_escape(e.get("edit_text") or "(no description)")}</div>'
            f'<div style="font-size:10px;color:#64748b;margin-top:4px;">'
            f'conf {e.get("classification_confidence", "—")}</div></div>'
        )
    edits_html = (
        "".join(edit_cards)
        if edit_cards else
        '<div style="color:#64748b;font-size:12px;">No edits proposed.</div>'
    )

    reason = _html_escape(run.get("promotion_reason") or "")
    return (
        f'<div class="section-h"><h2>Run {_html_escape(run_id[:8])}</h2>'
        f'<span class="badge {vcls}">{verdict}</span></div>'
        f'<div style="padding:12px 16px;font-size:13px;">'
        f'<div>agent: <strong>{_html_escape(run.get("agent_name", "?"))}</strong></div>'
        f'<div style="margin-top:6px;">dev {_pct(run.get("candidate_dev_score"))} · '
        f'test {_pct(run.get("candidate_test_score"))}</div>'
        f'<div style="margin-top:6px;color:#94a3b8;">{reason}</div>'
        f'<div style="margin-top:10px;"><strong>Eval breakdown</strong></div>'
        f"{eval_html}"
        f'<div style="margin-top:12px;"><strong>Proposed edits (not applied)</strong></div>'
        f"{edits_html}"
        f"</div>"
    )


def _html_escape(s) -> str:
    if s is None:
        return ""
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@router.get("/runs", response_class=HTMLResponse)
async def harness_runs(agent: Optional[str] = Query(None)):
    return HTMLResponse(_runs_html(agent))


@router.post("/gate-test", response_class=JSONResponse)
async def harness_gate_test(agent: str = Query("default")):
    """Run Counterfactual Fabrication Lab self-check (no LLM, no tokens)."""
    from observeco.capability.harness import HarnessOptimizer
    from observeco.db import Database

    try:
        opt = HarnessOptimizer(db=Database())
        result = opt.run_gate_test(agent)
        # Persist result for the GET view
        db = Database()
        db._write(
            "INSERT INTO harness_gate_tests "
            "(id, agent_name, run_at, proposer_model, total_runs, fabricated_runs, "
            "fabrication_rate, verdict, detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), agent, datetime.now(timezone.utc).isoformat(),
             "phantom_guardrail_gate", result["total_runs"], result["fabricated_runs"],
             result["fabrication_rate"], result["verdict"], json.dumps(result["detail"])),
        )
        return {"ok": True, "result": result}
    except Exception as e:
        logger.exception("Gate test failed for %s", agent)
        return {"ok": False, "message": str(e)}


@router.get("/gate-test", response_class=HTMLResponse)
async def harness_gate_test_view(agent: Optional[str] = Query(None)):
    from observeco.db import Database

    db = Database()
    row = db._get_conn().execute(
        "SELECT * FROM harness_gate_tests WHERE agent_name=? "
        "ORDER BY run_at DESC LIMIT 1",
        (agent or "default",),
    ).fetchone()
    if not row:
        return HTMLResponse(
            '<div style="color:#64748b;font-size:12px;padding:12px;">'
            'No gate test run yet. Click "🛡️ Gate Test" to verify the Phantom Guardrail gate.</div>'
        )
    detail = json.loads(row["detail"]) if row["detail"] else []
    rows = "".join(
        f'<div style="font-size:12px;padding:4px 0;border-bottom:1px solid #1e293b;">'
        f'<span class="badge {"ok" if d["accepted"] == d["expected"] else "fail"}">'
        f'{"PASS" if d["accepted"] == d["expected"] else "FAIL"}</span> '
        f'{_html_escape(d["edit"][:50])} → accepted={d["accepted"]}</div>'
        for d in detail
    )
    vcls = "ok" if row["verdict"] == "PASS" else "fail"
    return HTMLResponse(
        f'<div class="section-h"><h2>Phantom Guardrail Gate Test</h2>'
        f'<span class="badge {vcls}">{row["verdict"]}</span></div>'
        f'<div style="font-size:12px;color:#94a3b8;padding:8px 0;">'
        f'Total {row["total_runs"]} · Fabricated {row["fabricated_runs"]} · '
        f'Rate {row["fabrication_rate"]*100:.1f}%</div>'
        + rows
    )


@router.get("/experience", response_class=HTMLResponse)
async def harness_experience_view(agent: Optional[str] = Query(None)):
    from observeco.capability.experience import ExperienceBank

    agent = agent or "default"
    bank = ExperienceBank()
    stats = bank.stats(agent)
    reject_rows = "".join(
        f'<div style="font-size:11px;padding:4px 0;border-bottom:1px solid #1e293b;color:#94a3b8;">'
        f'<strong>{_html_escape(r["failure_class"])}</strong> — {_html_escape(r["diagnosis"][:60])}</div>'
        for r in stats["rejection_log"][:20]
    )
    fc_rows = "".join(
        f'<div style="font-size:11px;padding:2px 0;">{_html_escape(fc)}: {c}</div>'
        for fc, c in stats["failure_classes"].items()
    )
    return HTMLResponse(
        f'<div class="section-h"><h2>Experience Bank</h2>'
        f'<span class="count">{stats["total"]}</span></div>'
        f'<div style="font-size:12px;color:#94a3b8;padding:8px 0;">'
        f'Global patterns: {stats["global_patterns"]} · Layers: {stats["per_layer"]}</div>'
        + (f'<div style="margin-top:8px;"><strong style="font-size:12px;">Observed failure classes</strong>{fc_rows}</div>' if fc_rows else '')
        + (f'<div style="margin-top:12px;"><strong style="font-size:12px;">Phantom rejections</strong>{reject_rows}</div>' if reject_rows else '')
        + '<div style="margin-top:12px;"><button onclick="if(confirm(\'Clear all experiences for this agent?\')) '
          'fetch(\'/api/harness/experience/clear?agent=' + agent + '\', {method:\'POST\'}).then(()=>'
          'htmx.ajax(\'GET\', \'/api/harness/experience?agent=' + agent + '\', {target:\'#harnessExperience\', swap:\'innerHTML\'}))" '
          'style="background:#475569;border:none;color:white;border-radius:6px;padding:6px 12px;font-size:11px;cursor:pointer;">Clear</button></div>'
    )


@router.post("/experience/clear", response_class=JSONResponse)
async def harness_experience_clear(agent: str = Query("default")):
    from observeco.capability.experience import ExperienceBank

    bank = ExperienceBank()
    n = bank.clear(agent)
    return {"ok": True, "cleared": n}


@router.get("/runs/{run_id}", response_class=HTMLResponse)
async def harness_run_detail(run_id: str):
    return HTMLResponse(_run_detail_html(run_id))


@router.post("/run", response_class=JSONResponse)
async def harness_run_start(agent: str = Query("default"), iterations: int = Query(5)):
    """Trigger the real CLI loop as a detached subprocess (mirrors canary/run).

    Costs tokens (LLM proposer ~$0.50/iter, BYOK) + canary eval on dev/test.
    The frontend must show a cost estimate and confirm before calling this.
    """
    if not _run_lock.acquire(blocking=False):
        return {"ok": False, "message": "Harness optimization already running"}
    try:
        cmd = [
            sys.executable, "-m", "observeco.cli", "harness", "optimize",
            "--agent", agent, "--iterations", str(iterations),
        ]
        # Detach: survives dashboard restart; results read from DB, not the pipe.
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {
            "ok": True,
            "message": f"Harness optimization started for {agent} ({iterations} iterations)",
        }
    except Exception:
        logger.exception("Failed to start harness optimization for %s", agent)
        return {"ok": False, "message": "Failed to start harness optimization"}
    finally:
        _run_lock.release()
