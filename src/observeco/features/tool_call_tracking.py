"""Tool-call tracking tier selection — reads EnvSnapshot, returns best supported tier.

No OS specifics here: no os.path resolution, no psutil, no yaml, no socket.
The probe layer populates the snapshot; this function reads it.
"""

from __future__ import annotations

from observeco.capability.env_snapshot import EnvSnapshot


def select_tool_call_tier(snap: EnvSnapshot) -> tuple[str, str, str]:
    """Return (tier_name, quality, description) for the best supported tool-call tier.

    Tier ladder (highest to lowest):
      proxy-intercept — parse tool_calls from request/response; exact
      session-store   — read from session logs; near-exact, delayed
      disabled        — no proxy, no session store; enable proxy to capture
    """
    if snap.config_parsed is not None and snap.chosen_port is not None:
        return ("proxy-intercept", "exact", "parse tool_calls from request/response")
    if snap.session_store_path is not None:
        return ("session-store", "near-exact", "delayed from session logs")
    return ("disabled", "none", "enable proxy to capture tool-call data")
