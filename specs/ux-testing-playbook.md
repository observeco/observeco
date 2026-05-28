# UX Testing Playbook — The Human Lens

**Product:** ObserveCo (and all future frontend projects)
**Status:** Living — update as lessons accumulate
**Author:** Main (per Sean direction 2026-05-25)
**Source:** Real testing session — dashboard v0 passed all AI checks, failed every human check

---

## 1. Thesis

**AI tests the machine. Humans test the feeling.**

Every AI-to-human UX gap traceable to one root: the AI verifies *existence* and *correctness* (DOM element found? API returned 200?). The human evaluates *perceived completeness* and *confidence* (does this feel populated? do I trust what I see?).

This document is not a fix list. It is a **testing lens** — a repeatable way to catch the class of problem, not the instance.

---

## 2. The Three Human-Experience Layers

All human-facing testing failures fall into one of three layers:

| Layer | AI reports | Human feels | Example from dashboard v0 |
|-------|-----------|-------------|---------------------------|
| **Perception** — does the page look complete? | "15 agent cards render" | "Every card looks the same — nothing is happening" | Token bars, drift sparklines, error badges all empty → 15 identical cards |
| **Confidence** — does the user trust what they see? | "All endpoints return 200" | "Alerts panel shows Internal Server Error — dashboard is broken" | Pro tiles crashed `/api/alerts` with KeyError → right rail broken |
| **Friction** — does interaction feel effortless? | "toggleAgentDetail() exists, class toggle works" | "Clicked nothing happened. Clicked again. Now the wrong thing is open." | Card opens with no visual feedback on first click |

**Rule:** A feature that passes Layer 1 (perception) but fails Layer 2 (confidence) or Layer 3 (friction) is not done. Do not mark it complete until all three layers pass.

### 2.1 Why This Is Systematic

The three layers are not a checklist. They are a **diagnostic lens**:

- Every bug you find maps to exactly one layer
- Every layer has a specific fix pattern
- The fix for a Layer 1 problem (empty state looks incomplete) is NOT the same fix as a Layer 3 problem (click doesn't feel responsive)
- When you apply the lens to any future project, you catch the same class of bugs before they reach a human

---

## 3. The Five Expectation Traps (Pattern Catalogue)

Each trap is a **recurring failure pattern** — not a specific bug in the current code, but a class of bug that will reappear in any frontend project.

### Trap 1: Structural Correctness ≠ Visual Completeness

**Pattern:** AI verifies a section exists in the DOM. Human sees an empty-looking box.

**Detection:** For every section on the page, ask: *"Does this look like it has content, or does it look like something failed to load?"*

**Remedy (choose one, in order of preference):**
1. Populate with real data
2. Show a skeleton placeholder (grey animated blocks matching the final layout)
3. Show explanatory text: *"No errors in the last 24h. Data appears after the next agent pulse."*
4. Collapse the section entirely if empty and low-priority

**Never:** Leave a section heading + empty body. That reads as "broken" not "empty."

### Trap 2: Mechanism Works ≠ Feedback Registered

**Pattern:** AI verifies the click handler fires. Human can't tell whether anything happened.

**Detection:** Click every interactive element and watch for a visible response in <200ms. Any click that produces no visible change within 200ms will be clicked again.

**Remedy:**
1. Add `transition: all 0.15s` to every toggle — the brain registers motion before conscious thought
2. Change cursor to `pointer` on hover for all clickable elements
3. Add hover state (slight brightness shift, border highlight, or opacity change)
4. After click: if content loads async, show an inline loading indicator immediately

### Trap 3: Data Is Accurate ≠ Layout Is Readable

**Pattern:** AI passes the correct values into templates. Human can't read the output comfortably.

**Detection:** Read every line of text on the page at a normal viewing distance. Mark any line that requires squinting, leaning forward, or re-reading.

**Hard limits:**
- Body text: minimum **13px** on dark backgrounds (NNGroup research: 30% slower at 11px)
- Disabled/locked text: minimum **13px** — smaller reads as "broken" not "locked"
- Contrast ratio: minimum **4.5:1** for body text (WCAG AA)
- Locked state: use subtle blur overlay or muted colour, NOT full grayscale + 11px type

### Trap 4: API Returns 200 ≠ Loading Experience Is Good

**Pattern:** AI tests the happy path after everything loaded. Human experiences the blank→populated transition and remembers the blank.

**Detection:**
1. Clear all caches and hard-reload
2. Record the first 3 seconds frame by frame
3. Mark every frame that shows: white flash, blank section, placeholder text ("Loading..."), or error state

**Remedy (loading priority — render in this order):**
1. **Header/sticky bar** — always immediate (gives user a sense of "something is happening")
2. **Agent cards** — with skeleton placeholders (teaches the layout before data arrives)
3. **Alerts panel** — with skeleton or inline loading spinner
4. **Error timeline** — lowest priority, loads last

**Error fallback (every API call must have):**
- Inline error within the relevant panel, NOT a full-page crash
- Actionable text: *"Server appears down. Run `observeco dashboard --restart` to fix."*
- Never show "Internal Server Error" or an unhandled exception trace to the user

### Trap 5: Empty State Is Correct ≠ Empty State Is Helpful

**Pattern:** AI evaluates functional correctness (no data = render nothing). Human evaluates perceived value (empty page = useless page).

**Detection:** Find every section that shows zero data. For each, does it:
- Explain *why* it's empty?
- Tell the user *when* it will populate?
- Give a *next action* the user can take?

**Triage:**
| State | Good | Bad |
|-------|------|-----|
| No errors | "✅ No errors in the last 24 hours" | Empty space where an error list would be |
| No token data | "📊 Token data appears after the agent's next session" | Blank area below the agent card |
| No drift data | "📈 Establishing baseline — 3+ pulses needed" | Missing sparkline |
| No alerts | No alert panel needed at all (collapse it) | Empty right rail with "Pro Features" greyed out |

---

### Trap 6: Navigation Works ≠ User Stays in Context

**Pattern:** AI verifies the link/button navigates correctly (HTTP 200, page loads). Human lands on a different page and must navigate back — breaking mental flow.

**Detection:** Click every interactive element and watch what happens. If it navigates to a different URL or replaces the current view entirely, ask:
- Does this action *change* the user's task (e.g., editing settings) or *continue* it (e.g., seeing self-heal details)?
- If it continues the task, the user should stay on the same page
- If it changes the task, navigation may be acceptable — but always provide a visible back path

**Best practice (in order of preference):**
1. **Inline expand** — detail appears within the same card/section. No navigation, no modal.
2. **Slide-in overlay (drawer/panel)** — slides in from right, keeps dashboard visible underneath. Dismiss with:
   - Click outside the panel
   - Escape key
   - Explicit X/Close button
3. **Modal overlay** — for focused tasks. Same dismiss rules as drawer.
4. **Same-page section swap** — replace a section's content inline (e.g., swap the self-heal block for its detail view). User can click "Back" to return.
5. **Last resort: new page** — only when the scope fundamentally changes (e.g., going from dashboard to full settings page). Must include:
   - A visible "Back to Dashboard" link at the top
   - The same theme/layout so it doesn't feel like leaving the app
   - Browser back button works as expected

**Never:** Redirect to a different page for a secondary/detail action without a prominent way to return. Every navigation that breaks context costs the user 3-5 seconds to re-orient.

**Checklist for the playbook gate:**
- For each clickable element, note whether it navigates away or stays in-page
- If it navigates away: is the new page justified (does the user's task fundamentally change)?
- Is there a visible, one-click path back?
- Does the new page inherit the same theme and header so it feels continuous?
- Does the browser back button return to the same scroll position?

---

## 4. The Testing Protocol

This is the **minimum viable human-lens evaluation**. Apply it before any frontend deliverable is marked complete.

### 4.1 Pre-Ship Gate (run by Hound or any agent)

```
Before marking any frontend work done, run this gate:

1. SCREENSHOT the page in its current state
2. Answer for every section: does this look complete or broken?
3. CLICK every interactive element once. Does something visible happen within 200ms?
4. HARD-RELOAD (cache cleared). Record what shows in frames 0-3 seconds.
5. READ every text element. Can you read it at normal viewing distance without squinting?
6. SIMULATE an API failure (kill the data source). Does the page degrade gracefully?
7. CHECK for empty sections: does each one explain itself or sit there blank?
8. CHECK for context breaks: every click stays on the same page or uses inline overlay — no page redirects for secondary actions
9. CHECK every navigation path: is there a one-click way back? Does back button work?

One-line pass/fail per check. If any fails, the deliverable is not complete.
```

### 4.2 When to Run

| Phase | Trigger | Gate |
|-------|---------|------|
| **Build** | Each new section/component | Visual completeness + click feedback |
| **Integration** | All sections wired to real data | Loading sequence + empty states |
| **Pre-launch** | Before sharing with any human | Full 7-point gate above |
| **Regression** | Any backend/api change | Loading sequence + error fallback |

### 4.3 The Golden Rule

**If a bug survived the AI's review but was caught by a human in minutes, the testing protocol was wrong — not the human.**

Every time this happens, update this document with the new trap. The trap catalogue grows; the individual bugs stop.

---

## 5. Expert Prompts for Hound

Copy-paste these directly. Each maps to one Expectation Trap.

### Prompt 1: Visual Completeness (targets Trap 1)

```
Run a visual completeness pass on the ObserveCo dashboard at localhost:9122.

1. Take a full-page screenshot
2. For every section (fleet header, agent cards, alerts panel, error timeline, pro tiles, self-heal), answer:
   - Does this section look "done" or does it feel like something is missing?
   - If empty: is there a skeleton placeholder or explanation, or just blank space?
   - Can all text be read comfortably at a glance? (no 11px or smaller, no low-contrast pairs)
   - Do disabled elements look "premium-locked" or "broken-garbage"?
3. Screenshot the 3 most visually confusing elements with annotations
4. Deliver: screenshots + one-line fix per issue
```

### Prompt 2: Loading Sequence (targets Trap 4)

```
Test the dashboard loading sequence at localhost:9122.

1. Hard-reload (Cmd+Shift+R). Watch the first 3 seconds.
   - Is there a white flash before dark theme loads?
   - What renders first? Second? Last?
   - Is there ever a point where the page looks "done" but sections are still empty?
2. Restart the server (clear all caches). Reload. Same analysis.
   - Does any section flash an error before resolving?
3. For each section that shows blank then populates: can it show a skeleton or loading indicator at the start?
4. Deliver: 0-3s timeline in 500ms frames + fix per blank section
```

### Prompt 3: Click Confidence (targets Trap 2)

```
Test every interactive element for first-click confidence.

For each element (agent cards, pro tiles, tab buttons, search/filter):
1. Click once. Does something visible happen within 200ms?
2. If yes: does it look intentional (animation, color shift, new content) or accidental?
3. If no: is that because it needs 2 clicks or because it's broken?
4. Specifically test card toggle:
   - After click, can you tell if the card is open or closed without reading text?
   - What happens if you click a second card while one is open?
5. Does the page tell users things are clickable? (pointer cursor? hover effect? border?)
6. Deliver: interaction scorecard per element (High/Medium/Low confidence) + one-line fix per Medium/Low
```

### Prompt 4: Empty State Guidance (targets Trap 5)

```
Audit every section showing zero data.

1. List each empty section: error badges, token bars, drift sparklines, error timeline, self-heal
2. Per section: does it explain WHY it's empty? Does it say WHEN it populates?
   - Helpful: "No errors in 24h" / "Token data after next session"
   - Unhelpful: blank space, missing element, or just a section heading with nothing below
3. Per section: recommend one-sentence guidance text + skeleton placeholder design
4. Deliver: table (Section | Current | Recommended Fix | Priority)
```

### Prompt 5: Error Fallbacks (targets Trap 4)

```
Test every API failure scenario.

1. Simulate failures:
   - Kill server → what do JS XHRs show?
   - Stop the DB → what does /api/agents return?
   - Invalid pro-preview ID → what happens?
2. Per failure: does user see graceful inline error within the panel, or browser-level blank space?
3. Does the error tell them what to do? ("Run `observeco start` to resume.")
4. Deliver: error fallback matrix per endpoint + critical fixes
```

### Prompt 6: Context Preservation (targets Trap 6)

```
Test every interactive element for context-preserving behaviour at localhost:9122.

1. Click every button, link, card, and tile. Note which ones navigate away from the dashboard.
2. For each that navigates away:
   - Is the action fundamental (e.g., going to settings) or secondary (e.g., viewing self-heal details)?
   - If secondary: should it use an inline expand, slide-in drawer, or modal instead?
   - Is there a visible one-click path back to the dashboard?
   - Does the back button return the user to the same scroll position?
   - Does the destination feel like the same app (same theme, same header)?
3. Specifically test self-heal buttons → do they redirect to a separate page?
   - If yes: recommend slide-in drawer pattern where detail overlays the dashboard
   - User should not have to navigate back to continue monitoring
4. Deliver: interaction map showing which elements stay in context vs which break it, with one-line fix per break
```

---

## 6. Lessons Learned Log

Append here every time a human catches something an AI missed. This is how the playbook stays alive.

### 2026-05-25 — Dashboard v0 AI-Human Gap

| What AI said | What human found | Trap | Fix |
|-------------|------------------|------|-----|
| "All endpoints return 200" | Alerts panel shows "Internal Server Error" — Pro tiles crashed | Trap 4 — loading experience | Fixed `_pro_locked_tiles()` KeyError (server.py line 175) |
| "15 agent cards render correctly" | All 15 cards look identical — empty badges, bars, sparklines | Trap 1 — visual completeness | Add skeleton placeholders + empty-state guidance |
| "toggleAgentDetail() works" | First click produces no visible feedback; user clicks again confused | Trap 2 — feedback registered | Add transition animation + pointer cursor on all cards |
| "Empty badges/bars/sparklines = correct (no data)" | Dashboard feels useless — nothing is happening | Trap 5 — empty state unhelpful | Add per-section explanatory text + collapse low-value empty sections |
| "Text renders at spec sizes (11px)" | 11px on dark background is unreadable without squinting | Trap 3 — layout readability | Bump to 13px min for body text; change locked-tile visual from grayscale to blur overlay |

| 2026-05-25 — Self-heal buttons redirect to separate page
|
|| What AI said | What human found | Trap | Fix |
||-------------|------------------|------|-----|
|| "Self-heal button navigates to /self-heal correctly" | Redirects to new page — user loses dashboard context and must navigate back | Trap 6 — context preservation | Replace redirect with slide-in drawer overlay; user stays on dashboard |
|| "Pragma is in topic 2072 of Alpha Management, bot can send there" | Bot was never added to topic 2072 — can send but cannot receive messages | Telegram platform limitation | Group admin must add bot to topic 2072 as member (see infra note) |
|| "Agent detail tabs load on first click" | Clicking Health→Tokens→Memory then back to Health shows permanent "Loading health data..." — tab cache prevents re-fetch | Trap 2 — feedback registered | Fix: remove cached tab entries when switching tabs within same agent; detect stale "Loading..." state and re-fetch |
|| "Tokens tab shows no data for Hermes agents" | Accelerator (a Hermes agent) shows nothing under 📊 Tokens — likely no trim data in DB | Trap 1 — visual completeness | Show helpful empty state: "No trim data yet — run `observeco chisel trim` to see token savings" |
|| "Memory tab shows misleading message for Hermes agents" | "Memory garden is available for OpenClaw agents" — user is looking at a Hermes agent, not OpenClaw | Trap 5 — empty state unhelpful | Changed to: "This Hermes agent uses CHISEL for context optimization — check the Tokens tab" with explanatory tip |

### Template for future entries

```
| Date | Product | What AI said | What human found | Trap | Fix |
|------|---------|-------------|------------------|------|-----|
| YYYY-MM-DD | {product} | {AI claim} | {human finding} | {Trap N} | {what was done} |
```

---

## 7. Projecting Forward

This playbook applies to any frontend product we build — not just ObserveCo. Before shipping any UI:
1. Load the playbook
2. Run the 5 prompts
3. Check the Lessons Learned log for similar past gaps
4. If you find a new trap, log it before fixing

The goal is not to eliminate AI-human gaps. The goal is to make every new gap a one-time discovery that gets absorbed into the playbook, never repeated.
