"""Direct τ-bench runner: native tool calling via Ollama cloud API.

Measures model capability ceiling (no text-prompt harness overhead).
Compare against grid/text-prompt results to quantify harness penalty.

ponytail: No retry logic, no context management, no error recovery.
Upgrade path: wrap in HermesAgent-style retry/context management if needed.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from tau_bench.agents.base import Agent
from tau_bench.envs.base import Env
from tau_bench.types import RESPOND_ACTION_NAME, Action, SolveResult

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────

OLLAMA_CLOUD_BASE = "https://ollama.com/v1"
OLLAMA_CLOUD_KEY = os.environ.get(
    "OLLAMA_CLOUD_KEY",
    "c000ecc0fa72410eb0496643c2224395.1N28OGjn8lrMdU1Z0RytCUw0",
)

MODELS: dict[str, str] = {
    "flash": "deepseek-v4-flash",
    "pro": "deepseek-v4-pro",
    "ornith": "ornith:latest",  # local only — will fail on cloud
}

# ── Data types ─────────────────────────────────────────────────────────────


@dataclass
class DirectCellResult:
    model_name: str = ""
    task_name: str = ""
    task_env: str = ""
    reward: float = 0.0
    total_calls: int = 0
    total_tool_calls: int = 0
    total_respond_calls: int = 0
    total_tokens: int = 0
    total_time: float = 0.0
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


# ── Direct agent ───────────────────────────────────────────────────────────


class DirectTauAgent(Agent):
    """τ-bench agent using native tool calling via OpenAI-compatible API.

    No text-prompt harness. No context management. No retry logic.
    Just model + tools + conversation turns.
    """

    def __init__(
        self,
        tools_info: list[dict[str, Any]],
        wiki: str,
        model_name: str,
        temperature: float = 0.0,
        timeout: int = 120,
    ):
        self.tools_info = tools_info
        self.wiki = wiki
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = timeout
        self.client = OpenAI(base_url=OLLAMA_CLOUD_BASE, api_key=OLLAMA_CLOUD_KEY)

        # Metrics
        self.call_count = 0
        self.tool_call_count = 0
        self.respond_call_count = 0
        self.total_tokens = 0
        self.total_time = 0.0

    def solve(
        self, env: Env, task_index: int | None = None, max_num_steps: int = 30
    ) -> SolveResult:
        self.call_count = 0
        self.tool_call_count = 0
        self.respond_call_count = 0
        self.total_tokens = 0
        self.total_time = 0.0

        total_cost = 0.0
        env_reset = env.reset(task_index=task_index)
        obs = env_reset.observation
        info = env_reset.info.model_dump() if env_reset.info else {}
        reward = 0.0

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.wiki},
            {"role": "user", "content": obs},
        ]

        for step in range(max_num_steps):
            start = time.time()
            try:
                res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=self.tools_info,
                    temperature=self.temperature,
                    timeout=self.timeout,
                )
            except Exception as exc:
                logger.error("API call failed at step %d: %s", step, exc)
                return SolveResult(
                    reward=0.0,
                    info={**info, "error": str(exc)},
                    messages=messages,
                    total_cost=total_cost,
                )

            elapsed = time.time() - start
            self.total_time += elapsed
            self.call_count += 1

            choice = res.choices[0]
            msg = choice.message
            usage = res.usage
            if usage:
                self.total_tokens += usage.total_tokens

            # Convert to dict for τ-bench
            msg_dict = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                tc = msg.tool_calls[0]
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                ]

            action = self._message_to_action(msg_dict)
            env_response = env.step(action)
            reward = env_response.reward
            info = {**info, **env_response.info.model_dump()}

            if action.name != RESPOND_ACTION_NAME:
                self.tool_call_count += 1
                messages.append(msg_dict)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg_dict["tool_calls"][0]["id"],
                        "name": action.name,
                        "content": env_response.observation,
                    }
                )
            else:
                self.respond_call_count += 1
                messages.append(msg_dict)
                messages.append(
                    {"role": "user", "content": env_response.observation}
                )

            if env_response.done:
                break

        return SolveResult(
            reward=reward,
            info=info,
            messages=messages,
            total_cost=total_cost,
        )

    @staticmethod
    def _message_to_action(message: dict[str, Any]) -> Action:
        tc = message.get("tool_calls")
        if tc and tc[0].get("function"):
            return Action(
                name=tc[0]["function"]["name"],
                kwargs=json.loads(tc[0]["function"]["arguments"]),
            )
        return Action(
            name=RESPOND_ACTION_NAME,
            kwargs={"content": message.get("content", "")},
        )


# ── Runner ──────────────────────────────────────────────────────────────────


def run_direct_tau(
    env_name: str = "retail",
    model_key: str = "flash",
    task_ids: list[int] | None = None,
    num_trials: int = 3,
    max_steps: int = 30,
    output_dir: str = "",
) -> DirectCellResult:
    """Run one direct τ-bench cell: one model × N tasks × N trials."""
    from tau_bench.envs import get_env
    from tau_bench.envs.airline import tools as airline_tools
    from tau_bench.envs.airline import wiki as airline_wiki
    from tau_bench.envs.retail import tools as retail_tools
    from tau_bench.envs.retail import wiki as retail_wiki

    tools_info = (
        retail_tools.ALL_TOOLS if env_name == "retail" else airline_tools.ALL_TOOLS
    )
    wiki_text = retail_wiki.WIKI if env_name == "retail" else airline_wiki.WIKI

    model_name = MODELS.get(model_key, model_key)
    tool_dicts = [t.get_info() for t in tools_info]

    cell = DirectCellResult(
        model_name=model_key,
        task_name=f"tau_{env_name}",
        task_env=env_name,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    env = get_env(
        env_name=env_name,
        user_strategy="llm",
        user_model="ollama/hermes3:latest",
        user_provider="ollama",
        task_split="test",
    )
    all_task_ids = task_ids or list(range(len(env.tasks)))

    for trial in range(num_trials):
        logger.info("Trial %d/%d for %s", trial + 1, num_trials, model_key)

        agent = DirectTauAgent(
            tools_info=tool_dicts,
            wiki=wiki_text,
            model_name=model_name,
        )

        trial_env = get_env(
            env_name=env_name,
            user_strategy="llm",
            user_model="ollama/hermes3:latest",
            user_provider="ollama",
            task_split="test",
        )

        for tid in all_task_ids:
            try:
                solve_result = agent.solve(
                    trial_env, task_index=tid, max_num_steps=max_steps
                )
                cell.reward = solve_result.reward
                cell.total_calls += agent.call_count
                cell.total_tool_calls += agent.tool_call_count
                cell.total_respond_calls += agent.respond_call_count
                cell.total_tokens += agent.total_tokens
                cell.total_time += agent.total_time

                cell.trajectory.append(
                    {
                        "trial": trial,
                        "task_id": tid,
                        "reward": solve_result.reward,
                        "steps": len(solve_result.messages) // 2,
                        "tool_calls": agent.tool_call_count,
                        "respond_calls": agent.respond_call_count,
                        "tokens": agent.total_tokens,
                        "time": agent.total_time,
                    }
                )

                if solve_result.reward >= 0.9 and len(solve_result.messages) < 4:
                    cell.flags.append(
                        f"SHORTCUT: task={tid} trial={trial} "
                        f"reward={solve_result.reward}"
                    )

            except Exception as exc:
                logger.error("Task %d failed: %s", tid, exc)
                cell.flags.append(f"ERROR: task={tid} trial={trial} {exc}")

    cell.completed_at = datetime.now(timezone.utc).isoformat()

    # Save
    output_dir = output_dir or os.path.join(
        os.path.expanduser("~"), ".observeco", "grid", "direct"
    )
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{model_key}_{env_name}.json")
    with open(path, "w") as f:
        json.dump(
            {
                "model": cell.model_name,
                "task": cell.task_name,
                "env": cell.task_env,
                "reward": cell.reward,
                "total_calls": cell.total_calls,
                "total_tool_calls": cell.total_tool_calls,
                "total_respond_calls": cell.total_respond_calls,
                "total_tokens": cell.total_tokens,
                "total_time": cell.total_time,
                "flags": cell.flags,
                "trajectory_count": len(cell.trajectory),
                "started_at": cell.started_at,
                "completed_at": cell.completed_at,
            },
            f,
            indent=2,
        )
    logger.info("Direct results saved to %s", path)
    return cell
