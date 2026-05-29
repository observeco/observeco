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

**Triage:**
| State | Good | Bad |
|-------|------|-----|
| No errors | "✅ No errors in the last 24 hours" | Empty space where an error list would be |
| No token data | "📊 Token data appears after the agent's next session" | Blank area below the agent card |
| No drift data | "📈 Establishing baseline — 3+ pulses needed" | Missing sparkline |
| No alerts | No alert panel needed at all (collapse it) | Empty right rail with "Pro Features" greyed out |

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

### 4.1 Pre-Ship Gate (run by Hound or any agent)

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

## 6. Lessons Learned Log

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
| "git checkout reverted the broken line" | Also reverted font-size bumps, MIT badge, htmx fix — all uncommitted | Friction | Added Pitfall #10: atomic fix scripts survive git revert |

### Template for future entries

```
| Date | Product | What AI said | What human found | Trap/Layer | Fix |
|------|---------|-------------|------------------|-----------|-----|
| YYYY-MM-DD | {product} | {AI claim} | {human finding} | {Trap N or Layer X} | {what was done} |
```

---

## 7. Projecting Forward

This playbook applies to any frontend product we build — not just ObserveCo. Before shipping any UI:
1. Load the playbook
2. Run the 8 prompts (or the subset relevant to the deliverable)
3. Check the Lessons Learned log for similar past gaps
4. If you find a new trap, log it before fixing

The goal is not to eliminate AI-human gaps. The goal is to make every new gap a one-time discovery that gets absorbed into the playbook, never repeated.

---

## 8. Scaling the Playbook

The current protocol is designed for one engineer running manual checks on one dashboard. When ObserveCo has 12 dashboards and a team of 8, this does not scale.

### 8.1 Quantitative Success Metrics

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

### 8.2 Cross-Device & Environment Matrix

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

### 8.3 Visual Regression Testing in CI

Functional Playwright tests catch logic bugs. They do not catch "this card padding changed by 2px."

**Recommended toolchain:**
- **Pixel-diff tools:** Argos, Percy, or Chromatic — flag visual drift in CI before Sean ever sees it
- **Integration:** Add a `visual-regression.yml` GitHub Action that runs on every PR
- **Baseline:** Store approved screenshots per component. Any pixel diff >0.5% flags the PR
- **Threshold:** 0.5% tolerance for anti-aliasing noise; anything larger requires human review
- **Exclusions:** Animated regions, live data (replace with mock data for screenshots)

### 8.4 Real-User Session Replay & Heatmaps

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

### 8.5 AI Hallucination Trap in Testing Prompts

When agents run the prompts above, they may describe imaginary screenshots. The agent says "I took a screenshot showing..." without actually capturing one.

**Prevention:** Every prompt that includes a screenshot command must also say:

> "After any screenshot command, you must output the exact image ID or base64 thumbnail so I can verify you actually captured it."

This is now appended to Prompt 7 and Prompt 8 above.

### 8.6 Upgrade Path

| Scale level | What to add | When |
|---|---|---|
| 1 dashboard, 1 engineer | Manual 9-point gate + playbook prompts | Now |
| 3+ dashboards | Quantitative metrics per gate | Next quarter |
| 5+ dashboards | Visual regression CI (Percy/Chromatic) | Before team hires |
| 8+ dashboards, team of 4+ | Real-user session replay, cross-device lab | After first public release |
| 12+ dashboards, team of 8+ | Dedicated QA script suite + automated accessibility regression | Before enterprise launch |
