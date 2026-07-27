"""Timestamp formatting utilities — no dashboard imports, safe to import from anywhere."""
from datetime import datetime, timezone


def fmt_ts(ts: int, fmt: str = "%b %d %H:%M") -> str:
    """Absolute date: format a unix timestamp as a date string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt)


def fmt_ago(ts: int) -> str:
    """Relative time: '3m ago', '2h ago', '1d ago'."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta.total_seconds() < 60:
        return f"{int(delta.total_seconds())}s ago"
    elif delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() / 60)}m ago"
    elif delta.total_seconds() < 86400:
        return f"{int(delta.total_seconds() / 3600)}h ago"
    return f"{int(delta.total_seconds() / 86400)}d ago"


def fmt_now(fmt: str = "%H:%M:%S") -> str:
    """Format current UTC time."""
    return datetime.now(timezone.utc).strftime(fmt)
