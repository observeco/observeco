# Claude Code Independent Verification — ObserveCo "Three Lied-About Features"

You are an independent auditor. Do NOT trust the proposal below. Verify every claim against the actual code, then give a verdict. Be specific. Reference file:line. Don't be polite — be useful. If a claim is wrong, say which claim and what the code actually shows.

## Repo

Only `/Users/seanfzc/projects/observeco-main` is live. `/Users/seanfzc/projects/observeco` and `/Users/seanfzc/projects/observeco-cap` are stale copies — do not read them.

## Project context

ObserveCo is a local-first observability tool for an agent ecosystem (SQLite + Python, no ML infra). It was previously caught overstating three features: "ML-based risk predictions", "memory bloat detection", and "L2 auto-heal". Someone wrote an honest-rebuild proposal. Your job: check whether the proposal's CLAIMS ABOUT CURRENT CODE are accurate, and whether the PROPOSED CHANGES are minimal and correct.

## Claims to verify (each: CONFIRMED / REFUTED / PARTIAL + evidence)

1. `src/observeco/anomaly/__init__.py` exists and implements 4 real detectors (agent_dead, error_bursts, cost_spikes, retry_loops) with no ML dependency. — Check the file and its imports.
2. `src/observeco/tracking/tokens.py` line ~76 `compute_anomaly()` is a stub that returns None.
3. `src/observeco/tracking/tokens.py` `log_token_turn()` returns None (implicit), but `src/observeco/cli.py` ~line 1123-1129 does `result['anomaly_score']` on its return value → would raise TypeError if exercised.
4. `src/observeco/risk_predictor.py` line 1 docstring says "ML-based risk prediction" but the implementation is rule-based statistics over JSONL session files (no telemetry DB).
5. `src/observeco/cli.py` ~line 1668 the `risk` Typer app help text says "ML-based risk prediction and profiling".
6. `src/observeco/heal/l2.py` lines ~52-70: signal named `memory_bloat` with comment "RSS growth trend" but reads `latency_ms`. pulse_log table has NO memory/RSS column.
7. `token_logs` table (db.py migration 7, ~line 206-224) has a `memory_tokens` column — i.e. a real context-growth signal already exists per turn.
8. `src/observeco/heal/l2.py` lines ~110-120: auto-actions log and resolve but never execute (comment says "actual execution would happen in heal.py integration").
9. `src/observeco/watch_consumers.py` `register_all()` does NOT include an L2 consumer; `run_l2_scan` is never called from any consumer.
10. `src/observeco/db.py` ~line 345: heal_events CHECK constraint is `('l1_restart','l2_trim','l2_garden','circuit_reset','manual_heal','escalation')` and `src/observeco/heal/__init__.py` ~line 297-301 logs `event_type="heal_feedback"` inside a bare `except: pass` → IntegrityError silently swallowed.
11. `src/observeco/self_monitoring.py` is dead code — zero imports elsewhere in src/.
12. `src/observeco/heal/__init__.py` genuinely contains: 7 diagnosis patterns, LLM escalation, action executor (restart, cooldown, pip_install, trim, garden_cleanup), circuit breaker, pre-heal snapshots, post-heal evaluation.

## Proposal to sanity-check

A. Anomaly: replace `compute_anomaly()` with a rolling z-score over last 30 token turns (None under 5 samples, statistics stdlib). Make `log_token_turn` return `{"cost", "anomaly_score", "budget_alerts"}`. Relabel risk_predictor.py:1 and cli.py:1668 from "ML-based risk prediction" to "statistical risk analysis".

B. Memory: rename signal `memory_bloat` → `latency_drift` in l2.py + module docstring + constants. Add `tracking/context_growth.py`: per-agent 7d slope of (memory_tokens + total_tokens) from token_logs, flag when projection exceeds 128K context window. DB: new migration needed to widen the l2_trending CHECK (SQLite cannot ALTER CHECK) — keep old value for backward compat.

C. L2 heal: add L2Consumer (300s interval, calls run_l2_scan, publishes on detection) to watch_consumers.py. Replace l2.py resolve-only dispatch with real actions: graceful_restart → run_heal(auto_heal=True, agent_name=...); circuit_backoff → set_circuit_state(tripped, cooldown 300s); sigabort → needs PID lookup (flag if that dependency is unbuilt; downgrade to log+escalate if so). Add 'heal_feedback' to heal_events CHECK. Delete self_monitoring.py.

## Questions to answer

1. Which of claims 1-12 are wrong or partially wrong, with file:line evidence?
2. Is the z-score approach sound given the data actually in token_logs? Would MAD be meaningfully better for this data?
3. Is the `log_token_turn` return-type fix actually sufficient to unbreak cli.py, or are there other callers that also break?
4. Does any code path already call `run_l2_scan` that the proposal missed?
5. Is deleting self_monitoring.py safe? Grep for imports/callers first.
6. Is the l2_trending CHECK migration strategy (recreate table) correct for this codebase, or does db.py have a better migration pattern to follow?
7. Does the heal executor's `run_heal` signature actually accept `auto_heal=True, agent_name=...` as the proposal claims?
8. Would any proposed change introduce a silent failure? (This codebase's failure mode is silent swallowing.)
9. Any claim in the proposal that is itself a new lie (overstating what the fix does)?
10. Is there a simpler way to meet the original intent for any of the three features?

## Output

Write your verdict to `docs/claude-verdict-three-lies.md` in the repo. Structure: per-claim table (claim → verdict → evidence), then answers to questions 1-10, then your final recommendation (ship as-is / ship with changes / don't ship, with the minimal change list).
