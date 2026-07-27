"""Context Quality Preflight plugin — session-start hook + CLI.

Scores agent context against 7 criteria from arxiv 2607.14275.
Zero external deps. Regex-only pass.

Cite: Bousetouane (U Chicago / ProofAgent.ai) — the 7-criteria construct.
Our contribution: runtime integration, trending, baseline enforcement.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .preflight_core import score_prompt, format_report, load_system_prompt, load_soul

logger = logging.getLogger(__name__)


def on_session_start(session_id: str, model: str = "", platform: str = "") -> None:
    """Hook handler: score context quality on session start."""
    prompt = load_system_prompt()
    if not prompt or len(prompt) < 100:
        logger.debug("preflight: prompt too short — skipping")
        return

    result = score_prompt(prompt, load_soul())
    if "error" in result:
        logger.debug("preflight: %s", result["error"])
        return

    grade = result["grade"]
    if grade == "Weak":
        logger.warning(
            "preflight: context quality is WEAK (%.1f/10) — run 'hermes preflight scan' for details",
            result["overall_score"],
        )
    else:
        logger.debug("preflight: %s (%.1f/10)", grade, result["overall_score"])


def register(ctx) -> None:
    ctx.register_hook("on_session_start", on_session_start)
    logger.info("Preflight plugin registered — will score context on session start")