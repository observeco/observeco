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

Dashboard auth: all `/api/` routes (except `/api/phase`, `/api/agent-count`, `/api/licenses/validate`) require `X-ObserveCo-Token` header or `?token=` query param. Token auto-injected into htmx requests via `window.__OBSERVECO_TOKEN`. View with `observeco dashboard --show-token`.

Desktop app: `observeco desktop` launches a native pywebview window (1200×800). Falls back to browser if pywebview is not installed.

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

### Batch H (NEW): Security & Auth Flow (8 min)

**Pre-test setup:** Delete `~/.observeco/.dashboard_secret` if it exists (fresh state).

| # | Action | What To Notice / Questions to Answer | Layer |
|---|---|---|---|
| H1 | Run `observeco dashboard` in terminal | **Q: What does the terminal output say? Does it mention the access token?** Exact quote please. | Emotional Load |
| H2 | Open `http://localhost:9119/` in browser | **Q: Does the page load normally? Does the fluorescent "Local only — do not expose to the internet" banner appear at the top?** | Perception |
| H3 | Open your browser DevTools (F12), go to Console tab | **Q: Do you see any errors about missing token or 401 responses? Check for red errors.** | Friction |
| H4 | Open DevTools Network tab. Load the page. Look for a request to `/api/agents`. Click it and check Request Headers. | **Q: Does the request include `X-ObserveCo-Token` header with a ~43-character value?** | Confidence |
| H5 | Open DevTools Console and type: `window.__OBSERVECO_TOKEN` | **Q: Does it return a non-empty string? Yes/No + first 8 chars visible?** | Confidence |
| H6 | Run in a separate terminal: `curl -s http://localhost:9119/api/agents` | **Q: What status code and error body do you get? Expected: HTTP 401 with a message about `--show-token`** | Confidence |
| H7 | Run: `observeco dashboard --show-token` | **Q: Does it print a 43-character token?** Copy the token, then run: `curl -s -H 'X-ObserveCo-Token: <token>' http://localhost:9119/api/agents` | Friction |
| H8 | **Q: Does the authenticated curl return your agent cards HTML (no longer 401)?** | Confidence |
| H9 | **Q: Overall feeling — does this token flow feel secure but not annoying? Rate 1–10 (1 = "why do I need a token?", 10 = "this feels properly locked down")** | Emotional Load |
| H10 | Close the browser tab. Open a **new incognito/private window**. Navigate to `http://localhost:9119/`. | **Q: Does the page load normally (no auth prompt, no login screen)? The token is injected into the HTML, not a cookie — so it should work in incognito.** | Perception |

**Submit all H1–H10 before moving on.**

---

### Batch I (NEW): Desktop App Experience (5 min)

**Pre-test: If you have pywebview installed. Otherwise skip to I7.**

| # | Action | What To Notice / Questions to Answer | Layer |
|---|---|---|---|
| I1 | Run: `observeco desktop` | **Q: Does a native window open (1200×800, dark theme)? Or does it fall back to browser?** | Friction |
| I2 | Hover over the top of the window | **Q: Does the title bar show "ObserveCo · Fleet Dashboard"?** | Perception |
| I3 | Resize the window smaller than 800×600 | **Q: Does it stop at the minimum size or go smaller?** | Friction |
| I4 | Click the close (red X) button | **Q: Does a confirmation dialog appear before quitting?** | Friction |
| I5 | Look for a system tray icon (top-right menu bar on macOS) | **Q: Is there an ObserveCo icon? Click it — what menu options appear?** | Perception |
| I6 | **Q: Overall — does the desktop app feel native or does it feel like a website in a frame? Rate 1–10** | Emotional Load |
| I7 | (No pywebview) Run: `observeco desktop` | **Q: Does it print the "Desktop mode requires pywebview" message and open the browser instead? No crash?** | Perception |

**Submit I1–I7 (or as many as apply).**

---

### Batch J (NEW): Scale Experience (5 min)

Test the search/filter/pagination that handles 100+ agents.

| # | Action | What To Notice | Layer |
|---|---|---|---|
| J1 | Look at the top of the agent list | **Q: Is there a search bar with placeholder "Search agents by name or framework..."? If you only have 1–5 agents, is it still visible?** | Perception |
| J2 | Click the search bar and type the name of one of your agents | **Q: Does the list filter as you type (with ~300ms delay)? Does the non-matching agent disappear?** | Friction |
| J3 | Clear the search. Look for filter chips to the right of the search bar: **All / ● Alive / ● Warning / ● Down** | **Q: Click each filter chip. Does the active one highlight green? Does the list update? Click "All" — does everything come back?** | Perception |
| J4 | If you have >25 agents: | **Q: Do pagination controls appear at the bottom of the page showing "Showing 1–25 of X"? Click next page — does it load smoothly?** | Friction |
| J5 | If you have <25 agents: | **Q: Is there NO pagination bar? (Expected — pagination only shows when >25 agents)** | Perception |
| J6 | Click a filter (e.g. "● Down") then type a search query | **Q: Do both filters stack? (e.g. only 'down' agents matching your search text show up)** | Confidence |
| J7 | Click "Clear filters" link if no results match | **Q: Does it reset everything to "All" with empty search?** | Friction |
| J8 | **Q: Overall — does search/filter feel instant or laggy? Rate 1–10** | Emotional Load |

**Submit all J1–J8.**

---

### Batch K (NEW): Shared Mode Experience (5 min)

**Only do this batch if you have a network share available or want to test the shared DB path.**

| # | Action | What To Notice | Layer |
|---|---|---|---|
| K1 | Run in a terminal: `observeco dashboard --shared /tmp/team-observeco.db` | **Q: Does the terminal print "Shared fleet DB: /tmp/team-observeco.db"? Does the dashboard load normally?** | Perception |
| K2 | On the page, look just below the telemetry banner | **Q: Does a yellow "Shared Fleet Mode Active" banner appear? Does it show the DB path and a security warning about network shares?** | Confidence |
| K3 | Dismiss the warning by clicking the ✕ button, then reload the page | **Q: Does the warning come back? (Expected: no — it's a one-time banner, persisted in `~/.observeco/.shared_warning_shown`)** | Friction |
| K4 | **Q: Does the shared mode feel like it changes anything else on the page? Does it break any cards?** | Perception |

**Submit K1–K4 only if you tested shared mode.**

---

### Batch L (NEW): Overall Emotional Load & First-Use (3 min)

| # | Question | Emotional Load |
|---|---|---|
| L1 | **First 10 seconds:** Did you know what ObserveCo does without reading any text? Yes/No + one sentence | Layer 5 |
| L2 | **First action:** What was the first thing you wanted to click? Did it work? | Layer 5 |
| L3 | **Safety feeling:** Did you feel like the dashboard was "mine and no one else's"? The token system aims for that — did it achieve it? | Layer 5 |
| L4 | **Desktop feeling:** Did the desktop app feel like a real app or a website trick? Rate 1–10 | Layer 5 |
| L5 | **One thing you'd change:** If you could fix ONE thing about the whole experience right now, what is it? | Layer 5 |

**Submit L1–L5. This is the most important batch — it shapes the next sprint.**

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
| Auth middleware blocks unauthenticated requests | TestClient verifies this (layer F/15) |
| `observeco desktop --help` works | Subprocess test in audit layer |
| CSP / nosniff / Referrer-Policy headers | TestClient verifies these (auth middleware) |
| Token is crypto-secure (`secrets.token_urlsafe(32)`) | Code-level verification done |
| Token file persists across restarts | Tested via file read/write |
| billing.json atomic write (tmp→rename) | Phase 2 code audit + 270-test suite |
| billing.log rotation (RotatingFileHandler, 1MB×3) | Phase 2 code audit + integration test coverage |
| File lock acquisition/release (`_acquire_file_lock` / `_release_file_lock`) | Phase 2 code audit verified finally: guarantee |
| Concurrent read-after-write safety | Phase 2 System Design 9-Lens: 43/45 score verified |
| f-string leak in billing.py API responses | Step 0B audit script scans all endpoints |

---

## Feedback Submission

**Two channels, your choice:**

1. **Telegram DM** — send each issue as a separate message using the format above. I'll process in order.
2. **Batch list** — collect all issues from one batch into a single message. I'll still process each.

**Recommended flow:** Test Batch H → send all H issues → wait for my fix → test Batch H again → proceed to Batch I. This catches regressions fast.

**Do not skip the sequence.** Batch H fixes may affect Batch I rendering. If you test I before H is fixed, you'll report issues H already addressed.

---

## What Happens After You Test

1. I process each issue by SECTION + LAYER
2. Fixes ship as CSS changes (perception/friction) or backend changes (confidence)
3. Break test script re-runs to verify no regressions
4. I confirm fixes deployed, tell you to re-test the affected batch
5. Cycle repeats until all batches pass your standard

No kanban tasks. No tickets. This doc is the contract.

---

### Batch M (NEW): Billing & License Card (10 min)

Tests the billing gap fixes: RotatingFileHandler, file-level lock, spec metrics/AC6, and all 5 license card states.

**Pre-test setup:** Open `http://localhost:9121/` (or your dashboard port) with a fresh install — no billing history.

| # | Action | What To Notice | Layer |
|---|---|---|---|
| M1 | **Trial state** — fresh install landing | License card shows 🚀 Solo plan · `N` days left + [Subscribe via Stripe $9/mo] + [Cancel Trial] buttons. Does the countdown match 30 days? | Perception |
| M2 | **Cancel Trial** — click Cancel Trial → confirm "Yes, cancel" | Card transitions within 1s to "Trial cancelled" state. Subscribe button visible. Pro features lock. Does it feel safe or punitive? | Friction |
| M3 | **Re-trial blocked** — close dashboard, reopen | Card still shows cancelled state. No "Start Trial" reappearing. Does it feel like "it remembered me" or "it locked me out"? | Confidence |
| M4 | **Trial expiry** — close dashboard, set `OBSERVECO_TRIAL_DAYS=0`, restart, reopen | ⚠️ Warning banner: "Your free trial ended on..." with [Subscribe $9/mo] [Dismiss] buttons. Dismiss works. Does the warning feel urgent or aggressive? | Perception |
| M5 | **Pro state** (if you have a Stripe sub or admin key) — activate Pro | ✅ Pro · Solo $9/mo with [Manage Billing →] button. Next billing date shown. Does the Pro card feel premium? | Perception |
| M6 | **Log file exists** — run in terminal: `ls -la ~/.local/share/observeco/billing.log` | Does the file exist? Is the first line a timestamped log entry? No confused output? | Confidence |
| M7 | **Corrupt billing.json** — close dashboard, run: `echo "{bad" > ~/.local/share/observeco/billing.json`, reopen | Dashboard loads without crashing. License card shows default/empty state. No traceback on screen. Does it feel like "graceful fallback" or "broken"? | Confidence |
| M8 | **Trust audit** — read the license card and ask yourself: | Would I enter my credit card on this dashboard? Does the billing UI feel like a real product or an afterthought? | Emotional Load |
| M9 | **Stripe not configured** — default state, no Stripe keys | "Subscribe" button opens simulated/demo checkout (no real Stripe). Does it feel like a preview or a broken integration? | Perception |
| M10 | **State survives hard restart** — cancel trial → kill the dashboard process → restart | License card still says cancelled. No trial reset. Does the system remember you? | Confidence |

**Submit all M1–M10 before touching any other section. Then re-test Batch A to ensure no billing-related regressions.**