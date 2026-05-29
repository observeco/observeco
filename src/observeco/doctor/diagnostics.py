"""Environment diagnostics — check ObserveCo installation health."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
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
            data = json.loads(config_file.read_text())
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
