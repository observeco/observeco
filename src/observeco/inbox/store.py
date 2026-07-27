"""Inbox persistence — inbox_items CRUD via the shared Database instance.

Schema per obs-spec-092 §3.1:
  inbox_items stores normalized items from 9 detector adapters.
  The inbox is the read-side: source detectors keep their own tables.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """ISO-8601 timestamp for inbox_items."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _ts_from_iso(iso: str | None) -> int:
    """Convert ISO string to unix timestamp (for ordering)."""
    if not iso:
        return 0
    try:
        return int(time.mktime(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")))
    except (ValueError, OSError):
        return 0


def _make_id(item_class: str, agent_name: str | None, dedupe_key: str) -> str:
    """Deterministic id hash: class::agent::dedupe_key."""
    agent = agent_name or "__fleet__"
    return f"{item_class}::{agent}::{dedupe_key}"


class InboxStore:
    """Persistence layer for the anomalies inbox."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    # ── Query ───────────────────────────────────────────────────────────

    def list_items(self, state: str | None = None,
                   tone: str | None = None,
                   limit: int = 100) -> list[dict]:
        """List inbox items with optional filters.

        Returns items sorted by last_seen DESC (most recent first).
        """
        conn = self.db._get_conn()
        where = []
        params: list = []

        if state:
            where.append("state = ?")
            params.append(state)
        if tone:
            where.append("tone = ?")
            params.append(tone)

        # Exclude folded children by default (they're under the parent)
        where.append("(folded_count IS NULL OR state != 'folded')")

        sql = "SELECT * FROM inbox_items"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_item(self, item_id: str) -> dict | None:
        """Get a single item by id."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT * FROM inbox_items WHERE id = ?", (item_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_folded_children(self, parent_id: str) -> list[dict]:
        """Get children that were folded under a correlation parent."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT * FROM inbox_items WHERE folded_parent = ? ORDER BY last_seen DESC",
            (parent_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Write ───────────────────────────────────────────────────────────

    def upsert(self, item_class: str, agent_name: str | None,
               dedupe_key: str,
               tone: str,
               title: str,
               evidence: dict,
               actions: list[dict],
               why_source: str,
               pillar: str | None = None,
               attribution: str | None = None,
               first_seen: str | None = None,
               now_iso: str | None = None) -> str:
        """Upsert an inbox item. Returns the item id.

        If an item with the same (class, agent, dedupe_key) already exists,
        increments occurrence and updates last_seen/evidence/actions.
        """
        now = now_iso or _now_iso()
        item_id = _make_id(item_class, agent_name, dedupe_key)
        conn = self.db._get_conn()

        existing = conn.execute(
            "SELECT id, occurrence, first_seen FROM inbox_items WHERE id = ?",
            (item_id,),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE inbox_items SET occurrence = occurrence + 1, "
                "last_seen = ?, evidence = ?, actions = ?, attribution = ? "
                "WHERE id = ?",
                (now, json.dumps(evidence), json.dumps(actions),
                 attribution or "", item_id),
            )
        else:
            conn.execute(
                "INSERT INTO inbox_items "
                "(id, agent_name, class, tone, pillar, title, attribution, "
                "evidence, actions, why_source, first_seen, last_seen, occurrence) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (item_id, agent_name, item_class, tone, pillar, title,
                 attribution or "", json.dumps(evidence),
                 json.dumps(actions), why_source,
                 first_seen or now, now),
            )
        self.db._get_conn().commit()
        return item_id

    # ── Triage mutations ───────────────────────────────────────────────

    def ack(self, item_id: str) -> bool:
        """Acknowledge an item (state='acked')."""
        conn = self.db._get_conn()
        cur = conn.execute(
            "UPDATE inbox_items SET state = 'acked' WHERE id = ? AND state = 'open'",
            (item_id,),
        )
        conn.commit()
        return cur.rowcount > 0

    def snooze(self, item_id: str, until_iso: str) -> bool:
        """Snooze an item until a specific ISO timestamp."""
        conn = self.db._get_conn()
        cur = conn.execute(
            "UPDATE inbox_items SET state = 'snoozed', snoozed_until = ? "
            "WHERE id = ? AND state = 'open'",
            (until_iso, item_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def restore(self, item_id: str) -> bool:
        """Restore a previously acked/snoozed/triaged item back to open."""
        conn = self.db._get_conn()
        cur = conn.execute(
            "UPDATE inbox_items SET state = 'open', triage_reason = NULL "
            "WHERE id = ? AND state != 'open'",
            (item_id,),
        )
        conn.commit()
        return cur.rowcount > 0

    def auto_triage(self, item_id: str, reason: str) -> bool:
        """Automatically triage an item as noise with a reason."""
        conn = self.db._get_conn()
        cur = conn.execute(
            "UPDATE inbox_items SET state = 'triaged', triage_reason = ? "
            "WHERE id = ? AND state = 'open'",
            (reason, item_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def mark_folded(self, item_id: str, folded_parent: str) -> bool:
        """Mark an item as folded (child of a correlation parent)."""
        conn = self.db._get_conn()
        cur = conn.execute(
            "UPDATE inbox_items SET state = 'folded', folded_parent = ? "
            "WHERE id = ?",
            (folded_parent, item_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def split_children(self, parent_id: str) -> int:
        """Restore all folded children back to 'open'. Returns count."""
        conn = self.db._get_conn()
        cur = conn.execute(
            "UPDATE inbox_items SET state = 'open', folded_parent = NULL "
            "WHERE folded_parent = ?",
            (parent_id,),
        )
        conn.commit()
        return cur.rowcount

    # ── Stats ──────────────────────────────────────────────────────────

    def get_counts(self) -> dict:
        """Return counts of open items by tone and total triaged."""
        conn = self.db._get_conn()
        counts = {"alert": 0, "watch": 0, "insight": 0, "triaged": 0}
        for row in conn.execute(
            "SELECT tone, COUNT(*) as c FROM inbox_items "
            "WHERE state = 'open' GROUP BY tone"
        ).fetchall():
            counts[row["tone"]] = row["c"]
        row = conn.execute(
            "SELECT COUNT(*) as c FROM inbox_items WHERE state = 'triaged'"
        ).fetchone()
        counts["triaged"] = row["c"] if row else 0
        return counts

    def cleanup(self, cutoff_iso: str) -> int:
        """Remove items older than cutoff (retention policy)."""
        conn = self.db._get_conn()
        cur = conn.execute(
            "DELETE FROM inbox_items WHERE last_seen < ?",
            (cutoff_iso,),
        )
        conn.commit()
        return cur.rowcount


# ── Convenience helpers for adapter usage ──────────────────────────

def fmt_evidence(metrics: dict, source_table: str, detector: str) -> str:
    """Build the evidence JSON field."""
    return json.dumps({"metrics": metrics, "source_table": source_table, "detector": detector})


def fmt_actions(actions: list[dict]) -> str:
    """JSON-serialize actions list (each: {label, href|cmd, kind})."""
    return json.dumps(actions)


def fmt_why_source(source: str, detector: str) -> str:
    """Build the why_source text field."""
    return f"source: {source} · detector: {detector}"
