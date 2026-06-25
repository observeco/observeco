"""OpenAI SDK patcher — log token usage from OpenAI API calls."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from observeco.tracking.sdk.patcher_base import BasePatcher

logger = logging.getLogger(__name__)


class OpenAIPatcher(BasePatcher):
    """Patch OpenAI client to log token usage.

    Wraps client.chat.completions.create() and client.completions.create()
    to capture response.usage and log to token_logs.
    """

    name = "openai"
    sdk_package = "openai"

    def _patch_client(self, mod: Any) -> None:
        """Patch OpenAI ChatCompletions and Completions."""
        # Patch ChatCompletions.create
        try:
            chat_cls = mod.resources.ChatCompletions
            original_create = chat_cls.create

            @wraps(original_create)
            def patched_chat_create(*args, **kwargs):
                response = original_create(*args, **kwargs)
                self._capture_usage(response, "chat", kwargs)
                return response

            chat_cls.create = patched_chat_create
            self._original_methods["chat.create"] = original_create
            logger.debug("Patched OpenAI ChatCompletions.create")
        except (AttributeError, ImportError) as e:
            logger.debug("Could not patch ChatCompletions: %s", e)

        # Patch Completions.create
        try:
            comp_cls = mod.resources.Completions
            original_create = comp_cls.create

            @wraps(original_create)
            def patched_comp_create(*args, **kwargs):
                response = original_create(*args, **kwargs)
                self._capture_usage(response, "completion", kwargs)
                return response

            comp_cls.create = patched_comp_create
            self._original_methods["completion.create"] = original_create
            logger.debug("Patched OpenAI Completions.create")
        except (AttributeError, ImportError) as e:
            logger.debug("Could not patch Completions: %s", e)

    def _capture_usage(self, response: Any, call_type: str, request_kwargs: dict | None = None) -> None:
        """Extract usage from response and log it."""
        try:
            usage = getattr(response, "usage", None)
            if not usage:
                return

            model = getattr(response, "model", "unknown")
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens)

            # Cache tokens (prompt caching)
            cache_creation = getattr(usage, "prompt_tokens_details", None)
            cache_read = 0
            cache_write = 0
            if cache_creation:
                cache_read = getattr(cache_creation, "cached_tokens", 0) or 0
            cache_write_attr = getattr(usage, "prompt_tokens_details", None)
            if cache_write_attr:
                cache_write = getattr(cache_write_attr, "cache_creation_tokens", 0) or 0

            # Estimate system prompt tokens from request kwargs
            system_tokens = 0
            messages = (request_kwargs or {}).get("messages")
            if messages:
                system_tokens = self._estimate_system_tokens(messages)

            # Detect base_url for local/cloud routing
            base_url = ""
            try:
                client = getattr(response, "_client", None)
                if client:
                    base_url = str(getattr(client, "_base_url", ""))
            except Exception:
                pass

            if total_tokens > 0:
                self._log_token_turn(
                    agent_name="",
                    provider="openai",
                    model=model,
                    total_tokens=total_tokens,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    cache_creation_tokens=cache_write,
                    cache_read_tokens=cache_read,
                    source="sdk",
                    system_tokens=system_tokens,
                    base_url=base_url,
                )
        except Exception as e:
            logger.debug("Failed to capture OpenAI usage: %s", e)
