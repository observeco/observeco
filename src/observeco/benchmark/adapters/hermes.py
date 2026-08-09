"""Hermes harness adapter — runs benchmark tasks through a Hermes agent session.

ponytail: Uses subprocess to run a Hermes CLI command. This is the simplest
approach for v1 — it tests the agent through its actual CLI interface.
Upgrade path: use the Hermes API directly for faster execution and structured
output parsing.
"""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import time
from pathlib import Path

from observeco.benchmark.engine import BenchmarkTask

logger = logging.getLogger(__name__)

# Provider error patterns in stderr — retry these, don't count as model failures.
# Inspired by HF harness-optimization: "transient provider failures (5xx / 429 /
# stream drops) were re-run, so every remaining 0-score is a genuine model/harness
# failure, not infra."
_PROVIDER_ERROR_PATTERNS = [
    r"HTTP 5\d\d",
    r"429",
    r"rate.?limit",
    r"overloaded",
    r"service.unavailable",
    r"internal.server.error",
    r"bad.gateway",
    r"gateway.timeout",
    r"connection.?reset",
    r"stream.*error",
    r"upstream.*error",
]
_PROVIDER_ERROR_RE = re.compile("|".join(_PROVIDER_ERROR_PATTERNS), re.IGNORECASE)

_MAX_RETRIES = 2
_RETRY_DELAYS = [2, 4]  # seconds, exponential-ish

# Regex to parse token usage from Hermes --verbose stderr output.
# Format: Usage: CompletionUsage(completion_tokens=27, prompt_tokens=32403, total_tokens=32430, ...)
# ponytail: Hermes-internal format. If the format changes, parsing fails
# silently (returns None, cost=0). Upgrade path: use structured JSON output
# or the Hermes Python API directly.
_TOKEN_USAGE_RE = re.compile(
    r"Usage: CompletionUsage\(completion_tokens=(\d+), prompt_tokens=(\d+), total_tokens=(\d+)"
)
# session_id: 20260804_194735_e27347 (emitted by `hermes chat -Q --verbose` on stderr)
_SESSION_ID_RE = re.compile(r"session_id[:=]\s*([\w\-\.]+)", re.IGNORECASE)

# Per-model pricing in $/1M tokens (input, output). Covers models used
# by the Hermes adapter chain.
# ponytail: static table — update when provider pricing changes.
# Upgrade path: fetch from provider API or Hermes config.yaml provider defs.
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "deepseek-v4-flash": (0.15, 0.60),
    "deepseek-v4-pro": (2.00, 8.00),
    "deepseek-chat": (0.15, 0.60),
    "glm-5.2": (0.60, 2.40),  # estimate: Zhipu GLM family, mid-tier (similar to deepseek-v4-pro band)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-3.5": (0.80, 4.00),
    "claude-opus-4": (15.00, 75.00),
}


def _load_dotenv() -> None:
    """Load .env from the project root into os.environ, if it exists.

    ponytail: manual KEY=VALUE parser, not python-dotenv. Handles basic
    quoting and comments. Upgrade path: use python-dotenv if it becomes
    a dependency for other reasons.
    """
    # Walk up from this file to find the project root (where .env lives)
    # hermes.py is at src/observeco/benchmark/adapters/ — 5 levels from root
    env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


# Load .env at module import time so OBSERVECO_CANARY_MODEL is available
# before any adapter is instantiated.
_load_dotenv()


class HermesBenchmarkAdapter:
    """Runs benchmark tasks through a Hermes agent session."""

    def __init__(self, hermes_bin: str = "hermes", timeout: int = 300,
                 agent_profile: str = "", model: str = "",
                 workdir: str = ""):
        self.hermes_bin = hermes_bin
        self.timeout = timeout
        self.agent_profile = agent_profile
        # Workdir for the spawned hermes session. NEVER inherit ambient process
        # cwd — a replay must run inside its pinned worktree. Explicit cwd=
        # removes dependence on the parent process's state (which has been an
        # unpinned source of environment lies). Empty = inherit (default).
        self.workdir = workdir
        # Model priority chain (first non-empty wins):
        #   1. Per-task model column (set in run_task)
        #   2. OBSERVECO_CANARY_MODEL env var (user-level default)
        #   3. Adapter constructor model param (code-level fallback)
        #   4. Hermes default (whatever `hermes config get model` returns)
        self.model = model

    def _is_provider_error(self, stderr: str) -> bool:
        """Check if stderr indicates a transient provider error (5xx/429)."""
        return bool(_PROVIDER_ERROR_RE.search(stderr or ""))

    def _parse_token_usage(self, stderr: str) -> dict | None:
        """Extract token counts from Hermes verbose stderr output.

        Returns {prompt_tokens, completion_tokens, total_tokens} or None
        if the format doesn't match (silent fallback).
        """
        m = _TOKEN_USAGE_RE.search(stderr or "")
        if not m:
            return None
        return {
            "prompt_tokens": int(m.group(2)),
            "completion_tokens": int(m.group(1)),
            "total_tokens": int(m.group(3)),
        }

    def _parse_session_id(self, stderr: str) -> str:
        """Extract the created session id from Hermes verbose stderr.

        `hermes chat -Q --verbose` emits `session_id: <id>` on stderr. This is
        the session the replay actually ran in — bound to the run as provenance,
        so containment and audits target the right entity. Empty = not found.
        """
        m = _SESSION_ID_RE.search(stderr or "")
        return m.group(1) if m else ""

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
            logger.warning("Unknown model %s — cost estimate unavailable", model_used)
            return 0.0
        input_price, output_price = pricing
        return (
            tokens["prompt_tokens"] * input_price / 1_000_000
            + tokens["completion_tokens"] * output_price / 1_000_000
        )

    def run_task(self, agent_name: str, task: BenchmarkTask) -> dict:
        """Run a benchmark task through the Hermes agent.

        Returns {output, model_used, harness_type, provider_error}.
        Retries transient provider failures (5xx/429) up to 2 times.
        """
        prompt = task.input_text
        if task.context_text:
            prompt = f"{task.context_text}\n\n{task.input_text}"

        last_error = ""
        for attempt in range(_MAX_RETRIES + 1):
            try:
                start = time.time()
                cmd = [self.hermes_bin]
                # Model priority chain (first non-empty wins):
                #   1. Per-task model column
                #   2. OBSERVECO_CANARY_MODEL env var
                #   3. Adapter constructor model param
                #   4. Hermes default (no -m flag — inherits whatever is configured)
                task_model = (
                    getattr(task, "model", "") or ""
                    or os.environ.get("OBSERVECO_CANARY_MODEL", "")
                    or self.model
                )
                if task_model:
                    cmd += ["-m", task_model]
                    # If model name has a provider prefix (e.g. tencent/hy3:free),
                    # pass it as --provider so Hermes routes to the right backend.
                    # ponytail: assumes first segment before / is a valid provider name.
                    # Upgrade path: use a model→provider mapping table.
                    if "/" in task_model:
                        provider = task_model.split("/", 1)[0]
                        cmd += ["--provider", provider]
                if self.agent_profile:
                    cmd += ["-p", self.agent_profile]
                cmd += ["chat", "-q", prompt, "-Q", "--verbose"]
                # Temperature control: hermes chat supports --temperature (0.0-2.0).
                # Passed through to the model provider via request_overrides.
                # ponytail: only passes when non-zero; temperature=0.0 is the
                # deterministic default and is omitted to use the model's contract.
                temperature = float(getattr(task, "temperature", 0.0) or 0.0)
                if temperature:
                    cmd += ["--temperature", f"{temperature:.4f}"]
                # Sanitize environment: the parent process may be running inside
                # a Hermes cron/gateway session (HERMES_* vars set). If we don't
                # strip them, the child `hermes chat` inherits the session context
                # and fails with exit=1 (nested session conflict). Strip ALL
                # HERMES_* vars — the child Hermes resolves its own home.
                child_env = {
                    k: v for k, v in os.environ.items()
                    if not k.startswith("HERMES_")
                }
                # Force direct API URL — the hermes agent hardcodes
                # ollama-cloud → http://127.0.0.1:20128/v1 (9router proxy) which
                # is broken. Override with the config's direct HTTPS URL so the
                # agent calls ollama.com directly instead of through the dead proxy.
                child_env["OLLAMA_CLOUD_BASE_URL"] = "https://ollama.com/v1"
                child_env["OLLAMA_BASE_URL"] = "https://ollama.com/v1"
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid,
                    env=child_env,
                    cwd=self.workdir or None,
                )

                try:
                    stdout, stderr = proc.communicate(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Hermes timed out after %.0fs — killing process group",
                        self.timeout,
                    )
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                    proc.wait()
                    return {
                        "output": f"[ERROR: Hermes timed out after {self.timeout}s]",
                        "model_used": "unknown",
                        "harness_type": "hermes",
                        "elapsed_seconds": self.timeout,
                        "provider_error": False,
                        "timed_out": True,
                        "cost": 0.0,
                        "tokens": 0,
                    }

                elapsed = time.time() - start
                output = stdout.strip()
                clean_lines = [line for line in output.splitlines()
                                                if not line.startswith("Warning:")
                                                and not line.startswith("\u26a0")
                                                and not line.startswith("\U0001f916")
                                                and "AI Agent initialized" not in line
                                                and "\u26a1Some tools may not work" not in line
                                                and "Enabled toolset" not in line
                                                and "Loaded " not in line
                                                and "Final tool selection" not in line]
                output = "\n".join(clean_lines).strip()
                # Strip markdown code fences and formatting
                output = re.sub(r'```\w*\n?', '', output)
                output = re.sub(r'\*\*|__|\*|_', '', output).strip()
                # Strip Hermes reasoning box artifacts (┌─ Reasoning ─...┐)
                # that pollute the scored output in -Q / --safe-mode mode.
                output = re.sub(r'[┌┐└┘]', '', output)
                output = re.sub(r'─+', '', output)
                output = re.sub(r'\bReasoning\s*', '', output)
                output = re.sub(r'\n\s*\n\s*\n+', '\n\n', output).strip()

                # Generic fairness guard: if the agent exited 0 but produced
                # empty (or whitespace-only) content, the provider likely
                # returned an empty completion — common with reasoning models
                # (e.g. mimo-v2.5) that exhaust their output budget on hidden
                # reasoning and emit nothing. Treat it as retryable, exactly
                # like a 5xx/429, for EVERY model/provider — never score an
                # empty response as a legitimate 0.
                if not output and proc.returncode == 0:
                    if attempt < _MAX_RETRIES:
                        logger.info(
                            "Empty response (attempt %d/%d), retrying in %ds",
                            attempt + 1, _MAX_RETRIES + 1, _RETRY_DELAYS[attempt],
                        )
                        last_error = "empty response from provider"
                        time.sleep(_RETRY_DELAYS[attempt])
                        continue
                    logger.warning("Hermes returned empty output after %d attempts", _MAX_RETRIES + 1)
                    return {
                        "output": "",
                        "model_used": "unknown",
                        "harness_type": "hermes",
                        "elapsed_seconds": elapsed,
                        "provider_error": True,
                        "cost": 0.0,
                        "tokens": 0,
                    }

                if proc.returncode != 0:
                    error = stderr.strip() or "unknown error"
                    # Check if this is a transient provider error worth retrying
                    if attempt < _MAX_RETRIES and self._is_provider_error(error):
                        logger.info(
                            "Provider error (attempt %d/%d), retrying in %ds: %s",
                            attempt + 1, _MAX_RETRIES + 1, _RETRY_DELAYS[attempt], error[:200],
                        )
                        last_error = error
                        time.sleep(_RETRY_DELAYS[attempt])
                        continue
                    logger.warning(f"Hermes task failed (exit={proc.returncode}): {error}")
                    return {
                        "output": f"[ERROR: Hermes exited with code {proc.returncode}]",
                        "model_used": "unknown",
                        "harness_type": "hermes",
                        "elapsed_seconds": elapsed,
                        "provider_error": self._is_provider_error(error),
                        "cost": 0.0,
                        "tokens": 0,
                    }

                model_used = self._detect_model(stderr)
                # Parse token usage from verbose stderr and estimate cost
                tokens = self._parse_token_usage(stderr)
                cost = self._estimate_cost(tokens, model_used) if tokens else 0.0
                return {
                    "output": output,
                    "model_used": model_used,
                    "harness_type": "hermes",
                    "elapsed_seconds": elapsed,
                    "provider_error": False,
                    "cost": cost,
                    "tokens": tokens["total_tokens"] if tokens else 0,
                    "session_id": self._parse_session_id(stderr),
                }

            except FileNotFoundError:
                return {
                    "output": f"[ERROR: hermes binary not found at '{self.hermes_bin}']",
                    "model_used": "unknown",
                    "harness_type": "hermes",
                    "elapsed_seconds": 0,
                    "provider_error": False,
                    "cost": 0.0,
                    "tokens": 0,
                }

        # Exhausted retries
        return {
            "output": f"[ERROR: Provider error after {_MAX_RETRIES + 1} attempts: {last_error[:200]}]",
            "model_used": "unknown",
            "harness_type": "hermes",
            "elapsed_seconds": 0,
            "provider_error": True,
            "cost": 0.0,
            "tokens": 0,
        }

    def _detect_model(self, stderr: str = "") -> str:
        """Try to detect the current Hermes model from verbose stderr or config.

        Priority:
        1. Parse model=... from verbose stderr (most accurate — reflects what
           was actually used in the call)
        2. Run `hermes config show` and parse the model line
        3. Return "unknown"
        """
        # 1. Parse from verbose stderr: "model=deepseek-v4-flash"
        m = re.search(r"model=([\w.-]+)", stderr)
        if m:
            return m.group(1)
        # 2. Fallback: run hermes config show
        try:
            result = subprocess.run(
                [self.hermes_bin, "config", "show"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                # Look for the model line in the table output
                m = re.search(r"model[=:]\s*(\S+)", result.stdout, re.IGNORECASE)
                if m:
                    return m.group(1)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return "unknown"
