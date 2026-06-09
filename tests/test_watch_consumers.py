"""Tests for event-driven watch consumers."""
from observeco.watch_consumers import (
    BaseConsumer,
    ConsumerManager,
    DriftConsumer,
    GardenConsumer,
    HealConsumer,
    PathwayConsumer,
    PruneConsumer,
)


def test_base_consumer_start_stop():
    """BaseConsumer should start and stop cleanly."""
    c = BaseConsumer(name="test", interval=9999)
    c.start()
    assert c._running is True
    assert c._thread is not None
    assert c._thread.is_alive()
    c.stop()
    assert c._running is False


def test_base_consumer_idempotent_start():
    """Starting an already-running consumer should be a no-op."""
    c = BaseConsumer(name="test", interval=9999)
    c.start()
    c.start()  # second start should not create new thread
    assert c._running is True


def test_consumer_manager_registers_all():
    """ConsumerManager should register all 5 standard consumers."""
    mgr = ConsumerManager()
    mgr.register_all()
    assert len(mgr.consumers) == 5
    names = [c.name for c in mgr.consumers]
    assert "drift" in names
    assert "garden" in names
    assert "pathway" in names
    assert "heal" in names
    assert "prune" in names


def test_consumer_manager_start_stop_all():
    """ConsumerManager should start and stop all consumers."""
    mgr = ConsumerManager()
    mgr.register_all()
    mgr.start_all()
    for c in mgr.consumers:
        assert c._running is True
    mgr.stop_all()
    for c in mgr.consumers:
        assert c._running is False


def test_drift_consumer_runs_without_crash():
    """DriftConsumer._tick should not crash with no data."""
    c = DriftConsumer()
    c._tick()  # Should not raise with empty DB
    assert True


def test_garden_consumer_runs_without_crash():
    """GardenConsumer._tick should not crash with no memory files."""
    c = GardenConsumer()
    c._tick()  # Should not raise
    assert True


def test_pathway_consumer_runs_without_crash():
    """PathwayConsumer._tick should handle missing pathway module."""
    c = PathwayConsumer()
    c._tick()  # Should not raise
    assert True


def test_heal_consumer_runs_without_crash():
    """HealConsumer._tick should not crash with empty DB."""
    c = HealConsumer()
    c._tick()
    assert True


def test_prune_consumer_runs_without_crash():
    """PruneConsumer._tick should handle missing prune module."""
    c = PruneConsumer()
    c._tick()
    assert True
