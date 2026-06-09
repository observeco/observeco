"""Self-monitoring budget cap — prevents ObserveCo's own LLM diagnosis from looping.

Tracks tokens consumed by all 7 LLM consumers (self-diagnosis, not agent monitoring).
Uses a separate token pool with a default ceiling of 500K tokens/day and a
non-configurable floor of 100K tokens/day.

When the ceiling is reached, all self-diagnosis LLM calls are blocked and static
fallbacks are used instead. The budget resets at midnight (UTC day boundary).

Spec: observeco-master-plan.md §14.3.G1.1
"""
from __future__ import annotations

import time
from typing import Optional

from observeco.db import Database

# Default ceiling: 500K tokens/day for self-diagnosis
_DEFAULT_CEILING_TOKENS = 500_000
# Non-configurable floor: 100K tokens/day
_FLOOR_TOKENS = 100_000


class SelfMonitorBudget:
    """Token-based budget cap for ObserveCo's own LLM self-diagnosis calls.

    The budget is TOKEN-based (not cost-based) because users may use different
    LLM providers with different costs per token.
    """

    def __init__(self, db: Optional[Database] = None):
        self._db = db or Database()
        self._ceiling = _DEFAULT_CEILING_TOKENS
        # Floor is non-configurable by design
        self._floor = _FLOOR_TOKENS

    @property
    def ceiling(self) -> int:
        return self._ceiling

    @ceiling.setter
    def ceiling(self, value: int) -> None:
        self._ceiling = max(self._floor, value)

    @property
    def floor(self) -> int:
        return self._floor  # Always returns the hard floor

    def get_today_usage(self) -> dict:
        """Return today's usage summary from the DB."""
        return self._db.get_self_monitor_usage()

    def would_accept(self, input_tokens: int, output_tokens: int) -> bool:
        """Check if adding this call would exceed the daily ceiling.

        Args:
            input_tokens: Estimated input tokens for this call.
            output_tokens: Estimated output tokens for this call.

        Returns:
            True if the call is within budget, False if it would exceed ceiling.
        """
        usage = self.get_today_usage()
        current_total = usage.get("total_tokens", 0)
        new_total = current_total + input_tokens + output_tokens
        return new_total <= self._ceiling

    def record(self, consumer: str, input_tokens: int, output_tokens: int) -> None:
        """Record a self-monitoring call in the budget log.

        Call this AFTER the LLM call completes, not before.
        The would_accept() check is the gate; record() is the audit trail.
        """
        self._db.log_self_monitor(consumer, input_tokens, output_tokens)

    def usage_pct(self) -> float:
        """Return usage as percentage of ceiling (0.0 to 100.0+)."""
        usage = self.get_today_usage()
        total = usage.get("total_tokens", 0)
        if self._ceiling <= 0:
            return 100.0
        return round((total / self._ceiling) * 100, 1)

    def is_near_limit(self, threshold_pct: float = 90.0) -> bool:
        """Check if usage is near the ceiling."""
        return self.usage_pct() >= threshold_pct

    def is_at_limit(self) -> bool:
        """Check if usage has reached or exceeded the ceiling."""
        return self.usage_pct() >= 100.0

    def summary(self) -> dict:
        """Return a complete budget summary for the dashboard widget."""
        usage = self.get_today_usage()
        total = usage.get("total_tokens", 0)
        return {
            "total_tokens": total,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "call_count": usage.get("call_count", 0),
            "ceiling": self._ceiling,
            "floor": self._floor,
            "usage_pct": self.usage_pct(),
            "remaining": max(0, self._ceiling - total),
            "is_near_limit": self.is_near_limit(),
            "is_at_limit": self.is_at_limit(),
        }