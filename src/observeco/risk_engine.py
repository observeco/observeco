"""Risk engine — classifies tool calls and actions by risk level."""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from observeco.colors import Color
import sys


def get_platform_name() -> str:
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    elif sys.platform.startswith("linux"):
        return "linux"
    return "unknown"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_EMOJI = {
    RiskLevel.LOW: "✓",
    RiskLevel.MEDIUM: "✓",
    RiskLevel.HIGH: "⚠",
    RiskLevel.CRITICAL: "✗",
}

RISK_COLORS = {
    RiskLevel.LOW: Color.GREEN,
    RiskLevel.MEDIUM: Color.GREEN,
    RiskLevel.HIGH: Color.YELLOW,
    RiskLevel.CRITICAL: Color.RED,
}

# Headless-safe versions (no ANSI)
RISK_COLORS_NOANSI = {
    RiskLevel.LOW: "",
    RiskLevel.MEDIUM: "",
    RiskLevel.HIGH: "[!] ",
    RiskLevel.CRITICAL: "[X] ",
}


@dataclass
class ToolCall:
    """Represents a tool call from an agent."""
    name: str
    arguments: dict
    raw: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        """Parse from various agent runtime formats."""
        # OpenClaw format
        if "name" in data and "arguments" in data:
            args = data["arguments"]
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            return cls(name=data["name"], arguments=args, raw=data)

        # Claude Code format
        if "tool" in data:
            return cls(name=data["tool"], arguments=data.get("input", {}), raw=data)

        # Generic format
        if "type" in data and data["type"] == "toolCall":
            return cls(
                name=data.get("name", "unknown"),
                arguments=data.get("arguments", {}),
                raw=data,
            )

        # Fallback: treat as text action
        return cls(name="text", arguments={"text": str(data)}, raw=data)


@dataclass
class RiskResult:
    """Result of risk classification."""
    level: RiskLevel
    category: str
    reason: str
    action: str  # "auto_approve", "flag", "deny"


# --- Structured Risk Classification ---

# Dangerous command names — structured check based on the command/keyword
_DANGEROUS_COMMANDS = {
    "delete_file", "remove", "unlink", "rmdir",
    "drop_table", "truncate_table", "drop_database",
    "format_disk", "shutdown", "reboot",
    "sudo", "su",
}

_FLAGGED_COMMANDS = {
    "git_push", "git_force_push", "deploy", "release", "publish",
    "ssh", "scp", "rsync",
    "chmod", "chown",
    "set_env", "write_env",
}

_SENSITIVE_ARG_KEYS = {
    "sql", "query", "command", "script", "code",
    "password", "token", "secret", "api_key", "credential",
}

_PRODUCTION_PATHS = [
    "/prod", "/production", "/etc/", "/var/www",
    "production", "prod.db", "main.db",
]


def _classify_structured(tool_call: ToolCall) -> Optional[RiskResult]:
    """Try structured classification by inspecting tool call arguments.

    Looks at the tool name and argument keys/values directly
    rather than concatenating to a text blob for regex search.
    Returns None if no structured rule matched (fall back to regex).
    """
    name = tool_call.name.lower()
    args = tool_call.arguments

    # 1. Check by command name
    if name in _DANGEROUS_COMMANDS:
        return RiskResult(
            level=RiskLevel.CRITICAL,
            category="destructive",
            reason=f"Dangerous command: {tool_call.name}",
            action="deny",
        )

    if name in _FLAGGED_COMMANDS:
        return RiskResult(
            level=RiskLevel.HIGH,
            category="deploy" if name.startswith("git_") or name in ("deploy", "release", "publish") else "privilege",
            reason=f"Flagged command: {tool_call.name}",
            action="flag",
        )

    # 2. Check for SQL injection / dangerous SQL
    for key in ("sql", "query", "command"):
        val = args.get(key, "")
        if isinstance(val, str) and re.search(
            r"\b(drop\s+table|truncate|delete\s+from|drop\s+database)\b",
            val, re.IGNORECASE
        ):
            return RiskResult(
                level=RiskLevel.CRITICAL,
                category="database",
                reason=f"Dangerous SQL in argument '{key}'",
                action="deny",
            )

    # 3. Check for credentials in args
    for key in args:
        if key in ("password", "token", "secret", "api_key", "credential", "auth"):
            return RiskResult(
                level=RiskLevel.HIGH,
                category="credentials",
                reason=f"Sensitive argument key: {key}",
                action="flag",
            )

    # 4. Check paths for production paths
    for key in ("path", "filepath", "dest", "destination", "target"):
        val = str(args.get(key, ""))
        for prod_path in _PRODUCTION_PATHS:
            if prod_path in val:
                return RiskResult(
                    level=RiskLevel.HIGH,
                    category="destructive",
                    reason=f"Path '{val}' contains production location",
                    action="flag",
                )

    # 5. Check URL args for dangerous hosts
    for key in ("url", "endpoint", "host"):
        val = str(args.get(key, ""))
        if "prod" in val.lower() or "production" in val.lower():
            return RiskResult(
                level=RiskLevel.HIGH,
                category="network",
                reason=f"URL '{val}' targets production endpoint",
                action="flag",
            )

    return None


# --- Risk Rules ---

# Critical patterns: always deny
CRITICAL_PATTERNS = [
    (r"\b(drop\s+table|truncate|delete\s+from|delete\s+all\s+.*\s+from)\b", "database", "Database modification"),
    (r"\b(rm\s+-rf\s+/|rmdir\s+/s\s+/q|format\s+[a-z]:)\b", "destructive", "Destructive filesystem operation"),
    (r"\b DROP\s+DATABASE\b", "database", "Database deletion"),
    (r"\b(production|prod)\b.*\b(delete|drop|truncate|destroy|wipe|nuke)\b", "destructive", "Destructive production action"),
    (r"\b(delete|drop|truncate|destroy|wipe|nuke)\b.*\b(production|prod|database|db|all)\b", "destructive", "Destructive action on production data"),
]

# High patterns: always flag
HIGH_PATTERNS = [
    (r"\b(git\s+push|git\s+force|push\s+--force)\b", "deploy", "Code deployment"),
    (r"\b(deploy|release|ship|publish)\b", "deploy", "Deployment action"),
    (r"\b(ssh|scp|rsync)\b", "network", "Remote access"),
    (r"\b(sudo|su\s+|chmod\s+777)\b", "privilege", "Privilege escalation"),
    (r"\b(env|secret|token|password|key|credential)\b.*=", "credentials", "Credential access"),
    (r"\b(rm\s+|del\s+|unlink|remove)\b", "destructive", "File deletion"),
]

# Medium patterns
MEDIUM_PATTERNS = [
    (r"\b(edit|write|create|modify|update|add|append)\b", "write", "Write operation"),
    (r"\b(test|pytest|npm\s+test|jest)\b", "test", "Test execution"),
    (r"\b(install|pip\s+install|npm\s+install|apt\s+install)\b", "install", "Package installation"),
    (r"\b(curl|wget|fetch|http|request)\b", "network", "Network request"),
    (r"\b(run|exec|execute|python|node|bash)\b.*\b(script|file)\b", "exec", "Script execution"),
]

# Read-only patterns: always safe
READ_PATTERNS = [
    (r"\b(read|cat|less|head|tail|grep|find|ls|dir|echo)\b", "read", "Read-only operation"),
    (r"\b(status|list|show|info|version|help)\b", "read", "Information query"),
]


def classify_tool_call(tool_call: ToolCall, platform: str = None) -> RiskResult:
    """Classify a tool call by risk level.

    Tries structured classification first (inspects tool name and
    argument keys/values directly). Falls back to regex-based text
    classification for unstructured/text-based tool calls.
    """
    if platform is None:
        platform = get_platform_name()

    # Try structured classification first
    structured_result = _classify_structured(tool_call)
    if structured_result is not None:
        return structured_result

    # Fall back to regex-based text classification
    text = f"{tool_call.name} {json.dumps(tool_call.arguments)}".lower()

    # Check critical
    for pattern, category, reason in CRITICAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return RiskResult(
                level=RiskLevel.CRITICAL,
                category=category,
                reason=reason,
                action="deny",
            )

    # Check high
    for pattern, category, reason in HIGH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return RiskResult(
                level=RiskLevel.HIGH,
                category=category,
                reason=reason,
                action="flag",
            )

    # Check medium
    for pattern, category, reason in MEDIUM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return RiskResult(
                level=RiskLevel.MEDIUM,
                category=category,
                reason=reason,
                action="auto_approve",
            )

    # Check read-only
    for pattern, category, reason in READ_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return RiskResult(
                level=RiskLevel.LOW,
                category=category,
                reason=reason,
                action="auto_approve",
            )

    # Default: low risk
    return RiskResult(
        level=RiskLevel.LOW,
        category="unknown",
        reason="No risk pattern matched",
        action="auto_approve",
    )


def classify_text_action(action: str, platform: str = None) -> RiskResult:
    """Classify a text-based action (legacy compatibility)."""
    tc = ToolCall(name="text", arguments={"text": action})
    return classify_tool_call(tc, platform)


def get_risk_color(level: RiskLevel, use_ansi: bool = True) -> str:
    """Get color prefix for risk level."""
    if not use_ansi:
        return RISK_COLORS_NOANSI.get(level, "")
    return RISK_COLORS.get(level, "")


def format_risk(level: RiskLevel, action: str, auto_approved: bool, use_ansi: bool = True) -> str:
    """Format a risk assessment line for display."""
    emoji = RISK_EMOJI.get(level, "?")
    color = get_risk_color(level, use_ansi)
    reset = Color.RESET if use_ansi else ""

    if level == RiskLevel.CRITICAL:
        status = "DENIED"
    elif level == RiskLevel.HIGH:
        status = "FLAGGED"
    elif auto_approved:
        status = "auto-approved"
    else:
        status = "manual review"

    dim = Color.DIM if use_ansi else ""
    bright = Color.BRIGHT if use_ansi else ""

    return f"  {color}{emoji}{reset} {dim}{action}{reset} {color}({status}){reset}"
