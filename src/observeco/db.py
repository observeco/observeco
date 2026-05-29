"""SQLite data layer — single schema for all ObserveCo data."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

SCHEMA_VERSION = 4
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

-- obs-spec-018: Restart quality classification
CREATE TABLE IF NOT EXISTS restart_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    restart_type TEXT NOT NULL CHECK(restart_type IN ('healthy', 'toctou', 'crash')),
    duration_ms INTEGER DEFAULT 0,
    crash_log_snippet TEXT,
    evidence TEXT,
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
CREATE INDEX IF NOT EXISTS idx_restart_agent_ts ON restart_log(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_restart_ts ON restart_log(timestamp);

-- Feedback inbox (v1.1)
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_type TEXT NOT NULL,
    type_label TEXT,
    summary TEXT NOT NULL,
    detail TEXT DEFAULT '',
    severity TEXT DEFAULT '',
    version TEXT DEFAULT '',
    os_info TEXT DEFAULT '',
    install_method TEXT DEFAULT '',
    delivered_tg INTEGER DEFAULT 0,
    delivered_email INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);

-- Telemetry events (v1.1 — automatic crash/usage/install pings)
CREATE TABLE IF NOT EXISTS telemetry_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    machine_id TEXT DEFAULT '',
    version TEXT DEFAULT '',
    python TEXT DEFAULT '',
    os_info TEXT DEFAULT '',
    error_type TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    stack_trace TEXT DEFAULT '',
    command TEXT DEFAULT '',
    feature_name TEXT DEFAULT '',
    extra TEXT DEFAULT '{}',
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_telemetry_event ON telemetry_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_machine ON telemetry_events(machine_id);

-- Communication Pathway Map (§3.19)
CREATE TABLE IF NOT EXISTS pathway_nodes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('cron','agent','platform','consumer','router')),
    framework TEXT DEFAULT '',
    source TEXT DEFAULT 'manual' CHECK(source IN ('auto','manual')),
    confidence INTEGER DEFAULT 50 CHECK(confidence IN (0,25,50,75,100)),
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS pathway_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES pathway_nodes(id),
    target_id TEXT REFERENCES pathway_nodes(id),
    status TEXT NOT NULL DEFAULT 'unknown' CHECK(status IN ('green','yellow','red','teal','unknown')),
    mechanism TEXT DEFAULT '',
    confidence INTEGER DEFAULT 50 CHECK(confidence IN (0,25,50,75,100)),
    scenario TEXT DEFAULT '',
    last_verified INTEGER,
    created_at INTEGER NOT NULL
);

-- Node types for display
CREATE TABLE IF NOT EXISTS pathway_node_types (
    type TEXT PRIMARY KEY,
    icon TEXT NOT NULL,
    shape TEXT NOT NULL DEFAULT 'round-rectangle',
    color TEXT NOT NULL
);

INSERT OR IGNORE INTO pathway_node_types (type, icon, shape, color) VALUES
    ('cron', '⏰', 'round-rectangle', '#f59e0b'),
    ('agent', '🧠', 'round-rectangle', '#6366f1'),
    ('platform', '📱', 'round-rectangle', '#06b6d4'),
    ('consumer', '📖', 'ellipse', '#14b8a6'),
    ('router', '🔀', 'round-rectangle', '#3b82f6');

CREATE INDEX IF NOT EXISTS idx_edges_source ON pathway_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON pathway_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_status ON pathway_edges(status);
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
        # Run full schema to ensure all tables exist (IF NOT EXISTS makes it idempotent)
        conn.executescript(_SCHEMA_SQL)

        # Check/update schema version with migration support
        cur = conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
        row = cur.fetchone()
        if row is None:
            conn.execute("INSERT INTO _meta (key, value) VALUES ('schema_version', ?)",
                         (str(SCHEMA_VERSION),))
        else:
            existing = int(row["value"])
            if existing < 2:
                # Migration 1→2: restart_log table is already handled by IF NOT EXISTS above.
                # Just bump the version.
                pass
            if existing < SCHEMA_VERSION:
                conn.execute("UPDATE _meta SET value=? WHERE key='schema_version'",
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

    # -- Feedback Inbox --

    def save_feedback(self, payload: dict,
                      delivered_tg: bool = False,
                      delivered_email: bool = False) -> int:
        """Persist a feedback entry. Returns the row id."""
        conn = self._get_conn()
        env = payload.get("environment", {})
        cur = conn.execute(
            "INSERT INTO feedback (feedback_type, type_label, summary, detail, severity, "
            "version, os_info, install_method, delivered_tg, delivered_email, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payload.get("type", "other"),
                payload.get("type_label", ""),
                payload.get("summary", ""),
                payload.get("detail", ""),
                payload.get("severity", ""),
                env.get("observeco_version", ""),
                env.get("os", ""),
                env.get("install_method", ""),
                1 if delivered_tg else 0,
                1 if delivered_email else 0,
                int(time.time()),
            ),
        )
        conn.commit()
        return cur.lastrowid or 0

    def get_feedback(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """List feedback entries, newest first."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_recent_feedback(self, since_ts: int) -> list[dict]:
        """Get feedback entries since a timestamp."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM feedback WHERE created_at >= ? ORDER BY created_at DESC",
            (since_ts,),
        )
        return [dict(r) for r in cur.fetchall()]

    # -- Telemetry Events --

    def save_telemetry(self, event: dict) -> int:
        """Persist an automatic telemetry event. Returns row id."""
        conn = self._get_conn()
        payload = event.get("payload", {})
        cur = conn.execute(
            "INSERT INTO telemetry_events (event_type, machine_id, version, python, os_info, "
            "error_type, error_message, stack_trace, command, feature_name, extra, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.get("event", "unknown"),
                event.get("machine_id", ""),
                event.get("version", ""),
                event.get("python", ""),
                event.get("os", ""),
                payload.get("type", ""),
                payload.get("message", ""),
                payload.get("stack", ""),
                payload.get("command", ""),
                payload.get("feature", ""),
                json.dumps(payload.get("detail", "")),
                int(time.time()),
            ),
        )
        conn.commit()
        return cur.lastrowid or 0

    def get_telemetry(self, event_type: Optional[str] = None,
                      limit: int = 100, offset: int = 0) -> list[dict]:
        """List telemetry events, newest first."""
        conn = self._get_conn()
        if event_type:
            cur = conn.execute(
                "SELECT * FROM telemetry_events WHERE event_type=? "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (event_type, limit, offset),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM telemetry_events ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [dict(r) for r in cur.fetchall()]

    def get_recent_telemetry(self, since_ts: int) -> list[dict]:
        """Get telemetry events since a timestamp."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM telemetry_events WHERE created_at >= ? ORDER BY created_at DESC",
            (since_ts,),
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

    def purge_stale_agents(self, valid_names: set[str]) -> int:
        """Remove agents from DB that aren't in the current valid set.
        
        Cleans up stale entries left by the old config.yaml parser that
        treated every YAML key as an agent name.
        Returns count of removed agents.
        """
        conn = self._get_conn()
        cur = conn.execute("SELECT agent_name FROM agent_configs")
        all_agents = [r["agent_name"] for r in cur.fetchall()]
        stale = [name for name in all_agents if name not in valid_names]
        if stale:
            placeholders = ",".join("?" for _ in stale)
            conn.execute(
                f"DELETE FROM agent_configs WHERE agent_name IN ({placeholders})",
                stale,
            )
            conn.execute(
                f"DELETE FROM pulse_log WHERE agent_name IN ({placeholders})",
                stale,
            )
            conn.execute(
                f"DELETE FROM errors WHERE agent_name IN ({placeholders})",
                stale,
            )
            conn.commit()
        return len(stale)

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

    # -- Restart Log (obs-spec-018) --

    def log_restart(self, agent_name: str, restart_type: str, duration_ms: int = 0,
                    crash_log_snippet: str = "", evidence: str = "") -> None:
        """Record a daemon restart classified into healthy/TOCTOU/crash."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO restart_log (agent_name, restart_type, duration_ms, "
            "crash_log_snippet, evidence, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (agent_name, restart_type, duration_ms, crash_log_snippet[:5000],
             evidence[:500], int(time.time())),
        )
        conn.commit()

    def get_recent_restarts(self, agent_name: Optional[str] = None,
                            limit: int = 50) -> list[dict]:
        """Get recent restart log entries, optionally filtered by agent."""
        conn = self._get_conn()
        if agent_name:
            cur = conn.execute(
                "SELECT * FROM restart_log WHERE agent_name=? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM restart_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in cur.fetchall()]

    def get_restart_summary(self) -> dict:
        """Per-agent restart stats for last 24h."""
        conn = self._get_conn()
        cutoff = int(time.time()) - 86400
        cur = conn.execute("""
            SELECT agent_name, restart_type, COUNT(*) as count
            FROM restart_log
            WHERE timestamp >= ?
            GROUP BY agent_name, restart_type
            ORDER BY agent_name
        """, (cutoff,))
        rows = cur.fetchall()

        summary: dict[str, dict] = {}
        for r in rows:
            name = r["agent_name"]
            if name not in summary:
                summary[name] = {
                    "agent_name": name,
                    "healthy": 0,
                    "toctou": 0,
                    "crash": 0,
                    "total": 0,
                    "false_alarm_ratio": 0.0,
                }
            entry = summary[name]
            entry[r["restart_type"]] = r["count"]
            entry["total"] += r["count"]

        for name in summary:
            s = summary[name]
            crash_labeled = s["crash"]
            actual_crashes = s["crash"]  # classified as crash = real crash
            # False alarm ratio: crashes labeled that were actually TOCTOU
            false_alarms = s["toctou"]
            total_signals = false_alarms + actual_crashes
            s["false_alarm_ratio"] = round(
                false_alarms / total_signals * 100, 1
            ) if total_signals > 0 else 0.0

        return summary

    def get_agent_false_alarm_ratio(self, agent_name: str) -> float:
        """Compute false alarm ratio for a specific agent in last 24h."""
        cutoff = int(time.time()) - 86400
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT restart_type, COUNT(*) as count FROM restart_log "
            "WHERE agent_name=? AND timestamp>=? GROUP BY restart_type",
            (agent_name, cutoff),
        )
        counts: dict[str, int] = {}
        for r in cur.fetchall():
            counts[r["restart_type"]] = r["count"]

        false_alarms = counts.get("toctou", 0)
        crashes = counts.get("crash", 0)
        total = false_alarms + crashes
        if total == 0:
            return 0.0
        return round(false_alarms / total * 100, 1)

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

    # -- Communication Pathway Map (§3.19) --

    def pathway_add_node(self, node_id: str, name: str, node_type: str,
                          framework: str = "", source: str = "manual",
                          confidence: int = 50, metadata: str = "{}") -> None:
        """Register a pathway node (cron, agent, platform, consumer, router)."""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO pathway_nodes (id, name, type, framework, source, confidence, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node_id, name, node_type, framework, source, confidence, metadata),
        )
        conn.commit()

    def pathway_add_edge(self, source_id: str, target_id: str | None = None,
                          status: str = "green", mechanism: str = "",
                          confidence: int = 50, scenario: str = "") -> int:
        """Record a communication edge. target_id=None = dead end."""
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO pathway_edges (source_id, target_id, status, mechanism, confidence, scenario, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source_id, target_id, status, mechanism, confidence, scenario, int(time.time())),
        )
        conn.commit()
        return cur.lastrowid or 0

    def pathway_get_nodes(self) -> list[dict]:
        """Get all pathway nodes."""
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM pathway_nodes ORDER BY type, name")
        return [dict(r) for r in cur.fetchall()]

    def pathway_get_edges(self) -> list[dict]:
        """Get all pathway edges with node details."""
        conn = self._get_conn()
        cur = conn.execute("""
            SELECT e.*, sn.name as source_name, sn.type as source_type,
                   tn.name as target_name, tn.type as target_type
            FROM pathway_edges e
            LEFT JOIN pathway_nodes sn ON e.source_id = sn.id
            LEFT JOIN pathway_nodes tn ON e.target_id = tn.id
            ORDER BY e.id
        """)
        return [dict(r) for r in cur.fetchall()]

    def pathway_get_graph(self) -> dict:
        """Get full graph as nodes+edges (ready for Cytoscape.js)."""
        return {
            "nodes": self.pathway_get_nodes(),
            "edges": self.pathway_get_edges(),
        }

    def pathway_scan(self) -> int:
        """Auto-detect pathways from registered agents and known infrastructure.
        Returns number of edges scanned/updated."""
        conn = self._get_conn()
        count = 0
        now = int(time.time())

        # 1. Register known consumer nodes
        known_consumers = [("sean", "Sean", "consumer", "📖")]

        # 2. Register known platform nodes
        known_platforms = [("telegram", "Telegram", "platform", "📱"),
                           ("whatsapp", "WhatsApp", "platform", "📱"),
                           ("bluebubbles", "BlueBubbles", "platform", "📱")]

        # 3. Register signal router
        known_routers = [("signal-router", "Signal Router", "router", "🔀")]

        # Ensure infrastructure nodes exist
        for nid, nname, ntype, _ in known_consumers + known_platforms + known_routers:
            conn.execute(
                "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                "VALUES (?, ?, ?, 'auto', 50)",
                (nid, nname, ntype),
            )

        # 4. Scan agents from DB — register them as agent nodes
        agents = self.get_agents()
        for a in agents:
            aname = a["agent_name"]
            fw = a.get("framework", "custom")
            nid = f"agent-{aname}"
            conn.execute(
                "INSERT OR REPLACE INTO pathway_nodes (id, name, type, framework, source, confidence) "
                "VALUES (?, ?, 'agent', ?, 'auto', 75)",
                (nid, aname, fw),
            )

            # Connect agent → Telegram (telegram is the primary delivery)
            conn.execute(
                "INSERT OR IGNORE INTO pathway_edges (source_id, target_id, status, mechanism, confidence, created_at) "
                "VALUES (?, 'telegram', 'green', 'pulse check', 75, ?)",
                (nid, now),
            )
            count += 1

        # 5. Scan Hermes cron jobs from filesystem
        hermes_cron_dir = Path.home() / ".hermes" / "cron"
        if hermes_cron_dir.exists():
            jobs_file = hermes_cron_dir / "jobs.json"
            if jobs_file.exists():
                try:
                    import json
                    raw = json.loads(jobs_file.read_text())
                    job_list = raw.get("jobs", []) if isinstance(raw, dict) else raw
                    for jidx, job in enumerate(job_list):
                        jname = job.get("name", job.get("id", f"cron-{jidx}"))
                        nid = f"cron-{jname}"
                        conn.execute(
                            "INSERT OR REPLACE INTO pathway_nodes (id, name, type, source, confidence) "
                            "VALUES (?, ?, 'cron', 'auto', 75)",
                            (nid, jname),
                        )

                        # Determine delivery target from cron config
                        deliver = job.get("deliver", "local")
                        target_nid = None
                        if "telegram" in str(deliver):
                            target_nid = "telegram"
                        elif "whatsapp" in str(deliver):
                            target_nid = "whatsapp"
                        elif deliver == "local":
                            target_nid = None  # dead end
                        elif deliver in ("all", "origin"):
                            target_nid = "telegram"
                        elif deliver:
                            # Try to match to a known agent
                            for a in agents:
                                if a["agent_name"] in deliver:
                                    target_nid = f"agent-{a['agent_name']}"
                                    break
                            if not target_nid:
                                target_nid = "telegram"  # best guess

                        status = "green" if target_nid else "red"
                        scenario = "" if target_nid else "1"  # scenario 1: dead-end delivery

                        conn.execute(
                            "INSERT OR REPLACE INTO pathway_edges (source_id, target_id, status, "
                            "mechanism, confidence, scenario, last_verified, created_at) "
                            "VALUES (?, ?, ?, 'cron_delivery', 75, ?, ?, ?)",
                            (nid, target_nid, status, scenario, now, now),
                        )
                        count += 1
                except (json.JSONDecodeError, Exception) as exc:
                    pass

        conn.commit()
        return count

    def pathway_clear(self) -> int:
        """Reset all pathway data for fresh scan. Returns count of removed items."""
        conn = self._get_conn()
        edges = conn.execute("SELECT COUNT(*) FROM pathway_edges").fetchone()[0]
        nodes = conn.execute("SELECT COUNT(*) FROM pathway_nodes WHERE source='auto'").fetchone()[0]
        conn.execute("DELETE FROM pathway_edges")
        conn.execute("DELETE FROM pathway_nodes WHERE source='auto'")
        conn.commit()
        return edges + nodes
