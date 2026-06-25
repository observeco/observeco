# obs-spec-026 — Supervision Hierarchy & Resource Reconciler

**Spec ID:** obs-spec-026
**Title:** Supervision hierarchy — a framework of guardians, not a pile of loops
**Document version:** 1.2
**Status:** ⬜ DRAFT — for review
**Owner:** Main (arch + impl)
**Created:** 2026-06-17
**Supersedes:** obs-spec-025 (partially — the proxy config reconciler becomes one resource under this framework)
**Extends:** obs-spec-025 framework pattern into the `reconciler/` package
**Standards:** GS-019 (Data & Observability Continuity)
**Target stack:** All platforms (macOS/POSIX with launchd/systemd as supervision host)

## 1. What this spec is for

We've built three variants of the same control loop:

| What | File | Invariant |
|------|------|-----------|
| Proxy config reconciler | `proxy/reconciler.py` | Config → live proxy XOR real upstream, never dead port |
| Data source watchdog | `watch_consumers.py:DataSourceWatchdog` | OTel listener + proxy server are alive, data flows |
| Health checker | `health.py` | L1 operational + L2 functional checks (checks, no auto-heal) |

Three files. Three loop architectures. Three circuit-breaker implementations. And each time we add a new "thing that should be in state X," we're about to write a fourth.

This spec introduces a **supervision hierarchy**: one framework that every guardian of an invariant lives under. It is the answer to the question:

> Which invariants, if they rot quietly, make ObserveCo either lie to the user or break their agents?

Those invariants are exactly six. They live under one reconciler, supervised by one meta-monitor, supervised by the OS.

### 1.1 Relationship to existing subsystems

The `heal/` module (agent-level auto-remediation) and the `reconciler/` module (infrastructure-level invariant guardians) are **siblings** with different concerns:

| | `heal/` | `reconciler/` |
|---|---|---|
| **Subject** | Agents (Hermes/OpenClaw processes) | ObserveCo's own infrastructure |
| **What it checks** | Agent pulse, circuit breakers, error patterns | OTel port, DB integrity, proxy config, clock monotonicity |
| **What it heals** | Restart agent, trim context, pip install | Restart OTel listener, vacuum DB, repoint proxy config |
| **Action budget** | Max 3 retries, 4h cooldown per agent | Max N retries in rolling window, shared circuit breaker |
| **Trigger** | CLI `observeco heal` or cron | Tick loop (every 60s) inside `observeco watch` |

They share the event bus (`publish()`) but have independent execution paths. The reconciler is a `BaseConsumer` inside the watch daemon; `heal/` is a standalone CLI command.

---

## 2. The invariants — exactly six

| # | Name | Invariant | If it rots silently |
|---|------|-----------|---------------------|
| 1 | **Proxy config** | `base_url` → live proxy XOR real upstream, never dead port | Agents fail or cost tracking silently breaks |
| 2 | **Source liveness** | OTel listener (port 4318), proxy server, watchdog daemon are alive and writing | Data stops flowing, dashboard shows stale charts — **already hit this** |
| 3 | **Store integrity** | DB schema matches code, no WAL corruption, no silent data loss, space available | Dashboard errors or displays wrong data |
| 4 | **Meta-monitor** | The reconciler itself fires every tick and has recent output | No invariants are checked — the whole safety net has collapsed |
| 5 | **Clock & sleep** | Time moves monotonically, sleep durations are real-wall | Token timestamps wrong, drift fires on phantom deltas, snapshot order breaks |
| 6 | **Cost accuracy** | Sum(token_logs) ≈ sum(provider API costs) within threshold | User trusts the cost number on the dashboard, and it's wrong |

These six are **all** the mission-critical reconcilers. Every future need is either a new `ManagedResource` under this framework or it doesn't belong here.

---

## 3. Architecture

### 3.1 Supervision hierarchy (three levels)

```
┌────────────────────────────────────────┐
│          launchd / systemd             │  ← OS-level: restarts the whole process
│       (KeepAlive, max 3 restart / 10s) │     bounded in intensity
└───────────────────┬────────────────────┘
                    │ supervises
┌───────────────────▼────────────────────┐
│     ReconcilerMetaMonitor              │  ← level 2: checks the reconciler itself
│  checks: last_reconcile_at < 2 ticks   │     must be its own process or thread with
│  heals: SIGUSR1 → /restart endpoint    │     independent lifecycle
│  escalates: logs/alert if not healing  │
└───────────────────┬────────────────────┘
                    │ supervises
┌───────────────────▼────────────────────┐
│        ResourceReconciler              │  ← level 1: the main loop
│  ticks every N seconds                 │
│  runs each ManagedResource.check()     │
│  if not UP → heal() with budget guard  │
│  publishes status for each resource    │
└──────┬──────┬──────┬──────┬──────┬──────┬──────┐
       │      │      │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼      ▼      ▼
    Proxy   Source  Store   Clock  Cost    (future)
    Config  LivenessIntegrity       Accuracy
```

### 3.2 Level-triggered, not edge-triggered

Every tick, the reconciler **checks every resource**. It does not trust edge signals (SIGCHLD, fsnotify, launchd events) as the sole trigger for healing. Edge signals can:

- Be missed (SIGCHLD delivered to the wrong thread)
- Fire before the new state settles (fsnotify fires on partial write)
- Not fire at all (process killed with SIGKILL)

The edge signals are **wake-up optimizations** — they cause an early tick — but the tick always re-checks ground truth, same as Kubernetes controllers.

### 3.3 ManagedResource contract

```python
class ManagedResource(ABC):
    """One invariant that can silently drift. Declares probe, heal, budget."""

    name: str  # unique identifier, used in status API and logging
    invariant: str  # human-readable: what must stay true

    @abstractmethod
    def probe(self) -> ResourceState:
        """Check current state. Returns UP | DOWN | DEGRADED | UNKNOWN.
        Must complete within a bounded time (< 5s) — the entire reconciler
        loop is blocked until all probes return.

        Probes are wrapped in a per-probe timeout by the ResourceReconciler
        (concurrent.futures with 5s timeout). If a probe times out, it is
        treated as UNKNOWN and the resource is not healed this tick.
        Probes should NOT implement their own timeout — the reconciler
        handles it.
        """
        ...

    @abstractmethod
    def heal(self) -> bool:
        """Attempt to restore the invariant. Returns True if state is UP after.
        Must NOT retry internally — retries are orchestrated by the reconciler
        via RestartBudget. Raises on unexpected errors (not "tried and failed").
        """
        ...

    def describe(self) -> str:
        """Human-readable one-liner for dashboard and logs."""
        return f"{self.name}: {self.invariant}"

    # Optional hooks
    def on_transition(self, old: ResourceState, new: ResourceState) -> None:
        """Called on every state change. Publish events, log, alert here."""
        ...
```

```python
class ResourceState(Enum):
    UP = "up"          # Invariant holds. No action needed.
    DOWN = "down"      # Invariant broken. Heal required.
    DEGRADED = "degraded"  # Invariant partially holds. Heal recommended but not urgent.
    UNKNOWN = "unknown"    # Can't determine. Re-probe next tick.
```

### 3.4 RestartBudget (shared)

One `RestartBudget` per resource. Extracted from `proxy/reconciler.py:CircuitBreaker` and made generic.

```python
@dataclass
class RestartBudget:
    """How aggressively the reconciler should attempt to heal a resource.

    Default: 3 attempts in 300s window → 300s cooldown.
    """
    max_attempts: int = 3
    window_seconds: int = 300      # rolling window for counting attempts
    cooldown_seconds: int = 300    # backoff duration after budget exhausted
    _attempts: deque = field(default_factory=lambda: deque(maxlen=100))
    _cooldown_until: float = 0.0

    def can_attempt(self) -> bool:
        """True if within budget and not in cooldown."""
        if time.time() < self._cooldown_until:
            return False
        self._prune()
        return len(self._attempts) < self.max_attempts

    def record_failure(self) -> None:
        self._attempts.append(time.time())
        self._prune()
        if len(self._attempts) >= self.max_attempts:
            self._cooldown_until = time.time() + self.cooldown_seconds

    def record_success(self) -> None:
        self._attempts.clear()  # success resets the budget

    def _prune(self) -> None:
        cutoff = time.time() - self.window_seconds
        while self._attempts and self._attempts[0] < cutoff:
            self._attempts.popleft()
```

Moving from `proxy/reconciler.py` to `reconciler/circuit.py` — the proxy reconciler's circuit breaker was already this pattern. Now it's shared.

### 3.5 Hysteresis — prevent flap

No resource transitions to `DOWN` on a single failed probe. Every probe result is debounced:

```python
@dataclass
class DebouncedState:
    """Debounce a noisy probe. Only transitions after N consecutive same-state probes."""
    stable_after: int = 2  # consecutive same values to emit a state change
    _history: ResourceState = ResourceState.UNKNOWN
    _streak: int = 0

    def update(self, raw: ResourceState) -> Optional[ResourceState]:
        """Returns a new effective state only after stable_after consecutive readings."""
        if raw == self._history:
            self._streak += 1
            if self._streak >= self.stable_after:
                return self._history
            return None
        self._streak = 1
        self._history = raw
        return None

    @property
    def current(self) -> ResourceState:
        return self._history if self._streak >= self.stable_after else ResourceState.UNKNOWN
```

This means a one-tick network timeout can't trigger a heal loop.

### 3.6 ResourceReconciler — the main loop

```python
class ResourceReconciler:
    """Owns a set of ManagedResources and runs them on a shared tick."""

    def __init__(self, resources: list[ManagedResource], tick_s: int = 60):
        self.resources = {r.name: r for r in resources}
        self.debouncers = {r.name: DebouncedState() for r in resources}
        self.budgets = {r.name: RestartBudget() for r in resources}
        self._lock = threading.Lock()
        # Operations-in-flight ledger — see §4.1
        self._ops_in_flight: dict[str, float] = {}

        # Per-resource fast-path overrides — see §5.1 for proxy reconciler
        # Resources with skip_debounce=True skip hysteresis (immediate reaction)
        # and may set their own tick interval
        self._skip_debounce: set[str] = set()
        self._fast_tick_intervals: dict[str, int] = {}

    def reconcile(self) -> dict[str, dict]:
        """One full pass. Returns status snapshot.
        Each probe is wrapped in a 5s timeout via concurrent.futures.
        Timed-out probes return UNKNOWN and are not healed this tick.
        """
        statuses = {}
        with self._lock:
            for name, resource in self.resources.items():
                raw = self._probe_with_timeout(resource, timeout=5.0)
                if name in self._skip_debounce:
                    # Fast-path: no hysteresis — react immediately
                    effective = raw
                else:
                    effective = self.debouncers[name].update(raw)
                if effective and effective != ResourceState.UP:
                    state = self._reconcile_one(name, resource, effective)
                else:
                    state = raw.value  # UP or steady
                statuses[name] = {
                    "state": state,
                    "probe": raw.value,
                }
        return statuses

    def _probe_with_timeout(self, resource: ManagedResource, timeout: float = 5.0) -> ResourceState:
        """Run resource.probe() with a timeout. Returns UNKNOWN on timeout.

        Uses a daemon thread with join(timeout) — Python cannot cancel running
        threads, so the thread is left alive (daemon=True means it won't prevent
        process exit). The probe result is communicated via a list reference.
        If the thread is still alive after timeout, we log a warning and continue.
        """
        result: list[ResourceState] = []
        exc: list[Exception] = []

        def _run():
            try:
                result.append(resource.probe())
            except Exception as e:
                exc.append(e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            logger.warning(f"Reconciler {resource.name}: probe timed out after {timeout}s — thread abandoned")
            return ResourceState.UNKNOWN
        if exc:
            logger.error(f"Reconciler {resource.name}: probe raised: {exc[0]}")
            return ResourceState.UNKNOWN
        return result[0] if result else ResourceState.UNKNOWN

    def _reconcile_one(self, name: str, resource: ManagedResource, needed: ResourceState) -> str:
        budget = self.budgets[name]

        if not budget.can_attempt():
            return "cooldown"

        # Check operations-in-flight before healing — see §4.1
        if self._has_conflicting_op(name):
            return "deferred"

        # Emit an operations-in-flight marker
        self._ops_in_flight[name] = time.time()

        try:
            healed = resource.heal()
        except Exception as e:
            budget.record_failure()
            logger.error(f"Reconciler {name}: heal raised: {e}")
            return "heal_error"

        if healed:
            budget.record_success()
            resource.on_transition(needed, ResourceState.UP)
            return "healed"
        else:
            budget.record_failure()
            return "heal_failed"

    def _has_conflicting_op(self, name: str) -> bool:
        """Check if any conflicting resource has an operation in flight.
        Returns True if a conflict is detected — the current resource
        should defer to the next tick.
        """
        now = time.time()
        conflicts = CONFLICT_MAP.get(name, set())
        for other_name, started_at in list(self._ops_in_flight.items()):
            if other_name in conflicts and (now - started_at) < 10:
                return True
        return False
```

### 3.7 Meta-monitor

The meta-monitor is **its own thread** (not a `BaseConsumer`) inside the watch daemon. It checks that the reconciler's last-reconcile timestamp is not stale.

```
Thread: MetaMonitor
  tick every 30s
  check: reconciler.last_reconcile_at >= now - 2 * reconciler.tick_s
    if stale:
      log WARNING "reconciler stopped — triggering recovery"
      publish("meta:reconciler_stale")
      # If stale for 4+ ticks, escalate to critical
      if stale_count >= 4:
        publish("meta:reconciler_dead")
        # Write health file for OS-level supervisor to detect
        write_health_file("reconciler", "DEAD")
```

The OS-level supervisor (launchd/systemd) watches the process itself — if the whole daemon dies, it restarts. The meta-monitor watches the *function* of the daemon — if the reconciler loop has deadlocked (process alive, thread stuck), the meta-monitor detects it and either kills itself (triggering OS restart) or signals a separate watchdog.

**Design choice:** The meta-monitor is simpler than a full SRE dead man's switch infrastructure. It's a single thread with a single invariant. This is intentional — the meta-monitor must be too simple to fail in novel ways. No abstractions. No plugins. No config.

**Recovery topology (acyclic):**

```
OS supervisor (launchd/systemd)  ──restarts──→  whole process
    ↑                                                │
    │ (reads meta_monitor.health for                  │
    │  DEAD signal)                                   │
    │                                                 ▼
MetaMonitor thread (separate)  ──writes──→  meta_monitor.health
                                               (os-supervised)
    ↑                                                │
    │ (stale > 60s)                                  │
    │                                                 ▼
Reconciler thread  ──restarts──→  MetaMonitor              ← best-effort, not primary
```

The **primary** recovery path for a dead reconciler is the OS supervisor reading `meta_monitor.health`. If the reconciler is wedged, the meta-monitor detects it (last_reconcile_at stale for 4+ ticks) and writes DEAD to the health file. The OS supervisor picks this up and restarts the entire process. This path does not depend on the reconciler running.

The **secondary** path is the reconciler checking `meta_monitor.health` before each reconcile pass (the `_check_meta_monitor` method below). This only works if the reconciler is not wedged — so it catches meta-monitor thread crashes, not reconciler deadlocks. If both are wedged, only the OS supervisor path works; the meta-monitor's health file goes stale, and after 4+ ticks, the OS supervisor sees DEAD and restarts.

**Ponytail:** If the OS supervisor is absent (foreground/container mode), the meta-monitor health file has no automatic reader. In this mode, detection is best-effort: the reconciler's `_check_meta_monitor` runs before each tick, and if the meta-monitor crashes, the reconciler restarts it. If both crash, the process must be restarted manually. See §4.3 "No OS supervisor available."

**Meta-monitor self-health:** The meta-monitor writes its own health file (`meta_monitor.health`) every tick. The reconciler's `_check_meta_monitor` runs before each reconcile pass as a secondary check — if the file is stale (> 60s), it logs a warning and restarts the meta-monitor thread. This is best-effort: it only catches meta-monitor crashes, not reconciler deadlocks (which are handled by the primary OS supervisor path).

```python
# In ResourceReconciler, before each reconcile():
def _check_meta_monitor(self) -> None:
    """Check meta-monitor health file. Restart thread if stale."""
    try:
        hb = json.loads(Path(self._meta_health_path).read_text())
        age = time.time() - hb.get("last_check", 0)
        if age > 60:
            logger.warning(f"Meta-monitor health stale ({age:.0f}s) — restarting")
            self._restart_meta_monitor()
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("Meta-monitor health file missing — starting")
        self._restart_meta_monitor()
```

---

## 4. Coordination & safety

### 4.1 Operations-in-flight ledger

The resource reconciler holds an `_ops_in_flight: dict[str, float]` that records when a heal action starts. Before checking/healing any resource, the reconciler checks whether any *other* resource's `ops_in_flight` is within the last N seconds. If a conflicting pair is detected, the later one is deferred to the next tick.

**Why this matters:**

> Store-integrity vacuums the DB (takes exclusive lock) → source-liveness sees writes stop → concludes the source died → tries to restart the healthy OTel listener → feedback loop

The conflict matrix:

| | Proxy config | Source liveness | Store integrity | Cost accuracy |
|---|---|---|---|---|
| Proxy config | — | safe | safe | safe |
| Source liveness | safe | — | **conflict** | safe |
| Store integrity | safe | **conflict** | — | safe |
| Cost accuracy | safe | safe | safe | — |

Only one real conflict: **store integrity** (vacuum/backup/migration) takes an exclusive DB lock that starves source-liveness probes (which read `token_logs`). The ledger defers source-liveness checks until after store integrity releases the lock.

The conflict map is explicitly registered, not computed:

```python
CONFLICT_MAP = {
    "store_integrity": {"source_liveness", "cost_accuracy"},
    "source_liveness": {"store_integrity"},
    "cost_accuracy": {"store_integrity"},
}
```

`ponytail:` This is a static registration. If the resource set grows, the conflict map must be updated manually. Upgrade path: dynamically infer conflict by observing which resources share a DB connection pool and serializing those.

### 4.2 Memory guard

The reconciler tracks its own RSS and refuses to execute a reconcile tick if memory exceeds a threshold:

```python
def _self_preserve(self) -> bool:
    """Return True if the reconciler should skip this tick to save memory."""
    try:
        process = psutil.Process(os.getpid())
        rss_mb = process.memory_info().rss / (1024 * 1024)
        self._rss_mb = rss_mb
        if rss_mb > 100:  # soft limit
            logger.warning(f"Reconciler RSS {rss_mb:.0f}MB > 100MB — skipping tick")
            return True
        return False
    except Exception:
        return False  # can't measure → assume ok
```

This protects the host. Adopted from OTel Collector's `memory_limiter` processor — the safety net must not OOM the machine.

### 4.3 Restart intensity bounding

The OS-level supervisor (launchd `KeepAlive` / systemd `StartLimitIntervalSec`) bounds process restarts to protect the host from a tight crash loop.

| Supervisor | Bounding mechanism | Default |
|------------|-------------------|---------|
| launchd | `ThrottleInterval` | 10 seconds between relaunches |
| systemd | `StartLimitIntervalSec` + `StartLimitBurst` | 5 starts in 10 seconds → stop |

The reconciler's own `RestartBudget` bounds *resource* restarts (per-resource). The OS supervisor bounds *process* restarts (daemon-wide). Both are required.

**No OS supervisor available:** When running in a container, as a foreground process, or on a platform without launchd/systemd (e.g. Windows without NSSM), the meta-monitor's health file is the only recovery mechanism. The process runs in the foreground with no auto-restart. The meta-monitor still detects reconciler deadlock and writes a DEAD health file, but no OS process will restart it — the user must restart manually or configure their own supervisor. This is documented as a known limitation; the reconciler works correctly in all modes, only auto-recovery is degraded.

---

## 5. The six resources — spec

### 5.1 ProxyConfigResource

**Source:** Extracted from `proxy/reconciler.py:reconcile()` + `classify()`, `_repoint()`, `_revert()`

**Invariant:** Each managed provider's `base_url` points at a live ObserveCo proxy, XOR at the real upstream.

**Probe:** Read each provider's `base_url` via the obs-spec-024 adapter. Attempt socket connect to the port. Classify into one of 5 states (CONVERGED_OBSERVING, CONVERGED_UPSTREAM, DEAD_PORT, FOREIGN_PROXY, DRIFTED).

**Heal actions:**
- DEAD_PORT + proxy alive → `_repoint()` to new port
- DEAD_PORT + proxy dead → `_revert()` to snapshot upstream + alert
- UPSTREAM (desired=observe) → `snapshot_if_absent()` then `_repoint()`
- FOREIGN_PROXY → skip (not ours, don't clobber)
- DRIFTED → re-snapshot (external edit detected)

**Budget:** Default RestartBudget (3/300s → 300s cooldown)

**Fast path override:** ProxyConfigResource registers `skip_debounce=True` — the dead-port invariant must heal within one tick (<10s), not wait for `stable_after=2` consensus. It also registers `fast_tick_interval=10` for a 10s sub-tick (separate from the main 60s shared tick) aligned with the SIGCHLD signal trigger from obs-spec-025 §3.3. The 025-specified 60s circuit-breaker window is preserved via per-resource RestartBudget configuration (3/60s → 300s cooldown, not the default 3/300s).

**Moved files:**
- `proxy/reconciler.py:CircuitBreaker` → `reconciler/circuit.py` (shared)
- `proxy/reconciler.py:classify()` + `reconcile()` + helpers → `reconciler/resources/proxy_config.py`
- `proxy/reconciler.py:reconcile_loop()` → deprecated; replaced by `ResourceReconciler.reconcile()` + tick loop
- `proxy/reconciler.py:get_status()` → replaced by `ResourceReconciler.get_status()` + API endpoint

The backward-compat shim: `proxy/reconciler.py` re-exports from `reconciler/resources/proxy_config.py` for one release cycle.

### 5.2 SourceLivenessResource

**Source:** Replaces `watch_consumers.py:DataSourceWatchdog`

**Invariant:** OTel listener (port 4318), proxy server (port 9200), and the watch daemon's own pulse (port 9119) are listening and responding.

**Probe:** Socket connect to each port. For OTel, POST an OPTIONS ping to verify protocol response (not just port open — a dead process can hold a port). For proxy, send a lightweight GET to `/v1/models` and expect a 200/401 (not connection refused). For pulse, check the health endpoint.

**Heal actions:**
- OTel listener dead → `subprocess.Popen(['python', '-m', 'observeco', 'otel', 'listen', 'start', '--port', '4318'])` → verify port open
- Proxy server dead → `subprocess.Popen(['python', '-m', 'observeco', 'proxy', 'server', '--port', '9200'])` → verify `/v1/models` responds
- Watch daemon dead → meta-monitor handles this (level 2); source liveness does not restart its own supervisor

**Budget:** Stricter — 2/60s → 300s cooldown. OTel/proxy restart is cheap; flapping is worse.

**Deleted files:**
- `watch_consumers.py:DataSourceWatchdog` class removed
- `DATA_SOURCE_INTERVAL` constant removed from `watch_consumers.py`

### 5.3 StoreIntegrityResource — NEW

**Invariant:** SQLite schema matches expected version, WAL mode healthy, no silent corruption, free space > 1GB.

**Probe:**
1. `PRAGMA schema_version` — no unexpected drift
2. `PRAGMA integrity_check` (fast version, not full) — no corruption
3. `PRAGMA wal_checkpoint` — WAL not stuck growing
4. `SELECT MAX(id) FROM token_logs` — row count within expected range (no silent truncation)
5. `psutil.disk_usage(get_data_dir())` — free space > 1GB (soft), < 100MB (critical)

**Heal actions:**
- Schema mismatch → `observeco db migrate` (via subprocess)
- WAL stuck → `PRAGMA wal_checkpoint(TRUNCATE)`
- Schema missing table → run migration for that table
- Disk low → warn via event bus (no automated cleanup; user must act)
- Integrity check finds corruption → alert CRITICAL, do not attempt auto-repair (SQLite corruption rarely recovers cleanly)

**Budget:** Wider — 2/3600s (2 per hour). Integrity checks are expensive (can take seconds on a large DB), and vacuums lock the DB.

**Pony tail:** `PRAGMA integrity_check` on a large DB (>100K token_logs rows) can take 5+ seconds. If this blocks the reconciler tick, reduce frequency to every 10 ticks or run it in a background thread that feeds results back. Upgrade path: background integrity_check thread with result polling.

### 5.4 ClockMonotonicResource — NEW

**Invariant:** `time.time()` returns monotonically non-decreasing values, and `time.sleep()` actually sleeps for at least the requested duration.

**Probe:**
1. Record `time.monotonic()` + `time.time()` at start of tick
2. After all other probes, record again
3. If `time.time()` jumped backward (NTP correction) or forward > 5s (suspend/resume), flag as DEGRADED
4. Track tick interval histogram: if median drift from expected tick_s > 20%, flag as DEGRADED

**Heal:** None for the clock itself — you can't fix NTP drift or a VM pause from user space. The heal action is:
1. Log the event and tag all token_log rows in the affected window with `clock_discontinuity`
2. Publish alert if the jump exceeds a threshold (> 30s)

**Budget:** Not applicable (no healing). State transitions only.

### 5.5 CostAccuracyResource — NEW

**Invariant:** Sum of `token_logs.cost_usd` per provider is within 5% of the provider's billing API reported cost for the same period.

**Probe:**
1. Sum `token_logs.cost_usd` per provider for the most recent complete day
2. Query each provider's usage API (OpenAI cost, Anthropic cost, etc. — where available)
3. Compute `abs(computed - billed) / billed`
4. Return UP if < 5%, DEGRADED if 5-20%, DOWN if > 20%

**Heal:**
- If DEGRADED: publish a notification (cost discrepancy detected, recalibrating)
- If DOWN: publish alert + recalibrate the price table (re-fetch from provider API)

**Budget:** 1/86400s (once per day). This is an expensive probe (network calls to multiple provider billing APIs).

**Pony tail:** Provider billing APIs are not all available. OpenAI's usage API returns per-day totals; Anthropic's is less granular. This resource gracefully returns UNKNOWN for providers without a billing API and only checks providers that support it.

### 5.6 ReconcilerMetaMonitor (level 2 — not a ManagedResource)

**Invariant:** The `ResourceReconciler` has completed at least one reconcile pass in the last `2 * tick_s` seconds.

**Probe:**
1. Read `reconciler.last_reconcile_at` (thread-safe atomic access)
2. If `age > 2 * tick_s`: stale — log WARNING
3. If `age > 4 * tick_s`: critical — escalate (publish alert, write health file)

**Heal:**
- Stale (2-4 ticks): publish event, do not restart yet (transient)
- Critical (>4 ticks): write a health file that the OS supervisor reads → triggers process restart

**Implementation:** The meta-monitor is NOT a `ManagedResource` because it cannot use the `ResourceReconciler` to supervise itself (circular dependency). It is a separate thread that directly reads `last_reconcile_at` from a thread-safe variable and writes to an OS-monitored health file.

---

## 6. What changes — file mapping

### Deleted

| File | Reason | Replaced by |
|------|--------|-------------|
| `watch_consumers.py:DataSourceWatchdog` class | Built before we generalized the pattern | `reconciler/resources/source_liveness.py` |

### Moved / extracted

| Code | From | To |
|------|------|----|
| `CircuitBreaker` dataclass | `proxy/reconciler.py` | `reconciler/circuit.py` (shared) |
| `classify()`, `reconcile()`, `_repoint()`, `_revert()`, `_snapshot_if_absent()` | `proxy/reconciler.py` | `reconciler/resources/proxy_config.py` |
| `_handle_sigchld`, `_sigchld_event`, `reconcile_loop()` | `proxy/reconciler.py` | Deprecated. `ResourceReconciler.reconcile()` + external tick loop replaces it. |

### New

| File | Purpose |
|------|---------|
| `reconciler/__init__.py` | Exports `ResourceReconciler`, `ManagedResource`, `ResourceState` |
| `reconciler/circuit.py` | `RestartBudget` (generic circuit breaker) |
| `reconciler/base.py` | `ManagedResource` ABC, `DebouncedState`, `ResourceReconciler` class |
| `reconciler/resources/__init__.py` | Registry of all managed resources |
| `reconciler/resources/proxy_config.py` | `ProxyConfigResource` (extracted) |
| `reconciler/resources/source_liveness.py` | `SourceLivenessResource` (replaces DataSourceWatchdog) |
| `reconciler/resources/store_integrity.py` | `StoreIntegrityResource` (new) |
| `reconciler/resources/clock_monotonic.py` | `ClockMonotonicResource` (new) |
| `reconciler/resources/cost_accuracy.py` | `CostAccuracyResource` (new) |
| `reconciler/meta_monitor.py` | `ReconcilerMetaMonitor` thread (level 2) |
| `tests/reconciler/test_base.py` | Tests for ResourceReconciler + DebouncedState + RestartBudget |
| `tests/reconciler/test_resources.py` | Tests for each ManagedResource |

### Modified

| File | Change |
|------|--------|
| `proxy/reconciler.py` | Backward-compat shim: re-exports from `reconciler/resources/proxy_config.py`. Deprecated in comments. |
| `watch_consumers.py` | Remove `DataSourceWatchdog` class, `DATA_SOURCE_INTERVAL` constant. Add `ResourceReconciler` as a consumer instead. |
| `health.py` | Health dashboard endpoint reads from `ResourceReconciler.get_status()` instead of running its own probes. |
| `src/observeco/dashboard/server.py` | Add `/api/reconciler/status` endpoint returning all resource states. |

---

## 7. Integration: how it wires into the daemon

The `ResourceReconciler` runs as a `BaseConsumer` inside the existing watch daemon (`observeco watch`):

```python
# In watch_consumers.py, register_all():
from observeco.reconciler import ResourceReconciler
from observeco.reconciler.resources import (
    ProxyConfigResource,
    SourceLivenessResource,
    StoreIntegrityResource,
    ClockMonotonicResource,
    CostAccuracyResource,
)

self.consumers = [
    DriftConsumer(db=self.db),
    GardenConsumer(db=self.db),
    PathwayConsumer(db=self.db),
    HealConsumer(db=self.db),
    PruneConsumer(db=self.db),
    TokenHistoryConsumer(db=self.db),
    # One reconciler to rule them all — replaces DataSourceWatchdog
    ResourceReconciler(
        resources=[
            ProxyConfigResource(),
            SourceLivenessResource(),
            StoreIntegrityResource(),
            ClockMonotonicResource(),
            CostAccuracyResource(),
        ],
        tick_s=60,  # every 60 seconds
    ),
]
```

The `MetaMonitor` is a separate thread started in the watch daemon's main startup path (not a consumer), because it supervises the consumer manager:

```python
# In watch.py, after ConsumerManager.start_all():
from observeco.reconciler.meta_monitor import start_meta_monitor
start_meta_monitor(reconciler_ref, tick_s=30)
```

---

## 8. Status API

The dashboard exposes a single endpoint that returns the state of every managed resource:

```
GET /api/reconciler/status

{
  "reconciler": {
    "last_reconcile_at": 1718612345.0,
    "age_seconds": 15,
    "resources": {
      "proxy_config": {
        "state": "up",
        "probe": "up",
        "last_heal": null,
        "heal_count": 0,
        "last_error": null,
      },
      "source_liveness": {
        "state": "up",
        "probe": "up",
        "last_heal": null,
      },
      "store_integrity": {
        "state": "up",
        "probe": "up",
        "last_integrity_check": 1718612300.0,
        "db_size_mb": 42.5,
        "free_space_gb": 187.3,
      },
      "clock_monotonic": {
        "state": "up",
        "probe": "up",
        "tick_drift_pct": 2.3,
      },
      "cost_accuracy": {
        "state": "up",
        "probe": "up",
        "last_check": "2026-06-16",
        "discrepancy_pct": 0.8,
      },
    }
  },
  "meta_monitor": {
    "state": "healthy",
    "last_check": 1718612340.0,
  }
}
```

---

## 9. Data Continuity (GS-019 — mandatory)

**What happens to existing data?** No telemetry is migrated or deleted. The `reconciler/` package creates no new SQLite tables. The `proxy_config_snapshots` table (Migration 22 from obs-spec-025) remains unchanged; the proxy config resource merely moves the code that reads/writes it to a new file. The watch daemon's consumer infrastructure (`pulse_log`, `action_log`) is unchanged.

- Migrations: None
- Telemetry tables touched: None

**Is backup required?** No. All changes are file-reorganization. No destructive operations.

**What does the user see if empty?** The `/api/reconciler/status` endpoint returns all resources with `state: unknown` and `probe: unknown`. The dashboard shows a compact status card: "Reconciler: starting up (5/5 resources unknown)".

**What's the recovery path?** If the `reconciler/` package fails to import: the watch daemon starts without it, logs a critical error, and the dashboard shows "Reconciler: unavailable". The existing `DataSourceWatchdog` fallback is removed (it was only introduced in this session and never shipped), but the proxy/config reconciler's old `reconcile_loop()` remains importable as a fallback if `ResourceReconciler` fails to construct.

**Self-monitoring:** Per reconcile tick, record: resource states, heal counts, operation conflicts deferred, meta-monitor staleness checks, memory usage, tick duration.

---

## 10. Tasks

| # | Task | Owner | Priority | Notes |
|---|------|-------|----------|-------|
| 26.1 | `reconciler/` package skeleton + `ManagedResource` ABC + `ResourceState` | Main | P0 | |
| 26.2 | `reconciler/circuit.py` — `RestartBudget` extracted from `proxy/reconciler.py:CircuitBreaker` | Main | P0 | Tests must pass for both old import and new import |
| 26.3 | `reconciler/base.py` — `DebouncedState`, `ResourceReconciler`, operations-in-flight ledger, memory guard | Main | P0 | |
| 26.4 | `reconciler/resources/proxy_config.py` — `ProxyConfigResource` (extracted from `proxy/reconciler.py`) | Main | P0 | Backward-compat shim in old location |
| 26.5 | `reconciler/resources/source_liveness.py` — `SourceLivenessResource` (replaces `DataSourceWatchdog`) | Main | P0 | |
| 26.6 | `reconciler/resources/store_integrity.py` — `StoreIntegrityResource` (new) | Main | P1 | Integrity check runs every 10 ticks; vacuum must not block other probes |
| 26.7 | `reconciler/resources/clock_monotonic.py` — `ClockMonotonicResource` (new) | Main | P1 | |
| 26.8 | `reconciler/resources/cost_accuracy.py` — `CostAccuracyResource` (new) | Main | P2 | Depends on provider billing API |
| 26.9 | `reconciler/meta_monitor.py` — `MetaMonitor` thread | Main | P0 | |
| 26.10 | Wire `ResourceReconciler` into watch daemon (replace `DataSourceWatchdog`, add 4 new resources) | Main | P1 | Proxy config resource is conditionally available (only if proxy tier is active) |
| 26.11 | `/api/reconciler/status` endpoint in dashboard | Main | P1 | |
| 26.12 | Backward compat shim in `proxy/reconciler.py` | Main | P1 | Re-export from `reconciler/resources/proxy_config.py`. Deprecation warning. |
| 26.13 | Remove `DataSourceWatchdog` from `watch_consumers.py` | Main | P1 | After source_liveness resource is wired and tested |
| 26.14 | Tests: `DebouncedState` — transient failure suppressed, sustained failure propagates | Main | P0 | |
| 26.15 | Tests: `RestartBudget` — 3 failures in window → cooldown, success resets | Main | P0 | |
| 26.16 | Tests: `ResourceReconciler` — 5 resources, all probes, healing, conflict deferral | Main | P0 | |
| 26.17 | Tests: each resource's probe + heal in isolation | Main | P0 | |
| 26.18 | Tests: operations-in-flight conflict deferral (store_integrity blocks source_liveness) | Main | P1 | |
| 26.19 | Lifecycle tests: start/stop cycle, double-start guard, double-stop guard | Main | P1 | Per system-design playbook §4.2 |
| 26.20 | Lifecycle tests: kill-and-recover (SIGKILL → restart), stale detection, orphan PID | Main | P1 | Per system-design playbook §4.2 |
| 26.21 | Lifecycle tests: meta-monitor crash → reconciler detects and restarts | Main | P1 | Per §3.7 self-health mechanism |

---

## 11. Success criteria

- [ ] `ResourceReconciler` runs all 5+ resources on a single 60s tick without blocking longer than 10s total
- [ ] `DebouncedState` correctly suppresses a 1-tick transient and catches a 2-tick sustained failure
- [ ] `RestartBudget` correctly: allows 3 heals in 300s, enters cooldown on 4th, resets on success
- [ ] Operations-in-flight ledger defers source_liveness probe if store_integrity just acquired DB lock
- [ ] `RestartBudget` is the *only* circuit breaker pattern in the codebase (no second implementation elsewhere)
- [ ] All existing proxy config reconciler tests pass after extraction (backward compat shim)
- [ ] Meta-monitor detects a deadlocked reconciler within `2 * tick_s` and escalates within `4 * tick_s`
- [ ] `/api/reconciler/status` returns state for all registered resources (UP/DOWN/DEGRADED/UNKNOWN) with probe timestamps

---

## 12. Downstream blind spots (captured, not addressed here)

These were surfaced by the audit against mature observability systems. They are real blind spots — each is tracked to a separate spec:

| Blind spot | Severity | Spec |
|------------|----------|------|
| Cardinality limits (unbounded tool names, prompt hashes) | P1 | obs-spec-0XX-cardinality.md |
| Sampling + tail-based sampling | P1 | obs-spec-0XX-sampling.md |
| Backpressure (bounded buffer, drop-or-spill) | P0 | obs-spec-0XX-backpressure.md |
| Time-series rollups (raw → 1m → 1h → 1d) | P1 | obs-spec-0XX-rollups.md |
| Alert lifecycle (inhibition, grouping, ack, maintenance) | P1 | obs-spec-0XX-alert-lifecycle.md |
| Local-host security (loopback-only, token auth, store encryption) | P0 | obs-spec-0XX-local-security.md |
| Upstream conformance testing (nightly Hermes/OpenClaw contract tests) | P1 | obs-spec-0XX-conformance.md |
| Verified clean uninstall (byte-for-byte restore, launchd removal, port release) | P0 | obs-spec-0XX-clean-uninstall.md |
| Observer effect measurement (latency added, shadow mode) | P1 | obs-spec-0XX-observer-effect.md |
| Chart seam annotation (model changes, pricing changes, Hermes versions) | P2 | obs-spec-0XX-seams.md |
| Cost reconciliation with provider billing API | P2 | Handled in §5.5 of this spec (CostAccuracyResource) |
| Ambient surface (menubar, weekly digest) | P2 | obs-spec-0XX-ambient-surface.md |
| Max blast radius bounded | P0 | obs-spec-0XX-blast-radius.md |
| Alert credibility (start under-alerting, expand) | P2 | Implicit in obs-spec-0XX-alert-lifecycle.md |

These are not TODO items on this spec — they are separate specs. This spec builds the *foundation* (the supervision hierarchy) on which those solutions depend.

---

## 13. Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-17 | `ReconcilerMetaMonitor` is NOT a `ManagedResource` | Circular dependency: it would need the reconciler to supervise itself. Separate thread with direct variable access. |
| 2026-06-17 | `RestartBudget` replaces `CircuitBreaker` universally | The proxy config reconciler's CB pattern was correct; it just needed generic parameterization. |
| 2026-06-17 | `DebouncedState` uses `stable_after=2` (2 consecutive same readings) | One reading is noise; two is a transition. Aligns with Alertmanager's `FOR` clause concept. |
| 2026-06-17 | Operations-in-flight ledger uses static conflict map | Dynamic inference (watching which resources share a DB connection) adds complexity without proven benefit for the current 5-resource set. |
| 2026-06-17 | StoreIntegrity runs integrity_check every 10 ticks, not every tick | `PRAGMA integrity_check` is expensive on large DBs (>100K rows). 10-minute cadence is sufficient for corruption detection — corruption doesn't heal itself between checks. |
| 2026-06-17 | SourceLiveness replaces DataSourceWatchdog, not supplement | The watchdog was built in this session as an emergency fix. It was the strawman that exposed the pattern. It gets deleted. |
| 2026-06-17 | Audit findings are captured but deferred to separate specs | The supervision hierarchy is the foundation. Without it, the other fixes are more bespoke piles. The hierarchy ships first. |
