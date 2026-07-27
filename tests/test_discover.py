"""Tests for the discover gap scanner (#79)."""
from unittest.mock import patch, MagicMock

import observeco.discover.scanner as s


def _fake_agents():
    return []


def test_scan_finds_cron_gap(tmp_path, monkeypatch):
    # Point hermes_home at a temp dir with a cron job not in DB
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    (cron_dir / "jobs.json").write_text(
        '[{"name": "news_digest", "schedule": "0 9 * * *"}]'
    )
    monkeypatch.setattr(s, "hermes_home", lambda: tmp_path)
    with patch.object(s, "Database") as MockDB:
        MockDB.return_value.get_agents.return_value = _fake_agents()
        gaps = s.scan()
    names = {g["name"] for g in gaps}
    assert "news_digest" in names


def test_scan_finds_process_gap(monkeypatch):
    # Fake psutil returning one agent-like process not in DB
    class FakeProc:
        def __init__(self, info):
            self.info = info

    monkeypatch.setattr(s, "hermes_home", lambda: None)  # no cron/config gaps
    fake_procs = [
        FakeProc({"pid": 1, "name": "hermes-agent", "cmdline": ["hermes", "chat"]})
    ]
    import psutil

    with patch.object(psutil, "process_iter", return_value=fake_procs), patch.object(
        s, "Database"
    ) as MockDB:
        MockDB.return_value.get_agents.return_value = _fake_agents()
        gaps = s.scan()
    names = {g["name"] for g in gaps}
    assert "hermes-agent" in names


def test_add_gap_registers(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "hermes_home", lambda: tmp_path)
    from observeco.config import _AGENTS_JSON

    _AGENTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    if _AGENTS_JSON.exists():
        _AGENTS_JSON.unlink()
    with patch.object(s, "Database") as MockDB:
        mock_db = MockDB.return_value
        mock_db.get_agents.return_value = []
        res = s.add_gap("my_new_agent", "custom", health_check="pgrep -f my_new_agent")
    assert res["status"] == "ok", res
    mock_db.register_agent.assert_called_once()
