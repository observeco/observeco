# ObserveCo: Realistic Capability Proposal

**Date:** 2 August 2026  
**Trigger:** Prior proposal over-promised three advanced capabilities. This document replaces that with what is genuinely buildable.

---

## Prior Over-Promise Acknowledgment

The original proposal described:

1. **ML-based risk predictions** as a trained-model system that learns degradation patterns and forecasts failures. In reality, the stack (SQLite telemetry, Python, no dedicated ML infra) supports *statistical thresholding*, not trained models. "ML" was oversold.

2. **Memory bloat detection** as an intelligent profiler that identifies unsustainable context growth. In reality, we can track growth *rates* from existing telemetry and flag thresholds — valuable, but not the deep introspection that "detection" implies.

3. **L2 auto-heal** as autonomous remediation. In reality, we can build *scripted responses to known failure signatures* — useful automation, but not adaptive self-healing.

What follows is three capabilities we **can** ship, with honest framing about what each tier requires.

---

## 1. Statistical Degradation Alerts (was "ML-based risk predictions")

### (a) Buildable Now — with existing data

The telemetry pipeline already captures per-agent latency, error rates, and throughput over time. We can compute:

- **Rolling baselines** — per-agent moving average and standard deviation over a configurable window (e.g., 30 data points / last 24 hours).
- **Deviation flags** — a point or short window exceeding N sigma above baseline triggers an alert.
- **Trend detection** — simple linear regression over recent windows to detect drift *before* it crosses a threshold. Not ML — just `scipy.stats.linregress` or a manual slope calculation.
- **Severity tiers** — mild (1.5σ), moderate (2σ), severe (3σ), each with different alert routing.

No new dependencies. SQLite can compute rolling aggregates in-query. Python stdlib + sqlite3 covers the math. The existing dashboard grid already displays per-agent metrics; the same data feed drives this.

**Limitation:** This is threshold-based, not predictive. It catches degradation *as it happens*, not *before* it happens. A genuine forecast (e.g., "this agent will degrade in 4 hours") requires a time series model.

### (b) Needs New Infrastructure

- **Time series forecasting model** (ARIMA, Prophet, or a small LSTM) — requires training pipeline, model versioning, and serving.
- **Feature engineering** — raw metrics → derived features (acceleration, cyclical patterns, cross-agent correlation).
- **Model evaluation loop** — backtesting against historical incidents to measure recall/precision.

Hard requirement: someone to own the ML lifecycle. Without a dedicated ML engineer or at minimum a scheduled retraining cron, a model rots within weeks and produces worse alerts than the simple statistical baseline.

### (c) First Milestone (< 1 week)

**Ship the statistical alert system as a canary runner variant.**

- Add a new canary runner mode: `degradation-scan`.
- Query: per-agent rolling μ and σ from the last N runs in the telemetry DB.
- Flag: any agent whose latest run deviates >2σ from its own baseline.
- Output: a JSON report and an optional webhook POST to the configured alert channel.
- Expose as a cron schedule (`every 30m`).

Deliverable: a working CLI invocation (`hermes canary run --mode degradation-scan`) that produces actionable output using only existing data. No model, no training, no new infra. Value ships day 1.

---

## 2. Context Growth Tracking (was "Memory bloat detection")

### (a) Buildable Now — with existing data

If agent sessions store context/memory size (token count, message count, or byte-size of stored memory), we can:

- **Track growth rate** — per-agent slope of context size over time (last N sessions).
- **Threshold alerts** — flag agents whose context has grown past a configurable ceiling.
- **Growth acceleration** — second-derivative check: is the growth *rate itself* growing? That's the real bloat signal.
- **Per-provider/per-model breakdown** — some models accumulate context faster than others; comparing rates identifies model-level issues vs. agent-level issues.

All of this is SQL-aggregatable. If the data isn't being collected yet, the first step is adding a telemetry column for `context_size_bytes` or `message_count` at session end — a one-line instrumentation change.

### (b) Needs New Infrastructure

- **Heap/memory profiling** — actual memory bloat detection requires process-level instrumentation (tracemalloc, objgraph, or a sampling profiler), not just context-size tracking.
- **Object-level retention analysis** — which objects are being held, by what reference? This is deep Python runtime introspection, not telemetry.
- **Automated garbage collection tuning** — adjusting GC thresholds per agent workload.

These are genuine "memory bloat detection" features and they require either an agent-side profiler daemon or post-hoc core-dump analysis. Neither exists in the current stack.

### (c) First Milestone (< 1 week)

**Context growth dashboard panel + alert.**

- Instrument: add `context_size` to the telemetry payload on session close (one field, trivial).
- Query: per-agent growth rate over last 7 days, sorted by slope descending.
- Dashboard: a new panel showing the top 5 fastest-growing agents with their growth curve as a sparkline or simple table.
- Alert: if any agent exceeds 2× its average growth rate, flag it in the daily summary.

Deliverable: a dashboard view that makes bloat *visible*. The human decides what to do about it. This is honest: we're surfacing the signal, not pretending to fix it autonomously.

---

## 3. Scripted Remediation Playbooks (was "L2 auto-heal")

### (a) Buildable Now — with existing data

Auto-heal, honestly framed, means: *when we detect a known failure pattern, run a pre-approved script.* This is achievable:

- **Failure → action mapping** — a JSON or YAML playbook file mapping condition → command. Example:
  - `error_rate > 0.5 AND agent = "fleet-scanner"` → `systemctl restart observeco-fleet`
  - `last_heartbeat > 1h AND agent_type = "worker"` → `kill -HUP <pid>` then restart
- **Guard rails** — max N auto-restarts per hour, cooldown period, require human review for novel failure signatures.
- **Audit log** — every auto-action logs what was detected, what was executed, and the outcome (did the next run succeed?).
- **Dry-run mode** — reports what it *would* do without executing, for confidence-building.

The existing canary system already detects failures. Closing the loop to remediation is a matter of adding an action executor behind the same detection pipeline.

### (b) Needs New Infrastructure

- **Root cause analysis** — genuine auto-heal requires understanding *why* something failed, not just pattern-matching on symptoms. This needs causal tracing across the stack.
- **Safe rollback** — if an auto-action makes things worse, we need automatic reversal. This requires state snapshots or infrastructure-as-code that can revert.
- **Confidence scoring** — ML classifier that estimates P(success | action, failure_signature) so we only auto-act when confidence is high.
- **Canary deployment of remediation** — test auto-actions on a subset of agents before rolling out.

These are L2 auto-heal in the genuine sense. We are not there.

### (c) First Milestone (< 1 week)

**Auto-restart on dead-agent detection.**

- Detect: agent hasn't reported a heartbeat in > N minutes (already tracked in telemetry or session DB).
- Act: restart the agent process via the existing launchd/hermes orchestration.
- Gate: max 3 restarts per agent per hour. Beyond that, escalate to human (webhook/Slack/email).
- Log: structured audit entry with timestamp, agent ID, detection reason, action taken, outcome.

Deliverable: a single `hermes autoheal --dry-run` / `hermes autoheal --live` command that detects dead agents and restarts them with guard rails. This is the 80/20 of L2 auto-heal — most production incidents are "process died, restart it." The remaining 20% (corrupted state, config drift, resource exhaustion) needs the infra we don't have yet.

---

## Summary

| Capability | Original Framing | Honest Framing | Ships In |
|---|---|---|---|
| Risk predictions | ML model forecasts failures | Statistical deviation alerts | < 1 week |
| Memory bloat detection | Intelligent profiler | Context growth tracking + dashboard | < 1 week |
| L2 auto-heal | Autonomous remediation | Scripted restart playbooks with guard rails | < 1 week |

All three first milestones use the existing stack (SQLite + Python + telemetry pipeline). None require new dependencies, new infrastructure, or trained models. Each produces a working artifact that delivers genuine operational value — just not the "intelligent autonomous system" the original proposal implied.

The gap between these milestones and the original vision is real and honest: ML forecasting, deep memory profiling, and root-cause-aware auto-heal all require infrastructure and staffing we don't currently have. This proposal doesn't close that gap — it acknowledges it and ships what's possible today.
