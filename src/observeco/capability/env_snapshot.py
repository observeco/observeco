"""EnvSnapshot — flat dataclass produced by the probe layer.

Every feature reads from this struct; no feature reaches into configs,
processes, or ports itself. The probe is the only env-aware layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class EnvSnapshot:
    # Runtime
    runtime: str | None = None              # "hermes" | "openclaw"
    runtime_version: str | None = None      # "0.16" | "0.14" | "unknown"
    agent_pids: dict[str, int] = field(default_factory=dict)

    # Config
    config_path: str | None = None
    config_writable: bool = False
    config_parsed: dict | None = None       # raw parsed YAML, for LLM enrichment
    config_error: str | None = None         # reason if config unreadable (Trap 3 guard)

    # Ports & proxies
    chosen_port: int | None = None          # ephemeral port we can bind
    existing_proxies: dict[str, int] = field(default_factory=dict)  # e.g. {"skillclaw": 30000}

    # Permissions
    keychain_available: bool = False
    full_disk_access: bool = False
    can_install_launchagent: bool = False
    store_location_safe: bool = False

    # Session store
    framework_emits_usage: bool = False
    session_store_path: str | None = None

    # Metadata
    host_fingerprint: str = ""
    probed_at: float = field(default_factory=time.time)
    probe_errors: dict[str, str] = field(default_factory=dict)  # failed probe → reason

    # LLM-enriched (Phase 2+)
    anomalies: list[str] = field(default_factory=list)
    config_summary: str | None = None       # LLM-generated plain-English summary
