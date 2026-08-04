# Value-Unit Contract — Anomalies Inbox: Signal-Cleanup Card (P0.0)

**Spec source:** mockups/anomalies-inbox-v2.html (P0.0 card) + obs-spec-092 §3.5/§4
**Status:** Live — this is the value unit the inbox cleanup card must satisfy.

---

## The value unit

The inbox renders a **Signal Cleanup card** when the fleet contains
misclassification that would otherwise inflate the alert count. The card is the
difference between an inbox and a rail: it names the fix, its blast radius, and
an Apply button — and it disappears when the fleet is clean.

**User does:** sees "Signal cleanup available → 29 critical alerts become 2",
reads the named fixes, checks which to apply, clicks Apply. When nothing is
misclassified, the card is absent (the feed alone is honest).

**The sentence the feature must produce:** `Signal cleanup available` +
`applies → {N} critical alerts become {M}` (or the equivalent honest count).

## Fixture → output table

The card renders iff `_detect_cleanup()` returns a non-empty set. Detection is
deterministic, read-only, based on the same queries the Apply endpoints mutate:

| Fixture (DB state) | Detection result | Card renders? |
|---|---|---|
| profile-class agents probed as dead (kanban/workspace/spectrum class='profile') | `["reclassify_profiles"]` | Yes |
| test entities present (class='test') | `["exclude_tests"]` | Yes |
| stale tripped circuits >7d | `["reset_stale_circuits"]` | Yes |
| multiple of the above | all present | Yes |
| all clean (no profile/test/stale-circuit misclassification) | `[]` | **No — feed only** |

The distinguishability test: a card that renders for a clean fleet, OR hides
for a misclassified fleet, fails.

## Acceptance test (write first)

`tests/test_inbox_cleanup_card.py`:
- `_detect_cleanup()` returns `[]` when DB has no profile/test/stale-circuit
  misclassification (current prod state).
- `_detect_cleanup()` returns the expected fix IDs when each misclassification
  class is injected.
- `get_inbox` HTML contains the cleanup card when detection is non-empty and
  does NOT contain it when detection is empty.
