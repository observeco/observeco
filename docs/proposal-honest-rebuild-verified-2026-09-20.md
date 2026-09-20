# Honest Rebuild — Three Lied-About Features (verified 2026-09-20)

Repo: `/Users/seanfzc/projects/observeco-main` (live; `observeco/` and `observeco-cap/` are stale copies — ignore them)
Method: primary-source reads. Every claim below cites file:line and was re-verified this session.

---

## Current state (what's truth, what's still a lie)

### 1. "ML-based risk predictions"
| Claim | Verdict | Evidence |
|---|---|---|
| anomaly/ package is missing (design doc's claim) | **REFUTED — it exists** | `anomaly/__init__.py` — 233 lines, 4 real detectors (agent_dead, error_bursts, cost_spikes 3σ, retry_loops). Detects from pulse_log/errors/token_logs. Honest replacement for ML already built. |
| `compute_anomaly()` is a stub | **CONFIRMED** | `tracking/tokens.py:76-78` → `return None`. |
| CLI crash on `tokens log` | **CONFIRMED** | `cli.py:1123-1129` does `result['anomaly_score']` but `log_token_turn` (`tokens.py:81-101`) returns `None` → TypeError if exercised. |
| "ML-based" label | **CONFIRMED mislabel** | `risk_predictor.py:1` docstring "ML-based risk prediction"; `cli.py:1668` risk_app help "ML-based risk prediction and profiling". It's rule-based stats over JSONL session files. No telemetry DB, no learned model. |

### 2. "Memory bloat detection"
| Claim | Verdict | Evidence |
|---|---|---|
| `memory_bloat` measures latency, not memory | **CONFIRMED** | `heal/l2.py:52-70` comment says "Memory bloat — RSS growth trend", code reads `latency_ms` (line 53). pulse_log has no RSS column. |
| Real context signal exists | **CONFIRMED** | `token_logs.memory_tokens` column exists (`db.py:214`, migration 7) — the honest "context growth" signal is already captured per turn. No schema change needed. |
| Baseline machinery exists | **CONFIRMED** | `tracking/baselines.py`, `tracking/token_analytics.py` present. |

### 3. "L2 auto-heal"
| Claim | Verdict | Evidence |
|---|---|---|
| Auto-actions log but never execute | **CONFIRMED** | `l2.py:110-120` — resolves with `auto_action:{action}`, comment says "actual execution would happen in heal.py integration" (line 118-119). Never wired. |
| L2 not in watch loop | **CONFIRMED** | `watch_consumers.py` consumers: Drift, Garden, Pathway, Heal, Prune, TokenHistory, ConfigTimeline, DataSourceWatchdog. No L2Consumer. `run_l2_scan` is manual-only. |
| heal_feedback silently lost | **CONFIRMED BUG** | `db.py:345` heal_events CHECK allows only ('l1_restart','l2_trim','l2_garden','circuit_reset','manual_heal','escalation'). `heal/__init__.py:297-301` logs `event_type="heal_feedback"` inside bare `except: pass` → IntegrityError swallowed, feedback lost. |
| self_monitoring.py dead | **CONFIRMED** | grep across src finds only the file itself. Zero imports. 244 lines dead. |
| heal system itself real | **CONFIRMED** | `heal/__init__.py` (685 lines): 7 diagnosis patterns, LLM escalation, action executor (restart, cooldown, pip_install, trim, garden_cleanup), circuit breaker, pre-heal snapshots, post-heal evaluation. Keep. |

---

## Proposal (minimal, stdlib-only, no new deps)

### A. Finish the honest anomaly layer (~4 files, ~50 lines)
1. `tokens.py:76-78` — replace `compute_anomaly()` stub with rolling z-score: last 30 token turns for agent, z = (current − mean) / max(stdev, 1). Return None under 5 samples (cold start). ~15 lines, `statistics` stdlib.
   ponytail: z-score assumes near-normal; token bursts are heavy-tailed. Upgrade: MAD (2 extra lines). Not needed for a flagging heuristic.
2. `tokens.py:81-101` — `log_token_turn` must return `{"cost": cost, "anomaly_score": ..., "budget_alerts": []}`. This unbreaks `cli.py` without touching it.
3. Relabel: `risk_predictor.py:1` and `cli.py:1668` — "ML-based risk prediction" → "statistical risk analysis (rule-based)". Keep the file (imported by CLI); just stop lying in the label.
   Alternative (only if it's truly useless): route CLI risk commands to the DB-backed anomaly detectors. Verdict: relabel first, route later — the JSONL scanner has its own value for tool-level profiles.

### B. Honest memory-bloat signal (~2 files, ~40 lines)
1. `l2.py:52-70` — rename signal `memory_bloat` → `latency_drift`, module docstring + constants. 8 lines. (Kill the RSS claim; keep the latency heuristic.)
2. New `tracking/context_growth.py` (~30 lines): per-agent slope of `sum(memory_tokens + total_tokens)` over 7d from token_logs; flag when 7d projection exceeds context window (default 128K). Data already exists — no migration.
3. `db.py:157` — l2_trending CHECK is `('memory_bloat','stuck','drift','upstream_fail')`: new migration recreating the table with `latency_drift` added (SQLite can't ALTER CHECK). Keep old value for backward compat with existing rows.

### C. Wire L2 auto-heal (~3 files, ~35 lines)
1. `watch_consumers.py` — add `L2Consumer(BaseConsumer)`: interval 300s, tick calls `run_l2_scan`, publishes `l2_trends` on detection. Register in `register_all()`. Pattern identical to existing consumers.
2. `l2.py:110-120` — replace log-only resolution with real dispatch:
   - `graceful_restart` → `from observeco.heal import run_heal; run_heal(auto_heal=True, agent_name=...)` (heal's circuit breaker + cooldown are the guard rails).
   - `circuit_backoff` → `db.set_circuit_state(tripped=True, cooldown_until=now+300)`.
   - `sigabort` → needs PID lookup. ponytail: depends on agent launch mechanism (launchd/screen/pty). If PID lookup is out of scope, downgrade sigabort to log + escalate. Don't ship a kill without a verified PID mapping.
   - `db.resolve_l2_trend` after dispatch.
3. `db.py:345` — add `'heal_feedback'` to heal_events CHECK (migration required — see B3 pattern). Stop the silent loss.
4. Delete `self_monitoring.py` (244 lines, zero callers).

---

## Summary

| Item | Effort | Risk | Deps |
|---|---|---|---|
| A. compute_anomaly + return type + relabel | 45 min | Low — pure function, stdlib | none |
| B. rename memory_bloat→latency_drift + context_growth | 1.5 h | Low — read-only signal, no infra | none |
| C. L2Consumer + action dispatch + CHECK fix + delete dead file | 2 h | Medium — auto-restart touches prod agents; guard rails exist (circuit breaker, cooldown) | none |

**Honest ceilings (not building):**
- ML forecasting — needs a training pipeline; z-scores + rule heuristics cover the detection need.
- Real RSS memory profiling — pulse pipeline doesn't forward process RSS; requires agent-runtime change, not a code change here.
- Root-cause-aware auto-heal — causal tracing doesn't exist; heal stays pattern + escalation based.

**One runnable check to leave behind:** `compute_anomaly()` — assert-based self-check: feed a list of 30 known values, assert z-score math, assert None under 5 samples, assert TypeError impossible on log_token_turn return. One file, no framework.

---

## Verification note — Claude Code (sonnet 4.8)

Claude Code is currently gated: `claude auth status` shows authenticated API key (Seanfzc org), but `claude -p` returns "Credit balance is too low". This is billing, not auth — cannot be fixed from the terminal. Prompt saved at `docs/claude-verify-three-lies.md`; run when billing clears:
`cat docs/claude-verify-three-lies.md | claude -p "Read the prompt from stdin and execute it" --model sonnet --allowedTools "Read,Edit,Write,Bash" --max-turns 40 --dangerously-skip-permissions`
