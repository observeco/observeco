"""Metric Exemption mechanism for GS-013.

Allows flagging known-dead agents or broken data sources as EXEMPTED
so they don't skew daemon_uptime, heartbeat_compliance, signal_error_rate,
or other aggregate metrics.

Exempted entries are SKIPPED in rollups (not counted as FAILED, not
triggering breach flags or kanban tasks). They're recorded in a
separate exempted_readings log for audit purposes.

Usage:
    from observeco.metric_exemptions import is_exempted, add_exemption

    if not is_exempted(agent_name, "daemon_uptime"):
        # compute metric normally
        pass
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional

from observeco.dirs import get_data_dir

EXEMPTIONS_FILE = get_data_dir() / "metric_exemptions.json"


@dataclass
class MetricExemption:
    agent_name: str
    metric_name: str
    reason: str
    exempted_by: str = "hound"
    exempted_at: int = 0
    expires_at: Optional[int] = None
    active: bool = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return int(time.time()) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.active and not self.is_expired


def _load_raw() -> dict:
    if EXEMPTIONS_FILE.exists():
        try:
            return json.loads(EXEMPTIONS_FILE.read_text())
        except (json.JSONDecodeError, PermissionError, OSError):
            pass
    return {"exemptions": []}


def _save_raw(data: dict) -> None:
    EXEMPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = EXEMPTIONS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(EXEMPTIONS_FILE)


def _parse_exemptions(raw: dict) -> list[MetricExemption]:
    return [
        MetricExemption(
            agent_name=e.get("agent_name", ""),
            metric_name=e.get("metric_name", ""),
            reason=e.get("reason", ""),
            exempted_by=e.get("exempted_by", "hound"),
            exempted_at=e.get("exempted_at", 0),
            expires_at=e.get("expires_at"),
            active=e.get("active", True),
        )
        for e in raw.get("exemptions", [])
    ]


def _serialize_exemptions(exemptions: list[MetricExemption]) -> list[dict]:
    return [
        {
            "agent_name": e.agent_name,
            "metric_name": e.metric_name,
            "reason": e.reason,
            "exempted_by": e.exempted_by,
            "exempted_at": e.exempted_at,
            "expires_at": e.expires_at,
            "active": e.active,
        }
        for e in exemptions
    ]


def load_exemptions() -> list[MetricExemption]:
    """Return all exemptions (including expired/inactive)."""
    raw = _load_raw()
    return _parse_exemptions(raw)


def is_exempted(agent_name: str, metric_name: str) -> bool:
    """Check if (agent, metric) is currently exempted."""
    for e in load_exemptions():
        if e.agent_name == agent_name and e.metric_name == metric_name and e.is_valid:
            return True
    return False


def add_exemption(
    agent_name: str,
    metric_name: str,
    reason: str,
    exempted_by: str = "hound",
    expires_at: Optional[int] = None,
) -> dict:
    """Add a new metric exemption."""
    raw = _load_raw()
    # Re-read properly
    exemptions = [e for e in _parse_exemptions(raw)
                  if not (e.agent_name == agent_name and e.metric_name == metric_name)]

    now = int(time.time())
    exemptions.append(MetricExemption(
        agent_name=agent_name,
        metric_name=metric_name,
        reason=reason,
        exempted_by=exempted_by,
        exempted_at=now,
        expires_at=expires_at,
        active=True,
    ))

    _save_raw({"exemptions": _serialize_exemptions(exemptions)})

    return {
        "status": "exempted",
        "agent_name": agent_name,
        "metric_name": metric_name,
        "exempted_at": now,
        "expires_at": expires_at,
    }


def remove_exemption(agent_name: str, metric_name: str) -> dict:
    """Remove an exemption (sets active=False rather than deleting)."""
    exemptions = load_exemptions()
    for e in exemptions:
        if e.agent_name == agent_name and e.metric_name == metric_name:
            e.active = False
    _save_raw({"exemptions": _serialize_exemptions(exemptions)})
    return {"status": "removed", "agent_name": agent_name, "metric_name": metric_name}


def list_exemptions() -> dict:
    """Return exemptions grouped by agent, with validity status."""
    exemptions = load_exemptions()
    result: dict[str, list[dict[str, object]]] = {}
    for e in exemptions:
        if e.agent_name not in result:
            result[e.agent_name] = []
        result[e.agent_name].append({
            "metric_name": e.metric_name,
            "reason": e.reason,
            "exempted_by": e.exempted_by,
            "valid": e.is_valid,
            "expires_at": e.expires_at,
        })
    return result


def active_exemption_count() -> int:
    """Number of currently active exemptions."""
    return sum(1 for e in load_exemptions() if e.is_valid)
