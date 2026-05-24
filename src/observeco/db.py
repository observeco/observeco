"""SQLite data layer — single schema for all ObserveCo data."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

SCHEMA_VERSION = 1
DB_DIR = Path(user_data_dir("observeco", "observeco"))
DB_PATH = DB_DIR / "pulse.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS _meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS pulse_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    agent_framework TEXT NOT NULL DEFAULT 'hermes',
    status TEXT NOT NULL CHECK(status IN ('alive','dead','error')),
    latency_ms REAL DEFAULT 0,
    error_message TEXT,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS circuit_breakers (
    agent_name TEXT PRIMARY KEY,
    failure_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    tripped INTEGER NOT NULL DEFAULT 0,
    cooldown_until INTEGER,
    last_failure TEXT,
    last_failure_error TEXT
);

CREATE TABLE IF NOT EXISTS chisel_trims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    identity_tokens INTEGER DEFAULT 0,
    skills_tokens INTEGER DEFAULT 0,
    memory_tokens INTEGER DEFAULT 0,
    tools_tokens INTEGER DEFAULT 0,
    guidance_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER NOT NULL,
    savings_ratio REAL DEFAULT 0,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS chisel_drift (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    component TEXT NOT NULL,
    current_tokens INTEGER NOT NULL,
    week_avg_tokens INTEGER NOT NULL,
    delta_pct REAL NOT NULL,
    breached INTEGER NOT NULL DEFAULT 0,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS clawforge_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    memory_md_size INTEGER DEFAULT 0,
    skill_count INTEGER DEFAULT 0,
    workspace_files INTEGER DEFAULT 0,
    history_depth INTEGER DEFAULT 0,
    total_estimated_tokens INTEGER DEFAULT 0,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS clawforge_loads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    intent_class TEXT NOT NULL,
    sources_loaded INTEGER DEFAULT 0,
    sources_skipped INTEGER DEFAULT 0,
    tokens_saved INTEGER DEFAULT 0,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS clawforge_garden (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    duplicates_found INTEGER DEFAULT 0,
    contradictions_found INTEGER DEFAULT 0,
    stale_entries INTEGER DEFAULT 0,
    memory_debt_score REAL DEFAULT 0,
    suggestions TEXT,
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_configs (
    agent_name TEXT PRIMARY KEY,
    framework TEXT NOT NULL DEFAULT 'custom',
    health_check TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_seen INTEGER
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    severity TEXT NOT NULL DEFAULT 'warning' CHECK(severity IN ('info','warning','error','critical')),
    timestamp INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pulse_agent_ts ON pulse_log(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_pulse_ts ON pulse_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_chisel_trim_agent_ts ON chisel_trims(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_chisel_drift_agent_ts ON chisel_drift(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_errors_agent_ts ON errors(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_errors_ts ON errors(timestamp);
CREATE INDEX IF NOT EXISTS idx_profiles_agent_ts ON clawforge_profiles(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_garden_agent_ts ON clawforge_garden(agent_name, timestamp);
"""


class Database:
    """Thread-safe SQLite database for ObserveCo data."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)
        # Check/update schema version
        cur = conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
        row = cur.fetchone()
        if row is None:
            conn.execute("INSERT INTO _meta (key, value) VALUES ('schema_version', ?)",
                         (str(SCHEMA_VERSION),))
        conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- Pulse Log --

    def log_pulse(self, agent_name: str, status: str, latency_ms: float = 0,
                  error_message: str = "", agent_framework: str = "hermes") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO pulse_log (agent_name, agent_framework, status, latency_ms, error_message, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (agent_name, agent_framework, status, latency_ms, error_message, int(time.time())),
        )
        conn.commit()
        # Auto-log to errors table on error/dead status with message
        if status in ("error", "dead") and error_message:
            self.log_error(agent_name, f"pulse_{status}", error_message,
                           severity="critical" if status == "dead" else "error")

    def get_recent_pulses(self, agent_name: Optional[str] = None, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM pulse_log WHERE agent_name=? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM pulse_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in cur.fetchall()]

    # -- Circuit Breakers --

    def get_circuit_breakers(self) -> list[dict]:
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM circuit_breakers ORDER BY agent_name")
        now = int(time.time())
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            # Auto-clear expired cooldowns
            if d["cooldown_until"] and d["cooldown_until"] < now and d["tripped"]:
                d["tripped"] = 0
                d["cooldown_until"] = None
                self._update_breaker(d["agent_name"], d["failure_count"], d["max_retries"],
                                     0, None, d.get("last_failure"), d.get("last_failure_error"))
            rows.append(d)
        return rows

    def record_failure(self, agent_name: str, error: str) -> dict:
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM circuit_breakers WHERE agent_name=?",
                           (agent_name,))
        row = cur.fetchone()
        now = int(time.time())

        if row:
            failures = row["failure_count"] + 1
            max_r = row["max_retries"]
            tripped = 1 if failures >= max_r else 0
            cooldown = (now + 300) if tripped else None
            conn.execute(
                "UPDATE circuit_breakers SET failure_count=?, tripped=?, cooldown_until=?, "
                "last_failure=?, last_failure_error=? WHERE agent_name=?",
                (failures, tripped, cooldown, str(now), error[:500], agent_name),
            )
        else:
            failures = 1
            max_r = 3
            tripped = 0
            cooldown = None
            conn.execute(
                "INSERT INTO circuit_breakers (agent_name, failure_count, max_retries, tripped, "
                "cooldown_until, last_failure, last_failure_error) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (agent_name, failures, max_r, tripped, cooldown, str(now), error[:500]),
            )
        conn.commit()
        return {"agent_name": agent_name, "failures": failures, "tripped": bool(tripped)}

    def reset_breaker(self, agent_name: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE circuit_breakers SET failure_count=0, tripped=0, cooldown_until=NULL, "
            "last_failure=NULL, last_failure_error=NULL WHERE agent_name=?",
            (agent_name,),
        )
        conn.commit()

    def set_threshold(self, agent_name: str, max_retries: int) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO circuit_breakers (agent_name, failure_count, max_retries, tripped) "
            "VALUES (?, 0, ?, 0) "
            "ON CONFLICT(agent_name) DO UPDATE SET max_retries=excluded.max_retries",
            (agent_name, max_retries),
        )
        conn.commit()

    def _update_breaker(self, agent_name: str, failures: int, max_retries: int,
                        tripped: int, cooldown: int | None,
                        last_failure: str | None, error: str | None) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE circuit_breakers SET failure_count=?, max_retries=?, tripped=?, "
            "cooldown_until=?, last_failure=?, last_failure_error=? WHERE agent_name=?",
            (failures, max_retries, tripped, cooldown, last_failure, error, agent_name),
        )
        conn.commit()

    # -- Chisel --

    def log_trim(self, agent_name: str, identity: int, skills: int, memory: int,
                 tools: int, guidance: int, total: int, savings: float) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO chisel_trims (agent_name, identity_tokens, skills_tokens, memory_tokens, "
            "tools_tokens, guidance_tokens, total_tokens, savings_ratio, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_name, identity, skills, memory, tools, guidance, total, savings,
             int(time.time())),
        )
        conn.commit()

    def get_trims(self, agent_name: Optional[str] = None, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM chisel_trims WHERE agent_name=? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM chisel_trims ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in cur.fetchall()]

    def log_drift(self, agent_name: str, component: str, current: int,
                  week_avg: int, delta_pct: float, breached: bool) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO chisel_drift (agent_name, component, current_tokens, week_avg_tokens, "
            "delta_pct, breached, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (agent_name, component, current, week_avg, delta_pct, int(breached),
             int(time.time())),
        )
        conn.commit()

    def get_drift(self, agent_name: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM chisel_drift WHERE agent_name=? ORDER BY timestamp DESC",
                (agent_name,),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM chisel_drift ORDER BY timestamp DESC"
            )
        return [dict(r) for r in cur.fetchall()]

    # -- ClawForge --

    def log_profile(self, agent_name: str, memory_size: int, skills: int,
                    workspace_files: int, history_depth: int, total_tokens: int) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO clawforge_profiles (agent_name, memory_md_size, skill_count, "
            "workspace_files, history_depth, total_estimated_tokens, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (agent_name, memory_size, skills, workspace_files, history_depth,
             total_tokens, int(time.time())),
        )
        conn.commit()

    def get_profiles(self, agent_name: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM clawforge_profiles WHERE agent_name=? ORDER BY timestamp DESC",
                (agent_name,),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM clawforge_profiles ORDER BY timestamp DESC"
            )
        return [dict(r) for r in cur.fetchall()]

    def log_load(self, agent_name: str, intent_class: str,
                 loaded: int, skipped: int, tokens_saved: int) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO clawforge_loads (agent_name, intent_class, sources_loaded, "
            "sources_skipped, tokens_saved, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (agent_name, intent_class, loaded, skipped, tokens_saved, int(time.time())),
        )
        conn.commit()

    def get_loads(self, agent_name: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM clawforge_loads WHERE agent_name=? ORDER BY timestamp DESC",
                (agent_name,),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM clawforge_loads ORDER BY timestamp DESC"
            )
        return [dict(r) for r in cur.fetchall()]

    def log_garden(self, agent_name: str, duplicates: int, contradictions: int,
                   stale: int, debt_score: float, suggestions: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO clawforge_garden (agent_name, duplicates_found, contradictions_found, "
            "stale_entries, memory_debt_score, suggestions, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (agent_name, duplicates, contradictions, stale, debt_score, suggestions[:2000],
             int(time.time())),
        )
        conn.commit()

    def get_gardens(self, agent_name: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM clawforge_garden WHERE agent_name=? ORDER BY timestamp DESC",
                (agent_name,),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM clawforge_garden ORDER BY timestamp DESC"
            )
        return [dict(r) for r in cur.fetchall()]

    # -- Agent Config --

    def register_agent(self, name: str, framework: str = "custom",
                       health_check: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO agent_configs (agent_name, framework, health_check, is_active, last_seen) "
            "VALUES (?, ?, ?, 1, ?) "
            "ON CONFLICT(agent_name) DO UPDATE SET last_seen=excluded.last_seen",
            (name, framework, health_check, int(time.time())),
        )
        conn.commit()

    def get_agents(self) -> list[dict]:
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM agent_configs ORDER BY agent_name")
        return [dict(r) for r in cur.fetchall()]

    # -- Errors --

    def log_error(self, agent_name: str, error_type: str, message: str,
                  severity: str = "error") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO errors (agent_name, error_type, error_message, severity, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (agent_name, error_type, message[:2000], severity, int(time.time())),
        )
        conn.commit()

    def get_errors(self, agent_name: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM errors WHERE agent_name=? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM errors ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in cur.fetchall()]

    # -- Stats --

    def get_agent_status_summary(self) -> dict:
        """Return per-agent latest pulse status."""
        conn = self._get_conn()
        cur = conn.execute("""
            SELECT p.agent_name, p.status, p.latency_ms, p.timestamp, c.tripped as circuit_tripped
            FROM pulse_log p
            LEFT JOIN circuit_breakers c ON p.agent_name = c.agent_name
            WHERE p.id IN (SELECT MAX(id) FROM pulse_log GROUP BY agent_name)
        """)
        rows = cur.fetchall()
        return {r["agent_name"]: dict(r) for r in rows}
