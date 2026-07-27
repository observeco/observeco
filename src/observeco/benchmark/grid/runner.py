"""Grid runner: iterate models × harness configs × tasks, collect per-cell results.

Output per cell:
- Accuracy with confidence interval (from 3 repeated runs)
- Cost: tokens and dollars
- Trajectory logs with flagged shortcuts, loops, unsafe actions
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .configs import ALL_CONFIGS, HarnessConfig
from .tau_adapter import HermesTauAgent

logger = logging.getLogger(__name__)

# ── Models ──────────────────────────────────────────────────────────────────

MODELS: dict[str, str] = {
    "flash": "custom-ollama/deepseek-v4-flash",
    "pro": "custom-ollama/deepseek-v4-pro",
    "ornith": "custom-ollama/ornith:latest",
}

# ── Data types ─────────────────────────────────────────────────────────────


@dataclass
class CellResult:
    """Results for one cell in the grid (one model × one config × one task)."""

    model_name: str = ""
    config_name: str = ""
    task_name: str = ""
    task_env: str = ""  # "retail" or "airline"

    # Accuracy
    rewards: list[float] = field(default_factory=list)
    mean_reward: float = 0.0
    reward_ci: tuple[float, float] = (0.0, 0.0)  # 95% Wilson interval

    # Cost
    total_call_time: float = 0.0
    total_calls: int = 0
    total_timeouts: int = 0
    total_retries: int = 0
    hang_rate: float = 0.0  # timeouts / total_calls
    recovery_rate: float = 0.0  # retries that succeeded

    # Trajectory
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    # Metadata
    started_at: str = ""
    completed_at: str = ""


@dataclass
class GridResult:
    """Complete grid results."""

    cells: list[CellResult] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


# ── Wilson confidence interval ──────────────────────────────────────────────


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Compute Wilson score interval for a proportion.

    ponytail: Assumes binomial distribution. Upgrade path: bootstrap CI for
    non-binomial metrics (cost, time).
    """
    if trials == 0:
        return (0.0, 0.0)
    p = successes / trials
    denominator = 1 + z**2 / trials
    centre = (p + z**2 / (2 * trials)) / denominator
    margin = (
        z
        * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials)
        / denominator
    )
    return (max(0.0, centre - margin), min(1.0, centre + margin))


# ── Grid runner ────────────────────────────────────────────────────────────


class GridRunner:
    """Run the full grid: models × configs × tasks."""

    def __init__(
        self,
        models: Optional[dict[str, str]] = None,
        configs: Optional[list[HarnessConfig]] = None,
        num_trials: int = 3,
        hermes_bin: str = "hermes",
        output_dir: str = "",
    ) -> None:
        self.models = models or MODELS
        self.configs = configs or ALL_CONFIGS
        self.num_trials = num_trials
        self.hermes_bin = hermes_bin
        self.output_dir = output_dir or os.path.join(
            os.path.expanduser("~"), ".observeco", "grid"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def run_tau_bench(
        self,
        env_name: str = "retail",
        task_ids: Optional[list[int]] = None,
        max_steps: int = 30,
    ) -> GridResult:
        os.environ.setdefault("LITELLM_TIMEOUT", "120")  # ponytail: user simulator has no timeout param; env var is the only lever without patching tau_bench
        """Run τ-bench grid for a given environment.

        Iterates: models × configs × tasks × trials
        """
        from tau_bench.envs import get_env
        from tau_bench.envs.airline import tools as airline_tools
        from tau_bench.envs.airline import wiki as airline_wiki
        from tau_bench.envs.retail import tools as retail_tools
        from tau_bench.envs.retail import wiki as retail_wiki

        tools_info = retail_tools.ALL_TOOLS if env_name == "retail" else airline_tools.ALL_TOOLS
        wiki_text = retail_wiki.WIKI if env_name == "retail" else airline_wiki.WIKI

        # Convert Tool classes to dicts for the adapter
        tool_dicts = [t.get_info() for t in tools_info]

        result = GridResult(
            started_at=datetime.now(timezone.utc).isoformat()
        )

        # Get task count
        env = get_env(
            env_name=env_name,
            user_strategy="llm",
            user_model="ollama/hermes3:latest",
            user_provider="ollama",
            task_split="test",
        )
        all_task_ids = task_ids or list(range(len(env.tasks)))

        for model_key, model_name in self.models.items():
            for config in self.configs:
                logger.info(
                    "Grid cell: model=%s config=%s env=%s tasks=%d",
                    model_key, config.name, env_name, len(all_task_ids),
                )

                cell = CellResult(
                    model_name=model_key,
                    config_name=config.name,
                    task_name=f"tau_{env_name}",
                    task_env=env_name,
                    started_at=datetime.now(timezone.utc).isoformat(),
                )

                for trial in range(self.num_trials):
                    logger.info(
                        "  Trial %d/%d for %s/%s",
                        trial + 1, self.num_trials, model_key, config.name,
                    )

                    # Create agent
                    agent = HermesTauAgent(
                        tools_info=tool_dicts,
                        wiki=wiki_text,
                        harness_config=config,
                        hermes_bin=self.hermes_bin,
                    )

                    # Create fresh env for each trial
                    trial_env = get_env(
                        env_name=env_name,
                        user_strategy="llm",
                        user_model="ollama/hermes3:latest",
                        user_provider="ollama",
                        task_split="test",
                    )

                    # Run each task
                    trial_rewards: list[float] = []
                    for tid in all_task_ids:
                        try:
                            solve_result = agent.solve(
                                trial_env, task_index=tid, max_num_steps=max_steps
                            )
                            trial_rewards.append(solve_result.reward)

                            # Record trajectory
                            cell.trajectory.append({
                                "trial": trial,
                                "task_id": tid,
                                "reward": solve_result.reward,
                                "steps": len(solve_result.messages) // 2,
                                "info": solve_result.info,
                            })

                            # Flag shortcuts (high reward in very few steps)
                            if solve_result.reward >= 0.9 and len(solve_result.messages) < 4:
                                cell.flags.append(
                                    f"SHORTCUT: task={tid} trial={trial} "
                                    f"reward={solve_result.reward} steps={len(solve_result.messages)//2}"
                                )

                            # Flag loops (same action repeated)
                            self._check_loops(solve_result, tid, trial, cell)

                        except Exception as exc:
                            logger.error(
                                "Task %d failed: %s", tid, exc
                            )
                            trial_rewards.append(0.0)
                            cell.flags.append(
                                f"ERROR: task={tid} trial={trial} {exc}"
                            )

                    # Accumulate metrics
                    cell.total_calls += agent.call_count
                    cell.total_timeouts += agent.timeout_count
                    cell.total_retries += agent.retry_count
                    cell.total_call_time += agent.total_call_time

                # Compute cell metrics
                all_rewards = [
                    t["reward"]
                    for t in cell.trajectory
                ]
                if all_rewards:
                    cell.mean_reward = sum(all_rewards) / len(all_rewards)
                    successes = sum(1 for r in all_rewards if r >= 0.5)
                    cell.reward_ci = wilson_ci(successes, len(all_rewards))

                if cell.total_calls > 0:
                    cell.hang_rate = cell.total_timeouts / cell.total_calls
                if cell.total_timeouts > 0:
                    cell.recovery_rate = (
                        cell.total_retries / cell.total_timeouts
                    )

                cell.completed_at = datetime.now(timezone.utc).isoformat()
                result.cells.append(cell)

                # Save intermediate results
                self._save_cell(cell)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        self._save_grid(result)
        return result

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _check_loops(
        solve_result, task_id: int, trial: int, cell: CellResult
    ) -> None:
        """Detect action loops in trajectory."""
        actions = []
        for msg in solve_result.messages:
            if isinstance(msg, dict):
                tc = msg.get("tool_calls")
                if tc:
                    for call in tc:
                        func = call.get("function", {})
                        actions.append(func.get("name", ""))
                elif msg.get("role") == "assistant" and msg.get("content"):
                    actions.append("respond")

        # Flag if same action repeated 5+ times
        if len(actions) >= 5:
            last_5 = actions[-5:]
            if len(set(last_5)) == 1:
                cell.flags.append(
                    f"LOOP: task={task_id} trial={trial} "
                    f"action={last_5[0]} repeated 5x"
                )

    def _save_cell(self, cell: CellResult) -> None:
        """Save individual cell result to disk."""
        path = os.path.join(
            self.output_dir,
            f"{cell.model_name}_{cell.config_name}_{cell.task_name}.json",
        )
        with open(path, "w") as f:
            json.dump(
                {
                    "model": cell.model_name,
                    "config": cell.config_name,
                    "task": cell.task_name,
                    "env": cell.task_env,
                    "mean_reward": cell.mean_reward,
                    "reward_ci": list(cell.reward_ci),
                    "total_calls": cell.total_calls,
                    "total_timeouts": cell.total_timeouts,
                    "total_retries": cell.total_retries,
                    "total_call_time": cell.total_call_time,
                    "hang_rate": cell.hang_rate,
                    "recovery_rate": cell.recovery_rate,
                    "flags": cell.flags,
                    "trajectory_count": len(cell.trajectory),
                    "started_at": cell.started_at,
                    "completed_at": cell.completed_at,
                },
                f,
                indent=2,
            )

    def _save_grid(self, result: GridResult) -> None:
        """Save full grid results."""
        path = os.path.join(self.output_dir, "grid_result.json")
        with open(path, "w") as f:
            json.dump(
                {
                    "started_at": result.started_at,
                    "completed_at": result.completed_at,
                    "cells": [
                        {
                            "model": c.model_name,
                            "config": c.config_name,
                            "task": c.task_name,
                            "env": c.task_env,
                            "mean_reward": c.mean_reward,
                            "reward_ci": list(c.reward_ci),
                            "total_calls": c.total_calls,
                            "total_timeouts": c.total_timeouts,
                            "total_retries": c.total_retries,
                            "total_call_time": c.total_call_time,
                            "hang_rate": c.hang_rate,
                            "recovery_rate": c.recovery_rate,
                            "flags": c.flags,
                            "trajectory_count": len(c.trajectory),
                        }
                        for c in result.cells
                    ],
                },
                f,
                indent=2,
            )
        logger.info("Grid results saved to %s", path)
