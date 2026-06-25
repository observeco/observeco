"""Auto-loader for SDK instrumentation — triggered by sdk_auto.pth on Python startup.

Safe to import in any context; never raises. The .pth file in site-packages
calls this module, which applies SDK patchers only if OBSERVECO_AUTO_PATCH=1.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from observeco.tracking.sdk import _auto_apply

    _auto_apply()
except Exception:
    logger.debug("SDK auto-loader skipped (Hermes not installed or patchers unavailable)")
