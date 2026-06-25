"""Cost tracking tier selection — reads EnvSnapshot, returns best supported tier.

No OS specifics here: no os.path resolution, no psutil, no yaml, no socket.
The probe layer populates the snapshot; this function reads it.
"""

from __future__ import annotations

from observeco.capability.env_snapshot import EnvSnapshot


def select_cost_tracking_tier(snap: EnvSnapshot) -> tuple[str, str, str]:
    """Return (tier_name, quality, description) for the best supported cost-tracking tier.

    Tier ladder (highest to lowest):
      proxy-launcher  — agent launched via `observeco run --`; env-injected, crash-safe
      proxy-config    — persistent config rewrite; requires reconciler (opt-in)
      session-store   — read runtime usage logs; near-exact, delayed
      estimate        — context sizing × pricing; always available
    """
    if snap.config_parsed is not None and snap.chosen_port is not None:
        return ("proxy-launcher", "exact", "real-time via env injection")
    if (
        snap.config_parsed is not None
        and snap.config_writable
        and snap.chosen_port is not None
    ):
        return ("proxy-config", "exact", "real-time via config rewrite")
    if snap.session_store_path is not None:
        return ("session-store", "near-exact", "delayed from session logs")
    return ("estimate", "approximate", "context sizing × pricing")
