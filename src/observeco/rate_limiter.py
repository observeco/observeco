"""Rate limiter for outbound API calls.

Provides per-host rate limiting with exponential backoff on 429 responses.
Used by Slack, Discord, and Telegram adapters.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Tracks rate limit state for a single host."""
    requests: list[float] = field(default_factory=list)
    retry_after: float = 0  # Until when we should wait (from 429 Retry-After)
    consecutive_429s: int = 0


class RateLimiter:
    """Per-host rate limiter with exponential backoff.

    Usage:
        limiter = RateLimiter(max_per_second=1.0, burst=5)
        limiter.wait_if_needed("slack.com")
        # ... make API call ...
        limiter.record_response("slack.com", status_code)
    """

    def __init__(
        self,
        max_per_second: float = 1.0,
        burst: int = 5,
        backoff_base: float = 1.0,
        backoff_max: float = 60.0,
    ):
        self.max_per_second = max_per_second
        self.burst = burst
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self._hosts: dict[str, RateLimitState] = defaultdict(RateLimitState)

    def wait_if_needed(self, host: str) -> None:
        """Block if we need to wait before making a request to host."""
        state = self._hosts[host]
        now = time.time()

        # Check if we're in a retry-after cooldown
        if state.retry_after > now:
            wait_time = state.retry_after - now
            logger.info(f"Rate limiter: waiting {wait_time:.1f}s for {host} (retry-after)")
            time.sleep(wait_time)
            return

        # Prune requests older than 1 second
        cutoff = now - 1.0
        state.requests = [t for t in state.requests if t > cutoff]

        # If we've hit the per-second limit, wait
        if len(state.requests) >= self.burst:
            oldest = state.requests[0]
            wait_time = 1.0 - (now - oldest)
            if wait_time > 0:
                logger.debug(f"Rate limiter: waiting {wait_time:.2f}s for {host} (burst limit)")
                time.sleep(wait_time)

        # Also enforce per-second rate
        if len(state.requests) >= self.max_per_second:
            wait_time = 1.0 / self.max_per_second
            logger.debug(f"Rate limiter: waiting {wait_time:.2f}s for {host} (rate limit)")
            time.sleep(wait_time)

        state.requests.append(time.time())

    def record_response(self, host: str, status_code: int, headers: Optional[dict] = None) -> None:
        """Record a response to update rate limit state.

        On 429, parses Retry-After and applies exponential backoff.
        """
        state = self._hosts[host]

        if status_code == 429:
            state.consecutive_429s += 1

            # Parse Retry-After header
            retry_after = 0
            if headers:
                retry_after_header = headers.get("Retry-After", headers.get("retry-after", ""))
                if retry_after_header:
                    try:
                        retry_after = float(retry_after_header)
                    except ValueError:
                        pass

            # Exponential backoff if no Retry-After header
            if retry_after <= 0:
                retry_after = min(
                    self.backoff_base * (2 ** (state.consecutive_429s - 1)),
                    self.backoff_max,
                )

            state.retry_after = time.time() + retry_after
            logger.warning(
                f"Rate limiter: {host} returned 429, backing off {retry_after:.1f}s "
                f"(consecutive: {state.consecutive_429s})"
            )
        elif status_code < 400:
            # Successful request — reset consecutive count
            state.consecutive_429s = 0

    def get_state(self, host: str) -> dict:
        """Get current rate limit state for a host (for debugging)."""
        state = self._hosts[host]
        now = time.time()
        return {
            "host": host,
            "recent_requests": len([t for t in state.requests if t > now - 1.0]),
            "retry_after_remaining": max(0, state.retry_after - now),
            "consecutive_429s": state.consecutive_429s,
        }


# Module-level singleton — shared across all adapters
_default_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the default rate limiter instance."""
    return _default_limiter
