"""SWE-bench adapter: routes code patch generation through Hermes agent harness.

Each SWE-bench issue: agent reads the issue description + repo code, generates
a patch, and the harness applies it and runs the test suite.

ponytail: Sequential issue processing. No parallel Docker builds.
Upgrade path: concurrent issue processing with worker pool.
"""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import time
from typing import Any, Optional

from .configs import HarnessConfig

logger = logging.getLogger(__name__)


class HermesSWEAgent:
    """SWE-bench agent that routes patch generation through Hermes agent harness.

    For each issue:
    1. Read issue description + repo code
    2. Call Hermes to generate a patch
    3. Return the patch for SWE-bench evaluation
    """

    def __init__(
        self,
        harness_config: HarnessConfig,
        hermes_bin: str = "hermes",
    ) -> None:
        self.config = harness_config
        self.hermes_bin = hermes_bin

        # Metrics
        self.call_count = 0
        self.timeout_count = 0
        self.retry_count = 0
        self.total_call_time = 0.0

    def generate_patch(
        self,
        issue_text: str,
        repo_name: str,
        base_commit: str,
        repo_structure: Optional[str] = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generate a patch for a SWE-bench issue.

        Returns (patch_text, metrics_dict).
        """
        prompt = self._build_prompt(issue_text, repo_name, repo_structure)
        response, metrics = self._call_hermes(prompt)
        self.call_count += metrics["call_count"]
        self.timeout_count += metrics["timeout_count"]
        self.retry_count += metrics["retry_count"]
        self.total_call_time += metrics["total_time"]

        # Extract patch from response
        patch = self._extract_patch(response)
        return patch, metrics

    def _build_prompt(
        self,
        issue_text: str,
        repo_name: str,
        repo_structure: Optional[str] = None,
    ) -> str:
        """Build the prompt for patch generation."""
        parts = [
            f"You are fixing a bug in the repository: {repo_name}",
            "",
            "## Issue Description",
            issue_text,
            "",
        ]

        if repo_structure:
            parts.extend([
                "## Repository Structure",
                repo_structure,
                "",
            ])

        parts.extend([
            "## Instructions",
            "Read the issue carefully. Understand the bug and the expected behavior.",
            "Generate a patch (diff) that fixes the issue.",
            "The patch must be in unified diff format (git diff format).",
            "Only include the minimal changes needed to fix the issue.",
            "Do NOT add any explanation outside the patch.",
            "Start the patch with: ```diff",
            "End the patch with: ```",
        ])

        return "\n".join(parts)

    def _call_hermes(self, prompt: str) -> tuple[str, dict[str, Any]]:
        """Call Hermes agent with retry logic."""
        timeout_count = 0
        retry_count = 0
        total_time = 0.0
        call_count = 0

        for attempt in range(self.config.max_retries + 1):
            call_count += 1
            start = time.time()

            try:
                proc = subprocess.Popen(
                    [self.hermes_bin, "chat", "-q", prompt, "-Q"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid,
                )

                try:
                    stdout, stderr = proc.communicate(
                        timeout=self.config.call_timeout_seconds
                    )
                except subprocess.TimeoutExpired:
                    timeout_count += 1
                    logger.warning(
                        "SWE Hermes timed out after %.0fs (attempt %d/%d)",
                        self.config.call_timeout_seconds,
                        attempt + 1,
                        self.config.max_retries + 1,
                    )
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                    proc.wait()

                    if attempt < self.config.max_retries:
                        retry_count += 1
                        time.sleep(self.config.retry_delay_seconds)
                        continue
                    return (
                        f"[ERROR: timeout after {self.config.call_timeout_seconds:.0f}s]",
                        {
                            "call_count": call_count,
                            "timeout_count": timeout_count,
                            "retry_count": retry_count,
                            "total_time": total_time,
                        },
                    )

                elapsed = time.time() - start
                total_time += elapsed

                output = stdout.strip()

                # Strip Hermes warning/status lines
                output = "\n".join(
                    line
                    for line in output.splitlines()
                    if not line.startswith("Warning:")
                    and not line.startswith("session_id:")
                ).strip()

                if proc.returncode != 0:
                    error = stderr.strip() or "unknown error"
                    logger.warning(
                        "SWE Hermes failed (exit=%d): %s", proc.returncode, error
                    )
                    if attempt < self.config.max_retries:
                        retry_count += 1
                        time.sleep(self.config.retry_delay_seconds)
                        continue
                    output = f"[ERROR: exit={proc.returncode}]"

                return output, {
                    "call_count": call_count,
                    "timeout_count": timeout_count,
                    "retry_count": retry_count,
                    "total_time": total_time,
                }

            except FileNotFoundError:
                return (
                    f"[ERROR: {self.hermes_bin} not found]",
                    {
                        "call_count": call_count,
                        "timeout_count": timeout_count,
                        "retry_count": retry_count,
                        "total_time": total_time,
                    },
                )

            except Exception as exc:
                logger.error("SWE Hermes call failed: %s", exc)
                if attempt < self.config.max_retries:
                    retry_count += 1
                    time.sleep(self.config.retry_delay_seconds)
                    continue
                return (
                    f"[ERROR: {exc}]",
                    {
                        "call_count": call_count,
                        "timeout_count": timeout_count,
                        "retry_count": retry_count,
                        "total_time": total_time,
                    },
                )

        return (
            "[ERROR: max retries exceeded]",
            {
                "call_count": call_count,
                "timeout_count": timeout_count,
                "retry_count": retry_count,
                "total_time": total_time,
            },
        )

    @staticmethod
    def _extract_patch(response: str) -> str:
        """Extract the diff patch from Hermes response."""
        # Try to find diff in code blocks
        diff_match = re.search(
            r"```(?:diff)?\n(.*?)```", response, re.DOTALL
        )
        if diff_match:
            return diff_match.group(1).strip()

        # Try to find lines starting with +/-
        diff_lines = [
            line for line in response.splitlines()
            if line.startswith("---") or line.startswith("+++")
            or line.startswith("@@")
            or line.startswith("+")
            or line.startswith("-")
            or line.startswith(" ")
        ]
        if diff_lines:
            return "\n".join(diff_lines)

        return response.strip()
