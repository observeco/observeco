"""Shared thresholds and constants for ObserveCo.

Single source of truth for values used across multiple subsystems.
Each subsystem can import what it needs and override at runtime if needed.
"""

# ── Drift thresholds ─────────────────────────────────────────────────────
# Enforcer: early warning when drift exceeds this
DRIFT_WARN_PCT = 5.0

# Enforcer / Chisel: critical drift threshold
DRIFT_CRITICAL_PCT = 10.0

# Dashboard: UI display threshold (more lenient for visual alerts)
DRIFT_DISPLAY_PCT = 15.0

# ── Token thresholds ─────────────────────────────────────────────────────
# (imported from dashboard.config — those are the SSOT for token display)
