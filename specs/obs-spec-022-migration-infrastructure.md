# obs-spec-022: Migration Infrastructure Hardening

**Spec ID:** obs-spec-022
**Status:** DRAFT
**Author:** Pragma
**Date:** 2026-06-11
**Phase:** 2 (Plumbing Remediation)
**Priority:** P0
**Owner:** Pragma
**Standard:** GS-019 (Data & Observability Continuity)
**Master Plan:** §4.2, Tasks 2.23-2.24

---

## 1. Problem

The ObserveCo migration infrastructure (`db.py:_init_db()`) has 4 HIGH-severity gaps identified by playbook audit:

1. **No pre-migration backup** — `db.backup()` exists but is never called
2. **No downgrade protection** — version force-set on mismatch, no rollback
3. **Recreate-table data-loss window** — migrations 11, 15 can lose data on mid-migration crash
4. **Bootstrap masks data loss** — `_SCHEMA_SQL` re-runs on every startup, can create empty tables after drop

These violate GS-019 §Principle 2 (Backup Before Destructive) and §Principle 3 (Verify After Migration).

**Sean's direction:** "I would like the principles of ensuring data and observability continuity to be a key tenet of how we roll out products, especially critical since we are in observability space."

---

## 2. Current Architecture

### 2.1 Migration Runner (`db.py:612-657`)

```python
def _init_db(self) -> None:
    conn = self._get_conn()
    conn.executescript(_SCHEMA_SQL)  # Creates all tables (IF NOT EXISTS)
    
    # Check current version
    cur = conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
    current_version = int(row["value"]) if row else 1
    
    # Run pending migrations
    for target_version, migration_sql in MIGRATIONS:
        if current_version < target_version:
            try:
                conn.executescript(migration_sql)
                conn.execute("INSERT OR REPLACE INTO _meta ...")
                conn.commit()
                current_version = target_version
            except Exception as e:
                if "duplicate column name" in emsg:
                    # Treat as success
                    ...
                else:
                    break  # Stop on failure
    
    # Force version to current
    if current_version < SCHEMA_VERSION:
        conn.execute("INSERT OR REPLACE INTO _meta ...")
        conn.commit()
```

### 2.2 The Dual-Definition Problem

`_SCHEMA_SQL` (line 352) creates all tables with `IF NOT EXISTS`. Migrations 2-5 also create the same tables. On fresh install:
1. `_SCHEMA_SQL` creates all tables
2. Migrations 2-5 run but are no-ops (tables already exist)
3. 10 tables exist only in `_SCHEMA_SQL` with no migration provenance

This means the migration chain is not the source of truth — `_SCHEMA_SQL` is. The migration system is effectively decorative for tables defined before Migration 6.

### 2.3 The Recreate-Table Pattern (Migrations 11, 15)

```sql
-- Migration 11: Recreate pathway_nodes
CREATE TABLE pathway_nodes_v11 (...);
INSERT OR IGNORE INTO pathway_nodes_v11 SELECT ... FROM pathway_nodes;
DROP TABLE pathway_nodes;           -- ← DATA AT RISK
ALTER TABLE pathway_nodes_v11 RENAME TO pathway_nodes;
```

If crash occurs between `DROP` and `RENAME`, data is stranded in `_v11` table.

---

## 3. Solution: 6 Fixes

### Fix 1: Wire `db.backup()` Before Migrations

**File:** `db.py:_init_db()`
**Change:** Add backup call ONLY when there are pending migrations (not on every init)

```python
def _init_db(self) -> None:
    conn = self._get_conn()
    
    # Check current version BEFORE schema run
    cur = conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
    row = cur.fetchone()
    current_version = int(row["value"]) if row else 1
    
    # Check if any migrations are pending
    has_pending = any(current_version < tv for tv, _ in MIGRATIONS)
    
    # GS-019 §Principle 2: Backup ONLY before destructive migrations
    if has_pending and self._has_data(conn):
        self.backup()
    
    # Run full schema (IF NOT EXISTS makes it idempotent)
    conn.executescript(_SCHEMA_SQL)
    
    # ... rest of _init_db
```

**CRITICAL:** Backup must NOT run on every Database() instantiation. It must only run when:
1. There are pending migrations (schema version < target)
2. The database has user data

This prevents backup storms from multiple processes creating Database() instances.

**Helper method:**
```python
def _has_data(self, conn) -> bool:
    """Check if database has user data (not just schema)."""
    try:
        for table in ["pulse_log", "compress_log", "heal_events", "token_logs"]:
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            if cur.fetchone()[0] > 0:
                return True
    except Exception:
        pass
    return False
```

**Backup Rotation Policy:**
- Keep maximum 5 backups (configurable via `BACKUP_MAX_COUNT`)
- Delete oldest backups when limit exceeded
- Cooldown: minimum 4 hours between backups (prevent rapid backup storms)

```python
BACKUP_MAX_COUNT = 5
BACKUP_COOLDOWN_HOURS = 4

def backup(self, dest_path=None) -> bool:
    """Create backup with rotation and cooldown."""
    backup_dir = self.db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Cooldown check
    last_backup_time = self._get_last_backup_time(backup_dir)
    if last_backup_time and (time.time() - last_backup_time) < BACKUP_COOLDOWN_HOURS * 3600:
        logger.debug("Backup skipped: cooldown active")
        return False
    
    # Create backup
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest_path = backup_dir / f"pulse_{ts}.db"
    # ... existing backup logic ...
    
    # Rotation: delete old backups
    self._rotate_backups(backup_dir)
    return True

def _rotate_backups(self, backup_dir: Path) -> None:
    """Keep only last N backups."""
    backups = sorted(backup_dir.glob("pulse_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > BACKUP_MAX_COUNT:
        oldest = backups.pop(0)
        oldest.unlink()
        logger.info(f"Rotated old backup: {oldest.name}")
```

### Fix 2: Pre/Post Migration Row Counts

**File:** `db.py:_init_db()`
**Change:** Record row counts before migration, verify after

```python
def _init_db(self) -> None:
    conn = self._get_conn()
    
    # ... backup ...
    
    # GS-019 §Principle 3: Record pre-migration state
    pre_counts = self._snapshot_row_counts(conn)
    
    # Run migrations
    for target_version, migration_sql in MIGRATIONS:
        # ... existing logic ...
    
    # GS-019 §Principle 3: Verify post-migration state
    post_counts = self._snapshot_row_counts(conn)
    self._verify_migration_integrity(pre_counts, post_counts)
```

**Helper methods:**
```python
def _snapshot_row_counts(self, conn) -> dict:
    """Record row counts for all user tables."""
    counts = {}
    for table in ["pulse_log", "compress_log", "heal_events", "token_logs",
                   "pathway_nodes", "pathway_edges", "errors", "chisel_drift"]:
        try:
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
        except Exception:
            counts[table] = -1  # Table doesn't exist yet
    return counts

def _verify_migration_integrity(self, pre: dict, post: dict) -> None:
    """Verify row counts didn't drop unexpectedly."""
    for table, pre_count in pre.items():
        if pre_count <= 0:
            continue  # Table didn't exist or was empty
        post_count = post.get(table, -1)
        if post_count == -1:
            logger.error(f"GS-019 VIOLATION: {table} missing after migration (had {pre_count} rows)")
        elif post_count < pre_count * 0.9:  # >10% drop is suspicious
            logger.warning(f"GS-019 WARNING: {table} row count dropped: {pre_count} → {post_count}")
```

### Fix 3: Recovery Check for Recreate-Table Migrations

**File:** `db.py:_init_db()`
**Change:** Before migration loop, check for stranded `_v11` tables

```python
def _init_db(self) -> None:
    conn = self._get_conn()
    
    # GS-019 §Recovery: Check for stranded migration tables
    self._recover_stranded_tables(conn)
    
    # ... rest of _init_db

def _recover_stranded_tables(self, conn) -> None:
    """Recover from partial recreate-table migration failures."""
    recovery_map = {
        "pathway_nodes_v11": "pathway_nodes",
        "alert_subscriptions_v15": "alert_subscriptions",
    }
    for temp_table, target_table in recovery_map.items():
        try:
            temp_exists = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (temp_table,)
            ).fetchone()[0] > 0
            target_exists = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (target_table,)
            ).fetchone()[0] > 0
            
            if temp_exists and not target_exists:
                logger.warning(f"GS-019 RECOVERY: Renaming {temp_table} → {target_table}")
                conn.execute(f"ALTER TABLE {temp_table} RENAME TO {target_table}")
                conn.commit()
        except Exception as e:
            logger.error(f"GS-019 RECOVERY FAILED: {temp_table}: {e}")
```

### Fix 4: Downgrade Guard

**File:** `db.py:_init_db()`
**Change:** Don't force-set version if current > SCHEMA_VERSION

```python
# BEFORE (dangerous):
if current_version < SCHEMA_VERSION:
    conn.execute("INSERT OR REPLACE INTO _meta ...")
    conn.commit()

# AFTER (safe):
if current_version < SCHEMA_VERSION:
    conn.execute("INSERT OR REPLACE INTO _meta ...")
    conn.commit()
elif current_version > SCHEMA_VERSION:
    # GS-019 §Downgrade: Log warning, don't force-set
    logger.warning(
        f"GS-019: Database version ({current_version}) > code version "
        f"({SCHEMA_VERSION}). Possible downgrade. Not modifying version."
    )
```

### Fix 5: `observeco doctor` Data Health Check

**File:** `doctor/diagnostics.py`
**Change:** Add data continuity checks

```python
def check_data_health(db) -> list:
    """GS-019: Data continuity health checks."""
    findings = []
    
    # 1. Schema version check
    meta_version = db.get_meta("schema_version")
    if meta_version and int(meta_version) < SCHEMA_VERSION:
        findings.append({
            "severity": "CRITICAL",
            "check": "schema_version",
            "detail": f"Database version {meta_version} < expected {SCHEMA_VERSION}. Pending migrations."
        })
    
    # 2. Backup recency
    backup_dir = db.db_path.parent / "backups"
    if backup_dir.exists():
        backups = sorted(backup_dir.glob("pulse_*.db"))
        if backups:
            last_backup_age_days = (time.time() - backups[-1].stat().st_mtime) / 86400
            if last_backup_age_days > 7:
                findings.append({
                    "severity": "WARN",
                    "check": "backup_recency",
                    "detail": f"Last backup was {last_backup_age_days:.0f} days ago"
                })
        else:
            findings.append({
                "severity": "WARN",
                "check": "backup_exists",
                "detail": "No backups found"
            })
    
    # 3. Stranded migration tables
    conn = db._get_conn()
    for temp in ["pathway_nodes_v11", "alert_subscriptions_v15"]:
        exists = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (temp,)
        ).fetchone()[0] > 0
        if exists:
            findings.append({
                "severity": "CRITICAL",
                "check": "stranded_table",
                "detail": f"Table {temp} exists — partial migration not completed"
            })
    
    return findings
```

### Fix 6: Backup Before Retention Sweeps

**File:** `db.py:purge_old_data()`, `db.py:prune_old_data()`
**Change:** Add backup call before large deletions

```python
def purge_old_data(self, days: int = 90) -> dict:
    """Remove data older than N days. GS-019: backup if deleting >1000 rows."""
    conn = self._get_conn()
    cutoff = int(time.time()) - (days * 86400)
    
    # GS-019: Check if significant deletion is about to happen
    total_pending = sum(
        conn.execute(f"SELECT COUNT(*) FROM {table} WHERE timestamp < ?", (cutoff,)).fetchone()[0]
        for table in ["pulse_log", "chisel_trims", "chisel_drift", "errors",
                      "restart_log", "telemetry_events"]
    )
    if total_pending > 1000:
        self.backup()  # GS-019 §Principle 2
    
    # ... existing deletion logic ...
```

### Fix 7: Restore Mechanism + Auto-Restore on Failure

**Problem:** Backup files exist (`~/.observeco/backups/pulse_*.db`) but there's no way to restore from them. When migration fails, the DB is left in a partial state with no automatic rollback. User is never notified.

**Files:** `db.py`, `doctor/cli.py`, `dashboard/server.py`

#### 7.1 New Method: `db.restore(backup_path=None)`

```python
def restore(self, backup_path: Optional[str | Path] = None) -> dict:
    """Restore database from backup.
    
    If no path given, restores from most recent backup.
    GS-019: Creates a backup of current state before restoring.
    
    Returns: {"status": "restored", "from": str, "rows": int} or error dict.
    """
    backup_dir = self.db_path.parent / "backups"
    
    if backup_path is None:
        # Find most recent backup
        backups = sorted(backup_dir.glob("pulse_*.db"), key=lambda p: p.stat().st_mtime)
        if not backups:
            return {"status": "error", "message": "No backups found"}
        backup_path = backups[-1]
    else:
        backup_path = Path(backup_path)
    
    if not backup_path.exists():
        return {"status": "error", "message": f"Backup not found: {backup_path}"}
    
    # Validate backup is a valid SQLite database
    try:
        import sqlite3
        test_conn = sqlite3.connect(str(backup_path))
        test_conn.execute("SELECT COUNT(*) FROM sqlite_master")
        test_conn.close()
    except Exception as e:
        return {"status": "error", "message": f"Backup is corrupted: {e}"}
    
    # GS-019: Backup current state before restoring
    self.backup(dest_path=self.db_path.parent / "backups" / 
                f"pulse_pre_restore_{int(time.time())}.db")
    
    # Close current connection
    self.close()
    
    # Replace current DB with backup
    import shutil
    shutil.copy2(str(backup_path), str(self.db_path))
    
    # Reopen connection
    self._conn = None
    conn = self._get_conn()
    
    # Count rows to verify
    row_count = 0
    for table in ["pulse_log", "compress_log", "heal_events", "token_logs"]:
        try:
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            row_count += cur.fetchone()[0]
        except Exception:
            pass
    
    logger.info(f"GS-019: Restored from {backup_path.name} — {row_count} rows recovered")
    return {"status": "restored", "from": backup_path.name, "rows": row_count}
```

#### 7.2 Auto-Restore on Migration Failure

**File:** `db.py:_init_db()`

```python
def _init_db(self) -> None:
    conn = self._get_conn()
    
    # ... existing: check version, backup, run migrations ...
    
    for target_version, migration_sql in MIGRATIONS:
        if current_version < target_version:
            try:
                conn.executescript(migration_sql)
                # ... existing success logic ...
            except Exception as e:
                emsg = str(e)
                if "duplicate column name" in emsg:
                    # ... existing idempotent logic ...
                else:
                    logger.error(f"Migration {current_version}→{target_version} failed: {e}")
                    
                    # GS-019 §Recovery: Auto-restore from backup
                    restore_result = self._auto_restore_on_failure()
                    if restore_result["status"] == "restored":
                        logger.info(f"GS-019: Auto-restored from {restore_result['from']}")
                        # Re-initialize from restored state
                        self._conn = None
                        conn = self._get_conn()
                        current_version = self._get_schema_version(conn)
                        break
                    else:
                        logger.error(f"GS-019: Auto-restore failed: {restore_result['message']}")
                        break

def _auto_restore_on_failure(self) -> dict:
    """Attempt auto-restore from most recent backup on migration failure."""
    try:
        return self.restore()
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

#### 7.3 User Notification on Migration Failure

**File:** `db.py`

Add a notification flag that the dashboard can read:

```python
# Module-level flag for migration failure notification
_last_migration_failure: Optional[dict] = None

def get_migration_failure() -> Optional[dict]:
    """Get last migration failure info (for dashboard notification)."""
    return _last_migration_failure

def _init_db(self) -> None:
    global _last_migration_failure
    # ... existing logic ...
    
    # In the migration failure except block:
    except Exception as e:
        # ... existing logic ...
        _last_migration_failure = {
            "failed_at": int(time.time()),
            "from_version": current_version,
            "to_version": target_version,
            "error": str(e),
            "restored": restore_result["status"] == "restored",
            "restored_from": restore_result.get("from"),
        }
```

#### 7.4 CLI Commands

**File:** `doctor/cli.py`

```python
@cli.command()
@click.option("--backup-dir", type=click.Path(), help="Custom backup directory")
def backup(backup_dir):
    """Create a backup of the database."""
    from ..db import Database
    db = Database()
    result = db.backup(dest_path=backup_dir)
    if result:
        click.echo(f"✅ Backup created: {db.db_path.parent / 'backups'}")
    else:
        click.echo("⚠️  Backup skipped (cooldown active)")

@cli.command()
@click.option("--backup-file", type=click.Path(exists=True), help="Specific backup file to restore")
@click.confirmation_option(prompt="This will replace your current database. Continue?")
def restore(backup_file):
    """Restore database from backup."""
    from ..db import Database
    db = Database()
    result = db.restore(backup_path=backup_file)
    if result["status"] == "restored":
        click.echo(f"✅ Restored from {result['from']} — {result['rows']} rows recovered")
    else:
        click.echo(f"❌ Restore failed: {result['message']}")
```

#### 7.5 Dashboard Notification

**File:** `dashboard/server.py`

Add endpoint to check for migration failures:

```python
@app.get("/api/migration-status")
async def migration_status(request: Request):
    """Check for migration failure notification."""
    from observeco.db import get_migration_failure
    failure = get_migration_failure()
    if failure:
        return JSONResponse({
            "has_failure": True,
            **failure
        })
    return JSONResponse({"has_failure": False})
```

Add to dashboard HTML (in footer or alerts area):

```html
<div id="migrationAlert" style="display:none; background:#fef3cd; border:1px solid #ffc107; 
     border-radius:8px; padding:12px; margin-bottom:16px;">
  ⚠️ <strong>Migration Failed</strong>
  <span id="migrationAlertMsg"></span>
  <button onclick="dismissMigrationAlert()" style="margin-left:8px;">Dismiss</button>
</div>

<script>
fetch('/api/migration-status').then(r => r.json()).then(data => {
    if (data.has_failure) {
        const el = document.getElementById('migrationAlert');
        const msg = data.restored 
            ? `Auto-restored from backup (${data.restored_from}). Your data is safe.`
            : `Manual restore required. Backup at: ~/.observeco/backups/`;
        document.getElementById('migrationAlertMsg').textContent = msg;
        el.style.display = 'block';
    }
});
</script>
```

---

## 4. API Changes

### 4.1 New Method: `db.snapshot_counts()`

Returns current row counts for all user tables. Used by:
- `_init_db()` for pre/post migration verification
- `observeco doctor` for health checks
- `observeco status --data-health` for user visibility

### 4.2 New Method: `db.recover_stranded()`

Checks for and recovers from partial recreate-table migration failures. Called by `_init_db()` before migration loop.

### 4.3 Updated Method: `db._init_db()`

Now includes:
1. Backup before migrations (Fix 1)
2. Stranded table recovery (Fix 3)
3. Pre/post row count verification (Fix 2)
4. Downgrade guard (Fix 4)
5. **Auto-restore on failure (Fix 7)**

### 4.4 New Method: `db.restore(backup_path=None)`

Restores database from backup. Creates pre-restore backup. Returns status dict with row count.

### 4.5 New Function: `get_migration_failure()`

Module-level function returns last migration failure info for dashboard notification.

### 4.6 New Endpoint: `GET /api/migration-status`

Returns migration failure status for dashboard alert banner.

---

## 5. CLI Integration

### 5.1 `observeco doctor --data-health`

Output:
```
Data Health Check
  ✅ Schema version: 17 (current)
  ✅ No stranded migration tables
  ⚠️  Last backup: 12 days ago (recommend weekly)
  ✅ Row counts: pulse_log=1,247 compress_log=23 errors=89
  
  Result: PASS (1 warning)
```

### 5.2 `observeco status --data-health`

Shows data health in the status output. Used by `observeco doctor` and displayed in dashboard footer.

---

## 6. Backward Compatibility

All changes are backward-compatible:
- Existing databases continue to work
- New backup calls are additive (no existing behavior changes)
- Recovery check is idempotent (safe to run multiple times)
- Downgrade guard only adds a log warning (no behavior change for normal upgrades)

---

## 7. Success Criteria

- [ ] `db.backup()` called before every migration run (verify with log output)
- [ ] Pre/post row counts logged and verified (no silent data loss)
- [ ] Stranded `_v11` tables detected and recovered on startup
- [ ] Downgrade attempt logs warning instead of force-setting version
- [ ] `observeco doctor --data-health` shows schema version, backup status, row counts
- [ ] Retention sweep backs up before deleting >1000 rows
- [ ] **`db.restore()` method exists and can restore from backup** (Fix 7)
- [ ] **Migration failure auto-restores from backup and notifies user** (Fix 7)
- [ ] **CLI commands `observeco backup` and `observeco restore` work** (Fix 7)
- [ ] **Dashboard shows migration failure banner with restore status** (Fix 7)
- [ ] All existing tests pass (no behavior change for normal operation)
- [ ] Playbook audit: all 7 findings marked ✅ FIXED

---

## 8. Playbook Audit

| Playbook | Trap | Finding | Fix |
|----------|------|---------|-----|
| System Design | Migration Orphan | 10 tables orphaned in `_SCHEMA_SQL` | Acknowledged — `_SCHEMA_SQL` is the bootstrap, migrations are for upgrades. Not a bug, but document the pattern. |
| System Design | Partial Failure | Recreate-table data-loss window | Fix 3: Recovery check + Fix 1: Backup before |
| Requirements Fidelity | Lifecycle | No downgrade path | Fix 4: Downgrade guard |
| Coding Fidelity | 4.24 Error-chain | `_SCHEMA_SQL` masks data loss | Fix 2: Pre/post row counts catch the loss |
| Coding Fidelity | 4.40 Multi-entry | `backup()` never called | Fix 1: Wire backup call |
| System Design | Lens 1 Independence | Migration coupled to `Database()` | Acknowledged — acceptable coupling for now. Decoupling is a future refactor. |
| **GS-019** | **No restore path** | **Backup exists but no restore mechanism** | **Fix 7: restore() + auto-restore on failure + CLI + notification** |

---

## 9. Related Specs

- `obs-spec-021` — Action Log (§10 migration, §9 retention)
- **GS-019** — Data & Observability Continuity (§3 Schema Evolution Rules)
- `db.py:_init_db()` — Current migration runner (to be modified)
- `db.py:backup()` — Backup method (to be wired)
- `doctor/diagnostics.py` — Doctor module (to be extended)

---

**Next steps:** Confirm spec → implement Fix 1 (backup wiring) → Fix 3 (recovery check) → Fix 2 (row counts) → Fix 4 (downgrade guard) → Fix 5 (doctor check) → Fix 6 (retention backup) → **Fix 7 (restore mechanism)** → verify against success criteria.
