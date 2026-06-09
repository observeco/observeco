"""ObserveCo — Chisel Optimiser data layer & DB migration.

Adds:
1. mode column to chisel_trims
2. compress_log table for tracking all compression operations
3. skill_usage table for per-turn skill tracking (Token Optimiser)
4. guidance_fire table for guidance rule activation tracking
5. turn_log table for per-turn token tracking
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from observeco.db import Database

MIGRATIONS = [
    # 1. Add mode column to chisel_trims
    "ALTER TABLE chisel_trims ADD COLUMN mode TEXT DEFAULT 'stdin'",
    # 2. compress_log
    """CREATE TABLE IF NOT EXISTS compress_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        mode TEXT NOT NULL,
        before_tokens INTEGER NOT NULL,
        after_tokens INTEGER NOT NULL,
        savings INTEGER NOT NULL,
        savings_pct REAL NOT NULL,
        file_path TEXT,
        backup_path TEXT,
        triggered_by TEXT DEFAULT 'manual',
        timestamp INTEGER NOT NULL
    )""",
    # 3. skill_usage
    """CREATE TABLE IF NOT EXISTS skill_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        triggered INTEGER NOT NULL DEFAULT 0,
        turn_count INTEGER NOT NULL DEFAULT 1,
        last_triggered INTEGER,
        timestamp INTEGER NOT NULL
    )""",
    # 4. guidance_fire
    """CREATE TABLE IF NOT EXISTS guidance_fire (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        rule_hash TEXT NOT NULL,
        rule_text TEXT NOT NULL,
        fire_count INTEGER NOT NULL DEFAULT 1,
        last_fired INTEGER,
        timestamp INTEGER NOT NULL
    )""",
    # 5. turn_log
    """CREATE TABLE IF NOT EXISTS turn_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        total_tokens INTEGER NOT NULL DEFAULT 0,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        skills_used TEXT DEFAULT '[]',
        guidance_hit TEXT DEFAULT '[]',
        timestamp INTEGER NOT NULL
    )""",
    # 6. Indexes
    "CREATE INDEX IF NOT EXISTS idx_compress_log_agent ON compress_log(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_compress_log_ts ON compress_log(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_skill_usage_agent ON skill_usage(agent_name, skill_name)",
    "CREATE INDEX IF NOT EXISTS idx_guidance_fire_agent ON guidance_fire(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_turn_log_agent ON turn_log(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_turn_log_ts ON turn_log(timestamp)",
]

def run_migrations():
    db = Database()
    conn = db._get_conn()
    applied = 0
    errors = []
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
            applied += 1
        except Exception as e:
            # "duplicate column" is expected for ALTER TABLE ADD COLUMN on already-migrated DBs
            if "duplicate column" not in str(e).lower():
                errors.append(f"{sql[:60]}...: {e}")
    conn.commit()
    return applied, errors

if __name__ == "__main__":
    applied, errors = run_migrations()
    print(f"Applied: {applied} migrations")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
    else:
        print("All migrations clean!")
