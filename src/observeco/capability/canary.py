"""Canary runner — task execution, scoring, and run management.

obs-spec-051: Canary runner for capability monitoring.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)


# ── Data types ───────────────────────────────────────────────────────────────

@dataclass
class TaskResult:
    """Result of one task execution (one trial)."""
    output: str = ""
    latency_ms: float = 0.0
    model_used: str = ""
    harness_type: str = "hermes"
    tokens: int = 0
    cost: float = 0.0
    hang: bool = False
    error: str = ""
    passed: bool = False
    accuracy: float = 0.0
    provider_error: bool = False  # True if failure was provider-side (5xx/429), not model


@dataclass
class CanaryReport:
    """Aggregate canary run report."""
    run_id: str = ""
    agent_name: str = ""
    config_hash: str = ""
    total_tasks: int = 0
    pass_count: int = 0
    hang_count: int = 0
    fail_count: int = 0
    overall_accuracy: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0
    per_task: list[dict] = field(default_factory=list)
    drift: Optional[dict] = None  # set by BaselineManager.compare()


# ── Algorithmic token extraction for llm_judge fallback ──────────────────────
# When the LLM judge is unavailable (no API key), the fallback extracts
# algorithmic structure from the expected output instead of raw keywords.
# This avoids overfitting to exact naming — the model writing `evendescending`
# should still match if the expected says `get_even_descending`, as long as
# the algorithmic tokens (sorted, %, reverse, etc.) are present.

# Python builtins and operators that signal algorithmic intent
_ALGO_BUILTINS = frozenset({
    "sorted", "return", "def", "len", "range", "list", "dict", "set",
    "map", "filter", "zip", "sum", "min", "max", "abs", "all", "any",
    "int", "float", "str", "bool", "tuple", "lambda", "yield",
    "if", "elif", "else", "while", "for", "in", "not", "and", "or",
    "break", "continue", "pass", "raise", "try", "except", "finally",
    "with", "as", "import", "from", "class", "is", "none", "true", "false",
})

# Common method names and structural tokens
_ALGO_METHODS = frozenset({
    "reverse", "sort", "append", "pop", "insert", "remove", "index",
    "count", "extend", "clear", "copy", "keys", "values", "items",
    "get", "update", "split", "join", "strip", "replace", "startswith",
    "endswith", "lower", "upper", "format",
})

# Operators as searchable tokens
_ALGO_OPERATORS = frozenset({
    "%", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "//", "**",
})

# Algorithmic concept tokens (domain-agnostic)
_ALGO_CONCEPTS = frozenset({
    "even", "odd", "descending", "ascending", "reverse=true",
    "reverse=false", "sorted(", "lambda ", "list comprehension",
})


def _extract_algorithmic_tokens(expected: str) -> list[str]:
    """Extract algorithmic structure tokens from expected output.

    Returns tokens that represent the *logic* of the solution, not the
    specific variable/function names. This makes the llm_judge fallback
    robust to naming variations (e.g. `evendescending` vs `get_even_descending`).

    ponytail: token-based, not AST-based. Won't catch semantic equivalence
    (e.g. `filter` vs list comprehension). Upgrade path: use Python's ast
    module to compare AST structure, ignoring identifier names.
    """
    tokens: list[str] = []
    lower = expected.lower()

    # Builtins and keywords
    for tok in _ALGO_BUILTINS:
        if re.search(r'\b' + re.escape(tok) + r'\b', lower):
            tokens.append(tok)

    # Method names
    for tok in _ALGO_METHODS:
        if re.search(r'\b' + re.escape(tok) + r'\b', lower):
            tokens.append(tok)

    # Operators (literal substring match)
    for tok in _ALGO_OPERATORS:
        if tok in expected:
            tokens.append(tok)

    # Concept tokens
    for tok in _ALGO_CONCEPTS:
        if tok in lower:
            tokens.append(tok)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


class Scorer:
    """Score task outputs against assertions.

    Args:
        assertions: List of assertion dicts (from canary_tasks.assertions JSON).
        output: The raw agent output text.
        task_id: Optional task ID for judge cache lookups.

    Returns:
        (passed, accuracy, reasoning) — accuracy is 0.0 or 1.0 for binary assertions.
    """

    # Common English stopwords excluded from the llm_judge→contains fallback
    # so we don't reward matching "the/and/for" noise when the LLM is offline.
    _STOPWORDS = frozenset({
        "the", "and", "for", "with", "that", "this", "from", "your", "are",
        "was", "were", "have", "has", "will", "should", "would", "could",
        "their", "there", "what", "when", "where", "which", "while", "about",
        "into", "than", "then", "they", "them", "but", "not", "all", "any",
    })

    @staticmethod
    def score(assertions: list[dict], output: str, task_id: str = "") -> tuple[bool, float, str]:
        """Score output against assertions.

        Args:
            assertions: List of assertion dicts (from canary_tasks.assertions JSON).
            output: The raw agent output text.
            task_id: Optional task ID for judge cache lookups.

        Returns:
            (passed, accuracy, reasoning) — accuracy is 0.0 or 1.0 for binary assertions.
        """
        if not assertions:
            return (False, 0.0, "No assertions defined")

        # Assertion type weights for weighted scoring
        _WEIGHTS = {
            "exact_match": 1.0,
            "llm_judge": 1.0,
            "json_schema": 1.0,
            "tool_call_validation": 1.0,
            "ordering": 0.7,
            "numeric_range": 0.6,
            "regex": 0.5,
            "contains": 0.4,
        }

        results = []
        for assertion in assertions:
            a_type = assertion.get("type", "")
            try:
                if a_type == "exact_match":
                    p, acc, reason = Scorer._exact_match(assertion, output)
                elif a_type == "contains":
                    p, acc, reason = Scorer._contains(assertion, output)
                elif a_type == "numeric_range":
                    p, acc, reason = Scorer._numeric_range(assertion, output)
                elif a_type == "regex":
                    p, acc, reason = Scorer._regex(assertion, output)
                elif a_type == "llm_judge":
                    p, acc, reason = Scorer._llm_judge(assertion, output, task_id=task_id)
                elif a_type == "json_schema":
                    p, acc, reason = Scorer._json_schema(assertion, output)
                elif a_type == "ordering":
                    p, acc, reason = Scorer._ordering(assertion, output)
                elif a_type == "tool_call_validation":
                    p, acc, reason = Scorer._tool_call_validation(assertion, output)
                else:
                    p, acc, reason = (False, 0.0, f"Unknown assertion type: {a_type}")
            except Exception as exc:
                p, acc, reason = (False, 0.0, f"Assertion error: {exc}")
            results.append((p, acc, reason, a_type))

        # Weighted scoring per spec obs-spec-057 §2.2
        weight_sum = sum(_WEIGHTS.get(r[3], 0.5) for r in results) if results else 1.0
        weighted_acc = sum(r[1] * _WEIGHTS.get(r[3], 0.5) for r in results) / weight_sum if results else 0.0
        all_pass = all(r[0] for r in results)
        reasoning = "; ".join(r[2] for r in results)

        return (all_pass, weighted_acc, reasoning)

    @staticmethod
    def _exact_match(assertion: dict, output: str) -> tuple[bool, float, str]:
        target = assertion.get("target", "")
        passed = output.strip() == target.strip()
        return (passed, 1.0 if passed else 0.0,
                f"exact_match: {'PASS' if passed else 'FAIL'}")

    @staticmethod
    def _contains(assertion: dict, output: str) -> tuple[bool, float, str]:
        keywords = assertion.get("keywords", [])
        if not keywords:
            return (False, 0.0, "contains: no keywords specified")
        matches = [kw for kw in keywords if kw.lower() in output.lower()]
        min_match = assertion.get("min_match", len(keywords))
        passed = len(matches) >= min_match
        acc = len(matches) / len(keywords) if keywords else 0.0
        return (passed, acc,
                f"contains: {len(matches)}/{len(keywords)} keywords matched (need {min_match})"
                + ("" if passed else f" (missing: {[kw for kw in keywords if kw.lower() not in output.lower()]})"))

    @staticmethod
    def _numeric_range(assertion: dict, output: str) -> tuple[bool, float, str]:
        """Extract a number from output and check if within [min, max]."""
        # Extract first number from output
        numbers = re.findall(r'[-+]?\d*\.?\d+', output)
        if not numbers:
            return (False, 0.0, "numeric_range: no number found in output")

        val = float(numbers[0])
        lo = assertion.get("min", float("-inf"))
        hi = assertion.get("max", float("inf"))
        tolerance = assertion.get("tolerance", 0)

        in_range = (lo - tolerance) <= val <= (hi + tolerance)
        return (in_range, 1.0 if in_range else 0.0,
                f"numeric_range: {val} {'in' if in_range else 'outside'} [{lo}, {hi}]")

    @staticmethod
    def _regex(assertion: dict, output: str) -> tuple[bool, float, str]:
        pattern = assertion.get("pattern", "")
        if not pattern:
            return (False, 0.0, "regex: no pattern specified")
        try:
            match = re.search(pattern, output, re.DOTALL)
            passed = match is not None
            return (passed, 1.0 if passed else 0.0,
                    f"regex: {'matched' if passed else 'no match'} pattern '{pattern[:50]}'")
        except re.error as exc:
            return (False, 0.0, f"regex: invalid pattern: {exc}")

    # ── LLM-as-a-Verifier scoring (Tier 1+2) ──────────────────────────────
    # Implements expected-score-over-logprobs from Kwok et al. 2026 (arXiv:2607.05391).
    # Tier 1: 1-20 scale prompt + K=3 repetition (works on any provider).
    # Tier 2: logprob-based expected score (requires OpenAI-compatible logprobs API).
    # Falls back to discrete score parsing if logprobs unavailable.

    _SCORE_MIN = 1
    _SCORE_MAX = 20
    _DEFAULT_K = 3  # repetitions — paper shows K=3 captures most of the gain

    @staticmethod
    def _token_to_score(token: str) -> float | None:
        """Map a score token (e.g. "8", "12") to a numeric score.

        Returns None if the token isn't a valid score in [_SCORE_MIN, _SCORE_MAX].
        """
        token = token.strip()
        # Handle common non-numeric tokens the model might generate
        try:
            val = float(token)
        except ValueError:
            return None
        if val < Scorer._SCORE_MIN or val > Scorer._SCORE_MAX:
            return None
        return val

    @staticmethod
    def _expected_score_from_logprobs(logprobs: list[dict]) -> float | None:
        """Compute expected score from logprob distribution at the score token position.

        Implements Eq. 3.1 from the paper: R = sum_g p(v_g) * phi(v_g)
        where p(v_g) is the probability of score token v_g and phi maps to score value.

        Scans logprobs for the first position where top_logprobs contains valid score tokens.
        """
        import math
        for pos in logprobs:
            top_lps = pos.get("top_logprobs") or []
            if not top_lps:
                continue
            # Collect all valid score tokens at this position
            score_probs: list[tuple[float, float]] = []
            for lp in top_lps:
                score = Scorer._token_to_score(lp["token"])
                if score is not None:
                    prob = math.exp(lp["logprob"])
                    score_probs.append((score, prob))
            if not score_probs:
                continue
            # Normalize probabilities (they may not sum to 1 due to non-score tokens)
            total_prob = sum(p for _, p in score_probs)
            if total_prob <= 0:
                continue
            # Expected score = sum(score * normalized_prob)
            expected = sum(s * (p / total_prob) for s, p in score_probs)
            # Normalize to 0-1 range
            return (expected - Scorer._SCORE_MIN) / (Scorer._SCORE_MAX - Scorer._SCORE_MIN)
        return None

    @staticmethod
    def _byok_judge_chain(system_prompt: str, user_context: str, byok_key: str) -> float | None:
        """Call the LLM judge through a chain of providers until one scores.

        Generic: reads providers from ~/.hermes/config.yaml. ollama-cloud is
        tried first (glm-5.2 is the most reliable scorer there), then every
        other configured provider with an API key. Returns the parsed 1-20
        score from the first provider that answers, or None if all fail
        (rate-limited, empty, or unparseable).

        This makes the judge resilient to a single provider's rate limit —
        a 429 on ollama.com must not zero out every llm_judge task.
        """
        import json as _json
        import urllib.request as _ureq
        from pathlib import Path as _Path

        # Build provider list: cloud providers with base_url + api key that are
        # reachable (skip localhost proxies — they route through the broken
        # 9router). ollama-cloud is preferred first (glm-5.2 is the most
        # reliable scorer there), then any other cloud provider.
        providers: list[dict] = []
        try:
            import yaml as _yaml
            cfg_path = _Path.home() / ".hermes" / "config.yaml"
            if cfg_path.exists():
                cfg = _yaml.safe_load(cfg_path.read_text()) or {}
                p_cfg = cfg.get("providers", {})
                names = sorted(p_cfg.keys(), key=lambda n: (n != "ollama-cloud", n))
                for name in names:
                    p = p_cfg.get(name) or {}
                    base = p.get("base_url", "") or p.get("api", "")
                    key = p.get("api_key", "") or ""
                    if not base or not key:
                        continue
                    # Skip localhost / dead-gateway endpoints — they can't
                    # reach a real judge model.
                    if "localhost" in base or "127.0.0.1" in base or "11434" in base:
                        continue
                    # Prefer a default model; otherwise any chat-eligible model.
                    model = p.get("default_model", "") or next(iter(p.get("models", {})), "")
                    if not model:
                        # Provider with a key but no model list — use a known
                        # sensible chat model for the provider (deepseek's API
                        # serves deepseek-v4-flash; xiaomi serves mimo-v2.5).
                        model = {"deepseek": "deepseek-v4-flash",
                                 "xiaomi": "mimo-v2.5",
                                 "token-plan": "mimo-v2.5",
                                 "ollama-cloud": "deepseek-v4-flash"}.get(name, "")
                    if not model:
                        continue
                    providers.append({"name": name, "base": base.rstrip("/"), "key": key, "model": model})
        except Exception:
            pass

        # Always include the BYOK key on ollama.com as a last-resort endpoint
        # with the most reliable scorer (glm-5.2).
        providers.append({
            "name": "ollama-cloud",
            "base": "https://ollama.com/v1",
            "key": byok_key,
            "model": "glm-5.2",
        })

        # Prefer deepseek as an early fallback — it has a healthy independent
        # key and reliably returns <score>N</score>. Move it right after
        # ollama-cloud in priority.
        providers.sort(key=lambda pr: (pr["name"] != "ollama-cloud", pr["name"] != "deepseek"))

        for prov in providers:
            try:
                _payload = _json.dumps({
                    "model": prov["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_context},
                    ],
                    "temperature": 0,
                    "max_tokens": 200,
                    "stream": False,
                }).encode()
                _req = _ureq.Request(
                    f"{prov['base']}/chat/completions",
                    data=_payload,
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {prov['key']}"},
                )
                for _attempt in range(2):
                    try:
                        with _ureq.urlopen(_req, timeout=90) as _r:
                            _body = _json.loads(_r.read().decode())
                        _text = (_body["choices"][0]["message"]["content"] or "").strip()
                        if _text:
                            score = Scorer._parse_discrete_score(_text)
                            if score is not None:
                                return score
                        break  # answered but unparseable — try next provider
                    except Exception as _e:
                        if _attempt == 0:
                            continue  # one retry per provider
                        break
            except Exception:
                continue
        return None

    @staticmethod
    def _parse_discrete_score(text: str) -> float | None:
        """Extract a 1-20 score from model text output (fallback when no logprobs).

        Looks for <score> tags first, then falls back to last integer in text.
        Returns normalized 0-1 score or None.
        """
        # Try <score>N</score> tags
        m = re.search(r"<score>\s*(\d+)\s*</score>", text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if Scorer._SCORE_MIN <= val <= Scorer._SCORE_MAX:
                return (val - Scorer._SCORE_MIN) / (Scorer._SCORE_MAX - Scorer._SCORE_MIN)
        # Try "Score: N" pattern
        m = re.search(r"[Ss]core\s*[:=]\s*(\d+)", text)
        if m:
            val = int(m.group(1))
            if Scorer._SCORE_MIN <= val <= Scorer._SCORE_MAX:
                return (val - Scorer._SCORE_MIN) / (Scorer._SCORE_MAX - Scorer._SCORE_MIN)
        # Try last standalone integer 1-20 in text
        nums = re.findall(r"\b(\d{1,2})\b", text)
        for n in reversed(nums):
            val = int(n)
            if Scorer._SCORE_MIN <= val <= Scorer._SCORE_MAX:
                return (val - Scorer._SCORE_MIN) / (Scorer._SCORE_MAX - Scorer._SCORE_MIN)
        return None

    @staticmethod
    def _llm_judge(assertion: dict, output: str, task_id: str = "") -> tuple[bool, float, str]:
        """LLM-as-a-Verifier assertion — evaluates output quality against criteria.

        Uses fine-grained 1-20 scoring with K=3 repeated evaluation.
        If the provider supports logprobs, computes expected score from the
        logprob distribution (Tier 2). Otherwise falls back to discrete score
        parsing (Tier 1).

        Based on: Kwok et al. "LLM-as-a-Verifier" (arXiv:2607.05391, 2026).

        ponytail: Cache key uses (task_id, output_hash, criteria_hash) — different
        criteria on the same task+output get separate cache entries.
        """
        criteria = assertion.get("criteria", "")
        expected = assertion.get("expected", "")
        threshold = assertion.get("threshold", 0.5)
        k = int(assertion.get("repetitions", Scorer._DEFAULT_K))

        # ── Cache check ──────────────────────────────────────────────────
        cache_key = ""
        output_hash = ""
        cache_conn = None
        if task_id:
            output_hash = hashlib.sha256(output.encode()).hexdigest()
            criteria_hash = hashlib.sha256(criteria.encode()).hexdigest()
            cache_key = hashlib.sha256(f"{task_id}{output_hash}{criteria_hash}".encode()).hexdigest()
            try:
                from observeco.db import Database
                cache_conn = Database()._get_conn()
                cached = cache_conn.execute(
                    "SELECT score, created_at FROM canary_judge_cache WHERE cache_key = ?",
                    (cache_key,),
                ).fetchone()
                if cached and cached["created_at"]:
                    cached_dt = datetime.fromisoformat(cached["created_at"])
                    if (datetime.now(timezone.utc) - cached_dt).days < 7:
                        cached_score = cached["score"]
                        return (cached_score >= threshold, cached_score,
                                f"llm_judge: cached K=1 avg={cached_score:.3f}")
            except Exception:
                pass  # cache miss or DB error — proceed with LLM call

        system_prompt = (
            "You are an expert evaluator. Score the agent's response against the criteria. "
            f"Rate on a {Scorer._SCORE_MIN}-{Scorer._SCORE_MAX} scale "
            f"({Scorer._SCORE_MIN} = completely wrong, {Scorer._SCORE_MAX} = perfect). "
            f"Respond with ONLY: <score>N</score> where N is an integer {Scorer._SCORE_MIN}-{Scorer._SCORE_MAX}."
        )
        user_context = (
            f"Criteria: {criteria}\n"
            f"Expected: {expected}\n"
            f"Agent output: {output[:2000]}\n\n"
            f"Score (1-20):"
        )

        scores: list[float] = []
        used_logprobs = False
        used_discrete = False
        errors: list[str] = []

        try:
            from observeco.llm_service import ask_with_logprobs
        except ImportError:
            ask_with_logprobs = None  # type: ignore[assignment]

        # BYOK fast-path: when the user supplies their own key, judge directly
        # (ungated). The product LLM gate (tier-2 requires Pro) must NOT block
        # first-party canary scoring funded by the user's own key. Falls back to
        # the gated path below for environments without a BYOK key.
        # ponytail: uses deepseek-v4-flash on ollama.com/v1 which ignores
        # temperature and can return empty content on malformed prompts — callers
        # must send a well-formed "Score 1-20" prompt (system_prompt already does).
        # No logprobs from this path; discrete-score parsing handles the result.
        byok_key = os.environ.get("OBSERVECO_LLM_API_KEY", "")

        for i in range(k):
            if byok_key:
                # BYOK fast-path with a provider CHAIN — the judge must not
                # depend on a single endpoint. ollama.com (glm-5.2) is primary
                # but gets rate-limited (429) under load; fail over to any
                # other configured provider that answers <score>N</score>.
                # Generic: reads providers from hermes config, no hardcoded
                # per-provider special cases.
                score = Scorer._byok_judge_chain(system_prompt, user_context, byok_key)
                if score is not None:
                    scores.append(score)
                    used_discrete = True
                    continue
                errors.append("byok judge chain failed on all providers")
            elif ask_with_logprobs is not None:
                resp = ask_with_logprobs(
                    system_prompt, user_context,
                    consumer="canary_judge", tier=2,
                    top_logprobs=Scorer._SCORE_MAX,
                )
                if resp is None:
                    errors.append("call {} returned None".format(i))
                    continue

                # Tier 2: try logprob-based expected score
                if resp.logprobs:
                    score = Scorer._expected_score_from_logprobs(resp.logprobs)
                    if score is not None:
                        scores.append(score)
                        used_logprobs = True
                        continue

                # Tier 1 fallback: parse discrete score from text
                score = Scorer._parse_discrete_score(resp.text)
                if score is not None:
                    scores.append(score)
                    used_discrete = True
                    continue

                errors.append("could not parse score from response")
            else:
                # No logprobs support at all — use plain ask()
                from observeco.llm_service import ask
                text = ask(system_prompt, user_context, consumer="canary_judge", tier=2)
                if text is None:
                    errors.append("call {} returned None".format(i))
                    continue
                score = Scorer._parse_discrete_score(text)
                if score is not None:
                    scores.append(score)
                    used_discrete = True
                    continue
                errors.append("could not parse score from response")

        if not scores:
            # ── Fallback when no LLM provider is configured ──────────────────
            # If every K attempt returned None (no API key / provider), degrade
            # gracefully to a contains-check on the expected output's salient
            # keywords instead of failing the task outright. ponytail: this is a
            # weak proxy (keyword overlap, not quality) — it only fires when the
            # LLM judge is unavailable, so canary runs still complete offline.
            if any("returned None" in e for e in errors):
                exp = (expected or "").strip()
                if exp:
                    # Extract algorithmic patterns from expected, not raw keywords.
                    # Raw keyword matching overfits to exact naming (e.g. the model
                    # writes `evendescending` but expected says `get_even_descending`).
                    # Instead, extract the algorithmic structure: operators, control
                    # flow, builtins, and structural tokens that represent the actual
                    # logic — not the variable/function names.
                    algo_tokens = _extract_algorithmic_tokens(exp)
                    if algo_tokens:
                        output_lower = output.lower()
                        matched = [t for t in algo_tokens if t in output_lower]
                        acc = len(matched) / len(algo_tokens)
                        return (acc >= threshold, acc,
                                f"llm_judge: LLM unavailable, fell back to algorithmic "
                                f"pattern match ({len(matched)}/{len(algo_tokens)} tokens)")
                return (False, 0.0, "llm_judge: LLM unavailable and no expected output for fallback")
            return (False, 0.0, f"llm_judge: no valid scores ({'; '.join(errors)})")

        avg_score = sum(scores) / len(scores)
        passed = avg_score >= threshold
        method = "logprobs" if used_logprobs else ("discrete" if used_discrete else "mixed")
        reasoning = f"llm_judge: {method} K={len(scores)}/{k} avg={avg_score:.3f}"

        # ── Cache write ─────────────────────────────────────────────────
        if task_id and cache_key and cache_conn:
            try:
                cache_conn.execute(
                    "INSERT OR REPLACE INTO canary_judge_cache "
                    "(cache_key, task_id, output_hash, score, reasoning, model_used, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (cache_key, task_id, output_hash, avg_score, reasoning,
                     "", datetime.now(timezone.utc).isoformat()),
                )
                cache_conn.commit()
            except Exception:
                pass  # best-effort cache write

        return (passed, avg_score, reasoning)

    @staticmethod
    def _json_schema(assertion: dict, output: str) -> tuple[bool, float, str]:
        """Validate output parses as JSON and matches JSON Schema."""
        schema = assertion.get("schema", {})
        try:
            import json
            data = json.loads(output)
            try:
                import jsonschema
                jsonschema.validate(data, schema)
                return (True, 1.0, "json_schema: valid")
            except ImportError:
                return (True, 1.0, "json_schema: valid (schema check skipped - jsonschema not installed)")
            except Exception as exc:
                return (False, 0.0, f"json_schema: {exc}")
        except json.JSONDecodeError:
            return (False, 0.0, "json_schema: invalid JSON")

    @staticmethod
    def _ordering(assertion: dict, output: str) -> tuple[bool, float, str]:
        """Check if steps appear in the specified order in output."""
        steps = assertion.get("steps", [])
        if not steps:
            return (False, 0.0, "ordering: no steps specified")
        output_lower = output.lower()
        positions = []
        for step in steps:
            pos = output_lower.find(step.lower())
            if pos == -1:
                return (False, 0.0, f"ordering: step '{step[:30]}' not found")
            positions.append(pos)
        for i in range(len(positions) - 1):
            if positions[i] >= positions[i + 1]:
                return (False, 0.0, "ordering: steps out of order")
        return (True, 1.0, "ordering: all steps in correct order")

    @staticmethod
    def _tool_call_validation(assertion: dict, output: str) -> tuple[bool, float, str]:
        """Verify the agent called the right tool with correct arguments.

        Checks if output contains the expected tool name and optionally
        verifies expected argument key-value pairs appear in the output.

        Assertion fields:
            expected_tool (str, required): The tool name that should appear.
            expected_args (dict, optional): Key-value pairs that should appear
                in the output near the tool call.

        Returns:
            (passed, accuracy, reasoning)
        """
        expected_tool = assertion.get("expected_tool", "")
        if not expected_tool:
            return (False, 0.0, "tool_call_validation: no expected_tool specified")

        output_lower = output.lower()
        tool_lower = expected_tool.lower()

        # Check tool name appears in output
        if tool_lower not in output_lower:
            return (False, 0.0, f"tool_call_validation: tool '{expected_tool}' not found in output")

        # Check expected arguments if specified
        expected_args = assertion.get("expected_args", {})
        if expected_args:
            args_found = 0
            args_total = len(expected_args)
            for key, value in expected_args.items():
                key_lower = key.lower()
                value_lower = str(value).lower()
                # Check both "key: value" and "key=value" patterns
                if f"{key_lower}: {value_lower}" in output_lower or f"{key_lower}={value_lower}" in output_lower:
                    args_found += 1
            if args_found < args_total:
                return (False, float(args_found) / args_total,
                        f"tool_call_validation: tool '{expected_tool}' found, "
                        f"but only {args_found}/{args_total} expected args matched")
            return (True, 1.0, f"tool_call_validation: tool '{expected_tool}' with all {args_total} expected args")

        return (True, 1.0, f"tool_call_validation: tool '{expected_tool}' found")

    @staticmethod
    def bootstrap_ci(values: list[float], n_bootstrap: int = 1000, ci: float = 0.95) -> tuple[float, float]:
        """Compute bootstrap confidence interval for a list of accuracy values.

        Args:
            values: List of accuracy scores (0.0-1.0).
            n_bootstrap: Number of bootstrap iterations.
            ci: Confidence level (default 0.95).

        Returns:
            (lower_bound, upper_bound) or (0.0, 0.0) if insufficient data (n < 5).
        """
        if len(values) < 5:
            return (0.0, 0.0)

        alpha = (1 - ci) / 2
        means = []
        n = len(values)

        for _ in range(n_bootstrap):
            sample = [random.choice(values) for _ in range(n)]
            means.append(sum(sample) / n)

        means.sort()
        lower_idx = int(alpha * n_bootstrap)
        upper_idx = int((1 - alpha) * n_bootstrap) - 1

        return (round(means[lower_idx], 4), round(means[upper_idx], 4))


# ── TaskExecutor ─────────────────────────────────────────────────────────────

class TaskExecutor:
    """Execute one canary task against an agent adapter."""

    def __init__(self, adapter=None):
        """Args:
            adapter: An object with run_task(agent_name, task) that returns
                     {output, model_used, harness_type, tokens?, cost?, timed_out?, error?}.
        """
        self.adapter = adapter

    def execute(self, task: dict, agent_name: str, timeout: int = 300) -> TaskResult:
        """Run one task once through the adapter.

        Args:
            task: Task dict (from canary_tasks table).
            agent_name: Hermes agent profile name.
            timeout: Per-task timeout in seconds (matches HermesBenchmarkAdapter default).

        Returns:
            TaskResult with output, latency, hang, error info.
        """
        start = time.monotonic()

        if self.adapter is None:
            return TaskResult(
                output="",
                latency_ms=0,
                error="No adapter configured",
                hang=False,
            )

        try:
            # Build a BenchmarkTask-like object for the adapter
            task_obj = type("Task", (), {
                "id": task.get("id", ""),
                "task_name": task.get("name", task.get("id", "unknown")),
                "agent_name": agent_name,
                "input_text": task.get("prompt", ""),
                "context_text": "",
                "expected_output": "",
                "temperature": task.get("temperature", 0.0),
                "model": task.get("model", "") or "",
            })()

            result = self.adapter.run_task(agent_name, task_obj)
            elapsed = time.monotonic() - start

            return TaskResult(
                output=result.get("output", ""),
                latency_ms=elapsed * 1000,
                model_used=result.get("model_used", ""),
                harness_type=result.get("harness_type", "hermes"),
                tokens=result.get("tokens", 0),
                cost=result.get("cost", 0.0),
                hang=result.get("timed_out", False),
                error=result.get("error", ""),
                provider_error=result.get("provider_error", False),
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return TaskResult(
                output="",
                latency_ms=elapsed * 1000,
                error=str(exc),
                hang=True,
            )


# ── CanaryRunner ─────────────────────────────────────────────────────────────

class CanaryRunner:
    """Run the canary suite: tasks × trials, score, store, compare baseline."""

    def __init__(self, db: Optional[Database] = None, adapter=None):
        self.db = db or Database()
        self.scorer = Scorer()
        if adapter is None:
            from observeco.benchmark.adapters.hermes import HermesBenchmarkAdapter
            adapter = HermesBenchmarkAdapter()
        self.executor = TaskExecutor(adapter=adapter)

    # ── Task CRUD ──────────────────────────────────────────────────────────

    def list_tasks(self) -> list[dict]:
        """List all canary tasks."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT id, name, description, assertions, timeout, model, trials, "
            "category, difficulty, built_in, created_at FROM canary_tasks ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def _check_blanks(self, prompt: str) -> list[str]:
        """Scan prompt for unresolved template variables like {{ variable }}."""
        import re
        return re.findall(r'\{\{\s*\w+\s*\}\}', prompt)

    def create_task(self, task_data: dict) -> dict:
        """Create a new canary task from a dict.

        Args:
            task_data: {id, name, description?, prompt, assertions, timeout?, model?, trials?}

        Returns:
            {ok, task_id?, error?}
        """
        prompt = task_data.get("prompt", "")
        blanks = self._check_blanks(prompt)
        if blanks:
            return {
                "ok": False,
                "error": f"Prompt has unresolved templates: {', '.join(blanks)}. Replace them with actual test data or provide sample values."
            }

        conn = self.db._get_conn()
        task_id = task_data.get("id", task_data.get("name", "").lower().replace(" ", "-"))

        try:
            conn.execute(
                "INSERT INTO canary_tasks (id, name, description, prompt, assertions, "
                "timeout, model, trials, category, difficulty, temperature, built_in) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    task_data.get("name", task_id),
                    task_data.get("description", ""),
                    task_data["prompt"],
                    json.dumps(task_data.get("assertions", [])),
                    task_data.get("timeout", 60),
                    task_data.get("model", None),
                    task_data.get("trials", 10),  # default increased from 3 to 10 per obs-spec-057
                    task_data.get("category", None),
                    task_data.get("difficulty", "medium"),
                    task_data.get("temperature", 0.0),
                    0,  # user-defined
                ),
            )
            conn.commit()
            return {"ok": True, "task_id": task_id}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def delete_task(self, task_id: str) -> dict:
        """Delete a canary task."""
        conn = self.db._get_conn()
        try:
            conn.execute("DELETE FROM canary_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a single canary task by ID."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT id, name, description, prompt, assertions, timeout, model, trials, "
            "expected_output, category, difficulty, temperature, built_in, created_at "
            "FROM canary_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        # Parse assertions JSON for convenience
        try:
            result["assertions"] = json.loads(result["assertions"]) if isinstance(result["assertions"], str) else result["assertions"]
        except Exception:
            pass
        return result

    def update_task(self, task_id: str, task_data: dict) -> dict:
        """Update an existing canary task.

        Args:
            task_id: The task ID to update.
            task_data: {name?, description?, prompt?, assertions?, timeout?, model?, trials?}

        Returns:
            {ok, error?}
        """
        conn = self.db._get_conn()
        try:
            fields = []
            values = []
            for key, col in [("name", "name"), ("description", "description"),
                             ("prompt", "prompt"), ("timeout", "timeout"),
                             ("model", "model"), ("trials", "trials"),
                             ("expected_output", "expected_output"),
                             ("category", "category"),
                             ("difficulty", "difficulty"),
                             ("temperature", "temperature")]:
                if key in task_data:
                    # Validate prompt for template variables
                    if key == "prompt":
                        blanks = self._check_blanks(task_data[key])
                        if blanks:
                            return {
                                "ok": False,
                                "error": f"Prompt has unresolved templates: {', '.join(blanks)}. Replace them with actual test data or provide sample values."
                            }
                    fields.append(f"{col} = ?")
                    values.append(task_data[key])
            if "assertions" in task_data:
                fields.append("assertions = ?")
                values.append(json.dumps(task_data["assertions"]))

            if not fields:
                return {"ok": False, "error": "No fields to update"}

            values.append(task_id)
            conn.execute(
                f"UPDATE canary_tasks SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            conn.commit()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── Running ────────────────────────────────────────────────────────────

    def run(
        self,
        agent_name: str,
        task_ids: Optional[list[str]] = None,
        trials: Optional[int] = None,
        config_label: Optional[str] = None,
        split: str = "all",
        adapter_override=None,
    ) -> CanaryReport:
        """Run the canary suite for one agent.

        Args:
            agent_name: Hermes agent profile name.
            task_ids: Specific task IDs to run (None = all).
            trials: Override per-task trial count (None = use task default).
            config_label: Human-readable label for this config state.
            split: Filter tasks by split — 'dev', 'test', or 'all' (default).
                Dev/test split prevents overfitting when results inform config
                optimization. Inspired by HF harness-optimization (Niklaus 2026).
            adapter_override: Optional adapter for user-defined (built_in=0)
                tasks. When provided, generic (built_in=1) tasks run via
                self.executor (existing adapter) and user-defined tasks run via
                adapter_override. This is the two-pass design from obs-spec-060:
                generic tasks need no tools, user-defined tasks (mined from real
                agent conversations) need the Hermes adapter with -p default.

        Returns:
            CanaryReport with aggregate and per-task results.
        """
        # Set the adapter to use this agent's profile
        if hasattr(self.executor, 'adapter') and hasattr(self.executor.adapter, 'agent_profile'):
            self.executor.adapter.agent_profile = agent_name

        # 1. Load tasks (filtered by split)
        conn = self.db._get_conn()
        split_clause = ""
        split_params: list = []
        if split != "all":
            split_clause = " AND split = ?"
            split_params = [split]
        if task_ids:
            placeholders = ",".join("?" * len(task_ids))
            rows = conn.execute(
                f"SELECT id, name, prompt, assertions, timeout, model, trials, temperature, built_in "
                f"FROM canary_tasks WHERE id IN ({placeholders}){split_clause} "
                f"ORDER BY id",
                [*task_ids, *split_params],
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, name, prompt, assertions, timeout, model, trials, temperature, built_in "
                f"FROM canary_tasks WHERE 1=1{split_clause} ORDER BY id",
                split_params,
            ).fetchall()

        if not rows:
            logger.warning("No canary tasks found for agent %s", agent_name)
            return CanaryReport(agent_name=agent_name, total_tasks=0)

        tasks = [dict(r) for r in rows]
        # Filter out tasks with unresolved template variables
        valid_tasks = []
        skipped_count = 0
        for task in tasks:
            blanks = self._check_blanks(task.get("prompt", ""))
            if blanks:
                logger.warning("Skipping task %s — unresolved templates: %s", task["id"], blanks)
                skipped_count += 1
                continue
            valid_tasks.append(task)

        if not valid_tasks:
            logger.warning("All tasks skipped for agent %s (all have unresolved templates)", agent_name)
            return CanaryReport(agent_name=agent_name, total_tasks=0)

        tasks = valid_tasks

        # Two-pass setup (obs-spec-060): if adapter_override is provided, route
        # user-defined (built_in=0) tasks to it. Generic tasks keep self.executor.
        override_executor = None
        if adapter_override is not None:
            override_executor = TaskExecutor(adapter=adapter_override)

        # 2. Snapshot config
        config_hash = self._compute_config_hash(agent_name, tasks)

        # 3. Create run record
        run_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO canary_runs (id, agent_name, config_hash, config_label, "
            "started_at, status, total_tasks) VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (run_id, agent_name, config_hash, config_label, now_iso, len(tasks)),
        )
        conn.commit()

        # 4. Execute each task × trial
        all_results: list[dict] = []
        pass_count = 0
        hang_count = 0
        fail_count = 0
        total_cost = 0.0
        total_tokens = 0

        for task in tasks:
            task_trials = trials if trials is not None else task.get("trials", 10)
            # ponytail: per-task progress print. Without this, 120 trials
            # run silently for up to 2 hours. Upgrade: add --quiet flag.
            print(f"  {task['name']} ({task_trials} trials):", end="", flush=True)
            task_passes = 0
            task_hangs = 0
            task_fails = 0
            task_accuracies: list[float] = []
            task_costs: list[float] = []
            task_tokens: list[int] = []
            task_trajectories: list[dict] = []

            assertions = json.loads(task["assertions"]) if isinstance(task["assertions"], str) else task["assertions"]

            # Route executor: user-defined tasks (built_in=0) use the override
            # adapter when available; generic tasks use self.executor.
            executor = self.executor
            if override_executor is not None and task.get("built_in", 1) == 0:
                executor = override_executor

            for trial_idx in range(task_trials):
                result = executor.execute(task, agent_name, timeout=task.get("timeout", 300))

                if result.provider_error:
                    passed = False
                    accuracy = 0.0
                    status = "provider_error"
                    task_fails += 1
                elif result.hang or result.error:
                    passed = False
                    accuracy = 0.0
                    status = "hang"
                    task_hangs += 1
                else:
                    passed, accuracy, reasoning = self.scorer.score(assertions, result.output, task_id=task["id"])
                    if passed:
                        task_passes += 1
                        status = "pass"
                    else:
                        task_fails += 1
                        status = "fail"

                # ponytail: one-char per-trial progress. Prints '.'/'x'/'h'/'!'
                # so the user sees output every trial (~30-60s) instead of
                # silence for hours. Upgrade: use status bar with elapsed time.
                print({"pass": ".", "fail": "x", "hang": "h", "provider_error": "!"}[status], end="", flush=True)

                task_accuracies.append(accuracy)
                if result.cost:
                    task_costs.append(result.cost)
                if result.tokens:
                    task_tokens.append(result.tokens)

                task_trajectories.append({
                    "trial": trial_idx,
                    "status": status,
                    "accuracy": accuracy,
                    "output": result.output[:500],  # truncated for storage
                    "error": result.error,
                    "latency_ms": result.latency_ms,
                    "provider_error": result.provider_error,
                })

                # Store individual result
                result_id = str(uuid.uuid4())
                ci_lower, ci_upper = Scorer.bootstrap_ci(task_accuracies)
                conn.execute(
                    "INSERT INTO canary_results (id, run_id, task_id, status, accuracy, "
                    "ci_lower, ci_upper, cost, tokens, latency_ms, trajectory, error, "
                    "provider_error) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        result_id, run_id, task["id"], status,
                        accuracy, ci_lower, ci_upper,
                        result.cost, result.tokens, int(result.latency_ms),
                        json.dumps(task_trajectories[-1]),
                        result.error if result.error else None,
                        1 if result.provider_error else 0,
                    ),
                )

            # Blowup detection — one trial collapses to near-0 while others pass.
            # HF harness-optimization found per-trial variance is driven by catastrophic
            # blowups (provider 400, no deliverable), not smooth noise. Flag them as
            # signal, not noise — they point to specific, fixable failure modes.
            blowup_count = 0
            if len(task_accuracies) >= 2:
                median_acc = sorted(task_accuracies)[len(task_accuracies) // 2]
                if median_acc > 0:
                    blowup_count = sum(1 for a in task_accuracies if a < 0.2 * median_acc)

            # Task footer — closes the per-task progress line
            print(f"  {task_passes}/{task_trials} pass, {task_hangs} hang, {task_fails} fail")

            # Per-task aggregate
            mean_accuracy = sum(task_accuracies) / len(task_accuracies) if task_accuracies else 0.0
            ci_lower, ci_upper = Scorer.bootstrap_ci(task_accuracies)
            task_cost = sum(task_costs)
            task_token_total = sum(task_tokens)

            all_results.append({
                "task_id": task["id"],
                "task_name": task["name"],
                "passes": task_passes,
                "hangs": task_hangs,
                "fails": task_fails,
                "accuracy": round(mean_accuracy, 4),
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "cost": round(task_cost, 6),
                "tokens": task_token_total,
                "trajectory": task_trajectories,
                "blowups": blowup_count,
            })

            pass_count += task_passes
            hang_count += task_hangs
            fail_count += task_fails
            total_cost += task_cost
            total_tokens += task_token_total

        conn.commit()

        # 5. Update run record
        overall_accuracy = pass_count / (pass_count + fail_count) if (pass_count + fail_count) > 0 else 0.0
        all_accuracies = []
        for tr in all_results:
            all_accuracies.extend([t["accuracy"] for t in tr["trajectory"]])
        ci_lower, ci_upper = Scorer.bootstrap_ci(all_accuracies)

        completed_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE canary_runs SET completed_at=?, status='completed', "
            "pass_count=?, hang_count=?, fail_count=?, total_cost=?, total_tokens=? "
            "WHERE id=?",
            (completed_at, pass_count, hang_count, fail_count, round(total_cost, 6), total_tokens, run_id),
        )
        conn.commit()

        return CanaryReport(
            run_id=run_id,
            agent_name=agent_name,
            config_hash=config_hash,
            total_tasks=len(tasks),
            pass_count=pass_count,
            hang_count=hang_count,
            fail_count=fail_count,
            overall_accuracy=round(overall_accuracy, 4),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            total_cost=round(total_cost, 6),
            total_tokens=total_tokens,
            per_task=all_results,
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_config_hash(agent_name: str, tasks: list[dict]) -> str:
        """Compute sha256 of (agent_name + model + prompt + tools) as a config fingerprint.

        ponytail: Simple sha256. Won't detect template rendering changes.
        Upgrade path: hash the resolved prompt after template rendering.
        """
        # Use agent name + first task's model + all task prompts as fingerprint
        model = tasks[0].get("model", "") if tasks else ""
        prompts = "|".join(t.get("prompt", "") for t in tasks)
        raw = f"{agent_name}:{model}:{prompts}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def get_run(self, run_id: str) -> Optional[dict]:
        """Get a canary run by ID."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT * FROM canary_runs WHERE id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_runs(self, agent_name: str, limit: int = 20) -> list[dict]:
        """List recent canary runs for an agent."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT * FROM canary_runs WHERE agent_name = ? "
            "ORDER BY started_at DESC LIMIT ?",
            (agent_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_run_results(self, run_id: str) -> list[dict]:
        """Get all task results for a canary run."""
        conn = self.db._get_conn()
        rows = conn.execute(
            "SELECT cr.*, ct.name as task_name FROM canary_results cr "
            "JOIN canary_tasks ct ON cr.task_id = ct.id "
            "WHERE cr.run_id = ? ORDER BY ct.id",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]
