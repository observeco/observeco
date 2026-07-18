"""probe_environment() — single read-only pass that populates EnvSnapshot.

The probe is the only layer that imports OS/runtime specifics.
Feature modules must not import os.path resolution, lsof, psutil,
yaml config loaders, or socket/port logic (enforced by import-boundary test).
"""

from __future__ import annotations

import hashlib
import os
import socket
import time
from typing import Callable

import psutil
import yaml

from observeco.capability.env_snapshot import EnvSnapshot


def _get_hermes_candidates() -> tuple[str, ...]:
    """Resolve Hermes config candidates via dirs."""
    from observeco.dirs import hermes_home

    hh = hermes_home()
    if hh:
        return (str(hh / "config.yaml"), str(hh / "profiles" / "main" / "config.yaml"))
    return ("~/.hermes/config.yaml", "~/.hermes/profiles/main/config.yaml")

KNOWN_PORTS: dict[int, str] = {
    9200: "observeco",
    30000: "skillclaw",
    11434: "ollama",
    8645: "hermes_proxy",
}


def probe_environment() -> EnvSnapshot:
    """Run all probes and return a populated EnvSnapshot.

    Each probe is isolated in try/except — a single failure degrades
    that probe's fields to defaults but never aborts the pass.
    """
    snap = EnvSnapshot(probed_at=time.time())
    probes: list[tuple[str, Callable[[EnvSnapshot], None]]] = [
        ("process", _find_process),
        ("config", _read_config),
        ("fingerprint", _fingerprint),
        ("ports", _find_ports),
        ("keychain", _check_keychain),
        ("fda", _check_fda),
        ("launchagent", _check_launchagent),
        ("store_location", _check_store_location),
        ("session_store", _find_session_store),
        ("host_fingerprint", _compute_host_fingerprint),
    ]
    for name, fn in probes:
        try:
            fn(snap)
        except Exception as exc:
            snap.probe_errors[name] = str(exc)
    return snap


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------


def _find_process(snap: EnvSnapshot) -> None:
    """Detect running hermes/openclaw process and ground-truth config path."""
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            blob = " ".join(proc.info.get("cmdline") or [proc.info.get("name") or ""]).lower()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        for name in ("hermes", "openclaw"):
            if name in blob:
                snap.agent_pids[name] = proc.pid
                if snap.config_path is None:
                    try:
                        for f in proc.open_files():
                            if f.path.endswith((".yaml", ".yml", "config.json")):
                                snap.config_path = f.path  # ground truth from open files
                                break
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass

    # Fall back to candidate paths if process inspection didn't yield a config
    if snap.config_path is None:
        for cand in _get_hermes_candidates():
            resolved = os.path.realpath(os.path.expanduser(cand))
            if os.path.exists(resolved):
                snap.config_path = resolved
                break


def _read_config(snap: EnvSnapshot) -> None:
    """Parse the config file and check write access."""
    if snap.config_path is None:
        return
    try:
        with open(snap.config_path) as fh:
            snap.config_parsed = yaml.safe_load(fh) or {}
        snap.config_writable = os.access(snap.config_path, os.W_OK)
    except PermissionError:
        snap.config_error = (
            "Permission denied — grant ObserveCo read access to the config directory"
        )
    except yaml.YAMLError as exc:
        snap.config_error = f"Config file corrupt: {exc}"
    except OSError as exc:
        snap.config_error = f"Config unreadable: {exc}"


def _fingerprint(snap: EnvSnapshot) -> None:
    """Detect runtime version from config schema shape."""
    doc = snap.config_parsed or {}
    if "profiles" in doc:
        snap.runtime_version = "0.16"
    elif "providers" in doc:
        snap.runtime_version = "0.14"
    else:
        snap.runtime_version = "unknown"

    if "hermes" in snap.agent_pids:
        snap.runtime = "hermes"
    elif "openclaw" in snap.agent_pids:
        snap.runtime = "openclaw"


def _find_ports(snap: EnvSnapshot) -> None:
    """Discover an available ephemeral port and note known listeners."""
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr and conn.laddr.port in KNOWN_PORTS:
                snap.existing_proxies[KNOWN_PORTS[conn.laddr.port]] = conn.laddr.port
    except psutil.AccessDenied:
        pass

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        snap.chosen_port = sock.getsockname()[1]
    finally:
        sock.close()
    # ponytail: no retry on bind failure — if all ephemeral ports are exhausted,
    # probe crashes. Upgrade: add retry loop with exponential backoff.


def _check_keychain(snap: EnvSnapshot) -> None:
    """Verify OS keychain is usable via a round-trip probe key."""
    try:
        import keyring
        from keyring.backends import fail as fail_backend

        kr = keyring.get_keyring()
        if isinstance(kr, fail_backend.Keyring):
            return
        keyring.set_password("observeco-probe", "x", "1")
        snap.keychain_available = keyring.get_password("observeco-probe", "x") == "1"
        try:
            keyring.delete_password("observeco-probe", "x")
        except Exception:
            pass
    except Exception as e:
        # ponytail: broad except on keychain round-trip — a genuinely unexpected
        # error (e.g. keyring backend crash) is silently swallowed. Upgrade:
        # log the exception and set snap.keychain_available = False explicitly.
        print(f"[WARN] capability/probe: keychain check failed: {e}")
        snap.keychain_available = False


def _check_fda(snap: EnvSnapshot) -> None:
    """Detect Full Disk Access by attempting reads of TCC-protected paths."""
    from observeco.dirs import hermes_home

    hh = hermes_home()
    paths = ["~/Library/Safari/Bookmarks.plist"]
    if hh:
        paths.append(str(hh / "sessions"))
    else:
        paths.append("~/.hermes/sessions")
    for path in paths:
        try:
            with open(os.path.expanduser(path)):
                pass
            snap.full_disk_access = True
            return
        except PermissionError:
            continue
        except OSError:
            continue


def _check_launchagent(snap: EnvSnapshot) -> None:
    """Check if ~/Library/LaunchAgents is writable and launchctl is on PATH."""
    la_dir = os.path.expanduser("~/Library/LaunchAgents")
    launchctl_paths = ["/bin/launchctl", "/usr/bin/launchctl"]
    snap.can_install_launchagent = os.access(la_dir, os.W_OK) and any(
        os.access(p, os.X_OK) for p in launchctl_paths
    )


def _check_store_location(snap: EnvSnapshot) -> None:
    """Verify the ObserveCo store dir is not under a cloud-sync root."""
    store = os.path.expanduser("~/.observeco")
    sync_roots = [
        "~/Library/Mobile Documents",
        "~/Library/CloudStorage",
        "~/Dropbox",
        "~/Library/Application Support/Google/Drive",
    ]
    store_real = os.path.realpath(store)
    snap.store_location_safe = not any(
        store_real.startswith(os.path.realpath(os.path.expanduser(r)))
        for r in sync_roots
    )


def _find_session_store(snap: EnvSnapshot) -> None:
    """Locate the runtime's session store if readable."""
    from observeco.dirs import hermes_home, openclaw_home

    hh = hermes_home()
    oh = openclaw_home()
    candidates = []
    if hh:
        candidates.append(str(hh / "sessions"))
    else:
        candidates.append("~/.hermes/sessions")
    if oh:
        candidates.append(str(oh / "sessions"))
    else:
        candidates.append("~/.openclaw/sessions")
    for cand in candidates:
        path = os.path.expanduser(cand)
        if os.path.isdir(path) and os.access(path, os.R_OK):
            snap.session_store_path = path
            snap.framework_emits_usage = True
            return


def _compute_host_fingerprint(snap: EnvSnapshot) -> None:
    """Stable per-machine fingerprint from hostname + MAC address."""
    import uuid as _uuid

    node = _uuid.getnode()
    hostname = socket.gethostname()
    raw = f"{hostname}:{node}"
    snap.host_fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:16]
    # ponytail: _compute_host_fingerprint is not in the spec's probe table (§3.2).
    # It's a convenience for dashboard dedup. If it becomes a dependency,
    # promote to the spec and add a test.
