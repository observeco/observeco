"""Environment diagnostics — check ObserveCo installation health."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiagnosticCheck:
    """A single diagnostic check result."""
    name: str
    status: str  # "ok" | "warning" | "error"
    message: str
    auto_fix: Optional[str] = None  # Command to auto-fix
    category: str = "general"


@dataclass
class DiagnosticReport:
    """Full diagnostic report."""
    checks: list[DiagnosticCheck] = field(default_factory=list)
    os_name: str = ""
    python_version: str = ""
    packages: list[str] = field(default_factory=list)
    config_state: dict = field(default_factory=dict)

    @property
    def issues(self) -> list[DiagnosticCheck]:
        return [c for c in self.checks if c.status != "ok"]

    @property
    def ok_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "ok")

    def to_dict(self) -> dict:
        return {
            "os": self.os_name,
            "python_version": self.python_version,
            "checks": [
                {"name": c.name, "status": c.status, "message": c.message, "category": c.category}
                for c in self.checks
            ],
            "packages": self.packages,
            "config": self.config_state,
        }

    def to_text(self) -> str:
        lines = [
            f"Environment: {self.os_name}",
            f"Python: {self.python_version}",
            f"Checks: {self.ok_count} passed, {len(self.issues)} issues",
            "",
        ]
        for check in self.checks:
            icon = {"ok": "✓", "warning": "⚠", "error": "✗"}.get(check.status, "?")
            lines.append(f"  {icon} [{check.category}] {check.name}: {check.message}")
            if check.auto_fix:
                lines.append(f"    → Fix: {check.auto_fix}")
        return "\n".join(lines)


def run_diagnostics() -> DiagnosticReport:
    """Run all diagnostic checks and return a report."""
    report = DiagnosticReport(
        os_name=f"{platform.system()} {platform.release()}",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    # Package checks
    report.checks.extend(_check_packages())
    report.packages = _get_installed_packages()

    # Environment variable checks
    report.checks.extend(_check_env_vars())

    # Config checks
    report.checks.extend(_check_config())
    report.config_state = _get_config_state()

    # Network checks
    report.checks.extend(_check_network())

    # Permission checks
    report.checks.extend(_check_permissions())

    # LLM provider detection
    report.checks.extend(_check_llm_providers())

    return report


def check_data_health() -> list[DiagnosticCheck]:
    """GS-019: Data continuity health checks.

    Checks:
    1. Schema version (compare current vs expected)
    2. Backup recency (last backup < 7 days old)
    3. Stranded migration tables
    """
    from ..db import SCHEMA_VERSION, Database

    checks = []
    try:
        db = Database()
        conn = db._get_conn()

        # 1. Schema version check
        try:
            cur = conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
            row = cur.fetchone()
            meta_version = int(row["value"]) if row else 1
            if meta_version < SCHEMA_VERSION:
                checks.append(DiagnosticCheck(
                    name="schema_version",
                    status="error",
                    message=f"Database version {meta_version} < expected {SCHEMA_VERSION}. Pending migrations.",
                    auto_fix="Restart the application to run migrations",
                    category="data_health"
                ))
            elif meta_version > SCHEMA_VERSION:
                checks.append(DiagnosticCheck(
                    name="schema_version",
                    status="warning",
                    message=f"Database version {meta_version} > code version {SCHEMA_VERSION}. Possible downgrade.",
                    category="data_health"
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="schema_version",
                    status="ok",
                    message=f"Schema version {meta_version} (current)",
                    category="data_health"
                ))
        except Exception as e:
            checks.append(DiagnosticCheck(
                name="schema_version",
                status="error",
                message=f"Cannot read schema version: {e}",
                category="data_health"
            ))

        # 2. Backup recency
        import time
        backup_dir = db.db_path.parent / "backups"
        if backup_dir.exists():
            backups = sorted(backup_dir.glob("pulse_*.db"))
            if backups:
                last_backup_age_days = (time.time() - backups[-1].stat().st_mtime) / 86400
                if last_backup_age_days > 7:
                    checks.append(DiagnosticCheck(
                        name="backup_recency",
                        status="warning",
                        message=f"Last backup was {last_backup_age_days:.0f} days ago",
                        category="data_health"
                    ))
                else:
                    checks.append(DiagnosticCheck(
                        name="backup_recency",
                        status="ok",
                        message=f"Last backup: {last_backup_age_days:.1f} days ago",
                        category="data_health"
                    ))
            else:
                checks.append(DiagnosticCheck(
                    name="backup_exists",
                    status="warning",
                    message="No backups found",
                    category="data_health"
                ))
        else:
            checks.append(DiagnosticCheck(
                name="backup_exists",
                status="warning",
                message="No backup directory found",
                category="data_health"
            ))

        # 3. Stranded migration tables
        for temp in ["pathway_nodes_v11", "alert_subscriptions_v15"]:
            exists = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (temp,)
            ).fetchone()[0] > 0
            if exists:
                checks.append(DiagnosticCheck(
                    name=f"stranded_table_{temp}",
                    status="error",
                    message=f"Table {temp} exists — partial migration not completed",
                    auto_fix="Restart the application to auto-recover",
                    category="data_health"
                ))

        # 4. Row counts summary
        row_counts = {}
        for table in ["pulse_log", "compress_log", "heal_events", "token_logs"]:
            try:
                cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
                row_counts[table] = cur.fetchone()[0]
            except Exception:
                row_counts[table] = 0

        total_rows = sum(row_counts.values())
        checks.append(DiagnosticCheck(
            name="row_counts",
            status="ok",
            message=f"User data: {total_rows:,} rows across {len(row_counts)} tables",
            category="data_health"
        ))

        # 5. DB integrity check (fail loud if corrupt)
        try:
            from ..data_integrity import run_integrity_check
            chk = run_integrity_check(str(db.db_path))
            if chk["passed"]:
                checks.append(DiagnosticCheck(
                    name="db_integrity",
                    status="ok",
                    message=f"Database integrity verified ({chk['method']})",
                    category="data_health"
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="db_integrity",
                    status="error",
                    message=f"DB integrity FAILED: {chk['message']}. "
                            f"Run `observeco doctor restore` from a verified backup.",
                    auto_fix="observeco doctor restore",
                    category="data_health"
                ))
        except Exception as e:
            checks.append(DiagnosticCheck(
                name="db_integrity",
                status="error",
                message=f"Cannot run integrity check: {e}",
                category="data_health"
            ))

        # 6. Emptiness sanity: schema exists but 0 user rows AND a backup has data
        #    = classic silent-loss signal (corrupt DB served empty). Flag CRITICAL.
        try:
            backup_dir = db.db_path.parent / "backups"
            has_data_backup = False
            if backup_dir.exists():
                for b in sorted(backup_dir.glob("pulse_*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
                    try:
                        import sqlite3 as _s
                        bc = _s.connect(str(b))
                        rows = bc.execute(
                            "SELECT (SELECT COUNT(*) FROM token_logs)+"
                            "(SELECT COUNT(*) FROM pulse_log)").fetchone()[0]
                        bc.close()
                        if rows > 0:
                            has_data_backup = True
                            break
                    except Exception:
                        continue
            if total_rows == 0 and has_data_backup:
                checks.append(DiagnosticCheck(
                    name="db_empty_silent_loss",
                    status="error",
                    message="Live DB has 0 user rows but a backup contains data — "
                            "possible silent data loss. Restore from backup.",
                    auto_fix="observeco doctor restore",
                    category="data_health"
                ))
        except Exception:
            pass  # best-effort sanity; don't fail the whole diagnose on this

        db.close()
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="data_health_error",
            status="error",
            message=f"Cannot run data health check: {e}",
            category="data_health"
        ))

    return checks


def _check_packages() -> list[DiagnosticCheck]:
    """Check required and optional packages."""
    checks = []

    required = {
        "colorama": "Cross-platform terminal colors",
        "platformdirs": "OS-standard config locations",
    }

    optional = {
        "typer": "CLI framework",
        "rich": "Rich terminal output",
        "fastapi": "Dashboard server",
        "uvicorn": "ASGI server",
        "httpx": "HTTP client",
        "pynacl": "Discord Ed25519 webhook verification",
        "keyring": "OS keychain for secrets",
    }

    for pkg, desc in required.items():
        try:
            __import__(pkg)
            checks.append(DiagnosticCheck(
                name=f"{pkg} installed",
                status="ok",
                message=f"{desc} — required",
                category="packages",
            ))
        except ImportError:
            checks.append(DiagnosticCheck(
                name=f"{pkg} missing",
                status="error",
                message=f"{desc} — required package not installed",
                auto_fix=f"pip install {pkg}",
                category="packages",
            ))

    for pkg, desc in optional.items():
        try:
            __import__(pkg)
            checks.append(DiagnosticCheck(
                name=f"{pkg} installed",
                status="ok",
                message=f"{desc} — optional",
                category="packages",
            ))
        except ImportError:
            checks.append(DiagnosticCheck(
                name=f"{pkg} not installed",
                status="warning",
                message=f"{desc} — optional, some features may be limited",
                auto_fix=f"pip install {pkg}",
                category="packages",
            ))

    return checks


def _check_env_vars() -> list[DiagnosticCheck]:
    """Check environment variables for channel adapters."""
    checks = []

    slack_vars = {
        "OBSERVECO_SLACK_BOT_TOKEN": "Slack bot token",
        "OBSERVECO_SLACK_SIGNING_SECRET": "Slack signing secret",
    }

    discord_vars = {
        "OBSERVECO_DISCORD_BOT_TOKEN": "Discord bot token",
        "OBSERVECO_DISCORD_PUBLIC_KEY": "Discord public key",
    }

    telegram_vars = {
        "OBSERVECO_TG_BOT_TOKEN": "Telegram bot token",
        "OBSERVECO_TG_CHAT_ID": "Telegram chat ID",
    }

    llm_vars = {
        "OPENAI_API_KEY": "OpenAI API key",
        "ANTHROPIC_API_KEY": "Anthropic API key",
        "GOOGLE_API_KEY": "Google API key",
    }

    for var, desc in {**slack_vars, **discord_vars, **telegram_vars}.items():
        val = os.environ.get(var, "")
        if val:
            checks.append(DiagnosticCheck(
                name=f"{var} set",
                status="ok",
                message=f"{desc} — configured",
                category="env_vars",
            ))
        else:
            checks.append(DiagnosticCheck(
                name=f"{var} not set",
                status="warning",
                message=f"{desc} — not configured",
                category="env_vars",
            ))

    # LLM keys (informational)
    found_llm = []
    for var, desc in llm_vars.items():
        if os.environ.get(var):
            found_llm.append(desc)

    if found_llm:
        checks.append(DiagnosticCheck(
            name="LLM providers available",
            status="ok",
            message=f"Found: {', '.join(found_llm)} — can use for doctor troubleshooting",
            category="env_vars",
        ))
    else:
        checks.append(DiagnosticCheck(
            name="No LLM provider keys found",
            status="warning",
            message="No OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY — doctor will use static help",
            category="env_vars",
        ))

    return checks


def _check_config() -> list[DiagnosticCheck]:
    """Check configuration files."""
    checks = []

    from observeco.dirs import get_data_dir
    config_dir = get_data_dir()
    config_file = config_dir / "config.json"

    if config_file.exists():
        try:
            json.loads(config_file.read_text())
            checks.append(DiagnosticCheck(
                name="Config file valid",
                status="ok",
                message=f"Config at {config_file}",
                category="config",
            ))
        except json.JSONDecodeError:
            import platform
            if platform.system() == "Windows":
                fix = f"del {config_file} && observeco init"
            else:
                fix = f"rm {config_file} && observeco init"
            checks.append(DiagnosticCheck(
                name="Config file corrupt",
                status="error",
                message=f"Config at {config_file} is not valid JSON",
                auto_fix=fix,
                category="config",
            ))
    else:
        checks.append(DiagnosticCheck(
            name="No config file",
            status="warning",
            message="No config found — run `observeco init` to create one",
            auto_fix="observeco init",
            category="config",
        ))

    return checks


def _check_network() -> list[DiagnosticCheck]:
    """Check network connectivity."""
    checks = []

    # Check if we can reach common APIs
    endpoints = {
        "https://api.openai.com": "OpenAI API",
        "https://api.anthropic.com": "Anthropic API",
        "https://slack.com": "Slack API",
        "https://discord.com": "Discord API",
    }

    for url, name in endpoints.items():
        try:
            import urllib.request
            req = urllib.request.Request(url, method="HEAD")
            urllib.request.urlopen(req, timeout=5)
            checks.append(DiagnosticCheck(
                name=f"{name} reachable",
                status="ok",
                message=f"{name} is accessible",
                category="network",
            ))
        except Exception:
            checks.append(DiagnosticCheck(
                name=f"{name} unreachable",
                status="warning",
                message=f"Cannot reach {name} — may be blocked by firewall/proxy",
                category="network",
            ))

    return checks


def _check_permissions() -> list[DiagnosticCheck]:
    """Check file system permissions."""
    checks = []

    from observeco.dirs import get_data_dir

    for name, dir_path in [("Data", get_data_dir()), ("Config", get_data_dir())]:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            test_file = dir_path / ".observeco_test"
            test_file.write_text("test")
            test_file.unlink()
            checks.append(DiagnosticCheck(
                name=f"{name} directory writable",
                status="ok",
                message=f"{dir_path} is writable",
                category="permissions",
            ))
        except PermissionError:
            checks.append(DiagnosticCheck(
                name=f"{name} directory not writable",
                status="error",
                message=f"Cannot write to {dir_path}",
                category="permissions",
            ))

    return checks


def _check_llm_providers() -> list[DiagnosticCheck]:
    """Detect available LLM providers."""
    checks = []

    providers = []

    # Check major cloud providers
    env_keys = {
        "OPENAI_API_KEY": "OpenAI",
        "ANTHROPIC_API_KEY": "Anthropic",
        "GOOGLE_API_KEY": "Google",
        "GEMINI_API_KEY": "Google Gemini",
        "DEEPSEEK_API_KEY": "DeepSeek",
        "MISTRAL_API_KEY": "Mistral",
        "GROQ_API_KEY": "Groq",
        "TOGETHER_API_KEY": "Together AI",
        "OPENROUTER_API_KEY": "OpenRouter",
    }

    for env_var, name in env_keys.items():
        if os.environ.get(env_var):
            providers.append(name)

    # Check local servers
    local_servers = {
        "http://localhost:11434/api/tags": "Ollama",
        "http://localhost:1234/v1/models": "LM Studio",
        "http://localhost:8000/v1/models": "vLLM",
        "http://localhost:5000/v1/models": "TextGen",
        "http://localhost:8080/v1/models": "LocalAI",
    }

    for url, name in local_servers.items():
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=2)
            providers.append(name)
        except Exception:
            pass

    if providers:
        checks.append(DiagnosticCheck(
            name="LLM providers detected",
            status="ok",
            message=f"Available: {', '.join(providers)}",
            category="llm",
        ))
    else:
        checks.append(DiagnosticCheck(
            name="No LLM providers detected",
            status="warning",
            message="Doctor will use static help docs (set any LLM API key for AI-powered troubleshooting)",
            category="llm",
        ))

    return checks


def _get_installed_packages() -> list[str]:
    """Get list of installed packages."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            return [f"{p['name']}=={p['version']}" for p in packages]
    except Exception:
        pass
    return []


def _get_config_state() -> dict:
    """Get current config state."""
    try:
        from observeco.dirs import get_data_dir
        config_file = get_data_dir() / "config.json"
        if config_file.exists():
            return json.loads(config_file.read_text())
    except Exception:
        pass
    return {}
