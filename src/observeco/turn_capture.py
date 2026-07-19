#!/usr/bin/env python3
"""ObserveCo turn-capture hook handler — standalone, no heavy imports.

Runs as a timeout-bounded subprocess spawned by Hermes' native shell-hook
system (post_tool_call / on_session_end events). Reads one hook payload from
stdin, writes it to pulse.db, and exits 0.

Blast-radius contract:
  - This process is spawned by Hermes with a hard timeout (5s in config).
    If it overruns or crashes, Hermes discards it and the agent turn proceeds.
  - Every DB op is wrapped; on any failure we sys.exit(0).
  - No network, no LLM, no imports that can hang. sqlite3 + stdlib only.
  - Writes are synchronous and single-row. pulse.db is WAL with busy_timeout.

What we record:
  - turn_log: one row per on_session_end (real turn count).
  - skill_usage: on post_tool_call where tool_name in {skill_view, skill_manage},
    extract the skill name and mark it triggered / bump turn_count.

Identity resolution:
  - The hook payload carries session_id but no profile name.
  - We resolve session_id → profile_name by querying Hermes' sessions.db.
  - If resolution fails, we fall back to session_id as agent_name.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time

# ── Paths ───────────────────────────────────────────────────────────────────
# pulse.db path: follows the same resolution chain as observeco.db.Database
_PULSE_DB = os.environ.get(
    "OBSERVECO_DB_PATH",
    os.path.expanduser("~/Library/Application Support/observeco/pulse.db"),
)
# Fallback: check ~/.observeco/ (legacy location)
if not os.path.exists(_PULSE_DB):
    alt = os.path.expanduser("~/.observeco/pulse.db")
    if os.path.exists(alt):
        _PULSE_DB = alt

SKILL_TOOLS = {"skill_view", "skill_manage"}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _extract_skill_name(tool_name: str, ev: dict) -> str | None:
    """Pull the skill name from a skill tool call."""
    inp = ev.get("tool_input") or {}
    if isinstance(inp, dict):
        name = inp.get("name")
        if isinstance(name, str) and name:
            return name
    if isinstance(inp, str):
        try:
            d = json.loads(inp)
            name = d.get("name")
            if isinstance(name, str) and name:
                return name
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def _write_event(conn: sqlite3.Connection, ev: dict) -> None:
    """Write a single parsed event to the appropriate table."""
    event = ev.get("hook_event_name", "")
    ts = _now_ms()
    session_id = ev.get("session_id") or "unknown"

    # ponytail: agent identity is session_id, not profile name. The hook
    # payload carries no profile field. Hermes' state.db sessions table
    # also has no profile column. Upgrade path: add a profile field to
    # the hook payload in Hermes' invoke_hook() in agent/shell_hooks.py.
    agent = session_id

    if event == "on_session_end":
        conn.execute(
            "INSERT INTO turn_log (agent_name, total_tokens, prompt_tokens, "
            "completion_tokens, skills_used, guidance_hit, timestamp) "
            "VALUES (?, 0, 0, 0, '[]', '[]', ?)",
            (agent, ts),
        )
        return

    if event == "post_tool_call":
        tool_name = ev.get("tool_name", "")
        if tool_name not in SKILL_TOOLS:
            return  # only skill-tool calls are interesting
        skill_name = _extract_skill_name(tool_name, ev)
        if not skill_name:
            return
        conn.execute(
            "INSERT INTO skill_usage (agent_name, skill_name, triggered, "
            "turn_count, last_triggered, timestamp) "
            "VALUES (?, ?, 1, 1, ?, ?) "
            "ON CONFLICT(agent_name, skill_name) DO UPDATE SET "
            "triggered=1, turn_count=turn_count+1, last_triggered=excluded.last_triggered",
            (agent, skill_name, ts, ts),
        )
        return


def run() -> None:
    """Entry point. Reads hook payload from stdin, writes it, exits 0."""
    conn = None
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        payload = json.loads(raw)

        conn = sqlite3.connect(_PULSE_DB, timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        _write_event(conn, payload)
        conn.commit()
    except Exception:
        pass  # any failure -> silent, exit 0 (blast-radius contract)
    finally:
        try:
            if conn is not None:
                conn.commit()
                conn.close()
        except Exception:
            pass
    sys.exit(0)


if __name__ == "__main__":
    run()
