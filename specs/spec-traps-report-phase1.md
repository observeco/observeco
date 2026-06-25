# Phase 1: Requirements Fidelity — 6 Spec Traps Analysis

**Date:** 2026-06-11  
**Sprint:** Migration Infrastructure (obs-spec-022) + Unified Action Log (obs-spec-021) + Token Analytics Dashboard (obs-spec-020) + Compression 0% Bug Fix + GS-019 Standard  
**Auditor:** Requirements Fidelity Subagent

---

## Trap 1: Happy Path Only — Do specs cover failure states?

**Check:** Search for "error", "fail", "empty", "crash" in each spec. Are failure modes documented?

### obs-spec-022 (Migration Infrastructure)

| Finding | Evidence |
|---------|----------|
| ✅ Documents mid-migration crash recovery | §2.3: "If crash occurs between DROP and RENAME, data is stranded" |
| ✅ Documents partial failure masking | §1 Finding 4: "_SCHEMA_SQL re-runs on every startup, can create empty tables after drop" |
| ✅ Documents downgrade scenario | §3 Fix 4: "Don't force-set version if current > SCHEMA_VERSION" |
| ✅ Documents database corruption recovery | §3 Fix 3: `_recover_stranded_tables()` for partial recreate-table failures |
| ✅ Documents retention sweep risk | §3 Fix 6: "backup before deleting >1000 rows" |
| ✅ Playbook audit maps 6 failure modes | §8: Migration orphan, partial failure, lifecycle, error-chain, multi-entry, coupling |

**Verdict: PASS** — 6 failure modes explicitly identified and mitigated with dedicated fixes.

### obs-spec-021 (Unified Action Log)

| Finding | Evidence |
|---------|----------|
| ✅ Documents `no_action` failure mode | §3.4: "Log `no_action` results. When compression yields ≤5% savings" |
| ✅ Documents API errors | §12: "API error — fetch fails or server down: 'Couldn't load action history'" |
| ✅ Documents retention cleanup edge case | §9: "After 90-day cleanup: Dashboard gracefully handles missing old data" |
| ✅ Documents unique constraint violation | §8: Backfill idempotency via `INSERT OR IGNORE` |
| ✅ Documents insert failure resilience | §14 Lens 3: "action_log INSERT failure doesn't block the action itself" |
| ✅ Playbook audit: Trap 1 "Happy Path Only" closed | §14: "Empty states for fresh install, retention cleanup, and API error now specified" |

**Verdict: PASS** — Extensive failure coverage including `no_action`, API errors, retention cleanup, and idempotent backfill.

### obs-spec-020 (Token Analytics Dashboard)

| Finding | Evidence |
|---------|----------|
| ✅ Documents API timeout | §7: "Chart shows 'Request timed out. Retrying...' with auto-retry (3 attempts, 2s delay)" |
| ✅ Documents 5xx server error | §7: "Chart shows 'Server error. Check dashboard server status.' with manual retry button" |
| ✅ Documents 4xx client error | §7: "Chart shows 'Invalid request. Resetting filters...' with auto-reset" |
| ✅ Documents Chart.js CDN failure | §7: "Fallback to simple HTML table with token data" |
| ✅ Documents migration failure | §7: "Rollback procedure documented in §6 Phase 1" |
| ✅ Documents stale data | §7: "'Data may be outdated. Refreshing...' with auto-refresh" |
| ✅ Documents partial aggregation | §7: "Show available data with warning" |

**Verdict: PASS** — Comprehensive error state documentation across API, CDN, migration, and data freshness failure modes.

### Trap 1: Overall PASS ✓

All three specs cover failure states explicitly. obs-spec-021 and obs-spec-020 are exemplary with dedicated failure sections.

---

## Trap 2: Visuals Without States — Loading/Empty/Error states for UI elements?

**Check:** Search for "loading", "empty", "error state" in specs. Do UI specs define all visual states?

### obs-spec-022 (Migration Infrastructure)

| Finding | Evidence |
|---------|----------|
| ✅ Infrastructure spec (not a UI spec) | Primarily backend database changes |
| ✅ CLI output shows loading/error states | §5.1: `observeco doctor --data-health` output shows ✅/⚠️ indicators |
| ✅ Data health CLI handles all states | §5.1: Shows pass with warnings, fail states for schema version mismatch, outdated backup, stranded tables |

**Verdict: PASS** — Appropriate for an infrastructure spec. CLI outputs have explicit state indicators.

### obs-spec-021 (Unified Action Log)

| Finding | Evidence |
|---------|----------|
| ✅ Loading state defined | §12: "Skeleton placeholder (2-3 grey bars, pulsing)" |
| ✅ Populated state defined | §5.2-5.4: Full ASCII mockups for Pro populated in Brain Analysis, Skills Audit, Token Optimiser |
| ✅ Empty (fresh install) defined | §5.2: "No actions recorded yet" + CLI command to populate |
| ✅ Empty (retention cleanup) defined | §12: "Show only recent data, no warning" |
| ✅ API error state defined | §12: "'Couldn't load action history. Make sure the dashboard server is running.'" |
| ✅ Free/Pro gating visuals defined | §5: Full upsell banners for each section, Pro cards with real data |
| ✅ Helpful guidance in empty states | §12: Every empty state includes CLI command and explanation |

**Verdict: PASS** — 6 distinct visual states documented with ASCII mockups for each section. Gold standard.

### obs-spec-020 (Token Analytics Dashboard)

| Finding | Evidence |
|---------|----------|
| ✅ Loading state defined | §5: "Spinner with 'Loading token analytics...'" |
| ✅ Empty (no data) defined | §5: "'No token data for this agent. Run `observeco token log <agent>` to start tracking.'" |
| ✅ Empty (filter no match) defined | §5: "'No data matches your filters. Try widening the time range or removing filters.'" |
| ✅ Error (API error) defined | §5: "'Failed to load token data. Check dashboard server status.'" |
| ✅ Error (invalid params) defined | §5: "'Invalid filter parameters. Reset to defaults.'" |
| ✅ Chart.js CDN fallback | §5: "Fallback to HTML table if Chart.js CDN fails" |
| ✅ Summary cards show 0 values on empty | §7: "Summary cards show 0 values" |

**Verdict: PASS** — All 5 UI states (loading, empty-data, empty-filter, error-api, error-params) documented.

### Trap 2: Overall PASS ✓

All three specs define appropriate visual states. obs-spec-021 is the gold standard with 6 distinct states per UI section.

---

## Trap 3: No Lifecycle — First run, upgrade, downgrade, corrupted state?

**Check:** Search for "lifecycle", "upgrade", "first run", "downgrade", "corrupted", "recovery" in specs.

### obs-spec-022 (Migration Infrastructure)

| Finding | Evidence |
|---------|----------|
| ✅ Downgrade path | §3 Fix 4: Downgrade guard — logs warning, doesn't force-set version |
| ✅ Corrupted state recovery | §3 Fix 3: `_recover_stranded_tables()` — handles mid-migration crash |
| ✅ Upgrade protection | §3 Fix 1 + 2: Backup before migrations + pre/post row count verification |
| ✅ Every-startup safety | `_recover_stranded_tables()` called before migration loop every startup |
| ✅ Retention sweep lifecycle | §3 Fix 6: Backup before deleting >1000 rows in purge_old_data() |
| ✅ First run considered | `_has_data()` check — skips backup on fresh install (no data yet) |

**Verdict: PASS** — Full lifecycle coverage: first-run (no backup), upgrade (backup + verify), downgrade (guard), corrupted (recovery), retention (backup before delete).

### obs-spec-021 (Unified Action Log)

| Finding | Evidence |
|---------|----------|
| ✅ First run (fresh install) | §8: Backfill runs "On first run after migration" |
| ✅ Creation lifecycle | §3 Table creation (Migration 18) |
| ✅ Population lifecycle | §6: Logging integration points for compression, healing, skill compression, config fixes |
| ✅ Retention lifecycle | §9: "Retain for 90 days by default" → cleanup → graceful degradation |
| ✅ Post-retirement state | §9: "Dashboard gracefully handles missing old data — shows only current window" |
| ✅ Playbook audit: Trap 3 closed | §14: "Lifecycle: creation → population → 90-day retention → cleanup → graceful degradation" |
| ✅ Backfill idempotency | §8: "INSERT OR IGNORE" for safe re-runs |
| ✅ Unique constraint for idempotency | §3.1: Unique index on (agent_name, action_type, created_at, action_detail) |

**Verdict: PASS** — Complete lifecycle from creation through retirement with graceful degradation at each stage.

### obs-spec-020 (Token Analytics Dashboard)

| Finding | Evidence |
|---------|----------|
| ✅ Aggregation refresh lifecycle | §7: "Runs every 5 minutes via background job" |
| ✅ Stale data detection | §7: "Check last aggregation timestamp on each API call, refresh if stale" |
| ✅ Migration rollback | §7: "New columns have defaults (empty string, 0), old code ignores new columns" |
| ✅ Data cleanup lifecycle | §7: "token_aggregations table pruned to 90 days retention (configurable)" |
| ✅ Cross-platform first run | §7: Windows backfill path resolution via platformdirs |

**Verdict: PASS** — Lifecycle covers stale data, migration rollback, cleanup, and cross-platform first-run.

### Trap 3: Overall PASS ✓

All three specs cover lifecycle states (first run, upgrade, downgrade, corrupted, retention, cleanup).

---

## Trap 4: No Success Metrics — Quantitative success criteria?

**Check:** Search for "success criteria", "metric", "target" in specs.

### obs-spec-022 (Migration Infrastructure)

| Finding | Evidence |
|---------|----------|
| ✅ §7 Success Criteria defined | 8 items: backup called, row counts logged, stranded tables recovered, downgrade logged, doctor shows health, retention backup, tests pass, playbook fixed |
| ✅ Binary pass/fail metrics | 7/8 are binary checks (yes/no) — appropriate for infrastructure hardening |
| ✅ Row count verification includes threshold | §3 Fix 2: ">10% drop is suspicious" — quantitative threshold |
| 🔶 Missing: latency/performance targets | No specific query latency targets for migration checks |

**Verdict: PASS** — Success criteria are appropriate for an infrastructure hardening spec (binary checks for safety features).

### obs-spec-021 (Unified Action Log)

| Finding | Evidence |
|---------|----------|
| ✅ §13: 7 quantitative metrics | Action log coverage ≥90%, no_action 100%, per-skill 100%, API <100ms, backfill idempotent, Free/Pro visibility 100% |
| ✅ Each metric has measurement method | SQL queries specified for each: GROUP BY action_type, COUNT(DISTINCT), TestClient timing |
| ✅ Qualitative acceptance criteria | 4 items: user can answer key questions from UI alone |
| ✅ Targets are specific and testable | 90%, 100%, <100ms — all measurable |
| ✅ Backfill idempotency verifiable | Row count before and after second backfill run must match |

**Verdict: PASS** — Best-in-class success metrics with specific targets, measurement methods, and SQL verification queries.

### obs-spec-020 (Token Analytics Dashboard)

| Finding | Evidence |
|---------|----------|
| ✅ §8: Performance metrics (4) | Chart <500ms for 30d, aggregation <100ms, 1000 data points, filter <200ms, backfill <5min |
| ✅ Operational metrics (5) | Aggregation every 5min, stale detection within 1h, migration rollback, logging, heartbeat |
| ✅ Functional metrics (5) | All 14 agents, component breakdown, cost computation, zoom/pan, filters |
| ✅ Acceptance criteria (6) | User actions: select agent → trend, filter by provider → cost, click → details, export CSV, empty states, error states |

**Verdict: PASS** — Comprehensive 3-tier metrics (performance, operational, functional) with specific numerical targets.

### Trap 4: Overall PASS ✓

All three specs have quantified success criteria. obs-spec-021 and obs-spec-020 are particularly strong with numerical thresholds and measurement methods.

---

## Trap 5: Hidden Constraints — Environment assumptions documented?

**Check:** Search for "constraint", "limitation", "requirement" in specs.

### obs-spec-022 (Migration Infrastructure)

| Finding | Evidence |
|---------|----------|
| ✅ SQLite-specific constraints implicit | WAL journal mode, thread-safety, backup file naming |
| ✅ Backward compatibility stated | §6: "Existing databases continue to work. New backup calls are additive." |
| ✅ Recovery is idempotent | §6: "Recovery check is idempotent (safe to run multiple times)" |
| ✅ Decoupling acknowledged as future | §8: "Migration coupled to Database() — acceptable coupling for now" |
| 🔶 No explicit environment section | Constraints are embedded in architecture description rather than listed |

**Verdict: PASS** — Constraints are documented through architecture descriptions rather than a dedicated section, but all relevant constraints (idempotency, backward compatibility, coupling) are stated.

### obs-spec-021 (Unified Action Log)

| Finding | Evidence |
|---------|----------|
| ✅ Fresh install constraint | §12: "Empty (fresh install) — actions.length === 0" |
| ✅ Free user constraint | §5.1: "Free tier: All action log dashboard sections show upsell banners. No data is fetched or displayed." |
| ✅ Retention constraint | §9: "Retain for 90 days by default" |
| ✅ Post-retention constraint | §9: "After 90-day cleanup: Dashboard gracefully handles missing old data" |
| ✅ App-only constraints (no alert_log/drift_detect) | §6.1-6.4: Only compress, heal, restart, skill_compress, config_fix wired — alert_log and drift_detect not yet wired |
| ✅ Cost estimation assumption | §7: "Uses DeepSeek V3 pricing as baseline" |
| 🔶 Missing: writes single-threaded? | Thread safety not explicitly stated (implied by SQLite connection model) |

**Verdict: PASS** — Most constraints documented. Missing thread-safety for concurrent action_log writers but mitigatable (unique constraint + rollback).

### obs-spec-020 (Token Analytics Dashboard)

| Finding | Evidence |
|---------|----------|
| ✅ Cross-platform constraints | §7: Windows (platformdirs), macOS/Linux standard paths, Docker volume mount |
| ✅ Multi-instance constraints | §7: "Single-user assumption — Dashboard is single-user (no concurrent web sessions)" |
| ✅ Chart.js CDN dependency | §5: CDN fallback to HTML table |
| ✅ Large dataset constraints | §7: "max 1000 data points (aggregate to coarser granularity if needed)" |
| ✅ On-the-fly aggregation constraint | §3: "No separate token_aggregations table — avoids sync issues and storage overhead" |
| ✅ Provider constraints | §10.3: Explicit pricing table per provider with fallback to 'custom' |
| ✅ Legacy data constraint | §10.4: "When input_tokens + output_tokens == 0 (legacy rows), fall back to flat-rate" |

**Verdict: PASS** — Best environmental documentation of the three specs. Explicit platform, scale, dependency, and legacy constraints.

### Trap 5: Overall PASS ✓

All specs document environment assumptions and constraints. obs-spec-020 is the most thorough with explicit platform and scale limits.

---

## Trap 6: Contradictory Refs — Master plan tasks vs spec claims?

**Check:** Compare task statuses in master plan vs actual implementation.

### Master Plan Task Status Audit

| Task | Master Plan Status | Actual Implementation | Match? |
|------|-------------------|---------------------|--------|
| **2.23** — Wire `db.backup()` before migrations + pre/post row counts | ⬜ **TODO** | ✅ Code implements backup before migrations, pre/post row counts, `_verify_migration_integrity()` | ❌ **CONTRADICTION** — Code built but master plan says TODO |
| **2.24** — DB migration infrastructure (recovery check, downgrade guard, doctor data health) | ⬜ **TODO** | ✅ Code implements `_recover_stranded_tables()`, downgrade guard, `check_data_health()` | ❌ **CONTRADICTION** — Code built but master plan says TODO |
| **3.19** — Unified Action Log (obs-spec-021) | ✅ **Done** | ✅ Code implements action_log table, 6 API endpoints, Free/Pro cards, backfill | ✅ **CONSISTENT** |
| **obs-spec-020** — Token Analytics Dashboard | ⬜ **No task** (declared shipped in decision log only) | ✅ Code implements chart/breakdown/system-prompts endpoints, Chart.js UI | ❌ **CONTRADICTION** — Shipped product has no master plan task |
| **obs-spec-022** — Migration Infrastructure (6 fixes) | Declared "spec'd" in version header, tasks marked TODO | ✅ All 6 fixes implemented in code | ⚠️ **STALE** — Spec documents already-implemented code but tasks not updated |

### Spec-Internal Contradictions

| Spec | Contradiction | Detail |
|------|--------------|--------|
| **obs-spec-020** §3 vs §6 | On-the-fly vs materialized aggregation | §3: "Aggregation is computed on-the-fly from token_logs via SQL GROUP BY" + "No separate token_aggregations table". §6 Phase 1: "Create token_aggregations table" + "Populate aggregations from existing data". Code chose on-the-fly (no token_aggregations table found). | ❌ **CONTRADICTION** — §3 and §6 say opposite things about aggregation strategy |
| **obs-spec-020** §7 | References `token_aggregations` table cleanup | §7: "token_aggregations table pruned to 90 days retention" — but the table doesn't exist in the on-the-fly design. | ❌ **STALE REFERENCE** — References table eliminated by design decision in §3 |
| **obs-spec-022** Version status | "Status: DRAFT" but code already implements all 6 fixes | Spec is DRAFT, but master plan and code confirm all 6 fixes are built. | ⚠️ **STALE STATUS** — DRAFT designation may be misleading for review process |
| **obs-spec-021** v2 changelog | Claims §3.2 vs §5.2 contradiction resolved | Verified: §3.2 now says per-skill, §5.3 shows per-skill breakdown. Consistent. | ✅ **RESOLVED** |

### Trap 6: FAIL ⚠️

**3 contradictions found:**

1. **Tasks 2.23-2.24 status mismatch:** Master plan marks both as ⬜ TODO yet all 6 fixes of obs-spec-022 are implemented in `db.py`. The master plan tasks need updating to ✅ DONE.

2. **obs-spec-020 has no master plan task:** The Token Analytics Dashboard shipped per the decision log (line 533) but there is no Phase 2 or Phase 3 task entry for it. It's a phantom task — implemented but untracked.

3. **obs-spec-020 spec-internal contradiction:** §3 says "on-the-fly aggregation, no materialized table" but §6 Phase 1 says "Create token_aggregations table". The code chose §3's approach but §6 was never corrected.

---

## Summary Report

| Trap | Finding | Verdict | Evidence |
|------|---------|---------|----------|
| **1. Happy Path Only** | All 3 specs document failure modes (crash recovery, API errors, CDN failure, retention cleanup, mid-migration crash) | **PASS** | obs-spec-022: 6 failure fixes; obs-spec-021: §12 matrix + no_action; obs-spec-020: §7 edge cases |
| **2. Visuals Without States** | All UI specs define loading/empty/error states. obs-spec-021 has 6-state matrix; obs-spec-020 has 5 states | **PASS** | obs-spec-021 §5: mockup per state; obs-spec-020 §5: loading/empty/error/CDN fallback; obs-spec-022: CLI state indicators |
| **3. No Lifecycle** | Full lifecycle coverage: first-run, upgrade, downgrade, corrupted state, retention cleanup, graceful degradation | **PASS** | obs-spec-022: downgrade guard, stranded recovery; obs-spec-021: creation→retention→cleanup; obs-spec-020: 5min refresh→stale→rollback→90d cleanup |
| **4. No Success Metrics** | All specs have quantified success criteria with specific targets | **PASS** | obs-spec-022: 8 checkboxes; obs-spec-021: 7 metrics with SQL measurement; obs-spec-020: 20 metrics (performance/operational/functional) |
| **5. Hidden Constraints** | Environment assumptions documented: platform, scale limits, legacy data, pricing basis, single-user model | **PASS** | obs-spec-022: backward compatibility; obs-spec-021: Free/Pro gating, cost estimation; obs-spec-020: cross-platform, multi-instance, 1000-point limit |
| **6. Contradictory Refs** | **3 contradictions found**: (a) Tasks 2.23-2.24 marked TODO but code built; (b) obs-spec-020 has no master plan task; (c) obs-spec-020 §3 vs §6 on aggregation strategy | **FAIL** | Master plan tasks stale; phantom task for shipped feature; spec-internal design contradiction |

### Overall: 5 PASS / 1 FAIL

The sprint specs are strong on requirements fidelity — Trap 1 through Trap 5 all pass. The single **FAIL** is Trap 6 (Contradictory Refs), requiring:

1. **Update master plan tasks 2.23-2.24** from ⬜ TODO to ✅ DONE (or at minimum 🟡 PARTIAL with note)
2. **Add a master plan task entry** for obs-spec-020 (Token Analytics Dashboard) — possibly as Task 3.18.5 or a note under Phase 3
3. **Fix obs-spec-020 §6 Phase 1** to remove "Create token_aggregations table" (contradicts §3 on-the-fly design) or add a note explaining the decision