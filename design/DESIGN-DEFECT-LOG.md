# ObserveCo design system — defect log

Opened 2026-11-01 while auditing the consulting design system against production.
Each entry names the file:line, the measurement that exposes it, and the check that
would prove the fix. No entry is closed by reading code alone.

Status key: **OPEN** = live defect. **RESOLVED** = fixed and verified.

---

## D-001 — `.trend-chip` text fails contrast: 2.16:1 · OPEN

**Where:** `website/assets/draft.css:1312` — `color: var(--amber)` on
`background: rgba(201, 154, 63, 0.12)`.

**Measured:** amber `#c99a3f` on its own 12% tint over paper = **2.16:1**.
Amber on plain paper = **2.38:1**. Both fail AA body (4.5) and AA large (3.0), for
12px/500 text.

**Consequence:** every trend chip on the site is unreadable to anyone with reduced
contrast sensitivity, and it is the one live component that a design tool handed this
palette would copy verbatim.

**Fix:** keep the amber tint and the amber arrow glyph; set the words to `var(--fg)`.
Verify: `getComputedStyle(.trend-chip).color` on `#f1eade`-equivalent tint ≥ 4.5:1.

## D-002 — homepage `<h1>` is 12px; the real headline is a `<p>` · OPEN

**Where:** `website/index.html:251` (`<h1>Differentiation strategy consultancy for
Singapore small businesses</h1>`) and `:252` (`<p class="hero-tagline">`).

**Measured** at 1440×900 on `https://observeco.com/`:

| Element | Size | Weight |
|---|---|---|
| `h1` | **12px** | 500 |
| `p.hero-tagline` | **56px** | 600 |

Every other page (`/method.html`, `/books.html`, `/press.html`, `/whitepapers.html`)
renders `h1` at 56px desktop / 36px mobile. The homepage is the only outlier.

**Consequence:** the page carrying the most search weight publishes a small keyword
line as its document heading, while the visual headline carries no heading semantics.
The outline read by search engines and screen readers is inverted. It also explains
why a design tool measuring "the H1" got 12px and concluded headlines cap at 20px.

**Fix:** promote `p.hero-tagline` to `<h1>` (it already has `.teal` spans that survive
the swap), and demote the keyword line to a `<p class="kicker">` or fold it into the
page title. Verify with `document.querySelectorAll('h1').length === 1` and
`getComputedStyle(h1).fontSize === '56px'` at 1440, `'36px'` at 390.

## D-003 — `--yellow` is referenced but never defined · OPEN

**Where:** `website/assets/draft.css:1008` — `table.compare .generic { color:
var(--yellow); }`. No `--yellow` exists anywhere in `:root`.

**Measured:** the `:root` block defines 39 properties; `--yellow` is not among them.
An undefined custom property makes the declaration invalid at computed-value time, so
the colour silently falls back to inherited ink. The rule currently does nothing.

**Consequence:** a comparison-table cell that was meant to be visually distinguished
is indistinguishable from ordinary text. Silent — nothing errors.

**Fix:** either delete the rule, or point it at `--amber` **as a tint-plus-ink
treatment** (not amber text — see D-001 and the README contrast table). Verify by
reading the computed colour of a `.generic` cell in a rendered `table.compare`.

---

## Resolved this pass

- **R-001 — two naming families for one palette.** Docs said `--canvas`/`--insight`/`--ink`;
  production said `--bg`/`--green`/`--fg`. Copying a doc snippet produced dead variables.
  Fixed in `draft.css:58-77` with an alias block; verified 16 browser assertions
  (every alias resolves to its documented hex, no existing token moved). Note: `--space-*`
  is deliberately *not* aliased — the doc scale is a 4px grid, production is 8px.
- **R-002 — the design-system map was never committed.** `design/README.md` existed only
  on disk. Tracked in `8504ae0`.
- **R-003 — the retired dark palette was indistinguishable from the source of truth.**
  `design/tokens.css` sat beside `consulting-tokens.css` with the most natural filename,
  and was handed to an external design tool as the current tokens. Renamed to
  `tokens-RETIRED-dark-telemetry.css` with a do-not-use banner; `design/live-tokens.css`
  added as the only file that matches production (39/39 properties verified).
- **R-004 — `design/README.md` described a draft as the token source.** It claimed
  `consulting-tokens.css` was "the `:root` block draft.css is derived from". Measured:
  spacing, type scale, radii, and the coral/amber pair all diverge. Corrected, and the
  measured type ladder, radii, contrast table and handoff rules are now in the README.

## How these were measured

Computed styles read from the rendered live site (Playwright, Chromium headless) at
1440×900 and 390×844 across five pages; contrast ratios computed from the actual hex
pairs with tints blended over the paper canvas. Stylesheet greps alone are insufficient
here — `clamp()` sizes are invisible to a literal-px scan, which is how the type scale
was first undercounted.
