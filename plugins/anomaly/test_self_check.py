"""Self-check tests for Anomaly Detection plugin.

Pure assert, no framework. Creates temp DB with known data, verifies detection.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly.anomaly_core import (
    detect_anomalies,
    format_anomalies,
    _detect_no_tools,
    _detect_cost_spikes,
    _detect_retry_loops,
)


def _create_test_db(path: str) -> sqlite3.Connection:
    """Create a test DB with the sessions table schema."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT,
            model TEXT,
            profile_name TEXT,
            started_at REAL,
            ended_at REAL,
            end_reason TEXT,
            message_count INTEGER DEFAULT 0,
            tool_call_count INTEGER DEFAULT 0,
            api_call_count INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd REAL DEFAULT 0,
            title TEXT
        )
    """)
    conn.commit()
    return conn


def _insert_session(conn, sid, model="test-model", profile="test",
                    started=None, ended=None, end_reason="completed",
                    api_calls=1, tool_calls=0, cost=0.0, title="test"):
    conn.execute(
        "INSERT INTO sessions (id, model, profile_name, started_at, ended_at, "
        "end_reason, api_call_count, tool_call_count, estimated_cost_usd, title) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (sid, model, profile, started or time.time(), ended or time.time(),
         end_reason, api_calls, tool_calls, cost, title),
    )
    conn.commit()


def test_no_tools_detection():
    """Session with API calls but 0 tool calls is flagged."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        now = int(time.time())
        # Session with 5 API calls, 0 tools
        _insert_session(conn, "s1", api_calls=5, tool_calls=0, started=now-60)
        # Session with 3 API calls, 2 tools (normal)
        _insert_session(conn, "s2", api_calls=3, tool_calls=2, started=now-60)
        # Cron session — should be excluded
        _insert_session(conn, "s3", api_calls=5, tool_calls=0, started=now-60,
                       end_reason="cron_complete")

        anomalies = _detect_no_tools(conn, now - 3600, now)
        assert len(anomalies) == 1, f"Expected 1, got {len(anomalies)}"
        assert anomalies[0]["type"] == "no_tools"
        assert anomalies[0]["evidence"]["api_calls"] == 5
        conn.close()
    finally:
        os.unlink(db_path)
    print("  ✅ no_tools detection")


def test_no_tools_normal_session():
    """Session with tools is not flagged."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        now = int(time.time())
        _insert_session(conn, "s1", api_calls=5, tool_calls=3, started=now-60)
        anomalies = _detect_no_tools(conn, now - 3600, now)
        assert len(anomalies) == 0
        conn.close()
    finally:
        os.unlink(db_path)
    print("  ✅ no_tools normal session")


def test_cost_spike_detection():
    """Cost >3σ above average is flagged."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        now = int(time.time())
        # 15 normal sessions at $0.01
        for i in range(15):
            _insert_session(conn, f"normal_{i}", cost=0.01, started=now - 86400 + i*60)
        # 1 spike at $0.50
        _insert_session(conn, "spike_1", cost=0.50, started=now - 60)

        anomalies = _detect_cost_spikes(conn, now - 3600, now)
        assert len(anomalies) >= 1, f"Expected ≥1 cost spike, got {len(anomalies)}"
        assert anomalies[0]["type"] == "high_cost"
        assert anomalies[0]["evidence"]["ratio"] > 10  # 0.50 / 0.01 = 50x
        conn.close()
    finally:
        os.unlink(db_path)
    print("  ✅ cost spike detection")


def test_cost_spike_no_data():
    """No spike when costs are uniform."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        now = int(time.time())
        for i in range(15):
            _insert_session(conn, f"normal_{i}", cost=0.01, started=now - 86400 + i*60)

        anomalies = _detect_cost_spikes(conn, now - 3600, now)
        assert len(anomalies) == 0
        conn.close()
    finally:
        os.unlink(db_path)
    print("  ✅ cost spike no data")


def test_retry_loop_detection():
    """Same end_reason ≥3 times in 10 min is flagged."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        now = int(time.time())
        # 4 error sessions in last 5 min
        for i in range(4):
            _insert_session(conn, f"fail_{i}", end_reason="error",
                          started=now - 300 + i*30, ended=now - 300 + i*30 + 5)
        # 2 normal sessions
        for i in range(2):
            _insert_session(conn, f"ok_{i}", end_reason="completed",
                          started=now - 300 + i*30)

        anomalies = _detect_retry_loops(conn, now - 3600, now)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "retry_loop"
        assert anomalies[0]["evidence"]["count"] == 4
        conn.close()
    finally:
        os.unlink(db_path)
    print("  ✅ retry loop detection")


def test_retry_loop_normal():
    """Completed sessions are not flagged as retry loops."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        now = int(time.time())
        for i in range(5):
            _insert_session(conn, f"ok_{i}", end_reason="completed",
                          started=now - 300 + i*30)

        anomalies = _detect_retry_loops(conn, now - 3600, now)
        assert len(anomalies) == 0
        conn.close()
    finally:
        os.unlink(db_path)
    print("  ✅ retry loop normal")


def test_format_anomalies_empty():
    """Empty list shows all-clear message."""
    text = format_anomalies([])
    assert "No anomalies" in text
    print("  ✅ format empty")


def test_format_anomalies_found():
    """Non-empty list shows table."""
    anomalies = [
        {"type": "no_tools", "agent": "test", "severity": "warning",
         "description": "5 API calls, 0 tools", "timestamp": 0, "evidence": {}},
    ]
    text = format_anomalies(anomalies)
    assert "no_tools" in text
    assert "Total: 1" in text
    print("  ✅ format found")


def test_detect_anomalies_integration():
    """Full detect_anomalies() returns sorted list."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        now = int(time.time())
        _insert_session(conn, "s1", api_calls=5, tool_calls=0, started=now-60)
        result = detect_anomalies(db_path, lookback_minutes=60)
        assert isinstance(result, list)
        assert len(result) >= 1
        conn.close()
    finally:
        os.unlink(db_path)
    print("  ✅ detect_anomalies integration")


def test_detect_anomalies_empty_db():
    """Empty DB returns empty list, no crash."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = _create_test_db(db_path)
        conn.close()
        result = detect_anomalies(db_path, lookback_minutes=60)
        assert result == []
    finally:
        os.unlink(db_path)
    print("  ✅ empty DB no crash")


def main():
    tests = [
        test_no_tools_detection,
        test_no_tools_normal_session,
        test_cost_spike_detection,
        test_cost_spike_no_data,
        test_retry_loop_detection,
        test_retry_loop_normal,
        test_format_anomalies_empty,
        test_format_anomalies_found,
        test_detect_anomalies_integration,
        test_detect_anomalies_empty_db,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  💥 {test.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{passed+failed} passed")
    if failed:
        print(f"FAILED: {failed} tests")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())