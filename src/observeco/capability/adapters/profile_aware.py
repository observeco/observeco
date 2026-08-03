"""Profile-aware benchmark adapter — loads agent SOUL.md and calls model API directly.

Tests agent quality (profile context + model) without going through the hermes CLI.
Bypasses the broken hermes routing (9router proxy) by calling the API directly,
but injects the agent's SOUL.md as a system prompt so the model responds within
the agent's identity and constraints.

Middle ground between DirectModelAdapter (no context) and HermesBenchmarkAdapter
(full CLI, broken routing).
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .direct_model import _resolve_provider

logger = logging.getLogger(__name__)

_SOUL_CACHE: dict[str, str] = {}


def _load_soul_md(agent_profile: str) -> str:
    """Load the agent's SOUL.md content, cached per profile name."""
    if agent_profile in _SOUL_CACHE:
        return _SOUL_CACHE[agent_profile]

    hermes_home = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
    candidates = [
        hermes_home / "profiles" / agent_profile / "SOUL.md",
        hermes_home / "SOUL.md",
    ]
    for p in candidates:
        if p.exists():
            text = p.read_text(errors="replace")
            # Truncate to ~6K chars to keep prompt manageable
            if len(text) > 6000:
                text = text[:6000] + "\n\n[... truncated for benchmark ...]"
            _SOUL_CACHE[agent_profile] = text
            return text

    _SOUL_CACHE[agent_profile] = ""
    return ""


class ProfileAwareAdapter:
    """Calls the model API directly but injects the agent's SOUL.md as system prompt.

    API call: system=SOUL.md + user=task prompt → model response.
    Uses the same urllib.request code path as DirectModelAdapter (reliable, no proxy).
    """

    def __init__(self, model_spec: str, timeout: int = 60, agent_profile: str = ""):
        self.model_spec = model_spec
        self.timeout = timeout
        self.agent_profile = agent_profile
        self._base_url, self._model_name, self._headers = _resolve_provider(model_spec)
        self._soul_md = _load_soul_md(agent_profile) if agent_profile else ""

    def run_task(self, agent_name: str, task: Any) -> dict[str, Any]:
        """Run a canary task with agent profile context injected as system prompt."""
        prompt = getattr(task, "input_text", "") or getattr(task, "prompt", "")
        if not prompt:
            return {
                "output": "",
                "model_used": self.model_spec,
                "harness_type": "profile-aware",
                "tokens": 0,
                "cost": 0.0,
                "timed_out": False,
                "error": "No prompt provided",
                "provider_error": False,
            }

        # Build messages: SOUL.md as system + task as user
        messages = []
        if self._soul_md:
            messages.append({"role": "system", "content": self._soul_md})
        messages.append({"role": "user", "content": prompt})

        url = f"{self._base_url}/chat/completions"
        body = json.dumps({
            "model": self._model_name,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 2048,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=self._headers, method="POST")

        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"] or ""
            elapsed = time.monotonic() - start

            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            prompt_tok = usage.get("prompt_tokens", 0)
            compl_tok = usage.get("completion_tokens", 0)

            # Rough cost estimate
            cost = (prompt_tok * 0.15 + compl_tok * 0.60) / 1_000_000

            return {
                "output": content.strip(),
                "model_used": self.model_spec,
                "harness_type": "profile-aware",
                "elapsed_seconds": elapsed,
                "tokens": total_tokens,
                "prompt_tokens": prompt_tok,
                "completion_tokens": compl_tok,
                "cost": round(cost, 6),
                "timed_out": False,
                "error": "",
                "provider_error": False,
            }

        except urllib.error.HTTPError as exc:
            elapsed = time.monotonic() - start
            status = exc.code
            is_provider = status in (429, 500, 502, 503, 504)
            return {
                "output": "",
                "model_used": self.model_spec,
                "harness_type": "profile-aware",
                "elapsed_seconds": elapsed,
                "tokens": 0,
                "cost": 0.0,
                "timed_out": False,
                "error": f"HTTP {status}",
                "provider_error": is_provider,
            }

        except urllib.error.URLError as exc:
            elapsed = time.monotonic() - start
            return {
                "output": "",
                "model_used": self.model_spec,
                "harness_type": "profile-aware",
                "elapsed_seconds": elapsed,
                "tokens": 0,
                "cost": 0.0,
                "timed_out": False,
                "error": f"Connection failed: {exc.reason}",
                "provider_error": True,
            }

        except Exception as exc:
            elapsed = time.monotonic() - start
            return {
                "output": "",
                "model_used": self.model_spec,
                "harness_type": "profile-aware",
                "elapsed_seconds": elapsed,
                "tokens": 0,
                "cost": 0.0,
                "timed_out": False,
                "error": str(exc),
                "provider_error": False,
            }
