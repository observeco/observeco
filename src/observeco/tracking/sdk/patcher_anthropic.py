"""Anthropic SDK patcher — log token usage from Anthropic API calls."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from observeco.tracking.sdk.patcher_base import BasePatcher

logger = logging.getLogger(__name__)


class AnthropicPatcher(BasePatcher):
    """Patch Anthropic client to log token usage.

    Wraps client.messages.create() to capture usage and log to token_logs.
    """

    name = "anthropic"
    sdk_package = "anthropic"

    def _patch_client(self, mod: Any) -> None:
        try:
            client_cls = mod.Anthropic
            original_init = client_cls.__init__

            def patched_init(self_client, *args, **kwargs):
                original_init(self_client, *args, **kwargs)
                # Wrap messages.create on the instance
                if hasattr(self_client, "messages"):
                    orig_create = self_client.messages.create

                    @wraps(orig_create)
                    def patched_create(*args, **kwargs):
                        response = orig_create(*args, **kwargs)
                        self._capture_usage(response, kwargs)
                        return response

                    self_client.messages.create = patched_create

            client_cls.__init__ = patched_init
            self._original_methods["Anthropic.__init__"] = original_init
            logger.debug("Patched Anthropic client")
        except (AttributeError, ImportError) as e:
            logger.debug("Could not patch Anthropic: %s", e)

    def _capture_usage(self, response: Any, request_kwargs: dict | None = None) -> None:
        try:
            usage = getattr(response, "usage", None)
            if not usage:
                return

            model = getattr(response, "model", "unknown")
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0
            cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
            total = input_tokens + output_tokens

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

            if total > 0:
                self._log_token_turn(
                    agent_name="",
                    provider="anthropic",
                    model=model,
                    total_tokens=total,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_creation_tokens=cache_creation,
                    cache_read_tokens=cache_read,
                    source="sdk",
                    system_tokens=system_tokens,
                    base_url=base_url,
                )
        except Exception as e:
            logger.debug("Failed to capture Anthropic usage: %s", e)
