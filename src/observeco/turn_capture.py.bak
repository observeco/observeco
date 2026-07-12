"""ObserveCo turn-capture hook handler.

Runs as a *separate, timeout-bounded subprocess* spawned by Hermes' native
shell-hook system (post_tool_call / on_session_end events). It reads one hook
payload from stdin, writes it to pulse.db, and exits 0.

Blast-radius contract (why this is safe to attach to a live agent):
  - This process is spawned by Hermes with a hard timeout (2s in config).
    If it overruns or crashes, Hermes discards it and the agent turn proceeds.
    The agent is NEVER in this process's call path.
  - Every DB op is wrapped; on any failure we sys.exit(0). A hook returning
    non-zero is treated as an error by some callers — we must never do that.
  - No network, no LLM, no imports that can hang. sqlite3 + stdlib only.
  - Writes are synchronous and single-row. pulse.db is WAL with a 5s
    busy_timeout, so concurrent hook-subprocess writes cannot corrupt it.

What we record (honest only — no fabrication):
  - turn_log: one row per on_session_end (real turn count for the 200-turn goal).
  - skill_usage: on post_tool_call where tool_name in {skill_view, skill_manage},
    extract the skill name and mark it triggered / bump turn_count.

ponytail: agent identity is session_id, not the Hermes profile name. The hook
payload carries session_id/platform/model but no profile field. Upgrade path:
join session_id -> profile via the Hermes session DB (out of scope here).

ponytail: "skill never triggered" means "never explicitly skill_view'd". Skills
that are auto-loaded into context never fire a tool call, so they remain
triggered=0. This is the honest ceiling of tool-signal detection. A deeper
signal (LLM-judged activation) is a separate layer — not fabricated here.
"""

from __future__ import annotations

import json
import sys
import time

SKILL_TOOLS = {"skill_view", "skill_manage"}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _extract_skill_name(tool_name: str, ev: dict) -> str | None:
    """Pull the skill name from a skill tool call.

    skill_view(name=...) / skill_manage(action=..., name=...) carry it in
    tool_input. Falls back to scanning the serialized input for a name field.
    """
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


def _write_event(conn, ev: dict) -> None:
    """Write a single parsed event to the appropriate table."""
    event = ev.get("hook_event_name", "")
    ts = _now_ms()

    if event == "on_session_end":
        # Real turn heartbeat. Token counts aren't in the payload -> 0 (honest).
        agent = ev.get("session_id") or "unknown"
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
            return  # only skill-tool calls are interesting for the optimiser
        skill_name = _extract_skill_name(tool_name, ev)
        if not skill_name:
            return
        agent = ev.get("session_id") or "unknown"
        # Upsert: mark triggered, bump turn_count, stamp last_triggered.
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
    """Entry point for the `observeco capture-turn` CLI command.

    Reads the hook payload from stdin, writes it, exits 0. Never raises.
    """
    conn = None
    db = None
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        payload = json.loads(raw)

        # Lazy import keeps startup lean and failure isolated.
        from observeco.db import Database
        db = Database()
        conn = db._get_conn()
        _write_event(conn, payload)
        conn.commit()
    except Exception:
        pass  # any failure -> silent, exit 0 (blast-radius contract)
    finally:
        try:
            if conn is not None:
                conn.commit()
        except Exception:
            pass
        try:
            if db is not None:
                db.close()
        except Exception:
            pass
    sys.exit(0)


if __name__ == "__main__":
    run()
