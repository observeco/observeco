"""Capability grid runner — model × config comparison using canary tasks.

obs-spec-054: Runs the same canary tasks across different models and configs,
stores results in grid_runs/grid_results tables for the dashboard grid report.

Separate from benchmark/grid/runner.py (τ-bench environments). This runner
tests agent performance on user-defined canary tasks across model×config
combinations, using DirectModelAdapter to bypass the agent harness and
measure raw model capability.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from observeco.capability.adapters.direct_model import DirectModelAdapter
from observeco.capability.canary import Scorer
from observeco.db import Database

logger = logging.getLogger(__name__)

# Default blended-score weights (configurable via ~/.observeco/config.json)
DEFAULT_GRID_CONFIG = {
    "allpass_weight": 0.5,
    "cost_lambda": 0.005,
}

# Default models for grid runs
DEFAULT_MODELS = [
    "custom-ollama/deepseek-v4-flash",
    "custom-ollama/deepseek-v4-pro",
    "custom-ollama/ornith:latest",
]

# Default config labels
DEFAULT_CONFIGS = ["baseline-v3", "baseline-v2"]


def load_grid_config() -> dict:
    """Load grid config from ~/.observeco/config.json or defaults."""
    import os
    config = dict(DEFAULT_GRID_CONFIG)
    try:
        config_path = os.path.expanduser("~/.observeco/config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                user_config = json.load(f)
                config.update(user_config.get("grid", {}))
    except Exception:
        pass
    return config


def compute_blended_score(
    accuracy: float,
    all_pass_rate: float,
    tokens: int,
    allpass_weight: float = 0.5,
    cost_lambda: float = 0.005,
) -> float:
    """Compute blended score for a grid cell.

    score = accuracy + allpass_weight * all_pass_rate - cost_lambda * tokens/1M
    """
    return accuracy + allpass_weight * all_pass_rate - cost_lambda * (tokens / 1_000_000)


class CapabilityGridRunner:
    """Run canary tasks across model × config combinations.

    For each (model, config) pair:
    1. Create a DirectModelAdapter for the model
    2. Run the canary suite (3 trials per task)
    3. Aggregate per-task accuracy with bootstrap CI
    4. Store in grid_results table
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def run(
        self,
        agent_name: str,
        models: Optional[list[str]] = None,
        configs: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        trials: int = 3,
        timeout: int = 60,
    ) -> dict:
        """Run the full grid: models × configs × tasks.

        Args:
            agent_name: Agent name (for labeling, not used for routing).
            models: Model specs like ['custom-ollama/deepseek-v4-flash', ...].
            configs: Config labels like ['baseline-v3', 'baseline-v2'].
            task_ids: Specific task IDs to run (None = all).
            trials: Trials per task per cell.
            timeout: Per-task timeout in seconds.

        Returns:
            Grid report dict with cells, models, configs, tasks.
        """
        models = models or DEFAULT_MODELS
        configs = configs or DEFAULT_CONFIGS

        # Load tasks
        conn = self.db._get_conn()
        if task_ids:
            placeholders = ",".join("?" * len(task_ids))
            rows = conn.execute(
                f"SELECT id, name, prompt, assertions, timeout, model, trials "
                f"FROM canary_tasks WHERE id IN ({placeholders}) ORDER BY id",
                task_ids,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, prompt, assertions, timeout, model, trials "
                "FROM canary_tasks WHERE built_in = 1 ORDER BY id"
            ).fetchall()

        if not rows:
            return {
                "agent": agent_name,
                "run_id": None,
                "cells": [],
                "models": models,
                "configs": configs,
                "tasks": [],
                "error": "No canary tasks defined. Seed tasks first.",
            }

        tasks = [dict(r) for r in rows]

        # Create grid run record
        run_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        total_cells = len(tasks) * len(models) * len(configs)

        conn.execute(
            "INSERT INTO grid_runs (id, agent_name, started_at, status, models, configs, total_cells) "
            "VALUES (?, ?, ?, 'running', ?, ?, ?)",
            (run_id, agent_name, now_iso,
             json.dumps(models), json.dumps(configs), total_cells),
        )
        conn.commit()

        cells = []
        total_cost = 0.0

        for model_spec in models:
            for config_label in configs:
                logger.info(
                    "Grid cell: model=%s config=%s tasks=%d",
                    model_spec, config_label, len(tasks),
                )

                # Create adapter for this model
                adapter = DirectModelAdapter(model_spec=model_spec, timeout=timeout)

                for task in tasks:
                    task_trials = trials if trials else task.get("trials", 3)
                    assertions = json.loads(task["assertions"]) if isinstance(task["assertions"], str) else task["assertions"]
                    task_accuracies: list[float] = []
                    task_costs: list[float] = []
                    task_tokens: list[int] = []
                    hangs = 0
                    flags: list[str] = []

                    for trial_idx in range(task_trials):
                        # Build a task-like object for the adapter
                        task_obj = type("Task", (), {
                            "id": task["id"],
                            "task_name": task.get("name", task["id"]),
                            "agent_name": agent_name,
                            "input_text": task.get("prompt", ""),
                            "context_text": "",
                            "expected_output": "",
                        })()

                        result = adapter.run_task(agent_name, task_obj)

                        if result.get("provider_error"):
                            flags.append(f"provider_error: trial={trial_idx}")
                            task_accuracies.append(0.0)
                        elif result.get("timed_out") or result.get("error"):
                            hangs += 1
                            task_accuracies.append(0.0)
                        else:
                            passed, accuracy, _ = Scorer.score(assertions, result.get("output", ""))
                            task_accuracies.append(accuracy)

                        if result.get("cost"):
                            task_costs.append(result["cost"])
                        if result.get("tokens"):
                            task_tokens.append(result["tokens"])

                    # Aggregate
                    mean_accuracy = sum(task_accuracies) / len(task_accuracies) if task_accuracies else 0.0
                    ci_lower, ci_upper = Scorer.bootstrap_ci(task_accuracies)
                    cell_cost = sum(task_costs)
                    cell_tokens = sum(task_tokens)

                    # Store result
                    cell_id = str(uuid.uuid4())
                    conn.execute(
                        "INSERT INTO grid_results (id, grid_run_id, task_id, model, config, "
                        "accuracy, ci_lower, ci_upper, cost, tokens, flags, hang) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (cell_id, run_id, task["id"], model_spec, config_label,
                         round(mean_accuracy, 4), ci_lower, ci_upper,
                         round(cell_cost, 6), cell_tokens,
                         json.dumps(flags), hangs),
                    )

                    cells.append({
                        "task_id": task["id"],
                        "task_name": task.get("name", task["id"]),
                        "model": model_spec,
                        "config": config_label,
                        "accuracy": round(mean_accuracy, 4),
                        "ci_lower": ci_lower,
                        "ci_upper": ci_upper,
                        "cost": round(cell_cost, 6),
                        "tokens": cell_tokens,
                        "flags": flags,
                        "hang": hangs > 0,
                    })

                    total_cost += cell_cost

        # Finalize run
        completed_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE grid_runs SET completed_at=?, status='completed', total_cost=? WHERE id=?",
            (completed_at, round(total_cost, 6), run_id),
        )
        conn.commit()

        task_names = list(dict.fromkeys(c["task_name"] for c in cells))

        return {
            "agent": agent_name,
            "run_id": run_id,
            "date": now_iso[:10],
            "models": models,
            "configs": configs,
            "tasks": task_names,
            "cells": cells,
            "total_cost": round(total_cost, 6),
        }
