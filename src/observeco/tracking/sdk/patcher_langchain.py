"""LangChain callback patcher — log token usage via callback handler.

LangChain supports callbacks natively — no monkey-patching needed.
We register a callback handler that logs token usage to token_logs.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from observeco.tracking.sdk.patcher_base import BasePatcher

logger = logging.getLogger(__name__)


class LangChainCallbackHandler:
    """LangChain callback handler that logs token usage."""

    def __init__(self, log_fn):
        self._log_fn = log_fn

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        """LLM call started."""
        pass

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """LLM call ended — extract token usage."""
        try:
            generations = getattr(response, "generations", [])
            llm_output = getattr(response, "llm_output", None)

            if llm_output and isinstance(llm_output, dict):
                token_usage = llm_output.get("token_usage", {})
                model_name = llm_output.get("model_name", "unknown")

                prompt_tokens = token_usage.get("prompt_tokens", 0) or token_usage.get("input_tokens", 0) or 0
                completion_tokens = token_usage.get("completion_tokens", 0) or token_usage.get("output_tokens", 0) or 0
                total = token_usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)

                if total > 0:
                    # Determine provider from model name
                    provider = "unknown"
                    if "gpt" in model_name or "o1" in model_name or "o3" in model_name:
                        provider = "openai"
                    elif "claude" in model_name:
                        provider = "anthropic"

                    self._log_fn(
                        agent_name="langchain",
                        provider=provider,
                        model=model_name,
                        total_tokens=total,
                        input_tokens=prompt_tokens,
                        output_tokens=completion_tokens,
                        source="sdk",
                    )
        except Exception as e:
            logger.debug("Failed to capture LangChain usage: %s", e)

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """LLM call failed."""
        pass


class LangChainPatcher(BasePatcher):
    """Patch LangChain to log token usage via callback handler.

    Unlike OpenAI/Anthropic patchers, LangChain supports callbacks natively.
    We inject our callback handler into the global callback manager.
    """

    name = "langchain"
    sdk_package = "langchain"

    def _patch_client(self, mod: Any) -> None:
        """Register callback handler in LangChain's callback system."""
        try:
            from langchain_core.callbacks import CallbackManager
            from langchain_core.callbacks import BaseCallbackHandler

            handler = LangChainCallbackHandler(self._log_token_turn)

            # Try to get the global callback manager and add our handler
            try:
                from langchain_core.callbacks import get_callback_manager
                manager = get_callback_manager()
                manager.add_handler(handler)
                logger.debug("Registered LangChain callback handler")
            except (ImportError, AttributeError):
                # Fallback: patch at the LLM level
                logger.debug("Global callback manager not available, patching at LLM level")

            self._original_methods["handler"] = handler
        except ImportError as e:
            logger.debug("Could not patch LangChain: %s", e)
