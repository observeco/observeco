"""Service manager for ObserveCo.

Provides start/stop/status commands for the service components:
- OTEL listener (port 4318)
- Dashboard (port 8787)

Also handles process management, port conflict detection, and auto-restart.

GS-019: Data & Observability Continuity
"""

from __future__ import annotations

import logging
import subprocess

from observeco.dashboard.config import PORTS
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import psutil

from .dirs import get_data_dir

logger = logging.getLogger(__name__)

# Service constants
SERVICE_PID_DIR = get_data_dir() / ".service"
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 60  # seconds — consider component dead if no heartbeat
RESTART_MAX_ATTEMPTS = 3
RESTART_WINDOW = 300  # 5 minutes


class ComponentState(Enum):
    """Component state."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class ComponentInfo:
    """Information about a service component."""
    name: str
    state: ComponentState
    pid: Optional[int] = None
    port: Optional[int] = None
    started_at: Optional[float] = None
    last_heartbeat: Optional[float] = None
    restart_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "name": self.name,
            "state": self.state.value,
            "pid": self.pid,
            "port": self.port,
            "started_at": self.started_at,
            "uptime": time.time() - self.started_at if self.started_at else None,
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_age": time.time() - self.last_heartbeat if self.last_heartbeat else None,
            "restart_count": self.restart_count,
            "error": self.error,
        }


class ServiceManager:
    """Manages ObserveCo service components."""

    def __init__(self):
        self._components: dict[str, ComponentInfo] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._restart_history: dict[str, list[float]] = {}

        # Ensure PID directory exists
        SERVICE_PID_DIR.mkdir(parents=True, exist_ok=True)

    def start_component(self, name: str, command: list[str], port: Optional[int] = None) -> ComponentInfo:
        """Start a service component."""
        # Check if already running
        existing = self._get_component(name)
        if existing and existing.state == ComponentState.RUNNING:
            logger.warning(f"Component {name} is already running (PID {existing.pid})")
            return existing

        # Check port availability
        if port and not self._check_port_available(port):
            # Try to kill existing process on port
            killed = self._kill_process_on_port(port)
            if not killed:
                return ComponentInfo(
                    name=name,
                    state=ComponentState.FAILED,
                    error=f"Port {port} is already in use",
                )
            time.sleep(1)  # Wait for port to be released

        # Start the component
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            # Wait for process to start
            time.sleep(2)

            # Check if process is still running OR if it was a daemon that exited successfully
            returncode = process.poll()
            if returncode is not None:
                # Process exited - check if it was a successful daemon start
                if returncode == 0:
                    # Likely a daemon that forked and exited - check if port is listening
                    if port and self._is_port_listening(port):
                        # Daemon is running on the port, use a dummy PID
                        component = ComponentInfo(
                            name=name,
                            state=ComponentState.RUNNING,
                            pid=None,  # Daemon PID is managed by the daemon itself
                            port=port,
                            started_at=time.time(),
                        )
                        self._components[name] = component
                        logger.info(f"Component {name} started as daemon on port {port}")
                        return component

                # Process failed to start
                stdout, stderr = process.communicate()
                logger.error(f"Component {name} failed to start: {stderr.decode()}")
                return ComponentInfo(
                    name=name,
                    state=ComponentState.FAILED,
                    error=f"Process exited immediately: {stderr.decode()[:200]}",
                )

            component = ComponentInfo(
                name=name,
                state=ComponentState.RUNNING,
                pid=process.pid,
                port=port,
                started_at=time.time(),
            )

            self._components[name] = component
            self._processes[name] = process

            # Write PID file
            pid_file = SERVICE_PID_DIR / f"{name}.pid"
            pid_file.write_text(str(process.pid))

            logger.info(f"Started component {name} (PID {process.pid})")
            return component

        except Exception as e:
            logger.error(f"Failed to start component {name}: {e}")
            return ComponentInfo(
                name=name,
                state=ComponentState.FAILED,
                error=str(e),
            )

    def stop_component(self, name: str, timeout: int = 5) -> ComponentInfo:
        """Stop a service component."""
        component = self._get_component(name)
        if not component or component.state == ComponentState.STOPPED:
            return ComponentInfo(name=name, state=ComponentState.STOPPED)

        # Try graceful shutdown first
        if component.pid:
            try:
                process = psutil.Process(component.pid)
                process.terminate()
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                # Force kill
                try:
                    process = psutil.Process(component.pid)
                    process.kill()
                except psutil.NoSuchProcess:
                    pass
            except psutil.NoSuchProcess:
                pass

        # Clean up PID file
        pid_file = SERVICE_PID_DIR / f"{name}.pid"
        if pid_file.exists():
            pid_file.unlink()

        # Update component state
        component.state = ComponentState.STOPPED
        component.pid = None
        component.started_at = None

        logger.info(f"Stopped component {name}")
        return component

    def get_status(self) -> dict[str, ComponentInfo]:
        """Get status of all components."""
        # Read PID files to discover running components
        if SERVICE_PID_DIR.exists():
            for pid_file in SERVICE_PID_DIR.glob("*.pid"):
                name = pid_file.stem
                try:
                    pid = int(pid_file.read_text().strip())
                    process = psutil.Process(pid)
                    if process.is_running():
                        # Component is running
                        component = ComponentInfo(
                            name=name,
                            state=ComponentState.RUNNING,
                            pid=pid,
                            started_at=process.create_time(),
                        )
                        self._components[name] = component
                    else:
                        # Process exited, clean up PID file
                        pid_file.unlink()
                except (psutil.NoSuchProcess, ValueError):
                    # Process not found or invalid PID, clean up
                    pid_file.unlink()
                except Exception as e:
                    logger.warning(f"Error checking component {name}: {e}")

        # Check for running processes
        for name, component in list(self._components.items()):
            if component.pid:
                try:
                    process = psutil.Process(component.pid)
                    if process.is_running():
                        # Update heartbeat
                        component.last_heartbeat = time.time()
                    else:
                        component.state = ComponentState.FAILED
                        component.error = "Process exited"
                except psutil.NoSuchProcess:
                    component.state = ComponentState.FAILED
                    component.error = "Process not found"

        return self._components

    def restart_component(self, name: str, command: list[str], port: Optional[int] = None) -> ComponentInfo:
        """Restart a service component."""
        # Check restart limits
        if not self._can_restart(name):
            return ComponentInfo(
                name=name,
                state=ComponentState.FAILED,
                error=f"Restart limit exceeded (max {RESTART_MAX_ATTEMPTS} in {RESTART_WINDOW}s)",
            )

        # Stop if running
        self.stop_component(name)
        time.sleep(1)

        # Start again
        component = self.start_component(name, command, port)

        # Record restart
        if component.state == ComponentState.RUNNING:
            self._record_restart(name)

        return component

    def _get_component(self, name: str) -> Optional[ComponentInfo]:
        """Get component info by name."""
        return self._components.get(name)

    def _check_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        return not self._is_port_listening(port)

    def _is_port_listening(self, port: int) -> bool:
        """Check if a port is currently listening."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _kill_process_on_port(self, port: int) -> bool:
        """Kill the process using a specific port."""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # Check connections for this process
                    connections = proc.connections()
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr.port == port:
                            logger.info(f"Killing process {proc.info['name']} (PID {proc.info['pid']}) on port {port}")
                            proc.terminate()
                            proc.wait(timeout=5)
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.error(f"Failed to kill process on port {port}: {e}")
        return False

    def _can_restart(self, name: str) -> bool:
        """Check if we can restart a component (within limits)."""
        now = time.time()
        history = self._restart_history.get(name, [])

        # Remove old entries outside the window
        history = [t for t in history if (now - t) < RESTART_WINDOW]
        self._restart_history[name] = history

        # Can restart if we have fewer than max attempts
        return len(history) < RESTART_MAX_ATTEMPTS

    def _record_restart(self, name: str) -> None:
        """Record a restart attempt."""
        self._restart_history.setdefault(name, []).append(time.time())

    def cleanup(self) -> None:
        """Clean up all components."""
        # First, discover running components from PID files
        self.get_status()

        # Now stop all discovered components
        for name in list(self._components.keys()):
            self.stop_component(name)


# --- CLI Commands ---

def start_service(port: int = PORTS.service, otel_port: int = PORTS.otel) -> dict:
    """Start the ObserveCo service."""
    manager = ServiceManager()

    # Start OTEL listener (daemon mode via observeco CLI)
    otel_component = manager.start_component(
        "otel_listener",
        [sys.executable, "-m", "observeco", "otel", "listen", "start", "--port", str(otel_port)],
        port=otel_port,
    )

    # Start dashboard (use observeco CLI)
    dashboard_component = manager.start_component(
        "dashboard",
        [sys.executable, "-m", "observeco", "dashboard", "--port", str(port), "--no-browser"],
        port=port,
    )

    return {
        "otel_listener": otel_component.to_dict(),
        "dashboard": dashboard_component.to_dict(),
    }


def stop_service() -> dict:
    """Stop the ObserveCo service."""
    manager = ServiceManager()
    manager.cleanup()
    return {"status": "stopped"}


def get_service_status() -> dict:
    """Get the ObserveCo service status."""
    manager = ServiceManager()
    status = manager.get_status()
    return {name: info.to_dict() for name, info in status.items()}
