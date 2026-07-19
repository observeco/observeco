"""Ecosystem gap scanner — reads cron jobs, agent configs, and running processes
to find what's not being monitored by ObserveCo.

Spec: observeco-master-plan.md §3.64
"""

import json
import re
import time
from typing import Any

from observeco.config import _AGENTS_JSON, AgentConfig, write_agent
from observeco.db import Database
from observeco.dirs import hermes_home

# Cache for the GET endpoint (in-memory, 5min TTL)
_cache: dict[str, Any] = {"gaps": None, "ts": 0, "ttl": 300}

# Known AI agent executables — match these exactly (case-insensitive)
KNOWN_AGENTS = {
    "hermes", "openclaw", "ollama", "llama-server", "llama-cli", "llama.cpp",
    "claude", "codex", "opencode",
}

# Processes whose command-line contains a known agent framework
AGENT_CMDLINE_KEYWORDS = [
    "hermes", "openclaw", "ollama", "llama", "claude", "codex", "opencode",
    "crewai", "langchain", "autogen", "pydantic-ai", "observeco",
]

# Executable names that are NEVER agents (generic system/tooling processes)
NOT_AGENTS = {
    "bash", "zsh", "sh", "fish", "python3", "python3.11", "python3.12", "python3.13",
    "python", "node", "uv", "pip", "pip3", "npm", "npx", "yarn", "make", "cmake",
    "gcc", "clang", "rustc", "cargo", "go", "java", "ruby", "perl", "php",
    "fswatch", "watch", "sleep", "cat", "grep", "awk", "sed", "find", "sort",
    "curl", "wget", "git", "ssh", "scp", "rsync",
    "obsidian", "code", "cursor", "warp", "zed", "terminal",
    "launchd", "configd", "notifyd", "syslogd", "mds", "mds_stores",
    "WindowServer", "loginwindow", "hidd", "coreaudiod", "airportd",
    "bluetoothd", "wifi", "wifid", "sharingd", "netbiosd",
    "rapportd", "remindd", "siriknowledged", "parsecollaborationd",
    "nsurlsessiond", "nsurlstoraged", "trustd", "secinitd",
    "amfid", "syspolicyd", "sandboxd", "filecoordinationd",
    "distnoted", "cfprefsd", "useractivityd", "cloudd", "bird",
    "knowledge", "suggestd", "spotlight", "corespeechd",
    "mediaanalysisd", "mediaanalysisservice", "photolibraryd",
    "geod", "locationd", "navd", "mapsd", "findmy", "searchparty",
    "homeenergyd", "biomesyncd", "biome", "signpost_reporter",
    "powerd", "thermald", "backupd", "mobilebackup", "mobilebackupd",
    "installd", "softwareupdate", "swcd", "storeassetd", "appstoreagent",
    "commerce", "storekit", "passd", "paymentwebview", "peertalk",
    "networkserviceproxy", "kdc", "kcm", "scprefs", "system_installd",
    "opendirectoryd", "taskpolicy", "usermanagerd", "usernoted",
    "vtoolbox", "coreservices", "corebrightness", "displaypolicyd",
    "WindowManager", "dock", "finder", "notificationcenter",
    "controlcenter", "systemuiserver", "universalaccessd",
    "assistantd", "siriactionsd", "airplayd", "avconferenced",
    "cameracaptured", "mediaremote", "remoted", "remotenotificationd",
    "paireddevice", "proactive", "quicklook", "replayd",
    "runningboardd", "screensharingd", "securityd", "sidecar",
    "simulatestress", "siriinferenced", "sirittsd", "softwareupdateservicesd",
    "speechrecognition", "spotlightknowledged", "symptomsd",
    "sysdiagnose", "systempolicy", "tailspind", "talagent",
    "textinput", "timed", "touchbar", "tripmode", "trustedpeers",
    "uninstalld", "usermanaged", "videosubscriptionsd",
    "voiceover", "voicememoforkd", "watchdogd", "wcd",
    "webdav", "webinspect", "wifiagent", "wifianalyticsd",
    "wifip2pd", "xprotect", "xprotectd",
}


def _read_cron_jobs() -> list[dict]:
    """Read Hermes cron jobs from jobs.json."""
    home = hermes_home()
    if not home:
        return []
    jobs_path = home / "cron" / "jobs.json"
    if not jobs_path.exists():
        return []
    try:
        data = json.loads(jobs_path.read_text(encoding="utf-8"))
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        return [
            {"name": j.get("name", j.get("job_id", "unknown")), "source": str(jobs_path)}
            for j in jobs
        ]
    except (json.JSONDecodeError, OSError):
        return []


def _read_agent_configs() -> list[dict]:
    """Scan Hermes profiles for agent configs not yet in DB."""
    home = hermes_home()
    if not home:
        return []
    results = []

    # Check profiles directory
    profiles_dir = home / "profiles"
    if profiles_dir.is_dir():
        for p_dir in profiles_dir.iterdir():
            if p_dir.is_dir():
                # Look for SOUL.md or config.yaml
                soul = p_dir / "SOUL.md"
                config = p_dir / "config.yaml"
                name = p_dir.name
                if soul.exists() or config.exists():
                    results.append({"name": name, "source": str(p_dir)})

    # Check main config.yaml for agent entries
    config_path = home / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if cfg and isinstance(cfg, dict):
                # Look for profile references in config
                for key in ("profiles", "agents", "roles"):
                    entries = cfg.get(key, {})
                    if isinstance(entries, dict):
                        for name in entries:
                            if name not in {r["name"] for r in results}:
                                results.append({"name": name, "source": str(config_path)})
        except Exception:
            pass

    return results


def _read_running_processes() -> list[dict]:
    """Scan running processes for AI agent processes."""
    results = []
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                pname = (proc.info.get("name") or "").strip()
                pname_lower = pname.lower()
                cmdline_raw = proc.info.get("cmdline") or []
                cmdline_str = " ".join(cmdline_raw).lower()

                # 1) Known agent executable — always include
                if pname_lower in KNOWN_AGENTS:
                    if pname not in {r["name"] for r in results}:
                        results.append({"name": pname, "source": f"process/{proc.info['pid']}"})
                    continue

                # 2) Not a known agent and name is in NOT_AGENTS — skip
                if pname_lower in NOT_AGENTS:
                    continue

                # 3) Everything else: check cmdline for agent keywords
                if any(kw in cmdline_str for kw in AGENT_CMDLINE_KEYWORDS):
                    if pname not in {r["name"] for r in results}:
                        results.append({"name": pname, "source": f"process/{proc.info['pid']}"})

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        import subprocess
        try:
            out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
            for line in out.split("\n")[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 11:
                    continue
                proc_name = parts[10]
                pname_lower = proc_name.lower()
                cmd = " ".join(parts[10:]).lower()

                if pname_lower in KNOWN_AGENTS:
                    if proc_name not in {r["name"] for r in results}:
                        results.append({"name": proc_name, "source": "ps_aux"})
                    continue

                if pname_lower in NOT_AGENTS:
                    continue

                if any(kw in cmd for kw in AGENT_CMDLINE_KEYWORDS):
                    if proc_name not in {r["name"] for r in results}:
                        results.append({"name": proc_name, "source": "ps_aux"})
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return results


def scan() -> list[dict]:
    """Run all three scans and return gaps (items not tracked in DB).

    Returns list of dicts: {category, name, reason, suggested_framework, source}
    """
    db = Database()
    tracked_names = {a["agent_name"].lower() for a in db.get_agents()}
    gaps: list[dict] = []

    # 1. Cron jobs
    for job in _read_cron_jobs():
        name = job["name"].lower().replace(" ", "_").replace("-", "_")
        if name not in tracked_names and name not in {g["name"].lower() for g in gaps}:
            gaps.append({
                "category": "cron",
                "name": job["name"],
                "reason": "Not monitored",
                "suggested_framework": "cron",
                "health_check": f"pgrep -f {re.escape(name)}",
                "source": str(job["source"]),
            })

    # 2. Agent configs
    for cfg in _read_agent_configs():
        name = cfg["name"].lower().replace(" ", "_").replace("-", "_")
        if name not in tracked_names and name not in {g["name"].lower() for g in gaps}:
            gaps.append({
                "category": "agent",
                "name": cfg["name"],
                "reason": "Config found, not tracked",
                "suggested_framework": "hermes",
                "health_check": f"pgrep -f {re.escape(name)}",
                "source": str(cfg["source"]),
            })

    # 3. Running processes — use the original process name for pgrep
    for proc in _read_running_processes():
        name = proc["name"].lower().replace(" ", "_").replace("-", "_")
        if name not in tracked_names and name not in {g["name"].lower() for g in gaps}:
            # Use the original process name (not sanitized) for pgrep matching
            proc_name = proc["name"]
            gaps.append({
                "category": "process",
                "name": proc["name"],
                "reason": "Running, not registered",
                "suggested_framework": "custom",
                "health_check": f"pgrep -f {re.escape(proc_name)}",
                "source": str(proc["source"]),
            })

    return gaps


def scan_cached() -> list[dict]:
    """Like scan() but with 5min in-memory cache."""
    now = time.time()
    if _cache["gaps"] is not None and (now - _cache["ts"]) < _cache["ttl"]:
        return _cache["gaps"]
    _cache["gaps"] = scan()
    _cache["ts"] = now
    return _cache["gaps"]


def add_gap(name: str, framework: str = "custom", health_check: str = "") -> dict:
    """Register a gap item as a tracked agent.

    Returns dict with status and message.
    """
    db = Database()
    safe_name = name.lower().replace(" ", "_").replace("-", "_")

    # Check both stores: pulse.db and agents.json
    tracked = {a["agent_name"].lower() for a in db.get_agents()}
    if _AGENTS_JSON.exists():
        import json
        try:
            data = json.loads(_AGENTS_JSON.read_text())
            for a in data.get("agents", []):
                tracked.add(a.get("name", "").lower())
        except (json.JSONDecodeError, OSError):
            pass
    if safe_name in tracked:
        return {"status": "exists", "message": f"'{name}' is already tracked"}

    db.register_agent(safe_name, framework, health_check=health_check)
    # Also write to agents.json so pulse check picks it up
    write_agent(AgentConfig(name=safe_name, framework=framework, health_check=health_check))
    # Bump cache so next scan reflects the change
    _cache["gaps"] = None
    return {"status": "ok", "message": f"'{name}' registered and monitoring started"}
