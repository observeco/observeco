"""LiteLLM adapter for lm-eval-harness — real logprobs via DeepSeek reasoning.

Uses LiteLLM as the unified API layer. For MC scoring, extracts real
token-level logprobs from DeepSeek's ``reasoning_content`` field (the
thinking tokens that contain the answer). For free-text tasks, uses the
specified cloud provider via LiteLLM.

Architecture:
  - ``loglikelihood`` → DeepSeek API (real logprobs from reasoning tokens)
    Scores each continuation token-by-token: for each position, sends
    (context + continuation[:i]) and looks up continuation[i] in
    the reasoning_content logprobs.
  - ``generate_until`` → cloud provider via LiteLLM (free-text generation)
  - ``loglikelihood_rolling`` → 0.0 (no perplexity support)

ponytail: DeepSeek v4 is a reasoning model. The answer tokens appear in
``reasoning_content``, not ``content``. The content field is empty until
the model finishes reasoning. We extract logprobs from reasoning tokens.
  Upgrade path: use a non-reasoning model (OpenAI, Together) for clean
  content logprobs.
"""

from __future__ import annotations

import logging
import time

from litellm import completion
from lm_eval.api.instance import Instance
from lm_eval.api.model import LM

logger = logging.getLogger(__name__)


class LiteLLMAdapter(LM):
    """Routes lm-eval tasks through LiteLLM with real logprobs.

    For MC scoring (loglikelihood), uses DeepSeek's reasoning_content
    logprobs. For free-text (generate_until), uses the specified cloud
    provider via LiteLLM.
    """

    def __init__(
        self,
        model_spec: str = "deepseek/deepseek-v4-flash",
        timeout: float = 120,
    ) -> None:
        super().__init__()
        self.model_spec = model_spec
        self.timeout = timeout
        self._logprob_cache: dict[str, list[dict]] = {}

    @property
    def model_name_display(self) -> str:
        return f"litellm:{self.model_spec}"

    # ── Core lm-eval interface ─────────────────────────────────────────────

    def generate_until(self, requests: list[Instance]) -> list[str]:
        results: list[str] = []
        for req in requests:
            context, gen_kwargs = req.args
            output = self._generate(context, gen_kwargs)
            results.append(output)
        return results

    def loglikelihood(self, requests: list[Instance]) -> list[tuple[float, bool]]:
        """Score continuations using real logprobs from DeepSeek reasoning.

        For each (context, continuation) pair, scores token-by-token:
        1. For each position i in continuation:
           - Send (context + continuation[:i]) as prompt
           - Get top_logprobs from reasoning_content
           - Look up continuation[i] in top_logprobs
        2. Sum logprobs across all positions
        3. Return (sum_logprob, is_greedy_all)
        """
        results: list[tuple[float, bool]] = []
        for req in requests:
            context, continuation = req.args
            total_logprob = 0.0
            all_greedy = True

            for i in range(len(continuation)):
                prompt = context + continuation[:i]
                expected = continuation[i]

                top_logprobs = self._get_top_logprobs(prompt)
                logprob, is_greedy = self._lookup(expected, top_logprobs)
                total_logprob += logprob
                if not is_greedy:
                    all_greedy = False

            results.append((total_logprob, all_greedy))
        return results

    def loglikelihood_rolling(self, requests: list[Instance]) -> list[float]:
        return [0.0] * len(requests)

    # ── Generation ─────────────────────────────────────────────────────────

    def _generate(self, context: str, gen_kwargs: dict) -> str:
        until = gen_kwargs.get("until", [])
        max_tokens = gen_kwargs.get("max_tokens", 128)

        try:
            resp = completion(
                model=self.model_spec,
                messages=[{"role": "user", "content": context}],
                temperature=0.0,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            content = resp.choices[0].message.content or ""
            for seq in until:
                idx = content.find(seq)
                if idx != -1:
                    content = content[:idx]
            return content.strip()
        except Exception as exc:
            logger.error("generate failed: %s", exc)
            return ""

    # ── Logprobs from DeepSeek reasoning ──────────────────────────────────

    def _get_top_logprobs(self, prompt: str) -> list[dict]:
        """Get top_logprobs for the next token from DeepSeek reasoning.

        Returns list of {token, logprob} dicts, highest logprob first.
        Caches by prompt to avoid redundant calls.

        Extracts logprobs from ``reasoning_content`` — the thinking tokens
        that DeepSeek v4 generates before the visible answer.
        """
        if prompt in self._logprob_cache:
            return self._logprob_cache[prompt]

        start = time.monotonic()
        try:
            resp = completion(
                model=self.model_spec,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1,
                logprobs=True,
                top_logprobs=5,
                timeout=self.timeout,
            )
            elapsed = time.monotonic() - start

            choice = resp.choices[0]
            lp = choice.logprobs

            result: list[dict] = []

            if lp and lp.reasoning_content and len(lp.reasoning_content) > 0:
                # DeepSeek v4: logprobs are in reasoning_content
                # Each entry is a dict with 'token', 'logprob', 'top_logprobs'
                last = lp.reasoning_content[-1]
                if isinstance(last, dict):
                    top = last.get("top_logprobs", [])
                    result = [
                        {"token": t["token"], "logprob": t["logprob"]}
                        for t in top
                    ]
                elif hasattr(last, "top_logprobs"):
                    result = [
                        {"token": t.token, "logprob": t.logprob}
                        for t in last.top_logprobs
                    ]

            if not result and lp and lp.content and len(lp.content) > 0:
                # Fallback: content logprobs (non-reasoning models)
                top = lp.content[0].top_logprobs
                result = [
                    {"token": t.token, "logprob": t.logprob}
                    for t in top
                ]

            logger.debug("logprobs: %.1fs, %d candidates", elapsed, len(result))
            self._logprob_cache[prompt] = result
            return result

        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("logprobs failed (%.1fs): %s", elapsed, exc)
            self._logprob_cache[prompt] = []
            return []

    # ── Scoring ────────────────────────────────────────────────────────────

    @staticmethod
    def _lookup(
        expected_token: str, top_logprobs: list[dict]
    ) -> tuple[float, bool]:
        if not top_logprobs:
            return (-15.0, False)

        for entry in top_logprobs:
            if entry["token"] == expected_token:
                is_greedy = entry is top_logprobs[0]
                return (entry["logprob"], is_greedy)

        return (-15.0, False)
