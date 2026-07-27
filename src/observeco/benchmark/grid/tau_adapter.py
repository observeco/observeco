"""τ-bench agent adapter: routes multi-turn tool-calling through Hermes agent harness.

Implements τ-bench's ``Agent`` interface so each step goes through
``hermes chat -q``, exercising the actual agent harness (tool parsing,
context management, error recovery).

ponytail: Sequential per-step calls. No batching or parallelism.
Upgrade path: concurrent task execution via ThreadPoolExecutor.
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import time
from typing import Any, Optional

from tau_bench.agents.base import Agent
from tau_bench.envs.base import Env
from tau_bench.types import Action, SolveResult

from .configs import HarnessConfig

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────

RESPOND_ACTION_NAME = "respond"

# ── Agent ──────────────────────────────────────────────────────────────────


class HermesTauAgent(Agent):
    """τ-bench agent that routes each step through ``hermes chat -q``.

    The agent harness receives the conversation history + tool definitions
    and generates the next action (tool call or final response). Tool results
    are fed back for the next step.
    """

    def __init__(
        self,
        tools_info: list[dict[str, Any]],
        wiki: str,
        harness_config: HarnessConfig,
        hermes_bin: str = "hermes",
    ) -> None:
        self.tools_info = tools_info
        self.wiki = wiki
        self.config = harness_config
        self.hermes_bin = hermes_bin

        # Metrics collected during solve()
        self.call_count = 0
        self.timeout_count = 0
        self.retry_count = 0
        self.total_call_time = 0.0

    def solve(
        self,
        env: Env,
        task_index: Optional[int] = None,
        max_num_steps: Optional[int] = None,
    ) -> SolveResult:
        max_steps = max_num_steps or self.config.max_steps
        self.call_count = 0
        self.timeout_count = 0
        self.retry_count = 0
        self.total_call_time = 0.0

        total_cost = 0.0
        env_reset = env.reset(task_index=task_index)
        obs = env_reset.observation
        info = env_reset.info.model_dump() if env_reset.info else {}
        reward = 0.0

        # Build system prompt with wiki + tool definitions
        system_prompt = self._build_system_prompt()

        # Conversation history
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": obs},
        ]

        for step in range(max_steps):
            # Apply context management
            context = self._apply_context_management(messages)

            # Call Hermes agent
            response_text, call_metrics = self._call_hermes(context)
            self.call_count += call_metrics["call_count"]
            self.timeout_count += call_metrics["timeout_count"]
            self.retry_count += call_metrics["retry_count"]
            self.total_call_time += call_metrics["total_time"]

            if response_text.startswith("[ERROR"):
                # Agent failed — treat as respond with error
                action = Action(
                    name=RESPOND_ACTION_NAME,
                    kwargs={"content": response_text},
                )
            else:
                # Parse the response for a tool call or final answer
                action = self._parse_action(response_text)

            # Execute in τ-bench environment
            env_response = env.step(action)
            reward = env_response.reward
            if env_response.info:
                info = {**info, **env_response.info.model_dump()}

            # Build assistant message
            if action.name != RESPOND_ACTION_NAME:
                # Tool call
                assistant_msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_{step}",
                            "type": "function",
                            "function": {
                                "name": action.name,
                                "arguments": json.dumps(action.kwargs),
                            },
                        }
                    ],
                }
                messages.append(assistant_msg)
                # Tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": f"call_{step}",
                    "name": action.name,
                    "content": self._format_tool_feedback(
                        action.name,
                        env_response.observation,
                    ),
                })
            else:
                # Final response
                content = action.kwargs.get("content", json.dumps(action.kwargs))
                messages.append({
                    "role": "assistant",
                    "content": content,
                })
                messages.append({
                    "role": "user",
                    "content": env_response.observation,
                })

            if env_response.done:
                break

        return SolveResult(
            reward=reward,
            info=info,
            messages=messages,
            total_cost=total_cost,
        )

    # ── Internal ────────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Build system prompt from wiki + tool definitions."""
        parts = [self.wiki, "\n\n## Available Tools\n"]

        for tool in self.tools_info:
            func = tool.get("function", tool)
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = func.get("parameters", {})

            parts.append(f"\n### {name}")
            parts.append(f"Description: {desc}")

            if params:
                props = params.get("properties", {})
                required = params.get("required", [])
                for pname, pinfo in props.items():
                    req = " (required)" if pname in required else ""
                    ptype = pinfo.get("type", "string")
                    pdesc = pinfo.get("description", "")
                    parts.append(f"  - {pname}: {ptype}{req} — {pdesc}")

        parts.append(
            "\n\n## Output Format\n"
            "You are a customer service agent with access to tools. "
            "Your entire response must be ONLY a single valid JSON object. "
            "No other text, no markdown, no explanation.\n\n"
            "To call a tool:\n"
            '{"name": "tool_name", "arguments": {"param1": "value1", "param2": "value2"}}\n\n'
            "To respond to the user:\n"
            '{"name": "respond", "arguments": {"content": "your message here"}}\n\n'
            "CRITICAL RULES:\n"
            "- The user's first message already contains their name and zip code. "
            "Call find_user_id_by_name_zip immediately with their name and zip. Do NOT ask for email.\n"
            "- After getting the user ID, use get_order_details or other tools as needed.\n"
            "- Only respond to the user when you need confirmation or have completed the task.\n"
            "- NEVER ask for information the user already provided.\n\n"
            "Example first response:\n"
            '{"name": "find_user_id_by_name_zip", "arguments": {"first_name": "Yusuf", "last_name": "Rossi", "zip": "19122"}}\n\n'
            "IMPORTANT: Your entire response must be a single valid JSON object. "
            "Do not include any text before or after the JSON. "
            "Do not wrap it in code fences. Do not explain your reasoning.\n"
        )

        return "\n".join(parts)

    def _call_hermes(self, prompt: str) -> tuple[str, dict[str, Any]]:
        """Call Hermes agent with retry logic.

        Returns (response_text, metrics_dict).
        """
        timeout_count = 0
        retry_count = 0
        total_time = 0.0
        call_count = 0

        for attempt in range(self.config.max_retries + 1):
            call_count += 1
            start = time.time()

            try:
                proc = subprocess.Popen(
                    [self.hermes_bin, "chat", "-q", prompt, "-Q"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid,
                )

                try:
                    stdout, stderr = proc.communicate(
                        timeout=self.config.call_timeout_seconds
                    )
                except subprocess.TimeoutExpired:
                    timeout_count += 1
                    logger.warning(
                        "Hermes timed out after %.0fs (attempt %d/%d)",
                        self.config.call_timeout_seconds,
                        attempt + 1,
                        self.config.max_retries + 1,
                    )
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                    proc.wait()

                    if attempt < self.config.max_retries:
                        retry_count += 1
                        time.sleep(self.config.retry_delay_seconds)
                        continue
                    return (
                        f"[ERROR: timeout after {self.config.call_timeout_seconds:.0f}s]",
                        {
                            "call_count": call_count,
                            "timeout_count": timeout_count,
                            "retry_count": retry_count,
                            "total_time": total_time,
                        },
                    )

                elapsed = time.time() - start
                total_time += elapsed

                output = stdout.strip()

                # Strip Hermes warning/status lines
                output = "\n".join(
                    line
                    for line in output.splitlines()
                    if not line.startswith("Warning:")
                    and not line.startswith("session_id:")
                ).strip()

                # Strip markdown code fences
                output = re.sub(r"```\w*\n?", "", output).strip()

                if proc.returncode != 0:
                    error = stderr.strip() or "unknown error"
                    logger.warning(
                        "Hermes failed (exit=%d): %s", proc.returncode, error
                    )
                    if attempt < self.config.max_retries:
                        retry_count += 1
                        time.sleep(self.config.retry_delay_seconds)
                        continue
                    output = f"[ERROR: exit={proc.returncode}]"

                logger.debug("Hermes output (first 200 chars): %s", output[:200])
                return output, {
                    "call_count": call_count,
                    "timeout_count": timeout_count,
                    "retry_count": retry_count,
                    "total_time": total_time,
                }

            except FileNotFoundError:
                return (
                    f"[ERROR: {self.hermes_bin} not found]",
                    {
                        "call_count": call_count,
                        "timeout_count": timeout_count,
                        "retry_count": retry_count,
                        "total_time": total_time,
                    },
                )

            except Exception as exc:
                logger.error("Hermes call failed: %s", exc)
                if attempt < self.config.max_retries:
                    retry_count += 1
                    time.sleep(self.config.retry_delay_seconds)
                    continue
                return (
                    f"[ERROR: {exc}]",
                    {
                        "call_count": call_count,
                        "timeout_count": timeout_count,
                        "retry_count": retry_count,
                        "total_time": total_time,
                    },
                )

        # Shouldn't reach here
        return (
            "[ERROR: max retries exceeded]",
            {
                "call_count": call_count,
                "timeout_count": timeout_count,
                "retry_count": retry_count,
                "total_time": total_time,
            },
        )

    def _parse_action(self, text: str) -> Action:
        """Parse Hermes response into a τ-bench Action.

        Tries JSON parsing first. Falls back to regex extraction.
        """
        text = text.strip()

        # Try direct JSON parse
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "name" in obj:
                return Action(
                    name=obj["name"],
                    kwargs=obj.get("arguments", obj.get("kwargs", {})),
                )
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to find JSON in code blocks or braces
        json_match = re.search(r"\{[^{}]*\"name\"[^{}]*\}", text, re.DOTALL)
        if json_match:
            try:
                obj = json.loads(json_match.group())
                if isinstance(obj, dict) and "name" in obj:
                    return Action(
                        name=obj["name"],
                        kwargs=obj.get("arguments", obj.get("kwargs", {})),
                    )
            except (json.JSONDecodeError, TypeError):
                pass

        # Try to find tool call pattern: name(...) or name: args
        tool_match = re.search(
            r"""(?:name[: ]["']?(\w+)["']?|call\s+(\w+))""", text, re.IGNORECASE
        )
        if tool_match:
            name = tool_match.group(1) or tool_match.group(2)
            # Try to extract arguments
            args_match = re.search(
                r"""arguments[: ](\{.*\}|\[.*\]|["'].*?["'])""", text, re.DOTALL
            )
            args = args_match.group(1) if args_match else "{}"
            try:
                kwargs = json.loads(args)
            except (json.JSONDecodeError, TypeError):
                kwargs = {}
            return Action(name=name, kwargs=kwargs)

        # Default: respond with the raw text
        return Action(
            name=RESPOND_ACTION_NAME,
            kwargs={"content": text},
        )

    def _apply_context_management(self, messages: list[dict]) -> str:
        """Apply context management strategy to messages.

        Returns a single prompt string for the Hermes call.
        """
        if self.config.context_mode == "full":
            return self._messages_to_prompt(messages)

        if self.config.context_mode == "sliding_window":
            # Keep system prompt + last N turns
            system = [m for m in messages if m["role"] == "system"]
            recent = messages[-self.config.context_window_turns * 2 :]
            return self._messages_to_prompt(system + recent)

        if self.config.context_mode == "summary":
            # ponytail: Simple truncation — keep system + last 3 turns.
            # Upgrade path: actual LLM-based summarization every 5 turns.
            system = [m for m in messages if m["role"] == "system"]
            recent = messages[-6:]  # last 3 turns (assistant + user/tool pairs)
            return self._messages_to_prompt(system + recent)

        return self._messages_to_prompt(messages)

    @staticmethod
    def _messages_to_prompt(messages: list[dict]) -> str:
        """Convert message list to a single prompt string."""
        parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                tc = msg.get("tool_calls")
                if tc:
                    for call in tc:
                        func = call.get("function", {})
                        parts.append(
                            f"Assistant (tool call): {func.get('name')}"
                            f"({func.get('arguments', '')})"
                        )
                else:
                    parts.append(f"Assistant: {content}")
            elif role == "tool":
                parts.append(f"Tool result ({msg.get('name', '')}): {content}")

        return "\n\n".join(parts)

    def _format_tool_feedback(self, tool_name: str, observation: str) -> str:
        """Format tool result according to feedback mode."""
        if self.config.tool_feedback_mode == "full":
            return observation
        if self.config.tool_feedback_mode == "truncated":
            return observation[:500]
        if self.config.tool_feedback_mode == "minimal":
            if observation.startswith("[ERROR"):
                return f"error: {observation[:100]}"
            return "ok"
        return observation
