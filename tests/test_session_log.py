"""Tests for tamper-evident session logging."""

import json
from observeco.session_log import SessionLogger
from observeco.dir import get_data_dir


class TestSessionLog:
    """Test the hash-chained session log."""

    def test_log_creates_entry(self):
        logger = SessionLogger(session_id="test-session")
        entry = logger.log("test_event", {"message": "hello"})
        assert entry["event_type"] == "test_event"
        assert "timestamp" in entry
        assert "entry_hash" in entry
        assert "prev_hash" in entry

    def test_first_entry_has_no_prev_hash(self):
        logger = SessionLogger(session_id="unused")
        # Each logger starts with a file; force a unique ID
        from observeco.session_log import SessionLogger as SL
        lg = SL(session_id="fresh-test-chain")
        entry = lg.log("first", {"n": 1})
        # First entry should have empty or null prev_hash
        assert entry["prev_hash"] == "" or entry["prev_hash"] is None

    def test_chain_verification_passes_for_clean_log(self):
        logger = SessionLogger(session_id="verify-clean")
        logger.log("a", {"v": 1})
        logger.log("b", {"v": 2})
        ok, _ = logger.verify_chain()
        assert ok is True

    def test_chain_verification_fails_for_tampered_log(self):
        logger = SessionLogger(session_id="verify-tamper")
        logger.log("a", {"v": 1})
        logger.log("b", {"v": 2})

        # Find and tamper the file
        import os
        data_dir = get_data_dir()
        session_path = os.path.join(data_dir, "sessions")
        files = sorted(f for f in os.listdir(session_path) if "verify-tamper" in f)
        if not files:
            # try alternate location
            session_path = os.path.join(data_dir)
            files = sorted(f for f in os.listdir(session_path) if "verify-tamper" in f)

        if files:
            fpath = os.path.join(session_path, files[0])
            with open(fpath) as f:
                lines = f.readlines()
            if lines:
                tampered = json.loads(lines[0])
                if "data" in tampered:
                    tampered["data"]["v"] = 999
                lines[0] = json.dumps(tampered) + "\n"
                with open(fpath, "w") as f:
                    f.writelines(lines)

        ok, _ = logger.verify_chain()
        assert ok is False
