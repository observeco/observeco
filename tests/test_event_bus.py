"""Tests for Phase 7.1 — Event Pipeline: Event Stream."""
import json
import os
import tempfile
from pathlib import Path

from observeco.event_bus import EventStream, subscribe, publish, get_events


def test_event_stream_writes_to_file():
    """EventStream should write events to rotating files."""
    with tempfile.TemporaryDirectory() as tmp:
        stream = EventStream(event_dir=tmp)
        stream.write({"event_type": "probe_result", "agent": "test", "status": "alive"})
        # Check file was created
        files = list(Path(tmp).glob("events_*.jsonl"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "probe_result" in content
        assert "alive" in content


def test_event_stream_rotates_at_size():
    """EventStream should rotate when file exceeds max_bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        stream = EventStream(event_dir=tmp, max_bytes=100)
        # Write enough to trigger rotation
        for i in range(20):
            stream.write({"event_type": "test", "idx": i})
        files = sorted(Path(tmp).glob("events_*.jsonl"))
        assert len(files) >= 2, f"Expected at least 2 files, got {len(files)}"


def test_event_stream_limits_total_files():
    """EventStream should delete oldest files when count exceeds max_files."""
    with tempfile.TemporaryDirectory() as tmp:
        stream = EventStream(event_dir=tmp, max_bytes=50, max_files=3)
        # Write enough to trigger rotation past max_files
        for i in range(50):
            stream.write({"event_type": "test", "idx": i})
        files = sorted(Path(tmp).glob("events_*.jsonl"))
        assert len(files) <= 3, f"Expected <= 3 files, got {len(files)}"


def test_publish_and_subscribe():
    """publish() writes to the stream, subscribe() reads events."""
    with tempfile.TemporaryDirectory() as tmp:
        stream = EventStream(event_dir=tmp)
        publish(stream, "probe_result", agent="hound", status="alive", latency_ms=12.5)
        publish(stream, "probe_result", agent="kepler", status="dead")

        events = get_events(stream, event_type="probe_result")
        assert len(events) == 2
        assert events[0]["agent"] == "hound"
        assert events[0]["status"] == "alive"
        assert events[0]["event_type"] == "probe_result"


def test_get_events_filters_by_type():
    """get_events should filter by event_type."""
    with tempfile.TemporaryDirectory() as tmp:
        stream = EventStream(event_dir=tmp)
        publish(stream, "probe_result", agent="hound")
        publish(stream, "drift_result", agent="hound", drift_pct=5.0)
        publish(stream, "probe_result", agent="kepler")

        probes = get_events(stream, event_type="probe_result")
        drifts = get_events(stream, event_type="drift_result")

        assert len(probes) == 2
        assert len(drifts) == 1
        assert drifts[0]["drift_pct"] == 5.0


def test_get_events_returns_empty_for_unknown_type():
    """get_events should return empty list for types not seen."""
    with tempfile.TemporaryDirectory() as tmp:
        stream = EventStream(event_dir=tmp)
        publish(stream, "probe_result", agent="hound")
        events = get_events(stream, event_type="garden_result")
        assert events == []


def test_publish_handles_errors_gracefully():
    """publish should not crash on bad data."""
    with tempfile.TemporaryDirectory() as tmp:
        stream = EventStream(event_dir=tmp, max_bytes=10)
        try:
            publish(stream, "test")
            assert True
        except Exception:
            assert False, "publish should not raise on oversized data"