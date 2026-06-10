# UX Testing Playbook — The Human Lens

**Product:** ObserveCo (and all future frontend projects)
**Status:** Living — update as lessons accumulate
**Version:** 3.5 — 2026-06-10
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 2.0 | 2026-05-30 | Added Version field, Golden Gate, fixes section numbering |
| 3.1 | 2026-05-31 | Standardization pass: all 7 playbooks bumped to v3.1. Fixed stale playbook-count references. Confirmed cross-references to Playbook Inventory (requirements-fidelity-playbook.md §Playbook Inventory) and Layer F First-Run Audit (master-fidelity-gate.md §2 Layer F). Removed stray empty FILE tags. |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory, rename "Pre-Ship Gate" → "Golden Gate" |
| 3.2 | 2026-06-01 | Added Trap 14 (Representation Overflows Container), Trap 15 (Inline Reference Not Verified), Trap 16 (JS Rename Leaves Dead Call). Updated Trap 5 detection (actionable empty state commands), Trap 9 detection (flush-content check). Added Lessons Learned entry for 6 post-launch issues. |
| 3.3 | 2026-06-08 | Added Trap 18 (Overlay Dismiss on Text Selection). Updated Golden Gate checklist with text-selection test. Added Lessons Learned entry for Pro License Key modal bug. |
| 3.4 | 2026-06-09 | Added Trap 20 (Cross-System Format/State Inconsistency), Trap 21 (Hardcoded Ephemeral Value), Trap 22 (Schema-Code Drift), Trap 23 (Render Order Drift), Trap 24 (Entity-Type-Aware Rendering). Added entity-type-awareness to Golden Gate as item 8.5. Golden Gate now 12-point. Added cross-system consistency and ephemeral-value detection patterns. Version history table fixed (removed stray pipe). |
| 3.5 | 2026-06-10 | Added Trap 25 (Misleading Data — Real Enough to Confuse), Trap 26 (Subscription State Confusion), Trap 27 (Pro Activation Gap), Trap 28 (Backend Status ≠ Dashboard Status), Trap 29 (Silent Crash on Missing DOM Element), Trap 30 (Badge/State Refresh Missing After State Change). Golden Gate updated to 14-point. Added Lessons Learned entries for all 6 new traps. |
| 3.6 | 2026-06-10 | Added Trap 31 (Modal Stacking — Overlay Hides Overlay), Trap 32 (Action Buried Below Scroll Threshold), Trap 33 (Pro-Empty-State Mismatch). Added Lessons Learned entries for 6 bugs caught in post-Skill-Audit review. Golden Gate updated to 16-point. |

**Author:** Main (per Sean direction 2026-05-25)
**Source:** Real testing session — dashboard v0 passed all AI checks, failed every human check

---

## 1. Thesis

**AI tests the machine. Humans test the feeling.**

Every AI-to-human UX gap traceable to one root: the AI verifies *existence* and *correctness* (DOM element found? API returned 200?). The human evaluates *perceived completeness* and *confidence* (does this feel populated? do I trust what I see?).

This document is not a fix list. It is a **testing lens** — a repeatable way to catch the class of problem, not the instance.

---

## 2. The Five Human-Experience Layers

All human-facing testing failures fall into one of five layers:

### Layer 1: Perception — Does the page look complete?

| AI reports | Human feels |
|-----------|-------------|
| "15 agent cards render" | "Every card looks the same — nothing is happening" |

Token bars, drift sparklines, error badges all empty → 15 identical cards. The DOM is correct. The experience is broken.

**Detection:** For every section on the page, ask: *"Does this look like it has content, or does it look like something failed to load?"*

**Fix pattern:** Populate with real data > skeleton placeholders > explanatory text > collapse section.

### Layer 2: Confidence — Does the user trust what they see?

| AI reports | Human feels |
|-----------|-------------|
| "All endpoints return 200" | "Alerts panel shows Internal Server Error — dashboard is broken" |

Pro tiles crashed `/api/alerts` with KeyError → right rail broken. The API *mostly* works. The human only notices the broken part.

**Detection:** Simulate failures (kill server, kill DB) and inspect every panel. Any inline error text or blank panel erodes trust across the entire page.

**Fix pattern:** Every API call must have an inline, actionable error fallback within its own panel. Never show tracebacks or "Internal Server Error."

### Layer 3: Friction — Does interaction feel effortless?

| AI reports | Human feels |
|-----------|-------------|
| "toggleAgentDetail() exists, class toggle works" | "Clicked nothing happened. Clicked again. Now the wrong thing is open." |

Card opens with no visual feedback on first click. The mechanism works. The feeling is broken.

**Detection:** Click every interactive element and watch for a visible response in <200ms. Any click that produces no visible change within 200ms will be clicked again.

**Fix pattern:** Add `transition: all 0.15s` to all toggles, `cursor: pointer` on all clickables, loading indicators on async loads, and close-A-when-B-is-opened behaviour.

### Layer 4: Accessibility & Inclusion — Can everyone use this?

| AI reports | Human feels |
|-----------|-------------|
| "All elements are in the DOM" | "I can't tab to this card. My screen reader says 'unlabeled button'. I can't read green-on-dark text." |

AI rarely tests accessibility. Users with motor impairments, low vision, colour vision deficiency, screen readers, or non-English primary language will hit invisible walls that pass every automated check.

**Detection:**
1. Keyboard-only navigation: tab through every interactive element. Is focus ever trapped or invisible?
2. Screen-reader audit: does every interactive element announce its state and purpose?
3. Colour-blind simulator + contrast audit on every text/icon pair.
4. Touch targets: are all clickable areas ≥44×44 px on mobile viewports?
5. Reduced-motion mode: do all animations respect `@media (prefers-reduced-motion)`?

**Fix pattern:**
- Mandatory ARIA labels on all interactive elements
- Focus rings with 3px offset, never `outline: none`
- Minimum contrast ratio 4.5:1 for body text (WCAG AA)
- Touch targets ≥44×44px
- Respect `prefers-reduced-motion` — no auto-playing animations
- Never convey information through colour alone (add icons, text, or patterns)

### Layer 5: Emotional & Cognitive Load — Does the user feel in control?

| AI reports | Human feels |
|-----------|-------------|
| "Dashboard renders all 15 cards, all data present" | "I feel overwhelmed. I don't know where to look first. I'm afraid I'll break something." |

This layer explains why a dashboard can pass every technical check and every lower-layer UX check yet still have 40% of power users abandon it. The interface creates micro-anxiety, decision fatigue, or "I'm too stupid for this tool" feelings.

**Detection (test as a cold first-time user):**
1. First 10 seconds: what does a brand-new user feel? (overwhelmed, confused, excited, confident?)
2. Can they answer "What is this dashboard for?" and "What should I do first?" without help?
3. Walk through the three most common tasks a new user would attempt. Record friction points.
4. Rate emotional load on a 1-10 scale for each section.

**Fix pattern:**
- Progressive disclosure — show the most important 3 things first, let users drill in
- First-visit banner or guided tour for new users
- Micro-copy that reassures (not "Error 500" but "Something went wrong — your data is still safe")
- Default states that feel calm, not empty
- Clear visual hierarchy — the most important thing should be the most visually prominent

### Layer Priority Rule

A feature that passes Layers 1-3 but fails Layer 4 (Accessibility) or Layer 5 (Emotional Load) is not done. The lower layers are necessary but not sufficient.

---

## 3. The Expectation Traps (Pattern Catalogue)

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
- If the empty state is tied to a **user-actionable prerequisite** (daemon not running, API key missing, config not set): does it show the EXACT terminal command to resolve it? Every actionable empty state must include a runnable command — not just a description of what's missing.

**Triage:**
| State | Good | Bad |
|-------|------|-----|
| No errors | "✅ No errors in the last 24 hours" | Empty space where an error list would be |
| No token data | "📊 Token data appears after the agent's next session" | Blank area below the agent card |
| No drift data | "📈 Establishing baseline — 3+ pulses needed" | Missing sparkline |
| No alerts | No alert panel needed at all (collapse it) | Empty right rail with "Pro Features" greyed out |
| No daemon | "⏳ Watch daemon not running. Start: `observeco watch start`" — actionable, one terminal command | "Watch daemon (never started)" — describes the state, gives no path forward |

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

### Trap 7: Accessibility Compliance ≠ Inclusive Usability

**Pattern:** AI runs a Lighthouse accessibility audit (passes), but a real user with low vision, motor impairment, or colour vision deficiency cannot use the product.

**Detection:**
1. Keyboard-only: tab through every interactive element. Is focus ever trapped or invisible?
2. Screen-reader (VoiceOver/NVDA simulated): does every interactive element announce its state and purpose?
3. Colour-blind simulator on every text/icon pair — does information rely on colour alone?
4. Touch targets ≥44×44px on mobile viewports
5. `prefers-reduced-motion` — do animations respect it?
6. Focus rings: visible, minimum 3px offset, never `outline: none`

**Remedy:**
- Mandatory ARIA labels on all interactive elements (`aria-label`, `aria-expanded`, `aria-selected`, `role`)
- Focus rings with 3px offset on all focusable elements
- Minimum contrast ratio 4.5:1 for all body text (WCAG AA), 3:1 for large text
- Touch targets minimum 44×44px (Apple HIG / Google Material)
- Respect `prefers-reduced-motion` — turn off auto-playing animations, use `transition-duration: 0.01ms` as fallback
- Never convey information through colour alone — add icons, text labels, or patterns
- Test with zoom at 200% — does the layout break?

### Trap 8: Perceived Performance ≠ Actual Performance

**Pattern:** AI measures load time (800ms). Human feels jank, stutter, or "this feels slow even though it's 800ms."

Load Time (ms) and Perceived Performance do not map 1:1. A page that loads in 800ms but has layout shift, late-breaking images, or janky scroll will feel slower than a 1200ms page that renders progressively.

**Detection:**
1. Record 60fps video of every animation/transition — any frame drop below 55fps is jank
2. Measure Time to Interactive (TTI) and First Meaningful Paint (FMP) from cold start on a mid-tier laptop
3. Watch for Cumulative Layout Shift (CLS) — content jumping after the user has started reading
4. Test on throttled CPU (4x slowdown) and throttled network (Slow 3G)
5. Test scroll smoothness with content loaded — does scrolling hitch when new sections lazy-load?

**Remedy:**
- Reserve fixed heights for all images, skeletons, and async-loaded containers to prevent layout shift
- Use `content-visibility: auto` on sections below the fold — defer rendering, not loading
- Avoid late-loading images or resources that shift the page after first paint
- Use `will-change: transform` sparingly and only for elements that actually animate
- Test on a mid-tier machine (not a MacBook Pro) before shipping

### Trap 9: Visual Consistency ≠ Design-System Fidelity

**Pattern:** AI checks "button exists" and "button is blue." Human notices one button is `#3b82f6` and another is `#2563eb` — the page feels "off" even though everything works.

**Detection:**
1. Automated audit of every color token, spacing scale, border radius, icon weight, and typography ramp
2. Manual scan: does any element stand out as "wrong" (wrong font size, wrong spacing, wrong colour)?
3. Check every button, card, badge, and chip against the design-system tokens file
4. Check icon consistency: are all icons from the same set? Same stroke weight?
5. Check every container with `overflow: hidden`: does its content fit, or does text/buttons touch the container edges? No content should be flush against a container border — minimum 12-16px internal padding.

**Remedy:**
- Every visual token must come from a single source of truth (DESIGN.md, tokens.css, or a design-system component library)
- Enforce token usage with lint rules where possible (stylelint, TypeScript types)
- One-off buttons or custom-styled components must be approved by a human — they almost always drift from spec
- Even one off-brand button or misaligned card destroys the "premium" feeling

### Trap 10: First-Use Experience ≠ Expert Experience

**Pattern:** The product works well for Sean (who built it and knows every feature). A new user hits the dashboard cold and has no idea what to do first, second, or third.

This is by far the most expensive trap to miss — it determines whether the user stays for 5 minutes or 5 months.

**Detection (test as a cold first-time user):**
1. Clear all localStorage, open an incognito window
2. First 10 seconds: what does the user feel? (overwhelmed, confused, excited, confident?)
3. Can they answer "What is this dashboard for?" without reading help docs?
4. Can they answer "What should I do first?" from what's on screen?
5. Walk through the 3 most common first-user tasks. Record every hesitation, wrong click, and "I don't know what this is" moment.

**Remedy:**
- First-visit banner: "Welcome to ObserveCo — here's what you can do in 5 minutes"
- Guided tour or progressive onboarding: show 3 core actions, let the user complete them
- Every empty state must answer: "What should I do to populate this?"
- Default view should show the most valuable information first; secondary features are collapsed or one click away
- Add micro-copy near primary actions: "Start by adding an agent" instead of just an empty list
- Measure onboarding completion rate — if users drop off before completing the first action, the onboarding is too complex

---

## 4. The Testing Protocol

This is the **minimum viable human-lens evaluation**. Apply it before any frontend deliverable is marked complete.

### 4.1 The Golden Gate (run by Hound or any agent)

```
Before marking any frontend work done, run this 16-point gate:

1. SCREENSHOT the page in its current state
2. Answer for every section: does this look complete or broken?
3. CLICK every interactive element once. Does something visible happen within 200ms?
4. HARD-RELOAD (cache cleared). Record what shows in frames 0-3 seconds.
5. READ every text element. Can you read it at normal viewing distance without squinting?
6. SIMULATE an API failure (kill the data source). Does the page degrade gracefully?
7. CHECK for empty sections: does each one explain itself or sit there blank?
8. CHECK for context breaks: every click stays on the same page or uses inline overlay — no page redirects for secondary actions
9. CHECK every navigation path: is there a one-click way back? Does back button work?
10. TEXT SELECTION — open every modal with an input, drag-select text across boundary, confirm overlay stays open
11. ENTITY-TYPE-AWARE RENDERING — for any card list with heterogeneous types: confirm type-specific metrics (Confidence, Guard, Brain size, Composition) are gated behind entity type — never render irrelevant metrics with misleading empty states like "Learning..."
12. RENDER ORDER — define the expected render order (top→bottom) in the spec, then verify template/section concatenation matches it
13. STATE REFRESH — after any modal action (activate, deactivate, cancel, subscribe), does the badge/status update within 1 second without page reload?
14. DATA PROVENANCE — for every number on the page: can it be traced to a real computation? If not, is it clearly labeled as estimated or unavailable?
15. MODAL STACKING — after clicking any "Full Details" or "Details" button inside a modal: verify the parent modal is closed before the child modal opens. Confirm only one modal overlay is active at a time.
16. SCROLL-FIRST-MODAL — for every modal with action buttons: are the buttons visible without scrolling? If the modal has a scrollable detail section, action buttons must be above the fold or in a sticky footer.

One-line pass/fail per check. If any fails, the deliverable is not complete.

For every check, also pass through the Accessibility lens (Layer 4):
  - Can all 12 points be completed with keyboard-only navigation?
  - Does every interactive element have an ARIA label?
  - Does any information rely on colour alone?
```

### 4.2 When to Run

| Phase | Trigger | Gate |
|-------|---------|------|
| **Build** | Each new section/component | Visual completeness + click feedback + keyboard navigation |
| **Integration** | All sections wired to real data | Loading sequence + empty states + accessibility audit |
| **Pre-launch** | Before sharing with any human | Full 9-point gate above + Layer 4 & 5 evaluation |
| **Regression** | Any backend/api change | Loading sequence + error fallback + accessibility smoke test |

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

### Prompt 7: Accessibility & Inclusion (targets Layer 4 + Trap 7)

```
Run a full accessibility + inclusion pass on the ObserveCo dashboard at localhost:9122.

1. Keyboard-only navigation: tab through every card, button, tab, and expandable section. Is focus ever trapped or invisible? Are all actions reachable without a mouse?
2. Screen-reader audit (simulate VoiceOver): does every interactive element announce its state and purpose? Are dynamic content changes announced (aria-live regions)?
3. Colour-blind simulator + contrast audit on every text/icon pair. Does any information rely on colour alone?
4. Touch targets: are all clickable areas ≥44×44px on mobile viewports?
5. Reduced-motion mode: do all animations respect @media (prefers-reduced-motion)?
6. Zoom to 200%: does the layout break or overflow?
7. Contrast check: minimum 4.5:1 for body text, 3:1 for large text.

Deliver: accessibility scorecard (PASS/WARN/FAIL per dimension) + annotated screenshots of every violation.
```

### Prompt 8: First-Use & Emotional Load (targets Layer 5 + Trap 10)

```
Test the dashboard as a cold first-time user (clear all localStorage, new incognito window).

1. First 10 seconds: what does a brand-new user feel? (overwhelmed, confused, excited, confident?)
2. Can they answer "What is this dashboard for?" and "What should I do first?" without help?
3. Walk through the three most common tasks a new user would attempt:
   - Finding the agent with the highest error count
   - Understanding whether the system is healthy or broken
   - Taking a corrective action
   Record friction points, wrong clicks, hesitations.
4. Rate emotional load on a 1-10 scale for each section (1 = calm/confident, 10 = overwhelmed/anxious).
5. Does the dashboard feel like it was built for an expert or for a first-time user?

Deliver: first-use journey map + emotional heat map per section + recommended micro-copy or scaffolding changes.
```

After any screenshot command in Prompts 7 or 8, you must output the exact image ID or base64 thumbnail so the reviewer can verify you actually captured it.

---

## 6. Pathway Map UX Testing — The Graph Visualization Gate

**This section is dedicated to the unique UX testing challenges of directed graph visualizations (Cytoscape.js pathway maps).** The 5-layer framework and 10 traps above apply generically — this section covers the additional failure modes that only exist in graph-based UIs.

Graph UIs violate the fundamental assumption of every other UI type: that the visual layout is predictable. In a graph, the layout is computed at runtime and changes every time data or filters change. This introduces failure modes that don't exist in card-based dashboards or modal-based interfaces.

### 6.1 The Pathway Map UX Audit

```
┌──────────────────────────────────────────────────────────────────┐
│ PATHWAY MAP UX GATE — The Human Lens on Graphs                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│ GRAPH READABILITY                                                 │
│  [ ] Can you trace any path from source → consumer in <3 seconds? │
│  [ ] Do any two nodes overlap or obscure each other?              │
│  [ ] Are edge labels readable (not covering nodes/other edges)?   │
│  [ ] Does the graph look "full" at default zoom (not too sparse)? │
│  [ ] Does the left-to-right flow match the mental model of comms? │
│                                                                    │
│ LEGEND & COLOR                                                     │
│  [ ] Every node type in the graph has a match in the legend       │
│  [ ] Every edge color (green/yellow/red/teal) has a legend entry  │
│  [ ] Dead-end × markers are explained in the legend               │
│  [ ] Colors are distinguishable without reading labels            │
│  [ ] Color-blind test: red-green edge status still comprehensible │
│                                                                    │
│ INTERACTION                                                       │
│  [ ] Click node → detail panel updates in <100ms                 │
│  [ ] Click edge → detail shows source/status/mechanism            │
│  [ ] Click background → detail panel resets to idle               │
│  [ ] Pan & zoom: smooth (no jank at 50+ nodes)                    │
│  [ ] Reset Layout button works after zooming/panning              │
│  [ ] Refresh button works (destroy + reload + relayout)           │
│                                                                    │
│ FILTERING                                                         │
│  [ ] All filter shows everything (baseline)                       │
│  [ ] Green filter: only green edges + connected nodes visible     │
│  [ ] Red filter: only dead-end edges visible, no orphans          │
│  [ ] Yellow filter: only concern edges + connected nodes          │
│  [ ] Filtering animates (doesn't jump)                            │
│  [ ] After filter change: layout re-settles, no overlap           │
│  [ ] Dead-end nodes hidden when filtering green                   │
│                                                                    │
│ DETAIL PANEL                                                      │
│  [ ] Node detail shows correct name, type, ID, framework          │
│  [ ] Connections listed match actual edge count in graph          │
│  [ ] Edge detail shows source → target with status                │
│  [ ] Dead-end edge detail explains "no consumer — data lost"      │
│  [ ] Connected edge ref click → highlights that edge in graph     │
│  [ ] Empty state (no selection): helpful prompt, not blank        │
│                                                                    │
│ FIRST USE & EMOTIONAL LOAD                                        │
│  [ ] User understands "what am I looking at?" in <10 seconds      │
│  [ ] User can identify the most broken path without training      │
│  [ ] User can identify the healthiest path without training       │
│  [ ] The graph feels explorable, not overwhelming                 │
│  [ ] A first-time user can answer "what should I fix first?"      │
│                                                                    │
│ PASS/FAIL: ___/28 (≥25 = pass, <25 = do not ship)                 │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Graph-Specific Traps (Trap 11—17)

In addition to the 10 generic traps, pathway maps have 7 unique traps:

#### Trap 11: The Layout Is Correct but the Graph Is Unreadable

**Pattern:** Dagre renders every node in the correct rank order with no overlap. But edges cross 8 times, labels overlap edges, and dead-end stubs cluster in a corner. All rendering is technically correct. Human can't read the graph.

The difference between "correct layout" and "readable layout" in graph visualization:
- Correct: every node is positioned, no overlap, proper rank assignment
- Readable: the most important paths are visually distinct, edges don't cross frequently, labels don't overlap, dead ends are clearly visible

**Detection:**
1. Can you trace any single path from source → dead end without losing it in crossing edges?
2. Are there edge crossings within the same rank? (these are avoidable with rankSep tuning)
3. Do any labels overlap edges or other nodes?
4. Are dead-end stubs spread out or clustered into a hard-to-click group?

**Remedy:**
```javascript
// Tune dagre parameters for readability, not just validity
cy.layout({
    name: 'dagre',
    rankDir: 'LR',
    spacingFactor: 1.5,     // Increase from default 1.0 to reduce overlap
    nodeSep: 40,             // Minimum vertical space between nodes
    rankSep: 80,             // Minimum horizontal distance between ranks
    edgeSep: 20,             // Minimum distance between edges
    animate: true,
    animationDuration: 300,
}).run();
```

#### Trap 12: Data Integrity Passes but Visual Integrity Fails

**Pattern:** The `verify_pathway_data()` SQL query reports 0 orphans, 0 bad edges, 0 duplicates — the data layer is clean. But the visual render shows edges pointing at wrong targets, nodes in wrong ranks, or dead-end stubs that don't correspond to the right source edge.

This happens when the frontend JS processing of the DB data introduces its own bugs:
- Dead-end stub IDs reused → multiple edges collapse into one target node
- `nodeMap` lookup by string ID doesn't match the actual node IDs from the DB
- Edge `source_id`/`target_id` processing applies a normalization that doesn't match DB values
- Filter logic hides nodes that should be visible (or vice versa)

**Detection:**
1. Click a dead-end edge. Does the detail panel show the correct source node name?
2. Count visible nodes vs DB node count. Are any missing?
3. Click "All" filter, then click "Red". Do exactly the right nodes disappear?
4. For a known-complete path (green edge with both ends populated): click both ends and verify the edge connects them

**Remedy:**
```javascript
// Add data-integrity logging to the frontend
function logIntegrityCheck() {
    const nodes = cy.nodes().map(n => n.id());
    const edges = cy.edges().map(e => ({
        id: e.id(), source: e.source().id(), target: e.target().id()
    }));
    console.log('Rendered nodes:', nodes.length);
    console.log('Rendered edges:', edges.length);
    console.log('Edge-source match:', edges.every(e => nodes.includes(e.source)));
    console.log('Edge-target match:', edges.every(e => nodes.includes(e.target)));
    // Check for duplicate edge targets (dead-end collapse)
    const deadTargets = edges.filter(e => e.target.startsWith('__dead__'));
    const uniqueDead = new Set(deadTargets.map(e => e.target));
    if (deadTargets.length !== uniqueDead.size) {
        console.warn('DUPLICATE DEAD-END STUB: edges collapsed');
    }
}
```

#### Trap 13: Filtering Changes Meaning (the "Green Filter" Fallacy)

**Pattern:** User clicks "🟢 Complete" filter. Graph shows only green edges and their connected nodes. User concludes: "All these paths are healthy." But the filter has hidden ALL yellow and red paths — the user now has a misleadingly clean picture of the system.

This is unique to graph UIs. In a table, filtering by status shows a subset of rows — the user implicitly knows they're looking at a subset. In a graph, filtering removes entire nodes and edges, and the remaining graph still looks like a complete system. The user forgets they're looking at a filtered view.

**Detection:**
1. Activate each filter. For each one: does the filter toolbar clearly indicate that a filter is active?
2. Does the summary count update to show "N of M edges visible"?
3. Would a user who just clicked around for 30 seconds know they're in a filtered view?
4. Does the "All" filter restore everything?

**Remedy:**
```javascript
// After any filter change, update the filter toolbar
function updateFilterDisplay(filter, count, total) {
    const label = document.getElementById('filter-label');
    label.textContent = total > 0
        ? `Showing ${count} of ${total} elements`
        : `${total} elements`;
    // Highlight active filter button more prominently than inactive
}
```

**The one-question test:** Show someone the filtered graph without telling them a filter is active. Do they think this is the complete system? If yes, the filter needs a more prominent indicator.

#### Trap 14: Visual Representation Is Correct but Overflows the Container

**Pattern:** Data layer is correct (correct number of status dots, correct colours). But the visual representation chosen (emoji, unicode symbols, oversized icons) doesn't fit the allocated container at the rendered size.

Emoji have no fixed intrinsic dimensions — they vary by OS, font, and rendering engine. A 10×10px box that works with CSS dots will overflow with emoji at the same dimensions. The legend row overlaps the dot row because emoji characters exceed their nominal font-size bounding box.

**Detection:**
1. For every data-to-visual indicator: is it a CSS element (`div` with `background-color`) or a text character (emoji, unicode symbol)?
2. If text: pin the `font-size` explicitly, or switch to CSS-only elements
3. Check every pair of adjacent rows: does content from row N visually overlap row N+1?
4. Test on Safari, Chrome, and Mac vs Linux — emoji rendering varies significantly
5. For pulse dots specifically: CSS `width + height + border-radius` is deterministic. Emoji `🟢🔴🟡` at `font-size: 10px` is not — it renders at the host platform's emoji cell size.
6. At the code level: does the element use `display: inline` (behaves like text, can push past container) or `display: inline-block` with explicit dimensions?

**Fix pattern:**
- Use CSS-only elements for fixed-dimension indicators: `<div class="pulse-dot ok"></div>` not `<span>🟢</span>`
- For colored dots: `display: inline-block; width: 10px; height: 10px; border-radius: 2px;`
- Legends must use the same CSS class, not repeat the emoji
- Apply `flex-shrink: 0` and `line-height: 1` on indicator containers
- When there's a legend below a timeline of dots, add `margin-top` to the legend and verify no overlap in a screenshot — don't trust the computed style alone

#### Trap 15: Inline Reference Text Was Never Verified

**Pattern:** Dashboard help text, error messages, or CLI output tells the user to run a command. Nobody verified the exact command works on the installed binary.

**Root cause:** The developer assumes CLI flags match the internal function name. `watch.py` has a `start()` function → developer writes `observeco watch --daemon`. But the CLI uses subcommands, not flags — the real command is `observeco watch start`. The user hits the error and loses confidence in the product.

**Detection (before shipping ANY inline command text):**
1. Run the EXACT command string in a fresh terminal
2. Does it work? (exit 0, correct output)
3. If it fails: is this the wrong flag, wrong subcommand, or wrong product?
4. For CLI help text listed in the UI: run `observeco <command> --help` and verify the documented flags/subcommands actually exist in the output
5. If the command can't be tested (e.g., requires a remote server): mark it with a `<!-- @verify-command -->` comment and test before release

**Fix pattern:**
- Every inline command in the dashboard HTML, error messages, and documentation must be tested against the live CLI — not assumed from function signatures
- Run `observeco <command> --help` and grep for each flag or subcommand listed
- Use a simple CI step: `grep -rn 'observeco [a-z]' templates/ | cut -d' ' -f2-4 | while read cmd; do $cmd --help >/dev/null 2>&1 || echo "BROKEN: $cmd"; done`
- When the CLI interface changes, grep all templates for affected command strings

#### Trap 16: Renamed JS Function Leaves Dead Call in HTML Template

**Pattern:** Developer renames a JavaScript function (e.g. `applyFilter` → `applyFilters`). Python linters pass. The project uses vanilla JS in HTML templates (`.html` files). The old function name persists in a cytoscape callback, event listener, or inline `<script>` block. The page breaks silently — or worse, only breaks on a specific user interaction.

**Why AI misses this:** AI sees the rename in the JS file and the old name in the template's HTML and resolves the contradiction by assuming the template is correct. Without a type system or linter that understands the JS-in-HTML relationship, neither the builder nor the reviewer catches it.

**Detection:**
1. After ANY JS function rename, run: `grep -rn 'oldFunctionName' templates/`
2. Check every occurrence: is it a definition to update or a call site to rename?
3. Specifically check: `onclick=` attributes, event listeners (`cy.on()`, `addEventListener`), `onchange=` handlers, `setTimeout`/`setInterval` callbacks, template literals that construct JS code
4. Hard-reload the page (Cmd+Shift+R) and check the browser console for: `ReferenceError: oldFunctionName is not defined`
5. If the function is called inside a library callback (cytoscape init, plotly config, chart render), it won't fire on page load — you must trigger the specific interaction to catch it

**Fix pattern:**
- Add a project convention: when renaming a JS function that's called from HTML, grep ALL templates BEFORE merging
- Better: define all interactive JS functions in a single `.js` file and import them — ESLint or TypeScript would then catch dead references
- At minimum: after any JS refactor that touches interactive functions, hard-reload the page, simulate each user interaction, and check the console
- Add a post-refactor checklist item to the Golden Gate (Section 4.1): "After JS renames, grep templates for old name"

#### Trap 17: Dead-End Detail Is Confusing (Trap 5 variant)

**Pattern:** User clicks a dead-end red edge. Detail panel shows: "Dead End — This path has no consumer. Messages delivered here will be lost." The data is accurate. The language is accurate. The user still doesn't understand what to *do* about it.

The gap: telling someone WHAT is wrong is not the same as telling them WHY it matters or WHAT to fix.

**Dead-end detail must answer three questions:**
1. **What exactly is missing?** — "No consumer found for the output of [source agent/cron]"
2. **Why does this matter?** — "Any signal sent from [source] to this destination will be lost"
3. **What should the user do?** — "Declare the consumer (observeco pathway add --consumer X) or confirm this is intentional (observeco pathway exempt --reason 'deliberately dangling')"

**Detection:** Click every dead-end edge. For each one:
- Does the detail panel answer all three questions?
- Can a first-time user understand the dead end's impact without asking for help?
- Is there an actionable next step displayed?

---

#### Trap 18: Overlay Dismiss on Text Selection

**Pattern:** User opens a modal/overlay/popup with an input field. The overlay has a click-to-dismiss handler on the background (`if (event.target === this) close()`). The user triple-clicks or drag-selects text inside the input to copy a license key, token, or error message. The mouseup event lands on the overlay background (cursor drifted during selection), the click fires, and the overlay disappears — losing the user's work mid-copy.

**Why AI misses this:** AI navigates via programmatic selectors. It types into the input, reads the value, and clicks submit — text selection never enters its test flow. The overlay dismissal feels correct during automated interaction because the click event never lands on the background. Only a human dragging with a mouse hits this.

**Detection:**
1. Open any overlay that contains an input or selectable text
2. Triple-click a word inside the input field
3. Drag-select from the start of the input to well past its boundary (simulating a user selecting an entire key string)
4. Does the overlay dismiss itself when the mouseup fires?
5. Repeat by selecting text in result/error/status messages inside the overlay (the success "✅ Key activated!" or error text)
6. Also test: select text in the input, then right-click (context menu) — does the overlay dismiss on mousedown?

**Root cause checklist:**
- Overlay has an `onclick` or `addEventListener('click')` handler on the background that checks `e.target === this`
- The inner content div does NOT call `event.stopPropagation()` on click
- The overlay uses `click` (mouseup + mousedown within same element) instead of `mousedown` for dismissal — click events are cancelled by text selection, but a subsequent mouseup outside the content box after a drag fires the click handler

**Fix pattern:**
- Add `onclick="event.stopPropagation()"` to the inner content `<div>` — clicks inside the card never reach the overlay handler, but clicking the background directly still closes
- Alternative: use `onmousedown` instead of `onclick` for dismissal (fewer false positives during selection) but this makes the overlay more aggressive
- Verify: clicking the overlay background still dismisses; clicking inside the card never does
- For input fields specifically: don't dismiss on click at all when the user has text selected (`window.getSelection().toString() !== ''`)

**Golden Gate addition:** After item 8 (back navigation), insert: `8.5 TEXT SELECTION — open every modal with an input, drag-select text across boundary, confirm overlay stays open.`

---

#### Trap 20: Cross-System Format/State Inconsistency — Paired Paths That Must Agree

**Pattern:** Two independent code paths generate, validate, or consume the same data shape (license key format, DB column set, state machine transitions). They are maintained by different developers or at different times. One changes — the other doesn't. The result is a silent inconsistency: keys that pass validation can't be generated, INSERT queries reference columns that don't exist, or state transitions mismatch.

**Why AI misses this:** AI evaluates each path in isolation. When asked to fix a key generator, the AI fixes the generator without cross-referencing the validator. Both paths "look correct" individually. Only a cross-system assertion catches the mismatch.

**Detection:**
1. Find every pair of independent paths that must agree on a format or schema:
   - Key generators ↔ validators (same regex/format string)
   - INSERT queries ↔ CREATE TABLE DDL (same column set)
   - State machine producer ↔ consumer (same states and transitions)
   - Migration scripts ↔ startup runner (migration wired in?)
2. Extract the actual format/column/state values from each path
3. Compare them. Do they use the same format string, same column references, same ENUM values?

**Fix pattern:**
```python
# Define the format ONCE, reference from both paths:
LICENSE_KEY_PATTERN = r'^OBS-PRO-[A-Z0-9]{8}-[A-Z0-9]{6}$'

# Generator:
key = f"OBS-PRO-{secrets.token_hex(4).upper()}-{secrets.token_hex(3).upper()}"

# Validator:
import re
if not re.match(LICENSE_KEY_PATTERN, key):
    raise ValueError("Invalid key format")
```
- For DB columns: share a column definition dict between `CREATE TABLE` and `INSERT`
- For migrations: add every migration to the auto-run list in the same PR that creates the migration file
- **Rule of thumb:** If you can grep for a format string in two places without them referencing a shared constant, you have a bug waiting to happen

**Real example (ObserveCo, 2026-06-08):** CRM admin issued `OBS-ADMIN-XXXXXXXX`. Stripe webhook issued `OBS-XXXXXXXX-XXXX`. Validator expected `OBS-PRO-XXXXXXXX-XXXXXX`. Three independent format strings, all correct individually, all wrong together. Fix: define format once, reference from all three paths.

---

#### Trap 21: Hardcoded Ephemeral Value — Single-Use Tokens/Sessions in Production Templates

**Pattern:** A single-use URL or session token (Stripe Checkout `cs_live_...`, GitHub token `ghp_...`, API key `sk_live_...`) is hardcoded directly into a template or config file. It works when first written. Weeks later, the token expires or is consumed. The link silently breaks with no error, no 404, no fallback. The user clicks a dead button.

**Why AI misses this:** AI tests the template at the time of writing — the URL works, so the test passes. The AI has no concept of "this value will expire" because it has no model of the external service's token lifecycle.

**Detection (pre-ship CI gate):**
```bash
# Check for known ephemeral value patterns in templates
grep -rnE '(cs_|sk_|pk_|tok_|ghp_|gho_|ghs_)[A-Za-z0-9]{20,}' templates/ src/ 2>/dev/null
# Check for any 60+ character alphanumeric URL segment
grep -rnE '/[A-Za-z0-9_-]{60,}' templates/ src/ 2>/dev/null | grep -v 'node_modules\|\.git\|test_'
```
Flag ALL matches. Each must have a comment explaining why it's static, or be replaced with a dynamic endpoint.

**Fix pattern:**
- Replace with a backend endpoint that generates or retrieves the value at request time: `href="/api/checkout?plan=solo&trial=30"` not `href="https://checkout.stripe.com/pay/cs_live_..."`
- For truly static values (documentation links, icon URLs), add a comment: `<!-- STATIC: this is a permanent documentation URL -->`
- If it must be a fixed value, add a cron job that checks the URL returns 200 and flags it if it goes stale

**Real example (ObserveCo, 2026-06-08):** "Start Free Trial" button hardcoded a single-use Stripe Checkout session URL (`cs_live_a1xg...`). After the session was consumed, the link returned a Stripe 404. Three copies existed across `index.html` (2) and `licenses_api.py` (1). Fix: replace all three with `/api/checkout?plan=solo&trial=30`.

---

#### Trap 22: Schema-Code Drift — DDL and INSERT Query Don't Match

**Pattern:** A column is added to an INSERT statement (new feature needs new data) but never added to the table's CREATE TABLE DDL. Or a migration script exists on disk but was never wired into the auto-run startup chain. Data writes fail silently — the error is logged but no one reads the error log for this specific table. Result: zero data in that table, empty dashboards, confusing "no data" states everywhere.

**Why AI misses this:** AI adds the column to the INSERT without checking the DDL because the DDL is in a different file or was written months ago. The migration script "doesn't look broken" because it's syntactically valid SQL — it just never runs. The AI evaluates the INSERT and the migration as independent artifacts, not paired artifacts that must agree.

**Detection:**
1. For every INSERT or UPDATE query, find the corresponding CREATE TABLE or ALTER TABLE statement that defines those columns
2. Extract the column set from each — do they match?
3. For every migration file on disk: does it have a slot in the auto-run migration pipeline? Run `grep` for the migration filename in the startup code
4. Check: if SCHEMA_VERSION was bumped, was the migration entry added to MIGRATIONS dict?

**Fix pattern:**
- Define columns once, reference from both places
- Every migration script must be in the auto-run list before the PR merges
- After adding a new column to an INSERT, run the create-table DDL to verify the column exists
- When you bump SCHEMA_VERSION, immediately check that a MIGRATIONS entry exists for that version

**Real example (ObserveCo, 2026-06-09):** `log_trim()` was updated to INSERT a `mode` column, but the `chisel_trims` table DDL at schema v11 never received the column. A migration script existed at `chisel/migrations.py` but was never wired into `db.py`'s auto-run pipeline. Every watch daemon probe crashed with `table chisel_trims has no column named mode` — 1,265 errors accumulated, trim and drift tables stayed empty for days. Fix: bumped schema to v12, wired the migration into `db.py:MIGRATIONS`, schema auto-upgraded on next init.

---

#### Trap 23: Render Order Drift — Information Hierarchy vs Template Order

**Pattern:** The spec or mockup defines a clear information hierarchy (Section A → B → C, top to bottom). The server-side template builds sections in a different order (C → A → B or jumbled). Every section renders correctly with correct data — the order is just wrong. The human reads the page in a sequence that contradicts the designed narrative.

**Why AI misses this:** AI verifies each section exists and renders correctly. The template builds sections by composing strings or JS templates; the AI evaluates the output as individual sections, never the sequence. Ordering is a presentational concern invisible to function-level verification.

**Detection:**
1. List every top-level section of the page in the order the spec/mockup specifies (top→bottom)
2. Read the server template or mockup HTML — extract the section markers in the sequence they appear
3. Compare. Do they match?
4. For server-side `js_string` composition: grep for each section variable assignment and check the order they're concatenated

**Fix pattern:**
- Document the expected render order in the spec as part of every page design
- In the template, concatenate sections in spec order — don't let code evolution reorder them
- Add a comment at each concatenation point: `/* ORDER: A → B → C — keep in spec order */`
- After any multi-section page edit: diff the template section concatenation order against the spec

**Real example (ObserveCo health popup, 2026-06-08):** Mockup showed Last 24 Hours → Confidence → Signal Analysis. Server template built Confidence header first, then Last 24 Hours, then Signal Analysis. Fixed by moving `{conf_header}` into the Signal Analysis section during string concatenation.

---

#### Trap 24: Entity-Type-Aware Rendering — Irrelevant Metrics on Heterogeneous Card Lists

**Pattern:** A dashboard renders a heterogeneous list of cards (agents, services, workflows, crons). All cards use the same template, which renders every metric row unconditionally. A cron card shows `📈 Learning...` for token drift, `⚪ No data (not pulse-monitored)` for Guard, and `No brain data` for Composition. The user interprets these as bugs or missing features — not as "this metric doesn't apply to my entity type."

**Why AI misses this:** AI verifies the card renders (DOM exists) and the data is correct (no error state). The misleading empty state is technically correct — there's genuinely no data for that type. The AI doesn't reason about whether the metric *applies* to this entity type.

**Detection:**
1. List every metric row on each card type
2. For each row, ask: "Does this concept apply to every entity type in this list?"
3. If no: does the row actually tell the user "not applicable" — or does it just show an empty state that reads as "broken"?
4. Check specifically for: `📈 Learning...` (sounds intentional — most dangerous), `⚪ No data` (sounds like missing data), `No brain data` (sounds like something failed)

**Fix pattern:**
```python
# Gate type-specific rows by entity type. The classifier already exists.
is_agent = agent_type == 'agent'
```
- Universal rows (Health, Errors) remain unconditional — every entity has status and can produce errors
- See `ux-testing-playbook skill references/entity-type-aware-card-rendering.md` for the full pattern

**Real example (ObserveCo agent cards, 2026-06-08):** All 6 metric rows (Confidence, Guard, Errors, Health, Brain, Composition) rendered for every entity type. Services showed `📈 Learning...` for token drift (irrelevant) and `⚪ No data` for Guard (no circuit breaker). Fixed by gating Confidence, Guard, Brain size, and Composition rows behind `agent_type == 'agent'`.

---

#### Trap 25: Misleading Data — "Real Enough to Confuse"

**Pattern:** A data point that is fabricated, estimated, or derived from a heuristic is presented in the same visual style as real data. The user cannot distinguish "this is a real measurement" from "this is a rough guess." The product looks active and data-rich — but the numbers are theatre.

**Why AI misses this:** AI verifies the data renders correctly (correct value, correct unit, correct position). The AI has no concept of data provenance — it cannot distinguish "this 58% came from real compress_log entries" from "this 58% was hardcoded as a sales upsell."

**Detection:**
1. Trace every number rendered in the UI back to its source: is it a real computation, a heuristic, a hardcoded default, or a fallback?
2. If it's a heuristic or estimate: is it visually distinguished from real data? (different colour, different icon, explicit "(estimated)" label)
3. If it's hardcoded: can the user tell this is static content and not a live measurement?
4. Specifically check: savings percentages, usage statistics, "learned from X turns" counters, "optimised X skills" claims, comparison metrics

**Fix pattern:**
- Every number in the UI must have a `data-source` attribute: `data-source="real"`, `data-source="potential"`, or `data-source="none"`
- Estimated/potential values must be visually distinct: muted colour, "(based on composition)" suffix, ▲ indicator
- Hardcoded default/fallback values must NEVER resemble real data — use `—` (em dash) or "Run X to see data" empty state
- Add a data provenance section to every analytics/insights page: "Sources: real compress_log (agent A, B) · potential from composition (agent C, D)"

**Real example (ObserveCo, 2026-06-09):** Brain Analysis tab showed "58% savings — learned from 116 turns" for the Token Optimiser. The 58% was hardcoded. The "116 turns" was hardcoded. "3 of 8 skills" was hardcoded. All looked like real data. Fixed: replaced with `—` placeholders until real compress_log data exists. Added `savings_source` field with 3 states: `actual`, `potential`, `none`.

---

#### Trap 26: Subscription State Confusion — Action Visible When It Shouldn't Be

**Pattern:** A billing or subscription button is visible in a state where it doesn't make sense. User sees "Subscribe $9/mo" while actively on a Solo plan trial. The user wonders: "Can I subscribe twice? Will I lose my trial? Is this an upgrade or a new subscription?"

**Why AI misses this:** AI verifies the button exists, the button is clickable, and the payment flow starts. The AI has no model of the user's current subscription state, so it cannot detect that the button's presence contradicts that state.

**Detection:**
1. Enumerate ALL possible license states: free trial (solo), free trial (pro), solo paid, pro paid, pro license-key, cancelled, expired, deactivated, grace period
2. For each state, list every billing/subscription button and whether it should be visible:
   - On solo trial: "Subscribe $9/mo" is confusing — should be "Manage Trial" or hidden
   - On pro trial: "Subscribe" buttons should be visible (they upgrade)
   - On cancelled: "Reactivate" should replace "Cancel"
   - On expired: "Renew" should replace "Subscribe"
3. Test each state → each button state in a matrix. Any mismatch is a violation

**Fix pattern:**
- The billing button must be a function of `(current_plan, current_status, is_active)`, not a static label
- Never show a primary action button whose result contradicts the user's current state
- If a button would produce an confusing result (charging someone who's already subscribed), hide it or add explanatory text

**Real example (ObserveCo, 2026-06-09):** Solo trial user saw "Subscribe $9/mo Cancel Trial" buttons. "Cancel Trial" makes sense. "Subscribe $9/mo" alongside it raises "will I be charged twice?" confusion. Fixed: hide "Subscribe" when user is on an active paid-or-trial plan; show "Manage Subscription" instead.

---

#### Trap 27: Pro Activation Gap — Payment Success ≠ Feature Unlock

**Pattern:** User completes payment. Stripe says "successful." The dashboard still shows Free tier. Payment went through — Pro didn't activate. The gap between "payment accepted" and "feature unlocked" has a bug that's invisible unless you test the full pipeline.

**Why AI misses this:** AI tests the payment flow and the license activation flow as separate units. The Stripe webhook handler was tested in isolation ("it records the customer OK"). The license state change was tested in isolation ("set_state(pro) works OK"). Nobody ran the end-to-end test: pay → webhook fires → license changes → badge updates.

**Detection:**
1. Map every state transition: user clicks pay → Stripe session → user pays → success URL → webhook fires → license state changes → badge refreshes → email sent
2. Each transition must have a verifiable output (log, state file, DOM change, email)
3. Test: complete a real payment. Wait 60 seconds. Is Pro active IN THE DASHBOARD?
4. Test: fail the payment. Does the user get a helpful error or a broken state?
5. Walk backwards from the badge: if badge says "Free" but payment says "paid", where did the chain break?

**Fix pattern:**
- The webhook handler must do THREE things: (1) record the customer, (2) activate the license, (3) verify activation took effect
- If any of the three fails, the whole transaction should be flagged for manual review
- Add a post-payment audit: after checkout.session.completed, re-read the license state and compare to expected
- Never assume "Stripe says paid → user has Pro." Verify it.

**Real example (ObserveCo, 2026-06-09):** Three independent bugs created a silent activation gap:
1. Success URL missing `{CHECKOUT_SESSION_ID}` template variable → webhook couldn't correlate session
2. Encryption key file corrupted (two Fernet keys concatenated) → `load_key()` silently fell back to simulation mode
3. Webhook handler recorded the customer but never called `start_trial()`
Fix: all three corrected, end-to-end payment→activation test now part of release protocol.

---

#### Trap 28: Backend Status ≠ Dashboard Status — The Incomplete Feature Claim

**Pattern:** A feature is marked "✅ Live" in the master plan, spec, or sprint review because the backend is complete. The dashboard UI for that feature was never built, or exists as a stub. Anyone reading the plan assumes the feature is fully done and user-facing.

**Why AI misses this:** AI evaluates the backend feature endpoint (HTTP 200, correct data) and sees no reason to check the frontend. The backend team says "done" and the AI accepts it. The frontend doesn't exist — but nobody asked "done where?"

**Detection:**
1. For every feature claim in the master plan, spec, or README: verify backend AND frontend independently
2. If the feature is "Push Alerts" but only the backend API exists, the correct status is "🟡 Partial — Backend ✅ / Dashboard ❌"
3. If a feature has a single row in the plan but needs both backend and frontend, split the row or use a two-part status column

**Fix pattern:**
- Every feature that touches the UI must have a two-part status: "Backend: ✅ / Dashboard: ✅"
- A feature is only "✅ Live" when BOTH are done and verified
- The master plan must independently audit backend+frontend status after every sprint
- Specs must define feature completion requirements for EACH layer, not just the backend

**Real example (ObserveCo, 2026-06-08):** Master plan showed Push Alerts and Auto-Heal as ✅ Live. Audit revealed both had complete backends but ❌ No dashboard UI. Users couldn't configure or see these features. Fixed: all features split into backend/dashboard status columns in master plan.

---

#### Trap 29: Silent Crash on Missing DOM Element

**Pattern:** A JavaScript function calls `document.getElementById('someElement')` and immediately accesses `.innerHTML`, `.classList`, or `.style` on the result. The element doesn't exist on the current page (different tab, different modal state, different user role). The function throws a silent TypeError that's caught by no one — it fires in an `onclick` handler or `setTimeout` callback, so the error bubbles to nowhere.

**Why AI misses this:** AI tests the function on the page where the element exists (Settings tab, Pro user). The function works — test passes. The AI never switches to a tab where the element is absent. A tab-switching test isn't part of any standard AI testing flow.

**Detection:**
1. Every JS function that accesses `document.getElementById()`, `querySelector()`, or `$()` must guard for null
2. Specifically check functions that are called FROM multiple tabs: `loadLicenseStatus()`, `updateBadge()`, `refreshPlan()`
3. Test every function on every tab/view where it could be invoked — not just the one where it was developed
4. Enable "Pause on uncaught exceptions" in DevTools and trigger every action across all tabs

**Fix pattern:**
```javascript
// Before accessing any property on a DOM lookup:
function updateBadge() {
    const badge = document.getElementById('tierBadge');
    if (!badge) return;  // Element not on this page — safe to skip
    badge.textContent = newStatus;
}
```
- This is the safest pattern: early return, no error, no crash.
- For tab-switching functions: add a guard at the top and return silently if the target element doesn't exist.
- Never assume `getElementById` returns a non-null value — every DOM lookup is a candidate for null.

**Real example (ObserveCo, 2026-06-08):** `loadLicenseStatus()` was called on every tab switch. It tried `document.getElementById('proTrialStatus').textContent = ...` on Fleet/Brain/Auto-Heal/Push tabs where `proTrialStatus` didn't exist. The crash was silent — no error visible to the user, but upsells never hid when Pro was active. 5 bugs traced to this single null access. Fix: added `if (!el) return;` guard.

---

#### Trap 30: Badge/State Refresh Missing After State Change

**Pattern:** User performs an action (activate license, deactivate license, cancel trial, subscribe). The backend state changes correctly. The UI badge, button labels, and feature access don't update until the user manually reloads the page.

**Why AI misses this:** AI tests the action and then checks the backend state. The backend says "activated" — test passes. The AI doesn't verify that the UI badge changed from "Free" to "Pro" without page reload, because the AI never looks at the badge after the action.

**Detection:**
1. For every state-changing action (activate, deactivate, cancel, subscribe): verify the UI updates WITHOUT page reload
2. Specifically check: tier badge text, button labels, locked/unlocked feature visibility, pricing display
3. Test the full loop: open modal → perform action → close modal → badge updated → correct buttons visible → locked features unlocked
4. If the badge updates only after a manual page refresh, it's a violation — even if the backend state is correct

**Fix pattern:**
- After any state-changing modal action, call a refresh function immediately: `loadLicenseStatus()` or `refreshBadge()`
- The refresh function should re-fetch state from the API, not assume the local state is correct
- If the modal needs to close before the refresh: call refresh in the modal's "onclose" handler, not inline
- Verify: open modal → change state → close modal → badge changes within 1 second without user action

**Real example (ObserveCo, 2026-06-08):** Activating or deactivating a license key updated the backend (license table status flipped) but the badge still showed the old state. The subscribe → cancel → re-subscribe cycle on Stripe side had the same problem. Fix: added `loadLicenseStatus()` call after every modal close, badge now refreshes from API on each modal dismiss.

---

#### Trap 31: Modal Stacking — Overlay Hides Overlay

**Pattern:** Clicking "Full Details" on a modal (A) opens a second modal (B). Modal B renders correctly but is invisible because modal A's overlay (same z-index: 100) stays on top. User sees no change and assumes nothing happened.

**Why AI misses this:** AI tests each modal in isolation — opens it, verifies content, closes it, moves on. Never tests modal A → modal B → interaction, because the AI calls `openChiselModal()` which renders content, but the AI doesn't check z-index stacking.

**Detection:**
1. Open every modal that has a "details" or "full view" button
2. Click the button. Can you see the new modal?
3. Check the DOM: are both modals now `class="active"` or `display: flex`?
4. If both overlays are active simultaneously, the second one is invisible

**Fix pattern:**
- Before opening modal B, close modal A (`closeModalA()` first)
- Or: set modal B's z-index to 101 (one above modal A)
- Better: use a single modal slot with content-swap instead of separate overlay elements
- After any `openChiselModal()` or `openDetailModal()` call, verify the parent modal overlay is not still active

**Real example (ObserveCo, 2026-06-10):** Skill Audit modal → "Full Details" button opens Token Optimiser modal. Both `skillsAuditModal` and `chiselModal` had `.active` class. Chisel modal rendered behind Skills Audit overlay. Fix: `closeSkillsAudit()` called before `openChiselModal()`.

---

#### Trap 32: Action Buried Below Scroll Threshold

**Pattern:** A modal or page contains summary data, a large scrollable detail section (50+ rows), and action buttons at the bottom. User must scroll past all detail content to reach "Apply" or "Save" buttons. The action is functionally correct — the user just never finds it.

**Why AI misses this:** AI reads the full content linearly (summary → table → category → actions). The AI's rendering context is infinite — it doesn't scroll. The AI sees the action buttons because it's already "at the bottom." The human, who must scroll through 50+ rows, may not reach them.

**Detection:**
1. Open the modal. Take a mental snapshot of what's visible without scrolling
2. If action buttons (Apply, Save, Close, Submit, Full Details) are NOT visible in that first viewport, it's a violation
3. Specifically check: modal height vs content height. If content height > viewport height and action buttons are below the fold, the actions are buried
4. Test on a 768px viewport (common laptop) — mobile-first users are most affected

**Fix pattern (in order of preference):**
1. **Reorder:** action-critical sections first, detail sections after. If Apply + Full Details are the reason the user opened the modal, show them immediately after the summary, before the scrollable detail
2. **Sticky footer:** make the action bar `position: sticky; bottom: 0` so it's always visible regardless of scroll position
3. **Separate panel:** split the modal into two areas — top (summary + actions) and bottom (scrollable detail)
4. **Never:** bury the primary action below a non-summary scrollable section

**Real example (ObserveCo, 2026-06-10):** Skill Audit modal had Summary → Skills Table (50+ rows) → Category → Compression Preview (with Apply + Full Details). User had to scroll past 50+ skills to reach the buttons. Fix: reordered to Summary → Compression Preview (with buttons) → Skills Table → Category.

---

#### Trap 33: Pro-Empty-State Mismatch

**Pattern:** A tab or feature shows an empty state designed for Free users even when the user has a Pro license. Same "run this CLI command" empty state for all users, ignoring that Pro users can trigger the action from the UI.

**Why AI misses this:** AI tests the endpoint returns the correct empty state content. The AI checks "does this show the empty state?" and gets a pass. The AI doesn't check whether the empty state's call-to-action matches the user's license tier.

**Detection:**
1. For every tab/section that has an empty state: what does it tell the user to do?
2. If it says "Run `observeco heal --agent all` in your terminal" — check if the user has Pro
3. If Pro: the empty state should offer a UI button instead of (or in addition to) a CLI command
4. If Free: CLI command is correct — that's the only option

**Fix pattern:**
- Pro empty states should offer server-side actions that don't require CLI access
- Free empty states keep CLI instructions (it's their only path)
- If the action is available in both modes, the Pro state should prefer the UI button
- The empty state endpoint must check license tier before rendering

**Real example (ObserveCo, 2026-06-10):** Restart Quality tab showed "Run `observeco heal --agent all`" for all users. Pro users got the same empty state as Free users despite having a "Run Pulse Scan" button available. Fix: Pro empty state now shows a clickable scan button, Free keeps the CLI hint.

---

## 7. Lessons Learned Log

Append here every time a human catches something an AI missed. This is how the playbook stays alive.

### 2026-05-29 — Playbook v1 Self-Review

| What was wrong | Category | Fix applied |
|---|---|---|
| Section 2 header said "Three" layers but only had 3 — now has 5 | Structural bug | Renamed to "Five Human-Experience Layers" with Layer 4 (Accessibility) and Layer 5 (Emotional/Cognitive Load) |
| Section 3 header said "Five" traps but enumerated Trap 1-6 | Title-reality mismatch | Renamed to "Ten Expectation Traps" with Trap 7-10 added (Accessibility, Performance, Design Fidelity, First-Use Experience) |
| Section 4.1 gate claimed "7-point" but listed 9 checks | Number mismatch | Renamed to "9-point Pre-Ship Gate", numbered checks explicitly |
| Lessons Learned 2026-05-25 Self-heal row had broken pipe formatting | Formatting defect | Repaired table structure |

### 2026-05-25 — Dashboard v0 AI-Human Gap

| What AI said | What human found | Trap | Fix |
|---|---|---|---|
| "All endpoints return 200" | Alerts panel shows "Internal Server Error" — Pro tiles crashed | Trap 4 — loading experience | Fixed `_pro_locked_tiles()` KeyError (server.py line 175) |
| "15 agent cards render correctly" | All 15 cards look identical — empty badges, bars, sparklines | Trap 1 — visual completeness | Add skeleton placeholders + empty-state guidance |
| "toggleAgentDetail() works" | First click produces no visible feedback; user clicks again confused | Trap 2 — feedback registered | Add transition animation + pointer cursor on all cards |
| "Empty badges/bars/sparklines = correct (no data)" | Dashboard feels useless — nothing is happening | Trap 5 — empty state unhelpful | Add per-section explanatory text + collapse low-value empty sections |
| "Text renders at spec sizes (11px)" | 11px on dark background is unreadable without squinting | Trap 3 — layout readability | Bump to 13px min for body text; change locked-tile visual from grayscale to blur overlay |

| What AI said | What human found | Trap | Fix |
|---|---|---|---|
| "Self-heal button navigates to /self-heal correctly" | Redirects to new page — user loses dashboard context and must navigate back | Trap 6 — context preservation | Replace redirect with slide-in drawer overlay; user stays on dashboard |
| "Pragma is in topic 2072 of Alpha Management, bot can send there" | Bot was never added to topic 2072 — can send but cannot receive messages | Telegram platform limitation | Group admin must add bot to topic 2072 as member (see infra note) |
| "Agent detail tabs load on first click" | Clicking Health→Tokens→Memory then back to Health shows permanent "Loading health data..." — tab cache prevents re-fetch | Trap 2 — feedback registered | Fix: remove cached tab entries when switching tabs within same agent; detect stale "Loading..." state and re-fetch |
| "Tokens tab shows no data for Hermes agents" | Accelerator (a Hermes agent) shows nothing under 📊 Tokens — likely no trim data in DB | Trap 1 — visual completeness | Show helpful empty state: "No trim data yet — run `observeco chisel trim` to see token savings" |
| "Memory tab shows misleading message for Hermes agents" | "Memory garden is available for OpenClaw agents" — user is looking at a Hermes agent, not OpenClaw | Trap 5 — empty state unhelpful | Changed to: "This Hermes agent uses CHISEL for context optimization — check the Tokens tab" with explanatory tip |

### 2026-05-29 — ObserveCo Dashboard v0.2 UX Break-Test

| What AI said | What human found | Layer | Fix |
|---|---|---|---|
| "Dashboard loads fine on port 9119" | Port 9119 = Hermes React dashboard. ObserveCo on port 9120 due to port collision. | Confidence | Added dual-dashboard port detection to Step 0 Pre-Flight |
| "All endpoints return 200 via TestClient" | Browser renders `<body></body>` — htmx never loads. `document.write()` CDN fallback nukes the entire DOM after page load completes. | Perception | Replaced `document.write()` with DOM-based script injection. See references/session-20260529-breaktest-findings.md |
| "Font sizes at spec" | 54 font-size:10px and font-size:11px in server.py inline HTML generation — invisible to browser-only audit | Perception | Added API-level font scan via TestClient + regex to Step 0B |
| "Cards show data correctly" | 8/15 cards show 4 empty rows each ("No tokens / No drift / Learning... / No token data") = 32 rows of zero information | Perception | Added server-side empty-data row consolidation: single "Monitoring" row when both drift and token data are empty |
| "11 Pro mentions vs 0 Free/OSS" | MIT-licensed product reads as paid-only | Confidence | Added MIT License badge in header, Free & Open Source footer with GitHub star link |
| "f-string compiles fine" | `{brain_composition_html}` undefined at runtime raises NameError 500 — py_compile doesn't catch this | Friction | Added Pitfall #8: runtime f-string verification |
| "Font-size batch replace worked" | Batch replace script corrupted ❓ emoji inside an f-string — cause SyntaxError on next compile | Friction | Added Pitfall #9: multi-byte Unicode corruption from regex batch edits |
| "10 trap catalogue covers all known patterns" | Brand positioning statement missing — logo alone doesn't explain purpose | Trap 5 — Empty State | Added tagline: "Tells you if your AI agents are working, what they're doing, and where your money goes." |
| "Clickable elements have visual feedback" | Agent card toggle checkbox at top-right corner: clicking does nothing — no event handler | Trap 2 — Mechanism ≠ Feedback | Verified: `toggleHide()` appends to JS Set but never passes to backend. Needs query param filter. |
| "Status text is accurate" | "5d ago" timestamp + "● Running" status dot side-by-side: user cannot tell if agent is running NOW or ran 5 days ago | Trap 3 — Data ≠ Readable / Layer 2 Confidence | Timestamp shows last pulse. Status shows circuit state. These can diverge when pulses are stale. Needs staleness indicator or explicit label. |
| "Metric rows show real data" | All 5 rows pass static placeholder strings ("Health data loading...", "Guard data...", "Error data...", "Drift data...", "Composition data...") | Trap 1 — Structural Correctness ≠ Visual Completeness / Friction | Wire `openModal()` to `/api/agent-detail/{name}?tab=` with tabbed Health/Tokens/Memory panels. Backend already returns real data — frontend never called it. |
| "Services section accurate" | Only 1 card in Services. User expects more. No way to add a Service-type agent from the UI. | Trap 5 — Empty State | Add "Service" option to Add Agent dropdown alongside Hermes/OpenClaw/Custom. |
| "Detail modal has Tokens and Garden tabs" | No tab bar exists — clicking any metric row opens a plain modal with no tabs at all | Trap 6 — Navigation ≠ Context | Replaced plain `openModal()` with tabbed interface calling live `/api/agent-detail/` endpoint with Health/Tokens/Memory tabs. |

| 2026-05-29 | ObserveCo Dashboard v0.2 | Various (see full table above) | Multiple | All | Added 10 pitfall patterns, empty-data consolidation, f-string leak detection |

### 2026-05-30 — Framework Overfitting Audit (External Perspective Trap)

**Trigger:** Sean flagged that Kepler detection "fights between Hermes and OpenClaw" — the product was overfitting to our ecosystem by treating framework as primary identity.

**Root cause:** Agent detection separated into `_load_hermes_agents()` and `_load_openclaw_agents()`, but the dashboard then hardcoded framework labels to only "Hermes" or "OpenClaw". Default framework was "hermes". A CrewAI user would see their agent falsely labeled "OpenClaw" with no way to tell the label is wrong.

**Detection technique:** Ran TestClient-based automated audit across ALL API endpoints, searching for hardcoded framework strings in responses. Combined with grep over source files for pattern matches.

**Fix checklist codified in master plan:**
1. Framework label must render ANY value, not just known ones — never `"Hermes" or "OpenClaw"` ternary
2. Default framework must be empty string, not "hermes"
3. Agent card shows type first, framework second: `Agent · Hermes` not `Hermes · Agent`
4. User-facing text must not use internal brand names (CHISEL, ClawForge, Claw)
5. Add Agent dropdown: type options first (Agent/Service/Workflow), framework as optional metadata
6. CLI commands show generic names as primary, internal names as aliases

**Files patched (15 files):** server.py (7 locations), templates/index.html (2 locations), website/index.html (2 locations), auto_detect.py, README.md, observeco-master-plan.md (spec), ux-testing-playbook.md (this entry).

### Template for future entries

```
| Date | Product | What AI said | What human found | Trap/Layer | Fix |
|------|---------|-------------|------------------|-----------|-----|
| YYYY-MM-DD | {product} | {AI claim} | {human finding} | {Trap N or Layer X} | {what was done} |
```

### 2026-05-31 — Standardization Pass

| What was wrong | Category | Fix applied |
|----------------|----------|-------------|
| "Pre-Ship Gate" naming inconsistent with other playbooks' "Golden Gate" | Naming inconsistency | Renamed §4.1 heading from "Pre-Ship Gate" to "The Golden Gate" — matches coding-fidelity, system-design, and master-gate conventions. |
| No Version History table — inline version string only | Missing metadata | Added Version History table with 2.0 → 2.1 entries. |
| No cross-reference to Playbook Inventory | Cross-reference gap | Added reference to requirements-fidelity-playbook.md §Playbook Inventory (canonical system document count and roles). |

### 2026-06-01 — Spatial Density Blindspot (The "AI Blindspot")

| What was wrong | Category | Fix applied |
|----------------|----------|-------------|
| Playbook had no section for graph visualization spatial optimization | Missing UX dimension — AI verifies "nodes render" but doesn't think about whether a human can see all objects without zooming | Added §9.7 Spatial Density & Layout Optimization — the 3-Question Spatial Audit, fix patterns table, and the one-question smell test. |

### 2026-06-01 — ObserveCo Dashboard Post-Launch Review (6 Issues)

| Date | Product | What AI said | What human found | Trap/Layer | Fix |
|------|---------|-------------|------------------|-----------|-----|
| 2026-06-01 | ObserveCo | "Pulse dots render at 10px with 5px gap" | Emoji (🟢🔴🟡) overflow 10×10px boxes → dots overlap legend row below | Trap 14 — Representation Overflows Container | Replaced emoji with CSS `div` dots; added `flex-shrink: 0; line-height: 1`; legend uses same CSS class |
| 2026-06-01 | ObserveCo | "Yearly cost estimate calculated" | `if framework == "hermes":` never matches because upstream capitalizes to "Hermes" → falls to OpenClaw branch → `total_est = 0` → `$0.00` | Data-transformation pipeline bug | Changed to `"hermes" in framework.lower()` |
| 2026-06-01 | ObserveCo | "Memory tab shows daemon status" | Shows "never started" but no way to start it — user is stuck | Trap 5 — Empty State unactionable | Added start command + explanation to empty garden tab; updated Trap 5 detection to check for runnable command in actionable empty states |
| 2026-06-01 | ObserveCo | "Pathway map renders" | `initializeCy()` calls `applyFilter(currentFilter)` — renamed to `applyFilters()` → `ReferenceError: applyFilter is not defined` on every page load | Trap 16 — JS Rename Leaves Dead Call | Fixed call site; added Trap 16 to playbook |
| 2026-06-01 | ObserveCo | "Watch daemon start command shown" | Help text says `observeco watch --daemon` but CLI uses subcommands: `observeco watch start` | Trap 15 — Inline Reference Not Verified | Fixed help text; added Trap 15 to playbook |
| 2026-06-01 | ObserveCo | "Pro modal has padding" | `.modal { overflow: hidden }` with no internal padding → content flush to edges | Trap 9 — Visual Consistency | Added `.modal-body { padding: 18px; overflow-y: auto }`; added flush-content check to Trap 9 detection |

### 2026-06-08 — Pro License Key Modal UX Bugs

| Date | Product | What AI said | What human found | Trap/Layer | Fix |
|------|---------|-------------|------------------|-----------|-----|
| 2026-06-08 | ObserveCo | "License key modal opens, input accepts text" | Dragging to select the entire license key string causes mouseup on overlay background → modal dismisses mid-copy | Trap 18 — Overlay Dismiss on Text Selection | Added `event.stopPropagation()` to inner content div. Added Trap 18 to playbook + Golden Gate item 10. |
| 2026-06-08 | ObserveCo | "CRM issues license keys correctly" | CRM admin endpoint generates `OBS-ADMIN-XXXXXXXX` and Stripe webhook generates `OBS-XXXXXXXX-XXXX` — neither matches the `OBS-PRO-XXXXXXXX-XXXX` validator regex. All 7 active keys in Supabase unusable. | Data Integrity — CRM output ≠ client validator | Fixed both generation paths to `OBS-PRO-XXXXXXXX-XXXXXX`. Reissued all 7 active keys in Supabase. |
| 2026-06-08 | ObserveCo | "Start Free Trial button works" | Hardcoded single-use Stripe Checkout session URL (`cs_live_a1xg...`). After session consumed, button returns Stripe 404. Three copies in codebase. | Trap 21 — Hardcoded Ephemeral Value | Replaced all 3 copies with `/api/checkout?plan=solo&trial=30` dynamic endpoint. Added Trap 21 to playbook. |
| 2026-06-08 | ObserveCo | "Health popup shows correct data" | Confidence header renders before Last 24 Hours section — information hierarchy reversed. All data correct, order wrong. | Trap 23 — Render Order Drift | Moved `{conf_header}` into Signal Analysis section in `js_string` concatenation. Added Trap 23 to playbook. |
| 2026-06-08 | ObserveCo | "All metric rows render correctly" | Services/workflows show `📈 Learning...` for token drift and `⚪ No data` for Guard — metrics that don't apply to those entity types. | Trap 24 — Entity-Type-Aware Rendering | Gated Confidence, Guard, Brain size, Composition rows behind `agent_type == 'agent'`. Added Trap 24 to playbook + Golden Gate item 11. |
| 2026-06-09 | ObserveCo | "Brain analysis, fleet drift, composition all show data" | `chisel_trims` table missing `mode` column. `log_trim()` INSERTs `mode` but DDL at schema v11 never had it. Migration script existed but never wired into auto-run. 1,265 errors accumulated, trim/drift tables empty for days. | Trap 22 — Schema-Code Drift | Bumped schema to v12, wired migration into `db.py:MIGRATIONS`. Schema auto-upgraded on next Database() init. Added Trap 22 to playbook. |
| 2026-06-09 | ObserveCo | "Brain Analysis shows 58% savings, 116 turns, 3 of 8 skills" | All hardcoded upsell data — no real compress_log entries existed | Trap 25 — Misleading Data | Replaced with `—` placeholders, added `savings_source` field with 3 states |
| 2026-06-09 | ObserveCo | "Solo trial user sees correct billing UI" | "Subscribe $9/mo" visible alongside "Cancel Trial" — confusing state | Trap 26 — Subscription Confusion | Hidden "Subscribe" for active trial users; shown "Manage Subscription" |
| 2026-06-09 | ObserveCo | "Stripe payment flow completes" | Payment successful, Pro not activated — 3 independent bugs | Trap 27 — Pro Activation Gap | Fixed session ID, encryption key, missing start_trial(). E2E test added |
| 2026-06-09 | ObserveCo | "Master plan shows Push Alerts as ✅ Live" | Backend complete, dashboard UI never built | Trap 28 — Status Split | Features split into backend/dashboard status columns |
| 2026-06-09 | ObserveCo | "loadLicenseStatus() works on Settings tab" | Crashes silently on 4 other tabs — null element access | Trap 29 — Silent DOM Crash | Added null guard to all cross-tab JS functions |
| 2026-06-09 | ObserveCo | "License deactivation updates backend" | Badge shows old state until manual reload | Trap 30 — Badge Refresh | Added loadLicenseStatus() after every modal close |

### 2026-06-10 — Post-Skill-Audit Review (6 Bugs)

| Date | Product | What AI said | What human found | Trap/Layer | Fix |
|------|---------|-------------|------------------|-----------|-----|
| 2026-06-10 | ObserveCo | "Full Details button opens Token Optimiser modal" | Modal opens behind Skills Audit overlay — both modals have z-index:100. User sees no change. | Trap 31 — Modal Stacking | Added closeSkillsAudit() before openChiselModal() |
| 2026-06-10 | ObserveCo | "Modal content renders correctly" | Actions (Apply Compression + Full Details) at bottom of 50+ row skill table. User must scroll past all skills. | Trap 32 — Action Buried Below Scroll | Reordered: Summary → Compression Preview (with buttons) → Skills Table → Category |
| 2026-06-10 | ObserveCo | "Tab shows 'No restart data yet' with CLI hint" | Same empty state for Pro and Free users. Pro has a server-side scan button available but gets CLI hint instead. | Trap 33 — Pro-Empty-State Mismatch | Added Pro-aware empty state with clickable "Run Pulse Scan" button |
| 2026-06-10 | ObserveCo | "Restart Quality tab renders empty state" | No glossary entry explaining what restart types mean. No "?" hint on tab heading. | Missing glossary | Added restart-quality glossary entry (3 types, 5 FAQ) + "?" hint on tab heading |
| 2026-06-10 | ObserveCo | "Apply Compression button present" | Button exists but no server-side trigger to scan for data first. User must run CLI separately. | Pro empty state (Trap 33 variant) | Added POST /api/restart-quality/scan endpoint + triggerRestartScan() JS |
| 2026-06-10 | ObserveCo | "Memory Garden scan button planned" | POST endpoint built (api_garden_scan) but frontend button never completed. | Missing feature | *(carried over — tables empty, endpoint wired but button not built)* |

---

## 8. Projecting Forward

This playbook applies to any frontend product we build — not just ObserveCo. Before shipping any UI:
1. Load the playbook
2. Run the 8 prompts (or the subset relevant to the deliverable)
3. Check the Lessons Learned log for similar past gaps
4. If you find a new trap, log it before fixing

The goal is not to eliminate AI-human gaps. The goal is to make every new gap a one-time discovery that gets absorbed into the playbook, never repeated.

---

## 9. Scaling the Playbook

The current protocol is designed for one engineer running manual checks on one dashboard. When ObserveCo has 12 dashboards and a team of 8, this does not scale.

### 9.1 Quantitative Success Metrics

Add to every gate — pass/fail is not enough. Measure:

| Metric | Target | How to measure |
|--------|--------|----------------|
| Task completion time | <10s for "find agent with highest error count" | Timed user test or session replay |
| System Usability Scale (SUS) score | ≥85 (out of 100) | 10-question survey after first use |
| Error rate on first-click interactions | ≤5% | Click-tracking analytics or session replay |
| Time to First Meaningful Paint | <1.5s on mid-tier laptop | Lighthouse or Performance API |
| Cumulative Layout Shift (CLS) | <0.1 | Lighthouse or web-vitals library |
| First-input delay | <100ms | Performance Observer |
| Accessibility violations | 0 critical, 0 serious | axe-core or Lighthouse |

These are minimums. Set per-scope targets (higher for landing pages, lower for internal dashboards).

### 9.2 Cross-Device & Environment Matrix

The playbook assumes desktop Chrome. Must test all environments before any public launch:

| Environment | Priority | What to check |
|---|---|---|
| Desktop Chrome (latest) | 🔴 Always | Full gate |
| Desktop Firefox | 🔴 Always | Rendering, JS compatibility |
| Desktop Safari | 🔴 Always | Rendering, font rendering, WebKit quirks |
| Desktop Edge | 🟡 At release | Chromium-based, typically matches Chrome |
| Mobile portrait (iPhone 13/15) | 🔴 Always | Touch targets, layout breakpoints, font scaling |
| Mobile landscape | 🟡 At release | Layout shift, overflow |
| Tablet (iPad portrait) | 🟡 At release | Responsive breakpoints, readability |
| 4K/ultrawide monitor | 🟡 At release | Horizontal whitespace handling, max-width on cards |
| Dark mode forced | 🔴 Always | Colour contrast, all text legible |
| High-DPI / Retina | 🟡 At release | Icon crispness, image resolution |
| Offline mode | 🟡 At release | Offline cached state, "you're offline" messaging |
| Slow 3G throttled | 🔴 Always | Loading sequence, skeleton quality |
| Incognito / private browsing | 🟡 At release | localStorage fallbacks, no auth assumptions |

**Test every OS-level accessibility setting:** Reduce Transparency, Increase Contrast, Bold Text, Button Shapes, On/Off Labels, Differentiate Without Colour.

### 9.3 Visual Regression Testing in CI

Functional Playwright tests catch logic bugs. They do not catch "this card padding changed by 2px."

**Recommended toolchain:**
- **Pixel-diff tools:** Argos, Percy, or Chromatic — flag visual drift in CI before Sean ever sees it
- **Integration:** Add a `visual-regression.yml` GitHub Action that runs on every PR
- **Baseline:** Store approved screenshots per component. Any pixel diff >0.5% flags the PR
- **Threshold:** 0.5% tolerance for anti-aliasing noise; anything larger requires human review
- **Exclusions:** Animated regions, live data (replace with mock data for screenshots)

### 9.4 Real-User Session Replay & Heatmaps

The playbook relies on Sean's feedback. Real users behave differently.

**Post-launch protocol (Week 1 after any public release):**
1. Enable session recording (PostHog, Hotjar, or OpenReplay) for anonymous users
2. Review the first 50 recorded sessions:
   - Where do users click that isn't a link?
   - Where do they hover but not click? (hesitation = poor affordance)
   - Where do they scroll back and forth? (confusion = poor layout)
   - Where do they abandon the page? (friction = poor value signal)
3. Generate a click-heatmap and scroll-depth map
4. Log findings as Lessons Learned entries
5. If abandonment rate >40% on any core action, treat as a P0 bug

**Session review checklist:**
- [ ] No rage clicks (rapid repeated clicking on non-interactive elements)
- [ ] No dead clicks (clicking on something that looks interactive but isn't)
- [ ] No scrolling back and forth on a single section (user trying to find something)
- [ ] First-click accuracy >80% for primary actions
- [ ] Scroll depth >80% for the landing/dashboard page

### 9.5 AI Hallucination Trap in Testing Prompts

When agents run the prompts above, they may describe imaginary screenshots. The agent says "I took a screenshot showing..." without actually capturing one.

**Prevention:** Every prompt that includes a screenshot command must also say:

> "After any screenshot command, you must output the exact image ID or base64 thumbnail so I can verify you actually captured it."

This is now appended to Prompt 7 and Prompt 8 above.

## 9.6 Upgrade Path

| Scale level | What to add | When |
|---|---|---|
| 1 dashboard, 1 engineer | Manual 9-point gate + playbook prompts | Now |
| 3+ dashboards | Quantitative metrics per gate | Next quarter |
| 5+ dashboards | Visual regression CI (Percy/Chromatic) | Before team hires |
| 8+ dashboards, team of 4+ | Real-user session replay, cross-device lab | After first public release |
| 12+ dashboards, team of 8+ | Dedicated QA script suite + automated accessibility regression | Before enterprise launch |

### 9.7 Spatial Density & Layout Optimization (Graph Visualizations — The "AI Blindspot")

**Problem:** AI verifies "86 nodes, 277 edges render" — but the human needs to see ALL of them without zooming, scrolling, or squinting. Graph layout engines (Cytoscape.js, D3 force, vis-network) compute positions algorithmically and are blind to human-viewing constraints. They produce layouts that are:
- **Too sparse** — 80% empty canvas, nodes the size of pinpricks, human must zoom in to read anything
- **Too dense** — nodes overlap, edges tangle, labels collide, human must zoom in to find anything
- **Uneven** — one corner has 60 nodes, rest of canvas is empty

This is the exact class of problem Sean flagged: *"AI doesn't necessarily think about this."*

**Detection — The 3-Question Spatial Audit:**

Before marking any graph/network visualization done, run these checks:

```
1. SPATIAL UTILIZATION: What % of the viewport contains visible nodes/edges?
   - Screenshot the full graph at default zoom (no scroll)
   - Crop to the bounding box of all visible nodes
   - Measure: does the node bounding box fill <40% of the viewport?
   - PASS: >60% of viewport has graph content. FAIL: >40% is empty canvas.

2. OVERLAP CHECK: Do any nodes visually overlap or touch?
   - In dense areas, pick any 3 adjacent nodes
   - Can you see the boundary between each pair, or do they blend into a blob?
   - PASS: Every node boundary is distinguishable from its neighbours.
   - FAIL: Two or more nodes overlap, or edges pass under node labels.

3. LABEL READABILITY: Can every visible label be read at default zoom without squinting?
   - Pick the 3 smallest labels in the densest region
   - Read them aloud. Can you?
   - PASS: All labels readable at normal viewing distance.
   - FAIL: Any label needs squinting, zooming, or tilting the screen.
```

**If ANY check fails, the layout must be re-optimized BEFORE the graph is shipped.**

**Fix patterns (in order of preference):**

| Problem | Fix | When to use |
|---------|-----|-------------|
| Too sparse — nodes tiny, lots of empty space | Increase `nodeSpacing` multiplier. Or switch layout algorithm. Force-directed layouts (Cytoscape `cose`, `cola`, D3 force) compact naturally; grid/circle layouts leave gaps. | Always try this first |
| Too dense — nodes overlapping | Increase `padding` or `nodeDimensionsIncludeLabels`. Or use `cola` (constrained layout) which prevents overlap by design. | Dense cluster regions |
| Uneven distribution | Apply `spacingFactor` > 1.0 and run layout with `animate: false` and `fit: true` to scale into viewport. | Post-layout adjustment |
| Labels unreadable | Increase minimum label font size. Or show labels on hover only, with node colour alone identifying type at rest. | Last resort — labels hidden = worse UX |
| Layout looks wrong at a glance | Try a different layout algorithm. `cose-bilkent` (Cytoscape) or `d3-force` often produce better spatial utilization than default `cose` or `breadthfirst`. | When the current algorithm was chosen by default, not by testing |

**The one-question smell test for graph layouts:**

*"Can I understand the shape of the network at a glance without moving my eyes more than 30 degrees from center?"*

If the answer is no: zoom-to-fit is hiding a layout problem. If you need to zoom to see the graph, the graph is not optimized for human viewing — it's optimized for the algorithm.

**Extended — Multi-Viewport Rule (for complex graphs):**

If the graph genuinely cannot fit in one viewport without unacceptable density (true for >200 visible nodes with labels), the right answer is NOT "make the user zoom." The right answers (in order):

1. **Collapse modules** — group related nodes into clusters at a reasonable zoom level, show internal structure on click. Cytoscape supports this natively via compound nodes or `cy.expandCollapse`.
2. **Filter by subsystem** — default view shows only top-level clusters. User drills into a subsystem to see its internal edges.
3. **Zoom-dependent label density** — at default zoom, show labels only on hub nodes (degree ≥ 5). On zoom-in, reveal all labels.
4. **Last resort: zoom-to-fit with clear zoom affordance** — if the graph MUST be large, the initial view should show the user *that there's more to see* (cluster previews, not a scattered cloud of dots).

**Never:** Ship a graph where the user's first reaction is "I need to zoom in to see what this is."

**Reference:** `coding-fidelity-playbook.md` §2.2 (Implementation Fidelity — the 4-Question Audit applies to graph layouts too: Exists? renders. Correct? nodes at correct positions. Complete? all nodes visible at default zoom. Matches mockup? spatial density matches what the mockup suggested.)
