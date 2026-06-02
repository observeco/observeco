# Experience Gap 2026-05-30: Spec-to-Implementation Fidelity

**Status:** ✅ Resolved (same day)
**Trigger:** Sean clicked "See details" on an agent card and found the dashboard didn't match what the master plan described.
**Root cause:** The master plan (§3.2-3.6) described rich drill-down modals with 4-5 sections each. The implementation rendered minimal versions. The spec used "see kanban tasks" caveats, but the reader read the spec as the contract.

## What the Spec Said vs What Rendered

### Health Tab (`_detail_health_tab`)

| Section | Spec (§3.2) | Before fix | After fix |
|---------|------------|------------|-----------|
| Pulse timeline | 48 dots with legend (🟢🟡🔴) | ~24 raw dots, no legend | 48 dots with color legend |
| Annotated timeline | Time · Status · What happened table with error categorization | Raw error list, no table format | Proper table: Time column, Status column (🔴/🟡 with label), Message column |
| Summary + Verdict | Categorized plain-English summary (timeouts, connection refused, etc.) + verdict | Not present | 5-category classification with per-type explanation + status-adaptive verdict |
| Latest check | Time · Result · Latency table | Not present | Table with result badges (✅/🟡/🔴) and latency |
| Framework label | None needed | "Agent Framework" section with capitalized framework | Removed (not in mockup) |
| Circuit info | Compact guard status | Full circuit detail section | Compact guard section with just status + cooldown |

### Guard Tab (new: `_detail_guard_tab`)

| Section | Spec (§3.3) / Mockup | Before fix | After fix |
|---------|----------------------|------------|-----------|
| Status | "🔴 Guard is STOPPED" or "✅ Guard is OK" with explanation | Not a dedicated tab — was inline in Health | First-class tab with status + explanation |
| Failure trigger timeline | Time · (icon) · What happened table with summary | Raw error list in Health | Proper table with plain-English failure summary |
| What the guard does | Plain English explanation of guard mechanics | Not present | Paragraph explaining 3-failure trip, cooldown, auto-retry |
| Settings | Failures before stop · Cooldown period · Auto-retry | Not present | Settings table with active cooldown timer when tripped |

### Errors Tab (new: `_detail_errors_tab`)

| Section | Spec (§3.6) / Mockup | Before fix | After fix |
|---------|----------------------|------------|-----------|
| Timeline table | Time · What happened with color coding | Raw list in Health | Proper table with severity-colored messages |
| Verdict | Plain English per error count range (0/1/2+) | Not present | Three-tier verdict: clean/transient/ongoing problem |
| Pro upsell | Locked history preview card | Not present | Dashed-border preview: "🔒 More history unlocks patterns" |

## Why This Happened

The master plan was written with rich detail for all 3 drill-downs (Health, Guard, Errors). But when the dashboard was first built, only the Health tab was implemented, and at a bare-minimum level. The code had the data (pulse dots, errors, circuit state) but not the structured presentation.

The Guard and Errors tabs didn't exist at all — clicking those rows opened a static placeholder modal with no backend call.

## Reconciliation Rule (Codified)

When the master plan and mockup both describe a feature with the same level of detail, the most detailed version is the contract. "See kanban tasks" caveats mean the feature isn't built yet — not that the spec is aspirational. If a feature appears in the spec with full section-by-section detail, it should ship at that level, not at a minimal version.

## Files Changed

| File | Change |
|------|--------|
| `server.py:770-838` | Health tab: 4 sections — pulse timeline (48 dots + legend), annotated timeline table, categorized summary + verdict, latest check |
| `server.py:1028-1104` | New Guard tab: status, failure timeline, explanation, settings |
| `server.py:1107-1145` | New Errors tab: timeline, verdict, Pro upsell |
| `server.py:760-766` | Route handler: `guard` and `errors` tab routing added |
| `server.py:1616-1630` | Card clicks: wired from static `openModal()` to live `loadTab()` |
| `templates/index.html:1171-1188` | New `loadTab()` JS: fetches backend endpoint per tab |
