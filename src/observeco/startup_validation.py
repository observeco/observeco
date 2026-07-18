"""Startup validation — five pre-flight checks before dashboard/watch launch.

Checks 1-3 (data dir, DB writable, ports) are FATAL → exit 1 on failure.
Check 4 (config) is a WARNING → print warning, continue startup.

ponytail: Sequential checks — runs once at startup, <100ms total. If the
startup sequence ever grows beyond 10 checks, switch to a parallel runner
with aggregated results.
"""

from __future__ import annotations

import socket
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from observeco.dashboard.config import PORTS


@dataclass
class CheckResult:
    name: str
    ok: bool
    fatal: bool
    message: str = ""
    fix: str = ""


@dataclass
class ValidationResult:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def fatal_failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.ok and c.fatal]

    @property
    def warnings(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.ok and not c.fatal]

    @property
    def passed(self) -> bool:
        return not self.fatal_failures


def _find_port_owner(port: int) -> str:
    """Return process name using the port, or 'unknown process'."""
    try:
        import psutil

        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port:
                if conn.pid:
                    try:
                        return psutil.Process(conn.pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return f"PID {conn.pid}"
    except Exception:
        pass
    return "unknown process"


def check_data_dir(data_dir: Path) -> CheckResult:
    """Check 1 (FATAL): data directory exists — create it if missing."""
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        return CheckResult(name="data_dir", ok=True, fatal=True)
    except OSError as exc:
        db_dir = str(data_dir)
        return CheckResult(
            name="data_dir",
            ok=False,
            fatal=True,
            message=f"Error: Cannot create data directory {db_dir}\n  {exc}",
            fix=f'Fix: Run "mkdir -p {db_dir}" or check filesystem permissions',
        )


def check_db_writable(db_path: Path) -> CheckResult:
    """Check 2 (FATAL): SQLite DB is writable — PRAGMA quick_check."""
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA quick_check")
        conn.close()
        return CheckResult(name="db_writable", ok=True, fatal=True)
    except Exception as exc:
        db_dir = str(db_path.parent)
        return CheckResult(
            name="db_writable",
            ok=False,
            fatal=True,
            message=f"Error: Cannot write to {db_path}\n  {exc}",
            fix=f'Fix: Run "mkdir -p {db_dir}" or check filesystem permissions',
        )


def check_port(port: int) -> CheckResult:
    """Check 3 (FATAL): port is available — socket bind test."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        s.close()
        return CheckResult(name=f"port_{port}", ok=True, fatal=True)
    except OSError:
        owner = _find_port_owner(port)
        alt_port = port + 1
        return CheckResult(
            name=f"port_{port}",
            ok=False,
            fatal=True,
            message=f"Error: Port {port} is in use by {owner}",
            fix=f'Fix: Use "--port {alt_port}" or stop the other process',
        )


# Known keys and their valid values for the ObserveCo config file.
_VALID_CONFIG_VALUES: dict[str, list] = {
    "log_level": ["debug", "info", "warning", "error"],
}


def check_config(config_path: Path) -> CheckResult:
    """Check 4 (WARNING): config file is valid YAML with recognized values."""
    if not config_path.exists():
        # First-run: no config → use defaults, not an error.
        return CheckResult(name="config", ok=True, fatal=False)

    try:
        import yaml

        content = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return CheckResult(
            name="config",
            ok=False,
            fatal=False,
            message=f"Warning: Config file {config_path} is not valid YAML\n  {exc}",
            fix="Fix: Check YAML syntax — run `observeco doctor run` for guided repair",
        )

    for key, valid_values in _VALID_CONFIG_VALUES.items():
        if key in content:
            actual = content[key]
            if actual not in valid_values:
                return CheckResult(
                    name="config",
                    ok=False,
                    fatal=False,
                    message=f'Warning: Config file {config_path} has invalid value for "{key}"',
                    fix=f'Fix: Expected one of {valid_values}, got "{actual}"',
                )

    return CheckResult(name="config", ok=True, fatal=False)


def run_checks(
    data_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    ports: Optional[list[int]] = None,
    config_path: Optional[Path] = None,
    print_output: bool = True,
    exit_on_fatal: bool = True,
) -> ValidationResult:
    """Run all startup checks.

    Fatal failures print to stderr and call sys.exit(1) unless exit_on_fatal=False.
    Warnings print to stderr and allow startup to continue.
    """
    from observeco.dirs import get_data_dir as _get_data_dir

    if data_dir is None:
        data_dir = _get_data_dir()
    if db_path is None:
        db_path = data_dir / "pulse.db"
    if ports is None:
        ports = [PORTS.otel, PORTS.service]
    if config_path is None:
        config_path = data_dir / "config.yaml"

    result = ValidationResult()

    result.checks.append(check_data_dir(data_dir))
    result.checks.append(check_db_writable(db_path))
    for port in ports:
        result.checks.append(check_port(port))
    result.checks.append(check_config(config_path))

    if print_output:
        for check in result.checks:
            if not check.ok:
                print(check.message, file=sys.stderr)
                print(check.fix, file=sys.stderr)

    if exit_on_fatal and result.fatal_failures:
        sys.exit(1)

    return result


if __name__ == "__main__":
    # Self-check: validate the current environment.
    r = run_checks(ports=[PORTS.otel, PORTS.service], exit_on_fatal=False)
    if r.passed:
        print("All startup checks passed.")
    else:
        for f in r.fatal_failures:
            print(f.message)
            print(f.fix)
        sys.exit(1)
