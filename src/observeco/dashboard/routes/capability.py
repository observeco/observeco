"""Capability monitoring API routes — drift, grid, timeline, tasks.

obs-spec-052/053/054/055: Dashboard API endpoints for the capability monitoring layer.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from observeco.capability.canary import CanaryRunner
from observeco.capability.drift import DriftDetector
from observeco.db import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/capability", tags=["capability"])
db = Database()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _sev_color(severity: str) -> str:
    return {"breach": "var(--danger)", "warning": "var(--warn)", "info": "var(--meta)"}.get(severity, "var(--muted)")


def _sev_icon(severity: str) -> str:
    return {"breach": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")


def _resolve_agent(agent: str) -> str:
    """Resolve agent name, falling back to first available if 'default' has no data."""
    if agent != "default":
        return agent
    conn = db._get_conn()
    row = conn.execute(
        "SELECT agent_name FROM config_snapshots GROUP BY agent_name ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    if row:
        return row["agent_name"]
    # Fallback: try the config loader
    from observeco.config import load_config
    config = load_config()
    if config.agents:
        return config.agents[0].name
    return "default"


# ── Drift endpoints ─────────────────────────────────────────────────────────

@router.post("/grid/run", response_class=JSONResponse)
async def grid_run_from_dashboard(agent: str = Query("default")):
    """POST /api/capability/grid/run?agent=NAME — run full grid from dashboard.

    Uses CapabilityGridRunner to run canary tasks across model × config combinations.
    Runs synchronously (grid is typically small: 3 models × 2 configs × 9 tasks × 3 trials).
    """
    from observeco.capability.grid import CapabilityGridRunner
    import threading

    def _run():
        try:
            from observeco.db import Database
            runner = CapabilityGridRunner(db=Database())
            result = runner.run(agent_name=agent, trials=1)
            logger.info("Grid run complete for %s: %d cells", agent, len(result.get("cells", [])))
        except Exception:
            import traceback
            traceback.print_exc()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return {"ok": True, "message": f"Grid started for {agent}"}


@router.post("/canary/run", response_class=JSONResponse)
async def canary_run_from_fleet(agent: str = Query("default"), tasks: Optional[str] = Query(None)):
    """POST /api/capability/canary/run?agent=NAME&tasks=id1,id2 — run canary async, return immediately.

    Runs the benchmark in a SEPARATE PROCESS (not a thread) to avoid SQLite
    writer contention inside the web server's own process. The status endpoint
    polls canary_runs/canary_results, so no IPC is needed — the subprocess
    writes directly to the shared DB via WAL.
    """
    try:
        import subprocess
        import sys

        # Best-effort cleanup: mark runs stuck in 'running' for >30min as 'failed'
        try:
            conn = db._get_conn()
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                "UPDATE canary_runs SET status = 'failed' "
                "WHERE status = 'running' AND started_at < datetime('now', '-30 minutes')"
            )
            conn.commit()
        except Exception:
            pass  # cleanup is best-effort

        # Build CLI invocation: spawn a separate process running the same
        # interpreter that launched the dashboard (robust against venv/PATH).
        cmd = [sys.executable, "-m", "observeco.cli", "canary", "run", "--agent", agent, "--trials", "1"]
        if tasks:
            cmd += ["--tasks", tasks]

        # start_new_session=True detaches from the server's process group so the
        # benchmark keeps running even if the dashboard restarts. stdout/stderr
        # go to DEVNULL — results are read from the DB, not the pipe.
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"ok": True, "message": f"Canary started for {agent}"}
    except Exception:
        return {"ok": False, "message": "Failed to start canary"}


@router.get("/canary/judge-reasoning", response_class=JSONResponse)
async def judge_reasoning(task_id: str = Query("")):
    """GET /api/capability/canary/judge-reasoning?task_id=X
    Returns the latest LLM judge results for a task, with per-assertion scores and reasoning.
    """
    if not task_id:
        return {"assertions": []}
    import re as _re
    from observeco.capability.canary import CanaryRunner
    runner = CanaryRunner(db=db)
    task = runner.get_task(task_id)
    if not task:
        return {"assertions": []}
    conn = db._get_conn()
    # Get latest results for this task that have llm_judge in their reasoning
    results = conn.execute(
        "SELECT accuracy, status, reasoning FROM canary_results "
        "WHERE task_id = ? AND reasoning LIKE '%llm_judge%' "
        "ORDER BY created_at DESC LIMIT 5",
        (task_id,),
    ).fetchall()
    if not results:
        return {"assertions": []}
    assertions_list = []
    try:
        task_assertions = json.loads(task["assertions"]) if isinstance(task["assertions"], str) else task["assertions"]
    except Exception:
        task_assertions = []
    # Map results back to assertions
    for r in results:
        assertions_list.append({
            "type": "llm_judge",
            "name": task.get("name", task_id),
            "score": r["accuracy"] if r["accuracy"] is not None else 0.0,
            "status": r["status"],
            "reasoning": r["reasoning"] or "",
        })
    return {"assertions": assertions_list}


@router.get("/canary/status", response_class=JSONResponse)
async def canary_status(agent: str = Query("default")):
    """GET /api/capability/canary/status?agent=NAME — check if canary is still running with live progress."""
    try:
        conn = db._get_conn()
        conn.execute("PRAGMA busy_timeout=5000")
        # Best-effort cleanup: mark runs stuck in 'running' for >30min as 'failed'
        try:
            conn.execute(
                "UPDATE canary_runs SET status = 'failed' "
                "WHERE status = 'running' AND started_at < datetime('now', '-30 minutes')"
            )
            conn.commit()
        except Exception:
            pass  # cleanup is best-effort

        running = conn.execute(
            "SELECT COUNT(*) as c FROM canary_runs WHERE agent_name = ? AND status = 'running'",
            (agent,),
        ).fetchone()
        latest = conn.execute(
            "SELECT id, pass_count, fail_count, hang_count, total_tasks, status, started_at "
            "FROM canary_runs WHERE agent_name = ? ORDER BY started_at DESC LIMIT 1",
            (agent,),
        ).fetchone()
        if not latest:
            return {"running": False, "completed": False}

        # If latest is 'running' but started >5 min ago with no results, it's stuck
        is_running = latest["status"] == "running"
        if is_running:
            results_count = conn.execute(
                "SELECT COUNT(*) as c FROM canary_results WHERE run_id = ?",
                (latest["id"],),
            ).fetchone()["c"]
            if results_count == 0 and latest["started_at"]:
                from datetime import datetime, timezone
                started = datetime.fromisoformat(latest["started_at"])
                if (datetime.now(timezone.utc) - started).total_seconds() > 300:
                    is_running = False  # stuck — no progress in 5 min
            elif latest["started_at"]:
                from datetime import datetime, timezone
                started = datetime.fromisoformat(latest["started_at"])
                if (datetime.now(timezone.utc) - started).total_seconds() > 1800:
                    is_running = False  # stale — running for >30 min

        is_completed = not is_running and latest["status"] in ("completed", "failed")
        if not is_running and not is_completed:
            return {"running": False, "completed": False}

        # Sum individual results for live progress (stored per-trial during execution)
        live = conn.execute(
            "SELECT "
            "SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) as pass_count, "
            "SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) as fail_count, "
            "SUM(CASE WHEN status = 'hang' THEN 1 ELSE 0 END) as hang_count, "
            "COUNT(*) as total "
            "FROM canary_results WHERE run_id = ?",
            (latest["id"],),
        ).fetchone()

        return {
            "running": is_running,
            "completed": is_completed,
            "run_id": latest["id"],
            "pass_count": live["pass_count"] or 0 if live else 0,
            "fail_count": live["fail_count"] or 0 if live else 0,
            "hang_count": live["hang_count"] or 0 if live else 0,
            "total_tasks": latest["total_tasks"],
        }
    except Exception:
        return {"running": True, "completed": False, "pass_count": 0, "fail_count": 0, "hang_count": 0, "total_tasks": 0}


@router.get("/drift", response_class=JSONResponse)
async def drift_detail(agent: str = Query("default")):
    """GET /api/capability/drift?agent=NAME — latest drift detail for hero section."""
    agent = _resolve_agent(agent)
    detector = DriftDetector(db=db)
    result = detector.get_detail(agent)
    if result is None:
        return {"agent": agent, "current": None, "baseline": None, "drift": None, "tasks": []}
    return result


@router.get("/drift/history", response_class=JSONResponse)
async def drift_history(agent: str = Query("default"), days: int = Query(14)):
    """GET /api/capability/drift/history?agent=NAME&days=14 — time series for chart."""
    agent = _resolve_agent(agent)
    detector = DriftDetector(db=db)
    return detector.get_history(agent, days)


@router.post("/drift/{event_id}/acknowledge", response_class=JSONResponse)
async def drift_acknowledge(event_id: str):
    """POST /api/capability/drift/{id}/acknowledge — mark drift as acknowledged."""
    detector = DriftDetector(db=db)
    return detector.acknowledge(event_id)


# ── Grid endpoints ───────────────────────────────────────────────────────────

@router.get("/grid", response_class=JSONResponse)
async def grid_report(agent: str = Query("default"), run_id: Optional[str] = Query(None)):
    """GET /api/capability/grid?agent=NAME&run_id=ID — grid report data."""
    conn = db._get_conn()

    # Resolve latest run if not specified
    if not run_id:
        row = conn.execute(
            "SELECT id FROM grid_runs WHERE agent_name = ? AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT 1",
            (agent,),
        ).fetchone()
        if not row:
            return {"agent": agent, "run_id": None, "cells": [], "models": [], "configs": [], "tasks": []}
        run_id = row["id"]

    # Get run metadata
    run = conn.execute(
        "SELECT * FROM grid_runs WHERE id = ?", (run_id,)
    ).fetchone()
    if not run:
        return {"agent": agent, "run_id": run_id, "cells": [], "models": [], "configs": [], "tasks": []}

    models = json.loads(run["models"]) if isinstance(run["models"], str) else run["models"]
    configs = json.loads(run["configs"]) if isinstance(run["configs"], str) else run["configs"]

    # Get cells
    cells = conn.execute(
        "SELECT gr.task_id, ct.name as task_name, gr.model, gr.config, "
        "gr.accuracy, gr.ci_lower, gr.ci_upper, gr.cost, gr.flags, gr.hang "
        "FROM grid_results gr JOIN canary_tasks ct ON gr.task_id = ct.id "
        "WHERE gr.grid_run_id = ? ORDER BY ct.id, gr.model, gr.config",
        (run_id,),
    ).fetchall()

    task_names = list(dict.fromkeys(c["task_name"] for c in cells))

    return {
        "agent": agent,
        "run_id": run_id,
        "date": run["started_at"][:10] if run["started_at"] else "",
        "models": models,
        "configs": configs,
        "tasks": task_names,
        "cells": [dict(c) for c in cells],
    }


# ── Timeline endpoints ──────────────────────────────────────────────────────

@router.get("/timeline", response_class=JSONResponse)
async def config_timeline(agent: str = Query("default")):
    """GET /api/capability/timeline?agent=NAME — config change timeline."""
    agent = _resolve_agent(agent)
    conn = db._get_conn()

    # Get segments
    segments = {}
    seg_rows = conn.execute(
        "SELECT DISTINCT config_hash, config_label, segment FROM config_snapshots "
        "WHERE agent_name = ? AND segment IS NOT NULL ORDER BY created_at",
        (agent,),
    ).fetchall()
    for r in seg_rows:
        label = r["config_label"] or r["config_hash"][:12]
        segments[r["segment"]] = label

    # Get events
    events = conn.execute(
        "SELECT id, change_type, description, git_commit, accuracy, segment, created_at "
        "FROM config_snapshots WHERE agent_name = ? ORDER BY created_at DESC LIMIT 50",
        (agent,),
    ).fetchall()

    # Also include drift events as timeline entries
    drift_events = conn.execute(
        "SELECT id, drift_pct, severity, created_at FROM drift_events "
        "WHERE agent_name = ? ORDER BY created_at DESC LIMIT 20",
        (agent,),
    ).fetchall()

    event_list = []
    for e in events:
        event_list.append({
            "date": e["created_at"],
            "type": e["change_type"],
            "title": e["change_type"].replace("_", " ").title(),
            "description": e["description"] or "",
            "segment": e["segment"],
            "accuracy": e["accuracy"],
            "git_commit": e["git_commit"],
        })

    for d in drift_events:
        event_list.append({
            "date": d["created_at"],
            "type": "drift",
            "title": f"Drift {d['severity'].title()}",
            "description": f"Quality dropped {d['drift_pct']:+.1f}%",
            "severity": d["severity"],
            "segment": None,
            "accuracy": None,
        })

    # Sort by date descending
    event_list.sort(key=lambda x: x["date"], reverse=True)

    return {
        "agent": agent,
        "segments": segments,
        "events": event_list,
    }


# ── Task endpoints ───────────────────────────────────────────────────────────

@router.get("/tasks", response_class=JSONResponse)
async def task_list():
    """GET /api/capability/tasks — list all canary tasks."""
    runner = CanaryRunner(db=db)
    tasks = runner.list_tasks()

    # Enrich with last run data
    conn = db._get_conn()
    enriched = []
    for t in tasks:
        last = conn.execute(
            "SELECT cr.status, cr.accuracy, cr.created_at FROM canary_results cr "
            "WHERE cr.task_id = ? ORDER BY cr.created_at DESC LIMIT 1",
            (t["id"],),
        ).fetchone()

        enriched.append({
            "id": t["id"],
            "name": t["name"],
            "description": t.get("description", ""),
            "assertions": t.get("assertions", "[]"),
            "timeout": t["timeout"],
            "trials": t["trials"],
            "built_in": bool(t["built_in"]),
            "last_run": last["created_at"] if last else None,
            "last_accuracy": round(last["accuracy"] * 100, 1) if last and last["accuracy"] is not None else None,
            "last_status": last["status"] if last else None,
        })

    return {"tasks": enriched}


@router.post("/tasks", response_class=JSONResponse)
async def task_create(data: dict):
    """POST /api/capability/tasks — create or update a task."""
    runner = CanaryRunner(db=db)
    result = runner.create_task(data)
    return result


# ── Task list HTML partial (MUST be before parameterized /tasks/{task_id}) ──


@router.get("/tasks/list", response_class=HTMLResponse)
async def task_list_partial():
    """GET /api/capability/tasks/list — task list HTML partial."""
    runner = CanaryRunner(db=db)
    tasks = runner.list_tasks()

    if not tasks:
        return HTMLResponse(content="""
        <div class="cap-empty">
          <div class="cap-empty-icon">📝</div>
          <h2>No Tasks Defined</h2>
          <p>
            Create your first task to start measuring agent quality.
          </p>
          <button onclick="showNewTaskForm()" class="btn btn-primary">New Task</button>
        </div>
        """)

    conn = db._get_conn()
    rows = ""
    for t in tasks:
        last = conn.execute(
            "SELECT status, accuracy FROM canary_results cr "
            "WHERE cr.task_id = ? ORDER BY cr.created_at DESC LIMIT 1",
            (t["id"],),
        ).fetchone()

        # Which agents have been tested with this task?
        agent_rows = conn.execute(
            "SELECT DISTINCT cr2.agent_name FROM canary_results cr "
            "JOIN canary_runs cr2 ON cr.run_id = cr2.id "
            "WHERE cr.task_id = ? AND cr2.agent_name IS NOT NULL",
            (t["id"],),
        ).fetchall()
        agent_names = ", ".join(r["agent_name"] for r in agent_rows) if agent_rows else "—"

        status_dot = "🟢" if last and last["status"] == "pass" else "🟡" if last and last["status"] == "fail" else "⚪"
        status_dot_class = "green" if last and last["status"] == "pass" else "yellow" if last and last["status"] == "fail" else ""
        last_acc = f"{last['accuracy']*100:.0f}%" if last and last["accuracy"] is not None else "—"

        try:
            assertions = json.loads(t["assertions"]) if isinstance(t["assertions"], str) else t["assertions"]
            a_types = ", ".join(a.get("type", "?") for a in (assertions or []))
        except Exception:
            a_types = "?"

        # Category/difficulty badge styling
        cat_badge = ""
        cat = t.get("category") or ""
        diff = t.get("difficulty") or "medium"
        if cat:
            cat_colors = {
                "reasoning": "var(--accent)",
                "coding": "var(--success)",
                "extraction": "var(--purple)",
                "tool_use": "var(--warn)",
                "instruction_following": "var(--info)",
                "safety": "var(--danger)",
            }
            cat_color = cat_colors.get(cat, "var(--fg-2)")
            diff_color = {"easy": "var(--success)", "medium": "var(--warn)", "hard": "var(--danger)"}.get(diff, "var(--fg-2)")
            cat_badge = f"""<span class="badge badge-cat" style="background:{cat_color}15;color:{cat_color};border:1px solid {cat_color}40;font-size:10px;padding:0 6px;border-radius:4px;">{cat}</span>"""
            if diff:
                cat_badge += f"""<span class="badge badge-diff" style="background:{diff_color}15;color:{diff_color};font-size:9px;padding:0 4px;border-radius:3px;margin-left:4px;">{diff}</span>"""

        # Per-task baseline data
        baseline_info = ""
        try:
            ptb = conn.execute(
                "SELECT accuracy, run_count FROM canary_task_baselines "
                "WHERE task_id = ? AND expires_at IS NULL ORDER BY created_at DESC LIMIT 1",
                (t["id"],),
            ).fetchone()
            if ptb:
                baseline_info = f"""<span style="font-size:10px;color:var(--fg-3);margin-left:6px;">baseline: {ptb['accuracy']*100:.0f}% ({ptb['run_count']} runs)</span>"""
        except Exception:
            pass

        rows += f"""\
        <div class="task-item" data-task-id="{_html_escape(t['id'])}">
          <div class="task-row" onclick="this.nextElementSibling.classList.toggle('open')">
            <div class="task-item-info">
              <span class="status-dot {status_dot_class}"></span>
              <div>
                <div class="task-item-name">{_html_escape(t['name'])} <span style="font-size:10px;color:var(--muted);font-weight:400;">{'📦 built-in' if t.get('built_in') else '✏️ custom'}</span></div>
                <div class="task-item-meta">{cat_badge} {a_types} · {t['timeout']}s timeout · {t['trials']} trials{baseline_info}</div>
                <div class="task-item-agents" style="font-size:11px;color:var(--fg-3);margin-top:2px;">🧪 tested on: {_html_escape(agent_names)}</div>
              </div>
            </div>
            <div class="task-item-actions">
              <span style="font-size:12px;color:var(--fg-2);font-weight:600;">{last_acc}</span>
              <button onclick="editTask('{t['id']}')" class="btn btn-sm btn-outline">Edit</button>
              <button onclick="duplicateTask('{t['id']}')" class="btn-icon" title="Duplicate">⧉</button>
              <button onclick="deleteTask('{t['id']}')" class="btn-icon" title="Delete">✕</button>
              <span style="color:var(--fg-3);font-size:11px;margin-left:4px;cursor:pointer;">▼</span>
            </div>
          </div>
          <div class="judge-panel">
            <div class="judge-card" id="judge-{_html_escape(t['id'])}">
              <div style="padding:12px;text-align:center;color:var(--fg-3);font-size:12px;">
                <span class="spinner"></span> Loading judge reasoning...
              </div>
            </div>
          </div>
        </div>"""

    return HTMLResponse(content=f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;">
      <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);">
        <span style="font-size:13px;font-weight:600;color:var(--fg);">Tasks ({len(tasks)})</span>
        <div style="display:flex;gap:6px;">
          <button onclick="showNewTaskForm()" style="background:var(--accent);color:var(--accent-on);border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;">+ New Task</button>
          <button onclick="showToast('Paste YAML in the editor')" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:6px 14px;font-size:12px;color:var(--fg-2);cursor:pointer;">Import YAML</button>
        </div>
      </div>
      {rows}
    </div>
    """)


@router.delete("/tasks/{task_id}", response_class=JSONResponse)
async def task_delete(task_id: str):
    """DELETE /api/capability/tasks/{id} — delete a task."""
    runner = CanaryRunner(db=db)
    return runner.delete_task(task_id)


@router.get("/tasks/{task_id}", response_class=JSONResponse)
async def task_get(task_id: str):
    """GET /api/capability/tasks/{id} — get a single task with parsed assertions."""
    runner = CanaryRunner(db=db)
    task = runner.get_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return task


@router.put("/tasks/{task_id}", response_class=JSONResponse)
async def task_update(task_id: str, data: dict):
    """PUT /api/capability/tasks/{id} — update an existing task."""
    runner = CanaryRunner(db=db)
    return runner.update_task(task_id, data)


@router.get("/tasks/{task_id}/editor", response_class=HTMLResponse)
async def task_editor_partial(task_id: str):
    """GET /api/capability/tasks/{id}/editor — task editor HTML partial (YAML + Form mode)."""
    runner = CanaryRunner(db=db)
    task = runner.get_task(task_id)
    if task is None:
        return HTMLResponse(content="<div style='color:var(--danger);'>Task not found</div>")

    # Build YAML representation
    yaml_lines = [
        f"# {task['name']}",
        f"# {task.get('description', '')}" if task.get('description') else "",
        f"name: {task['id']}",
        f"description: \"{task.get('description', '')}\"",
        "prompt: |",
    ]
    for line in task["prompt"].split("\n"):
        yaml_lines.append(f"  {line}")
    yaml_lines.append("assertions:")
    for a in (task.get("assertions") or []):
        if isinstance(a, dict):
            yaml_lines.append(f"  - type: {a.get('type', '')}")
            for k, v in a.items():
                if k == "type":
                    continue
                if isinstance(v, list):
                    yaml_lines.append(f"    {k}: [{', '.join(repr(x) for x in v)}]")
                else:
                    yaml_lines.append(f"    {k}: {v}")
    yaml_lines.append(f"timeout: {task.get('timeout', 60)}")
    yaml_lines.append(f"trials: {task.get('trials', 3)}")
    yaml_text = "\n".join(yaml_lines)

    # Build form fields from assertions
    a = (task.get("assertions") or [{}])[0] if isinstance(task.get("assertions"), list) else {}
    a_type = a.get("type", "exact_match")
    a_target = ""
    if a_type == "exact_match":
        a_target = a.get("target", "")
    elif a_type == "contains":
        a_target = ", ".join(a.get("keywords", []))
    elif a_type == "numeric_range":
        a_target = f"{a.get('min', 0)}, {a.get('max', 100)}"
    elif a_type == "regex":
        a_target = a.get("pattern", "")

    return HTMLResponse(content=f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="font-size:14px;font-weight:600;color:var(--fg);">✏️ {_html_escape(task['name'])}</div>
        <div style="display:flex;gap:6px;">
          <button onclick="switchEditorMode('{task['id']}', 'yaml')" id="yamlBtn_{task['id']}" class="editor-mode-btn active" style="background:var(--accent-on);border:1px solid rgba(34,197,94,0.3);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--accent);cursor:pointer;">YAML</button>
          <button onclick="switchEditorMode('{task['id']}', 'form')" id="formBtn_{task['id']}" class="editor-mode-btn" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--fg-2);cursor:pointer;">Form</button>
        </div>
      </div>

      <!-- YAML mode -->
      <div id="yamlEditor_{task['id']}" class="editor-pane">
        <textarea id="yamlText_{task['id']}" rows="14" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;font-size:12px;color:var(--fg);font-family:var(--font-mono);resize:vertical;white-space:pre;overflow-x:auto;">{_html_escape(yaml_text)}</textarea>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px;">
          <button onclick="closeEditor('{task['id']}')" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:6px 14px;font-size:12px;color:var(--fg-2);cursor:pointer;">Cancel</button>
          <button onclick="saveYamlTask('{task['id']}')" style="background:var(--accent);color:var(--accent-on);border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;">Save</button>
        </div>
      </div>

      <!-- Form mode -->
      <div id="formEditor_{task['id']}" class="editor-pane" style="display:none;">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
          <div>
            <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Task ID</label>
            <input id="formId_{task['id']}" value="{_html_escape(task['id'])}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
          </div>
          <div>
            <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Display Name</label>
            <input id="formName_{task['id']}" value="{_html_escape(task['name'])}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
          </div>
        </div>
        <div style="margin-bottom:10px;">
          <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Description</label>
          <input id="formDesc_{task['id']}" value="{_html_escape(task.get('description', ''))}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
        </div>
        <div style="margin-bottom:10px;">
          <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Prompt Template</label>
          <textarea id="formPrompt_{task['id']}" rows="5" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:var(--font-mono);resize:vertical;">{_html_escape(task['prompt'])}</textarea>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
          <div>
            <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Assertion Type</label>
            <select id="formAType_{task['id']}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
              <option value="exact_match" {'selected' if a_type == 'exact_match' else ''}>Exact Match</option>
              <option value="contains" {'selected' if a_type == 'contains' else ''}>Contains Keywords</option>
              <option value="numeric_range" {'selected' if a_type == 'numeric_range' else ''}>Numeric Range</option>
              <option value="regex" {'selected' if a_type == 'regex' else ''}>Regex</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Target / Keywords</label>
            <input id="formATarget_{task['id']}" value="{_html_escape(a_target)}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
          <div>
            <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Timeout (s)</label>
            <input id="formTimeout_{task['id']}" type="number" value="{task.get('timeout', 60)}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
          </div>
          <div>
            <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Trials</label>
            <input id="formTrials_{task['id']}" type="number" value="{task.get('trials', 3)}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
          </div>
        </div>
        <div style="margin-bottom:10px;">
          <label style="font-size:11px;color:var(--fg-2);display:block;margin-bottom:4px;">Model Override <span style="font-weight:400;color:var(--muted);">(optional)</span></label>
          <select id="formModel_{task['id']}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--fg);font-family:inherit;">
            <option value="">Default (agent model)</option>
            <option value="deepseek-v4-flash" {'selected' if task.get('model') == 'deepseek-v4-flash' else ''}>DeepSeek V4 Flash</option>
            <option value="deepseek-v4-pro" {'selected' if task.get('model') == 'deepseek-v4-pro' else ''}>DeepSeek V4 Pro</option>
            <option value="ornith:latest" {'selected' if task.get('model') == 'ornith:latest' else ''}>Ornith 9B</option>
          </select>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;">
          <button onclick="closeEditor('{task['id']}')" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:6px 14px;font-size:12px;color:var(--fg-2);cursor:pointer;">Cancel</button>
          <button onclick="saveFormTask('{task['id']}')" style="background:var(--accent);color:var(--accent-on);border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;">Save</button>
        </div>
      </div>
    </div>
    """)


@router.post("/tasks/seed", response_class=JSONResponse)
async def task_seed():
    """POST /api/capability/tasks/seed — seed 9 built-in tasks if none exist."""
    runner = CanaryRunner(db=db)
    existing = runner.list_tasks()
    if existing:
        return {"ok": True, "count": 0, "message": "Tasks already exist, skipping seed"}

    builtin_tasks = [
        {
            "id": "extract-structured-data",
            "name": "Extract structured data",
            "description": "Agent extracts structured information from unstructured text",
            "prompt": "Extract the name, date, and amount from the following text:\n\nJohn Smith signed the contract on March 15, 2024. The total amount agreed was $1,234 for the quarterly retainer.",
            "assertions": [{"type": "contains", "keywords": ["John", "2024", "1,234"]}],
            "timeout": 45, "trials": 3, "built_in": True,
        },
        {
            "id": "follow-multi-step-instructions",
            "name": "Follow multi-step instructions",
            "description": "Agent follows a sequence of instructions correctly",
            "prompt": "Perform the following steps:\n1. Identify the main topic\n2. List three key points\n3. Provide a one-sentence summary\n\nText: The new Singapore rail line will connect Clementi to Jurong by 2027. Commuters expect 15-minute savings. Three new stations open next year.",
            "assertions": [{"type": "contains", "keywords": ["topic", "key", "summary"]}],
            "timeout": 60, "trials": 3, "built_in": True,
        },
        {
            "id": "arithmetic-reasoning",
            "name": "Arithmetic reasoning",
            "description": "Agent solves a multi-step arithmetic word problem",
            "prompt": "Solve: If a train leaves Station A at 60 mph and another train leaves Station B (which is 300 miles away) at 40 mph heading toward each other, how many hours until they meet?",
            "assertions": [{"type": "numeric_range", "min": 0, "max": 1000}],
            "timeout": 30, "trials": 3, "built_in": True,
        },
        {
            "id": "summarize-conversation",
            "name": "Summarize conversation",
            "description": "Agent summarizes a conversation transcript",
            "prompt": "Summarize the following conversation in 2-3 sentences:\n\nAlice: Did you finish the report?\nBob: Yes, I submitted it yesterday.\nAlice: Great. What did the client say?\nBob: They asked about the timeline and discussed the budget. We agreed to meet Friday.\nAlice: Perfect, thanks for the update.",
            "assertions": [{"type": "contains", "keywords": ["said", "asked", "discussed", "agreed", "talked", "mentioned", "conversation"], "min_match": 2}],
            "timeout": 60, "trials": 3, "built_in": True,
        },
        {
            "id": "tool-selection",
            "name": "Tool selection",
            "description": "Agent selects the correct tool for a given task",
            "prompt": "Given the available tools: search, calculate, translate, summarize\n\nWhich tool should be used for: Convert this English paragraph into French for the Brussels office.",
            "assertions": [{"type": "contains", "keywords": ["search", "calculate", "translate", "summarize", "tool"], "min_match": 1}],
            "timeout": 30, "trials": 3, "built_in": True,
        },
        {
            "id": "time-bound-response",
            "name": "Time-bound response",
            "description": "Agent responds within a time constraint",
            "prompt": "Answer in exactly one sentence: What is the capital of Japan?",
            "assertions": [{"type": "regex", "pattern": r"^[A-Za-z].*[.!?]$"}],
            "timeout": 30, "trials": 3, "built_in": True,
        },
        {
            "id": "chart-interpretation",
            "name": "Chart interpretation",
            "description": "Agent reads chart data and answers questions",
            "prompt": "Given chart data: Mon: 120 visitors, Tue: 145, Wed: 110, Thu: 165, Fri: 200, Sat: 310, Sun: 280\n\nQuestion: Which day had the highest number of visitors and what was the overall trend from Monday to Sunday?",
            "assertions": [{"type": "contains", "keywords": ["increase", "decrease", "unchanged", "higher", "lower", "change", "trend"]}],
            "timeout": 45, "trials": 3, "built_in": True,
        },
        {
            "id": "document-qa",
            "name": "Document Q&A",
            "description": "Agent answers questions based on a document",
            "prompt": "Based on the following document, answer the question:\n\nDocument: The Q3 financial report states that revenue increased 12% quarter-over-quarter, driven by enterprise subscriptions. According to the filing, cloud margins improved following the infrastructure migration.\n\nQuestion: What was the main driver of revenue growth?",
            "assertions": [{"type": "contains", "keywords": ["according", "document", "states", "based", "says", "mentions", "refers"], "min_match": 2}],
            "timeout": 60, "trials": 3, "built_in": True,
        },
        {
            "id": "code-generation",
            "name": "Code generation",
            "description": "Agent generates code from a specification",
            "prompt": "Write a Python function that: takes a list of integers and returns a new list containing only the even numbers, sorted in descending order. Return ONLY the function implementation, no explanation.",
            "assertions": [{"type": "regex", "pattern": r"(def |function |class |import |from |const |let |var |fn )"}],
            "timeout": 60, "trials": 3, "built_in": True,
        },
    ]

    count = 0
    for t in builtin_tasks:
        result = runner.create_task(t)
        if result.get("ok"):
            count += 1

    return {"ok": True, "count": count, "message": f"Seeded {count} built-in tasks"}


# ── Drift chart HTML partial ─────────────────────────────────────────────────

@router.get("/drift/chart", response_class=HTMLResponse)
async def drift_chart_partial(agent: str = Query("default")):
    """GET /api/capability/drift/chart?agent=NAME — drift chart HTML partial.

    Returns the drift hero section + chart container + summary cards + per-task table.
    The chart JS rendering is done client-side by loadDriftChart().
    """
    # Cleanup: mark runs stuck in 'running' for >30min as 'failed'
    conn = db._get_conn()
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        "UPDATE canary_runs SET status = 'failed' "
        "WHERE status = 'running' AND started_at < datetime('now', '-30 minutes')"
    )
    conn.commit()

    agent = _resolve_agent(agent)
    detector = DriftDetector(db=db)
    detail = detector.get_detail(agent)
    history = detector.get_history(agent)

    if detail is None or detail.get("drift") is None:
        # Check if we have some runs but not enough for drift detection
        points = history.get("points", [])
        if len(points) > 0 and len(points) < 7:
            return _drift_insufficient_html(agent, len(points))
        return _drift_empty_html(agent)

    drift = detail["drift"]
    current = detail.get("current", {})
    baseline = detail.get("baseline", {})
    tasks = detail.get("tasks", [])

    sev = drift.get("severity", "info")
    sev_color = _sev_color(sev)
    sev_icon_c = _sev_icon(sev)
    drift_pct = drift.get("pct", 0)
    p_val = drift.get("p_value", 1.0)
    ci = drift.get("ci", [0, 0])

    # So What insight card
    if drift_pct < 0:
        swc_tone = "alert" if abs(drift_pct) >= 5 else "watch"
        swc_mark = "!" if swc_tone == "alert" else "⚠"
        swc_lead = "DEGRADING" if swc_tone == "alert" else "WATCH"
        swc_text = f"Agent quality is {'declining significantly' if swc_tone == 'alert' else 'showing early signs of decline'}. <b>{abs(drift_pct):.1f}% drop</b> vs baseline. Check config timeline for recent changes."
    else:
        swc_tone = "insight"
        swc_mark = "i"
        swc_lead = "IMPROVING"
        swc_text = f"Agent quality is improving. <b>+{drift_pct:.1f}% rise</b> vs baseline. Recent changes may be having a positive effect."

    swc_html = f"""
    <div class="swc {swc_tone}">
      <span class="mark">{swc_mark}</span>
      <div class="body">
        <span class="lead">{swc_lead}</span>
        <div class="txt">{swc_text}</div>
      </div>
    </div>
    """

    # Build hero section
    hero_badge = f"{sev_icon_c} Drift detected · {abs(drift_pct):.1f}% {'drop' if drift_pct < 0 else 'rise'}"
    hero_headline = f"Config unchanged, quality {'dropped' if drift_pct < 0 else 'improved'} {abs(drift_pct):.1f}%"
    hero_subhead = "Same model, same prompt, same tools — but accuracy is changing."

    # Drift meta row
    baseline_date = baseline.get('date', '—') if baseline else '—'
    run_count = baseline.get('run_count', '?') if baseline else '?'
    drift_meta = f"""
    <div class="drift-meta">
      <span>📅 Baseline: {baseline_date}</span>
      <span>⏱️ {len(history.get('points', []))} data points</span>
      <span>📊 {run_count} canary runs</span>
      <span>🔬 p={p_val:.4f} {'(significant)' if p_val < 0.05 else '(not significant)'}</span>
    </div>
    """

    # Summary cards
    baseline_acc = baseline.get("accuracy", 0) if baseline else 0
    current_acc = current.get("accuracy", 0) if current else 0

    cards_html = f"""
    <div class="drift-summary">
      <div class="drift-card">
        <div class="drift-card-num green">{baseline_acc:.1f}%</div>
        <div class="drift-card-label">Baseline Accuracy</div>
        <div class="drift-card-detail">from {baseline.get('run_count', '?')} runs</div>
      </div>
      <div class="drift-card">
        <div class="drift-card-num red">{current_acc:.1f}%</div>
        <div class="drift-card-label">Current Accuracy</div>
        <div class="drift-card-detail">{current.get('date', '')}</div>
      </div>
      <div class="drift-card">
        <div class="drift-card-num red">{drift_pct:+.1f}%</div>
        <div class="drift-card-label">Drift Magnitude</div>
        <div class="drift-card-detail">p={p_val:.4f} · CI [{ci[0]:.1f}, {ci[1]:.1f}]</div>
      </div>
    </div>
    """

    # Per-task drift table
    task_rows = ""
    max_delta = max((abs(t.get("delta", 0)) for t in tasks), default=0)
    for t in tasks:
        t_sev = t.get("severity", "stable")
        t_color = _sev_color(t_sev) if t_sev != "stable" else "var(--accent)"
        delta = t.get("delta", 0)
        delta_str = f"{delta:+.1f}%" if delta is not None else "—"
        bar_pct = min(abs(delta) / max_delta * 100, 100) if max_delta > 0 and delta else 0
        bar_color = "var(--danger)" if delta and delta < 0 else "var(--accent)"

        task_rows += f"""
        <tr>
          <td class="task-name">{_html_escape(t.get('name', ''))}</td>
          <td>{t.get('baseline', '—') if t.get('baseline') else '—'}</td>
          <td>{t.get('accuracy', '—') if t.get('accuracy') else '—'}</td>
          <td class="drift-pct {'down' if delta and delta < 0 else 'up' if delta and delta > 0 else 'neutral'}">{delta_str}</td>
          <td><div class="drift-bar"><div class="drift-fill {'down' if delta and delta < 0 else 'up'}" style="width:{bar_pct:.0f}%"></div></div></td>
          <td><span style="font-size:11px;padding:2px 8px;border-radius:4px;background:{'rgba(239,68,68,0.15)' if t_sev == 'breach' else 'rgba(234,179,8,0.15)' if t_sev == 'warning' else 'rgba(34,197,94,0.15)'};color:{_sev_color(t_sev) if t_sev != 'stable' else 'var(--accent)'};">{t_sev}</span></td>
        </tr>"""

    task_table = f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:20px;">
      <div style="padding:12px 16px;font-size:13px;font-weight:600;color:var(--fg);border-bottom:1px solid var(--border);">Per-Task Drift Breakdown</div>
      <table class="drift-table">
        <thead>
          <tr>
            <th>Task</th>
            <th>Baseline</th>
            <th>Current</th>
            <th>Δ</th>
            <th>Trend</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {task_rows}
        </tbody>
      </table>
    </div>
    """

    # Chart container (rendered by JS)
    chart_data = json.dumps(history.get("points", []))
    baseline_val = history.get("baseline", {}).get("value", 0) if history.get("baseline") else 0
    drift_events_json = json.dumps(history.get("drift_events", []))

    chart_container = f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="font-size:14px;font-weight:600;color:var(--fg);">Accuracy Over Time</div>
        <div style="display:flex;gap:8px;">
          <button onclick="shareDriftView()" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--fg-2);cursor:pointer;">📸 Share</button>
          <button onclick="runCanary()" style="background:var(--accent-on);border:1px solid rgba(34,197,94,0.3);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--accent);cursor:pointer;">🔄 Re-run Canary</button>
          <button onclick="switchTab('alerts', document.querySelector('.tab-btn:nth-child(6)'))" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--fg-2);cursor:pointer;">🔔 Create Alert</button>
        </div>
      </div>
      <div class="chart-wrapper"><canvas id="driftChart"></canvas></div>
    </div>
    <script>
      window._driftChartData = {{points: {chart_data}, baseline: {baseline_val}, drift_events: {drift_events_json}}};
      if (typeof loadDriftChart === 'function') setTimeout(loadDriftChart, 100);
    </script>
    """

    # Triage path (collapsed by default)
    triage_html = """
    <details style="margin-bottom:20px;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 16px;">
      <summary style="font-size:13px;font-weight:600;color:var(--fg-2);cursor:pointer;">💡 Triage path</summary>
      <div style="margin-top:10px;font-size:13px;color:var(--fg-2);line-height:1.8;">
        <div>1. <a href="#config-timeline" style="color:var(--meta);text-decoration:none;">Check config timeline</a> → was there an intentional change?</div>
        <div>2. <a href="#" onclick="runCanary();return false;" style="color:var(--meta);text-decoration:none;">Re-run canary</a> → is the drift real or noise?</div>
        <div>3. <a href="#grid-report" style="color:var(--meta);text-decoration:none;">Run grid report</a> → which config performs best now?</div>
        <div>4. <a href="#" onclick="switchTab('alerts', document.querySelector('.tab-btn:nth-child(6)'));return false;" style="color:var(--meta);text-decoration:none;">Create alert</a> → get notified if it gets worse</div>
      </div>
    </details>
    """

    return HTMLResponse(content=f"""
    <div class="drift-hero">
      <div class="drift-badge">{hero_badge}</div>
      <div class="drift-headline">{_html_escape(hero_headline)}</div>
      <div class="drift-subhead">{hero_subhead}</div>
    </div>
    {swc_html}
    {drift_meta}
    {cards_html}
    {chart_container}
    {task_table}
    {triage_html}
    """)


def _drift_empty_html(agent: str) -> HTMLResponse:
    """Empty state when no drift data exists."""
    return HTMLResponse(content=f"""
    <div class="cap-empty">
      <div class="cap-empty-icon">🔬</div>
      <h2>No Drift Data Yet</h2>
      <p>
        Run a canary to establish a baseline. After 3+ runs with the same config, drift detection activates automatically.
      </p>
      <button onclick="runCanary()" class="btn btn-primary">Run Canary</button>
    </div>
    """)


def _drift_insufficient_html(agent: str, run_count: int) -> HTMLResponse:
    """State when some runs exist but not enough for drift detection."""
    return HTMLResponse(content=f"""
    <div class="cap-empty">
      <div class="cap-empty-icon">⚠️</div>
      <h2>Insufficient Data for Drift Detection</h2>
      <p>
        {run_count}/7 canary runs complete. Need 7+ runs with the same config to detect meaningful drift.
      </p>
      <button onclick="runCanary()" class="btn btn-primary">Run Canary</button>
    </div>
    """)


# ── Grid report HTML partial ─────────────────────────────────────────────────

@router.get("/grid/table", response_class=HTMLResponse)
async def grid_table_partial(agent: str = Query("default"), run_id: Optional[str] = Query(None)):
    """GET /api/capability/grid/table?agent=NAME&run_id=ID — grid table HTML partial."""
    agent = _resolve_agent(agent)
    conn = db._get_conn()

    if not run_id:
        row = conn.execute(
            "SELECT id FROM grid_runs WHERE agent_name = ? AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT 1",
            (agent,),
        ).fetchone()
        if not row:
            return HTMLResponse(content=_grid_empty_html())
        run_id = row["id"]

    assert run_id is not None  # guaranteed by early return above
    run = conn.execute(
        "SELECT * FROM grid_runs WHERE id = ?", (run_id,)
    ).fetchone()
    if not run:
        return HTMLResponse(content=_grid_empty_html())

    models = json.loads(run["models"]) if isinstance(run["models"], str) else run["models"]
    configs = json.loads(run["configs"]) if isinstance(run["configs"], str) else run["configs"]

    cells = conn.execute(
        "SELECT gr.task_id, ct.name as task_name, gr.model, gr.config, "
        "gr.accuracy, gr.ci_lower, gr.ci_upper, gr.cost, gr.flags, gr.hang "
        "FROM grid_results gr JOIN canary_tasks ct ON gr.task_id = ct.id "
        "WHERE gr.grid_run_id = ? ORDER BY ct.id, gr.model, gr.config",
        (run_id,),
    ).fetchall()

    if not cells:
        return HTMLResponse(content=_grid_empty_html())

    # Build cell lookup: (task_name, model, config) -> cell
    cell_map = {}
    for c in cells:
        cell_map[(c["task_name"], c["model"], c["config"])] = c

    task_names = list(dict.fromkeys(c["task_name"] for c in cells))

    # Build header
    header_html = "<tr>"
    header_html += '<th style="padding:8px 12px;text-align:left;font-size:11px;color:var(--muted);text-transform:uppercase;">Task</th>'
    for model in models:
        header_html += f'<th style="padding:8px 12px;text-align:center;font-size:11px;color:var(--fg-2);" colspan="3">{_html_escape(model)}</th>'
    header_html += "</tr>"

    # Sub-header: Acc (CI) | Flags | Cost per model
    sub_header = "<tr>"
    sub_header += '<th style="padding:4px 12px;"></th>'
    for model in models:
        sub_header += '<th style="padding:4px 4px;text-align:center;font-size:10px;color:var(--muted);font-weight:400;">Acc (CI)</th>'
        sub_header += '<th style="padding:4px 4px;text-align:center;font-size:10px;color:var(--muted);font-weight:400;">Flags</th>'
        sub_header += '<th style="padding:4px 4px;text-align:center;font-size:10px;color:var(--muted);font-weight:400;">Cost</th>'
    sub_header += "</tr>"

    # Body rows
    body_rows = ""
    for task_name in task_names:
        body_rows += f'<tr style="border-bottom:1px solid var(--border-soft);">'
        body_rows += f'<td style="padding:8px 12px;font-size:13px;color:var(--fg);">{_html_escape(task_name)}</td>'
        for model in models:
            for _ in configs:
                cell = cell_map.get((task_name, model, _))
                if cell is None:
                    body_rows += '<td style="padding:8px 4px;text-align:center;"><span class="cell-score na">—</span></td>'
                    body_rows += '<td class="cell-flags">—</td>'
                    body_rows += '<td class="cell-cost">—</td>'
                elif cell["hang"]:
                    body_rows += '<td style="padding:8px 4px;text-align:center;"><span class="cell-score na">Hang</span></td>'
                    body_rows += '<td class="cell-flags">—</td>'
                    body_rows += '<td class="cell-cost">—</td>'
                else:
                    acc = cell["accuracy"]
                    if acc is None:
                        body_rows += '<td style="padding:8px 4px;text-align:center;"><span class="cell-score na">—</span></td>'
                        body_rows += '<td class="cell-flags">—</td>'
                        body_rows += '<td class="cell-cost">—</td>'
                    else:
                        pct = acc * 100
                        score_cls = "high" if pct >= 80 else "medium" if pct >= 60 else "low"
                        ci_str = f"[{cell['ci_lower']*100:.0f}–{cell['ci_upper']*100:.0f}]" if cell["ci_lower"] is not None else ""
                        flags = json.loads(cell["flags"]) if isinstance(cell["flags"], str) else (cell["flags"] or [])
                        flag_html = "—"
                        if any("loop" in str(f).lower() for f in flags):
                            flag_html = '<span class="flag-badge flag-loop">🔄</span>'
                        elif any("unsafe" in str(f).lower() for f in flags):
                            flag_html = '<span class="flag-badge flag-unsafe">⚠️</span>'
                        elif any("shortcut" in str(f).lower() for f in flags):
                            flag_html = '<span class="flag-badge flag-shortcut">🔵</span>'
                        cost_str = f"${cell['cost']:.4f}" if cell.get("cost") else "—"
                        body_rows += f'<td style="padding:8px 4px;text-align:center;"><span class="cell-score {score_cls}">{pct:.0f}%</span><span class="cell-ci">{ci_str}</span></td>'
                        body_rows += f'<td class="cell-flags">{flag_html}</td>'
                        body_rows += f'<td class="cell-cost">{cost_str}</td>'
        body_rows += "</tr>"

    # Summary text
    summary = _generate_grid_summary(cells, models, configs)

    return HTMLResponse(content=f"""
    <div class="grid-controls">
      <div style="display:flex;align-items:center;gap:6px;">
        <label>Agent</label>
        <select class="grid-select">
          <option>{_html_escape(agent)}</option>
        </select>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <label>Config</label>
        <select class="grid-select">
          <option>All configs</option>
          {''.join(f'<option>{_html_escape(c)}</option>' for c in configs)}
        </select>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <label>Show</label>
        <select class="grid-select">
          <option>All tasks</option>
          <option>Passing only</option>
          <option>Failing only</option>
        </select>
      </div>
      <span style="flex:1;"></span>
      <button onclick="runGrid()" class="grid-select" style="background:var(--accent-on);border:1px solid rgba(34,197,94,0.3);color:var(--accent);cursor:pointer;">▶ Run Full Grid</button>
      <button onclick="exportGridCSV('{run_id}')" class="grid-select" style="cursor:pointer;">⬇ Export CSV</button>
    </div>
    <div style="overflow-x:auto;background:var(--surface);border:1px solid var(--border);border-radius:12px;">
      <table class="data-table" style="width:100%;min-width:800px;">
        <thead>{header_html}{sub_header}</thead>
        <tbody>{body_rows}</tbody>
      </table>
    </div>
    <div class="grid-footer">
      <div class="summary">
        <strong>{len(task_names)} tasks</strong> × <strong>{len(models)} models</strong> = {len(task_names) * len(models)} data points<br>
        <strong>Read by pairing:</strong> {_html_escape(summary)}
      </div>
      <button onclick="runGrid()" style="background:var(--accent);color:var(--accent-on);border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;">Run Full Grid</button>
    </div>
    """)


def _grid_empty_html() -> str:
    return """
    <div class="cap-empty">
      <div class="cap-empty-icon">📊</div>
      <h2>No Grid Runs Yet</h2>
      <p>
        Run a grid to compare models and configs side by side.
      </p>
      <button onclick="runGrid()" class="btn btn-primary">Run Full Grid</button>
    </div>
    """


def _generate_grid_summary(cells: list, models: list, configs: list) -> str:
    """Generate a human-readable summary of grid results."""
    if not cells:
        return "No data to compare."

    # Find best model×config by accuracy
    best = max(cells, key=lambda c: c["accuracy"] if c["accuracy"] is not None else 0)
    best_model = best["model"]
    best_config = best["config"]
    best_acc = best["accuracy"] * 100 if best["accuracy"] else 0

    # Find cheapest
    cheapest = min(cells, key=lambda c: c["cost"] if c["cost"] else 999)
    cheap_model = cheapest["model"]
    cheap_config = cheapest["config"]
    cheap_cost = cheapest["cost"] or 0

    # Compare best vs cheapest
    if best_model == cheap_model and best_config == cheap_config:
        return f"{best_model} × {best_config} leads on both accuracy ({best_acc:.0f}%) and cost (${cheap_cost:.4f})."

    return f"{best_model} × {best_config} wins on raw accuracy ({best_acc:.0f}%). {cheap_model} × {cheap_config} is cheapest at ${cheap_cost:.4f}. Model and harness interact — read grid by pairing, not isolated components."


# ── Timeline HTML partial ────────────────────────────────────────────────────

@router.get("/timeline/events", response_class=HTMLResponse)
async def timeline_events_partial(agent: str = Query("default")):
    """GET /api/capability/timeline/events?agent=NAME — timeline HTML partial."""
    agent = _resolve_agent(agent)
    conn = db._get_conn()

    # Get config snapshots
    snapshots = conn.execute(
        "SELECT change_type, description, git_commit, accuracy, segment, created_at "
        "FROM config_snapshots WHERE agent_name = ? ORDER BY created_at DESC LIMIT 30",
        (agent,),
    ).fetchall()

    # Get drift events
    drift_events = conn.execute(
        "SELECT drift_pct, severity, created_at FROM drift_events "
        "WHERE agent_name = ? ORDER BY created_at DESC LIMIT 20",
        (agent,),
    ).fetchall()

    # Get segments
    segments = {}
    seg_rows = conn.execute(
        "SELECT DISTINCT config_hash, config_label, segment FROM config_snapshots "
        "WHERE agent_name = ? AND segment IS NOT NULL ORDER BY created_at",
        (agent,),
    ).fetchall()
    for r in seg_rows:
        label = r["config_label"] or r["config_hash"][:12]
        segments[r["segment"]] = label

    # Build event list
    events = []
    for s in snapshots:
        events.append({
            "date": s["created_at"],
            "type": s["change_type"],
            "title": s["change_type"].replace("_", " ").title(),
            "description": s["description"] or "",
            "segment": s["segment"],
            "accuracy": s["accuracy"],
            "git_commit": s["git_commit"],
        })
    for d in drift_events:
        events.append({
            "date": d["created_at"],
            "type": "drift",
            "title": f"Drift {d['severity'].title()}",
            "description": f"Quality dropped {d['drift_pct']:+.1f}%",
            "severity": d["severity"],
            "segment": None,
            "accuracy": None,
        })

    events.sort(key=lambda x: x["date"], reverse=True)

    if not events:
        return HTMLResponse(content=_timeline_empty_html())

    # Segment colors (always defined)
    seg_colors = ["#22c55e", "#3b82f6", "#eab308", "#ec4899", "#14b8a6"]

    # Segment legend
    seg_legend = ""
    if segments:
        seg_items = []
        for i, (seg, label) in enumerate(segments.items()):
            seg_class = ["seg-a", "seg-b", "seg-c", "seg-d", "seg-e"][i % 5]
            seg_items.append(f'<span><span class="swatch {seg_class}"></span> {seg}: {_html_escape(label)}</span>')
        seg_legend = f'<div class="baseline-legend">{"".join(seg_items)}</div>'

    # Event cards
    dot_colors = {
        "baseline": "green",
        "model_switch": "green",
        "prompt_update": "yellow",
        "tool_update": "blue",
        "drift": "red",
    }

    event_cards = ""
    for e in events:
        dot_class = dot_colors.get(e["type"], "green")
        date_str = e["date"][:19] if e["date"] else ""
        seg_badge = ""
        if e.get("segment"):
            seg_class = ["seg-a", "seg-b", "seg-c", "seg-d", "seg-e"][min(ord(e["segment"]) - ord("A"), 4)]
            seg_badge = f'<span class="baseline-badge {seg_class}">Segment {e["segment"]}</span>'

        acc_str = f' · {e["accuracy"]*100:.0f}%' if e.get("accuracy") else ""
        git_str = f' · <code>{e["git_commit"][:7]}</code>' if e.get("git_commit") else ""

        event_cards += f"""
        <div class="timeline-event">
          <div class="timeline-date"><div class="date">{date_str[5:10]}</div><div class="time">{date_str[11:16]}</div></div>
          <div class="timeline-dot {dot_class}"></div>
          <div class="timeline-card">
            <div class="timeline-card-header">
              <div class="timeline-card-title">{_html_escape(e['title'])} <span class="change-type">· {e['type'].replace('_', ' ')}</span></div>
              {seg_badge}
            </div>
            <div class="timeline-card-desc">{_html_escape(e['description'])}{acc_str}{git_str}</div>
          </div>
        </div>"""

    return HTMLResponse(content=f"""
    <div class="agent-selector">
      <span style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;padding:4px 0;margin-right:4px;">Agent:</span>
      <button onclick="switchTimelineAgent('{agent}')" class="agent-pill active">{_html_escape(agent)}</button>
    </div>
    {seg_legend}
    <div class="timeline" style="max-width:600px;">
      {event_cards}
    </div>
    """)


def _timeline_empty_html() -> str:
    return """
    <div class="cap-empty">
      <div class="cap-empty-icon">📅</div>
      <h2>No Config Changes Yet</h2>
      <p>
        Changes appear here when SOUL.md or config is modified.
      </p>
    </div>
    """


# ── Capability page HTML partial ──────────────────────────────────────────────


@router.get("/page", response_class=HTMLResponse)
async def capability_page():
    """GET /api/capability/page — full capability page HTML partial."""
    agent = _resolve_agent("default")

    return HTMLResponse(content=f"""
    <div style="display:flex;flex-direction:column;gap:20px;">
      <!-- Drift section -->
      <section>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <h2 style="font-size:16px;font-weight:600;color:var(--fg);">📉 Drift Monitor</h2>
          <div style="display:flex;gap:8px;">
            <button onclick="runCanary()" style="background:var(--accent-on);border:1px solid rgba(34,197,94,0.3);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--accent);cursor:pointer;">🔄 Re-run Canary</button>
            <button onclick="runGrid()" style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--fg-2);cursor:pointer;">📊 Run Grid</button>
          </div>
        </div>
        <div id="driftChartContainer" hx-get="/api/capability/drift/chart" hx-trigger="load" hx-swap="innerHTML">
          <div style="color:var(--muted);font-size:12px;">Loading drift data…</div>
        </div>
      </section>

      <!-- Grid section -->
      <section>
        <h2 style="font-size:16px;font-weight:600;color:var(--fg);margin-bottom:12px;">📊 Grid Report</h2>
        <div id="gridTableContainer" hx-get="/api/capability/grid/table" hx-trigger="load" hx-swap="innerHTML">
          <div style="color:var(--muted);font-size:12px;">Loading grid data…</div>
        </div>
      </section>

      <!-- Tasks section -->
      <section>
        <h2 style="font-size:16px;font-weight:600;color:var(--fg);margin-bottom:12px;">📋 Tasks</h2>
        <div id="taskListContainer" hx-get="/api/capability/tasks/list" hx-trigger="load" hx-swap="innerHTML">
          <div style="color:var(--muted);font-size:12px;">Loading tasks…</div>
        </div>
      </section>
    </div>

    <script>
    function runCanary() {{
      var agent = '{agent}';
      fetch('/api/capability/canary/run?agent=' + encodeURIComponent(agent), {{method:'POST'}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          if (d.ok) {{
            showToast('Canary started for ' + agent);
            var poll = setInterval(function() {{
              fetch('/api/capability/canary/status?agent=' + encodeURIComponent(agent))
                .then(function(r) {{ return r.json(); }})
                .then(function(s) {{
                  if (!s.running && s.completed) {{
                    clearInterval(poll);
                    showToast('Canary complete — refreshing');
                    htmx.ajax('GET', '/api/capability/drift/chart', {{target: '#driftChartContainer', swap: 'innerHTML'}});
                    htmx.ajax('GET', '/api/capability/grid/table', {{target: '#gridTableContainer', swap: 'innerHTML'}});
                    htmx.ajax('GET', '/api/capability/tasks/list', {{target: '#taskListContainer', swap: 'innerHTML'}});
                  }}
                }});
            }}, 5000);
          }}
        }})
        .catch(function(e) {{ showToast('Canary failed: ' + e.message); }});
    }}

    function runGrid() {{
      var agent = '{agent}';
      fetch('/api/capability/grid/run?agent=' + encodeURIComponent(agent), {{method:'POST'}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          if (d.ok) {{
            showToast('Grid started for ' + agent);
            var poll = setInterval(function() {{
              fetch('/api/capability/grid?agent=' + encodeURIComponent(agent))
                .then(function(r) {{ return r.json(); }})
                .then(function(g) {{
                  if (g.cells && g.cells.length > 0) {{
                    clearInterval(poll);
                    showToast('Grid complete — refreshing');
                    htmx.ajax('GET', '/api/capability/grid/table', {{target: '#gridTableContainer', swap: 'innerHTML'}});
                  }}
                }});
            }}, 10000);
          }}
        }})
        .catch(function(e) {{ showToast('Grid failed: ' + e.message); }});
    }}

    function showToast(msg) {{
      var existing = document.getElementById('capToast');
      if (existing) existing.remove();
      var t = document.createElement('div');
      t.id = 'capToast';
      t.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 16px;color:#f8fafc;font-size:13px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
      t.textContent = msg;
      document.body.appendChild(t);
      setTimeout(function() {{ t.remove(); }}, 3000);
    }}

    function runCanaryForAgent(agent) {{
      fetch('/api/capability/canary/run?agent=' + encodeURIComponent(agent), {{method:'POST'}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{ if (d.ok) showToast('Canary started for ' + agent); }});
    }}

    function showNewTaskForm() {{ showToast('Task editor coming soon'); }}
    function editTask(id) {{ showToast('Task editor coming soon'); }}
    function deleteTask(id) {{
      if (!confirm('Delete this task?')) return;
      fetch('/api/capability/tasks/' + id, {{method:'DELETE'}})
        .then(function() {{ htmx.ajax('GET', '/api/capability/tasks/list', {{target: '#taskListContainer', swap: 'innerHTML'}}); }});
    }}
    function duplicateTask(id) {{ showToast('Duplicate coming soon'); }}
    function switchEditorMode(id, mode) {{}}
    function saveYamlTask(id) {{ showToast('Save coming soon'); }}
    function saveFormTask(id) {{ showToast('Save coming soon'); }}
    function closeEditor(id) {{}}
    function shareDriftView() {{ showToast('Share coming soon'); }}
    </script>
    """)
