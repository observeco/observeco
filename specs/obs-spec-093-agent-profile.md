# OBS-SPEC-093 — Agent Detail Modal v2 (Four-Pillar Profile)

**Status:** Draft — approved for build (mockup v4 approved 2026-07-21)
**Product:** ObserveCo dashboard — Fleet agent detail modal
**Depends on:** obs-spec-092 (inbox action links land here); obs-spec-069 (original modal — this supersedes its UI layer)
**Owner:** Pragma (backend + wiring) · Spectrum (design authority)
**Design authority:** `mockups/agent-profile-v4.html` (operator layer) + `mockups/agent-profile-v2.html` (technical tab internals)

---

## 1. Problem

The live modal fails the operator on three axes, all confirmed against live data (2026-07-20):

1. **Wrong verdict.** hound rendered "Healthy" while its latest benchmark was 1/3 passing and probe latency exceeded its own cadence. The verdict contradicted the evidence on the same screen.
2. **Wrong language.** Top layer speaks infra ("watch_probe_failed — database is locked", "+408.0% drift", raw floats like `33982.75375366211ms`). Sean's review: "too technical for a user operator."
3. **Missing dimension.** Quality (benchmark/canary) data exists in the backend but has no surface in the modal at all. Reliable ≠ good — the modal only showed reliable.

Formatting defects also confirmed live: "7s ago ago" duplication, Errors tab header "0 events — clean" while listing 1 row, guidance drift baseline disagreement (modal +408% vs fleet summary +21.4%).

## 2. What Exists

| Asset | Location | State |
|---|---|---|
| Live modal (6 tabs, raw data) | `GET /api/fleet/modal/<agent>` (~9–11KB HTML) | Working, no synthesis layer |
| Benchmark runner + status | `canary_runs`, `/api/capability/canary/status?agent=` | Live; UI already renamed canary→"benchmark" |
| Garden health | `clawforge_garden` (+log, +outcomes) | Live; data stale (last scan Jun 17) |
| Token composition + drift | `token_logs`, `chisel_drift`, `/api/drift-summary` | Live; two baselines disagree |
| Reliability signals | `pulse_log`, `errors`, `circuit_breakers`, `l2_trending`, Guard | Live |
| Detector registry (9 read-side adapters) | spec-092 §3.2 | Spec'd; feeds issue cards |
| Config attribution | `config_snapshots` | Live; never emits alone |
| Approved mockups | `mockups/agent-profile-v4.html`, `-v2.html` | Design authority |

## 3. Architecture

### 3.1 The four-pillar model (shared vocabulary)

The modal's top layer is a projection of four pillars. **This model is the shared per-agent vocabulary across three surfaces** — modal tiles, inbox item framing (spec-092), and fleet so-what cards. One model, three surfaces.

| Pillar | Operator question | Sources | Value format |
|---|---|---|---|
| **Quality** | "Is the work good?" | `canary_runs` | "N of M" tasks passed, latest run + trend |
| **Reliability** | "Is it up?" | `pulse_log`, `errors`, `circuit_breakers`, `l2_trending`, Guard | "% checks passing" (24h) |
| **Usage** | "What's it costing?" | `token_logs` (+ pricing) | tokens/day + $; composition in drawer |
| **Memory** | "Is it forgetting?" | `clawforge_garden` | debt score or days-since-scan |

**Drift is a modifier, not a pillar.** A pillar is an independent failure mode with its own operator question; drift is a cause that always lands on one of the four (guidance drift → Usage chip; config drift → Quality context). Rendered as a tile modifier chip (`↗ grew 4× this week`), never a tile.

### 3.2 Composite endpoint — `agent_profile_service`

New `GET /api/agent/<name>/profile` replacing the six per-tab fetches. One response:

```
{ status_line, status_sub,
  pillars: [{key, label, value, sub, state: ok|attention|unknown|unset,
             modifier?, sources: [...]}],
  needs_attention: [{icon, title, why, actions[]}],
  worth_knowing: [...], doing_well: [...],
  drawer: {quality: [rows], reliability: [rows], usage: [rows], memory: [rows]} }
```

Verdict and issue sentences are **template-generated server-side with computed slots** (no LLM in the render path). `_so_what_insights()` in `routes/fleet.py` is the pattern reference; the profile service owns agent-scope synthesis and fleet.py keeps fleet-scope.

### 3.3 Language layer (binding rules)

| Never at top layer | Always at top layer |
|---|---|
| canary | quality check / benchmark |
| guidance component | instruction file |
| +408% | grew 4× |
| watch_probe_failed — database is locked | the monitor got briefly stuck |
| probe latency / cadence | health checks running slow |
| SQLite contention / WAL | (drawer only) |

Technical terms live in the drawer, grouped by pillar, each group headed `PILLAR ← source_table(s)`. Every issue card answers **what happened → why it matters → what to press**, in that order. spec-092's item copy gets the same rules (patch §3.2 note).

### 3.4 Tile states

- `ok` — normal border, green value
- `attention` — tone border (amber/red), drives status line
- `unknown` — **dashed border**, "health unknown" copy; never render stale data as clean (hound's garden: 33 days stale shows "33 days", not debt 0)
- `unset` — feature never configured → CTA state ("No quality checks yet — set one up →"), which is the adoption funnel for benchmarks/garden on the 29 watch-only agents

### 3.5 Traceability

Every tile carries `details ›` opening the drawer at its pillar group. Every drawer row names its source table and raw values. The glanceable number and its evidence are one click apart — this backs every verdict the status line makes.

### 3.6 Formatting contract (fixes confirmed live defects)

1. Human numbers: `34.0s`, `41s`, never `33982.75375366211ms`
2. No duplicated units: "7s ago", never "7s ago ago"
3. Count honesty: header count must equal rendered rows (Errors tab said 0, showed 1)
4. Verdict consistency: the status line must not contradict any visible evidence ("healthy" beside 1/3 is a bug, not a choice)
5. **One drift baseline:** rolling 7d is canonical everywhere; the modal's first-seen baseline (+408% vs +21.4% same agent, same week) is a backend defect — reconcile in `chisel_drift` computation, flag as P0.3-adjacent fix

## 4. Implementation

| File | Change | Est. lines |
|---|---|---|
| `src/observeco/dashboard/services/agent_profile_service.py` | New: pillar assembly, status-line synthesis, drawer rows, state logic (§3.4) | ~260 |
| `src/observeco/dashboard/routes/fleet.py` | Add `/api/agent/<name>/profile`; keep `/api/fleet/modal/` for drawer tab content during transition | ~45 |
| `src/observeco/dashboard/templates/partials/c-modal-profile.html` | New: v4 structure (status, tiles, issues, well, drawer) | ~190 |
| `src/observeco/dashboard/static/dashboard.css` | Tile states (dashed unknown), modifier chip, drawer groups | ~80 |
| `tests/test_agent_profile.py` | Pillar states, unknown/unset logic, formatting contract, verdict-consistency invariant | ~130 |

htmx pattern unchanged: modal shell loads composite once; drawer reuses existing tab partials lazily beneath the pillar groups.

## 5. Edge Cases

- **Agent down:** status line leads with down state; tiles show last-known values with "as of HH:MM" — never blank
- **Watch-only agents:** `unset` states + CTAs; no fabricated pillar values
- **No benchmark runs ever:** Quality = `unset`, not 0%
- **Garden never scanned:** Memory = `unknown` with days-since copy; `auto-scan off` note in drawer
- **Benchmark currently running:** Quality tile shows "check running…" (canary status endpoint exposes `running`)
- **Slow probe latency as only signal:** worth-knowing, not needs-attention (hound precedent: agent was never down)
- **spec-092 inbox links:** action URLs carry `#pillar=quality` anchor; modal opens drawer at that group

## 6. Pro Gating

Matches existing gating: watch-only tier sees status line + Reliability pillar + upgrade prompt. Full four pillars, issue cards, and drawer require monitored tier. No new gates introduced.

## 7. Success Criteria

| # | Criterion | Measure |
|---|---|---|
| 1 | Operator comprehension | Non-engineer answers "is it okay / what's wrong / what do I press" in 5s from the top layer alone |
| 2 | Quality surfaced | Benchmark result present on every monitored agent's modal (was: absent entirely) |
| 3 | Verdict consistency | Status line never contradicts any tile/issue on the same render (test-covered invariant) |
| 4 | Formatting contract | Zero instances of the four named defect classes (float ms, ago-ago, count≠rows, dual drift baselines) |
| 5 | Traceability | Every tile value resolves to a drawer row naming source table + raw values |
| 6 | Shared vocabulary | Inbox items, so-what cards, and modal tiles use identical pillar names and language rules |
| 7 | Performance | Composite endpoint < 500ms at 641MB pulse.db (single connection, batched queries — fleet batching pattern) |
