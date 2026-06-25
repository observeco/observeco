# obs-spec-044 — Token History Daemon Snapshot

**Spec ID:** obs-spec-044
**Title:** Token history daemon snapshot — close the only data continuity gap
**Document version:** 1.1
**Status:** ✅ APPROVED — implemented
**Owner:** Main (impl) → Hound (audit)
**Created:** 2026-06-17
**Implements:** GS-019 §Data Continuity — closes the `token_history` writer gap
**Standards:** GS-019 (Data & Observability Continuity) — §6 is mandatory

---

## RDR: Token History Daemon Snapshot

**Problem:** The 90-day token trend chart reads from `token_history` (daily snapshots). The `POST /api/token-history/snapshot` route exists and contains the correct aggregation SQL, but nothing calls it automatically. The `token_history` table is the only dashboard-read table without an independent writer.

**Solution:** Add a `TokenHistoryConsumer` to the existing watch daemon's `ConsumerManager` that runs the same aggregation SQL on a 24-hour cycle. No new process, no new cron, no new config.

**Key constraint:** Must not crash the daemon on error. Must be idempotent (re-running same day updates, doesn't duplicate).

**Success metric:** `token_history` table receives a new row every 24h while the watch daemon is running. Verified by checking `SELECT MAX(snapshot_date) FROM token_history` is within the last 36 hours.

**Edge states accounted for:**
☐ Loading, ☐ Empty, ☐ Error, ☐ Partial, ☐ Stale, ☐ Timeout, ☐ Degraded

**Lifecycle coverage:**
☐ Start, ☐ Run, ☐ Crash, ☐ Reboot, ☐ Cleanup, ☐ Stale detection

**Cross-references verified:**
☐ Yes (all claims verified against actual code — see audit report)

--- RDR APPROVED ---

---

## 1. Trigger & Context

The 90-day token trend chart reads from `token_history` (daily snapshots). The `POST /api/token-history/snapshot` route exists and contains the correct aggregation SQL, but **nothing calls it automatically**. The `token_history` table is the only dashboard-read table without an independent writer.

| Source | Status |
|--------|--------|
| `pulse_log` | ✅ Watch daemon every 30s |
| `token_logs` | ✅ Proxy, OTel, SDK — independent processes |
| `chisel_trims/drift` | ✅ Chisel daemon |
| `errors` | ✅ Pulse checker every cycle |
| `pathway_nodes/edges` | ✅ Pathway scanner |
| **`token_history`** | ❌ **No writer** — only a dashboard POST endpoint |

**Fix:** Add a `TokenHistoryConsumer` to the existing watch daemon's `ConsumerManager` that runs the same aggregation SQL on a 24-hour cycle. No new process, no new cron, no new config.

---

## 2. Design

### 2.1 What changes

One new consumer class in `watch_consumers.py`:

```python
class TokenHistoryConsumer(BaseConsumer):
    """Aggregate daily token usage from token_logs into token_history every 24h."""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "token_history")
        kwargs.setdefault("interval", 86400)  # 24h
        super().__init__(**kwargs)

    def _tick(self) -> None:
        # ponytail: aggregates YESTERDAY's complete data (midnight→midnight), not today's partial window.
        # If the daemon was down for a full day, that day is skipped (no backfill).
        # Upgrade path: on first tick, backfill all missing days from token_logs.
        now = int(time.time())
        today = (now // 86400) * 86400
        yesterday = today - 86400
        row = self.db._get_conn().execute("""\
            SELECT
                COALESCE(SUM(input_tokens), 0) as total_input,
                COALESCE(SUM(output_tokens), 0) as total_output,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read,
                COUNT(DISTINCT agent_name) as agent_count
            FROM token_logs
            WHERE recorded_at >= ? AND recorded_at < ?
        """, (yesterday, today)).fetchone()

        self.db._get_conn().execute("""\
            INSERT OR REPLACE INTO token_history
                (snapshot_date, total_input_tokens, total_output_tokens,
                 total_cache_creation_tokens, total_cache_read_tokens,
                 agent_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (yesterday, row[0], row[1], row[2], row[3], row[4], "{}"))
        self.db._get_conn().commit()
```

### 2.2 Registration

One line added to `ConsumerManager.register_all()`:

```python
def register_all(self) -> None:
    self.consumers = [
        DriftConsumer(db=self.db),
        GardenConsumer(db=self.db),
        PathwayConsumer(db=self.db),
        HealConsumer(db=self.db),
        PruneConsumer(db=self.db),
        TokenHistoryConsumer(db=self.db),  # ← NEW
    ]
```

### 2.3 Schema dependency

The consumer reads `token_logs` columns: `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens`, `agent_name`, `recorded_at`. These columns must exist before the consumer starts.

**Current state:** `input_tokens`, `output_tokens`, `agent_name`, `recorded_at` exist. `cache_creation_tokens` and `cache_read_tokens` are added by obs-spec-020's Migration 18 (or whichever migration ships first). If they don't exist, the consumer's SQL will throw `no such column` and the daemon will log an error every 24h.

**Mitigation:** The consumer should use COALESCE with a subquery that gracefully handles missing columns, OR the migration for these columns must ship before the consumer is enabled. Documented here as a deployment ordering constraint: **Migration 18 (or equivalent adding cache_* columns) must run before TokenHistoryConsumer is registered.**

### 2.4 No new dependencies

Uses `Database._get_conn()` and raw SQLite — same as every other consumer.

---

## 3. States & Edge Cases

| State | Behaviour |
|-------|-----------|
| **Normal** | Every 24h, aggregates today's `token_logs` into `token_history`. If today's row already exists, it's replaced (idempotent). |
| **No token_logs** | All COALESCE'd to 0. Writes a zero row. Dashboard shows 0 for that day — correct. |
| **Daemon not running** | No snapshots written. Dashboard shows data up to last snapshot. Same as today's behaviour. |
| **First run** | Aggregates all `token_logs` from today. If daemon started at 2pm, only data from midnight→2pm is captured. Next day captures full 24h. |
| **Daemon restart** | Consumer resumes on next tick. Missed days are not backfilled — only current day is written. |
| **DB locked** | `busy_timeout=5000` handles it. Consumer retries on next tick (24h later). |
| **Consumer error** | Caught by `BaseConsumer._loop()` try/except. Logged, does not crash daemon. |
| **Multi-instance** | Two daemons writing to same DB: `INSERT OR REPLACE` + UNIQUE index on `snapshot_date` means last-writer-wins. Data is identical from same aggregation SQL, so no conflict. |

---

## 4. Data Continuity (GS-019 — mandatory)

**What happens to existing data?**
- No existing data is migrated or deleted.
- `token_history` table is unchanged — the consumer only writes new rows.
- `token_logs` is unchanged — the consumer reads from it, does not modify.

**Is backup required?**
- No. The change is purely additive (new consumer, no schema change, no destructive operation).

**What does the user see if empty?**
- Fresh install with no daemon: same as today — 90-day chart shows no data.
- Fresh install with daemon running: first snapshot written at next 24h boundary. Chart shows data from that day forward.
- Daemon stopped: chart shows data up to last snapshot. No error state — just older data.

**What's the recovery path?**
- Consumer error: logged, retries next tick (24h). No data loss — `token_logs` still has the raw data.
- Daemon crash: on restart, consumer resumes. Missed days are not backfilled (only current day is written). The dashboard route `POST /api/token-history/snapshot` remains as a manual backfill option.
- DB corruption: `token_logs` is the source of truth. `token_history` can be rebuilt by running the snapshot endpoint for each missed day.

**Self-monitoring:**
- Consumer logs its tick (success/failure) via the existing `BaseConsumer` logging.
- Dashboard can surface "last snapshot" age from `token_history` table (already shown in token analytics tab).

---

## 5. Success criteria

- [ ] `TokenHistoryConsumer` registered in `ConsumerManager.register_all()`
- [ ] Consumer runs on 24h interval without crashing
- [ ] `INSERT OR REPLACE` is idempotent — re-running on same day updates, doesn't duplicate
- [ ] Zero rows written when `token_logs` is empty (all COALESCE'd to 0 — acceptable)
- [ ] Consumer error does not crash the daemon (caught by `BaseConsumer._loop()`)
- [ ] No schema changes, no new dependencies, no new config

---

## 6. Files modified

- `src/observeco/watch_consumers.py` — add `TokenHistoryConsumer` class + `TOKEN_HISTORY_INTERVAL` constant + register in `register_all()`
- `tests/test_watch_consumers.py` — add 2 tests: start/stop lifecycle + runs without crash

---

## 8. Master plan diff

```diff
+ Token History Daemon Snapshot (obs-spec-044)
+   Status: ✅ Live
+   Backend: ✅ TokenHistoryConsumer in watch daemon
+   Tests: ✅ 2 lifecycle tests, 11 total in test_watch_consumers.py
+   Data continuity: token_history now has automatic writer (24h cycle)
```

---

## 7. Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-17 | Add as consumer in existing daemon, not a new process | Daemon already exists, consumer framework already exists, aggregation SQL already exists. Adding a 24h timer to the existing loop is the minimal change. |
| 2026-06-17 | No backfill on restart | `token_logs` retains raw data. Backfill is a separate concern (manual via POST endpoint). The consumer only writes current day to keep the code simple and avoid edge cases with partial-day data. |
