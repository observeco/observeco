"""Runtime adapters — per-version config accessors for Hermes/OpenClaw."""

from observeco.capability.adapters.hermes import HermesSchemaV14, HermesSchemaV16

HERMES_ADAPTERS: dict[str, type] = {
    "0.14": HermesSchemaV14,
    "0.16": HermesSchemaV16,
}

__all__ = ["HERMES_ADAPTERS", "HermesSchemaV14", "HermesSchemaV16"]
