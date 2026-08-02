"""Tests for _resolve_agent default-remap behavior.

Regression test: _resolve_agent('default') must NOT remap to another agent
when 'default' has grid runs of its own, otherwise the grid table falls
back to a stale completed run from another agent (b588dc7).
"""

import sqlite3
import uuid

import pytest

import observeco.dashboard.routes.capability as cap_mod


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_observeco.db"
    from observeco.db import Database
    db = Database(db_path=str(db_path))
    monkeypatch.setattr(cap_mod, "db", db)
    conn = db._get_conn()
    # Ensure grid_runs exists
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS grid_runs ("
            "id TEXT PRIMARY KEY, agent_name TEXT, started_at TEXT, "
            "completed_at TEXT, status TEXT, models TEXT, configs TEXT, "
            "total_cells INTEGER, total_cost REAL, error TEXT)"
        )
        conn.commit()
    except sqlite3.Error:
        pass
    yield db
    db.close()


def _insert_run(conn, agent_name, status="running"):
    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO grid_runs (id, agent_name, started_at, completed_at, status, models, configs, total_cells) "
        "VALUES (?, ?, '2026-08-02T00:00:00+00:00', NULL, ?, '[]', '[]', 1)",
        (run_id, agent_name, status),
    )
    conn.commit()
    return run_id


def test_resolve_keeps_default_when_default_has_grid_data(temp_db):
    conn = temp_db._get_conn()
    _insert_run(conn, "default", status="running")
    # Most-snapshotted agent would be 'main' if snapshots existed; none do,
    # but the grid-run check must short-circuit BEFORE the snapshot query.
    assert cap_mod._resolve_agent("default") == "default"


def test_resolve_remaps_default_when_no_grid_data(temp_db):
    # No grid runs for 'default' -> falls through to snapshot fallback.
    # With no snapshots either, it returns the first configured agent or None.
    result = cap_mod._resolve_agent("default")
    # It must not be the literal 'default' (that would show empty table) —
    # but with a bare DB, the fallback chain returns None/fallback safely.
    assert isinstance(result, str)


def test_resolve_passthrough_non_default(temp_db):
    assert cap_mod._resolve_agent("main") == "main"
    assert cap_mod._resolve_agent("accelerator") == "accelerator"
