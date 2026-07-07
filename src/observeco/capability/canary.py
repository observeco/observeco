"""Canary runner — task execution, scoring, and run management.

obs-spec-051: Canary runner for capability monitoring.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from observeco.db import Database

logger = logging.getLogger(__name__)


# ── Data types ───────────────────────────────────────────────────────────────

@dataclass
class TaskResult:
    """Result of one task execution (one trial)."""
    output: str = ""
    latency_ms: float = 0.0
    model_used: str = ""
    harness_type: str = "hermes"
    tokens: int = 0
    cost: float = 0.0
    hang: bool = False
    error: str = ""
    passed: bool = False
    accuracy: float = 0.0
    provider_error: bool = False  # True if failure was provider-side (5xx/429), not model


@dataclass
class CanaryReport:
    """Aggregate canary run report."""
    run_id: str = ""
    agent_name: str = ""
    config_hash: str = ""
    total_tasks: int = 0
    pass_count: int = 0
    hang_count: int = 0
    fail_count: int = 0
    overall_accuracy: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0
    per_task: list[dict] = field(default_factory=list)
    drift: Optional[dict] = None  # set by BaselineManager.compare()


# ── Scorer ───────────────────────────────────────────────────────────────────

class Scorer:
    """Score task outputs against assertions.

    Assertion types (5):
    - exact_match: output.strip() == target
    - contains: all keywords present in output
    - numeric_range: extracted number within [min, max]
    - regex: output matches pattern
    - llm_judge: LLM evaluates output against criteria (ponytail: deferred)
    """

    @staticmethod
    def score(assertions: list[dict], output: str) -> tuple[bool, float, str]:
        """Score output against assertions.

        Args:
            assertions: List of assertion dicts (from canary_tasks.assertions JSON).
            output: The raw agent output text.

        Returns:
            (passed, accuracy, reasoning) — accuracy is 0.0 or 1.0 for binary assertions.
        """
        if not assertions:
            return (False, 0.0, "No assertions defined")

        # Assertion type weights for weighted scoring
        _WEIGHTS = {
            "exact_match": 1.0,
            "llm_judge": 1.0,
            "json_schema": 1.0,
            "tool_call_validation": 1.0,
            "semantic_similarity": 0.8,
            "ordering": 0.7,
            "numeric_range": 0.6,
            "regex": 0.5,
            "contains": 0.4,
        }

        results = []
        for assertion in assertions:
            a_type = assertion.get("type", "")
            try:
                if a_type == "exact_match":
                    p, acc, reason = Scorer._exact_match(assertion, output)
                elif a_type == "contains":
                    p, acc, reason = Scorer._contains(assertion, output)
                elif a_type == "numeric_range":
                    p, acc, reason = Scorer._numeric_range(assertion, output)
                elif a_type == "regex":
                    p, acc, reason = Scorer._regex(assertion, output)
                elif a_type == "llm_judge":
                    p, acc, reason = Scorer._llm_judge(assertion, output)
                elif a_type == "json_schema":
                    p, acc, reason = Scorer._json_schema(assertion, output)
                elif a_type == "ordering":
                    p, acc, reason = Scorer._ordering(assertion, output)
                else:
                    p, acc, reason = (False, 0.0, f"Unknown assertion type: {a_type}")
            except Exception as exc:
                p, acc, reason = (False, 0.0, f"Assertion error: {exc}")
            results.append((p, acc, reason, a_type))

        # Weighted scoring per spec obs-spec-057 §2.2
        weight_sum = sum(_WEIGHTS.get(r[3], 0.5) for r in results) if results else 1.0
        weighted_acc = sum(r[1] * _WEIGHTS.get(r[3], 0.5) for r in results) / weight_sum if results else 0.0
        all_pass = all(r[0] for r in results)
        reasoning = "; ".join(r[2] for r in results)

        return (all_pass, weighted_acc, reasoning)

    @staticmethod
    def _exact_match(assertion: dict, output: str) -> tuple[bool, float, str]:
        target = assertion.get("target", "")
        passed = output.strip() == target.strip()
        return (passed, 1.0 if passed else 0.0,
                f"exact_match: {'PASS' if passed else 'FAIL'}")

    @staticmethod
    def _contains(assertion: dict, output: str) -> tuple[bool, float, str]:
        keywords = assertion.get("keywords", [])
        if not keywords:
            return (False, 0.0, "contains: no keywords specified")
        matches = [kw for kw in keywords if kw.lower() in output.lower()]
        min_match = assertion.get("min_match", len(keywords))
        passed = len(matches) >= min_match
        acc = len(matches) / len(keywords) if keywords else 0.0
        return (passed, acc,
                f"contains: {len(matches)}/{len(keywords)} keywords matched (need {min_match})"
                + ("" if passed else f" (missing: {[kw for kw in keywords if kw.lower() not in output.lower()]})"))

    @staticmethod
    def _numeric_range(assertion: dict, output: str) -> tuple[bool, float, str]:
        """Extract a number from output and check if within [min, max]."""
        # Extract first number from output
        numbers = re.findall(r'[-+]?\d*\.?\d+', output)
        if not numbers:
            return (False, 0.0, "numeric_range: no number found in output")

        val = float(numbers[0])
        lo = assertion.get("min", float("-inf"))
        hi = assertion.get("max", float("inf"))
        tolerance = assertion.get("tolerance", 0)

        in_range = (lo - tolerance) <= val <= (hi + tolerance)
        return (in_range, 1.0 if in_range else 0.0,
                f"numeric_range: {val} {'in' if in_range else 'outside'} [{lo}, {hi}]")

    @staticmethod
    def _regex(assertion: dict, output: str) -> tuple[bool, float, str]:
        pattern = assertion.get("pattern", "")
        if not pattern:
            return (False, 0.0, "regex: no pattern specified")
        try:
            match = re.search(pattern, output, re.DOTALL)
            passed = match is not None
            return (passed, 1.0 if passed else 0.0,
                    f"regex: {'matched' if passed else 'no match'} pattern '{pattern[:50]}'")
        except re.error as exc:
            return (False, 0.0, f"regex: invalid pattern: {exc}")

    @staticmethod
    def _llm_judge(assertion: dict, output: str) -> tuple[bool, float, str]:
        """LLM-as-judge assertion — evaluates output quality against criteria."""
        criteria = assertion.get("criteria", "")
        expected = assertion.get("expected", "")
        system_prompt = "You are evaluating an AI agent's response. Score it on a 0-1 scale. Respond with JSON: {\"score\": 0.0-1.0, \"reasoning\": \"...\"}"
        user_context = f"Criteria: {criteria}\nExpected output: {expected}\nAgent output: {output[:2000]}"
        try:
            from observeco.llm_service import ask
            result = ask(system_prompt, user_context, consumer="canary_judge", tier=2)
            if result is None:
                return (False, 0.0, "llm_judge: no API key or budget exhausted")
            import json
            judge = json.loads(result)
            score = max(0.0, min(1.0, float(judge.get("score", 0.0))))
            reasoning_msg = judge.get("reasoning", "")
            passed = score >= assertion.get("threshold", 0.5)
            return (passed, score, f"llm_judge: {reasoning_msg}")
        except Exception as exc:
            return (False, 0.0, f"llm_judge: error: {exc}")

    @staticmethod
    def _json_schema(assertion: dict, output: str) -> tuple[bool, float, str]:
        """Validate output parses as JSON and matches JSON Schema."""
        schema = assertion.get("schema", {})
        try:
            import json
            data = json.loads(output)
            try:
                import jsonschema
                jsonschema.validate(data, schema)
                return (True, 1.0, "json_schema: valid")
            except ImportError:
                return (True, 1.0, "json_schema: valid (schema check skipped - jsonschema not installed)")
            except Exception as exc:
                return (False, 0.0, f"json_schema: {exc}")
        except json.JSONDecodeError:
            return (False, 0.0, "json_schema: invalid JSON")

    @staticmethod
    def _ordering(assertion: dict, output: str) -> tuple[bool, float, str]:
        """Check if steps appear in the specified order in output."""
        steps = assertion.get("steps", [])
        if not steps:
            return (False, 0.0, "ordering: no steps specified")
        output_lower = output.lower()
        positions = []
        for step in steps:
            pos = output_lower.find(step.lower())
            if pos == -1:
                return (False, 0.0, f"ordering: step '{step[:30]}' not found")
            positions.append(pos)
        for i in range(len(positions) - 1):
            if positions[i] >= positions[i + 1]:
                return (False, 0.0, f"ordering: steps out of order")
        return (True, 1.0, "ordering: all steps in correct order")

    @staticmethod
    def bootstrap_ci(values: list[float], n_bootstrap: int = 1000, ci: float = 0.95) -> tuple[float, float]:
        """Compute bootstrap confidence interval for a list of accuracy values.

        Args:
            values: List of accuracy scores (0.0-1.0).
            n_bootstrap: Number of bootstrap iterations.
            ci: Confidence level (default 0.95).

        Returns:
            (lower_bound, upper_bound) or (0.0, 0.0) if insufficient data (n < 5).
        """
        if len(values) < 5:
            return (0.0, 0.0)

        alpha = (1 - ci) / 2
        means = []
        n = len(values)

        for _ in range(n_bootstrap):
            sample = [random.choice(values) for _ in range(n)]
            means.append(sum(sample) / n)

        means.sort()
        lower_idx = int(alpha * n_bootstrap)
        upper_idx = int((1 - alpha) * n_bootstrap) - 1

        return (round(means[lower_idx], 4), round(means[upper_idx], 4))


# ── TaskExecutor ─────────────────────────────────────────────────────────────

class TaskExecutor:
    """Execute one canary task against an agent adapter."""

    def __init__(self, adapter=None):
        """Args:
            adapter: An object with run_task(agent_name, task) that returns
                     {output, model_used, harness_type, tokens?, cost?, timed_out?, error?}.
        """
        self.adapter = adapter

    def execute(self, task: dict, agent_name: str, timeout: int = 60) -> TaskResult:
        """Run one task once through the adapter.

        Args:
            task: Task dict (from canary_tasks table).
            agent_name: Hermes agent profile name.
            timeout: Per-task timeout in seconds (matches HermesBenchmarkAdapter default).

        Returns:
            TaskResult with output, latency, hang, error info.
        """
        start = time.monotonic()

        if self.adapter is None:
            return TaskResult(
                output="",
                latency_ms=0,
                error="No adapter configured",
                hang=False,
            )

        try:
            # Build a BenchmarkTask-like object for the adapter
            task_obj = type("Task", (), {
                "id": task.get("id", ""),
                "task_name": task.get("name", task.get("id", "unknown")),
                "agent_name": agent_name,
                "input_text": task.get("prompt", ""),
                "context_text": "",
                "expected_output": "",
                "temperature": task.get("temperature", 0.0),
            })()

            result = self.adapter.run_task(agent_name, task_obj)
            elapsed = time.monotonic() - start

            return TaskResult(
                output=result.get("output", ""),
                latency_ms=elapsed * 1000,
                model_used=result.get("model_used", ""),
                harness_type=result.get("harness_type", "hermes"),
                tokens=result.get("tokens", 0),
                cost=result.get("cost", 0.0),
                hang=result.get("timed_out", False),
                error=result.get("error", ""),
                provider_error=result.get("provider_error", False),
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return TaskResult(
                output="",
                latency_ms=elapsed * 1000,
                error=str(exc),
                hang=True,
            )


# ── CanaryRunner ─────────────────────────────────────────────────────────────

class CanaryRunner:
    """Run the canary suite: tasks × trials, score, store, compare baseline."""

    def __init__(self, db: Optional[Database] = None, adapter=None):
        self.db = db or Database()
        self.scorer = Scorer()
        if adapter is None:
            from observeco.benchmark.adapters.hermes import HermesBenchmarkAdapter
            adapter = HermesBenchmarkAdapter()
        self.executor = TaskExecutor(adapter=adapter)

    # ── Task CRUD ──────────────────────────────────────────────────────────

    def list_tasks(self) -> list[dict]:
        """List all canary tasks."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT id, name, description, assertions, timeout, model, trials, "
            "category, difficulty, built_in, created_at FROM canary_tasks ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def _check_blanks(self, prompt: str) -> list[str]:
        """Scan prompt for unresolved template variables like {{ variable }}."""
        import re
        return re.findall(r'\{\{\s*\w+\s*\}\}', prompt)

    def create_task(self, task_data: dict) -> dict:
        """Create a new canary task from a dict.

        Args:
            task_data: {id, name, description?, prompt, assertions, timeout?, model?, trials?}

        Returns:
            {ok, task_id?, error?}
        """
        prompt = task_data.get("prompt", "")
        blanks = self._check_blanks(prompt)
        if blanks:
            return {
                "ok": False,
                "error": f"Prompt has unresolved templates: {', '.join(blanks)}. Replace them with actual test data or provide sample values."
            }

        conn = self.db._get_conn()
        task_id = task_data.get("id", task_data.get("name", "").lower().replace(" ", "-"))

        try:
            conn.execute(
                "INSERT INTO canary_tasks (id, name, description, prompt, assertions, "
                "timeout, model, trials, category, difficulty, temperature, built_in) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    task_data.get("name", task_id),
                    task_data.get("description", ""),
                    task_data["prompt"],
                    json.dumps(task_data.get("assertions", [])),
                    task_data.get("timeout", 60),
                    task_data.get("model", None),
                    task_data.get("trials", 10),  # default increased from 3 to 10 per obs-spec-057
                    task_data.get("category", None),
                    task_data.get("difficulty", "medium"),
                    task_data.get("temperature", 0.0),
                    0,  # user-defined
                ),
            )
            conn.commit()
            return {"ok": True, "task_id": task_id}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def delete_task(self, task_id: str) -> dict:
        """Delete a canary task."""
        conn = self.db._get_conn()
        try:
            conn.execute("DELETE FROM canary_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a single canary task by ID."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT id, name, description, prompt, assertions, timeout, model, trials, built_in, created_at "
            "FROM canary_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        # Parse assertions JSON for convenience
        try:
            result["assertions"] = json.loads(result["assertions"]) if isinstance(result["assertions"], str) else result["assertions"]
        except Exception:
            pass
        return result

    def update_task(self, task_id: str, task_data: dict) -> dict:
        """Update an existing canary task.

        Args:
            task_id: The task ID to update.
            task_data: {name?, description?, prompt?, assertions?, timeout?, model?, trials?}

        Returns:
            {ok, error?}
        """
        conn = self.db._get_conn()
        try:
            fields = []
            values = []
            for key, col in [("name", "name"), ("description", "description"),
                             ("prompt", "prompt"), ("timeout", "timeout"),
                             ("model", "model"), ("trials", "trials")]:
                if key in task_data:
                    # Validate prompt for template variables
                    if key == "prompt":
                        blanks = self._check_blanks(task_data[key])
                        if blanks:
                            return {
                                "ok": False,
                                "error": f"Prompt has unresolved templates: {', '.join(blanks)}. Replace them with actual test data or provide sample values."
                            }
                    fields.append(f"{col} = ?")
                    values.append(task_data[key])
            if "assertions" in task_data:
                fields.append("assertions = ?")
                values.append(json.dumps(task_data["assertions"]))

            if not fields:
                return {"ok": False, "error": "No fields to update"}

            values.append(task_id)
            conn.execute(
                f"UPDATE canary_tasks SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            conn.commit()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── Running ────────────────────────────────────────────────────────────

    def run(
        self,
        agent_name: str,
        task_ids: Optional[list[str]] = None,
        trials: Optional[int] = None,
        config_label: Optional[str] = None,
        split: str = "all",
    ) -> CanaryReport:
        """Run the canary suite for one agent.

        Args:
            agent_name: Hermes agent profile name.
            task_ids: Specific task IDs to run (None = all).
            trials: Override per-task trial count (None = use task default).
            config_label: Human-readable label for this config state.
            split: Filter tasks by split — 'dev', 'test', or 'all' (default).
                Dev/test split prevents overfitting when results inform config
                optimization. Inspired by HF harness-optimization (Niklaus 2026).

        Returns:
            CanaryReport with aggregate and per-task results.
        """
        # Set the adapter to use this agent's profile
        if hasattr(self.executor, 'adapter') and hasattr(self.executor.adapter, 'agent_profile'):
            self.executor.adapter.agent_profile = agent_name

        # 1. Load tasks (filtered by split)
        conn = self.db._get_conn()
        split_clause = ""
        split_params: list = []
        if split != "all":
            split_clause = " AND split = ?"
            split_params = [split]
        if task_ids:
            placeholders = ",".join("?" * len(task_ids))
            rows = conn.execute(
                f"SELECT id, name, prompt, assertions, timeout, model, trials "
                f"FROM canary_tasks WHERE id IN ({placeholders}){split_clause} "
                f"ORDER BY id",
                [*task_ids, *split_params],
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, name, prompt, assertions, timeout, model, trials "
                f"FROM canary_tasks WHERE 1=1{split_clause} ORDER BY id",
                split_params,
            ).fetchall()

        if not rows:
            logger.warning("No canary tasks found for agent %s", agent_name)
            return CanaryReport(agent_name=agent_name, total_tasks=0)

        tasks = [dict(r) for r in rows]
        # Filter out tasks with unresolved template variables
        valid_tasks = []
        skipped_count = 0
        for task in tasks:
            blanks = self._check_blanks(task.get("prompt", ""))
            if blanks:
                logger.warning("Skipping task %s — unresolved templates: %s", task["id"], blanks)
                skipped_count += 1
                continue
            valid_tasks.append(task)

        if not valid_tasks:
            logger.warning("All tasks skipped for agent %s (all have unresolved templates)", agent_name)
            return CanaryReport(agent_name=agent_name, total_tasks=0)

        tasks = valid_tasks

        # 2. Snapshot config
        config_hash = self._compute_config_hash(agent_name, tasks)

        # 3. Create run record
        run_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO canary_runs (id, agent_name, config_hash, config_label, "
            "started_at, status, total_tasks) VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (run_id, agent_name, config_hash, config_label, now_iso, len(tasks)),
        )
        conn.commit()

        # 4. Execute each task × trial
        all_results: list[dict] = []
        pass_count = 0
        hang_count = 0
        fail_count = 0
        total_cost = 0.0
        total_tokens = 0

        for task in tasks:
            task_trials = trials if trials is not None else task.get("trials", 3)
            task_passes = 0
            task_hangs = 0
            task_fails = 0
            task_accuracies: list[float] = []
            task_costs: list[float] = []
            task_tokens: list[int] = []
            task_trajectories: list[dict] = []

            assertions = json.loads(task["assertions"]) if isinstance(task["assertions"], str) else task["assertions"]

            for trial_idx in range(task_trials):
                result = self.executor.execute(task, agent_name, timeout=task.get("timeout", 60))

                if result.provider_error:
                    passed = False
                    accuracy = 0.0
                    status = "provider_error"
                    task_fails += 1
                elif result.hang or result.error:
                    passed = False
                    accuracy = 0.0
                    status = "hang"
                    task_hangs += 1
                else:
                    passed, accuracy, reasoning = self.scorer.score(assertions, result.output)
                    if passed:
                        task_passes += 1
                        status = "pass"
                    else:
                        task_fails += 1
                        status = "fail"

                task_accuracies.append(accuracy)
                if result.cost:
                    task_costs.append(result.cost)
                if result.tokens:
                    task_tokens.append(result.tokens)

                task_trajectories.append({
                    "trial": trial_idx,
                    "status": status,
                    "accuracy": accuracy,
                    "output": result.output[:500],  # truncated for storage
                    "error": result.error,
                    "latency_ms": result.latency_ms,
                    "provider_error": result.provider_error,
                })

                # Store individual result
                result_id = str(uuid.uuid4())
                ci_lower, ci_upper = Scorer.bootstrap_ci(task_accuracies)
                conn.execute(
                    "INSERT INTO canary_results (id, run_id, task_id, status, accuracy, "
                    "ci_lower, ci_upper, cost, tokens, latency_ms, trajectory, error, "
                    "provider_error) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        result_id, run_id, task["id"], status,
                        accuracy, ci_lower, ci_upper,
                        result.cost, result.tokens, int(result.latency_ms),
                        json.dumps(task_trajectories[-1]),
                        result.error if result.error else None,
                        1 if result.provider_error else 0,
                    ),
                )

            # Blowup detection — one trial collapses to near-0 while others pass.
            # HF harness-optimization found per-trial variance is driven by catastrophic
            # blowups (provider 400, no deliverable), not smooth noise. Flag them as
            # signal, not noise — they point to specific, fixable failure modes.
            blowup_count = 0
            if len(task_accuracies) >= 2:
                median_acc = sorted(task_accuracies)[len(task_accuracies) // 2]
                if median_acc > 0:
                    blowup_count = sum(1 for a in task_accuracies if a < 0.2 * median_acc)

            # Per-task aggregate
            mean_accuracy = sum(task_accuracies) / len(task_accuracies) if task_accuracies else 0.0
            ci_lower, ci_upper = Scorer.bootstrap_ci(task_accuracies)
            task_cost = sum(task_costs)
            task_token_total = sum(task_tokens)

            all_results.append({
                "task_id": task["id"],
                "task_name": task["name"],
                "passes": task_passes,
                "hangs": task_hangs,
                "fails": task_fails,
                "accuracy": round(mean_accuracy, 4),
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "cost": round(task_cost, 6),
                "tokens": task_token_total,
                "trajectory": task_trajectories,
                "blowups": blowup_count,
            })

            pass_count += task_passes
            hang_count += task_hangs
            fail_count += task_fails
            total_cost += task_cost
            total_tokens += task_token_total

        conn.commit()

        # 5. Update run record
        overall_accuracy = pass_count / (pass_count + fail_count) if (pass_count + fail_count) > 0 else 0.0
        all_accuracies = []
        for tr in all_results:
            all_accuracies.extend([t["accuracy"] for t in tr["trajectory"]])
        ci_lower, ci_upper = Scorer.bootstrap_ci(all_accuracies)

        completed_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE canary_runs SET completed_at=?, status='completed', "
            "pass_count=?, hang_count=?, fail_count=?, total_cost=?, total_tokens=? "
            "WHERE id=?",
            (completed_at, pass_count, hang_count, fail_count, round(total_cost, 6), total_tokens, run_id),
        )
        conn.commit()

        return CanaryReport(
            run_id=run_id,
            agent_name=agent_name,
            config_hash=config_hash,
            total_tasks=len(tasks),
            pass_count=pass_count,
            hang_count=hang_count,
            fail_count=fail_count,
            overall_accuracy=round(overall_accuracy, 4),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            total_cost=round(total_cost, 6),
            total_tokens=total_tokens,
            per_task=all_results,
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_config_hash(agent_name: str, tasks: list[dict]) -> str:
        """Compute sha256 of (agent_name + model + prompt + tools) as a config fingerprint.

        ponytail: Simple sha256. Won't detect template rendering changes.
        Upgrade path: hash the resolved prompt after template rendering.
        """
        # Use agent name + first task's model + all task prompts as fingerprint
        model = tasks[0].get("model", "") if tasks else ""
        prompts = "|".join(t.get("prompt", "") for t in tasks)
        raw = f"{agent_name}:{model}:{prompts}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def get_run(self, run_id: str) -> Optional[dict]:
        """Get a canary run by ID."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT * FROM canary_runs WHERE id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_runs(self, agent_name: str, limit: int = 20) -> list[dict]:
        """List recent canary runs for an agent."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT * FROM canary_runs WHERE agent_name = ? "
            "ORDER BY started_at DESC LIMIT ?",
            (agent_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_run_results(self, run_id: str) -> list[dict]:
        """Get all task results for a canary run."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT cr.*, ct.name as task_name FROM canary_results cr "
            "JOIN canary_tasks ct ON cr.task_id = ct.id "
            "WHERE cr.run_id = ? ORDER BY ct.id",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]
