"""Correlation pass — fold related items into parent items.

Rule (obs-spec-092 §3.3):
  Same class + first_seen within ±10m window + ≥3 distinct agents
    → parent: class=circuit_event, folded_count=N

Children remain in DB as state='folded', restorable via Split.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict

from observeco.db import Database
from observeco.inbox.store import InboxStore, _make_id, fmt_why_source

logger = logging.getLogger(__name__)

CORRELATION_WINDOW_S = 600  # ±10 minutes


class CorrelationResult:
    """Result of a correlation pass."""

    def __init__(self):
        self.parents_created: int = 0
        self.children_folded: int = 0
        self.parent_items: list[dict] = []


def correlate(store: InboxStore | None = None,
              db: Database | None = None) -> CorrelationResult:
    """Fold correlated open items into parent items.

    Returns: CorrelationResult with counts and parent item dicts.
    """
    if store is None:
        db = db or Database()
        store = InboxStore(db)
    else:
        db = db or store.db

    result = CorrelationResult()
    conn = db._get_conn()

    # Get all open items (not already folded)
    open_items = store.list_items(state="open", limit=500)

    # Group by class
    by_class: dict[str, list[dict]] = defaultdict(list)
    for item in open_items:
        by_class[item["class"]].append(item)

    for cls, items in by_class.items():
        if len(items) < 3:
            continue  # need at least 3 for correlation

        # Find groups within the ±10m window
        # Sort by first_seen (ISO string)
        items.sort(key=lambda i: i["first_seen"] or "")

        groups = _find_windows(items)

        for group in groups:
            if len(group) < 3:
                continue

            agent_names = [i["agent_name"] for i in group if i["agent_name"]]
            unique_agents = list(dict.fromkeys(agent_names))  # preserve order, dedupe
            if len(unique_agents) < 3:
                continue

            n = len(unique_agents)
            # Create parent item
            parent_id = _make_id(cls, None, f"correlated::{cls}::{group[0]['first_seen']}")

            parent = {
                "id": parent_id,
                "agent_name": None,
                "class": cls,
                "tone": "alert" if any(i.get("tone") == "alert" for i in group) else "watch",
                "pillar": group[0].get("pillar"),
                "title": f"{n} agents {cls} in the same window — likely one upstream cause, not {n} incidents.",
                "attribution": f"The raw detector emits {n} rows; the inbox folds correlated events into one.",
                "evidence": json.dumps({
                    "metrics": {"agent_count": n, "agents": unique_agents,
                                "window_s": CORRELATION_WINDOW_S},
                    "source_table": "inbox_correlation",
                    "detector": "inbox/correlate.py",
                }),
                "actions": json.dumps([
                    {"label": f"Split into {n} items", "kind": "primary", "href": f"/api/inbox/{parent_id}/split"},
                    {"label": "Ack as one", "kind": "neutral", "href": "#", "ack_parent": True},
                ]),
                "why_source": fmt_why_source(
                    " & ".join(i.get("agent_name") or "fleet" for i in group[:3]),
                    "inbox/correlate.py",
                ),
                "state": "open",
                "first_seen": group[0]["first_seen"],
                "last_seen": group[-1]["last_seen"],
                "occurrence": 1,
                "folded_count": n,
            }

            # Upsert parent
            existing = conn.execute(
                "SELECT id FROM inbox_items WHERE id = ?", (parent_id,)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO inbox_items "
                    "(id, agent_name, class, tone, pillar, title, attribution, "
                    "evidence, actions, why_source, state, first_seen, last_seen, "
                    "occurrence, folded_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, 1, ?)",
                    (parent_id, None, cls,
                     parent["tone"], parent.get("pillar"),
                     parent["title"], parent.get("attribution"),
                     parent["evidence"], parent["actions"],
                     parent["why_source"],
                     parent["first_seen"], parent["last_seen"],
                     n),
                )
                result.parents_created += 1

            # Fold children
            for child in group:
                cur = conn.execute(
                    "UPDATE inbox_items SET state = 'folded', folded_parent = ? "
                    "WHERE id = ? AND state = 'open'",
                    (parent_id, child["id"]),
                )
                result.children_folded += cur.rowcount

    conn.commit()

    if result.parents_created > 0 or result.children_folded > 0:
        logger.info(
            "Correlation: %d parents created, %d children folded",
            result.parents_created, result.children_folded,
        )

    return result


def split(parent_id: str, db: Database | None = None) -> int:
    """Restore folded children of a parent back to 'open'. Returns count."""
    store = InboxStore(db or Database())
    return store.split_children(parent_id)


def _find_windows(items: list[dict]) -> list[list[dict]]:
    """Group items that fall within ±10m of each other by first_seen.

    Uses a simple sliding window: for each item, group all items
    whose first_seen is within CORRELATION_WINDOW_S seconds.
    """
    # Parse ISO timestamps to unix time
    import time as _time

    def _parse_iso(iso: str | None) -> float:
        if not iso:
            return 0
        try:
            return _time.mktime(_time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S"))
        except (ValueError, OSError):
            return 0

    items_with_ts = [(i, _parse_iso(i["first_seen"])) for i in items if i["first_seen"]]
    items_with_ts.sort(key=lambda x: x[1])

    groups: list[list[dict]] = []
    used: set[str] = set()

    for i, (item, ts) in enumerate(items_with_ts):
        if item["id"] in used:
            continue
        group = [item]
        used.add(item["id"])
        for j in range(i + 1, len(items_with_ts)):
            other, other_ts = items_with_ts[j]
            if other["id"] in used:
                continue
            if abs(other_ts - ts) <= CORRELATION_WINDOW_S:
                group.append(other)
                used.add(other["id"])
        if len(group) >= 2:
            groups.append(group)

    return groups
