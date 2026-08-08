#!/usr/bin/env python3
"""Tests for the profile tracker's pin-agreement validation.

The pin-agreement check is the tracker's FIRST job: for each captured session,
does the captured git_sha's repo match the repo paths the session's own tool
calls touched? A confidently-wrong SHA is worse than a NULL — NULL excludes, a
wrong pin produces a reconstruction that looks valid and isn't.
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
import profile_tracker as pt


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, git_sha TEXT)")
    conn.execute("CREATE TABLE messages (session_id TEXT, role TEXT, content TEXT)")
    return conn


def test_extract_touched_repos_finds_observeco():
    content = '{"path": "/Users/seanfzc/projects/observeco/src/db.py", "total_count": 1}'
    repos = pt.extract_touched_repos(content)
    assert "/Users/seanfzc/projects/observeco" in repos


def test_extract_touched_repos_ignores_unknown_paths():
    content = '{"path": "/tmp/scratch.py"}'
    assert pt.extract_touched_repos(content) == set()


def test_extract_touched_repos_finds_hermes_agent():
    content = '{"path": "/Users/seanfzc/.hermes/hermes-agent/run_agent.py"}'
    repos = pt.extract_touched_repos(content)
    assert "/Users/seanfzc/.hermes/hermes-agent" in repos


def test_session_touched_repos_aggregates():
    conn = _make_db()
    conn.execute("INSERT INTO sessions VALUES ('s1', 'abc1234')")
    conn.execute(
        "INSERT INTO messages VALUES ('s1', 'tool', "
        "'{\"path\": \"/Users/seanfzc/projects/observeco/src/db.py\"}')"
    )
    conn.execute(
        "INSERT INTO messages VALUES ('s1', 'tool', "
        "'{\"path\": \"/Users/seanfzc/projects/observeco-main/scripts/x.py\"}')"
    )
    repos = pt.session_touched_repos(conn, "s1")
    assert "/Users/seanfzc/projects/observeco" in repos
    assert "/Users/seanfzc/projects/observeco-main" in repos


def test_pin_agreement_no_sha():
    conn = _make_db()
    conn.execute("INSERT INTO sessions VALUES ('s1', NULL)")
    assert pt.pin_agreement(conn, "s1", None) == "no_sha"


def test_pin_agreement_no_tool_paths():
    conn = _make_db()
    conn.execute("INSERT INTO sessions VALUES ('s1', 'abc1234')")
    # no tool messages -> no touched repos
    verdict = pt.pin_agreement(conn, "s1", "abc1234")
    assert verdict == "no_tool_paths", verdict
