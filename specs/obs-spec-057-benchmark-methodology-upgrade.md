# obs-spec-057 — Benchmark Methodology Upgrade

**Spec ID:** obs-spec-057
**Title:** User-defined benchmark methodology — assertion system, scoring, statistical validity, gold standards, and automatic change tracking
**Status:** DRAFT (v5 — 2026-08-08: judge determinism + TTL exemption, confirmation-rerun guard, validated first known-good, independent liveness emitter, coverage-classified alerts)
**Owner:** Main
**Depends on:** obs-spec-050 (data model), obs-spec-051 (canary runner), obs-spec-055 (task definition)
**Master plan ref:** v0.6.0 "Agent Quality Management"
**Created:** 2026-07-06
**Updated:** 2026-08-08

---

## 0. Purpose — Factory Regression Detector (Primary)

**The canary's primary job is to detect agent performance regressions when the factory changes — not to rank agents on a leaderboard.**

The factory (Hermes agent ecosystem) changes constantly: SOUL.md edits, model swaps, provider changes, prefill updates, harness fixes, config drift. Each change risks silently degrading agent output. The canary is the instrument that answers, before/after a change: **did agent quality go up, down, or stay the same?**

This reframing (2026-08-08) follows an end-to-end audit of the canary's 23 tasks and 1520 results, which found:
- 10 of 23 tasks are raw session fragments ("Ping", "[Sean Foo] What's next?") with no gold standard — they cannot detect regressions
- 14 of 23 tasks have no `expected_output` — scoring is ungrounded
- Template variables (`{{ problem }}`) still live in a built-in task despite §2.4 — the model correctly refused to solve a non-problem, scored 0.0
- The 52.6% pass rate measures task quality, not agent quality

**Consequence:** a small, stable, curated core of tasks with gold standards is the foundation. The leaderboard ambition (agent quality comparison) is a separate product track that builds on the same core — it is not the factory's need.

**Design principles for the core set:**
1. **Small and stable** — 8-12 tasks covering the capabilities the factory actually ships (reasoning, coding, extraction, instruction-following, tool-use)
2. **Gold-standard grounded** — every task has `expected_output` + calibrated assertions (§2.8)
3. **Deterministic** — temperature=0, concrete fixtures, no templates. **n=1 per task per run** — determinism means identical trials add nothing; bootstrap CI is meaningless over identical values (§2.3)
4. **Split-aware** — `dev` for optimization, `test` for monitoring (never touched by optimization)
5. **Change-triggered** — a config change auto-runs the core and compares against a rolling-window baseline (§2.9)
6. **Versioned** — every run records the task content hash, assertion version, judge model/prompt version, and scorer version; a mismatch invalidates comparison rather than silently proceeding (§2.10)

---

## 1. Problem Statement

The current canary benchmark system (obs-spec-051/055) is functional as a smoke test but cannot support meaningful quality comparisons between agents. A critical evaluation of the implementation revealed:

1. **Assertions are too weak** — 6 of 9 tasks use keyword containment checks that can be passed by echoing prompt content or sounding authoritative without being correct
2. **LLM-as-judge was unimplemented** — the `llm_judge` assertion type existed in the Scorer but returned "not implemented". **Fixed 2026-07-10** — upgraded to LLM-as-a-Verifier (1-20 scale, K=3, logprob-based expected score).
3. **No reference outputs** — tasks have no `expected_output` field; scoring is purely binary pattern matching
4. **Trials=3 is insufficient for bootstrap CI** — bootstrap resampling from n=3 produces wide, unstable intervals
5. **Per-task drift compares against aggregate baseline** — individual task drift is meaningless because it compares a single task's accuracy against the overall baseline, not that task's own historical accuracy
6. **Template variables block 6/9 tasks for most agents** — `{{ language }}`, `{{ document }}`, etc. skip silently, making run counts inconsistent across agents
7. **No temperature control** — canary runs use whatever the agent's default temperature is, making results non-reproducible
8. **Dev/test split is unused** — all tasks have `split="all"` despite the split feature existing in code
9. **No category/difficulty metadata** — all tasks weighted equally regardless of complexity

**Reference:** Critical evaluation conducted 2026-07-06 against industry standards (lm-eval-harness, DeepEval, Promptfoo, Inspect AI).

---

## 2. Design

### 2.1 Enhanced Task Schema

Add new columns to `canary_tasks`:

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `category` | TEXT | NULL | Capability category: reasoning, coding, extraction, tool_use, safety, instruction_following |
| `difficulty` | TEXT | 'medium' | easy / medium / hard — weights for scoring |
| `expected_output` | TEXT | NULL | Reference answer for comparison (gold standard) |
| `few_shot_examples` | TEXT (JSON) | NULL | Array of {input, output} examples for in-context learning |
| `system_override` | TEXT | NULL | Optional system prompt override for this task only |
| `temperature` | REAL | 0.0 | Sampling temperature for canary runs (0 = deterministic) |

**Migration:** `ALTER TABLE canary_tasks ADD COLUMN ...` for each new column. Schema version bump. After ALTER, run UPDATE statements to populate `category`, `difficulty`, and `temperature` for existing 9 built-in tasks:

```sql
UPDATE canary_tasks SET category = 'reasoning',           difficulty = 'easy',   temperature = 0.0 WHERE id = 'arithmetic-reasoning';
UPDATE canary_tasks SET category = 'reasoning',           difficulty = 'medium', temperature = 0.0 WHERE id = 'chart-interpretation';
UPDATE canary_tasks SET category = 'coding',              difficulty = 'hard',   temperature = 0.0 WHERE id = 'code-generation';
UPDATE canary_tasks SET category = 'extraction',          difficulty = 'medium', temperature = 0.0 WHERE id = 'document-qa';
UPDATE canary_tasks SET category = 'extraction',          difficulty = 'easy',   temperature = 0.0 WHERE id = 'extract-structured-data';
UPDATE canary_tasks SET category = 'instruction_following', difficulty = 'medium', temperature = 0.0 WHERE id = 'follow-multi-step-instructions';
UPDATE canary_tasks SET category = 'extraction',          difficulty = 'medium', temperature = 0.0 WHERE id = 'summarize-conversation';
UPDATE canary_tasks SET category = 'instruction_following', difficulty = 'easy',   temperature = 0.0 WHERE id = 'time-bound-response';
UPDATE canary_tasks SET category = 'tool_use',            difficulty = 'medium', temperature = 0.0 WHERE id = 'tool-selection';
```

Without this, all historical task results show "unknown" category — the dashboard category breakdown would be empty until new tasks are created.

### 2.2 Enhanced Assertion System

#### New Assertion Types

| Type | Fields | Description |
|------|--------|-------------|
| `json_schema` | `schema` | Validate output parses as JSON and matches JSON Schema |
|| `semantic_similarity` | `expected`, `threshold` (default 0.7) | Compute cosine similarity between output and expected output using sentence-transformers. Model: `all-MiniLM-L6-v2` (80MB). Lazy-loaded on first use. Falls back to `contains` assertion with warning log if package not installed. Add `sentence-transformers>=2.2` to `pyproject.toml` optional deps: `[project.optional-dependencies] sim = ["sentence-transformers>=2.2"]`. Install with `pip install observeco[sim]` or `uv add observeco --extra sim`. macOS Metal acceleration via MPS if available. |
| `code_executable` | `language` | **Deferred to v0.7.0.** Executing agent-generated code requires a proper sandbox (network isolation, filesystem isolation, resource limits) that subprocess alone cannot provide. Current risk mitigation (restricted env vars + timeout) insufficient — fork bombs, filesystem reads, and memory exhaustion remain exploitable. When implemented, use Docker container or nsjail, not bare subprocess. In v0.6.0, `code_executable` assertion returns "not implemented (deferred to v0.7.0)" with a warning. |
| `ordering` | `steps` | Check if output contains steps in the specified order |
| `tool_call_validation` | `expected_tool`, `expected_args` | Verify the agent called the right tool with correct arguments |
| `llm_judge` | `criteria`, `threshold` (default 0.5), `repetitions` (default 3) | LLM-as-a-Verifier evaluates output against criteria on a 1-20 scale with K=3 repetition. Uses logprob-based expected score (Tier 2) or discrete fallback (Tier 1). Based on Kwok et al. (arXiv:2607.05391, 2026). |

#### LLM-as-Judge Implementation (v2 — 2026-07-10)

**Upgraded to LLM-as-a-Verifier** per Kwok et al. (arXiv:2607.05391, 2026). Replaced the original 0-1 JSON prompt with a 1-20 scale + logprob-based expected score.

```python
def _llm_judge(assertion: dict, output: str) -> tuple[bool, float, str]:
    """LLM-as-a-Verifier assertion — evaluates output quality against criteria.

    Uses fine-grained 1-20 scoring with K=3 repeated evaluation.
    If the provider supports logprobs, computes expected score from the
    logprob distribution (Tier 2). Otherwise falls back to discrete score
    parsing (Tier 1).
    """
    criteria = assertion.get("criteria", "")
    expected = assertion.get("expected", "")
    threshold = assertion.get("threshold", 0.5)
    k = int(assertion.get("repetitions", 3))

    system_prompt = (
        "You are an expert evaluator. Score the agent's response against the criteria. "
        "Rate on a 1-20 scale "
        "(1 = completely wrong, 20 = perfect). "
        "Respond with ONLY: <score>N</score> where N is an integer 1-20."
    )
    user_context = (
        f"Criteria: {criteria}\n"
        f"Expected: {expected}\n"
        f"Agent output: {output[:2000]}\n\n"
        f"Score (1-20):"
    )

    # Judge determinism: the judge MUST run at temperature=0. The core track's
    # "any delta is signal" rule assumes the measuring instrument is stable —
    # a judge at default temperature injects sampling variance that reads as
    # agent regression. Pin temperature=0 for all judge calls.
    judge_temperature = 0.0

    # K repeated evaluations
    for i in range(k):
        resp = ask_with_logprobs(system_prompt, user_context,
                                 consumer="canary_judge", tier=2,
                                 top_logprobs=20)
        # Tier 2: logprob-based expected score
        if resp.logprobs:
            score = expected_score_from_logprobs(resp.logprobs)
        # Tier 1 fallback: parse <score>N</score> from text
        else:
            score = parse_discrete_score(resp.text)
        # Average across K calls
        ...

    return (avg_score >= threshold, avg_score, reasoning)
```

**Key differences from v1 (0-1 JSON):**
- **1-20 scale** instead of 0-1 — finer granularity reduces tie rates from ~27% to ~0%
- **Logprob-based expected score** instead of reading the generated token — computes `E[score] = Σ p(v_g) · φ(v_g)` from the full logprob distribution
- **K=3 repetition** instead of single call — averages 3 independent evaluations
- **`<score>N</score>` output format** instead of JSON — enables logprob extraction at a single token position
- **`repetitions` field** — users can override K per assertion

**Logprob extraction (Tier 2):**
```python
def expected_score_from_logprobs(logprobs: list[dict]) -> float | None:
    """Compute expected score from logprob distribution at the score token position.

    Implements Eq. 3.1 from the paper: R = sum_g p(v_g) * phi(v_g)
    """
    for pos in logprobs:
        top_lps = pos.get("top_logprobs") or []
        score_probs = []
        for lp in top_lps:
            score = token_to_score(lp["token"])  # 1-20
            if score is not None:
                prob = math.exp(lp["logprob"])
                score_probs.append((score, prob))
        if not score_probs:
            continue
        total_prob = sum(p for _, p in score_probs)
        expected = sum(s * (p / total_prob) for s, p in score_probs)
        return (expected - 1) / (20 - 1)  # normalize to 0-1
    return None
```

**Discrete fallback (Tier 1):**
```python
def parse_discrete_score(text: str) -> float | None:
    """Extract a 1-20 score from model text output.
    Tries: <score>N</score> tags → Score: N → last integer 1-20 in text.
    """
    m = re.search(r"<score>\s*(\d+)\s*</score>", text)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 20:
            return (val - 1) / 19
    ...
```

**Provider support:**
- OpenAI-compatible (DeepSeek, OpenRouter, Groq, Together, Mistral, vLLM, LM Studio) → Tier 2
- Anthropic, Google, Ollama native → Tier 1
- Falls back to `contains` if no LLM provider configured

**Caching:** Judge results cached by `(task_id, sha256(output), criteria, judge_model, judge_prompt_version)` to avoid re-evaluating identical outputs across trials. Cache stored in `canary_judge_cache` table. **The cache key must include the criteria text, judge model, and judge prompt version** — otherwise editing a task's criteria or swapping judge providers reuses scores computed under different rules for up to 7 days (§2.10).

**Cost guard:** Judge calls count against the self-monitoring budget cap (G1.1). If budget exhausted, fall back to `contains` assertion.

**Interface:** `ask_with_logprobs(system_prompt, user_context, *, consumer, max_cost_cents, cache_ttl_secs, tier, top_logprobs) -> LLMResponse | None`. Returns `LLMResponse(text, logprobs)` or `None` when gated/budget-exhausted/no-API-key. Uses `OBSERVECO_LLM_API_KEY` (BYOK).

#### Scoring Weight

```
task_score = weighted_average(assertion_scores, weight_by_type)
```

| Assertion Type | Weight | Rationale |
|----------------|--------|-----------|
| `exact_match` | 1.0 | Binary — must match |
| `llm_judge` | 1.0 | High-quality grader |
| `semantic_similarity` | 0.8 | Approximate match |
| `json_schema` | 1.0 | Structural correctness |
| `ordering` | 0.7 | Sequence correct but individual steps may be wrong |
| `contains` | 0.4 | Weak signal — necessary but not sufficient |
| `tool_call_validation` | 1.0 | Correct tool + args = correct action |

### 2.3 Statistical Methodology Fixes

#### Trials

- **Core set (factory regression detector): n=1 per task per run.** Temperature=0 means identical trials add nothing — bootstrap CI over identical values has zero width and is meaningless. Regression detection compares the single score against a rolling-window baseline (§2.9).
- **Product/leaderboard track (temp > 0 deliberately):** default trials 10 per task (configurable), 5 for `llm_judge` tasks (cost). Bootstrap CI requires minimum n=5 to produce meaningful intervals. For n < 5, report point estimate without CI.
- **The two tracks are mutually exclusive by design.** Determinism (n=1, no CI, direct comparison) and variance estimation (temp > 0, n=10, CI) cannot coexist in the same run — §0's reframing resolves the contradiction by assigning each to its track.

#### Per-Task Drift Fix

```python
# BEFORE (broken): compares single task accuracy vs AGGREGATE baseline
task_drift = (tr["accuracy"] - baseline_accuracy) * 100

# AFTER (correct): compares single task score vs THAT TASK'S last known-good
task_known_good = get_last_known_good(agent_name, task_hash, task_id)
task_drift = (tr["accuracy"] - task_known_good.accuracy) * 100
```

**New table:** `canary_task_baselines` — per-task known-good score per agent+task content. See §2.7 for schema.

**Per-task known-good computation:** the last completed run for that task content (`task_hash`) that was NOT skipped (no template variables unresolved), NOT degraded (budget exhaustion, §2.9), and NOT a flagged regression. Per-task score = the trial-level accuracy from that run (core track: n=1). A `task_hash` change starts a new series — the old known-good is archived, not compared (§2.10).

#### Z-Test n1 Fix

```python
# BEFORE (broken): hardcoded assumption of 9 tasks per run
n1 = baseline.get("run_count", 3) * 9

# AFTER (correct): use actual total task-trials from baseline runs
n1 = sum(r["total_tasks"] for r in baseline_runs)  # actual count
```

#### Temperature Control

All canary runs use `temperature=0.0` by default (per-task override via `canary_tasks.temperature` column). This ensures reproducibility — same config + same task = same result (modulo provider non-determinism).

The current Hermes adapter (`benchmark/adapters/hermes.py`) runs `hermes chat -q "prompt" -Q --safe-mode` and has **no temperature flag**. Temperature must be added:

1. **Add `temperature` field to the task object** constructed in `TaskExecutor.execute()` (`canary.py:235-242`)
2. **Update `HermesBenchmarkAdapter.run_task()`** to accept temperature and pass `--temperature` to the `hermes chat` CLI
3. **Verify `hermes chat` supports `--temperature`** — if not, use the Hermes Python API directly with temperature parameter
4. Fallback: if the provider ignores temperature or `hermes chat` lacks the flag, document the limitation and warn in logs. Providers known to support temperature: OpenAI, Anthropic, Ollama. Providers known to ignore it: some local models.

**SPIKE (before Phase 2, not inside it):** the determinism premise rests on `hermes chat --temperature` actually working end-to-end. Verify in a spike: (a) the flag exists, (b) it reaches the provider, (c) two identical runs at temp=0 produce identical output. If any fails, determinism is not achievable and the core set must use the variance track instead. **Scope the reproducibility claim:** temperature only controls sampling nondeterminism. Hermes agents read SOUL.md, carry memory, and may call tools — run-to-run variance has sources temperature cannot touch. The claim is "same task, same config, same temp → same output *for the controlled path*", not absolute reproducibility.

### 2.4 Template Variable Resolution

**Problem:** 6 of 9 tasks have `{{ variable }}` templates. Agents without context to resolve them skip silently, making run counts inconsistent.

**Fix:**

1. **Replace all template prompts with concrete fixture data** — no `{{ }}` variables in built-in tasks
2. Tasks that need test data load from **fixture files** at `~/.observeco/tasks/fixtures/`
3. Custom tasks with templates are rejected at creation time with a clear error: "Replace `{{ variable }}` with concrete test data"
4. The `_check_blanks` function already rejects templates for new tasks — existing tasks must be migrated

**Migration script:** For each existing task with templates:
1. Generate concrete fixture data (sample document, sample transcript, etc.)
2. Replace `{{ variable }}` with the fixture content in the prompt
3. Store as concrete prompt (no templates)

### 2.5 Dev/Test Split Activation

Built-in tasks assigned splits:

| Split | Tasks | Purpose |
|-------|-------|---------|
| `dev` | 3 tasks (arithmetic, extract-structured-data, time-bound-response) | Used for harness optimization loop (obs-spec-056) — config tuning |
| `test` | 6 tasks (chart, code-gen, document-qa, follow-instructions, summarize, tool-selection) | Used for quality monitoring — never touched by optimization |
| `all` | 3 tasks (ci-lint-fix, realistic-tier3, spec-compliance) | Run in both contexts — the "keep as-is" tasks from §2.8 curation; they are stable enough to run everywhere |

**Canary runs default to `split=test`** — monitoring only.
**Harness optimization** uses `split=dev` (obs-spec-056).
**The 12-task core (§2.8) = 3 dev + 6 test + 3 all.**
**Known limitation at the obs-spec-056 interface:** dev = 3 tasks is a very thin optimization set. Config tuned against three tasks will fit noise, and the test split will catch it only after the fact. This is a named limitation, not a hidden one — if obs-spec-056's optimization loop needs more signal, the dev split must grow (moving tasks from `all` or adding new dev tasks) before the loop ships.

### 2.6 Category Metadata

Built-in tasks categorised:

| Task | Category | Difficulty |
|------|----------|------------|
| Arithmetic reasoning | reasoning | easy |
| Chart interpretation | reasoning | medium |
| Code generation | coding | hard |
| Document Q&A | extraction | medium |
| Extract structured data | extraction | easy |
| Follow multi-step instructions | instruction_following | medium |
| Summarize conversation | extraction | medium |
| Time-bound response | instruction_following | easy |
| Tool selection | tool_use | medium |

**Dashboard:** Show category breakdown in task list and results. Agents scored per-category, not just aggregate.

### 2.7 New Tables — Schema Definitions

#### `canary_judge_cache` — LLM judge result caching

```sql
CREATE TABLE canary_judge_cache (
    cache_key    TEXT PRIMARY KEY,  -- sha256(task_id + output_hash + criteria + judge_model + judge_prompt_version)
    task_id      TEXT NOT NULL,
    output_hash  TEXT NOT NULL,     -- sha256(agent_output)
    criteria     TEXT NOT NULL,     -- assertion criteria text (part of key, §2.10)
    judge_model  TEXT NOT NULL,     -- judge model (part of key, §2.10)
    judge_prompt_version TEXT NOT NULL, -- judge prompt version (part of key, §2.10)
    score        REAL NOT NULL,     -- 0.0 to 1.0
    reasoning    TEXT,
    model_used   TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES canary_tasks(id)
);
CREATE INDEX idx_judge_cache_task ON canary_judge_cache(task_id);
```

Cache key is `sha256(f"{task_id}:{sha256(output)}:{criteria}:{judge_model}:{judge_prompt_version}")`. Lookup before calling LLM judge. If found and created within TTL (default 7 days), reuse cached score. Purge entries older than 7 days on maintenance cron. **The key includes criteria, judge model, and judge prompt version** — otherwise editing a task's criteria or swapping judge providers reuses scores computed under different rules (§2.10). **TTL exemption for active known-good:** a cache entry that backs the current known-good score for a task is exempt from TTL purge — purging it forces a fresh judge call on byte-identical output, and judge sampling/logprob jitter or a provider-side model update under the same model name can score differently, firing a regression caused entirely by the measuring instrument. The known-good's cached score stays valid until the task content changes (§2.10). **Judge variance check (Phase 0):** score the same output N times with the cache bypassed to measure judge variance. If variance > 0 under temperature=0, the judge is not deterministic and the core track's "any delta is signal" rule must be relaxed to the product track's tolerance band.

#### `canary_task_baselines` — Per-task baseline accuracy

```sql
CREATE TABLE canary_task_baselines (
    id            TEXT PRIMARY KEY,  -- UUID
    agent_name    TEXT NOT NULL,
    config_hash   TEXT NOT NULL,     -- annotation for attribution, NOT a partition key (§2.9)
    task_id       TEXT NOT NULL,
    task_hash     TEXT NOT NULL,     -- sha256(prompt+assertions+expected_output+temperature) — partition key (§2.10)
    accuracy      REAL NOT NULL,     -- mean accuracy across baseline runs
    ci_lower      REAL NOT NULL,
    ci_upper      REAL NOT NULL,
    run_count     INTEGER NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at    TEXT,              -- NULL = active, set when superseded
    FOREIGN KEY (task_id) REFERENCES canary_tasks(id),
    UNIQUE(agent_name, task_hash, task_id, expires_at)
);
CREATE INDEX idx_task_baseline_lookup ON canary_task_baselines(agent_name, task_hash, task_id);
```

Per-task baseline is computed from the last N completed runs where the task was NOT skipped (no template variables failed) and the run was NOT degraded (budget exhaustion, §2.9). Per-task accuracy = mean of trial-level accuracies across those runs. Minimum 3 runs with that task completed before a baseline is created. When a new baseline is computed, the old one's `expires_at` is set. A `task_hash` change starts a new window — the old window is archived, not compared (§2.10). **Note: the "minimum 3 runs" gate applies to the product/leaderboard track's variance baseline. The core track's known-good comparison (§2.9) has no such gate — the first clean run IS the known-good.**

### 2.8 Gold-Standard Authoring Methodology

**Purpose:** every task in the core set must have a gold standard that is (a) correct, (b) verifiable, and (c) calibrated to the assertion type. A gold standard is not just an `expected_output` string — it is the full task contract.

**Authoring process (per task):**

1. **Capability mapping** — the task must map to a capability the factory actually ships (reasoning, coding, extraction, instruction-following, tool-use). If it maps to none, it does not belong in the core set.
2. **Prompt hygiene** — concrete fixture data only. No `{{ }}` templates. No session fragments. The prompt must be self-contained: an agent with no prior context can execute it.
3. **Gold standard** — write the expected output as a *verifiable claim set*, not a prose blob:
   - For extraction: the exact fields and values (e.g. `Name: John Smith, Date: Jan 15 2024, Amount: $1,234.56`)
   - For reasoning: the answer + the key intermediate steps that must appear
   - For coding: the function signature + the test cases it must pass
   - For instruction-following: the ordered checklist of required elements
4. **Assertion calibration** — choose the assertion type by what the gold standard can verify:
   - `exact_match` — deterministic outputs (arithmetic, extraction with fixed fields)
   - `llm_judge` — open-ended outputs where correctness is judgment (summaries, proposals) — criteria must name the verifiable elements, not vibes
   - `contains` — only as a *necessary* check, never sufficient (weight 0.4)
   - `json_schema` — structured outputs
5. **Negative calibration** — for each task, verify the assertion FAILS on a deliberately wrong output. A gold standard that passes everything is not calibrated.
6. **Difficulty calibration** — the task must be solvable by the current best agent (else it measures impossibility, not regression) but not trivially (else it measures nothing). Target: 70-90% pass on the current baseline agent. **Tasks freeze after calibration.** Recalibrating a task produces a NEW task version (new `task_hash`, new baseline series) — it does not silently continue the old longitudinal series. Otherwise an improved agent saturates the task and sensitivity in the improvement direction is lost, and recalibration breaks comparison without anyone noticing (§2.10). **Known property, stated deliberately:** freeze + 70-90% target means every task has a built-in expiry — when agents improve past saturation, recalibration is required, which resets the series by design. This is a feature (the task stops measuring once the capability is saturated) not a defect; plan for periodic recalibration as agents improve.
7. **Stability check** — run the task 3× at temperature=0. If the score varies >10%, the prompt or assertion is ambiguous — fix before accepting.

**Core set curation (from the 23 existing tasks):**

| Verdict | Tasks | Action |
|---------|-------|--------|
| **Keep + fix** | arithmetic-reasoning (fill template), extract-structured-data, chart-interpretation, code-generation, document-qa, follow-multi-step-instructions, summarize-conversation, time-bound-response, tool-selection | Fix templates, add missing expected_output, calibrate assertions |
| **Keep as-is** | ci-lint-fix-e711-f841, realistic-tier3-proposal, spec-compliance-review-capability-probe | Add expected_output + assertions |
| **Remove from core** | all 10 `history-*` tasks | Session fragments, no gold standard. Archive (not delete) — they may inform future task design |
| **Remove from core** | llm-judge-sample | Test artifact, not a benchmark task |

**Result:** 12-task core set, all with gold standards, all calibrated, all split-aware.

### 2.9 Automatic Change Tracking (Regression Detection)

**Purpose:** when the factory changes (SOUL.md, model, provider, prefill, harness, config), automatically detect whether agent quality regressed — without waiting for a manual canary run.

**Trigger — agent fingerprint vector, not config-hash.** The old trigger (config-hash change) was a hole: `_compute_config_hash` hashes only `agent_name + model + task prompts` — a SOUL.md edit, prefill change, or config.yaml change does NOT change it, so the canary never fires on the changes most likely to cause regressions. The trigger is now a **fingerprint vector** — per-component hashes, so the alert can name WHAT changed, not just THAT something changed:

```
agent_fingerprint (vector, computed per agent):
  soul_hash      = sha256(SOUL.md content)
  prefill_hash   = sha256(prefill file content)
  config_hash    = sha256(config.yaml content)
  skills_hash    = sha256(skills dir listing + content)
  model          = agent's default model
  scorer_version = canary Scorer version (§2.10)
```

**Fingerprint is annotation, not partition key.** Same rule as config_hash: the fingerprint is recorded per run for attribution ("what changed when") but does NOT gate comparison. `task_hash` remains the partition key (§2.10). Otherwise every SOUL edit starts a new series and — since the factory changes constantly — no series ever forms.

**The watcher — proactive, not reactive.** The canary must fire without a human invoking it. A cron (every 15 min) does:

1. **Compute** the fingerprint vector for each covered agent.
2. **Compare** against the last recorded vector.
3. **On change: debounce** — wait for the fingerprint to be stable for 15 min before firing (Sean iterating on SOUL.md fires once, not five times). **The debounce window is measured from the FIRST observation of the new fingerprint, not from tick count** — a change made a minute before a tick must not be treated as stable at the next tick on a single observation. The watcher records when a new fingerprint was first seen and fires only after 15 min of continuous stability. Then fire **only the changed agent's** core set (a forge SOUL change does not run main's canary).
4. **Infra-down handling** — if the agent's model is unreachable (server down, provider 429), skip and retry next tick, mark the run `degraded` — **never fire a false regression alert** on infrastructure failure.
5. **First deployment** — the first watcher run establishes the baseline without alerting (no known-good exists yet). **The first known-good must be validated, not assumed:** a first run captured during a provider hiccup, a mid-edit SOUL state, or a misconfigured agent becomes the permanent reference — every subsequent healthy run then reads as an improvement, and real regressions relative to true-good never surface. Require the first known-good to pass §2.8's negative calibration, or to be explicitly human-accepted (Sean/Hound confirms the agent is in a known-good state before the first run is promoted).
6. **Self-monitoring** — the watcher writes a heartbeat + last-run timestamp. **The liveness alert must have an independent emitter.** If the watcher writes its own heartbeat AND raises its own alarm, a dead watcher raises nothing — a dead-man's switch wired to the thing that's dead (same shape as the `|| echo` gate and the GS-019 warning). The independent evaluator: **the dashboard computes heartbeat staleness at read time** — whenever anyone looks at the capability page, it checks the watcher's last-run timestamp and flags staleness. This runs on the dashboard's own process, not the watcher's. Additionally, the existing production-error sweep (ecosystem) checks the watcher's heartbeat file as a cron surface — a second independent emitter.

**Baseline model — last-known-good, not a rolling mean.** The factory changes constantly; requiring N=3 stable runs at a config before a baseline forms means no baseline ever forms. A rolling mean is a low-pass filter: it smooths the step-change we're trying to detect, and a sustained regression gets partially absorbed into the baseline meant to expose it. Instead:

- **Comparison point = the last known-good run** for the same task content (`task_hash`), with the fingerprint diff attached. The detector asks: "did this run regress relative to the last state we trusted?"
- **Task content hash (`task_hash`) IS a partition key.** A run whose `task_hash` differs from the window's is a different measurement — it starts a new series, it does not join the old one (§2.10).
- **The rolling window is retained only for noise estimation** — and only if the Phase 0 spike shows determinism does not hold. Under determinism, the window is not the comparison point.

**Process:**

1. **Detect** — the watcher fires when the fingerprint vector changes (or a manual `canary run --track` is invoked after a known change).
2. **Run the core set** — the 12-task core, `split=test`, temperature=0, **n=1 per task** (§2.3).
3. **Compare per-task** — each task's score vs the **last known-good run** for that task content. Per-task drift = `task_score - last_known_good_score`.
4. **Degraded-run refusal** — if the run hit budget exhaustion and fell back to `contains` assertions (§2.2 cost guard), the run marks itself `degraded` and **refuses comparison**. A score composed of judge-graded and keyword-graded tasks compared against a judge-only baseline reads as a regression that isn't one. Degraded runs are recorded but excluded from the series.
5. **Classify the change:**
   - **Regression** — a task drops below the last known-good score. **Under determinism (core track), any delta is signal by definition** — there is no tolerance band, because temperature=0 means the same task + same config produces the same output; a difference means something changed. **The multiple-comparisons guard is the confirmation re-run, not a 2-or-more rule.** If the false-alarm rate is genuinely zero (determinism holds), a 2-or-more rule would suppress real single-task regressions — recorded but never alerted. The correct guard: **re-run the one flagged task; if it differs again, it's real — alert.** Cheap, definitive, no signal loss. The 2-or-more rule is reserved for the product track (n=10, temp>0) where variance is real and the ~46% false-alarm math applies.
   - **Improvement** — a task rises above the last known-good score → record as improvement, promote to new known-good.
   - **No change** — score equals last known-good → no alert.
6. **Update the series** — the run joins the series **only if it is not degraded and not a flagged regression**. Flagged regressions are recorded and **excluded from the series until resolved or explicitly accepted** — otherwise a real regression drags the comparison point down and the detector forgets what it found. An accepted regression (Sean/Hound confirms it's expected) becomes the new known-good. No "N=3 stable runs" promotion gate — the known-good advances on each clean run.
7. **Alert** — regressions go to the ecosystem thread (topic 29) with: task name, before/after score, **fingerprint component diff** (e.g. "SOUL.md changed" — from the vector, not a scalar), and a link to the run.

**Regression with NO fingerprint change — the most important case.** A provider degradation (DeepSeek gets worse), a rate-limit regime, a dependency change — none touch files, none change the fingerprint, but all degrade output. The canary catches the regression; the fingerprint says "nothing changed." This is the canary working as intended, not a bug: **regression + no fingerprint change = investigate environment/model, not config.** The alert must say so explicitly.

**Coverage limit — stated explicitly, with the consequence drawn.** The canary measures what the 12-task core covers, nothing else. A SOUL.md change that alters tone, caution, or proactivity — none measured by the core — fires the watcher, runs the core, and reports "no regression detected" — **which is a false reassurance, since the honest answer is not measured.** That is the fake-clean-zero pattern (DPA §2-A) appearing in the benchmark layer rather than the UI. It also has a practical cost: most fingerprint changes will be outside the core's field of view, so most alerts will say "no regression," and people will learn to ignore the canary. **Fix: classify the fingerprint diff against the capability categories the core covers.** When the changed component (e.g. SOUL.md) maps to a capability the core does not measure, the alert says: **"fired; this change class is outside the core's coverage; not measured"** — not "no regression." Only a run where the changed component maps to a measured capability and all tasks pass may report "no regression."

**Fault-side attribution (Phase 3, after core is clean):** when a regression is detected, classify the failing trials with the interaction-centric taxonomy (edge + fault_side + mode) to determine whether the regression is model-side (SOUL/prompt fix), harness-side (code/config fix), or environment-side (external service). This is the Scale AI "Model or Harness?" (arXiv 2607.28802) contribution applied to the canary — it only works on a clean task set.

**Dashboard:** the capability page shows per-task accuracy over time with fingerprint-change markers — a regression is visible as a step-change at the marker, and the marker names the component that changed.

### 2.10 Measurement-Instrument Versioning

**Problem:** four distinct failure modes in this spec are instances of one missing concept — nothing ties a measurement to the instrument that produced it. A baseline computed under old task content, old assertions, or an old judge is compared against a new run as if they were the same measurement.

**Fix — every run records its instrument version, and a mismatch invalidates comparison:**

| Version field | Computed from | Invalidates comparison when |
|---------------|---------------|------------------------------|
| `task_hash` | sha256(prompt + assertions + expected_output + temperature) | Task content changed (Phase 3.5 rewrites prompts, recalibrates assertions) |
| `assertion_version` | assertion type + criteria text hash | Criteria edited |
| `judge_version` | judge model + judge prompt version | Judge provider swapped (Tier 2 ↔ Tier 1), judge prompt changed |
| `scorer_version` | Scorer class version | Scorer logic changed |

**Rules:**
1. **Baseline key includes `task_hash`** — `(agent_name, task_hash, task_id)` for the known-good series. A task content change starts a new series; the old series is archived, not compared.
2. **Judge cache key includes judge_version** — `sha256(task_id + output_hash + criteria + judge_model + judge_prompt_version)`. Cached scores computed under different rules must not be reused.
3. **A version mismatch invalidates rather than silently proceeds** — the run is recorded, flagged as `instrument_changed`, and excluded from comparison until a new series forms.

**This is the same coupling-failure pattern as the SOUL.md headings and the keyword table:** two artifacts that must agree, with nothing enforcing it. The version fields are the enforcement.

---

## 3. Industry Framework Alignment

### 3.1 Inspect AI Integration (Recommended)

[Inspect AI](https://inspect.ai) (UK AISI) is the recommended evaluation framework for ObserveCo alignment:

- Supports custom tasks with `expected_output` and LLM-as-judge scorers
- Built-in statistical comparison (Wilson CI, bootstrap, paired tests)
- Designed for agent evaluation, not just model evaluation
- MIT licensed, Python-native

**Integration path:** ObserveCo canary tasks can be exported as Inspect AI task definitions. Long-term: replace the custom Scorer with Inspect AI's scorer, keeping ObserveCo's UI/dashboard layer.

### 3.1.1 Inspect AI Verification

Before implementation, verify against current Inspect AI release:

1. **Version stability:** Check latest release at https://github.com/UKGovernmentBEIS/inspect_ai — confirm MIT license, Python-native, active maintenance
2. **Custom scorer API:** Verify Inspect AI supports custom scorers (LLM-as-judge, JSON schema, semantic similarity) matching ObserveCo's assertion types
3. **Task import/export:** Verify the Python task definition format supports all ObserveCo fields (`expected_output`, `few_shot_examples`, `temperature`)
4. **Fallback:** If Inspect AI is incompatible or unmaintained, maintain the custom Scorer enhanced per §2.2 — the export path is P3, not blocking

### 3.2 lm-eval-harness Compatibility

Maintain the existing lm-eval-harness integration for curated model benchmarks (MMLU, GSM8K, etc.). These remain **secondary benchmarks** — user-defined tasks with reference outputs are **primary**.

### 3.3 What We Don't Build

As per agent-quality-management-brief.md §9:
- **No evaluation metrics from scratch** — use Inspect AI or DeepEval if needed
- **No prompt management/playground** — Phoenix/LangFuse territory
- **No blind benchmarking without guidance** — all results come with honest pros/cons

---

## 4. Implementation Plan

**Ordering principle (2026-08-08):** Phase 3.5 (core-set curation) invalidates every existing baseline — prompts rewritten, expected_output added, assertions recalibrated. Running statistical work (Phases 1-2) against tasks about to be rewritten spends effort on measurements that will be thrown away. **Curate first, then fix the statistics on a stable task set.** The injected-regression falsification test (§5) is only meaningful once there is a stable core to validate against.

### Phase 0: Core Set Curation (P0 — 2026-08-08, from §2.8)

| Task | Effort | Files |
|------|--------|-------|
| Fix arithmetic-reasoning template (`{{ problem }}` → concrete) | ~0.5h | `canary_tasks` UPDATE |
| Add `expected_output` to 3 built-in tasks missing it (ci-lint-fix, realistic-tier3, spec-compliance) | ~1h | `canary_tasks` UPDATE |
| Archive 10 `history-*` tasks (set `split='archive'` or soft-disable) | ~0.5h | `canary_tasks` UPDATE |
| Remove llm-judge-sample from core | ~0.1h | `canary_tasks` UPDATE |
| Calibrate assertions per §2.8 (negative + stability checks) | ~3h | `canary_tasks` assertions, manual runs |
| **Temperature spike** — verify `hermes chat --temperature` end-to-end (§2.3) | ~1h | spike, before any determinism-dependent work |

### Phase 1: Scoring Validity (P0)

| Task | Effort | Files |
|------|--------|-------|
| Implement `llm_judge` assertion | ~4h | `canary.py:Scorer._llm_judge`, `canary_judge_cache` table |
| Add `expected_output` column | ~1h | `db.py` migration, `canary.py:create_task/update_task` |
| Add `json_schema` assertion type | ~2h | `canary.py:Scorer._json_schema` |
| Fix per-task drift comparison | ~2h | `baseline.py:compare()` |
| Fix z-test n1 calculation | ~0.5h | `baseline.py:compare()` |
| **Instrument versioning (§2.10)** — task_hash, assertion_version, judge_version, scorer_version on every run | ~3h | `db.py` migration, `canary.py`, `baseline.py` |

### Phase 2: Statistical Rigor (P1)

| Task | Effort | Files |
|------|--------|-------|
| Core set n=1 per task; product track trials=10 | ~1h | `canary.py:run()`, `canary_tasks` defaults |
| Add temperature control | ~2h | `canary_tasks.temperature` column, adapter changes |
| Add `semantic_similarity` assertion | ~3h | `canary.py:Scorer._semantic_similarity`, sentence-transformers dep |
| Bootstrap CI minimum n=5 guard (product track only) | ~0.5h | `canary.py:Scorer.bootstrap_ci` |
| **Degraded-run refusal** — budget-exhausted runs mark `degraded`, refuse baseline comparison (§2.9) | ~1h | `canary.py:run()`, `baseline.py` |

### Phase 3: Task Quality (P2)

| Task | Effort | Files |
|------|--------|-------|
| Set dev/test splits | ~1h | `canary_tasks.split` UPDATE |
| Add `tool_call_validation` assertion | ~3h | `canary.py:Scorer._tool_call_validation` |
| `code_executable` assertion | — | **Deferred to v0.7.0** — requires Docker/nsjail sandbox |

### Phase 3.6: Automatic Change Tracking (P2 — 2026-08-08, from §2.9)

| Task | Effort | Files |
|------|--------|-------|
| Agent fingerprint vector (soul/prefill/config/skills/model/scorer hashes) | ~2h | `canary.py:_compute_agent_fingerprint()` |
| Watcher cron (15 min): compute → compare → debounce → fire changed agent | ~3h | new `capability/canary_watcher.py`, cron |
| Infra-down handling (skip/retry/degraded, never false regression) | ~1h | `canary_watcher.py` |
| Watcher self-monitoring (heartbeat + last-run, alert on death) | ~1h | `canary_watcher.py`, heartbeat check |
| Last-known-good comparison (task_hash-keyed, fingerprint as annotation) | ~2h | `baseline.py:compare()` |
| Multiple-comparisons guard (2+ tasks or confirmation re-run) | ~1h | `baseline.py:compare()` |
| Regression alert to ecosystem thread (with fingerprint component diff) | ~1h | `capability/drift.py`, dashboard routes |
| Fault-side attribution on regression trials (Phase 3 of paper integration) | ~4h | `capability/canary.py`, classifier reuse |
| **Injected-regression falsification test (§5)** — degrade agent, confirm fires; control arm, confirm doesn't | ~2h | test harness |

### Phase 4: Industry Alignment (P3)

| Task | Effort | Files |
|------|--------|-------|
| Inspect AI export format | ~4h | New `capability/inspect_export.py` |
| Inspect AI scorer integration | ~8h | Replace or wrap custom Scorer |

---

## 5. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| LLM-judge coverage | 7/9 built-in tasks use llm_judge by default (core set: 12 tasks, judge where judgment is required) | Task assertion audit |
| Bootstrap CI stability | CI width < 20% of mean at n=10 (product track only — core track is n=1, no CI) | Simulation vs actual |
| Per-task drift accuracy | Per-task drift matches manual audit in 90% of cases | Manual review |
| Temperature reproducibility | Same task × same config = same result 95%+ of time (controlled path only — SOUL.md/memory/tool variance excluded, §2.3 spike) | Run same task 3x |
| Template elimination | 0 tasks with `{{ }}` templates | `canary_tasks` scan |
| Category breakdown | All tasks have category + difficulty | `canary_tasks` scan |
| **Core set size** | 12 tasks, all with gold standards | `canary_tasks` scan (2026-08-08) |
| **Session fragments in core** | 0 `history-*` tasks in active core | `canary_tasks` scan |
| **Change-triggered runs** | SOUL.md/prefill/config/skills change auto-runs the changed agent's core set | `canary_runs` fingerprint-vector diff |
| **Watcher liveness** | Watcher heartbeat fresh; alert if it stops firing | Watcher heartbeat + last-run timestamp |
| **Regression detection latency** | Regression flagged within 1-2 runs of config change (single-task flags require a confirmation re-run per §2.9's determinism guard) | Alert log |
| **Sensitivity (falsification test)** | Deliberately degrade an agent (truncate SOUL.md, swap to weaker model, corrupt prefill) → run core set → regression fires | Injected-regression test, run before Phase 3.6 ships |
| **False-positive rate (falsification test)** | Run unchanged config twice → no regression fires | Same test, control arm |

---

## 6. Constraints Register

| # | Constraint | Type | Notes |
|---|-----------|------|-------|
| 1 | LLm-judge requires API key | MUST | Falls back to `contains` if `OBSERVECO_LLM_API_KEY` not set |
| 2 | sentence-transformers dep | SHOULD | 80MB model, local, for `semantic_similarity` |
| 3 | Code execution sandbox | SHOULD | **Deferred to v0.7.0** — subprocess isolation insufficient. Requires Docker/nsjail sandbox. (Constraint #3 in the original draft said "use subprocess + timeout + restricted env vars" — that contradicts §2.2 and §7, which defer. The deferral wins.) |
| 4 | Inspect AI integration | MAY | Long-term alignment, not blocking v0.6.0 |
| 5 | Temperature=0 default | MUST | Per-task override allowed, but default is deterministic |

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:---------:|:------:|-----------|
| LLM-judge adds cost/trials | High | Token usage increase | Cache judge results; use 5 trials for judge tasks (product track only — core track is n=1) |
| sentence-transformers dependency | Medium | +80MB install | Make optional; fall back to `contains` if not installed |
| Code execution sandbox | Medium | Security risk | **Deferred to v0.7.0** — subprocess isolation insufficient. Requires Docker/nsjail sandbox. |
| Fixture migration breaks existing runs | Low | Historical comparison breaks | Keep old prompts in archive; new runs use new format |
| Temperature=0 not supported by all providers | **High (present blocker)** | Determinism premise fails | **The Hermes adapter has no temperature flag today (§2.3) — this is a present blocker, not a low risk.** The Phase 0 spike verifies `hermes chat --temperature` end-to-end before any determinism-dependent work. If it fails, the core track falls back to the variance model (n=10, temp>0, CI). |

---

## 8. File Changes

| File | Change |
|------|--------|
| `src/observeco/db.py` | Migration: add `category`, `difficulty`, `expected_output`, `few_shot_examples`, `system_override`, `temperature` columns to `canary_tasks`; add `canary_judge_cache` table (key includes criteria + judge model + prompt version, §2.10); add `canary_task_baselines` table (key includes `task_hash`, §2.10); add `task_hash`, `assertion_version`, `judge_version`, `scorer_version`, `degraded` columns to `canary_runs`/`canary_results` |
| `src/observeco/capability/canary.py` | Implement `llm_judge`, `json_schema`, `semantic_similarity`, `ordering`, `tool_call_validation`; fix per-task drift; core set n=1 per task, product track trials=10; add temperature control; add scoring weights; degraded-run refusal on budget exhaustion; instrument versioning on every run; `_compute_agent_fingerprint()` vector |
| `src/observeco/capability/canary_watcher.py` | **New (Phase 3.6)** — 15-min watcher: compute fingerprint vector → compare → debounce → fire changed agent's core set; infra-down handling; self-monitoring heartbeat |
| `src/observeco/capability/baseline.py` | Fix per-task drift; fix n1 calculation; last-known-good comparison (task_hash-keyed, fingerprint as annotation); confirmation-rerun guard (core) / 2-or-more rule (product); `canary_task_baselines` management |
| `src/observeco/dashboard/routes/capability.py` | Update task list to show category/difficulty; update task editor for new fields; per-task accuracy over time with config-change markers |
| `src/observeco/capability/fixtures/` | New — concrete fixture data files for built-in tasks |
| `src/observeco/capability/inspect_export.py` | New (Phase 4) — Inspect AI task format export |