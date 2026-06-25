"""Pipeline health check — data quality tier detection.

Tiers:
  estimated (0): watch daemon estimates only (config size heuristics, ±80%)
  accurate  (1): OTEL plugin providing real per-call token data (±5%)
  full      (2): SDK patchers or proxy providing exact data (±1%)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from observeco.dirs import hermes_home


def _ts_to_iso(ts: Optional[int]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _check_otel_listener_running() -> bool:
    """Check if OTEL listener is responding on port 4318."""
    try:
        import httpx
        r = httpx.get("http://127.0.0.1:4318/health", timeout=1.5)
        return r.status_code < 500
    except Exception:
        return False


def _check_hermes_otel_plugin_enabled() -> bool:
    """Check if observability/otel plugin is listed in Hermes config.yaml."""
    try:
        import yaml  # type: ignore[import]
    except ImportError:
        return False
    try:
        config_path = hermes_home() / "config.yaml"
        if not config_path.exists():
            return False
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            return False
        plugins = cfg.get("plugins", {})
        if isinstance(plugins, dict):
            enabled = plugins.get("enabled", [])
        elif isinstance(plugins, list):
            enabled = plugins
        else:
            return False
        return any("otel" in str(p).lower() for p in (enabled or []))
    except Exception:
        return False


def get_source_stats(hours: int = 24) -> dict[str, dict]:
    """Query token_logs for per-source activity in the last N hours.

    Returns dict keyed by source ('watch', 'otel', 'sdk', 'proxy', 'unknown')
    with {rows_24h, last_data_ts}.
    """
    from observeco.db import Database

    db = Database()
    conn = db._get_conn()
    cutoff = int(time.time()) - hours * 3600

    try:
        rows = conn.execute(
            "SELECT source, COUNT(*) as cnt, MAX(recorded_at) as last_ts "
            "FROM token_logs WHERE recorded_at >= ? GROUP BY source",
            (cutoff,),
        ).fetchall()
    except Exception:
        return {}

    stats: dict[str, dict] = {}
    for row in rows:
        source = row[0] or "unknown"
        stats[source] = {
            "rows_24h": row[1],
            "last_data_ts": row[2],
        }

    # Fill zeros for known sources not present
    for src in ("watch", "otel", "sdk", "proxy"):
        if src not in stats:
            # Get absolute last ts for this source (ever)
            try:
                last = conn.execute(
                    "SELECT MAX(recorded_at) FROM token_logs WHERE source = ?",
                    (src,),
                ).fetchone()[0]
            except Exception:
                last = None
            stats[src] = {"rows_24h": 0, "last_data_ts": last}

    return stats


def check_pipeline_health() -> dict:
    """Determine data quality tier and pipeline source status.

    Returns a dict suitable for /api/pipeline/health response.
    """
    source_stats = get_source_stats(hours=24)

    listener_running = _check_otel_listener_running()
    plugin_enabled = _check_hermes_otel_plugin_enabled()

    def _build_source(name: str, extra: Optional[dict] = None) -> dict:
        s = source_stats.get(name, {"rows_24h": 0, "last_data_ts": None})
        rows = s["rows_24h"]
        last_ts = s["last_data_ts"]
        active = rows > 0
        result: dict = {
            "active": active,
            "last_data": _ts_to_iso(last_ts) if last_ts else None,
            "rows_24h": rows,
        }
        if extra:
            result.update(extra)
        return result

    watch_src = _build_source("watch")
    otel_src = _build_source("otel", {
        "listener_running": listener_running,
        "plugin_enabled": plugin_enabled,
    })
    sdk_src = _build_source("sdk")
    proxy_src = _build_source("proxy")

    # Tier determination (highest wins)
    tier: str
    upgrade_path: str

    if sdk_src["active"] or proxy_src["active"]:
        tier = "full"
        upgrade_path = ""
    elif otel_src["active"] and listener_running:
        tier = "accurate"
        upgrade_path = ""
    else:
        tier = "estimated"
        if not plugin_enabled:
            upgrade_path = "Run `hermes plugins enable observability/otel` to get real token data"
        elif not listener_running:
            upgrade_path = "Run `observeco otel listen start` to start the OTEL listener"
        else:
            upgrade_path = "Run `observeco setup` to verify your OTEL pipeline"

    # Warn if OTEL was recently active but data stopped
    otel_stale = False
    if otel_src["last_data"] is not None and not otel_src["active"]:
        otel_stale = True

    return {
        "tier": tier,
        "otel_stale": otel_stale,
        "sources": {
            "watch": watch_src,
            "otel": otel_src,
            "sdk": sdk_src,
            "proxy": proxy_src,
        },
        "upgrade_path": upgrade_path,
    }
