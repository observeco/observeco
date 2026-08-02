"""Capability monitoring API routes — drift, grid, timeline, tasks.

obs-spec-052/053/054/055: Dashboard API endpoints for the capability monitoring layer.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3 as _sqlite3
import threading
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from observeco.capability.canary import CanaryRunner
from observeco.capability.drift import DriftDetector
from observeco.db import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/capability", tags=["capability"])
db = Database()

_grid_run_lock = threading.Lock()
_canary_run_lock = threading.Lock()
_last_grid_error: Optional[str] = None


# ── History-assisted task generation (obs-spec-060) ──────────────────────────

_HERMES_STATE_DB = os.path.expanduser("~/.hermes/state.db")


@router.get("/canary/pending-tasks", response_class=JSONResponse)
async def canary_pending_tasks():
    """GET /api/capability/canary/pending-tasks — list LLM-proposed drafts."""
    conn = db._get_conn()
    rows = conn.execute(
        "SELECT id, name, description, prompt, assertions, category, difficulty, "
        "source_session, llm_judge_unavailable, created_at "
        "FROM canary_task_drafts ORDER BY created_at DESC"
    ).fetchall()
    drafts = []
    for r in rows:
        d = dict(r)
        try:
            d["assertions"] = json.loads(d["assertions"]) if isinstance(d["assertions"], str) else d["assertions"]
        except Exception:
            d["assertions"] = []
        drafts.append(d)
    return {"ok": True, "drafts": drafts}


@router.post("/canary/pending-tasks/approve", response_class=JSONResponse)
async def canary_approve_draft(payload: dict):
    """POST /api/capability/canary/pending-tasks/approve — move a draft to canary_tasks."""
    task_id = payload.get("task_id")
    if not task_id:
        return {"ok": False, "error": "task_id required"}
    conn = db._get_conn()
    row = conn.execute(
        "SELECT id, name, description, prompt, assertions, category, difficulty, source_session "
        "FROM canary_task_drafts WHERE id = ?", (task_id,)
    ).fetchone()
    if not row:
        return {"ok": False, "error": "draft not found"}
    draft = dict(row)
    runner = CanaryRunner(db=db)
    res = runner.create_task({
        "id": draft["id"],
        "name": draft["name"],
        "description": draft["description"],
        "prompt": draft["prompt"],
        "assertions": json.loads(draft["assertions"]) if isinstance(draft["assertions"], str) else draft["assertions"],
        "category": draft["category"],
        "difficulty": draft["difficulty"],
        "trials": 2,
        "timeout": 60,
    })
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error", "create_task failed")}
    # Persist source_session on the now-active task (create_task hardcodes built_in=0).
    # Use db._write() (retry-on-lock) — the watch daemon writes pulse.db constantly.
    try:
        db._write(
            "UPDATE canary_tasks SET source_session = ? WHERE id = ?",
            (draft["source_session"], draft["id"]),
        )
        db._write("DELETE FROM canary_task_drafts WHERE id = ?", (task_id,))
    except _sqlite3.OperationalError:
        logger.warning("canary draft persist failed (db locked): %s", task_id)
    return {"ok": True, "task_id": draft["id"]}


@router.post("/canary/pending-tasks/reject", response_class=JSONResponse)
async def canary_reject_draft(payload: dict):
    """POST /api/capability/canary/pending-tasks/reject — delete a draft."""
    task_id = payload.get("task_id")
    if not task_id:
        return {"ok": False, "error": "task_id required"}
    try:
        db._write("DELETE FROM canary_task_drafts WHERE id = ?", (task_id,))
    except _sqlite3.OperationalError:
        logger.warning("canary draft reject failed (db locked): %s", task_id)
    return {"ok": True}


@router.get("/canary/source-session", response_class=JSONResponse)
async def canary_source_session(session_id: str = Query("")):
    """GET /api/capability/canary/source-session?session_id=X

    Returns the first 5 messages from the source Hermes session for review context.
    Graceful on missing session (deleted) or DB error.
    """
    if not session_id:
        return {"ok": False, "error": "session_id required"}
    if not os.path.exists(_HERMES_STATE_DB):
        return {"ok": False, "error": "Hermes state.db not found", "deleted": False}
    try:
        sconn = _sqlite3.connect(f"file:{_HERMES_STATE_DB}?mode=ro", uri=True)
        sconn.row_factory = _sqlite3.Row
        rows = sconn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT 5",
            (session_id,),
        ).fetchall()
        sconn.close()
        if not rows:
            return {"ok": True, "deleted": True, "messages": []}
        return {"ok": True, "deleted": False, "messages": [{"role": r["role"], "content": (r["content"] or "")[:1000]} for r in rows]}
    except _sqlite3.Error as exc:
        return {"ok": False, "error": f"database error: {exc}", "deleted": False}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))


def _sev_color(severity: str) -> str:
    return {"breach": "var(--danger)", "warning": "var(--warn)", "info": "var(--meta)"}.get(severity, "var(--muted)")


def _sev_icon(severity: str) -> str:
    return {"breach": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")


def _infer_category(name: str) -> str:
    """ponytail: heuristic category inference from task name.
    Upgrade path: require category on task creation (migration 57 added the column)."""
    n = name.lower()
    if any(kw in n for kw in ["code", "program", "function", "debug", "refactor", "generate"]):
        return "coding"
    if any(kw in n for kw in ["extract", "parse", "read", "document", "pdf", "json", "csv", "table"]):
        return "extraction"
    if any(kw in n for kw in ["tool", "api", "search", "browse", "call", "select"]):
        return "tool_use"
    if any(kw in n for kw in ["follow", "instruction", "step", "time-bound", "multi-step", "bind"]):
        return "instruction_following"
    return "reasoning"


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


def _list_agents() -> list[str]:
    """Return all known agent names from config_snapshots + config."""
    conn = db._get_conn()
    rows = conn.execute(
        "SELECT DISTINCT agent_name FROM config_snapshots ORDER BY agent_name"
    ).fetchall()
    agents = [r["agent_name"] for r in rows]
    if not agents:
        from observeco.config import load_config
        config = load_config()
        agents = [a.name for a in config.agents] if config.agents else []
    return agents or ["default"]


def _validate_agent_param(agent: str) -> Optional[str]:
    """Validate the agent query param. Returns an error string or None if valid."""
    if not agent:
        return "agent parameter required"
    if len(agent) > 64:
        return "agent name too long (max 64 chars)"
    if agent == "default":
        return None
    if agent not in _list_agents():
        return f"unknown agent: {agent}"
    return None

@router.post("/grid/run", response_class=JSONResponse)
async def grid_run_from_dashboard(
    agent: str = Query("default"),
    models: Optional[str] = Query(None, description="Comma-separated model specs"),
    configs: Optional[str] = Query(None, description="Comma-separated agent profiles"),
):
    """POST /api/capability/grid/run?agent=NAME&models=model1,model2 — run full grid from dashboard.

    Spawns a subprocess so the grid run survives server restarts and avoids
    SQLite writer contention in the web server's process. Runs can take 5-10
    minutes. The grid table will show 'running' status and poll for results.
    """
    err = _validate_agent_param(agent)
    if err:
        return {"ok": False, "message": err}

    if not _grid_run_lock.acquire(blocking=False):
        return {"ok": False, "message": f"Grid already running for {agent}"}
    try:
        import subprocess
        import sys

        # Clean up stale runs (Hermes adapter is slower — allow 60 min)
        try:
            db._write(
                "UPDATE grid_runs SET status='failed' WHERE agent_name=? AND status='running'"
                " AND started_at < datetime('now', '-60 minutes')",
                (agent,),
            )
        except Exception:
            pass

        # Spawn subprocess
        cmd = [sys.executable, "-m", "observeco.cli", "grid", "run",
               "--agent", agent, "--trials", "1"]
        if models:
            cmd += ["--models", models]
        if configs:
            cmd += ["--configs", configs]
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"ok": True, "message": f"Grid started for {agent} — this can take up to 10 minutes, results will appear automatically"}
    except Exception:
        logger.exception("Failed to start grid for %s", agent)
        return {"ok": False, "message": "Failed to start grid"}
    finally:
        _grid_run_lock.release()


@router.post("/canary/run", response_class=JSONResponse)
async def canary_run_from_fleet(agent: str = Query("default"), tasks: Optional[str] = Query(None)):
    """POST /api/capability/canary/run?agent=NAME&tasks=id1,id2 — run canary async, return immediately.

    Runs the benchmark in a SEPARATE PROCESS (not a thread) to avoid SQLite
    writer contention inside the web server's own process. The status endpoint
    polls canary_runs/canary_results, so no IPC is needed — the subprocess
    writes directly to the shared DB via WAL.
    """
    err = _validate_agent_param(agent)
    if err:
        return {"ok": False, "message": err}
    # In-process lock prevents two simultaneous spawn attempts racing each other
    if not _canary_run_lock.acquire(blocking=False):
        return {"ok": False, "message": f"Canary already running for {agent}"}
    try:
        import subprocess
        import sys

        # Best-effort cleanup: mark runs stuck in 'running' for >30min as 'failed'
        try:
            db._write(
                "UPDATE canary_runs SET status = 'failed' "
                "WHERE status = 'running' AND started_at < datetime('now', '-30 minutes')",
                (),
            )
        except _sqlite3.OperationalError:
            pass  # cleanup is best-effort

        # Concurrent run guard: don't spawn a second canary while one is running.
        # Insert a synchronous 'running' placeholder BEFORE spawning so the DB
        # guard catches subsequent attempts immediately (the subprocess writes
        # its own row asynchronously, which would leave a race window).
        try:
            guard_conn = db._get_conn()
            running = guard_conn.execute(
                "SELECT COUNT(*) as c FROM canary_runs WHERE agent_name = ? AND status = 'running'",
                (agent,),
            ).fetchone()["c"]
            if running > 0:
                _canary_run_lock.release()
                return {"ok": False, "message": f"Canary already running for {agent}"}
            # Insert placeholder 'running' row synchronously to claim the slot
            import uuid
            db._write(
                "INSERT INTO canary_runs (id, agent_name, config_hash, status, started_at, total_tasks) "
                "VALUES (?, ?, 'pending', 'running', datetime('now'), 0)",
                (f"placeholder-{uuid.uuid4().hex[:8]}", agent),
            )
        except _sqlite3.OperationalError:
            pass  # fail open: if we can't check, allow the run

        # Build CLI invocation: spawn a separate process running the same
        # interpreter that launched the dashboard (robust against venv/PATH).
        # Uses --direct to bypass the agent harness — DirectModelAdapter calls
        # the model API directly (faster, no profile loading, avoids broken
        # profile providers like xiaomi).
        cmd = [sys.executable, "-m", "observeco.cli", "canary", "run", "--agent", agent, "--trials", "1", "--direct"]
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
        _canary_run_lock.release()
        return {"ok": True, "message": f"Canary started for {agent}"}
    except Exception:
        _canary_run_lock.release()
        logger.exception("Failed to start canary for %s", agent)
        return {"ok": False, "message": "Failed to start canary"}


@router.get("/canary/judge-reasoning", response_class=JSONResponse)
async def judge_reasoning(task_id: str = Query("")):
    """GET /api/capability/canary/judge-reasoning?task_id=X
    Returns the latest LLM judge results for a task, with per-assertion scores and reasoning.
    """
    if not task_id:
        return {"assertions": []}
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
        return {"assertions": [], "error": "No LLM judge data available for this task"}
    assertions_list = []
    try:
        json.loads(task["assertions"]) if isinstance(task["assertions"], str) else task["assertions"]
    except Exception:
        logger.warning("Malformed assertions JSON for task %s", task_id)
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
        # Skip the db._write() cleanup — it takes the write lock and blocks
        # when the watch daemon is writing. The watch daemon already cleans
        # up stale runs. This endpoint is read-only.
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
            "SUM(CASE WHEN status = 'provider_error' THEN 1 ELSE 0 END) as provider_error_count, "
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
            "provider_error_count": live["provider_error_count"] or 0 if live else 0,
            "total_tasks": latest["total_tasks"],
        }
    except Exception:
        logger.exception("canary_status failed for %s", agent)
        return {"running": False, "completed": False, "error": "Could not check canary status", "pass_count": 0, "fail_count": 0, "hang_count": 0, "total_tasks": 0}


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

    # Resolve latest run if not specified (prefer most recent by recency, any status,
    # so the UI poll can see 'running'/'failed' and stop instead of hanging)
    if not run_id:
        row = conn.execute(
            "SELECT id, status FROM grid_runs WHERE agent_name = ? "
            "ORDER BY started_at DESC LIMIT 1",
            (agent,),
        ).fetchone()
        if not row:
            return {"agent": agent, "run_id": None, "status": None, "error": None, "cells": [], "models": [], "configs": [], "tasks": []}
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
        "status": run["status"] if run and "status" in run.keys() else None,
        "error": (_last_grid_error if (run and run["status"] == "failed") else None),
        "date": run["started_at"][:10] if run and run["started_at"] else "",
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

        status_dot_class = ("green" if last and last["status"] == "pass"
                           else "yellow" if last and last["status"] == "fail"
                           else "red" if last and last["status"] == "provider_error"
                           else "gray" if last and last["status"] == "hang"
                           else "")
        status_label = (last["status"] if last else "none")
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
              <span style="font-size:10px;color:var(--muted);margin-left:4px;">{status_label}</span>
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


@router.get("/pending-tasks/html", response_class=HTMLResponse)
async def pending_tasks_partial():
    """GET /api/capability/pending-tasks/html — pending-review drafts list (obs-spec-060 §6.1)."""
    conn = db._get_conn()
    rows = conn.execute(
        "SELECT id, name, description, prompt, assertions, category, difficulty, "
        "source_session, llm_judge_unavailable, created_at "
        "FROM canary_task_drafts ORDER BY created_at DESC"
    ).fetchall()

    if not rows:
        return HTMLResponse(content="""
        <div class="cap-empty">
          <div class="cap-empty-icon">📭</div>
          <h2>No Pending Task Drafts</h2>
          <p>
            Mine your agent's conversation history to propose canary tasks.<br>
            Run <code>observeco canary suggest-tasks --limit 10</code> in your terminal.
          </p>
        </div>
        """)

    items = ""
    for r in rows:
        d = dict(r)
        try:
            assertions = json.loads(d["assertions"]) if isinstance(d["assertions"], str) else d["assertions"]
            a_types = ", ".join(a.get("type", "?") for a in (assertions or [])) or "none"
        except Exception:
            a_types = "?"

        cat = d.get("category") or ""
        diff = d.get("difficulty") or "medium"
        cat_colors = {
            "reasoning": "var(--accent)", "coding": "var(--success)",
            "extraction": "var(--purple)", "tool_use": "var(--warn)",
            "instructions": "var(--info)", "operations": "var(--info)", "safety": "var(--danger)",
        }
        cat_color = cat_colors.get(cat, "var(--fg-2)")
        diff_color = {"easy": "var(--success)", "medium": "var(--warn)", "hard": "var(--danger)"}.get(diff, "var(--fg-2)")
        cat_badge = f"""<span class="badge" style="background:{cat_color}15;color:{cat_color};border:1px solid {cat_color}40;font-size:10px;padding:0 6px;border-radius:4px;">{cat or '—'}</span>"""
        cat_badge += f"""<span class="badge" style="background:{diff_color}15;color:{diff_color};font-size:9px;padding:0 4px;border-radius:3px;margin-left:4px;">{diff}</span>"""

        unavailable_badge = (
            '<span style="font-size:10px;color:var(--warn);border:1px solid var(--warn)40;'
            'background:var(--warn)15;padding:1px 6px;border-radius:4px;margin-left:6px;">'
            '⚠️ LLM judge unavailable — review assertions manually</span>'
            if d.get("llm_judge_unavailable") else ""
        )

        items += f"""
        <div class="task-item" data-draft-id="{_html_escape(d['id'])}">
          <div class="task-row">
            <div class="task-item-info">
              <span class="status-dot"></span>
              <div>
                <div class="task-item-name">{_html_escape(d['name'])}{unavailable_badge}</div>
                <div class="task-item-meta">{cat_badge} {_html_escape(a_types)} · source: {_html_escape(str(d.get('source_session',''))[:16])}…</div>
                <div class="task-item-agents" style="font-size:11px;color:var(--fg-3);margin-top:2px;">📝 {_html_escape((d.get('prompt') or '')[:100])}{'…' if len(d.get('prompt') or '') > 100 else ''}</div>
              </div>
            </div>
            <div class="task-item-actions">
              <button onclick="viewSourceSession('{_html_escape(str(d.get('source_session','')))}')" class="btn btn-sm btn-outline" title="View original conversation">👁 Source</button>
              <button onclick="approveDraft('{_html_escape(d['id'])}')" class="btn btn-sm btn-primary" style="background:var(--success);color:#fff;">✓ Approve</button>
              <button onclick="rejectDraft('{_html_escape(d['id'])}')" class="btn-icon" title="Reject">✕</button>
            </div>
          </div>
        </div>"""

    return HTMLResponse(content=f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;">
      <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);">
        <span style="font-size:13px;font-weight:600;color:var(--fg);">Pending Review ({len(rows)})</span>
        <span style="font-size:11px;color:var(--fg-3);">LLM-proposed · review &amp; approve</span>
      </div>
      {items}
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
              <option value="llm_judge" {'selected' if a_type == 'llm_judge' else ''}>LLM-as-a-Verifier (1-20, K=3, logprob)</option>
              <option value="json_schema" {'selected' if a_type == 'json_schema' else ''}>JSON Schema</option>
              <option value="ordering" {'selected' if a_type == 'ordering' else ''}>Ordering</option>
              <option value="tool_call_validation" {'selected' if a_type == 'tool_call_validation' else ''}>Tool Call Validation</option>
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
            "prompt": "Perform the following steps:\n1. Identify the main topic\n2. List three key points\n3. Provide a one-sentence summary\n\nText: The new metro line will connect the city center to the airport by 2027. Commuters expect 15-minute savings. Three new stations open next year.",
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


# ── Per-task drift history ──────────────────────────────────────────────────

@router.get("/drift/per-task-history", response_class=JSONResponse)
async def per_task_drift_history(agent: str = Query("default"), days: int = Query(21)):
    """GET /api/capability/drift/per-task-history?agent=NAME&days=21

    Returns per-task accuracy time series for the multi-line per-task drift chart.
    Each task gets baseline/current/delta/severity computed from its own history.
    """
    agent = _resolve_agent(agent)
    try:
        conn = db._get_conn()

        runs = conn.execute(
            "SELECT id, started_at, COALESCE(total_cost, 0.0) as total_cost, "
            "COALESCE(total_tokens, 0) as total_tokens FROM canary_runs "
            "WHERE agent_name = ? AND status = 'completed' "
            "AND started_at >= datetime('now', ? || ' days') "
            "ORDER BY started_at ASC LIMIT 100",
            (agent, f'-{days}'),
        ).fetchall()

        if not runs:
            return {"tasks": []}

        run_ids = [r["id"] for r in runs]
        run_dates = {r["id"]: r["started_at"][:10] for r in runs}
        placeholders = ",".join(["?"] * len(run_ids))

        results = conn.execute(
            f"SELECT cr.task_id, cr.run_id, cr.accuracy, cr.status, "
            f"ct.name, ct.category, ct.difficulty "
            f"FROM canary_results cr JOIN canary_tasks ct ON cr.task_id = ct.id "
            f"WHERE cr.run_id IN ({placeholders}) "
            f"ORDER BY cr.run_id, ct.id",
            run_ids,
        ).fetchall()

        # Group points by task
        tasks_map: dict[str, dict] = {}
        for row in results:
            tid = row["task_id"]
            if tid not in tasks_map:
                tasks_map[tid] = {
                    "task_id": tid,
                    "name": row["name"],
                    "category": row["category"] or _infer_category(row["name"]),
                    "difficulty": row["difficulty"] or "medium",
                    "points": [],
                }
            acc = row["accuracy"]
            if acc is not None and row["status"] != "hang":
                tasks_map[tid]["points"].append({
                    "date": run_dates.get(row["run_id"], ""),
                    "accuracy": round(acc * 100, 1),
                })

        # Compute per-task baseline, current, delta, severity
        for tid, t in tasks_map.items():
            pts = t["points"]
            if len(pts) >= 2:
                mid = max(len(pts) // 2, 1)
                bl_pts = pts[:mid]
                cur_pts = pts[mid:]
                t["baseline"] = round(sum(p["accuracy"] for p in bl_pts) / len(bl_pts), 1)
                t["current"] = round(sum(p["accuracy"] for p in cur_pts) / len(cur_pts), 1)
                t["delta"] = round(t["current"] - t["baseline"], 1)
            elif len(pts) == 1:
                t["baseline"] = pts[0]["accuracy"]
                t["current"] = pts[0]["accuracy"]
                t["delta"] = 0.0
            else:
                t["baseline"] = 0.0
                t["current"] = 0.0
                t["delta"] = 0.0

            abs_d = abs(t["delta"])
            if abs_d >= 5.0:
                t["severity"] = "breach"
            elif abs_d >= 3.0:
                t["severity"] = "warning"
            else:
                t["severity"] = "stable"

        return {"tasks": list(tasks_map.values()),
                "run_meta": {r["id"]: {"date": r["started_at"][:10], "cost": r["total_cost"], "tokens": r["total_tokens"]} for r in runs}}

    except Exception:
        logger.exception("per_task_drift_history failed for %s", agent)
        return {"tasks": [], "error": "Failed to load per-task history"}


# ── Drift chart HTML partial ─────────────────────────────────────────────────

@router.get("/drift/chart", response_class=HTMLResponse)
async def drift_chart_partial(agent: str = Query("default")):
    """GET /api/capability/drift/chart?agent=NAME — drift chart HTML partial.

    Returns the drift hero section + chart container + summary cards + per-task table.
    The chart JS rendering is done client-side by loadDriftChart().
    """
    # Cleanup: mark runs stuck in 'running' for >30min as 'failed'.
    # Use db._write() (retry-on-lock) instead of a raw execute+commit — the watch
    # daemon writes to the same DB constantly, so a bare UPDATE collides and 500s.
    try:
        db._write(
            "UPDATE canary_runs SET status = 'failed' "
            "WHERE status = 'running' AND started_at < datetime('now', '-30 minutes')",
            (),
        )
    except _sqlite3.OperationalError:
        pass  # non-critical cleanup; skip if the DB is locked right now

    agent = _resolve_agent(agent)
    try:
        detector = DriftDetector(db=db)
        detail = detector.get_detail(agent)
        history = detector.get_history(agent)
    except Exception:
        logger.exception("drift_chart_partial failed for %s", agent)
        return HTMLResponse(content=_drift_error_html(agent))

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
    _sev_color(sev)
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
        _sev_color(t_sev) if t_sev != "stable" else "var(--accent)"
        delta = t.get("delta", 0)
        delta_str = f"{delta:+.1f}%" if delta is not None else "—"
        bar_pct = min(abs(delta) / max_delta * 100, 100) if max_delta > 0 and delta else 0

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
      <div class="chart-wrapper"><canvas id="driftChart" data-chart='{chart_data}' data-baseline='{baseline_val}' data-events='{drift_events_json}'></canvas></div>
    </div>"""

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


def _drift_error_html(agent: str) -> HTMLResponse:
    return HTMLResponse(content=f"""
    <div class="cap-empty">
      <div class="cap-empty-icon">⚠️</div>
      <h2>Could not load drift data</h2>
      <p>An error occurred while computing drift for {_html_escape(agent)}. Try again.</p>
      <button onclick="loadDriftChart()" class="btn btn-primary">Retry</button>
    </div>
    """)


def _drift_empty_html(agent: str) -> HTMLResponse:
    """Empty state when no drift data exists."""
    return HTMLResponse(content="""
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


@router.get("/grid/options", response_class=JSONResponse)
async def grid_options():
    """GET /api/capability/grid/options — available models (grouped by provider),
    profiles, and task count for building the grid controls.

    Generic: reads from hermes config, not hardcoded. The UI uses this to
    render provider-grouped model selectors, profile checkboxes, and a
    live cell-count estimate before a run.
    """
    from observeco.capability.model_config import (
        get_default_grid_models,
        get_default_grid_profiles,
        list_runnable_cloud_providers,
    )
    from observeco.db import Database as _DB

    providers = list_runnable_cloud_providers()
    default_models = set(get_default_grid_models())
    model_groups = []
    for pname, info in providers.items():
        model_groups.append({
            "provider": pname,
            "default_model": info["default_model"],
            "models": [
                {
                    "spec": m,
                    "name": m.split("/")[-1],
                    "is_default": m in default_models,
                }
                for m in info["models"]
            ],
        })

    profiles = get_default_grid_profiles()

    task_count = 0
    try:
        db = _DB()
        conn = db._get_conn()
        task_count = conn.execute(
            "SELECT COUNT(*) as c FROM canary_tasks WHERE built_in = 1"
        ).fetchone()["c"]
    except Exception:
        task_count = 0

    return {
        "model_groups": model_groups,
        "profiles": profiles,
        "default_models": list(default_models),
        "task_count": task_count,
    }


# ── Grid report HTML partial ─────────────────────────────────────────────────

@router.get("/grid/table", response_class=HTMLResponse)
async def grid_table_partial(agent: str = Query("default"), run_id: Optional[str] = Query(None)):
    """GET /api/capability/grid/table?agent=NAME&run_id=ID — grid table HTML partial."""
    agent = _resolve_agent(agent)
    conn = db._get_conn()

    if not run_id:
        # Check for a running run first (show progress indicator)
        running_row = conn.execute(
            "SELECT id, started_at FROM grid_runs WHERE agent_name = ? AND status = 'running' "
            "ORDER BY started_at DESC LIMIT 1",
            (agent,),
        ).fetchone()
        if running_row:
            return HTMLResponse(
                content=_grid_running_html(agent, running_row["started_at"] or "")
            )
        # Fall back to latest completed run
        row = conn.execute(
            "SELECT id FROM grid_runs WHERE agent_name = ? AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT 1",
            (agent,),
        ).fetchone()
        if not row:
            return HTMLResponse(content=_grid_empty_html(agent))
        run_id = row["id"]

    assert run_id is not None  # guaranteed by early return above
    run = conn.execute(
        "SELECT * FROM grid_runs WHERE id = ?", (run_id,)
    ).fetchone()
    if not run:
        return HTMLResponse(content=_grid_empty_html(agent))

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
        return HTMLResponse(content=_grid_empty_html(agent))

    # Build cell lookup: (task_name, model, config) -> cell
    cell_map = {}
    for c in cells:
        cell_map[(c["task_name"], c["model"], c["config"])] = c

    task_names = list(dict.fromkeys(c["task_name"] for c in cells))

    # Build header
    cols_per_model = len(configs) * 3  # Acc/Flags/Cost per config
    header_html = "<tr>"
    header_html += '<th style="padding:8px 12px;text-align:left;font-size:11px;color:var(--muted);text-transform:uppercase;">Task</th>'
    for model in models:
        header_html += f'<th style="padding:8px 12px;text-align:center;font-size:11px;color:var(--fg-2);" colspan="{cols_per_model}">{_html_escape(model)}</th>'
    header_html += "</tr>"

    # Sub-header: config labels per model + Acc/Flags/Cost per config
    sub_header = "<tr>"
    sub_header += '<th style="padding:4px 12px;"></th>'
    for model in models:
        for config_label in configs:
            sub_header += f'<th style="padding:4px 4px;text-align:center;font-size:10px;color:var(--muted);font-weight:400;" colspan="3">{_html_escape(config_label)}</th>'
    sub_header += "</tr>"
    # Per-column sub-header: Acc (CI) | Flags | Cost
    col_sub = "<tr>"
    col_sub += '<th style="padding:2px 12px;"></th>'
    for model in models:
        for config_label in configs:
            col_sub += '<th style="padding:2px 4px;text-align:center;font-size:10px;color:var(--muted);font-weight:400;">Acc (CI)</th>'
            col_sub += '<th style="padding:2px 4px;text-align:center;font-size:10px;color:var(--muted);font-weight:400;">Flags</th>'
            col_sub += '<th style="padding:2px 4px;text-align:center;font-size:10px;color:var(--muted);font-weight:400;">Cost</th>'
    col_sub += "</tr>"

    # Body rows
    body_rows = ""
    for task_name in task_names:
        body_rows += '<tr style="border-bottom:1px solid var(--border-soft);">'
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
                        cost_str = f"${cell['cost']:.4f}" if cell["cost"] else "—"
                        body_rows += f'<td style="padding:8px 4px;text-align:center;"><span class="cell-score {score_cls}">{pct:.0f}%</span><span class="cell-ci">{ci_str}</span></td>'
                        body_rows += f'<td class="cell-flags">{flag_html}</td>'
                        body_rows += f'<td class="cell-cost">{cost_str}</td>'
        body_rows += "</tr>"

    # Summary text
    summary = _generate_grid_summary(cells, models, configs)
    return HTMLResponse(content=f"""
    <div class="grid-controls" style="display:flex;flex-wrap:wrap;align-items:flex-start;gap:12px;padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:6px;">
        <label style="font-size:11px;color:var(--muted);font-weight:600;">AGENT</label>
        <select class="grid-select" id="gridAgent" style="padding:6px 8px;border-radius:6px;border:1px solid var(--border);background:var(--surface-2);color:var(--fg);font-size:12px;">
          <option>{_html_escape(agent)}</option>
        </select>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:240px;">
        <div style="display:flex;align-items:center;gap:6px;justify-content:space-between;">
          <label style="font-size:11px;color:var(--muted);font-weight:600;">MODELS</label>
          <span style="font-size:11px;color:var(--accent);" id="gridModelCount">0 selected</span>
        </div>
        <div id="gridModels" class="grid-checkbox-list" style="max-height:140px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:4px;">
          <div style="color:var(--muted);font-size:12px;padding:4px;">Loading models…</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:200px;">
        <div style="display:flex;align-items:center;gap:6px;justify-content:space-between;">
          <label style="font-size:11px;color:var(--muted);font-weight:600;">PROFILES</label>
          <span style="font-size:11px;color:var(--accent);" id="gridProfileCount">0 selected</span>
        </div>
        <div id="gridProfiles" class="grid-checkbox-list" style="max-height:140px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:4px;">
          <div style="color:var(--muted);font-size:12px;padding:4px;">Loading profiles…</div>
        </div>
      </div>
      <span style="flex:1;"></span>
      <button onclick="runGrid()" class="btn btn-primary" style="padding:8px 16px;border-radius:6px;font-weight:600;font-size:12px;cursor:pointer;">▶ Run Grid</button>
      <button onclick="exportGridCSV('{run_id}')" class="btn" style="padding:8px 16px;border-radius:6px;font-size:12px;cursor:pointer;">⬇ Export</button>
    </div>
    <div style="overflow-x:auto;background:var(--surface);border:1px solid var(--border);border-radius:12px;">
      <table class="data-table" style="width:100%;min-width:800px;">
        <thead>{header_html}{sub_header}{col_sub}</thead>
        <tbody>{body_rows}</tbody>
      </table>
    </div>
    <div class="grid-footer">
      <div class="summary" style="display:flex;flex-direction:column;gap:6px;">
        <strong>{len(task_names)} tasks</strong> × <strong>{len(models)} models</strong> = {len(task_names) * len(models)} data points
        <div style="font-size:12px;line-height:1.6;color:var(--fg-2);">{summary}</div>
      </div>
      <button onclick="runGrid()" style="background:var(--accent);color:var(--accent-on);border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;">Run Full Grid</button>
    </div>
    """)


def _grid_running_html(agent: str, started_at: str) -> str:
    """Show a running indicator with polling for an in-progress grid run."""
    return f"""
    <div class="cap-empty" hx-get="/api/capability/grid/table?agent={_html_escape(agent)}"
         hx-trigger="every 10s" hx-swap="outerHTML">
      <div class="cap-empty-icon" style="font-size:32px;">⏳</div>
      <h2>Grid Run In Progress</h2>
      <p style="color:var(--fg-3);">
        Started at {started_at[:19] if started_at else 'unknown'} · models × profiles × tasks
      </p>
      <p>Grid comparison tests each model through the full agent harness (SOUL.md + skills + tools). Takes 10–30 minutes. This page refreshes automatically.</p>
      <div style="margin-top:8px;">
        <span class="spinner"></span>
        <span style="color:var(--accent);font-weight:600;font-size:13px;">Running — results will appear here when ready</span>
      </div>
    </div>
    """


def _grid_empty_html(agent: str = "main") -> str:
    """Show empty state with dynamically-loaded models and profiles."""
    return f"""
    <div class="cap-empty">
      <div class="cap-empty-icon">📊</div>
      <h2>No Grid Runs Yet</h2>
      <p>
        Compare model performance across different agent profiles.
        Each model runs through the full agent harness (SOUL.md + skills + tools).
      </p>
      <div style="margin:16px 0; display:flex; gap:24px; justify-content:center; flex-wrap:wrap; align-items:flex-start;">
        <div style="text-align:left;">
          <label style="font-size:13px;color:var(--fg-2);display:block;margin-bottom:6px;">Models (all cloud providers): <span style="color:var(--accent);" id="gridModelCount">0 selected</span></label>
          <div id="gridModels" class="grid-checkbox-list" style="max-height:160px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:6px;min-width:220px;">
            <div style="color:var(--muted);font-size:12px;padding:4px;">Loading models…</div>
          </div>
        </div>
        <div style="text-align:left;">
          <label style="font-size:13px;color:var(--fg-2);display:block;margin-bottom:6px;">Agent Profiles: <span style="color:var(--accent);" id="gridProfileCount">0 selected</span></label>
          <div id="gridProfiles" class="grid-checkbox-list" style="max-height:160px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:6px;min-width:160px;">
            <div style="color:var(--muted);font-size:12px;padding:4px;">Loading profiles…</div>
          </div>
        </div>
      </div>
      <button onclick="runGrid()" class="btn btn-primary">Run Full Grid</button>
    </div>
    """


def _grid_error_html() -> str:
    return """
    <div class="cap-empty" style="border:1px solid rgba(239,68,68,0.3);">
      <div class="cap-empty-icon">⚠️</div>
      <h2>Grid Data Unavailable</h2>
      <p>
        Could not load grid results. The grid may still be running or the database may be unavailable.
      </p>
      <button onclick="runGrid()" class="btn btn-primary">Run Grid Again</button>
    </div>
    """


def _generate_grid_summary(cells: list, models: list, configs: list) -> str:
    """Generate an actionable summary of grid results.

    The grid exists to answer one question (Working Backwards): for a fixed
    agent profile, does the choice of model change agentic quality — and is
    the difference worth the cost? This summary therefore reports:

    1. Model ranking aggregated across profiles (accuracy + cost/value)
    2. Profile spread (does the harness identity matter at all?)
    3. Task-level divergence — where models disagree most (the agentic signal)
    4. Plain-language takeaway
    """
    if not cells:
        return "No data to compare."

    def _mname(m: str) -> str:
        return m.split("/")[-1]

    # 1. Aggregate per model across all profiles
    model_stats: dict[str, dict] = {}
    for c in cells:
        acc = c["accuracy"] or 0
        cost = c["cost"] or 0
        s = model_stats.setdefault(c["model"], {"acc": [], "pass": 0, "total": 0, "cost": []})
        s["acc"].append(acc)
        s["cost"].append(cost)
        if acc > 0:
            s["pass"] += 1
        s["total"] += 1
    model_rank = sorted(
        model_stats.items(),
        key=lambda kv: (sum(kv[1]["acc"]) / kv[1]["total"]),
        reverse=True,
    )

    # 2. Aggregate per profile across all models
    profile_stats: dict[str, list] = {}
    for c in cells:
        profile_stats.setdefault(c["config"], []).append(c["accuracy"] or 0)
    profile_avgs = {p: sum(a) / len(a) for p, a in profile_stats.items()}
    profile_spread = max(profile_avgs.values()) - min(profile_avgs.values())

    # 3. Task-level model divergence (agentic signal): per task, the range
    # between best-model avg and worst-model avg across profiles.
    task_rows: dict[str, dict] = {}
    for c in cells:
        t = task_rows.setdefault(c["task_name"], {})
        per_model = t.setdefault("per_model", {})
        per_model.setdefault(c["model"], []).append(c["accuracy"] or 0)
    divergences = []
    for task, data in task_rows.items():
        avgs = {m: sum(v) / len(v) for m, v in data["per_model"].items()}
        spread = max(avgs.values()) - min(avgs.values())
        if spread > 0.15:  # meaningful divergence (>15 pts)
            divergences.append((task, spread, avgs))
    divergences.sort(key=lambda x: x[1], reverse=True)

    lines: list[str] = []
    lines.append(f"<strong>Model ranking (agentic quality, all profiles):</strong>")
    for i, (m, s) in enumerate(model_rank, 1):
        avg = sum(s["acc"]) / s["total"]
        cost = sum(s["cost"]) / s["total"]
        badge = " 🏆" if i == 1 else ""
        lines.append(
            f"&nbsp;&nbsp;{i}. {_html_escape(_mname(m))} — "
            f"<strong>{avg*100:.1f}%</strong> avg ({s['pass']}/{s['total']} tasks pass), "
            f"${cost:.4f}/cell{badge}"
        )

    # Cost per accuracy point (value ranking) — only models WITH cost data.
    # A model with all-zero cost (missing pricing table entry or token parse
    # failure) would otherwise rank as "free" and corrupt the takeaway.
    costed_models = [
        kv for kv in model_rank
        if sum(kv[1]["cost"]) / kv[1]["total"] > 0
    ]
    if costed_models:
        value_rank = sorted(
            costed_models,
            key=lambda kv: (sum(kv[1]["cost"]) / kv[1]["total"]) / max(sum(kv[1]["acc"]) / kv[1]["total"], 0.01),
        )
        best_value = value_rank[0][0]
        best_value_cost = sum(value_rank[0][1]["cost"]) / value_rank[0][1]["total"]
        best_value_acc = sum(value_rank[0][1]["acc"]) / value_rank[0][1]["total"]
        lines.append(
            f"<strong>Best value:</strong> {_html_escape(_mname(best_value))} — "
            f"${best_value_cost:.4f}/cell for {best_value_acc*100:.1f}% accuracy "
            f"(${best_value_cost / max(best_value_acc, 0.01):.3f} per accuracy point)."
        )
        missing_cost = [m for m, s in model_rank if sum(s["cost"]) / s["total"] <= 0]
        if missing_cost:
            lines.append(
                f"<span style=\"color:var(--warn);\">⚠️ Cost data missing for: "
                f"{', '.join(_html_escape(_mname(m)) for m in missing_cost)} — "
                f"excluded from value ranking.</span>"
            )
    else:
        lines.append("<span style=\"color:var(--warn);\">⚠️ No cost data recorded for any model — value ranking unavailable.</span>")

    # Profile spread
    if profile_spread < 0.05:
        lines.append(
            f"<strong>Profile spread:</strong> {profile_spread*100:.1f} pts across "
            f"{len(profile_avgs)} profiles — profiles behave nearly identically on these tasks. "
            f"Model choice matters more than agent identity here."
        )
    else:
        best_p = max(profile_avgs, key=profile_avgs.get)
        lines.append(
            f"<strong>Profile spread:</strong> {profile_spread*100:.1f} pts — "
            f"{_html_escape(best_p)} leads ({profile_avgs[best_p]*100:.1f}%). "
            f"Agent identity shifts results on these tasks."
        )

    # Task divergence
    if divergences:
        top = divergences[0]
        worst_model = min(top[2], key=top[2].get)
        best_model = max(top[2], key=top[2].get)
        lines.append(
            f"<strong>Biggest model disagreement:</strong> "
            f"<em>{_html_escape(top[0][:60])}</em> — {_html_escape(_mname(best_model))} "
            f"{top[2][best_model]*100:.0f}% vs {_html_escape(_mname(worst_model))} "
            f"{top[2][worst_model]*100:.0f}% ({top[1]*100:.0f} pt gap). "
            f"This is where model choice changes agentic outcome."
        )
        if len(divergences) > 1:
            others = ", ".join(
                f"{_html_escape(t[:30])} ({_html_escape(_mname(max(a, key=lambda k: a[k])))} {max(a.values())*100:.0f}% vs "
                f"{_html_escape(_mname(min(a, key=lambda k: a[k])))} {min(a.values())*100:.0f}%)"
                for t, _, a in divergences[1:4]
            )
            lines.append(f"&nbsp;&nbsp;also diverges: {others}")

    return "<br>".join(lines)


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

        acc_str = f' · {e["accuracy"]*100:.0f}%' if e["accuracy"] else ""
        git_str = f' · <code>{e["git_commit"][:7]}</code>' if e.get("git_commit") else ""

        # Drift events get an "Investigate →" link (obs-spec-053 §4.4)
        investigate_link = ""
        if e["type"] == "drift":
            investigate_link = ' <a href="#" onclick="document.querySelector(\'.nav-tab[data-tab=drift]\')?.click();return false;" style="color:var(--meta);text-decoration:none;font-size:11px;">Investigate →</a>'

        event_cards += f"""
        <div class="timeline-event">
          <div class="timeline-date"><div class="date">{date_str[5:10]}</div><div class="time">{date_str[11:16]}</div></div>
          <div class="timeline-dot {dot_class}"></div>
          <div class="timeline-card">
            <div class="timeline-card-header">
              <div class="timeline-card-title">{_html_escape(e['title'])} <span class="change-type">· {e['type'].replace('_', ' ')}</span></div>
              {seg_badge}
            </div>
            <div class="timeline-card-desc">{_html_escape(e['description'])}{acc_str}{git_str}{investigate_link}</div>
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


# ── Capability page helpers ──────────────────────────────────────────────────

def _list_agents_with_canary_status() -> tuple[list[str], list[str]]:
    """Return (tested_agents, untested_agents) based on canary_runs table."""
    conn = db._get_conn()
    tested = conn.execute(
        "SELECT DISTINCT agent_name FROM canary_runs ORDER BY agent_name"
    ).fetchall()
    tested_names = [r["agent_name"] for r in tested]
    all_agents = _list_agents()
    untested = [a for a in all_agents if a not in tested_names]
    return tested_names, untested


# ── Capability page HTML partial ──────────────────────────────────────────────


@router.get("/page", response_class=HTMLResponse)
async def capability_page(agent: str = Query("default")):
    """GET /api/capability/page?agent=NAME — full capability page HTML partial."""
    agent = _resolve_agent(agent)
    tested_agents, untested_agents = _list_agents_with_canary_status()

    # Build agent dropdown options with optgroups
    agent_options = ""
    if tested_agents:
        agent_options += '<optgroup label="── Tested Agents ──">'
        for a in tested_agents:
            sel = ' selected' if a == agent else ''
            agent_options += f'<option value="{_html_escape(a)}"{sel}>{_html_escape(a)}</option>'
        agent_options += '</optgroup>'
    if untested_agents:
        agent_options += '<optgroup label="── Untested ──">'
        for a in untested_agents:
            sel = ' selected' if a == agent else ''
            agent_options += f'<option value="{_html_escape(a)}"{sel}>{_html_escape(a)}</option>'
        agent_options += '</optgroup>'

    # Escape agent name for JS embedding
    agent_escaped = _html_escape(agent).replace("'", "\\'")

    # ── Pre-populate overview card with real data ──
    conn = db._get_conn()
    has_data = False
    pass_count = 0
    fail_count = 0
    total_tasks = 0
    last_tested = "Not tested yet"
    accuracy = None
    accuracy_label = "No benchmark data yet"
    accuracy_class = "muted"

    # Check if this agent has canary runs
    latest_run = conn.execute(
        "SELECT id, status, pass_count, fail_count, total_tasks, started_at "
        "FROM canary_runs WHERE agent_name = ? ORDER BY started_at DESC LIMIT 1",
        (agent,),
    ).fetchone()

    if latest_run:
        has_data = True
        pass_count = latest_run["pass_count"] or 0
        fail_count = latest_run["fail_count"] or 0
        total_tasks = latest_run["total_tasks"] or 0
        if latest_run["started_at"]:
            from datetime import datetime, timezone
            try:
                tested_dt = datetime.fromisoformat(latest_run["started_at"])
                now = datetime.now(timezone.utc)
                diff = now - tested_dt.replace(tzinfo=timezone.utc) if tested_dt.tzinfo else now.replace(tzinfo=timezone.utc) - tested_dt.replace(tzinfo=timezone.utc)
                hours = diff.total_seconds() / 3600
                if hours < 1:
                    last_tested = "Tested &lt; 1 hour ago"
                elif hours < 24:
                    last_tested = f"Tested {int(hours)} hours ago"
                else:
                    last_tested = f"Tested {int(hours/24)} days ago"
            except Exception:
                last_tested = "Tested recently"

        # Get accuracy from latest results
        acc_row = conn.execute(
            "SELECT AVG(accuracy) as avg_acc FROM canary_results "
            "WHERE run_id = ? AND accuracy IS NOT NULL",
            (latest_run["id"],),
        ).fetchone()
        if acc_row and acc_row["avg_acc"] is not None:
            accuracy = acc_row["avg_acc"] * 100
            accuracy_class = "good" if accuracy >= 80 else "warn" if accuracy >= 50 else "bad"
            accuracy_label = f"Average accuracy: {accuracy:.0f}%"

    # Check if drift data exists (for Performance Trend section)
    has_drift = conn.execute(
        "SELECT COUNT(*) as c FROM chisel_drift WHERE agent_name = ? AND method='rolling' LIMIT 1",
        (agent,),
    ).fetchone()["c"] > 0

    # Build overview card HTML based on whether agent has data
    if has_data:
        overview_html = f"""\
      <div class="cap-overview" id="capOverviewCard">
        <div class="cap-overview-card agent-info">
          <div>
            <div class="cap-ov-name">{_html_escape(agent)}</div>
            <div class="cap-ov-last-tested">{last_tested}</div>
            <div class="cap-ov-stats">
              <div class="cap-ov-stat"><div class="val {'good' if pass_count > 0 else 'muted'}">{pass_count}</div><div class="lbl">Passed</div></div>
              <div class="cap-ov-stat"><div class="val bad">{fail_count}</div><div class="lbl">Failed</div></div>
              <div class="cap-ov-stat"><div class="val">{total_tasks}</div><div class="lbl">Total</div></div>
            </div>
          </div>
          <div class="cap-ov-actions">
            <button onclick="runCanary()" class="cap-btn cap-btn-primary">▶ Run Benchmark</button>
            <button onclick="navigateToTasksTab()" class="cap-btn cap-btn-sm">📋 View Tasks</button>
          </div>
        </div>
        <div class="cap-overview-card cap-ov-accuracy-card">
          <div class="cap-ov-big-accuracy {accuracy_class}">{(f'{accuracy:.0f}' if accuracy is not None else '—')}%</div>
          <div class="cap-ov-accuracy-label">{accuracy_label}</div>
        </div>
      </div>"""
        untested_style = "display:none;"
        perf_trend_style = "" if has_drift else "display:none;"
    else:
        overview_html = """\
      <div class="cap-overview" id="capOverviewCard" style="display:none;">
        <div class="cap-overview-card agent-info">
          <div>
            <div class="cap-ov-name">--</div>
            <div class="cap-ov-last-tested">Not tested yet</div>
            <div class="cap-ov-stats">
              <div class="cap-ov-stat"><div class="val muted">—</div><div class="lbl">Passed</div></div>
              <div class="cap-ov-stat"><div class="val muted">—</div><div class="lbl">Failed</div></div>
              <div class="cap-ov-stat"><div class="val muted">—</div><div class="lbl">Total</div></div>
            </div>
          </div>
          <div class="cap-ov-actions">
            <button onclick="runCanary()" class="cap-btn cap-btn-primary">▶ Run Benchmark</button>
            <button onclick="navigateToTasksTab()" class="cap-btn cap-btn-sm">📋 View Tasks</button>
          </div>
        </div>
        <div class="cap-overview-card cap-ov-accuracy-card">
          <div class="cap-ov-big-accuracy muted">—%</div>
          <div class="cap-ov-accuracy-label">No benchmark data yet</div>
        </div>
      </div>"""
        untested_style = ""
        perf_trend_style = "display:none;"

    return HTMLResponse(content=f"""\
    <style>
      /* ── Capability Page Redesign ── */
      .cap-agent-bar {{
        display: flex; align-items: center; gap: 12px; padding: 0 0 16px 0;
        border-bottom: 1px solid var(--border-soft); margin-bottom: 4px;
      }}
      .cap-agent-bar label {{
        font-size: 12px; font-weight: 600; color: var(--fg-2);
        text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;
      }}
      .cap-agent-select {{
        padding: 6px 32px 6px 12px; border-radius: 8px; font-size: 13px;
        background: var(--surface); color: var(--fg); border: 1px solid var(--border);
        font-family: inherit; cursor: pointer; appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
        background-repeat: no-repeat; background-position: right 10px center;
        min-width: 200px; max-width: 300px;
      }}
      .cap-agent-select:hover {{ border-color: var(--muted); }}
      .cap-agent-select:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(34,197,94,0.15); }}
      .cap-agent-select optgroup {{ font-weight: 700; color: var(--fg); background: var(--surface); }}
      .cap-agent-select option {{ font-weight: 400; padding: 6px 0; }}

      /* ── Overview Card ── */
      .cap-overview {{
        display: grid; grid-template-columns: 1fr 2fr;
        gap: 16px; margin-bottom: 8px;
      }}
      .cap-overview-card {{
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 12px; padding: 20px;
      }}
      .cap-overview-card.agent-info {{
        display: flex; flex-direction: column; justify-content: space-between;
      }}
      .cap-ov-name {{
        font-size: 16px; font-weight: 700; color: var(--fg); margin-bottom: 4px;
      }}
      .cap-ov-last-tested {{
        font-size: 12px; color: var(--fg-3); margin-bottom: 12px;
      }}
      .cap-ov-stats {{
        display: flex; gap: 20px; margin-bottom: 16px;
      }}
      .cap-ov-stat {{
        text-align: center;
      }}
      .cap-ov-stat .val {{
        font-size: 22px; font-weight: 700; font-family: var(--font-mono);
      }}
      .cap-ov-stat .lbl {{
        font-size: 10px; color: var(--fg-3); text-transform: uppercase;
        letter-spacing: 0.04em; margin-top: 2px;
      }}
      .cap-ov-stat .val.green {{ color: var(--accent); }}
      .cap-ov-stat .val.red {{ color: var(--danger); }}
      .cap-ov-stat .val.muted {{ color: var(--muted); }}
      .cap-ov-actions {{
        display: flex; gap: 8px; flex-wrap: wrap;
      }}
      .cap-ov-accuracy-card {{
        display: flex; align-items: center; justify-content: center;
        flex-direction: column; gap: 8px;
      }}
      .cap-ov-big-accuracy {{
        font-size: 48px; font-weight: 700; font-family: var(--font-mono);
        line-height: 1;
      }}
      .cap-ov-big-accuracy.green {{ color: var(--accent); }}
      .cap-ov-big-accuracy.amber {{ color: var(--warn); }}
      .cap-ov-big-accuracy.red {{ color: var(--danger); }}
      .cap-ov-big-accuracy.muted {{ color: var(--muted); }}
      .cap-ov-accuracy-label {{
        font-size: 12px; color: var(--fg-3); text-align: center;
      }}
      .cap-ov-accuracy-label strong {{ color: var(--fg-2); }}

      /* ── Empty State (not tested) ── */
      .cap-untested {{
        background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
        padding: 48px 32px; text-align: center;
      }}
      .cap-untested-icon {{ font-size: 48px; margin-bottom: 16px; }}
      .cap-untested h3 {{ font-size: 18px; font-weight: 600; color: var(--fg); margin-bottom: 8px; }}
      .cap-untested p {{
        font-size: 13px; color: var(--fg-2); max-width: 480px; margin: 0 auto 20px;
        line-height: 1.6;
      }}
      .cap-untested .help-text {{
        font-size: 12px; color: var(--fg-3); margin-top: 12px;
      }}
      .cap-tooltip {{
        display: inline-block; cursor: help; border-bottom: 1px dotted var(--fg-3);
        color: var(--fg-3); font-size: 12px;
      }}

      /* ── Section Headers ── */
      .cap-section {{
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 12px; overflow: hidden; margin-bottom: 8px;
      }}
      .cap-section-h {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 14px 20px; border-bottom: 1px solid var(--border-soft);
      }}
      .cap-section-h h3 {{
        font-size: 14px; font-weight: 600; color: var(--fg); margin: 0;
        display: flex; align-items: center; gap: 8px;
      }}
      .cap-section-h h3 .badge {{
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 11px; padding: 2px 8px; border-radius: 99px;
        font-weight: 500; background: rgba(34,197,94,0.12); color: var(--accent);
      }}
      .cap-section-body {{
        padding: 16px 20px;
      }}

      /* ── Summary strip ── */
      .cap-summary-strip {{
        display: flex; align-items: center; gap: 12px;
        padding: 0 20px 12px 20px; font-size: 13px; color: var(--fg-2);
      }}
      .cap-summary-strip .ok {{ color: var(--accent); }}
      .cap-summary-strip .warn {{ color: var(--warn); }}
      .cap-summary-strip .bad {{ color: var(--danger); }}

      /* ── Buttons ── */
      .cap-btn {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 8px 16px; border-radius: 8px; font-size: 13px;
        font-weight: 500; cursor: pointer; border: 1px solid var(--border);
        background: var(--bg); color: var(--fg-2); font-family: inherit;
        transition: all 0.15s;
      }}
      .cap-btn:hover {{ border-color: var(--muted); color: var(--fg); }}
      .cap-btn-primary {{
        background: var(--accent); color: var(--accent-on); border-color: var(--accent);
      }}
      .cap-btn-primary:hover {{ opacity: 0.9; color: var(--accent-on); }}
      .cap-btn-sm {{ padding: 5px 12px; font-size: 12px; }}

      /* ── Task table (simplified) ── */
      .cap-task-table {{
        width: 100%; border-collapse: collapse;
      }}
      .cap-task-table th {{
        text-align: left; font-size: 10px; color: var(--muted);
        text-transform: uppercase; letter-spacing: 0.05em;
        padding: 8px 12px; border-bottom: 1px solid var(--border);
        font-weight: 600;
      }}
      .cap-task-table td {{
        padding: 10px 12px; border-bottom: 1px solid var(--border-soft);
        font-size: 13px; color: var(--fg);
      }}
      .cap-task-table tr:last-child td {{ border-bottom: none; }}
      .cap-task-trend {{ font-family: var(--font-mono); font-weight: 600; font-size: 12px; }}
      .cap-task-trend.up {{ color: var(--accent); }}
      .cap-task-trend.down {{ color: var(--danger); }}
      .cap-task-trend.flat {{ color: var(--muted); }}
      .cap-task-status {{
        display: inline-flex; align-items: center; gap: 5px;
        font-size: 11px; padding: 2px 8px; border-radius: 99px;
        font-weight: 500;
      }}
      .cap-task-status.pass {{ background: rgba(34,197,94,0.12); color: var(--accent); }}
      .cap-task-status.fail {{ background: rgba(239,68,68,0.12); color: var(--danger); }}
      .cap-task-status.warn {{ background: rgba(234,179,8,0.12); color: var(--warn); }}

      /* ── Advanced (collapsible) ── */
      .cap-advanced-toggle {{
        display: flex; align-items: center; gap: 8px;
        padding: 12px 20px; cursor: pointer; font-size: 13px;
        color: var(--fg-3); user-select: none;
        border: 1px solid var(--border-soft); border-radius: 12px;
        background: var(--surface); margin-bottom: 8px;
        transition: color 0.15s;
      }}
      .cap-advanced-toggle:hover {{ color: var(--fg-2); }}
      .cap-advanced-toggle .arrow {{
        transition: transform 0.2s; font-size: 10px;
      }}
      .cap-advanced-toggle.open .arrow {{ transform: rotate(90deg); }}
      .cap-advanced-body {{
        display: none; flex-direction: column; gap: 8px;
        margin-bottom: 16px;
      }}
      .cap-advanced-body.open {{ display: flex; }}

      /* ── Performance summary card inline ── */
      .cap-perf-summary {{
        display: flex; align-items: center; gap: 16px;
        padding: 0 20px 8px 20px; flex-wrap: wrap;
      }}
    </style>

    <div class="section" style="display:flex;flex-direction:column;gap:8px;">

      <!-- Agent Selector -->
      <div class="cap-agent-bar">
        <label>Agent</label>
        <form hx-get="/api/capability/page" hx-trigger="change from:#capAgentSelect" hx-target="#capabilityContainer" hx-swap="innerHTML" style="margin:0;">
          <select class="cap-agent-select" name="agent" id="capAgentSelect">
            {agent_options}
          </select>
        </form>
        <span style="font-size:11px;color:var(--fg-3);">
          {len(tested_agents)} tested · {len(untested_agents)} untested
        </span>
      </div>

      <!-- ──── Assertion Types Info Banner ──── -->
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:12px;color:var(--fg-2);display:flex;align-items:center;gap:8px;">
        <span style="font-size:16px;">🧪</span>
        <span>
          <strong>8 assertion types</strong> available:
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;">exact_match</code>
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;">contains</code>
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;">numeric_range</code>
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;">regex</code>
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;color:var(--accent);">llm_judge</code>
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;">json_schema</code>
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;">ordering</code>
          <code style="background:var(--bg);padding:1px 5px;border-radius:3px;">tool_call_validation</code>
          <span style="color:var(--muted);margin-left:4px;">
            · <strong>llm_judge</strong> uses LLM-as-a-Verifier (1-20 scale, K=3, logprob-based expected score) per Kwok et al. 2026
          </span>
        </span>
      </div>

      <!-- ──── Section 1: Agent Overview Card ──── -->
      {overview_html}

      <!-- ──── Empty State: Untested Agent ──── -->
      <div class="cap-untested" id="capUntested" style="{untested_style}">
        <div class="cap-untested-icon">🧪</div>
        <h3>This agent hasn't been tested yet</h3>
        <p>
          A benchmark test runs 9 evaluation tasks to measure this agent's capabilities
          across reasoning, coding, extraction, tool use, and instruction following.
          It takes about <strong>2–3 minutes</strong> and costs roughly
          <strong>$0.05</strong> in API calls.
        </p>
        <button onclick="runCanary()" class="cap-btn cap-btn-primary" style="font-size:15px;padding:12px 28px;">
          🚀 Run First Benchmark
        </button>
        <div class="help-text">
          <span class="cap-tooltip" title="A benchmark (canary) runs a fixed set of tasks against your agent and scores the results. After 3+ runs with the same config, drift detection activates automatically to alert you of performance changes.">
            💡 What is a benchmark?
          </span>
        </div>
      </div>

      <!-- ──── Section 2: Performance Trend ──── -->
      <div class="cap-section" id="perfTrendSection" style="{perf_trend_style}">
        <div class="cap-section-h">
          <h3>📈 Performance Over Time <span class="badge" id="perfTrendBadge" style="display:none;"></span></h3>
          <button onclick="runCanary()" class="cap-btn cap-btn-sm">🔄 Re-run Benchmark</button>
        </div>
        <div class="cap-perf-summary" id="perfTrendSummary" style="display:none;">
          <!-- Populated by JS -->
        </div>
        <div id="driftChartContainer" hx-get="/api/capability/drift/chart?agent={agent}" hx-trigger="load" hx-swap="innerHTML" hx-on::after-swap="setTimeout(loadDriftChart, 100)">
          <div class="skel" style="width:100%;height:140px;border-radius:8px;margin:16px 20px;max-width:calc(100% - 40px);"></div>
        </div>
        <div class="cap-section-body" id="driftChartBody" style="display:none;">
          <!-- The drift chart partial renders into driftChartContainer; this is the post-chart content -->
        </div>
      </div>

      <!-- ──── Section 3: Task Breakdown ──── -->
      <div class="cap-section" id="taskBreakdownSection">
        <div class="cap-section-h">
          <h3>📋 Task Breakdown</h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <button onclick="filterPerTaskDrift('all')" class="cap-btn cap-btn-sm per-task-chip" data-cat="all" style="background:var(--meta);color:#fff;border-color:var(--meta);">All</button>
            <button onclick="filterPerTaskDrift('reasoning')" class="cap-btn cap-btn-sm per-task-chip" data-cat="reasoning" style="background:transparent;color:var(--fg-2);border-color:var(--border);">🧮 Reasoning</button>
            <button onclick="filterPerTaskDrift('coding')" class="cap-btn cap-btn-sm per-task-chip" data-cat="coding" style="background:transparent;color:var(--fg-2);border-color:var(--border);">💻 Coding</button>
            <button onclick="filterPerTaskDrift('extraction')" class="cap-btn cap-btn-sm per-task-chip" data-cat="extraction" style="background:transparent;color:var(--fg-2);border-color:var(--border);">📄 Extraction</button>
            <button onclick="filterPerTaskDrift('tool_use')" class="cap-btn cap-btn-sm per-task-chip" data-cat="tool_use" style="background:transparent;color:var(--fg-2);border-color:var(--border);">🛠 Tool Use</button>
            <button onclick="filterPerTaskDrift('instruction_following')" class="cap-btn cap-btn-sm per-task-chip" data-cat="instruction_following" style="background:transparent;color:var(--fg-2);border-color:var(--border);">📋 Instructions</button>
          </div>
        </div>
        <div class="cap-section-body" id="taskBreakdownBody">
          <div id="perTaskLegend" style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px;"></div>
          <div style="background:var(--bg);border:1px solid var(--border-soft);border-radius:8px;padding:16px;">
            <div class="chart-wrapper"><canvas id="perTaskDriftChart"></canvas></div>
          </div>
          <div id="perTaskDetail" style="display:none;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:16px;margin-top:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <span id="perTaskDetailName" style="font-size:14px;font-weight:600;"></span>
              <span onclick="closePerTaskDetail()" style="cursor:pointer;color:var(--muted);font-size:16px;">✕</span>
            </div>
            <div id="perTaskDetailGrid" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px;"></div>
            <div style="font-size:12px;color:var(--fg-2);line-height:1.6;padding:8px;background:rgba(15,23,42,.5);border-radius:6px;">
              <div style="color:var(--muted);font-weight:600;margin-bottom:4px;">🧠 LLM Judge Reasoning</div>
              <div id="perTaskDetailReasoningText" style="color:var(--muted);">Loading...</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ──── Section 4: What Changed ──── -->
      <div class="cap-section">
        <div class="cap-section-h">
          <h3>🕐 What Changed</h3>
        </div>
        <div class="cap-section-body">
          <div id="timelineContainer" hx-get="/api/capability/timeline/events?agent={agent}" hx-trigger="load" hx-swap="innerHTML">
            <div class="skel" style="width:100%;height:60px;border-radius:8px;"></div>
          </div>
        </div>
      </div>

      <!-- ──── Section 5: Advanced (collapsed) ──── -->
      <div class="cap-advanced-toggle" onclick="toggleAdvanced()">
        <span class="arrow">▶</span> Advanced
        <span style="font-size:11px;color:var(--fg-3);">Grid Comparison, Task Editor</span>
      </div>
      <div class="cap-advanced-body" id="capAdvancedBody">
        <!-- Grid -->
        <div class="cap-section">
          <div class="cap-section-h">
            <h3>📊 Model × Config Comparison</h3>
            <button onclick="runGrid()" class="cap-btn cap-btn-sm">🔄 Run Comparison</button>
          </div>
          <div class="cap-section-body">
            <div id="gridTableContainer" hx-get="/api/capability/grid/table?agent={agent}" hx-trigger="load" hx-swap="innerHTML">
              <div class="skel" style="width:100%;height:100px;border-radius:8px;"></div>
            </div>
          </div>
        </div>

        <!-- Tasks -->
        <div class="cap-section">
          <div class="cap-section-h">
            <h3>📋 Task Library</h3>
            <div style="display:flex;gap:4px;">
              <button onclick="showTaskTab('active')" id="taskTabActive" class="cap-btn cap-btn-sm cap-btn-active">Active</button>
              <button onclick="showTaskTab('pending')" id="taskTabPending" class="cap-btn cap-btn-sm">⏳ Pending</button>
            </div>
          </div>
          <div class="cap-section-body">
            <div id="taskListContainer" hx-get="/api/capability/tasks/list" hx-trigger="load" hx-swap="innerHTML">
              <div class="skel" style="width:100%;height:60px;border-radius:8px;"></div>
            </div>
            <div id="pendingListContainer" style="display:none;" hx-get="/api/capability/pending-tasks/html" hx-trigger="load" hx-swap="innerHTML">
              <div class="skel" style="width:100%;height:60px;border-radius:8px;"></div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <script>
    // ── Agent switcher ──
    function switchCapabilityAgent(agent) {{
      htmx.ajax('GET', '/api/capability/page?agent=' + encodeURIComponent(agent), {{target: '#capabilityContainer', swap: 'innerHTML'}});
    }}

    // ── Navigate to Tasks tab ──
    window.navigateToTasksTab = function() {{
      // Scroll to the Task Breakdown grid section
      var el = document.getElementById('gridReport') || document.querySelector('.cap-section');
      if (el) el.scrollIntoView({{behavior:'smooth', block:'start'}});
    }};

    // ── Advanced section toggle ──
    window.toggleAdvanced = function() {{
      var body = document.getElementById('capAdvancedBody');
      var toggle = document.querySelector('.cap-advanced-toggle');
      if (!body || !toggle) return;
      var open = body.classList.toggle('open');
      toggle.classList.toggle('open', open);
      if (open) {{
        // Lazy-load advanced content if not already loaded
        var gridEl = document.getElementById('gridTableContainer');
        if (gridEl && gridEl.querySelector('.cap-empty') && gridEl.querySelector('.cap-empty').textContent.includes('No Grid Runs')) {{
          htmx.ajax('GET', '/api/capability/grid/table?agent=' + encodeURIComponent('{agent}'), {{target: '#gridTableContainer', swap: 'innerHTML'}});
        }}
      }}
    }};

    // ── Canary runner (renamed to "benchmark" in UI, backend stays "canary") ──
    function runCanary() {{
      var agent = '{agent_escaped}';
      var btn = document.querySelector('.cap-btn-primary') || document.querySelector('button');
      if (btn) {{ btn.textContent = '⏳ Running…'; btn.disabled = true; }}

      // Get auth token from meta tag (injected by server)
      var _token = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _headers = _token ? {{ 'X-ObserveCo-Token': _token }} : {{}};

      fetch('/api/capability/canary/run?agent=' + encodeURIComponent(agent), {{method:'POST', headers: _headers}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          if (d.ok) {{
            showToast('Benchmark started for ' + agent + ' — this takes ~2–3 min');
            // Show running state in overview
            var accEl = document.getElementById('capOvBigAcc');
            if (accEl) {{ accEl.textContent = '...'; accEl.className = 'cap-ov-big-accuracy muted'; }}
            var lastEl = document.getElementById('capOvLastTested');
            if (lastEl) lastEl.textContent = '⏳ Benchmark running…';
            // Hide untested banner
            var untestedEl = document.getElementById('capUntested');
            if (untestedEl) untestedEl.style.display = 'none';

            var poll = setInterval(function() {{
              fetch('/api/capability/canary/status?agent=' + encodeURIComponent(agent), {{headers: _headers}})
                .then(function(r) {{ return r.json(); }})
                .then(function(s) {{
                  if (s.running) {{
                    // Live progress update
                    if (accEl && s.total_tasks) {{
                      var done = (s.pass_count||0) + (s.fail_count||0) + (s.hang_count||0);
                      accEl.textContent = done + '/' + s.total_tasks;
                    }}
                  }} else if (!s.running && s.completed) {{
                    clearInterval(poll);
                    showToast('Benchmark complete — refreshing');
                    // Full page refresh to show results
                    htmx.ajax('GET', '/api/capability/page?agent=' + encodeURIComponent(agent), {{target: '#capabilityContainer', swap: 'innerHTML'}});
                  }} else if (!s.running && !s.completed) {{
                    clearInterval(poll);
                    if (btn) {{ btn.textContent = '▶ Run Benchmark'; btn.disabled = false; }}
                    showToast('No test data available — try running a benchmark');
                  }}
                }});
            }}, 5000);
          }} else {{
            if (btn) {{ btn.textContent = '▶ Run Benchmark'; btn.disabled = false; }}
            showToast('Benchmark failed to start: ' + (d.error || 'unknown'));
          }}
        }})
        .catch(function(e) {{
          if (btn) {{ btn.textContent = '▶ Run Benchmark'; btn.disabled = false; }}
          showToast('Benchmark failed: ' + e.message);
        }});
    }}

    function runGrid() {{
      var agent = '{agent_escaped}';
      var _token = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _gh = _token ? {{ 'X-ObserveCo-Token': _token }} : {{}};
      fetch('/api/capability/grid/run?agent=' + encodeURIComponent(agent), {{method:'POST', headers: _gh}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          if (d.ok) {{
            showToast('Comparison started for ' + agent);
            var poll = setInterval(function() {{
              fetch('/api/capability/grid?agent=' + encodeURIComponent(agent), {{headers: _gh}})
                .then(function(r) {{ return r.json(); }})
                .then(function(g) {{
                  if (g.cells && g.cells.length > 0) {{
                    clearInterval(poll);
                    showToast('Comparison complete — refreshing');
                    htmx.ajax('GET', '/api/capability/grid/table?agent=' + encodeURIComponent(agent), {{target: '#gridTableContainer', swap: 'innerHTML'}});
                  }} else if (g.status === 'failed') {{
                    clearInterval(poll);
                    showToast('Comparison failed: ' + (g.error || 'see server log'));
                  }}
                }})
                .catch(function(e) {{ clearInterval(poll); showToast('Comparison poll error: ' + e.message); }});
            }}, 10000);
          }}
        }})
        .catch(function(e) {{ showToast('Comparison failed: ' + e.message); }});
    }}

    function showToast(msg) {{
      var existing = document.getElementById('capToast');
      if (existing) existing.remove();
      var t = document.createElement('div');
      t.id = 'capToast';
      t.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 16px;color:#f8fafc;font-size:13px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
      t.textContent = msg;
      document.body.appendChild(t);
      setTimeout(function() {{ t.remove(); }}, 5000);
    }}

    function runCanaryForAgent(agent) {{
      var _t = (document.querySelector('meta[name=\"observeco-token\"]') || {{}}).getAttribute('content') || '';
      fetch('/api/capability/canary/run?agent=' + encodeURIComponent(agent), {{method:'POST', headers: _t ? {{'X-ObserveCo-Token': _t}} : {{}}}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{ if (d.ok) showToast('Benchmark started for ' + agent); }});
    }}

    function showNewTaskForm() {{ showToast('Task editor coming soon'); }}
    function editTask(id) {{ showToast('Task editor coming soon'); }}
    function showTaskTab(tab) {{
      var activeBtn = document.getElementById('taskTabActive');
      var pendingBtn = document.getElementById('taskTabPending');
      var activeEl = document.getElementById('taskListContainer');
      var pendingEl = document.getElementById('pendingListContainer');
      if (tab === 'pending') {{
        activeEl.style.display = 'none';
        pendingEl.style.display = 'block';
        activeBtn.classList.remove('cap-btn-active');
        pendingBtn.classList.add('cap-btn-active');
        htmx.ajax('GET', '/api/capability/pending-tasks/html', {{target: '#pendingListContainer', swap: 'innerHTML'}});
      }} else {{
        activeEl.style.display = 'block';
        pendingEl.style.display = 'none';
        pendingBtn.classList.remove('cap-btn-active');
        activeBtn.classList.add('cap-btn-active');
      }}
    }}

    function approveDraft(id) {{
      var _token = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _ah = {{'Content-Type': 'application/json'}};
      if (_token) _ah['X-ObserveCo-Token'] = _token;
      fetch('/api/capability/canary/pending-tasks/approve', {{
        method: 'POST',
        headers: _ah,
        body: JSON.stringify({{task_id: id}})
      }})
      .then(function(r) {{ return r.json(); }})
      .then(function(d) {{
        if (d.ok) {{
          showToast('✓ Approved — now active in canary');
          htmx.ajax('GET', '/api/capability/pending-tasks/html', {{target: '#pendingListContainer', swap: 'innerHTML'}});
        }} else {{
          showToast('Approve failed: ' + (d.error || 'unknown'));
        }}
      }})
      .catch(function(e) {{ showToast('Approve failed: ' + e.message); }});
    }}

    function rejectDraft(id) {{
      if (!confirm('Reject this draft? It will be deleted.')) return;
      var _token = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _rh = {{'Content-Type': 'application/json'}};
      if (_token) _rh['X-ObserveCo-Token'] = _token;
      fetch('/api/capability/canary/pending-tasks/reject', {{
        method: 'POST',
        headers: _rh,
        body: JSON.stringify({{task_id: id}})
      }})
      .then(function(r) {{ return r.json(); }})
      .then(function(d) {{
        if (d.ok) {{
          showToast('Draft rejected');
          htmx.ajax('GET', '/api/capability/pending-tasks/html', {{target: '#pendingListContainer', swap: 'innerHTML'}});
        }} else {{
          showToast('Reject failed: ' + (d.error || 'unknown'));
        }}
      }})
      .catch(function(e) {{ showToast('Reject failed: ' + e.message); }});
    }}

    function viewSourceSession(sessionId) {{
      if (!sessionId) {{ showToast('No source session linked'); return; }}
      var modal = document.getElementById('sourceSessionModal');
      if (!modal) {{
        modal = document.createElement('div');
        modal.id = 'sourceSessionModal';
        modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9998;display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = '<div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;max-width:640px;width:90%;max-height:80vh;overflow:auto;padding:20px;">'
          + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
          + '<h3 style="margin:0;font-size:15px;color:var(--fg);">Original Conversation</h3>'
          + '<button onclick="closeSourceModal()" style="background:none;border:none;color:var(--fg-3);font-size:20px;cursor:pointer;">✕</button>'
          + '</div>'
          + '<div id="sourceSessionBody"><div class="spinner"></div> Loading...</div>'
          + '</div>';
        document.body.appendChild(modal);
      }}
      var body = document.getElementById('sourceSessionBody');
      body.innerHTML = '<div class="spinner"></div> Loading...';
      var _stoken = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _sheaders = _stoken ? {{ 'X-ObserveCo-Token': _stoken }} : {{}};
      fetch('/api/capability/canary/source-session?session_id=' + encodeURIComponent(sessionId), {{headers: _sheaders}})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          if (!d.ok) {{
            body.innerHTML = '<p style="color:var(--danger);">' + (d.error || 'Failed to load') + '</p>';
            return;
          }}
          if (d.deleted) {{
            body.innerHTML = '<p style="color:var(--warn);">Original conversation no longer available (session deleted).</p>';
            return;
          }}
          if (!d.messages || d.messages.length === 0) {{
            body.innerHTML = '<p style="color:var(--fg-3);">No messages found for this session.</p>';
            return;
          }}
          var html = '';
          for (var i = 0; i < d.messages.length; i++) {{
            var m = d.messages[i];
            var roleColor = m.role === 'user' ? 'var(--accent)' : 'var(--success)';
            var roleLabel = m.role === 'user' ? '👤 User' : '🤖 Agent';
            html += '<div style="margin-bottom:10px;padding:8px 12px;border-left:3px solid ' + roleColor + ';background:var(--bg);border-radius:6px;">'
              + '<div style="font-size:11px;color:' + roleColor + ';font-weight:600;margin-bottom:4px;">' + roleLabel + '</div>'
              + '<div style="font-size:13px;color:var(--fg);white-space:pre-wrap;word-break:break-word;">' + _escHtml(m.content) + '</div>'
              + '</div>';
          }}
          body.innerHTML = html;
        }})
        .catch(function(e) {{ body.innerHTML = '<p style="color:var(--danger);">Error: ' + e.message + '</p>'; }});
    }}

    function closeSourceModal() {{
      var m = document.getElementById('sourceSessionModal');
      if (m) m.remove();
    }}

    function _escHtml(s) {{
      var d = document.createElement('div');
      d.textContent = s || '';
      return d.innerHTML;
    }}

    function deleteTask(id) {{
      if (!confirm('Delete this task?')) return;
      var _dtoken = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _dheaders = _dtoken ? {{ 'X-ObserveCo-Token': _dtoken }} : {{}};
      fetch('/api/capability/tasks/' + id, {{method:'DELETE', headers: _dheaders}})
        .then(function() {{ htmx.ajax('GET', '/api/capability/tasks/list', {{target: '#taskListContainer', swap: 'innerHTML'}}); }});
    }}
    function duplicateTask(id) {{ showToast('Duplicate coming soon'); }}
    function switchEditorMode(id, mode) {{}}
    function saveYamlTask(id) {{ showToast('Save coming soon'); }}
    function saveFormTask(id) {{ showToast('Save coming soon'); }}
    function closeEditor(id) {{}}
    function shareDriftView() {{ showToast('Share coming soon'); }}

    // ── Overview card: load canary status ──
    (function loadCapOverview() {{
      var agent = '{agent_escaped}';
      var _otoken = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _oheaders = _otoken ? {{ 'X-ObserveCo-Token': _otoken }} : {{}};
      fetch('/api/capability/canary/status?agent=' + encodeURIComponent(agent), {{headers: _oheaders}})
        .then(function(r) {{ return r.json(); }})
        .then(function(s) {{
          var lastEl = document.getElementById('capOvLastTested');
          var statsEl = document.getElementById('capOvStats');
          var accEl = document.getElementById('capOvBigAcc');
          var accLabel = document.getElementById('capOvAccLabel');
          var untestedEl = document.getElementById('capUntested');
          var overviewCard = document.getElementById('capOverviewCard');
          var perfSection = document.getElementById('perfTrendSection');

          if (!s.completed && !s.running) {{
            // No test data — show untested state
            if (overviewCard) overviewCard.style.display = 'none';
            if (untestedEl) untestedEl.style.display = 'block';
            if (perfSection) perfSection.style.display = 'none';
            if (lastEl) lastEl.textContent = 'Not tested yet';
            if (accEl) {{ accEl.textContent = '—%'; accEl.className = 'cap-ov-big-accuracy muted'; }}
            if (accLabel) accLabel.innerHTML = '<strong>No benchmark data yet</strong><br>Run a test to establish a baseline';
          }} else if (s.running) {{
            if (overviewCard) overviewCard.style.display = 'grid';
            if (untestedEl) untestedEl.style.display = 'none';
            if (lastEl) lastEl.textContent = '⏳ Benchmark running…';
            if (accEl) {{ accEl.textContent = '...'; accEl.className = 'cap-ov-big-accuracy muted'; }}
          }} else {{
            if (overviewCard) overviewCard.style.display = 'grid';
            if (untestedEl) untestedEl.style.display = 'none';
            var pass = s.pass_count || 0;
            var fail = s.fail_count || 0;
            var hang = s.hang_count || 0;
            var total = s.total_tasks || (pass + fail + hang);
            var accuracy = total > 0 ? Math.round((pass / total) * 100) : 0;

            // Accuracy color
            var accClass = accuracy >= 80 ? 'green' : accuracy >= 60 ? 'amber' : 'red';
            if (accEl) {{
              accEl.textContent = accuracy + '%';
              accEl.className = 'cap-ov-big-accuracy ' + accClass;
            }}
            if (accLabel) {{
              var desc = accuracy >= 80 ? 'Good performance' : accuracy >= 60 ? 'Needs attention' : 'Significant issues';
              accLabel.innerHTML = '<strong>' + desc + '</strong><br>' + pass + '/' + total + ' tasks passed';
            }}

            // Last tested time
            if (lastEl && s.run_id) {{
              lastEl.textContent = 'Last test results available — hover chart for details';
            }}

            // Stats
            if (statsEl) {{
              statsEl.innerHTML =
                '<div class="cap-ov-stat"><div class="val green">' + pass + '</div><div class="lbl">Passed</div></div>' +
                '<div class="cap-ov-stat"><div class="val ' + (fail > 0 ? 'red' : 'muted') + '">' + fail + '</div><div class="lbl">Failed</div></div>' +
                '<div class="cap-ov-stat"><div class="val muted">' + total + '</div><div class="lbl">Total</div></div>';
            }}

            // Show performance trend section
            if (perfSection) perfSection.style.display = 'block';
          }}
        }})
        .catch(function() {{
          var lastEl = document.getElementById('capOvLastTested');
          if (lastEl) lastEl.textContent = '⚠ Could not load status';
        }});
    }})();

    // ── Per-task drift chart ──────────────────────────────────────────
    var _perTaskChart = null;
    var _perTaskAllTasks = [];
    var _perTaskActiveCat = 'all';

    var _perTaskCatColors = {{
      reasoning: '#3b82f6',
      coding: '#22c55e',
      extraction: '#a855f7',
      tool_use: '#eab308',
      instruction_following: '#14b8a6'
    }};

    function _perTaskColor(task) {{
      if (task.severity === 'breach') return '#ef4444';
      if (task.severity === 'warning') return '#eab308';
      return _perTaskCatColors[task.category] || '#64748b';
    }}

    // Auto-fetch per-task data on load
    (function() {{
      fetchPerTaskData();
    }})();

    async function fetchPerTaskData() {{
      try {{
        var _token = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
        var _headers = _token ? {{ 'X-ObserveCo-Token': _token }} : {{}};
        var resp = await fetch('/api/capability/drift/per-task-history?agent=' + encodeURIComponent('{agent_escaped}'), {{headers: _headers}});
        var data = await resp.json();
        _perTaskAllTasks = data.tasks || [];
        if (_perTaskAllTasks.length === 0) {{
          var body = document.getElementById('taskBreakdownBody');
          if (body) body.innerHTML = '<div style="text-align:center;padding:32px;color:var(--fg-3);font-size:13px;">📋 Run a benchmark to see per-task breakdown</div>';
        }} else {{
          renderPerTaskDriftChart();
        }}
      }} catch(e) {{ console.error('per-task drift fetch failed', e); }}
    }}

    function renderPerTaskDriftChart() {{
      if (typeof Chart === 'undefined') return;
      var ctx = document.getElementById('perTaskDriftChart');
      if (!ctx) return;

      var filtered = _perTaskAllTasks;
      if (_perTaskActiveCat !== 'all') {{
        filtered = _perTaskAllTasks.filter(function(t) {{ return t.category === _perTaskActiveCat; }});
      }}

      if (filtered.length === 0) {{
        var legendEl = document.getElementById('perTaskLegend');
        if (legendEl) legendEl.innerHTML = '<span style="font-size:12px;color:var(--muted);">No tasks in this category yet. Run a benchmark to populate.</span>';
        return;
      }}

      var dateSet = {{}};
      filtered.forEach(function(t) {{
        t.points.forEach(function(p) {{ dateSet[p.date] = true; }});
      }});
      var labels = Object.keys(dateSet).sort();

      var datasets = filtered.map(function(t) {{
        var accMap = {{}};
        t.points.forEach(function(p) {{ accMap[p.date] = p.accuracy; }});
        var data = labels.map(function(d) {{ return accMap[d] !== undefined ? accMap[d] : null; }});
        var color = _perTaskColor(t);
        return {{
          label: t.name,
          data: data,
          borderColor: color,
          backgroundColor: color,
          borderWidth: t.severity === 'stable' ? 1.5 : 2.5,
          pointRadius: t.severity === 'stable' ? 2 : 4,
          pointHoverRadius: 6,
          pointBackgroundColor: color,
          fill: false,
          tension: 0.3,
          spanGaps: false,
          taskId: t.task_id,
          taskName: t.name,
          baseline: t.baseline,
          current: t.current,
          delta: t.delta,
          severity: t.severity,
          category: t.category
        }};
      }});

      if (_perTaskChart) {{ _perTaskChart.destroy(); _perTaskChart = null; }}

      _perTaskChart = new Chart(ctx, {{
        type: 'line',
        data: {{ labels: labels, datasets: datasets }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          interaction: {{ mode: 'nearest', intersect: true }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              backgroundColor: 'rgba(30,41,59,.95)',
              titleColor: '#f8fafc',
              bodyColor: '#94a3b8',
              borderColor: '#334155',
              borderWidth: 1,
              padding: 10,
              callbacks: {{
                title: function(ctx) {{
                  return ctx[0].dataset.taskName || ctx[0].dataset.label || '';
                }},
                label: function(ctx) {{
                  var ds = ctx.dataset;
                  var lines = [];
                  lines.push('Accuracy: ' + (ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) + '%' : 'N/A'));
                  lines.push('Baseline: ' + (ds.baseline != null ? ds.baseline.toFixed(1) + '%' : '—'));
                  lines.push('Current:  ' + (ds.current != null ? ds.current.toFixed(1) + '%' : '—'));
                  var dsgn = ds.delta >= 0 ? '+' : '';
                  lines.push('Change: ' + dsgn + (ds.delta != null ? ds.delta.toFixed(1) + 'pp' : '—') + ' · ' + (ds.severity || 'stable'));
                  return lines;
                }}
              }}
            }}
          }},
          onClick: function(e, elements) {{
            if (elements.length > 0) {{
              var ds = _perTaskChart.data.datasets[elements[0].datasetIndex];
              showPerTaskDetail(ds.taskId, ds.taskName, ds.baseline, ds.current, ds.delta, ds.severity);
            }}
          }},
          scales: {{
            x: {{
              grid: {{ display: false }},
              ticks: {{ color: '#64748b', font: {{ size: 9 }}, maxRotation: 0, autoSkip: true, maxTicksLimit: 14 }}
            }},
            y: {{
              min: 0,
              max: 100,
              grid: {{ color: 'rgba(51,65,85,.2)' }},
              ticks: {{ color: '#94a3b8', font: {{ size: 9 }}, callback: function(v) {{ return v + '%'; }} }}
            }}
          }}
        }}
      }});

      renderPerTaskLegend(filtered);
    }}

    function renderPerTaskLegend(tasks) {{
      var el = document.getElementById('perTaskLegend');
      if (!el) return;
      var h = '';
      tasks.forEach(function(t, i) {{
        var c = _perTaskColor(t);
        var tag = '';
        if (t.severity === 'breach') {{
          tag = ' <span style="font-size:9px;padding:0 4px;border-radius:3px;background:rgba(239,68,68,.2);color:#ef4444;">BREACH</span>';
        }} else if (t.severity === 'warning') {{
          tag = ' <span style="font-size:9px;padding:0 4px;border-radius:3px;background:rgba(234,179,8,.2);color:#eab308;">WARNING</span>';
        }}
        h += '<span style="display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--fg-2);cursor:pointer;padding:2px 0;" onclick="(function(){{var m=_perTaskChart.getDatasetMeta(' + i + ');m.hidden=!m.hidden;_perTaskChart.update();}})()">' +
          '<span style="width:8px;height:8px;border-radius:50%;background:' + c + ';display:inline-block;flex-shrink:0;"></span>' +
          t.name + tag + '</span>';
      }});
      el.innerHTML = h;
    }}

    // Keep togglePerTaskDrift for backward compat (not used in new UI, but referenced by htmx partials)
    window.togglePerTaskDrift = function() {{}};

    window.filterPerTaskDrift = function(cat) {{
      _perTaskActiveCat = cat;
      document.querySelectorAll('.per-task-chip').forEach(function(c) {{
        var active = c.dataset.cat === cat;
        c.style.background = active ? 'var(--meta)' : 'transparent';
        c.style.color = active ? '#fff' : 'var(--fg-2)';
        c.style.borderColor = active ? 'var(--meta)' : 'var(--border)';
      }});
      renderPerTaskDriftChart();
    }};

    window.showPerTaskDetail = function(taskId, name, baseline, current, delta, severity) {{
      var panel = document.getElementById('perTaskDetail');
      var nameEl = document.getElementById('perTaskDetailName');
      var gridEl = document.getElementById('perTaskDetailGrid');
      var reasonEl = document.getElementById('perTaskDetailReasoningText');
      if (!panel || !nameEl || !gridEl || !reasonEl) return;

      var deltaColor = delta < 0 ? '#ef4444' : delta > 0 ? 'var(--accent)' : 'var(--muted)';
      var dsgn = delta >= 0 ? '+' : '';

      nameEl.textContent = name;
      nameEl.style.color = severity === 'breach' ? '#ef4444' : severity === 'warning' ? '#eab308' : 'var(--fg)';
      gridEl.innerHTML =
        '<div style="text-align:center;"><div style="font-size:20px;font-weight:700;color:var(--accent);">' + (baseline != null ? baseline.toFixed(1) + '%' : '—') + '</div><div style="font-size:10px;color:var(--muted);margin-top:2px;">Baseline</div></div>' +
        '<div style="text-align:center;"><div style="font-size:20px;font-weight:700;color:' + (delta < 0 ? '#ef4444' : 'var(--accent)') + ';">' + (current != null ? current.toFixed(1) + '%' : '—') + '</div><div style="font-size:10px;color:var(--muted);margin-top:2px;">Current</div></div>' +
        '<div style="text-align:center;"><div style="font-size:20px;font-weight:700;color:' + deltaColor + ';">' + dsgn + (delta != null ? delta.toFixed(1) + 'pp' : '—') + '</div><div style="font-size:10px;color:var(--muted);margin-top:2px;">Change</div></div>';
      reasonEl.innerHTML = 'Loading judge reasoning...';
      panel.style.display = 'block';

      var _jtoken = (document.querySelector('meta[name="observeco-token"]') || {{}}).getAttribute('content') || '';
      var _jheaders = _jtoken ? {{ 'X-ObserveCo-Token': _jtoken }} : {{}};
      fetch('/api/capability/canary/judge-reasoning?task_id=' + encodeURIComponent(taskId), {{headers: _jheaders}})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
          var assertions = data.assertions || [];
          if (assertions.length === 0) {{
            reasonEl.innerHTML = '<span style="color:var(--muted);">No LLM judge reasoning available for this task.</span>';
            return;
          }}
          var h = '';
          assertions.forEach(function(a) {{
            var sc = a.status === 'pass' ? 'var(--accent)' : a.status === 'fail' ? 'var(--danger)' : 'var(--muted)';
            h += '<div style="margin-bottom:8px;"><span style="color:' + sc + ';font-weight:600;">' + (a.status || '?').toUpperCase() + '</span> ' +
              '<span style="color:var(--fg-2);">Score: ' + (a.score != null ? (a.score * 100).toFixed(0) + '%' : '—') + '</span></div>' +
              '<div style="color:var(--muted);margin-bottom:12px;">' + (a.reasoning || 'No reasoning provided.') + '</div>';
          }});
          reasonEl.innerHTML = h || '<span style="color:var(--muted);">No judge data available.</span>';
        }})
        .catch(function() {{
          reasonEl.innerHTML = '<span style="color:var(--muted);">Failed to load judge reasoning.</span>';
        }});
    }};

    window.closePerTaskDetail = function() {{
      var panel = document.getElementById('perTaskDetail');
      if (panel) panel.style.display = 'none';
    }};
    </script>
    """)
