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

from observeco.benchmark.adapters.hermes import HermesBenchmarkAdapter
from observeco.capability.canary import Scorer
from observeco.capability.model_config import get_default_grid_models, load_available_models
from observeco.db import Database

logger = logging.getLogger(__name__)

# Default blended-score weights (configurable via ~/.observeco/config.json)
DEFAULT_GRID_CONFIG = {
    "allpass_weight": 0.5,
    "cost_lambda": 0.005,
}

# Default models for grid runs — loaded from hermes config
# Falls back to ollama-cloud deepseek models if config can't be read
DEFAULT_MODELS = None  # Will be loaded lazily from config

# Default config labels — agent profiles to test
# Each config is an agent profile name that the Hermes adapter passes as -p.
DEFAULT_CONFIGS = None  # Will be loaded from profiles dir


def _resolve_configs(configs: Optional[list[str]] = None) -> list[str]:
    """Resolve config labels — uses agent profiles if none specified."""
    if configs:
        return configs
    from observeco.capability.model_config import get_default_grid_profiles
    return get_default_grid_profiles()


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
        """Run the full grid: models × profiles × tasks.

        Args:
            agent_name: Agent name (for labeling, not used for routing).
            models: Model specs like ['ollama-cloud/deepseek-v4-flash', ...].
            configs: Agent profiles to test (e.g., ['main', 'accelerator']).
            task_ids: Specific task IDs to run (None = all).
            trials: Trials per task per cell.
            timeout: Per-task timeout in seconds.

        Returns:
            Grid report dict with cells, models, configs, tasks.
        """
        models = models or get_default_grid_models()
        configs = _resolve_configs(configs)

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
                    "Grid cell: model=%s profile=%s tasks=%d",
                    model_spec, config_label, len(tasks),
                )

                # Use HermesBenchmarkAdapter — tests the full agent (SOUL.md +
                # skills + tools + streaming) with each model and profile.
                # config_label is now an agent profile name (e.g., 'main').
                adapter = HermesBenchmarkAdapter(
                    agent_profile=config_label,
                    model=model_spec,
                    timeout=timeout,
                )

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
                            "model": model_spec,
                            "temperature": 0.0,
                        })()

                        result = adapter.run_task(agent_name, task_obj)

                        if result.get("provider_error"):
                            # Measurement failure — NOT a quality 0. Store as
                            # NULL accuracy so the summary/table treat it as
                            # 'not measured', never as a real 0.
                            flags.append(f"provider_error: trial={trial_idx}")
                            task_accuracies.append(None)
                        elif result.get("timed_out") or result.get("error"):
                            hangs += 1
                            task_accuracies.append(None)
                        else:
                            passed, accuracy, reasoning = Scorer.score(assertions, result.get("output", ""))
                            # A judge failure (LLM judge couldn't run) is also a
                            # measurement failure — flag it so the summary can
                            # detect dubious runs, but still record the score
                            # attempt (it may be a fallback score).
                            if "llm_judge" in reasoning and (
                                "failed" in reasoning.lower() or "unavailable" in reasoning.lower()
                                or "no valid scores" in reasoning.lower()
                            ):
                                flags.append("judge_failure")
                            task_accuracies.append(accuracy)

                        if result.get("cost"):
                            task_costs.append(result["cost"])
                        if result.get("tokens"):
                            task_tokens.append(result["tokens"])

                    # Aggregate — None entries are measurement failures, not 0s.
                    # mean_accuracy is None when every trial failed to measure.
                    real = [a for a in task_accuracies if a is not None]
                    mean_accuracy = sum(real) / len(real) if real else None
                    ci_lower, ci_upper = Scorer.bootstrap_ci(real) if real else (None, None)
                    cell_cost = sum(task_costs)
                    cell_tokens = sum(task_tokens)

                    # Store result
                    cell_id = str(uuid.uuid4())
                    conn.execute(
                        "INSERT INTO grid_results (id, grid_run_id, task_id, model, config, "
                        "accuracy, ci_lower, ci_upper, cost, tokens, flags, hang) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (cell_id, run_id, task["id"], model_spec, config_label,
                         round(mean_accuracy, 4) if mean_accuracy is not None else None,
                         ci_lower, ci_upper,
                         round(cell_cost, 6), cell_tokens,
                         json.dumps(flags), hangs),
                    )
                    # Commit per cell — a grid run holds the connection open for
                    # the whole run (each cell is a slow LLM call). Without this,
                    # the single write transaction stays open for minutes and
                    # every other DB writer (dashboard pages, fleet telemetry)
                    # blocks on busy_timeout then 500s. Per-cell commit keeps the
                    # write lock held for milliseconds.
                    conn.commit()

                    cells.append({
                        "task_id": task["id"],
                        "task_name": task.get("name", task["id"]),
                        "model": model_spec,
                        "config": config_label,
                        "accuracy": round(mean_accuracy, 4) if mean_accuracy is not None else None,
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
