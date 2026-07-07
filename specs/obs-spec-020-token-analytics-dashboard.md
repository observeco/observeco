# obs-spec-020: Token Analytics Dashboard

**Status:** v3 Built 2026-07-07 — Token tab now ships the 4-chart grid (Cost + Target benchmark line, Cache Hit Rate, Output Share, Cache Hit by Agent) matching the v0.3.1 design. Verdict card, cache-by-agent chart, confidence indicator, per-agent breakdown table retained. Component toggle + zoom/pan + drill-down modal deferred.
**Product:** ObserveCo dashboard
**Depends on:** obs-spec-014 (per-turn token tracking), token_logs table (exists)
**Owner:** Pragma (COO)

---

## §1 Problem

The dashboard has per-turn token data (38K+ entries across 14 agents) but no **visual analytics**. Users can't see:

- Token usage trends over time (hourly/daily/weekly)
- Which agents consume the most tokens
- Cost breakdown by provider
- System prompt impact on token usage
- Workflow/service attribution

**Current state:** Raw `token_logs` table exists with input/output/cache breakdown. SDK patchers (OpenAI, Anthropic, LangChain) auto-apply via `sitecustomize.py` when `OBSERVECO_ENABLED=1` is set. Agent attribution via `OBSERVECO_AGENT_NAME` env var. Local provider detection via `base_url` check. System prompt estimation via 4-char heuristic from request kwargs.

## §2 Requirements

### R1: Time-Series Aggregation
- Bucket token data by minute, hour, day, week, month
- Support filtering by agent, provider, time range
- Return pre-aggregated data for chart rendering

### R2: Chart API Endpoints
- `GET /api/tokens/chart` — time-series data for line/area charts
- `GET /api/tokens/breakdown` — slice/dice by dimension (agent, provider, workflow)
- `GET /api/tokens/system-prompts` — top system prompts by token usage

### R3: Dashboard UI
- New "Token Analytics" tab in agent detail view
- Chart.js time-series with zoom/pan
- Filters: agent, provider, time range, granularity, component (total/input/output/cache), source (accurate vs all)
- Source filter: "Accurate" (sdk, otel) vs "All" (sdk, otel, watch)
- Verdict card: total cost, top spender, cache rate, recommendation, confidence badge
- Per-agent cache bar chart: horizontal bars showing each agent's cache hit rate
- Breakdown table sorted by cost with % column
- Drill-down: click data point → see turn details

### R4: Data Collection Updates
- Add `workflow_name` column (for cron jobs, scheduled tasks)
- Add `service_name` column (hermes, openclaw, etc.)
- Update Hermes/OpenClaw to log workflow/service metadata

### R5: Historical Data Backfill
- Backfill from Hermes session DB (total tokens only)
- Backfill from OpenClaw logs (if available)
- Component breakdown not available for historical data

## §3 Database Schema

### Migration: Add columns to token_logs

```sql
-- Add workflow/service metadata
ALTER TABLE token_logs ADD COLUMN workflow_name TEXT DEFAULT '';
ALTER TABLE token_logs ADD COLUMN service_name TEXT DEFAULT '';
ALTER TABLE token_logs ADD COLUMN session_id TEXT DEFAULT '';
ALTER TABLE token_logs ADD COLUMN system_prompt_hash TEXT DEFAULT '';

-- Indexes for new columns
CREATE INDEX IF NOT EXISTS idx_token_workflow ON token_logs(workflow_name);
CREATE INDEX IF NOT EXISTS idx_token_service ON token_logs(service_name);
CREATE INDEX IF NOT EXISTS idx_token_session ON token_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_token_prompt_hash ON token_logs(system_prompt_hash);
```

### Aggregation: On-the-fly (no materialized table)

Aggregation is computed on-the-fly from `token_logs` via SQL `GROUP BY` with time-bucket truncation. No separate `token_aggregations` table — avoids sync issues and storage overhead. Performance target: <100ms for 30-day hourly queries on 38K+ rows.

## §4 API Endpoints

### GET /api/tokens/chart

**Query params:**
- `agent` (optional) — filter by agent name
- `provider` (optional) — filter by provider
- `workflow` (optional) — filter by workflow name
- `service` (optional) — filter by service name
- `from_ts` (optional) — start timestamp (Unix)
- `to_ts` (optional) — end timestamp (Unix)
- `granularity` (optional) — 'minute', 'hour', 'day' (default: 'hour')
- `component` (optional) — 'total', 'input', 'output', 'cache' (default: 'total')

**Response:**
```json
{
  "granularity": "hour",
  "agent": "hound",
  "component": "total",
  "data": [
    {
      "bucket_start": 1781104321,
      "bucket_end": 1781107921,
      "total_tokens": 125000,
      "turn_count": 45,
      "avg_tokens": 2777,
      "max_tokens": 8500,
      "min_tokens": 1200,
      "cost": 0.01875
    }
  ],
  "summary": {
    "total_tokens": 1250000,
    "total_cost": 0.1875,
    "avg_per_turn": 2777,
    "turn_count": 450
  }
}
```

### GET /api/tokens/breakdown

**Query params:**
- `dimension` (required) — 'agent', 'provider', 'workflow', 'service'
- `from_ts` (optional) — start timestamp
- `to_ts` (optional) — end timestamp

**Response:**
```json
{
  "dimension": "agent",
  "data": [
    {
      "name": "hound",
      "total_tokens": 5310317,
      "cost": 0.7965,
      "turn_count": 3509,
      "avg_per_turn": 1513
    }
  ]
}
```

### GET /api/tokens/system-prompts

**Query params:**
- `from_ts` (optional) — start timestamp
- `to_ts` (optional) — end timestamp
- `limit` (optional) — max results (default: 20)

**Response:**
```json
{
  "data": [
    {
      "system_prompt_hash": "abc123",
      "total_tokens": 850000,
      "turn_count": 1200,
      "avg_per_turn": 708,
      "agents": ["hound", "main"]
    }
  ]
}
```

## §5 Dashboard UI

### Token Analytics Tab

**Location:** Agent detail view → new "Token Analytics" tab

**Components (SHIPPED — matches v0.3.1 token tab screenshot):**

1. **5-Chart Grid** (single vertical column, uniform height → all 5 share an aligned time axis). Each chart has a stat-card header (value + label). Benchmark bands drawn via inline Chart.js plugin (no annotation-plugin dependency):
   - **Cost** (bar) — X: time, Y: $ cost. Red dashed **Target** line (mean daily cost of window; configurable via budget config).
   - **Tokens / Turn** (line) — X: time, Y: tokens/turn (lower better). Bands: Low 1000 / Mod 10000 / High 50000 / V.High 100000.
   - **Output / Input ratio** (line) — X: time, Y: output÷input (higher better). Bands: Low 0.5 / Mod 1 / High 5 / V.High 20.
   - **Cache Hit Rate** (line, %) — X: time, Y: 0-100% (higher better). Bands: Low 5 / Mod 10 / High 50 / V.High 80.
   - **Cost / Turn** (line, $) — X: time, Y: $/turn (lower better). Bands: Low 0.001 / Mod 0.01 / High 0.1.
   - ponytail: earlier spec called for one stacked time-series with component toggle + zoom/pan. Shipped design uses 5 focused charts (v0.3.1 lineage). Component toggle + zoom/pan deferred.

2. **Filter Bar**
   - Agent selector (dropdown)
   - Time range (preset: 1h, 24h, 7d, 30d)
   - (Provider selector, granularity, component toggle — deferred, not in shipped build)

3. **Verdict Card** (v2 — replaces summary cards)
   - Total cost + turn count for the period
   - Top spender: agent name + % of total (red if >50%)
   - Cache hit rate: overall % (red if <5%)
   - Recommendation: one-sentence actionable insight
   - Confidence badge: "X% of cost from accurate sources" (green if >80%, yellow if >50%, red if <50%)

4. **Breakdown Table**
   - Top agents by token usage, sorted by cost descending
   - Columns: Agent, Cost (bold), Tokens, Model, Data (Acc/Est), Cache %
   - Click to open agent modal

5. **Per-Agent Cache Bar Chart** (v2) — horizontal bars, one per agent, X: 0-100% hit rate, colored red <5% / yellow 5-20% / green >20%. Rendered in the Cache Efficiency section below the grid.

6. **Drill-Down Modal** — deferred (not in shipped build).

### Empty States

- **No data:** "No token data for this agent. Run `observeco token log <agent>` to start tracking."
- **No data for filter:** "No data matches your filters. Try widening the time range or removing filters."
- **Loading:** Spinner with "Loading token analytics..."

### Error States

- **API error:** "Failed to load token data. Check dashboard server status."
- **Invalid params:** "Invalid filter parameters. Reset to defaults."

## §6 Implementation Phases

### Phase 1: Schema Migration + Query Functions (1 day)
- Add columns to token_logs
- Build aggregation query functions (SQL GROUP BY with time-bucket truncation)
- Verify query performance on existing data (target: <100ms for 30-day hourly)
- **Verification:** py_compile all new files, TestClient for aggregation functions
- **Rollback:** DROP new columns + indexes if migration fails
- **Observability:** Log query duration to logger; warn if >500ms
- **Heartbeat:** Write timestamp to token_analytics_heartbeat file after each successful query

### Phase 2: API Endpoints (1 day)
- `/api/tokens/chart` endpoint
- `/api/tokens/breakdown` endpoint
- `/api/tokens/system-prompts` endpoint
- Input validation + error handling
- **Verification:** TestClient assertions for each endpoint
- **Error handling:** Auto-retry on timeout (3 attempts, 2s delay)
- **Logging:** Log API requests + errors to logger

### Phase 3: Dashboard UI (2-3 days)
- Token Analytics tab component
- Chart.js integration
- Filter bar
- Summary cards
- Breakdown table
- Drill-down modal
- **Verification:** DOM assertions for empty/loading/error states
- **Fallback:** HTML table if Chart.js CDN fails
- **Performance:** Lazy load chart data (only on tab open)

### Phase 4: Data Collection Updates (1 day)
- Update Hermes to log workflow/service metadata
- Update OpenClaw to log service metadata
- Test end-to-end data flow
- **Verification:** Integration test with mock agent data
- **Backward compatibility:** Old agents ignore new columns (defaults)

### Phase 5: Backfill + Testing (1 day)
- Backfill historical data from session DBs
- End-to-end testing
- Performance testing with large datasets
- **Verification:** Full test suite, load test with 100K rows
- **Cleanup:** Prune token_aggregations to 90 days retention

**Total estimate: 6-8 days**

## §7 Edge Cases

### Error States
- **API timeout:** Chart shows "Request timed out. Retrying..." with auto-retry (3 attempts, 2s delay)
- **API error (5xx):** Chart shows "Server error. Check dashboard server status." with manual retry button
- **API error (4xx):** Chart shows "Invalid request. Resetting filters..." with auto-reset to defaults
- **Chart.js CDN failure:** Fallback to simple HTML table with token data
- **Migration failure:** Rollback procedure documented in §6 Phase 1, automatic retry on next startup

### Degraded States
- **Partial aggregation:** Show available data with warning: "Data may be incomplete. Some sources not yet reporting."
- **Stale data:** If last data point >1 hour old, show "Data may be outdated. Refreshing..." with auto-refresh
- **Concurrent writes:** On-the-fly aggregation reads from token_logs directly — no locking needed

### Lifecycle
- **Data refresh:** On-the-fly aggregation per API call — no background job needed. Heartbeat file tracks last successful query.
- **Stale data detection:** Check last data point timestamp on each API call, warn if >1 hour old
- **Migration rollback:** New columns have defaults (empty string, 0), old code ignores new columns
- **Cleanup:** token_logs pruned to 90 days retention (configurable)

### No Data
- Empty chart with message: "No token data for this agent."
- Summary cards show 0 values
- Breakdown table shows "No data available"

### Partial Data
- Missing component values default to 0
- Missing cost values computed from provider rates
- Missing workflow/service columns use empty string

### Large Datasets
- Aggregation table pre-computed for performance
- Pagination for breakdown tables (max 100 items)
- Chart limits: max 1000 data points (aggregate to coarser granularity if needed)

### Cross-Platform
- **Windows:** Backfill script uses platformdirs for DB path resolution
- **macOS:** Standard paths work as-is
- **Linux:** Standard paths work as-is
- **Docker:** Volume mount required for persistent data

### Multi-Instance
- **Single-user assumption:** Dashboard is single-user (no concurrent web sessions)
- **Multiple agents:** 14+ agents supported, aggregation handles concurrent writes
- **Multiple providers:** Provider breakdown works across DeepSeek, OpenAI, Anthropic, etc.

## §8 Success Metrics

### Performance Metrics
- [ ] Chart loads in <500ms for 30-day range
- [ ] Aggregation query completes in <100ms
- [ ] Dashboard renders 1000 data points without lag
- [ ] Filter changes update chart in <200ms
- [ ] Historical backfill completes in <5 minutes (for 2-3 days of data)

### Operational Metrics
- [ ] Aggregation job runs every 5 minutes without failure
- [ ] Stale data detection triggers refresh within 1 hour
- [ ] Migration rollback succeeds without data loss
- [ ] Aggregation job logs start/end/error to logger
- [ ] Heartbeat file updated after each aggregation refresh

### Functional Metrics
- [ ] All 14 agents show token data correctly
- [ ] Component breakdown (identity/skills/memory/tools/guidance) renders accurately
- [ ] Cost computation matches provider rates (DeepSeek $0.15/M, OpenAI $2.50/M, etc.)
- [ ] Time-series chart zooms/pans smoothly
- [ ] Filters narrow data correctly (agent, provider, time range, granularity)

### Acceptance Criteria
- [ ] User can select agent → see token usage trend over time
- [ ] User can filter by provider → see cost breakdown
- [ ] User can click data point → see turn details
- [ ] User can export chart data as CSV
- [ ] Empty states guide user to start tracking
- [ ] Error states provide actionable next steps

### Tier Mapping
- **Free tier:** Basic token summary (total tokens, cost) on agent cards
- **Pro tier:** Full analytics dashboard with charts, filters, drill-down, export

## §9 Cross-References

- obs-spec-014: Per-turn token tracking (foundation)
- token_logs table: Existing data (38K+ entries)
- Hermes session DB: Historical backfill source
- OpenClaw logs: Historical backfill source (if available)

## §10 Input/Output/Cache Token Breakdown

**Status:** Planned (2026-06-11)
**Depends on:** §1-§8 (Token Analytics Dashboard shipped)

### §10.1 Problem

Current cost calculation uses a single flat rate on `total_tokens`. This is inaccurate because:

- Input tokens and output tokens have different pricing (e.g., DeepSeek: $0.15/M input, $0.60/M output — 4x difference)
- Cache read/write tokens have separate pricing (often free or near-zero)
- System prompt tokens (identity, skills, memory, tools, guidance) are always input tokens — they're not distinguished from user prompt tokens
- OTel listener captures `input_tokens` and `output_tokens` from spans but writes to `compress_log` via `db.log_trim()`, not `token_logs`

**Current cost accuracy:** Single flat rate on total tokens. Overestimates for cache-heavy workloads, underestimates for output-heavy ones.

### §10.2 Schema Changes

**New columns on `token_logs`:**

```sql
ALTER TABLE token_logs ADD COLUMN input_tokens INTEGER DEFAULT 0;
ALTER TABLE token_logs ADD COLUMN output_tokens INTEGER DEFAULT 0;
ALTER TABLE token_logs ADD COLUMN cache_creation_tokens INTEGER DEFAULT 0;
ALTER TABLE token_logs ADD COLUMN cache_read_tokens INTEGER DEFAULT 0;
ALTER TABLE token_logs ADD COLUMN cost_computed TEXT DEFAULT 'flat';  -- 'flat' | 'tiered' | 'cache_aware'
ALTER TABLE token_logs ADD COLUMN cache_savings REAL DEFAULT 0;  -- display-only, does not affect cost
```

**Indexes:**
```sql
CREATE INDEX IF NOT EXISTS idx_token_input ON token_logs(input_tokens);
CREATE INDEX IF NOT EXISTS idx_token_output ON token_logs(output_tokens);
CREATE INDEX IF NOT EXISTS idx_token_cost_computed ON token_logs(cost_computed);
```

**Migration:** 18 (follows Migration 17)

**Backward compatibility:** New columns default to 0. `cost_computed` defaults to `'flat'`. Existing rows have `input_tokens=0, output_tokens=0, cost_computed='flat'`. Cost recalculation triggers when `input_tokens + output_tokens > 0` and `cost_computed='flat'`.

### §10.3 Provider Pricing Table

Replace flat `PROVIDER_RATES` with tiered pricing:

```python
PROVIDER_PRICING = {
    "deepseek": {"input": 0.15, "output": 0.60, "cache_read": 0.015, "cache_write": 0.15},
    "openai": {"input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 2.50},
    "gpt-4o": {"input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 2.50},
    "gpt-4": {"input": 10.00, "output": 30.00, "cache_read": 5.00, "cache_write": 10.00},
    "claude": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-sonnet": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-haiku": {"input": 0.25, "output": 1.25, "cache_read": 0.025, "cache_write": 0.30},
    "gemini": {"input": 0.15, "output": 0.60, "cache_read": 0.015, "cache_write": 0.15},
    "ollama": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},
    "custom": {"input": 0.15, "output": 0.60, "cache_read": 0.015, "cache_write": 0.15},
}
```

All rates are per million tokens.

### §10.4 Cost Computation Update

```python
def compute_cost_tiered(input_tokens: int, output_tokens: int,
                        cache_creation: int, cache_read: int,
                        provider: str) -> float:
    """Compute cost with input/output/cache tiered pricing."""
    rates = PROVIDER_PRICING.get(provider.lower(), PROVIDER_PRICING["custom"])
    cost = (
        (input_tokens / 1_000_000) * rates["input"]
        + (output_tokens / 1_000_000) * rates["output"]
        + (cache_creation / 1_000_000) * rates["cache_write"]
        + (cache_read / 1_000_000) * rates["cache_read"]
    )
    return round(cost, 6)
```

**Fallback:** When `input_tokens + output_tokens == 0` (legacy rows), fall back to flat-rate `compute_cost(total_tokens, provider)` and set `cost_computed='flat'`.

**Double-counting prevention:** §10.4 computes cost from raw token counts (input, output, cache_creation, cache_read). §10.9 cache_savings is a **display-only metric** — it shows what was saved vs. full-price input rates, but does NOT reduce the cost computed in §10.4. The `cost` column always reflects what the provider actually charged. Cache_savings is informational only, stored separately in `cache_savings` column.

Cost computation flow:
1. Provider reports: input=8000, output=1500, cache_read=7000 (of the 8000 input)
2. §10.4 computes: `(8000-7000)/1M × input_rate + 1500/1M × output_rate + 7000/1M × cache_read_rate`
3. §10.9 computes: `cache_savings = 7000/1M × (input_rate - cache_read_rate)` — display only
4. `cost` column = result from step 2. `cache_savings` column = result from step 3. No double-counting.

### §10.5 Data Routing Changes

**Provider detection:** All paths use a shared `resolve_provider(span_attrs: dict) -> str` function that extracts provider from OTel attributes, config, or falls back to `'custom'`. Place in `tracking/tokens.py`:

```python
def resolve_provider(span_attrs: dict = None, config_provider: str = "") -> str:
    """Resolve provider from OTel attributes, config, or fallback."""
    if span_attrs:
        # OTel semantic conventions: llm.provider or gen_ai.system
        for key in ("llm.provider", "gen_ai.system", "gen_ai.request.model"):
            val = span_attrs.get(key, "")
            if val:
                # Extract provider from model string (e.g., "deepseek-chat" → "deepseek")
                for p in PROVIDER_PRICING:
                    if p in val.lower():
                        return p
    if config_provider:
        for p in PROVIDER_PRICING:
            if p in config_provider.lower():
                return p
    return "custom"
```

**OTel listener (`otel_listener.py`):**

Currently writes to `db.log_trim()` (compress_log). Add parallel write to `token_logs`:

```python
if input_tokens or output_tokens:
    # Existing: write to compress_log
    db.log_trim(...)

    # New: also write to token_logs with full breakdown
    from observeco.tracking.tokens import resolve_provider
    provider = resolve_provider(span_attrs=span_attrs)
    db.log_token_turn(
        agent_name=agent_name,
        turn_id=f"otel_{span_id}",
        total_tokens=input_tokens + output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider=provider,
    )
```

**Watch daemon (`watch.py`):**

Currently passes `total_tokens` from `trim_result` without breakdown. When trim_result includes component data, split into input/output:

```python
# trim_result has identity/skills/memory/tools/guidance — all input tokens
input_tokens = sum(trim_result.get(k, 0) for k in
    ["identity_tokens", "skills_tokens", "memory_tokens", "tools_tokens", "guidance_tokens"])
output_tokens = 0  # trim doesn't capture output
```

**CLI caller (`cli.py:675`):**

Currently calls `log_token_turn` without input/output breakdown. Add optional params:

```python
result = log_token_turn(agent_name, turn_id, total_tokens,
    identity=identity, skills=skills, memory=memory,
    tools=tools, guidance=guidance,
    input_tokens=identity + skills + memory + tools + guidance,  # all components are input
    output_tokens=0,  # CLI log doesn't capture output
    provider=provider,
)
```

**Hermes/OpenClaw integration:**

Agents should report `input_tokens` and `output_tokens` in their token log payloads. The `log_token_turn` wrapper already accepts these params — callers need to pass them.

**Agent non-compliance fallback:**

When agents don't report `input_tokens`/`output_tokens` (backward compatibility):
1. If `identity + skills + memory + tools + guidance > 0` → set `input_tokens = sum of components`, `output_tokens = 0`
2. If all component tokens are 0 but `total_tokens > 0` → set `input_tokens = total_tokens`, `output_tokens = 0` (conservative: assume all input)
3. Set `cost_computed = 'flat'` — tiered pricing not possible without breakdown
4. Log a warning: "Agent {name} did not report input/output breakdown — using flat-rate cost estimate"

This ensures every row gets a reasonable cost even when agents don't provide granular data.

### §10.6 Analytics Updates

**Chart endpoint (`/api/tokens/chart`):**

- New `component` options: `input`, `output`, `cache_creation`, `cache_read` (in addition to existing `total`, `identity`, etc.)
- Default remains `total` for backward compatibility

**Breakdown endpoint (`/api/tokens/breakdown`):**

- New dimension: `token_type` — returns `[{name: "input", total_tokens: X, cost: Y}, ...]`

**Summary cards:**

- Add "Input/Output ratio" card when input_tokens > 0
- Cost card uses tiered pricing when available, flat rate as fallback

**Drill-down modal:**

- Show input/output/cache breakdown when available
- Show "flat-rate estimate" badge when only total_tokens is known

### §10.7 Migration Strategy

**Phase 1 (schema):** Migration 18 adds columns. Zero downtime — new columns default to 0.

**Phase 2 (backfill):** For existing 38K rows from watch daemon:
- `input_tokens = total_tokens` (watch only sees system prompt components = input)
- `output_tokens = 0` (watch doesn't capture output)
- `cost_computed = 'flat'` (no breakdown available)
- Recompute cost with tiered pricing

**Phase 3 (routing):** OTel listener writes to token_logs. Watch daemon passes component breakdown as input_tokens. CLI caller passes component sum as input_tokens.

**Phase 4 (cost recalculation):** Batch update cost for rows where `cost_computed = 'flat'` and `input_tokens + output_tokens > 0`. Set `cost_computed = 'tiered'` after recalculation.

**Migration failure/rollback:**

Each migration is wrapped in a transaction. If any step fails:

```python
# Migration 18 — wrapped in transaction
def migrate_18(conn):
    try:
        conn.execute("ALTER TABLE token_logs ADD COLUMN input_tokens INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE token_logs ADD COLUMN output_tokens INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE token_logs ADD COLUMN cache_creation_tokens INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE token_logs ADD COLUMN cache_read_tokens INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE token_logs ADD COLUMN cost_computed TEXT DEFAULT 'flat'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_token_input ON token_logs(input_tokens)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_token_output ON token_logs(output_tokens)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_token_cost_computed ON token_logs(cost_computed)")
        conn.commit()
        logger.info("Migration 18 applied successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration 18 failed: {e} — rolled back, existing schema preserved")
        raise  # re-raise to prevent SCHEMA_VERSION bump on partial failure
```

**Partial migration recovery:** If Migration 18 succeeds but 19 fails:
- token_logs has new columns (input/output/cache/cost_computed) — functional
- token_message_breakdown doesn't exist — per-message attribution unavailable
- Analytics falls back to total-only view (existing behavior)
- Dashboard shows "Per-message breakdown unavailable — run migration 19" in drill-down modal

**Migration logging:** Every migration logs:
- Start: `logger.info("Migration {N} starting — schema version {current}")`
- End: `logger.info("Migration {N} complete — schema version {new}")`
- Failure: `logger.error("Migration {N} failed: {error}")`

This ensures silent migration failures are surfaced in logs.

### §10.8 Acceptance Criteria

- [ ] Migration 18 adds 6 columns without data loss
- [ ] Migration 18 rolls back cleanly on failure (no partial schema)
- [ ] Existing rows backfilled with `input_tokens = total_tokens, output_tokens = 0, cost_computed = 'flat'`
- [ ] Tiered cost matches provider pricing for known providers
- [ ] Flat-rate fallback works for legacy rows (input+output = 0, cost_computed = 'flat')
- [ ] OTel spans write to token_logs with input/output breakdown
- [ ] CLI caller passes component sum as input_tokens
- [ ] Agent non-compliance fallback produces reasonable cost (flat-rate estimate)
- [ ] Chart component filter includes input/output/cache options
- [ ] Breakdown by token_type returns correct aggregation
- [ ] Cost difference between flat-rate and tiered is <5% for typical workloads
- [ ] Cache hit ratio computed when provider returns cache metadata
- [ ] Cache heuristic accuracy within ±30% of provider-reported (when both available)
- [ ] Per-turn cache savings displayed when cache_read > 0
- [ ] Cache_savings is display-only — does not affect cost column
- [ ] token_message_breakdown rows cascade-delete when token_logs row is pruned
- [ ] Message-level token breakdown stored and queryable
- [ ] System prompt cost isolated from conversation cost
- [ ] Context accumulation cost visible in per-turn analytics
- [ ] Per-message breakdown unavailable state handled gracefully (drill-down shows fallback message)

**Regression constraint register — must survive unchanged:**

| Feature | Must survive | Verification |
|---------|-------------|-------------|
| Flat-rate cost for legacy rows | `cost_computed = 'flat'` rows use old `compute_cost()` | Query: `SELECT cost FROM token_logs WHERE cost_computed = 'flat' LIMIT 1` — must return non-zero |
| Existing chart behavior | `component = 'total'` renders identically to pre-§10 | TestClient: `/api/tokens/chart?component=total` returns same shape |
| Existing breakdown endpoint | `/api/tokens/breakdown?dimension=agent` returns same structure | TestClient assertion on response shape |
| Migration 17 columns | workflow_name, service_name, session_id, system_prompt_hash intact | `PRAGMA table_info(token_logs)` — all 17+5 columns present |
| Token analytics tab | Loads without error when input_tokens = 0 for all rows | TestClient: `/api/tokens/analytics` returns 200 |
| Pruning (Extended History) | Pruned token_logs rows don't leave orphaned token_message_breakdown rows | After prune: `SELECT COUNT(*) FROM token_message_breakdown WHERE token_log_id NOT IN (SELECT id FROM token_logs)` = 0 |

### §10.9 Prompt Caching Detection

**Problem:** Providers like Anthropic and OpenAI support prompt caching. When the same system prompt is sent across turns, the provider caches it and charges cache-read rates (90% cheaper). Without detecting this, cost calculations overestimate by up to 9x for multi-turn conversations.

**Provider cache metadata:**

| Provider | Cache creation field | Cache read field | Cache write cost | Cache read cost |
|----------|---------------------|-----------------|-----------------|----------------|
| Anthropic | `usage.cache_creation_input_tokens` | `usage.cache_read_input_tokens` | 25% surcharge on input | 90% discount |
| OpenAI | Not yet available (automatic, no metadata) | — | — | — |
| DeepSeek | Not available | — | — | — |

**Detection strategy:**

1. **Provider-reported (preferred):** When OTel span attributes include `llm.usage.cache_creation_input_tokens` or `llm.usage.cache_read_input_tokens`, use them directly.

2. **Heuristic fallback (when provider doesn't report):** Detect repeated prefixes by comparing system prompt hash across turns:
   ```python
   def detect_cache_savings(agent_name: str, system_prompt_hash: str,
                            turn_number: int, input_tokens: int,
                            provider: str) -> dict:
       """Estimate cache savings when provider doesn't report cache metadata."""
       if turn_number <= 1:
           return {"cache_read": 0, "estimated_savings": 0}
       # System prompt is typically 60-80% of input tokens for agents
       estimated_prompt_tokens = input_tokens * 0.7  # conservative estimate
       cache_read_rate = PROVIDER_PRICING.get(provider, {}).get("cache_read", 0)
       input_rate = PROVIDER_PRICING.get(provider, {}).get("input", 0)
       if input_rate > 0 and cache_read_rate < input_rate:
           savings_pct = 1 - (cache_read_rate / input_rate)
           estimated_savings = (estimated_prompt_tokens / 1_000_000) * input_rate * savings_pct
           return {
               "cache_read": int(estimated_prompt_tokens * 0.9),  # 90% likely cached after turn 1
               "estimated_savings": round(estimated_savings, 6),
           }
       return {"cache_read": 0, "estimated_savings": 0}
   ```

3. **Confidence levels:**
   - `confirmed` — provider returned cache metadata
   - `estimated` — heuristic detection (system prompt hash repeated)
   - `unknown` — no cache data available

**Heuristic accuracy bound:**

The `input_tokens * 0.7` estimate assumes 70% of input tokens are the system prompt. Accuracy varies by conversation stage:

| Turn # | Actual prompt % | Estimated (0.7) | Error |
|--------|----------------|-----------------|-------|
| 1 | 90% (system = 8K, user = 1K) | 70% | -22% underestimate |
| 5 | 75% (system = 8K, history = 3K) | 70% | -7% underestimate |
| 10 | 60% (system = 8K, history = 8K) | 70% | +17% overestimate |
| 20 | 40% (system = 8K, history = 20K) | 70% | +75% overestimate |

**Accuracy target:** Heuristic cache_savings should be within ±30% of provider-reported values when both are available. Calibration: compare heuristic vs confirmed for 100 turns after OTel routing is live, then adjust the 0.7 constant.

**Adaptive formula (recommended):**
```python
# Reduce prompt estimate as conversation grows
estimated_prompt_pct = max(0.3, 0.7 - (turn_number * 0.02))
# Floor at 30% — system prompt is always at least 30% of input
```

This bounds the error to ±30% across all turn counts.

**Schema addition:** `cache_savings` column on `token_logs` (REAL DEFAULT 0) — stores estimated or confirmed cost savings from caching. Display-only — does not affect `cost` column (see §10.4 double-counting prevention).

**Analytics impact:**
- New summary card: "Cache Savings" — total $ saved across all turns
- New chart component: "cache_read" in component filter
- Drill-down modal: show cache hit ratio when available

### §10.10 Per-Message Cost Attribution

**Problem:** A single API call in a multi-turn conversation sends `[system_prompt, msg1, msg2, ..., new_user_msg]`. Total tokens = everything. Users can't tell which messages cost how much, or that turns 8-10 cost 3x more than turns 1-3 due to context accumulation.

**New table: `token_message_breakdown`**

```sql
CREATE TABLE IF NOT EXISTS token_message_breakdown (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_log_id INTEGER NOT NULL,       -- FK to token_logs.id
    message_index INTEGER NOT NULL,       -- 0-based position in conversation
    message_role TEXT NOT NULL,           -- 'system', 'user', 'assistant', 'tool'
    content_hash TEXT DEFAULT '',         -- SHA256 of message content (for dedup)
    token_count INTEGER NOT NULL,        -- tokens for this message
    is_system_prompt INTEGER DEFAULT 0,  -- 1 if this is the system prompt
    is_cached INTEGER DEFAULT 0,         -- 1 if provider reported cache hit
    cost REAL DEFAULT 0,                 -- cost attributed to this message
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_msg_breakdown_log ON token_message_breakdown(token_log_id);
CREATE INDEX IF NOT EXISTS idx_msg_breakdown_role ON token_message_breakdown(message_role);
CREATE INDEX IF NOT EXISTS idx_msg_breakdown_hash ON token_message_breakdown(content_hash);
```

**Migration:** 19 (follows Migration 18)

**FK orphan handling:** SQLite doesn't enforce foreign keys by default. Two safeguards:

1. **Enable foreign keys on connection:**
   ```python
   conn.execute("PRAGMA foreign_keys = ON")
   ```
   This ensures `token_message_breakdown` rows are cascade-deleted when the parent `token_logs` row is pruned.

2. **Pruning hook:** When `run_prune()` removes token_logs rows, explicitly delete orphaned breakdown rows:
   ```python
   def run_prune():
       # ... existing pruning logic ...
       # Also prune orphaned message breakdowns
       conn.execute("""
           DELETE FROM token_message_breakdown
           WHERE token_log_id NOT IN (SELECT id FROM token_logs)
       """)
   ```

**Growth rate:** 10 agents × 10 turns/day × 10 messages/turn = 1000 rows/day = 365K rows/year. SQLite handles this fine. If retention policy prunes token_logs, breakdown rows follow via cascade or explicit cleanup.

**Data collection:** Agents report per-message breakdown in their token log payloads:

```python
# Agent payload format
{
    "agent_name": "hound",
    "total_tokens": 12500,
    "input_tokens": 11000,
    "output_tokens": 1500,
    "messages": [
        {"role": "system", "token_count": 8000, "is_system_prompt": true},
        {"role": "user", "token_count": 200, "content_hash": "a1b2..."},
        {"role": "assistant", "token_count": 800, "content_hash": "c3d4..."},
        {"role": "user", "token_count": 150, "content_hash": "e5f6..."},
        {"role": "assistant", "token_count": 600, "content_hash": "g7h8..."},
        {"role": "user", "token_count": 300, "content_hash": "i9j0..."},
    ]
}
```

**Analytics impact:**

1. **System prompt cost isolation:**
   ```sql
   -- Average system prompt cost per turn
   SELECT AVG(cost) FROM token_message_breakdown WHERE is_system_prompt = 1;
   -- % of total cost that is system prompt
   SELECT SUM(cost) / (SELECT SUM(cost) FROM token_logs) * 100
   FROM token_message_breakdown WHERE is_system_prompt = 1;
   ```

2. **Context accumulation visualization:**
   ```sql
   -- Token count by message position across turns
   SELECT message_index, AVG(token_count), role
   FROM token_message_breakdown
   GROUP BY message_index, role;
   -- Shows: turn 1 has 6 messages, turn 10 has 15 messages
   -- Each turn re-sends all previous messages
   ```

3. **New chart: "Cost by Message Role"**
   - Stacked bar: system (fixed), user (growing), assistant (growing), tool (variable)
   - Shows context accumulation pattern clearly

4. **New summary card: "Context Overhead"**
   - Tokens re-sent per turn (not new content)
   - Cost of re-sending previous messages

**Out of scope for this section:**
- Deduplication of repeated messages (e.g., same user message sent twice)
- Token-level attribution (only message-level)
- Real-time streaming attribution (attribution happens post-completion)

### §11 SDK Patcher Architecture (v1 Built 2026-06-21)

**Status:** v1 Built
**Files:**
- `src/observeco/tracking/sdk/patcher_base.py` — base class with agent name resolution, system token estimation, local provider detection
- `src/observeco/tracking/sdk/patcher_openai.py` — monkey-patches `openai.Client.chat.completions.create()`
- `src/observeco/tracking/sdk/patcher_anthropic.py` — monkey-patches `anthropic.Anthropic.messages.create()`
- `src/observeco/tracking/sdk/patcher_langchain.py` — registers LangChain callback handler
- `src/observeco/tracking/sdk/patcher_registry.py` — applies all patchers
- `src/observeco/tracking/sdk/detector.py` — scans for installed SDKs without importing them
- `sitecustomize.py` at Hermes venv `site-packages/` — auto-applies patchers on Python startup

### §11.1 Activation

Set `OBSERVECO_ENABLED=1` in the environment. The `sitecustomize.py` file in the Hermes venv `site-packages/` directory auto-imports and applies all patchers at Python startup.

### §11.2 Agent Attribution

Set `OBSERVECO_AGENT_NAME=<agent_name>` in the environment. The patcher reads this env var and logs it as `agent_name` in `token_logs`. Fallback: process name from `sys.argv[0]`.

### §11.3 System Prompt Estimation

The patcher has access to `messages` from the request kwargs. It counts tokens from messages with `role="system"` using a 4-char-per-token heuristic.

**ponytail:** ±20% for English, worse for code/Chinese. Upgrade path: use `tiktoken` when installed.

### §11.4 Local Provider Detection

The patcher checks `base_url` for localhost patterns (`localhost`, `127.0.0.1`, `0.0.0.0`, `::1`). When detected, provider is overridden to `"local"` and cost is set to `0.0`.

### §11.5 Data Sources

| Source | Accuracy | How | Status |
|--------|----------|-----|--------|
| SDK Patchers | ✅ Actual API calls | Monkey-patches SDK methods | Active when `OBSERVECO_ENABLED=1` |
| OTEL Listener | ✅ Actual API calls | OpenInference spans on port 4318 | Running, has data |
| Watch Daemon | ❌ Estimated from config | Reads SOUL.md every 30s | Running, has data |

### §11.6 Dashboard Source Filter

The Token Analytics tab has a source filter toggle:
- **Accurate** (default): `include_source=sdk,otel` — only actual API call data
- **All**: `include_source=sdk,otel,watch` — includes estimated data

### §11.7 Chart Components

The chart shows input/output/cache breakdown instead of the previous identity/skills/memory/tools/guidance breakdown (which was misleading — it showed config file section sizes, not actual token usage).

| Component | Description | Source |
|-----------|-------------|--------|
| Total | All tokens | All sources |
| Input | Prompt tokens | SDK patchers, OTEL |
| Output | Completion tokens | SDK patchers, OTEL |
| Cache | Cache read + cache creation tokens | SDK patchers, OTEL |

## §12 Data Quality Tier System

**See master plan §18 for full spec.**

The token analytics dashboard now shows a data quality bar above the chart indicating the current accuracy tier:

| Tier | Badge | Meaning |
|------|-------|---------|
| Estimated | ⚠️ Yellow | Watch daemon only (±80% accuracy) |
| Accurate | ✓ Green | OTEL plugin providing real per-call data (±5%) |
| Full | ✓ Blue | SDK patchers or proxy providing exact data (±1%) |

The bar also shows data freshness, stale warnings when OTEL data stops flowing, and an upgrade path to the next tier.

**API:** `GET /api/pipeline/health` returns tier, per-source stats, and upgrade path.

**Setup:** `observeco setup` CLI command checks plugin status, listener status, and data flow.

## §13 Out of Scope (Remaining)

- **Cost optimization recommendations** (suggesting prompt compression based on token patterns)
- **Real-time cost alerts** (push notifications when cost exceeds threshold — deferred to budget system)
