"""Benchmark engine — create, run, and score benchmarks via lm-eval-harness.

ponytail: The old ``_keyword_scorer`` and ``_llm_judge`` have been deleted.
Scoring is now handled by lm-eval-harness metrics (exact_match, f1, acc, etc.).
Upgrade path: integrated lm-eval metric pipeline is the target architecture.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

SGT = timezone.utc  # stored as UTC, displayed in SGT


# ── Data types ───────────────────────────────────────────────────────────────

@dataclass
class BenchmarkTask:
    """A user-defined task with expected output."""
    id: int = 0
    agent_name: str = ""
    task_name: str = ""
    input_text: str = ""
    context_text: str = ""
    expected_output: str = ""
    created_at: int = 0  # unix ts


@dataclass
class BenchmarkResult:
    """Result of running a benchmark task through an agent harness."""
    id: int = 0
    agent_name: str = ""
    task_name: str = ""
    score: float = 0.0
    passed: bool = False
    total: int = 1
    model_used: str = ""
    harness_type: str = "hermes"
    run_at: int = 0
    details: dict = field(default_factory=dict)  # judge reasoning, raw output, etc.


# ── Suite definitions ────────────────────────────────────────────────────────

# ponytail: suites use free-text generation tasks (no MC scoring needed).
# Canary = 15 samples per task. Full = 50-100+ samples per task.
# All tasks are generate_until (free-text), so no logprobs needed.
# Upgrade path: add more dimensions as agent quality needs grow.
#
# Agent dimensions covered (7 dimensions, 9 tasks):
#   - Reasoning:       BBH subtasks (boolean expressions, navigation, truth deduction)
#   - Math:            GSM8K (word problems, chain-of-thought)
#   - Instruction:     IFEval (format constraints)
#   - Code:            MBPP (basic Python — replaces HumanEval which hung on agent harness)
#   - Knowledge:       TriviaQA (factual recall)
#   - Safety:          BBQ generate (bias/social reasoning)
#   - Science:         ARC challenge chat (grade-school science)
SUITES: dict[str, tuple[list[str], int | None]] = {
    "canary": (
        [
            "bbh_cot_fewshot_boolean_expressions",
            "bbh_cot_fewshot_navigate",
            "bbh_cot_fewshot_web_of_lies",
            "gsm8k_cot",
            "ifeval",
            "mbpp",
            "triviaqa",
            "bbq_generate",
            "arc_challenge_chat",
        ],
        15,
    ),
    "full": (
        [
            "bbh_cot_fewshot_boolean_expressions",
            "bbh_cot_fewshot_navigate",
            "bbh_cot_fewshot_web_of_lies",
            "gsm8k_cot",
            "ifeval",
            "mbpp",
            "triviaqa",
            "bbq_generate",
            "arc_challenge_chat",
        ],
        50,
    ),
}


# ── Engine ──────────────────────────────────────────────────────────────────

class BenchmarkEngine:
    """Create, list, delete tasks and run benchmarks via lm-eval-harness."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    # ── Task CRUD ──────────────────────────────────────────────────────────

    def create_task(self, agent_name: str, task_name: str,
                    input_text: str, context_text: str = "",
                    expected_output: str = "") -> dict:
        """Create a new benchmark task. Returns {ok, task_id?, error?}."""
        conn = self.db._get_conn()
        now = int(time.time())
        try:
            cur = conn.execute(
                "INSERT INTO benchmark_tasks "
                "(agent_name, task_name, input_text, context_text, expected_output, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (agent_name, task_name, input_text, context_text, expected_output, now),
            )
            conn.commit()
            return {"ok": True, "task_id": cur.lastrowid}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_tasks(self, agent_name: str) -> list[dict]:
        """List all tasks for an agent."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT id, agent_name, task_name, input_text, context_text, "
            "       expected_output, created_at "
            "FROM benchmark_tasks WHERE agent_name = ? ORDER BY created_at DESC",
            (agent_name,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_task(self, agent_name: str, task_name: str) -> dict:
        """Delete a task by name. Returns {ok, error?}."""
        conn = self.db._get_conn()
        try:
            conn.execute(
                "DELETE FROM benchmark_tasks WHERE agent_name = ? AND task_name = ?",
                (agent_name, task_name),
            )
            conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Running (lm-eval backend) ─────────────────────────────────────────

    def run_lm_eval(
        self,
        agent_name: str,
        tasks: Optional[list[str]] = None,
        suite: str = "",
        limit: Optional[int] = None,
        task_include_path: Optional[str] = None,
        direct: bool = False,
        litellm: bool = False,
        harness_config: Optional[dict] = None,
        direct_system_prompt: str = "",
    ) -> dict:
        """Run lm-eval-harness benchmarks through agent harness or direct model API.

        Args:
            agent_name: Hermes agent profile name (ignored when direct=True).
            tasks: List of task names or paths to YAML task files.
            suite: Pre-built suite name (e.g. 'mmlu-canary').
            limit: Max samples per task. Overrides suite default.
            task_include_path: Extra directory for custom YAML task files.
            direct: If True, call model API directly (no agent harness).
            litellm: If True, use LiteLLM adapter with real logprobs from
                local llama-server for MC scoring. Implies direct=True.

        Returns:
            {ok, error?, results?, agent_name, suite_name}
        """
        from lm_eval import simple_evaluate
        from lm_eval.tasks import TaskManager
        from observeco.benchmark.adapters.lm_eval_adapter import HermesAgentLM

        # Resolve task list
        task_list: list[str] = []
        suite_limit: Optional[int] = None

        if suite:
            if suite not in SUITES:
                return {"ok": False, "error": f"Unknown suite: {suite}. Available: {list(SUITES.keys())}"}
            suite_tasks, suite_limit = SUITES[suite]
            task_list.extend(suite_tasks)

        if tasks:
            task_list.extend(tasks)

        if not task_list:
            return {"ok": False, "error": "No tasks or suite specified"}

        # Use suite's default limit unless explicitly overridden
        effective_limit = limit if limit is not None else suite_limit

        # Build TaskManager with custom YAML path
        if not task_include_path:
            # Auto-detect tasks directory relative to package
            import observeco
            pkg_dir = os.path.dirname(observeco.__file__)
            tasks_dir = os.path.join(pkg_dir, "benchmark", "tasks")
            if os.path.isdir(tasks_dir):
                task_include_path = tasks_dir

        task_manager = None
        if task_include_path:
            task_manager = TaskManager(include_path=task_include_path)

        # Create adapter — agent harness, direct API, or LiteLLM
        if litellm:
            from observeco.benchmark.adapters.litellm_adapter import LiteLLMAdapter

            # Detect what model Hermes uses, then use LiteLLM for generation
            from observeco.benchmark.adapters.lm_eval_adapter import HermesAgentLM
            probe = HermesAgentLM(agent_name=agent_name, timeout=5)
            model_spec = probe.detect_model()
            adapter = LiteLLMAdapter(model_spec=model_spec, timeout=120)
            model_name = f"litellm:{model_spec}"
        elif direct:
            from observeco.benchmark.adapters.direct_model import DirectModelLM

            # Resolve model spec: detect what Hermes would use, then call directly
            from observeco.benchmark.adapters.lm_eval_adapter import HermesAgentLM
            probe = HermesAgentLM(agent_name=agent_name, timeout=5)
            model_spec = probe.detect_model()
            adapter = DirectModelLM(model_spec=model_spec, timeout=120, system_prompt=direct_system_prompt)
            model_name = f"direct:{model_spec}"
        else:
            from observeco.benchmark.adapters.lm_eval_adapter import HermesAgentLM

            adapter = HermesAgentLM(agent_name=agent_name, timeout=120, harness_config=harness_config)
            model_name = adapter.detect_model()

        # Run evaluation — data file paths in YAML are relative to the YAML's
        # directory, so chdir to the tasks base dir before evaluation.
        old_cwd = os.getcwd()
        try:
            if task_include_path:
                os.chdir(task_include_path)
            results = simple_evaluate(
                model=adapter,
                tasks=task_list,
                limit=effective_limit,
                task_manager=task_manager,
                log_samples=True,
                verbosity="WARNING",
                confirm_run_unsafe_code=True,  # needed for humaneval
            )
        except Exception as exc:
            logger.exception("lm-eval evaluation failed")
            return {"ok": False, "error": f"Evaluation failed: {exc}"}
        finally:
            if task_include_path:
                os.chdir(old_cwd)

        if results is None:
            return {"ok": False, "error": "Evaluation returned None (possible multi-process issue)"}

        # Store results
        stored = self._store_lm_eval_results(
            agent_name=agent_name,
            suite_name=suite or ",".join(task_list),
            model_used=model_name,
            results=results,
        )

        return {
            "ok": True,
            "agent_name": agent_name,
            "suite_name": suite or ",".join(task_list),
            "model_used": model_name,
            "results": results.get("results", {}),
            "stored": stored,
        }

    def _store_lm_eval_results(
        self,
        agent_name: str,
        suite_name: str,
        model_used: str,
        results: dict,
    ) -> list[int]:
        """Store lm-eval results in benchmark_results table.

        Each lm-eval task → one row. Metrics stored in details JSON.

        Returns list of result IDs.
        """
        conn = self.db._get_conn()
        now = int(time.time())
        ids = []

        task_results = results.get("results", {})
        samples = results.get("samples", {})

        # Known lm-eval metadata keys that aren't metrics
        _META_KEYS = {"alias", "sample_len"}

        for task_name, metrics in task_results.items():
            # Primary metric: use the first real metric (skip metadata)
            primary_metric = None
            primary_value = 0.0
            for key, value in metrics.items():
                if key in _META_KEYS:
                    continue
                if not key.endswith("_stderr") and isinstance(value, (int, float)):
                    primary_metric = key
                    primary_value = value
                    break

            # Determine "passed" — for accuracy-like metrics, >= 0.5 is passed
            passed = 1 if primary_value >= 0.5 else 0

            task_samples = samples.get(task_name, [])

            details = {
                "suite_name": suite_name,
                "metrics": {k: v for k, v in metrics.items()
                            if isinstance(v, (int, float, str, bool))},
                "primary_metric": primary_metric,
                "sample_count": len(task_samples),
            }

            cur = conn.execute(
                "INSERT INTO benchmark_results "
                "(agent_name, task_name, score, passed, total, model_used, harness_type, run_at, details) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    agent_name,
                    task_name,
                    round(primary_value, 4),
                    passed,
                    1,
                    model_used,
                    "lm-eval",
                    now,
                    json.dumps(details),
                ),
            )
            ids.append(cur.lastrowid)

        conn.commit()
        return ids

    # ── Legacy run_suite (backward compat) ─────────────────────────────────

    def run_suite(self, agent_name: str, suite_name: str = "",
                  adapter: Optional[Any] = None,
                  use_judge: bool = False) -> dict:
        """Run all tasks for an agent through the harness adapter.

        Deprecated: use ``run_lm_eval`` for lm-eval-harness benchmarks.
        Kept for backward compatibility with existing benchmark_tasks.

        adapter: an object with a run_task(agent_name, task) method that
                 returns {"output": str, "model_used": str, "harness_type": str}.
                 If None, uses HermesBenchmarkAdapter.
        """
        tasks = self.list_tasks(agent_name)
        if not tasks:
            return {"ok": False, "error": "no tasks found", "results": []}

        if adapter is None:
            from observeco.benchmark.adapters.hermes import HermesBenchmarkAdapter
            adapter = HermesBenchmarkAdapter()

        results = []
        for t in tasks:
            task = BenchmarkTask(**t)
            # Run through harness
            harness_result = adapter.run_task(agent_name, task)
            # Score using lm-eval adapter (keyword heuristic kept for compat)
            score_result = self._legacy_score(task, harness_result, use_judge)
            # Store
            self._save_result(agent_name, task.task_name, score_result,
                              harness_result.get("model_used", ""),
                              harness_result.get("harness_type", "hermes"))
            results.append(score_result)

        passed = sum(1 for r in results if r["passed"])
        return {
            "ok": True,
            "agent_name": agent_name,
            "total": len(results),
            "passed": passed,
            "score": passed / len(results) if results else 0.0,
            "results": results,
        }

    def _legacy_score(self, task: BenchmarkTask, harness_result: dict,
                      use_judge: bool = False) -> dict:
        """Legacy scoring for backward-compatible task-based benchmarks.

        ponytail: Keyword overlap is a naive heuristic kept for pre-existing
        custom tasks. New benchmarks should use lm-eval YAML tasks via
        ``run_lm_eval``. Upgrade path: migrate custom tasks to lm-eval YAML format.
        """
        import re as _re

        output = harness_result.get("output", "")

        if not task.expected_output:
            return {
                "task_name": task.task_name,
                "score": 0.0,
                "passed": False,
                "reasoning": "No expected output defined — run recorded without scoring",
                "output": output,
            }

        # Keyword overlap (kept for compat)
        expected_words = set(_re.findall(r'\w+(?:\.\w+)?', task.expected_output.lower()))
        actual_words = set(_re.findall(r'\w+(?:\.\w+)?', output.lower()))
        if not expected_words:
            score = 0.0
            reasoning = "Empty expected output"
        else:
            overlap = len(expected_words & actual_words) / len(expected_words)
            score = overlap
            reasoning = f"Keyword overlap: {overlap:.2f} ({len(expected_words & actual_words)}/{len(expected_words)} terms matched)"

        return {
            "task_name": task.task_name,
            "score": score,
            "passed": score >= 0.5,
            "reasoning": reasoning,
            "output": output,
        }

    # ── Storage ────────────────────────────────────────────────────────────

    def _save_result(self, agent_name: str, task_name: str,
                     score_result: dict, model_used: str,
                     harness_type: str) -> int:
        """Save a benchmark result to the database. Returns result id."""
        conn = self.db._get_conn()
        now = int(time.time())
        cur = conn.execute(
            "INSERT INTO benchmark_results "
            "(agent_name, task_name, score, passed, total, model_used, harness_type, run_at, details) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                agent_name, task_name,
                score_result.get("score", 0.0),
                1 if score_result.get("passed") else 0,
                1,
                model_used,
                harness_type,
                now,
                json.dumps({
                    "reasoning": score_result.get("reasoning", ""),
                    "output": score_result.get("output", ""),
                }),
            ),
        )
        conn.commit()
        return cur.lastrowid

    def get_results(self, agent_name: str, limit: int = 20) -> list[dict]:
        """Get recent benchmark results for an agent."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT id, agent_name, task_name, score, passed, total, "
            "       model_used, harness_type, run_at, details "
            "FROM benchmark_results WHERE agent_name = ? "
            "ORDER BY run_at DESC LIMIT ?",
            (agent_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Baseline comparison ────────────────────────────────────────────────

    def compare_baseline(
        self,
        agent_name: str,
        task_name: Optional[str] = None,
        degradation_threshold: float = 0.05,
    ) -> dict:
        """Compare latest results to baseline (previous run per task).

        Returns per-task deltas and flags tasks with significant degradation.

        ponytail: Simple pairwise comparison — latest run vs previous run.
        Doesn't track long-term trends or compute confidence intervals.
        Upgrade path: integrate with lm-eval's bootstrap_iters for CI computation,
        or track rolling averages over N runs.
        """
        conn = self.db._get_conn()

        where = "WHERE agent_name = ?"
        params: tuple = (agent_name,)
        if task_name:
            where += " AND task_name = ?"
            params = (agent_name, task_name)

        rows = conn.execute(
            f"SELECT task_name, score, run_at, details "
            f"FROM benchmark_results {where} "
            f"ORDER BY task_name, run_at DESC",
            params,
        ).fetchall()

        # Group by task_name, get latest two runs
        task_runs: dict[str, list[dict]] = {}
        for row in rows:
            r = dict(row)
            name = r["task_name"]
            if name not in task_runs:
                task_runs[name] = []
            task_runs[name].append(r)

        comparisons = []
        for name, runs in task_runs.items():
            if len(runs) < 2:
                comparisons.append({
                    "task_name": name,
                    "latest_score": runs[0]["score"],
                    "baseline_score": None,
                    "delta": None,
                    "degraded": False,
                    "reason": "No baseline — only one run",
                })
                continue

            latest = runs[0]["score"]
            baseline = runs[1]["score"]
            delta = latest - baseline
            degraded = delta < -degradation_threshold

            comparisons.append({
                "task_name": name,
                "latest_score": latest,
                "baseline_score": baseline,
                "delta": round(delta, 4),
                "degraded": degraded,
                "reason": f"Degradation of {abs(delta):.1%}" if degraded else "Stable",
            })

        total = len(comparisons)
        degraded_count = sum(1 for c in comparisons if c["degraded"])
        stable_count = total - degraded_count

        return {
            "ok": True,
            "agent_name": agent_name,
            "total_tasks": total,
            "degraded": degraded_count,
            "stable": stable_count,
            "comparisons": comparisons,
        }
