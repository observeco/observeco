# UI Testing Playbook — The Visual Gate

**Product:** ObserveCo (and all future frontend projects)
**Status:** Living — update as lessons accumulate
**Version:** 2.0 — 2026-06-09

**Review Cadence:** After any sprint that touches UI — monthly minimum.
**Lessons Archival:** Entries older than 90 days with no recurrence moved to `lessons-archive.md`.

**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-06-09 | Initial creation — 8 UI dimensions, Trap catalogue, Visual Regression protocol, Design Token Audit, Golden Gate checklist |
| 2.0 | 2026-06-09 | **Major revision per Sean review.** Added Dimension 9 (Accessibility Consistency). Golden Gate moved to §3 with [BLOCKER]/[WARN] tags. Split Dimension 6 into Hard + Configurable layers. Frame budget (60fps = 16.67ms) replaces subjective "feels sluggish" in D8. Token table replaced with `tokens.css` reference. Added §8 CI/CD Integration (Playwright, ESLint, pre-commit, Percy). Fixed hex colour detector to exclude CSS variable definitions (`--var:`). Audit scripts now have `--help` + exit codes. Added WCAG 2.5.8 note for ✕ hit targets. Sharpened Trap 5 vs Dimension 2 distinction. Inter font-weight range specified. Review cadence and lessons archival rules added. Master-fidelity-gate cross-reference made concrete. |

**Author:** Main (per Sean direction 2026-06-09)
**Source:** Real dashboard — 11 modals with 3 different visual languages, inconsistent border-radii, missing X buttons, mixed design patterns across popups

---

## Playbook Inventory Reference

This playbook joins the 7 existing playbooks (see requirements-fidelity-playbook.md §Playbook Inventory). It sits downstream of the coding-fidelity playbook (code exists) and upstream of the ux-testing playbook (human evaluates it). It fills the gap between "the code works" and "the human likes it."

```
Requirements Spec  →  Code  →  UI CONSISTENCY  →  UX Feeling  →  Production
                      ↑            ↑                    ↑
                coding-fidelity  UI-TESTING         ux-testing
                playbook         PLAYBOOK           playbook
```

---

## 1. Thesis

**A consistent design system is not a luxury — it's a trust signal.**

Every visual inconsistency — mismatched border-radius, different button styles, a modal without an X, a header that uses `<span>` instead of `<h3>` — is a micro-signal to the user that says "this product is unfinished." One user action ("click outside to close") works on some modals but not others. One header uses `font-size:14px;font-weight:600` and another uses `font-size:18px;color:#f8fafc`. The user won't articulate the difference. They'll just feel "off" and trust the product less.

This document does not replace the UX playbook (which tests human perception). It tests **visual system integrity** — the cold, automatable, pixel-level consistency that must hold before human testing begins.

---

## 2. The Nine UI Dimensions (D1–D9, with D6 split into Hard + Configurable)

All UI consistency failures fall into one of nine dimensions:

### Dimension 1: Structural Pattern Consistency

Every instance of the same UI pattern (modal, card, button, badge, tab) must share the same HTML structure, CSS class hierarchy, and behavior.

| What drifts | Example from production |
|---|---|
| Modal header | 3 modals used `modal-header > h3 + .sub + ✕`. 2 used absolute-positioned ✕ with no header. 1 used `<span>` instead of `<h3>`. 1 was JS-generated with entirely different markup. |
| Modal close | 6 modals closed via ✕ button. 2 closed via backdrop click. 3 had no ✕ at all. |
| Button styling | Some modals used `class="modal-close"`, others used inline `background:transparent;border:1px solid #475569;border-radius:8px`. |
| Overlay | Some used `class="modal-overlay"`, the license key modal used `style.cssText = 'position:fixed;...'` with different z-index and opacity. |

**Hard rule:** Every instance of a pattern must use the exact same class-based HTML structure. Inline style overrides are allowed only for width/height/max-width variations. No pattern-creeping — if you need a different structure, it must be approved as a new pattern with its own class.

**Detection:** Run a structural diff across all instances of each pattern. Any structural divergence (different class names, different nesting, different close mechanisms) is a violation.

**Contract test:** The DOM query asserts *"we have N modals"* and the spec says *"these are their IDs."* If N changes without a spec update, the test fails.

### Dimension 2: Design Token Compliance

Every colour, spacing, border-radius, font-size, and shadow must come from the approved token set — not from ad-hoc hex values chosen at implementation time.

**Canonical source:** `tokens.css` (CSS custom properties in the project's stylesheet). **This playbook does not duplicate tokens** — all audits derive from parsing the `var(--*)` references at runtime.

**Known token prefixes:**
| Prefix | Purpose | Example value |
|--------|---------|---------------|
| `--bg` | Background (deepest layer) | `#0f172a` |
| `--surface` | Surface/card background | `#1e293b` |
| `--border` | Border colour | `#334155` |
| `--fg` | Primary foreground text | `#e2e8f0` |
| `--fg-2` | Secondary foreground | `#94a3b8` |
| `--muted` | Muted/disabled text | `#64748b` |
| `--accent` | Accent (green pulse) | `#22c55e` |
| `--accent-on` | Accent background | rgba form variant |
| `--warn` | Warning colour | amber/orange |
| `--danger` | Error/danger colour | red |
| `--meta` | Primary CTA/accent UI | `#6366f1` (indigo) |
| `--font-mono` | Monospace font stack | `ui-monospace, ...` |
| `--radius-lg` | Large border-radius | `12px` |

The reference file (`tokens.css` or the `<style>` block in `index.html`) is the **single source of truth**. These values change; the playbook does not.

**Detection:**
1. Parse `tokens.css` / CSS variable definitions — extract all `--*` tokens
2. Grep the template for any inline hex colour that matches a known token value
3. Every ad-hoc value must be either (a) converted to the nearest token equivalent or (b) explicitly approved as a new token in `tokens.css`

### Dimension 3: Component State Coverage

Every interactive component must define and render distinct visual states for: default, hover, active, disabled/loading, and (where applicable) selected, error, and empty.

| Component | States required | Common failure |
|-----------|----------------|----------------|
| Button | default, hover, active, disabled, loading spinner | Disabled buttons use reduced opacity but no cursor change |
| Card | default, hover, selected, expanded | Cards open with no loading indicator |
| Input | default, focus, filled, error, disabled | Error state only changes border colour (violates WCAG) |
| Close/✕ button | default, hover | ✕ buttons use different hover behaviours across modals |
| Tab | default, active, hover, disabled | Active tab has no visual distinction beyond colour |

**Detection:** For every component type, enumerate its possible states and verify each one renders a visibly distinct style. Hover each element and confirm `cursor: pointer` on all clickables.

### Dimension 4: Layout & Spacing Integrity

Every component and section must respect the spacing scale. Similar components must share consistent margins/padding. Content must never touch container edges.

| Rule | Enforcement |
|------|-------------|
| Modal body padding | `18px` (`.modal-body` class) |
| Modal header padding | `14px 18px` (`.modal-header` class) |
| Card internal padding | Minimum `12px` — content must not be flush against card border |
| Section vertical spacing | Consistent gap between sections (≥16px) |
| Text-to-container margin | No text or button should touch a container edge — minimum 12px internal padding |

**Detection:** Measure spacing on every component. Any content flush against a border edge is a violation.

### Dimension 5: Typography Consistency

Every heading, body, label, and caption must use consistent font sizes, weights, and colours from the token set. Similar semantic levels must use the same typography.

**Font:** `Inter` (weights 400, 500, 600, 700 loaded via `@font-face`). System stack fallback: `system-ui, -apple-system, sans-serif`. If Inter is loaded but weights 400/500/600/700 are not all declared, the renderer synthesises faux-bold — this is a violation.

| Level | Style | Source |
|-------|-------|--------|
| Major heading (h1) | `font-size:20px;font-weight:600` | Page titles |
| Section heading (h3) | `font-size:14px;font-weight:600;color:var(--fg)` | `.modal-header h3` |
| Body text | `font-size:13px;color:var(--fg-2)` | Standard body |
| Sub/description | `font-size:11px;color:var(--muted)` | `.sub` class |
| Small/meta | `font-size:10-12px;color:#64748b` | Helper text, hints |

**Detection:** Audit all text elements. Any heading that uses a different size/weight/colour than the token for its level is a violation. Any `<span>` used where `<h3>` is the token structure is a violation. Verify all 4 Inter weights are referenced in `@font-face` declarations.

### Dimension 6 (Hard): Behavioural Fundamentals (Non-Negotiable)

These are accessibility and platform conventions — not design preferences. Every modal, drawer, and overlay MUST conform.

| Rule | Rationale | WCAG ref |
|------|-----------|----------|
| **Escape key closes** | All interactive overlays must dismiss on Escape. No user should need a mouse to close a modal. | WCAG 2.1.2 |
| **Focus trap** | Tab focus must cycle within the open modal, not escape to the page behind. | WCAG 2.4.3 |
| **Body scroll lock** | Background page scroll must be disabled while a modal is open. | WCAG 1.4.13 |
| **Focus returns on close** | When modal closes, focus returns to the element that triggered it. | WCAG 2.4.3 |
| **prefers-reduced-motion** | All animations must respect `@media (prefers-reduced-motion)` — set `transition-duration: 0.01ms` when reduced motion is preferred. | WCAG 2.3.3 |

**Detection:** Open every modal. Press Escape — does it close? Tab through — does focus cycle within the modal or escape to the background? Scroll while modal is open — does the background scroll? Close the modal — does the trigger element regain focus? Set `prefers-reduced-motion: reduce` in DevTools — do animations disable?

**Failure is a [BLOCKER]. Do not ship.**

### Dimension 6 (Configurable): Behavioural Preferences (Product Decision)

These are design choices that the product owner (Sean) defines. The playbook enforces **consistency** — every modal must use the same mechanism — but does not prescribe which mechanism.

| Rule | Current preference | Notes |
|------|-------------------|-------|
| Close method | ✕ button only | Backdrop-click-to-close is disabled across all modals |
| Animation style | Fade overlay + scale modal | 0.15s ease in, 0.1s ease out |
| Transition duration | 0.15s for toggles, 0.2s for section expand | All state changes must be animated |
| Scroll lock behaviour | Lock body, allow modal scroll | No jank when scrollbar disappears |
| Close button position | Top-right of modal header | Consistent across all modals |

**Detection:** Open every modal. Does the close mechanism match the preference? Does the animation feel consistent across all instances? Any modal with a different close pattern is a violation.

### Dimension 7: Responsive & Container Integrity

Every component must render correctly at all supported viewport widths and when placed in containers of varying sizes.

| Test | What to check |
|------|---------------|
| 1024px (desktop min) | No horizontal scrollbar, no overlapping elements, minimum 3-4 agent cards visible |
| 768px (tablet) | Cards stack to 2 columns, modals shrink to 85% width, no cut-off text |
| 480px (mobile) | Single-column layout, modals at 92% width with 12px edge padding, buttons full-width |
| Container overflow | Any element with `overflow:hidden` — content must not spill or be cut off |
| Text overflow | No text should overflow its container or be truncated without ellipsis |

**Detection:** Resize browser to each breakpoint. Take screenshots. Compare layout, spacing, and text integrity.

### Dimension 8: Animation & Transition Consistency

Every state change must have a consistent animation pattern. Similar transitions must share duration, easing, and behaviour.

| Element | Expected transition |
|---------|-------------------|
| Modal open | Fade overlay + scale modal: `0.15s ease` |
| Modal close | Reverse: `0.1s ease` |
| Card expand | Slide content: `0.15s ease` |
| Colour hover | `0.15s ease` on brightness/background |
| Tab switch | `0.1s ease` instant colour swap |
| Loading skeleton | Pulse animation: `1.5s ease-in-out infinite` |

**Frame budget:** 60fps = **16.67ms per frame**. A modal animation that triggers layout thrashing (forced reflow on every frame) is a violation — even if the duration is 0.15s.

**Detection:**
1. Enable `prefers-reduced-motion` — all animations should disable or run at `0.01ms`
2. Record the Performance panel in DevTools during each animation
3. Check for **forced reflows** (Layout triggers between style recalc and paint). Any layout thrashing = violation
4. Frame rate must be ≥55fps throughout the animation. If it drops below 55fps, the animation is too heavy
5. Time all transitions — any that feel sluggish (>0.3s) or instant (no transition) are violations

**Remedy:**
- Use `transform` and `opacity` for animations — they don't trigger layout
- Never animate `width`, `height`, `left`, `top`, `margin`, or `padding` — these force reflows
- Use `will-change: transform` sparingly and only on elements that actually animate
- Test animations on a mid-tier machine (not a MacBook Pro) before shipping

### Dimension 9: Accessibility Consistency (a11y)

Every interactive element must be accessible by keyboard, readable by screen reader, and perceivable by users with low vision, colour vision deficiency, or motor impairments.

| Criterion | Standard | Detection |
|-----------|----------|-----------|
| **Contrast ratio** | ≥4.5:1 for body text (WCAG AA), ≥3:1 for large text (18px+ bold) | DevTools contrast checker on every text/icon pair |
| **Keyboard reachability** | All interactive elements reachable via Tab, all actions performable without a mouse | Tab through entire page — no focus traps, no invisible focus |
| **Focus indicator** | Visible focus ring, minimum 3px `outline-offset`, never `outline: none` | Click each element and check focus ring is visible against any background |
| **ARIA labels** | Every interactive element has `aria-label`, `aria-expanded`, or `role` as appropriate | Audit every button, link, and card for ARIA attributes |
| **Touch targets** | ≥44×44px (WCAG 2.5.8) for all pointer targets | DevTools element inspector — measure clickable area |
| **Colour independence** | No information conveyed through colour alone — icons, text labels, or patterns required | Remove colour (desaturate) — is all information still visible? |
| **Screen reader** | Dynamic content changes announced via `aria-live` regions, modal open/close announced | Simulate VoiceOver/NVDA on every modal and dynamic section |
| **Zoom resilience** | Layout doesn't break at 200% zoom | Zoom browser to 200% — no overlapping, cut-off, or horizontal scroll |

**Note on ✕ button sizing:** The 24×24px close button falls below the WCAG 2.5.8 44×44px minimum for pointer targets. This is an accepted exception for conventional close buttons in desktop-first applications (Chrome, VS Code, macOS — all use 20-28px). For any future touch-targeted interface or mobile layout, increase to 44×44px.

**Failure of contrast, keyboard reachability, or focus indicator is a [BLOCKER]. Do not ship.**

---

## 3. The UI Consistency Gate (Golden Gate)

**This is the single most important artifact in the playbook.** Run it before any frontend change is marked complete.

Items tagged **[BLOCKER]** must ALL pass — any failure hard-blocks the release.
Items tagged **[WARN]** are advisories — must pass ≥80% with documented exceptions for the remainder.

```
## UI CONSISTENCY GATE — v2.0

### Structural Pattern Check
[ ] [BLOCKER] All modals share the same HTML structure: modal-overlay > modal > modal-header(h3 + ✕) > modal-body
[ ] [BLOCKER] JS-generated modals use className, not inline style.cssText
[ ] [WARN]    All instances of each component pattern use identical class hierarchy
[ ] [WARN]    No inline style overrides for colour, spacing, typography, or border-radius

### Design Token Compliance
[ ] [BLOCKER] No inline hex colour values — all colours reference CSS variables
[ ] [WARN]    Every visual property (spacing, radius, shadow) uses a CSS variable or approved token
[ ] [WARN]    Font sizes match: 14px (h3 headings), 13px (body), 11px (.sub/muted)

### State Coverage
[ ] [BLOCKER] Every ✕ button has hover state (background: var(--border))
[ ] [WARN]    Every button has: default, hover, active, disabled states
[ ] [WARN]    Every card has: default, hover, click feedback
[ ] [WARN]    Every input has: default, focus, error states

### Behavioural Fundamentals (Non-negotiable)
[ ] [BLOCKER] All modals support Escape key to close
[ ] [BLOCKER] Focus is trapped inside open modals (Tab cycles within)
[ ] [BLOCKER] Body scroll is locked while any modal is open
[ ] [BLOCKER] Focus returns to trigger element on modal close
[ ] [WARN]    All animations respect prefers-reduced-motion

### Behavioural Preferences (Product-consistent)
[ ] [WARN]    All modals close via ✕ button only (no backdrop-click-to-close)
[ ] [WARN]    No modal closes when user moves mouse outside
[ ] [WARN]    All modals use fade + scale animation (0.15s in, 0.1s out)

### Typography Audit
[ ] [BLOCKER] All major headings use <h3> (not <span>, <div>, or styled text)
[ ] [WARN]    Section descriptions use .sub class pattern (not inline styling)
[ ] [WARN]    No text below 11px on interactive elements
[ ] [WARN]    All 4 Inter weights (400/500/600/700) declared in @font-face

### Accessibility (a11y) — BLOCKER items are non-negotiable
[ ] [BLOCKER] Contrast ratio ≥4.5:1 for all body text
[ ] [BLOCKER] Every interactive element keyboard-reachable (Tab)
[ ] [BLOCKER] Visible focus indicator on every interactive element (never outline: none)
[ ] [WARN]    ARIA labels present on all interactive elements
[ ] [WARN]    No information conveyed through colour alone
[ ] [WARN]    Layout survives 200% zoom without breakage

### Responsive Check
[ ] [WARN]    Page renders without horizontal scroll at 1024px, 768px, 480px
[ ] [WARN]    Modals don't overflow viewport at any width
[ ] [WARN]    Text doesn't overflow containers at any width

### Animation & Performance
[ ] [WARN]    No forced reflows during modal/toggle animations (check Performance panel)
[ ] [WARN]    Animation frame rate ≥55fps (60fps target = 16.67ms/frame)
[ ] [WARN]    CSS transitions use transform/opacity (not width/height/top/left)

### Visual Regression
[ ] [WARN]    Screenshot taken of every new/modified page before and after change
[ ] [WARN]    Side-by-side comparison confirms only intended changes visible
[ ] [WARN]    No flash of unstyled content (FOUC) on hard reload

PASS/FAIL: ___/33 (≥29 of 33 — all [BLOCKER] = pass, <19 or any BLOCKER fail = DO NOT SHIP)
```

### When to Run

| Phase | Trigger | Minimum gates |
|-------|---------|--------------|
| **Build** | Each new component pattern created | Structural + Token + State + a11y keyboard (12 checks) |
| **Integration** | All sections wired to live data | Full 33-point gate |
| **Refactor** | Changing shared patterns (modals, cards, headers) | Full 33-point gate + visual regression |
| **Pre-launch** | Before any human testing | Full 33-point gate + responsive check across 3 viewports |
| **Regression** | Any backend-only change | Structural + Token + a11y keyboard (skip state/behavioural if no frontend change) |

### The Golden Rule

**If a visual inconsistency survived the coding review but was caught by a human in minutes, the UI testing protocol was missing a trap — not the human.**

Every time this happens, update this document with the new trap or dimension.

---

## 4. The UI Traps (Pattern Catalogue)

Each trap is a **recurring failure pattern** — a class of bug that will reappear if not caught systematically.

### Trap 1: Same Pattern, Different Markup

**Pattern:** Two instances of the same UI pattern (e.g., modals) use completely different HTML structures — one uses `modal-header > h3`, another uses `position:absolute` ✕ with inline styles, another is created entirely in JS with ad-hoc markup. All work. None match.

**Detection:** Run a structural diff across all instances of each pattern class (modal, card, button, etc.). Any structural divergence is a violation.

**Remedy:**
1. Define the canonical HTML structure for each pattern in DESIGN.md or a shared template
2. Every new instance must copy the canonical structure exactly
3. JS-generated modals must use the exact same class hierarchy — no inline `style.cssText` or ad-hoc markup
4. Use `class`-based styling, not inline styles, for all layout/visual properties

### Trap 2: Inline Style Drift

**Pattern:** A component starts with class-based styling. A one-off fix adds an inline style override. Another fix adds another inline override. After 3 iterations, the component has 5 inline styles that overlap and partially contradict the class styles. The component works but looks subtly wrong.

**Detection:** For every component, compare its inline styles to its class styles. Any property set in both places is a code smell. More than 3 inline styles on a single element is a violation.

**Remedy:**
1. Inline styles allowed only for: width/height/max-width numeric overrides, dynamic values from JS
2. All colour, spacing, typography, and layout properties must live in CSS classes
3. When adding a one-off visual tweak, first check if an existing class token covers it

### Trap 3: JS-Generated Markup Skips the Design System

**Pattern:** Modals created via `document.createElement('div')` or `innerHTML` often skip the class-based design system entirely, using inline styles with ad-hoc values. These modals look different from their HTML-declared counterparts even when they contain the same elements.

**Detection:** Find every JS-generated UI element (searched by `innerHTML`, `createElement`, `style.cssText`). Compare its markup to the canonical HTML pattern. Any divergence is a violation.

**Remedy:**
1. JS-generated modals must use `className` and class-based structure, not inline styles
2. The overlay div must use `className = 'modal-overlay active'` — not `style.cssText`
3. The inner container must use `className = 'modal'` with standard `modal-header` + ✕ + `modal-body` structure
4. Ad-hoc values for border-radius, background, padding, and font-size are banned in JS-generated HTML

### Trap 4: Same Function, Different Visual Result

**Pattern:** Two components call the same function (e.g., `showGlossary()`, `openModal()`) but produce different visual results because one passes data through a different template or applies different styling.

**Detection:** Open every call site of shared UI functions. Verify the output looks identical regardless of which trigger was used.

**Remedy:** All invocations of a shared UI function must produce identical visual output. Template parameters should control content, not structure.

### Trap 5: Future Token Drift (Time-Dimension Fault)

**Pattern:** The design system evolves. A new token is added (`--surface-alt`). Old code uses `#1e293b` directly. New code uses `var(--surface-alt)`. Both produce the same colour *today*. A theme update changes `--surface-alt` — old code stays `#1e293b` and drifts visually.

**Relationship to Dimension 2:** Dimension 2 checks *current* compliance — are you using tokens *now*? Trap 5 checks *future* compliance — will you stay compliant after a token change? Different failure mode, different detection method:
- D2: static audit (grep for hex values matching tokens)
- T5: diff-after-token-change (after any token update, re-run the D2 audit and check for NEW violations)

**Detection:**
1. Snapshot the D2 audit result (hex values → token mapping)
2. After any `tokens.css` change, re-run the D2 audit
3. Compare snapshots — any new hex-value-to-token mapping is a Trap 5 escape (a token changed and code wasn't updated)

**Remedy:** Every token change must include a re-run of the Design Token Compliance audit (§5.2). CI should enforce this — on any change to `tokens.css`, fire the hex colour leak detector.

### Trap 6: Component State Gap

**Pattern:** A component renders correctly in its default state but has no distinct visual state for hover, active, disabled, or loading. The user clicks and sees nothing happen, or clicks a disabled element and nothing responds.

**Detection:** For every component type, hover over it, click it, disable it if possible. Does each state produce a visibly distinct appearance? Does the cursor change appropriately?

**Remedy:** Every component must define all applicable states. At minimum: default, hover (cursor: pointer + background shift), disabled (opacity + cursor: not-allowed), loading (spinner or skeleton). Focus indicator must be visible on all keyboard-focusable elements.

### Trap 7: Responsive Breakpoint Gap

**Pattern:** A page looks perfect at 1440px. At 1024px, two sections overlap. At 768px, the header wraps awkwardly. At 480px, modals overflow the viewport with no scroll.

**Detection:** Resize the browser to each defined breakpoint. Take screenshots. Compare layout integrity.

**Remedy:** Every page must be tested at minimum widths of 1024px, 768px, and 480px. Modals must not exceed viewport dimensions at any size.

---

## 5. Automated Audit Scripts

All scripts follow exit code conventions:
- `exit 0` = no violations found
- `exit 1` = violations found

### 5.1 Structural Drift Detector

```python
#!/usr/bin/env python3
"""Audit all modals for structural consistency.
Usage: python3 audit_structural_drift.py <path/to/index.html>
Exit: 0 = pass, 1 = violations found
"""
import re, sys

html = open(sys.argv[1]).read()

# Find all modal-overlay divs — contract test finds every instance
modals = re.findall(
    r'(<div class="modal-overlay"[^>]*>.*?</div>\s*</div>\s*</div>)',
    html, re.DOTALL
)
print(f"Found {len(modals)} modal-overlay elements")

# Contract test: expected modal IDs (from spec)
expected_ids = {
    'llmWarningModal', 'brainProModal', 'pathwayModal', 'chiselModal',
    'openclawModal', 'skillsAuditModal', 'drillModal', 'thresholdsModal',
    'glossaryModal', 'licenseKeyModal', 'cancelTrialModal'
}
found_ids = set(re.findall(r'id="([^"]+Modal)"', html))
missing = expected_ids - found_ids
extra = found_ids - expected_ids
if missing:
    print(f"CONTRACT FAIL: Missing expected modal IDs: {missing}")
if extra:
    print(f"CONTRACT NOTE: Unexpected modal IDs found (may need spec update): {extra}")

exit_code = 0
for i, m in enumerate(modals):
    issues = []
    has_header = '<div class="modal-header">' in m
    has_h3 = '<h3' in m
    has_close_x = '✕' in m
    has_body = '<div class="modal-body"' in m
    has_inline_overlay = 'style.cssText' in m or 'style="position:fixed' in m
    has_click_outside = 'event.target===this' in m

    if not has_header: issues.append("[BLOCKER] MISSING modal-header")
    if not has_h3: issues.append("[BLOCKER] MISSING h3 in header or modal")
    if not has_close_x: issues.append("[BLOCKER] MISSING ✕ close button")
    if not has_body: issues.append("[WARN] MISSING modal-body")
    if has_inline_overlay: issues.append("[WARN] Uses inline overlay style (should use modal-overlay class)")
    if has_click_outside: issues.append("[BLOCKER] Uses backdrop-click-to-close (should be ✕ only)")

    if issues:
        exit_code = 1
        print(f"  Modal {i+1}: {'; '.join(issues)}")
    else:
        print(f"  Modal {i+1}: ✓")

sys.exit(exit_code)
```

### 5.2 Hex Colour Leak Detector

```bash
#!/bin/bash
# Find hardcoded hex colours outside of token definitions
# Usage: ./hex-colour-leak.sh <path/to/template.html>
# Exit: 0 = pass, 1 = violations found
#
# Excludes:
#   - CSS variable definitions  (--var: #hex)
#   - Class-level styles        (<style> blocks)
#   - Binary/image files
#   - Markdown docs

TEMPLATE="$1"
EXIT_CODE=0

# Find all hex colours in inline style attributes only
# (class-level styles in <style> blocks are the token source of truth)
VIOLATIONS=$(grep -nP 'style="[^"]*#[0-9a-fA-F]{6}' "$TEMPLATE" | \
  grep -vP -- '--[a-zA-Z-]+\s*:\s*#' | \
  grep -v '.md\|.jpg\|.png\|.svg\|.ico')

if [ -n "$VIOLATIONS" ]; then
  echo "VIOLATIONS: Hardcoded hex colours in inline styles (use var(--*) instead):"
  echo "$VIOLATIONS"
  echo ""
  echo "Fix: Replace each hex value with its matching --var token. See tokens.css."
  EXIT_CODE=1
else
  echo "✓ No hex colour leaks in inline styles."
fi

exit $EXIT_CODE
```

### 5.3 CSS Variable Audit

```bash
#!/bin/bash
# Verify all inline styles use CSS variables, not hardcoded colours
# Exclusions: --var:#hex definition lines, brand/docs files
# Usage: ./audit-css-vars.sh <path/to/template.html>
# Exit: 0 = pass, 1 = violations found

TEMPLATE="$1"
EXIT_CODE=0

HARDCODED=$(grep -noP 'color:#[0-9a-fA-F]{6}|background:#[0-9a-fA-F]{6}' "$TEMPLATE" | \
  grep -vP '--[a-zA-Z-]+\s*:\s*#' | \
  grep -v '.md\|.jpg\|.png\|.ico')

if [ -n "$HARDCODED" ]; then
  echo "VIOLATIONS: Hardcoded colours in inline styles:"
  echo "$HARDCODED"
  EXIT_CODE=1
else
  echo "✓ All colours use CSS variables."
fi

exit $EXIT_CODE
```

### 5.4 JS-Generated Modal Audit

```python
#!/usr/bin/env python3
"""Find JS-generated modals and check they use className-based structure.
Usage: python3 audit_js_modals.py <path/to/index.html>
Exit: 0 = pass, 1 = violations found
"""
import re, sys

html = open(sys.argv[1]).read()

js_modals = re.findall(r'\.innerHTML\s*=\s*`.*?modal-overlay.*?`', html, re.DOTALL)
inline_modals = re.findall(r'\.style\.cssText\s*=.*?(?:modal|overlay)', html, re.DOTALL)

print(f"JS innerHTML modals: {len(js_modals)}")
print(f"Inline style modals: {len(inline_modals)}")

exit_code = 0
if inline_modals:
    exit_code = 1
    print("\n[BLOCKER] Modals created with style.cssText (should use className='modal-overlay'):")
    for m in inline_modals:
        print(f"  {m[:120]}...")

if not exit_code:
    print("✓ All JS modals use className-based structure.")

sys.exit(exit_code)
```

### 5.5 Performance Frame Budget Check

```javascript
// Run in DevTools Console on the dashboard page
// Detects forced reflows during animations
// Usage: paste into DevTools Console, run one animation, then call check()
let reflowCount = 0;
let observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.name.includes('Layout') ||
        (entry.entryType === 'layout-shift' && entry.value > 0.01)) {
      reflowCount++;
      console.warn(`⚠️ Layout/reflow detected:`, entry.name);
    }
  }
});
observer.observe({entryTypes: ['layout-shift', 'longtask']});

function check() {
  const fps = Math.round(60 - reflowCount * 5); // rough estimate
  console.log(`Reflows: ${reflowCount}, Estimated FPS: ${fps}`);
  if (reflowCount > 0) console.error(`FAIL: ${reflowCount} forced reflows detected. Use transform/opacity instead of width/height/top/left.`);
  else console.log('✓ No forced reflows detected.');
  return reflowCount === 0;
}
```

---

## 6. CI/CD Integration

### 6.1 Pre-Commit Hook

```yaml
# .pre-commit-config.yaml (add to project root)
repos:
  - repo: local
    hooks:
      - id: structural-drift
        name: UI Structural Drift Detector
        entry: python3 scripts/audit_structural_drift.py
        files: '\.html$'
        language: system
      - id: hex-colour-leak
        name: Hex Colour Leak Detector
        entry: bash scripts/hex-colour-leak.sh
        files: '\.html$'
        language: system
      - id: css-variable-audit
        name: CSS Variable Audit
        entry: bash scripts/audit-css-vars.sh
        files: '\.html$'
        language: system
```

### 6.2 ESLint Rule: Ban Hex Colours in Inline Styles

```javascript
// .eslintrc.js — add to rules
module.exports = {
  rules: {
    // Ban hex colours in JSX inline styles
    'react/style-prop-object': ['error', {
      // Only CSS variable references allowed in style attributes
      custom: {
        cssVariableOnly: true
      }
    }],
    // Custom rule: disallow #hex in template literals used for style
    'no-restricted-syntax': [
      'error',
      {
        selector: 'TemplateLiteral[value.match(/#[0-9a-fA-F]{6}/)]',
        message: 'Use CSS variables (var(--*)) instead of hardcoded hex colours'
      }
    ]
  }
};
```

### 6.3 Playwright Test Structure

```javascript
// tests/ui-consistency.spec.js
import { test, expect } from '@playwright/test';

test.describe('UI Consistency Gate', () => {

  test('all modals have consistent structure', async ({ page }) => {
    await page.goto('http://localhost:9128');
    // Count modal-overlay elements in DOM vs spec
    const modals = await page.locator('.modal-overlay').all();
    expect(modals.length).toBeGreaterThanOrEqual(9);
    // Each modal must have modal-header > h3 + .modal-close
    for (const modal of modals) {
      const header = modal.locator('.modal-header');
      await expect(header).toBeVisible();
      await expect(header.locator('h3')).toBeVisible();
      await expect(header.locator('.modal-close')).toBeVisible();
    }
  });

  test('Escape closes all modals, focus returns', async ({ page }) => {
    // Open each modal type, press Escape, verify it closes
    const modalTriggers = await page.locator('[data-modal-trigger]').all();
    for (const trigger of modalTriggers) {
      const triggerId = await trigger.getAttribute('id');
      await trigger.click();
      await expect(page.locator('.modal-overlay.active')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator('.modal-overlay.active')).not.toBeVisible();
      // Focus should return to the trigger element
      await expect(trigger).toBeFocused();
    }
  });

  test('keyboard reachability — all interactive elements tabbable', async ({ page }) => {
    await page.goto('http://localhost:9128');
    const tabbable = await page.locator('button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])').all();
    for (const el of tabbable) {
      await el.focus();
      await expect(el).toBeFocused();
      // Verify focus ring is visible (non-zero outline)
      const outline = await el.evaluate(el => getComputedStyle(el).outline);
      expect(outline).not.toBe('0px');
      expect(outline).not.toBe('none');
    }
  });

  test('body scroll locked when modal open', async ({ page }) => {
    await page.goto('http://localhost:9128');
    const scrollYBefore = await page.evaluate(() => window.scrollY);
    // Open modal
    await page.locator('.modal-trigger').first().click();
    const scrollYAfter = await page.evaluate(() => window.scrollY);
    expect(scrollYAfter).toBe(scrollYBefore);
    // Body overflow should be hidden
    const overflow = await page.evaluate(() => getComputedStyle(document.body).overflow);
    // May be 'hidden' or computed differently — check scroll blocking
    const scrollEnabled = await page.evaluate(() => document.body.style.overflow !== 'hidden' && document.documentElement.style.overflow !== 'hidden');
    expect(scrollEnabled).toBe(false);
  });
});
```

### 6.4 Visual Regression (Percy / Chromatic)

```yaml
# .percy.yml
version: 2
snapshot:
  widths: [480, 768, 1024, 1440]
  minHeight: 1024
  percyCSS: |
    /* Remove dynamic tooltips/overlays for stable snapshots */
    .toast { display: none !important; }

# CI step (example GitHub Actions)
steps:
  - name: Visual Snapshot
    run: npx percy snapshot ./screenshots/
    if: github.event_name == 'pull_request'
```

### 6.5 CI Pipeline

```yaml
# .github/workflows/ui-consistency.yml
name: UI Consistency Gate
on: [pull_request]
jobs:
  structural-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Structural drift
        run: python3 scripts/audit_structural_drift.py src/observeco/dashboard/templates/index.html
      - name: Hex colour leak
        run: bash scripts/hex-colour-leak.sh src/observeco/dashboard/templates/index.html
      - name: CSS variable audit
        run: bash scripts/audit-css-vars.sh src/observeco/dashboard/templates/index.html
  token-change-trigger:
    if: contains(github.event.pull_request.files.*.path, 'tokens.css')
    runs-on: ubuntu-latest
    steps:
      - name: Token change detected — re-run full design token audit
        run: |
          echo "tokens.css changed — all hex values must be re-checked for token drift."
          python3 scripts/audit_structural_drift.py src/observeco/dashboard/templates/index.html
  playwright:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Run UI consistency tests
        run: npx playwright test tests/ui-consistency.spec.js
      - name: Visual regression (Percy)
        if: github.event_name == 'pull_request'
        run: npx percy snapshot --config .percy.yml
```

---

## 7. Integration with Master Fidelity Gate

This playbook is referenced by the Master Fidelity Gate (master-fidelity-gate.md) as a standalone layer. The UI Consistency Gate (§3 above) provides a pass/fail score that feeds into the Master Gate's scoring system.

**Integration:**
- Each BLOCKER item = weight 3 (critical)
- Each WARN item = weight 1 (informational)
- Total score: 33 points possible → minimum pass = 29 points AND zero BLOCKER failures

A PR that fails the UI Consistency Gate should not proceed to human UX testing — fix visual consistency first, then evaluate the feeling. If this ordering is violated and a human catches a visual inconsistency, update the Golden Gate.

---

## 8. Relationship to Other Playbooks

| This playbook | Not this playbook |
|--------------|-------------------|
| Does the UI look consistent? | Does the UI feel right? (ux-testing-playbook) |
| Do all modals share the same visual structure? | Do all states (empty/loading/error) have explanatory copy? (ux-testing-playbook) |
| Does the hex colour match the design token? | Does the text have sufficient contrast? (ux-testing-playbook Layer 4) |
| Does the component render at all breakpoints? | Does the page load fast enough? (ux-testing-playbook Trap 8) |
| Does every pattern instance use the same HTML? | Does the code match the spec? (coding-fidelity-playbook) |

---

## 9. Lessons Learned Log

| Date | Escape | Root Cause | Trap Added |
|------|--------|------------|------------|
| 2026-06-09 | 11 modals with 3 different visual languages | No UI consistency gate — each modal built independently with different patterns | Trap 1 (Same Pattern, Different Markup), Trap 3 (JS-Generated Markup Skips Design System) |
| 2026-06-09 | License Key modal used ad-hoc inline styles with different border-radius and no ✕ button | JS-generated modal skipped class-based design system entirely | Trap 3 expanded — className requirement for all JS-generated UI |
| 2026-06-09 | Contrast, keyboard reachability, and focus indicators had zero automated checks | No a11y dimension in original playbook | Dimension 9 (Accessibility Consistency) with [BLOCKER] criteria |

**Archival rule:** Entries older than 90 days with no recurrence in the current codebase are moved to `lessons-archive.md`. Active lessons are surfaced into their relevant dimension or trap in this document.

---

*Last updated: 2026-06-09*
*Author: Main — Applied Thinker*