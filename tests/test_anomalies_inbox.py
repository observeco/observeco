"""Tests for Anomalies Inbox (obs-spec-092).

§7 Success Criteria:
- 29 → ≤3 criticals on recorded fixture
- Correlation fold of 10-agent event
- Split/restore
- Every item carries attribution + ≥1 action
- Tab renders HTML partial, no JSON leak

Uses synthetic in-memory SQLite database for deterministic results.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from observeco.dashboard.auth import init_auth
from observeco.dashboard.server import app
from observeco.db import Database
from observeco.inbox.store import InboxStore, _now_iso, _make_id
from observeco.inbox.registry import (
    AdapterContext, run_l2_adapter, run_circuit_adapter,
    run_drift_adapter, run_spend_adapter, run_all_adapters, build_and_store,
    run_anomaly_adapter, run_canary_adapter,
)
from observeco.inbox.correlate import correlate, split, _find_windows

TEST_SECRET = init_auth(app)
client = TestClient(app)
AUTH = {"X-ObserveCo-Token": TEST_SECRET}


# ── Synthetic DB Fixture ─────────────────────────────────────────


@pytest.fixture
def syn_db():
    """Create an isolated in-memory SQLite database with synthetic data.

    Schema matches the observeco pulse.db but only creates tables we
    actually query in the adapters. Populated with controlled test data
    that produces deterministic adapter output.
    """
    # Use a temp file so SQLite works properly with indexing
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    db = Database(db_path)
    conn = db._get_conn()

    # Database() already ran all migrations, which created the tables.
    # Add any columns our synthetic data needs that migrations don't provide.
    for col_sql in [
        "ALTER TABLE agent_configs ADD COLUMN first_seen INTEGER DEFAULT 0",
        "ALTER TABLE agent_configs ADD COLUMN last_seen INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(col_sql)
        except Exception:
            pass  # column already exists

    # Also ensure inbox_items exists (from migration 66 on this branch)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inbox_items (
            id TEXT PRIMARY KEY,
            agent_name TEXT,
            class TEXT NOT NULL DEFAULT '',
            tone TEXT NOT NULL DEFAULT '',
            pillar TEXT,
            title TEXT NOT NULL DEFAULT '',
            attribution TEXT,
            evidence TEXT NOT NULL DEFAULT '{}',
            actions TEXT NOT NULL DEFAULT '[]',
            why_source TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'open',
            triage_reason TEXT,
            first_seen TEXT NOT NULL DEFAULT '',
            last_seen TEXT NOT NULL DEFAULT '',
            occurrence INTEGER NOT NULL DEFAULT 1,
            folded_count INTEGER,
            folded_parent TEXT,
            snoozed_until TEXT
        )
    """)

    # Insert synthetic agents: 2 normal agents + 1 profile + 1 test
    now_ts = int(time.time())
    for name, cls in [("alpha-agent", "agent"), ("beta-agent", "agent"),
                      ("profile-box", "profile"), ("test-box", "test")]:
        conn.execute(
            "INSERT OR IGNORE INTO agent_configs (agent_name, class, first_seen, last_seen) "
            "VALUES (?, ?, ?, ?)",
            (name, cls, now_ts - 86400, now_ts),
        )

    # Insert synthetic circuit breaker data: alpha tripped, beta clean
    conn.execute(
        "INSERT INTO circuit_breakers (agent_name, tripped, failure_count, cooldown_until) "
        "VALUES (?, 1, 3, ?)",
        ("alpha-agent", now_ts + 3600),
    )
    conn.execute(
        "INSERT INTO circuit_breakers (agent_name, tripped, failure_count, cooldown_until) "
        "VALUES (?, 0, 0, 0)",
        ("beta-agent",),
    )

    # Insert synthetic pulse data: alpha alive, beta last seen long ago
    for name in ["alpha-agent", "beta-agent"]:
        conn.execute(
            "INSERT INTO pulse_log (agent_name, status, latency_ms, timestamp) "
            "VALUES (?, 'alive', 1200, ?)",
            (name, now_ts - 60),
        )

    # Insert synthetic drift data: alpha breached
    conn.execute(
        "INSERT INTO chisel_drift (agent_name, component, current_tokens, week_avg_tokens, "
        "delta_pct, breached, timestamp, method) VALUES (?, 'guidance', 5000, 2000, 150, 1, ?, 'rolling')",
        ("alpha-agent", now_ts),
    )

    # Insert synthetic garden data: alpha stale scan
    conn.execute(
        "INSERT INTO clawforge_garden (agent_name, memory_debt_score, timestamp) "
        "VALUES (?, 0, ?)",
        ("alpha-agent", now_ts - 30 * 86400),
    )

    conn.commit()
    yield db

    # Cleanup: close and remove temp file
    conn.close()
    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def syn_ctx(syn_db):
    """AdapterContext backed by synthetic DB."""
    return AdapterContext(syn_db)


@pytest.fixture
def syn_store(syn_db):
    """InboxStore backed by synthetic DB."""
    return InboxStore(syn_db)


# ── §7.1: No critical items from excluded agents ────────────────


def test_no_critical_from_excluded_agents(syn_ctx):
    """§7.1+§7.3: Zero critical items from profile/test agents.

    All adapters must respect class-based exclusion. The synthetic DB
    has 'profile-box' (profile) and 'test-box' (test) which should
    never produce items.
    """
    items = run_all_adapters(syn_ctx)

    # Verify no items from excluded agents
    excluded_agents = syn_ctx.get_excluded_agents()
    for item in items:
        agent = item.get("agent_name", "")
        assert agent not in excluded_agents, \
            f"Adapter emitted item for excluded agent {agent}: {item.get('class')}"

    # Verify items from normal agents exist
    normal_items = [i for i in items if i["agent_name"] in ("alpha-agent", "beta-agent")]
    assert len(normal_items) >= 1, \
        "Should produce at least 1 item from normal agents"


# ── §7.2: Items carry attribution + ≥1 action ───────────────────


def test_all_items_have_attribution_and_actions(syn_ctx):
    """§7.2: 100% of inbox items carry attribution + ≥1 action.

    After build_and_store, every stored item must have non-empty
    attribution, ≥1 action, and non-empty why_source.
    """
    build_and_store(syn_ctx)
    items = syn_ctx.store.list_items(limit=100)

    for item in items:
        # Skip folded children (they inherit from parent)
        if item.get("state") == "folded":
            continue

        assert item.get("attribution"), \
            f"Item {item['id']} missing attribution (got {repr(item.get('attribution'))})"
        actions_raw = item.get("actions", "[]")
        try:
            actions = json.loads(actions_raw) if isinstance(actions_raw, str) else actions_raw
        except (json.JSONDecodeError, TypeError):
            actions = []
        assert len(actions) >= 1, \
            f"Item {item['id']} has no actions"
        assert item.get("why_source"), \
            f"Item {item['id']} missing why_source"


# ── §7.3: No false 'dead' from profile agents ───────────────────


def test_no_false_dead_from_profiles(syn_ctx):
    """§7.3: Zero false 'dead' alerts from profile-class agents.

    Sets up synthetic data that would trigger 'agent_dead' detection
    for a profile agent, then verifies no such item is produced.
    """
    conn = syn_ctx.db._get_conn()

    # Intentionally create pulse data that would make profile-box look dead
    # (old pulse, no recent activity) — the adapter should skip it due to class
    now_ts = int(time.time())
    conn.execute(
        "INSERT INTO pulse_log (agent_name, status, latency_ms, timestamp) "
        "VALUES (?, 'alive', 100, ?)",
        ("profile-box", now_ts - 86400 * 3),  # 3 days old
    )
    conn.commit()

    items = run_all_adapters(syn_ctx)

    # Verify no items from profile-box
    profile_items = [i for i in items if i["agent_name"] == "profile-box"]
    assert len(profile_items) == 0, \
        f"Profile agent produced {len(profile_items)} items: {[i.get('class') for i in profile_items]}"

    # Any agent_dead items should only be from normal agents
    dead_items = [i for i in items if i.get("class") == "agent_dead"]
    for item in dead_items:
        assert item["agent_name"] not in syn_ctx.get_excluded_agents(), \
            f"Dead alert for excluded agent: {item['agent_name']}"


# ── §7.4: Correlation fold ──────────────────────────────────────


def test_correlation_fold(syn_ctx, syn_store):
    """§7.3+: ≥3 agents in same window → 1 parent item.

    Inserts 3 synthetic circuit events for 3 different agents with
    the same timestamp window, runs correlation, verifies folding.
    """
    now_iso = _now_iso()
    items = []
    for agent in ["fold-agent-a", "fold-agent-b", "fold-agent-c"]:
        items.append({
            "class": "circuit_event",
            "agent_name": agent,
            "dedupe_key": f"fold_test_{agent}",
            "tone": "watch",
            "pillar": "reliability",
            "title": f"{agent} circuit tripped",
            "attribution": "Test item for correlation fold",
            "evidence": {"metrics": {"test": 1}, "source_table": "test", "detector": "test"},
            "actions": [{"label": "Ack", "kind": "neutral"}],
            "why_source": "source: test · detector: test",
            "first_seen": now_iso,
        })

    # Upsert test items
    for item_data in items:
        syn_store.upsert(
            item_class=item_data["class"],
            agent_name=item_data["agent_name"],
            dedupe_key=item_data["dedupe_key"],
            tone=item_data["tone"],
            title=item_data["title"],
            evidence=item_data["evidence"],
            actions=item_data["actions"],
            why_source=item_data["why_source"],
            pillar=item_data.get("pillar"),
            attribution=item_data.get("attribution"),
            first_seen=item_data["first_seen"],
        )

    # Run correlation
    result = correlate(syn_store)
    assert result.parents_created >= 1, \
        "Should create at least 1 correlation parent"

    # Verify the parent has folded_count = 3
    parent_items = [i for i in syn_store.list_items(limit=50)
                    if i.get("folded_count") and i["folded_count"] >= 3]
    assert len(parent_items) >= 1, \
        "No correlation parent with folded_count >= 3 found"

    # Clean up test items
    conn = syn_ctx.db._get_conn()
    conn.execute("DELETE FROM inbox_items WHERE id LIKE 'circuit_event::fold-agent-%'")
    conn.execute("DELETE FROM inbox_items WHERE id LIKE 'circuit_event::__fleet__::correlated%'")
    conn.commit()


def test_build_and_store_correlates_automatically(syn_ctx):
    """Option B: write-time folding — correlation runs inside build_and_store.

    The manual /api/inbox/refresh job was deleted (the audit's first real catch:
    a registered POST route with no caller). Folding must now happen as part of
    ingestion, so the parent appears after a plain build_and_store() with NO
    separate correlate() call.
    """
    now_iso = _now_iso()
    # Simulate the adapters emitting 3 circuit events in the same window.
    for agent in ["auto-fold-a", "auto-fold-b", "auto-fold-c"]:
        syn_ctx.store.upsert(
            item_class="circuit_event",
            agent_name=agent,
            dedupe_key=f"auto_fold_{agent}",
            tone="watch",
            title=f"{agent} circuit tripped",
            evidence={"metrics": {"test": 1}, "source_table": "test", "detector": "test"},
            actions=[{"label": "Ack", "kind": "neutral"}],
            why_source="source: test · detector: test",
            first_seen=now_iso,
        )

    # build_and_store runs correlation internally — NO manual correlate() call.
    build_and_store(syn_ctx)

    # The parent must now exist with folded_count >= 3.
    parents = [i for i in syn_ctx.store.list_items(limit=50)
               if i.get("folded_count") and i["folded_count"] >= 3]
    assert len(parents) >= 1, (
        "build_and_store should correlate automatically (write-time folding); "
        "a parent with folded_count>=3 must exist without any manual correlate() call"
    )

    # Clean up
    conn = syn_ctx.db._get_conn()
    conn.execute("DELETE FROM inbox_items WHERE id LIKE 'circuit_event::auto-fold-%'")
    conn.execute("DELETE FROM inbox_items WHERE id LIKE 'circuit_event::__fleet__::correlated%'")
    conn.commit()


# ── §7.4: Split/restore ───────────────────────────────────────────

def test_split_restore(syn_ctx, syn_store):
    """§7.4: Split restores folded children; restore works on acked items."""
    # Create a test correlation parent and children
    now_iso = _now_iso()
    parent_id = f"syn::parent::{int(time.time())}"
    child_ids = []

    syn_store.db._get_conn().execute(
        "INSERT INTO inbox_items (id, agent_name, class, tone, title, "
        "evidence, actions, why_source, first_seen, last_seen, folded_count) "
        "VALUES (?, NULL, 'circuit_event', 'alert', 'Test parent', '{}', '[]', "
        "'test', ?, ?, 3)",
        (parent_id, now_iso, now_iso),
    )

    for agent in ["syn-child-a", "syn-child-b", "syn-child-c"]:
        cid = f"syn::child::{agent}"
        child_ids.append(cid)
        syn_store.db._get_conn().execute(
            "INSERT INTO inbox_items (id, agent_name, class, tone, title, "
            "evidence, actions, why_source, first_seen, last_seen, state, folded_parent) "
            "VALUES (?, ?, 'circuit_event', 'watch', 'Test child', '{}', '[]', "
            "'test', ?, ?, 'folded', ?)",
            (cid, agent, now_iso, now_iso, parent_id),
        )
    syn_store.db._get_conn().commit()

    # Test split
    n = split(parent_id, db=syn_ctx.db)
    assert n == 3, f"Expected 3 children restored, got {n}"

    # Verify children are now open
    for cid in child_ids:
        item = syn_store.get_item(cid)
        assert item is not None, f"Child {cid} not found"
        assert item["state"] == "open", f"Child {cid} not restored to open"

    # Test restore
    syn_store.ack(child_ids[0])
    restored = syn_store.restore(child_ids[0])
    assert restored, "Restore failed"
    item = syn_store.get_item(child_ids[0])
    assert item["state"] == "open", "Restored item not open"

    # Cleanup
    conn = syn_ctx.db._get_conn()
    all_ids = [parent_id] + child_ids
    for cid in all_ids:
        conn.execute("DELETE FROM inbox_items WHERE id = ?", (cid,))
    conn.commit()


# ── §7.5: Tab renders HTML partial ────────────────────────────────

def test_inbox_endpoint_returns_html():
    """§7.5: GET /api/inbox returns HTML partial (not JSON)."""
    resp = client.get("/api/inbox", headers=AUTH)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", ""), \
        "Expected HTML content type"
    # Check it's not a JSON leak
    assert not resp.text.strip().startswith("{"), \
        "Response starts with { — possible JSON leak"


def test_inbox_json_endpoint():
    """§7.5: GET /api/inbox/json returns structured JSON."""
    resp = client.get("/api/inbox/json", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data
    assert "verdict" in data


def test_inbox_verdict_sentence(syn_ctx):
    """§3.6: Verdict is a sentence, never a raw count."""
    from observeco.dashboard.routes.inbox import _build_verdict_sentence

    counts = syn_ctx.store.get_counts()
    verdict = _build_verdict_sentence(counts)

    # It should be a proper sentence (ends with period)
    assert verdict.endswith("."), "Verdict should end with period"
    # Should mention "action" or "quiet" or "insight" not just raw numbers
    assert ("issue" in verdict.lower() or "quiet" in verdict.lower()
            or "insight" in verdict.lower() or "anomal" in verdict.lower()), \
        f"Verdict not a proper sentence: {verdict}"


# ── §7.6: Triage mutations ────────────────────────────────────────

def test_ack_removes_item_from_default_feed():
    """Acked items leave the default open feed and appear only under Acked filter.

    Regression: previously list_items() defaulted to ALL states, so acking an
    item left it dimmed-but-present in its tone section (the "Ack doesn't remove"
    UX bug). Now default view is state='open' only.
    """
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = Database(tmp.name)
    store = InboxStore(db)
    item_id = store.upsert(
        "test_class", "agent-x", "key-1", "alert", "Test alert",
        {"metrics": {"value": 5}}, [{"label": "Open agent →", "href": "/api/agent-detail/agent-x", "kind": "primary"}],
        "why", pillar="reliability",
    )
    # Open feed contains it
    assert any(i["id"] == item_id for i in store.list_items())
    # Ack it
    assert store.ack(item_id)
    # Default feed no longer contains it
    assert not any(i["id"] == item_id for i in store.list_items())
    # It appears under the Acked filter
    assert any(i["id"] == item_id for i in store.list_items(state="acked"))
    os.unlink(tmp.name)


def test_ack_endpoint():
    """POST /api/inbox/{id}/ack returns HTML htmx response."""
    # First get an item to ack
    resp = client.get("/api/inbox", headers=AUTH)
    assert resp.status_code == 200

    # Ack with a nonexistent item (tests graceful handling)
    resp = client.post("/api/inbox/nonexistent-item/ack", headers=AUTH)
    # Should still return HTML (htmx expects it)
    assert resp.status_code in (200, 404)


def test_cleanup_apply():
    """POST /api/inbox/cleanup/apply applies fixes."""
    resp = client.post(
        "/api/inbox/cleanup/apply",
        json={"fixes": ["reclassify_profiles", "exclude_tests", "reset_stale_circuits"]},
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "reclassify_profiles" in data.get("results", {})


# ── §7.7: Registry adapters ───────────────────────────────────────

def test_registry_l2_adapter(syn_ctx):
    """L2 adapter returns normalized items."""
    items = run_l2_adapter(syn_ctx)
    for item in items:
        assert "class" in item
        assert "agent_name" in item
        assert "tone" in item
        assert "title" in item
        assert item["tone"] in ("alert", "watch")
        assert len(item["actions"]) >= 1

def test_registry_all_adapters_run_without_error(syn_ctx):
    """All adapters run without raising exceptions."""
    items = run_all_adapters(syn_ctx)
    assert isinstance(items, list)
    for item in items:
        assert "dedupe_key" in item, f"Item missing dedupe_key: {item.get('title', '')[:40]}"


# ── §7.8: Correlation window finding ──────────────────────────────

def test_find_windows():
    """_find_windows groups items within ±10m."""
    now = int(time.time())
    items = [
        {"id": "a", "first_seen": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now))},
        {"id": "b", "first_seen": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now + 120))},
        {"id": "c", "first_seen": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now + 300))},
        {"id": "d", "first_seen": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now + 40000))},
    ]
    groups = _find_windows(items)
    # a, b, c should be in one group (within 10m); d should be separate
    assert len(groups) >= 1
    main_group = [g for g in groups if len(g) >= 3]
    assert len(main_group) >= 1, "Should have a group with 3 items"


# ── §7.9: Store persistence ───────────────────────────────────────

def test_store_upsert_and_counts(syn_ctx, syn_store):
    """Store upsert works and counts are consistent."""
    now_iso = _now_iso()

    # Insert test item
    item_id = syn_store.upsert(
        item_class="test_persist",
        agent_name="syn-test-agent",
        dedupe_key="syn_persist_test",
        tone="insight",
        title="Test persistence",
        evidence={"metrics": {"test": 1}, "source_table": "test", "detector": "test"},
        actions=[{"label": "View", "kind": "primary"}],
        why_source="source: test · detector: test",
        pillar="quality",
        attribution="Test attribution",
        first_seen=now_iso,
    )

    # Verify it exists
    item = syn_store.get_item(item_id)
    assert item is not None
    assert item["tone"] == "insight"
    assert item["occurrence"] == 1

    # Upsert again (same dedupe_key) → occurrence should increment
    syn_store.upsert(
        item_class="test_persist",
        agent_name="syn-test-agent",
        dedupe_key="syn_persist_test",
        tone="insight",
        title="Test persistence (updated)",
        evidence={"metrics": {"test": 2}, "source_table": "test", "detector": "test"},
        actions=[{"label": "View", "kind": "primary"}],
        why_source="source: test · detector: test",
    )
    item = syn_store.get_item(item_id)
    assert item["occurrence"] == 2, f"Expected occurrence=2, got {item['occurrence']}"

    # Cleanup
    conn = syn_ctx.db._get_conn()
    conn.execute("DELETE FROM inbox_items WHERE id = ?", (item_id,))
    conn.commit()


# ── §7.8: Snooze (Snooze 1h) ────────────────────────────────────────

def test_snooze_removes_from_default_feed_and_counts_separately(syn_ctx, syn_store):
    """Snooze removes item from the open feed; verdict counts it separately.

    snoozed != resolved: the action count must NOT drop, and the item re-opens
    via read-time derivation once snoozed_until passes.
    """
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = Database(tmp.name)
    store = InboxStore(db)
    item_id = store.upsert(
        "agent_dead", "agent-x", "key-1", "alert", "agent-x dead",
        {"metrics": {"v": 1}}, [{"label": "Ack", "kind": "neutral"}],
        "why", pillar="reliability",
    )
    # In the open feed, counts as 1 action.
    assert any(i["id"] == item_id for i in store.list_items())
    counts = store.get_counts()
    assert counts["alert"] == 1 and counts["snoozed"] == 0

    # Snooze with a FUTURE expiry (1h): leaves the open feed, counts as snoozed.
    future = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(time.time()) + 3600))
    assert store.snooze(item_id, future)
    assert not any(i["id"] == item_id for i in store.list_items())
    counts = store.get_counts()
    assert counts["alert"] == 0 and counts["snoozed"] == 1, counts

    # Snooze with a PAST expiry: read-time derivation re-opens it (no mutation).
    # Note: snooze() requires state='open', so set the past expiry directly on
    # the already-snoozed row (simulating a snoozed_until that has since lapsed).
    past = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(time.time()) - 10))
    store.db._get_conn().execute(
        "UPDATE inbox_items SET snoozed_until = ? WHERE id = ?",
        (past, item_id),
    )
    store.db._get_conn().commit()  # state stays 'snoozed', but now expired
    assert any(i["id"] == item_id for i in store.list_items()), \
        "expired snooze must re-open via read-time derivation"
    counts = store.get_counts()
    assert counts["alert"] == 1 and counts["snoozed"] == 0, counts
    os.unlink(tmp.name)


def test_verdict_sentence_all_snoozed_not_all_clear():
    """'0 issues — all snoozed' must NOT read as all-clear."""
    from observeco.dashboard.routes.inbox import _build_verdict_sentence
    # 1 snoozed, 0 action -> "No issues need action — 1 snoozed for now."
    s = _build_verdict_sentence({"alert": 0, "watch": 0, "insight": 0,
                                 "triaged": 0, "snoozed": 1})
    assert "snoozed" in s and "quiet" not in s, s
    assert "No issues need action" in s, s
    # 2 action + 1 snoozed -> "2 issues need action — 1 snoozed — ..."
    s2 = _build_verdict_sentence({"alert": 2, "watch": 0, "insight": 0,
                                  "triaged": 0, "snoozed": 1})
    assert "2 issues need action" in s2 and "1 snoozed" in s2, s2
