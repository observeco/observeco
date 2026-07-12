"""
ObserveCo Proxy Service — Task 4.6

Manages the transparent API proxy lifecycle (start/stop/status).
Integrates with ObserveCo's service manager pattern.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Optional

from observeco.dashboard.config import PORTS
from observeco.dirs import hermes_home

logger = logging.getLogger("observeco.proxy.service")

PROXY_PID_FILE = "proxy.pid"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = PORTS.proxy


def _get_data_dir() -> str:
    """Get ObserveCo data directory."""
    from observeco.dirs import get_data_dir
    return str(get_data_dir())


def _get_pid_path() -> str:
    return os.path.join(_get_data_dir(), PROXY_PID_FILE)


def _is_running(pid: int) -> bool:
    """Check if process is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _get_db_path() -> str:
    return os.path.join(_get_data_dir(), "observeco.db")


def _detect_local_llm() -> bool:
    """Auto-detect if a local LLM server (ollama) is running.

    Checks localhost:11434 (ollama default). Returns True if reachable.
    Extend this list as more local providers are supported.
    """
    import urllib.request
    for host, port in [("127.0.0.1", 11434), ("localhost", 11434)]:
        try:
            resp = urllib.request.urlopen(f"http://{host}:{port}/api/tags", timeout=2)
            if resp.status == 200:
                logger.info(f"Detected local LLM at http://{host}:{port} — enabling local tracking")
                return True
        except Exception:
            continue
    return False


def start_proxy(
    port: int = PROXY_PORT,
    upstream: str = "https://api.openai.com",
    agent_name: str = "proxy-agent",
    background: bool = True,
    track_local: Optional[bool] = None,
) -> dict:
    """
    Start the ObserveCo API proxy.

    When track_local is True, also starts a second proxy instance on port+1
    for local LLM providers (ollama, llama.cpp). Enables the SDK toggle so
    local providers get routed through the proxy.

    When track_local is None (default), auto-detects if ollama is running
    on localhost:11434 and enables local tracking automatically.

    Returns dict with state, pid, port, etc.
    """
    pid_path = _get_pid_path()

    # Check if already running
    if os.path.exists(pid_path):
        try:
            old_pid = int(open(pid_path).read().strip())
            if _is_running(old_pid):
                return {
                    "state": "already_running",
                    "pid": old_pid,
                    "port": port,
                    "message": f"Proxy already running (PID {old_pid})",
                }
        except (ValueError, FileNotFoundError):
            pass

    # Auto-detect local LLM if track_local not explicitly set
    if track_local is None:
        track_local = _detect_local_llm()

    db_path = _get_db_path()

    if background:
        # Auto-discover routing table
        from observeco.proxy.server import ProxyServer
        routing_table = ProxyServer.build_routing_table_from_config()

        # Start as background process
        cmd = [
            sys.executable, "-m", "observeco.proxy.server",
            "--port", str(port),
            "--upstream", upstream,
            "--db", db_path,
            "--agent", agent_name,
            "--log-level", "INFO",
        ]
        if routing_table:
            cmd += ["--routing", json.dumps(routing_table)]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Write PID file
        with open(pid_path, "w") as f:
            f.write(str(proc.pid))

        result = {
            "state": "running",
            "pid": proc.pid,
            "port": port,
            "upstream": upstream,
            "db_path": db_path,
        }

        # Start local LLM proxy if requested
        if track_local:
            local_port = port + 1
            local_upstream = "http://localhost:11434"
            local_cmd = [
                sys.executable, "-m", "observeco.proxy.server",
                "--port", str(local_port),
                "--upstream", local_upstream,
                "--db", db_path,
                "--agent", f"{agent_name}-local",
                "--log-level", "INFO",
            ]
            local_proc = subprocess.Popen(
                local_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Write local PID file
            local_pid_path = os.path.join(_get_data_dir(), "proxy-local.pid")
            with open(local_pid_path, "w") as f:
                f.write(str(local_proc.pid))
            result["local_pid"] = str(local_proc.pid)
            result["local_port"] = local_port
            result["local_upstream"] = local_upstream

            # Enable SDK toggle so local providers get routed through proxy
            from observeco.tracking.sdk.provider_registry import set_track_local
            set_track_local(True)

            # Auto-configure Hermes to route through proxy
            try:
                ac_result = auto_configure_hermes(port=port)
                if ac_result.get("changed"):
                    logger.info(
                        f"Auto-configured {len(ac_result['changes'])} provider(s) "
                        f"to route through proxy"
                    )
            except Exception as e:
                logger.warning(f"Auto-config failed: {e}")

        # Wait briefly to check if it started successfully
        time.sleep(1)
        if _is_running(proc.pid):
            return result
        else:
            return {
                "state": "failed",
                "pid": None,
                "error": "Process exited immediately — check logs",
            }
    else:
        # Foreground mode — import and run directly
        import uvicorn

        # Auto-discover routing table from Hermes config
        from observeco.proxy.server import ProxyServer, create_app
        routing_table = ProxyServer.build_routing_table_from_config()

        app = create_app(
            upstream_url=upstream,
            port=port,
            db_path=db_path,
            agent_name=agent_name,
            routing_table=routing_table,
        )
        uvicorn.run(app, host=PROXY_HOST, port=port, log_level="info")
        return {"state": "stopped"}


def stop_proxy() -> dict:
    """Stop the ObserveCo API proxy (and local proxy if running)."""
    pid_path = _get_pid_path()
    local_pid_path = os.path.join(_get_data_dir(), "proxy-local.pid")

    result = {"state": "not_running"}

    # Stop main proxy
    if os.path.exists(pid_path):
        try:
            pid = int(open(pid_path).read().strip())
        except (ValueError, FileNotFoundError):
            os.remove(pid_path)
            pid = None

        if pid and _is_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.5)
                    if not _is_running(pid):
                        break
                else:
                    os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            result = {"state": "stopped", "pid": pid}

        if os.path.exists(pid_path):
            os.remove(pid_path)

    # Stop local proxy
    if os.path.exists(local_pid_path):
        try:
            local_pid = int(open(local_pid_path).read().strip())
        except (ValueError, FileNotFoundError):
            os.remove(local_pid_path)
            local_pid = None

        if local_pid and _is_running(local_pid):
            try:
                os.kill(local_pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.5)
                    if not _is_running(local_pid):
                        break
                else:
                    os.kill(local_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            result["local_pid"] = str(local_pid)

        if os.path.exists(local_pid_path):
            os.remove(local_pid_path)

    # Disable SDK toggle
    from observeco.tracking.sdk.provider_registry import set_track_local
    set_track_local(False)

    return result


def get_proxy_status(port: int = PROXY_PORT) -> dict:
    """Get proxy status."""
    pid_path = _get_pid_path()

    if not os.path.exists(pid_path):
        return {"state": "not_running"}

    try:
        pid = int(open(pid_path).read().strip())
    except (ValueError, FileNotFoundError):
        return {"state": "not_running", "message": "Invalid PID file"}

    if not _is_running(pid):
        # Clean up stale PID file
        try:
            os.remove(pid_path)
        except OSError:
            pass
        return {"state": "not_running", "message": f"Stale PID {pid} cleaned up"}

    # Try to get health info
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"http://{PROXY_HOST}:{port}/health", timeout=2)
        health = json.loads(resp.read())
        return {
            "state": "running",
            "pid": pid,
            "port": port,
            "health": health,
        }
    except Exception:
        return {
            "state": "running",
            "pid": pid,
            "port": port,
            "health": "unreachable (may be starting up)",
        }


def auto_configure_hermes(port: int = PROXY_PORT) -> dict:
    """
    Task 4.7: Auto-configure Hermes to use the proxy.

    Updates ~/.hermes/config.yaml provider base_urls to route through proxy.
    When track_local is enabled, local providers route through port+1 instead.
    Returns dict with what was changed.
    """
    import yaml

    hh = hermes_home()
    config_path = str(hh / "config.yaml") if hh else os.path.expanduser("~/.hermes/config.yaml")
    if not os.path.exists(config_path):
        return {"changed": False, "error": "Hermes config not found"}

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    changes = []
    proxy_base = f"http://localhost:{port}/v1"
    local_proxy_base = f"http://localhost:{port + 1}/v1"

    # Detect if local proxy is running by checking PID file
    local_pid_path = os.path.join(_get_data_dir(), "proxy-local.pid")
    track_local = os.path.exists(local_pid_path)
    if track_local:
        try:
            local_pid = int(open(local_pid_path).read().strip())
            track_local = _is_running(local_pid)
        except (ValueError, OSError):
            track_local = False

    # Update providers section
    providers = config.get("providers", {})
    for name, prov in providers.items():
        old_url = prov.get("base_url", "")
        if not old_url:
            continue

        # Determine which proxy to use based on ORIGINAL base_url
        orig_url = prov.get("_original_base_url", old_url)
        is_local_provider = "localhost" in orig_url or "127.0.0.1" in orig_url
        if track_local and is_local_provider:
            target_url = local_proxy_base
        elif not orig_url.startswith("http://localhost"):
            target_url = proxy_base
        else:
            continue  # Already pointing at localhost proxy

        # Store original for revert (only if not already stored)
        if "_original_base_url" not in prov:
            prov["_original_base_url"] = old_url
        prov["base_url"] = target_url
        changes.append(f"providers.{name}: {old_url} → {target_url}")

    # Update default model provider
    model = config.get("model", {})
    old_default_url = model.get("base_url", "")
    if old_default_url and not old_default_url.startswith("http://localhost"):
        model["_original_base_url"] = old_default_url
        model["base_url"] = proxy_base
        changes.append(f"model.default: {old_default_url} → {proxy_base}")

    # Update fallback_providers
    for fb in config.get("fallback_providers", []):
        old_url = fb.get("base_url", "")
        if old_url and not old_url.startswith("http://localhost"):
            fb["_original_base_url"] = old_url
            fb["base_url"] = proxy_base
            changes.append(f"fallback: {old_url} → {proxy_base}")

    # Update auxiliary providers (vision, compression, etc.)
    aux = config.get("auxiliary", {})
    for aux_name, aux_cfg in aux.items():
        old_url = aux_cfg.get("base_url", "") if isinstance(aux_cfg, dict) else ""
        if old_url and not old_url.startswith("http://localhost"):
            # Check if this is a local provider
            is_local_aux = "localhost" in old_url or "127.0.0.1" in old_url
            if track_local and is_local_aux:
                aux_cfg["base_url"] = local_proxy_base
                changes.append(f"auxiliary.{aux_name}: {old_url} → {local_proxy_base}")
            else:
                aux_cfg["base_url"] = proxy_base
                changes.append(f"auxiliary.{aux_name}: {old_url} → {proxy_base}")
            aux_cfg["_original_base_url"] = old_url

    if changes:
        # Backup original config
        backup_path = config_path + f".bak.{int(time.time())}"
        import shutil
        shutil.copy2(config_path, backup_path)

        # Write updated config
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return {
            "changed": True,
            "changes": changes,
            "backup": backup_path,
            "proxy_port": port,
        }

    return {"changed": False, "message": "All providers already pointing at proxy"}


def revert_hermes_config() -> dict:
    """Revert Hermes config to original base_urls (before proxy auto-config)."""
    import yaml

    hh = hermes_home()
    config_path = str(hh / "config.yaml") if hh else os.path.expanduser("~/.hermes/config.yaml")
    if not os.path.exists(config_path):
        return {"changed": False, "error": "Hermes config not found"}

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    changes = []

    # Revert providers
    for name, prov in config.get("providers", {}).items():
        if "_original_base_url" in prov:
            prov["base_url"] = prov.pop("_original_base_url")
            changes.append(f"providers.{name}: restored {prov['base_url']}")

    # Revert default model
    model = config.get("model", {})
    if "_original_base_url" in model:
        model["base_url"] = model.pop("_original_base_url")
        changes.append(f"model.default: restored {model['base_url']}")

    # Revert fallbacks
    for fb in config.get("fallback_providers", []):
        if "_original_base_url" in fb:
            fb["base_url"] = fb.pop("_original_base_url")
            changes.append(f"fallback: restored {fb['base_url']}")

    if changes:
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    return {"changed": bool(changes), "changes": changes}
