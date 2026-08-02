# obs-spec-092: Anomalies Inbox (P0.0 Signal Integrity + P0.1 Unified Feed)

**Status:** 🔴 Spec (2026-07-20) — New
**Product:** ObserveCo (Free + Pro)
**Depends on:** `l2_trending`, `chisel_drift`, `drift_events`, `clawforge_garden`, `circuit_breakers`, `token_logs`, `canary_runs`, `config_snapshots`, `errors`, alerts-center ack API, `anomaly/` module
**Owner:** Spectrum (design/spec) → Pragma (implementation)
**Visual contract:** `mockups/anomalies-inbox-v2.html` (browser-verified 2026-07-20, zero console errors)

---

## §1 Problem

ObserveCo has **nine signal sources** and no inbox. Live pass on the production fleet (2026-07-20, pulse.db 641MB, 39 agents) proved the cost:

1. **`/api/anomalies` returns raw JSON** (`{"ok":true,"anomalies":[...]}`) — the Anomalies tab is click-blocked by a `soon` badge, and that badge is accidentally load-bearing: unblocking it today renders a JSON dump.
2. **Detectors are siloed.** 10 agents circuit-tripped in the same 579-second window with an identical signature (19 trips each) — one upstream cause, rendered as 10 flat rows.
3. **Misclassification manufactures criticals.** The alert rail shows **29 CRITICAL** items; triage shows ~2 are real. `kanban` is flagged "dead in 111 pulse checks" but is a Hermes profile — idle, not dead. `blueprint` carries 23,300 stale circuit failures. Test entities (`test-config-agent`, 9,930 failures) feed the rail.
4. **No triage path.** Alert-center ack exists in the API but the rail offers ✕-only; there is no snooze, no bulk exclude, no "why am I seeing this."

**Goal:** one feed that reads across every detector, classifies before it alerts, folds correlated events, and makes every item answer *what is it, why does it matter, what do I do* — the activation moment from master-plan §33: *"your agent has 3 problems right now."*

---

## §2 What Already Exists (verified live 2026-07-20)

| Component | Status | Evidence |
|-----------|--------|----------|
| L2 trending (stuck, upstream_fail) | ✅ Real signals | `dreamer` stuck 834s critical; `hermes-agent` 4 upstream failures — but no nav surface |
| Drift detection | ✅ Real signals | `accelerator` memory +731.6%/7d, 181 breaches — raw table only |
| Canary runs + judge cache | ✅ Real signals | `default` went 0/10 (Jul 19) vs 47/60 (Jul 18) — undisplayed |
| Circuit breakers | ⚠️ Noisy | 8 circuits stale >7d, 1,996–23,300 failures each, still counted active |
| Anomaly detector (`anomaly/`) | ⚠️ Misclassifies | dead/retry_loop fire on idle profiles; JSON-only output |
| Garden scans | ❌ Stale | Last scan Jun 17 (33d) — detector dead, no surface noticed |
| OTEL data-quality tiering | ✅ Honest | 0/39 agents accurate; verdict chip reports it — nowhere actionable |
| Alert ack backend | ✅ Built | Alert-center API has ack; rail UI doesn't expose triage |
| **Unified, classified, triaged feed** | ❌ **Missing** | This spec |

**Reference context:** the So-What Card pattern (mockup `so-what-cards.html`) defines the 4-tone visual language (insight/watch/alert/neutral, 3px tone rule, mono micro-label). DPA §2-A (UNKNOWN ≠ CRITICAL), §2-B (verdict = sentence), §2-D (data-quality chips) are binding constraints, verbatim.

---

## §3 Architecture

### §3.1 Inbox Item Schema

One new table (first schema addition; all detectors already write their own tables — this is the *read-side normalization*):

```sql
CREATE TABLE IF NOT EXISTS inbox_items (
  id            TEXT PRIMARY KEY,        -- hash(class, agent, dedupe_key)
  agent_name    TEXT,                    -- NULL for fleet-wide items
  class         TEXT NOT NULL,           -- stuck|upstream_fail|drift_breach|canary_regress|
                                         -- circuit_event|retry_loop|spend_anomaly|dq_gap|stale_source
  tone          TEXT NOT NULL,           -- alert|watch|insight  (swc vocabulary)
  pillar        TEXT,                    -- quality|reliability|usage|memory  (obs-spec-093 §3.1 shared vocabulary)
  title         TEXT NOT NULL,           -- plain-English per obs-spec-093 §3.3 language rules; template-generated (no LLM)
  attribution   TEXT,                    -- "two consecutive all-fail runs — step change, not noise"
  evidence      TEXT NOT NULL,           -- JSON: {metrics: {...}, source_table, detector}
  actions       TEXT NOT NULL,           -- JSON: [{label, href|cmd, kind}]
  why_source    TEXT NOT NULL,           -- "source: l2_trending · detector: heal/l2.py"
  state         TEXT NOT NULL DEFAULT 'open',  -- open|acked|snoozed|triaged
  triage_reason TEXT,                    -- why auto-triaged (shown in drawer, reversible)
  first_seen    TEXT NOT NULL,
  last_seen     TEXT NOT NULL,
  occurrence    INTEGER NOT NULL DEFAULT 1,    -- repeat counter, folds dupes
  folded_count  INTEGER,                 -- set on correlation parents (fleet events)
  snoozed_until TEXT
);
CREATE INDEX IF NOT EXISTS idx_inbox_state_tone ON inbox_items(state, tone, last_seen DESC);
```

### §3.2 Detector Registry (read-side, no detector rewrites)

`inbox/registry.py` — each adapter maps one source table → normalized items:

| Adapter | Source | Item rule (live examples from 2026-07-20) |
|---------|--------|-------------------------------------------|
| `l2_adapter` | `l2_trending` | `stuck·critical` → alert; `stuck·warning`, `upstream_fail` → watch |
| `drift_adapter` | `chisel_drift` | 7d Δ >20% → watch; >50% → alert. Evidence: breaches, peak |
| `canary_adapter` | `canary_runs` | pass-rate step-change (prev run ≥60% → latest ≤10%, or 2 consecutive all-fail) → alert |
| `circuit_adapter` | `circuit_breakers` | tripped <7d → watch; **>7d + no recovery attempt → auto-triage "stale circuit"** |
| `anomaly_adapter` | `anomaly/` output | dead/retry_loop — **subject to §3.4 class rules before emitting** |
| `spend_adapter` | `token_logs` | >3σ daily spend, or >70% fleet concentration → insight |
| `dq_adapter` | `token_logs.source` | Tier-1 coverage <50% → insight (one standing item, not per-agent) |
| `garden_adapter` | `clawforge_garden` | latest scan older than cadence×3 → insight "stale source" (§3.7) |
| `config_adapter` | `config_snapshots` | **never emits items** — attribution join only ("same day as config change") |

### §3.3 Correlation Pass (the inbox's headline intelligence)

```python
def correlate(items: list[InboxItem]) -> list[InboxItem]:
    """Fold correlated children into one parent item.
    Rule: same class + first_seen within ±10m window + ≥3 distinct agents
      → parent: class=circuit_event, folded_count=N,
        title: "{N} agents {signature} in the same window — likely one
                upstream cause, not {N} incidents"
    Parent carries actions: [View the window →] [Split into N items] [Ack as one]
    Children remain in DB, state='folded', restorable via Split.
    """
```

Live validation: folds the 10-agent × 19-trip/579s event into 1 item. This is the difference between an anomaly *feed* and an anomaly *inbox*.

### §3.4 Classification Rules (P0.0 — gates §3.2 emission)

1. **Agent-class registry.** `agents.json` gains `class: daemon|profile|service|test` (default `daemon`; discovery sets `test` for config-scan orphans; user-overridable, fleet × flow already persists exclusions here).
2. **Profiles are activity-monitored.** `profile` class → no pulse probing; state derives from session activity. `idle` is a state, not a failure. (Fixes: kanban/workspace/spectrum false criticals — DPA §2-A enforced at the source.)
3. **Stale circuits reset.** Tripped >7d with no recovery attempt → auto-triage with reason; a `POST /api/circuits/{agent}/reset` re-baselines. Next genuine failure starts a fresh count.
4. **Test entities excluded** from monitoring + alerts (persisted, reversible).
5. **Cleanup surfacing.** When ≥2 classification fixes are available, the inbox renders the P0.0 cleanup card (mockup §cleanup) with per-fix blast radius and one-click apply. Expected effect stated honestly: "29 critical alerts → 2" on the current fleet.

### §3.5 Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/inbox` | **HTML partial** (htmx, Jinja `partials/inbox.html`) — replaces today's raw-JSON `/api/anomalies` render path |
| `GET /api/inbox/json` | Raw items (API consumers, debugging) |
| `POST /api/inbox/{id}/ack` · `/snooze` · `/restore` · `/split` | Triage mutations (ack reuses alert-center ack storage pattern) |
| `POST /api/inbox/cleanup/apply` | Applies checked P0.0 fixes (class reassign, exclude, circuit reset) |

`/api/anomalies` stays for back-compat but gains `Content-Type: application/json` discipline — never again wired to `hx-swap="innerHTML"`.

### §3.6 Verdict Sentence (DPA §2-B)

Computed **after** classification + correlation, never before:

```
"{A} issues need action — {W} worth watching, {T} auto-triaged as noise"
```

Counts derive from open items by tone. If A=0: "Fleet quiet — {W} worth watching." Counts alone are forbidden as the headline.

### §3.7 Meta-Monitoring (the inbox watches the detectors)

Any source table whose newest row is older than its cadence × 3 emits a `stale_source` insight item. Live validation: garden scans (cadence daily, last row Jun 17) → caught. This surfaces silent subsystem death that no per-agent detector can see.

---

## §4 Implementation

### Phase 1 — P0.0 classification (~150 lines, 0.5d)

| File | Change |
|------|--------|
| `agents.json` schema + discovery | Add `class` field; discovery marks config-scan orphans `test` |
| `anomaly/` dead-detection | Respect class: profiles → activity-based, skip pulse-death rule |
| `dashboard/routes/fleet.py` | Circuit reset endpoint; stale-circuit auto-triage in alert-center query |

### Phase 2 — Inbox core (~300 lines, 1d)

| File | Change |
|------|--------|
| `inbox/registry.py` (new) | 9 adapters per §3.2 |
| `inbox/store.py` (new) | `inbox_items` table, upsert-by-id, occurrence folding |
| `dashboard/routes/inbox.py` (new) | §3.5 endpoints; HTML partial render |
| `templates/partials/inbox.html` (new) | Port of verified mockup (tokens, swc tones, evidence drawer, triage drawer) |

### Phase 3 — Correlation + verdict (~120 lines, 0.5d)

| File | Change |
|------|--------|
| `inbox/correlate.py` (new) | §3.3 fold + split/restore |
| `dashboard/routes/inbox.py` | §3.6 verdict sentence in partial header |

### Phase 4 — Promotion (~20 lines)

Remove `soon` badge, place Anomalies in nav Monitor group (position 2, after Fleet), wire auto-refresh (60s, `every 60s` htmx, not `revealed once`).

**Stack discipline:** htmx + vanilla JS + Jinja partials — matches today's revamp patterns (42 partials, `/api/fleet/state` model). No React, no new build step.

---

## §5 Edge Cases

- **Cold start:** no detector has fired → empty state: "No anomalies detected. The inbox reads 9 sources — it will speak when one does." (Lists sources; never a blank panel.)
- **All noise:** everything auto-triaged → verdict "Fleet quiet — 13 filtered", drawer expanded by default once so the user learns the filter exists.
- **Ack persistence:** `inbox_items.state` survives restart (DB-backed, not localStorage — mockup's localStorage is demo-only).
- **False merge:** correlation parent carries "Split into N items" → children restore as individuals; split decision persisted per dedupe-key.
- **Class misassignment:** user reclassifies via fleet card ⋮ menu; override wins over discovery forever.
- **BYOK absent:** titles/attribution are deterministic templates — zero LLM dependency. LLM enrichment (future) may *rewrite* strings but never gates the feed.
- **Big fleet:** 100+ agents → adapters query with `LIMIT` + covering indexes; correlation is O(n) per window. Partial render target <500ms on 641MB pulse.db.

---

## §6 Pro Gating

- **Free:** full feed, ack, correlation folding, P0.0 cleanup, 7-day item retention
- **Pro:** snooze, push delivery (P1.2 dependency), config-diff attribution joins ("started same day as SOUL.md edit"), 90-day retention, `/api/inbox/json` export

---

## §7 Success Criteria

| Metric | Target | Current (2026-07-20 live) |
|--------|--------|---------------------------|
| Critical items shown on production fleet | ≤3 | 29 |
| Items carrying attribution + ≥1 action | 100% | 0% (no actions anywhere) |
| Correlated events folded | ≥3 agents/window → 1 item | 10 flat rows |
| Tab renders | HTML partial, no JSON leak | raw JSON |
| Partial render time (641MB DB) | <500ms | n/a |
| False "dead" alerts from profiles | 0 | 3 (kanban, workspace, spectrum) |
| Time-to-first-insight from dashboard open | <30s | never (tab blocked) |
