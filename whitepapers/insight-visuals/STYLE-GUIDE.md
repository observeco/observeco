# Book 1 Insight Visuals — Style Guide (v2 — Unified)

## Canonical Design System

All visuals MUST use these tokens. No exceptions.

```css
:root {
  --canvas: #f7f6f3;           /* Light paper background */
  --surface: #ffffff;          /* White card surface */
  --surface-muted: #efeee9;    /* Muted card backgrounds */
  --ink: #1b1f24;              /* Primary text */
  --ink-2: #4a525c;            /* Secondary text */
  --ink-3: #6b737e;            /* Muted/label text */
  --accent: #0e6e5c;           /* Primary teal accent */
  --accent-strong: #0a5447;    /* Dark teal for emphasis */
  --accent-tint: #e7f1ee;      /* Light teal background */
  --accent-line: #c6dcd4;      /* Teal border */
  --critical: #b42318;         /* Red for warnings/alerts */
  --critical-tint: #fbeae7;    /* Light red background */
  --warning: #9a6500;          /* Amber for caution */
  --warning-tint: #fbf0d8;     /* Light amber background */
  --line: #e4e2dc;             /* Borders */
}
```

## Typography
- **Display:** `'Playfair Display', Georgia, serif` — 38px / 800 weight (h1)
- **Body:** `'Inter', system-ui, sans-serif` — 14-15px / 400-600 weight
- **Overline:** 11px / uppercase / 0.12em letter-spacing / accent color / 600 weight
- **Subtitle:** 15px / ink-2 / 1.5 line-height
- **Stat values:** Playfair Display / 28-40px / 800 weight / ink color
- **Labels:** 12px / ink-3 / 1.4 line-height
- **Footer:** 11px / ink-3

## Layout
- **Card:** 1200px wide, white surface, 16px radius, `var(--line)` border, subtle shadow
- **Card header:** 32px 40px 24px padding, line border-bottom
- **Card body:** 32px 40px padding
- **Card footer:** 16px 40px padding, line border-top
- **Inner cards:** `var(--surface-muted)` background, 10px radius, 20px padding
- **Gaps:** 12-16px between grid items, 24px between sections
- **Insight box:** accent-tint bg, accent-line border, 10px radius, 16px 20px padding

## Confidence Badge
- Pill shape (999px radius)
- `rgba(14,110,92,0.1)` background
- `var(--accent-strong)` text
- 6px dot indicator before text
- 10px uppercase 600 weight

## Background Colors for Data Emphasis
- **Critical/alert data:** `var(--critical-tint)` bg + `rgba(180,35,24,0.15)` border
- **Positive/accent data:** `var(--accent-tint)` bg + `var(--accent-line)` border
- **Neutral data:** `var(--surface-muted)` bg, no border

## Forbidden
- No dark backgrounds (`#0f172a`, `#1e293b`, `#273548`)
- No blue accents (`#3b82f6`, `#8b5cf6`) — use teal only
- No `box-shadow` heavier than the card-level shadow
- No fonts other than Playfair Display + Inter

## File Naming
`{NN}-{slug}.html` — e.g., `01-three-engines.html`

## Output
- Standalone HTML (no external deps except Google Fonts)
- 1200px card width, responsive centering
- Light paper canvas behind white card
