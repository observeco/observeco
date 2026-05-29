# Human Test Plan — ObserveCo Dashboard v2

**Purpose:** This document is the contract between human tester (Sean) and AI builder (Main). It defines exactly what to test on the rebuilt dashboard, how to deliver feedback, and what to skip.

**When to use:** After I confirm the dashboard is **style-frozen** (all remaining inline→CSS conversions done). Testing against mid-conversion layout breaks defeats the purpose.

---

## Feedback Protocol

### Required Format — One Issue Per Line

```
[SECTION]  landing | agent-drill | brain | heal | skills-audit | pathway | error-state
[ELEMENT]  The visible label, button, icon, or area
[LAYER]    perception | confidence | friction
[PROBLEM]  What's wrong, in human terms (1-2 sentences)
[EXPECTED] What you expected to see or happen (1 sentence)
```

### Examples

```
[LANDING] [Status row "13 alive"] [CONFIDENCE] No timestamp on the alive count — is this from 5s ago or 5h ago?
[LANDING] [Agent card health row] [PERCEPTION] Green dot next to "4d ago" — contradicting. Green usually means now.
[BRAIN] [Savings chart] [FRICTION] Changed provider dropdown, nothing updated until I clicked somewhere else.
[PATHWAY] [Graph nodes] [PERCEPTION] Node labels overlap each other when two agents have similar names.
[SKILLS-AUDIT] [Skills table] [CONFIDENCE] "Yearly cost" shows $0.00 for all skills — rate provider not selected?
```

### Bad Feedback (Will Be Rejected)

| Don't say | Why |
|---|---|
| "It feels off" | No anchor — I can't grep "off" |
| "Not modern" | No visual reference for "modern" |
| "Fix the layout" | Which layout? Which section? |
| "Animations are weird" | Which animation? What's the specific issue? |

---

## Architecture Overview (Test Context)

The dashboard is a **single FastAPI app** (`src/observeco/dashboard/server.py`) serving:
- **Main page** (`templates/index.html`) — htmx-driven, auto-refresh every 30s
- **Pathways** (`templates/pathway.html`) — Cytoscape.js graph inside an iframe modal

**Key pages/sections:**
| Section | Type | How to access |
|---|---|---|
| Landing | Main page | `http://localhost:9120/` |
| Agent drill-down | Modal | Click any metric row on an agent card |
| Brain Analysis | Inline tab | Tab on landing page — agent selector + token bars + savings chart + drift + timeline |
| Heal Check | Inline tab | Tab on landing page — loads heal log from `/api/heal-log` |
| Skills Audit | Modal | Trigger from agent card / Brain analysis |
| CHISEL Compression | Modal | Trigger from Brain analysis |
| OpenClaw Plugins | Modal | Trigger from Brain analysis |
| Pathway Map | Modal (iframe) | Button somewhere in the UI |

Auto-refresh: every 30s via htmx. Phase banners auto-detect onboarding state (Phase 0/1/2).

---

## Test Batches — Do In Order

### Batch A: Landing Page (12 min)

Open `http://localhost:9120/` and scan top to bottom **once**. Do not scroll back up. First impressions only.

| # | Look At | What To Notice | Layer |
|---|---|---|---|
| A1 | **Header** — brand logo + "ObserveCo · Fleet Dashboard" + tier badge | Does the header feel pinned/reliable? Is the tier badge meaningful or noise? | Perception |
| A2 | **Status row** — X alive, Y dead, Z errors (color-coded dots) + feedback button + "Add agent" button | Do these numbers feel current? Is the Add Agent button obvious or buried? | Confidence |
| A3 | **Phase banner** — top of page from `/api/phase` (Phase 0 / Phase 1 / Phase 2) | Does it explain current state clearly? If Phase 2 auto-fades after 8s, is the transition smooth? | Friction |
| A4 | **Error banners** — from `/api/error-state` inline above or interspersed | If present: actionable? If absent: does the empty state reassure? | Confidence |
| A5 | **Agent cards** — pick 3: one alive (accelerator), one dead (skeptical), one with data | Gradient card backgrounds, status dot (alive/dead/error), hide-toggle top-right, 5+ metric rows. Hover: does row highlight appear? | Perception |
| A6 | **Click a metric row** on any agent card | Does a drill-down modal open smoothly? | Friction |
| A7 | **Feedback bar** — click "Feedback" button in header | Does inline bar appear? Type something, pick category, click send. Does it POST? | Friction |
| A8 | **Collapsible sections** — click section header | Does it collapse/expand smoothly? Does section-count + total-tokens make sense? | Friction |

**Submit all A1–A8 feedback before touching Batch B.**

---

### Batch B: Agent Drill-Down Modal (5 min)

Click any **alive** agent card's metric row to open the drill modal.

| # | Action | What To Notice | Layer |
|---|---|---|---|
| B1 | Click a metric row | How fast does the modal open? Does it animate or snap? | Friction |
| B2 | **Modal content** — circuits table (status, type, trips), pulse timeline dots | Does the circuit hierarchy make sense? Are pulse dots (ok/warn/err) readable? | Perception |
| B3 | Close modal (+), click a different agent's row | Does the first modal close cleanly before the second opens? | Friction |

**Submit all B1–B3 before moving on.**

---

### Batch C: Brain Analysis (8 min)

Find the Brain tab on the landing page (tab bar with Health / Tokens / Brain / Heal).

| # | Action | What To Notice | Layer |
|---|---|---|---|
| C1 | Click **Brain** tab | Does it load `brainData` via `/api/brain`? Agent selector populated? Does "all" fleet show? | Friction |
| C2 | **Total tokens** display + component bars (skills, tools, memory, guidance, identity) | Are the 5 component colors distinct? Do percentages add up? | Perception |
| C3 | **Savings chart** — Original → Lite (Free) → Full (Pro) | Does $ savings/day update when you switch provider dropdown? | Confidence |
| C4 | **Savings calc** — 4 cards (% lite save, % full save, tokens saved/day, dollars saved/day) | Do numbers seem real? Do dollar columns show $0 when rate=0? | Confidence |
| C5 | **Drift charts** — SVG mini line charts per component | Do you understand what direction means (up=worse orange, down=better green)? | Friction |
| C6 | **Per-turn timeline** — bars at bottom, hover tooltips | Do tooltips appear on hover? Can you read token count? | Friction |
| C7 | **Pro upsells** — 3+ touchpoints in Brain, Skills Audit, Push Alerts | Do these look "locked feat" or "broken element"? Is upgrade path clear? | Perception |
| C8 | Click any locked upsell (e.g. "Push Alerts are Pro") | Does the Pro modal appear with feature list + CTA? | Friction |

**Submit all C1–C8 before moving on.**

---

### Batch D: Heal Check (3 min)

Click the **Heal** tab on the landing page.

| # | Action | What To Notice | Layer |
|---|---|---|---|
| D1 | Click Heal tab | Does it call `/api/heal-log` automatically? | Friction |
| D2 | Read heal log output | Is it actionable or just noise? | Confidence |

**Submit D1–D2 before moving on.**

---

### Batch E: Skills Audit (3 min)

Find the trigger to open Skills Audit (from an agent card or Brain section).

| # | Action | What To Notice | Layer |
|---|---|---|---|
| E1 | Open Skills Audit modal | Summary cards at top: skills installed, tokens/session, yearly cost, Pro savings | Perception |
| E2 | **Skills table** — rank, name + badge (ok/breach), composition bar, drift, last used, $/yr | Is any row showing a breach (red)? Does drift direction + percentage make sense? | Confidence |
| E3 | **Categories** section at bottom | By-category grouping — does it help? | Friction |

**Submit E1–E3 before moving on.**

---

### Batch F: Pathway Map (3 min)

Open the Pathway Map (button or trigger from the main page).

| # | Action | What To Notice | Layer |
|---|---|---|---|
| F1 | **Pathway modal/iframe** — bar with summary stats (nodes, 🟢, 🟡, 🔴) | Does the Cytoscape graph render quickly? | Friction |
| F2 | **Graph interaction** — click a node, drag a node, scroll to zoom | Does the right detail panel update? Does dragging feel responsive? | Friction |
| F3 | **Filter chips** — All / 🟢 Complete / 🟡 Concerns / 🔴 Dead Ends | Click each. Does graph refilter with animation? | Confidence |
| F4 | **Dead ends** — red dashed edges ending at "∅" node | Are dead ends visually obvious? Does clicking one show "messages will be lost" warning? | Perception |

**Submit F1–F4 before moving on.**

---

### Batch G: Error & Empty States (4 min)

This requires deliberately breaking the running dashboard.

1. Tell me to kill the watch daemon.
2. I'll stop it, you reload the page.
3. Then check:

| # | What To Notice | Layer |
|---|---|---|
| G1 | Does `/api/error-state` detect stale pulse (>2h) and show orange "Monitoring stopped Xh ago" banner? | Confidence |
| G2 | Do agent cards still render with stale data + last-seen timestamp? | Perception |
| G3 | After I restart daemon: does htmx auto-refresh show Phase 2 "system stabilised" banner that auto-fades? | Friction |
| G4 | Fresh install (no agents, no data): does Phase 0 banner show "Observing your system..." message? | Perception |

**Submit G1–G4.**

---

## What Not to Test (Covered by AI)

| Skip | Reason |
|---|---|
| Font sizes under 11px | CSS token-verified against DESIGN.md |
| All 12+ API endpoints return 200 | Break test script runs this every session |
| ARIA labels on interactive elements | Already passed |
| Dashboard on mobile viewport | v1 is desktop-only — acknowledged gap in master plan |
| Color contrast ratios | Design tokens are the spec |
| Agent card count accuracy | Data-dependent, SQL is correct |
| Modal close/hide mechanics | Script-verified |
| htmx auto-refresh timing | Script-verified |

---

## Feedback Submission

**Two channels, your choice:**

1. **Telegram DM** — send each issue as a separate message using the format above. I'll process in order.
2. **Batch list** — collect all issues from one batch into a single message. I'll still process each.

**Recommended flow:** Test Batch A → send all A issues → wait for my fix → test Batch A again → proceed to Batch B. This catches regressions fast.

**Do not skip the sequence.** Batch A fixes may affect Batch B rendering. If you test B before A is fixed, you'll report issues A already addressed.

---

## What Happens After You Test

1. I process each issue by SECTION + LAYER
2. Fixes ship as CSS changes (perception/friction) or backend changes (confidence)
3. Break test script re-runs to verify no regressions
4. I confirm fixes deployed, tell you to re-test the affected batch
5. Cycle repeats until all batches pass your standard

No kanban tasks. No tickets. This doc is the contract.