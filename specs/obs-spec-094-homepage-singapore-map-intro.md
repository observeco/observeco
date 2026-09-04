# OBS-SPEC-094 — Homepage Dark Singapore Map Intro Overlay

**Status:** Draft — approved for build (dark projection chosen 2026-09-04)
**Product:** ObserveCo consulting website — homepage (`website/index.html`)
**Depends on:** none (standalone homepage enhancement)
**Owner:** Pragma (implementation) · Spectrum (design authority)
**Design authority:** `mockups/singapore-map-intro-overlay-v4-dark.html` (dark projection) — the exact Watch map SVG + dark-adapted zone/sparkle styles

---

## 1. Problem

The homepage loads straight into the light consultancy site with no opening moment. Sean wants a deliberate, on-brand intro: the Singapore map (the same archipelago used on The Watch page) pops up as a dark projection overlay on load, then fades to reveal the light site. This gives the homepage a signature opening beat that ties the brand to its Singapore market.

**Decision (2026-09-04):** dark projection mode chosen over light paper. The dark map pops up, then fades to the light site — a deliberate contrast moment.

## 2. What Exists

| Asset | Location | State |
|---|---|---|
| Live consultancy homepage | `website/index.html` (branch `fix/drift-alias`) | Live; light-first paper design system |
| The Watch Singapore map SVG | `differentiation-watch.html` → `.map-svg` (`viewBox="4 0 707 459"`) | Live; 16 big zones, 16 small zones, 30 white sparkle stars |
| Consulting design tokens | `design/consulting-tokens.css` | Dark projection mode defined via `[data-theme="dark"]` |
| Approved dark mockup | `mockups/singapore-map-intro-overlay-v4-dark.html` | Design authority |

**Already implemented (commit `df56caa` on `fix/drift-alias`):** the intro overlay is already injected into `website/index.html`. This spec documents the change for the record and as the implementation reference.

## 3. Architecture

### 3.1 Placement

- **CSS:** a `<style>` block injected before `</head>` — scoped under `#sg-intro` so it cannot collide with the site's `assets/draft.css` classes (`.zone`, `.sparkle`, `.map-svg` are all namespaced under `#sg-intro`).
- **HTML:** the overlay `<div id="sg-intro">` injected immediately after `<body>`, containing the map card, the survey grid, and the exact Watch map SVG.
- **JS:** an IIFE before `</body>` that auto-dismisses the overlay after 3.2s and wires the skip button.

### 3.2 The overlay structure

```
#sg-intro (fixed, inset:0, z-index:1000, bg #10141a)
├── button.skip#sgSkip          — "skip →", top-right
├── .map-card#sgMapCard         — width min(82vw,760px), aspect 3/2, dark card
│   ├── .map-grid               — faint teal survey grid (masked radial)
│   └── svg.map-svg             — the exact Watch map (16 big, 16 small, 30 sparkle)
└── .intro-label                — "● observeco · singapore · live"
```

### 3.3 Animations (all scoped under `#sg-intro`)

| Animation | Element | Behavior |
|---|---|---|
| `sg-pop-in` | `.map-card` | scale 0.55→1.04→1, opacity 0→1, 1.1s `cubic-bezier(0.16,1,0.3,1)` delay 0.25s |
| `sg-sheen` | `.map-card::after` | diagonal light band sweeps, 7s loop |
| `sg-drift` | `.map-svg` | slow Ken Burns pan/zoom, 36s loop |
| `sg-breathe` | `.zone.big` | scale 1→1.02, 18s loop, staggered 3s phases |
| `sg-flash` | `.zone.small` | fill flashes white, 12s loop, `--sd` stagger |
| `sg-twinkle` | `.sparkle` | white stars twinkle, 7.2s loop, `--sp` stagger |
| `sg-fade-up` | `.intro-label` | fades up, 0.8s delay 1.1s |

### 3.4 Dark-adapted map palette

The Watch map's light-theme colors are brightened for the dark card:

| Token | Light (Watch) | Dark (intro) |
|---|---|---|
| Zone fill | `rgba(14,110,92,0.26)` | `rgba(63,182,155,0.22)` |
| Zone stroke | `rgba(14,110,92,0.55)` | `rgba(63,182,155,0.60)` |
| Zone shadow | `rgba(20,60,50,…)` | `rgba(0,0,0,…)` |
| Small-zone flash | white | white (unchanged) |
| Sparkle | `#ffffff` | `#ffffff` (unchanged) |
| Card bg | `#eaf4f1→#e8f1ee` | `#0d1117→#141a21→#0d1117` |
| Grid | `rgba(14,110,92,0.05)` | `rgba(63,182,155,0.08)` |

## 4. Implementation

### 4.1 Files

| File | Change |
|---|---|
| `website/index.html` | Add `<style>` block before `</head>`; add `<div id="sg-intro">` after `<body>`; add dismiss IIFE before `</body>` |

### 4.2 The exact map SVG

Copy the `.map-svg` element verbatim from `differentiation-watch.html` (or from `mockups/singapore-map-intro-overlay-v4-dark.html`). It is 293KB: 16 `zone big` paths, 16 `zone small` paths, 30 `sparkle` circles, `viewBox="4 0 707 459"`. Do not regenerate or simplify it — the exact geometry is the design authority.

### 4.3 Dismiss logic

```js
(function () {
  var intro = document.getElementById('sg-intro');
  if (!intro) return;
  function dismiss() {
    intro.classList.add('hide');          // opacity 0, pointer-events none
    setTimeout(function () { intro.style.display = 'none'; }, 1200);
  }
  setTimeout(dismiss, 3200);              // auto-dismiss after 3.2s
  var skip = document.getElementById('sgSkip');
  if (skip) skip.addEventListener('click', dismiss);
})();
```

## 5. Edge Cases

| Case | Handling |
|---|---|
| `prefers-reduced-motion` | All animations disabled; map renders static at scale 1, sparkles at 0.5 opacity |
| JS disabled | Overlay never dismisses → **must not block the page.** The overlay is `position:fixed` with `z-index:1000`; if JS is off, the site is hidden behind it. **Mitigation:** add a `<noscript>` style that hides `#sg-intro` (see §6 note). |
| Mobile | Map card `width:min(82vw,760px)` scales down; aspect-ratio keeps it proportional |
| Skip button | Dismisses immediately |
| Homepage's own scripts | Nav toggle, clicker, etc. must keep working — verified (nav toggle + skip both functional) |
| CSS collision | All intro classes namespaced under `#sg-intro`; cannot clash with `assets/draft.css` `.zone`/`.sparkle`/`.map-svg` |

## 6. Pro Gating

- **Accessibility:** overlay is `role="dialog"` with `aria-label`; skip button is keyboard-focusable. The map is `aria-hidden` (decorative).
- **No-JS fallback (recommended before ship):** add `<noscript><style>#sg-intro{display:none}</style></noscript>` so the site is never permanently hidden behind the overlay when JS is disabled. **Not yet added** — flag for Pragma.
- **Performance:** the 293KB inline SVG adds weight to the homepage HTML. Acceptable for a single-page intro; if it becomes a concern, move the SVG to an external file loaded after first paint.

## 7. Success Criteria

1. On load, the dark Singapore map pops up (scale-in) over the light site.
2. The 30 white sparkle stars twinkle; the 16 small zones flash white; the map drifts slowly.
3. After 3.2s (or on skip), the overlay fades to reveal the light consultancy homepage.
4. The homepage's own nav, clicker, and all interactive elements work normally after dismissal.
5. `prefers-reduced-motion` renders a static map with no animation.
6. No JS console errors.
7. The exact Watch map geometry is preserved (16/16/30, `viewBox="4 0 707 459"`).

---

*Committed as `df56caa` on `fix/drift-alias`. Spec written for the record 2026-09-04.*
