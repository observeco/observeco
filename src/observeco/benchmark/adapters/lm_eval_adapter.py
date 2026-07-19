"""Agent harness adapter for lm-eval-harness.

Implements ``lm_eval.api.model.LM``, routing all prompts through
``hermes chat -q`` to evaluate agent quality through the actual agent harness.

ponytail: No logprob access from agent harness.
  - ``loglikelihood`` uses generate-then-compare heuristic (exact/prefix/substring match).
  - ``loglikelihood_rolling`` returns 0.0 (no perplexity from agent harness).
  Upgrade path: hermes API with logprob support, or a local LLM backend.

ponytail: Sequential agent calls (one per request). No batching or parallelism.
  Upgrade path: concurrent subprocess calls via ThreadPoolExecutor.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from typing import Optional

from lm_eval.api.instance import Instance
from lm_eval.api.model import LM

logger = logging.getLogger(__name__)


class HermesAgentLM(LM):
    """Routes lm-eval tasks through a Hermes agent session.

    Each lm-eval request becomes a ``hermes chat -q`` call. The agent's output
    is returned for scoring by lm-eval's metric pipelines (exact_match, f1, etc.).
    """

    def __init__(
        self,
        agent_name: str = "default",
        hermes_bin: str = "hermes",
        timeout: float = 60,
        harness_config: Optional[dict] = None,
    ) -> None:
        super().__init__()
        self.agent_name = agent_name
        self.hermes_bin = hermes_bin
        self.timeout = timeout
        # ponytail: harness_config overrides timeout/retry for grid sweeps.
        # Only timeout and max_retries apply to single-turn lm-eval tasks.
        # Upgrade path: wire tool_feedback_mode and context_mode when lm-eval
        # tasks become multi-turn.
        self.harness_config = harness_config or {}
        if self.harness_config.get("call_timeout_seconds"):
            self.timeout = self.harness_config["call_timeout_seconds"]
        self.max_retries = self.harness_config.get("max_retries", 1)
        self.retry_delay = self.harness_config.get("retry_delay_seconds", 2.0)
        # Profile override: use a different Hermes profile for benchmark runs.
        # Minimal profiles (no routing rules, no PTCA) avoid the 80-pt system
        # prompt penalty measured on BBH boolean expressions.
        self.profile = self.harness_config.get("profile")
        # Cache: context text → generated output (avoids redundant calls for MC tasks)
        self._context_cache: dict[str, str] = {}

    # ── Core lm-eval interface ─────────────────────────────────────────────

    def generate_until(self, requests: list[Instance]) -> list[str]:
        """Generate continuations from each context through the agent harness.

        Each ``Instance.args`` is ``(context: str, gen_kwargs: dict)``.

        When ``self_check`` is enabled in harness_config, each answer is
        verified by the model before submission. If verification changes the
        answer, the verified version is used. Cap at 2 total attempts per
        sample (1 initial + 1 verify).

        ponytail: Self-check doubles API calls per sample. Upgrade path:
        skip self-check for knowledge tasks (TriviaQA, ARC) where the model
        either knows or doesn't — verification doesn't help.
        """
        results: list[str] = []
        for req in requests:
            context, gen_kwargs = req.args
            prompt = self._build_generation_prompt(context, gen_kwargs)
            output = self._run_agent(prompt)

            # Self-check: verify answer before submitting.
            # Only applies to reasoning tasks (BBH, BBQ, IFEval) where
            # the model can catch its own mistakes. Skipped for code
            # (MBPP — verification prompt causes second-guessing) and
            # knowledge (TriviaQA, ARC — model either knows or doesn't).
            if self.harness_config.get("self_check", False):
                task_name = getattr(req, "task_name", "") or ""
                if any(kw in task_name for kw in ["bbh", "bbq", "ifeval"]):
                    verified = self._self_check(context, output)
                    if verified and verified != output:
                        output = verified

            # Normalize output for scoring: if the model responds with just
            # "True." or "False." without "the answer is" prefix, reformat
            # so BBH's get-answer regex can extract it.
            # ponytail: simple True/False detection on last line.
            # Upgrade path: broader answer format normalization for all BBH tasks.
            output = self._normalize_answer(output)
            # ponytail: Simple until-stop trimming. Upgrade: proper stop-token
            # tracking if hermes exposes generation tokens.
            until = gen_kwargs.get("until", [])
            if until:
                output = self._trim_until(output, until)
            results.append(output)
        return results

    def loglikelihood(self, requests: list[Instance]) -> list[tuple[float, bool]]:
        """Score continuations given contexts — generate-then-compare heuristic.

        Each ``Instance.args`` is ``(context: str, continuation: str)``.
        Returns ``(logprob, is_greedy)`` tuples.

        ponytail: No real logprobs from agent harness. Maps comparison outcome to
        approximate logprobs for MC ranking. Upgrade path: local model backend
        with token-level logprob access.
        """
        results: list[tuple[float, bool]] = []
        for req in requests:
            context, continuation = req.args
            # Cache: generate once per unique context (MC sends same context N times)
            if context not in self._context_cache:
                self._context_cache[context] = self._run_agent(context)
            generated = self._context_cache[context]
            logprob, is_greedy = self._score_continuation(
                continuation, generated
            )
            results.append((logprob, is_greedy))
        return results

    def loglikelihood_rolling(self, requests: list[Instance]) -> list[float]:
        """For perplexity — no logprobs from agent harness.

        ponytail: Returns 0.0 for all requests. Agent harness cannot compute
        token-level perplexity. Upgrade path: local model backend.
        """
        return [0.0] * len(requests)

    # ── Prompt building ────────────────────────────────────────────────────

    @staticmethod
    def _build_generation_prompt(context: str, gen_kwargs: dict) -> str:
        """Build the prompt for generate_until from context + gen_kwargs.

        If gen_kwargs includes ``max_gen_toks`` or ``temperature``, we append them
        as hints — hermes chat -q doesn't accept these natively, but the agent
        self-regulates.
        """
        return context

    # ── Agent communication ────────────────────────────────────────────────

    def _run_agent(self, prompt: str) -> str:
        """Run ``hermes chat -q <prompt>`` and return stripped output.

        Times out after ``self.timeout`` seconds. Returns error string on failure
        (never raises — lm-eval expects graceful degradation).

        ponytail: Uses Popen + process group kill to ensure child processes are
        reaped on timeout. Upgrade path: async subprocess with proper process
        tree management.
        """
        import os
        import signal
        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                start = time.time()
                cmd = [self.hermes_bin]
                if self.profile:
                    cmd.extend(["-p", self.profile])
                cmd.extend(["chat", "-q", prompt, "-Q"])
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid,
                )
                try:
                    stdout, stderr = proc.communicate(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Hermes timed out after %.0fs (attempt %d/%d)",
                        self.timeout,
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                    proc.wait()
                    last_error = f"[ERROR: timeout after {self.timeout:.0f}s]"
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay)
                        continue
                    return last_error

                elapsed = time.time() - start
                logger.debug(
                    "hermes chat -q completed in %.1fs (exit=%d)",
                    elapsed,
                    proc.returncode,
                )

                output = stdout.strip()

                # Strip Hermes warning/status lines
                output = "\n".join(
                    line for line in output.splitlines()
                    if not line.startswith("Warning:")
                    and not line.startswith("session_id:")
                ).strip()

                # Strip markdown code fences and formatting
                output = re.sub(r"```\w*\n?", "", output)
                output = re.sub(r"\*\*|__|\*|_", "", output).strip()

                if proc.returncode != 0:
                    error = stderr.strip() or "unknown error"
                    logger.warning(
                        "Hermes task failed (exit=%d): %s", proc.returncode, error
                    )
                    last_error = f"[ERROR: exit={proc.returncode}]"
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay)
                        continue
                    return last_error

                return output

            except FileNotFoundError:
                return f"[ERROR: {self.hermes_bin} not found]"

            except Exception as exc:
                logger.error("Hermes call failed: %s", exc)
                last_error = f"[ERROR: {exc}]"
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue

        return last_error or "[ERROR: max retries exceeded]"

    # ── Scoring heuristic ──────────────────────────────────────────────────

    @staticmethod
    def _score_continuation(
        continuation: str, generated: str
    ) -> tuple[float, bool]:
        """Compare continuation against generated output.

        Returns ``(logprob, is_greedy)`` where logprob is an approximate value
        suitable for MC ranking.

        Mapping:
          - Generated starts with continuation: logprob=-0.223 (~0.8), greedy=True
          - Generated contains continuation:    logprob=-1.609 (~0.2), greedy=False
          - No match:                           logprob=-10.0,          greedy=False

        ponytail: Ad-hoc scoring table tuned for MC ranking, not calibrated
        against true token probabilities. Upgrade path: local LLM backend
        with token-level logprobs.
        """
        gen_stripped = generated.strip()
        cont_stripped = continuation.strip()

        if not cont_stripped:
            return (-0.223, True)

        if gen_stripped.startswith(cont_stripped):
            return (-0.223, True)
        elif cont_stripped in gen_stripped:
            return (-1.609, False)
        else:
            return (-10.0, False)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _self_check(self, context: str, answer: str) -> str:
        """Verify answer via self-check. Returns verified answer or empty string.

        Asks the model to verify its own answer. If the model changes its
        answer, the new answer is returned. If the model confirms, the
        original answer is returned unchanged.

        ponytail: Simple re-ask with verification prompt. No structured
        verification (running code, checking facts). Upgrade path: task-type
        specific verification (run test cases for code, check facts for
        knowledge, re-solve for math).
        """
        verify_prompt = (
            f"Question: {context}\n\n"
            f"Your answer: {answer}\n\n"
            f"Verify your answer. If it is correct, restate it. "
            f"If it is wrong, provide the correct answer."
        )
        verified = self._run_agent(verify_prompt)
        if not verified or verified.startswith("[ERROR"):
            return answer  # verification failed, keep original
        return verified

    @staticmethod
    def _normalize_answer(output: str) -> str:
        """Normalize output for metric scoring.

        Three behaviors:
        1. BBH-format answers (\"So the answer is\", \"Therefore/Thus\") → preserved.
           The ``get-answer`` filter needs the full prefix to extract the answer.
        2. Generic answer markers (\"The correct answer is\", \"The answer:\") →
           extracted. TriviaQA, ARC, BBQ expect bare answers for exact_match.
        3. Bare True/False → appended with \"So the answer is\" for BBH.

        ponytail: Regex-based answer extraction. Upgrade path: task-config-driven
        extraction patterns per metric type.
        """
        import re

        # 1. BBH markers — preserve full output for get-answer filter
        bbh_markers = r'(?i)(So the answer is|Therefore,? the answer|Thus,? the answer)'
        if re.search(bbh_markers, output):
            return output

        # 2. Generic markers — extract just the answer for exact_match tasks
        extract_pattern = r'(?i)(?:The correct answer is|The answer:)\s*(.+?)(?:[.,;!?\n]|$)'
        m = re.search(extract_pattern, output)
        if m:
            answer = m.group(1).strip()
            # Clean up: "option B" → "B", "Option C" → "C"
            answer = re.sub(r'(?i)option\s+([A-D])', r'\1', answer)
            return answer

        # 3. Bare True/False — add BBH format
        words = re.findall(r'\b(True|False)\b', output)
        if words:
            answer = words[-1]
            return output.rstrip() + "\nSo the answer is " + answer + "."

        return output

    @staticmethod
    def _trim_until(output: str, until: list[str]) -> str:
        """Trim output at the first occurrence of any stop sequence.

        ponytail: Post-hoc trim — doesn't prevent the agent from generating
        past the stop. Upgrade path: hermes API with stop-token support.

        ``\\n\\n`` is special: only stops when it appears AFTER a recognizable
        answer marker. Internal ``\\n\\n`` between chain-of-thought paragraphs
        is preserved. This prevents premature truncation of multi-paragraph
        reasoning for BBH/BBQ tasks.

        Sentence-level stops (``.``, ``,``, ``\\n``) use naive first-occurrence
        trimming — these are the correct boundaries for short-answer tasks
        (TriviaQA, ARC, GSM8K). Protecting them causes rambling completions
        that confuse exact-match scoring.
        ponytail: Regex-based answer detection. Upgrade path: task-config-driven
        stop rules with per-task answer patterns.
        """
        answer_markers = (
            r'(?i)'
            r'(So the answer is|'
            r'the correct answer is|'
            r'Therefore,? the answer|'
            r'Thus,? the answer|'
            r'The answer:)'
        )
        answer_match = re.search(answer_markers, output)

        for stop_seq in until:
            if stop_seq == "\n\n":
                if not answer_match:
                    continue
                after_answer = output[answer_match.end():]
                idx = after_answer.find(stop_seq)
                if idx != -1:
                    return output[:answer_match.end() + idx].strip()
            else:
                idx = output.find(stop_seq)
                if idx != -1:
                    return output[:idx].strip()
        return output

    def detect_model(self) -> str:
        """Detect current Hermes model from config. Returns 'unknown' on failure."""
        try:
            result = subprocess.run(
                [self.hermes_bin, "config", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse model from config show output
                # Format: "  Model:        {'default': 'deepseek-v4-pro', 'provider': 'deepseek'}"
                for line in result.stdout.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("Model:") and "default" in stripped:
                        # Extract the dict-like value and parse the model name
                        import ast
                        val = stripped.split(":", 1)[1].strip()
                        try:
                            model_dict = ast.literal_eval(val)
                            if isinstance(model_dict, dict):
                                provider = model_dict.get("provider", "")
                                model = model_dict.get("default", "")
                                if provider and model:
                                    return f"{provider}/{model}"
                                return model or "unknown"
                        except (ValueError, SyntaxError):
                            pass
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return "unknown"
