# ObserveCo v2 Strong-Fit Dashboard Migration

**Date:** 2026-07-04
**Source:** `design/` (June 30 files — Fleet Prototype, All States, So What Card, Agent Detail Modal, Token Analytics, Data Presentation Architecture, tokens.css)
**Target:** Replace `index.html` with v2 Strong-Fit design, migrate all backend routes to serve HTML partials matching the new design system.

## Design Tokens (from `design/tokens.css`)

All components share these tokens. Must be in `:root` of the final template.

```
--bg, --surface, --surface-hover, --surface-active
--border, --border-soft
--status-healthy, --status-warning, --status-critical, --status-info
--token-identity, --token-skills, --token-memory, --token-tools, --token-guidance
--fg, --fg-2, --fg-3
--accent, --accent-on, --warn, --danger, --meta
--font-sans, --font-mono
--text-xs, --text-sm, --text-base, --text-lg, --text-xl
--space-1 through --space-16
--radius-sm, --radius-md, --radius-lg, --radius-pill
--elev-flat, --elev-ring, --elev-raised
--motion-fast, --motion-base, --ease-standard
```

## Phase 1: Foundation — Template + Nav + Verdict Bar

**Scope:** Replace `index.html` with `index_new.html` as the base template. Add domain-grouped nav. Add sticky verdict bar with data quality chip.

**Files:**
- `src/observeco/dashboard/templates/index.html` — Replace with v2 layout
- `src/observeco/dashboard/static/observeco-dashboard.css` — Add v2 CSS classes
- `src/observeco/dashboard/routes/fleet.py` — Update verdict bar endpoint

**Components:**
- `.topbar` — Logo + daemon status
- `.nav` — Domain-grouped: Monitor (Fleet, Alerts, Error Timeline), Analyze (Tokens, Brain, Drift, Compare), Intelligence (Anomalies, Health Score, Traces), Settings (Config, Billing)
- `.verdict` — Sticky bar with icon, text sentence, meta chips (agent count, tripped count, discovery gap, data quality)
- `.vchip` — Agent count chip
- `.dqchip` — Data quality chip (otel vs watch)

**Backend changes:**
- `GET /api/fleet/verdict` — Return v2 verdict bar HTML with data quality computation
- `GET /api/partials/nav` — Return domain-grouped nav HTML

**States:** Loading (skeleton verdict), Empty (no agents), Error (daemon down), Data (populated)

## Phase 2: Fleet View — Agent Cards

**Scope:** Replace agent card rendering with v2 collapsible cards.

**Files:**
- `src/observeco/dashboard/routes/fleet.py` — Update agent card HTML
- `src/observeco/dashboard/static/observeco-dashboard.css` — Add card CSS

**Components:**
- `.card` — Collapsible agent card with `.crit`/`.warn`/`.healthy` left border
- `.card-collapsed` — Status dot, agent name, error badge, token count + drift, data quality dot, chevron
- `.card-detail` — Expandable rows: Health, Guard, Errors, Brain, Compose
- `.crow` — Row with label + value + sub
- `.pulse-mini` — 6-dot pulse indicator (a=alive, e=error, d=dead)
- `.tokbar` — 5-segment token composition bar (identity/skills/memory/tools/guidance)
- `.health-panel` — Inline mini-panel with 6-pulse bar chart + latency + confidence badge
- `.dqdot` — Data quality dot (acc=green, est=amber)

**Backend changes:**
- `GET /api/fleet/agents` — Return agent cards with v2 HTML
- `GET /api/agent-detail/{name}?tab=health` — Return health panel HTML

**States:** Loading (skeleton cards), Empty (no agents discovered), Error (daemon down), Data (populated)

## Phase 3: Alerts Rail

**Scope:** Add right-side alerts rail with gap banner and severity groups.

**Files:**
- `src/observeco/dashboard/routes/alerts.py` — Already exists, update HTML to v2
- `src/observeco/dashboard/static/observeco-dashboard.css` — Add alerts CSS

**Components:**
- `.gap-banner` — Discovery gap summary (big number + description)
- `.panel` — Alerts panel container
- `.panel-h` — Panel header with title + count
- `.agroup-h` — Severity group header (CRITICAL/WARNING/INFO)
- `.alert` — Alert row with left border, agent name, message, gap badge
- `.allclear` — Empty state when no alerts

**Backend changes:**
- `GET /api/alerts2` — Already exists, update HTML to v2

**States:** Loading (skeleton), Empty (all clear), Error, Data (alerts present)

## Phase 4: Error Timeline

**Scope:** Add Gantt-style error timeline below fleet view.

**Files:**
- `src/observeco/dashboard/routes/timeline.py` — Update error timeline endpoint
- `src/observeco/dashboard/static/observeco-dashboard.css` — Add timeline CSS

**Components:**
- `.tl-rows` — Timeline container
- `.tl-row` — Row with time, agent, message, Gantt track, duration
- `.tl-track` — Duration bar with severity color
- `.tl-axis` — Time axis below timeline

**Backend changes:**
- `GET /api/timeline/errors` — Return v2 error timeline HTML

**States:** Loading (skeleton rows), Empty (no errors), Error, Data (events present)

## Phase 5: Agent Detail Modal

**Scope:** Add modal with 5 tabs (Health, Guard, Errors, Tokens, Memory).

**Files:**
- `src/observeco/dashboard/routes/detail.py` — Update agent detail endpoint
- `src/observeco/dashboard/static/observeco-dashboard.css` — Add modal CSS

**Components:**
- `.scrim` — Modal backdrop
- `.modal` — Modal container
- `.m-head` — Header with status dot, name, badge, framework, close button
- `.m-tabs` — Tab bar (Health, Guard, Errors, Tokens, Memory)
- `.m-body` — Tab content area
- `.pulse48` — 48-dot pulse grid (24 columns × 2 rows)
- `.latline` — Latency bar chart
- `.ftl` — Failure timeline (guard tab)
- `.compbar` — Component breakdown bars (tokens tab)
- `.debt-head` — Memory debt score + trend (memory tab)
- `.mstat` — Memory stats grid

**Backend changes:**
- `GET /api/agent-detail/{name}?tab=health|guard|errors|tokens|memory` — Return v2 tab HTML

**States:** Loading, Empty, Error, Data for each tab

## Phase 6: Token Analytics Page

**Scope:** Add full token analytics page with charts, attribution, cost table.

**Files:**
- `src/observeco/dashboard/routes/tokens.py` — New endpoint for token analytics
- `src/observeco/dashboard/static/observeco-dashboard.css` — Add token analytics CSS

**Components:**
- `.so` — So What insight card (4 tones)
- `.grid2` — Two-column grid for chart + attribution
- `.panel` — Chart/attribution panel
- `.chart-box` — Chart.js container
- `.attr-ring` — Attribution gap display
- `.tblwrap` — Table wrapper
- `.tbl` — Per-agent cost table
- `.comp-row` — Composition bar per agent
- `.cache-row` — Cache efficiency bar per agent
- `.cache-mini` — Mini cache bar

**Backend changes:**
- `GET /api/token-analytics?agent=&days=` — Return v2 token analytics HTML

**States:** Loading, Empty, Error, Data

## Phase 7: All States Integration

**Scope:** Ensure every component handles loading, empty, error, and populated states.

**Files:** All route files

**Components:**
- `.skel` — Shimmer animation skeleton
- `.skel-card` — Skeleton card
- `.empty-card` — Empty state card with icon, message, CTA
- `.state-msg` — Error state with icon, message, recovery command
- `.state-msg.err` — Error variant

## Build Order

1. Phase 1: Foundation (template + nav + verdict) — **Forge**
2. Phase 2: Fleet view (agent cards) — **Forge**
3. Phase 3: Alerts rail — **Forge**
4. Phase 4: Error timeline — **Forge**
5. Phase 5: Agent detail modal — **Forge**
6. Phase 6: Token analytics — **Forge**
7. Phase 7: All states integration — **Forge**
8. Audit: Spec-playbook audit on all phases — **Main**

## Audit Gates

Each phase must pass:
- `pytest` — 0 failures
- `python3 -c "import ast"` — All files parse
- Spec-playbook audit — No CRITICAL/HIGH findings
- Visual parity check against v2 mockups

## Audit Findings (from spec-playbook audit, 2026-07-04)

**Master Fidelity Gate: 19/60 (FAIL).** Key findings fixed before Phase 1 build:

### CRITICAL (fixed)
1. `GET /api/partials/nav` endpoint missing — `index_new.html` calls hx-get but no route exists. Fix: register route or use static nav fallback.

### HIGH (fixed)
2. `.latline` CSS class missing — latency bars in detail.py Health tab render unstyled. ✅ Added to observeco-dashboard.css
3. `tripled` typo in detail.py:157 — would raise NameError on Guard tab. ✅ Fixed to `tripped`
4. `.health-panel` hallucinated — component described in plan doesn't exist in code. Fix: remove from plan.

### MEDIUM (fixed)
5. Endpoint path mismatches: plan says `/api/agent-detail/{name}`, actual is `/api/fleet/modal/{agent_name}`. Plan says `/api/token-analytics`, actual is `/api/analytics/tokens`.
6. Stray quote in detail.py:123 — trailing `"` renders as visible text. ✅ Fixed

### LOW
7. `.so` vs `.swc` class name mismatch in plan
8. `.tl-axis` component doesn't exist
9. `.skel-card` not in shared CSS
10. `/new` vs `/` serving — both templates coexist
