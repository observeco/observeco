# Changelog

All notable changes to ObserveCo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-11

### Added
- **Token Analytics Dashboard** — Chart.js time-series, breakdown, summary cards, drill-down modal
- **Unified Action Log** — Single table for all ObserveCo actions (compression, healing, drift)
- **Migration Infrastructure** — Backup before migrations, row count verification, stranded table recovery
- **Data Health Check** — `observeco doctor run --data-health` command
- **GS-019 Standard** — Data & Observability Continuity principles
- **Compression Labels** — Honest "Already condensed" labels instead of 0%

### Fixed
- Compression 0% bug — skills showing 0% now show "Already condensed"
- Static/upsell data that looked real on Brain Analysis
- Missing `</div>` in Alerts tab + onboarding overlay
- Onboarding overlay skipping when agents exist

### Changed
- Brain Analysis uses composition-based savings
- Potential savings uses real fleet-wide compress_log averages
- ~~Skill Audit~~ — merged into Brain Analysis

## [0.1.0] - 2026-05-29

### Added
- Initial release
- Agent observability dashboard
- Skill compression (Lite/Full)
- Auto-heal for common agent issues
- Pulse monitoring
- Risk engine
- Drift alerts
- Pro tier gating
