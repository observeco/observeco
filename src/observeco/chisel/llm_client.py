"""
LLM Provider Abstraction for Chisel Compression.

Supports: DeepSeek, OpenAI, Anthropic, Google, Ollama, Hermes, Lite (no LLM).
Auto-detects available providers with configurable fallback chain.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from observeco.dirs import hermes_home

# ── Provider Defaults ──────────────────────────────────────────────────────────

PROVIDER_DEFAULTS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.05,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "max_tokens": 4096,
        "temperature": 0.05,
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-haiku-20240307",
        "max_tokens": 4096,
        "temperature": 0.05,
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-2.0-flash",
        "max_tokens": 4096,
        "temperature": 0.05,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1",
        "max_tokens": 4096,
        "temperature": 0.1,
    },
    "hermes": {
        "base_url": "http://localhost:8080",
        "model": "default",
        "max_tokens": 4096,
        "temperature": 0.05,
    },
}


# ── API Key Readers ────────────────────────────────────────────────────────────

def _read_env_key(env_name: str) -> str:
    """Read API key from environment variable."""
    return os.environ.get(env_name, "").strip().strip("\"'").strip()


def _read_hermes_env_key(provider: str) -> str:
    """Read API key from Hermes .env file."""
    hh = hermes_home()
    if hh is None:
        return ""
    env_path = hh / ".env"
    if not env_path.exists():
        return ""
    prefix = f"{provider.upper()}_API_KEY="
    for line in env_path.read_text().splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip().strip("\"'").strip()
    return ""


def _read_hermes_config_key(provider: str) -> str:
    """Read API key from Hermes config.yaml."""
    import yaml
    hh = hermes_home()
    if hh is None:
        return ""
    cfg_path = hh / "config.yaml"
    if not cfg_path.exists():
        return ""
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg_key = cfg.get("providers", {}).get(provider, {}).get("api_key", "")
    if cfg_key and "..." not in cfg_key:
        return cfg_key
    return ""


def get_api_key(provider: str) -> str:
    """Get API key for a provider. Checks BYOK, env, .env file, config.yaml."""
    # BYOK: user's own API key (primary path for free tier)
    byok = os.environ.get("OBSERVECO_LLM_API_KEY", "")
    if byok:
        return byok
    env_name = f"{provider.upper()}_API_KEY"
    key = _read_env_key(env_name)
    if key:
        return key
    key = _read_hermes_env_key(provider)
    if key:
        return key
    key = _read_hermes_config_key(provider)
    if key:
        return key
    return ""


# ── Provider Clients ───────────────────────────────────────────────────────────

class LLMClient:
    """Base LLM client with OpenAI-compatible API support."""

    def __init__(self, provider: str, config: dict):
        self.provider = provider
        self.config = {**PROVIDER_DEFAULTS.get(provider, {}), **config}
        self.base_url = self.config["base_url"]
        self.model = self.config["model"]
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.05)

    def complete(self, prompt: str, system: str = "") -> str:
        """Send prompt to LLM, return response text."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())

        return result["choices"][0]["message"]["content"].strip()

    @property
    def api_key(self) -> str:
        return get_api_key(self.provider)

    def is_available(self) -> bool:
        """Check if provider is reachable and configured."""
        if not self.api_key:
            return False
        try:
            # Quick connectivity check
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False


class AnthropicClient(LLMClient):
    """Anthropic Messages API client (different format from OpenAI)."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Anthropic Messages API format."""
        payload_data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload_data["system"] = system

        payload = json.dumps(payload_data).encode()

        req = urllib.request.Request(
            f"{self.base_url}/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())

        # Extract text from content blocks
        content = result.get("content", [])
        return "".join(block.get("text", "") for block in content).strip()

    def is_available(self) -> bool:
        """Check if Anthropic is configured (skip connectivity check)."""
        return bool(self.api_key)


class GoogleClient(LLMClient):
    """Google Generative Language API client."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Google API format."""
        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = json.dumps({
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }).encode()

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())

        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(part.get("text", "") for part in parts).strip()
        return ""

    def is_available(self) -> bool:
        """Check if Google API key is configured."""
        return bool(self.api_key)


class OllamaClient(LLMClient):
    """Ollama local API client."""

    def __init__(self, config: dict):
        super().__init__("ollama", config)
        # Ollama uses port 11434, not 11434/v1
        if "localhost:11434/v1" in self.base_url:
            self.base_url = "http://localhost:11434"

    def is_available(self) -> bool:
        """Check if Ollama is running locally."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False


class HermesClient(LLMClient):
    """Delegate compression to Hermes agent."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Send compression task to Hermes."""
        # Hermes expects a specific task format
        task = f"Compress this text using caveman compression:\n\n{prompt}"
        payload = json.dumps({
            "task": task,
            "system": system,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/compress",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode())

        return result.get("compressed", "")

    def is_available(self) -> bool:
        """Check if Hermes is running."""
        try:
            req = urllib.request.Request(f"{self.base_url}/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False


class LiteClient(LLMClient):
    """No-LLM fallback — returns empty string (triggers regex-only compression)."""

    def __init__(self, provider: str = "lite", config: Optional[dict] = None):
        # Skip parent __init__ since we don't need API keys
        self.provider = provider
        self.config = config or {}
        self.base_url = ""
        self.model = "none"
        self.max_tokens = 0
        self.temperature = 0

    def complete(self, prompt: str, system: str = "") -> str:
        """No LLM available — return empty to trigger Lite mode."""
        return ""

    def is_available(self) -> bool:
        """Always available as fallback."""
        return True


# ── Client Factory ─────────────────────────────────────────────────────────────

CLIENT_CLASSES = {
    "deepseek": LLMClient,
    "openai": LLMClient,
    "anthropic": AnthropicClient,
    "google": GoogleClient,
    "ollama": OllamaClient,
    "hermes": HermesClient,
    "lite": LiteClient,
}


def get_client(
    provider: str = "auto",
    model: str = "default",
    config: Optional[dict] = None,
) -> LLMClient:
    """Get an LLM client for the specified provider.

    Args:
        provider: Provider name or "auto" for auto-detection
        model: Model name or "default" for provider default
        config: Additional config overrides

    Returns:
        Configured LLMClient instance

    Raises:
        ValueError: If provider is unknown or unavailable
    """
    config = config or {}

    if provider == "auto":
        return _auto_detect(config)

    if provider not in CLIENT_CLASSES:
        raise ValueError(f"Unknown provider: {provider}. Choose from: {list(CLIENT_CLASSES.keys())}")

    client_class = CLIENT_CLASSES[provider]
    client = client_class(provider, config)

    if not client.is_available():
        raise ValueError(f"Provider '{provider}' is not available (check API key or connectivity)")

    return client


def _auto_detect(config: dict) -> LLMClient:
    """Auto-detect available provider with fallback chain.

    Chain: Hermes → Ollama → DeepSeek → OpenAI → Anthropic → Google → Lite
    """
    detection_order = ["hermes", "ollama", "deepseek", "openai", "anthropic", "google"]

    for provider in detection_order:
        try:
            client_class = CLIENT_CLASSES[provider]
            client = client_class(provider, config)
            if client.is_available():
                return client
        except Exception:
            continue

    # Fallback to Lite mode
    return LiteClient("lite", config)


def list_providers() -> list[dict]:
    """List all providers with availability status."""
    providers = []
    for name, client_class in CLIENT_CLASSES.items():
        if name == "lite":
            providers.append({
                "name": name,
                "available": True,
                "model": "none",
                "description": "No LLM — regex-only compression",
            })
            continue

        try:
            client = client_class(name, {})
            providers.append({
                "name": name,
                "available": client.is_available(),
                "model": client.model,
                "description": f"{name.title()} API",
            })
        except Exception:
            providers.append({
                "name": name,
                "available": False,
                "model": PROVIDER_DEFAULTS.get(name, {}).get("model", "unknown"),
                "description": f"{name.title()} API",
            })

    return providers
