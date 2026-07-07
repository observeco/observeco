"""Direct model adapter — calls a model's chat API directly for canary tasks.

Used by CapabilityGridRunner to run the same canary tasks across different
models without going through the agent harness. This isolates model capability
from harness quality.

Resolves model endpoints from Hermes config (providers section) or falls back
to environment variables (OPENAI_API_KEY, DEEPSEEK_API_KEY, etc.).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Provider resolution: (base_url_suffix, env_var_prefix)
# Each entry maps a provider key to its base URL path and env var name.
_PROVIDER_MAP: dict[str, tuple[str, str]] = {
    "deepseek": ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    "openai": ("https://api.openai.com", "OPENAI_API_KEY"),
    "anthropic": ("https://api.anthropic.com", "ANTHROPIC_API_KEY"),
    "ollama": ("http://localhost:11434", ""),  # no API key needed
    "custom-ollama": ("http://localhost:11434", ""),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}

# Default models per provider when none specified
_DEFAULT_MODELS: dict[str, str] = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "ollama": "deepseek-v4-flash",
    "custom-ollama": "deepseek-v4-flash",
}


def _load_hermes_config() -> dict:
    """Load Hermes config from standard locations."""
    candidates = [
        Path.home() / ".hermes" / "config.yaml",
        Path.home() / ".hermes" / "profiles" / "main" / "config.yaml",
    ]
    for path in candidates:
        if path.exists():
            try:
                import yaml
                with open(path) as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}


def _resolve_provider(model_spec: str) -> tuple[str, str, dict]:
    """Resolve a model spec like 'deepseek/deepseek-chat' to (base_url, model_name, headers).

    Args:
        model_spec: 'provider/model_name' or just 'model_name' (uses deepseek default).

    Returns:
        (base_url, model_name, headers_dict)
    """
    parts = model_spec.split("/", 1)
    if len(parts) == 2:
        provider_key = parts[0]
        model_name = parts[1]
    else:
        provider_key = "deepseek"
        model_name = parts[0]

    # Try Hermes config first
    cfg = _load_hermes_config()

    # Check custom_providers (Hermes v0.16+)
    for cp in cfg.get("custom_providers", []):
        if isinstance(cp, dict) and cp.get("name") == provider_key:
            base_url = (cp.get("base_url", "") or "").rstrip("/")
            api_key = cp.get("api_key", "") or ""
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            return base_url, model_name, headers

    # Check providers dict (Hermes v0.14)
    providers = cfg.get("providers", {})
    if isinstance(providers, dict) and provider_key in providers:
        prov_cfg = providers[provider_key]
        base_url = (prov_cfg.get("base_url", "") or "").rstrip("/")
        api_key = prov_cfg.get("api_key", "") or ""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        return base_url, model_name, headers

    # Fall back to built-in provider map
    if provider_key in _PROVIDER_MAP:
        base_url, env_var = _PROVIDER_MAP[provider_key]
        api_key = os.environ.get(env_var, "") if env_var else ""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        return base_url, model_name, headers

    # Last resort: assume OpenAI-compatible at localhost
    logger.warning("Unknown provider '%s', assuming OpenAI-compatible at localhost", provider_key)
    return "http://localhost:11434/v1", model_name, {
        "Content-Type": "application/json",
    }


class DirectModelAdapter:
    """Runs canary tasks by calling a model's chat API directly.

    This adapter bypasses the agent harness to measure raw model capability.
    Used by CapabilityGridRunner for model × config comparison.
    """

    def __init__(self, model_spec: str, timeout: int = 60):
        """Args:
            model_spec: 'provider/model_name' (e.g. 'deepseek/deepseek-chat').
            timeout: Per-request timeout in seconds.
        """
        self.model_spec = model_spec
        self.timeout = timeout
        self._base_url, self._model_name, self._headers = _resolve_provider(model_spec)

    def run_task(self, agent_name: str, task) -> dict:
        """Run a canary task through the model's chat API.

        Args:
            agent_name: Ignored (used for interface compatibility with CanaryRunner).
            task: A BenchmarkTask-like object with .input_text (the prompt).

        Returns:
            {output, model_used, harness_type, tokens?, cost?, timed_out?, error?, provider_error?}
        """
        prompt = getattr(task, "input_text", "")
        if not prompt:
            prompt = getattr(task, "prompt", "")

        if not prompt:
            return {
                "output": "",
                "model_used": self.model_spec,
                "harness_type": "direct",
                "tokens": 0,
                "cost": 0.0,
                "timed_out": False,
                "error": "No prompt provided",
                "provider_error": False,
            }

        url = f"{self._base_url}/chat/completions"
        body = json.dumps({
            "model": self._model_name,
            "messages": [{"role": "user", "content": prompt}],
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

            # Estimate tokens (rough: 4 chars ≈ 1 token)
            input_tokens = len(prompt) // 4
            output_tokens = len(content) // 4
            total_tokens = input_tokens + output_tokens

            # Estimate cost (rough: $0.15/M input, $0.60/M output for typical API)
            cost = (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000

            return {
                "output": content.strip(),
                "model_used": self.model_spec,
                "harness_type": "direct",
                "tokens": total_tokens,
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
                "harness_type": "direct",
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
                "harness_type": "direct",
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
                "harness_type": "direct",
                "tokens": 0,
                "cost": 0.0,
                "timed_out": False,
                "error": str(exc),
                "provider_error": False,
            }
