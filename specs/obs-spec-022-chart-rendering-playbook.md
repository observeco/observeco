# obs-spec-022: Chart Rendering & Data Visualization Playbook

**Status:** Draft 2026-06-13
**Product:** ObserveCo dashboard
**Depends on:** obs-spec-020 (Token Analytics Dashboard)
**Owner:** Pragma (COO)

---

## §1 Purpose

Standardize how ObserveCo renders charts, graphs, and data visualizations. This playbook ensures consistency across all dashboard tabs and prevents the anti-patterns discovered during the Brain Analysis UX redesign (raw Canvas without HiDPI, no tooltips, no interactivity, magic-number sizing).

## §2 Current State (Inventory)

| # | Chart | Location | Engine | Interactivity | Issues |
|---|-------|----------|--------|---------------|--------|
| 1 | Token time-series | Token Analytics | Chart.js | Full (filters, drill-down) | CDN fragility, hardcoded colors |
| 2 | 90-day trend | Brain Analysis modal | Raw Canvas | None | No HiDPI, no tooltips, no resize |
| 3 | Component bars | Brain Analysis | CSS divs | Static | Hardcoded colors |
| 4 | Drift sparklines | Brain Analysis | Inline SVG | Static | Fixed width, no tooltips |
| 5 | Turn timeline | Brain Analysis | CSS divs | Hover tooltip | Tiny (34px max), no axis labels |
| 6 | Input tokens bar | Brain Analysis | CSS divs | Static | Magic thresholds |
| 7 | Optimiser progress | Brain Analysis | CSS bar | None | No transitions |
| 8 | Garden grade | Brain Analysis | CSS cards | None | Edge case for N/A |

## §3 Rendering Engine Decision Matrix

| Chart Type | Recommended Engine | Why |
|------------|-------------------|-----|
| Time-series (line/area) | **uPlot** or **Chart.js** | Built-in tooltips, zoom, responsive resize, HiDPI |
| Stacked area (token breakdown) | **uPlot** or **Chart.js** | Stacked mode handles input/cache/output layers |
| Bar chart (categorical) | **Inline SVG** or **Chart.js** | <20 elements, SVG is fine |
| Sparkline (mini trend) | **Inline SVG** | Lightweight, no library needed |
| Donut/pie (breakdown) | **Inline SVG** | Arc path math is simple for <8 segments |
| Progress bar | **CSS** | No JS needed |
| KPI card with sparkline | **CSS + inline SVG** | Compact, no library |

### Anti-Patterns (Never Do)

1. ❌ **Raw Canvas for new charts** — no tooltips, no HiDPI, no accessibility, manual coordinate math
2. ❌ **CDN-loaded libraries without local fallback** — Chart.js CDN fails silently
3. ❌ **Hardcoded pixel sizes** — use `container.clientWidth` + `ResizeObserver`
4. ❌ **Magic number thresholds** — define in config, not inline
5. ❌ **No `devicePixelRatio` scaling** — charts blur on Retina displays
6. ❌ **Client-side aggregation of raw data** — do it on the backend with SQL `GROUP BY`

## §4 Backend Data API Pattern

### Standard Response Schema

All chart data endpoints must return:

```json
{
  "series": [
    {
      "metric": "input_tokens",
      "unit": "tokens",
      "label": "Input Tokens",
      "color": "#3b82f6",
      "data": [
        {"ts": 1780876800, "value": 3366786},
        {"ts": 1780963200, "value": 3542100}
      ]
    }
  ],
  "totals": {
    "input_tokens": 24800000,
    "output_tokens": 7440000,
    "cache_creation_tokens": 1200000,
    "cache_read_tokens": 800000
  },
  "metadata": {
    "granularity": "day",
    "timezone": "UTC",
    "data_points": 30,
    "has_real_data": true,
    "last_updated": "2025-06-13T14:30:00Z"
  }
}
```

**Compatibility note:** obs-spec-020 §4 ships `{data, summary}` as its response shape (frozen in §10.8). This spec defines `{series, totals, metadata}` as the canonical shape for *new* endpoints. Existing 020 endpoints keep their shape; new chart endpoints use this schema. A future migration can add a `series` alias to 020's response without breaking existing clients.

### Rules

1. **Server-side aggregation always** — never send raw event rows to the frontend for charting
2. **ISO 8601 UTC timestamps** — client formats to local time
3. **Arrays, not objects** — `[{ts, value}]` not `{ts1: v1, ts2: v2}`
4. **`null` for missing buckets** — avoids interpolation artifacts
5. **Include `metadata` block** — gives UI hints for formatting and debugging
6. **Send totals alongside series** — eliminates client-side summation
7. **Color per series** — backend specifies colors, frontend uses them consistently

## §5 Frontend Chart Patterns

### HiDPI Support (Mandatory for Canvas)

```javascript
const dpr = window.devicePixelRatio || 1;
canvas.width = container.clientWidth * dpr;
canvas.height = height * dpr;
canvas.style.width = container.clientWidth + 'px';
canvas.style.height = height + 'px';
ctx.scale(dpr, dpr);
```

### Responsive Resize (Mandatory)

```javascript
const ro = new ResizeObserver(entries => {
  const { width } = entries[0].contentRect;
  chart.setSize({ width, height: 400 });
});
ro.observe(container);
```

### Tooltip Pattern (Mandatory for Interactive Charts)

- **uPlot/Chart.js**: built-in, configure via options
- **Raw Canvas/SVG**: implement custom tooltip div positioned near cursor
- **CSS-only charts**: use `title` attribute or CSS `::after` pseudo-element

### Filter Pattern

- **Global filter bar** at top of chart section
- **URL-synced** via `?from=...&to=...&agent=...` for shareability
- **Debounced** (300ms) for text inputs, immediate for dropdowns
- **Optimistic loading** — show stale data with loading indicator

### Stacked Area Chart Pattern (Token Breakdown)

For showing input/cache/output token layers:

```
┌─────────────────────────────────────┐
│ ████ Cache Read (green)             │  ← top layer
│ ████████████ Cache Creation (amber) │  ← middle layer
│ ██████████████████████ Input (blue) │  ← bottom layer
│ ─────────────────────────────────── │
│         Time axis                   │
└─────────────────────────────────────┘
```

- Bottom layer = largest (input tokens)
- Middle = cache creation (write cost)
- Top = cache read (savings indicator)
- Legend clickable to toggle series visibility

## §6 Token Breakdown Categories

| Category | Field | Description | Chart Color |
|----------|-------|-------------|-------------|
| Input Tokens | `input_tokens` | Total prompt/input tokens | `#3b82f6` (blue) |
| Output Tokens | `output_tokens` | Total completion/output tokens | `#8b5cf6` (purple) |
| Cache Creation | `cache_creation_tokens` | Tokens written to cache (cost) | `#f59e0b` (amber) |
| Cache Read | `cache_read_tokens` | Tokens read from cache (savings) | `#22c55e` (green) |

### Filter Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Total** | Fleet-wide aggregate | Overview, daily monitoring |
| **Per-Agent** | Breakdown by agent name | Drill-down, debugging |

## §7 Migration Path

### Phase 1: Immediate (This Sprint)
1. Add cache columns to `token_history` table (Migration 22)
2. Update snapshot endpoint to record cache tokens
3. Rewrite trend modal with stacked area chart (input/cache/output)
4. Add Total/Agent filter toggle to trend modal
5. Apply HiDPI + responsive resize to all Canvas charts

### Phase 2: Next Sprint
1. Replace raw Canvas trend chart with uPlot (if performance warrants)
2. Add URL-synced filters to Token Analytics tab
3. Add sparkline SVGs to KPI cards
4. Migrate remaining CSS-only charts to consistent color system

### Phase 3: Future
1. Add zoom/pan to time-series charts
2. Add chart export (PNG/SVG)
3. Add accessibility (aria-labels, keyboard navigation)

## §8 Color System

All charts must use these CSS variables (defined in `:root`):

```css
--chart-blue: #3b82f6;     /* Input tokens, primary series */
--chart-purple: #8b5cf6;    /* Output tokens, secondary series */
--chart-amber: #f59e0b;     /* Cache creation, cost indicator */
--chart-green: #22c55e;     /* Cache read, savings indicator */
--chart-red: #ef4444;       /* Alerts, thresholds */
--chart-grid: #1e293b;      /* Grid lines */
--chart-label: #64748b;     /* Axis labels */
--chart-bg: #0f172a;        /* Chart background */
```

## §9 Acceptance Criteria

- [ ] All new charts use a library (uPlot/Chart.js) or inline SVG — no raw Canvas
- [ ] All Canvas charts support HiDPI (`devicePixelRatio` scaling)
- [ ] All charts resize responsively via `ResizeObserver`
- [ ] All interactive charts have tooltips on hover
- [ ] All chart data comes from server-side aggregated APIs
- [ ] Token breakdown shows input/cache/output as stacked layers
- [ ] Total/Agent filter works and updates chart in-place
- [ ] Color system is consistent across all chart types
- [ ] No hardcoded magic numbers — all thresholds in config
