# Agent Quality Management — Methodology & Purpose

**Status:** Live — v0.5.0 "Capability Monitoring Layer"
**Last updated:** 2026-07-13
**Sources:** `agent-quality-management-brief.md`, `observeco-master-plan.md`, `obs-spec-051/052/057/060`, `capability/canary.py`, `capability/drift.py`, `capability/baseline.py`

---

## 1. Purpose — Why This Exists

ObserveCo's original question was **"Is my agent running?"** — liveness, tokens, errors, context bloat. Useful but insufficient.

The real question: **"Is my agent any good?"** Running ≠ working. An agent can be alive, within budget, zero errors — and producing garbage. Nobody answers this question.

**Agent Quality Management closes that gap.** It tells you:

- "I swapped models. Is my agent better or worse?"
- "My agent feels dumber. Is it real or in my head?"
- "Is this agent actually completing tasks successfully?"
- "Which of my 7 agents is the weakest link?"

No other tool answers these questions. Phoenix/LangFuse answer "what did the model return?" for developers during development. Nobody answers quality questions for operators running agents in production.

---

## 2. The Two-Instrument System

Sean redirected from a three-tier benchmark approach to a **two-instrument system** (2026-07-01):

| Instrument | What it does | When it runs | Cost |
|------------|-------------|--------------|------|
| **Canary** | Lightweight daily smoke test — 10 tasks × 10 trials across 7 capability dimensions | Daily (3am cron) | Low — small sample, fast |
| **Grid** | Deep model × config comparison — τ-bench + SWE-bench, multiple trials, Wilson CIs | On-demand (model swap, config change) | High — many cells, expensive |

**Why two instruments, not one:**
- Canary is cheap enough to run daily. Catches degradation fast.
- Grid is expensive but thorough. Answers "which model/harness is best?" definitively.
- Canary drift → triggers grid for confirmation. Grid results → update canary baselines.

---

## 3. Methodology — How It Works

### 3.1 Canary Benchmarks

**Task types** (10 built-in tasks across 7 dimensions):

| Category | Tasks | Difficulty |
|----------|-------|------------|
| reasoning | arithmetic-reasoning, chart-interpretation | easy, medium |
| coding | code-generation | hard |
| extraction | document-qa, extract-structured-data, summarize-conversation | medium, easy, medium |
| instruction_following | follow-multi-step-instructions, time-bound-response | medium, easy |
| tool_use | tool-selection | medium |

**Scoring — 8 assertion types:**

| Type | What it checks | Weight |
|------|---------------|--------|
| `exact_match` | Exact string match | 1.0 |
| `llm_judge` | LLM-as-a-Verifier (1-20 scale, K=3, logprob-based expected score) | 1.0 |
| `json_schema` | Valid JSON matching schema | 1.0 |
| `tool_call_validation` | Correct tool + args | 1.0 |
| `semantic_similarity` | Cosine similarity via sentence-transformers | 0.8 |
| `ordering` | Steps in correct sequence | 0.7 |
| `contains` | Keyword presence | 0.4 |
| `regex` | Pattern match | 1.0 |

**Statistical validity:**
- Default 10 trials per task (bootstrap CI requires n≥5)
- Wilson confidence intervals
- Per-task baselines (not aggregate — each task compared against its own history)
- Temperature=0.0 for reproducibility
- Dev/test split (3 dev, 6 test) prevents overfitting

### 3.2 Drift Detection

Continuous statistical comparison after every canary run:

```
After each canary run:
  → Compare per-task accuracy against that task's historical baseline
  → Z-test with config-aware baselines (config_hash = f(model, SOUL, skills))
  → Three thresholds: breach (alert), warning (flag), info (note)
  → Store drift_event in DB
```

**Config-aware baselines** prevent false alarms:
- Model swap → new baseline. No alert.
- SOUL.md change → new baseline. No alert.
- Same config, same workload, different behavior → **real drift. Alert.**

### 3.3 History-Assisted Task Generation (obs-spec-060)

Mines real agent conversations from `~/.hermes/state.db` to propose user-defined tasks:

```
suggest-tasks → mine Telegram sessions (3+ messages, last 30 days)
             → cluster by topic (keyword overlap)
             → LLM proposes task + assertions
             → User reviews/edits/approves in dashboard
             → Approved tasks run alongside generic tasks in daily canary
```

**Two-tier scoring:**
- **Generic:** 10 built-in tasks — measures model capability
- **User-defined:** N approved tasks — measures agent quality on actual work

**Why not fully automated:** LLM proposes, user disposes. The human review step is the ground truth anchor. Using past responses as "expected output" would benchmark against prior performance, not correctness.

### 3.4 Grid Runner (τ-bench + SWE-bench)

Deep comparison for model/harness decisions:

```
Models × configs × tasks × trials → per-cell scores with Wilson CIs
→ Trajectory flags (loops, shortcuts, unsafe actions)
→ "Read by pairing" — model and harness interact, never isolate
```

**7 harness configs:** baseline, timeout variants, feedback variants, context variants.

### 3.5 RQGM (Phase 5 — Not Yet Wired)

Demoted from central evaluation engine to **trajectory analysis hardener**. Grid's Wilson CIs handle statistical significance. Canary's tripwire handles degradation detection. RQGM's remaining role: tighten loop/shortcut/unsafe thresholds when agents learn to game trajectory flags.

---

## 4. The Verification Loop

```
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│ CANARY   │────▶│  DRIFT MONITOR   │────▶│ RE-BENCHMARK │
│ (daily)  │     │  (continuous)    │     │ (verify)     │
│          │     │                  │     │              │
│ Run once │     │ Track behavioral │     │ When drift   │
│ to get   │     │ fingerprint with │     │ detected →   │
│ baseline │     │ config-aware     │     │ run canary   │
│ score    │     │ baselines        │     │ to confirm   │
│          │     │ Free. No tokens. │     │              │
└──────────┘     └──────────────────┘     └──────────────┘
```

1. **Benchmark first** — get a score. User has a number that predicts real work.
2. **Drift monitor** runs continuously. Config-aware. Workload-clustered. Free.
3. **When drift fires** — "Agent Main: behavioral shift detected (same config, same workload)."
4. **Auto-trigger canary** — score unchanged → false alarm, update baseline. Score dropped → alert.

**Drift monitoring dimensions** (all from existing telemetry, zero tokens):
- Response length distribution
- Response structure (sections, code blocks, markdown)
- Tool usage frequency & type distribution
- Token efficiency (input/output ratio, cache hits)
- Error rate & type distribution
- Context utilization (window size, memory usage)
- Latency distribution
- Output embeddings — topic clustering

---

## 5. What's Built vs What's Pending

| Component | Status | Built by |
|-----------|--------|----------|
| Canary runner (task execution, scoring, baselines) | ✅ Live | Pragma |
| 10 built-in tasks across 7 dimensions | ✅ Live | Pragma |
| 8 assertion types (incl. llm_judge, json_schema, tool_call_validation) | ✅ Live | Pragma |
| Per-task drift with config-aware baselines | ✅ Live | Pragma |
| Drift detection (z-test, 3 thresholds) | ✅ Live | Pragma |
| History-assisted task generation (suggest-tasks) | ✅ Live | Pragma |
| Grid runner (τ-bench + SWE-bench) | ✅ Live | Pragma |
| Grid CLI (`observeco benchmark grid`) | ✅ Live | Pragma |
| Dashboard quality cards (fleet row + per-task chart) | ✅ Live | Pragma |
| GAIA task loader | ❌ Not built | — |
| Grid reporter (decision-aid tables) | ❌ Not built | — |
| Canary→grid synergy wiring | ❌ Not built | — |
| RQGM trajectory analysis | ❌ Not wired | — |
| Config-aware drift monitoring (full) | ❌ Not built | — |
| Behavioral fingerprint (output embeddings) | ❌ Not built | — |

---

## 6. Competitive Position

| What we do | Who else does it | Our edge |
|-----------|:---:|---------|
| Agent runtime health | No one | ✅ First |
| User-defined task benchmarks | No one | ✅ Tests actual job, not proxy tasks |
| Comparative (before/after) benchmarks | No one | ✅ Delta is more useful than absolute score |
| Behavioral drift monitoring (config-aware) | No one (academic only) | ✅ First to productize |
| Canary verification loop | No one | ✅ Drift + score drop = confirmed degradation |
| Fleet-wide quality comparison | No one | ✅ First |

**Category position:** "Agent Quality Management." Not "LLM evaluation" (DeepEval). Not "LLM tracing" (Phoenix/LangFuse). Not "infrastructure monitoring" (Datadog/Grafana). The empty space: **"Is my agent actually working well?"**

---

## 7. What We Don't Do

- **LLM-as-judge for every session** — too expensive, breaks local-first. Benchmarks have ground truth. Drift monitoring needs no judge.
- **Evaluation metrics from scratch** — DeepEval has 50+. We use theirs if needed.
- **Prompt management, datasets, playground** — Phoenix/LangFuse territory.
- **Blind model-centric benchmarking** — all results come with honest guidance: "This tests general reasoning, not your specific job."
