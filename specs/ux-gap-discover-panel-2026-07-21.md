# UX Audit: Discover Panel v2 — Live Walkthrough Findings

**Date:** 2026-07-21
**Surface:** Discover panel (click "... gaps" badge on Fleet tab)
**Instance:** localhost:9122

## What the user experiences

1. **Clicks "... 119 gaps" badge** → panel opens as full-width overlay covering 31% of viewport
2. **Sees "What's new 0" as the active tab** — the badge said 119, the tab says 0. Immediate cognitive dissonance.
3. **Sees two collapsed sections**: "Never seen 119" and "Learning 0 skills" — no content visible without clicking
4. **Clicks "Never seen"** → 119 items explode into view. Still a firehose, just with prettier styling.
5. **Clicks "Learning" tab** → empty state with brain emoji: "No prevention skills yet."
6. **Tries to click an item** → nothing happens. Items have no onclick handler. Only the "+ Add" button works.
7. **Tries "Add all"** → nothing happens. Button has no handler.
8. **Tries "Dismiss all seen"** → nothing happens. Button has no handler.
9. **Clicks "Everything" tab** → same view as "What's new" — no difference because all items are classified the same way.

## Root causes

| Problem | Root cause |
|---------|-----------|
| "What's new 0" when badge says 119 | `_classify_gaps()` puts everything in `never_seen` — no history/dismiss tracking exists |
| Sections collapsed by default | "Never seen" section has `expanded=False` in `_render_section()` |
| "Add all" / "Dismiss all" do nothing | No HTMX or JS handlers wired |
| Items not clickable | No `onclick` on `.item` — only the button works |
| "Everything" = "What's new" | Same classification, same rendering |
| Full-width overlay | CSS `left:0; right:0; width:100%` — no max-width constraint |
| Learning tab always empty | `prevention_skills` table exists but has 0 rows in live DB |

## What needs to change

### P0 — Make the panel useful immediately (no backend changes)

1. **Remove "What's new" tab** — it shows 0 and confuses. Default to "Everything" since that's the only tab with data.
2. **Default "Never seen" to expanded** — the user clicked the badge to see gaps, show them.
3. **Wire "Add all" button** — HTMX POST to batch-add all gaps in the section.
4. **Wire "Dismiss all" button** — HTMX POST to dismiss all (store in a `dismissed_gaps` table).
5. **Make items clickable** — clicking an item opens the agent profile modal (same as clicking the name in the fleet grid).
6. **Limit "Never seen" to first 20 items** with "Show all 99 more" link — 119 items is still a firehose.

### P1 — Learning tab needs real data

7. **Seed prevention_skills** — the table exists but is empty. Either the L3 loop hasn't run or the data isn't being written.
8. **Show meaningful empty state** — "No prevention skills yet" with a link to enable the learning loop.

### P2 — Classification needs history

9. **Add `dismissed_gaps` table** — track which gaps the user has dismissed, how many times, and when.
10. **Add `gap_history` table** — track when a gap was first seen, last seen, and if its status changed.
11. **Use history to populate "What's new"** — gaps that have never been seen before, or whose status changed.

## Effort

| Item | Effort | Type |
|------|--------|------|
| Remove "What's new" tab, default to "Everything" | 5 min | Template |
| Default "Never seen" to expanded | 1 line | API |
| Wire "Add all" button | 15 min | API + template |
| Wire "Dismiss all" button | 30 min | API + DB migration |
| Make items clickable | 5 min | Template |
| Limit "Never seen" to 20 + "Show all" | 10 min | API |
| Seed prevention_skills | Investigate | Ops |
| Better empty state for Learning | 5 min | Template |
| dismissed_gaps table + history | 1h | DB + API |
