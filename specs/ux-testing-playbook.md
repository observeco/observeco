# UX Testing Playbook — The Human Lens

**Product:** ObserveCo (and all future frontend projects)
**Status:** Living — update as lessons accumulate
**Version:** 3.2 — 2026-06-01
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 2.0 | 2026-05-30 | Added Version field, Golden Gate, fixes section numbering |
| 3.1 | 2026-05-31 | Standardization pass: all 7 playbooks bumped to v3.1. Fixed stale playbook-count references. Confirmed cross-references to Playbook Inventory (requirements-fidelity-playbook.md §Playbook Inventory) and Layer F First-Run Audit (master-fidelity-gate.md §2 Layer F). Removed stray empty FILE tags. |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory, rename "Pre-Ship Gate" → "Golden Gate" |
| 3.2 | 2026-06-01 | Added Trap 14 (Representation Overflows Container), Trap 15 (Inline Reference Not Verified), Trap 16 (JS Rename Leaves Dead Call). Updated Trap 5 detection (actionable empty state commands), Trap 9 detection (flush-content check). Added Lessons Learned entry for 6 post-launch issues. |

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

## 3. The Ten Expectation Traps (Pattern Catalogue)

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
Before marking any frontend work done, run this 9-point gate:

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

For every check, also pass through the Accessibility lens (Layer 4):
  - Can all 9 points be completed with keyboard-only navigation?
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
