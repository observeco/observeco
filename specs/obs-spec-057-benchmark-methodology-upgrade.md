# obs-spec-057 — Benchmark Methodology Upgrade

**Spec ID:** obs-spec-057
**Title:** User-defined benchmark methodology — assertion system, scoring, and statistical validity upgrade
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-050 (data model), obs-spec-051 (canary runner), obs-spec-055 (task definition)
**Master plan ref:** v0.6.0 "Agent Quality Management"
**Created:** 2026-07-06

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

**Caching:** Judge results cached by `(task_id, sha256(output))` to avoid re-evaluating identical outputs across trials. Cache stored in `canary_judge_cache` table.

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

- Default trials increased from 3 to **10** per task (configurable)
- For `llm_judge` tasks, default to **5** trials (cost)
- Bootstrap CI requires minimum **n=5** to produce meaningful intervals
- For n < 5, report point estimate without CI

#### Per-Task Drift Fix

```python
# BEFORE (broken): compares single task accuracy vs AGGREGATE baseline
task_drift = (tr["accuracy"] - baseline_accuracy) * 100

# AFTER (correct): compares single task accuracy vs THAT TASK'S baseline
task_baseline = get_per_task_baseline(agent_name, config_hash, task_id)
task_drift = (tr["accuracy"] - task_baseline.accuracy) * 100
```

**New table:** `canary_task_baselines` — per-task baseline accuracy per agent+config. See §2.7 for schema.

**Per-task baseline computation:** Baseline is computed from the last N completed runs where the task was NOT skipped (no template variables unresolved). Per-task accuracy = mean of trial-level accuracies across those runs (not pass/fail binary — uses the `accuracy` field from `canary_results`). Minimum 3 runs with that task completed before a per-task baseline is created. Tasks that were skipped in some runs (due to template variables) are excluded from those runs only — the baseline uses only runs where the task ran.

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

**Canary runs default to `split=test`** — monitoring only.
**Harness optimization** uses `split=dev` (obs-spec-056).

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
    cache_key    TEXT PRIMARY KEY,  -- sha256(task_id + output_hash)
    task_id      TEXT NOT NULL,
    output_hash  TEXT NOT NULL,     -- sha256(agent_output)
    score        REAL NOT NULL,     -- 0.0 to 1.0
    reasoning    TEXT,
    model_used   TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES canary_tasks(id)
);
CREATE INDEX idx_judge_cache_task ON canary_judge_cache(task_id);
```

Cache key is `sha256(f"{task_id}:{sha256(output)}")`. Lookup before calling LLM judge. If found and created within TTL (default 7 days), reuse cached score. Purge entries older than 7 days on maintenance cron.

#### `canary_task_baselines` — Per-task baseline accuracy

```sql
CREATE TABLE canary_task_baselines (
    id            TEXT PRIMARY KEY,  -- UUID
    agent_name    TEXT NOT NULL,
    config_hash   TEXT NOT NULL,
    task_id       TEXT NOT NULL,
    accuracy      REAL NOT NULL,     -- mean accuracy across baseline runs
    ci_lower      REAL NOT NULL,
    ci_upper      REAL NOT NULL,
    run_count     INTEGER NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at    TEXT,              -- NULL = active, set when superseded
    FOREIGN KEY (task_id) REFERENCES canary_tasks(id),
    UNIQUE(agent_name, config_hash, task_id, expires_at)
);
CREATE INDEX idx_task_baseline_lookup ON canary_task_baselines(agent_name, config_hash, task_id);
```

Per-task baseline is computed from the last N completed runs where the task was NOT skipped (no template variables failed). Per-task accuracy = mean of trial-level accuracies across those runs. Minimum 3 runs with that task completed before a baseline is created. When a new baseline is computed, the old one's `expires_at` is set.

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

### Phase 1: Scoring Validity (P0)

| Task | Effort | Files |
|------|--------|-------|
| Implement `llm_judge` assertion | ~4h | `canary.py:Scorer._llm_judge`, `canary_judge_cache` table |
| Add `expected_output` column | ~1h | `db.py` migration, `canary.py:create_task/update_task` |
| Add `json_schema` assertion type | ~2h | `canary.py:Scorer._json_schema` |
| Fix per-task drift comparison | ~2h | `baseline.py:compare()` |
| Fix z-test n1 calculation | ~0.5h | `baseline.py:compare()` |

### Phase 2: Statistical Rigor (P1)

| Task | Effort | Files |
|------|--------|-------|
| Increase default trials to 10 | ~1h | `canary.py:run()`, `canary_tasks` defaults |
| Add temperature control | ~2h | `canary_tasks.temperature` column, adapter changes |
| Add `semantic_similarity` assertion | ~3h | `canary.py:Scorer._semantic_similarity`, sentence-transformers dep |
| Bootstrap CI minimum n=5 guard | ~0.5h | `canary.py:Scorer.bootstrap_ci` |

### Phase 3: Task Quality (P2)

| Task | Effort | Files |
|------|--------|-------|
| Migrate 6 template tasks to concrete fixtures | ~4h | `canary_tasks` UPDATE, fixture files |
| Set dev/test splits | ~1h | `canary_tasks.split` UPDATE |
| Add `category`, `difficulty` columns | ~1h | `db.py` migration, `canary.py` |
| Add `tool_call_validation` assertion | ~3h | `canary.py:Scorer._tool_call_validation` |
| `code_executable` assertion | — | **Deferred to v0.7.0** — requires Docker/nsjail sandbox |

### Phase 4: Industry Alignment (P3)

| Task | Effort | Files |
|------|--------|-------|
| Inspect AI export format | ~4h | New `capability/inspect_export.py` |
| Inspect AI scorer integration | ~8h | Replace or wrap custom Scorer |

---

## 5. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| LLM-judge coverage | 7/9 tasks use llm_judge by default | Task assertion audit |
| Bootstrap CI stability | CI width < 20% of mean at n=10 | Simulation vs actual |
| Per-task drift accuracy | Per-task drift matches manual audit in 90% of cases | Manual review |
| Temperature reproducibility | Same task × same config = same result 95%+ of time | Run same task 3x |
| Template elimination | 0 tasks with `{{ }}` templates | `canary_tasks` scan |
| Category breakdown | All tasks have category + difficulty | `canary_tasks` scan |

---

## 6. Constraints Register

| # | Constraint | Type | Notes |
|---|-----------|------|-------|
| 1 | LLm-judge requires API key | MUST | Falls back to `contains` if `OBSERVECO_LLM_API_KEY` not set |
| 2 | sentence-transformers dep | SHOULD | 80MB model, local, for `semantic_similarity` |
| 3 | Code execution sandbox | SHOULD | Use `subprocess` + `timeout` + restricted env vars |
| 4 | Inspect AI integration | MAY | Long-term alignment, not blocking v0.6.0 |
| 5 | Temperature=0 default | MUST | Per-task override allowed, but default is deterministic |

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:---------:|:------:|-----------|
| LLM-judge adds cost/trials | High | Token usage increase | Cache judge results; use 5 trials for judge tasks |
| sentence-transformers dependency | Medium | +80MB install | Make optional; fall back to `contains` if not installed |
| Code execution sandbox | Medium | Security risk | **Deferred to v0.7.0** — subprocess isolation insufficient. Requires Docker/nsjail sandbox. |
| Fixture migration breaks existing runs | Low | Historical comparison breaks | Keep old prompts in archive; new runs use new format |
| Temperature=0 may not be supported by all providers | Low | Some providers ignore it | Document provider compatibility; warn if ignored |

---

## 8. File Changes

| File | Change |
|------|--------|
| `src/observeco/db.py` | Migration: add `category`, `difficulty`, `expected_output`, `few_shot_examples`, `system_override`, `temperature` columns to `canary_tasks`; add `canary_judge_cache` table; add `canary_task_baselines` table |
| `src/observeco/capability/canary.py` | Implement `llm_judge`, `json_schema`, `semantic_similarity`, `ordering`, `tool_call_validation`; fix per-task drift; increase default trials; add temperature control; add scoring weights |
| `src/observeco/capability/baseline.py` | Fix per-task drift; fix n1 calculation; add `canary_task_baselines` management |
| `src/observeco/dashboard/routes/capability.py` | Update task list to show category/difficulty; update task editor for new fields |
| `src/observeco/capability/fixtures/` | New — concrete fixture data files for built-in tasks |
| `src/observeco/capability/inspect_export.py` | New (Phase 4) — Inspect AI task format export |