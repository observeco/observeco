"""Proxy config reconciler — enforces the invariant:

  config → live proxy XOR real upstream, never dead proxy

Only needed for the proxy-config tier (config-rewrite, opt-in).
The proxy-launcher tier (env injection) needs no reconciler because
nothing is written to disk.

Circuit-breaker: 3 proxy-launch failures in 60 s → 5-minute cooldown.
"""

from __future__ import annotations

import logging
import signal
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Literal

from observeco.proxy import snapshot_store
from observeco.proxy.config_io import atomic_write_base_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

State = Literal[
    "CONVERGED_OBSERVING",
    "CONVERGED_UPSTREAM",
    "DEAD_PORT",
    "FOREIGN_PROXY",
    "DRIFTED",
]

Trigger = Literal["SIGCHLD", "tick", "boot", "launchd"]

CIRCUIT_FAILURE_WINDOW = 60       # seconds
CIRCUIT_MAX_FAILURES = 3
CIRCUIT_COOLDOWN = 300            # 5 minutes


@dataclass
class CircuitBreaker:
    """Tracks relaunch failures and enforces a cooldown when the budget is exhausted."""

    _failures: deque = field(default_factory=lambda: deque(maxlen=CIRCUIT_MAX_FAILURES))
    _cooldown_until: float = 0.0
    # ponytail: persisted via proxy_reconciler_state table (get/set per tick),
    # but still loses the _failures deque on restart. That's acceptable: cooldown
    # preservation is what matters for crash safety; failure counting resets.

    def __post_init__(self) -> None:
        """Restore persisted cooldown on construction (survives ObserveCo restart)."""
        try:
            persisted = snapshot_store.get_reconciler_cooldown()
            if persisted > time.time():
                self._cooldown_until = persisted
        except Exception:
            pass  # fresh DB — no reconciler_state table yet

    def record_failure(self) -> None:
        self._failures.append(time.time())

    def is_open(self) -> bool:
        """True when the circuit is open (cooldown active)."""
        if time.time() < self._cooldown_until:
            return True
        # Check if we've hit the failure budget in the rolling window
        now = time.time()
        recent = [t for t in self._failures if now - t <= CIRCUIT_FAILURE_WINDOW]
        if len(recent) >= CIRCUIT_MAX_FAILURES:
            self._cooldown_until = now + CIRCUIT_COOLDOWN
            try:
                snapshot_store.set_reconciler_cooldown(self._cooldown_until)
            except Exception:
                pass  # fresh DB — no reconciler_state table yet
            logger.warning(
                "reconciler: circuit breaker open — %d failures in %ds, cooldown until %s",
                len(recent), CIRCUIT_FAILURE_WINDOW,
                time.strftime("%H:%M:%S", time.localtime(self._cooldown_until)),
            )
            return True
        return False

    def reset(self) -> None:
        self._failures.clear()
        self._cooldown_until = 0.0
        try:
            snapshot_store.set_reconciler_cooldown(0.0)
        except Exception:
            pass

    @property
    def cooldown_until(self) -> float:
        return self._cooldown_until


@dataclass
class ReconcilerState:
    """Mutable state shared across reconcile ticks."""

    circuit: CircuitBreaker = field(default_factory=CircuitBreaker)
    last_trigger: str = ""
    last_reconcile_at: float = 0.0


# ---------------------------------------------------------------------------
# Module-level state + cross-component visibility (dashboard, CLI)
# ---------------------------------------------------------------------------

_state: ReconcilerState | None = None
_lock = threading.Lock()
_sigchld_event = threading.Event()


def _handle_sigchld(signum: int, frame: object) -> None:
    _sigchld_event.set()


def get_status() -> dict:
    """Return circuit-breaker status for the dashboard endpoint."""
    global _state
    with _lock:
        if _state is None:
            return {
                "circuit_open": False,
                "cooldown_until": 0.0,
                "last_trigger": "",
                "last_reconcile_at": 0.0,
            }
        circuit = _state.circuit
        return {
            "circuit_open": circuit.is_open(),
            "cooldown_until": circuit.cooldown_until,
            "last_trigger": _state.last_trigger,
            "last_reconcile_at": _state.last_reconcile_at,
        }


def reconcile_loop(
    *,
    config_path: str,
    our_port: int | None,
    providers: list[str],
    runtime: str,
    adapter: type,
    existing_proxies: dict[str, int] | None = None,
    ensure_proxy_alive: Callable[[int | None], tuple[bool, int | None]] | None = None,
    alert: Callable[[str, str], None] | None = None,
    tick_s: float = 10.0,
) -> tuple[threading.Event, threading.Thread]:
    """Start a daemon thread calling reconcile() every *tick_s* seconds
    and also on SIGCHLD.  Returns (stop_event, thread) so the caller
    can shut it down.

    ponytail: signal.signal(SIGCHLD) must be called from the main thread.
    If invoked from a non-main thread the handler is silently omitted and
    only the tick timer triggers reconciles.  Upgrade path: use a
    self-pipe (os.pipe + select) instead of signal for the thread-safe
    wake-up.
    """
    from observeco.proxy.process import ensure_proxy_alive as _default_ensure

    global _state

    if ensure_proxy_alive is None:
        ensure_proxy_alive = _default_ensure
    if existing_proxies is None:
        existing_proxies = {}

    with _lock:
        _state = ReconcilerState()

    stop_event = threading.Event()

    # Install SIGCHLD handler — only works from main thread
    try:
        signal.signal(signal.SIGCHLD, _handle_sigchld)
    except ValueError:
        pass  # not in main thread, tick-only mode

    def _loop() -> None:
        while not stop_event.is_set():
            _sigchld_event.wait(timeout=tick_s)
            _sigchld_event.clear()
            if stop_event.is_set():
                break
            with _lock:
                reconcile(
                    config_path=config_path,
                    desired_mode="observe",
                    our_port=our_port,
                    providers=providers,
                    runtime=runtime,
                    adapter=adapter,
                    existing_proxies=existing_proxies,
                    ensure_proxy_alive=ensure_proxy_alive,  # type: ignore
                    state=_state,  # type: ignore
                    trigger="tick",
                    alert=alert,
                )

    t = threading.Thread(target=_loop, daemon=True, name="reconciler-loop")
    t.start()
    return stop_event, t


# ---------------------------------------------------------------------------
# Port liveness
# ---------------------------------------------------------------------------


def _port_alive(port: int) -> bool:
    """True if something is listening on 127.0.0.1:<port>."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# State classifier
# ---------------------------------------------------------------------------


def classify(
    current_url: str,
    our_port: int | None,
    existing_proxies: dict[str, int],
    snapshot_row: object,  # sqlite3.Row | None
) -> State:
    """Classify the current base_url into one of the five reconciler states."""
    if not current_url.startswith("http://127.0.0.1:") and not current_url.startswith(
        "http://localhost:"
    ):
        return "CONVERGED_UPSTREAM"

    # Extract port from the URL
    try:
        port_str = current_url.split(":")[2].split("/")[0]
        port = int(port_str)
    except (IndexError, ValueError):
        return "CONVERGED_UPSTREAM"

    if our_port is not None and port == our_port:
        if _port_alive(port):
            return "CONVERGED_OBSERVING"
        else:
            return "DEAD_PORT"

    # Port belongs to a known foreign proxy (e.g. Skillclaw)
    if port in existing_proxies.values():
        return "FOREIGN_PROXY"

    # Port is local but not ours and not a known proxy → external edit
    if snapshot_row is not None:
        return "DRIFTED"

    return "CONVERGED_UPSTREAM"


# ---------------------------------------------------------------------------
# Core reconcile function
# ---------------------------------------------------------------------------


def reconcile(
    *,
    config_path: str,
    desired_mode: Literal["observe", "off"],
    our_port: int | None,
    providers: list[str],
    runtime: str,
    adapter: type,
    existing_proxies: dict[str, int],
    ensure_proxy_alive: Callable[[int | None], tuple[bool, int | None]],
    state: ReconcilerState,
    trigger: Trigger,
    alert: Callable[[str, str], None] | None = None,
) -> None:
    """Run one reconcile pass.

    Args:
        config_path: absolute path to the agent's config file.
        desired_mode: "observe" (proxy active) or "off" (revert to upstream).
        our_port: the port ObserveCo's proxy should run on.
        providers: list of provider names to manage.
        runtime: "hermes" | "openclaw".
        adapter: the version-specific adapter class (HermesSchemaV14 or V16).
        existing_proxies: from EnvSnapshot.existing_proxies (foreign proxy detection).
        ensure_proxy_alive: callable that launches/checks the proxy, returns (alive, port).
        state: mutable reconciler state (circuit breaker etc.).
        trigger: which event triggered this pass.
        alert: optional callable(event_type, detail) for surfacing alerts.
    """
    state.last_trigger = trigger
    state.last_reconcile_at = time.time()
    logger.info("reconcile: trigger=%s mode=%s providers=%s", trigger, desired_mode, providers)

    snapshot_store.ensure_table()

    if desired_mode == "off":
        for row in snapshot_store.active_providers(config_path):
            _revert(config_path, str(row["provider"]), adapter, state)
        return

    # Attempt to ensure the proxy is alive (with circuit-breaker guard)
    if state.circuit.is_open():
        proxy_alive, active_port = False, None
        logger.warning("reconciler: circuit open, skipping proxy relaunch")
    else:
        proxy_alive, active_port = ensure_proxy_alive(our_port)
        if not proxy_alive:
            state.circuit.record_failure()

    for provider in providers:
        try:
            current_url = adapter.get_base_url(adapter.load(config_path), provider)
        except Exception as exc:
            logger.warning("reconciler: can't read config for provider=%s: %s", provider, exc)
            continue

        if current_url is None:
            continue

        row = snapshot_store.get_snapshot(config_path, provider)
        cls = classify(current_url, active_port, existing_proxies, row)
        logger.debug("reconciler: provider=%s state=%s", provider, cls)

        if cls == "CONVERGED_OBSERVING":
            continue  # idempotent — no write needed

        elif cls == "DEAD_PORT":
            if proxy_alive and active_port is not None:
                _repoint(config_path, provider, active_port, adapter, state)
            else:
                _revert(config_path, provider, adapter, state)
                if alert:
                    alert("proxy_unrecoverable", f"provider={provider}")

        elif cls == "CONVERGED_UPSTREAM":
            if proxy_alive and active_port is not None:
                # Take a snapshot of the original before we first repoint
                _snapshot_if_absent(config_path, runtime, provider, current_url, adapter)
                _repoint(config_path, provider, active_port, adapter, state)

        elif cls == "FOREIGN_PROXY":
            logger.info(
                "reconciler: FOREIGN_PROXY on provider=%s url=%s — not clobbering",
                provider, current_url,
            )

        elif cls == "DRIFTED":
            # External edit — re-snapshot but don't clobber
            logger.info(
                "reconciler: DRIFTED provider=%s new_url=%s — re-snapshotting",
                provider, current_url,
            )
            with open(config_path) as fh:
                blob = fh.read()
            snapshot_store.snapshot_provider(config_path, runtime, provider, current_url, blob)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _snapshot_if_absent(
    config_path: str,
    runtime: str,
    provider: str,
    original_url: str,
    adapter: type,
) -> None:
    if snapshot_store.get_snapshot(config_path, provider) is None:
        with open(config_path) as fh:
            blob = fh.read()
        snapshot_store.snapshot_provider(config_path, runtime, provider, original_url, blob)
        logger.debug("reconciler: snapshot captured for provider=%s", provider)


def _repoint(
    config_path: str,
    provider: str,
    port: int,
    adapter: type,
    state: ReconcilerState,
) -> None:
    url = f"http://127.0.0.1:{port}/v1"
    logger.info("reconciler: repointing provider=%s → %s", provider, url)
    atomic_write_base_url(config_path, provider, url, adapter)
    state.circuit.reset()


def _revert(
    config_path: str,
    provider: str,
    adapter: type,
    state: ReconcilerState,
) -> None:
    row = snapshot_store.get_snapshot(config_path, provider)
    if row is None:
        logger.warning("reconciler: no snapshot for provider=%s, cannot revert", provider)
        return
    original_url = str(row["original_base_url"])
    logger.info("reconciler: reverting provider=%s → %s", provider, original_url)
    atomic_write_base_url(config_path, provider, original_url, adapter)
    snapshot_store.deactivate_snapshot(config_path, provider)


# ---------------------------------------------------------------------------
# Self-check (one runnable assertion against the loop contract)
# ---------------------------------------------------------------------------


def _self_check() -> None:
    """Verify reconcile_loop starts and stops without error."""
    stop_evt, t = reconcile_loop(
        config_path="/dev/null",
        our_port=None,
        providers=["nonexistent"],
        runtime="hermes",
        adapter=object,
        existing_proxies={},
        tick_s=0.1,
    )
    assert t.is_alive(), "reconcile_loop thread should be alive after start"
    assert not stop_evt.is_set(), "stop_event should not be set after start"
    stop_evt.set()
    t.join(timeout=5)
    assert not t.is_alive(), "reconcile_loop thread should stop after stop_event"
    print("reconciler.py self-check: OK")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    _self_check()
