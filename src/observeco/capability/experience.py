"""Experience bank store + retrieval (obs-spec-088 §3).

MemoHarness-style persistent memory of past harness-optimization episodes.

MVP: exact/near match on failure_class + agent_name (no new dependency).
Upgrade path: embedding-based similarity (sentence-transformers / litellm
adapter) behind a config flag requiring Sean's explicit approval.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)


class ExperienceBank:
    """Queryable store of harness-optimization experiences (per-case + global)."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    # ── Write ──────────────────────────────────────────────────────────────

    def add(
        self,
        agent_name: str,
        layer: str,
        failure_class: str,
        diagnosis: str,
        proposed_edit: str,
        outcome: str,
        source_run_id: Optional[str] = None,
        episode_ref: Optional[str] = None,
        observed_count: int = 0,
    ) -> str:
        """Insert one experience row. Returns the new row id."""
        row_id = str(uuid.uuid4())
        self.db._write(
            "INSERT INTO harness_experiences "
            "(id, agent_name, layer, source_run_id, episode_ref, failure_class, "
            "diagnosis, proposed_edit, outcome, observed_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row_id, agent_name, layer, source_run_id, episode_ref,
                failure_class, diagnosis, proposed_edit, outcome, observed_count,
            ),
        )
        return row_id

    def record_rejection(
        self,
        agent_name: str,
        failure_class: str,
        proposed_edit: str,
        reason: str,
    ) -> str:
        """Shorthand for a phantom_rejected outcome (closed-rule-set log)."""
        return self.add(
            agent_name=agent_name,
            layer="per_case",
            failure_class=failure_class,
            diagnosis=reason,
            proposed_edit=proposed_edit,
            outcome="phantom_rejected",
        )

    # ── Read ───────────────────────────────────────────────────────────────

    def retrieve_similar(
        self,
        agent_name: str,
        failure_class: str,
        layer: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Return past experiences for the same agent + failure class.

        ponytail: exact failure_class match — O(n) scan over harness_experiences.
        Fine up to ~10k rows. Upgrade path: embedding index (FAISS / sqlite-vss)
        when row count or cross-agent retrieval demands it.
        """
        if layer:
            rows = self.db._get_conn().execute(
                "SELECT * FROM harness_experiences "
                "WHERE agent_name=? AND failure_class=? AND layer=? "
                "ORDER BY created_at DESC LIMIT ?",
                (agent_name, failure_class, layer, limit),
            ).fetchall()
        else:
            rows = self.db._get_conn().execute(
                "SELECT * FROM harness_experiences "
                "WHERE agent_name=? AND failure_class=? "
                "ORDER BY created_at DESC LIMIT ?",
                (agent_name, failure_class, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def count_observations(self, failure_class: str, agent_name: str | None = None) -> int:
        """Count observed experiences for a failure class (PG-3 closed rule set)."""
        if agent_name:
            row = self.db._get_conn().execute(
                "SELECT COALESCE(SUM(observed_count), 0) AS c FROM harness_experiences "
                "WHERE failure_class=? AND agent_name=? AND outcome != 'phantom_rejected'",
                (failure_class, agent_name),
            ).fetchone()
        else:
            row = self.db._get_conn().execute(
                "SELECT COALESCE(SUM(observed_count), 0) AS c FROM harness_experiences "
                "WHERE failure_class=? AND outcome != 'phantom_rejected'",
                (failure_class,),
            ).fetchone()
        return int(row["c"]) if row else 0

    def stats(self, agent_name: str) -> dict:
        """Aggregate stats for the dashboard experience view."""
        conn = self.db._get_conn()
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM harness_experiences WHERE agent_name=?",
            (agent_name,),
        ).fetchone()["c"]
        per_layer = conn.execute(
            "SELECT layer, COUNT(*) AS c FROM harness_experiences "
            "WHERE agent_name=? GROUP BY layer",
            (agent_name,),
        ).fetchall()
        rejection_log = conn.execute(
            "SELECT id, failure_class, diagnosis, proposed_edit, created_at "
            "FROM harness_experiences WHERE agent_name=? AND outcome='phantom_rejected' "
            "ORDER BY created_at DESC LIMIT 50",
            (agent_name,),
        ).fetchall()
        failures = conn.execute(
            "SELECT failure_class, SUM(observed_count) AS c FROM harness_experiences "
            "WHERE agent_name=? AND outcome != 'phantom_rejected' GROUP BY failure_class "
            "ORDER BY c DESC LIMIT 20",
            (agent_name,),
        ).fetchall()
        grounded = conn.execute(
            "SELECT COUNT(*) AS c FROM harness_experiences "
            "WHERE agent_name=? AND layer='global_pattern'",
            (agent_name,),
        ).fetchone()["c"]
        return {
            "total": total,
            "per_layer": {r["layer"]: r["c"] for r in per_layer},
            "global_patterns": grounded,
            "failure_classes": {r["failure_class"]: r["c"] for r in failures},
            "rejection_log": [dict(r) for r in rejection_log],
        }

    def clear(self, agent_name: str) -> int:
        """Prune all experiences for an agent. Returns row count deleted."""
        conn = self.db._get_conn()
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM harness_experiences WHERE agent_name=?",
            (agent_name,),
        ).fetchone()["c"]
        self.db._write(
            "DELETE FROM harness_experiences WHERE agent_name=?", (agent_name,),
        )
        return int(n)
