"""Load available models from hermes config for grid comparison.

Reads ~/.hermes/config.yaml to find configured providers and their models.
Returns a list of model specs in 'provider/model' format suitable for
DirectModelAdapter or ProfileAwareAdapter.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for loaded models
_model_cache: Optional[list[str]] = None

# Cache for API-fetched models
_api_model_cache: dict[str, list[str]] = {}


def _fetch_models_from_api(provider_name: str, base_url: str) -> list[str]:
    """Fetch available models from the provider's /v1/models endpoint.

    Caches results per provider to avoid repeated API calls.
    """
    if provider_name in _api_model_cache:
        return _api_model_cache[provider_name]

    try:
        # Get API key from env or hermes config
        import yaml
        api_key = ""
        config_path = Path.home() / '.hermes' / 'config.yaml'
        if config_path.exists():
            cfg = yaml.safe_load(open(config_path))
            provider_cfg = (cfg.get('providers', {}) or {}).get(provider_name, {})
            api_key = provider_cfg.get('api_key', '') or ''

        if not api_key:
            return []

        url = f"{base_url.rstrip('/')}/models"
        import urllib.request
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json
            data = json.loads(resp.read())
            models = [m['id'] for m in data.get('data', [])]

        _api_model_cache[provider_name] = models
        logger.info("Fetched %d models from %s API", len(models), provider_name)
        return models
    except Exception as e:
        logger.warning("Failed to fetch models from %s: %s", provider_name, e)
        return []


def load_available_models(provider_filter: Optional[str] = None) -> list[str]:
    """Load available models from hermes config.

    Args:
        provider_filter: If set, only return models from this provider
                        (e.g., 'ollama-cloud', 'deepseek').

    Returns:
        List of model specs in 'provider/model' format.
    """
    global _model_cache
    if _model_cache is not None and provider_filter is None:
        return _model_cache

    models = []
    config_path = Path.home() / '.hermes' / 'config.yaml'

    if not config_path.exists():
        logger.warning("Hermes config not found at %s", config_path)
        return _get_default_models()

    try:
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}

        providers = cfg.get('providers', {})
        for provider_name, provider_cfg in providers.items():
            if provider_filter and provider_name != provider_filter:
                continue

            base_url = provider_cfg.get('base_url', '')
            if not base_url:
                continue

            # Get models from provider config
            provider_models = provider_cfg.get('models', {})
            default_model = provider_cfg.get('default_model', '')

            # If no explicit models listed, try fetching from API
            if not provider_models:
                api_models = _fetch_models_from_api(provider_name, base_url)
                if api_models:
                    for model_name in api_models:
                        models.append(f"{provider_name}/{model_name}")
                    continue
                # Fallback to default model
                if default_model:
                    models.append(f"{provider_name}/{default_model}")
            else:
                # Add all listed models
                for model_name in provider_models.keys():
                    models.append(f"{provider_name}/{model_name}")

                # Add default model if not in list
                if default_model and default_model not in provider_models:
                    models.append(f"{provider_name}/{default_model}")

    except Exception as e:
        logger.warning("Failed to load hermes config: %s", e)
        return _get_default_models()

    # Filter out models from providers without base_url (like9router)
    models = [m for m in models if not m.startswith('9router/')]

    if not models:
        logger.warning("No models found in config, using defaults")
        return _get_default_models()

    if provider_filter is None:
        _model_cache = models

    return models


def _get_default_models() -> list[str]:
    """Fallback default models when config can't be read."""
    return [
        "ollama-cloud/deepseek-v4-flash",
        "ollama-cloud/deepseek-v4-pro",
    ]


def get_provider_models(provider_name: str) -> list[str]:
    """Get models from a specific provider.

    Args:
        provider_name: Provider to query (e.g., 'ollama-cloud').

    Returns:
        List of model specs for that provider.
    """
    return load_available_models(provider_filter=provider_name)


def get_default_grid_models() -> list[str]:
    """Get models for grid comparison — cloud providers only."""
    return load_available_models(provider_filter='ollama-cloud')


def load_available_profiles() -> list[str]:
    """Load available agent profiles from ~/.hermes/profiles/.

    Returns:
        List of profile names (directories under profiles/).
    """
    profiles_dir = Path.home() / '.hermes' / 'profiles'
    if not profiles_dir.exists() or not profiles_dir.is_dir():
        logger.warning("No hermes profiles directory found at %s", profiles_dir)
        return ["main", "accelerator"]

    profiles = []
    for entry in profiles_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith('.'):
            if (entry / 'SOUL.md').exists():
                profiles.append(entry.name)

    if not profiles:
        logger.warning("No valid profiles found, using defaults")
        return ["main", "accelerator"]

    return sorted(profiles)


def get_default_grid_profiles() -> list[str]:
    """Get the default agent profiles for a grid run."""
    profiles = load_available_profiles()
    priority = [p for p in ['main', 'accelerator', 'hound'] if p in profiles]
    rest = [p for p in profiles if p not in priority]
    return (priority + rest)[:3]
