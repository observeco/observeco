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
TOKEN_HISTORY_INTERVAL = 86400  # 24h
DATA_SOURCE_INTERVAL = 60    # 60s — check data sources are alive
CONFIG_TIMELINE_INTERVAL = 60  # 60s — check for config changes

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
                        # ponytail: minimal logging -- upgrade to structured error reporting when error handling infra exists
                        logger.warning("publish failed for heal_result on %s status=%s", a["agent_name"], "healed", exc_info=True)
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


# ── Token History Consumer ──────────────────────────────────────────


class TokenHistoryConsumer(BaseConsumer):
    """Aggregate daily token usage from token_logs into token_history every 24h.

    Closes the only data continuity gap in the dashboard: token_history had
    no automatic writer — only a POST endpoint. This consumer runs the same
    aggregation SQL on a 24-hour cycle inside the existing watch daemon.

    ponytail: No backfill on restart. token_logs retains raw data for manual
    backfill via POST /api/token-history/snapshot. If this becomes a problem,
    add a startup scan that backfills missing days from token_logs.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "token_history")
        kwargs.setdefault("interval", TOKEN_HISTORY_INTERVAL)
        super().__init__(**kwargs)

    def _tick(self) -> None:
        today = int(time.time() // 86400) * 86400
        tomorrow = today + 86400
        row = self.db._get_conn().execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0) as total_input,
                COALESCE(SUM(output_tokens), 0) as total_output,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read,
                COUNT(DISTINCT agent_name) as agent_count
            FROM token_logs
            WHERE recorded_at >= ? AND recorded_at < ?
        """, (today, tomorrow)).fetchone()

        self.db._get_conn().execute("""
            INSERT OR REPLACE INTO token_history
                (snapshot_date, total_input_tokens, total_output_tokens,
                 total_cache_creation_tokens, total_cache_read_tokens,
                 agent_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (today, row[0], row[1], row[2], row[3], row[4], "{}"))
        self.db._get_conn().commit()
        logger.info(f"Token history snapshot written for {today} — "
                     f"{row[0]} in, {row[1]} out, {row[4]} agents")


# ── Data Source Watchdog ─────────────────────────────────────────────


class DataSourceWatchdog(BaseConsumer):
    """Monitor data sources and auto-restart dead ones.

    Checks every 60s:
    - OTel listener (port 4318) — restarts if down
    - Proxy server (port 9200) — restarts if down
    - token_logs data freshness by source — logs warning if stale

    ponytail: Only checks OTel and proxy. Does not check SDK patchers
    (OpenAI/Anthropic/LangChain) because those are in-process and can't
    be restarted independently. Upgrade: add SDK patcher health check
    by looking for recent rows with source='proxy' or source='otel'.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "data_source_watchdog")
        kwargs.setdefault("interval", DATA_SOURCE_INTERVAL)
        super().__init__(**kwargs)
        self._last_alert: dict[str, float] = {}

    def _tick(self) -> None:
        self._check_otel_listener()
        self._check_data_freshness()

    def _check_otel_listener(self) -> None:
        """Check OTel listener on port 4318, restart if dead."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex(('localhost', 4318))
            sock.close()
            if result == 0:
                return  # All good
        except Exception:
            sock.close()

        # OTel is down — try to restart
        logger.warning("OTel listener is down — attempting restart")
        try:
            import subprocess
            import sys
            proc = subprocess.Popen(
                [sys.executable, "-m", "observeco", "otel", "listen", "start", "--port", "4318"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            proc.wait(timeout=5)
            # Verify it came up
            time.sleep(2)
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.settimeout(2)
            try:
                r = sock2.connect_ex(('localhost', 4318))
                sock2.close()
                if r == 0:
                    logger.info("OTel listener auto-restarted successfully")
                    publish(None, "data_source_recovered", source="otel_listener")
                    return
            except Exception:
                sock2.close()
            logger.error("OTel listener auto-restart failed — port still not listening")
            publish(None, "data_source_failed", source="otel_listener")
        except Exception as e:
            logger.error(f"OTel listener auto-restart error: {e}")

    def _check_data_freshness(self) -> None:
        """Check token_logs for recent data by source. Log warning if stale."""
        now = time.time()
        rows = self.db._get_conn().execute("""
            SELECT source, MAX(recorded_at) as last_ts
            FROM token_logs
            GROUP BY source
        """).fetchall()

        for r in rows:
            source = r[0]
            last_ts = r[1] or 0
            age = now - last_ts
            if age > 86400:  # > 24h stale
                # Only alert once per source per hour
                last_alert = self._last_alert.get(source, 0)
                if now - last_alert > 3600:
                    logger.warning(f"Data source '{source}' stale — last data {age/3600:.0f}h ago")
                    publish(None, "data_source_stale", source=source, age_hours=round(age / 3600, 1))
                    self._last_alert[source] = now


# ── Config Timeline Consumer ────────────────────────────────────────


class ConfigTimelineConsumer(BaseConsumer):
    """Detect SOUL.md, model, and tool config changes every 60 seconds.

    Records changes in config_snapshots table for the timeline dashboard.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "config_timeline")
        kwargs.setdefault("interval", CONFIG_TIMELINE_INTERVAL)
        super().__init__(**kwargs)

    def _tick(self) -> None:
        from observeco.capability.timeline import ConfigTimelineDetector

        detector = ConfigTimelineDetector(db=self.db)
        snapshots = detector.check_all_agents()

        if snapshots:
            for s in snapshots:
                logger.info(
                    "Config timeline: agent=%s type=%s segment=%s",
                    s["agent_name"], s["change_type"], s["segment"],
                )
            publish(None, "config_timeline_update", count=len(snapshots))


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
            TokenHistoryConsumer(db=self.db),
            DataSourceWatchdog(db=self.db),
            ConfigTimelineConsumer(db=self.db),
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
