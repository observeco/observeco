"""Seeded-state fixtures for ObserveCo.

Creates the three dashboard data states on a throwaway DB:
  - empty:  no agents, no pulses  -> phase 'zero'  (fresh install)
  - setup:  agents exist, no pulses -> phase 'setup' (waiting for first health check)
  - live:   agents + pulses        -> phase 'live'  (full dashboard)

These are load-bearing for three things:
  1. The referential-integrity audit's render pass (direction 6) — run it against
     a FIXED state, not the live DB, so the verdict is deterministic.
  2. The N=0 / N=1 / N=max screenshot review.
  3. The onboarding phase tests.

Each returns (db, path). Caller owns cleanup (os.unlink(path)).
"""
from __future__ import annotations

import os
import tempfile
import time

from observeco.db import Database


def _fresh_db() -> tuple[Database, str]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = Database(tmp.name)  # runs migrations, empty tables
    return db, tmp.name


def empty_db() -> tuple[Database, str]:
    """Phase 'zero': no agents, no pulses. Fresh install."""
    return _fresh_db()


def setup_db(n_agents: int = 3) -> tuple[Database, str]:
    """Phase 'setup': agents registered, no pulses yet."""
    db, path = _fresh_db()
    for i in range(n_agents):
        db.register_agent(f"agent-{i}", framework="hermes")
    return db, path


def live_db(n_agents: int = 3, n_pulses: int = 5) -> tuple[Database, str]:
    """Phase 'live': agents + pulse data. Full dashboard."""
    db, path = _fresh_db()
    for i in range(n_agents):
        db.register_agent(f"agent-{i}", framework="hermes")
        for _ in range(n_pulses):
            db.log_pulse(
                agent_name=f"agent-{i}",
                status="alive",
                latency_ms=10.0 + i,
            )
    return db, path
