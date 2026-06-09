"""ObserveCo Daily License Validation — no_agent watchdog script.

Runs license validation and reports state. Silent when healthy.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observeco.license import status

s = status()
lines = [f"📋 ObserveCo License Report — {s['license_type'].upper()}"]
lines.append(f"  Plan: {s['plan']}")
lines.append(f"  Pro features: {'✅ Active' if s['is_pro'] else '❌ Disabled'}")

if s['is_in_grace']:
    lines.append("  ⚠️ Grace period active — past due")
elif s['has_trial']:
    lines.append(f"  Trial days remaining: {s['trial_days_remaining']}")
if s['validation_stale']:
    lines.append("  ⚠️ Validation stale — revalidate needed")

print("\n".join(lines))
