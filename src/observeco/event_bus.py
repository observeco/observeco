"""Event pipeline — rotating JSONL event stream with publish/subscribe.

Architecture per Phase 7.1 spec:
- Main loop only probes agents + writes heartbeat
- Events written to rotating JSONL files (~/.observeco/events/events_N.jsonl)
- Consumers read from the stream independently
- Each consumer has its own try/except + restart cycle
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional


class EventStream:
    """Rotating JSONL event stream writer.

    Writes events as newline-delimited JSON to rotating files.
    Rotates at max_bytes per file, keeps at most max_files on disk.
    """

    def __init__(
        self,
        event_dir: str | Path = "",
        max_bytes: int = 1_048_576,  # 1MB per file
        max_files: int = 10,
    ):
        self.event_dir = Path(event_dir) if event_dir else Path.home() / ".observeco" / "events"
        self.max_bytes = max_bytes
        self.max_files = max_files
        self.event_dir.mkdir(parents=True, exist_ok=True)
        self._current_fd: Optional[Any] = None
        self._current_path: Optional[Path] = None

    def _get_current_path(self) -> Path:
        """Get or create the current event file path."""
        if self._current_path is not None and self._current_path.exists():
            size = self._current_path.stat().st_size
            if size < self.max_bytes:
                return self._current_path

        # Need to rotate
        files = sorted(self.event_dir.glob("events_*.jsonl"))
        next_idx = 1
        if files:
            last = files[-1]
            try:
                next_idx = int(last.stem.split("_")[-1]) + 1
            except (ValueError, IndexError):
                next_idx = len(files) + 1

        self._current_path = self.event_dir / f"events_{next_idx:04d}.jsonl"
        self._current_fd = None

        # Enforce max_files limit — delete oldest BEFORE adding the new file
        # so total stays ≤ max_files
        self._trim_old_files()

        return self._current_path

    def _trim_old_files(self) -> None:
        """Delete oldest files if count exceeds or equals max_files.

        Trims to max_files - 1 to leave room for the new file about to be created.
        """
        files = sorted(self.event_dir.glob("events_*.jsonl"))
        while len(files) >= self.max_files:
            oldest = files.pop(0)
            try:
                oldest.unlink()
            except OSError:
                pass

    def _write_line(self, line: str) -> None:
        """Write a single JSON line to the current file."""
        path = self._get_current_path()
        # Append mode, create if not exists
        with open(str(path), "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def write(self, event: dict) -> None:
        """Write an event to the stream.

        Args:
            event: Dict with at minimum an 'event_type' key.
                  Gets 'timestamp' added automatically if not present.
        """
        if "timestamp" not in event:
            event["timestamp"] = int(time.time())
        line = json.dumps(event, default=str)
        self._write_line(line)

    def close(self) -> None:
        """Close any open file handles."""
        self._current_fd = None
        self._current_path = None


# Module-level default stream for convenience
_default_stream: Optional[EventStream] = None


def _get_default_stream(event_dir: str = "") -> EventStream:
    """Get or create the default event stream."""
    global _default_stream
    if _default_stream is None:
        _default_stream = EventStream(event_dir=event_dir)
    return _default_stream


def publish(
    stream: EventStream | None = None,
    event_type: str = "",
    event_dir: str = "",
    **kwargs,
) -> None:
    """Publish an event to the event stream.

    Args:
        stream: Optional EventStream instance. Uses global default if None.
        event_type: Type of event (e.g. 'probe_result', 'drift_result').
        event_dir: Optional event directory override.
        **kwargs: Additional event data fields.
    """
    if stream is None:
        stream = _get_default_stream(event_dir=event_dir)
    event = {"event_type": event_type, **kwargs}
    stream.write(event)


def subscribe(stream: EventStream | None = None, event_type: str = "", **filters) -> list[dict]:
    """Read events matching a type and optional field filters.

    Args:
        stream: Optional EventStream instance. Uses global default if None.
        event_type: Filter by event_type (empty string = all types).
        **filters: Additional field:value filters.

    Returns:
        List of matching event dicts, most recent first.
    """
    if stream is None:
        stream = _get_default_stream()
    events = []

    # Read all event files, newest first
    files = sorted(stream.event_dir.glob("events_*.jsonl"), reverse=True)
    for fpath in files:
        try:
            with open(str(fpath), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event_type and event.get("event_type") != event_type:
                        continue
                    if filters:
                        if not all(event.get(k) == v for k, v in filters.items()):
                            continue
                    events.append(event)
        except OSError:
            continue

    return events


def get_events(
    stream: EventStream | None = None,
    event_type: str = "",
    limit: int = 100,
    **filters,
) -> list[dict]:
    """Get recent events matching filters.

    Args:
        stream: Optional EventStream instance.
        event_type: Filter by type.
        limit: Max events to return.
        **filters: Additional field filters.

    Returns:
        List of matching event dicts, most recent first, capped at limit.
    """
    if stream is None:
        stream = _get_default_stream()
    events = subscribe(stream=stream, event_type=event_type, **filters)
    return events[:limit]