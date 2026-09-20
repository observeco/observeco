# ObserveCo Consulting Design System - Rationale

## What changes from the dark telemetry system
- Canvas: #0f172a navy -> #f7f6f3 bond paper; surface #1e293b -> #ffffff cards.
- Accent: #22c55e telemetry green -> #0e6e5c insight teal (differentiation brand).
- Typography: mono/Inter everywhere -> serif display (Iowan) for authority, Inter body, mono for identifiers.
- Shape: 4/8/12px -> 6/10/14/18px (softer, editorial).
- Elevation: heavy dark shadows -> hairlines + ink-tinted shadows.
- Motion: 100/150ms snap -> 120/200/320ms easeOutCubic, state-change only.
- Density: cockpit telemetry -> evidence-forward whitespace.

## Why light-first (the light-vs-dark call)
1. Consulting credibility: Bain, McKinsey, BCG lead with white. Dark reads dev tool; paper reads client analysis.
2. Print heritage: deliverables are read on paper and projected. Light survives both; dark neon dies on a projector.
3. Trust: high-contrast ink on paper signals certainty; glowing status lights signal systems to be watched.
4. Data as evidence: light canvas makes charts and tables read as report pages, the proof behind the strategy promise.
5. Audience: decision-makers skew 40+, and light reduces halation and eye strain.
Dark survives as [data-theme="dark"] for projection rooms only. Light is canonical.

## Old token -> new token mapping
| Old (tokens.css) | New (consulting-tokens.css) | Note |
|---|---|---|
| --bg #0f172a | --canvas #f7f6f3 | navy -> paper |
| --surface #1e293b / hover #253349 | --surface #ffffff / hover #f1f0ec | |
| --border #334155 / soft #273548 | --line #e4e2dc / soft #efeee9 | |
| --status-healthy #22c55e | #227a4e + tint | same semantics, AA on paper |
| --status-warning #eab308 | #9a6500 + tint | |
| --status-critical #ef4444 | #b42318 + tint | |
| --status-info #3b82f6 | #1d5fbf + tint | --meta merged here |
| --accent #22c55e | --insight #0e6e5c | brand accent: telemetry -> strategy |
| --fg / --fg-2 / --fg-3 | --ink / --ink-2 / --ink-3 | dark -> light text |
| --font-sans | --font-body (+ --font-display serif) | |
| --font-mono | --font-mono | kept, identifiers only |
| --radius-sm/md/lg 4/8/12 | 6/10/14 (+ --radius-xl 18) | softer editorial |
| --elev-raised (black .42) | --shadow-raised (ink .10) | tinted, print-flat |
| --focus-ring (accent mix) | --focus-ring (insight mix 30%) | |
| --motion-fast/base 100/150 | 120/200 (+ --motion-slow 320) | |
| --token-identity/skills/memory/tools/guidance | --seg-steel/slate/rose/olive/terracotta | composition -> muted chart segments |
