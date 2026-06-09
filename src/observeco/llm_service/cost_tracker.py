"""Daily LLM cost tracking — budget cap, per-call recording, summary.

Prevents bill shock on heavy crash days. Default budget: $0.10/day.
Configurable via OBSERVECO_LLM_BUDGET env var (in cents).
"""

from __future__ import annotations

import os
import time


class CostTracker:
    """Tracks LLM API costs within a daily budget.

    Resets daily (based on a monotonic day counter).
    """

    def __init__(self):
        self._day = self._today()
        self._total_cents = 0.0
        self._calls: list[dict] = []

    @property
    def daily_budget_cents(self) -> float:
        """Daily budget in cents. Default: $0.10/day = 10 cents."""
        return float(os.environ.get("OBSERVECO_LLM_BUDGET", "10"))

    def _today(self) -> int:
        """Return a day counter (resets daily)."""
        return int(time.time()) // 86400

    def _reset_if_new_day(self) -> None:
        day = self._today()
        if day != self._day:
            self._day = day
            self._total_cents = 0.0
            self._calls = []

    def would_accept(self, consumer: str, max_cost_cents: float) -> bool:
        """Check if this call would fit within the daily budget."""
        self._reset_if_new_day()
        if max_cost_cents <= 0:
            return False
        # Check if single call exceeds budget (sanity)
        if max_cost_cents > self.daily_budget_cents:
            return False
        # Check if we have room
        return self._total_cents + max_cost_cents <= self.daily_budget_cents

    def record(self, *, consumer: str, input_tokens: int, output_tokens: int,
               provider: str, duration_sec: float) -> None:
        """Record a completed LLM call.

        Costs are estimated based on provider pricing.
        If the actual cost can't be determined, a nominal 0.002 cents/token
        estimate is used (roughly $0.02/M input tokens for cloud providers).
        """
        self._reset_if_new_day()
        # Rough cost estimate: $0.15/M input, $0.60/M output for cloud
        input_cost = (input_tokens / 1_000_000) * 0.15 * 100  # in cents
        output_cost = (output_tokens / 1_000_000) * 0.60 * 100  # in cents
        actual_cost = input_cost + output_cost

        self._total_cents += actual_cost
        self._calls.append({
            "consumer": consumer,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_cents": round(actual_cost, 4),
            "duration_sec": round(duration_sec, 2),
            "timestamp": time.time(),
        })

        # Keep last 1000 calls for summary
        if len(self._calls) > 1000:
            self._calls = self._calls[-1000:]

    def remaining(self) -> float:
        """Return remaining budget in cents."""
        self._reset_if_new_day()
        return max(0.0, self.daily_budget_cents - self._total_cents)

    def summary(self) -> dict:
        """Return today's cost summary."""
        self._reset_if_new_day()
        return {
            "budget_cents": self.daily_budget_cents,
            "spent_cents": round(self._total_cents, 4),
            "remaining_cents": round(self.remaining(), 4),
            "calls_today": len(self._calls),
            "recent_calls": self._calls[-5:] if self._calls else [],
        }
