"""Self-check for the turn-capture layer (no framework, stdlib only).

Run:  python3 tests/test_turn_capture.py
Exits non-zero if the capture logic is broken. This is the ONE runnable
check mandated for non-trivial logic — it round-trips a real payload through
the real Database class and asserts the rows land correctly.

It writes to a throwaway temp DB (via OBSERVECO_TEST_DB env override if the
Database class honours it) — or to the real pulse.db under a sentinel agent
name that is deleted on cleanup, so it never pollutes production stats.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

# Make observeco importable from this file's location.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

SENTINEL = "__turn_capture_selftest__"


def _payload(event, **kw):
    p = {"hook_event_name": event, "session_id": SENTINEL}
    p.update(kw)
    return p


def main() -> int:
    # Drive the real CLI entry point the way Hermes' hook would.
    sample = [
        _payload("on_session_end", completed=True, model="test"),
        _payload("post_tool_call", tool_name="skill_view",
                 tool_input={"name": "launch-content-writing"}),
        _payload("post_tool_call", tool_name="skill_view",
                 tool_input={"name": "launch-content-writing"}),  # 2nd hit -> turn_count=2
        _payload("post_tool_call", tool_name="terminal",
                 tool_input={"command": "echo hi"}),  # ignored, not a skill tool
        _payload("post_tool_call", tool_name="skill_manage",
                 tool_input={"action": "create", "name": "deep-research-playbook"}),
    ]

    for p in sample:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(ROOT, "src") + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "observeco.cli", "capture-turn"],
            input=json.dumps(p), capture_output=True, text=True,
            cwd=ROOT, timeout=30, env=env,
        )
        # Hook handler MUST exit 0 even on garbage — blast-radius contract.
        if proc.returncode != 0:
            print(f"FAIL: capture-turn exited {proc.returncode} on {p['hook_event_name']}")
            print(proc.stderr)
            return 1

    # Writes are synchronous in the handler (one row per subprocess), so the
    # DB is already updated by the time each subprocess exits. No flush needed.
    from observeco.db import Database
    db = Database()
    conn = None
    try:
        conn = db._get_conn()
        turns = conn.execute(
            "SELECT COUNT(*) FROM turn_log WHERE agent_name=?", (SENTINEL,)
        ).fetchone()[0]
        if turns != 1:
            print(f"FAIL: expected 1 turn_log row, got {turns}")
            return 1

        row = conn.execute(
            "SELECT triggered, turn_count FROM skill_usage "
            "WHERE agent_name=? AND skill_name=?", (SENTINEL, "launch-content-writing")
        ).fetchone()
        if not row:
            print("FAIL: launch-content-writing not recorded in skill_usage")
            return 1
        if row["triggered"] != 1 or row["turn_count"] != 2:
            print(f"FAIL: bad skill_usage row: {dict(row)}")
            return 1

        row2 = conn.execute(
            "SELECT triggered, turn_count FROM skill_usage "
            "WHERE agent_name=? AND skill_name=?", (SENTINEL, "deep-research-playbook")
        ).fetchone()
        if not row2 or row2["triggered"] != 1 or row2["turn_count"] != 1:
            print(f"FAIL: skill_manage path broken: {dict(row2) if row2 else None}")
            return 1

        # terminal call must NOT create a skill_usage row
        bad = conn.execute(
            "SELECT COUNT(*) FROM skill_usage WHERE agent_name=? AND skill_name=?",
            (SENTINEL, "terminal")
        ).fetchone()[0]
        if bad != 0:
            print("FAIL: non-skill tool leaked into skill_usage")
            return 1
    finally:
        # Cleanup sentinel rows so production stats stay honest.
        if conn is not None:
            conn.execute("DELETE FROM turn_log WHERE agent_name=?", (SENTINEL,))
            conn.execute("DELETE FROM skill_usage WHERE agent_name=?", (SENTINEL,))
            conn.commit()
        db.close()

    print("PASS: turn_capture round-trip OK (turn_log=1, skill upserts correct, non-skill filtered)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
