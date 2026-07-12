"""Fleet routes — Quality Benchmark per-category breakdown (obs-spec-057 Variant C)."""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


@router.get("/qb-categories", response_class=JSONResponse)
async def qb_categories(agent: str = Query("")):
    """GET /api/fleet/qb-categories?agent=NAME — per-category quality breakdown."""
    from observeco.db import Database
    db = Database()
    conn = db._get_conn()

    if not agent:
        return {"categories": [], "overall": 0, "total": 0, "failed": 0, "worst_reasoning": "", "worst_task": ""}

    run = conn.execute(
        "SELECT id FROM canary_runs WHERE agent_name = ? AND status = 'completed' "
        "ORDER BY started_at DESC LIMIT 1",
        (agent,),
    ).fetchone()
    if not run:
        return {"categories": [], "overall": 0, "total": 0, "failed": 0, "worst_reasoning": "", "worst_task": ""}

    rows = conn.execute(
        "SELECT cr.accuracy, cr.status, ct.category, ct.difficulty, ct.name as task_name, "
        "cr.error, cr.id as result_id "
        "FROM canary_results cr "
        "JOIN canary_tasks ct ON cr.task_id = ct.id "
        "WHERE cr.run_id = ? AND ct.category IS NOT NULL",
        (run["id"],),
    ).fetchall()

    if not rows:
        return {"categories": [], "overall": 0, "total": 0, "failed": 0, "worst_reasoning": "", "worst_task": ""}

    cat_data = {}
    worst = {"task": "", "acc": 1.0, "reasoning": ""}
    total_pass = 0
    total_count = 0

    for r in rows:
        cat = r["category"] or "unknown"
        acc = r["accuracy"] if r["accuracy"] is not None else 0.0
        if cat not in cat_data:
            cat_data[cat] = {"pass": 0, "total": 0, "acc_sum": 0.0}
        cat_data[cat]["total"] += 1
        cat_data[cat]["acc_sum"] += acc
        if r["status"] == "pass":
            cat_data[cat]["pass"] += 1
        total_pass += 1 if r["status"] == "pass" else 0
        total_count += 1
        if acc < worst["acc"]:
            # Use error column (contains assertion failure reasons / LLM judge feedback)
            reasoning = (r["error"] or "").strip()[:200]
            worst = {"task": r["task_name"] or "", "acc": acc, "reasoning": reasoning}

    categories = sorted(
        [{"name": c, "pass": d["pass"], "total": d["total"], "accuracy": round(d["acc_sum"] / d["total"], 2)}
         for c, d in cat_data.items()],
        key=lambda x: x["accuracy"],
        reverse=True,
    )
    overall = round(sum(d["acc_sum"] for d in cat_data.values()) / total_count, 2) if total_count > 0 else 0.0
    return {
        "categories": categories,
        "overall": overall,
        "total": total_count,
        "failed": total_count - total_pass,
        "worst_reasoning": worst["reasoning"][:200] if worst["reasoning"] else "",
        "worst_task": worst["task"],
    }
