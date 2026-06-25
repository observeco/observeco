"""Health monitoring system for ObserveCo.

Provides Level 1 (operational) and Level 2 (functional) health checks
with auto-recovery capabilities.

GS-019: Data & Observability Continuity
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import psutil

from .dirs import get_data_dir

logger = logging.getLogger(__name__)

# Health check constants
HEALTH_CHECK_INTERVAL_L1 = 30  # seconds
HEALTH_CHECK_INTERVAL_L2 = 60  # seconds
HEALTH_CHECK_INTERVAL_RESOURCE = 300  # 5 minutes
HEALTH_STALE_THRESHOLD = 300  # 5 minutes — consider health stale
HEALTH_RESTART_MAX_ATTEMPTS = 3
HEALTH_RESTART_WINDOW = 300  # 5 minutes


class HealthLevel(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentStatus(Enum):
    """Individual component status."""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthIssue:
    """A single health issue."""
    component: str
    level: HealthLevel
    message: str
    timestamp: float = field(default_factory=time.time)
    auto_recovered: bool = False
    recovery_action: Optional[str] = None


@dataclass
class HealthStatus:
    """Overall health status object."""
    level1: dict[str, ComponentStatus] = field(default_factory=dict)
    level2: dict[str, ComponentStatus] = field(default_factory=dict)
    overall: HealthLevel = HealthLevel.UNKNOWN
    last_check: float = 0.0
    issues: list[HealthIssue] = field(default_factory=list)
    resources: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "level1": {k: v.value for k, v in self.level1.items()},
            "level2": {k: v.value for k, v in self.level2.items()},
            "overall": self.overall.value,
            "last_check": self.last_check,
            "last_check_ago": time.time() - self.last_check if self.last_check else None,
            "issues": [
                {
                    "component": i.component,
                    "level": i.level.value,
                    "message": i.message,
                    "timestamp": i.timestamp,
                    "auto_recovered": i.auto_recovered,
                    "recovery_action": i.recovery_action,
                }
                for i in self.issues
            ],
            "resources": self.resources,
        }


class HealthChecker:
    """Health monitoring system with L1 + L2 checks."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_data_dir() / "pulse.db"
        self.status = HealthStatus()
        self._restart_history: dict[str, list[float]] = {}
        self._last_checks: dict[str, float] = {}

    def check_all(self) -> HealthStatus:
        """Run all health checks and return status."""
        # Level 1: Operational checks
        self.status.level1["otel_listener"] = self._check_otel_listener()
        self.status.level1["dashboard"] = self._check_dashboard()
        self.status.level1["database"] = self._check_database()
        self.status.level1["ports"] = self._check_ports()

        # Level 2: Functional checks
        self.status.level2["data_flow"] = self._check_data_flow()
        self.status.level2["schema"] = self._check_schema()
        self.status.level2["disk"] = self._check_disk()
        self.status.level2["resources"] = self._check_resources()

        # Calculate overall status
        self.status.overall = self._calculate_overall()
        self.status.last_check = time.time()

        return self.status

    def check_l1(self) -> HealthStatus:
        """Run only Level 1 checks (faster)."""
        self.status.level1["otel_listener"] = self._check_otel_listener()
        self.status.level1["dashboard"] = self._check_dashboard()
        self.status.level1["database"] = self._check_database()
        self.status.level1["ports"] = self._check_ports()

        self.status.overall = self._calculate_overall()
        self.status.last_check = time.time()

        return self.status

    def is_stale(self) -> bool:
        """Check if health status is stale (no recent check)."""
        if not self.status.last_check:
            return True
        return (time.time() - self.status.last_check) > HEALTH_STALE_THRESHOLD

    # --- Level 1 Checks: Operational ---

    def _check_otel_listener(self) -> ComponentStatus:
        """Check if OTEL listener is responding on port 4318."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 4318))
            sock.close()
            if result == 0:
                return ComponentStatus.UP
            return ComponentStatus.DOWN
        except Exception as e:
            logger.debug(f"OTEL listener check failed: {e}")
            return ComponentStatus.DOWN

    def _check_dashboard(self) -> ComponentStatus:
        """Check if dashboard is responding — always UP since this check runs inside the dashboard process."""
        return ComponentStatus.UP

    def _check_database(self) -> ComponentStatus:
        """Check if database is writable."""
        try:
            if not self.db_path.exists():
                return ComponentStatus.DOWN

            conn = sqlite3.connect(str(self.db_path), timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")

            # Test write
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _health_check (
                    id INTEGER PRIMARY KEY,
                    ts REAL
                )
            """)
            conn.execute("INSERT INTO _health_check (ts) VALUES (?)", (time.time(),))
            conn.execute("DELETE FROM _health_check WHERE id = last_insert_rowid()")
            conn.commit()
            conn.close()

            return ComponentStatus.UP
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                logger.warning(f"Database locked: {e}")
                return ComponentStatus.DEGRADED
            logger.error(f"Database check failed: {e}")
            return ComponentStatus.DOWN
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return ComponentStatus.DOWN

    def _check_ports(self) -> ComponentStatus:
        """Check if required ports are in use by ObserveCo components."""
        ports_in_use = {}
        # ponytail: checks hardcoded ports (4318 OTel + 9119 dashboard default).
        # If dashboard runs on a non-default port, this check reflects that.
        for port in [4318, 9119]:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                ports_in_use[port] = result == 0
            except Exception:
                ports_in_use[port] = False

        # Both ports should be in use (by ObserveCo components)
        if all(ports_in_use.values()):
            return ComponentStatus.UP
        elif any(ports_in_use.values()):
            return ComponentStatus.DEGRADED
        else:
            return ComponentStatus.DOWN

    # --- Level 2 Checks: Functional ---

    def _check_data_flow(self) -> ComponentStatus:
        """Check if data is flowing (recent OTEL events)."""
        try:
            if not self.db_path.exists():
                return ComponentStatus.DOWN

            conn = sqlite3.connect(str(self.db_path), timeout=5)
            conn.row_factory = sqlite3.Row

            # Check for recent events in pulse_log
            try:
                cur = conn.execute(
                    "SELECT MAX(timestamp) as last_ts FROM pulse_log"
                )
                row = cur.fetchone()
                if row and row["last_ts"]:
                    age_seconds = time.time() - row["last_ts"]
                    if age_seconds < 300:  # 5 minutes
                        return ComponentStatus.UP
                    elif age_seconds < 3600:  # 1 hour
                        return ComponentStatus.DEGRADED
                    else:
                        return ComponentStatus.DOWN
            except sqlite3.OperationalError:
                pass  # Table might not exist yet

            conn.close()
            return ComponentStatus.UNKNOWN  # No data yet
        except Exception as e:
            logger.debug(f"Data flow check failed: {e}")
            return ComponentStatus.UNKNOWN

    def _check_schema(self) -> ComponentStatus:
        """Check if database schema is current."""
        try:
            if not self.db_path.exists():
                return ComponentStatus.DOWN

            conn = sqlite3.connect(str(self.db_path), timeout=5)
            try:
                cur = conn.execute(
                    "SELECT value FROM _meta WHERE key='schema_version'"
                )
                row = cur.fetchone()
                if row:
                    from .db import SCHEMA_VERSION
                    db_version = int(row[0])
                    if db_version >= SCHEMA_VERSION:
                        return ComponentStatus.UP
                    else:
                        return ComponentStatus.DEGRADED
            except sqlite3.OperationalError:
                pass
            conn.close()

            return ComponentStatus.UNKNOWN
        except Exception as e:
            logger.debug(f"Schema check failed: {e}")
            return ComponentStatus.UNKNOWN

    def _check_disk(self) -> ComponentStatus:
        """Check if disk usage is healthy."""
        try:
            data_dir = get_data_dir()
            usage = psutil.disk_usage(str(data_dir))
            percent = usage.percent

            self.status.resources["disk_percent"] = percent
            self.status.resources["disk_free_gb"] = usage.free / (1024**3)

            if percent < 80:
                return ComponentStatus.UP
            elif percent < 90:
                return ComponentStatus.DEGRADED
            else:
                return ComponentStatus.DOWN
        except Exception as e:
            logger.debug(f"Disk check failed: {e}")
            return ComponentStatus.UNKNOWN

    def _check_resources(self) -> ComponentStatus:
        """Check CPU and memory usage."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.status.resources["cpu_percent"] = cpu_percent

            # Memory
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / (1024**2)
            self.status.resources["memory_mb"] = mem_mb

            # File descriptors (Unix only)
            try:
                fds = process.num_fds()
                self.status.resources["open_fds"] = fds
            except AttributeError:
                pass  # Windows

            # Evaluate
            if cpu_percent < 50 and mem_mb < 200:
                return ComponentStatus.UP
            elif cpu_percent < 80 and mem_mb < 500:
                return ComponentStatus.DEGRADED
            else:
                return ComponentStatus.DEGRADED  # Not critical, but warn
        except Exception as e:
            logger.debug(f"Resource check failed: {e}")
            return ComponentStatus.UNKNOWN

    # --- Overall Status Calculation ---

    def _calculate_overall(self) -> HealthLevel:
        """Calculate overall health from L1 + L2 checks."""
        all_statuses = list(self.status.level1.values()) + list(self.status.level2.values())

        # Any L1 DOWN = CRITICAL
        if any(s == ComponentStatus.DOWN for s in self.status.level1.values()):
            return HealthLevel.CRITICAL

        # Any L1 DEGRADED or L2 DOWN = DEGRADED
        if any(s == ComponentStatus.DEGRADED for s in self.status.level1.values()):
            return HealthLevel.DEGRADED
        if any(s == ComponentStatus.DOWN for s in self.status.level2.values()):
            return HealthLevel.DEGRADED

        # All UP or UNKNOWN = HEALTHY
        return HealthLevel.HEALTHY

    # --- Auto-Recovery ---

    def can_restart(self, component: str) -> bool:
        """Check if we can attempt auto-restart (within limits)."""
        now = time.time()
        history = self._restart_history.get(component, [])

        # Remove old entries outside the window
        history = [t for t in history if (now - t) < HEALTH_RESTART_WINDOW]
        self._restart_history[component] = history

        return len(history) < HEALTH_RESTART_MAX_ATTEMPTS

    def record_restart(self, component: str) -> None:
        """Record a restart attempt."""
        self._restart_history.setdefault(component, []).append(time.time())

    def add_issue(self, issue: HealthIssue) -> None:
        """Add a health issue."""
        self.status.issues.append(issue)

    def clear_resolved_issues(self) -> None:
        """Remove issues that are no longer active."""
        self.status.issues = [
            i for i in self.status.issues
            if not i.auto_recovered
        ]
