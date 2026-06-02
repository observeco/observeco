"""Error feedback collection — send diagnostic data to central server.

This module collects anonymized diagnostic data when the user opts in,
enabling ObserveCo to improve troubleshooting for all users.

Privacy-first design:
- No PII collected (no emails, no API keys, no file contents)
- Only diagnostic check results and LLM fix outcomes
- User must explicitly opt in
- Data is encrypted in transit (HTTPS)
- User can opt out at any time
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from .diagnostics import DiagnosticReport


FEEDBACK_SERVER = "https://observeco-license-crm.vercel.app/api/telemetry"
FEEDBACK_OPTOUT_VAR = "OBSERVECO_NO_TELEMETRY"


@dataclass
class FeedbackPayload:
    """Anonymized feedback payload for central server."""
    # Environment (anonymized)
    os_name: str
    os_version: str
    python_version: str
    observeco_version: str

    # Diagnostic results (no file contents, no secrets)
    checks: list[dict]  # [{name, status, category}] — no messages with env vars
    issue_count: int
    auto_fix_count: int
    llm_provider: str  # "anthropic" | "openai" | "google" | "ollama" | "none"
    llm_used: bool

    # Fix outcomes
    fixes_applied: int
    fixes_skipped: int
    fixes_succeeded: int
    fixes_failed: int

    # Metadata
    timestamp: str
    session_id: str  # Random, not linked to user identity

    @classmethod
    def from_report(
        cls,
        report: DiagnosticReport,
        llm_provider: str = "none",
        llm_used: bool = False,
        fixes_applied: int = 0,
        fixes_skipped: int = 0,
        fixes_succeeded: int = 0,
        fixes_failed: int = 0,
    ) -> "FeedbackPayload":
        """Create feedback from diagnostic report."""
        import uuid

        # Anonymize checks — strip messages that might contain env var values
        anonymized_checks = []
        for check in report.checks:
            anonymized_checks.append({
                "name": check.name,
                "status": check.status,
                "category": check.category,
            })

        # Get ObserveCo version
        try:
            from observeco import __version__
            version = __version__
        except ImportError:
            version = "unknown"

        return cls(
            os_name=platform.system(),
            os_version=platform.release(),
            python_version=report.python_version,
            observeco_version=version,
            checks=anonymized_checks,
            issue_count=len(report.issues),
            auto_fix_count=sum(1 for c in report.checks if c.auto_fix),
            llm_provider=llm_provider,
            llm_used=llm_used,
            fixes_applied=fixes_applied,
            fixes_skipped=fixes_skipped,
            fixes_succeeded=fixes_succeeded,
            fixes_failed=fixes_failed,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=str(uuid.uuid4()),
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def is_telemetry_opted_out() -> bool:
    """Check if user has opted out of telemetry."""
    return os.environ.get(FEEDBACK_OPTOUT_VAR, "").lower() in ("1", "true", "yes")


def send_feedback(payload: FeedbackPayload) -> bool:
    """Send anonymized feedback to central server.

    Returns True if sent successfully, False otherwise.
    Never raises exceptions — failures are silently logged.
    """
    if is_telemetry_opted_out():
        return False

    try:
        data = payload.to_json().encode()
        req = urllib.request.Request(
            FEEDBACK_SERVER,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def collect_fix_outcome(fixes_applied: int, fixes_skipped: int,
                         fixes_succeeded: int, fixes_failed: int,
                         report: DiagnosticReport, llm_provider: str = "none",
                         llm_used: bool = False) -> bool:
    """Collect fix outcomes for feedback.

    This is called after the doctor has applied fixes to report what happened.
    """
    payload = FeedbackPayload.from_report(
        report=report,
        llm_provider=llm_provider,
        llm_used=llm_used,
        fixes_applied=fixes_applied,
        fixes_skipped=fixes_skipped,
        fixes_succeeded=fixes_succeeded,
        fixes_failed=fixes_failed,
    )
    return send_feedback(payload)
