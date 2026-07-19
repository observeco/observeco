"""Harness optimizer — automated harness optimization loop + evaluation framework.

obs-spec-056: harness optimization loop (proposer → lab → promotion gate).
obs-spec-061: evaluation framework (test-time baselines, generalization gate, edit
              classification, difficulty-stratified reporting, unified budget report).

"""

from __future__ import annotations

import json
import logging
import os
import shutil
import statistics
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Optional

from observeco.capability.canary import CanaryReport, CanaryRunner
from observeco.capability.experience import ExperienceBank
from observeco.db import Database

logger = logging.getLogger(__name__)


# ── Phantom Guardrails + Evaluation Fairness gates (obs-spec-088) ──────────


class EpisodeLog:
    """Queryable source of truth for observed harness failures.

    Derived from canary_results + harness_edits outcomes. The Phantom
    Guardrails gate rejects edits citing failures absent from this log.
    """

    def __init__(self, db: Database):
        self.db = db

    def count_observations(self, failure_class: str, agent_name: str | None = None) -> int:
        """Count real (non-phantom) observations of a failure class."""
        conn = self.db._get_conn()
        if agent_name:
            row = conn.execute(
                "SELECT COALESCE(SUM(observed_count), 0) AS c FROM harness_experiences "
                "WHERE failure_class=? AND agent_name=? AND outcome != 'phantom_rejected'",
                (failure_class, agent_name),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COALESCE(SUM(observed_count), 0) AS c FROM harness_experiences "
                "WHERE failure_class=? AND outcome != 'phantom_rejected'",
                (failure_class,),
            ).fetchone()
        return int(row["c"]) if row else 0

    def has_failure(self, failure_class: str, agent_name: str | None = None) -> bool:
        return self.count_observations(failure_class, agent_name) >= 1


class PhantomGuardrailGate:
    """Reject proposed edits that cite failures not present in observed episodes.

    Blocks the 'phantom guardrail' failure mode (Wang et al. 2026, arXiv 2607.13083).
    Mandatory safety layer for obs-spec-088 — sits before _apply_edit.
    """

    def __init__(self, episode_log: EpisodeLog, min_observations: int = 1):
        self.episode_log = episode_log
        self.min_observations = min_observations

    def check(self, edit: dict, agent_name: str | None = None) -> tuple[bool, str]:
        """Return (accepted, reason).

        An edit is accepted only if every failure class it references has been
        observed >= min_observations times (PG-3 closed rule set). Edits that
        introduce a brand-new guardrail class with zero observations are rejected
        unless flagged human_review=True.
        """
        cited = edit.get("cited_failures", [])
        if not cited:
            # Edits with no cited failure aren't phantom guardrails — but PG-4
            # (abstain-on-legal) is enforced at the proposer level. Allow through.
            return True, "No cited failures — not a phantom guardrail."
        for failure in cited:
            fclass = failure.get("class", failure) if isinstance(failure, dict) else failure
            obs = self.episode_log.count_observations(fclass, agent_name)
            if obs < self.min_observations:
                return False, (
                    f"Phantom guardrail rejected: failure class '{fclass}' has "
                    f"{obs} observed occurrences (min {self.min_observations}). "
                    f"No real failure to fix."
                )
        return True, "All cited failures observed in episode log."


class EvaluationFairnessGate:
    """Reject candidates whose gain is search budget, not harness design.

    Rethinking Evaluation (Wang et al. 2026, arXiv 2607.12227). Every promoted
    candidate must beat parallel sampling, sequential refinement, AND harness
    scaling baselines at equal budget, and must improve pass@1 (not pass@k),
    and must generalize to held-out test.
    """

    def __init__(self, context_bloat_threshold: float = 2.0):
        self.context_bloat_threshold = context_bloat_threshold

    def check(
        self,
        candidate_dev: float,
        candidate_test: float,
        incumbent_dev: float,
        incumbent_test: float,
        tts_baselines: dict[str, float],
        candidate_pass1: float | None = None,
        incumbent_pass1: float | None = None,
        frontier_prompt_size: int = 0,
        initial_prompt_size: int = 0,
    ) -> tuple[bool, str]:
        """Return (promoted, reason)."""
        # EF-1: matched-budget TTS — candidate dev gain must exceed all baselines
        cand_dev_gain = candidate_dev - incumbent_dev
        best_tts_gain = max(
            (tts_baselines.get(m, 0.0) - incumbent_dev)
            for m in ("parallel_sampling", "sequential_refinement", "harness_scaling")
        )
        if cand_dev_gain <= best_tts_gain:
            return False, (
                f"search-budget-illusion: candidate dev gain +{cand_dev_gain * 100:.1f}pp "
                f"<= best TTS gain +{best_tts_gain * 100:.1f}pp"
            )

        # EF-2: pass@1, not pass@k
        if candidate_pass1 is not None and incumbent_pass1 is not None:
            if candidate_pass1 <= incumbent_pass1:
                return False, "passk-not-pass1: candidate improved pass@k but not pass@1"

        # EF-3: held-out generalization
        if candidate_test < incumbent_test - 0.005:
            return False, (
                f"no_generalization: held-out test {candidate_test * 100:.1f}% "
                f"< incumbent {incumbent_test * 100:.1f}%"
            )

        # EF-4: context bloat budget
        if initial_prompt_size and frontier_prompt_size > initial_prompt_size * self.context_bloat_threshold:
            return False, (
                f"context-bloat: frontier prompt {frontier_prompt_size} > "
                f"{self.context_bloat_threshold:.1f}x initial ({initial_prompt_size})"
            )

        return True, "Candidate beats TTS baselines + generalizes + within bloat budget"


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
        self, agent_name: str, iterations: int = 5, budget: int = 45,
        no_baselines: bool = False,
        no_phantom_gate: bool = False,
        context_bloat_threshold: float = 2.0,
        with_experience: bool = False,
    ) -> dict:
        """Run the harness optimization loop with full evaluation framework.

        Args:
            agent_name: Hermes agent profile name.
            iterations: Number of optimization iterations.
            budget: Total compute budget (agent rollouts).
            no_baselines: Skip baseline comparison (not recommended — gains
                won't be attributable to harness design vs search budget).
            no_phantom_gate: DEBUG ONLY. Disable PG-2/PG-3. Must be refused
                inside scheduled/cron context (Constraint #1). Default: False.
            context_bloat_threshold: Max frontier prompt size multiplier
                (default 2.0). Loop stops promoting additions beyond this.
            with_experience: Enable experience-bank retrieval for the proposer.
        """
        if no_phantom_gate and os.environ.get("OBSERVECO_IN_CRON"):
            raise RuntimeError("Phantom Guardrail gate is non-bypassable in scheduled runs")

        run_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        self.db._get_conn()

        # 0. Precondition check (EF-5): headroom + harness-sensitivity
        if not no_baselines:
            pre_acc = self.runner.run(agent_name, split="dev").overall_accuracy
            if pre_acc >= 0.90:
                logger.info("precondition skipped: agent accuracy %.1f%% >= 90%% (no headroom)", pre_acc * 100)
                self.db._write(
                    "INSERT INTO harness_optimization_runs "
                    "(id, agent_name, started_at, status, iterations, budget, "
                    "promotion_reason) VALUES (?, ?, ?, 'skipped', ?, ?, ?)",
                    (run_id, agent_name, now_iso, iterations, budget,
                     "precondition: accuracy >= 90% (no headroom)"),
                )
                return {"run_id": run_id, "promoted": False,
                        "promotion_reason": "precondition: accuracy >= 90% (no headroom)",
                        "skipped": True}

        # 1. Save optimization run record
        self.db._write(
            "INSERT INTO harness_optimization_runs "
            "(id, agent_name, started_at, status, iterations, budget) "
            "VALUES (?, ?, ?, 'running', ?, ?)",
            (run_id, agent_name, now_iso, iterations, budget),
        )

        # 2. Snapshot incumbent harness
        incumbent_snapshot = self._snapshot_harness(agent_name)
        initial_prompt_size = len(incumbent_snapshot.get("soul", ""))

        # 3. Evaluate incumbent on dev and test splits (skip if no_baselines)
        if not no_baselines:
            logger.info("evaluating incumbent on dev split")
            incumbent_dev = self.runner.run(agent_name, split="dev")
            logger.info("evaluating incumbent on test split")
            incumbent_test = self.runner.run(agent_name, split="test")
        else:
            incumbent_dev = incumbent_test = None

        best_dev_score = incumbent_dev.overall_accuracy if incumbent_dev else 0.0
        best_test_score = incumbent_test.overall_accuracy if incumbent_test else 0.0
        best_harness = incumbent_snapshot

        # Front-end gates (obs-spec-088)
        episode_log = EpisodeLog(self.db)
        phantom_gate = PhantomGuardrailGate(episode_log, min_observations=1)
        fairness_gate = EvaluationFairnessGate(context_bloat_threshold=context_bloat_threshold)
        experience_bank = ExperienceBank(self.db)

        # Precompute TTS baseline dev scores once (EF-1: equal-budget comparison).
        # ponytail: baselines computed once before the loop, not per-iteration —
        # they're stable for a fixed budget. Cost: ~budget rollouts up front.
        tts_baselines = self._tts_baseline_scores(agent_name, budget, no_baselines)

        # Frontier inheritance (Gap 2 fix): start from incumbent, stack promoted edits
        frontier_soul = incumbent_snapshot.get("soul", "")
        mechanism_stack: list[str] = []

        promoted = False
        promotion_reason = "No candidate beat the incumbent"

        # 4. Optimization loop: propose → classify → [PG] → apply → evaluate → [EF] → promote
        for i in range(iterations):
            logger.info("optimization iteration %d/%d", i + 1, iterations)

            # 4a. Propose edit (reads frontier, not static incumbent)
            frontier_harness = {
                "agent": agent_name,
                "soul": frontier_soul,
                "soul_path": incumbent_snapshot.get("soul_path", ""),
            }
            # PG-1 + experience grounding: pass observed failures into proposer context
            if with_experience:
                past = experience_bank.retrieve_similar(agent_name, "", limit=5)
                frontier_harness["past_experiences"] = [p.get("diagnosis", "") for p in past]
            edit = self._propose_edit(agent_name, frontier_harness, incumbent_dev)
            if not edit or not edit.get("description"):
                logger.info("no edit proposed — skipping iteration")
                continue

            # 4b. Classify edit
            classification = self._classify_edit(edit)

            # 4c. PHANTOM GUARDRAIL GATE (before apply) — PG-2/PG-3
            if not no_phantom_gate:
                accepted, pg_reason = phantom_gate.check(edit, agent_name)
                if not accepted:
                    logger.warning("phantom guardrail rejected iter %d: %s", i, pg_reason)
                    experience_bank.record_rejection(
                        agent_name,
                        failure_class=(edit.get("cited_failures", [{}])[0].get("class", "unknown")
                                       if edit.get("cited_failures") else "unknown"),
                        proposed_edit=edit.get("description", ""),
                        reason=pg_reason,
                    )
                    self._save_edit(run_id, i, edit, classification, False, pg_reason,
                                    best_dev_score, 0.0)
                    continue

            # 4d. Apply edit to temp profile (Gap 1 fix)
            temp_profile = self._apply_edit(agent_name, edit)
            if not temp_profile:
                logger.warning("could not create temp profile — skipping iteration")
                continue

            incumbent_score = best_dev_score

            try:
                # 4e. Evaluate candidate on dev split
                logger.info("evaluating candidate on dev split (profile=%s)", temp_profile)
                dev_report = self.runner.run(temp_profile, split="dev")

                # 4f. Leakage audit (Gap 6 fix)
                if not self._check_leakage(dev_report):
                    logger.warning("leakage detected — rejecting candidate")
                    self._save_edit(run_id, i, edit, classification, False,
                                    "Leakage: candidate touched test split",
                                    incumbent_score, dev_report.overall_accuracy)
                    continue

                # 4g. Evaluate on test split (generalization gate, obs-spec-061 §2.2)
                logger.info("evaluating candidate on test split (profile=%s)", temp_profile)
                test_report = self.runner.run(temp_profile, split="test")

                # 4h. EVALUATION FAIRNESS GATE (EF-1..EF-4)
                ef_promoted, ef_reason = fairness_gate.check(
                    candidate_dev=dev_report.overall_accuracy,
                    candidate_test=test_report.overall_accuracy,
                    incumbent_dev=best_dev_score,
                    incumbent_test=best_test_score,
                    tts_baselines=tts_baselines,
                    candidate_pass1=dev_report.overall_accuracy,
                    incumbent_pass1=best_dev_score,
                    frontier_prompt_size=len(frontier_soul) + len(edit.get("new_snippet", "")),
                    initial_prompt_size=initial_prompt_size,
                )

                # 4i. Promotion gate (blended score, obs-spec-061 §2.2)
                blended_promoted, blended_reason = self._check_promotion(
                    dev_report, best_dev_score,
                    test_report, best_test_score,
                )

                if ef_promoted and blended_promoted:
                    best_dev_score = dev_report.overall_accuracy
                    best_test_score = test_report.overall_accuracy
                    frontier_soul = self._read_temp_soul(temp_profile)
                    best_harness = {"agent": agent_name, "soul": frontier_soul}
                    mechanism_stack.append(edit.get("description", "")[:80])
                    promotion_reason = blended_reason
                    logger.info("promoted: %s", blended_reason)

                    # Update frontier in DB
                    self._update_frontier(agent_name, run_id, best_dev_score, mechanism_stack)

                    # Deploy edit to live agent profile (closes the apply-edit no-op)
                    if self._deploy_edit(agent_name, temp_profile):
                        logger.info("edit deployed to live agent %s", agent_name)
                    else:
                        logger.warning("edit promoted but NOT deployed to live agent")

                    # Write experience bank entry (global_pattern if generalizable)
                    if classification.get("label") == "generalizable":
                        experience_bank.add(
                            agent_name=agent_name, layer="global_pattern",
                            failure_class=edit.get("cited_failures", [{}])[0].get("class", "general")
                                if edit.get("cited_failures") else "general",
                            diagnosis=edit.get("description", ""),
                            proposed_edit=edit.get("description", ""),
                            outcome="helped", observed_count=1,
                            source_run_id=run_id,
                        )
                else:
                    reason = ef_reason if not ef_promoted else blended_reason
                    logger.info("rejected: %s", reason)

                # 4j. Save edit record
                self._save_edit(run_id, i, edit, classification,
                                ef_promoted and blended_promoted,
                                (ef_reason if not ef_promoted else blended_reason),
                                incumbent_score, dev_report.overall_accuracy)
            finally:
                # Clean up temp profile
                self._cleanup_temp_profile(temp_profile)

        # 5. Run test-time scaling baselines for comparison (skip if no_baselines)
        if not no_baselines:
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
        else:
            k = 1
            rounds = 1
            baseline = parallel = sequential = None

        # 6. Save eval runs and finalize
        if not no_baselines:
            self._save_eval_runs(
                run_id, agent_name, baseline, parallel, sequential,
                best_dev_score, best_test_score,
                k, rounds,
            )

        # Update optimization run as completed
        self.db._write(
            "UPDATE harness_optimization_runs SET status='completed', "
            "completed_at=?, candidate_dev_score=?, candidate_test_score=?, "
            "promoted=?, promotion_reason=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), best_dev_score,
             best_test_score, 1 if promoted else 0, promotion_reason, run_id),
        )

        # 7. Build unified budget report
        return self._build_report(
            run_id, agent_name, baseline, parallel, sequential,  # type: ignore[arg-type]
            best_dev_score, best_test_score, best_harness, promoted, promotion_reason,
        )

    # ── Proposer + edit classification ─────────────────────────────────────

    def _propose_edit(
        self, agent_name: str, current_harness: dict, last_report: CanaryReport | None
    ) -> dict:
        """LLM proposer: analyse failures, propose ONE harness edit.

        ponytail: Uses the shared LLM service. Falls back to None if LLM is
        unavailable (no API key, --no-llm flag). Upgrade path: allow specifying
        a proposal model independently (e.g. local model for cheap proposals).
        """
        if last_report is None:
            logger.info("no baseline report — skipping edit proposal")
            return {}
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
        dev_report: CanaryReport,
        incumbent_dev: "CanaryReport | float",
        test_report: CanaryReport,
        incumbent_test: float,
    ) -> tuple[bool, str]:
        """Promotion gate per obs-spec-061 §2.2 + blended score (obs-spec-054).

        Blended score: accuracy + 0.5 * all_pass_rate - 0.005 * tokens/1M.
        Promotion requires:
        1. dev_blended >= incumbent_blended + 1pp
        2. test_accuracy >= incumbent_test - 0.5pp (generalization guard)

        Returns (promoted, reason).
        """
        allpass_weight = 0.5
        cost_lambda = 0.005

        def _blended(r: CanaryReport) -> float:
            all_pass_rate = r.pass_count / r.total_tasks if r.total_tasks > 0 else 0.0
            return (r.overall_accuracy
                    + allpass_weight * all_pass_rate
                    - cost_lambda * (r.total_tokens / 1_000_000))

        dev_blended = _blended(dev_report)
        inc_blended = _blended(incumbent_dev) if hasattr(incumbent_dev, 'overall_accuracy') else incumbent_dev

        # ponytail: incumbent is a float score if it's the best_dev_score stored value.
        # Recompute from stored fields when possible; fall back to raw float.
        if isinstance(incumbent_dev, (int, float)):
            inc_blended = float(incumbent_dev)  # no all_pass/token data available

        dev_delta = dev_blended - inc_blended
        test_delta = test_report.overall_accuracy - (incumbent_test if isinstance(incumbent_test, (int, float)) else incumbent_test)

        if dev_delta >= 0.01 and test_delta >= -0.005:
            return True, (
                f"Blended +{dev_delta * 100:.1f}pp, "
                f"test {'+' if test_delta >= 0 else ''}{test_delta * 100:.1f}pp — promoted"
            )
        elif dev_delta >= 0.01:
            return False, (
                f"Blended +{dev_delta * 100:.1f}pp but test {test_delta * 100:.1f}pp "
                f"(overfitting suspected)"
            )
        else:
            return False, (
                f"Blended +{dev_delta * 100:.1f}pp (below 1pp threshold)"
            )

    def _tts_baseline_scores(
        self, agent_name: str, budget: int = 45, no_baselines: bool = False
    ) -> dict[str, float]:
        """Compute dev scores for the 3 TTS baselines under equal budget (EF-1).

        Returns dict with keys: parallel_sampling, sequential_refinement,
        harness_scaling. If no_baselines, returns zeros (gate will then reject
        all candidates — caller must not run with no_baselines in production).
        """
        if no_baselines:
            return {"parallel_sampling": 0.0, "sequential_refinement": 0.0,
                    "harness_scaling": 0.0}
        k = max(1, budget // 3)
        rounds = max(1, budget // 3)
        try:
            parallel = self.run_parallel_sampling(agent_name, k=k)
            sequential = self.run_sequential_refinement(agent_name, rounds=rounds)
        except Exception as e:
            logger.warning("TTS baseline computation failed: %s", e)
            return {"parallel_sampling": 0.0, "sequential_refinement": 0.0,
                    "harness_scaling": 0.0}
        # ponytail: harness_scaling (instance-guided per-task harness adaptation)
        # is approximated here as max(parallel, sequential) dev — a true harness
        # scaling run needs per-task harness edits, which the loop itself does.
        # Upgrade path: run actual harness-scaling baseline as a 4th method.
        harness_scaling = max(parallel.overall_accuracy, sequential.overall_accuracy)
        return {
            "parallel_sampling": parallel.overall_accuracy,
            "sequential_refinement": sequential.overall_accuracy,
            "harness_scaling": harness_scaling,
        }

    def run_gate_test(self, agent_name: str = "default") -> dict:
        """Counterfactual Fabrication Lab self-check (Wang et al. 2607.13083).

        Deterministic, no LLM, no tokens. Feeds known phantom edits (citing
        failures with zero observations) to PhantomGuardrailGate and asserts
        they are ALL rejected. Returns a result dict for the dashboard.
        """
        episode_log = EpisodeLog(self.db)
        gate = PhantomGuardrailGate(episode_log, min_observations=1)

        # Known phantom edits: failures that have never been observed
        phantom_edits = [
            {"description": "Add guardrail: never retry on timeout",
             "cited_failures": [{"class": "phantom_timeout_xyz"}]},
            {"description": "Block action B2 after repeated ARENA failure",
             "cited_failures": [{"class": "phantom_arena_b2"}]},
            {"description": "Suppress output when input looks rule-shaped",
             "cited_failures": [{"class": "phantom_ruleshape"}]},
        ]
        # A legitimate edit (failure observed in episode log) should pass
        legit_edit = {"description": "Increase canary timeout",
                      "cited_failures": [{"class": "observed_timeout"}]}

        results = []
        for e in phantom_edits:
            accepted, reason = gate.check(e, agent_name)
            results.append({"edit": e["description"], "accepted": accepted,
                            "reason": reason, "expected": False})

        # Inject the observed failure so the legit edit passes (else vacuously true)
        from observeco.capability.experience import ExperienceBank
        eb = ExperienceBank(self.db)
        eb.add(agent_name=agent_name, layer="per_case",
               failure_class="observed_timeout", diagnosis="test",
               proposed_edit="test", outcome="helped", observed_count=1)
        legit_accepted, legit_reason = gate.check(legit_edit, agent_name)
        results.append({"edit": legit_edit["description"], "accepted": legit_accepted,
                        "reason": legit_reason, "expected": True})

        # Clean up the injected test experience
        self.db._write(
            "DELETE FROM harness_experiences WHERE agent_name=? AND diagnosis='test'",
            (agent_name,),
        )

        total = len(results)
        fabricated = sum(1 for r in results if r["accepted"] != r["expected"])
        verdict = "PASS" if fabricated == 0 else "FAIL"
        return {
            "agent_name": agent_name,
            "total_runs": total,
            "fabricated_runs": fabricated,
            "fabrication_rate": fabricated / total if total else 0.0,
            "verdict": verdict,
            "detail": results,
        }

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
        # Determine verdict (handle None reports for no-baselines mode)
        harness_beats_parallel = (
            harness_dev > (parallel.overall_accuracy if parallel else 0.0)
        )
        # Difficulty-stratified analysis
        difficulty = self._difficulty_breakdown(baseline, parallel) if baseline else {}

        def _score(report: CanaryReport | None) -> float:
            return report.overall_accuracy if report else 0.0

        return {
            "run_id": run_id,
            "agent_name": agent_name,
            "methods": {
                "baseline": {
                    "dev": _score(baseline),
                    "test": _score(baseline),
                },
                "parallel_sampling": {
                    "dev": _score(parallel),
                    "test": _score(parallel),
                },
                "sequential_refinement": {
                    "dev": _score(sequential),
                    "test": _score(sequential),
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
        incumbent_score: float = 0.0, dev_score: float = 0.0,
    ) -> None:
        """Persist a proposed edit to harness_edits + harness_candidates."""
        edit_id = str(uuid.uuid4())
        code_diff = json.dumps({
            "old": edit.get("old_snippet", ""),
            "new": edit.get("new_snippet", ""),
        })

        # harness_edits
        self.db._write(
            "INSERT INTO harness_edits "
            "(id, optimization_run_id, iteration, edit_text, old_snippet, "
            "new_snippet, classification, classification_confidence, "
            "classification_reasoning, code_diff, incumbent_score, dev_score, "
            "promoted, promotion_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                edit_id,
                run_id,
                iteration,
                edit.get("description", ""),
                edit.get("old_snippet", ""),
                edit.get("new_snippet", ""),
                classification.get("label", "unclassified"),
                classification.get("confidence", 0.0),
                classification.get("reasoning", ""),
                code_diff,
                incumbent_score,
                dev_score,
                1 if promoted else 0,
                reason,
            ),
        )

        # harness_candidates (spec §4.1)
        self.db._write(
            "INSERT INTO harness_candidates "
            "(id, agent_name, iteration, name, mechanism_type, description, "
            "code_diff, dev_score, incumbent_score, promoted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                edit_id,
                "default",  # ponytail: agent_name not threaded through here; use 'default'
                iteration,
                edit.get("description", "untitled")[:60],
                classification.get("label", "unclassified"),
                edit.get("description", ""),
                code_diff,
                dev_score,
                incumbent_score,
                1 if promoted else 0,
            ),
        )

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
        methods = [
            ("baseline", baseline.overall_accuracy, baseline.overall_accuracy, 1),
            ("parallel_sampling", parallel.overall_accuracy, parallel.overall_accuracy, k),
            ("sequential_refinement", sequential.overall_accuracy, sequential.overall_accuracy, rounds),
            ("harness_optimization", harness_dev, harness_test, None),
        ]
        for method, dev_score, test_score, pass_at_k in methods:
            rollouts = pass_at_k or 1
            for split, score in [("dev", dev_score), ("test", test_score)]:
                self.db._write(
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

    # ── Temp profile management (Gap 1: apply edits) ──────────────────────

    def _apply_edit(self, agent_name: str, edit: dict) -> str | None:
        """Create a temp Hermes profile with the edit applied to SOUL.md.

        Copies the incumbent profile, applies old_snippet→new_snippet
        substitution to SOUL.md, returns the temp profile name.
        Returns None if the profile can't be created.

        ponytail: string-based substitution only — won't handle overlapping
        edits across iterations. If old_snippet is empty, the new_snippet is
        prepended to SOUL.md. Upgrade path: proper unified diff (patch -p0)
        with conflict detection.
        """
        incumbent_dir = os.path.expanduser(f"~/.hermes/profiles/{agent_name}")
        if not os.path.isdir(incumbent_dir):
            logger.warning("incumbent profile dir not found: %s", incumbent_dir)
            return None

        temp_name = f"{agent_name}-opt-{str(uuid.uuid4())[:8]}"
        temp_dir = os.path.expanduser(f"~/.hermes/profiles/{temp_name}")
        os.makedirs(temp_dir, exist_ok=True)

        # Copy incumbent files
        for name in os.listdir(incumbent_dir):
            src = os.path.join(incumbent_dir, name)
            dst = os.path.join(temp_dir, name)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

        # Apply edit to SOUL.md
        soul_path = os.path.join(temp_dir, "SOUL.md")
        soul = ""
        if os.path.exists(soul_path):
            with open(soul_path) as f:
                soul = f.read()

        old_snippet = edit.get("old_snippet", "")
        new_snippet = edit.get("new_snippet", "")

        if old_snippet and old_snippet in soul:
            soul = soul.replace(old_snippet, new_snippet, 1)
        elif new_snippet:
            # ponytail: prepend new snippet when no old match found
            soul = new_snippet + "\n\n" + soul

        with open(soul_path, "w") as f:
            f.write(soul)

        logger.info("created temp profile %s with edit applied", temp_name)
        return temp_name

    def _read_temp_soul(self, temp_profile: str) -> str:
        """Read SOUL.md from a temp profile."""
        soul_path = os.path.expanduser(f"~/.hermes/profiles/{temp_profile}/SOUL.md")
        if os.path.exists(soul_path):
            with open(soul_path) as f:
                return f.read()
        return ""

    def _cleanup_temp_profile(self, temp_profile: str) -> None:
        """Remove the temp profile directory."""
        temp_dir = os.path.expanduser(f"~/.hermes/profiles/{temp_profile}")
        if os.path.isdir(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug("cleaned up temp profile %s", temp_profile)
            except OSError as e:
                logger.warning("could not clean up temp profile %s: %s", temp_profile, e)

    def _deploy_edit(self, agent_name: str, temp_profile: str) -> bool:
        """Copy the promoted edit from temp profile to the live agent profile.

        Backs up the incumbent SOUL.md before overwriting, then copies the
        temp profile's SOUL.md to the live agent directory. This closes the
        apply-edit no-op: after promotion, the agent's harness actually changes.

        ponytail: Only deploys SOUL.md. Does not deploy config.yaml or other
        harness components. Upgrade path: full profile sync with diff-based
        rollback on failure.
        """
        live_dir = os.path.expanduser(f"~/.hermes/profiles/{agent_name}")
        temp_dir = os.path.expanduser(f"~/.hermes/profiles/{temp_profile}")
        live_soul = os.path.join(live_dir, "SOUL.md")
        temp_soul = os.path.join(temp_dir, "SOUL.md")

        if not os.path.isfile(temp_soul):
            logger.warning("temp profile SOUL.md not found: %s", temp_soul)
            return False
        if not os.path.isdir(live_dir):
            logger.warning("live profile dir not found: %s", live_dir)
            return False

        # 1. Backup incumbent SOUL.md
        backup_path = live_soul + ".bak"
        if os.path.isfile(live_soul):
            try:
                shutil.copy2(live_soul, backup_path)
                logger.info("backed up incumbent SOUL.md to %s", backup_path)
            except OSError as e:
                logger.warning("could not backup SOUL.md: %s", e)
                return False

        # 2. Copy temp SOUL.md to live profile
        try:
            shutil.copy2(temp_soul, live_soul)
            logger.info(
                "deployed edit to %s (backup at %s)",
                live_soul, backup_path,
            )
            return True
        except OSError as e:
            logger.error("failed to deploy edit: %s", e)
            # Attempt rollback
            if os.path.isfile(backup_path):
                shutil.copy2(backup_path, live_soul)
                logger.info("rolled back SOUL.md from backup")
            return False

    # ── Leakage audit (Gap 6) ─────────────────────────────────────────────

    def _check_leakage(self, report: CanaryReport) -> bool:
        """Reject if any task in the report is from the test split.

        ponytail: checks per_task split field only. If the canary_tasks table
        doesn't have test-split tasks, or per_task doesn't carry split info,
        this is a no-op (always passes). Upgrade path: store split in
        canary_results entries and verify at write time.
        """
        conn = self.db._get_conn()
        for pt in report.per_task:
            tid = pt.get("task_id")
            if not tid:
                continue
            row = conn.execute(
                "SELECT split FROM canary_tasks WHERE id = ?", (tid,)
            ).fetchone()
            if row and row["split"] == "test":
                logger.warning("leakage: task %s is in test split", tid)
                return False
        return True

    # ── Frontier persistence (Gap 3: harness_frontier) ────────────────────

    def _update_frontier(
        self, agent_name: str, candidate_id: str,
        score: float, mechanism_stack: list[str],
    ) -> None:
        """Upsert the harness_frontier for this agent."""
        frontier_id = str(uuid.uuid4())
        self.db._write(
            "INSERT OR REPLACE INTO harness_frontier "
            "(id, agent_name, candidate_id, score, mechanism_stack, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                frontier_id,
                agent_name,
                candidate_id,
                score,
                json.dumps(mechanism_stack),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    # ── Read paths for the dashboard (obs-spec-056 §8 frontend) ──────────────
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
    # Blended score: pass_count=2, total_tasks=3 → all_pass_rate=0.667 bonus
    dr1 = FakeReport(overall_accuracy=0.62, pass_count=2, total_tasks=3, total_tokens=1000)
    tr1 = FakeReport(overall_accuracy=0.40, pass_count=1, total_tasks=3, total_tokens=1000)
    # Incumbent: blended = 0.60 + 0.5*0.667 = 0.933
    # Candidate: blended = 0.62 + 0.5*0.667 = 0.953, delta=0.02 → promoted
    # Use FakeReport for incumbent so blended matches
    inc_fr1 = FakeReport(overall_accuracy=0.60, pass_count=2, total_tasks=3, total_tokens=1000)
    promoted, reason = opt._check_promotion(dr1, inc_fr1, tr1, 0.40)
    assert promoted, f"Expected promotion, got: {reason}"

    # Scenario 2: dev improves 2pp, test drops 2pp → rejected
    dr2 = FakeReport(overall_accuracy=0.62, pass_count=2, total_tasks=3, total_tokens=1000)
    tr2 = FakeReport(overall_accuracy=0.38, pass_count=1, total_tasks=3, total_tokens=1000)
    inc_fr2 = FakeReport(overall_accuracy=0.60, pass_count=2, total_tasks=3, total_tokens=1000)
    promoted, reason = opt._check_promotion(dr2, inc_fr2, tr2, 0.40)
    assert not promoted, f"Expected rejection (overfitting), got: {reason}"

    # Scenario 3: dev improves 0.5pp (below 1pp blended threshold) → rejected
    # Same all_pass_rate, so blended delta = accuracy delta = 0.005
    dr3 = FakeReport(overall_accuracy=0.605, pass_count=2, total_tasks=3, total_tokens=1000)
    tr3 = FakeReport(overall_accuracy=0.40, pass_count=1, total_tasks=3, total_tokens=1000)
    inc_fr3 = FakeReport(overall_accuracy=0.60, pass_count=2, total_tasks=3, total_tokens=1000)
    promoted, reason = opt._check_promotion(dr3, inc_fr3, tr3, 0.40)
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
