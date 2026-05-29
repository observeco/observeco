"""Telemetry client — automatic error capture and usage pings.

Sends anonymous crash/error data to telemetry.observeco.dev.
Fire-and-forget — never blocks the CLI, never raises.

Opt-out: set OBSERVECO_TELEMETRY=off
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import threading
import traceback
import urllib.request
from typing import Optional

from observeco import __version__

TELEMETRY_URL = os.environ.get(
    "OBSERVECO_TELEMETRY_URL",
    "https://telemetry.observeco.ai/v1/telemetry",
)

# Users can opt out
TELEMETRY_ENABLED = os.environ.get("OBSERVECO_TELEMETRY", "on").lower() not in ("off", "0", "false", "no")

logger = logging.getLogger("observeco.telemetry")


def _build_envelope(event_type: str, payload: dict) -> dict:
    """Build a standard telemetry envelope for all events."""
    return {
        "event": event_type,
        "version": __version__,
        "python": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "machine_id": _get_machine_id(),
        "payload": payload,
    }


def _get_machine_id() -> str:
    """Get a stable (but anonymous) machine identifier.

    Uses /etc/machine-id (Linux) or IOPlatformUUID (macOS).
    Falls back to hashed hostname.
    """
    import hashlib

    # Try macOS
    if sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=3,
            )
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    uuid = line.split('"')[1]
                    return hashlib.sha256(uuid.encode()).hexdigest()[:16]
        except Exception:
            pass

    # Try /etc/machine-id (Linux)
    try:
        with open("/etc/machine-id") as f:
            return f.read().strip()[:16]
    except Exception:
        pass

    # Fallback: hostname hash
    hostname = platform.node()
    return hashlib.sha256(hostname.encode()).hexdigest()[:16]


def _send(url: str, data: dict) -> None:
    """Fire-and-forget POST — never raises."""
    if not TELEMETRY_ENABLED:
        return
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # Silent — telemetry cannot interrupt the user


def send_sync(event_type: str, payload: dict) -> None:
    """Blocking send (for use in background threads / hooks)."""
    _send(TELEMETRY_URL, _build_envelope(event_type, payload))


def send(event_type: str, payload: dict) -> None:
    """Fire-and-forget in a daemon thread."""
    if not TELEMETRY_ENABLED:
        return
    t = threading.Thread(
        target=_send,
        args=(TELEMETRY_URL, _build_envelope(event_type, payload)),
        daemon=True,
    )
    t.start()


def send_install_ping() -> None:
    """Called once on first install — identifies new user."""
    send("install", {
        "install_method": _detect_install_method(),
    })


def send_error(error_type: str, error_message: str, stack_trace: str,
               command: str = "") -> None:
    """Called automatically on CLI crashes."""
    send("error", {
        "type": error_type,
        "message": error_message[:500],
        "stack": stack_trace[:2000],
        "command": command,
    })


def send_usage(command: str) -> None:
    """Called on CLI command execution."""
    send("usage", {
        "command": command,
    })


def send_feature_usage(feature: str, detail: str = "") -> None:
    """Called when specific features are used (dashboard, pulse, etc.)."""
    send("feature", {
        "feature": feature,
        "detail": detail,
    })


def _detect_install_method() -> str:
    """Detect how observeco was installed."""
    try:
        import observeco
        module_path = os.path.dirname(os.path.dirname(observeco.__file__))
        if "site-packages" in module_path:
            return "pip"
        return "editable"
    except Exception:
        return "unknown"
