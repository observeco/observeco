# obs-spec-082: Coverage Tab — Replace Discover Panel

**Status:** 🔴 Spec — not yet implemented
**Product:** ObserveCo
**Depends on:** obs-spec-079 (Discover gap scanner), obs-spec-081 (L3 Learning Loop)
**Replaces:** Discover dropdown panel (`#discoverPanel` overlay)

## §1 Problem

The Discover panel is a fixed-position overlay that tries to be four things at once: a badge count, a browsable gap list, a bulk-action bar, and a learning-loop analytics dashboard. Every interaction fix broke another because the overlay container is wrong for browsable lists with per-row actions. After ~10 rounds of patches (concatenation, disappearing panel, OOB swap conflicts, event bubbling, z-index, scrolling overlap), the panel still has UX issues and is blocking launch.

**Root cause:** Overlays work for quick actions (confirm, filter, search). They don't work for scrolling through 119 items with per-row buttons, tab switching, and HTMX state management. The dashboard already has a correct pattern for this — tabs with tables (Fleet, Alerts, Error Timeline).

## §2 What Exists

| Component | Location | Status |
|-----------|----------|--------|
| Discover badge | `index_new.html` line 28 — `#discoverBadge` | Shows "N gaps" pill in header |
| Discover panel | `index_new.html` line 32 — `#discoverPanel` overlay | Fixed-position 480px dropdown, collapsed by default |
| Gap scanner | `src/observeco/discover/scanner.py` — `scan_cached()`, `add_gap()` | Scans cron jobs, running processes, health checks. Caches 5min. |
| Panel API | `src/observeco/discover/api.py` — `/api/discover/panel` | Returns HTML partial with gap list, mode tabs, learning section |
| dismissed_gaps table | `db.py` Migration 67 | `CREATE TABLE dismissed_gaps (gap_name TEXT PRIMARY KEY, dismissed_at TEXT)` |
| prevention_skills table | `db.py` | Exists, 0 rows. L3 loop not yet active. |
| Tab system | `app.js` — `switchTab(tab, btn)` | `tabMap` object maps tab names to `#tabXxx` divs. Adding a tab = add nav span + tabMap entry + tab-content div. |
| Learning section | Inside `/api/discover/panel` response | Stat cards (skills created, times applied, cost saved, deprecated) + skill list. Currently empty. |

## §3 Architecture

### 3.1 Kill the overlay

Remove entirely:
- `#discoverPanel` div from `index_new.html`
- `.discover-panel` CSS block from `observeco-dashboard.css`
- `toggleDiscover()` JS function
- `syncBadgeCount()` JS function
- `htmx:afterOnLoad` handler for `/api/discover/panel`
- The `hx-get`, `hx-target`, `hx-swap`, `hx-trigger` attributes from `#discoverBadge`

### 3.2 Badge becomes a nav link

The badge stays in the header but becomes a navigation trigger, not an overlay toggle:

```html
<div class="discover-badge" id="discoverBadge" onclick="switchTab('coverage', this)" title="See what you're not monitoring">
  <span class="dot"></span><span id="discoverCount">…</span> gaps
</div>
```

Badge count is populated by a lightweight JSON endpoint (`/api/discover/count`) on page load and refreshed every 5min via `setInterval`. No HTMX, no HTML parsing, no OOB swaps.

### 3.3 New Coverage tab

Add to MONITOR group in nav, between Fleet and Alerts:

```html
<span class="nav-tab clickable" data-tab="coverage">Coverage</span>
```

Tab content div:

```html
<div id="tabCoverage" class="tab-content">
  <div id="coverageContainer" hx-get="/api/discover/coverage" hx-trigger="revealed once" hx-target="this" hx-swap="innerHTML">
    <div class="loading">Loading coverage...</div>
  </div>
</div>
```

Add to `tabMap` in `app.js`:
```js
'coverage': 'tabCoverage',
```

Add HTMX trigger in `switchTab()`:
```js
if (tab === 'coverage') htmx.ajax('GET', '/api/discover/coverage' + _q, {target: '#coverageContainer', swap: 'innerHTML'});
```

### 3.4 Coverage page endpoint

`GET /api/discover/coverage` — returns full HTML page content (not a partial overlay).

Layout — **Monitor** surface, density over decoration:

```
┌─────────────────────────────────────────────────────────┐
│  Coverage                                               │
│  119 untracked · 0 dismissed · Updated 22:32            │
├─────────────────────────────────────────────────────────┤
│  [Search gaps...]    [All] [Running] [Down] [Dismissed] │
├─────────────────────────────────────────────────────────┤
│  Name                          Framework   Status  Act  │
│  ─────────────────────────────────────────────────────  │
│  Daily News Digest             cron        ●       + ✕  │
│  PA Sweep - hourly             cron        ●       + ✕  │
│  Travel Deal Scout — 5:30pm    cron        ●       + ✕  │
│  ...                                                    │
│  Show all 99 more ▾                                     │
├─────────────────────────────────────────────────────────┤
│  ── Learning ────────────────────────────────────────── │
│  0 skills · 0 applied · $0.00 saved                     │
│  No prevention skills yet. Enable with                  │
│  `observeco heal --learn`.                              │
└─────────────────────────────────────────────────────────┘
```

### 3.5 Learning section — inline, not tabbed

The Learning section lives at the bottom of the Coverage page as a bordered section — not a separate tab. It's contextual: "what the system learned about coverage gaps." If it grows beyond stat cards + a short skill list, it can graduate to its own tab later.

## §4 Implementation

### 4.1 Files to modify

| File | Change |
|------|--------|
| `src/observeco/dashboard/templates/index_new.html` | Remove `#discoverPanel`, `toggleDiscover()`, `syncBadgeCount()`, `htmx:afterOnLoad` handler. Change `#discoverBadge` to `onclick="switchTab('coverage', this)"`. Add `<span class="nav-tab clickable" data-tab="coverage">Coverage</span>` to MONITOR nav group. Add `<div id="tabCoverage" class="tab-content">` with `#coverageContainer`. |
| `src/observeco/dashboard/static/js/app.js` | Add `'coverage': 'tabCoverage'` to `tabMap`. Add `if (tab === 'coverage') htmx.ajax(...)` to `switchTab()`. Add `setInterval` to refresh `#discoverCount` from `/api/discover/count` every 5min. |
| `src/observeco/dashboard/static/observeco-dashboard.css` | Remove `.discover-panel` and all `.discover-panel *` rules (lines ~2211-2400). Keep `.discover-badge` rules. Add `#tabCoverage` table styles — reuse existing `.tab-content` patterns. |
| `src/observeco/discover/api.py` | Add `GET /api/discover/coverage` endpoint returning full page HTML. Add `GET /api/discover/count` returning `{"count": N}` JSON. Keep `/api/discover/add`, `/api/discover/add-all`, `/api/discover/dismiss`, `/api/discover/dismiss-all` — change `hx-target` to `#coverageContainer` with `innerHTML` swap. Remove `/api/discover/panel` endpoint. |
| `src/observeco/discover/scanner.py` | No changes — `scan_cached()` and `add_gap()` stay as-is. |

### 4.2 New endpoints

| Endpoint | Method | Returns | Purpose |
|----------|--------|---------|---------|
| `/api/discover/coverage` | GET | HTML (full page) | Coverage tab content — gap table + learning section |
| `/api/discover/count` | GET | `{"count": N}` | Badge count refresh (lightweight JSON) |

### 4.3 Modified endpoints

| Endpoint | Change |
|----------|--------|
| `/api/discover/add` | Return `_render_coverage()` instead of `_render_panel()`. `hx-target="#coverageContainer"`. |
| `/api/discover/add-all` | Same. |
| `/api/discover/dismiss` | Same. |
| `/api/discover/dismiss-all` | Same. |
| `/api/discover/panel` | **Remove.** Replaced by `/api/discover/coverage`. |

### 4.4 HTML structure for coverage page

```python
def _render_coverage() -> str:
    """Return coverage page HTML as a plain string."""
    gaps = scan_cached()
    classified = _classify_gaps(gaps)
    active = classified["never_seen"]
    dismissed_count = classified["dismissed_count"]

    # Gap table
    table_html = _render_gap_table(active, limit=20)

    # Learning section (inline, not tabbed)
    learning_html = _get_learning_html()

    return f"""
  <div class="coverage-header">
    <h2>Coverage</h2>
    <span class="coverage-meta">{len(active)} untracked · {dismissed_count} dismissed · Updated {datetime.now().strftime('%H:%M')}</span>
  </div>
  <div class="coverage-toolbar">
    <input type="text" placeholder="Search gaps..." class="coverage-search" id="coverageSearch">
    <div class="coverage-filters">
      <button class="filter-btn active">All</button>
      <button class="filter-btn">Dismissed</button>
    </div>
  </div>
  <div class="coverage-bulk">
    <button class="bulk-btn primary" hx-post="/api/discover/add-all"
      hx-vals="js:{{names: Array.from(document.querySelectorAll('#coverageTable .gap-row')).map(function(r){{return r.dataset.name}})}}"
      hx-target="#coverageContainer" hx-swap="innerHTML">+ Add all</button>
    <button class="bulk-btn" hx-post="/api/discover/dismiss-all"
      hx-target="#coverageContainer" hx-swap="innerHTML">Dismiss all</button>
  </div>
  <div id="coverageTable" class="coverage-table">
    {table_html}
  </div>
  <div class="coverage-learning">
    {learning_html['html']}
  </div>
"""
```

### 4.5 Gap table rows

Each row is a `<div class="gap-row" data-name="...">` with:

| Column | Content | Width |
|--------|---------|-------|
| Name | Gap name (bold) | flex-grow |
| Framework | `cron` / `custom` / etc. | 80px |
| Status | `●` dot (yellow = untracked) | 24px |
| Actions | `+ Add` button, `✕ Dismiss` button | auto |

Buttons use `hx-target="#coverageContainer" hx-swap="innerHTML"` — same single-swap pattern that works. No overlay, no OOB, no event bubbling.

## §5 Edge Cases

| Case | Behavior |
|------|----------|
| No gaps | Show "✅ Everything running is tracked" empty state. Badge shows "0 gaps" with green dot. |
| All gaps dismissed | Show "All gaps dismissed. [Undo]" with link to clear dismissed_gaps table. |
| Gap name has apostrophe (e.g. "Sean's Reply Capture") | `hx-vals` uses `js:` syntax — no HTML attribute escaping issues. |
| Gap name has HTML special chars | `_html_escape()` already applied in `_render_gap_table`. |
| Learning table empty | Show CLI hint: "No prevention skills yet. Enable with `observeco heal --learn`." |
| User clicks badge while on Coverage tab | `switchTab('coverage', this)` — tab is already active, no-op. |
| User navigates away from Coverage tab | Tab content stays in DOM (`.tab-content` class toggle). No state loss. |
| Mobile (≤768px) | Table becomes stacked rows. Bulk bar wraps. Search full-width. |

## §6 Pro Gating

| Feature | Free | Pro |
|---------|------|-----|
| View gap count (badge) | ✅ | ✅ |
| View Coverage tab | ✅ | ✅ |
| Add individual gap | ✅ | ✅ |
| Dismiss individual gap | ✅ | ✅ |
| Add all / Dismiss all (bulk) | ❌ | ✅ |
| Learning section | ✅ (view) | ✅ (view + `--learn` flag) |

## §7 Success Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Badge shows "N gaps" count, updates every 5min | `curl /api/discover/count` returns JSON `{"count": N}`. Browser: badge text matches. |
| 2 | Clicking badge navigates to Coverage tab | Browser: `switchTab('coverage')` called. `#tabCoverage` has `.active` class. |
| 3 | Coverage tab shows gap table with real data | `curl /api/discover/coverage` returns HTML with gap rows. Browser: rows visible. |
| 4 | "+ Add" button registers agent, table refreshes | Click "+ Add" → `POST /api/discover/add` → `#coverageContainer` innerHTML swaps → row disappears from list. |
| 5 | "✕" button dismisses gap, table refreshes | Click "✕" → `POST /api/discover/dismiss` → `#coverageContainer` innerHTML swaps → row disappears. |
| 6 | "+ Add all" registers all visible gaps | Click → `POST /api/discover/add-all` → table refreshes with fewer rows. |
| 7 | "Dismiss all" dismisses all visible gaps | Click → `POST /api/discover/dismiss-all` → table shows empty state. |
| 8 | No overlay, no fixed-position panel, no z-index | `grep -r "discover-panel" src/` returns 0 results. |
| 9 | No event bubbling issues | Click any button → tab stays active, container stays in place. |
| 10 | Learning section shows at bottom of Coverage page | `curl /api/discover/coverage` HTML contains `coverage-learning` div. |
| 11 | Empty state when no gaps | Dismiss all → page shows "✅ Everything running is tracked". |
| 12 | All existing tests pass | `pytest tests/` — 631 passed, 0 failed. |
| 13 | Headless click-through: add, dismiss, bulk add, bulk dismiss | Playwright/curl: each action returns 200, container re-renders, no JS errors. |

## §8 Migration

1. Implement new endpoints (`/api/discover/coverage`, `/api/discover/count`)
2. Add Coverage tab to template + JS
3. Update badge to use `switchTab('coverage', this)`
4. Update add/dismiss endpoints to return `_render_coverage()`
5. Remove old panel code (endpoint, CSS, JS, template)
6. Run tests
7. Verify on port 9122

## §9 What This Eliminates

| Problem | Why it's gone |
|---------|--------------|
| Panel disappears on click | No overlay — tab content is in normal document flow |
| Badge count goes null | Count comes from JSON endpoint, not HTML parsing |
| Buttons don't work | All buttons target `#coverageContainer` with `innerHTML` — one swap, one target |
| Scrolling overlaps | No `position: fixed` — tab content scrolls with page |
| Tab clicks close panel | No overlay to close — `event.stopPropagation()` not needed |
| Concatenation bug | Table rows have proper column structure with padding |
| OOB swap conflicts | No OOB — badge count is separate JSON poll |
| 10 rounds of patches | The container is wrong. This replaces the container. |