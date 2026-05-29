"""Risk engine — classifies tool calls and actions by risk level."""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .platform import get_platform_name


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
    RiskLevel.LOW: "\033[92m",
    RiskLevel.MEDIUM: "\033[92m",
    RiskLevel.HIGH: "\033[93m",
    RiskLevel.CRITICAL: "\033[91m",
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
    """Classify a tool call by risk level."""
    if platform is None:
        platform = get_platform_name()

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
    reset = "\033[0m" if use_ansi else ""

    if level == RiskLevel.CRITICAL:
        status = "DENIED"
    elif level == RiskLevel.HIGH:
        status = "FLAGGED"
    elif auto_approved:
        status = "auto-approved"
    else:
        status = "manual review"

    dim = "\033[2m" if use_ansi else ""
    bold = "\033[1m" if use_ansi else ""

    return f"  {color}{emoji}{reset} {dim}{action}{reset} {color}({status}){reset}"
