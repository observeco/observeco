# Honest Rebuild Proposal

What was claimed vs what exists vs what we should actually build.

---

## Item 1: Anomaly Detection ("ML-based risk predictions")

**Claimed:** Risk scoring pipeline using ML to detect anomalous agent turns.
**Exists:** `compute_anomaly()` at `tokens.py:76` is `def compute_anomaly(...): return None`. Dashboard has full anomaly UI (red columns, /api/anomalies route, anomaly-feed HTML). Server imports `from observeco.anomaly import detect_anomalies` — this module doesn't exist, would throw ImportError at runtime. CLI at `cli.py:1123` does `result = log_token_turn(...)` then accesses `result['anomaly_score']` — but `log_token_turn` returns `None`. The whole pipeline is a facade with dependent code that would crash if exercised.

**What to build:** Replace the stub with a rolling z-score. Stdlib only, no ML.

**Changes (3 files, ~40 lines total):**

1. **`tokens.py:76-78`** — Replace `compute_anomaly()` with a real rolling z-score:
   - Query last 30 token turns for this agent from DB
   - Compute `mean` and `stdev` of total_tokens
   - Return `(current - mean) / max(stdev, 1)` — a z-score
   - If fewer than 5 turns exist, return None (cold start)

2. **`tokens.py:81-101`** — Fix `log_token_turn` return type:
   - Currently returns `None` implicitly
   - CLI code expects `dict` with `cost`, `anomaly_score`, `budget_alerts`
   - Change to return `{"cost": cost, "anomaly_score": compute_anomaly(...), "budget_alerts": []}`
   - This unbreaks the CLI without any other changes

3. **Create `src/observeco/anomaly.py`** (~15 lines):
   - `detect_anomalies(db, lookback_minutes=60)` — queries token_logs WHERE recorded_at >= lookback AND abs(anomaly_score) > 2.0
   - Returns list of anomalous turns with agent_name, timestamp, tokens, score
   - This is what the server routes already import

**ponytail:** Rolling z-score assumes token counts are roughly normal. LLM token usage can be heavy-tailed (bursts are real). Upgrade path: switch to MAD (median abs deviation) — `from statistics import median; mad = median(abs(x - median(x)) for x in series)` — 2 extra lines, outlier-robust.

---

## Item 2: Memory Bloat Detection

**Claimed:** L2 proactive monitoring detects RSS memory growth >5%/h for 3+ consecutive samples.
**Exists:** L2 scan at `l2.py:52-70` has a "memory_bloat" signal that reads `latency_ms` from pulses and calls it memory growth. The comment says "Memory bloat — RSS growth trend" but the code reads `latency_ms`. The pulse_log table has NO `memory_rss` column — just `latency_ms`, `status`, `error_message`, `metadata`. This is a straight mislabel.

**What to build:** Option A first (rename, fixes the lie today). Option B as capability upgrade.

### Option A (Admit the lie, rename to what it is)

**1 file, ~8 lines changed:**

**`l2.py:52-70`** — Change `memory_bloat` trend type to `latency_drift`:
- Line 52: `"# 1. Memory bloat — RSS growth trend"` → `"# 1. Latency drift — response time growth trend"`
- Line 61: `"memory_bloat"` → `"latency_drift"`
- Line 7: Update module docstring
- Lines 22-23: `MEMORY_BLOAT_PCT` → `LATENCY_DRIFT_PCT`, `MEMORY_BLOAT_SAMPLES` → `LATENCY_DRIFT_SAMPLES`

**`db.py:157`** — Update CHECK constraint to include `latency_drift`:
- SQLite can't ALTER CHECK, so: add migration to recreate l2_trending table with added value, OR just extend the CHECK to include both (backward compat with existing rows that say `memory_bloat`)
- Simpler: leave CHECK loose — since this is an existing table with rows, don't break existing data. Just use the string `latency_drift` and let the old `memory_bloat` rows coexist.

### Option B (Real memory detection — follow-up)

Requires pulse data source to capture process RSS. Hermes agents write pulse JSON files that could include `psutil` data, but the proxy/OTel pipeline doesn't forward it. Full pipeline:
1. Add `memory_rss` to pulse_log table schema (new migration)
2. Forward RSS from Hermes agent pulse files through the proxy
3. Change L2 scan to read `memory_rss` instead of `latency_ms`

**Not building now.** This is an infrastructure change, not a code change.

---

## Item 3: L2 Heal Auto-Action Execution

**Claimed:** L2 auto-actions (graceful_restart, sigabort, circuit_backoff) execute automatically when trends are detected.
**Exists:** `run_l2_scan()` at `l2.py:30-125` detects trends and logs them to l2_trending. But:
- `run_l2_scan()` is NEVER called from any consumer or daemon loop
- Lines 110-120 resolve trends with a comment: `"# actual execution would happen in heal.py integration"`
- The HealConsumer checks for dead agents (L1 heartbeat) but never invokes L2
- Auto-actions are logged to DB but the actual actions (restart, kill, backoff) never fire

**What to build:** Wire `run_l2_scan()` into the daemon via a consumer. Then make auto-actions real.

**Changes (2 files, ~20 lines total):**

1. **`watch_consumers.py`** — Add `L2Consumer` and register it:
```python
class L2Consumer(BaseConsumer):
    """Proactive L2 trend scanning — memory/latency/drift/upstream detection."""
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "l2")
        kwargs.setdefault("interval", 300)  # 5 min
        super().__init__(**kwargs)

    def _tick(self) -> None:
        from observeco.heal.l2 import run_l2_scan
        detected = run_l2_scan(db=self.db)
        if detected:
            publish(None, "l2_trends", count=len(detected))
```
- Add `L2Consumer(db=self.db)` to `register_all()` (1 line)

2. **`l2.py:110-120`** — Replace passive resolution with real action:
```python
unresolved = db.get_l2_trends(agent_name, limit=10)
unresolved_active = [t for t in unresolved if not t["resolved"]
                     and t["severity"] == "critical"]
for trend in unresolved_active:
    action = trend["auto_action"]
    if action == "graceful_restart":
        from observeco.heal import run_heal
        run_heal(auto_heal=True, agent_name=trend["agent_name"])
        # Already resolved by the heal; skip resolution here
    elif action == "sigabort":
        # Kill + restart the agent process
        pid = find_agent_pid(trend["agent_name"])  # ponytail: needs pid lookup
        if pid:
            os.kill(pid, signal.SIGABRT)
    elif action == "circuit_backoff":
        db.set_circuit_state(trend["agent_name"], tripped=True,
                             cooldown_until=int(time.time()) + 300)
    db.resolve_l2_trend(trend["id"], f"auto_action:{action}")
```

**ponytail:** The `sigabort` action needs `find_agent_pid()` which doesn't exist yet — depends on how agents are launched (screen/tmux/launchd/systemd). `graceful_restart` and `circuit_backoff` are fully wired. Upgrade: add process registry or agent PID tracking.

---

## Summary Table

| Item | Today's Lie | Honest Fix | Files Changed | Lines |
|------|------------|------------|---------------|-------|
| Anomaly | `return None` stub | Rolling z-score + fix return type + create anomaly.py | 3 | ~40 |
| Memory bloat | Latency mislabeled as RSS | Rename to `latency_drift` (Option A) | 1 | ~8 |
| L2 heal | Actions logged but never executed | L2Consumer + real action dispatch | 2 | ~20 |

**Not building this session:**
- Real RSS memory detection (requires pulse pipeline changes)
- ML models for anomaly detection (not needed — z-score catches token spikes)
- An orchestrator daemon (consumer pattern already handles threading and intervals)
