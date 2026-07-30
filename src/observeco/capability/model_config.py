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

            # If no explicit models listed, use default model
            if not provider_models and default_model:
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
    """Get the default models for a grid run.

    Returns models from ollama-cloud provider (the primary cloud provider).
    Falls back to hardcoded defaults if config can't be read.
    """
    ollama_cloud_models = get_provider_models('ollama-cloud')
    if ollama_cloud_models:
        return ollama_cloud_models[:2]  # Return first 2 models for grid

    return _get_default_models()
