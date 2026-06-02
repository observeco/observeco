"""LLM service gate — decides whether to call LLM or return static fallback.

Gating logic:
- Trial/Pro → full LLM intelligence (all tiers)
- Free → static fallback only (no LLM calls)
- --no-llm opt-out → always static, no trial clock consumed
- Tier 2 (shallow) can be selectively disabled without affecting Tier 1
"""

from __future__ import annotations

import os

from observeco.license import load as _load_license


class LLMGate:
    """Gate for LLM service calls."""

    def __init__(self):
        self._no_llm_flag = os.environ.get("OBSERVECO_NO_LLM", "").lower() in ("1", "true", "yes")

    @property
    def no_llm(self) -> bool:
        """Check the --no-llm opt-out flag."""
        return self._no_llm_flag

    @no_llm.setter
    def no_llm(self, value: bool) -> None:
        self._no_llm_flag = value

    def should_call(self, *, consumer: str, tier: int = 1) -> bool:
        """Return True if the LLM should be called.

        Args:
            consumer: Name of the consumer module (for future per-consumer gates).
            tier: 1 (deep/mission-critical) or 2 (shallow/value-add).
        """
        # Opt-out always skips
        if self._no_llm_flag:
            return False

        # Check license — trial and Pro get full access
        lic = _load_license()
        if lic.is_trial_active or lic.is_pro:
            return True

        # Free tier: no LLM
        return False

    def is_trial_active(self) -> bool:
        """Check if trial is active (for trial-specific UI)."""
        return _load_license().is_trial_active

    def is_pro(self) -> bool:
        """Check if Pro license is active."""
        return _load_license().is_pro