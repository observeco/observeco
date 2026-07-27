"""Provider config registry — detect AI tool configs and generate wiring instructions.

Scans known config file locations for Hermes, OpenClaw, LangChain, and raw SDK configs.
Reports what's configured and generates instructions for proxy wiring.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProviderEntry:
    """A detected provider configuration."""
    tool: str           # hermes, openclaw, langchain, etc.
    provider: str       # openai, anthropic, etc.
    base_url: str       # current base URL
    config_path: str    # path to config file
    is_local: bool      # True if localhost/ollama (auto-detected or user-overridden)
    needs_proxy: bool   # True if should be routed through proxy
    local_override: bool | None = None  # user-set `local:` field; wins over auto-detection


@dataclass
class WiringInstruction:
    """Instruction for wiring a tool through the proxy."""
    tool: str
    config_path: str
    action: str         # "update_base_url" or "add_callback"
    current_value: str
    new_value: str
    notes: str = ""


# Known config file locations
def _get_config_registry() -> dict[str, list[dict]]:
    """Build config registry with paths resolved via dirs."""
    from observeco.dirs import hermes_home, openclaw_home

    hh = hermes_home()
    oh = openclaw_home()
    return {
        "hermes": [
            {
                "path": str(hh / "config.yaml") if hh else "~/.hermes/config.yaml",
                "format": "yaml",
                "description": "Hermes Agent main config",
            },
        ],
        "openclaw": [
            {
                "path": str(oh / "config.json") if oh else "~/.openclaw/config.json",
                "format": "json",
                "description": "OpenClaw agent config",
            },
        ],
    "langchain": [
        {
            "path": "~/.langchain/config.yaml",
            "format": "yaml",
            "description": "LangChain config",
        },
    ],
    "litellm": [
        {
            "path": "~/.litellm_config.yaml",
            "format": "yaml",
            "description": "LiteLLM proxy config",
        },
        {
            "path": "litellm_config.yaml",
            "format": "yaml",
            "description": "LiteLLM config (current dir)",
        },
    ],
}

# Localhost patterns — never proxy these (unless track_local is enabled)
LOCALHOST_PATTERNS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "ollama",
    "llama.cpp",
    "vllm",
    "text-generation-inference",
    "http://localhost",
    "http://127.0.0.1",
]

# Global toggle: when True, _is_local() returns False so local providers get proxied
_track_local_enabled = False


def set_track_local(enabled: bool = True):
    """Enable or disable local LLM tracking through the proxy.

    When enabled, _is_local() returns False for localhost URLs,
    so the SDK auto-config routes local providers through the proxy.
    """
    global _track_local_enabled
    _track_local_enabled = enabled


def is_track_local() -> bool:
    """Check if local LLM tracking is enabled."""
    return _track_local_enabled


def _is_local(base_url: str) -> bool:
    """Check if a base URL points to a local service.

    When track_local is enabled, returns False for all URLs
    so local providers get routed through the proxy.
    """
    if _track_local_enabled:
        return False
    url_lower = base_url.lower()
    return any(p in url_lower for p in LOCALHOST_PATTERNS)


def _parse_yaml_config(path: Path) -> dict:
    """Parse a YAML config file."""
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _parse_json_config(path: Path) -> dict:
    """Parse a JSON config file."""
    try:
        import json
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _extract_providers_hermes(config: dict, path: str) -> list[ProviderEntry]:
    """Extract provider entries from Hermes config."""
    entries = []
    providers = config.get("providers", {})

    for prov_name, prov_config in providers.items():
        if isinstance(prov_config, dict):
            base_url = prov_config.get("base_url", "")
            if base_url:
                is_local = _is_local(base_url)
                # User override: `local: false` in config wins over auto-detection
                local_override = prov_config.get("local")
                if local_override is not None:
                    is_local = bool(local_override)
                entries.append(ProviderEntry(
                    tool="hermes",
                    provider=prov_name,
                    base_url=base_url,
                    config_path=path,
                    is_local=is_local,
                    needs_proxy=not is_local,
                    local_override=local_override,
                ))

    return entries


def _extract_providers_openclaw(config: dict, path: str) -> list[ProviderEntry]:
    """Extract provider entries from OpenClaw config."""
    entries = []
    providers = config.get("providers", {})

    for prov_name, prov_config in providers.items():
        if isinstance(prov_config, dict):
            base_url = prov_config.get("base_url", "")
            if base_url:
                is_local = _is_local(base_url)
                local_override = prov_config.get("local")
                if local_override is not None:
                    is_local = bool(local_override)
                entries.append(ProviderEntry(
                    tool="openclaw",
                    provider=prov_name,
                    base_url=base_url,
                    config_path=path,
                    is_local=is_local,
                    needs_proxy=not is_local,
                    local_override=local_override,
                ))

    return entries


def detect_provider_configs() -> list[ProviderEntry]:
    """Scan all known config files and extract provider configurations."""
    entries = []

    for tool_name, configs in _get_config_registry().items():
        for cfg in configs:
            path = Path(os.path.expanduser(cfg["path"]))
            if not path.exists():
                continue

            config = {}
            if cfg["format"] == "yaml":
                config = _parse_yaml_config(path)
            elif cfg["format"] == "json":
                config = _parse_json_config(path)

            if not config:
                continue

            # Extract providers based on tool
            if tool_name == "hermes":
                entries.extend(_extract_providers_hermes(config, str(path)))
            elif tool_name == "openclaw":
                entries.extend(_extract_providers_openclaw(config, str(path)))

    return entries


def generate_wiring_instructions(
    proxy_url: str = "http://localhost:9200/v1",
    entries: Optional[list[ProviderEntry]] = None,
) -> list[WiringInstruction]:
    """Generate wiring instructions for detected providers.

    Only generates instructions for remote providers (not local).
    """
    if entries is None:
        entries = detect_provider_configs()

    instructions = []
    for entry in entries:
        if not entry.needs_proxy:
            continue

        instructions.append(WiringInstruction(
            tool=entry.tool,
            config_path=entry.config_path,
            action="update_base_url",
            current_value=entry.base_url,
            new_value=proxy_url,
            notes=f"Route {entry.provider} through proxy for real token tracking",
        ))

    return instructions


def detect_and_report() -> dict:
    """Detect configs and return a full report."""
    entries = detect_provider_configs()
    instructions = generate_wiring_instructions(entries=entries)

    return {
        "providers": [
            {
                "tool": e.tool,
                "provider": e.provider,
                "base_url": e.base_url,
                "config_path": e.config_path,
                "is_local": e.is_local,
                "needs_proxy": e.needs_proxy,
            }
            for e in entries
        ],
        "instructions": [
            {
                "tool": i.tool,
                "config_path": i.config_path,
                "action": i.action,
                "current": i.current_value,
                "new": i.new_value,
                "notes": i.notes,
            }
            for i in instructions
        ],
        "total_providers": len(entries),
        "need_proxy": sum(1 for e in entries if e.needs_proxy),
        "local": sum(1 for e in entries if e.is_local),
    }
