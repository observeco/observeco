#!/usr/bin/env python3
"""End-to-end test for per-tool-call git provenance capture (forge shape).

Manufactures the real delegation shape that broke the previous three attempts:
a session that launches from HOME (not a git repo) but patches a file inside
`~/.hermes/scripts/` (a real git repo). Verifies the resolver walks up from the
TOUCHED PATH to the enclosing repo and records git_sha.

This is the kill-condition test: if it fails, per-tool-call capture is
declared infeasible in this architecture and the conversion measurement
question closes with it (registered in workbench-per-tool-call-capture.md).

Runs against a real git repo so `git rev-parse --show-toplevel` is real, not
mocked. Uses the ACTUAL resolver functions from run_agent.
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def _load_run_agent():
    spec = importlib.util.spec_from_file_location(
        "run_agent", "/Users/seanfzc/.hermes/hermes-agent/run_agent.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_repo() -> str:
    """Create a throwaway git repo to stand in for ~/.hermes/scripts."""
    repo = tempfile.mkdtemp(prefix="forge-shape-")
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True)
    p = Path(repo) / "worker.py"
    p.write_text("#!/usr/bin/env python3\nprint('hi')\n")
    subprocess.run(["git", "-C", repo, "add", "worker.py"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-q", "-m", "seed"], check=True)
    return repo


class _FakeAgent:
    """Minimal agent with session_id + a session_db that has update_session_cwd.

    The resolver calls session_db.update_session_cwd(...) — a raw sqlite3
    Connection does NOT have that method, which would make the capture silently
    no-op (AttributeError swallowed by the resolver's broad except). Using a
    stub that implements the method is the correct test fixture.
    """

    def __init__(self, conn, session_id):
        self._session_db = _StubSessionDB(conn)
        self.session_id = session_id


class _StubSessionDB:
    """Implements just the session_db methods the resolver uses, over a raw conn."""

    def __init__(self, conn):
        self._conn = conn

    def get_session(self, session_id):
        row = self._conn.execute(
            "SELECT git_sha FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        # sqlite3.Row has no .get() — return a dict so the resolver's
        # `existing.get("git_sha")` works.
        return dict(row) if row else None

    def update_session_cwd(self, session_id, cwd, **kw):
        self._conn.execute(
            "UPDATE sessions SET cwd=?, git_sha=?, spawn_dirty_diff=?, spawn_untracked=? WHERE id=?",
            (cwd, kw.get("git_sha"), kw.get("spawn_dirty_diff"), kw.get("spawn_untracked"), session_id),
        )
        self._conn.commit()


def test_resolver_pins_from_touched_path_not_home():
    """A session launching from home but touching a repo file must pin that repo."""
    ra = _load_run_agent()

    # forge shape: launch cwd = HOME (not a git repo), touched file = in repo
    home = os.path.expanduser("~")
    repo = _make_repo()
    touched = os.path.join(repo, "worker.py")
    try:
        # session_db with a real row
        dbpath = tempfile.mktemp(suffix=".db")
        conn = sqlite3.connect(dbpath)
        conn.execute(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, cwd TEXT, "
            "git_sha TEXT, spawn_dirty_diff TEXT, spawn_untracked TEXT)"
        )
        conn.execute(
            "INSERT INTO sessions VALUES ('forge-s1', 'subagent', ?, NULL, NULL, NULL)",
            (home,),
        )
        conn.commit()
        conn.close()
        conn = sqlite3.connect(dbpath)
        conn.row_factory = sqlite3.Row

        agent = _FakeAgent(conn, "forge-s1")
        # launch cwd is home (not a git repo)
        assert ra._git_state_for_cwd(home)[0] is None, "home should not resolve a SHA"
        # fire the per-tool-call capture on the touched path
        ra._maybe_capture_session_git_state(agent, touched)
        row = conn.execute("SELECT git_sha, cwd FROM sessions WHERE id='forge-s1'").fetchone()
        assert row and row["git_sha"], f"expected SHA, got {dict(row) if row else None}"
        # git's --show-toplevel returns the realpath (/private/var/...) which
        # may differ from the symlinked path the test used (/var/...). Compare realpaths.
        assert os.path.realpath(row["cwd"]) == os.path.realpath(repo), (
            f"expected cwd realpath={os.path.realpath(repo)}, got {row['cwd']}"
        )
        print(f"PASS: pinned repo={row['cwd']} sha={row['git_sha'][:10]}")
    finally:
        # clean up
        for p in [dbpath]:
            try: os.remove(p)
            except OSError: pass
        subprocess.run(["git", "-C", repo, "checkout", "-q", "main"], capture_output=True, text=True) if False else None
        import shutil
        shutil.rmtree(repo, ignore_errors=True)


def test_no_repo_from_touched_path_is_noop():
    """A touched path outside any git repo must not capture (no false SHA)."""
    ra = _load_run_agent()
    dbpath = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(dbpath)
    conn.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, cwd TEXT, "
        "git_sha TEXT, spawn_dirty_diff TEXT, spawn_untracked TEXT)"
    )
    conn.execute("INSERT INTO sessions VALUES ('s2', 'subagent', '/tmp', NULL, NULL, NULL)")
    conn.commit(); conn.close()
    conn = sqlite3.connect(dbpath); conn.row_factory = sqlite3.Row
    try:
        agent = _FakeAgent(conn, "s2")
        ra._maybe_capture_session_git_state(agent, "/tmp/scratch.py")  # not in a repo
        row = conn.execute("SELECT git_sha FROM sessions WHERE id='s2'").fetchone()
        assert row["git_sha"] is None, f"expected no SHA for non-repo path, got {row['git_sha']}"
        print("PASS: non-repo touched path records no SHA (no false pin)")
    finally:
        conn.close()
        try: os.remove(dbpath)
        except OSError: pass
