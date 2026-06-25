"""Capability layer — probe-first environment discovery for ObserveCo."""

from observeco.capability.env_snapshot import EnvSnapshot
from observeco.capability.probe import probe_environment

__all__ = ["EnvSnapshot", "probe_environment"]
