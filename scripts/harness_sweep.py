#!/usr/bin/env python3
"""Harness sweep: run canary tasks through each grid config, collect results.

Usage: python scripts/harness_sweep.py [--configs baseline,timeout_aggressive,feedback_minimal] [--tasks bbh_cot_fewshot_boolean_expressions,gsm8k_cot,mbpp] [--limit 5]

ponytail: Sequential per-config runs. No parallelism.
Upgrade path: ThreadPoolExecutor for concurrent config runs.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from observeco.benchmark.engine import BenchmarkEngine
from observeco.benchmark.grid.configs import ALL_CONFIGS

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("harness_sweep")

# ── Config ──────────────────────────────────────────────────────────────────

# Default: 3 configs × 3 tasks × 5 samples = 45 runs (~15-30 min)
DEFAULT_CONFIGS = ["baseline", "timeout_aggressive", "feedback_minimal"]
DEFAULT_TASKS = [
    "bbh_cot_fewshot_boolean_expressions",
    "gsm8k_cot",
    "mbpp",
]
DEFAULT_LIMIT = 5

# Tasks that produce code — must bypass agent harness.
# Agent harness routes tool calls (patch/write_file) and captures diff output,
# not the raw code. Direct API returns clean completions.
# ponytail: hardcoded set. Upgrade path: task-type heuristics from YAML metadata.
DIRECT_TASKS: set[str] = {
    "mbpp",
    "humaneval",
    "humaneval_plus",
    "mbpp_plus",
}

# System prompt for code-gen tasks — prevents markdown wrapping and explanations
# that would break the pass@1 execution metric.
DIRECT_CODE_PROMPT = (
    "Output ONLY raw Python code. "
    "No markdown formatting, no code fences, no explanations. "
    "Start with the function definition. "
    "Do not include example usage or test cases."
)


def parse_args() -> tuple[list[str], list[str], int]:
    configs = DEFAULT_CONFIGS
    tasks = DEFAULT_TASKS
    limit = DEFAULT_LIMIT

    for arg in sys.argv[1:]:
        if arg.startswith("--configs="):
            configs = arg.split("=", 1)[1].split(",")
        elif arg.startswith("--tasks="):
            tasks = arg.split("=", 1)[1].split(",")
        elif arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])

    return configs, tasks, limit


# ── Helpers ──────────────────────────────────────────────────────────────


def _parse_task_results(results: dict) -> list[tuple[str, str, float]]:
    """Extract (task_name, primary_metric, primary_value) tuples from lm-eval results."""
    out = []
    for task_name, metrics in results.items():
        primary_metric = None
        primary_value = 0.0
        for key, value in metrics.items():
            if key in {"alias", "sample_len"} or key.endswith("_stderr"):
                continue
            if isinstance(value, (int, float)):
                primary_metric = key
                primary_value = value
                break
        out.append((task_name, primary_metric or "?", primary_value))
    return out


def _merge_task_results(results: dict, target: dict) -> None:
    """Merge parsed lm-eval task results into target dict."""
    for task_name, primary_metric, primary_value in _parse_task_results(results):
        # Re-extract all non-meta metrics for completeness
        metrics = results[task_name]
        target[task_name] = {
            "primary_metric": primary_metric,
            "primary_value": primary_value,
            "all_metrics": {k: v for k, v in metrics.items()
                            if isinstance(v, (int, float, str, bool))},
        }


def _log_task_results(results: dict, logger: logging.Logger) -> None:
    """Log each task's primary metric."""
    for task_name, primary_metric, primary_value in _parse_task_results(results):
        logger.info(
            "  %s: %s = %.4f",
            task_name, primary_metric, primary_value,
        )


def main() -> None:
    config_names, task_list, limit = parse_args()

    # Resolve configs
    config_map = {c.name: c for c in ALL_CONFIGS}
    selected = []
    for name in config_names:
        if name not in config_map:
            logger.error("Unknown config: %s (available: %s)", name, list(config_map.keys()))
            sys.exit(1)
        selected.append(config_map[name])

    engine = BenchmarkEngine()
    results_dir = os.path.join(
        os.path.expanduser("~"), ".observeco", "harness_sweep",
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
    )
    os.makedirs(results_dir, exist_ok=True)

    # Split tasks: code-gen → direct API, reasoning → agent harness
    agent_tasks = [t for t in task_list if not any(dt in t for dt in DIRECT_TASKS)]
    direct_tasks = [t for t in task_list if any(dt in t for dt in DIRECT_TASKS)]

    logger.info("=" * 60)
    logger.info("Harness Sweep: %d configs × %d tasks × %d samples", len(selected), len(task_list), limit)
    logger.info("Configs: %s", [c.name for c in selected])
    logger.info("Tasks (agent):  %s", agent_tasks or "(none)")
    logger.info("Tasks (direct): %s", direct_tasks or "(none)")
    logger.info("Output: %s", results_dir)
    logger.info("=" * 60)

    all_results = {}
    total_start = time.time()

    for config in selected:
        logger.info("\n--- Config: %s (%s) ---", config.name, config.description)
        config_start = time.time()

        harness_config = {
            "call_timeout_seconds": config.call_timeout_seconds,
            "max_retries": config.max_retries,
            "retry_delay_seconds": config.retry_delay_seconds,
            # Use minimal profile to avoid system prompt penalty.
            # Default profile's routing rules + PTCA protocol cost
            # 80 points on BBH boolean expressions.
            "profile": "benchmark",
            # Self-check: verify each answer before submission.
            # Maka-style: model verifies its own work before we accept it.
            "self_check": config.self_check,
        }

        # Run agent tasks through agent harness
        agent_result = None
        if agent_tasks:
            agent_result = engine.run_lm_eval(
                agent_name="default",
                tasks=agent_tasks,
                limit=limit,
                harness_config=harness_config,
            )

        # Run code-gen tasks through direct API (no agent harness)
        direct_result = None
        if direct_tasks:
            direct_result = engine.run_lm_eval(
                agent_name="default",
                tasks=direct_tasks,
                limit=limit,
                direct=True,
                direct_system_prompt=DIRECT_CODE_PROMPT,
            )

        elapsed = time.time() - config_start
        all_results[config.name] = {
            "config": {
                "name": config.name,
                "description": config.description,
                "call_timeout_seconds": config.call_timeout_seconds,
                "max_retries": config.max_retries,
                "tool_feedback_mode": config.tool_feedback_mode,
                "context_mode": config.context_mode,
            },
            "ok": True,
            "error": None,
            "model_used": (
                agent_result.get("model_used", "") if agent_result else ""
            ),
            "elapsed_seconds": round(elapsed, 1),
            "tasks": {},
        }

        # Merge agent results
        if agent_result and agent_result.get("ok") and agent_result.get("results"):
            _merge_task_results(agent_result["results"], all_results[config.name]["tasks"])
            _log_task_results(agent_result["results"], logger)

        # Merge direct results
        if direct_result and direct_result.get("ok") and direct_result.get("results"):
            _merge_task_results(direct_result["results"], all_results[config.name]["tasks"])
            _log_task_results(direct_result["results"], logger)

        # Surface errors
        errors = []
        if agent_result and not agent_result.get("ok"):
            errors.append(f"agent: {agent_result.get('error')}")
        if direct_result and not direct_result.get("ok"):
            errors.append(f"direct: {direct_result.get('error')}")
        if errors:
            all_results[config.name]["ok"] = False
            all_results[config.name]["error"] = "; ".join(errors)
            logger.warning("  Errors: %s", "; ".join(errors))

        logger.info("  → %.1fs elapsed", elapsed)

    total_elapsed = time.time() - total_start
    logger.info("\n" + "=" * 60)
    logger.info("Sweep complete in %.1fs", total_elapsed)

    # Summary table
    logger.info("\nSummary:")
    logger.info("%-25s | %-15s | %-15s | %-15s | %s", "Config", "Task", "Metric", "Value", "Time")
    logger.info("-" * 90)
    for config_name, data in all_results.items():
        for task_name, task_data in data.get("tasks", {}).items():
            logger.info(
                "%-25s | %-15s | %-15s | %-15.4f | %.1fs",
                config_name,
                task_name.split("_")[-1] if "_" in task_name else task_name[:15],
                task_data.get("primary_metric", "?")[:15],
                task_data.get("primary_value", 0.0),
                data.get("elapsed_seconds", 0),
            )

    # Save full results
    output_path = os.path.join(results_dir, "sweep_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "configs_run": config_names,
            "tasks_run": task_list,
            "limit": limit,
            "total_elapsed_seconds": round(total_elapsed, 1),
            "results": all_results,
        }, f, indent=2)
    logger.info("\nFull results saved to %s", output_path)


if __name__ == "__main__":
    main()
