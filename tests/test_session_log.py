"""Tests for tamper-evident session logging."""

import json
import os
import tempfile

from observeco.session_log import SessionLogger
from observeco.dirs import get_data_dir


class TestSessionLog:
    """Test the hash-chained session log."""

    def test_log_creates_entry(self):
        logger = SessionLogger(session_id="test_entry_keys")
        entry = logger.log("test_event", {"message": "hello"})
        # Internal keys use _hash and _prev_hash
        assert "entry_hash" not in entry
        assert "_hash" in entry
        assert "_prev_hash" in entry
        assert entry["event_type"] == "test_event"
        assert "timestamp" in entry

    def test_chain_verification_passes_for_clean_log(self):
        logger = SessionLogger(session_id="test_verify_clean")
        logger.log("a", {"v": 1})
        logger.log("b", {"v": 2})
        ok, msg = logger.verify_chain()
        assert ok is True, f"Chain verification failed: {msg}"

    def test_chain_verification_fails_for_tampered_log(self):
        logger = SessionLogger(session_id="test_verify_tamper_chain")
        logger.log("a", {"v": 1})
        logger.log("b", {"v": 2})

        # Find session file
        data_dir = get_data_dir()
        session_dir = os.path.join(data_dir, "sessions")
        if not os.path.isdir(session_dir):
            os.makedirs(session_dir, exist_ok=True)

        files = sorted(f for f in os.listdir(session_dir) if "verify_tamper_chain" in f)
        assert len(files) > 0, f"No session file found for verify_tamper_chain in {session_dir}"

        fpath = os.path.join(session_dir, files[0])
        with open(fpath) as f:
            lines = f.readlines()
        tampered = json.loads(lines[0])
        if "data" in tampered:
            tampered["data"]["v"] = 999
        lines[0] = json.dumps(tampered) + "\n"
        with open(fpath, "w") as f:
            f.writelines(lines)

        ok, msg = logger.verify_chain()
        assert ok is False, f"Tampered chain should fail: {msg}"

    def test_verify_returns_true_for_single_entry(self):
        logger = SessionLogger(session_id="test_single_entry_v")
        logger.log("single", {"x": 1})
        ok, msg = logger.verify_chain()
        assert ok is True, f"Single entry failed: {msg}"

    def test_get_entries_returns_list(self):
        logger = SessionLogger(session_id="test_get_entries_list")
        logger.log("first", {"i": 1})
        logger.log("second", {"i": 2})
        entries = logger.get_entries()
        assert len(entries) >= 2
