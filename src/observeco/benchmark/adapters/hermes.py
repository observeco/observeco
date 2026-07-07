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


class HermesBenchmarkAdapter:
    """Runs benchmark tasks through a Hermes agent session."""

    def __init__(self, hermes_bin: str = "hermes", timeout: int = 60,
                 agent_profile: str = ""):
        self.hermes_bin = hermes_bin
        self.timeout = timeout
        self.agent_profile = agent_profile

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
                if self.agent_profile:
                    cmd += ["-p", self.agent_profile]
                cmd += ["chat", "-q", prompt, "-Q", "--safe-mode"]
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
