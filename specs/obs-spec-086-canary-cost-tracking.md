# obs-spec-086 — Canary Cost & Token Tracking

**Spec ID:** obs-spec-086
**Title:** Real cost and token tracking for canary runs
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-051 (canary runner), obs-spec-057 (benchmark methodology)
**Master plan ref:** v0.6.0 "Agent Quality Management"
**Created:** 2026-07-19

---

## 1. Problem Statement

Every canary run in the DB shows **$0.0000 total_cost and 0 total_tokens** — all 37 runs for 'main', all 157 total runs. The `CanaryReport` dataclass has `total_cost` and `total_tokens` fields, and the canary runner accumulates them per-task (lines 1002-1005 of `canary.py`), but the Hermes adapter never returns them.

The Hermes CLI outputs token usage in stderr when run with `--verbose`:
```
Usage: CompletionUsage(completion_tokens=27, prompt_tokens=32403, total_tokens=32430, ...)
```

The adapter:
1. Runs in quiet mode (`-Q`) — suppresses verbose output
2. Never parses stderr for token/cost info
3. Returns a dict with only `output`, `model_used`, `harness_type`, `elapsed_seconds` — no `cost` or `tokens`

**Impact:** The dashboard shows $0 cost for all canary runs. The blended score in the harness optimizer (`cost_lambda * tokens/1M`) is always 0. Budget tracking (G1.1) has no data from canary runs.

**Not affected:** The harness proposer (which uses `llm_service` directly) already calls `log_self_monitor` for its own LLM calls. The async flush queue fix ensures those writes don't block. This spec only covers the canary subprocess path.

---

## 2. Design

### 2.1 Hermes Adapter: Parse Token Usage from Stderr

**File:** `src/observeco/benchmark/adapters/hermes.py`

**Change 1:** Add `--verbose` flag to the Hermes CLI command (line 127).

```python
# Current:
cmd += ["chat", "-q", prompt, "-Q"]

# New:
cmd += ["chat", "-q", prompt, "-Q", "--verbose"]
```

`-Q` suppresses the banner/spinner. `--verbose` enables token usage logging to stderr. These flags are compatible — `-Q` controls stdout, `--verbose` controls stderr.

**Change 2:** Parse stderr for token usage after the subprocess completes (after line 186, before the return).

```python
# Parse token usage from stderr
tokens = self._parse_token_usage(stderr)
cost = self._estimate_cost(tokens, model_used) if tokens else 0.0
```

**Change 3:** Add `_parse_token_usage` method.

```python
import re

_TOKEN_USAGE_RE = re.compile(
    r"Usage: CompletionUsage\(completion_tokens=(\d+), prompt_tokens=(\d+), total_tokens=(\d+)"
)

def _parse_token_usage(self, stderr: str) -> dict | None:
    """Extract token counts from Hermes verbose stderr output.

    Returns {prompt_tokens, completion_tokens, total_tokens} or None.
    """
    m = _TOKEN_USAGE_RE.search(stderr)
    if not m:
        return None
    return {
        "prompt_tokens": int(m.group(2)),
        "completion_tokens": int(m.group(1)),
        "total_tokens": int(m.group(3)),
    }
```

**Change 4:** Add `_estimate_cost` method.

```python
# Per-model pricing in $/1M tokens (input, output). Covers models used
# by the Hermes adapter chain. ponytail: static table — update when
# pricing changes or new models are added. Upgrade path: fetch from
# provider API or Hermes config.
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "deepseek-v4-flash": (0.15, 0.60),
    "deepseek-chat": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-3.5": (0.80, 4.00),
    "claude-opus-4": (15.00, 75.00),
}

def _estimate_cost(self, tokens: dict, model_used: str) -> float:
    """Estimate cost from token counts using a pricing table.

    Returns cost in USD. Returns 0.0 for unknown models.
    """
    pricing = _MODEL_PRICING.get(model_used)
    if not pricing:
        # Try fuzzy match: check if any known model is a substring
        for known, prices in _MODEL_PRICING.items():
            if known in model_used or model_used in known:
                pricing = prices
                break
    if not pricing:
        return 0.0
    input_price, output_price = pricing
    return (
        tokens["prompt_tokens"] * input_price / 1_000_000
        + tokens["completion_tokens"] * output_price / 1_000_000
    )
```

**Change 5:** Update the return dict to include `cost` and `tokens`.

```python
return {
    "output": output,
    "model_used": model_used,
    "harness_type": "hermes",
    "elapsed_seconds": elapsed,
    "provider_error": False,
    "cost": cost,
    "tokens": tokens["total_tokens"] if tokens else 0,
}
```

### 2.2 Canary Runner: Already Handles Cost/Tokens

The canary runner at `canary.py:1002-1005` already accumulates `result.cost` and `result.tokens`:

```python
if result.cost:
    task_costs.append(result.cost)
if result.tokens:
    task_tokens.append(result.tokens)
```

And stores them in `canary_results` (line 1028) and `canary_runs` (line 1089). No changes needed in the canary runner — it just needs the adapter to return non-zero values.

### 2.3 TaskResult Dataclass

The `TaskResult` dataclass (used by the canary runner's `TaskExecutor`) has `cost` and `tokens` fields. The Hermes adapter returns a dict, which is converted to `TaskResult` in `TaskExecutor.execute()`. Let me verify this conversion path.

**File:** `src/observeco/capability/canary.py` — `TaskExecutor.execute()` (line 638)

The adapter returns a dict. The executor converts it to `TaskResult`. If the dict has `cost` and `tokens` keys, they'll be passed through. If not, they default to 0.0/0. **No change needed** — adding `cost` and `tokens` to the adapter's return dict is sufficient.

### 2.4 Self-Monitoring Integration

The canary runner does NOT call `log_self_monitor` for each task — it uses the Hermes CLI subprocess, not the `llm_service`. The cost/token data flows through `canary_results` and `canary_runs` tables, not `self_monitor_budget`. This is correct: canary runs are benchmark evaluations, not self-monitoring calls. The dashboard reads cost from `canary_runs.total_cost`.

**No change needed** to the self-monitoring system for canary cost tracking.

---

## 3. Migration

No schema changes needed. All required columns (`total_cost`, `total_tokens` in `canary_runs`; `cost`, `tokens` in `canary_results`) already exist from obs-spec-050.

---

## 4. CLI

No CLI changes. The `observeco canary run` command already displays cost/tokens in its output (it reads from `CanaryReport`). The fix is purely in the adapter — once the adapter returns real values, the CLI and dashboard will show them.

---

## 5. Verification

1. Run `observeco canary run --agent default --tasks 1` (single task, fast)
2. Check output shows non-zero cost and tokens
3. Check `canary_runs.total_cost > 0` in DB
4. Check `canary_results.cost > 0` in DB
5. Check dashboard shows non-zero cost for the run

---

## 6. Constraints

| # | Constraint | Type | Description |
|---|------------|------|-------------|
| 1 | Pricing table staleness | MUST | Update `_MODEL_PRICING` when provider pricing changes. Add a `ponytail:` comment noting the upgrade path (fetch from provider API). |
| 2 | Unknown models | MUST | Return 0.0 cost for unknown models — don't crash. Log a warning. |
| 3 | Stderr parsing fragility | MUST | The `CompletionUsage(...)` format is Hermes-internal. If the format changes, parsing fails silently (returns None, cost=0). Add a `ponytail:` comment. |
| 4 | Verbose stderr size | SHOULD | `--verbose` adds ~20 lines of log output per call. For 10 tasks × 10 trials = 100 calls, that's ~2000 lines of stderr. Negligible. |
| 5 | Cost estimation accuracy | SHOULD | Pricing table is approximate. Actual cost depends on provider, caching, and billing tier. Document as "estimated cost" in the dashboard. |

---

## 7. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Hermes CLI `--verbose` format changes | Low | Parsing fails silently → cost=0 (same as current behavior). Add a `ponytail:` comment with the upgrade path. |
| Pricing table out of date | Low | Cost estimates drift from actual. Document as "estimated" in the dashboard. Add a note to update pricing quarterly. |
| `--verbose` + `-Q` conflict | Low | Tested: `-Q` suppresses stdout banner, `--verbose` enables stderr logging. They're compatible. |

---

## 8. File Changes

| File | Change | Type |
|------|--------|------|
| `src/observeco/benchmark/adapters/hermes.py` | Add `--verbose` flag to CLI command | Modify |
| `src/observeco/benchmark/adapters/hermes.py` | Add `_parse_token_usage()` method | New |
| `src/observeco/benchmark/adapters/hermes.py` | Add `_estimate_cost()` method + `_MODEL_PRICING` table | New |
| `src/observeco/benchmark/adapters/hermes.py` | Add `cost` and `tokens` to return dict | Modify |
| `specs/obs-spec-086-canary-cost-tracking.md` | This spec | New |
| `specs/observeco-master-plan.md` | Add row for obs-spec-086 | Modify |
