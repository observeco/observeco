"""SDK patcher registry — maps SDK names to patcher classes."""
from __future__ import annotations

import logging
from typing import Type

from observeco.tracking.sdk.patcher_base import BasePatcher

logger = logging.getLogger(__name__)

# Registry of available patchers
_PATCHER_REGISTRY: dict[str, Type[BasePatcher]] = {}


def _register_patcher(cls: Type[BasePatcher]) -> None:
    """Register a patcher class."""
    _PATCHER_REGISTRY[cls.name] = cls


def _load_patchers() -> None:
    """Lazily load patcher classes."""
    if _PATCHER_REGISTRY:
        return

    try:
        from observeco.tracking.sdk.patcher_openai import OpenAIPatcher
        _register_patcher(OpenAIPatcher)
    except ImportError:
        pass

    try:
        from observeco.tracking.sdk.patcher_anthropic import AnthropicPatcher
        _register_patcher(AnthropicPatcher)
    except ImportError:
        pass

    try:
        from observeco.tracking.sdk.patcher_langchain import LangChainPatcher
        _register_patcher(LangChainPatcher)
    except ImportError:
        pass


def get_patcher(name: str) -> BasePatcher | None:
    """Get a patcher instance by SDK name."""
    _load_patchers()
    cls = _PATCHER_REGISTRY.get(name)
    if cls:
        return cls()
    return None


def get_all_patchers() -> list[BasePatcher]:
    """Get instances of all registered patchers."""
    _load_patchers()
    return [cls() for cls in _PATCHER_REGISTRY.values()]


def apply_patcher(name: str) -> bool:
    """Apply a specific patcher by name."""
    patcher = get_patcher(name)
    if patcher:
        return patcher.apply()
    return False


def apply_all_patchers() -> dict[str, bool]:
    """Apply all available patchers. Returns {name: success}."""
    results = {}
    for patcher in get_all_patchers():
        results[patcher.name] = patcher.apply()
    return results


def list_patcher_names() -> list[str]:
    """List available patcher names."""
    _load_patchers()
    return list(_PATCHER_REGISTRY.keys())
