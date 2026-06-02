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
import subprocess
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
    """Detect Hermes agents from profiles/ directory (SOUL.md) and agents/ directory.

    The canonical Hermes agent structure is profiles/<name>/SOUL.md.
    ~/.hermes/config.yaml contains many YAML keys (model names, tool configs,
    threshold settings) that are NOT agents — parsing it as agent names is wrong
    and produces garbage. Only scan directories that contain SOUL.md files.
    """
    agents: list[AgentConfig] = []
    seen: set[str] = set()
    excluded = _get_excluded_set()

    # Method 1 (preferred): Scan ~/.hermes/profiles/ for SOUL.md — the canonical source
    hermes_profiles_dir = Path.home() / ".hermes" / "profiles"
    if hermes_profiles_dir.exists():
        for entry in sorted(hermes_profiles_dir.iterdir()):
            if entry.is_dir():
                soul = entry / "SOUL.md"
                if soul.exists():
                    name = entry.name
                    if name not in seen and name not in excluded:
                        seen.add(name)
                        agents.append(AgentConfig(name=name, framework="hermes",
                                                   config_path=str(soul)))

    # Method 2 (fallback): Scan ~/.hermes/agents/ for SOUL.md
    if _HERMES_AGENTS_DIR.exists():
        for entry in sorted(_HERMES_AGENTS_DIR.iterdir()):
            if entry.is_dir():
                soul = entry / "SOUL.md"
                if soul.exists() and entry.name not in seen and entry.name not in excluded:
                    seen.add(entry.name)
                    agents.append(AgentConfig(name=entry.name, framework="hermes",
                                               config_path=str(soul)))
            elif entry.name.endswith(".md") and not entry.name.startswith("."):
                name = entry.stem
                if name not in seen and name not in excluded:
                    seen.add(name)
                    agents.append(AgentConfig(name=name, framework="hermes",
                                               config_path=str(entry)))

    return agents


def _load_openclaw_agents() -> list[AgentConfig]:
    """Detect OpenClaw agents from their workspace and SOUL identity markers."""
    agents: list[AgentConfig] = []
    seen: set[str] = set()
    excluded = _get_excluded_set()

    # Method 1 (most authoritative): Scan ~/.openclaw/workspace/ for SOUL.md
    oc_workspace = Path.home() / ".openclaw" / "workspace"
    if oc_workspace.exists():
        soul = oc_workspace / "SOUL.md"
        if soul.exists():
            text = soul.read_text().lower()
            if "openclaw" in text:
                name = soul.parent.name  # "workspace" — but we need the actual agent name
                # Try to extract name from SOUL content
                name = "kepler" if "kepler" in soul.read_text().lower() else name
                if name not in seen and name not in excluded:
                    seen.add(name)
                    agents.append(AgentConfig(name=name, framework="openclaw",
                                               config_path=str(soul)))

    # Method 2: Check ~/.hermes/profiles/ for SOUL.md with OpenClaw ownership markers
    profiles_dir = Path.home() / ".hermes" / "profiles"
    if profiles_dir.exists():
        for entry in profiles_dir.iterdir():
            soul = entry / "SOUL.md"
            if soul.exists():
                text = soul.read_text()
                lower = text.lower()
                # Only match if the SOUL explicitly owns the OpenClaw identity
                if ("openclaw" in lower and ("i am" in lower or "i run" in lower or "i'm" in lower)) or \
                   ("openclaw" in lower and "workspace" in lower):
                    name = entry.name
                    if name not in seen and name not in excluded:
                        seen.add(name)
                        agents.append(AgentConfig(name=name, framework="openclaw",
                                                   config_path=str(soul)))

    # Method 3: Legacy — AGENTS.md / SOUL.md in home or cwd
    search_paths = [
        Path.home() / "AGENTS.md",
        Path.home() / "SOUL.md",
        Path.cwd() / "AGENTS.md",
        Path.cwd() / "SOUL.md",
    ]
    for sp in search_paths:
        if sp.exists() and "openclaw" in sp.read_text().lower():
            text = sp.read_text().lower()
            name = "kepler" if "kepler" in text else sp.stem.lower()
            if name not in seen and name not in excluded:
                seen.add(name)
                agents.append(AgentConfig(name=name, framework="openclaw",
                                           config_path=str(sp)))
    return agents


def _load_agents_json() -> list[AgentConfig]:
    """Read agents from ~/.observeco/agents.json."""
    agents: list[AgentConfig] = []
    excluded = _get_excluded_set()
    if _AGENTS_JSON.exists():
        try:
            data = json.loads(_AGENTS_JSON.read_text())
            for item in data.get("agents", []):
                name = item.get("name", "unknown")
                if name in excluded:
                    continue
                agents.append(AgentConfig(
                    name=name,
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
    excluded = _get_excluded_set()
    yml_path = Path.cwd() / "observeco.yml"
    if yml_path.exists():
        try:
            text = yml_path.read_text()
            for line in text.splitlines():
                m = re.match(r"^\s*-\s*name:\s*(\S+)", line)
                if m:
                    name = m.group(1)
                    if name in excluded:
                        continue
                    fw_m = re.search(r"framework:\s*(\S+)", text)
                    framework = fw_m.group(1) if fw_m else "custom"
                    agents.append(AgentConfig(name=name, framework=framework,
                                               config_path=str(yml_path)))
        except Exception:
            pass
    return agents


def _scan_launchd_agents() -> list[AgentConfig]:
    """Scan macOS launchd for known agent services. Returns [] if not macOS."""
    agents: list[AgentConfig] = []
    excluded = _get_excluded_set()
    try:
        result = subprocess.run(
            ["launchctl", "list"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            label = parts[2].strip()
            # Only include known agent patterns
            if any(label.startswith(p) for p in
                   ["ai.hermes.", "ai.openclaw.", "com.observeco.",
                    "ai.observeco.", "com.hermes."]):
                name = label.split(".")[-1] if "." in label else label
                if name in excluded:
                    continue
                agents.append(AgentConfig(
                    name=name, framework="launchd",
                    health_check=f"launchd:{label}",
                ))
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return agents


def _scan_docker_agents() -> list[AgentConfig]:
    """Scan Docker for running containers. Returns [] if Docker not available."""
    agents: list[AgentConfig] = []
    excluded = _get_excluded_set()
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Image}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if not parts or not parts[0].strip():
                continue
            name = parts[0].strip()
            image = parts[1].strip() if len(parts) > 1 else "unknown"
            if name in excluded:
                continue
            agents.append(AgentConfig(
                name=name, framework="docker",
                health_check=f"docker:{name}",
                config_path=f"docker://{image}",
            ))
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return agents


def _scan_systemd_agents() -> list[AgentConfig]:
    """Scan systemd for agent-like services. Returns [] if not Linux."""
    agents: list[AgentConfig] = []
    excluded = _get_excluded_set()
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--all", "--no-pager"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        # Filter for agent-like service names
        agent_keywords = ["agent", "bot", "hermes", "observeco",
                          "openclaw", "crew", "worker", "daemon"]
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            unit_name = parts[0].strip()
            unit_lower = unit_name.lower()
            # Only include if a keyword matches
            if any(kw in unit_lower for kw in agent_keywords):
                if unit_name in excluded:
                    continue
                agents.append(AgentConfig(
                    name=unit_name.replace(".service", ""),
                    framework="systemd",
                    health_check=f"systemd:{unit_name}",
                ))
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return agents


def load_config() -> ObserveConfig:
    """Auto-detect all agents from all sources."""
    config = ObserveConfig()
    seen: set[str] = set()

    for loader in [_load_openclaw_agents, _load_hermes_agents,
                   _load_agents_json, _load_cwd_yml,
                   _scan_launchd_agents, _scan_docker_agents,
                   _scan_systemd_agents]:
        for agent in loader():
            if agent.name in seen:
                # Merge frameworks instead of deduping by name
                for existing in config.agents:
                    if existing.name == agent.name:
                        existing_fw = set(existing.framework.lower().replace("+", "").split())
                        new_fw = agent.framework.lower()
                        if new_fw not in existing_fw:
                            existing.framework = existing.framework + " + " + agent.framework
                        break
                continue
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


def _get_excluded_set() -> set[str]:
    """Read the excluded_agents set from agents.json."""
    if not _AGENTS_JSON.exists():
        return set()
    try:
        data = json.loads(_AGENTS_JSON.read_text())
        return set(data.get("excluded_agents", []))
    except Exception:
        return set()


def exclude_agent(name: str) -> None:
    """Add an agent name to the excluded set so auto-discovery skips it."""
    _AGENTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(_AGENTS_JSON.read_text()) if _AGENTS_JSON.exists() else {"agents": []}
    excluded = set(existing.get("excluded_agents", []))
    excluded.add(name)
    existing["excluded_agents"] = sorted(excluded)
    # Also remove from the agents list if present
    existing["agents"] = [a for a in existing["agents"] if a.get("name") != name]
    _AGENTS_JSON.write_text(json.dumps(existing, indent=2))


def list_excluded() -> list[str]:
    """Return the list of excluded agent names."""
    return sorted(_get_excluded_set())
