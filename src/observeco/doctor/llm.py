"""LLM-powered troubleshooting — thin shim over llm_service.

This module keeps doctor-specific prompts, parsing, and safety validation.
The core provider detection, cost tracking, caching, and gating now live
in observeco/llm_service/ (shared across all consumers).
"""

from __future__ import annotations

from observeco.llm_service import (
    LLMProvider,
    detect_providers,
    get_auto_provider,
    ask as _ask_llm,
)
from .diagnostics import DiagnosticReport, DiagnosticCheck


SYSTEM_PROMPT = """You are ObserveCo's intelligent troubleshooter. You help users fix installation and configuration issues for ObserveCo, a runtime observability tool for AI agents.

You have access to their full environment diagnostics. Diagnose each issue and provide specific, actionable fixes.

Rules:
1. Be specific — give exact commands, not vague instructions
2. Check their OS — Windows/macOS/Linux commands differ
3. Explain WHY each fix is needed, not just WHAT
4. If an issue requires manual steps (like creating a Slack app), provide step-by-step
5. If an issue can't be fixed automatically, say so clearly
6. NEVER suggest destructive actions (rm, sudo, chmod, delete, format)
7. NEVER suggest commands with pipes, redirects, or command chaining (;, &&, ||, |)
8. NEVER suggest network requests (curl, wget, ssh, scp)
9. For env var issues, explain how to set them permanently (not just export)
10. For permission issues, explain the security implications of sudo/chmod
11. Only suggest: pip install, pip3 install, python -m pip install, observeco commands
12. If you're unsure about a fix, say so — don't guess

SAFE COMMANDS (always OK to suggest):
- pip install <package>
- pip3 install <package>
- python -m pip install <package>
- observeco init
- observeco doctor diagnose
- python3 -m observeco.cli

Response format — for each issue, provide:
ISSUE: <name>
SEVERITY: <critical|warning|info>
EXPLANATION: <what's wrong and why>
FIX_COMMAND: <exact command to run, or empty if manual steps needed>
FIX_MANUAL: <step-by-step manual instructions if command isn't enough, or empty>
"""

USER_PROMPT = """Here are my ObserveCo diagnostics:

{diagnostics}

Please diagnose each issue (status != ok) and provide fixes. For each issue, respond in this exact format:

ISSUE: <name>
SEVERITY: <critical|warning|info>
EXPLANATION: <what's wrong>
FIX_COMMAND: <command to run>
FIX_MANUAL: <manual steps if needed>

After all issues, add a summary line:
SUMMARY: <one-line summary of total fixes>"""


from dataclasses import dataclass
from typing import Optional


# Re-export for backward compat
detect_llm_providers = detect_providers
get_auto_provider = get_auto_provider


@dataclass
class LLMFix:
    """A fix recommended by the LLM."""
    issue: str
    severity: str
    explanation: str
    fix_command: str
    fix_manual: str


def diagnose_with_llm(
    report: DiagnosticReport,
    provider: Optional[LLMProvider] = None,
) -> list[LLMFix]:
    """Send diagnostics to LLM and get fixes.

    Uses the shared llm_service but with doctor-specific prompts.
    Falls back to static diagnosis when LLM unavailable.
    """
    diagnostics_text = report.to_text()
    user_prompt = USER_PROMPT.format(diagnostics=diagnostics_text)

    response = _ask_llm(
        SYSTEM_PROMPT,
        user_prompt,
        consumer="doctor_diagnose",
        max_cost_cents=0.02,
        cache_ttl_secs=300,
        tier=1,
    )

    if response is None:
        return _static_diagnosis(report)

    return _parse_fixes(response)


def _parse_fixes(response: str) -> list[LLMFix]:
    """Parse LLM response into structured fixes."""
    fixes = []
    current = {}

    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("ISSUE:"):
            if current:
                fixes.append(LLMFix(**current))
            current = {
                "issue": line[6:].strip(),
                "severity": "warning",
                "explanation": "",
                "fix_command": "",
                "fix_manual": "",
            }
        elif line.startswith("SEVERITY:"):
            current["severity"] = line[9:].strip().lower()
        elif line.startswith("EXPLANATION:"):
            current["explanation"] = line[12:].strip()
        elif line.startswith("FIX_COMMAND:"):
            current["fix_command"] = line[12:].strip()
        elif line.startswith("FIX_MANUAL:"):
            current["fix_manual"] = line[11:].strip()

    if current:
        fixes.append(LLMFix(**current))

    return fixes


def _static_diagnosis(report: DiagnosticReport) -> list[LLMFix]:
    """Provide static fixes when no LLM is available."""
    fixes = []

    for check in report.issues:
        if check.auto_fix:
            fixes.append(LLMFix(
                issue=check.name,
                severity=check.status,
                explanation=check.message,
                fix_command=check.auto_fix,
                fix_manual="",
            ))
        else:
            fixes.append(LLMFix(
                issue=check.name,
                severity=check.status,
                explanation=check.message,
                fix_command="",
                fix_manual="Check the ObserveCo documentation for manual setup instructions.",
            ))

    return fixes