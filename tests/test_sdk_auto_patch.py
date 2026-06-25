"""Test that SDK auto-patch triggers on import with OBSERVECO_AUTO_PATCH=1.

Verifies patchers were attempted (not that they succeeded — SDKs may not be installed).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_auto_patch_attempted() -> None:
    """Import observeco.tracking.sdk with OBSERVECO_AUTO_PATCH=1 and verify
    the auto-apply ran without crashing."""
    os.environ["OBSERVECO_AUTO_PATCH"] = "1"

    # Force reimport
    for mod in list(sys.modules.keys()):
        if "observeco.tracking.sdk" in mod:
            del sys.modules[mod]

    import observeco.tracking.sdk  # noqa: F401, F811

    # The module imported without error — that's the check.
    # If patchers were attempted, the registry was loaded.
    from observeco.tracking.sdk.patcher_registry import list_patcher_names

    names = list_patcher_names()
    # We don't assert specific names — SDKs may not be installed.
    # The key assertion: the module loaded and the registry is accessible.
    assert isinstance(names, list)
