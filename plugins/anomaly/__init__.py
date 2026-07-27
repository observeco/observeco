"""Anomaly Detection plugin — session-end hook + CLI.

Registers on_session_end hook. Scans Hermes state.db for anomalies.
Zero external deps. stdlib only.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from .anomaly_core import detect_anomalies, format_anomalies

logger = logging.getLogger(__name__)

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
STATE_DB = HERMES_HOME / "state.db"


def on_session_end(session_id: str, model: str = "", profile: str = "") -> None:
    """Hook handler: scan for anomalies after each session ends."""
    if not STATE_DB.exists():
        logger.debug("anomaly: state.db not found — skipping")
        return

    anomalies = detect_anomalies(str(STATE_DB), lookback_minutes=30)
    if anomalies:
        critical = [a for a in anomalies if a["severity"] == "critical"]
        if critical:
            logger.warning(
                "anomaly: %d critical anomalies detected after session %s",
                len(critical), session_id,
            )


def register(ctx) -> None:
    """Register the on_session_end hook."""
    ctx.register_hook("on_session_end", on_session_end)
    logger.info("Anomaly plugin registered — will scan for anomalies on session end")