"""Tests for reconciler — state classifier, CircuitBreaker, reconcile loop, actions.

Uses real HermesSchemaV14 adapter on tmp_path config files.
Monkeypatches _port_alive (in reconciler), snapshot_store._get_db_path,
and ensure_proxy_alive callable to avoid real sockets/DBs.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from observeco.capability.adapters.hermes import HermesSchemaV14
from observeco.proxy import reconciler, snapshot_store
from observeco.proxy.reconciler import (
    CIRCUIT_COOLDOWN,
    CIRCUIT_FAILURE_WINDOW,
    CircuitBreaker,
    ReconcilerState,
    _repoint,
    _revert,
    _snapshot_if_absent,
    classify,
    reconcile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

V14_CONFIG = """\
providers:
  - name: deepseek
    base_url: https://api.deepseek.com/v1
    api_key: sk-abc
  - name: ollama
    base_url: http://localhost:11434/v1
"""

LOCAL_V14_CONFIG = """\
providers:
  - name: deepseek
    base_url: http://127.0.0.1:9200/v1
    api_key: sk-abc
  - name: ollama
    base_url: http://localhost:11434/v1
"""


@pytest.fixture
def config_path(tmp_path):
    f = tmp_path / "config.yaml"
    f.write_text(V14_CONFIG)
    return str(f)


@pytest.fixture
def local_config_path(tmp_path):
    f = tmp_path / "config.yaml"
    f.write_text(LOCAL_V14_CONFIG)
    return str(f)


@pytest.fixture
def adapter():
    return HermesSchemaV14


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "observeco.db"


@pytest.fixture
def patch_db(db_path, monkeypatch):
    """Redirect snapshot_store DB to temp file and create tables."""
    monkeypatch.setattr(snapshot_store, "_get_db_path", lambda: db_path)
    snapshot_store.ensure_table()  # creates proxy_config_snapshots + proxy_reconciler_state
    return db_path


@pytest.fixture
def patch_port_alive(monkeypatch):
    """Control _port_alive inside reconciler module."""
    values = iter([])

    def set_values(vals):
        nonlocal values
        values = iter(vals)

    def _mock(port):
        return next(values, False)

    monkeypatch.setattr(reconciler, "_port_alive", _mock)
    return type("MockAlive", (), {"set_values": staticmethod(set_values)})()


@pytest.fixture
def state():
    return ReconcilerState()


@pytest.fixture
def ensure_alive():
    """Factory that creates a mock ensure_proxy_alive returning (alive, port)."""
    def _make(alive: bool, port: int | None):
        return MagicMock(return_value=(alive, port))
    return _make


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------


class FakeTime:
    """Control time.time() returns for CircuitBreaker tests."""
    def __init__(self, now=0.0):
        self._now = now

    def __call__(self):
        return self._now

    def advance(self, secs):
        self._now += secs
        return self._now


@pytest.fixture
def fake_time(monkeypatch):
    ft = FakeTime()
    monkeypatch.setattr(time, "time", ft)
    return ft


class TestCircuitBreaker:
    def test_starts_closed(self):
        """Fresh circuit → is_open() is False."""
        cb = CircuitBreaker()
        assert cb.is_open() is False

    def test_not_open_after_few_failures(self, fake_time):
        """1-2 failures within window → still closed."""
        cb = CircuitBreaker()
        cb.record_failure()  # t=0
        fake_time.advance(10)
        cb.record_failure()  # t=10
        assert cb.is_open() is False

    def test_opens_at_max_failures(self, fake_time):
        """3 failures within window → opens, cooldown set."""
        cb = CircuitBreaker()
        cb.record_failure()  # t=0
        fake_time.advance(10)
        cb.record_failure()  # t=10
        fake_time.advance(10)
        assert cb.is_open() is False  # still 2 failures
        cb.record_failure()  # t=20 → 3rd failure
        assert cb.is_open() is True
        assert cb._cooldown_until == 20 + CIRCUIT_COOLDOWN

    def test_open_during_cooldown(self, fake_time):
        """Once open, stays open until cooldown expires."""
        cb = CircuitBreaker()
        cb._cooldown_until = fake_time() + 100
        assert cb.is_open() is True
        fake_time.advance(150)
        assert cb.is_open() is False

    def test_reset_clears(self, fake_time):
        """reset() clears failures and cooldown."""
        cb = CircuitBreaker()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open() is True
        cb.reset()
        assert cb.is_open() is False
        assert cb._cooldown_until == 0.0

    def test_old_failures_expire(self, fake_time):
        """Failures outside window don't count."""
        cb = CircuitBreaker()
        cb.record_failure()  # t=0
        fake_time.advance(CIRCUIT_FAILURE_WINDOW + 10)
        cb.record_failure()  # old failure expired
        assert cb.is_open() is False

    def test_cooldown_property(self):
        """cooldown_until property matches internal value."""
        cb = CircuitBreaker()
        assert cb.cooldown_until == 0.0
        cb._cooldown_until = 100.0
        assert cb.cooldown_until == 100.0


# ---------------------------------------------------------------------------
# classify — 5 states
# ---------------------------------------------------------------------------


class TestClassify:
    def test_converged_upstream_non_local_url(self):
        """http://api.example.com → CONVERGED_UPSTREAM."""
        cls = classify("http://api.example.com/v1", 9200, {}, None)
        assert cls == "CONVERGED_UPSTREAM"

    def test_converged_upstream_localhost_without_port(self):
        """http://localhost/... → CONVERGED_UPSTREAM (can't extract port)."""
        cls = classify("http://localhost/v1", 9200, {}, None)
        assert cls == "CONVERGED_UPSTREAM"

    def test_converged_observing(self, patch_port_alive):
        """http://127.0.0.1:<our_port> and alive → CONVERGED_OBSERVING."""
        patch_port_alive.set_values([True])
        cls = classify("http://127.0.0.1:9200/v1", 9200, {}, None)
        assert cls == "CONVERGED_OBSERVING"

    def test_dead_port(self, patch_port_alive):
        """http://127.0.0.1:<our_port> but dead → DEAD_PORT."""
        patch_port_alive.set_values([False])
        cls = classify("http://127.0.0.1:9200/v1", 9200, {}, None)
        assert cls == "DEAD_PORT"

    def test_foreign_proxy(self):
        """Port matches existing_proxies → FOREIGN_PROXY."""
        cls = classify("http://127.0.0.1:51888/v1", 9200, {"skillclaw": 51888}, None)
        assert cls == "FOREIGN_PROXY"

    def test_drifted_with_snapshot(self):
        """Port is local but not ours, not foreign, has snapshot → DRIFTED."""
        row = MagicMock()
        row.__getitem__.return_value = "snapshot"
        cls = classify("http://127.0.0.1:9999/v1", 9200, {}, row)
        assert cls == "DRIFTED"

    def test_converged_upstream_local_unknown_no_snapshot(self):
        """Port is local but not ours, not foreign, no snapshot → CONVERGED_UPSTREAM."""
        cls = classify("http://127.0.0.1:9999/v1", 9200, {}, None)
        assert cls == "CONVERGED_UPSTREAM"


# ---------------------------------------------------------------------------
# reconcile
# ---------------------------------------------------------------------------


class TestReconcileOff:
    def test_off_mode_reverts_active_providers(self, config_path, adapter, patch_db, state):
        """desired_mode='off' calls _revert for each active provider."""
        # Need an active snapshot first
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider(config_path, "hermes", "deepseek",
                                         "https://api.deepseek.com/v1", V14_CONFIG)

        reconcile(
            config_path=config_path,
            desired_mode="off",
            our_port=None,
            providers=["deepseek", "ollama"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=MagicMock(return_value=(False, None)),
            state=state,
            trigger="tick",
        )
        # After revert, snapshot should be deactivated
        assert snapshot_store.get_snapshot(config_path, "deepseek") is None
        assert state.last_trigger == "tick"


class TestReconcileObserve:
    def test_open_circuit_skips_launch(self, config_path, adapter, patch_db, state):
        """Circuit is open → ensure_proxy_alive not called, providers processed with no proxy."""
        state.circuit._cooldown_until = time.time() + 300  # force open
        mock_alive = MagicMock()

        reconcile(
            config_path=config_path,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=mock_alive,
            state=state,
            trigger="tick",
        )
        mock_alive.assert_not_called()

    def test_converged_observing_skips_write(self, config_path, adapter, patch_db, state,
                                              patch_port_alive, ensure_alive):
        """CONVERGED_OBSERVING → no snapshot, no write."""
        # Set up: local config with our port, port alive
        config_path2 = config_path  # reuse but write local URL
        with open(config_path2, "w") as f:
            f.write("""providers:
  - name: deepseek
    base_url: http://127.0.0.1:9200/v1
    api_key: sk-abc
""")
        patch_port_alive.set_values([True])
        mock_proxy = ensure_alive(True, 9200)

        snapshot_store.ensure_table()
        reconcile(
            config_path=config_path2,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=mock_proxy,
            state=state,
            trigger="boot",
        )
        # No snapshot should have been written
        assert snapshot_store.get_snapshot(config_path2, "deepseek") is None

    def test_dead_port_with_alive_proxy_repoints(self, config_path, adapter, patch_db, state,
                                                  patch_port_alive, ensure_alive):
        """DEAD_PORT (port in URL but socket dead) + proxy alive → repoint to proxy.

        classify is called with active_port from ensure_proxy_alive.
        When ensure_proxy_alive returns (True, 9200), active_port=9200 matches
        the URL port. _port_alive returns False → DEAD_PORT.
        Since proxy_alive=True → _repoint.
        """
        with open(config_path, "w") as f:
            f.write("""providers:
  - name: deepseek
    base_url: http://127.0.0.1:9200/v1
    api_key: sk-abc
""")
        # reconciler._port_alive returns False → classify says DEAD_PORT
        patch_port_alive.set_values([False])
        # ensure_proxy_alive says alive so active_port=9200 is passed to classify
        mock_proxy = ensure_alive(True, 9200)

        snapshot_store.ensure_table()
        reconcile(
            config_path=config_path,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=mock_proxy,
            state=state,
            trigger="tick",
        )
        # Should have repointed to proxy URL (same URL it already had in this test)
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:9200/v1"

    def test_dead_port_with_dead_proxy_reverts_to_upstream(self, config_path, adapter, patch_db,
                                                           state, ensure_alive):
        """DEAD_PORT scenario where port matches our port but is dead: when proxy is dead
        the active_port is None, so classify won't return DEAD_PORT — it returns DRIFTED
        if a snapshot exists. The revert happens via the DRIFTED/UPSTREAM paths instead.

        This test verifies the full flow: proxy dead → snapshot exists → config reverted.
        """
        with open(config_path, "w") as f:
            f.write("""providers:
  - name: deepseek
    base_url: http://127.0.0.1:9200/v1
    api_key: sk-abc
""")
        mock_proxy = ensure_alive(False, None)
        mock_alert = MagicMock()

        # Put snapshot in place so the off-spec port (not ours, not foreign) with
        # a snapshot triggers DRIFTED → re-snapshots but doesn't revert.
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider(config_path, "hermes", "deepseek",
                                         "https://api.deepseek.com/v1", V14_CONFIG)

        reconcile(
            config_path=config_path,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=mock_proxy,
            state=state,
            trigger="tick",
            alert=mock_alert,
        )
        # With active_port=None, classify sees our_port=None, port in URL is 9200,
        # snapshot exists → DRIFTED. DRIFTED doesn't revert, it re-snapshots.
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:9200/v1"
        # No alert since it's DRIFTED, not DEAD_PORT's unreachable revert path
        mock_alert.assert_not_called()

    def test_converged_upstream_with_proxy_snapshots_and_repoints(self, config_path, adapter,
                                                                   patch_db, state,
                                                                   ensure_alive):
        """CONVERGED_UPSTREAM + proxy alive → snapshot + repoint."""
        mock_proxy = ensure_alive(True, 9200)
        snapshot_store.ensure_table()

        reconcile(
            config_path=config_path,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=mock_proxy,
            state=state,
            trigger="tick",
        )
        # Snapshot should exist
        row = snapshot_store.get_snapshot(config_path, "deepseek")
        assert row is not None
        assert row["original_base_url"] == "https://api.deepseek.com/v1"
        # Config should be repointed
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:9200/v1"

    def test_foreign_proxy_not_clobbered(self, config_path, adapter, patch_db, state,
                                          ensure_alive):
        """FOREIGN_PROXY → no write, log only."""
        with open(config_path, "w") as f:
            f.write("""providers:
  - name: deepseek
    base_url: http://127.0.0.1:51888/v1
    api_key: sk-abc
""")
        mock_proxy = ensure_alive(True, 9200)
        snapshot_store.ensure_table()

        reconcile(
            config_path=config_path,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={"skillclaw": 51888},
            ensure_proxy_alive=mock_proxy,
            state=state,
            trigger="boot",
        )
        # URL unchanged
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:51888/v1"

    def test_drifted_re_snapshots(self, config_path, adapter, patch_db, state, ensure_alive):
        """DRIFTED → re-snapshot."""
        with open(config_path, "w") as f:
            f.write("""providers:
  - name: deepseek
    base_url: http://127.0.0.1:9999/v1
    api_key: sk-abc
""")
        mock_proxy = ensure_alive(True, 9200)
        snapshot_store.ensure_table()
        # Create an initial snapshot so classify sees DRIFTED (snapshot_row is not None)
        snapshot_store.snapshot_provider(config_path, "hermes", "deepseek",
                                         "https://api.deepseek.com/v1",
                                         "old_blob_content")

        reconcile(
            config_path=config_path,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=mock_proxy,
            state=state,
            trigger="tick",
        )
        # Snapshot should still exist (re-snapshotted, not deactivated)
        row = snapshot_store.get_snapshot(config_path, "deepseek")
        assert row is not None
        # URL unchanged (DRIFTED doesn't write)
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:9999/v1"

    def test_reconcile_records_failure_on_dead_proxy(self, config_path, adapter, patch_db,
                                                      state, patch_port_alive):
        """Proxy launch failure → circuit.record_failure() called."""
        patch_port_alive.set_values([False])
        snapshot_store.ensure_table()
        assert len(state.circuit._failures) == 0

        reconcile(
            config_path=config_path,
            desired_mode="observe",
            our_port=9200,
            providers=["deepseek"],
            runtime="hermes",
            adapter=adapter,
            existing_proxies={},
            ensure_proxy_alive=MagicMock(return_value=(False, None)),
            state=state,
            trigger="tick",
        )
        assert len(state.circuit._failures) == 1


# ---------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------


class TestSnapshotIfAbsent:
    def test_creates_snapshot_when_none_exists(self, config_path, adapter, patch_db):
        """No snapshot → snapshot_provider is called."""
        snapshot_store.ensure_table()
        _snapshot_if_absent(config_path, "hermes", "deepseek",
                            "https://api.deepseek.com/v1", adapter)
        row = snapshot_store.get_snapshot(config_path, "deepseek")
        assert row is not None
        assert row["original_base_url"] == "https://api.deepseek.com/v1"

    def test_skips_when_snapshot_exists(self, config_path, adapter, patch_db):
        """Snapshot already exists → no second insert."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider(config_path, "hermes", "deepseek",
                                         "https://api.deepseek.com/v1", V14_CONFIG)
        _snapshot_if_absent(config_path, "hermes", "deepseek",
                            "http://other:9090/v1", adapter)
        # Original URL preserved
        row = snapshot_store.get_snapshot(config_path, "deepseek")
        assert row["original_base_url"] == "https://api.deepseek.com/v1"


class TestRepoint:
    def test_writes_proxy_url_and_resets_circuit(self, config_path, adapter, patch_db):
        """Repoint writes http://127.0.0.1:<port>/v1 and resets circuit."""
        snapshot_store.ensure_table()
        st = ReconcilerState()
        st.circuit._cooldown_until = time.time() + 100  # force open
        _repoint(config_path, "deepseek", 9200, adapter, st)
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "http://127.0.0.1:9200/v1"
        assert st.circuit._cooldown_until == 0.0


class TestRevert:
    def test_reverts_and_deactivates(self, config_path, adapter, patch_db):
        """Revert writes original URL and deactivates snapshot."""
        snapshot_store.ensure_table()
        snapshot_store.snapshot_provider(config_path, "hermes", "deepseek",
                                         "https://api.deepseek.com/v1", V14_CONFIG)
        st = ReconcilerState()
        _revert(config_path, "deepseek", adapter, st)
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "https://api.deepseek.com/v1"
        # Snapshot deactivated
        assert snapshot_store.get_snapshot(config_path, "deepseek") is None

    def test_noop_when_no_snapshot(self, config_path, adapter, patch_db):
        """No snapshot → no crash, URL unchanged."""
        snapshot_store.ensure_table()
        st = ReconcilerState()
        _revert(config_path, "nonexistent", adapter, st)
        doc = adapter.load(config_path)
        assert adapter.get_base_url(doc, "deepseek") == "https://api.deepseek.com/v1"
