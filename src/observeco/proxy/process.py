"""Proxy process lifecycle — start, stop, health-check for the proxy subprocess.

The reconciler depends on this module as its ``ensure_proxy_alive`` callable.
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import sys
import time

logger = logging.getLogger(__name__)

PROXY_HOST = "127.0.0.1"
_STARTUP_WAIT = 1.0   # seconds to wait after launch before health-checking
_HEALTH_TO = 0.5      # socket connect timeout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _port_alive(host: str, port: int) -> bool:
    """True if something is listening on *host:port*."""
    try:
        with socket.create_connection((host, port), timeout=_HEALTH_TO):
            return True
    except OSError:
        return False


def _resolve_db_path() -> str:
    """Path to ``observeco.db`` (empty string if unresolvable)."""
    try:
        from observeco.dirs import get_data_dir
        return os.path.join(str(get_data_dir()), "observeco.db")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ensure_proxy_alive(our_port: int | None) -> tuple[bool, int | None]:
    """Make sure the proxy subprocess is running on *our_port*.

    If the port is ``None`` the answer is always ``(False, None)`` — the
    caller is signalling "no proxy desired" and should fall through to
    revert logic.

    Returns ``(True, port)`` when the proxy is reachable, ``(False, None)``
    when it couldn't be started.

    ponytail:  This uses a fixed 1-second sleep-then-check startup pattern.
    A process-notify (pipe-read until "listening") would be faster and more
    reliable under load, but requires teaching the proxy child to signal
    on a fd, which is out of scope for now.
    """
    if our_port is None:
        return False, None

    if _port_alive(PROXY_HOST, our_port):
        return True, our_port

    db_path = _resolve_db_path()
    cmd = [
        sys.executable, "-m", "observeco.proxy.server",
        "--port", str(our_port),
        "--log-level", "WARNING",
    ]
    if db_path:
        cmd += ["--db", db_path]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # orphan so parent exit doesn't kill it
        )
    except OSError as exc:
        logger.error("ensure_proxy_alive: subprocess spawn failed — %s", exc)
        return False, None

    time.sleep(_STARTUP_WAIT)

    if _port_alive(PROXY_HOST, our_port):
        logger.info("Proxy running on port %d (PID %d)", our_port, proc.pid)
        return True, our_port

    proc.poll()
    logger.error(
        "Proxy on port %d exited prematurely (rc=%s)",
        our_port, proc.returncode,
    )
    return False, None


def stop_proxy(port: int) -> bool:
    """Kill whatever is listening on *port*.

    Sends SIGTERM, waits 0.5 s for graceful shutdown, then SIGKILL
    survivors.  Returns ``True`` if at least one process was killed.

    ponytail:  Uses ``lsof -ti`` to find the PID by port rather than a
    PID-file.  This is simpler and works even if the process was orphaned,
    but depends on ``lsof`` being installed (macOS / most Linux).  Upgrade
    path: cache the PID in ``ensure_proxy_alive`` and kill by PID directly.
    """
    try:
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("stop_proxy: can't enumerate port %d — %s", port, exc)
        return False

    if result.returncode != 0 or not result.stdout.strip():
        return False

    # Extract PIDs — lsof -ti returns one PID per line
    pids = []
    for line in result.stdout.strip().splitlines():
        pid = line.strip()
        if pid.isdigit():
            pids.append(int(pid))

    if not pids:
        return False

    # SIGTERM round
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    time.sleep(0.5)

    # SIGKILL survivors
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    logger.info("Stopped proxy on port %d — %d PID(s) killed", port, len(pids))
    return True


# ---------------------------------------------------------------------------
# Self-check (one runnable assertion against the contract)
# ---------------------------------------------------------------------------

def _self_check() -> None:
    """Exercise the contract with guaranteed invariants.

    Covers:
    - ``None`` port → ``(False, None)`` (caller signalling "no proxy desired").
    - Negative ``stop_proxy`` on unresolvable port → ``False``.
    """
    # 1) None port → (False, None)
    alive, port = ensure_proxy_alive(None)
    assert (alive, port) == (False, None), f"expected (False, None), got ({alive}, {port})"
    # 2) stop_proxy on a non-existent high port → False
    stopped = stop_proxy(65535)
    assert stopped is False, f"expected False on empty port, got {stopped}"
    print("process.py self-check: OK")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _self_check()
