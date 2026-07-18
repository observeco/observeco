"""Tests for Incident Skill Auto-Creation (L3 Learning Loop, #81)."""
from unittest.mock import patch

from observeco.db import Database
from observeco.heal import prevention as prev
from observeco.heal.prevention import (
    extract_error_signature,
    write_prevention_skill,
    check_prevention,
    apply_prevention,
    remove_skill,
)


def _tmp_db(tmp_path):
    """Point prevention's Database at a fresh temp DB for isolation."""
    db = Database(db_path=tmp_path / "test_pulse.db")
    return db


def test_signature_strips_volatile():
    sig = extract_error_signature(
        "2026-07-12 10:00:01 ERROR PID 1234 /Users/sean/fzc/x.py crashed 0x1a2b",
        "kepler",
        {"status": "error"},
    )
    assert "2026-07-12" not in sig
    assert "PID 1234" not in sig
    assert "<file>" in sig
    assert "0xADDR" in sig
    assert sig.startswith("kepler:error:")


def test_write_then_fts_find(tmp_path, monkeypatch):
    monkeypatch.setattr(prev, "PREVENTION_DIR", tmp_path)
    monkeypatch.setattr(prev, "Database", lambda: _tmp_db(tmp_path))
    sig = "kepler:error:OOM killed during compaction"
    path = write_prevention_skill("kepler", sig, "Memory exhausted", "restart the agent")
    assert path
    found = check_prevention("kepler", "kepler:error:OOM killed during compaction loop")
    assert found is not None, "FTS5 match failed"
    assert found["agent_name"] == "kepler"
    remove_skill(found["id"])


def test_apply_safe_remediation(monkeypatch):
    skill = {"id": 999, "agent_name": "kepler",
             "remediation": "ACTION: restart the agent process", "skill_path": ""}
    calls = {}

    def fake_execute(action, args):
        calls["action"] = action
        return True, "restarted"

    with patch("observeco.heal._execute_action", side_effect=fake_execute):
        ok, msg = apply_prevention(skill, "kepler")
    assert ok is True
    assert calls.get("action") == "restart"


def test_dangerous_remediation_not_auto_run():
    skill = {"id": 998, "agent_name": "kepler",
             "remediation": "pip_install some_package and restart", "skill_path": ""}
    ok, msg = apply_prevention(skill, "kepler")
    assert ok is False
    assert "human" in msg.lower()


def test_two_failures_deprecate(tmp_path, monkeypatch):
    monkeypatch.setattr(prev, "PREVENTION_DIR", tmp_path)
    monkeypatch.setattr(prev, "Database", lambda: _tmp_db(tmp_path))
    sig = "kepler:error:flaky network timeout"
    write_prevention_skill("kepler", sig, "Network flake", "restart")
    found = check_prevention("kepler", sig)
    sid = found["id"]
    with patch("observeco.heal._execute_action", return_value=(False, "boom")):
        apply_prevention(found, "kepler")
        found2 = check_prevention("kepler", sig)
        assert found2 is not None  # 1 fail, not yet deprecated
        apply_prevention(found2, "kepler")
    after = prev.get_skill(sid)
    assert after["deprecated"] == 1, after
    assert check_prevention("kepler", sig) is None  # deprecated -> not matched
    remove_skill(sid)


def test_remove_skill(tmp_path, monkeypatch):
    monkeypatch.setattr(prev, "PREVENTION_DIR", tmp_path)
    monkeypatch.setattr(prev, "Database", lambda: _tmp_db(tmp_path))
    sig = "kepler:error:temp failure"
    write_prevention_skill("kepler", sig, "Temp", "restart")
    found = check_prevention("kepler", sig)
    sid = found["id"]
    assert remove_skill(sid) is True
    assert check_prevention("kepler", sig) is None
    assert remove_skill(sid) is False
