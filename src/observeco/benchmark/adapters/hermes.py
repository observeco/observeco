"""Hermes harness adapter — runs benchmark tasks through a Hermes agent session.

ponytail: Uses subprocess to run a Hermes CLI command. This is the simplest
approach for v1 — it tests the agent through its actual CLI interface.
Upgrade path: use the Hermes API directly for faster execution and structured
output parsing.
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

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
                 agent_profile: str = "", model: str = ""):
        self.hermes_bin = hermes_bin
        self.timeout = timeout
        self.agent_profile = agent_profile
        # Model priority chain (first non-empty wins):
        #   1. Per-task model column (set in run_task)
        #   2. OBSERVECO_CANARY_MODEL env var (user-level default)
        #   3. Adapter constructor model param (code-level fallback)
        #   4. Hermes default (whatever `hermes config get model` returns)
        self.model = model

    def _is_provider_error(self, stderr: str) -> bool:
        """Check if stderr indicates a transient provider error (5xx/429)."""
        return bool(_PROVIDER_ERROR_RE.search(stderr or ""))

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
                if self.agent_profile:
                    cmd += ["-p", self.agent_profile]
                cmd += ["chat", "-q", prompt, "-Q"]
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
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid,
                    env=child_env,
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
                    }

                elapsed = time.time() - start
                output = stdout.strip()
                clean_lines = [l for l in output.splitlines()
                               if not l.startswith("Warning:")]
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
                    }

                model_used = self._detect_model()
                return {
                    "output": output,
                    "model_used": model_used,
                    "harness_type": "hermes",
                    "elapsed_seconds": elapsed,
                    "provider_error": False,
                }

            except FileNotFoundError:
                return {
                    "output": f"[ERROR: hermes binary not found at '{self.hermes_bin}']",
                    "model_used": "unknown",
                    "harness_type": "hermes",
                    "elapsed_seconds": 0,
                    "provider_error": False,
                }

        # Exhausted retries
        return {
            "output": f"[ERROR: Provider error after {_MAX_RETRIES + 1} attempts: {last_error[:200]}]",
            "model_used": "unknown",
            "harness_type": "hermes",
            "elapsed_seconds": 0,
            "provider_error": True,
        }

    def _detect_model(self) -> str:
        """Try to detect the current Hermes model from config."""
        try:
            result = subprocess.run(
                [self.hermes_bin, "config", "get", "model"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return "unknown"
