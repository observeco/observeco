"""Config reader/writer — agent detection configs.

Reads agents from:
1. ~/.hermes/config.yaml (Hermes agents)
2. ~/.hermes/agents/ (Hermes SOUL.md files)
3. OpenClaw AGENTS.md / SOUL.md
4. ~/.observeco/agents.json
5. cwd observeco.yml (fallback)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir


@dataclass
class AgentConfig:
    name: str
    framework: str  # "hermes", "openclaw", "ollama", "custom"
    health_check: Optional[str] = None
    config_path: Optional[str] = None


@dataclass
class ObserveConfig:
    agents: list[AgentConfig] = field(default_factory=list)


_HERMES_CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"
_HERMES_AGENTS_DIR = Path.home() / ".hermes" / "agents"
_AGENTS_JSON = Path(user_data_dir("observeco", "observeco")) / "agents.json"


def _load_hermes_agents() -> list[AgentConfig]:
    """Detect Hermes agents from config.yaml and agents/ directory."""
    agents: list[AgentConfig] = []

    # Method 1: Parse config.yaml for profile definitions
    if _HERMES_CONFIG_PATH.exists():
        try:
            text = _HERMES_CONFIG_PATH.read_text()
            # Simple YAML-free extraction of profile names
            for line in text.splitlines():
                m = re.match(r"^\s+(\w+):\s*$", line)
                if m:
                    name = m.group(1)
                    if name not in ("default", "profiles", "tools", "gateways"):
                        agents.append(AgentConfig(name=name, framework="hermes",
                                                   config_path=str(_HERMES_CONFIG_PATH)))
        except Exception:
            pass

    # Method 2: Scan agents directory for SOUL.md files
    if _HERMES_AGENTS_DIR.exists():
        for entry in sorted(_HERMES_AGENTS_DIR.iterdir()):
            if entry.is_dir():
                soul = entry / "SOUL.md"
                if soul.exists():
                    agents.append(AgentConfig(name=entry.name, framework="hermes",
                                               config_path=str(soul)))
            elif entry.name.endswith(".md") and not entry.name.startswith("."):
                name = entry.stem
                agents.append(AgentConfig(name=name, framework="hermes",
                                           config_path=str(entry)))

    # Deduplicate by name
    seen: set[str] = set()
    deduped: list[AgentConfig] = []
    for a in agents:
        if a.name not in seen:
            seen.add(a.name)
            deduped.append(a)
    return deduped


def _load_openclaw_agents() -> list[AgentConfig]:
    """Detect OpenClaw agents from AGENTS.md / SOUL.md in common locations."""
    agents: list[AgentConfig] = []
    search_paths = [
        Path.home() / "AGENTS.md",
        Path.home() / "SOUL.md",
        Path.cwd() / "AGENTS.md",
        Path.cwd() / "SOUL.md",
    ]
    for sp in search_paths:
        if sp.exists():
            name = "kepler" if "kepler" in sp.read_text().lower() else sp.stem.lower()
            agents.append(AgentConfig(name=name, framework="openclaw",
                                       config_path=str(sp)))
    # Check ~/.hermes/profiles/ for OpenClaw profiles
    profiles_dir = Path.home() / ".hermes" / "profiles"
    if profiles_dir.exists():
        for entry in profiles_dir.iterdir():
            soul = entry / "SOUL.md"
            if soul.exists():
                text = soul.read_text()
                if "openclaw" in text.lower():
                    agents.append(AgentConfig(name=entry.name, framework="openclaw",
                                               config_path=str(soul)))
    return agents


def _load_agents_json() -> list[AgentConfig]:
    """Read agents from ~/.observeco/agents.json."""
    agents: list[AgentConfig] = []
    if _AGENTS_JSON.exists():
        try:
            data = json.loads(_AGENTS_JSON.read_text())
            for item in data.get("agents", []):
                agents.append(AgentConfig(
                    name=item.get("name", "unknown"),
                    framework=item.get("framework", "custom"),
                    health_check=item.get("health_check"),
                    config_path=str(_AGENTS_JSON),
                ))
        except Exception:
            pass
    return agents


def _load_cwd_yml() -> list[AgentConfig]:
    """Read observeco.yml from current working directory."""
    agents: list[AgentConfig] = []
    yml_path = Path.cwd() / "observeco.yml"
    if yml_path.exists():
        try:
            text = yml_path.read_text()
            for line in text.splitlines():
                m = re.match(r"^\s*-\s*name:\s*(\S+)", line)
                if m:
                    name = m.group(1)
                    fw_m = re.search(r"framework:\s*(\S+)", text)
                    framework = fw_m.group(1) if fw_m else "custom"
                    agents.append(AgentConfig(name=name, framework=framework,
                                               config_path=str(yml_path)))
        except Exception:
            pass
    return agents


def load_config() -> ObserveConfig:
    """Auto-detect all agents from all sources."""
    config = ObserveConfig()
    seen: set[str] = set()

    for loader in [_load_hermes_agents, _load_openclaw_agents,
                   _load_agents_json, _load_cwd_yml]:
        for agent in loader():
            if agent.name not in seen:
                seen.add(agent.name)
                config.agents.append(agent)

    return config


def write_agent(agent: AgentConfig) -> None:
    """Write a single agent to ~/.observeco/agents.json."""
    _AGENTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(_AGENTS_JSON.read_text()) if _AGENTS_JSON.exists() else {"agents": []}
    # Remove existing entry with same name
    existing["agents"] = [a for a in existing["agents"] if a.get("name") != agent.name]
    existing["agents"].append({
        "name": agent.name,
        "framework": agent.framework,
        "health_check": agent.health_check,
    })
    _AGENTS_JSON.write_text(json.dumps(existing, indent=2))
