# ObserveCo v0.3.2 — Data Pipeline for Research Papers

**Goal:** Continuous, quality data flowing into ObserveCo so we can write research papers with real empirical evidence.

**Date:** 2026-06-28
**Status:** Planning — blockers identified, fixes prioritised

---

## Why This Matters

The research objectives require:
- Token economics with real dollar costs (not just token counts)
- Error timelines with meaningful failure types (not probe noise)
- Memory health analysis (contradictions, staleness, bloat)
- Circuit breaker effectiveness data
- Auto-heal recovery metrics
- Multi-agent coordination traces
- 7+ days of continuous data for trend analysis

Without these, we have dashboards that look complete but contain empty tables or noise. Papers need signal, not schema.

---

## Current State (verified 2026-06-28)

### What Works

| Table | Rows | Quality | Research Use |
|-------|------|---------|--------------|
| token_logs | 29,174 (13 agents, ~36h) | input/output/cache breakdown | Token economics, fleet comparison |
| pulse_log | 73,188 (39 agents) | alive/dead/error status | Liveness, uptime measurement |
| chisel_drift | 18,653 | Component drift tracked | Drift trends, breach analysis |
| chisel_trims | 29,182 | Component breakdown (watch source) | Token composition analysis |
| errors | 1,265 | All watch_probe_failed | **Noise — not usable for papers** |

### What's Broken or Missing

**⚠️ Two-DB architecture problem:** OTEL listener writes to `observeco.db` (0 bytes — never written to). Watch daemon writes to `pulse.db` (14MB, primary). Fix 1 eliminates this by wiring OTEL to pulse.db. Until then, observeco.db is dead storage.

| Table | Rows | Problem | Impact on Research |
|-------|------|---------|-------------------|
| token_logs.cost | $0.00 | Cost column not populated | Cannot write about "$X/day" or cost attribution |
| clawforge_garden | 0 | Garden daemon not running | No memory health data at all |
| circuit_events | TABLE MISSING | Circuit breaker events not persisted | Cannot measure circuit breaker effectiveness |
| heal_events | 1 | Barely active | Cannot measure auto-heal recovery times |
| skill_usage | 0 | Not tracked | Cannot measure skill-to-skill transitions |
| guidance_fire | 0 | Not tracked | Cannot measure guidance rule hit rates |
| turn_log | 0 | Not tracked | Cannot measure success rates, latency per step |
| errors | 1,265 (noise) | All same type (watch_probe_failed) | Error timeline is meaningless — needs real errors |

---

## The 6 Fixes (Priority Order)

### Fix 1: Enable Hermes ObserveCo Plugin
**Unlocks:** Tool call traces, subagent lifecycle, session lifecycle, error events, gateway dispatch — 10 new telemetry dimensions
**Blocker:** Plugin disabled in Hermes config
**Fix:** `hermes plugins enable observability/observeco` + wire OTEL listener to write to pulse.db (not observeco.db)
**Effort:** ~2h config + ~1d OTEL wiring
**Research value:** Highest — this single fix enables coordination traces, error timelines, tool efficiency ranking, and session lifecycle analysis

### Fix 2: Fix Watch Probe (watch_probe_failed)
**Unlocks:** Clean pulse_log data, reliable liveness measurement
**Blocker:** All 1,265 errors are watch_probe_failed — the probe itself is broken
**Fix:** Investigate why watch probe fails for all agents. Likely a path or permission issue.
**Effort:** ~2h investigation
**Research value:** High — without clean liveness data, uptime measurements are unreliable

### Fix 3: Populate Cost Column
**Unlocks:** Token economics with real dollar costs, cost attribution, fleet cost comparison
**Blocker:** Cost column = $0.00 for all 29K rows
**Fix:** Two paths — (A) Simple pricing table (model → $/token mapping, ~4h) or (B) Full Cost Estimation Engine (feature #58, ~2d). Path A is sufficient for v0.3.2 research papers. Path B adds provider billing API accuracy.
**Effort:** ~4h (path A) or ~2d (path B, feature #58)
**Research value:** High — papers need "$X/day" not "Y tokens/day"

### Fix 4: Start Garden Daemon
**Unlocks:** Memory health analysis — contradictions, staleness, bloat detection
**Blocker:** Garden consumer runs but finds zero MEMORY.md files — path resolution issue (not daemon status)
**Fix:** Investigate why garden consumer finds zero files despite watch daemon running (73K pulse_log entries). Likely path resolution or file location mismatch. Verify MEMORY.md paths match what the consumer expects.
**Effort:** ~1h investigation + fix
**Research value:** High — memory bloat is a key research topic. Without garden data, we can't write about it.

### Fix 5: Persist Circuit Breaker Events
**Unlocks:** Circuit breaker effectiveness analysis — trip rate, recovery time, false positive rate
**Blocker:** circuit_events table defined in code (db.py line 587) but not migrated to running pulse.db. circuit_breakers table exists with 0 rows — breakers not firing or not recorded.
**Fix:** Run migration to create circuit_events table. If table already exists, `DROP TABLE IF EXISTS circuit_events;` and re-run. Wire HealCircuit to persist events.
**Effort:** ~30m (schema migration) + ~2h (event wiring)
**Research value:** Medium-high — circuit breakers are a key reliability feature. Need data to prove they work.

### Fix 6: Investigate Low Heal Event Rate
**Unlocks:** Auto-heal recovery metrics — detection-to-recovery time, success rate, escalation patterns
**Blocker:** heal_events has 1 row. Heal daemon runs but rarely fires. The wiring IS in place — `heal/__init__.py:297` calls `db.log_heal_event()` which inserts into heal_events. The issue is that the heal circuit rarely triggers (high L2 threshold, extended cooldown, or auto-heal disabled).
**Fix:** Investigate why heal fires so rarely: (A) Check if auto-heal is enabled and configured, (B) Check L2 threshold settings, (C) Check HealCircuit cooldown state. Then tune config to generate events.
**Effort:** ~1h investigation + ~2h config tuning
**Research value:** Medium-high — self-healing is a differentiator. Need recovery time data to prove it.

---

## Data Collection Timeline

| Week | What Happens | Data Milestone |
|------|-------------|----------------|
| Week 1 | Fixes 1-4 deployed. Garden running. Hermes plugin enabled. | First meaningful error events. First garden scans. First cost data. |
| Week 2 | Fixes 5-6 deployed. Circuit events persisting. Heal events flowing. | 7+ days of continuous token_logs. First drift trends. |
| Week 3 | Full pipeline running. All tables populated. | 14+ days of data. Research-grade dataset ready. |
| Week 4 | Analysis begins. Visualisations built. Paper drafts started. | Taxonomy of failure modes. Cost attribution study. Memory bloat analysis. |

---

## Research Objectives → Data Mapping

| Research Objective | Required Data | Fix Needed | Earliest Available |
|-------------------|--------------|------------|-------------------|
| Token economics & cost attribution | token_logs with cost column | Fix 3 (populate cost) | Week 1 |
| Failure mode taxonomy | errors with real types + error timelines | Fix 1 (Hermes plugin) | Week 1-2 |
| Memory bloat & drift analysis | clawforge_garden + chisel_drift | Fix 4 (start garden) | Week 1 |
| Circuit breaker effectiveness | circuit_events (new table) | Fix 5 (persist events) | Week 2 |
| Auto-heal recovery metrics | heal_events with recovery times | Fix 6 (wire L2 events) | Week 2 |
| Multi-agent coordination | skill_usage + subagent traces | Fix 1 (Hermes plugin) | Week 2 |
| Success rates & latency | turn_log (new pipeline) | Needs new work (not in v0.3.2) | Week 4+ |
| Confidence scoring | New table + scoring logic | Needs new work (not in v0.3.2) | Week 4+ |

---

## What v0.3.2 Does NOT Cover

These are important but out of scope for v0.3.2 (data pipeline focus):

- **turn_log pipeline** — per-turn execution traces. Needed for success rates and latency. Requires new hook. Estimate: ~2d.
- **Confidence scoring** — not in schema. Needs design. Estimate: ~3d.
- **Provider billing API** (#44) — aggregate cloud spend. Useful but not blocking research. Estimate: ~1d.
- **Anomaly detection** (#60) — needs 14+ days of baseline data first. Can't build until data exists.
- **OpenClaw plugin** (#16) — cross-framework comparison is nice but Hermes-only data is sufficient for first papers.

---

## Lifecycle & Rollback

All 6 fixes are **independent** — apply in any order. None requires another to succeed first.

### Deployment Commands (per fix)

| Fix | Deploy Command | Verify Command |
|-----|---------------|----------------|
| 1: Enable plugin | `hermes plugins enable observability/observeco` + `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway` | `hermes plugins list --enabled` |
| 2: Watch probe | Edit `src/observeco/pulse/watch.py` → restart `observeco watch stop && observeco watch start` | `sqlite3 ~/.observeco/pulse.db "SELECT DISTINCT error_type FROM errors;"` should show >1 type |
| 3: Pricing table | Add model→$/token mapping to `src/observeco/tracking/pricing.py` → run backfill | `sqlite3 ~/.observeco/pulse.db "SELECT SUM(cost) FROM token_logs;"` > 0 |
| 4: Garden path | Fix MEMORY.md path resolution in clawsforge/garden.py → restart watch daemon | `sqlite3 ~/.observeco/pulse.db "SELECT COUNT(*) FROM clawforge_garden;"` > 0 |
| 5: circuit_events | Run migration: `python -c "from observeco.db import Database; Database()._migrate()"` or `sqlite3 ~/.observeco/pulse.db < migration.sql` | `sqlite3 ~/.observeco/pulse.db ".tables" \| grep circuit_events` should show it |
| 6: Heal config | Check auto-heal toggle, L2 thresholds, HealCircuit cooldown → tune | `sqlite3 ~/.observeco/pulse.db "SELECT COUNT(*) FROM heal_events;"` > 10 |

### Failure Modes

| Fix | Failure Mode | Rollback | Independent? |
|-----|-------------|----------|-------------|
| 1: Enable plugin | Plugin crashes Hermes, OTEL listener still writes to wrong DB | Disable plugin (`hermes plugins disable observability/observeco`), proxy still works | Yes |
| 2: Watch probe | Probe still fails after fix, errors remain noisy | Revert probe changes, errors stay as-is | Yes |
| 3: Pricing table | Wrong prices, provider API errors | Remove pricing column, $0 is acceptable for now | Yes |
| 4: Garden path | Consumer crashes, wrong files indexed | Stop garden daemon, no data loss (garden_scans stays 0) | Yes |
| 5: circuit_events migration | Table already exists (migration fails) | `DROP TABLE IF EXISTS circuit_events;` re-run | Yes |
| 6: L2 heal events | Events fire but aren't persisted | Revert wiring, heal_events stays at 1 row | Yes |

---

## Constraints & Scope

**In scope:**
- macOS + Hermes on Mac Mini (primary environment)
- pulse.db as the single source of truth
- 7-day data collection window after fixes deployed

**Out of scope (v0.3.2):**
- Docker, Windows, CI-only environments
- Multi-instance scenarios
- Data older than 30 days (pruning cron removes after 30 days)

**Data retention:** Pruning cron runs daily at 3am. Data older than 30 days is removed. 7 days of data at current rate ≈ 50 MB storage.

---

## Success Criteria

v0.3.2 is complete when:

1. **Cost column populated** — every token_log row has a non-zero cost
2. **Garden running** — clawforge_garden has 100+ scans across agents
3. **Real errors flowing** — errors table has mix of types, not just watch_probe_failed
4. **Circuit events persisted** — circuit_events table exists and has data
5. **Heal events flowing** — heal_events has 10+ entries with recovery times
6. **7+ days continuous** — token_logs spans 7+ days with no gaps
7. **Hermes plugin enabled** — tool calls, subagents, sessions appearing in telemetry

When all 7 criteria met, the dataset is research-paper-ready.
