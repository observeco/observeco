# Durable Per-Agent Efficiency Storage (Option B)

**Status:** Draft
**Spec:** obs-spec-084-durable-efficiency-storage.md
**Owner:** Main
**Estimated effort:** ~2h (schema + capture + backfill + API + frontend)

---

## §1 Problem

The Efficiency tab in the Agent Detail modal and the proposed fleet-card efficiency row both read from Hermes session files (`~/.hermes/sessions/*.jsonl`). This has three problems:

1. **Session files are rotated monthly** — the most recent file is June 16, a month stale. The Efficiency tab shows old data.
2. **Session files carry no agent identity** — the tab shows fleet-wide data, not per-agent. The card can't show per-agent scores.
3. **File scanning is slow** — `_list_recent_sessions()` scans up to 500 files, parsing each. This blocks the fleet page render.

## §2 Solution

A new `efficiency_scores` table in the ObserveCo DB that stores per-session efficiency results permanently. A capture hook writes to it whenever `compute_efficiency()` is called. A backfill script populates it from existing data. The fleet card and detail modal read from the DB — fast, per-agent, never stale.

## §3 Schema

```sql
CREATE TABLE IF NOT EXISTS efficiency_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    session_id TEXT NOT NULL,
    archetype TEXT NOT NULL,          -- debug/research/feature/ops/edit/unknown
    score INTEGER,                    -- 0-100 efficiency score, NULL if noop
    effectiveness_score INTEGER,      -- 0-100 effectiveness score, NULL if unclear
    turn_count INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    UNIQUE(session_id, agent_name)    -- one score per session per agent
);
CREATE INDEX IF NOT EXISTS idx_efficiency_agent ON efficiency_scores(agent_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_efficiency_archetype ON efficiency_scores(archetype);
```

## §4 Capture Hook

In `compute_efficiency()` in `metrics.py` — after computing the score, write to `efficiency_scores` via a fire-and-forget DB call. This is called from the existing `/api/efficiency/sessions` endpoint and the detail modal's Efficiency tab. The write is non-blocking (separate connection, no rollback on failure).

**ponytail:** The hook fires on every `compute_efficiency()` call, including the session-list page. This means every time the Efficiency tab loads, it re-writes the same scores. The `UNIQUE(session_id, agent_name)` constraint makes this an idempotent upsert. Upgrade: move to a dedicated capture cron that runs once per session end.

## §5 Backfill

A CLI command `observeco efficiency backfill` that:
1. Scans all session files (`~/.hermes/sessions/*.jsonl`)
2. For each session, looks up `token_logs` by `session_id` to get `agent_name`
3. Computes efficiency + effectiveness
4. Stores to `efficiency_scores`

**ponytail:** Session files don't carry agent_name. The backfill joins on `token_logs.session_id` to find the agent. Sessions with no matching token_logs row are stored with `agent_name='unknown'`. Upgrade: add agent_name to session metadata when Hermes writes the file.

## §6 API

### `GET /api/efficiency/agent-summary/{agent_name}`

Returns HTML partial for the fleet card row:

```html
<div class="crow tappable" onclick="htmx.ajax('GET', '/api/fleet/modal/{name}?tab=efficiency', {target:'#modalContainer', swap:'innerHTML'})">
  <span class="row-label">Efficiency</span>
  <span class="row-val" style="color:var(--accent)">57</span>
  <span class="row-sub">debug:62 · feature:51 · ops:89 <span class="row-chev">▸</span></span>
</div>
```

Empty state (no data):
```html
<div class="crow" style="cursor:default;">
  <span class="row-label">Efficiency</span>
  <span class="row-val" style="color:var(--fg-3)">—</span>
  <span class="row-sub" style="color:var(--fg-3)">no session data</span>
</div>
```

The endpoint queries `efficiency_scores` grouped by archetype, returning the average score per archetype and overall average for the last 10 sessions.

## §7 Frontend

### Fleet card row (class="agent" only)

Added after the Errors row, before the Brain row. Lazy-loaded via htmx:

```html
<div class="crow" id="eff-row-{name}"
     hx-get="/api/efficiency/agent-summary/{name}"
     hx-trigger="load"
     hx-target="this"
     hx-swap="outerHTML">
  <span class="row-label">Efficiency</span>
  <span class="row-val" style="color:var(--fg-3)">…</span>
  <span class="row-sub">loading…</span>
</div>
```

### Detail modal Efficiency tab

Already exists — it reads from session files. After backfill, it should read from `efficiency_scores` instead. **Deferred to Phase 2** — the current tab works (just shows stale data). The fleet card is the priority.

## §8 Files Changed

| File | Change | Lines |
|------|--------|-------|
| `src/observeco/db.py` | Add `efficiency_scores` table to schema + `get_efficiency_summary()` + `save_efficiency_score()` | ~40 |
| `src/observeco/efficiency/metrics.py` | Add capture hook in `compute_efficiency()` | ~15 |
| `src/observeco/efficiency/api.py` or new file | `GET /api/efficiency/agent-summary/{name}` | ~30 |
| `src/observeco/dashboard/routes/fleet.py` | Add efficiency row to agent card template | ~10 |
| `src/observeco/cli.py` | `observeco efficiency backfill` command | ~30 |
| **Total** | | **~125** |

## §9 Success Metrics

| Metric | Target | How measured |
|--------|--------|-------------|
| Fleet card load time | <500ms from page render to efficiency data visible | Browser DevTools network tab — htmx GET to `/api/efficiency/agent-summary/{name}` |
| Backfill coverage | ≥90% of existing sessions stored with a known agent_name | `SELECT COUNT(*) FROM efficiency_scores WHERE agent_name != 'unknown'` / total sessions |
| Per-agent accuracy | Every agent with session data shows its own scores, not fleet-wide | Spot-check: open kepler's fleet card, verify scores differ from main's |
| Capture reliability | Every `compute_efficiency()` call produces a DB row | `SELECT COUNT(*) FROM efficiency_scores` grows with each Efficiency tab load |

## §10 Pro/Free

All free. Efficiency scoring is core product value, not upsell.

## §10 Deferred

- **Detail modal reads from DB** — currently reads session files. After backfill, switch to `efficiency_scores` query.
- **Capture cron** — dedicated cron that runs at session end instead of inline hook.
- **Trend chart** — per-agent efficiency over time.
