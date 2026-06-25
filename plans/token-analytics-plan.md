# Revised Plan: Token Analytics Dashboard

**Date:** 2026-06-21
**Status:** Revised plan (not yet implemented)
**Based on:** obs-spec-020, existing code review

---

## §1 Current State Assessment

### What already exists and works

| Component | Status | Notes |
|-----------|--------|-------|
| `token_logs` table (DB schema) | ✅ Complete | Migrations 7, 17, 18, 23 — all columns exist |
| `db.log_token_turn()` | ✅ Complete | Accepts all fields including input/output/cache/source |
| `token_analytics.py` aggregation | ✅ Complete | `get_chart_data()`, `get_breakdown()`, `get_system_prompts()` — 429 lines, fully functional |
| `tokens.py` helpers | ✅ Complete | `log_token_turn()`, `get_token_summary()`, `get_daily_trends()` |
| SDK patcher classes | ✅ Complete | OpenAI, Anthropic, LangChain patchers — all written |
| SDK patcher registry | ✅ Complete | `apply_all_patchers()`, `apply_patcher(name)` |
| SDK detector | ✅ Complete | `detect_sdks()` — scans installed packages |
| CLI `observeco sdk install` | ✅ Complete | Manual activation command |
| Chart.js bundle | ✅ Static file | `/static/chart.umd.min.js` — already in repo |
| Watch daemon token logging | ✅ Complete | `watch.py` lines 317-340 — logs trim results to `token_logs` |
| OTel listener | ✅ Complete | Standalone server on port 4318 |
| Agent detail "tokens" tab | ✅ Complete | `_detail_tokens_tab()` — CSS stacked bars per-agent |
| `loadTokenAnalytics()` JS | ⚠️ Exists but wrong | Fetches `/api/tokens/analytics` (HTML endpoint), expects `taInitChart()` |

### What's missing or wrong

| Component | Status | Notes |
|-----------|--------|-------|
| `/api/tokens/chart` JSON endpoint | ❌ Missing | `get_chart_data()` never called from server.py |
| `/api/tokens/breakdown` JSON endpoint | ❌ Missing | `get_breakdown()` never called from server.py |
| `/api/tokens/system-prompts` JSON endpoint | ❌ Missing | `get_system_prompts()` never called from server.py |
| `/api/tokens/analytics` HTML endpoint | ❌ Wrong | Returns CSS stacked bars, not Chart.js. Spec calls for Chart.js with zoom/pan |
| Fleet-level Token Analytics tab UI | ❌ Missing | Tab placeholder exists in HTML, but no Chart.js chart, filter bar, breakdown table, or drill-down modal |
| SDK patcher auto-activation | ❌ Missing | No startup hook calls `apply_all_patchers()` |
| DB has data | ❌ Empty | 0 rows in `token_logs` — pipeline not running |

---

## §2 Revised Plan

### Principle: Minimum viable, no new abstractions

The aggregation layer is already built and correct. The Chart.js bundle is already in the repo. The SDK patchers are written. The only real work is:

1. **Wire up 3 JSON API endpoints** (add ~15 lines to server.py)
2. **Replace the wrong HTML endpoint** with a proper Chart.js client-rendered tab (modify ~1 function in server.py + ~80 lines of JS in index.html)
3. **Activate SDK patchers at startup** (add ~3 lines to the dashboard startup path)
4. **Delete the wrong code** (remove the CSS stacked bar HTML endpoint)

That's it. No new files. No new dependencies. No new abstractions.

---

### §2.1 SDK Patcher Activation (non-intrusive)

**YAGNI check:** The patchers exist, the registry exists, the CLI command exists. The only missing piece is a startup hook. Do we need a complex plugin system? No. Do we need config flags? Not yet.

**Plan:**

1. In `server.py`, add a one-time call to `apply_all_patchers()` at startup, wrapped in a try/except so failure doesn't crash the dashboard:

```python
# ponytail: applies all SDK patchers at dashboard startup.
# If no SDKs are installed, this is a no-op (each patcher's apply()
# catches ImportError and returns False).
# Upgrade path: when per-user config exists, gate behind
# observeco.yml setting like `auto_instrument: true`.
@app.on_event("startup")
async def _startup_apply_patchers():
    try:
        from observeco.tracking.sdk.patcher_registry import apply_all_patchers
        results = apply_all_patchers()
        applied = [k for k, v in results.items() if v]
        if applied:
            logger.info("SDK patchers applied: %s", ", ".join(applied))
    except Exception:
        logger.debug("SDK patcher startup skipped", exc_info=True)
```

**Why this is non-intrusive:**
- Each patcher's `apply()` catches `ImportError` — if the SDK isn't installed, it's a silent no-op
- The outer try/except catches anything else — dashboard never crashes
- No proxy, no network interception, no config changes needed
- Works for ALL users regardless of which SDKs they have installed
- The patchers monkey-patch at import time, not at request time — zero overhead on non-LLM calls

**What about Hermes/OpenClaw integration?** The patchers log with `agent_name="openai-sdk"` etc. by default. When called from within an agent's process, the agent should set its own name. This is a future concern — for now, the data flows into `token_logs` and the dashboard shows it.

---

### §2.2 Chart API Endpoints

**YAGNI check:** The aggregation functions already exist. Do we need separate endpoints for chart, breakdown, and system-prompts? The spec says yes — they serve different UI components. But we can wire them up in one file with minimal code.

**Plan — add 3 routes to `server.py`:**

```python
@app.get("/api/tokens/chart")
async def api_tokens_chart(
    agent: str = "", provider: str = "", workflow: str = "", service: str = "",
    from_ts: int = 0, to_ts: int = 0,
    granularity: str = "hour", component: str = "total",
    include_source: str = "",
):
    from observeco.tracking.token_analytics import get_chart_data
    return JSONResponse(get_chart_data(
        agent=agent, provider=provider, workflow=workflow, service=service,
        from_ts=from_ts, to_ts=to_ts,
        granularity=granularity, component=component,
        include_source=include_source,
    ))

@app.get("/api/tokens/breakdown")
async def api_tokens_breakdown(
    dimension: str = "agent", from_ts: int = 0, to_ts: int = 0,
    include_source: str = "",
):
    from observeco.tracking.token_analytics import get_breakdown
    return JSONResponse(get_breakdown(
        dimension=dimension, from_ts=from_ts, to_ts=to_ts,
        include_source=include_source,
    ))

@app.get("/api/tokens/system-prompts")
async def api_tokens_system_prompts(
    from_ts: int = 0, to_ts: int = 0, limit: int = 20,
):
    from observeco.tracking.token_analytics import get_system_prompts
    return JSONResponse(get_system_prompts(
        from_ts=from_ts, to_ts=to_ts, limit=limit,
    ))
```

**What to delete:** The existing `/api/tokens/analytics` HTML endpoint (lines 3268-3348+ in server.py) that returns CSS stacked bars. It's the wrong approach — the spec calls for Chart.js.

**What to keep:** The existing `/api/tokens/summary`, `/api/tokens/trends`, `/api/tokens/log`, `/api/tokens/recent` endpoints — they serve the agent detail tab and are not in scope for replacement.

---

### §2.3 Chart.js UI Architecture

**YAGNI check:** Do we need a full SPA framework? No. The dashboard already uses htmx + inline JS. Chart.js is already bundled. The zoom/pan plugin is part of Chart.js 4.x (built-in via `options.plugins.zoom`). Do we need a separate JS file? No — inline in the template is fine for a single tab.

**Plan — modify `index.html`:**

1. **Replace the `loadTokenAnalytics()` function** to fetch JSON from `/api/tokens/chart` instead of HTML from `/api/tokens/analytics`, then render a Chart.js chart inline.

2. **Build the tab content in JS** (not server-rendered HTML):
   - Summary cards (4 stat cards from `response.summary`)
   - Chart.js time-series area chart (from `response.data`)
   - Filter bar (agent, provider, time range, granularity, component toggle)
   - Breakdown table (from `/api/tokens/breakdown`)
   - Drill-down modal (click data point → show turn details)

3. **Chart.js configuration:**
   - Type: `'line'` with `fill: true` for area effect
   - X-axis: time (parsed from `bucket_start` unix timestamps)
   - Y-axis: token count
   - Zoom/pan: built-in Chart.js zoom plugin (`options.plugins.zoom`)
   - Dark theme: match existing CSS variables

4. **Filter bar:**
   - Agent dropdown: populated from `/api/agents` (existing endpoint)
   - Provider dropdown: hardcoded (openai, anthropic, deepseek, ollama)
   - Time range: preset buttons (24h, 7d, 30d) + custom date range
   - Granularity: minute/hour/day buttons
   - Component toggle: total/identity/skills/memory/tools/guidance

5. **Breakdown table:**
   - Fetched from `/api/tokens/breakdown?dimension=agent`
   - Sortable columns (click header to sort)
   - Click row to filter chart

6. **Drill-down modal:**
   - Click data point on chart → show modal with turn details
   - Fetched from `/api/tokens/recent?agent=X&from_ts=Y&to_ts=Z`

**What to delete from index.html:**
- The `initTokenChart()` stub (lines 2465-2476) — it calls `taInitChart()` which doesn't exist
- The `renderTokenChart()` stub (lines 2478-2482) — deprecated
- The reference to `taInitChart` in `loadTokenAnalytics()` — replace with direct Chart.js rendering

**ponytail:** The chart is rendered client-side with inline JS. For a single tab this is fine. Upgrade path: if the dashboard grows more charts, extract to `/static/token-analytics.js`.

---

### §2.4 What Hermes Main Should Build vs Claude Code

| Task | Who | Why |
|------|-----|-----|
| Wire up 3 JSON endpoints in server.py | Hermes Main | ~15 lines, straightforward FastAPI |
| Add SDK patcher startup hook | Hermes Main | ~10 lines, one-time startup event |
| Delete wrong `/api/tokens/analytics` HTML endpoint | Hermes Main | Deletion, not construction |
| Rewrite `loadTokenAnalytics()` JS in index.html | Claude Code | ~80 lines of Chart.js + filter logic, better suited to LLM codegen |
| Build filter bar HTML/JS | Claude Code | DOM-heavy, iterative |
| Build breakdown table with sort | Claude Code | DOM-heavy, iterative |
| Build drill-down modal | Claude Code | DOM-heavy, iterative |
| Test with empty DB | Both | Hermes Main verifies endpoints return correct JSON; Claude Code verifies UI shows empty states |

**Rationale:** Hermes Main handles the backend wiring (small, precise changes). Claude Code handles the frontend (DOM manipulation, Chart.js config, event handling — the kind of code LLMs write well).

---

### §2.5 Testing Strategy

**YAGNI check:** Do we need a full test suite? No. The aggregation layer already has no tests. We need one runnable check per non-trivial logic change.

1. **API endpoint test** (one file, pytest, no fixtures):
   ```python
   # tests/test_token_analytics_api.py
   """One runnable check: endpoints return correct JSON structure with empty DB."""
   from fastapi.testclient import TestClient
   from observeco.dashboard.server import app
   
   client = TestClient(app)
   
   def test_chart_endpoint_returns_json():
       resp = client.get("/api/tokens/chart")
       assert resp.status_code == 200
       data = resp.json()
       assert "granularity" in data
       assert "data" in data
       assert "summary" in data
   
   def test_breakdown_endpoint_returns_json():
       resp = client.get("/api/tokens/breakdown?dimension=agent")
       assert resp.status_code == 200
       data = resp.json()
       assert "dimension" in data
       assert "data" in data
   
   def test_system_prompts_endpoint_returns_json():
       resp = client.get("/api/tokens/system-prompts")
       assert resp.status_code == 200
       data = resp.json()
       assert "data" in data
   ```

2. **SDK patcher startup test** (verify it doesn't crash):
   ```python
   def test_patcher_startup_noop_when_no_sdks():
       from observeco.tracking.sdk.patcher_registry import apply_all_patchers
       results = apply_all_patchers()
       # All should be False (no SDKs installed in test env)
       assert all(v is False for v in results.values())
   ```

3. **UI test** (manual or Playwright): Open dashboard, click Token Analytics tab, verify:
   - Empty state shows when DB is empty
   - Chart renders when data exists
   - Filters update chart
   - Click data point opens modal

**No test framework, no fixtures, no mocks.** Just `assert` statements that fail if the logic breaks.

---

### §2.6 Edge Cases & Empty States

| State | Behavior |
|-------|----------|
| DB empty (0 rows) | Chart shows "No token data yet" message. Summary cards show 0. Breakdown table shows "No data available." |
| DB has data but no matches for filters | Chart shows "No data matches your filters. Try widening the time range." |
| API error (5xx) | Chart shows "Server error. Check dashboard server status." with retry button |
| API timeout | Chart shows "Request timed out. Retrying..." with auto-retry (3 attempts, 2s delay) |
| Chart.js CDN/static fails | Fallback to simple HTML table with token data |
| Partial data (missing components) | Missing values default to 0. Chart shows available data with warning |
| Large dataset (>1000 points) | Aggregate to coarser granularity client-side |

---

## §3 Summary of Changes

### Files to modify:
1. **`src/observeco/dashboard/server.py`** — Add 3 JSON endpoints, add SDK patcher startup hook, delete wrong HTML endpoint (~+30 lines, -80 lines)
2. **`src/observeco/dashboard/templates/index.html`** — Rewrite `loadTokenAnalytics()` and related JS (~+100 lines, -20 lines)

### Files to create:
- **`tests/test_token_analytics_api.py`** — One runnable check file (~20 lines)

### Files to delete:
- None (the wrong HTML endpoint is in server.py, not a separate file)

### No new dependencies:
- Chart.js is already bundled at `/static/chart.umd.min.js`
- Chart.js zoom plugin is built into Chart.js 4.x
- No npm, no webpack, no build step

---

## §4 Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| SDK patcher crashes an agent process | Low | Each patcher wraps in try/except. `_log_token_turn()` catches all exceptions. Dashboard startup hook is isolated. |
| Chart.js zoom plugin not bundled | Low | Chart.js 4.x includes zoom in `chartjs-plugin-zoom`. Verify the bundled version. Fallback: disable zoom, keep pan. |
| Empty DB makes development hard | High | Seed script: `INSERT INTO token_logs ...` with synthetic data for 3 agents over 14 days. Or run `observeco watch start` and let it collect real data. |
| `/api/tokens/analytics` HTML endpoint has callers | Low | Only called from `loadTokenAnalytics()` JS. We're replacing both simultaneously. |
| Large token_logs table slows queries | Low | On-the-fly aggregation with proper indexes. Target <100ms for 30-day hourly on 38K rows. If slow, add materialized aggregation table (Phase 5 of spec). |
