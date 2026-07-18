"""Direct model adapter for lm-eval-harness — bypasses agent harness.

Calls the model's provider API directly (no hermes chat wrapper) to establish
a true ceiling for comparison against agent-harnessed benchmarks.

ponytail: No logprob access from these APIs.
  - ``loglikelihood`` uses generate-then-compare heuristic (same as agent adapter).
  - ``loglikelihood_rolling`` returns 0.0.
  Upgrade path: use local model (llama.cpp) for real token-level logprobs.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None

from lm_eval.api.instance import Instance
from lm_eval.api.model import LM

logger = logging.getLogger(__name__)

# ── Provider resolution ────────────────────────────────────────────────────

def _load_hermes_config() -> dict:
    config_path = Path.home() / ".hermes" / "config.yaml"
    if not config_path.exists():
        return {}
    if yaml is None:
        return {}
    with open(config_path) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg


def _resolve_api(model_spec: str) -> tuple[str, str, dict]:
    """Resolve ``provider/model_name`` to (base_url, model_name, headers).

    Returns headers dict with Authorization and Content-Type set.
    """
    parts = model_spec.split("/", 1)
    provider_key = parts[0] if len(parts) == 2 else "deepseek"
    model_name = parts[1] if len(parts) == 2 else parts[0]

    cfg = _load_hermes_config()
    providers = cfg.get("providers", {})
    prov_cfg = providers.get(provider_key, {})

    base_url = (prov_cfg.get("base_url", "") or "").rstrip("/")
    api_key = prov_cfg.get("api_key", "") or os.environ.get(
        f"{provider_key.upper()}_API_KEY",
        os.environ.get("OPENAI_API_KEY", ""),
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    return base_url, model_name, headers


# ── Adapter ─────────────────────────────────────────────────────────────────

class DirectModelLM(LM):
    """Routes lm-eval tasks directly through a model provider API (no agent harness)."""

    def __init__(
        self,
        model_spec: str,
        timeout: float = 120,
        system_prompt: str = "",
    ) -> None:
        super().__init__()
        self.model_spec = model_spec
        self.timeout = timeout
        self._base_url, self._model_name, self._headers = _resolve_api(model_spec)
        self.system_prompt = system_prompt
        self._context_cache: dict[str, str] = {}

    @property
    def model_name_display(self) -> str:
        return f"direct:{self.model_spec}"

    # ── Core lm-eval interface ─────────────────────────────────────────────

    def generate_until(self, requests: list[Instance]) -> list[str]:
        results: list[str] = []
        for req in requests:
            context, gen_kwargs = req.args
            output = self._chat(context)
            until = gen_kwargs.get("until", [])
            if until:
                output = self._trim_until(output, until)
            results.append(output)
        return results

    def loglikelihood(self, requests: list[Instance]) -> list[tuple[float, bool]]:
        results: list[tuple[float, bool]] = []
        for req in requests:
            context, continuation = req.args
            if context not in self._context_cache:
                self._context_cache[context] = self._chat(context)
            generated = self._context_cache[context]
            logprob, is_greedy = self._score_continuation(continuation, generated)
            results.append((logprob, is_greedy))
        return results

    def loglikelihood_rolling(self, requests: list[Instance]) -> list[float]:
        return [0.0] * len(requests)

    # ── API call (stdlib urllib — no deps) ─────────────────────────────────

    def _chat(self, prompt: str) -> str:
        """Send prompt to model's /v1/chat/completions endpoint."""
        url = f"{self._base_url}/chat/completions"
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": self._model_name,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 1024,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=self._headers, method="POST")

        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"] or ""
            elapsed = time.monotonic() - start
            logger.debug("direct call: %.1fs, %d chars", elapsed, len(content))
            return content.strip()
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("direct call failed (%.1fs): %s", elapsed, exc)
            return ""

    # ── Scoring heuristic ──────────────────────────────────────────────────

    @staticmethod
    def _score_continuation(
        continuation: str, generated: str
    ) -> tuple[float, bool]:
        gen_stripped = generated.strip().lower()
        cont_stripped = continuation.strip().lower()

        if not gen_stripped:
            return (-10.0, False)
        if gen_stripped == cont_stripped:
            return (-0.105, True)
        elif gen_stripped.startswith(cont_stripped):
            return (-0.223, True)
        elif cont_stripped in gen_stripped:
            return (-1.609, False)
        else:
            return (-10.0, False)

    @staticmethod
    def _trim_until(output: str, until: list[str]) -> str:
        for seq in until:
            idx = output.find(seq)
            if idx != -1:
                return output[:idx].strip()
        return output
