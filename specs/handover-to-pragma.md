# ObserveCo: Agent Quality Management — Handover to Pragma

**From:** Gladwell (Chief Storyteller / Launch Strategist)
**To:** Pragma (COO / Build Execution)
**Date:** 2026-06-30
**Updated:** 2026-07-02 (post-redirect: Canary+Grid architecture, RQGM re-scoped)
**Context:** This document gives you everything you need to continue building the Agent Quality Management feature. Read the product brief first (`specs/agent-quality-management-brief.md`) for the full strategic context — this handover covers what was built, why, and what's next.

---

## 1. What This Is

ObserveCo is pivoting from **"agent observability"** (passive monitoring — is it running? how much does it cost?) to **"Agent Quality Management"** (active quality assessment — is it any good?).

The core insight: nobody answers "is my agent actually working well?" Phoenix/LangFuse answer "what did the model return?" for developers. Datadog/Grafana answer "is my server up?" for ops. The empty space is agent quality for operators.

The product has two mechanisms:
1. **Benchmarks** — run tasks against the agent's actual harness, get a score
2. **Behavioral drift monitoring** — track behavioral fingerprints, alert on change (not yet built)

---

## 2. What Was Built (v2 — Canary + Grid)

**Architecture redirect (2026-07-01):** Sean redirected from the original three-tier benchmark approach to a two-instrument system. The lm-eval-harness approach was superseded by the Canary+Grid architecture.

### Instrument 1: Canary — Regression Tripwire

**Purpose:** Detect degradation. Not measure capability. Cheap, fast, frequent.

**What exists:**

| Component | Status | Notes |
|-----------|:------:|-------|
| `benchmark/engine.py` — `run_lm_eval()` | ✅ Built | lm-eval-harness backend. 9 tasks across 7 dimensions (BBH, GSM8K, IFEval, MBPP, TriviaQA, BBQ, ARC) |
| `benchmark/engine.py` — `SUITES` | ✅ Built | "canary" (15 samples/task) and "full" (50 samples/task) |
| `benchmark/adapters/hermes.py` | ✅ Built | Hermes agent harness adapter for lm-eval |
| `benchmark/adapters/lm_eval_adapter.py` | ✅ Built | lm-eval model adapter wrapping Hermes agent |
| `benchmark/adapters/direct_model.py` | ✅ Built | Direct model API adapter (no agent harness) |
| `benchmark/adapters/litellm_adapter.py` | ✅ Built | LiteLLM adapter with real logprobs for MC scoring |
| `benchmark_tasks` table | ✅ Built | DB schema for user-defined tasks |
| `benchmark_results` table | ✅ Built | DB schema for storing results |
| CLI: `benchmark run --suite canary` | ✅ Built | Runs lm-eval tasks through agent harness |
| CLI: `benchmark run --direct` | ✅ Built | Direct model API (no agent harness) |
| CLI: `benchmark run --litellm` | ✅ Built | LiteLLM with logprobs for MC scoring |
| CLI: `benchmark create-task/list/delete` | ✅ Built | User-defined task CRUD |
| `_legacy_score()` (keyword overlap) | ✅ Kept for compat | Backward-compatible scoring for pre-existing custom tasks |
| `_llm_judge` | ❌ Removed from canary | Too expensive for a tripwire. Keyword overlap sufficient for change detection |

**Canary run frequency:** Cron `0 */4 * * *` (every 4 hours). ~2 min, ~$0.002.

### Instrument 2: Grid — Capability Measurement

**Purpose:** Separate model from harness. Find the best combination for real agentic tasks.

**What exists:**

| Component | Status | Notes |
|-----------|:------:|-------|
| `grid/__init__.py` | ✅ Built | Module docstring defining the grid approach |
| `grid/configs.py` | ✅ Built | 7 harness configs: baseline, timeout_aggressive, timeout_generous, feedback_truncated, feedback_minimal, context_sliding, context_summary |
| `grid/runner.py` | ✅ Built | GridRunner class. `run_tau_bench()` method. Wilson CI calculation. Trajectory flagging (shortcuts, loops). Per-cell result storage |
| `grid/tau_adapter.py` | ✅ Built | HermesTauAgent implementing τ-bench's Agent interface. Routes multi-turn tool-calling through `hermes chat -q` |
| `grid/swe_adapter.py` | ✅ Built | HermesSWEAgent for SWE-bench patch generation. Retry logic, timeout handling, patch extraction |
| CLI: `benchmark grid` | ✅ Built | Grid command group |

**Not yet built (Phase 3-5):**
- GAIA task loader
- Grid reporter (decision-aid tables with per-task CI, cost, trajectory)
- Synergy wiring (canary fire → observability check → grid trigger)

### RQGM Status

RQGM has been **demoted from central evaluation engine to trajectory analysis hardener (Phase 5).**

| RQGM's Old Job | Handled Now By |
|---|---|
| "Is this improvement real or gaming?" | Grid's Wilson CIs |
| "Is this degradation or noise?" | Canary's binary tripwire + observability correlation |
| "Which change caused the shift?" | Observability config tracking |

**Where RQGM still applies:** Trajectory analysis hardening. If the agent learns to avoid loop/shortcut/unsafe flags, RQGM tightens detection thresholds epoch by epoch.

**Current state:** `rqgm-core` package exists at `~/projects/rqgm-core`. 4 cron jobs exist (Dreamer, Spec-Build, Test Suite, Hound Audit) — all in error state. Not wired into the grid or canary pipeline. Phase 5 work.

---

## 3. Architecture

```
CLI (cli.py)
  └── BenchmarkEngine (engine.py)
        ├── Task CRUD → pulse.db (benchmark_tasks table)
        ├── run_suite()
        │     └── HermesBenchmarkAdapter (adapters/hermes.py)
        │           └── subprocess: hermes chat -q <prompt> -Q
        └── _score_task()
              ├── _keyword_scorer()  [default]
              └── _llm_judge()       [--judge flag]
```

**Key design decisions:**
- Hermes adapter uses subprocess (simplest for v1). Upgrade path: Hermes API for structured output.
- Default scorer is keyword overlap (no tokens, no API calls). Upgrade path: per-task scoring modes.
- LLM judge defaults to local ornith:latest (no cloud cost). Upgrade path: configurable judge model.
- No suite filtering — `run` always executes all tasks for the agent. Upgrade path: suite names.

---

## 4. What NOT to Build (Decisions Made)

These were discussed and explicitly deferred:

| Feature | Why deferred |
|---------|-------------|
| **Behavioral drift monitoring** | Separate phase. Requires config hashing, workload clustering, baseline versioning. ~750 lines. |
| **Curated model benchmarks (MMLU, GSM8K)** | Secondary priority. User-defined tasks are the primary benchmark type. |
| **Full dashboard redesign** | Just add a basic quality card to existing fleet view. |
| **Canary verification loop** | Comes after drift monitoring exists. |
| **BFCL for model-harness compatibility** | Proxy data, not real. Comparative benchmarks on user tasks are better. |
| **LLM-as-judge for every session** | Too expensive, breaks local-first. Benchmarks have ground truth or expected outputs. |

---

## 5. Known Limitations (Ponytails)

These are documented in the code with `ponytail:` comments. Read them before modifying.

| Limitation | Ceiling | Upgrade path |
|-----------|---------|-------------|
| Keyword overlap scorer | Scores term presence, not reasoning quality | Per-task scoring modes (exact match, regex, LLM judge, human review) |
| Hermes adapter uses subprocess | Slow, no structured output | Hermes API directly |
| No suite filtering | Run always executes all tasks | Suite names + filtering |
| LLM judge defaults to ornith:latest | Local model quality varies | Configurable judge model, multiple backends |
| No task templates | Users must define tasks from scratch | Pre-built templates for common agent roles |

---

## 6. What's Next (Roadmap)

Priority order, as decided with Sean:

### Phase 1: Dogfood (immediate)

Create real tasks for Sean's 7 agents and run benchmarks. This proves the concept with real data.

**What to do:**
1. Create 3-5 tasks per agent that match their actual job
2. Run `observeco benchmark run --agent <name>` for each
3. Show Sean the output
4. Iterate on task quality and scoring thresholds

**Agent task ideas:**
- Hermes Main: code review, architecture analysis, root cause analysis
- Kepler: market research synthesis, revenue opportunity identification
- Dreamer: pattern detection, signal extraction
- PA: calendar parsing, commitment extraction
- Hound: strategy evaluation, decision quality
- Aleph: knowledge ingestion, wiki page creation
- Raven: deal sourcing, price comparison

### Phase 2: Dashboard Quality Cards (~400 lines)

Add benchmark scores to the fleet view so users can see quality at a glance.

**What to build:**
- Quality column in fleet table (score + trend arrow)
- Agent detail page with benchmark history chart
- Per-task breakdown (which tasks passed/failed)
- Guidance tooltips explaining benchmark limitations

### Phase 3: Curated Benchmark Ingestion (~200 lines)

Pull MMLU/GSM8K canary subsets from HuggingFace. Offer alongside user-defined tasks.

**What to build:**
- Benchmark ingestion script (pull, cache, version)
- Canary subset selection (10-20 representative tasks per suite)
- CLI integration: `observeco benchmark --suite mmlu-canary`

### Phase 4: Comparative Benchmarking (~150 lines)

`--compare` flag that runs the same benchmark with different models against the same agent.

**What to build:**
- Model iteration in harness adapter
- Side-by-side score comparison
- Recommendation output

### Phase 5: Behavioral Drift Monitoring (~750 lines)

Config-aware fingerprinting + drift detection. The other half of the product.

**What to build:**
- Config hashing (model + SOUL + skills + system prompt)
- Workload clustering (embedding-based session grouping)
- Baseline versioning (per-config, per-workload)
- Drift detection (JS divergence, z-score, cosine distance)
- Canary verification loop (drift → auto-trigger benchmark → confirm or dismiss)

---

## 7. Key Context You Need

These are the decisions and discussions that shaped this direction. Read them before making architectural changes.

### The Category Argument

AI agents are not LLM apps. They are a fundamentally different runtime — stateful, looping, cascading, self-modifying, financially explosive. The tools built for LLM tracing (Phoenix, LangFuse, OpenLIT) answer "what did the model return?" The question that matters for agents is "is my agent healthy?" — and nobody answers it.

### The Benchmark Validity Problem

Model-centric benchmarks (MMLU, GSM8K) were designed for models, not full agent systems with tools, memory, SOUL, skills, and multi-turn behavior. Running them through a harness adapter produces numbers that look scientific but have low predictive power for real work.

**Solution:** Three-tier benchmark system:
1. **Primary: User-defined tasks** — tests the agent's actual job. Highest validity.
2. **Secondary: Curated model benchmarks** — general capability signal. Honest guidance: "This tests general reasoning, not your specific job."
3. **Tertiary: Comparative (before/after)** — delta is meaningful even if absolute score isn't.

### The Drift Noise Problem

Behavioral fingerprints are noisy. Agents change behavior when SOUL/skills change, models are swapped, or workload shifts. These intentional changes look identical to degradation.

**Solution:** Config-aware baselines + workload clustering. Drift = fingerprint change WITHOUT config change, within the same workload type. Drift alone is noise — drift + canary verification is signal.

### The "No Local Model" Problem

LLM-as-judge requires a secondary model. For users without local models, this breaks the local-first pitch.

**Solution:** Default scorer is keyword overlap (deterministic, free, instant). LLM judge is optional (`--judge` flag). Benchmarks use the agent's own model — no secondary judge needed for the primary scoring path.

### The Human Factor

Benchmarks have tremendous power on humans because they are deterministic and immediately available, as inaccurate as they may be. "My agent scored 87%" is a statement. "My agent's behavioral fingerprint shifted 0.3 standard deviations" is noise. The benchmark makes the abstract concrete. Drift monitoring is the net that catches what happens between benchmarks.

---

## 8. Reference Documents

| Document | Path | What it contains |
|----------|------|-----------------|
| Product brief | `specs/agent-quality-management-brief.md` | Full product direction, architecture, risks, roadmap |
| Competitive analysis | `docs/competitive-analysis.md` | Competitor landscape, feature matrix, positioning |
| Agent Drift paper | arxiv:2601.04170 | Academic framework for behavioral degradation in multi-agent systems |
| Existing codebase | `src/observeco/` | ObserveCo v0.4.0 — fleet health, token tracking, anomaly detection, baselines |

---

## 9. Signal Protocol

When you complete a build phase, write an outcome signal to Gladwell's inbox:

```
~/.hermes/signals/gladwell/inbox/<descriptive_name>.json
```

Format:
```json
{
  "from": "pragma",
  "to": "gladwell",
  "type": "build_complete",
  "payload": {
    "task_id": "<task_id from the build request>",
    "status": "built|verified|failed",
    "summary": "What was built and what was verified",
    "files_created": ["..."],
    "files_modified": ["..."],
    "ponytails": ["Known limitations"],
    "built_at": "ISO8601"
  },
  "written_at": "ISO8601",
  "consumed": false
}
```

---

## 10. Quick Start

```bash
# Create a task
observeco benchmark create-task \
  --agent hermes-main \
  --name code_review \
  --input "Review this Python function for security issues:\ndef login(username, password):\n    query = f\"SELECT * FROM users WHERE username='{username}'\"\n    return db.execute(query)" \
  --expected "Must identify SQL injection vulnerability"

# List tasks
observeco benchmark list --agent hermes-main

# Run all tasks (default: keyword scoring)
observeco benchmark run --agent hermes-main

# Run with LLM judge
observeco benchmark run --agent hermes-main --judge

# View results
observeco benchmark results --agent hermes-main --limit 10
```
