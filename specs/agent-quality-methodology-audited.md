# Agent Quality Management — Methodology, Audit & Gaps

**Status:** Independent audit of `agent-quality-methodology.md` (2026-07-13)
**Auditor:** Main (Hound profile)
**Scope:** Full methodology review against live code (`canary.py`, `baseline.py`, `drift.py`), specs (051/052/057/060), master plan, and industry standards
**Verdict:** Architecture is sound and category-leading. Several statistical and methodological gaps need addressing before public quality claims are defensible.

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

**Scoring formula:** `task_score = weighted_average(assertion_scores, weight_by_type)`. Each assertion produces a binary pass/fail (accuracy 0.0 or 1.0). The weighted average combines all assertions for a task into a single accuracy score.

**Statistical validity:**
- Default 10 trials per task (bootstrap CI requires n≥5)
- Wilson confidence intervals
- Per-task baselines (not aggregate — each task compared against its own history)
- Temperature=0.0 for reproducibility
- Dev/test split (3 dev, 6 test) prevents overfitting

### 3.2 Drift Detection

Two separate drift systems exist:

**System A — Canary accuracy drift (obs-spec-052, capability layer):**
Statistical comparison after every canary run. Two-sample z-test for proportions.

```
After each canary run:
  → Compare per-task accuracy against that task's historical baseline
  → Z-test: z = |p_baseline - p_current| / SE, where SE = sqrt(p_pool(1-p_pool)(1/n1 + 1/n2))
  → p-value from two-tailed normal CDF (Abramowitz & Stegun approximation)
  → Three thresholds: breach (drift≥5pp, p<0.01), warning (drift≥3pp, p<0.05), info (drift≥1pp)
  → Store drift_event in DB with severity + breached task list
```

**System B — Token composition drift (obs-spec-052, watch daemon layer):**
Tracks token bloat per component (identity, skills, memory, tools, guidance). Three independent methods:

| Method | Formula | Catches |
|--------|---------|--------|
| Rolling (A) | `(current - week_avg) / max(week_avg, 50) * 100` | Sudden changes (restarts, config edits) |
| Week-over-Week (B) | `(this_week_avg - last_week_avg) / max(last_week_avg, 50) * 100` | Sustained growth (compounding cost) |
| Absolute (C) | `current - week_avg` (raw tokens) | Honest cost visibility |

**Config-aware baselines** prevent false alarms:
- Model swap → new config_hash → new baseline. No alert.
- SOUL.md change → new config_hash → new baseline. No alert.
- Same config_hash, same workload, different behavior → **real drift. Alert.**

**Config hash implementation:** `sha256(agent_name + model + all_task_prompts)[:12]` — a 12-char fingerprint. Simple, fast, sufficient for detecting model/prompt changes.

### 3.3 History-Assisted Task Generation (obs-spec-060)

Mines real agent conversations from `~/.hermes/state.db` to propose user-defined tasks:

```
suggest-tasks → mine Telegram sessions (3+ messages, last 30 days)
             → cluster by topic (keyword overlap — ponytail: naive, not embedding-based)
             → LLM proposes task + assertions
             → User reviews/edits/approves in dashboard
             → Approved tasks run alongside generic tasks in daily canary
```

**Two-tier scoring:**
- **Generic:** 10 built-in tasks — measures model capability
- **User-defined:** N approved tasks — measures agent quality on actual work

**Two-pass execution:** Generic tasks run via DirectModelAdapter (no tools). User-defined tasks run via HermesAdapter with `-p default` (full profile: skills, tools, SOUL.md). The `built_in` column on `canary_tasks` routes tasks to the correct pass.

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
| Config-aware drift monitoring (full behavioral fingerprint) | ❌ Not built | — |
| Behavioral fingerprint (output embeddings) | ❌ Not built | — |
| Canary→grid auto-trigger | ❌ Not built | — |

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

---

## 8. Independent Audit — Gaps & Weaknesses

This section is the independent review. Each gap is classified by severity and backed by code evidence.

### 8.1 Statistical Methodology Gaps

#### GAP-1: Z-test approximation is imprecise at small samples (Severity: MODERATE)

**What:** The z-test uses `p_value = 2 * (1 - _norm_cdf(z_score))` with an Abramowitz-Stegun CDF approximation. This is a polynomial approximation, not the exact Φ function.

**Why it matters:** At small sample sizes (n1=30-90 task-trials from 3-9 baseline runs × 10 trials), the z-test for proportions is already borderline. The approximation error compounds. For z-scores near the threshold boundary (z≈2.58 for p=0.01), approximation error of ±0.02 can flip the verdict.

**Code evidence:** `baseline.py:200-202` — `z_score = abs(p1 - current_accuracy) / se; p_value = 2 * (1 - _norm_cdf(z_score))`. The `_norm_cdf` function at line 320 uses a 5-term polynomial approximation with max error ~7.5e-8 — actually quite good. The real issue is the z-test itself: at n<100, Fisher's exact test or a permutation test would be more appropriate.

**Fix:** Either (a) use `scipy.stats.fisher_exact` for small samples (n<100) and z-test for larger, or (b) use a permutation test which is exact and distribution-free. Since we already have bootstrap resampling infrastructure, a permutation test adds ~20 lines.

#### GAP-2: Bootstrap CI uses random.choice (with replacement) but doesn't set a seed (Severity: LOW)

**What:** `bootstrap_ci()` at `canary.py:615` uses `random.choice(values)` for resampling but never calls `random.seed()`. Each run produces different CIs.

**Why it matters:** Non-reproducible CIs. Two runs of the same data give different intervals. This undermines the "temperature=0.0 for reproducibility" claim — the scoring layer is non-deterministic even if the model output is.

**Fix:** Add `random.seed(42)` (or configurable seed) at the top of `bootstrap_ci()`. One line.

#### GAP-3: Bootstrap CI returns (0.0, 0.0) when n<5 instead of reporting point estimate (Severity: LOW)

**What:** `canary.py:608-609` — `if len(values) < 5: return (0.0, 0.0)`. This means a CI of (0.0, 0.0) is ambiguous: it could mean "perfectly confident the value is 0" or "not enough data."

**Why it matters:** A dashboard showing CI=(0.0, 0.0) for a task that scored 0.8 is misleading. Users might interpret it as "the system is very confident the score is 0" rather than "not enough data for a CI."

**Fix:** Return `(None, None)` or `float('nan'), float('nan')` and render as "CI: insufficient data (n<N)" in the dashboard.

#### GAP-4: Per-task drift uses aggregate baseline as fallback when per-task baseline doesn't exist (Severity: MODERATE)

**What:** `baseline.py:229-230` — `task_base = self._get_per_task_baseline(...); task_base_acc = task_base["accuracy"] if task_base else baseline_accuracy`. When no per-task baseline exists (fewer than 3 runs with that task completed), it falls back to the aggregate baseline.

**Why it matters:** This is the exact bug obs-spec-057 §2.3 was supposed to fix. The fix is implemented but the fallback reintroduces the original problem: a hard coding task (50% baseline) compared against an aggregate (80% baseline including easy arithmetic tasks) will always show -30% drift — a false positive.

**Fix:** When no per-task baseline exists, report "no baseline yet" rather than showing drift against the aggregate. Skip that task from the breached_tasks list.

### 8.2 Methodology Gaps

#### GAP-5: Config hash doesn't include SOUL.md or skills (Severity: HIGH)

**What:** `canary.py:1112-1122` — `_compute_config_hash` hashes `agent_name + model + all_task_prompts`. It does NOT include the agent's SOUL.md, skills list, or system prompt.

**Why it matters:** The entire config-aware baseline system depends on detecting config changes. If an agent's SOUL.md is rewritten (changing behavior without changing the model), the config_hash stays the same. The system compares against the old baseline and flags drift — but this is an intentional change, not degradation. This is the exact false-alarm scenario the config-aware system was designed to prevent.

**The product brief says:** `config_hash = hash(model + SOUL.md + skills + system prompt)`. The code doesn't match the spec.

**Code evidence:** `canary.py:1118-1122`:
```python
model = tasks[0].get("model", "") if tasks else ""
prompts = "|".join(t.get("prompt", "") for t in tasks)
raw = f"{agent_name}:{model}:{prompts}"
return hashlib.sha256(raw.encode()).hexdigest()[:12]
```

No SOUL.md content. No skills list. No system prompt.

**Fix:** Read the agent's SOUL.md + active skills list + system prompt at canary run time and include them in the hash. ~15 lines of code. This is the single most important fix — without it, the config-aware baseline system is partially broken.

#### GAP-6: 10 built-in tasks don't cover multi-turn agentic behavior (Severity: HIGH)

**What:** All 10 canary tasks are single-prompt, single-response tasks. The agent receives a prompt, produces an output, gets scored. No task requires:
- Multi-turn conversation
- Tool calling chains (use tool A, read result, use tool B based on result)
- Context accumulation across turns
- Error recovery (tool fails, agent retries with different approach)
- Long-horizon planning (break task into subtasks)

**Why it matters:** Real agent work is multi-turn and tool-heavy. A model that scores 90% on single-prompt tasks can fail at multi-turn agentic tasks because it can't maintain context, recover from errors, or plan across steps. The canary measures model capability, not agent capability. The product brief acknowledges this: "Grid tests execution" — but the grid is not yet wired for daily monitoring.

**Fix:** Add 3-5 multi-turn agentic tasks to the canary suite:
- "Research and summarize" — agent must use web_search tool, read a page, summarize
- "Debug and fix" — agent must read code, identify bug, propose fix
- "Plan and execute" — agent must break a task into steps, execute each, report results
These require the Hermes adapter (with tools), not the DirectModelAdapter.

#### GAP-7: History-assisted task clustering is naive keyword overlap (Severity: LOW)

**What:** obs-spec-060 §3.2 — sessions are clustered by keyword overlap in title (split on spaces, remove stop words, group by shared keywords). The spec itself acknowledges this with a `ponytail:` comment.

**Why it matters:** Two sessions about different aspects of the same topic ("token optimization config" vs "token optimization dashboard") cluster together, producing redundant task proposals. A session about "SPGG booking" and "SPGG cancellation" would also cluster, missing the distinction.

**Fix:** Already noted in the spec — upgrade path is sentence-transformers embeddings with cosine similarity. Low priority because the user review step catches duplicates.

#### GAP-8: No inter-rater reliability metric for LLM judge (Severity: MODERATE)

**What:** The `llm_judge` assertion uses K=3 repeated evaluations and averages them. But there's no measurement of whether the 3 evaluations agree. If the judge returns [2, 18, 10] (scores 1-20), the average is 10 — but the disagreement is extreme. The system reports the average as if it's reliable.

**Why it matters:** A quality management system whose quality assessment tool is itself unreliable undermines the entire value proposition. Users make model swap decisions based on these scores. If the judge disagrees with itself, the delta between model A (score=10±8) and model B (score=12±8) is noise, not signal.

**Fix:** Report K=3 individual scores alongside the average. If standard deviation > 3 (on 1-20 scale), flag as "low judge confidence." Add this to the canary run report. ~10 lines.

### 8.3 Coverage Gaps

#### GAP-9: No safety/adversarial task in the canary suite (Severity: MODERATE)

**What:** The 10 tasks cover reasoning, coding, extraction, instruction_following, and tool_use. None test safety behavior:
- Does the agent refuse harmful instructions?
- Does the agent leak system prompt when asked?
- Does the agent execute dangerous shell commands without confirmation?
- Does the agent hallucinate when it doesn't know something?

**Why it matters:** Safety regressions are the highest-impact degradation mode. A model swap that improves reasoning but breaks safety is a net negative. Without safety tasks in the canary, a safety regression goes undetected until a real incident.

**Fix:** Add 2-3 safety tasks:
- "prompt_injection_resistance" — agent receives a prompt injection attempt, must not comply
- "system_prompt_leakage" — agent asked to reveal its SOUL.md, must refuse
- "hallucination_detection" — agent asked an unanswerable question, must admit uncertainty

#### GAP-10: No measurement of canary-to-reality correlation (Severity: HIGH)

**What:** The system runs canary benchmarks and reports scores. But there's no mechanism to validate whether canary scores correlate with real agent performance. The product brief says user-defined tasks are "the most valid benchmark type" but doesn't prove it with data.

**Why it matters:** This is the core value proposition. If canary scores don't predict real performance, the entire system is an elaborate random number generator. The product brief asserts validity ("tests the agent's actual job, score directly predicts real performance") but provides no evidence.

**Fix:** After dogfooding (running canary for 30+ days alongside real agent usage), compute the correlation between canary accuracy and real-world task success rate. Report this correlation in the dashboard: "Canary scores explain X% of real performance variance." If the correlation is low, the canary tasks need revision.

#### GAP-11: Drift monitoring (behavioral fingerprint) is not built (Severity: HIGH)

**What:** The product brief describes a rich behavioral drift monitoring system (8 dimensions: response length, structure, tool usage, token efficiency, errors, context utilization, latency, output embeddings). The code only implements token composition drift (System B above). The behavioral fingerprint system (System A in the brief's architecture diagram) is not built.

**Why it matters:** The "verification loop" (drift → canary → confirm) is described as the key innovation. But without behavioral drift monitoring, there's nothing to trigger the canary. The canary runs on a daily cron regardless of drift. The "auto-trigger on drift" feature doesn't exist. The entire loop is open.

**Fix:** This is a separate workstream (estimated ~750 lines in the product brief). It's the largest unbuilt component and the one that most differentiates ObserveCo from competitors. Priority should be elevated.

#### GAP-12: Grid reporter is not built (Severity: MODERATE)

**What:** The grid runner executes models × configs × tasks × trials and stores results. But the reporter (decision-aid tables with per-task CI, cost, trajectory) is not built. Grid results sit in the database with no user-facing presentation.

**Why it matters:** The grid is the deep-dive instrument. Without a reporter, users can't interpret grid results. The grid runner is a backend with no frontend.

**Fix:** Build the grid reporter (estimated ~100 lines). Per-task CI, cost, trajectory flags in a dashboard table. This is Phase 4 in the master plan.

### 8.4 Architecture Gaps

#### GAP-13: Single-threaded task execution (Severity: LOW)

**What:** `obs-spec-051 §7 #4` — tasks run sequentially per agent. 10 tasks × 10 trials = 100 LLM calls, each up to 60s timeout. Worst case: 100 minutes for one canary run.

**Why it matters:** At 100 minutes, the 3am cron may not finish before the user wakes up. If the canary model is slow (local Ollama at 16 tok/s), a single task might take 30s, making the total ~50 minutes — feasible but tight.

**Fix:** Parallelize at the task level (run all 10 tasks concurrently, each doing 10 sequential trials). 10x speedup. Use `concurrent.futures.ThreadPoolExecutor(max_workers=10)`. ~20 lines. Low priority unless canary runs are observed exceeding 60 minutes.

#### GAP-14: No canary failure alerting (Severity: MODERATE)

**What:** If the daily 3am canary cron fails silently (agent process down, Ollama unreachable, DB locked), there's no alert. The system just stops producing quality data. The user sees stale scores on the dashboard with no indication that the canary isn't running.

**Why it matters:** Silent failure of a monitoring system is the worst failure mode. The quality management system itself degrades without detection. This violates R12 (fail loud).

**Fix:** Add a canary heartbeat check: if no `canary_runs` row exists in the last 36 hours for an agent, surface a warning in the dashboard: "Canary hasn't run in 36 hours — check cron and agent status." ~15 lines.

#### GAP-15: LLM judge cost is unbounded (Severity: MODERATE)

**What:** The `llm_judge` assertion makes K=3 LLM calls per task per trial. For 10 tasks × 10 trials × K=3 = 300 judge calls per canary run. The product brief mentions a "self-monitoring budget cap (G1.1)" but this is not built (🔴 Planned in the master plan).

**Why it matters:** Without a budget cap, the canary can burn through API credits. If the user configures an expensive judge model (GPT-4o at $0.15/1K tokens), 300 judge calls × ~500 tokens each = 150K tokens = $22.50 per canary run. Daily. $675/month in judge costs alone.

**Fix:** Implement a simple daily budget tracker: count judge tokens consumed per day, compare against a configurable ceiling (default: $1/day). When exceeded, fall back to `contains` assertion. ~30 lines. This is G1.1 from the master plan.

---

## 9. Priority Summary

| Gap | Severity | Effort | Fix |
|-----|----------|--------|-----|
| **GAP-5:** Config hash misses SOUL.md/skills | HIGH | ~15 lines | Include SOUL.md + skills in hash |
| **GAP-6:** No multi-turn agentic tasks | HIGH | ~3-5 tasks | Add tool-using tasks to canary |
| **GAP-10:** No canary-to-reality correlation | HIGH | 30-day study | Track real task success vs canary scores |
| **GAP-11:** Behavioral drift not built | HIGH | ~750 lines | Full workstream (separate) |
| **GAP-1:** Z-test imprecise at small n | MODERATE | ~20 lines | Permutation test or Fisher's exact |
| **GAP-4:** Per-task drift falls back to aggregate | MODERATE | ~5 lines | Report "no baseline" instead |
| **GAP-8:** No judge inter-rater reliability | MODERATE | ~10 lines | Report K=3 scores + std dev |
| **GAP-9:** No safety tasks | MODERATE | ~3 tasks | Add safety/adversarial canary tasks |
| **GAP-12:** Grid reporter not built | MODERATE | ~100 lines | Dashboard table for grid results |
| **GAP-14:** No canary failure alerting | MODERATE | ~15 lines | Stale-run detection in dashboard |
| **GAP-15:** LLM judge cost unbounded | MODERATE | ~30 lines | Daily budget tracker for judge calls |
| **GAP-2:** Bootstrap CI non-reproducible | LOW | 1 line | `random.seed(42)` |
| **GAP-3:** Bootstrap CI (0,0) ambiguity | LOW | ~5 lines | Return None, render as "insufficient data" |
| **GAP-7:** Naive clustering | LOW | Deferred | Spec already notes upgrade path |
| **GAP-13:** Single-threaded execution | LOW | ~20 lines | ThreadPoolExecutor |

---

## 10. Strengths (Independent Assessment)

The audit isn't complete without acknowledging what's done right:

1. **Category positioning is correct and empty.** "Agent Quality Management" for production operators is genuinely unoccupied. Phoenix/LangFuse serve developers. DeepEval serves ML engineers. Nobody serves the operator running agents in production.

2. **Two-instrument architecture is well-reasoned.** Canary (cheap, daily) + Grid (expensive, deep) is the right split. Trying to do both in one instrument would either be too expensive for daily runs or too shallow for model decisions.

3. **Config-aware baselines are the right idea.** Most drift systems compare against a static baseline. ObserveCo's config_hash approach (when fixed to include SOUL.md/skills) will be genuinely novel in the product space.

4. **LLM-as-a-Verifier (1-20 scale, logprob-based) is state-of-the-art.** Most systems use 0-1 binary judge or 5-point Likert. The 1-20 scale with logprob extraction from Kwok et al. (arXiv:2607.05391) is a genuine implementation of 2026 research.

5. **Human-in-the-loop for task generation is the right call.** The spec explicitly rejects fully automated task generation and explains why (circular benchmarking, selection bias, staleness). This is a mature design decision.

6. **Dev/test split prevents overfitting.** This is standard in ML but rare in agent evaluation. Including it from v0.5.0 is ahead of the field.

7. **Per-task baselines (when they exist) are the correct approach.** Comparing a hard coding task against an aggregate baseline was a real bug. The fix is implemented. The remaining gap (GAP-4) is the fallback, not the core logic.

8. **The "what we don't do" section is a sign of product discipline.** Explicitly declining LLM-as-judge per session, evaluation metrics from scratch, and prompt management shows clear scope control.