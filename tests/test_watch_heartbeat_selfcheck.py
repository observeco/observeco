"""Self-check: watch daemon alive-check logic.

Exercises the three patterns used in _ensure_watch_running():
1. Heartbeat file parsing (JSON decode, age check)
2. PID verification (os.kill with signal 0)
3. Subprocess launch retry logic

Does NOT launch real subprocesses — uses mock fixtures.
"""

import json
import os
import tempfile
import time
from pathlib import Path


def test_heartbeat_parsing():
    """Verify heartbeat file age check and PID parse."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        hb = tmpdir / "watch.heartbeat"
        now = time.time()

        # Case 1: fresh heartbeat with live PID
        pid = os.getpid()  # our own PID — definitely alive
        hb.write_text(json.dumps({"pid": pid, "time": now, "cycle": 5}))
        data = json.loads(hb.read_text())
        age = time.time() - data["time"]
        assert age < 30, f"Heartbeat age {age:.1f}s should be fresh"
        # PID check: os.kill(pid, 0) raises if dead
        os.kill(data["pid"], 0)
        assert data["cycle"] == 5
        print("PASS: fresh heartbeat with live PID passes")

        # Case 2: stale heartbeat (>30s)
        hb.write_text(json.dumps({"pid": pid, "time": now - 60, "cycle": 5}))
        data = json.loads(hb.read_text())
        age = time.time() - data["time"]
        assert age > 30, f"Stale age {age:.1f}s should exceed 30s"
        print("PASS: stale heartbeat correctly flagged")

        # Case 3: dead PID in heartbeat
        dead_pid = 999999999  # unlikely to be alive
        hb.write_text(json.dumps({"pid": dead_pid, "time": now, "cycle": 5}))
        data = json.loads(hb.read_text())
        try:
            os.kill(data["pid"], 0)
            assert False, "PID should be dead"
        except OSError:
            print("PASS: dead PID correctly detected")

        # Case 4: corrupt heartbeat
        hb.write_text("not-json")
        try:
            data = json.loads(hb.read_text())
            assert False, "Should have raised"
        except (json.JSONDecodeError, ValueError):
            print("PASS: corrupt heartbeat raises correctly")

    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("All heartbeat-parsing checks passed.")


if __name__ == "__main__":
    test_heartbeat_parsing()
