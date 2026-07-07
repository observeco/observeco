"""Harness configuration variations for the grid.

Each config varies ONE component at a time, in priority order:
1. Per-call timeout + retry policy
2. Tool-result/error feedback
3. Context management
4. Max-step budget (later)
5. System-prompt/tool-schema wording (later)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HarnessConfig:
    """A single cell in the grid: one harness configuration."""

    # Identity
    name: str
    description: str

    # 1. Per-call timeout + retry policy
    call_timeout_seconds: float = 60.0
    max_retries: int = 1
    retry_delay_seconds: float = 2.0

    # 2. Tool-result/error feedback
    #   "full" = complete tool output
    #   "truncated" = first 500 chars
    #   "minimal" = "ok" / "error: <type>"
    tool_feedback_mode: str = "full"

    # 3. Context management
    #   "full" = entire conversation history
    #   "sliding_window" = last N turns
    #   "summary" = periodic summarization
    context_mode: str = "full"

    # 4. Self-check: verify each answer before submission
    #   ponytail: Doubles API calls per sample. Upgrade path: skip for
    #   knowledge tasks where verification doesn't help.
    self_check: bool = False
    context_window_turns: int = 50  # for sliding_window

    # 4. Max-step budget
    max_steps: int = 30

    # 5. System prompt style
    system_prompt_style: str = "default"  # "default" | "terse" | "verbose"


# ── Baseline config (current production behavior) ──────────────────────────

BASELINE = HarnessConfig(
    name="baseline",
    description="Current production: 60s timeout, 1 retry, full tool feedback, full context",
    call_timeout_seconds=60.0,
    max_retries=1,
    tool_feedback_mode="full",
    context_mode="full",
)

# ── Axis 1: Timeout + retry variations ────────────────────────────────────

TIMEOUT_AGGRESSIVE = HarnessConfig(
    name="timeout_aggressive",
    description="30s timeout, 0 retries — fail fast",
    call_timeout_seconds=30.0,
    max_retries=0,
    tool_feedback_mode="full",
    context_mode="full",
)

TIMEOUT_GENEROUS = HarnessConfig(
    name="timeout_generous",
    description="120s timeout, 2 retries — never give up",
    call_timeout_seconds=120.0,
    max_retries=2,
    retry_delay_seconds=3.0,
    tool_feedback_mode="full",
    context_mode="full",
)

# ── Axis 2: Tool feedback variations ──────────────────────────────────────

FEEDBACK_TRUNCATED = HarnessConfig(
    name="feedback_truncated",
    description="Tool output truncated to 500 chars",
    call_timeout_seconds=60.0,
    max_retries=1,
    tool_feedback_mode="truncated",
    context_mode="full",
)

FEEDBACK_MINIMAL = HarnessConfig(
    name="feedback_minimal",
    description="Tool output: 'ok' or 'error: <type>' only",
    call_timeout_seconds=60.0,
    max_retries=1,
    tool_feedback_mode="minimal",
    context_mode="full",
)

# ── Axis 3: Context management variations ─────────────────────────────────

CONTEXT_SLIDING = HarnessConfig(
    name="context_sliding",
    description="Sliding window of last 10 turns",
    call_timeout_seconds=60.0,
    max_retries=1,
    tool_feedback_mode="full",
    context_mode="sliding_window",
    context_window_turns=10,
)

CONTEXT_SUMMARY = HarnessConfig(
    name="context_summary",
    description="Summarize every 5 turns, keep last 3 turns raw",
    call_timeout_seconds=60.0,
    max_retries=1,
    tool_feedback_mode="full",
    context_mode="summary",
)

# ── Axis 4: Self-check variations ──────────────────────────────────────────

SELF_CHECK = HarnessConfig(
    name="self_check",
    description="Verify each answer before submission (Maka-style)",
    call_timeout_seconds=60.0,
    max_retries=1,
    tool_feedback_mode="full",
    context_mode="full",
    self_check=True,
)

# ── All configs for the grid ──────────────────────────────────────────────

ALL_CONFIGS: list[HarnessConfig] = [
    BASELINE,
    TIMEOUT_AGGRESSIVE,
    TIMEOUT_GENEROUS,
    FEEDBACK_TRUNCATED,
    FEEDBACK_MINIMAL,
    CONTEXT_SLIDING,
    CONTEXT_SUMMARY,
    SELF_CHECK,
]
