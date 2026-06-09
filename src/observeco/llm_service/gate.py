"""LLM service gate — decides whether to call LLM or return static fallback.

Gating logic (corrected per product design):
- First 30 days (new-user LLM grace): Tier 1 (deep) always ON to show value.
  Tier 2 (shallow) ON only if trial or Pro active.
  Reason: deep calls (discovery, onboarding, heal) prove ObserveCo's worth.
- Trial/Pro: full LLM intelligence (all tiers).
- After 30 days + no trial/Pro: all LLM turns off.
- --no-llm opt-out: always static (all tiers). No trial clock consumed.

The --no-llm flag can be set via:
  1. CLI flag (sets OBSERVECO_NO_LLM env var)
  2. Dashboard Settings toggle (persists to DB, runtime_opt_out flag)
  3. OS environment variable permanently
"""

from __future__ import annotations

import os

from observeco.license import load as _load_license

# Runtime opt-out flag — set by dashboard toggle POST endpoint.
# Checked in addition to the env var so the dashboard toggle works
# without requiring a process restart.
_runtime_opt_out: bool = False


def set_runtime_opt_out(disabled: bool) -> None:
    """Set the runtime opt-out flag from the dashboard toggle endpoint."""
    global _runtime_opt_out
    _runtime_opt_out = disabled
    # Also sync the env var so any future gate instances see it
    if disabled:
        os.environ["OBSERVECO_NO_LLM"] = "true"
    else:
        os.environ.pop("OBSERVECO_NO_LLM", None)


class LLMGate:
    """Gate for LLM service calls."""

    def __init__(self):
        self._no_llm_flag = (
            _runtime_opt_out
            or os.environ.get("OBSERVECO_NO_LLM", "").lower() in ("1", "true", "yes")
        )

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
        # Check runtime opt-out (dashboard toggle) + env var
        is_opted_out = _runtime_opt_out or os.environ.get("OBSERVECO_NO_LLM", "").lower() in ("1", "true", "yes")
        if is_opted_out:
            return False

        lic = _load_license()

        # Trial or Pro: full access
        if lic.is_trial_active or lic.is_pro:
            return True

        # New-user grace period: Tier 1 (deep) always ON for first 30 days
        # to show ObserveCo's value. Tier 2 (shallow) still requires trial/Pro.
        if tier == 1 and lic.is_new_user_llm_grace:
            return True

        # Free tier (outside 30-day grace): no LLM
        return False

    def is_trial_active(self) -> bool:
        """Check if trial is active (for trial-specific UI)."""
        return _load_license().is_trial_active

    def is_pro(self) -> bool:
        """Check if Pro license is active."""
        return _load_license().is_pro
