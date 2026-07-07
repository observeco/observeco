"""Drift detection — statistical comparison, alerting, per-task drift.

obs-spec-052: Drift detection for capability monitoring.
Uses two-sample z-test with configurable thresholds.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from observeco.capability.baseline import BaselineManager, DriftResult
from observeco.db import Database

logger = logging.getLogger(__name__)

# Default thresholds (configurable via ~/.observeco/config.json)
DEFAULT_DRIFT_CONFIG = {
    "threshold_breach": 5.0,   # |drift_pct| >= 5% AND p < 0.01
    "threshold_warning": 3.0,  # |drift_pct| >= 3% AND p < 0.05
    "threshold_info": 1.0,     # |drift_pct| >= 1% AND p < 0.05
    "p_value_breach": 0.01,
    "p_value_warning": 0.05,
    "min_runs_for_baseline": 3,
}


class DriftDetector:
    """Detect drift after canary runs, store events, provide history."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.baseline_manager = BaselineManager(db=self.db)

    def check(
        self,
        run_id: str,
        agent_name: str,
        config_hash: str,
        config_label: Optional[str],
        pass_count: int,
        fail_count: int,
        per_task_results: list[dict],
    ) -> Optional[dict]:
        """Check for drift after a canary run.

        Call after CanaryRunner.run() completes. Stores drift_event if significant.

        Returns drift_event dict if drift detected, None otherwise.
        """
        # Load drift config
        config = self._load_config()

        result = self.baseline_manager.compare(
            run_id=run_id,
            agent_name=agent_name,
            config_hash=config_hash,
            current_pass=pass_count,
            current_fail=fail_count,
            per_task_results=per_task_results,
            threshold_breach=config["threshold_breach"],
            threshold_warning=config["threshold_warning"],
            threshold_info=config["threshold_info"],
            p_breach=config["p_value_breach"],
            p_warning=config["p_value_warning"],
        )

        if result is None:
            # No baseline exists yet — auto-create if enough runs
            self.baseline_manager.compute_baseline(
                agent_name=agent_name,
                config_hash=config_hash,
                config_label=config_label,
                min_runs=config["min_runs_for_baseline"],
            )
            return None

        # Store drift event
        baseline = self.baseline_manager.get_active_baseline(agent_name, config_hash)
        event_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self.db._get_conn()
        conn.execute(
            "INSERT INTO drift_events (id, agent_name, baseline_id, run_id, "
            "config_hash, config_label, drift_pct, p_value, ci_lower, ci_upper, "
            "severity, breached_tasks, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id, agent_name,
                baseline["id"] if baseline else None,
                run_id,
                config_hash, config_label,
                result.drift_pct, result.p_value,
                result.ci_lower, result.ci_upper,
                result.severity,
                json.dumps(result.breached_tasks),
                now_iso,
            ),
        )
        conn.commit()

        logger.info(
            "Drift detected: agent=%s drift=%+.1f%% severity=%s p=%.4f",
            agent_name, result.drift_pct, result.severity, result.p_value,
        )

        return {
            "id": event_id,
            "agent_name": agent_name,
            "drift_pct": result.drift_pct,
            "p_value": result.p_value,
            "ci_lower": result.ci_lower,
            "ci_upper": result.ci_upper,
            "severity": result.severity,
            "breached_tasks": result.breached_tasks,
        }

    def get_latest(self, agent_name: str) -> Optional[dict]:
        """Get the most recent drift event for an agent."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT * FROM drift_events WHERE agent_name = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        return dict(row) if row else None

    def get_history(self, agent_name: str, days: int = 14) -> dict:
        """Get drift history for an agent.

        Also returns canary run accuracy points for the chart.
        """
        conn = self.db._get_conn()

        # Get drift events
        drift_rows = conn.execute(
            "SELECT id, agent_name, drift_pct, p_value, ci_lower, ci_upper, "
            "severity, breached_tasks, acknowledged, created_at "
            "FROM drift_events WHERE agent_name = ? "
            "ORDER BY created_at DESC",
            (agent_name,),
        ).fetchall()

        # Get recent canary run accuracies for time series
        run_rows = conn.execute(
            "SELECT id, started_at, pass_count, fail_count, hang_count, total_tasks "
            "FROM canary_runs WHERE agent_name = ? AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT ?",
            (agent_name, days * 2),  # approx 2 runs/day
        ).fetchall()

        # Build time series
        points = []
        for r in reversed(run_rows):
            total = (r["pass_count"] or 0) + (r["fail_count"] or 0)
            acc = r["pass_count"] / total if total > 0 else 0.0
            points.append({
                "date": r["started_at"][:10],
                "accuracy": round(acc * 100, 1),
                "run_id": r["id"],
            })

        # Get active baseline
        baseline_row = conn.execute(
            "SELECT accuracy, created_at FROM canary_baselines "
            "WHERE agent_name = ? AND expires_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name,),
        ).fetchone()

        baseline = None
        if baseline_row:
            baseline = {
                "value": round(baseline_row["accuracy"] * 100, 1),
                "date": baseline_row["created_at"][:10],
            }

        return {
            "agent": agent_name,
            "points": points,
            "baseline": baseline,
            "drift_events": [
                {
                    "id": d["id"],
                    "date": d["created_at"][:10],
                    "drift_pct": d["drift_pct"],
                    "p_value": d["p_value"],
                    "severity": d["severity"],
                    "breached_tasks": json.loads(d["breached_tasks"]) if d["breached_tasks"] else [],
                    "acknowledged": bool(d["acknowledged"]),
                }
                for d in drift_rows
            ],
        }

    def get_detail(self, agent_name: str) -> Optional[dict]:
        """Get detailed drift info for the dashboard hero section.

        Includes current run vs baseline comparison, per-task breakdown.
        """
        drift = self.get_latest(agent_name)
        if not drift:
            return None

        # Get current run
        conn = self.db._get_conn()
        run = conn.execute(
            "SELECT * FROM canary_runs WHERE id = ?", (drift["run_id"],)
        ).fetchone()

        # Get baseline
        baseline = None
        if drift.get("baseline_id"):
            bl = conn.execute(
                "SELECT * FROM canary_baselines WHERE id = ?", (drift["baseline_id"],)
            ).fetchone()
            if bl:
                baseline = dict(bl)

        # Per-task drift
        results = conn.execute(
            "SELECT cr.task_id, ct.name as task_name, cr.status, cr.accuracy "
            "FROM canary_results cr JOIN canary_tasks ct ON cr.task_id = ct.id "
            "WHERE cr.run_id = ? ORDER BY ct.id",
            (drift["run_id"],),
        ).fetchall()

        tasks = []
        for r in results:
            task_acc = r["accuracy"] if r["accuracy"] is not None else 0.0
            baseline_acc = baseline["accuracy"] if baseline else 0.0
            delta = (task_acc - baseline_acc) * 100
            abs_delta = abs(delta)
            if abs_delta >= 5.0:
                t_sev = "breach"
            elif abs_delta >= 3.0:
                t_sev = "warning"
            else:
                t_sev = "stable"

            tasks.append({
                "name": r["task_name"],
                "task_id": r["task_id"],
                "accuracy": round(task_acc * 100, 1),
                "baseline": round(baseline_acc * 100, 1) if baseline else None,
                "delta": round(delta, 1),
                "severity": t_sev,
            })

        current = None
        if run:
            run_total = (run["pass_count"] or 0) + (run["fail_count"] or 0)
            run_acc = run["pass_count"] / run_total if run_total > 0 else 0.0
            current = {
                "accuracy": round(run_acc * 100, 1),
                "ci": [drift["ci_lower"], drift["ci_upper"]],
                "run_id": drift["run_id"],
                "date": run["started_at"][:10] if run else "",
            }

        baseline_info = None
        if baseline:
            baseline_info = {
                "accuracy": round(baseline["accuracy"] * 100, 1),
                "ci": [baseline["ci_lower"], baseline["ci_upper"]],
                "run_count": baseline["run_count"],
                "date": baseline["created_at"][:10],
            }

        return {
            "agent": agent_name,
            "current": current,
            "baseline": baseline_info,
            "drift": {
                "pct": drift["drift_pct"],
                "p_value": drift["p_value"],
                "ci": [drift["ci_lower"], drift["ci_upper"]],
                "severity": drift["severity"],
            },
            "tasks": tasks,
        }

    def acknowledge(self, event_id: str) -> dict:
        """Mark a drift event as acknowledged."""
        conn = self.db._get_conn()
        conn.execute(
            "UPDATE drift_events SET acknowledged = 1 WHERE id = ?",
            (event_id,),
        )
        conn.commit()
        return {"ok": True}

    @staticmethod
    def _load_config() -> dict:
        """Load drift configuration from ~/.observeco/config.json or defaults."""
        import os
        config_path = os.path.expanduser("~/.observeco/config.json")
        config = dict(DEFAULT_DRIFT_CONFIG)
        try:
            if os.path.exists(config_path):
                with open(config_path) as f:
                    user_config = json.load(f)
                    drift_config = user_config.get("drift", {})
                    config.update(drift_config)
        except Exception:
            pass
        return config
