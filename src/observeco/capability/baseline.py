"""Baseline manager for canary runs.

obs-spec-051 §2.4: Computes baselines from N runs with same config_hash,
compares current run against baseline, and manages baseline lifecycle.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    """Result of comparing a run against its baseline."""
    drift_pct: float = 0.0
    p_value: float = 1.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    severity: str = "info"  # breach | warning | info
    breached_tasks: list = field(default_factory=list)


class BaselineManager:
    """Create, retrieve, and compare canary baselines."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def get_active_baseline(self, agent_name: str, config_hash: str) -> Optional[dict]:
        """Get the most recent active baseline for this agent+config."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT id, agent_name, config_hash, config_label, run_count, "
            "accuracy, ci_lower, ci_upper, created_at, expires_at "
            "FROM canary_baselines "
            "WHERE agent_name = ? AND config_hash = ? AND expires_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name, config_hash),
        ).fetchone()
        return dict(row) if row else None

    def compute_baseline(
        self,
        agent_name: str,
        config_hash: str,
        config_label: Optional[str] = None,
        min_runs: int = 3,
    ) -> Optional[dict]:
        """Compute a new baseline from the last N completed runs.

        Args:
            agent_name: Hermes agent profile name.
            config_hash: Config fingerprint from CanaryRunner.
            config_label: Human-readable label for this config.
            min_runs: Minimum number of runs required to build a baseline.

        Returns:
            Baseline dict if enough runs exist, None otherwise.
        """
        conn = self.db._get_conn()

        # Get last N completed runs with this config_hash
        rows = conn.execute(
            "SELECT id, pass_count, fail_count, total_tasks, started_at "
            "FROM canary_runs "
            "WHERE agent_name = ? AND config_hash = ? AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT ?",
            (agent_name, config_hash, min_runs),
        ).fetchall()

        if len(rows) < min_runs:
            logger.info(
                "Not enough runs for baseline: %d/%d (agent=%s, config=%s)",
                len(rows), min_runs, agent_name, config_hash,
            )
            return None

        # Aggregate accuracy across all runs
        total_pass = sum(r["pass_count"] or 0 for r in rows)
        total_fail = sum(r["fail_count"] or 0 for r in rows)
        total_tasks = sum(r["total_tasks"] or 0 for r in rows)

        if total_pass + total_fail == 0:
            accuracy = 0.0
        else:
            accuracy = total_pass / (total_pass + total_fail)

        # Bootstrap CI across runs' accuracy values
        run_accuracies = []
        for r in rows:
            p = r["pass_count"] or 0
            f = r["fail_count"] or 0
            if p + f > 0:
                run_accuracies.append(p / (p + f))

        from observeco.capability.canary import Scorer
        ci_lower, ci_upper = Scorer.bootstrap_ci(run_accuracies) if len(run_accuracies) >= 2 else (accuracy, accuracy)

        # Expire existing active baseline for this config
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE canary_baselines SET expires_at = ? "
            "WHERE agent_name = ? AND config_hash = ? AND expires_at IS NULL",
            (now_iso, agent_name, config_hash),
        )

        # Create new baseline
        baseline_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO canary_baselines (id, agent_name, config_hash, config_label, "
            "run_count, accuracy, ci_lower, ci_upper, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                baseline_id, agent_name, config_hash, config_label,
                len(rows), round(accuracy, 4), ci_lower, ci_upper, now_iso,
            ),
        )
        conn.commit()

        return {
            "id": baseline_id,
            "agent_name": agent_name,
            "config_hash": config_hash,
            "config_label": config_label,
            "run_count": len(rows),
            "accuracy": round(accuracy, 4),
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "created_at": now_iso,
        }

    def compare(
        self,
        run_id: str,
        agent_name: str,
        config_hash: str,
        current_pass: int,
        current_fail: int,
        per_task_results: list[dict],
        threshold_breach: float = 5.0,
        threshold_warning: float = 3.0,
        threshold_info: float = 1.0,
        p_breach: float = 0.01,
        p_warning: float = 0.05,
    ) -> Optional[DriftResult]:
        """Compare a completed run against the active baseline.

        Uses two-sample z-test for proportions.

        Args:
            run_id: The run to compare.
            agent_name: Agent being evaluated.
            config_hash: Config fingerprint.
            current_pass: Pass count from current run.
            current_fail: Fail count from current run.
            per_task_results: Per-task results from CanaryReport.
            threshold_breach/warning/info: Drift percentage thresholds.
            p_breach/warning: p-value thresholds.

        Returns:
            DriftResult if baseline exists and comparison was made, None if no baseline.
        """
        baseline = self.get_active_baseline(agent_name, config_hash)
        if baseline is None:
            return None

        baseline_accuracy = baseline["accuracy"]
        current_total = current_pass + current_fail
        current_accuracy = current_pass / current_total if current_total > 0 else 0.0

        drift_pct = (current_accuracy - baseline_accuracy) * 100  # percentage points

        # Two-sample z-test for proportions
        p1 = baseline_accuracy
        # Use actual total task-trials from baseline runs (obs-spec-057: remove hardcoded * 9)
        base_runs = self._get_baseline_runs(agent_name, config_hash)
        n1 = sum(r["total_tasks"] for r in base_runs)
        n2 = current_total

        if n1 == 0 or n2 == 0 or p1 == 0:
            return DriftResult(drift_pct=drift_pct, p_value=1.0, severity="info")

        # Pooled proportion
        p_pool = (p1 * n1 + current_accuracy * n2) / (n1 + n2)
        se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5

        if se == 0:
            return DriftResult(drift_pct=drift_pct, p_value=1.0, severity="info")

        import math
        z_score = abs(p1 - current_accuracy) / se
        # Two-tailed p-value from z-score using approximation
        p_value = 2 * (1 - _norm_cdf(z_score))

        # Determine severity
        abs_drift = abs(drift_pct)
        if abs_drift >= threshold_breach and p_value < p_breach:
            severity = "breach"
        elif abs_drift >= threshold_warning and p_value < p_warning:
            severity = "warning"
        elif abs_drift >= threshold_info and p_value < p_warning:
            severity = "info"
        else:
            severity = "info"

        # Bootstrap CI on drift
        from observeco.capability.canary import Scorer
        drift_samples = []
        for tr in per_task_results:
            if "accuracy" in tr:
                drift_samples.append(tr["accuracy"] - baseline_accuracy)
        ci_lower, ci_upper = Scorer.bootstrap_ci(
            [max(0.0, min(1.0, baseline_accuracy + d)) for d in drift_samples]
        ) if len(drift_samples) >= 2 else (drift_pct, drift_pct)

        # Per-task breach detection
        breached_tasks = []
        for tr in per_task_results:
            # Use per-task baseline when available (obs-spec-057 §2.3)
            task_base = self._get_per_task_baseline(agent_name, config_hash, tr.get("task_id", ""))
            task_base_acc = task_base["accuracy"] if task_base else baseline_accuracy
            task_drift = (tr.get("accuracy", 0.0) - task_base_acc) * 100
            if abs(task_drift) >= threshold_breach:
                breached_tasks.append(tr.get("task_name", tr.get("task_id", "")))

        return DriftResult(
            drift_pct=round(drift_pct, 2),
            p_value=round(p_value, 6),
            ci_lower=round(ci_lower, 4),
            ci_upper=round(ci_upper, 4),
            severity=severity,
            breached_tasks=breached_tasks,
        )

    def _get_baseline_runs(self, agent_name: str, config_hash: str) -> list[dict]:
        """Get the baseline runs for computing average tasks per run."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT total_tasks FROM canary_runs "
            "WHERE agent_name = ? AND config_hash = ? AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT 10",
            (agent_name, config_hash),
        ).fetchall()
        return [dict(r) for r in rows]

    def _get_per_task_baseline(self, agent_name: str, config_hash: str, task_id: str) -> Optional[dict]:
        """Get per-task baseline accuracy for this agent+config+task."""
        if not task_id:
            return None
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT accuracy, ci_lower, ci_upper, run_count FROM canary_task_baselines "
            "WHERE agent_name = ? AND config_hash = ? AND task_id = ? AND expires_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name, config_hash, task_id),
        ).fetchone()
        return dict(row) if row else None

    def get_per_task_baseline(self, agent_name: str, config_hash: str, task_id: str) -> Optional[dict]:
        """Public API: get per-task baseline."""
        return self._get_per_task_baseline(agent_name, config_hash, task_id)

    def create_per_task_baseline(
        self,
        agent_name: str,
        config_hash: str,
        task_id: str,
        accuracy: float,
        run_count: int,
        ci_lower: float = 0.0,
        ci_upper: float = 0.0,
    ) -> dict:
        """Create/update a per-task baseline for a specific task.

        Expires any existing active baseline for this (agent, config, task) before
        inserting the new one.
        """
        conn = self.db._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Expire existing active baseline
        conn.execute(
            "UPDATE canary_task_baselines SET expires_at = ? "
            "WHERE agent_name = ? AND config_hash = ? AND task_id = ? AND expires_at IS NULL",
            (now_iso, agent_name, config_hash, task_id),
        )

        baseline_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO canary_task_baselines "
            "(id, agent_name, config_hash, task_id, accuracy, ci_lower, ci_upper, run_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (baseline_id, agent_name, config_hash, task_id,
             round(accuracy, 4), ci_lower, ci_upper, run_count, now_iso),
        )
        conn.commit()

        return {
            "id": baseline_id,
            "agent_name": agent_name,
            "config_hash": config_hash,
            "task_id": task_id,
            "accuracy": round(accuracy, 4),
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "run_count": run_count,
            "created_at": now_iso,
        }


def _norm_cdf(x: float) -> float:
    """Approximation of standard normal CDF (Abramowitz & Stegun)."""
    import math
    # Constants for approximation
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p_coeff = 0.3275911

    sign = 1 if x >= 0 else -1
    x = abs(x)

    t = 1.0 / (1.0 + p_coeff * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2.0)

    return 0.5 * (1.0 + sign * y)
