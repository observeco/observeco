# Human Test Plan — ObserveCo Dashboard

**Purpose:** This document is the contract between human tester (Sean) and AI builder (Main). It defines exactly what to test, how to deliver feedback, and what to skip.

**When to use:** After I confirm the dashboard is **style-frozen** (all remaining inline→CSS conversions done). Testing against mid-conversion layout breaks defeats the purpose.

---

## Feedback Protocol

### Required Format — One Issue Per Line

```
[SECTION]  landing | agent-card:<name> | detail:<tab> | pathway | code-graph
[ELEMENT]  The visible label, button, icon, or area
[LAYER]    perception | confidence | friction
[PROBLEM]  What's wrong, in human terms (1-2 sentences)
[EXPECTED] What you expected to see or happen (1 sentence)
```

### Examples

```
[LANDING] [Fleet stat "13 Alive"] [CONFIDENCE] No timestamp on the alive count — is this from 5s ago or 5h ago?
[AGENT-CARD:hound] [Health row] [PERCEPTION] Green dot next to "4d ago" — contradicting. Green usually means now.
[DETAIL:health] [Circuit status] [FRICTION] Tapped "See details" on hound, waited 800ms before panel appeared — felt stuck.
[PATHWAY] [Graph nodes] [PERCEPTION] Node labels overlap each other when two agents have similar names.
[CODE-GRAPH] [Search input] [FRICTION] Typed a symbol name, nothing happened until I pressed Enter — should search as I type.
```

### Bad Feedback (Will Be Rejected)

| Don't say | Why |
|---|---|
| "It feels off" | No anchor — I can't grep "off" |
| "Not modern" | No visual reference for "modern" |
| "Fix the layout" | Which layout? Which section? |
| "Animations are weird" | Which animation? What's the specific issue? |
| "This looks outdated" | Compared to what? Point to a specific element. |

---

## Test Batches — Do In Order

### Batch A: Landing Page (10 min)

Open `http://localhost:9120/` and scan top to bottom **once**. Do not scroll back up. First impressions only.

| # | Look At | What To Notice | Layer Focus |
|---|---|---|---|
| A1 | **Header bar** — brand, refresh indicator, action buttons | Does the header feel sticky/reliable? Is the "Add agent" button obviously clickable? | Perception |
| A2 | **Fleet stats row** — X alive, Y dead, Z errors, drift badge | Do these numbers make sense at a glance? Are they current? Do you trust them? | Confidence |
| A3 | **Agent cards** — pick 3: one alive (accelerator), one dead (skeptical), one with gap badges (aleph) | Open each. Compare visual weight of alive vs dead. Do gap badges ("No tokens") look like badges or broken elements? | Perception |
| A4 | **Agent card content** — health row, guard row, errors row, brain size, composition | Scan all 5 rows on one card. Do you understand what each row tells you? Read "Brain size" — is it clear? | Confidence |
| A5 | **Alerts / heal section** — below agent cards | Is there content? If empty, does it explain why? Is the "Run Heal Check Now" button visible? | Friction |
| A6 | **Pro tiles** — right sidebar | Do these look "you could unlock this" or "broken feature"? Is the upgrade path clear? | Perception |
| A7 | **Error banners** — above or interspersed | See any red/yellow banners? If yes, do they tell you what to do? If no, is the empty state reassuring? | Confidence |

**Submit feedback for all A1-A7 issues before touching Batch B.**

---

### Batch B: Detail Panels (5 min)

Click any **alive** agent card's "See details" link. Then cycle through the 3 tabs.

| # | Action | What To Notice | Layer Focus |
|---|---|---|---|
| B1 | Click "See details" on an agent | How fast does the panel open? Does it animate smoothly or snap? | Friction |
| B2 | Click **Health** tab | Scan the circuit breaker status, error list, timestamp. Is the hierarchy clear (what's important vs secondary)? | Perception |
| B3 | Click **Tokens** tab | Look at the bar chart, drift indicator, CHISEL savings badge. Are the numbers readable? Does "291 total" mean anything? | Confidence |
| B4 | Click **Garden** tab (if data exists) or empty state | If data: does the grade/score make sense? If empty: does it say why it's empty? | Friction |
| B5 | Close panel, click a different agent | Did the first panel close cleanly before the second opened? | Friction |

**Submit all B1-B5 feedback before moving on.**

---

### Batch C: Secondary Pages (5 min)

| # | Action | What To Notice | Layer Focus |
|---|---|---|---|
| C1 | Click **Pathways** link in header | Wait for Cytoscape graph to render. Do you understand what the nodes/edges represent? Are red dead-ends visually obvious? | Confidence |
| C2 | **Pathways** — zoom/drag/click | Drag a node. Does it feel responsive? Right-click or click a node — does anything happen? | Friction |
| C3 | Navigate back to landing page, scroll to **Code Graph** section | Is the search box obvious? Type something (e.g. "run_check") — does anything happen on Enter? | Friction |

**Submit all C1-C3 feedback.**

---

### Batch D: Error & Empty States (3 min)

This requires deliberately breaking the running dashboard.

1. Tell me to kill the watch daemon.
2. I'll stop it, you reload the page.
3. Then check:

| # | What To Notice | Layer Focus |
|---|---|---|
| D1 | Does the error banner appear at the top with an actionable message? | Confidence |
| D2 | Do agent cards still render with stale data + "data as of" indicator? | Perception |
| D3 | Does the heal section say something useful (not just "error")? | Friction |
| D4 | After I restart the daemon, does the page recover in under 60s (via htmx auto-refresh)? | Friction |

**Submit D1-D4 feedback.**

---

## What Not to Test (Covered by AI)

| Skip | Reason |
|---|---|
| Font sizes under 11px | Script-verified against DESIGN.md tokens |
| All 12 API endpoints return 200 | Break test script runs this every session |
| ARIA labels on interactive elements | Already fixed in prior session |
| Dashboard on mobile viewport | v1 is desktop-only — acknowledged gap in master plan |
| Color contrast ratios | Design tokens are the spec — verified against DESIGN.md |
| Agent card count accuracy | Data-dependent, code produces correct SQL queries |
| Pathways graph data accuracy | Data-dependent, code produces correct nodes/edges from DB |

---

## Feedback Submission

**Two channels, your choice:**

1. **Telegram DM** — send each issue as a separate message using the format above. I'll process them in order.
2. **Batch list** — collect all issues from one batch into a single message. I'll still process each.

**Recommended flow:** Test Batch A → send all A issues at once → wait for my fix → test Batch A again → proceed to Batch B. This catches regressions fast.

**Do not skip the sequence.** Batch A's fixes may affect Batch B's rendering. If you test B before A is fixed, you'll report issues that A's fixes already addressed.

---

## What Happens After You Test

1. I process each issue by SECTION + LAYER
2. Fixes ship as CSS changes (perception/friction) or backend changes (confidence)
3. Break test script re-runs to verify no regressions
4. I confirm fixes deployed, tell you to re-test the affected batch
5. Cycle repeats until all batches pass your standard

No kanban tasks. No tickets. This doc is the contract.
