"""SDK detector — scan installed packages for AI SDKs.

Uses importlib.util.find_spec() to check if packages are installed
without actually importing them (avoids side effects).
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DetectedSDK:
    """A detected AI SDK."""
    name: str
    package: str
    version: Optional[str] = None
    patcher_available: bool = True
    description: str = ""


# Registry of known AI SDKs and their detection info
SDK_REGISTRY: list[DetectedSDK] = [
    DetectedSDK(
        name="openai",
        package="openai",
        description="OpenAI Python SDK (GPT-4, GPT-4o, o1, etc.)",
    ),
    DetectedSDK(
        name="anthropic",
        package="anthropic",
        description="Anthropic Python SDK (Claude 3, Claude 4)",
    ),
    DetectedSDK(
        name="langchain",
        package="langchain",
        description="LangChain framework (chains, agents, tools)",
    ),
    DetectedSDK(
        name="langchain_openai",
        package="langchain_openai",
        description="LangChain OpenAI integration",
    ),
    DetectedSDK(
        name="langchain_anthropic",
        package="langchain_anthropic",
        description="LangChain Anthropic integration",
    ),
    DetectedSDK(
        name="llama_index",
        package="llama_index",
        description="LlamaIndex framework (RAG, agents)",
    ),
    DetectedSDK(
        name="litellm",
        package="litellm",
        description="LiteLLM proxy (100+ LLM providers)",
    ),
    DetectedSDK(
        name="cohere",
        package="cohere",
        description="Cohere Python SDK",
    ),
    DetectedSDK(
        name="google_generativeai",
        package="google.generativeai",
        description="Google Generative AI SDK (Gemini)",
    ),
    DetectedSDK(
        name="mistralai",
        package="mistralai",
        description="Mistral AI Python SDK",
    ),
]


def _get_version(package: str) -> Optional[str]:
    """Get package version without importing it."""
    try:
        # Try importlib.metadata first (Python 3.8+)
        from importlib.metadata import version, PackageNotFoundError
        try:
            # Map package names to distribution names
            dist_map = {
                "google.generativeai": "google-generativeai",
                "langchain_openai": "langchain-openai",
                "langchain_anthropic": "langchain-anthropic",
                "llama_index": "llama-index",
                "mistralai": "mistralai",
            }
            dist_name = dist_map.get(package, package)
            return version(dist_name)
        except PackageNotFoundError:
            return None
    except ImportError:
        return None


def detect_sdks() -> list[DetectedSDK]:
    """Detect all installed AI SDKs.

    Returns list of DetectedSDK for packages that are installed.
    """
    detected: list[DetectedSDK] = []

    for sdk in SDK_REGISTRY:
        # For dotted names (e.g. "google.generativeai"), check the top-level package
        top_pkg = sdk.package.split(".")[0]
        spec = importlib.util.find_spec(top_pkg)
        if spec is not None:
            sdk.version = _get_version(sdk.package)
            detected.append(sdk)

    return detected


def detect_sdks_dict() -> dict:
    """Detect SDKs and return as dict for API responses."""
    detected = detect_sdks()
    return {
        "detected": [
            {
                "name": s.name,
                "package": s.package,
                "version": s.version,
                "patcher_available": s.patcher_available,
                "description": s.description,
            }
            for s in detected
        ],
        "total": len(detected),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
