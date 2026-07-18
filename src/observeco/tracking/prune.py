"""Pruning cron engine — tier-aware data retention.

Free tier: prunes to 7d every data type.
Pro tier: exits immediately (never prune).
Configurable via retention_config table.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

DATA_TYPES = ["pulse", "error", "drift", "token", "l2", "canary", "grid", "drift_event"]


def run_prune(db: Optional[Database] = None) -> dict:
    """Run pruning for all data types according to retention config.
    Returns dict of data_type -> rows_deleted.
    """
    if db is None:
        db = Database()

    config = db.get_retention_config()
    if not config.get("pruning_enabled", "1") != "0":
        return {"status": "disabled"}

    # Check license tier — Pro never prunes
    try:
        from observeco.license import load as load_license
        lic = load_license()
        if lic.license_type == "pro":
            return {"status": "pro_never_prune"}
    except Exception:
        pass

    results = {}
    for dt in DATA_TYPES:
        days_key = f"{dt}_days"
        days_str = config.get(days_key, "7")
        try:
            days = int(days_str)
        except (ValueError, TypeError):
            days = 7
        if days <= 0:
            continue  # Unlimited retention (Pro)
        deleted = db.prune_old_data(dt, days)
        if deleted > 0:
            logger.info(f"Pruned {deleted} rows from {dt} (retention: {days}d)")
        results[dt] = deleted

    results["status"] = "ok"
    return results


def run_scheduled_prune(db: Optional[Database] = None) -> dict:
    """Run pruning only if within scheduled hour.
    Called by cron every hour; only actually prunes at configured hour.
    """
    if db is None:
        db = Database()
    config = db.get_retention_config()
    pruning_hour = int(config.get("pruning_hour", "3"))
    current_hour = time.localtime().tm_hour
    if current_hour == pruning_hour:
        return run_prune(db)
    return {"status": "not_scheduled_hour", "current_hour": current_hour, "scheduled_hour": pruning_hour}
