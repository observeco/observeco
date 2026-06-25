"""Shared LLM service — extracted from doctor/llm.py.

Every ObserveCo module calls this for deeper diagnosis, alert enrichment,
personalized guidance, and per-agent summaries. Three tiers:

- Tier 1 (deep, mission-critical): agent discovery, first-run wizard, heal escalation
- Tier 2 (shallow, value-add): alert enrichment, per-agent summary, health check
  suggestion, heal feedback, pathway anomaly, error translation

BYOK model:         OBSERVECO_LLM_API_KEY set → full LLM (user's own key)
                    no key configured → static fallback only
                    --no-llm → opt-out, always static
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

from observeco.llm_service.cache import LLMCache
from observeco.llm_service.cost_tracker import CostTracker
from observeco.llm_service.gate import LLMGate, get_self_monitor

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_cache = LLMCache()
_cost = CostTracker()
_gate = LLMGate()


def ask(
    system_prompt: str,
    user_context: str,
    *,
    consumer: str = "generic",
    max_cost_cents: float = 0.02,
    cache_ttl_secs: int = 300,
    tier: int = 1,
) -> str | None:
    """Core LLM call — cached, cost-tracked, gated.

    Args:
        system_prompt: System-level instructions for the LLM.
        user_context: The context/data the LLM should analyse.
        consumer: Name of the consumer module (for cost tracking).
        max_cost_cents: Maximum cost for this call before fallback.
        cache_ttl_secs: How long to cache this response.
        tier: 1 (deep/mission-critical) or 2 (shallow/value-add).

    Returns:
        LLM response text, or None if gated/failed/budget-exhausted.
    """
    if not _gate.should_call(consumer=consumer, tier=tier):
        return None

    # Check cache first
    cache_key = _build_cache_key(system_prompt, user_context)
    cached = _cache.get(cache_key, max_age_secs=cache_ttl_secs)
    if cached is not None:
        return cached

    # Detect provider
    provider = get_auto_provider()
    if not provider:
        return None

    # Check budget
    if not _cost.would_accept(consumer, max_cost_cents):
        return None

    # Make the call
    start = time.monotonic()
    response = _call_provider(provider, system_prompt, user_context)
    duration = time.monotonic() - start

    if response is None:
        return None

    # Track cost (estimated)
    input_tokens = _estimate_tokens(system_prompt + user_context)
    output_tokens = _estimate_tokens(response)
    _cost.record(
        consumer=consumer,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider=provider.name,
        duration_sec=duration,
    )

    # Track self-monitoring budget (G1.1)
    get_self_monitor().record(consumer, input_tokens, output_tokens)

    # Cache it
    _cache.set(cache_key, response)
    return response


def detect_providers() -> list[LLMProvider]:
    """Detect available LLM providers from environment. (Externally callable.)"""
    return _detect_llm_providers()


def get_auto_provider() -> Optional[LLMProvider]:
    """Auto-detect the best available provider. (Externally callable.)"""
    return _get_auto_provider(_detect_llm_providers())


def clear_cache() -> None:
    """Clear the LLM response cache."""
    _cache.clear()


def budget_remaining() -> float:
    """Return today's remaining budget in cents."""
    return _cost.remaining()


def cost_summary() -> dict:
    """Return today's cost summary for dashboard display."""
    return _cost.summary()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LLMProvider:
    name: str
    available: bool = False
    api_key: str = ""


# ---------------------------------------------------------------------------
# Internal helpers (moved from doctor/llm.py)
# ---------------------------------------------------------------------------

def _build_cache_key(system_prompt: str, user_context: str) -> str:
    raw = system_prompt + user_context
    return hashlib.sha256(raw.encode()).hexdigest()


def _estimate_tokens(text: str) -> int:
    """Rough token estimation (~4 chars per token)."""
    return len(text) // 4


def _detect_llm_providers() -> list[LLMProvider]:
    """Detect available LLM providers from environment.

    Checks 20+ provider env vars plus local LLM servers.
    Primary BYOK path: OBSERVECO_LLM_API_KEY (user's own key, OpenAI-compatible).
    """
    providers = []
    seen_providers = set()

    # --- BYOK: user's own API key (primary path for free tier) ---
    byok_key = os.environ.get("OBSERVECO_LLM_API_KEY", "")
    if byok_key and "byok" not in seen_providers:
        providers.append(LLMProvider(name="byok", available=True, api_key=byok_key))
        seen_providers.add("byok")

    # --- Major providers (env vars) ---
    env_providers = [
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("google", "GOOGLE_API_KEY"),
        ("deepseek", "DEEPSEEK_API_KEY"),
        ("mistral", "MISTRAL_API_KEY"),
        ("groq", "GROQ_API_KEY"),
        ("together", "TOGETHER_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
    ]

    for provider_name, env_var in env_providers:
        key = os.environ.get(env_var, "")
        if key and provider_name not in seen_providers:
            providers.append(LLMProvider(name=provider_name, available=True, api_key=key))
            seen_providers.add(provider_name)

    # --- Check OpenRouter (uses OPENAI_API_KEY sometimes) ---
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key and "openai" not in seen_providers:
        if openai_key.startswith("sk-or-"):
            providers.append(LLMProvider(name="openrouter", available=True, api_key=openai_key))
            seen_providers.add("openrouter")

    # --- Local LLM servers (from DB registry) ---
    try:
        from observeco.db import Database
        _db = Database()
        _registry = _db.get_provider_registry()
        _db.close()
        local_providers = [p for p in _registry if p["provider_type"] == "local" and p["detect_endpoint"]]
    except Exception:
        local_providers = []

    for prov in local_providers:
        name = prov["name"]
        if name in seen_providers:
            continue
        try:
            import urllib.request
            urllib.request.urlopen(prov["detect_endpoint"], timeout=prov.get("detect_timeout", 2))
            providers.append(LLMProvider(name=name, available=True))
            seen_providers.add(name)
        except Exception:
            pass

    return providers


def _get_auto_provider(providers: list[LLMProvider]) -> Optional[LLMProvider]:
    """Auto-detect the best available provider.
    Uses DB registry priority ordering (higher = preferred).
    """
    # Build priority map from registry
    try:
        from observeco.db import Database
        _db = Database()
        _registry = _db.get_provider_registry()
        _db.close()
        priority_map = {p["name"]: p["priority"] for p in _registry}
    except Exception:
        priority_map = {}

    # Sort available providers by registry priority (descending)
    available = [p for p in providers if p.available]
    available.sort(key=lambda p: priority_map.get(p.name, 0), reverse=True)
    return available[0] if available else None


def _call_provider(provider: LLMProvider, system: str, prompt: str) -> str | None:
    """Route to the correct provider API using DB registry config."""
    # Look up provider config from registry
    try:
        from observeco.db import Database
        _db = Database()
        _config = _db.get_provider_config(provider.name)
        _db.close()
    except Exception:
        _config = None

    api_format = _config["api_format"] if _config else provider.name
    base_url = _config["base_url"] if _config else None
    model = _config["default_model"] if _config else "default"

    try:
        if api_format == "anthropic":
            return _call_anthropic(provider.api_key, system, prompt)
        elif api_format == "google":
            return _call_google(provider.api_key, system, prompt)
        elif api_format == "ollama":
            return _call_ollama(system, prompt)
        elif api_format == "openai" and base_url:
            return _call_openai_compatible(
                provider.api_key or "", system, prompt,
                base_url=base_url,
                model=model,
            )
        elif api_format == "openai":
            # Fallback for known providers without registry entry
            return _call_openai(provider.api_key, system, prompt)
        else:
            return None
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        return None


def _call_anthropic(api_key: str, system: str, prompt: str) -> str:
    import urllib.request
    data = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["content"][0]["text"]


def _call_openai(api_key: str, system: str, prompt: str) -> str:
    import urllib.request
    data = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


def _call_google(api_key: str, system: str, prompt: str) -> str:
    import urllib.request
    data = json.dumps({
        "contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
    }).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(system: str, prompt: str) -> str:
    import urllib.request
    data = json.dumps({
        "model": "llama3.1",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result["message"]["content"]


def _call_openai_compatible(api_key: str, system: str, prompt: str,
                             base_url: str, model: str) -> str:
    import urllib.request
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions" if "/v1" not in base_url else f"{base_url.rstrip('/')}/chat/completions",
        data=data,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


# Legacy alias — doctor/llm.py will re-import these
diagnose_with_llm = ask
