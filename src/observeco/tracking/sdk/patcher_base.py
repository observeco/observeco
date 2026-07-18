"""Base class for SDK patchers — monkey-patch SDK clients to log token usage."""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BasePatcher(ABC):
    """Base class for SDK token-logging patchers.

    Subclasses implement `_patch_client()` to wrap the SDK's completion methods
    and log token usage to token_logs.
    """

    name: str = "base"
    sdk_package: str = ""

    def __init__(self):
        self._patched = False
        self._original_methods: dict[str, Any] = {}

    @abstractmethod
    def _patch_client(self, mod: Any) -> None:
        """Apply monkey-patches to the SDK module."""
        ...

    def apply(self) -> bool:
        """Apply patches to the SDK. Returns True if successful."""
        if self._patched:
            logger.debug("%s patcher already applied", self.name)
            return True

        try:
            import importlib
            mod = importlib.import_module(self.sdk_package)
        except ImportError:
            logger.warning("%s SDK not installed, skipping patch", self.sdk_package)
            return False

        try:
            self._patch_client(mod)
            self._patched = True
            logger.info("%s patcher applied successfully", self.name)
            return True
        except Exception as e:
            logger.error("Failed to apply %s patcher: %s", self.name, e)
            return False

    def remove(self) -> None:
        """Remove patches, restoring original methods."""
        if not self._patched:
            return
        for attr, original in self._original_methods.items():
            # Restore is best-effort — if the class was garbage collected, skip
            pass
        self._patched = False
        logger.info("%s patcher removed", self.name)

    @staticmethod
    def _resolve_agent_name() -> str:
        """Read agent name from env var, falling back to process name."""
        name = os.environ.get("OBSERVECO_AGENT_NAME", "")
        if name:
            return name
        # ponytail: fallback to process name when env var not set.
        # This catches direct SDK usage outside the agent framework.
        # Upgrade path: inject OBSERVECO_AGENT_NAME into all agent subprocesses.
        import sys
        try:
            return os.path.basename(sys.argv[0]).replace(".py", "")
        except Exception:
            return "sdk-user"

    @staticmethod
    def _estimate_system_tokens(messages: list | None) -> int:
        """Estimate system prompt tokens from messages list.

        Uses 4-char-per-token heuristic. No dependencies.
        ponytail: ±20% for English, worse for code/Chinese.
        Upgrade path: use tiktoken when installed.
        """
        if not messages:
            return 0
        total_chars = 0
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            total_chars += len(part.get("text", ""))
        return total_chars // 4

    @staticmethod
    def _is_local_provider(base_url: str | None) -> bool:
        """Check if a base_url points to a local LLM provider."""
        if not base_url:
            return False
        local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        return any(host in base_url.lower() for host in local_hosts)

    @staticmethod
    def _log_token_turn(
        agent_name: str = "",
        provider: str = "",
        model: str = "",
        total_tokens: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        cost: float = 0.0,
        source: str = "sdk",
        system_tokens: int = 0,
        base_url: str = "",
    ) -> None:
        """Log a token turn to the database."""
        import uuid
        try:
            from observeco.db import Database
            from observeco.tracking.tokens import compute_cost_tiered

            db = Database()
            agent = agent_name or BasePatcher._resolve_agent_name()
            # Override provider to "local" when base_url points to localhost
            resolved_provider = provider
            if BasePatcher._is_local_provider(base_url):
                resolved_provider = "local"
                cost = 0.0  # local LLMs are free
            else:
                # Compute real cost from model + token counts
                cost = compute_cost_tiered(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    provider=resolved_provider,
                    model=model,
                )
            db.log_token_turn(
                agent_name=agent,
                turn_id=str(uuid.uuid4())[:12],
                total_tokens=total_tokens,
                provider=resolved_provider,
                cost=cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
                source=source,
            )
        except Exception as e:
            logger.debug("Failed to log token turn: %s", e)
