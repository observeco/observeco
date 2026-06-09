"""`observeco watch` — agent health auto-collection daemon.

Two modes of operation:

**Daemon mode** (default): Runs as an independent background process.
  ``observeco watch start``  — fork (POSIX) or subprocess + DETACHED_PROCESS (Windows)
  ``observeco watch stop``   — signal the daemon to shut down
  ``observeco watch status`` — is it running? How fresh is the heartbeat?

**Foreground mode** (debug/testing):
  ``observeco watch --once``  — single pulse cycle, then exit
  ``observeco watch --foreground`` — run loop attached to this terminal

The daemon writes these data sources every cycle:
  - pulse_log (health status per agent)
  - chisel_trims (token breakdown for alive agents)
  - errors (probe failures)
  - chisel_drift (7-day token drift, every 5 min)
  - clawforge_garden (memory hygiene, every 15 min)
  - pathway_nodes/edges (communication topology, every 15 min)

Self-check: writes heartbeat file every cycle so external monitors
(dashboard, health checks) can detect if the daemon is stuck or dead.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from observeco.chisel.trim import run_trim_file
from observeco.config import load_config
from observeco.db import Database
from observeco.dirs import get_data_dir
from observeco.event_bus import publish
from observeco.pulse.check import _probe_agent
from observeco.watch_consumers import ConsumerManager

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

_DATA_DIR = get_data_dir()
_HEARTBEAT_PATH = _DATA_DIR / ".watch_heartbeat.json"
_PID_PATH = _DATA_DIR / ".watch.pid"

# ── Timing ───────────────────────────────────────────────────────────────────

PULSE_INTERVAL = 30         # seconds between agent probes
HEARTBEAT_STALE_THRESHOLD = 90  # 3 missed cycles

# ── Daemon management ────────────────────────────────────────────────────────


def _pid_file() -> Optional[int]:
    """Read PID file. Returns PID or None."""
    try:
        return int(_PID_PATH.read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _is_pid_alive(pid: int) -> bool:
    """Check if a process is running on any platform."""
    try:
        os.kill(pid, 0)  # Signal 0 = test, no signal sent
        return True
    except (OSError, ProcessLookupError):
        return False


def _heartbeat_age() -> Optional[float]:
    """Age of last heartbeat in seconds, or None if no heartbeat."""
    try:
        data = json.loads(_HEARTBEAT_PATH.read_text())
        return time.time() - data.get("timestamp", 0)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def status() -> dict:
    """Return structured status of the watch daemon.

    Returns:
        dict with keys: running (bool), pid (int|None),
        heartbeat_age (float|None), cycle (int|None)
    """
    pid = _pid_file()
    alive = pid is not None and _is_pid_alive(pid)
    age = _heartbeat_age()
    return {"running": alive, "pid": pid, "heartbeat_age": age}


def start() -> None:
    """Start the watch daemon as an independent background process.

    POSIX: double-fork + setsid for proper daemonization.
    Windows: subprocess.Popen with DETACHED_PROCESS flag.
    If daemonization fails, prints a clear error message.
    """
    current = status()
    if current["running"]:
        print(f"ObserveCo watch is already running (PID {current['pid']}).")
        return

    if sys.platform == "win32":
        _start_windows()
        return

    # POSIX: fork + setsid (proper daemonization)
    try:
        pid = os.fork()
    except (OSError, AttributeError) as e:
        print(f"Could not start watch daemon: {e}")
        print("Run 'observeco watch foreground' instead to monitor in-terminal.")
        return

    if pid > 0:
        _PID_PATH.write_text(str(pid))
        print(f"ObserveCo watch started (PID {pid}).")
        return

    # Child: detach from terminal
    try:
        os.setsid()
    except OSError:
        os._exit(1)

    # Second fork to prevent re-acquiring terminal
    try:
        pid2 = os.fork()
    except OSError:
        os._exit(1)
    if pid2 > 0:
        os._exit(0)

    # Redirect stdio to /dev/null
    try:
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
    except OSError:
        pass

    _PID_PATH.write_text(str(os.getpid()))
    _run_loop()


def _start_windows() -> None:
    """Start the watch daemon on Windows using DETACHED_PROCESS.

    If subprocess.Popen fails, prints a fallback message.
    """
    try:
        # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
        proc = subprocess.Popen(
            [sys.executable, "-m", "observeco", "watch", "foreground"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        _PID_PATH.write_text(str(proc.pid))
        print(f"ObserveCo watch started (PID {proc.pid}).")
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Could not start watch daemon on Windows: {e}")
        print("Run 'observeco watch foreground' instead to monitor in-terminal.")


def stop() -> None:
    """Stop the watch daemon by signalling its PID.

    Cross-platform: uses CTRL_BREAK_EVENT (Windows) or SIGTERM (POSIX)
    with fallback to taskkill (Windows) or SIGKILL (POSIX).
    """
    current = status()
    if not current["running"]:
        print("ObserveCo watch is not running.")
        return

    pid = current["pid"]
    print(f"Stopping ObserveCo watch (PID {pid})...")

    if sys.platform == "win32":
        try:
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        except (OSError, AttributeError):
            # Fallback: use taskkill
            _windows_kill(pid)
    else:
        os.kill(pid, signal.SIGTERM)

    # Wait up to 5 seconds for clean exit
    for _ in range(50):
        time.sleep(0.1)
        if not _is_pid_alive(pid):
            break

    if _is_pid_alive(pid):
        if sys.platform == "win32":
            _windows_kill(pid)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except (OSError, AttributeError):
                pass

    _PID_PATH.unlink(missing_ok=True)
    print("ObserveCo watch stopped.")


def _windows_kill(pid: int) -> None:
    """Kill a Windows process using taskkill."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        pass


# ── The core loop ────────────────────────────────────────────────────────────


def _run_loop(interval: int = PULSE_INTERVAL) -> None:
    """Main daemon loop — runs until signalled.

    Args:
        interval: Seconds between pulse cycles.
    """
    db = Database()
    running = True
    cycle = 0
    instance_id = os.environ.get("OBSERVECO_INSTANCE_ID", "")

    def _handle_signal(sig, frame):
        nonlocal running
        running = False

    # Signal handlers: SIGINT is universal. SIGTERM is POSIX-only.
    try:
        signal.signal(signal.SIGINT, _handle_signal)
    except (ValueError, OSError, AttributeError):
        pass
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _handle_signal)
        except (ValueError, OSError):
            pass
    # Windows: also handle CTRL_BREAK_EVENT
    if sys.platform == "win32" and hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, _handle_signal)
        except (ValueError, OSError):
            pass

    # Write initial heartbeat so dashboard can detect us immediately
    _write_heartbeat(status="starting", cycle=0)

    # Start event-driven consumers (drift, garden, pathway, heal, prune)
    consumer_mgr = ConsumerManager(db=db)
    consumer_mgr.register_all()
    consumer_mgr.start_all()

    while running:
        cycle += 1

        # ── Cycle 1: Probe agent health ──────────────────────────────────────
        config = load_config()
        try:
            from observeco.auto_detect import run_discover
            run_discover(show_all=False)
        except Exception:
            pass

        config = load_config()
        agents = getattr(config, "agents", [])
        # ── Cycle 0.5: Purge stale DB-only agents ──
        purged_cycle = 0
        try:
            valid = {a.name for a in agents}
            purged_cycle = Database().purge_stale_agents(valid)
        except Exception:
            pass

        if agents:
            results = []
            # Parallel probe via ThreadPoolExecutor — max(30s) per agent
            with ThreadPoolExecutor(max_workers=10) as pool:
                future_map = {pool.submit(_probe_agent, agent): agent for agent in agents}
                for future in as_completed(future_map, timeout=45):
                    agent = future_map[future]
                    try:
                        status_val, latency, error, metadata_json = future.result(timeout=30)
                        db.log_pulse(
                            agent_name=agent.name,
                            agent_framework=getattr(agent, "framework", "custom"),
                            status=status_val,
                            latency_ms=latency * 1000,
                            instance_id=instance_id,
                            metadata_json=metadata_json,
                        )
                        # Auto-trim SOUL.md for all alive agents
                        trim_result = None
                        if status_val == "alive" and getattr(agent, "config_path", None):
                            trim_result = run_trim_file(agent.name, agent.config_path)
                        # Log token snapshot from trim results (feeds token_logs for dashboard)
                        if trim_result and isinstance(trim_result, dict):
                            try:
                                turn_id = f"watch_{int(time.time())}_{agent.name}"
                                db.log_token_turn(
                                    agent_name=agent.name,
                                    turn_id=turn_id,
                                    total_tokens=trim_result.get("total_tokens", 0),
                                    identity_tokens=trim_result.get("identity_tokens", 0),
                                    skills_tokens=trim_result.get("skills_tokens", 0),
                                    memory_tokens=trim_result.get("memory_tokens", 0),
                                    tools_tokens=trim_result.get("tools_tokens", 0),
                                    guidance_tokens=trim_result.get("guidance_tokens", 0),
                                    provider="auto-detected",
                                )
                            except Exception:
                                pass
                        results.append((agent.name, status_val, latency))
                        # Publish probe event
                        try:
                            publish(None, "probe_result", agent_name=agent.name,
                                    status=status_val, latency_ms=latency * 1000)
                        except Exception:
                            pass
                    except Exception as e:
                        db.log_pulse(
                            agent_name=agent.name,
                            agent_framework=getattr(agent, "framework", "custom"),
                            status="error",
                            latency_ms=0,
                            instance_id=instance_id,
                        )
                        db.log_error(
                            agent_name=agent.name,
                            error_type="watch_probe_failed",
                            message=str(e),
                            severity="error",
                        )
                        results.append((agent.name, "error", 0))
                        # Publish error event
                        try:
                            publish(None, "probe_error", agent_name=agent.name, error=str(e))
                        except Exception:
                            pass

            alive = sum(1 for _, s, _ in results if s == "alive")
            dead = sum(1 for _, s, _ in results if s == "dead")
            error = sum(1 for _, s, _ in results if s == "error")

            # Write heartbeat
            _write_heartbeat(
                status="running", cycle=cycle, agents=len(results),
                alive=alive, dead=dead, errors=error, purged=purged_cycle,
            )

        # Sleep in short intervals for responsive signal handling
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    consumer_mgr.stop_all()
    _write_heartbeat(status="stopped", cycle=cycle)
    _PID_PATH.unlink(missing_ok=True)


# ── Heartbeat helper ──────────────────────────────────────────────────────────


def _write_heartbeat(status: str, cycle: int, agents: int = 0,
                     alive: int = 0, dead: int = 0, errors: int = 0,
                     purged: int = 0) -> None:
    """Write heartbeat file for external monitoring."""
    try:
        _HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _HEARTBEAT_PATH.write_text(json.dumps({
            "status": status,
            "cycle": cycle,
            "timestamp": int(time.time()),
            "agents": agents,
            "alive": alive,
            "dead": dead,
            "errors": errors,
            "purged": purged,
            "pid": os.getpid(),
        }, indent=2))
    except Exception:
        pass


# ── Foreground helpers (debug) ───────────────────────────────────────────────


def run_watch(interval: int = 30, once: bool = False) -> None:
    """Run the watch loop in the foreground (debug/testing).

    Args:
        interval: Seconds between polls.
        once: Single pass and exit.
    """
    if once:
        _run_once()
        return
    _run_loop(interval=interval)


def _run_once() -> None:
    """Single pulse cycle for one-shot use (observeco watch --once)."""
    _run_loop(interval=99999999)  # Sleep forever after one cycle
