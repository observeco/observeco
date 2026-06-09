"""Event-driven consumers for the ObserveCo watch daemon.

Each consumer runs in its own thread, subscribing to events from the event bus.
Failure in one consumer does not affect others — per §7.1 spec.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from threading import Thread
from typing import Optional

from observeco.db import Database
from observeco.event_bus import publish

logger = logging.getLogger(__name__)

# ── Interval constants ─────────────────────────────────────────────

DRIFT_INTERVAL = 300      # 5 min
GARDEN_INTERVAL = 900     # 15 min
PATHWAY_INTERVAL = 900    # 15 min
PRUNE_INTERVAL = 86400    # 24h
SKILLS_INTERVAL = 604800  # 7 days
HEARTBEAT_INTERVAL = 30   # 30s

# ── Base Consumer ───────────────────────────────────────────────────


class BaseConsumer:
    """Abstract base for event-driven consumers.

    Each consumer runs in its own thread with:
    - Isolated try/except failure domain
    - Configurable tick interval
    - Start/stop lifecycle
    """

    def __init__(self, name: str, interval: float = DRIFT_INTERVAL,
                 db: Optional[Database] = None):
        self.name = name
        self.interval = interval
        self.db = db or Database()
        self._running = False
        self._thread: Optional[Thread] = None
        self._last_run = 0

    def start(self) -> None:
        """Start the consumer in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._loop, name=f"consumer-{self.name}", daemon=True)
        self._thread.start()
        logger.info(f"Consumer '{self.name}' started (interval={self.interval}s)")

    def stop(self) -> None:
        """Signal the consumer to stop."""
        self._running = False

    def _loop(self) -> None:
        """Main consumer loop — ticks on interval."""
        while self._running:
            try:
                now = time.time()
                if now - self._last_run >= self.interval:
                    self._tick()
                    self._last_run = now
            except Exception as e:
                logger.error(f"Consumer '{self.name}' error: {e}")
            time.sleep(1)

    def _tick(self) -> None:
        """Override with the consumer's work. Must not raise."""
        raise NotImplementedError


# ── Drift Consumer ──────────────────────────────────────────────────


class DriftConsumer(BaseConsumer):
    """Compute and log 7-day token drift every 5 minutes."""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "drift")
        kwargs.setdefault("interval", DRIFT_INTERVAL)
        super().__init__(**kwargs)
        self._components = ["identity", "skills", "memory", "tools", "guidance"]

    def _tick(self) -> None:
        from observeco.config import load_config

        config = load_config()
        agents = getattr(config, "agents", [])
        if not agents:
            return

        now = time.time()
        week_ago = now - 7 * 86400

        for agent_cfg in agents:
            name = agent_cfg.name
            trims = self.db.get_trims(agent_name=name, limit=50)
            if not trims or len(trims) < 2:
                continue

            latest = trims[0]
            week_entries = [t for t in trims if t.get("timestamp", 0) >= week_ago]

            for comp in self._components:
                current = latest.get(f"{comp}_tokens", 0) or 0
                comp_vals = [t.get(f"{comp}_tokens", 0) or 0 for t in week_entries]
                week_avg = int(sum(comp_vals) / max(len(comp_vals), 1))
                delta_pct = ((current - week_avg) / max(week_avg, 1)) * 100
                breached = int(abs(delta_pct) > 10.0)

                self.db.log_drift(name, comp, current, week_avg, delta_pct, bool(breached))

        publish(None, "drift_result", agents=len(agents))


# ── Garden Consumer ─────────────────────────────────────────────────


class GardenConsumer(BaseConsumer):
    """Scan MEMORY.md files and log garden data every 15 minutes."""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "garden")
        kwargs.setdefault("interval", GARDEN_INTERVAL)
        super().__init__(**kwargs)

    def _tick(self) -> None:
        from observeco.clawforge.garden import (
            _find_contradictions,
            _find_duplicates,
            _find_memory_files,
            _find_stale,
        )

        memories = _find_memory_files()
        if not memories:
            return

        for mem in memories:
            path = Path(mem["path"])
            if not path.exists():
                continue

            lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
            dupes = _find_duplicates(lines)
            contradictions = _find_contradictions(lines)
            stale = _find_stale(lines, str(path))

            dupe_score = min(40, len(dupes) * 5)
            contra_score = min(30, len(contradictions) * 10)
            stale_score = min(30, len(stale) * 3)
            debt_score = min(100, dupe_score + contra_score + stale_score)

            suggestions_parts = []
            if dupes:
                suggestions_parts.append(f"{len(dupes)} duplicates found")
            if contradictions:
                suggestions_parts.append(f"{len(contradictions)} contradictions found")
            if stale:
                suggestions_parts.append(f"{len(stale)} stale entries found")
            suggestions = "; ".join(suggestions_parts) or "No issues found"

            self.db.log_garden(mem["agent"], len(dupes), len(contradictions),
                               len(stale), debt_score, suggestions)

        publish(None, "garden_result", memories=len(memories))


# ── Pathway Consumer ────────────────────────────────────────────────


class PathwayConsumer(BaseConsumer):
    """Re-discover communication pathways every 15 minutes."""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "pathway")
        kwargs.setdefault("interval", PATHWAY_INTERVAL)
        super().__init__(**kwargs)

    def _tick(self) -> None:
        try:
            from observeco.pathway.discover import run_discover as discover_pathways
            discover_pathways()
            publish(None, "pathway_result", status="ok")
        except Exception:
            logger.warning("Pathway discovery skipped — module not installed")


# ── Heal Consumer ───────────────────────────────────────────────────


class HealConsumer(BaseConsumer):
    """Auto-heal dead agents by subscribing to probe_result events.

    Runs on a short interval and checks for recently dead agents.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "heal")
        kwargs.setdefault("interval", HEARTBEAT_INTERVAL)
        super().__init__(**kwargs)

    def _tick(self) -> None:
        # Check all agents — heal any that are dead
        agents = self.db.get_agents()
        now = time.time()
        for a in agents:
            if a.get("is_active") is False or a.get("is_active") == 0:
                continue
            pulses = self.db.get_recent_pulses(agent_name=a["agent_name"], limit=3)
            if pulses:
                latest = pulses[0]
                if now - latest.get("timestamp", 0) > 60 and latest.get("status") == "error":
                    # Agent has been erroring for 60+ seconds — try heal
                    try:
                        from observeco.heal import run_heal
                        run_heal(auto_heal=True, agent_name=a["agent_name"])
                        from observeco.alerts.push import push_alert
                        push_alert(
                            "agent_death",
                            f"🔴 {a['agent_name']} is dead — auto-heal triggered",
                            agent_name=a["agent_name"], db=self.db,
                        )
                        publish(None, "heal_result", agent_name=a["agent_name"], status="healed")
                    except Exception:
                        pass


# ── Prune Consumer ──────────────────────────────────────────────────


class PruneConsumer(BaseConsumer):
    """Run pruning every 24 hours."""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "prune")
        kwargs.setdefault("interval", PRUNE_INTERVAL)
        super().__init__(**kwargs)

    def _tick(self) -> None:
        try:
            from observeco.tracking.prune import run_prune
            run_prune(db=self.db)
            publish(None, "prune_result", status="ok")
        except Exception:
            logger.warning("Prune skipped — module not installed")


# ── Consumer Manager ────────────────────────────────────────────────


class ConsumerManager:
    """Manages lifecycle of all event-driven consumers."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.consumers: list[BaseConsumer] = []

    def register_all(self) -> None:
        """Create and register all standard consumers."""
        self.consumers = [
            DriftConsumer(db=self.db),
            GardenConsumer(db=self.db),
            PathwayConsumer(db=self.db),
            HealConsumer(db=self.db),
            PruneConsumer(db=self.db),
        ]

    def start_all(self) -> None:
        """Start all registered consumers."""
        for c in self.consumers:
            c.start()

    def stop_all(self) -> None:
        """Stop all registered consumers."""
        for c in self.consumers:
            c.stop()

    def add(self, consumer: BaseConsumer) -> None:
        """Register an additional consumer."""
        self.consumers.append(consumer)
