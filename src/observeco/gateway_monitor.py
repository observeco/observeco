"""Gateway Health Monitor — sidecar for OpenClaw + Hermes gateways.

Monitors gateway infrastructure for:
- Telegram connection pool exhaustion
- Memory leaks (RSS growth)
- Error rate spikes
- Agent activation stalls
- Platform disconnections

Auto-recovers by triggering gateway restart via SIGTERM (launchd handles restart).

Usage:
    observeco gateway-monitor              # daemon mode
    observeco gateway-monitor --once       # single check, then exit
    observeco gateway-monitor --foreground # run in foreground
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None

from observeco.dirs import hermes_home, openclaw_home

logger = logging.getLogger("observeco.gateway_monitor")

# ---------------------------------------------------------------------------
# Configuration — lazy init to avoid import-time I/O
# ---------------------------------------------------------------------------

def _get_hermes_home() -> Path:
    hh = hermes_home()
    return hh if hh is not None else Path.home() / ".hermes"

def _get_openclaw_home() -> Path:
    oc = openclaw_home()
    return oc if oc is not None else Path.home() / ".openclaw"

HERMES_HOME = _get_hermes_home()
OPENCLAW_HOME = _get_openclaw_home()
# ponytail: fallback to Path.home() / ".hermes"|".openclaw" when dirs returns None.
# If Hermes/OpenClaw is genuinely absent the downstream code still gets a valid
# Path — callers that need "is it installed?" should check dirs directly.

HERMES_LOG_DIR = HERMES_HOME / "logs"
HERMES_STATE_FILE = HERMES_HOME / "gateway_state.json"
OPENCLAW_LOG_DIR = Path("/tmp/openclaw")
OPENCLAW_CONFIG_FILE = OPENCLAW_HOME / "openclaw.json"

CHECK_INTERVAL = 60  # seconds
ALERT_COOLDOWN = 300  # don't re-alert same issue within 5 min

# Thresholds
POOL_TIMEOUT_WINDOW = 600  # 10 min
POOL_TIMEOUT_THRESHOLD = 5  # alerts if >5 in window
MEMORY_WARN_MB = 600
MEMORY_CRITICAL_MB = 800
MEMORY_GROWTH_WARN_MB_PER_HOUR = 50
ERROR_RATE_WARN_PERCENT = 1.0
ZERO_AGENTS_WARN_MINUTES = 15
UPTIME_WARN_HOURS = 24

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GatewayMetrics:
    """Metrics collected from a single gateway."""
    name: str  # "hermes" or "openclaw"
    pid: Optional[int] = None
    running: bool = False
    active_agents: int = 0
    memory_rss_mb: float = 0.0
    uptime_seconds: float = 0.0
    pool_timeouts_10min: int = 0
    error_count: int = 0
    total_log_lines: int = 0
    platforms: dict = field(default_factory=dict)
    last_check: float = field(default_factory=time.time)
    errors: list = field(default_factory=list)


@dataclass
class AlertState:
    """Tracks alert cooldowns to avoid spam."""
    last_alerts: dict = field(default_factory=dict)  # key -> timestamp

    def should_alert(self, key: str) -> bool:
        now = time.time()
        last = self.last_alerts.get(key, 0)
        if now - last >= ALERT_COOLDOWN:
            self.last_alerts[key] = now
            return True
        return False

# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

def parse_hermes_error_log(log_path: Path, window_seconds: int = POOL_TIMEOUT_WINDOW) -> dict:
    """Parse Hermes gateway.error.log for recent errors."""
    if not log_path.exists():
        return {"pool_timeouts": 0, "errors": [], "total_lines": 0}

    pool_timeouts = 0
    errors = []
    total_lines = 0

    try:
        # Read last 10KB efficiently
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 10240))
            tail = f.read().decode("utf-8", errors="replace")

        for line in tail.split("\n"):
            if not line.strip():
                continue
            total_lines += 1

            # Check for pool timeout
            if "Pool timeout" in line or "connection pool are occupied" in line:
                pool_timeouts += 1

            # Collect error lines
            if "ERROR" in line or "WARNING" in line:
                errors.append(line.strip()[:200])
    except Exception as e:
        logger.warning(f"Failed to parse {log_path}: {e}")

    return {
        "pool_timeouts": pool_timeouts,
        "errors": errors[-10:],  # last 10
        "total_lines": total_lines,
    }


def parse_openclaw_log(log_path: Path, window_seconds: int = POOL_TIMEOUT_WINDOW) -> dict:
    """Parse OpenClaw log file for errors."""
    if not log_path.exists():
        return {"rate_limits": 0, "errors": [], "total_lines": 0}

    rate_limits = 0
    errors = []
    total_lines = 0

    try:
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 10240))
            tail = f.read().decode("utf-8", errors="replace")

        for line in tail.split("\n"):
            if not line.strip():
                continue
            total_lines += 1

            if "429" in line or "rate_limit" in line or "Rate limit" in line:
                rate_limits += 1

            if "ERROR" in line or "error" in line.lower():
                errors.append(line.strip()[:200])
    except Exception as e:
        logger.warning(f"Failed to parse {log_path}: {e}")

    return {
        "rate_limits": rate_limits,
        "errors": errors[-10:],
        "total_lines": total_lines,
    }

# ---------------------------------------------------------------------------
# State file parsing
# ---------------------------------------------------------------------------

def read_json_safe(path: Path) -> dict:
    """Read a JSON file, return empty dict on failure."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def collect_hermes_metrics() -> GatewayMetrics:
    """Collect metrics from Hermes gateway."""
    metrics = GatewayMetrics(name="hermes")
    state = read_json_safe(HERMES_STATE_FILE)

    if state:
        metrics.pid = state.get("pid")
        metrics.running = state.get("gateway_state") == "running"
        metrics.active_agents = state.get("active_agents", 0)
        metrics.platforms = {
            k: v.get("state", "unknown")
            for k, v in state.get("platforms", {}).items()
        }

    # Memory from process
    if metrics.pid and psutil:
        try:
            proc = psutil.Process(metrics.pid)
            mem = proc.memory_info()
            metrics.memory_rss_mb = mem.rss / (1024 * 1024)
            metrics.uptime_seconds = time.time() - proc.create_time()
        except psutil.NoSuchProcess:
            pass

    # Parse error log
    error_log = HERMES_LOG_DIR / "gateway.error.log"
    parsed = parse_hermes_error_log(error_log)
    metrics.pool_timeouts_10min = parsed["pool_timeouts"]
    metrics.error_count = parsed["total_lines"]
    metrics.errors = parsed["errors"]

    return metrics


def collect_openclaw_metrics() -> GatewayMetrics:
    """Collect metrics from OpenClaw gateway."""
    metrics = GatewayMetrics(name="openclaw")

    # Find the gateway process by port
    try:
        import subprocess
        # Find process listening on port 18789
        result = subprocess.run(
            ["lsof", "-ti", ":18789"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            pid = int(result.stdout.strip().split("\n")[0])
            metrics.pid = pid
            metrics.running = True

            if psutil:
                proc = psutil.Process(pid)
                mem = proc.memory_info()
                metrics.memory_rss_mb = mem.rss / (1024 * 1024)
                metrics.uptime_seconds = time.time() - proc.create_time()
    except Exception:
        pass

    # Parse today's log
    import datetime
    today = datetime.date.today().isoformat()
    log_file = OPENCLAW_LOG_DIR / f"openclaw-{today}.log"
    parsed = parse_openclaw_log(log_file)
    metrics.error_count = parsed["total_lines"]
    metrics.errors = parsed["errors"]

    return metrics

# ---------------------------------------------------------------------------
# Alerting
# ---------------------------------------------------------------------------

def send_telegram_alert(message: str) -> bool:
    """Send alert via OpenClaw gateway (best-effort)."""
    import os
    chat_id = os.environ.get("OBSERVECO_TG_CHAT_ID", "")
    if not chat_id:
        logger.warning("OBSERVECO_TG_CHAT_ID not set, skipping Telegram alert")
        return False
    try:
        import subprocess
        # Use the openclaw CLI to send a message
        result = subprocess.run(
            ["openclaw", "message", "send",
             "--channel", "telegram",
             "--target", chat_id,
             "--message", f"⚠️ Gateway Monitor: {message}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 and result.stderr:
            logger.warning(f"openclaw send failed: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Failed to send Telegram alert: {e}")
        return False


def check_thresholds(metrics: GatewayMetrics, alert_state: AlertState) -> list[str]:
    """Check metrics against thresholds, return alert messages."""
    alerts = []

    # Pool exhaustion
    if metrics.pool_timeouts_10min > POOL_TIMEOUT_THRESHOLD:
        key = f"{metrics.name}_pool_exhaustion"
        if alert_state.should_alert(key):
            alerts.append(
                f"CRITICAL [{metrics.name}] Connection pool exhausted: "
                f"{metrics.pool_timeouts_10min} timeouts in 10min"
            )

    # Memory critical
    if metrics.memory_rss_mb > MEMORY_CRITICAL_MB:
        key = f"{metrics.name}_memory_critical"
        if alert_state.should_alert(key):
            alerts.append(
                f"CRITICAL [{metrics.name}] Memory usage critical: "
                f"{metrics.memory_rss_mb:.0f}MB RSS"
            )
    elif metrics.memory_rss_mb > MEMORY_WARN_MB:
        key = f"{metrics.name}_memory_warn"
        if alert_state.should_alert(key):
            alerts.append(
                f"WARN [{metrics.name}] Memory usage high: "
                f"{metrics.memory_rss_mb:.0f}MB RSS"
            )

    # Zero agents
    if (metrics.running and metrics.active_agents == 0
            and metrics.name == "hermes"):
        key = f"{metrics.name}_zero_agents"
        if alert_state.should_alert(key):
            alerts.append(
                f"WARN [{metrics.name}] Zero active agents for >{ZERO_AGENTS_WARN_MINUTES}min"
            )

    # Platform disconnection
    for platform, state in metrics.platforms.items():
        if state != "connected":
            key = f"{metrics.name}_platform_{platform}"
            if alert_state.should_alert(key):
                alerts.append(
                    f"CRITICAL [{metrics.name}] Platform '{platform}' "
                    f"disconnected (state={state})"
                )

    # Uptime warning
    if metrics.uptime_seconds > UPTIME_WARN_HOURS * 3600:
        key = f"{metrics.name}_uptime"
        if alert_state.should_alert(key):
            hours = metrics.uptime_seconds / 3600
            alerts.append(
                f"WARN [{metrics.name}] Gateway running for {hours:.0f}h "
                f"without restart — consider recycling"
            )

    return alerts


def maybe_auto_recover(metrics: GatewayMetrics) -> bool:
    """Trigger auto-recovery if thresholds are critically exceeded."""
    if metrics.pool_timeouts_10min > POOL_TIMEOUT_THRESHOLD * 2:
        logger.critical(
            f"[{metrics.name}] Pool exhaustion critical — triggering restart"
        )
        return restart_gateway(metrics.name)

    if metrics.memory_rss_mb > MEMORY_CRITICAL_MB:
        logger.critical(
            f"[{metrics.name}] Memory critical ({metrics.memory_rss_mb:.0f}MB) "
            f"— triggering restart"
        )
        return restart_gateway(metrics.name)

    return False


def restart_gateway(name: str) -> bool:
    """Gracefully restart a gateway via SIGTERM (launchd handles restart)."""
    state_file = HERMES_STATE_FILE if name == "hermes" else None
    if state_file:
        state = read_json_safe(state_file)
        pid = state.get("pid")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to {name} gateway (PID {pid})")
                return True
            except ProcessLookupError:
                logger.warning(f"{name} gateway PID {pid} not found")
    return False

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_check_once(alert_state: AlertState) -> bool:
    """Run a single monitoring cycle. Returns True if any auto-recovery was triggered."""
    recovered = False

    for collector in [collect_hermes_metrics, collect_openclaw_metrics]:
        try:
            metrics = collector()
            alerts = check_thresholds(metrics, alert_state)

            for alert in alerts:
                logger.warning(alert)
                send_telegram_alert(alert)

            if maybe_auto_recover(metrics):
                recovered = True

            # Log status
            logger.info(
                f"[{metrics.name}] pid={metrics.pid} "
                f"running={metrics.running} "
                f"agents={metrics.active_agents} "
                f"mem={metrics.memory_rss_mb:.0f}MB "
                f"pool_timeouts={metrics.pool_timeouts_10min} "
                f"errors={metrics.error_count}"
            )
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")

    return recovered


def daemon_loop():
    """Main monitoring loop."""
    logger.info("Gateway Monitor started")
    alert_state = AlertState()

    while True:
        try:
            run_check_once(alert_state)
        except Exception as e:
            logger.error(f"Monitor cycle failed: {e}")
        time.sleep(CHECK_INTERVAL)


def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(HERMES_LOG_DIR / "gateway_monitor.log"),
        ],
    )

    if "--once" in sys.argv:
        alert_state = AlertState()
        run_check_once(alert_state)
    elif "--foreground" in sys.argv:
        daemon_loop()
    else:
        # Daemon mode — fork to background
        if os.fork() > 0:
            sys.exit(0)
        os.setsid()
        if os.fork() > 0:
            sys.exit(0)
        daemon_loop()


if __name__ == "__main__":
    main()
