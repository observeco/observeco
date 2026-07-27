# obs-spec-083: Token-Log Session Attribution (unblock #82 token metrics)

**Status:** Built — 2026-07-12. Root cause found (Hermes `observability/otel` plugin already emits `hermes.session_id`; ObserveCo just wasn't reading it). Implemented: `otel_listener.py` captures `hermes.session_id` → `log_token_turn()` stores it → `compute_efficiency()` feeds the 3 token metrics. Verified live on :8899 (injected test span → context-pressure/cache-hit/yield-density all scored from real token_logs join). No Hermes change, no migration. ~70 lines, 4 files.
**Product:** ObserveCo dashboard → Session Efficiency Scoring
**Owner:** Main
**Depends on:** #82 (scoring engine, built), `token_logs` table (exists, migration 17 added `session_id` col), Hermes OTEL plugin (emits `gen_ai.*` spans)

---

## §1 Problem (evidence-based)

#82's 3 token-derived metrics are `noop`:
- `context-pressure` (peak input tokens)
- `cache-hit` (cache_read ÷ total input)
- `yield-density` (output ÷ input)

They noop because `compute_efficiency()` passes an empty token list — there is no reliable way to associate a Hermes session with its `token_logs` rows.

**Verified 2026-07-12:**
- `token_logs.session_id` is **empty across all rows** (0 of ~507K populated). Schema column exists (migration 17) but no caller writes it.
- Row sources: **477,791 `watch_` rows** (watch-daemon trim snapshots, `turn_id=watch_{ts}_{agent}`) + **~29K `otel_` rows** (real LLM spans, `turn_id=otel_{span_id}`) + proxy/SDK rows.
- The 3 metrics already *accept* token data as params (`token_counts`, `token_log_rows`); they just receive `[]`. The fix is the **attribution + read path**, not the metric math.

---

## §2 Root cause

`log_token_turn()` (db.py:3814) has no `session_id` parameter. Callers:
| Caller | turn_id shape | Has session context? |
|--------|--------------|---------------------|
| `watch.py:338` | `watch_{ts}_{agent}` | ❌ No — periodic loop per agent, no Hermes session awareness |
| `otel_listener.py:283` | `otel_{span_id}` | ⚠️ Maybe — Hermes OTEL plugin emits `gen_ai.*` spans; if it also emits a session attr, capture it |
| `proxy/server.py:298` | (proxy) | ❓ Depends on proxy wiring |
| `tracking/sdk/patcher_*.py` | (SDK) | ⚠️ SDK is invoked *by* the agent — session may be in scope |
| `cli.py:1017` | (CLI) | ❓ |

The `watch_` rows (93% of volume) are **trim snapshots, not real session turns** — they can never be attributed to a session. Only the `otel_` / SDK / proxy rows represent actual LLM calls that *could* carry session_id.

---

## §3 Two approaches (with trade-offs)

### Approach A — Capture session_id from OTEL span (recommended)
The Hermes OTEL plugin already emits `gen_ai.system`, `gen_ai.request.model` per LLM call. If it emits a session attribute (e.g. `gen_ai.session.id` or `hermes.session.id`), `otel_listener.py` captures it and passes it to `log_token_turn()`.

- **Pros:** Real session attribution for the actual LLM calls (the token-heavy ones). No watch-daemon change. Clean, event-driven.
- **Cons:** Requires the Hermes OTEL plugin to emit session_id (may need a plugin config tweak or a Hermes-side change). Only covers OTEL-sourced tokens, not watch/proxy.
- **Coverage:** The 29K+ OTEL rows (real LLM calls) — these are exactly what the token metrics need.

### Approach B — Timestamp-window join (rejected for now)
Join sessions to token_logs by `agent_name` + overlapping `recorded_at` window.

- **Pros:** No schema/caller change.
- **Cons:** Sessions overlap on the same agent → false attribution. A session's tokens get attributed to the wrong session. **This produces lies in the dashboard.** Rejected per #82 ponytail ("Not building it wrong").

### Approach C — Add session_id param to log_token_turn + wire all callers
Add `session_id` param, persist it, and thread session context through every caller that has it.

- **Pros:** Complete — every source attributes correctly.
- **Cons:** watch.py has no session context (would need agent runtime to expose "current session"), SDK/proxy wiring is non-trivial. Largest scope.
- **Coverage:** All sources *that have* session context; watch rows stay session-less (correct — they're not session turns).

**Recommendation:** **Approach A first** (unblocks the real LLM-call tokens via OTEL), then **Approach C partially** for the SDK patchers (they run in-agent and likely have session scope). Leave watch.py session-less by design — its rows aren't session turns.

---

## §4 Implementation plan (if approved)

### Step 1 — Schema/DB (trivial, already partially done)
- `log_token_turn()` gains `session_id: str = ""` param; INSERT includes `session_id`.
- No migration needed (column exists). Backfill impossible for existing rows (watch rows have no session).

### Step 2 — OTEL capture (Approach A)
- In `otel_listener.py:283`, read `span_attrs.get("gen_ai.session.id")` (or `hermes.session.id`) → pass as `session_id` to `log_token_turn()`.
- **Gate:** verify the Hermes OTEL plugin actually emits this attr. If not, this step blocks until the plugin is updated (separate workstream, possibly Hermes-side).

### Step 3 — SDK patchers (Approach C partial)
- `tracking/sdk/patcher_base.py:_log_token_turn()` — thread session_id from agent runtime context if available.

### Step 4 — Read path in #82
- `compute_efficiency(turns)` currently calls the 3 token metrics with `[]`. Change to query `token_logs WHERE session_id = ?` (new helper `get_session_tokens(session_id)` in db.py / tokens.py).
- Pass `token_counts` (input_tokens list) and `token_log_rows` to the 3 metrics. They already score correctly once fed real data.

### Step 5 — Verification
- Unit: `test_token_attribution` — insert a token_log row with session_id, confirm `compute_efficiency` returns non-noop for the 3 metrics.
- Prod: after OTEL emits session_id, confirm `token_logs` gets populated session_id on next LLM call; confirm Efficiency tab shows context-pressure / cache-hit / yield-density instead of `noop`.

---

## §5 Scope guardrails (lazy rules)

- **Do NOT** touch `watch.py` to fake session attribution — its rows are trim snapshots, not session turns.
- **Do NOT** implement Approach B (timestamp join) — false attribution.
- **Do NOT** backfill — existing 507K rows cannot be attributed.
- **Do** keep the 3 metrics' math untouched (already correct); only the data feed changes.
- Minimum: param + OTEL capture + read-path query. SDK patchers only if session context is trivially available.

---

## §6 RESOLVED — Hermes OTEL plugin DOES emit session_id (verified 2026-07-12)

Investigated outside the observeco repo. Findings (evidence, not assumption):

1. **Hermes config enables the `observability/otel` plugin** (`~/.hermes/config.yaml:737`). It is a Hermes *plugin*, not core — exports one OTLP/HTTP span per LLM API call to ObserveCo's listener on `:4318`.
2. **The OTEL plugin's `on_post_api_request` hook already receives `session_id`** from Hermes (`model_tools.py:980` threads `session_id` through the model-call path; the hook signature at `plugins/observability/otel/__init__.py:134` takes `session_id`).
3. **The plugin ALREADY emits `hermes.session_id` in the span attributes** (`plugins/observability/otel/__init__.py:184`: `"hermes.session_id": session_id or ""`).

**Conclusion:** The session_id data is already on the wire for every real LLM call. ObserveCo's `otel_listener.py` simply does NOT read `hermes.session_id` from `span_attrs` — that is the entire gap. **No Hermes-side change required.**

### Updated implementation (now SMALL — Approach A only)

| Step | File | Change |
|------|------|--------|
| 1 | `src/observeco/otel_listener.py` | After building `span_attrs` (line 226), read `hermes.session_id` → pass as `session_id` to `log_token_turn()` (line 283) |
| 2 | `src/observeco/db.py` | `log_token_turn()` (line 3814): add `session_id: str = ""` param; include in INSERT (column exists via migration 17) |
| 3 | `src/observeco/efficiency/metrics.py` | `compute_efficiency()`: replace the `[]` passed to the 3 token metrics with a query `get_session_tokens(session_id)` from token_logs |
| 4 | `src/observeco/tracking/tokens.py` | Add `get_session_tokens(session_id)` helper (SELECT input/cache from token_logs WHERE session_id=?) |
| 5 | `tests/test_efficiency.py` | Insert a token_log row with session_id; assert the 3 token metrics return non-noop |

**Watch-daemon rows (`watch_`):** stay session-less by design — they are trim snapshots, not session turns. The OTEL-sourced rows (real LLM calls) will now carry session_id and become joinable.

**Effort:** ~4 files, ~60 lines. No migration, no Hermes change, no schema change. Rejected Approach B (timestamp join) stands — false attribution.



---

## §7 Files touched (estimated)

| File | Action | Notes |
|------|--------|-------|
| `src/observeco/db.py` | Patch `log_token_turn` | Add `session_id` param + INSERT column |
| `src/observeco/otel_listener.py` | Patch | Capture session attr → pass to log_token_turn |
| `src/observeco/tracking/sdk/patcher_base.py` | Patch | Thread session_id if in scope |
| `src/observeco/efficiency/metrics.py` | Patch `compute_efficiency` | Query token_logs by session_id, feed the 3 metrics |
| `src/observeco/tracking/tokens.py` | Add | `get_session_tokens(session_id)` helper |
| `tests/test_efficiency.py` | Add | Token attribution test |

~6 files, ~120 lines. No schema migration (column exists).

---

## §8 Out of scope

- Watch-daemon session attribution (not a session turn source).
- Per-profile AGENTS.md optimization (separate #82 ponytail).
- Historical backfill (impossible — no session data in existing rows).
