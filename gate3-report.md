# Gate 3 — Diff Gate Report

**Date:** 2026-06-11
**Sprint:** obs-spec-022 (Migration Infrastructure), obs-spec-021 (Action Log), obs-spec-020 (Token Analytics), Governance Docs
**SCHEMA_VERSION:** 20 (was 17)

---

## 1. New Defaults Introduced?

| Item | Introduced | Overfitted? | Generic? |
|------|-----------|-------------|----------|
| Backup before destructive migrations | `_init_db()` now calls `self.backup()` if `_has_data()` | **No** — standard safety pattern for any SQLite app | ✅ Generic — uses SQLite online backup, works cross-platform |
| Retention sweep backs up >1000 rows | `purge_old_data()` calls `backup()` | **No** — industry-standard data safety | ✅ Generic |
| Downgrade guard (no forced version set) | Version `> SCHEMA_VERSION` logs warning, doesn't overwrite | **No** — correct behavior for any schema migration system | ✅ Generic |

**Verdict:** All new defaults are generic safety patterns. No ecosystem-specific assumptions.

---

## 2. New Paths or Conventions?

None. Backups continue at `{db_dir}/backups/pulse_{ts}.db`. No new directory conventions.

**Verdict:** No new paths. ✅

---

## 3. New CLI Commands?

| Command | File | Notes |
|---------|------|-------|
| `observeco doctor run --data-health` | `doctor/cli.py:28` | Runs GS-019 data continuity checks |
| `observeco doctor run --fix` (existing) | `doctor/cli.py:30` | Applies auto-fixes |

**Overfitting check:** `--data-health` is named generically. The `doctor` CLI is framework-agnostic.

**Verdict:** Generic. ✅

---

## 4. New API Endpoints?

**Token Analytics (10 endpoints):**
| Endpoint | File | Line |
|----------|------|------|
| `POST /api/tokens/log` | `server.py` | 6981 |
| `GET /api/tokens/summary` | `server.py` | 7003 |
| `GET /api/tokens/trends` | `server.py` | 7011 |
| `GET /api/tokens/recent` | `server.py` | 7019 |
| `POST /api/tokens/budget` | `server.py` | 7046 |
| `GET /api/tokens/budgets` | `server.py` | 7064 |
| `GET /api/tokens/chart` | `server.py` | 7078 |
| `GET /api/tokens/breakdown` | `server.py` | 7103 |
| `GET /api/tokens/system-prompts` | `server.py` | 7119 |
| `GET /api/tokens/analytics` (HTML tab) | `server.py` | 7135 |

**Action Log (6 endpoints):**
| Endpoint | File | Line |
|----------|------|------|
| `GET /api/action-log` | `server.py` | 7425 |
| `GET /api/action-log/cumulative` | `server.py` | 7472 |
| `GET /api/action-log/skill-summary` | `server.py` | 7510 |
| `GET /api/action-log/impact-card` (HTML) | `server.py` | 7562 |
| `GET /api/action-log/skills-history` (HTML) | `server.py` | 7666 |
| `GET /api/action-log/recent-activity` (HTML) | `server.py` | 7778 |

**Overfitting check:** All endpoints use `/api/` prefix under FastAPI standard. Token analytics uses `token_logs` table — generic naming. Action log uses `action_log` table — generic naming. No Hermes/OpenClaw-specific path segments.

**Verdict:** Generic. ✅

---

## 5. New Database Tables/Columns?

### New Table: `action_log` (Migration 20)
```sql
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_detail TEXT NOT NULL,
    tokens_saved INTEGER DEFAULT 0,
    cost_saved REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'success',
    metadata TEXT DEFAULT '{}',
    triggered_by TEXT DEFAULT 'daemon',
    created_at INTEGER NOT NULL
);
```
**Overfitting?** No — `action_type` is a free-text enum (not tied to any specific framework), `agent_name` is generic "who performed this", `triggered_by` covers any trigger source.

### New Table: `token_message_breakdown` (Migration 19)
```sql
CREATE TABLE IF NOT EXISTS token_message_breakdown (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_log_id INTEGER NOT NULL,
    message_index INTEGER NOT NULL,
    message_role TEXT NOT NULL,
    content_hash TEXT DEFAULT "",
    token_count INTEGER NOT NULL,
    is_system_prompt INTEGER DEFAULT 0,
    is_cached INTEGER DEFAULT 0,
    cost REAL DEFAULT 0,
    created_at INTEGER NOT NULL
);
```
**Overfitting?** No — per-message cost attribution is a standard LLM observability pattern.

### New Columns on `token_logs` (Migrations 17, 18):
- `workflow_name`, `service_name`, `session_id`, `system_prompt_hash`
- `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens`
- `cost_computed`, `cache_savings`

**Overfitting?** No — these are standard LLM token-tracking fields. OTel semantic convention compatible.

**Verdict:** Generic. ✅

---

## 6. New Error Messages?

| Message | Where | Context |
|---------|-------|---------|
| "GS-019 VIOLATION: {table} missing after migration (had {n} rows)" | `db.py:_verify_migration_integrity()` | Data loss detection |
| "GS-019 WARNING: {table} row count dropped: {n} → {m}" | `db.py:_verify_migration_integrity()` | Suspicious data loss |
| "GS-019 RECOVERY: Renaming {temp} → {target}" | `db.py:_recover_stranded_tables()` | Stranded table recovery |
| "GS-019: Database version ({n}) > code version ({n}). Possible downgrade." | `db.py:_init_db()` | Downgrade guard |
| Canonical action detail formats (14 patterns) | `db.py:backfill_action_log()` + spec | Pre-formatted human-readable strings |

**Overfitting check:** Error messages use "GS-019" prefix (internal standard name). While this is ObserveCo-specific branding in the log messages, the data patterns they describe (row count drops, stranded tables, downgrade detection) are generic observability patterns.

**⚠ Partial overfitting:** The "GS-019" prefix is ObserveCo-internal. These are log messages only (not user-facing), so impact is minimal.

---

## 7. New UI Text or Labels?

| UI Element | Where | Detail |
|------------|-------|--------|
| "Token Analytics" tab | Agent detail view | Chart.js time-series, filters, summary cards, breakdown table, drill-down modal |
| "Your ObserveCo Impact" card | Brain Analysis tab | Cumulative stats with Pro/Free gating |
| "Compression History" section | Skills Audit | Per-skill breakdown with Pro/Free gating |
| "Recent Activity" feed | Token Optimiser | Live action feed with Pro/Free gating |
| "Already condensed" labels | Compression results | Honest reporting instead of 0% |
| Upsell banners | All action log UI | "🔒 Action history is a Pro feature" |

**Overfitting check:** UI text is ObserveCo-specific (the product's own branding). However, the patterns (empty states, loading states, error states, upsell banners) are standard SaaS patterns — not overfitted to any specific ecosystem.

**Verdict:** The product name is inherently ObserveCo-specific, but the UI patterns are generic and reusable. ✅ Acceptable.

---

## 8. New Configuration Options?

None. No new config keys, no new env vars. Retention settings unchanged.

**Verdict:** No new configuration. ✅

---

## 9. New Dependencies?

None. Chart.js is loaded via CDN at render time (no pip dependency). All code uses existing packages (sqlite3, json, logging, platformdirs, fastapi).

**Verdict:** No new dependencies. ✅

---

## 10. New Test Patterns?

| File | What it tests | Coverage |
|------|--------------|----------|
| `tests/test_infra.py` | Smoke tests for `auto_detect` and `dashboard` | Basic import/param checks only |

**Gaps:**
- ❌ No tests for `db.py:_init_db()` migration fixes (backup, recovery, downgrade guard, row count verification)
- ❌ No tests for `db.py:log_action()` or `get_actions()`
- ❌ No tests for `token_analytics.py:get_chart_data()`, `get_breakdown()`, `get_system_prompts()`
- ❌ No tests for action log API endpoints
- ❌ No tests for token analytics API endpoints
- ❌ No tests for `doctor/diagnostics.py:check_data_health()`
- ❌ No tests for backfill_action_log()

**Overfitting check:** The test gap is a coverage concern, not an overfitting concern. The patterns needed (TestClient, mock DB, snapshot assertions) are generic testing patterns.

**Verdict: ⚠ Significant testing debt.** 7 missing test categories for critical infrastructure.

---

## 11. New Documentation?

| Document | Type | Purpose |
|----------|------|---------|
| `CHANGELOG.md` (updated) | Governance | v0.2.0 changelog |
| `SECURITY.md` | Governance | Security policy |
| `CODE_OF_CONDUCT.md` | Governance | Community standards |
| `specs/obs-spec-022-migration-infrastructure.md` | Spec | Migration hardening design |
| `specs/obs-spec-021-action-log.md` | Spec | Unified action log design |
| `specs/obs-spec-020-token-analytics-dashboard.md` | Spec | Token analytics design |

**Overfitting check:** Specs reference Obs-spec IDs and GS-019 standard — these are project-internal frameworks. However, the design patterns (migration infrastructure, action logging, token analytics) are generic observability patterns.

**Verdict:** Acceptable — internal documentation conventions are expected. ✅

---

## 12. New Billing/Upsell Surfaces?

| Surface | Where | Mechanism |
|---------|-------|-----------|
| Brain Analysis "Your ObserveCo Impact" card | Dashboard Brain Analysis tab | `license.require_pro()` → show data or upsell |
| Skills Audit "Compression History" | Dashboard Skills Audit | `license.require_pro()` → show data or upsell |
| Token Optimiser "Recent Activity" | Dashboard Token Optimiser | `license.require_pro()` → show data or upsell |
| Token Analytics full dashboard | Dashboard Token Analytics tab | Free: basic summary only; Pro: full charts/filters/drill-down |

**Overfitting check:** The upsell pattern uses `from observeco import license` with `require_pro()` — a standard feature gating pattern. The Pro/Free tier split is product-specific but the mechanism (license check → conditional render) is generic.

**Verdict:** Acceptable — standard SaaS gating pattern. ✅

---

## Gate 3 Summary

| # | Item | Status | Overfitting Risk |
|---|------|--------|-----------------|
| 1 | New defaults | ✅ PASS | None |
| 2 | New paths/conventions | ✅ PASS | None |
| 3 | New CLI commands | ✅ PASS | None |
| 4 | New API endpoints | ✅ PASS | None |
| 5 | New DB tables/columns | ✅ PASS | None |
| 6 | New error messages | ⚠ PASS | GS-019 prefix is internal branding (logs only) |
| 7 | New UI text/labels | ✅ PASS | Product naming expected |
| 8 | New configuration options | ✅ PASS | None |
| 9 | New dependencies | ✅ PASS | None |
| 10 | New test patterns | ❌ FAIL | **7 missing test categories** — critical gap |
| 11 | New documentation | ✅ PASS | Internal convention expected |
| 12 | New billing/upsell surfaces | ✅ PASS | Standard SaaS gating |

**Overall Gate 3 Result:** ⚠ **FAIL** (1 failure — test coverage gap)

Test coverage is the single blocker. The code is generic and not overfitted, but critical infrastructure (migration safety, action log, token analytics) has no automated test coverage.

---

## Lessons Learned

### What Worked Well

1. **Consistent gating pattern** — All Pro/Free gating uses the same `license.require_pro()` pattern, making tier changes a single-point update.

2. **Spec-driven development** — All three features (obs-spec-020, 021, 022) were spec'd before implementation. The specs included success criteria, backward compatibility notes, and edge cases.

3. **GS-019 standard integration** — Migration infrastructure fixes consistently trace back to the GS-019 standard principles (Backup Before Destructive, Verify After Migration). This creates an audit trail from code to standard.

4. **Pre-formatted action_detail strings** — Storing human-readable strings in the DB avoids formatting logic at display time, reducing UI complexity.

5. **Idempotent backfill** — `backfill_action_log()` uses `INSERT OR IGNORE` via the unique constraint, enabling safe re-runs without duplicates.

### What Should Be Improved

1. **🚨 Test coverage is critically missing** — 7 areas of new code have zero tests:
   - Migration infrastructure fixes (backup, recovery, downgrade guard, row counts)
   - `log_action()` and `get_actions()` methods
   - Token analytics aggregation functions
   - Action log API endpoints
   - Token analytics API endpoints
   - `check_data_health()` doctor diagnostics
   - `backfill_action_log()` one-time migration

2. **Error message standards should use generic codes** — "GS-019" prefix in log messages is fine for internal logging, but if these ever become user-visible error messages, they should use standard error codes or plain language instead.

3. **No schema migration tests** — The recreate-table pattern (Migrations 11, 15) and the new recovery logic have no automated verification. A crash at the DROP/RENAME boundary is only caught by manual inspection.

4. **Action log integration points aren't wired** — The spec defines logging calls in `trim.py`, `heal_events`, and `skill_compress.py`, but the actual `db.log_action()` calls in those modules were not verified in this audit. Need to confirm they're actually calling the method.

5. **UI patterns are in server.py (8K+ lines)** — The dashboard `server.py` is now 8,150 lines. The new action log HTML templates (impact-card, skills-history, recent-activity) are inlined in Python strings, making maintenance harder. Consider extracting templates to separate HTML files.

### Patterns That Emerged

1. **Safety-first migration pattern** — `backup → recover_stranded → _SCHEMA_SQL → pre_counts → migrate → post_counts → verify` is now the canonical migration flow. This is a reusable pattern for any SQLite-based application.

2. **Unified action log pattern** — A single append-only event table with pre-formatted display strings, unique constraint for idempotency, and type/agent/time indexes. This pattern is reusable for any system that needs a unified activity feed.

3. **On-the-fly aggregation pattern** — Token analytics uses SQL `GROUP BY` with time-bucket truncation rather than materialized aggregation tables. This avoids sync issues at the cost of slightly higher query latency. Good tradeoff for <100K rows.

4. **Three-tier billing gate** — Consistent pattern: `Pro` (full data), `Free` (upsell banner), `Empty state` (guidance without gate). Applies uniformly across Brain Analysis, Skills Audit, and Token Optimiser.

---

## Version History Update

### CHANGELOG.md
CHANGELOG.md at v0.2.0 is already up to date. No changes needed.

### playbook-evolution-meta.md (This File)
Version history should be updated with this Phase 8 run.

### spec/deprecated/08-phase-8-meta-evolution.md
This deprecated spec confirms Phase 8 is complete.