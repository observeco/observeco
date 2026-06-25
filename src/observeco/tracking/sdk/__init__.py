"""SDK auto-instrumentation — detect installed SDKs and apply token logging patches.

Auto-applies all available patchers when OBSERVECO_AUTO_PATCH=1 is set.
Place sdk_auto.pth in site-packages to trigger this on Python startup.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _auto_apply() -> None:
    """Apply all available SDK patchers if OBSERVECO_AUTO_PATCH=1.

    Safe to call multiple times — patchers are idempotent.
    Never raises; failures are logged as warnings.
    """
    if os.environ.get("OBSERVECO_AUTO_PATCH") != "1":
        return
    try:
        from observeco.tracking.sdk.patcher_registry import apply_all_patchers

        results = apply_all_patchers()
        for name, ok in results.items():
            if ok:
                logger.info("Auto-patched %s SDK", name)
            else:
                logger.warning("Auto-patch skipped %s (SDK not installed)", name)
    except Exception as exc:
        logger.warning("SDK auto-patch failed: %s", exc)


_auto_apply()
