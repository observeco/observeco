# obs-spec-088 — MemoHarness Experience-Based Adaptation (v0.7.0)

**Spec ID:** obs-spec-088
**Title:** MemoHarness experience-based harness adaptation + Phantom Guardrails safety layer
**Status:** DRAFT (not started — no code exists)
**Owner:** Main
**Depends on:** obs-spec-056 (v0.6.0 loop, evaluation-only), obs-spec-050 (data model), obs-spec-057 (benchmark methodology, dev/test split)
**Master plan ref:** v0.7.0 "Automated Harness Optimization" (row #56b)
**Papers:**
- Huang et al., "MemoHarness: Agent Harnesses That Learn from Experience," arXiv 2607.14159, July 2026. [Paper](https://arxiv.org/abs/2607.14159)
- Wang et al., "Phantom Guardrails: When Self-Improving Agent Harnesses Fix Failures That Never Happened," arXiv 2607.13083, July 2026. [Paper](https://arxiv.org/abs/2607.13083)
- Wang et al., "Rethinking the Evaluation of Harness Evolution for Agents," arXiv 2607.12227, July 2026. [Paper](https://arxiv.org/abs/2607.12227) — evaluation-fairness layer (matched-budget TTS baseline + held-out generalization).

---

## 0. Honest Status of the v0.6.0 Foundation

Before scoping v0.7.0, the actual state of the v0.6.0 loop (verified 2026-07-19 against `capability/harness.py`):

| Capability | Reality |
|------------|---------|
| Proposer (`_propose_edit`) | ✅ Exists — reads frontier + canary trajectories, returns edit descriptor |
| Classifier (`_classify_edit`) | ✅ Exists — classifies edits (task-specific / generalizable etc.) |
| Leakage audit (`_check_leakage`) | ✅ Exists — rejects candidates that touch test split |
| Apply edit (`_apply_edit`) | ⚠️ **No-op on live harness** — evaluates against a temp profile, never hot-swaps SOUL.md |
| Frontier promotion | ⚠️ Records `promoted=True` but the live harness never changes |
| Experience bank | ❌ Does not exist |
| Similarity retrieval | ❌ Does not exist (only naive keyword overlap in `history_tasks.py`) |
| 6 control dimensions | ❌ `HarnessConfig` has 5 static axes, not mutable by the loop |
| **Phantom Guardrails check** | ❌ **Does not exist — this is the critical safety gap** |

**Implication:** v0.7.0 must (a) close the apply-edit no-op before experience adaptation is meaningful, and (b) add the Phantom Guardrails fabrication check as a hard gate before any edit is accepted into the loop.

---

## 1. What This Spec Adds

Two distinct layers on top of the v0.6.0 loop:

1. **Experience Bank (MemoHarness)** — a persistent, queryable memory of past harness-optimization episodes and agent execution patterns, used to ground future proposals in real evidence.
2. **Phantom Guardrails Gate (mandatory safety layer)** — a deterministic pre-accept check that rejects any proposed edit citing a failure that did not occur in observed episodes.

---

## 2. Phantom Guardrails Gate (MUST ship with v0.7.0)

### 2.1 The failure mode

Wang et al. (arXiv 2607.13083) show that LLM-based harness proposers **hallucinate failures that never happened** and add "phantom guardrails" — fixes for nonexistent problems. Mechanism:

- In a deterministic micro-lab (Counterfactual Fabrication Lab) where the correct action is *do nothing*:
  - On **featureless legal input**: 0/60 runs fabricated a failure.
  - On **legal input containing a rule-shaped pattern** (resembling a familiar game rule): **15/60 runs** invented a failure, enabled a guardrail for a nonexistent rule, and cited a violation a byte-exact oracle refuted.
- The effect is **structured, not indiscriminate** — it appears only when **three conditions coincide**:
  1. A **rule-shaped pattern** in the input (something that looks like a violation trigger),
  2. An **open-ended rule set** the proposer is free to extend,
  3. An **instruction that presupposes failures** ("fix the failures you observe").
- Removing any one condition eliminates the fabrication.
- It is **not reward hacking and not over-refusal** — the phantom guardrail changes no true outcome and cannot improve an already-perfect suppression score. It is invisible to suppression-only acceptance.
- **Critical compounding risk:** inside an **add-only accept loop**, the phantom guardrail re-enters even *without* the failure-presupposing instruction (the loop's "keep adding" role supplies the demand), and once in, it **stays**.

### 2.2 Countermeasures mandated by this spec

| # | Countermeasure | Maps to condition eliminated |
|---|----------------|------------------------------|
| PG-1 | **Do not presuppose failures.** The proposer prompt must ask "propose an improvement" — never "fix the failures you observe." | Condition 3 |
| PG-2 | **Fabrication oracle.** Before accepting any edit, verify every cited failure against an observed-episode log. If a cited violation has no matching record (byte-exact or near-match on episode id + assertion id + timestamp), reject the edit as a phantom. | Conditions 1+2 |
| PG-3 | **Closed rule set by default.** The harness may only *enable* guardrails for failure classes that have at least N≥1 observed occurrences in the episode log. New failure classes require human approval (out-of-loop). | Condition 2 |
| PG-4 | **Abstain-on-legal.** If the optimizer cannot find a real failure to address, it must emit "no edit" — not a speculative guardrail. Log abstentions. | All |
| PG-5 | **Warrant-aware acceptance, not add-only.** The paper tests three acceptance rules: (a) accept-if-not-worse → phantom enters and stays (absorbing); (b) strict-improvement → phantom rides a strictly-improving batch (qwen3.7-max: 2/12); (c) **warrant-aware acceptance** → phantom is excluded. ObserveCo MUST use warrant-aware acceptance: an edit is accepted only if (1) the suppression proxy improves AND (2) every cited failure is verified against the episode log by the fabrication oracle. Acceptance is not monotonic — removing a previously-added guardrail (because the underlying failure was later found to be phantom) MUST be permitted. The loop is edit-and-revert, not append-only. | Compounding risk |
| PG-6 | **Proposer-model fabrication risk grading.** The paper shows a per-proposer capability gradient: glm-5.1 fabricated 11/12, deepseek-v4-pro 1/12, deepseek-v4-flash 0/12. Stronger models fabricate less. The proposer model must be logged per iteration. If the fabrication rate exceeds 20% across the last 10 iterations, the spec must warn and suggest switching to a stronger proposer model. The `harness gate test` self-check should report fabrication rate per model. | All |

### 2.3 `PhantomGuardrailGate` (proposed interface)

```python
class PhantomGuardrailGate:
    """Reject proposed edits that cite failures not present in observed episodes.

    Blocks the 'phantom guardrail' failure mode (Wang et al. 2026, arXiv 2607.13083).
    """

    def __init__(self, episode_log: EpisodeLog, min_observations: int = 1):
        self.episode_log = episode_log
        self.min_observations = min_observations

    def check(self, edit: dict) -> tuple[bool, str]:
        """Return (accepted, reason).

        An edit is accepted only if every failure class it references has been
        observed >= min_observations times in the episode log. Edits that
        introduce a brand-new guardrail class with zero observations are rejected
        (PG-3) unless flagged human_review=True.
        """
        cited = edit.get("cited_failures", [])
        for failure in cited:
            obs = self.episode_log.count_observations(failure["class"])
            if obs < self.min_observations:
                return False, (
                    f"Phantom guardrail rejected: failure class "
                    f"'{failure['class']}' has {obs} observed occurrences "
                    f"(min {self.min_observations}). No real failure to fix."
                )
        return True, "All cited failures observed in episode log."
```

`EpisodeLog` is the source of truth: a queryable store of (agent_run_id, task_id, assertion_id, outcome, error_type, timestamp) records derived from `canary_results`, `errors`, `pulse_log`, `token_logs`.

### 2.4 Where it sits in the loop

```
propose → classify → [PhantomGuardrailGate.check] → apply(temp) → evaluate
                         ↑ reject phantom here, before any temp-profile eval
                       → [EvaluationFairnessGate.check] → promote
                            ↑ must beat matched-budget TTS baseline + generalize to held-out
```

The gate runs **before** `_apply_edit`. A phantom edit never reaches evaluation, so it never accumulates cost or pollutes the frontier.

---

## 2.5 Evaluation Fairness Gate (Rethinking Evaluation, arXiv 2607.12227)

Wang et al. compare four methods under a unified budget protocol: parallel sampling, sequential refinement, harness evolution, and **harness scaling** (instance-guided harness adaptation — updates harness per-task, not cross-task). Their empirical results on Terminal-Bench 2.1 with Claude Opus 4.6 and GPT-5.4:

| Finding | Data |
|---------|------|
| Harness evolution does NOT consistently beat TTS | pass@1: Harness Evolution 73.0 vs Parallel Sampling 84.8 (Claude) |
| Gains show up in pass@k, not pass@1 | pass@1 barely improves; pass@5 improves — harness doesn't help solve new tasks, just makes more attempts viable |
| Edits memorize fixes, not strategies | §5.1: "most edits memorize fixes rather than distilling strategies... much of this information is precisely what a competent agent can rediscover through exploration within a single rollout" |
| Context bloat offsets gains | Growing persistent prompt text from accumulated edits introduces context bloat that can offset remaining gains |
| No generalization to held-out tasks | Table 3: evolved harness yields +0.6 avg on held-out test set (vs large gains on training tasks) |
| Harness evolution only valuable when two conditions hold | §5.2: (1) tasks difficult enough that agents leave substantial headroom, (2) performance depends heavily on the harness |

### Mandatory requirements

| # | Requirement | Detail |
|---|-------------|--------|
| EF-1 | **Matched-budget TTS baseline (all three variants)** | Every candidate is compared against parallel sampling, sequential refinement, AND harness scaling baselines under equal feedback + inference budget. A candidate is promoted only if `(candidate.dev_score − incumbent.dev_score) > (best_tts.dev_score − incumbent.dev_score) + min_delta`. If any TTS baseline already captures the gain, the "improvement" is search, not design — reject with `reason='search-budget-illusion'`. |
| EF-2 | **pass@1 improvement, not just pass@k** | The promotion gate must use pass@1, not pass@k. If the candidate improves pass@k but not pass@1, it means the harness doesn't help the agent *solve* new tasks — it just makes more attempts viable. That's search, not design. Reject with `reason='passk-not-pass1'`. |
| EF-3 | **Held-out generalization** | Dev gain and held-out test gain are both reported per candidate. A candidate that improves dev but regresses or is flat on held-out tasks is NOT promoted (flagged `outcome='no_generalization'`). |
| EF-4 | **Context bloat budget** | Track cumulative prompt size across iterations. If the frontier harness's prompt exceeds `context_bloat_threshold` (default: 2× initial prompt, configurable via `--context-bloat-threshold` CLI flag), flag with `reason='context-bloat'` and do NOT promote further additions without removing equivalent text. The paper shows accumulated edits introduce context bloat that offsets gains. |
| EF-5 | **Precondition check: headroom + harness-sensitivity** | Before running the loop, verify (1) the agent leaves ≥10% headroom on dev tasks (accuracy < 90%), and (2) canary tasks are harness-sensitive (grid report shows ≥5pp spread across configs). If either condition fails, skip the loop — the paper shows harness evolution yields marginal gains when tasks are too easy or harness-insensitive. |

**Expected outcome:** The paper's empirical result is that evolution rarely beats matched-budget TTS and generalizes poorly. A loop that promotes nothing (because TTS matches or beats every candidate) is a *valid, correct* result — not a failure. Surface "no harness improvement over TTS baseline" as a first-class finding, consistent with the HF plateau observation (obs-spec-056 §6).

---

## 3. Experience Bank (MemoHarness)

### 3.1 Dual-layer structure

| Layer | Content | Source |
|-------|---------|--------|
| **Per-case** | Diagnoses of individual agent runs: what failed, why, what edit was proposed, did it help | `canary_results`, `harness_optimization_runs`, `harness_edits` |
| **Global patterns** | Cross-run aggregated patterns: "edits of type X improve agent Y by Z% on task class W" | Derived from the per-case layer on a schedule |

**⚠️ Risk — "memorize fixes, not strategies" (Rethinking §5.1):** Wang et al. found that most harness edits are task-specific rules (prescribed command orderings, verified dataset properties) that a competent agent could rediscover on its own. The experience bank risks encoding exactly this kind of task-specific memorization, which:
1. Does not generalize to held-out tasks (EF-3 will catch this)
2. Introduces context bloat that offsets gains (EF-4 will catch this)

**Mitigation:** The experience bank's global-pattern layer must aggregate by *failure class*, not by *task id*. A per-case diagnosis that is task-specific ("ARENA-00013 failed because B2 was repeated") must be abstracted to a failure class ("move-repetition") before it enters the global layer. The classifier (`_classify_edit` in harness.py) already labels edits as "task-specific" vs "generalizable" — only "generalizable" edits may be promoted to the global layer.

### 3.2 New DB tables

```sql
CREATE TABLE IF NOT EXISTS harness_experiences (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    layer           TEXT NOT NULL,            -- 'per_case' | 'global_pattern'
    source_run_id   TEXT,                     -- harness_optimization_runs.id (per_case)
    episode_ref     TEXT,                     -- canary_results row id
    failure_class   TEXT,                     -- e.g. 'timeout', 'parser_error'
    diagnosis       TEXT,                     -- LLM or rule-based diagnosis
    proposed_edit   TEXT,                     -- edit descriptor
    outcome         TEXT,                     -- 'helped' | 'no_effect' | 'harmed' | 'phantom_rejected'
    observed_count  INTEGER DEFAULT 0,        -- for PG-3 closed-rule-set check
    embedding       BLOB,                     -- for similarity retrieval (optional, see §3.4)
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_he_agent ON harness_experiences(agent_name, layer);
CREATE INDEX IF NOT EXISTS idx_he_failure ON harness_experiences(failure_class);

CREATE TABLE IF NOT EXISTS harness_control_dims (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL UNIQUE,
    -- The 6 editable control dimensions (Huang et al.):
    context         TEXT,     -- context window / memory management strategy
    tools           TEXT,     -- tool-selection and tool-feedback policy
    orchestration   TEXT,     -- sub-agent / delegation policy
    memory          TEXT,     -- long-term memory read/write policy
    decoding        TEXT,     -- temperature / sampling policy
    output          TEXT,     -- output formatting / validation policy
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
-- ponytail: No FK on agent_name — SQLite FKs are off by default and
-- agent_name is not a PK in any parent table. Orphan cleanup is
-- handled explicitly in the lifecycle (see §5 "Agent profile deleted").
```

### 3.3 Retrieval

`retrieve_similar(episode)` returns the k most relevant past experiences for a new optimization episode.

- **MVP (no new dependency):** exact/near match on `failure_class` + `agent_name`. This satisfies the closed-rule-set check (PG-3) and gives the proposer grounding.
- **Upgrade path:** embedding-based similarity (sentence-transformers or the existing litellm adapter). Opt-in, behind a config flag. **New dependency must be approved by Sean** — do not add silently.

### 3.4 6 control dimensions

Huang et al. define 6 editable control dimensions. These are **mutable harness parameters** the optimizer may adjust (unlike the v0.6.0 static `HarnessConfig`). The optimizer proposes dimension changes; the Phantom Guardrails gate validates the cited failure before the change is applied.

| Dimension | What it controls |
|-----------|------------------|
| context | Context window management, what to retain/evict |
| tools | Tool-selection policy, tool-result feedback mode |
| orchestration | Delegation / sub-agent spawn policy |
| memory | Long-term memory read/write triggers |
| decoding | Sampling temperature, top-p |
| output | Output schema validation, formatting |

**Note:** These are aspirational until the apply-edit no-op (§0) is fixed. v0.7.0 must ship apply-edit *before* dimension mutation, or the dimensions are decoration.

---

## 4. CLI

```
observeco harness optimize [--agent AGENT] [--iterations N] [--with-experience] [--no-phantom-gate] [--context-bloat-threshold N]
observeco harness experience [--agent AGENT]          # show experience bank stats
observeco harness experience clear [--agent AGENT]    # prune (with confirmation)
observeco harness gate test [--agent AGENT]           # run Counterfactual Fabrication Lab self-check
```

- `--with-experience` enables experience-bank retrieval for the proposer.
- `--no-phantom-gate` is a **debug-only** flag that disables PG-2/PG-3. It must refuse to run inside any scheduled/cron context. Default: gate ON.
- `--context-bloat-threshold` sets the max prompt size multiplier (default: 2.0). The loop stops promoting additions when the frontier harness's prompt exceeds `initial_prompt_size × threshold`.

---

## 5. Lifecycle & Failure Modes (Requirements-Fidelity)

| Phase | Happy path | Failure / empty / degraded state |
|-------|------------|----------------------------------|
| Cold start | Experience bank empty → proposer runs without retrieval (same as v0.6.0) | No error; log "experience bank cold" |
| Episode log empty | PG gate sees 0 observations for all classes → every new guardrail rejected (PG-3) | Proposer must abstain (PG-4); loop records "no edit" and continues |
| Similarity search no match | Fall back to failure_class exact match | Log "no similar experience" |
| Apply-edit fails | Temp profile eval runs, result recorded | Skip iteration, log warning (same as v0.6.0) |
| Phantom detected | Edit rejected at gate, recorded with `outcome='phantom_rejected'` | No temp-profile eval, no cost |
| Human removes a phantom guardrail later | Edit-and-revert permitted (PG-5) | Loop must support removing, not just adding |
| Agent profile deleted | Experience bank persists (separate table). `harness_control_dims` row cleaned up via `DELETE FROM harness_control_dims WHERE agent_name = ?`. Old experiences tagged stale. | Re-accumulates on next runs; old experiences tagged stale |

---

## 6. Success Metrics (testable)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Phantom rejection rate | 100% of edits citing 0-observation failures rejected | `COUNT(*) WHERE outcome='phantom_rejected'` vs proposed edits |
| Abstention on legal input | ≥ 95% (target, vs 0/60 baseline in paper) | `harness gate test` Counterfactual Fabrication Lab self-check |
| Experience grounding | ≥ 50% of proposals reference ≥1 real past experience | `harness_experiences` join on accepted edits |
| Apply-edit effectiveness | Measurable score gain on live agent after promotion | `harness_control_dims` diff vs baseline canary run (requires §0 fix) |
| No compounding phantoms | 0 phantom guardrails persist after a revert cycle | Audit `harness_experiences` for orphaned phantom classes |
| Matched-budget TTS delta | Candidate dev gain over incumbent must exceed ALL TTS baseline gains (parallel sampling, sequential refinement, harness scaling) at equal budget | `candidate.dev_score - best_tts.dev_score` logged per iteration |
| pass@1 improvement | Candidate must improve pass@1, not just pass@k | `candidate.pass1 - incumbent.pass1` > 0 |
| Held-out generalization | Dev gain and held-out test gain both reported; regression on held-out blocks promotion | `dev_score - test_score` delta per candidate |
| Context bloat | Frontier prompt size stays < 2× initial | Cumulative prompt char count per iteration |
| Precondition headroom | Agent accuracy < 90% on dev before loop runs | Canary baseline accuracy |
| Precondition harness-sensitivity | Grid report shows ≥5pp spread across configs | Grid results from obs-spec-054 |

---

## 7. Constraints Register

| # | Constraint | Type | Notes |
|---|-----------|------|-------|
| 1 | **Phantom Gate is non-bypassable in scheduled runs** | MUST | `--no-phantom-gate` refused inside cron. Same class of guardrail as leakage audit. |
| 2 | **Closed rule set by default** | MUST | New failure-class guardrails need ≥1 observation or human review. |
| 3 | **Apply-edit must work before dimension mutation** | MUST | Shipping 6 mutable dimensions on a no-op apply is decoration. |
| 4 | **No silent new dependencies** | MUST | Embedding-based retrieval requires Sean's explicit approval. |
| 5 | **Edit-and-revert, not append-only** | MUST | Loop must support removing phantom guardrails (PG-5). |
| 6 | **Dev/test split required** | MUST | Inherited from obs-spec-056. |
| 7 | **Read-only tasks only** | MUST | Inherited from obs-spec-056. |
| 8 | **Evaluation fairness (matched-budget TTS, all 3 variants)** | MUST | Every promoted candidate must beat parallel sampling, sequential refinement, AND harness scaling baselines under equal feedback + inference budget (Rethinking Evaluation, arXiv 2607.12227). Gains explained by search alone are not harness improvements. |
| 9 | **pass@1, not pass@k** | MUST | Promotion gate uses pass@1. Candidates that improve only pass@k are search, not design. |
| 10 | **Context bloat budget** | MUST | Frontier prompt must stay < 2× initial. Accumulated edits that bloat context offset their own gains (Rethinking §5.1). |
| 11 | **Precondition: headroom + harness-sensitivity** | MUST | Loop skipped if agent accuracy ≥90% on dev (no headroom) or grid report shows <5pp config spread (harness-insensitive). Rethinking §5.2. |
| 12 | **Experience bank: failure-class aggregation, not task-id** | MUST | Only "generalizable" edits (per `_classify_edit`) enter the global pattern layer. Task-specific diagnoses stay in per-case only. Prevents memorize-fixes-not-strategies failure (Rethinking §5.1). |

---

## 8. File Changes

| File | Change |
|------|--------|
| `src/observeco/capability/harness.py` | Add `PhantomGuardrailGate`, `EpisodeLog`, `retrieve_similar()`; wire gate into `optimize()` before `_apply_edit`; add experience-bank write on each iteration |
| `src/observeco/capability/experience.py` | New — experience bank store + retrieval (exact match MVP; embedding upgrade path) |
| `src/observeco/cli_harness.py` | Add `experience`, `gate test` subcommands; `--with-experience`, `--no-phantom-gate` flags |
| `src/observeco/db.py` | Migration 64: `harness_experiences`, `harness_control_dims` tables |
| `src/observeco/dashboard/routes/harness_opt.py` | Experience bank stats view; phantom-rejection log |

---

## 9. ponytail Notes

- **Similarity retrieval ceiling:** MVP uses exact `failure_class` match — O(n) scan over `harness_experiences`. Fine up to ~10k rows. Upgrade path: embedding index (FAISS/sqlite-vss) when row count or cross-agent retrieval demands it.
- **Episode log freshness:** `EpisodeLog` is rebuilt from `canary_results` + `errors` on demand (not streamed). Stale if canary hasn't run recently — the cold-start phase handles this.
- **Apply-edit is the real blocker:** until §0's no-op is fixed, the entire experience bank is observation-only. This spec scopes the gate + bank; the apply-edit fix is a prerequisite tracked in obs-spec-056.
