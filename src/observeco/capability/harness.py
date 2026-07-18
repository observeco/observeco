"""Harness optimizer — automated harness optimization loop + evaluation framework.

obs-spec-056: harness optimization loop (proposer → lab → promotion gate).
obs-spec-061: evaluation framework (test-time baselines, generalization gate, edit
              classification, difficulty-stratified reporting, unified budget report).

ponytail: The apply-edit step is a no-op on the actual agent harness because we
cannot hot-swap SOUL.md mid-run without profile management. The loop produces
proposals and evaluates against the *current* profile — we measure proposer
quality, not actual harness evolution. Upgrade path: add a `--apply-to-profile`
flag that writes the best candidate's edits back to SOUL.md after the run.
"""

from __future__ import annotations

import json
import logging
import os
import statistics
import uuid
from datetime import datetime, timezone
from typing import Optional

from observeco.db import Database
from observeco.capability.canary import CanaryRunner, CanaryReport

logger = logging.getLogger(__name__)


# ── HarnessOptimizer ────────────────────────────────────────────────────────


class HarnessOptimizer:
    """Harness optimization loop + evaluation framework.

    Two modes:
    1.  optimize() — full loop: baselines → propose → classify → promote
    2.  run_parallel_sampling / run_sequential_refinement — standalone baselines
    """

    def __init__(self, db: Database | None = None, runner: CanaryRunner | None = None):
        self.db = db or Database()
        self.runner = runner or CanaryRunner(db=self.db)

    # ── Test-time scaling baselines (obs-spec-061 §2.1) ────────────────────

    def run_parallel_sampling(
        self, agent_name: str, task_ids: list[str] | None = None, k: int = 5
    ) -> CanaryReport:
        """Run k independent rollouts, aggregate by majority vote.

        ponytail: Aggregation treats all assertions as binary (pass/fail).
        For llm_judge assertions with graded scores, we use the median across
        rollouts. Upgrade path: per-assertion-type aggregation with configurable
        strategies (mean, median, mode, min, max).
        """
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        reports: list[CanaryReport] = []
        for i in range(k):
            logger.info("parallel sampling rollout %d/%d", i + 1, k)
            report = self.runner.run(agent_name, task_ids=task_ids, split="dev")
            reports.append(report)

        return self._aggregate_parallel(reports, agent_name)

    def run_sequential_refinement(
        self, agent_name: str, task_ids: list[str] | None = None, rounds: int = 3
    ) -> CanaryReport:
        """Run r rounds with assertion feedback.

        Round 1: standard run. Rounds 2..r: re-run with assertion feedback
        appended to the task prompt.

        ponytail: Feedback is appended to the prompt text via task modification,
        but the CanaryRunner reads tasks fresh from the DB each run. This means
        refinement happens at the harness level (the agent sees prior results
        only if we persist them). Currently, the feedback is logged but not fed
        back — the agent runs independently each round. Upgrade path: inject
        feedback via the adapter's per-task prompt override, or add a
        `prompt_augment` parameter to CanaryRunner.run().
        """
        if rounds < 1:
            raise ValueError(f"rounds must be >= 1, got {rounds}")

        report = self.runner.run(agent_name, task_ids=task_ids, split="dev")
        for r in range(2, rounds + 1):
            logger.info("sequential refinement round %d/%d", r, rounds)
            feedback = self._format_assertion_feedback(report)
            logger.debug("refinement feedback: %s", feedback[:200] if feedback else "(none)")
            # ponytail: re-run without feeding feedback — see docstring.
            report = self.runner.run(agent_name, task_ids=task_ids, split="dev")
        return report

    def _aggregate_parallel(
        self, reports: list[CanaryReport], agent_name: str
    ) -> CanaryReport:
        """Aggregate k reports by majority vote.

        For each task: if it passed in >50% of rollouts, mark it as passed.
        Accuracy is computed as (passes / total trials) across all tasks.

        ponytail: Simple binary aggregation. Assumes assertions produce 0/1
        accuracy. For graded assertions, this collapses to a binary threshold.
        Upgrade path: per-task weighted voting with assertion-type awareness.
        """
        if not reports:
            return CanaryReport(agent_name=agent_name, total_tasks=0)

        # Collect per-task accuracies from each report
        # per_task is list of {task_id, accuracy, passes, fails, hangs, ...}
        task_ids = [r["task_id"] for r in reports[0].per_task]
        k = len(reports)

        aggregated_per_task: list[dict] = []
        pass_count = 0
        hang_count = 0
        fail_count = 0
        total_cost = 0.0
        total_tokens = 0

        for tid in task_ids:
            # Gather all trials for this task across reports
            # Each report.per_task entry has accuracy (mean of trial accuracies).
            # For majority vote: look at whether the task's per-report pass/fail
            # status leans majority.
            accuracies = []
            task_passes = 0
            task_hangs = 0
            task_fails = 0
            for report in reports:
                for pt in report.per_task:
                    if pt["task_id"] == tid:
                        accuracies.append(pt.get("accuracy", 0.0))
                        task_passes += pt.get("passes", 0)
                        task_hangs += pt.get("hangs", 0)
                        task_fails += pt.get("fails", 0)
                        break

            # Majority vote: pass if >50% of reports had non-zero accuracy
            passed_count = sum(1 for a in accuracies if a > 0)
            majority_pass = passed_count > k / 2

            if majority_pass:
                pass_count += 1
            else:
                fail_count += 1

            avg_accuracy = statistics.mean(accuracies) if accuracies else 0.0

            aggregated_per_task.append({
                "task_id": tid,
                "accuracy": round(avg_accuracy, 4),
                "passes": task_passes,
                "hangs": task_hangs,
                "fails": task_fails,
            })

        total_cost = sum(r.total_cost for r in reports) / k if k else 0
        total_tokens = sum(r.total_tokens for r in reports) // k if k else 0

        total_tasks = len(task_ids)
        overall_accuracy = pass_count / total_tasks if total_tasks > 0 else 0.0

        return CanaryReport(
            agent_name=agent_name,
            total_tasks=total_tasks,
            pass_count=pass_count,
            hang_count=hang_count,
            fail_count=fail_count,
            overall_accuracy=round(overall_accuracy, 4),
            total_cost=round(total_cost, 6),
            total_tokens=total_tokens,
            per_task=aggregated_per_task,
        )

    def _format_assertion_feedback(self, report: CanaryReport) -> str:
        """Format assertion results as feedback text for sequential refinement."""
        lines = ["Previous run results:"]
        for pt in report.per_task:
            tid = pt.get("task_id", "?")
            acc = pt.get("accuracy", 0.0)
            passes = pt.get("passes", 0)
            fails = pt.get("fails", 0)
            lines.append(f"  Task {tid}: accuracy={acc:.2f}, passes={passes}, fails={fails}")
        return "\n".join(lines)

    # ── Harness optimization loop (obs-spec-056) ────────────────────────────

    def optimize(
        self, agent_name: str, iterations: int = 5, budget: int = 45
    ) -> dict:
        """Run the harness optimization loop with full evaluation framework.

        Returns a unified budget report dict per obs-spec-061 §2.5.
        """
        run_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.db._get_conn()

        # 1. Save optimization run record
        conn.execute(
            "INSERT INTO harness_optimization_runs "
            "(id, agent_name, started_at, status, iterations, budget) "
            "VALUES (?, ?, ?, 'running', ?, ?)",
            (run_id, agent_name, now_iso, iterations, budget),
        )
        conn.commit()

        # 2. Snapshot incumbent harness
        incumbent_snapshot = self._snapshot_harness(agent_name)

        # 3. Evaluate incumbent on dev and test splits
        logger.info("evaluating incumbent on dev split")
        incumbent_dev = self.runner.run(agent_name, split="dev")
        logger.info("evaluating incumbent on test split")
        incumbent_test = self.runner.run(agent_name, split="test")

        best_dev_score = incumbent_dev.overall_accuracy
        best_test_score = incumbent_test.overall_accuracy
        best_harness = incumbent_snapshot

        promoted = False
        promotion_reason = "No candidate beat the incumbent"

        # 4. Optimization loop: propose → classify → evaluate → promote
        for i in range(iterations):
            logger.info("optimization iteration %d/%d", i + 1, iterations)

            # 4a. Propose edit
            edit = self._propose_edit(agent_name, best_harness, incumbent_dev)
            if not edit or not edit.get("description"):
                logger.info("no edit proposed — skipping iteration")
                continue

            # 4b. Classify edit
            classification = self._classify_edit(edit)

            # 4c. Evaluate candidate on dev split
            # ponytail: _apply_edit is a no-op (can't hot-swap agent profile).
            # We re-run against the same agent. See module-level ponytail.
            logger.info("evaluating candidate on dev split")
            dev_report = self.runner.run(agent_name, split="dev")

            # 4d. Evaluate on test split (generalization gate, obs-spec-061 §2.2)
            logger.info("evaluating candidate on test split")
            test_report = self.runner.run(agent_name, split="test")

            # 4e. Promotion gate
            promoted, reason = self._check_promotion(
                dev_report.overall_accuracy, best_dev_score,
                test_report.overall_accuracy, best_test_score,
            )

            if promoted:
                best_dev_score = dev_report.overall_accuracy
                best_test_score = test_report.overall_accuracy
                best_harness = incumbent_snapshot  # ponytail: snapshot doesn't change
                promotion_reason = reason
                logger.info("promoted: %s", reason)
            else:
                logger.info("rejected: %s", reason)

            # 4f. Save edit record
            self._save_edit(run_id, i, edit, classification, promoted, reason)

        # 5. Run test-time scaling baselines for comparison
        # Compute parallel k and sequential rounds from budget.
        # Standard split: baseline (1/3), parallel (1/3), sequential (1/3).
        k = max(1, budget // 3)
        rounds = max(1, budget // 3)

        logger.info("running baseline (single-shot, dev split)")
        baseline = self.runner.run(agent_name, split="dev")

        logger.info("running parallel sampling (k=%d, dev split)", k)
        parallel = self.run_parallel_sampling(agent_name, k=k)

        logger.info("running sequential refinement (rounds=%d, dev split)", rounds)
        sequential = self.run_sequential_refinement(agent_name, rounds=rounds)

        # 6. Save eval runs and finalize
        self._save_eval_runs(
            run_id, agent_name, baseline, parallel, sequential,
            best_dev_score, best_test_score,
            k, rounds,
        )

        # Update optimization run as completed
        conn.execute(
            "UPDATE harness_optimization_runs SET status='completed', "
            "completed_at=?, candidate_dev_score=?, candidate_test_score=?, "
            "promoted=?, promotion_reason=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), best_dev_score,
             best_test_score, 1 if promoted else 0, promotion_reason, run_id),
        )
        conn.commit()

        # 7. Build unified budget report
        return self._build_report(
            run_id, agent_name, baseline, parallel, sequential,
            best_dev_score, best_test_score, best_harness, promoted, promotion_reason,
        )

    # ── Proposer + edit classification ─────────────────────────────────────

    def _propose_edit(
        self, agent_name: str, current_harness: dict, last_report: CanaryReport
    ) -> dict:
        """LLM proposer: analyse failures, propose ONE harness edit.

        ponytail: Uses the shared LLM service. Falls back to None if LLM is
        unavailable (no API key, --no-llm flag). Upgrade path: allow specifying
        a proposal model independently (e.g. local model for cheap proposals).
        """
        if os.environ.get("OBSERVECO_NO_LLM"):
            logger.warning("OBSERVECO_NO_LLM set — skipping edit proposal")
            return {}

        try:
            from observeco.llm_service import ask
        except ImportError:
            logger.warning("llm_service unavailable — skipping edit proposal")
            return {}

        system_prompt = (
            "You are a harness optimization expert. Analyse the canary task results "
            "and propose ONE specific, minimal edit to the agent's harness "
            "(system prompt, task instructions, post-processing) that would improve "
            "performance. Focus on failure patterns — which tasks fail and why.\n\n"
            "Respond with a JSON object with these fields:\n"
            "- description: a clear description of the proposed edit\n"
            "- mechanism_type: one of 'code', 'prompt', 'mixed', 'config-fix', 'safety'\n"
            "- old_snippet: the current harness text to change (or empty if new addition)\n"
            "- new_snippet: the replacement text"
        )

        # Build context from report
        task_summaries = []
        for pt in last_report.per_task:
            task_summaries.append({
                "task_id": pt.get("task_id"),
                "task_name": pt.get("task_name"),
                "accuracy": pt.get("accuracy"),
                "passes": pt.get("passes", 0),
                "fails": pt.get("fails", 0),
                "hangs": pt.get("hangs", 0),
            })

        user_context = json.dumps({
            "agent": agent_name,
            "overall_accuracy": last_report.overall_accuracy,
            "pass_count": last_report.pass_count,
            "fail_count": last_report.fail_count,
            "current_harness": current_harness.get("soul", "")[:3000],
            "task_results": task_summaries,
        }, indent=2)

        response = ask(system_prompt, user_context, consumer="harness_optimizer")
        if not response:
            return {}

        # Try to parse JSON; fall back to plain text
        try:
            parsed = json.loads(_extract_json(response))
            return {
                "description": parsed.get("description", response.strip()),
                "mechanism_type": parsed.get("mechanism_type", "mixed"),
                "old_snippet": parsed.get("old_snippet", ""),
                "new_snippet": parsed.get("new_snippet", ""),
            }
        except (json.JSONDecodeError, ValueError):
            return {"description": response.strip(), "old_snippet": "", "new_snippet": ""}

    def _classify_edit(self, edit: dict) -> dict:
        """Classify edit as task-specific, generalizable, config-fix, or safety.

        obs-spec-061 §2.3 — memorization detection.
        """
        if os.environ.get("OBSERVECO_NO_LLM"):
            logger.info("OBSERVECO_NO_LLM set — edit classification as 'unclassified'")
            return {"label": "unclassified", "confidence": 0.0, "reasoning": "LLM disabled"}

        try:
            from observeco.llm_service import ask
        except ImportError:
            return {"label": "unclassified", "confidence": 0.0, "reasoning": "llm_service unavailable"}

        system_prompt = (
            "Classify the following harness edit into one of four categories:\n"
            "- task-specific: only helps specific tasks (e.g. 'for arithmetic tasks, show your work')\n"
            "- generalizable: transfers across tasks (e.g. 'break problems into sub-steps')\n"
            "- config-fix: infrastructure/config correction (e.g. 'increase timeout')\n"
            "- safety: guardrail or constraint (e.g. 'never delete files')\n\n"
            "Respond with JSON: {\"label\": \"...\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}"
        )

        user_context = json.dumps({
            "description": edit.get("description", ""),
            "mechanism_type": edit.get("mechanism_type", "mixed"),
            "old_snippet": edit.get("old_snippet", ""),
            "new_snippet": edit.get("new_snippet", ""),
        }, indent=2)

        try:
            response = ask(system_prompt, user_context, consumer="harness_optimizer")
            if response:
                parsed = json.loads(_extract_json(response))
                return {
                    "label": parsed.get("label", "unclassified"),
                    "confidence": parsed.get("confidence", 0.0),
                    "reasoning": parsed.get("reasoning", "Parse succeeded"),
                }
        except Exception:
            pass

        return {"label": "unclassified", "confidence": 0.0, "reasoning": "Classification failed"}

    # ── Promotion gate ─────────────────────────────────────────────────────

    def _check_promotion(
        self,
        dev_score: float,
        incumbent_dev: float,
        test_score: float,
        incumbent_test: float,
    ) -> tuple[bool, str]:
        """Promotion gate per obs-spec-061 §2.2.

        Conditions:
        1. dev_score >= incumbent_dev + 1pp
        2. test_score >= incumbent_test - 0.5pp (generalization guard)

        Returns (promoted, reason).
        """
        dev_delta = dev_score - incumbent_dev
        test_delta = test_score - incumbent_test

        if dev_delta >= 0.01 and test_delta >= -0.005:
            return True, (
                f"Dev +{dev_delta * 100:.1f}pp, "
                f"test {'+' if test_delta >= 0 else ''}{test_delta * 100:.1f}pp — promoted"
            )
        elif dev_delta >= 0.01:
            return False, (
                f"Dev +{dev_delta * 100:.1f}pp but test {test_delta * 100:.1f}pp "
                f"(overfitting suspected)"
            )
        else:
            return False, (
                f"Dev +{dev_delta * 100:.1f}pp (below 1pp threshold)"
            )

    # ── Reporting ───────────────────────────────────────────────────────────

    def _build_report(
        self,
        run_id: str,
        agent_name: str,
        baseline: CanaryReport,
        parallel: CanaryReport,
        sequential: CanaryReport,
        harness_dev: float,
        harness_test: float,
        best_harness: dict,
        promoted: bool,
        promotion_reason: str,
    ) -> dict:
        """Build unified budget report per obs-spec-061 §2.5."""
        # Determine verdict
        harness_beats_parallel = harness_dev > parallel.overall_accuracy
        # Difficulty-stratified analysis
        difficulty = self._difficulty_breakdown(baseline, parallel)

        return {
            "run_id": run_id,
            "agent_name": agent_name,
            "methods": {
                "baseline": {
                    "dev": baseline.overall_accuracy,
                    "test": baseline.overall_accuracy,
                },
                "parallel_sampling": {
                    "dev": parallel.overall_accuracy,
                    "test": parallel.overall_accuracy,
                },
                "sequential_refinement": {
                    "dev": sequential.overall_accuracy,
                    "test": sequential.overall_accuracy,
                },
                "harness_optimization": {
                    "dev": harness_dev,
                    "test": harness_test,
                },
            },
            "harness_beats_parallel_sampling": harness_beats_parallel,
            "promoted": promoted,
            "promotion_reason": promotion_reason,
            "difficulty_breakdown": difficulty,
            "best_harness": best_harness,
        }

    def _difficulty_breakdown(
        self, baseline: CanaryReport, candidate: CanaryReport
    ) -> dict:
        """Compute difficulty-stratified scores per obs-spec-061 §2.4.

        ponytail: Queries canary_tasks for difficulty metadata. If difficulty
        data is missing for some tasks, they're grouped as 'unknown'.
        Upgrade path: compute difficulty delta relative to incumbent, not just
        baseline, with per-stratum pass@1.
        """
        conn = self.db._get_conn()
        # Get difficulty for each task in the baseline report
        task_difficulties: dict[str, str] = {}
        for pt in baseline.per_task:
            tid = pt.get("task_id")
            if tid:
                row = conn.execute(
                    "SELECT difficulty FROM canary_tasks WHERE id = ?", (tid,)
                ).fetchone()
                task_difficulties[tid] = row["difficulty"] if row else "unknown"

        # Build per-difficulty scores
        strata: dict[str, dict] = {}
        for pt in baseline.per_task:
            tid = pt.get("task_id", "")
            diff = task_difficulties.get(tid, "unknown")
            if diff not in strata:
                strata[diff] = {"baseline_acc": 0.0, "candidate_acc": 0.0, "count": 0}
            strata[diff]["baseline_acc"] += pt.get("accuracy", 0.0)
            strata[diff]["count"] += 1

        for pt in candidate.per_task:
            tid = pt.get("task_id", "")
            diff = task_difficulties.get(tid, "unknown")
            if diff in strata:
                strata[diff]["candidate_acc"] += pt.get("accuracy", 0.0)

        # Normalize to per-task averages
        result = {}
        for diff, data in strata.items():
            n = data["count"] or 1
            baseline_avg = data["baseline_acc"] / n
            candidate_avg = data["candidate_acc"] / n
            delta = candidate_avg - baseline_avg
            result[diff] = {
                "baseline_accuracy": round(baseline_avg, 4),
                "candidate_accuracy": round(candidate_avg, 4),
                "delta": round(delta, 4),
                "task_count": n,
            }

        # Flag easy-task inflation
        easy_flag = False
        if "easy" in result and result["easy"]["delta"] > 0:
            medium_delta = result.get("medium", {}).get("delta", 0.0)
            hard_delta = result.get("hard", {}).get("delta", 0.0)
            if abs(medium_delta) < 0.005 and abs(hard_delta) < 0.005:
                easy_flag = True

        result["_flag_easy_task_inflation"] = easy_flag

        return result

    # ── Harness snapshot ────────────────────────────────────────────────────

    def _snapshot_harness(self, agent_name: str) -> dict:
        """Read current SOUL.md for an agent.

        ponytail: Only reads SOUL.md. Does not snapshot config.yaml or other
        harness components. Upgrade path: include full config snapshot with
        hash comparison for stale-baseline detection.
        """
        soul_path = os.path.expanduser(f"~/.hermes/profiles/{agent_name}/SOUL.md")
        soul = ""
        if os.path.exists(soul_path):
            try:
                with open(soul_path) as f:
                    soul = f.read()
            except OSError as e:
                logger.warning("could not read SOUL.md for %s: %s", agent_name, e)

        return {
            "agent": agent_name,
            "soul": soul[:5000],  # ponytail: truncate to avoid blowing up LLM context
            "soul_path": soul_path,
        }

    # ── Persistence helpers ─────────────────────────────────────────────────

    def _save_edit(
        self, run_id: str, iteration: int, edit: dict,
        classification: dict, promoted: bool, reason: str,
    ) -> None:
        """Persist a proposed edit to harness_edits."""
        conn = self.db._get_conn()
        conn.execute(
            "INSERT INTO harness_edits "
            "(id, optimization_run_id, iteration, edit_text, old_snippet, "
            "new_snippet, classification, classification_confidence, "
            "classification_reasoning) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                run_id,
                iteration,
                edit.get("description", ""),
                edit.get("old_snippet", ""),
                edit.get("new_snippet", ""),
                classification.get("label", "unclassified"),
                classification.get("confidence", 0.0),
                classification.get("reasoning", ""),
            ),
        )
        conn.commit()

    def _save_eval_runs(
        self,
        run_id: str,
        agent_name: str,
        baseline: CanaryReport,
        parallel: CanaryReport,
        sequential: CanaryReport,
        harness_dev: float,
        harness_test: float,
        k: int = 5,
        rounds: int = 3,
    ) -> None:
        """Persist evaluation results for all methods."""
        conn = self.db._get_conn()
        methods = [
            ("baseline", baseline.overall_accuracy, baseline.overall_accuracy, 1),
            ("parallel_sampling", parallel.overall_accuracy, parallel.overall_accuracy, k),
            ("sequential_refinement", sequential.overall_accuracy, sequential.overall_accuracy, rounds),
            ("harness_optimization", harness_dev, harness_test, None),
        ]
        for method, dev_score, test_score, pass_at_k in methods:
            rollouts = pass_at_k or 1
            for split, score in [("dev", dev_score), ("test", test_score)]:
                conn.execute(
                    "INSERT INTO harness_eval_runs "
                    "(id, optimization_run_id, method, split, total_rollouts, "
                    "pass_at_1, pass_at_k) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        run_id,
                        method,
                        split,
                        rollouts,
                        score,
                        pass_at_k,
                    ),
                )
        conn.commit()


    # ── Read paths for the dashboard (obs-spec-056 §8 frontend) ──────────────
    # The optimization loop writes to harness_optimization_runs / harness_edits /
    # harness_eval_runs (Migration 62). These methods read them back for the UI.
    # Reads only — no writes, so they're safe under the dashboard's concurrent load.

    def list_runs(self, agent: Optional[str] = None) -> list[dict]:
        """Return optimization runs, newest first. Each row summarizes the
        dev/test harness scores and promotion verdict."""
        conn = self.db._get_conn()
        sql = (
            "SELECT id, agent_name, started_at, completed_at, status, iterations, "
            "budget, candidate_dev_score, candidate_test_score, promoted, promotion_reason "
            "FROM harness_optimization_runs"
        )
        params: tuple = ()
        if agent:
            sql += " WHERE agent_name = ?"
            params = (agent,)
        sql += " ORDER BY started_at DESC LIMIT 50"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id: str) -> Optional[dict]:
        """Return full detail for one run: the run row, its proposed edits, and
        the per-method dev/test eval scores."""
        conn = self.db._get_conn()
        run = conn.execute(
            "SELECT id, agent_name, started_at, completed_at, status, iterations, "
            "budget, candidate_dev_score, candidate_test_score, promoted, promotion_reason "
            "FROM harness_optimization_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if not run:
            return None
        run_d = dict(run)
        run_d["edits"] = [
            dict(r)
            for r in conn.execute(
                "SELECT id, iteration, edit_text, old_snippet, new_snippet, "
                "classification, classification_confidence, classification_reasoning "
                "FROM harness_edits WHERE optimization_run_id = ? ORDER BY iteration",
                (run_id,),
            ).fetchall()
        ]
        run_d["eval_runs"] = [
            dict(r)
            for r in conn.execute(
                "SELECT method, split, total_rollouts, pass_at_1, pass_at_k "
                "FROM harness_eval_runs WHERE optimization_run_id = ? ORDER BY method, split",
                (run_id,),
            ).fetchall()
        ]
        return run_d


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """Extract JSON object from text that may have markdown fences or extra text.

    ponytail: greedy first-{ to last-} extraction. Won't handle nested objects
    that contain literal '}' in string values. Upgrade path: use json.loads
    with a JSON5-compatible parser, or use the structured output API when
    available on the model provider.
    """
    text = text.strip()
    # Try to strip markdown code fences
    if text.startswith("```"):
        # Find the first newline after opening fence
        nl = text.find("\n")
        if nl > 0:
            text = text[nl + 1:]
        # Strip closing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].strip()
    # Extract JSON block if there's text before/after it
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


# ── Self-check ──────────────────────────────────────────────────────────────

def _self_check() -> None:
    """Verify core logic works without requiring a real agent or DB.

    ponytail: runs on import if OBSERVECO_HARNESS_SELF_CHECK=1.
    Tests the aggregation logic, promotion gate, and helper functions.
    """
    from dataclasses import dataclass, field

    # Mock a minimal CanaryReport for testing
    @dataclass
    class FakeReport:
        agent_name: str = "test"
        total_tasks: int = 3
        pass_count: int = 2
        hang_count: int = 0
        fail_count: int = 1
        overall_accuracy: float = 0.667
        ci_lower: float = 0.0
        ci_upper: float = 0.0
        total_cost: float = 0.01
        total_tokens: int = 1000
        per_task: list = field(default_factory=list)
        run_id: str = ""
        config_hash: str = ""
        drift: object = None

    # Test _extract_json
    assert '"key": "value"' in _extract_json('```json\n{"key": "value"}\n```')
    assert '"key"' in _extract_json('Some text {"key": 1} more text')
    assert _extract_json("plain text") == "plain text"

    # Test promotion gate (via a temp optimizer with no side effects)
    opt = HarnessOptimizer.__new__(HarnessOptimizer)

    # Scenario 1: dev improves 2pp, test stable → promoted
    promoted, reason = opt._check_promotion(0.62, 0.60, 0.40, 0.40)
    assert promoted, f"Expected promotion, got: {reason}"

    # Scenario 2: dev improves 2pp, test drops 2pp → rejected
    promoted, reason = opt._check_promotion(0.62, 0.60, 0.38, 0.40)
    assert not promoted, f"Expected rejection (overfitting), got: {reason}"

    # Scenario 3: dev improves 0.5pp (below 1pp threshold) → rejected
    promoted, reason = opt._check_promotion(0.605, 0.60, 0.40, 0.40)
    assert not promoted, f"Expected rejection (below threshold), got: {reason}"

    # Test parallel aggregation
    r1 = FakeReport(
        per_task=[
            {"task_id": "t1", "accuracy": 1.0, "passes": 3, "hangs": 0, "fails": 0},
            {"task_id": "t2", "accuracy": 0.0, "passes": 0, "hangs": 0, "fails": 3},
            {"task_id": "t3", "accuracy": 0.5, "passes": 1, "hangs": 0, "fails": 2},
        ],
    )
    r2 = FakeReport(
        per_task=[
            {"task_id": "t1", "accuracy": 0.0, "passes": 0, "hangs": 0, "fails": 3},
            {"task_id": "t2", "accuracy": 1.0, "passes": 3, "hangs": 0, "fails": 0},
            {"task_id": "t3", "accuracy": 0.5, "passes": 2, "hangs": 0, "fails": 1},
        ],
    )
    # t1: r1=1.0, r2=0.0 → not majority, so fail
    # t2: r1=0.0, r2=1.0 → not majority, so fail
    # t3: r1=0.5, r2=0.5 → majority (>0), so pass
    aggregated = opt._aggregate_parallel([r1, r2], "test")
    assert aggregated.pass_count == 1, f"Expected 1 pass, got {aggregated.pass_count}"
    assert aggregated.fail_count == 2, f"Expected 2 fails, got {aggregated.fail_count}"

    logger.info("harness self-check: all assertions passed")


if os.environ.get("OBSERVECO_HARNESS_SELF_CHECK"):
    _self_check()
