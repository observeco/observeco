# obs-spec-056 — Automated Harness Optimization Loop

**Spec ID:** obs-spec-056
**Title:** Automated harness optimization loop — Meta-Harness inspired
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-050 (data model, dev/test split), obs-spec-051 (canary runner), obs-spec-054 (grid report, blended score)
**Master plan ref:** v0.6.0 "Automated Harness Optimization"
**Inspired by:** Niklaus, "Don't Train the Model, Evolve the Harness," Hugging Face, July 2026. [Source](https://huggingface.co/spaces/joelniklaus/harness-optimization) · [Code](https://github.com/JoelNiklaus/harness-optimization) · [Meta-Harness paper](https://arxiv.org/abs/2603.28052) · **v0.7.0 upgrade:** Huang et al., "MemoHarness: Agent Harnesses That Learn from Experience," arXiv 2607.14159, July 2026. [Paper](https://arxiv.org/abs/2607.14159)

---

## 1. What It Is

An automated loop that optimizes an agent's harness (the runtime wrapper — adapter code, task prompts, post-processing) by proposing changes, evaluating them on a held-out dev split, and promoting only candidates that beat the incumbent by a noise margin.

**Core thesis:** Harness quality is a separate axis from model capability. HF proved a frozen 0% model reaches 80.1% by optimizing only the harness. ObserveCo measures this; the optimization loop acts on it.

**What changes vs. what doesn't:**
- Model weights: frozen (never touched)
- Harness code (adapter, post-processing, retry logic): optimized
- Task prompts (system prompt additions, work-type playbooks): optimized
- Canary tasks: frozen (dev/test split prevents overfitting)

---

## 2. Architecture

```
CLI → HarnessOptimizer → Proposer (LLM) → reads canary_results.trajectory
                       → Lab (CanaryRunner) → runs candidate on dev split, 3 trials
                       → PromotionGate → blended score ≥ incumbent + 1pp?
                       → LeakageAudit → reject if test split touched
                       → Frontier → store promoted harness + mechanism log
```

### 2.1 HarnessOptimizer

```python
class HarnessOptimizer:
    def __init__(self, db, canary_runner, proposer_model="claude-opus-4.8"):
        self.db = db
        self.canary = canary_runner
        self.proposer = Proposer(model=proposer_model)
        self.gate = PromotionGate()
        self.audit = LeakageAudit()

    def optimize(self, agent_name, iterations=5, eval_split="dev"):
        for i in range(iterations):
            # 1. Proposer reads run history + trajectories
            candidate = self.proposer.propose(agent_name, self._get_history())
            # 2. Lab: run candidate on dev split, 3 trials
            report = self.canary.run(agent_name, split=eval_split, trials=3,
                                      config_label=candidate.name)
            # 3. Leakage audit: reject if test split was touched
            if not self.audit.check(candidate, report):
                logger.warning("Leakage detected — rejecting candidate")
                continue
            # 4. Promotion gate: blended score ≥ incumbent + min_delta?
            incumbent_score = self.gate.get_incumbent_score(agent_name)
            candidate_score = self.gate.score(report)
            if candidate_score >= incumbent_score + self.gate.min_delta:
                self.gate.promote(candidate, report, candidate_score)
                logger.info("Promoted: %s (score=%.4f, delta=%+.4f)",
                            candidate.name, candidate_score,
                            candidate_score - incumbent_score)
            else:
                logger.info("Rejected: %s (score=%.4f, delta=%+.4f)",
                            candidate.name, candidate_score,
                            candidate_score - incumbent_score)
```

### 2.2 Proposer

The proposer is an LLM (Claude Opus or local model) that:
1. Reads the last N canary run trajectories from `canary_results.trajectory` (JSON)
2. Reads the current frontier harness file (adapter code + prompts)
3. Researches failure patterns from trajectories
4. Writes ONE candidate harness that copies the current frontier and adds ONE mechanism
5. Returns a candidate descriptor: {name, mechanism_type, description, code_diff}

**Mechanism types** (from HF findings):
- `code` — deterministic post-processing, retry logic, validation gates
- `prompt` — system prompt additions, work-type playbooks
- `mixed` — code + prompt

**Key constraint:** Each candidate copies the current frontier and adapts it. Wins compound. This is not random search — it's hill climbing with inheritance.

### 2.3 PromotionGate

```python
class PromotionGate:
    def __init__(self, min_delta=0.01, allpass_weight=0.5, cost_lambda=0.005):
        self.min_delta = min_delta  # 1pp minimum improvement
        self.allpass_weight = allpass_weight
        self.cost_lambda = cost_lambda

    def score(self, report: CanaryReport) -> float:
        """Blended score: accuracy + 0.5 * all_pass_rate - 0.005 * tokens/1M"""
        all_pass_rate = report.pass_count / report.total_tasks if report.total_tasks > 0 else 0
        return (report.overall_accuracy
                + self.allpass_weight * all_pass_rate
                - self.cost_lambda * (report.total_tokens / 1_000_000))
```

**Why blended, not raw accuracy:** The HF paper found that all-pass rate (whole-task success) is noisy but valuable as a bonus, and that cost should penalize marginally better but much more expensive harnesses. The incumbent is rescored under current weights on every comparison — changing weights can't promote a worse harness.

### 2.4 LeakageAudit

```python
class LeakageAudit:
    def check(self, candidate, report) -> bool:
        """Reject if candidate touched the test split."""
        # Check if any test-split tasks appear in the run
        for task_id in [r["task_id"] for r in report.per_task]:
            task = self._get_task(task_id)
            if task and task.get("split") == "test":
                return False
        return True
```

**Why this matters:** Without a dev/test split, the loop optimizes against the evaluation set. The HF paper used 24 dev tasks for optimization and 100 test tasks as a held-out guard. A candidate that overfits dev will fail on test.

---

## 3. CLI Entry Point

```
observeco harness optimize [--agent AGENT] [--iterations N] [--proposer-model MODEL]
observeco harness history [--agent AGENT]
observeco harness frontier [--agent AGENT]
```

- `harness optimize` — runs the optimization loop
- `harness history` — shows all candidates with scores, promoted/rejected status
- `harness frontier` — shows the current best harness + mechanism stack

---

## 4. New DB Tables

### 4.1 `harness_candidates` — per-iteration candidates

```sql
CREATE TABLE IF NOT EXISTS harness_candidates (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    iteration   INTEGER NOT NULL,
    name        TEXT NOT NULL,         -- "deliverable_landing_gate"
    mechanism_type TEXT NOT NULL,      -- code | prompt | mixed
    description TEXT,
    code_diff   TEXT,                  -- diff of harness changes
    dev_score   REAL,                  -- blended score on dev split
    incumbent_score REAL,              -- score of incumbent at time of evaluation
    promoted    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_harness_candidates_agent ON harness_candidates(agent_name, iteration);
```

### 4.2 `harness_frontier` — current best harness per agent

```sql
CREATE TABLE IF NOT EXISTS harness_frontier (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL UNIQUE,
    candidate_id TEXT NOT NULL REFERENCES harness_candidates(id),
    score       REAL NOT NULL,
    mechanism_stack TEXT NOT NULL,     -- JSON array of mechanism names
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 5. Constraints Register

| # | Constraint | Type | Notes |
|---|-----------|------|-------|
| 1 | **Dev/test split required** | MUST | Without dev/test split (obs-spec-050), the loop overfits. Non-negotiable prerequisite. |
| 2 | **Blended score required** | MUST | Without blended score (obs-spec-054), the loop optimizes the wrong thing. |
| 3 | **Provider retry required** | MUST | Without provider retry in adapter, the loop chases provider noise instead of model/harness signal. |
| 4 | **LLM proposer costs tokens** | SHOULD | The proposer uses an LLM (Claude Opus or local). Budget-conscious users should be able to use a local model (ornith:latest) as proposer. |
| 5 | **Read-only tasks only (MVP)** | MUST | Same as canary runner constraint. Write operations detected and flagged. |
| 6 | **Leakage audit is non-negotiable** | MUST | Any candidate that touches test split is rejected. No exceptions. |
| 7 | **Copy-and-adapt, not from-scratch** | MUST | Each candidate copies the current frontier and adds one mechanism. Random search without inheritance doesn't compound. |

---

## 6. What the HF Paper Tells Us About Limits

| HF Finding | Implication for ObserveCo |
|------------|--------------------------|
| Dev size bounds what can be optimized | 9 built-in canary tasks may be too few. Consider expanding to 24+ for meaningful optimization. |
| Plateau is real (~83% pooled, top 6 in tight band) | The loop will converge. That's success, not failure. Surface the plateau to the user. |
| Prompt playbooks are model-specific | Promote code mechanisms first. Tag prompt mechanisms as model-specific in the frontier stack. |
| Compounding orphans matter | Some mechanisms score as noise solo but compound when stacked. Don't reject candidates that show 0pp delta but add infrastructure for future mechanisms. |
| Per-trial variance from blowups | 3 trials is the minimum. Blowup detection (already implemented) helps distinguish signal from noise. |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Loop completion | 95% of iterations complete without infra error | `harness_candidates` row count vs `--iterations` |
| Promotion rate | 20-40% of candidates promoted | `SUM(promoted) / COUNT(*)` in harness_candidates |
| Leakage detection | 100% of test-touching candidates rejected | Manual audit of rejected candidates |
| Frontier improvement | Measurable score gain over vanilla baseline | `harness_frontier.score` vs baseline canary run |
| Proposer cost | < $0.50 per iteration (BYOK) | Token usage from proposer LLM calls |

---

## 8. File Changes

| File | Change |
|------|--------|
| `src/observeco/capability/optimizer.py` | New — HarnessOptimizer, Proposer, PromotionGate, LeakageAudit |
| `src/observeco/cli.py` | Add `harness` command group |
| `src/observeco/db.py` | Add migration 52 (harness_candidates, harness_frontier tables) |
| `src/observeco/dashboard/server.py` | Add `/api/capability/harness/` routes |
| `src/observeco/dashboard/templates/index.html` | Add harness optimization section |

---

## 9. ponytail: The proposer LLM is the bottleneck. Using `hermes chat -q` as the proposer interface means each iteration spawns a subprocess. For 5 iterations that's fine. For long runs (50+ iterations), consider using the Hermes API directly or a local model (ornith:latest) as proposer to reduce latency and cost. Upgrade path: add `--proposer-model` flag that routes to different LLM providers.