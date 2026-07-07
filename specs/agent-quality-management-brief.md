# ObserveCo: Agent Quality Management — Product Brief

**Status:** Active build. Two instruments live (Canary + Grid). RQGM demoted to Phase 5.
**Date:** 2026-06-30
**Updated:** 2026-07-02 (post-redirect: Canary+Grid architecture, RQGM re-scoped)
**Context:** Evolution from "agent observability" (passive monitoring) to "agent quality management" (active quality assessment). Informed by competitive analysis, Reddit pain-point research, Agent Drift paper (arxiv:2601.04170), and Sean's strategic direction.

## Architecture Evolution (2026-07-01)

Sean redirected from the original three-tier benchmark approach to a **two-instrument system**:

| Old Plan | New Plan | Why |
|----------|----------|-----|
| Replace engine with lm-eval-harness | Keep existing engine for canary, build grid separately | lm-eval tests models. We're testing agent *systems* — model × harness config × task |
| Quiz benchmarks (MMLU, GSM8K) | Agentic benchmarks (SWE-bench, τ-bench, GAIA) | Quiz tasks measure recall. Grid tasks measure execution |
| Suite-level average scores | Per-task, per-cell, with confidence intervals | Averaging hides the interaction |
| "Harness is worth +X%" claim | Grid read by pairing, not isolated component | Model and harness interact |
| LLM judge scoring | Trajectory analysis — shortcuts, loops, unsafe actions | Scoring the output misses how the agent got there |
| RQGM as central evaluation engine | RQGM as trajectory analysis hardener (Phase 5) | Grid's CIs + Canary's tripwire handle statistical significance and degradation detection |

## Current Build Status (2026-07-02)

| Component | Status | Built By | Notes |
|-----------|:------:|:--------:|-------|
| **Canary** (lm-eval backend) | ✅ Built | Pragma | 9 tasks across 7 dimensions, 15/50 sample modes. `observeco benchmark run --suite canary` |
| **Grid runner** (τ-bench) | ✅ Built | Pragma | `grid/runner.py` + `grid/tau_adapter.py`. Iterates models × configs × tasks × trials |
| **Grid runner** (SWE-bench) | ✅ Built | Pragma | `grid/swe_adapter.py`. Patch generation through Hermes harness |
| **Grid configs** | ✅ Built | Pragma | 7 harness configs: baseline, timeout variants, feedback variants, context variants |
| **Grid CLI** | ✅ Built | Pragma | `observeco benchmark grid` command |
| **GAIA task loader** | ❌ Not built | — | Pending Phase 3 |
| **Grid reporter** (decision-aid tables) | ❌ Not built | — | Pending Phase 4 |
| **Synergy wiring** (canary→grid trigger) | ❌ Not built | — | Pending Phase 5 |
| **RQGM → trajectory analysis** | ❌ Not wired | — | Pending Phase 5. rqgm-core package exists, 4 cron jobs in error state |
| **Drift monitoring** | ❌ Not built | — | Separate workstream. Config hashing, workload clustering, baseline versioning |
| **Dashboard quality cards** | ❌ Not built | — | Separate workstream |

---

## 1. The Problem

Current ObserveCo answers one question: **"Is my agent running?"** It shows liveness, token usage, error counts, context bloat. This is useful but insufficient.

The question users actually care about is: **"Is my agent any good?"** Running ≠ working. An agent can be alive, within budget, zero errors — and producing garbage. Nobody answers this question.

**The gap:** Every agent operator has these questions and no tool answers them:

- "I swapped models. Is my agent better or worse?"
- "My agent feels dumber. Is it real or in my head?"
- "Is this agent actually completing tasks successfully?"
- "Which of my 7 agents is the weakest link?"

Phoenix/LangFuse answer "what did the model return?" for developers during development. Nobody answers quality questions for operators running agents in production.

---

## 2. The Product

**Agent Quality Management — know if your agents are actually working.**

Two complementary mechanisms:

### Mechanism A: Benchmarks (The Truth Anchor)

Run tasks against the agent's actual harness (model + SOUL + skills + tools). Get a score. Three benchmark types, from most valid to most general:

#### Primary: User-Defined Task Benchmarks

The user defines tasks that match their actual workload. **This is the most valid benchmark type** — it tests the agent's real job, not a proxy.

```bash
observeco benchmark create-task --agent hermes-main \
  --input "Review this code for security issues" \
  --context "./example_code.py" \
  --expected "Must identify SQL injection on line 42 and XSS on line 78"
```

**Scoring:** LLM compares agent output to expected output. Partial credit. Confidence score based on task count.

| Aspect | Assessment |
|--------|-----------|
| **Validity for real agents** | ✅ High — tests the agent's actual job. Score directly predicts real performance. |
| **Predictive power** | ✅ High — same task, same harness, same context. |
| **Setup cost** | 🔴 User must define tasks + expected outputs. |
| **Generalizability** | 🔴 Limited to the user's specific tasks. Can't compare across users. |

#### Secondary: Curated Model Benchmarks (MMLU, GSM8K, etc.)

Run established model benchmarks through the agent's harness. These were designed for models, not agent systems — scores should be treated as a **comparative signal, not a performance guarantee.**

```bash
observeco benchmark --agent hermes-main --suite mmlu-canary
```

**Guidance we provide to users:**
- "MMLU scores measure general reasoning, not your agent's specific job. An agent that scores 90% on MMLU can still fail at code review."
- "Use these for before/after comparison (model swap, SOUL change) — not for absolute performance claims."
- "Run user-defined task benchmarks for the signal that matters."

| Aspect | Assessment |
|--------|-----------|
| **Validity for real agents** | 🟡 Moderate — tests general capability, not job-specific performance. |
| **Predictive power** | 🟡 Low for specific tasks. Useful for detecting large capability gaps. |
| **Setup cost** | ✅ Low — pre-built, curated, canary subsets ready. |
| **Generalizability** | ✅ High — same benchmarks, all users. Enables cross-user comparison. |
| **Human psychology** | ✅ High — users want a number. 87% is concrete even if imperfect. |

#### Tertiary: Comparative Benchmarking (Before/After)

Same benchmark, before/after a change. The absolute score is weak. The **delta is strong.**

```bash
observeco benchmark --agent hermes-main --suite reasoning --compare
# deepseek-v4-pro:   87% (13/15) [current]
# qwen3-coder:480b:  80% (12/15) [↓7%]
```

| Aspect | Assessment |
|--------|-----------|
| **Validity** | ✅ High — delta is meaningful even if absolute score isn't. |
| **Best use** | Model swaps, SOUL updates, skill changes. "Did this change make things better or worse?" |

### Mechanism B: Behavioral Drift Monitoring (The Early Warning)

Continuously track the agent's behavioral fingerprint — response patterns, tool usage, token efficiency, error rates, output embeddings. Alert when the fingerprint shifts significantly **without an intentional config change and within the same workload type.**

#### The Noise Problem

| Change | Fingerprint shifts? | Should we alert? | Why |
|--------|:------------------:|:----------------:|-----|
| Model swapped | ✅ | ❌ | Intentional. New baseline. |
| SOUL.md updated | ✅ | ❌ | Intentional. New baseline. |
| Skills changed | ✅ | ❌ | Intentional. New baseline. |
| Workload shifted (code → docs) | ✅ | ❌ | Different task type. Compare within workload clusters only. |
| Agent degrading silently | ✅ | ✅ | **This is the signal.** Same config, same workload, different behavior. |
| Session variance | ❌ | ❌ | Random noise. Ignore. |

#### The Fix: Baseline Versioning

Drift monitoring doesn't compare against a single static baseline. It compares against **the baseline for the current configuration and workload.**

```
Baseline = f(config_hash, workload_type)

Where:
  config_hash = hash(model + SOUL.md + skills + system prompt)
  workload_type = cluster(session_input_embeddings)
```

**When config changes** → new baseline. Old baseline archived. No alert.

**When workload shifts** → sessions routed to different workload cluster. Comparisons stay within-cluster.

**When fingerprint shifts with same config and same workload** → drift detected. Trigger canary verification.

#### Drift → Canary Verification Loop

Drift detection triggers a canary benchmark. Drift alone is noise. Drift + score drop is signal.

```
Drift detected → auto-trigger canary benchmark
                → score unchanged → false alarm, update baseline
                → score dropped   → alert with cause analysis
```

**Dimensions tracked** (all from existing telemetry, no tokens):
- Response length distribution (mean, variance)
- Response structure (sections, code blocks, markdown)
- Tool usage frequency & type distribution
- Token efficiency (input/output ratio, cache hits)
- Error rate & type distribution
- Context utilization (window size, memory usage)
- Latency distribution
- Output embeddings — topic clustering (sentence-transformers)

**Why drift monitoring:** It's free, continuous, and catches degradation between benchmarks. Continuous canary benchmarks are too expensive. Continuous drift monitoring costs nothing.

**Why it needs verification:** Drift is not always degradation. The canary check separates signal from noise.

---

## 3. How They Work Together

```
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│ BENCHMARK│────▶│  DRIFT MONITOR   │────▶│ RE-BENCHMARK │
│ (setup)  │     │  (continuous)    │     │ (verify)     │
│          │     │                  │     │              │
│ Run once │     │ Track behavioral │     │ When drift   │
│ to get   │     │ fingerprint with │     │ detected →   │
│ baseline │     │ config-aware     │     │ run canary   │
│ score    │     │ baselines        │     │ to confirm   │
│          │     │ Free. No tokens. │     │              │
└──────────┘     └──────────────────┘     └──────────────┘
```

1. **Benchmark first** — get a score. "87% on user-defined tasks." User has a number that predicts real work.
2. **Drift monitor** runs continuously. Config-aware. Workload-clustered. Free.
3. **When drift fires** — "Agent Main: behavioral shift detected (same config, same workload). Output length -40%, tool usage recategorized. Running accuracy check..."
4. **Auto-trigger canary** — score unchanged → false alarm, update baseline. Score dropped → alert.

---

## 4. The Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BENCHMARK TYPES                           │
│                                                              │
│  PRIMARY: User-defined task benchmarks                       │
│  → User creates tasks with expected output                   │
│  → Highest validity. Tests actual job.                       │
│                                                              │
│  SECONDARY: Curated model benchmarks (MMLU, GSM8K, BFCL...)  │
│  → Pulled from HuggingFace/GitHub                             │
│  → Canary subsets: 10-20 tasks per suite                     │
│  → Honest guidance: comparative signal, not performance      │
│    guarantee                                                 │
│                                                              │
│  TERTIARY: Comparative (before/after same benchmark)         │
│  → Delta is meaningful even if absolute score isn't          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    HARNESS ADAPTER (NEW)                      │
│  Takes benchmark task → formats for agent → collects response│
│  → scores against ground truth or expected output → stores   │
│  Adapters: Hermes first, then Claude Code, OpenAI, etc.      │
│  ~300 lines per adapter (handles multi-benchmark types)      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
|                    RQGM EVALUATION (PHASE 5 — NOT YET WIRED)                 |
|  Demoted from central evaluation engine to trajectory analysis hardener.   |
|  Grid's Wilson CIs handle statistical significance.                       |
|  Canary's tripwire + observability handle degradation detection.          |
|  RQGM's remaining role: tighten loop/shortcut/unsafe thresholds            |
|  when agents learn to game trajectory flags.                              |
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         CONFIG-AWARE BEHAVIORAL DRIFT MONITORING (NEW)       │
│                                                              │
│  Baseline versioning:                                        │
│  • config_hash → new baseline on SOUL/model/skill change     │
│  • workload_type → clusters by input embedding similarity    │
│                                                              │
│  Dimensions tracked (all from existing telemetry):           │
│  • Response length distribution                              │
│  • Response structure (sections, code blocks, markdown)      │
│  • Tool usage frequency & type distribution                  │
│  • Token efficiency (input/output ratio, cache hits)         │
│  • Error rate & type distribution                            │
│  • Context utilization (window size, memory usage)           │
│  • Latency distribution                                      │
│  • Output embeddings — topic clustering (sentence-transform) │
│                                                              │
│  ~750 lines (config hashing + workload clustering + drift)   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         CANARY VERIFICATION LOOP (NEW — thin)                │
│  Drift detected → auto-trigger canary benchmark              │
│  Score unchanged → false alarm → update baseline             │
│  Score dropped → degradation confirmed → alert               │
│  ~100 lines (scheduler + integration glue)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              OBSERVECO MONITORING (EXISTING)                  │
│  Baselines: benchmark scores + behavioral fingerprints        │
│  Anomaly detection: "quality_score_drop" + drift flags       │
│  Alerts: push when quality degrades                          │
│  Dashboard: quality scores alongside health & cost            │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. What We Build vs. What We Use

| Component | Build/Use | Effort | Notes |
|-----------|:---------:|--------|-------|
| User task benchmark engine | Built | ~300 lines | lm-eval-harness backend. 9 tasks across 7 dimensions. Canary + full suites. |
| Benchmark ingestion (curated) | Built | ~100 lines | Pulled from lm-eval-harness task library. Canary subsets: 15 samples/task. |
| Harness adapter (Hermes) | Built | ~300 lines | HermesAgentLM adapter for lm-eval. Also: direct model + LiteLLM adapters. |
| Scoring engine | Built | ~200 lines | lm-eval metrics (exact_match, f1, acc). Legacy keyword overlap kept for compat. |
| Canary subset selection | Built | ~100 lines | 9 tasks across 7 dimensions. 15/50 sample modes. |
| Benchmark CLI | Built | ~250 lines | `observeco benchmark run --suite canary --agent <name>` with --direct and --litellm modes. |
| Grid runner (τ-bench) | Built | ~300 lines | `grid/runner.py` + `grid/tau_adapter.py`. Models × configs × tasks × trials. |
| Grid runner (SWE-bench) | Built | ~250 lines | `grid/swe_adapter.py`. Patch generation through Hermes harness. |
| Grid configs | Built | ~130 lines | 7 harness configs: baseline, timeout, feedback, context variants. |
| Grid CLI | Built | ~100 lines | `observeco benchmark grid` command. |
| GAIA task loader | Not built | ~200 lines | Pending Phase 3. |
| Grid reporter (decision-aid tables) | Not built | ~100 lines | Pending Phase 4. Per-task CI, cost, trajectory. |
| Synergy wiring (canary→grid trigger) | Not built | ~50 lines | Pending Phase 5. |
| RQGM → trajectory analysis | Not wired | ~50 lines | Phase 5. rqgm-core exists, 4 cron jobs in error state. |
| Config hashing + baseline versioning | Not built | ~100 lines | Separate workstream. |
| Workload clustering | Not built | ~200 lines | Separate workstream. |
| Behavioral fingerprint | Not built | ~250 lines | Separate workstream. |
| Drift detection | Not built | ~300 lines | Separate workstream. |
| Output embedding | Not built | ~150 lines | Separate workstream. |
| Canary verification scheduler | Not built | ~100 lines | Separate workstream. |
| Baseline extension | Not built | ~50 lines | Separate workstream. |
| Anomaly extension | Not built | ~100 lines | Separate workstream. |
| Dashboard quality cards | Not built | ~400 lines | Separate workstream. |
| User task templates | Not built | ~100 lines | Separate workstream. |
| Guidance system | Not built | ~100 lines | Separate workstream. |
| Benchmark library | **Curate, not build** | 0 code | MMLU, GSM8K, BFCL, HumanEval, GAIA, MT-Bench |
| RQGM engine | **Existing** | 0 code | rqgm-core package at ~/projects/rqgm-core |
| Telemetry collection | **Existing** | 0 code | token_logs, pulse_log, errors, trace_spans |

**Total new code: ~2,900 lines + dashboard.** All thin layers on existing infrastructure.

---

## 6. The User Experience

### Creating a Task Benchmark

```bash
# Define a task that matches the agent's real job
$ observeco benchmark create-task --agent hermes-main \
  --name "code_review_sql_injection" \
  --input "Review this Python code for security issues" \
  --context "./examples/login_handler.py" \
  --expected "Must identify SQL injection on line 42, XSS on line 78, missing input validation on line 15"

Task created: code_review_sql_injection
```

### Running Benchmarks

```bash
# Primary: user-defined tasks
$ observeco benchmark --agent hermes-main --suite my-tasks
Running 5 user-defined benchmarks...
████████████████████ 5/5 complete

Agent: hermes-main
⸻ User Tasks ⸻
Score: 0.80 (4/5 correct)
Confidence: 0.85 (sample: 5 tasks)
Model: deepseek-v4-pro

⸻ MMLU Canary ⸻
Score: 0.87 (13/15 correct)
Confidence: 0.89 (sample: 15 tasks)
⚠️  Model-centric benchmark. Scores test general reasoning, not your agent's
    specific job. Use 'my-tasks' results for decisions about this agent.

Baseline saved.
```

### Dashboard

The fleet view gains a **Quality** column alongside existing Health and Cost:

| Agent | Health | Quality | Cost (7d) |
|-------|:------:|:-------:|----------:|
| Hermes Main | 🟢 Alive | 80% (—) | $0.12 |
| Kepler | 🟢 Alive | 78% (↓12%) | $0.45 |
| Dreamer | 🟡 Drift | 72% (↓8%) | $0.08 |

Click Kepler → see: "User-task score dropped from 90% to 78% over 14 days. Drift detected: output length -35%, tool usage recategorized (same config, same workload cluster). Verification canary confirmed degradation (83% confidence). Correlated: model swap on 2026-06-25. Recommendation: re-benchmark or rollback model."

### Alert (Telegram)

```
🟡 Kepler Quality Degradation

User-task score: 90% → 78% (14-day trend)
Confidence: 0.83 (drift + canary verification confirmed)

Correlated signals:
• Model swap: qwen3-coder → deepseek-v4-flash (2026-06-25)
• Output length: -35% (within same workload cluster)
• Tool usage pattern: recategorized (same config)

Recommendation: Run full benchmark or rollback model.

$ observeco benchmark --agent kepler --suite my-tasks
```

---

## 7. Model-Harness Compatibility

A natural extension of comparative benchmarking: run the SAME benchmark suite with DIFFERENT models against the SAME agent.

```bash
$ observeco benchmark --agent hermes-main --suite my-tasks --compare
Comparing models for hermes-main on your tasks...

deepseek-v4-pro:   0.80 (4/5) [current]
qwen3-coder:480b:  0.80 (4/5) [—]
gemma4:31b:        0.40 (2/5) [↓50%]
MMLU canary:
deepseek-v4-pro:   0.87 (13/15)
qwen3-coder:480b:  0.80 (12/15)
gemma4:31b:        0.53 (8/15)
⚠️  MMLU scores test general reasoning, not your specific tasks.
    Use 'my-tasks' delta for model selection decisions.

Best fit for your tasks: deepseek-v4-pro (equal to qwen3-coder for these tasks)
Recommendation: Either model works. Choose based on cost/latency.
```

This answers the question no tool answers today: "Is this model right for my agent's actual job?" Not abstract benchmarks. Real results from real tasks on the real harness.

---

## 8. Competitive Position

| What we do | Who else does it | Our edge |
|-----------|:---:|---------|
| Agent runtime health | No one | ✅ First |
| Cost tracking | Codeburn, AgentTrace | ✅ Integrated |
| Context/memory monitoring | No one | ✅ First |
| User-defined task benchmarks | No one | ✅ Tests actual job, not proxy tasks |
| Comparative (before/after) benchmarks | No one | ✅ Delta is more useful than absolute score |
| Behavioral drift monitoring (config-aware) | No one (academic only) | ✅ First to productize |
| Canary verification loop | No one | ✅ Drift + score drop = confirmed degradation |
| Model-harness compatibility via user tasks | No one | ✅ Tests real agent, not abstract function calling |
| Fleet-wide quality comparison | No one | ✅ First |

**Category position:** "Agent Quality Management." Not "LLM evaluation" (DeepEval owns that). Not "LLM tracing" (Phoenix/LangFuse own that). Not "infrastructure monitoring" (Datadog/Grafana own that). The empty space: "Is my agent actually working well?"

---

## 9. What We Don't Build

- **LLM-as-judge pipeline for every session.** Too expensive, breaks local-first, requires cloud API. Benchmarks have ground truth or user-defined expected outputs. Drift monitoring needs no judge.
- **Evaluation metrics from scratch.** DeepEval has 50+. We use theirs if needed. We don't rebuild.
- **Prompt management, datasets, playground.** Phoenix/LangFuse's territory. Not our fight.
- **Blind model-centric benchmarking without guidance.** We offer curated benchmarks but with honest pros/cons. Users choose. We don't pretend MMLU predicts real agent performance.

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:---------:|:------:|-----------|
| Model benchmarks misinterpreted by users | High | Users trust wrong signal | Honest guidance in CLI output + dashboard. "This tests general reasoning, not your job." |
| User-defined tasks require setup effort | High | Low adoption of primary feature | Task templates for common agent roles. Import/export. Community library. |
| Drift ≠ degradation (false alarms) | Medium | Alert fatigue | Config-aware baselines reduce noise. Canary verification before alerting. |
| Workload clustering mis-classifies sessions | Medium | Drift checks compare wrong sessions | Embedding similarity threshold. Minimum cluster size before monitoring. |
| Cold start (no history for new agent/config) | Medium | No drift baseline | Require initial benchmark. Minimum 7 days or 50 sessions before drift monitoring activates. |
| Embedding dependency (sentence-transformers) | Low | New dependency | Lightweight (all-MiniLM-L6, 80MB). Local. No API. Established library. |
| DeepEval/competitor ships similar | Medium | Category blur | Move fast on config-aware drift + canary verification — they're the defensible pieces. |

---

## 11. Next Steps

1. ✅ **Build user-defined task benchmark engine.** lm-eval-harness backend. 9 tasks across 7 dimensions. Canary + full suites. Built by Pragma.
2. ✅ **Build harness adapter (Hermes).** HermesAgentLM adapter for lm-eval. Direct model + LiteLLM adapters also built.
3. ✅ **Build curated benchmark ingestion.** Pulled from lm-eval-harness task library. Canary subsets: 15 samples/task.
4. ✅ **Build grid runner (τ-bench + SWE-bench).** Models × configs × tasks × trials. Wilson CI. Trajectory flagging. Built by Pragma.
5. 🔴 **Benchmark Methodology Upgrade (obs-spec-057).** LLM-as-judge, reference outputs, per-task drift fix, temperature control, concrete fixtures, dev/test split. **Critical — current assertions are too weak for meaningful quality claims.** ETA v0.6.0.
6. ❌ **Build GAIA task loader.** Pending Phase 3.
7. ❌ **Build grid reporter (decision-aid tables).** Per-task CI, cost, trajectory. Pending Phase 4.
8. ❌ **Wire synergy (canary→grid trigger + RQGM trajectory hardening).** Pending Phase 5.
9. ❌ **Build config-aware drift monitoring.** Config hashing, baseline versioning, workload clustering. Separate workstream.
10. ❌ **Design dashboard quality cards.** Benchmark scores, drift flags, comparative views, guidance tooltips.
11. ❌ **Dogfood on Sean's fleet.** Create user-defined tasks for each agent. Run benchmarks. Monitor drift. Tune thresholds before public launch.
12. ❌ **Update competitive analysis and README.** Reposition from "agent observability" to "agent quality management."
