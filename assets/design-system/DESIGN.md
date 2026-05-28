# ObserveCo Design System

> Category: Developer Tools
> Agent observability. Dark mission-control aesthetic, green telemetry, data-dense dashboard surfaces. Built for fleet monitoring at 3am.

## 1. Visual Theme & Atmosphere

An **agent observability command center** — dark, information-dense, unambiguous. Every pixel earns its place. The aesthetic draws from NASA mission control rooms meets modern cloud monitoring (Datadog, Grafana) — but purpose-built for AI agent fleets. Green telemetry on dark navy is the core contrast pair, anchored by the brand green `#22c55e` that runs through the logo pulse line, key metrics, and status indicators.

| Element | Hex | Role |
|---------|-----|------|
| Background | `#0f172a` | Deep navy canvas (ObserveCo brand) |
| Surface | `#1e293b` | Agent cards, panels, elevated areas |
| Surface Hover | `#253349` | Interactive surface hover |
| Surface Active | `#334155` | Selected panel, active filter |
| Border | `#334155` | Panel dividers, card outlines |
| Brand Green | `#22c55e` | Primary brand accent — pulse line, key metrics, healthy status |
| Accent Blue | `#3b82f6` | Info / baseline indicators, learning phase |
| Warning Yellow | `#eab308` | Degraded, 1-2 missed heartbeats |
| Critical Red | `#ef4444` | Dead agent, tripped circuit |
| Text Primary | `#f8fafc` | High-contrast readable text |
| Text Secondary | `#94a3b8` | Labels, secondary information |
| Text Tertiary | `#64748b` | Timestamps, metadata |

*Every readout must be readable at a glance by someone who's been debugging agent failures for 6 hours.*

### Use Cases

ObserveCo is purpose-built for:
- **Agent fleet monitoring** — health dashboard, circuit breaker state, pulse tracking
- **Token observability** — per-component token breakdown, drift detection, compression savings
- **Memory hygiene** — ClawForge garden scores, duplicate/contradiction/stale counts
- **Error timeline** — circuit trips, heartbeat misses, drift breaches across all agents
- **Any information-dense, dark-themed, high-stakes agent operations display**

### Prior Art

NASA Mission Control (Houston) — amber-on-navy telemetry, hierarchical alert systems. Datadog/Grafana — modern cloud monitoring dashboards, modular panel layouts, real-time data feeds. The ObserveCo aesthetic combines mission-control clarity with modern dashboard density: dark navy `#0f172a` canvas, green brand telemetry `#22c55e`, independent status colour layer (green/yellow/red), and token composition bars that use a completely separate palette to avoid confusion.

## 2. Color

### Surface Palette

| Token | Hex | Usage |
|-------|-----|-------|
| Background | `#0f172a` | Page canvas, primary depth |
| Surface | `#1e293b` | Agent cards, panels, elevated areas |
| Surface Hover | `#253349` | Interactive surface state |
| Surface Active | `#334155` | Selected, active panel |
| Border Default | `#334155` | Card borders, dividers |
| Border Subtle | `#273548` | Inner dividers, minor separation |

### Status Palette (health semantics)

| Token | Hex | Usage |
|-------|-----|-------|
| Healthy | `#22c55e` | 🟢 Pulse OK, circuit closed, drift negative (savings) |
| Warning | `#eab308` | 🟡 1-2 missed heartbeats, drift >10%, near-threshold |
| Critical | `#ef4444` | 🔴 Dead agent, circuit tripped, hard failure |
| Info / Baseline | `#3b82f6` | 🔵 Learning phase, no baseline yet, neutral information |

All status colors on `#1e293b` pass WCAG AA (minimum 4.5:1).

### Data & Telemetry Palette

| Token | Hex | Usage |
|-------|-----|-------|
| Brand Green | `#22c55e` | Key metrics, telemetry values, healthy status indicators |
| Accent Blue | `#3b82f6` | Info / baseline indicators, links, learning phase |
| Alert Critical | `#ef4444` | Circuit trip, heartbeat miss, hard failure |
| Alert Warning | `#eab308` | Drift breach, degraded state |
| Alert Success | `#22c55e` | Nominal status, recovery events |

### Token Composition Palette (distinct from status)

These colors represent token breakdown components. They are deliberately DIFFERENT from the status palette to prevent confusion between "what is the agent's health" and "what is in the agent's context window."

| Component | Hex | Usage |
|-----------|-----|-------|
| Identity | `#6366f1` | Indigo — agent identity block in token bar |
| Skills | `#8b5cf6` | Violet — skills/tools section in token bar |
| Memory | `#ec4899` | Pink — memory/context block in token bar |
| Tools | `#14b8a6` | Teal — tool schemas section in token bar |
| Guidance | `#f97316` | Orange — guidance/prose section in token bar |

### Text Palette

| Token | Hex | Usage |
|-------|-----|-------|
| Primary | `#f8fafc` | Readable at distance, primary content |
| Secondary | `#94a3b8` | Labels, descriptors, secondary metrics |
| Tertiary | `#64748b` | Timestamps, metadata, grid labels |

### Dark Mode

Dark mode is the native mode. No light mode variant by design — agent observability environments are always low-light (on-call at 3am, monitoring screens in a dark office). The `#0f172a` background was chosen specifically because it reduces eye strain during extended monitoring sessions while maintaining sufficient contrast for the telemetry layer.

```css
:root {
  --bg-default: #0f172a;
  --bg-surface: #1e293b;
  --bg-surface-hover: #253349;
  --bg-surface-active: #334155;
  --border-default: #334155;
  --border-subtle: #273548;
  --data-primary: #22c55e;
  --data-secondary: #3b82f6;
  --data-accent: #3b82f6;
  --data-alert-success: #22c55e;
  --data-alert-warning: #eab308;
  --data-alert-critical: #ef4444;
  --token-identity: #6366f1;
  --token-skills: #8b5cf6;
  --token-memory: #ec4899;
  --token-tools: #14b8a6;
  --token-guidance: #f97316;
  --fg-primary: #f8fafc;
  --fg-secondary: #94a3b8;
  --fg-tertiary: #64748b;
}
```

## 3. Typography

### Font Stack

```css
/* Monospace for all data readouts — consistency at speed */
--font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;

/* Sans-serif for labels, navigation, prose */
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
```

### Type Scale

| Role | Size | Weight | Line Height | Font | Style |
|------|------|--------|-------------|------|-------|
| Fleet Count | 40px | 700 | 1.0 | JetBrains Mono | — |
| Agent Name | 15px | 600 | 1.2 | Inter | — |
| Section Header | 13px | 600 | 1.2 | Inter | uppercase, 0.08em tracking |
| Card Label | 11px | 600 | 1.0 | Inter | uppercase, 0.06em tracking |
| Body | 14px | 400 | 1.5 | Inter | — |
| Caption | 12px | 400 | 1.4 | Inter | — |
| Micro | 10px | 600 | 1.0 | Inter | uppercase, 0.05em tracking |
| Monospace Data | 14px | 500 | 1.2 | JetBrains Mono | — |

**Font labels for catalog extraction:**

```
Display: "JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace
Body: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif
Mono: "JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace
```

## 4. Spacing

4px baseline grid for dense telemetry layouts. Agent cards use 12px padding, fleet header uses 16-24px, section gaps use 32px.

```css
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;  --space-4: 16px;
--space-5: 20px;  --space-6: 24px;  --space-8: 32px;   --space-12: 48px;
--space-16: 64px; --space-20: 80px;
```

## 5. Layout & Composition

### Dashboard Grid

Two-column layout: left rail (agent cards, flex) + right rail (alerts panel, 320px fixed). Error timeline full-width below. Fleet header sticky at top.

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-3);
}

.fleet-header {
  position: sticky;
  top: 0;
  background: var(--bg-default);
  padding: var(--space-4);
  z-index: 10;
}
```

### Agent Card

```css
.agent-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: var(--space-3);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-3);
}
```

## 6. Components

### Status Dot

```css
/* Health indicator for agent status */

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.healthy {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
}

.status-dot.warning {
  background: #eab308;
  box-shadow: 0 0 6px rgba(234, 179, 8, 0.4);
}

.status-dot.critical {
  background: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.4);
  animation: pulse-alert 2s ease-in-out infinite;
}

@keyframes pulse-alert {
  0%, 100% { box-shadow: 0 0 6px rgba(239, 68, 68, 0.4); }
  50% { box-shadow: 0 0 14px rgba(239, 68, 68, 0.7); }
}
```

### Token Profile Bar

```css
/* Horizontal stacked bar showing token composition */
.token-bar {
  display: flex;
  height: 8px;
  border-radius: 2px;
  overflow: hidden;
  gap: 0;
}

.token-bar-segment {
  height: 100%;
  transition: width 150ms ease-out;
}

.token-bar-segment.identity { background: #6366f1; }
.token-bar-segment.skills   { background: #8b5cf6; }
.token-bar-segment.memory   { background: #ec4899; }
.token-bar-segment.tools    { background: #14b8a6; }
.token-bar-segment.guidance { background: #f97316; }
```

### Drift Sparkline

```css
/* 7-bar mini chart showing token change over time */

.drift-sparkline {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 20px;
}

.drift-bar {
  flex: 1;
  min-width: 3px;
  border-radius: 1px 1px 0 0;
}

.drift-bar.positive { background: #f97316; }
.drift-bar.negative { background: #22c55e; }
.drift-bar.neutral  { background: #94a3b8; }
```

### Alert Panel Row

```css
/* Single alert in the right-rail panel */

.alert-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-left: 3px solid transparent;
  font-size: 13px;
}

.alert-row.critical {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}

.alert-row.warning {
  border-left-color: #eab308;
}

.alert-row.info {
  border-left-color: #3b82f6;
}
```

### Error Timeline Row

```css
/* Full-width event feed row */

.timeline-row {
  display: grid;
  grid-template-columns: 32px 80px 1fr auto;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  align-items: center;
  font-size: 13px;
  border-bottom: 1px solid var(--border-subtle);
}

.timeline-row.critical {
  border-left: 3px solid #ef4444;
  background: rgba(239, 68, 68, 0.03);
}

.timeline-row.warning {
  border-left: 3px solid #eab308;
}

.timeline-row.info {
  border-left: 3px solid #3b82f6;
}

.timeline-time {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--fg-tertiary);
}

.timeline-agent {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--data-primary);
  cursor: pointer;
}

.timeline-agent:hover {
  color: var(--data-secondary);
  text-decoration: underline;
}
```

### Locked Pro Tile

```css
/* Grayed-out Pro feature — visible but locked */

.pro-tile {
  opacity: 0.5;
  filter: grayscale(0.6);
  transition: opacity 150ms ease-out;
  border: 1px dashed var(--border-default);
}

.pro-tile:hover {
  opacity: 0.8;
  filter: grayscale(0.2);
}

.pro-tile-badge {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--fg-tertiary);
  padding: 1px 6px;
  border: 1px solid var(--border-default);
  border-radius: 2px;
}
```

### Fleet Summary Strip

```css
/* Horizontal metric strip in sticky header */

.fleet-strip {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  font-family: var(--font-mono);
  font-size: 14px;
}

.fleet-metric {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.fleet-metric-value {
  font-weight: 700;
  font-size: 18px;
}
```

## 7. Motion & Interaction

| Interaction | Duration | Easing | Effect |
|-------------|----------|--------|--------|
| Alert pulse (critical) | 2s | ease-in-out | Glow intensity oscillation (loop) |
| Card appear | 200ms | ease-out | Opacity 0→1 |
| Status change | 150ms | ease-out | Background flash on new data |
| Token bar update | 150ms | ease-out | Width transition on segments |
| Hover state | 100ms | ease-in | Border color brightens |

```css
--transition-fast: 100ms ease-in;
--transition-base: 150ms ease-out;
--transition-slow: 300ms ease-out;
```

### prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## 8. Voice & Brand

### Iconography

Minimal, functional iconography — Lucide or similar stroke-based icons (1.5px stroke, 16px default). Every icon must communicate operational state:
- ⚡ Circuit breaker / error event
- 💔 Heartbeat miss
- 📈 Drift breach
- ✅ Recovery
- 🔒 Pro-locked feature indicator

### Tone

- **Precise**: Data-first, no marketing language. The dashboard speaks through values and colour, not prose.
- **Sparse**: Agent cards are dense but never cluttered. Every pixel earns its place.
- **Hierarchical**: Visual urgency maps directly to operational urgency. Red is critical. Yellow is warning. Green is healthy. No decorative use of status colours.
- **Transparent**: Locked Pro tiles use the user's OWN data in preview modals. No screenshots of someone else's dashboard.

### Visual Signals

- **Status dot colour** → agent health (green/yellow/red)
- **Token bar colours** → composition breakdown (indigo/violet/pink/teal/orange — deliberately NOT green/yellow/red)
- **Left border colour** → event severity (red for critical, yellow for warning, blue for info)
- **Dash vs solid border** → Pro-locked vs free feature

The two colour systems (status and composition) are kept visually separate at all times. Token composition bars never use green/yellow/red, which would confuse "what is the agent's health" with "what is in the agent's context."

## 9. Anti-patterns

- Do not use decorative colors in data displays — every hue must convey operational meaning
- Do not mix status palette (green/yellow/red) with token palette (indigo/violet/pink/teal/orange) — they serve different purposes
- Do not use rounded corners > 4px on panels — agent monitoring is functional, not friendly
- Do not use proportional fonts for metric values — use monospace exclusively for data
- Do not animate non-alert elements — motion is reserved for signals that matter
- Do not use light mode — low-light environments are the only context
- Do not use low-contrast text on dark backgrounds — tertiary `#64748b` is only for non-critical metadata (timestamps, metadata)
- Do not grey out errors — even "locked Pro" alerts use real data and are visible, just not deliverable
- Do not use the status colour palette anywhere in token composition bars — this is the most common design mistake in observability dashboards
