"""Hermes runtime adapters — schema-specific config accessors.

V0.14 uses a top-level `providers` list; V0.16 uses `profiles`.
New Hermes versions add a new class here — no probe or feature changes needed.
"""

from __future__ import annotations

from typing import IO

import yaml


class HermesSchemaV14:
    """Accessor for Hermes config schema v0.14 (`providers` list)."""

    @staticmethod
    def load(path: str) -> dict:
        with open(path) as fh:
            return yaml.safe_load(fh) or {}

    @staticmethod
    def dump(doc: dict, file: IO[str]) -> None:
        yaml.dump(doc, file, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def get_base_url(doc: dict, provider: str) -> str | None:
        """Return base_url for the named provider, or None if not found."""
        for entry in doc.get("providers", []):
            if isinstance(entry, dict) and entry.get("name") == provider:
                return entry.get("base_url")
        return None

    @staticmethod
    def set_base_url(doc: dict, provider: str, url: str) -> None:
        """Set base_url for the named provider; add entry if absent."""
        for entry in doc.get("providers", []):
            if isinstance(entry, dict) and entry.get("name") == provider:
                entry["base_url"] = url
                return
        doc.setdefault("providers", []).append({"name": provider, "base_url": url})


class HermesSchemaV16:
    """Accessor for Hermes config schema v0.16 (`profiles` dict)."""

    @staticmethod
    def load(path: str) -> dict:
        with open(path) as fh:
            return yaml.safe_load(fh) or {}

    @staticmethod
    def dump(doc: dict, file: IO[str]) -> None:
        yaml.dump(doc, file, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def get_base_url(doc: dict, provider: str) -> str | None:
        """Return base_url for the named provider across all profiles, or None."""
        for _profile_name, profile in doc.get("profiles", {}).items():
            if not isinstance(profile, dict):
                continue
            providers = profile.get("providers", [])
            for entry in providers:
                if isinstance(entry, dict) and entry.get("name") == provider:
                    return entry.get("base_url")
        return None

    @staticmethod
    def set_base_url(doc: dict, provider: str, url: str) -> None:
        """Set base_url for the named provider in the first profile that has it."""
        profiles = doc.get("profiles", {})
        for _profile_name, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            for entry in profile.get("providers", []):
                if isinstance(entry, dict) and entry.get("name") == provider:
                    entry["base_url"] = url
                    return
        # Provider not found — add to first profile, or create default profile
        if profiles:
            first_profile = next(iter(profiles.values()))
            if isinstance(first_profile, dict):
                first_profile.setdefault("providers", []).append(
                    {"name": provider, "base_url": url}
                )
        else:
            doc["profiles"] = {"default": {"providers": [{"name": provider, "base_url": url}]}}
