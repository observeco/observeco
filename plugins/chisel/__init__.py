"""Chisel — System Prompt Decomposition + Drift Detection plugin.

Registers on_session_start hook. Reads system prompt from disk,
decomposes into 5 components, stores to chisel.db, checks drift.

Zero external deps. stdlib only.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from .chisel_core import (
    COMPONENT_ORDER,
    assemble_prompt,
    check_drift,
    decompose,
    format_breakdown,
    format_drift,
    prompt_hash,
)

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
CHISEL_DB = Path(
    os.environ.get("OBSERVECO_CHISEL_DB", str(HERMES_HOME / "state" / "chisel.db"))
)
SCHEMA_VERSION = 2
TIME_GATE_S = 3600  # 1 hour — skip drift if last trim was within this window


# ── DB Layer ──────────────────────────────────────────────────────────────


def _get_db() -> sqlite3.Connection:
    """Get a connection to chisel.db, creating it if needed."""
    CHISEL_DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(CHISEL_DB))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    _ensure_schema(db)
    return db


def _ensure_schema(db: sqlite3.Connection) -> None:
    """Create tables if they don't exist. Run migrations if needed."""
    db.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = db.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
    current_version = row[0] if row else 0

    if current_version < 1:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS trim_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                timestamp REAL NOT NULL,
                identity_tokens INTEGER NOT NULL,
                skills_tokens INTEGER NOT NULL,
                memory_tokens INTEGER NOT NULL,
                tools_tokens INTEGER NOT NULL,
                guidance_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                savings_ratio REAL NOT NULL,
                raw_prompt_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drift_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                component TEXT NOT NULL,
                current_tokens INTEGER NOT NULL,
                baseline_tokens INTEGER NOT NULL,
                delta_pct REAL NOT NULL,
                delta_tokens INTEGER NOT NULL,
                breached INTEGER NOT NULL,
                method TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS baseline (
                agent_name TEXT PRIMARY KEY,
                identity_tokens INTEGER NOT NULL,
                skills_tokens INTEGER NOT NULL,
                memory_tokens INTEGER NOT NULL,
                tools_tokens INTEGER NOT NULL,
                guidance_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                set_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_trim_agent ON trim_log(agent_name, timestamp);
            CREATE INDEX IF NOT EXISTS idx_drift_agent ON drift_log(agent_name, timestamp);
            INSERT INTO schema_version (version) VALUES (1);
        """)
        db.commit()

    if current_version < 2:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS cut_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                timestamp REAL NOT NULL,
                file_path TEXT NOT NULL,
                cut_type TEXT NOT NULL,
                tokens_before INTEGER NOT NULL,
                tokens_after INTEGER NOT NULL,
                tokens_saved INTEGER NOT NULL,
                backup_path TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                verified_at REAL,
                rule_hash TEXT,
                details TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_cut_agent ON cut_log(agent_name, timestamp);
            CREATE INDEX IF NOT EXISTS idx_cut_verified ON cut_log(verified);
            CREATE INDEX IF NOT EXISTS idx_cut_rule_hash ON cut_log(rule_hash);
            INSERT INTO schema_version (version) VALUES (2);
        """)
        db.commit()


def _recreate_db() -> None:
    """Recreate chisel.db from scratch after corruption."""
    logger.warning("chisel.db corrupted — recreated from schema. Historical data lost.")
    try:
        CHISEL_DB.unlink(missing_ok=True)
    except OSError:
        pass
    db = _get_db()
    db.close()


def _db_op(fn):
    """Decorator: wrap DB operations with corruption recovery."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "no such table" in str(e) or "database disk image is malformed" in str(e):
                _recreate_db()
                return fn(*args, **kwargs)
            raise
    return wrapper


# ── DB Queries ────────────────────────────────────────────────────────────


@_db_op
def store_trim(agent_name: str, result: dict, prompt: str) -> None:
    """Store a trim result to chisel.db."""
    db = _get_db()
    try:
        db.execute(
            """INSERT INTO trim_log
               (agent_name, timestamp, identity_tokens, skills_tokens, memory_tokens,
                tools_tokens, guidance_tokens, total_tokens, savings_ratio, raw_prompt_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_name, time.time(),
                result["identity_tokens"], result["skills_tokens"],
                result["memory_tokens"], result["tools_tokens"],
                result["guidance_tokens"], result["total_tokens"],
                result["savings_ratio"], prompt_hash(prompt),
            ),
        )
        db.commit()
    finally:
        db.close()


@_db_op
def store_drift(agent_name: str, drift_results: list[dict]) -> None:
    """Store drift results to chisel.db."""
    db = _get_db()
    try:
        now = time.time()
        for d in drift_results:
            db.execute(
                """INSERT INTO drift_log
                   (agent_name, component, current_tokens, baseline_tokens,
                    delta_pct, delta_tokens, breached, method, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent_name, d["component"],
                    d["current_tokens"], d["baseline_tokens"],
                    d["delta_pct"], d["delta_tokens"],
                    1 if d["breached"] else 0,
                    "rolling", now,
                ),
            )
        db.commit()
    finally:
        db.close()


@_db_op
def get_last_trim_time(agent_name: str) -> Optional[float]:
    """Get timestamp of most recent trim for this agent. None if never trimmed."""
    db = _get_db()
    try:
        row = db.execute(
            "SELECT timestamp FROM trim_log WHERE agent_name = ? ORDER BY timestamp DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        return row[0] if row else None
    finally:
        db.close()


@_db_op
def get_recent_trims(agent_name: str, limit: int = 50) -> list[dict]:
    """Get recent trim entries for an agent."""
    db = _get_db()
    try:
        rows = db.execute(
            """SELECT timestamp, identity_tokens, skills_tokens, memory_tokens,
                      tools_tokens, guidance_tokens, total_tokens, savings_ratio
               FROM trim_log
               WHERE agent_name = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (agent_name, limit),
        ).fetchall()
        return [
            {
                "timestamp": r[0],
                "identity_tokens": r[1],
                "skills_tokens": r[2],
                "memory_tokens": r[3],
                "tools_tokens": r[4],
                "guidance_tokens": r[5],
                "total_tokens": r[6],
                "savings_ratio": r[7],
            }
            for r in rows
        ]
    finally:
        db.close()


@_db_op
def get_trims_since(agent_name: str, since: float) -> list[dict]:
    """Get trim entries for an agent since a timestamp."""
    db = _get_db()
    try:
        rows = db.execute(
            """SELECT timestamp, identity_tokens, skills_tokens, memory_tokens,
                      tools_tokens, guidance_tokens, total_tokens, savings_ratio
               FROM trim_log
               WHERE agent_name = ? AND timestamp >= ?
               ORDER BY timestamp ASC""",
            (agent_name, since),
        ).fetchall()
        return [
            {
                "timestamp": r[0],
                "identity_tokens": r[1],
                "skills_tokens": r[2],
                "memory_tokens": r[3],
                "tools_tokens": r[4],
                "guidance_tokens": r[5],
                "total_tokens": r[6],
                "savings_ratio": r[7],
            }
            for r in rows
        ]
    finally:
        db.close()


@_db_op
def get_drift_log(agent_name: str, limit: int = 20) -> list[dict]:
    """Get recent drift entries for an agent."""
    db = _get_db()
    try:
        rows = db.execute(
            """SELECT component, current_tokens, baseline_tokens, delta_pct,
                      delta_tokens, breached, method, timestamp
               FROM drift_log
               WHERE agent_name = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (agent_name, limit),
        ).fetchall()
        return [
            {
                "component": r[0],
                "current_tokens": r[1],
                "baseline_tokens": r[2],
                "delta_pct": r[3],
                "delta_tokens": r[4],
                "breached": bool(r[5]),
                "method": r[6],
                "timestamp": r[7],
            }
            for r in rows
        ]
    finally:
        db.close()


@_db_op
def get_all_agents() -> list[str]:
    """Get list of all agents with trim data."""
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT DISTINCT agent_name FROM trim_log ORDER BY agent_name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        db.close()


# ── v0.2: Cut Log Queries ────────────────────────────────────────────────


@_db_op
def store_cut(
    agent_name: str,
    file_path: str,
    cut_type: str,
    tokens_before: int,
    tokens_after: int,
    backup_path: str,
    details: str = "",
    rule_hash_val: str = "",
) -> int:
    """Store a cut result to cut_log. Returns the row id."""
    db = _get_db()
    try:
        cur = db.execute(
            """INSERT INTO cut_log
               (agent_name, timestamp, file_path, cut_type, tokens_before,
                tokens_after, tokens_saved, backup_path, verified, rule_hash, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (
                agent_name, time.time(), file_path, cut_type,
                tokens_before, tokens_after, tokens_before - tokens_after,
                backup_path, rule_hash_val, details,
            ),
        )
        db.commit()
        return cur.lastrowid or 0
    finally:
        db.close()


@_db_op
def get_last_cut(agent_name: str) -> Optional[dict]:
    """Get the most recent cut for an agent."""
    db = _get_db()
    try:
        row = db.execute(
            """SELECT id, agent_name, timestamp, file_path, cut_type,
                      tokens_before, tokens_after, tokens_saved, backup_path,
                      verified, verified_at, rule_hash
               FROM cut_log
               WHERE agent_name = ?
               ORDER BY timestamp DESC LIMIT 1""",
            (agent_name,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "agent_name": row[1],
            "timestamp": row[2],
            "file_path": row[3],
            "cut_type": row[4],
            "tokens_before": row[5],
            "tokens_after": row[6],
            "tokens_saved": row[7],
            "backup_path": row[8],
            "verified": row[9],
            "verified_at": row[10],
            "rule_hash": row[11],
        }
    finally:
        db.close()


@_db_op
def update_cut_verified(cut_id: int, verified: int) -> None:
    """Mark a cut as verified (1), regression (-1), or pending (0)."""
    db = _get_db()
    try:
        db.execute(
            "UPDATE cut_log SET verified = ?, verified_at = ? WHERE id = ?",
            (verified, time.time(), cut_id),
        )
        db.commit()
    finally:
        db.close()


@_db_op
def get_verified_rules(agent_name: str) -> set[str]:
    """Get rule_hashes of cuts that were verified safe for this agent."""
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT rule_hash FROM cut_log WHERE agent_name = ? AND verified = 1 AND rule_hash IS NOT NULL AND rule_hash != ''",
            (agent_name,),
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        db.close()


@_db_op
def get_trim_before_cut(agent_name: str, cut_timestamp: float) -> Optional[dict]:
    """Get the trim snapshot taken just before a cut."""
    db = _get_db()
    try:
        row = db.execute(
            """SELECT timestamp, identity_tokens, skills_tokens, memory_tokens,
                      tools_tokens, guidance_tokens, total_tokens, savings_ratio
               FROM trim_log
               WHERE agent_name = ? AND timestamp < ?
               ORDER BY timestamp DESC LIMIT 1""",
            (agent_name, cut_timestamp),
        ).fetchone()
        if not row:
            return None
        return {
            "timestamp": row[0],
            "identity_tokens": row[1],
            "skills_tokens": row[2],
            "memory_tokens": row[3],
            "tools_tokens": row[4],
            "guidance_tokens": row[5],
            "total_tokens": row[6],
            "savings_ratio": row[7],
        }
    finally:
        db.close()


# ── Prompt Reader ─────────────────────────────────────────────────────────


def _read_file_safe(path: Path) -> str:
    """Read a file, returning empty string on any error."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def _read_skills() -> list[str]:
    """Read all skill .md files from ~/.hermes/skills/."""
    skills_dir = HERMES_HOME / "skills"
    if not skills_dir.is_dir():
        return []
    texts = []
    for f in sorted(skills_dir.iterdir()):
        if f.suffix in (".md", ".txt", ".yaml", ".yml"):
            text = _read_file_safe(f)
            if text.strip():
                texts.append(text)
    return texts


def _read_memory() -> list[str]:
    """Read all memory files from ~/.hermes/memory/."""
    memory_dir = HERMES_HOME / "memory"
    if not memory_dir.is_dir():
        return []
    texts = []
    for f in sorted(memory_dir.iterdir()):
        if f.suffix in (".md", ".txt", ".json"):
            text = _read_file_safe(f)
            if text.strip():
                texts.append(text)
    return texts


def read_system_prompt(agent_name: str = "main") -> str:
    """Read and assemble the system prompt from disk.

    Reads config.yaml, SOUL.md, skills/, and memory/ from ~/.hermes/.
    Falls back gracefully if any source is missing.
    """
    config_yaml = _read_file_safe(HERMES_HOME / "config.yaml")
    soul_md = _read_file_safe(HERMES_HOME / "SOUL.md")
    skills = _read_skills()
    memory = _read_memory()

    return assemble_prompt(config_yaml, soul_md, skills, memory)


# ── Hook Handler ──────────────────────────────────────────────────────────


def on_session_start(session_id: str, model: str = "", platform: str = "") -> None:
    """Hook handler: decompose system prompt, store, check drift.

    Fires on every new session. Time-gated to skip if last trim was <1h ago.
    """
    # Resolve agent name from session_id or model
    agent_name = model or "main"

    # Time gate: skip if recently trimmed
    last_trim = get_last_trim_time(agent_name)
    if last_trim and (time.time() - last_trim) < TIME_GATE_S:
        logger.debug("chisel: skip trim for %s — last trim was %.0fs ago", agent_name, time.time() - last_trim)
        return

    # Read system prompt from disk
    prompt = read_system_prompt(agent_name)
    if not prompt or len(prompt) < 100:
        logger.debug("chisel: system prompt too short (%d chars) for %s — skipping", len(prompt), agent_name)
        return

    # Decompose
    result = decompose(prompt)
    store_trim(agent_name, result, prompt)

    # Check drift against 7-day rolling average
    week_ago = time.time() - 7 * 86400
    recent = get_trims_since(agent_name, week_ago)
    if len(recent) >= 2:
        # Compute baseline from all entries in the window
        baseline = {
            "identity_tokens": sum(r["identity_tokens"] for r in recent) // len(recent),
            "skills_tokens": sum(r["skills_tokens"] for r in recent) // len(recent),
            "memory_tokens": sum(r["memory_tokens"] for r in recent) // len(recent),
            "tools_tokens": sum(r["tools_tokens"] for r in recent) // len(recent),
            "guidance_tokens": sum(r["guidance_tokens"] for r in recent) // len(recent),
            "total_tokens": sum(r["total_tokens"] for r in recent) // len(recent),
        }
        drift_results = []
        for comp in COMPONENT_ORDER:
            key = f"{comp}_tokens"
            cur_val = result[key]
            base_val = baseline[key]
            delta_pct, delta_tokens, breached = check_drift(cur_val, base_val)
            drift_results.append({
                "component": comp,
                "current_tokens": cur_val,
                "baseline_tokens": base_val,
                "delta_pct": round(delta_pct, 1),
                "delta_tokens": delta_tokens,
                "breached": breached,
            })
        store_drift(agent_name, drift_results)

        breached = [d for d in drift_results if d["breached"]]
        if breached:
            comps = ", ".join(d["component"] for d in breached)
            logger.warning(
                "chisel: drift breach for %s — %s. "
                "Run 'hermes chisel drift --agent %s' for details.",
                agent_name, comps, agent_name,
            )


# ── Plugin Registration ────────────────────────────────────────────────────


def register(ctx) -> None:
    """Register the on_session_start hook."""
    ctx.register_hook("on_session_start", on_session_start)
    logger.info("Chisel plugin registered — will decompose system prompts on session start")
