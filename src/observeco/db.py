"""SQLite data layer — single schema for all ObserveCo data."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 8
DB_DIR = Path(user_data_dir("observeco", "observeco"))
DB_PATH = DB_DIR / "pulse.db"

# Versioned migrations — each entry is (version, sql)
# Run in order when upgrading from an older version.
MIGRATIONS = [
    (2, """-- Migration 2: restart_log table
CREATE TABLE IF NOT EXISTS restart_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    restart_type TEXT NOT NULL CHECK(restart_type IN ('healthy', 'toctou', 'crash')),
    duration_ms INTEGER DEFAULT 0,
    crash_log_snippet TEXT,
    evidence TEXT,
    timestamp INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_restart_agent_ts ON restart_log(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_restart_ts ON restart_log(timestamp);
"""),
    (3, """-- Migration 3: feedback table
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
"""),
    (4, """-- Migration 4: telemetry + pathway tables
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
CREATE INDEX IF NOT EXISTS idx_edges_source ON pathway_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON pathway_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_status ON pathway_edges(status);
"""),
    (5, """-- Migration 5: auth sessions + dead letter queue
CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    email TEXT DEFAULT '',
    name TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    provider TEXT DEFAULT 'local',
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    agent_id TEXT DEFAULT '',
    payload TEXT DEFAULT '{}',
    error TEXT NOT NULL,
    retries INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','retried','failed','resolved')),
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_dlq_status ON dead_letter_queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_dlq_retries ON dead_letter_queue(retries);
"""),
    (6, """-- Migration 6: L2 trending, push alerts, plugin tracking
CREATE TABLE IF NOT EXISTS l2_trending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    trend_type TEXT NOT NULL CHECK(trend_type IN ('memory_bloat','stuck','drift','upstream_fail')),
    signal_label TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'warning' CHECK(severity IN ('info','warning','critical')),
    metric_value REAL DEFAULT 0,
    threshold REAL DEFAULT 0,
    auto_action TEXT NOT NULL DEFAULT 'none' CHECK(auto_action IN ('none','graceful_restart','sigabort','circuit_backoff','restart_fallback')),
    resolved INTEGER NOT NULL DEFAULT 0,
    resolved_action TEXT DEFAULT '',
    timestamp INTEGER NOT NULL,
    resolved_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_l2_trending_agent ON l2_trending(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_l2_trending_type ON l2_trending(trend_type, resolved);

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL CHECK(channel IN ('telegram','webhook','email')),
    target TEXT NOT NULL,
    event_types TEXT NOT NULL DEFAULT 'all' CHECK(event_types IN ('all','critical_only','heal_failure','drift','circuit_trip','agent_death')),
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    target TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0,
    delivery_error TEXT DEFAULT '',
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alert_log_ts ON alert_log(created_at);

CREATE TABLE IF NOT EXISTS plugin_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    plugin_name TEXT NOT NULL DEFAULT 'clawforge',
    hook_point TEXT NOT NULL CHECK(hook_point IN ('bootstrap','ingest','pre_response')),
    intent_class TEXT DEFAULT '',
    sources_loaded INTEGER NOT NULL DEFAULT 0,
    sources_skipped INTEGER NOT NULL DEFAULT 0,
    tokens_saved INTEGER NOT NULL DEFAULT 0,
    context_window_pct REAL DEFAULT 0,
    timestamp INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_plugin_agent ON plugin_tracking(agent_name, timestamp);
"""),
    (7, """-- Migration 7: per-turn token tracking + extended history
CREATE TABLE IF NOT EXISTS token_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    identity_tokens INTEGER DEFAULT 0,
    skills_tokens INTEGER DEFAULT 0,
    memory_tokens INTEGER DEFAULT 0,
    tools_tokens INTEGER DEFAULT 0,
    guidance_tokens INTEGER DEFAULT 0,
    provider TEXT DEFAULT '',
    cost REAL DEFAULT 0,
    anomaly_score REAL,
    recorded_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_agent_ts ON token_logs(agent_name, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_token_ts ON token_logs(recorded_at);

CREATE TABLE IF NOT EXISTS token_budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL UNIQUE,
    max_daily_tokens INTEGER DEFAULT 0,
    max_turn_cost REAL DEFAULT 0,
    max_component_growth_pct REAL DEFAULT 0,
    anomaly_threshold_sigma REAL DEFAULT 3.0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS retention_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO retention_config (key, value) VALUES ('pulse_days', '7');
INSERT OR IGNORE INTO retention_config (key, value) VALUES ('error_days', '7');
INSERT OR IGNORE INTO retention_config (key, value) VALUES ('drift_days', '7');
INSERT OR IGNORE INTO retention_config (key, value) VALUES ('token_days', '7');
INSERT OR IGNORE INTO retention_config (key, value) VALUES ('l2_days', '7');
"""),
    (8, """-- Migration 8: instance_id for shared-view mode
-- SAFE & IDEMPOTENT (ref requirements-fidelity Trap 3: lifecycle safety,
-- ref system-design Lens 9: multi-instance safety):
-- ALTER TABLE ADD COLUMN is a no-op if the column already exists
-- (SQLite ignores duplicate ADD COLUMN gracefully).
ALTER TABLE pulse_log ADD COLUMN instance_id TEXT DEFAULT '';
"""),
]

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
    timestamp INTEGER NOT NULL,
    instance_id TEXT DEFAULT ''
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

-- Auth sessions (persisted — survive restart)
CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    email TEXT DEFAULT '',
    name TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    provider TEXT DEFAULT 'local',
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);

-- Dead letter queue for failed event ingestion
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    agent_id TEXT DEFAULT '',
    payload TEXT DEFAULT '{}',
    error TEXT NOT NULL,
    retries INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','retried','failed','resolved')),
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_dlq_status ON dead_letter_queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_dlq_retries ON dead_letter_queue(retries);

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

        # Check current version
        cur = conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
        row = cur.fetchone()
        current_version = int(row["value"]) if row else 1

        # Run pending migrations in order
        for target_version, migration_sql in MIGRATIONS:
            if current_version < target_version:
                try:
                    conn.executescript(migration_sql)
                    conn.execute(
                        "UPDATE _meta SET value=? WHERE key='schema_version'",
                        (str(target_version),),
                    )
                    conn.commit()
                    current_version = target_version
                except Exception as e:
                    logger.error(f"Migration {current_version}→{target_version} failed: {e}")
                    # Continue — next startup will retry
                    break

        # Ensure version is current
        if current_version < SCHEMA_VERSION:
            conn.execute(
                "UPDATE _meta SET value=? WHERE key='schema_version'",
                (str(SCHEMA_VERSION),),
            )
            conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def backup(self, dest_path: Optional[str | Path] = None) -> bool:
        """Create a backup of the database using SQLite's online backup API.

        Safe to call while the database is in use (WAL mode).
        Returns True on success.
        """
        import shutil
        if dest_path is None:
            backup_dir = self.db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            dest_path = backup_dir / f"pulse_{ts}.db"
        dest_path = Path(dest_path)
        try:
            src_conn = self._get_conn()
            dest_conn = sqlite3.connect(str(dest_path))
            src_conn.backup(dest_conn)
            dest_conn.close()
            logger.info(f"Database backed up to {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False

    def vacuum(self) -> bool:
        """Reclaim space and clean WAL. Run periodically."""
        try:
            conn = self._get_conn()
            conn.execute("VACUUM")
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"VACUUM failed: {e}")
            return False

    def purge_old_data(self, days: int = 90) -> dict:
        """Remove data older than N days. Returns counts of deleted rows."""
        conn = self._get_conn()
        cutoff = int(time.time()) - (days * 86400)
        counts = {}
        for table in ["pulse_log", "chisel_trims", "chisel_drift", "errors",
                      "restart_log", "telemetry_events"]:
            try:
                cur = conn.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))
                counts[table] = cur.rowcount
            except Exception:
                counts[table] = 0
        conn.commit()
        return counts

    # -- Pulse Log --

    def log_pulse(self, agent_name: str, status: str, latency_ms: float = 0,
                  error_message: str = "", agent_framework: str = "hermes",
                  instance_id: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO pulse_log (agent_name, agent_framework, status, latency_ms, error_message, timestamp, instance_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (agent_name, agent_framework, status, latency_ms, error_message,
             int(time.time()), instance_id or ""),
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

    def get_instances(self) -> list[dict]:
        """Get all unique dashboard instances that have written pulse data.

        Returns list of {instance_id, last_seen, agent_count} sorted by last_seen DESC.
        Only includes instances seen within the last 24 hours.
        """
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT instance_id, MAX(timestamp) as last_seen, "
                "COUNT(DISTINCT agent_name) as agent_count "
                "FROM pulse_log "
                "WHERE instance_id != '' AND timestamp > ? "
                "GROUP BY instance_id "
                "ORDER BY last_seen DESC",
                (int(time.time()) - 86400,),
            )
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            return []

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

    # -- Auth Sessions (persisted — survive restart) --

    def save_session(self, token: str, user_id: str, email: str, name: str,
                     avatar_url: str = "", provider: str = "local",
                     expires_at: float = 0, created_at: float = 0) -> None:
        """Persist an auth session to SQLite."""
        conn = self._get_conn()
        now = created_at or time.time()
        exp = expires_at or (now + 86400 * 7)
        conn.execute(
            "INSERT OR REPLACE INTO auth_sessions "
            "(token, user_id, email, name, avatar_url, provider, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (token, user_id, email, name, avatar_url, provider, exp, now),
        )
        conn.commit()

    def get_session(self, token: str) -> Optional[dict]:
        """Load a session by token. Returns None if expired or missing."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM auth_sessions WHERE token=?", (token,)
        )
        row = cur.fetchone()
        if not row:
            return None
        session = dict(row)
        if session["expires_at"] < time.time():
            # Expired — clean up
            self.delete_session(token)
            return None
        return session

    def delete_session(self, token: str) -> bool:
        """Delete a session. Returns True if a row was deleted."""
        conn = self._get_conn()
        cur = conn.execute("DELETE FROM auth_sessions WHERE token=?", (token,))
        conn.commit()
        return cur.rowcount > 0

    def purge_expired_sessions(self) -> int:
        """Delete expired sessions. Returns count removed."""
        conn = self._get_conn()
        now = time.time()
        cur = conn.execute(
            "DELETE FROM auth_sessions WHERE expires_at < ?", (now,)
        )
        conn.commit()
        return cur.rowcount

    # -- Dead Letter Queue (failed events) --

    def dlq_add(self, event_type: str, agent_id: str, payload: dict, error: str) -> int:
        """Add a failed event to the dead letter queue. Returns row id."""
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO dead_letter_queue "
            "(event_type, agent_id, payload, error, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_type, agent_id, json.dumps(payload), error, int(time.time())),
        )
        conn.commit()
        return cur.lastrowid or 0

    def dlq_get_pending(self, limit: int = 50) -> list[dict]:
        """Get pending DLQ entries for retry."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM dead_letter_queue "
            "WHERE status='pending' AND retries < max_retries "
            "ORDER BY created_at ASC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]

    def dlq_mark_retried(self, row_id: int) -> None:
        """Mark a DLQ entry as retried (increment retry count)."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE dead_letter_queue SET retries = retries + 1 WHERE id=?",
            (row_id,),
        )
        conn.commit()

    def dlq_mark_failed(self, row_id: int) -> None:
        """Mark a DLQ entry as permanently failed."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE dead_letter_queue SET status='failed', resolved_at=? WHERE id=?",
            (int(time.time()), row_id),
        )
        conn.commit()

    def dlq_mark_resolved(self, row_id: int) -> None:
        """Mark a DLQ entry as resolved."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE dead_letter_queue SET status='resolved', resolved_at=? WHERE id=?",
            (int(time.time()), row_id),
        )
        conn.commit()

    def dlq_stats(self) -> dict:
        """Get DLQ statistics."""
        conn = self._get_conn()
        pending = conn.execute(
            "SELECT COUNT(*) FROM dead_letter_queue WHERE status='pending'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM dead_letter_queue WHERE status='failed'"
        ).fetchone()[0]
        resolved = conn.execute(
            "SELECT COUNT(*) FROM dead_letter_queue WHERE status='resolved'"
        ).fetchone()[0]
        return {"pending": pending, "failed": failed, "resolved": resolved}

    def dlq_purge(self, older_than_days: int = 7) -> int:
        """Purge old DLQ entries. Returns count removed."""
        conn = self._get_conn()
        cutoff = int(time.time()) - (older_than_days * 86400)
        cur = conn.execute(
            "DELETE FROM dead_letter_queue WHERE created_at < ? AND status IN ('resolved','failed')",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount

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
                 tools: int, guidance: int, total: int, savings: float,
                 mode: str = "stdin") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO chisel_trims (agent_name, identity_tokens, skills_tokens, memory_tokens, "
            "tools_tokens, guidance_tokens, total_tokens, savings_ratio, mode, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_name, identity, skills, memory, tools, guidance, total, savings,
             mode, int(time.time())),
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
        existing = conn.execute(
            "SELECT framework FROM agent_configs WHERE agent_name=?",
            (name,)
        ).fetchone()

        if existing:
            existing_fw = existing["framework"]
            existing_parts = set(p.strip().lower() for p in existing_fw.split("+"))
            new_fw = framework.lower().strip()

            # If the incoming framework is itself a composite (e.g. "openclaw + hermes"),
            # check that ALL its parts are tracked — not just the full string
            new_parts = set(p.strip().lower() for p in new_fw.split("+"))
            if new_parts.issubset(existing_parts):
                return  # All parts already registered — no-op

            # Check if the full new_fw is a single part already tracked
            if new_fw in existing_parts:
                return  # Already registered — no-op

            # Merge: append only the missing parts to existing composite
            if new_fw not in ("custom", "agent", "service", "workflow"):
                missing_parts = " + ".join(p for p in new_parts if p not in existing_parts)
                if missing_parts:
                    composite = existing_fw + " + " + missing_parts
                    conn.execute(
                        "UPDATE agent_configs SET framework=? WHERE agent_name=?",
                        (composite, name),
                    )
                    conn.commit()
                return
            # New framework is a type classifier — skip, don't overwrite
            return

        conn.execute(
            "INSERT INTO agent_configs (agent_name, framework, health_check, is_active, last_seen) "
            "VALUES (?, ?, ?, 1, ?) "
            "ON CONFLICT(agent_name) DO UPDATE SET framework=excluded.framework, "
            "health_check=excluded.health_check, last_seen=excluded.last_seen",
            (name, framework, health_check, int(time.time())),
        )
        conn.commit()

    def get_agents(self) -> list[dict]:
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM agent_configs ORDER BY agent_name")
        return [dict(r) for r in cur.fetchall()]

    def remove_agents(self, names: list[str]) -> None:
        """Remove named agents and all their data from the database."""
        if not names:
            return
        conn = self._get_conn()
        placeholders = ",".join("?" for _ in names)
        conn.execute(f"DELETE FROM agent_configs WHERE agent_name IN ({placeholders})", names)
        conn.execute(f"DELETE FROM pulse_log WHERE agent_name IN ({placeholders})", names)
        conn.execute(f"DELETE FROM errors WHERE agent_name IN ({placeholders})", names)
        conn.commit()

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
        now = int(time.time())

        # Clear all auto-detected pathway data first to avoid duplication on re-scan
        conn.execute("DELETE FROM pathway_edges")
        conn.execute("DELETE FROM pathway_nodes WHERE source='auto'")
        count = 0

        # 1. Register known consumer nodes
        known_consumers = [("sean", "Sean", "consumer", "📖")]

        for nid, nname, ntype, _ in known_consumers:
            conn.execute(
                "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                "VALUES (?, ?, ?, 'auto', 50)",
                (nid, nname, ntype),
            )

        # 2. Register known platform nodes — and connect each to the consumer
        known_platforms = [("telegram", "Telegram", "platform", "📱"),
                           ("slack", "Slack", "platform", "💬"),
                           ("discord", "Discord", "platform", "🎮"),
                           ("whatsapp", "WhatsApp", "platform", "📱"),
                           ("bluebubbles", "BlueBubbles", "platform", "📱")]

        for nid, nname, ntype, _ in known_platforms:
            conn.execute(
                "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                "VALUES (?, ?, ?, 'auto', 50)",
                (nid, nname, ntype),
            )
            # Link platform → consumer so no node dangles
            conn.execute(
                "INSERT OR IGNORE INTO pathway_edges (source_id, target_id, status, mechanism, confidence, created_at) "
                "VALUES (?, 'sean', 'green', 'message delivery', 75, ?)",
                (nid, now),
            )
            count += 1

        # 3. Register signal router
        known_routers = [("signal-router", "Signal Router", "router", "🔀")]
        for nid, nname, ntype, _ in known_routers:
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

        # 5. Scan cron jobs from filesystem (configurable path for framework-agnostic support)
        import os
        cron_dir_env = os.environ.get("OBSERVECO_PATHWAY_CRON_DIR", "")
        hermes_cron_dir = Path(cron_dir_env) if cron_dir_env else (Path.home() / ".hermes" / "cron")
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
                            target_nid = "signal-router"  # local cron output feeds signal pipeline
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

        # 6. Detect agent-to-agent routing from signal inboxes (configurable path)
        import os
        signals_env = os.environ.get("OBSERVECO_PATHWAY_SIGNALS_DIR", "")
        signal_base = Path(signals_env) if signals_env else (Path.home() / ".hermes" / "signals")
        if signal_base.exists():
            for _agent_node_dir in signal_base.iterdir():
                if not _agent_node_dir.is_dir():
                    continue
                agent_name = _agent_node_dir.name
                inbox_dir = _agent_node_dir / "inbox"
                if not inbox_dir.exists():
                    continue
                # Read all signals in this inbox to find who sent them
                try:
                    for sig_file in sorted(inbox_dir.iterdir()):
                        if not sig_file.name.endswith(".json"):
                            continue
                        try:
                            sig = json.loads(sig_file.read_text())
                            sig_from = sig.get("from", "")
                            sig_to = sig.get("to", agent_name)
                            if not sig_from or sig_from == agent_name:
                                continue
                            # Source: sender (map to agent- prefix or use as-is)
                            src_nid = f"agent-{sig_from}"
                            tgt_nid = f"agent-{sig_to}"
                            # Ensure both nodes exist
                            conn.execute(
                                "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                                "VALUES (?, ?, 'agent', 'auto', 75)",
                                (src_nid, sig_from),
                            )
                            conn.execute(
                                "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                                "VALUES (?, ?, 'agent', 'auto', 75)",
                                (tgt_nid, sig_to),
                            )
                            # Create edge
                            sig_type = sig.get("type", "signal")
                            mechanism = f"signal_{sig_type}"
                            conn.execute(
                                "INSERT OR REPLACE INTO pathway_edges (source_id, target_id, status, "
                                "mechanism, confidence, scenario, last_verified, created_at) "
                                "VALUES (?, ?, 'green', ?, 75, '', ?, ?)",
                                (src_nid, tgt_nid, mechanism, now, now),
                            )
                            count += 1
                            # Only process first few signals per agent to avoid duplicates
                            if count > 200:
                                break
                        except (json.JSONDecodeError, Exception):
                            continue
                        if count > 200:
                            break
                except Exception:
                    continue

        # 7. Detect daemons and watchers — long-running background processes
        # Sources: restart_log in pulse.db, launchd plists, running processes
        try:
            # 7a. Restart log shows which agents had daemon processes
            restart_rows = conn.execute(
                "SELECT DISTINCT agent_name FROM restart_log ORDER BY agent_name"
            ).fetchall()
            for row in restart_rows:
                aname = row["agent_name"]
                nid = f"agent-{aname}"
                conn.execute(
                    "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                    "VALUES (?, ?, 'agent', 'auto', 75)",
                    (nid, aname),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO pathway_edges (source_id, target_id, status, "
                    "mechanism, confidence, created_at) "
                    "VALUES (?, ?, 'green', 'daemon_restart_log', 50, ?)",
                    (nid, "signal-router", now),
                )
                count += 1
        except Exception:
            pass

        # 7b. Detect running watch daemon process
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "observeco.*watch"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                nid = "daemon-watch"
                conn.execute(
                    "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                    "VALUES (?, 'ObserveCo Watch Daemon', 'daemon', 'auto', 75)",
                    (nid,),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO pathway_edges (source_id, target_id, status, "
                    "mechanism, confidence, created_at) "
                    "VALUES (?, ?, 'green', 'daemon_active', 75, ?)",
                    (nid, "signal-router", now),
                )
                count += 1
        except Exception:
            pass

        # 7c. Detect launchd-managed agents (macOS)
        try:
            launchd_dir = Path.home() / "Library" / "LaunchAgents"
            if launchd_dir.exists():
                for plist in launchd_dir.glob("ai.hermes.*.plist"):
                    aname = plist.stem.replace("ai.hermes.", "")
                    nid = f"agent-{aname}"
                    conn.execute(
                        "INSERT OR IGNORE INTO pathway_nodes (id, name, type, source, confidence) "
                        "VALUES (?, ?, 'agent', 'auto', 75)",
                        (nid, aname),
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO pathway_edges (source_id, target_id, status, "
                        "mechanism, confidence, created_at) "
                        "VALUES (?, ?, 'green', 'launchd_daemon', 50, ?)",
                        (nid, "signal-router", now),
                    )
                    count += 1
        except Exception:
            pass

        # 8. Detect ClawForge hub routing for OpenClaw agents
        try:
            oc_agents = [a for a in agents if "openclaw" in a.get("framework", "").lower()]
            for a in oc_agents:
                aname = a["agent_name"]
                nid = f"agent-{aname}"
                # Look for AGENTS.md in the OpenClaw agent's profile directory
                profiles_dir = Path.home() / ".hermes" / "profiles"
                agent_dir = profiles_dir / aname
                if agent_dir.exists():
                    # AGENTS.md lists peer agents in an OpenClaw cluster
                    agents_file = agent_dir / "AGENTS.md"
                    if agents_file.exists():
                        content = agents_file.read_text(encoding="utf-8", errors="replace")
                        for other in agents:
                            o_name = other["agent_name"]
                            if o_name != aname and o_name.lower() in content.lower():
                                tgt_nid = f"agent-{o_name}"
                                conn.execute(
                                    "INSERT OR IGNORE INTO pathway_edges (source_id, target_id, status, "
                                    "mechanism, confidence, created_at) "
                                    "VALUES (?, ?, 'green', 'clawforge_hub', 50, ?)",
                                    (nid, tgt_nid, now),
                                )
                                count += 1
                    # HEARTBEAT.md or cron dir shows internal scheduling
                    cron_dir = agent_dir / "cron"
                    if cron_dir.exists():
                        conn.execute(
                            "INSERT OR IGNORE INTO pathway_edges (source_id, target_id, status, "
                            "mechanism, confidence, created_at) "
                            "VALUES (?, ?, 'green', 'clawforge_scheduler', 50, ?)",
                            (nid, "signal-router", now),
                        )
                        count += 1
        except Exception:
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

    # --- L2 Trending ---
    def log_l2_trend(self, agent_name: str, trend_type: str, signal_label: str,
                     severity: str = "warning", metric_value: float = 0,
                     threshold: float = 0, auto_action: str = "none") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO l2_trending (agent_name, trend_type, signal_label, severity, "
            "metric_value, threshold, auto_action, timestamp) VALUES (?,?,?,?,?,?,?,?)",
            (agent_name, trend_type, signal_label, severity, metric_value, threshold,
             auto_action, int(time.time()))
        )
        conn.commit()

    def get_l2_trends(self, agent_name: str = "", limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            rows = conn.execute(
                "SELECT * FROM l2_trending WHERE agent_name=? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM l2_trending ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def resolve_l2_trend(self, trend_id: int, action: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE l2_trending SET resolved=1, resolved_action=?, resolved_at=? WHERE id=?",
            (action, int(time.time()), trend_id)
        )
        conn.commit()

    # --- Push Alerts ---
    def add_alert_subscription(self, channel: str, target: str,
                                event_types: str = "all") -> dict:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO alert_subscriptions (channel, target, event_types, created_at) VALUES (?,?,?,?)",
            (channel, target, event_types, int(time.time()))
        )
        conn.commit()
        return {"id": cur.lastrowid, "channel": channel, "target": target}

    def get_alert_subscriptions(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM alert_subscriptions ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_alert_subscription(self, sub_id: int) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM alert_subscriptions WHERE id=?", (sub_id,))
        conn.commit()

    def log_alert_delivery(self, channel: str, target: str, event_type: str,
                           message: str, delivered: bool = True, error: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO alert_log (channel, target, event_type, message, delivered, "
            "delivery_error, created_at) VALUES (?,?,?,?,?,?,?)",
            (channel, target, event_type, message, int(delivered), error, int(time.time()))
        )
        conn.commit()

    def get_alert_log(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM alert_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Plugin Tracking ---
    def log_plugin_tracking(self, agent_name: str, plugin_name: str = "clawforge",
                            hook_point: str = "ingest", intent_class: str = "",
                            sources_loaded: int = 0, sources_skipped: int = 0,
                            tokens_saved: int = 0, context_window_pct: float = 0) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO plugin_tracking (agent_name, plugin_name, hook_point, intent_class, "
            "sources_loaded, sources_skipped, tokens_saved, context_window_pct, timestamp) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (agent_name, plugin_name, hook_point, intent_class, sources_loaded,
             sources_skipped, tokens_saved, context_window_pct, int(time.time()))
        )
        conn.commit()

    def get_plugin_tracking(self, agent_name: str = "", limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            rows = conn.execute(
                "SELECT * FROM plugin_tracking WHERE agent_name=? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM plugin_tracking ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_plugin_stats(self, agent_name: str = "") -> dict:
        conn = self._get_conn()
        if agent_name:
            row = conn.execute(
                "SELECT COUNT(*) as turns, COALESCE(SUM(sources_loaded),0) as loaded, "
                "COALESCE(SUM(sources_skipped),0) as skipped, COALESCE(SUM(tokens_saved),0) as saved "
                "FROM plugin_tracking WHERE agent_name=?", (agent_name,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as turns, COALESCE(SUM(sources_loaded),0) as loaded, "
                "COALESCE(SUM(sources_skipped),0) as skipped, COALESCE(SUM(tokens_saved),0) as saved "
                "FROM plugin_tracking", ()
            ).fetchone()
        if not row:
            return {"turns": 0, "loaded": 0, "skipped": 0, "saved": 0}
        d = dict(row)
        total = d["loaded"] + d["skipped"]
        d["avg_reduction_pct"] = round((d["skipped"] / max(total, 1)) * 100, 1)
        return d

    # --- Token Tracking (#14) ---
    def log_token_turn(self, agent_name: str, turn_id: str, total_tokens: int,
                       identity_tokens: int = 0, skills_tokens: int = 0,
                       memory_tokens: int = 0, tools_tokens: int = 0,
                       guidance_tokens: int = 0, provider: str = "",
                       cost: float = 0, anomaly_score: float | None = None) -> dict:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO token_logs (agent_name, turn_id, total_tokens, identity_tokens, "
            "skills_tokens, memory_tokens, tools_tokens, guidance_tokens, "
            "provider, cost, anomaly_score, recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (agent_name, turn_id, total_tokens, identity_tokens, skills_tokens,
             memory_tokens, tools_tokens, guidance_tokens, provider, cost,
             anomaly_score, int(time.time()))
        )
        conn.commit()
        return {"id": cur.lastrowid}

    def get_token_turns(self, agent_name: str = "", limit: int = 100,
                        since: int = 0) -> list[dict]:
        conn = self._get_conn()
        if agent_name and since:
            rows = conn.execute(
                "SELECT * FROM token_logs WHERE agent_name=? AND recorded_at>=? ORDER BY recorded_at DESC LIMIT ?",
                (agent_name, since, limit)
            ).fetchall()
        elif agent_name:
            rows = conn.execute(
                "SELECT * FROM token_logs WHERE agent_name=? ORDER BY recorded_at DESC LIMIT ?",
                (agent_name, limit)
            ).fetchall()
        elif since:
            rows = conn.execute(
                "SELECT * FROM token_logs WHERE recorded_at>=? ORDER BY recorded_at DESC LIMIT ?",
                (since, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM token_logs ORDER BY recorded_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_token_summary(self, agent_name: str = "", since: int = 0) -> dict:
        conn = self._get_conn()
        since_clause = "AND recorded_at>=?" if since else ""
        params = (agent_name,) if agent_name and not since else (agent_name, since) if agent_name and since else (since,) if since else ()
        where = "WHERE agent_name=?" if agent_name else ""

        row = conn.execute(
            f"SELECT COUNT(*) as turns, COALESCE(SUM(total_tokens),0) as total_tokens, "
            f"COALESCE(SUM(cost),0) as total_cost, "
            f"COALESCE(AVG(total_tokens),0) as avg_tokens, "
            f"COALESCE(MAX(total_tokens),0) as max_tokens "
            f"FROM token_logs {where} {since_clause}", params
        ).fetchone()
        if not row:
            return {"turns": 0, "total_tokens": 0, "total_cost": 0, "avg_tokens": 0, "max_tokens": 0}
        return dict(row)

    def get_token_trends(self, agent_name: str = "", days: int = 7) -> dict:
        conn = self._get_conn()
        now = int(time.time())
        since = now - days * 86400
        if agent_name:
            rows = conn.execute(
                "SELECT skills_tokens, memory_tokens, tools_tokens, guidance_tokens, "
                "identity_tokens, total_tokens, recorded_at "
                "FROM token_logs WHERE agent_name=? AND recorded_at>=? ORDER BY recorded_at",
                (agent_name, since)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT agent_name, skills_tokens, memory_tokens, tools_tokens, guidance_tokens, "
                "identity_tokens, total_tokens, recorded_at "
                "FROM token_logs WHERE recorded_at>=? ORDER BY recorded_at",
                (since,)
            ).fetchall()
        if not rows:
            return {"components": {}, "total_tokens": 0, "avg_per_turn": 0, "days": days}
        comps = {"skills": 0, "memory": 0, "tools": 0, "guidance": 0, "identity": 0}
        total = 0
        for r in rows:
            rd = dict(r)
            for c in comps:
                comps[c] += rd.get(f"{c}_tokens", 0) or 0
            total += rd.get("total_tokens", 0) or 0
        avg = total / max(len(rows), 1)
        return {"components": comps, "total_tokens": total,
                "avg_per_turn": round(avg, 1), "turns": len(rows), "days": days}

    def set_token_budget(self, agent_name: str, max_daily_tokens: int = 0,
                          max_turn_cost: float = 0,
                          max_component_growth_pct: float = 0,
                          anomaly_threshold_sigma: float = 3.0) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO token_budgets (agent_name, max_daily_tokens, max_turn_cost, "
            "max_component_growth_pct, anomaly_threshold_sigma, created_at) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(agent_name) DO UPDATE SET "
            "max_daily_tokens=excluded.max_daily_tokens, max_turn_cost=excluded.max_turn_cost, "
            "max_component_growth_pct=excluded.max_component_growth_pct, "
            "anomaly_threshold_sigma=excluded.anomaly_threshold_sigma",
            (agent_name, max_daily_tokens, max_turn_cost, max_component_growth_pct,
             anomaly_threshold_sigma, int(time.time()))
        )
        conn.commit()

    def get_token_budgets(self, agent_name: str = "") -> list[dict]:
        conn = self._get_conn()
        if agent_name:
            rows = conn.execute("SELECT * FROM token_budgets WHERE agent_name=?", (agent_name,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM token_budgets ORDER BY agent_name").fetchall()
        return [dict(r) for r in rows]

    # --- Retention / Extended History (#18) ---
    def get_retention_config(self) -> dict:
        conn = self._get_conn()
        rows = conn.execute("SELECT key, value FROM retention_config").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def set_retention_days(self, data_type: str, days: str) -> None:
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO retention_config (key, value) VALUES (?, ?)",
                     (f"{data_type}_days", days))
        conn.commit()

    def prune_old_data(self, data_type: str, days: int) -> int:
        """Delete rows older than `days` for a data type. Returns rows deleted."""
        conn = self._get_conn()
        cutoff = int(time.time()) - days * 86400
        table_map = {
            "pulse": "pulse_log",
            "error": "errors",
            "drift": "chisel_drift",
            "token": "token_logs",
            "l2": "l2_trending",
        }
        table = table_map.get(data_type)
        if not table:
            return 0
        col = {"pulse_log": "timestamp", "errors": "timestamp",
               "chisel_drift": "timestamp", "token_logs": "recorded_at",
               "l2_trending": "timestamp"}.get(table, "timestamp")
        cur = conn.execute(f"DELETE FROM {table} WHERE {col} < ?", (cutoff,))
        conn.commit()
        return cur.rowcount

    def set_pruning_schedule(self, enabled: bool, hour: int = 3) -> None:
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO retention_config (key, value) VALUES (?, ?)",
                     ("pruning_enabled", str(int(enabled))))
        conn.execute("INSERT OR REPLACE INTO retention_config (key, value) VALUES (?, ?)",
                     ("pruning_hour", str(hour)))
        conn.commit()

    # --- L2 Baseline Engine (#18 Phase 2) ---
    def compute_l2_baselines(self, agent_name: str = "", days: int = 7) -> dict:
        """Compute rolling L2 baselines from historical data."""
        conn = self._get_conn()
        now = int(time.time())
        since = now - days * 86400

        if agent_name:
            pulses = conn.execute(
                "SELECT latency_ms, timestamp FROM pulse_log WHERE agent_name=? AND timestamp>=? AND latency_ms>0 ORDER BY timestamp",
                (agent_name, since)
            ).fetchall()
            tokens = conn.execute(
                "SELECT total_tokens, recorded_at FROM token_logs WHERE agent_name=? AND recorded_at>=? ORDER BY recorded_at",
                (agent_name, since)
            ).fetchall()
            errors = conn.execute(
                "SELECT error_message, timestamp FROM errors WHERE agent_name=? AND timestamp>=? ORDER BY timestamp",
                (agent_name, since)
            ).fetchall()
        else:
            pulses = conn.execute(
                "SELECT agent_name, latency_ms, timestamp FROM pulse_log WHERE timestamp>=? AND latency_ms>0 ORDER BY timestamp",
                (since,)
            ).fetchall()
            tokens = conn.execute(
                "SELECT agent_name, total_tokens, recorded_at FROM token_logs WHERE recorded_at>=? ORDER BY recorded_at",
                (since,)
            ).fetchall()
            errors = conn.execute(
                "SELECT agent_name, error_message, timestamp FROM errors WHERE timestamp>=? ORDER BY timestamp",
                (since,)
            ).fetchall()

        # Compute baselines
        p95_latency = 0
        if pulses:
            latencies = sorted(p["latency_ms"] for p in pulses)
            p95_latency = latencies[int(len(latencies) * 0.95)] if len(latencies) > 10 else (latencies[-1] if latencies else 0)

        rss_baseline = p95_latency  # RSS approximated by latency trend
        avg_tokens = round(sum(t["total_tokens"] for t in tokens) / max(len(tokens), 1), 1) if tokens else 0
        error_rate = round(len(errors) / max(days, 1), 2)

        upstream_errors = sum(1 for e in errors if
                              "refused" in (e.get("error_message", "") or "").lower()
                              or "timeout" in (e.get("error_message", "") or "").lower())

        return {
            "rss_baseline_ms": rss_baseline,
            "p95_latency_ms": p95_latency,
            "avg_token_per_turn": avg_tokens,
            "total_turns": len(tokens),
            "error_rate_per_day": error_rate,
            "upstream_error_count": upstream_errors,
            "sample_days": days,
        }
