"""LLM response cache — SHA256(prompt+context) → response with TTL.

Reduces cost by avoiding duplicate LLM calls for identical inputs within
the cache window. Cleared on provider change or manual clear_cache() call.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Optional


class LLMCache:
    """Simple in-memory cache keyed by SHA256 of (system_prompt + context).

    Max 256 entries to prevent memory leak. LRU eviction.
    """

    MAX_ENTRIES = 256

    def __init__(self):
        self._entries: OrderedDict[str, tuple[str, float]] = OrderedDict()

    def get(self, cache_key: str, *, max_age_secs: int = 300) -> Optional[str]:
        """Return cached response if fresh, else None."""
        if cache_key not in self._entries:
            return None
        response, timestamp = self._entries[cache_key]
        if time.monotonic() - timestamp > max_age_secs:
            # Stale — remove
            del self._entries[cache_key]
            return None
        # Move to end (LRU)
        self._entries.move_to_end(cache_key)
        return response

    def set(self, cache_key: str, response: str) -> None:
        """Store response in cache."""
        self._entries[cache_key] = (response, time.monotonic())
        # Evict oldest if over limit
        while len(self._entries) > self.MAX_ENTRIES:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached responses."""
        self._entries.clear()

    def size(self) -> int:
        return len(self._entries)

    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "entries": len(self._entries),
            "max_entries": self.MAX_ENTRIES,
        }
