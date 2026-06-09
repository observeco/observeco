"""PA Brief Delta — diff between evening and morning state.

Produces a structured delta report:
"Since evening brief (22:00): 2 new WhatsApp messages, 1 new email, 1 calendar change, 0 agent status changes"

Usage:
    python3 -m observeco.pa_brief_diff          # print delta
    observeco pa brief --morning                 # CLI alias (planned)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HOME = Path.home()
BRIEF_SNAPSHOT_DIR = HOME / ".hermes" / "cron" / "output"
EVENING_SNAPSHOT_FILE = BRIEF_SNAPSHOT_DIR / "pa_evening_brief_snapshot.json"


def _find_latest_evening_snapshot() -> Optional[Path]:
    """Find the most recent evening brief snapshot."""
    if EVENING_SNAPSHOT_FILE.exists():
        return EVENING_SNAPSHOT_FILE
    # Fallback: search for any evening brief files
    candidates = sorted(BRIEF_SNAPSHOT_DIR.glob("*evening*"), reverse=True)
    if candidates:
        return candidates[0]
    return None


def _load_snapshot(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_snapshot(data: dict) -> None:
    """Save current state as an evening snapshot."""
    BRIEF_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    EVENING_SNAPSHOT_FILE.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# State collectors
# ---------------------------------------------------------------------------

def _count_flags(prefix: str = "") -> int:
    """Count signal/flag files in intelligence directories."""
    paths_to_check = [
        HOME / ".hermes" / "intelligence" / "flags",
        HOME / ".hermes" / "intelligence" / "decisions",
    ]
    total = 0
    for p in paths_to_check:
        if p.exists():
            for f in p.iterdir():
                if f.is_file() and (not prefix or f.name.startswith(prefix)):
                    total += 1
    return total


def _check_pulse_status() -> dict:
    """Get basic pulse status from pulse DB."""
    db_path = HOME / ".observeco" / "pulse.db"
    if not db_path.exists():
        return {"agents": 0, "alive": 0, "dead": 0, "unknown": 0}

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT agent_name, status FROM pulses ORDER BY agent_name").fetchall()
        conn.close()
        agents = {}
        for r in rows:
            agents[r["agent_name"]] = r["status"]
        return {
            "agents": len(agents),
            "alive": sum(1 for s in agents.values() if s == "alive"),
            "dead": sum(1 for s in agents.values() if s == "dead"),
            "unknown": sum(1 for s in agents.values() if s not in ("alive", "dead")),
            "agent_list": agents,
        }
    except Exception:
        return {"agents": 0}


def _list_calendar_events() -> int:
    """Count upcoming calendar events (best-effort)."""
    cal_paths = [
        HOME / "seanfzc.ics",
        HOME / "Library" / "Calendars",
        Path("/tmp") / "seanfzc_calendar.json",
    ]
    for p in cal_paths:
        if p.exists():
            if p.suffix == ".ics":
                count = sum(1 for line in p.read_text().split("\n") if line.startswith("DTSTART:"))
                return count
            if p.suffix == ".json":
                try:
                    data = json.loads(p.read_text())
                    return len(data)
                except Exception:
                    pass
    return 0


def collect_state() -> dict:
    """Gather current state for snapshot/diff comparison."""
    pulse = _check_pulse_status()
    return {
        "collected_at": int(time.time()),
        "signal_count": _count_flags(),
        "pulse": pulse,
        "calendar_events_estimate": _list_calendar_events(),
    }


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------


class DiffResult:
    def __init__(self):
        self.new_signals = 0
        self.pulse_changes: list[str] = []
        self.calendar_changes = 0

    def __bool__(self) -> bool:
        return bool(self.new_signals or self.pulse_changes or self.calendar_changes)


def compute_delta(previous: dict, current: dict) -> DiffResult:
    result = DiffResult()

    # Signal count diff
    prev_signals = previous.get("signal_count", 0)
    cur_signals = current.get("signal_count", 0)
    result.new_signals = max(0, cur_signals - prev_signals)

    # Pulse changes
    prev_pulse = previous.get("pulse", {})
    cur_pulse = current.get("pulse", {})
    prev_agents = prev_pulse.get("agent_list", {})
    cur_agents = cur_pulse.get("agent_list", {})

    for agent, status in cur_agents.items():
        prev_status = prev_agents.get(agent)
        if prev_status is not None and prev_status != status:
            result.pulse_changes.append(f"{agent}: {prev_status} → {status}")

    # New agents
    new_agents = [a for a in cur_agents if a not in prev_agents]
    if new_agents:
        result.pulse_changes.append(f"NEW agents: {', '.join(new_agents)}")

    # Calendar events diff
    prev_cal = previous.get("calendar_events_estimate", 0)
    cur_cal = current.get("calendar_events_estimate", 0)
    result.calendar_changes = cur_cal - prev_cal

    return result


def format_delta(result: DiffResult) -> str:
    lines = []

    if result.new_signals > 0:
        lines.append(f"📬 {result.new_signals} new signal(s)")
    else:
        lines.append("📬 No new signals")

    if result.pulse_changes:
        for c in result.pulse_changes[:5]:
            lines.append(f"  {c}")
        if len(result.pulse_changes) > 5:
            lines.append(f"  ... and {len(result.pulse_changes) - 5} more")
    else:
        lines.append("📊 No agent status changes")

    if result.calendar_changes > 0:
        lines.append(f"📅 +{result.calendar_changes} new calendar events")
    elif result.calendar_changes < 0:
        lines.append(f"📅 {abs(result.calendar_changes)} events removed")
    else:
        lines.append("📅 No calendar changes")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------


def evening_snapshot() -> str:
    """Take a snapshot of current state (run at 22:00 after brief)."""
    state = collect_state()
    _save_snapshot(state)
    return f"Evening snapshot saved: {len(str(state))} bytes"


def morning_delta() -> str:
    """Compare current state to last evening snapshot."""
    snapshot_path = _find_latest_evening_snapshot()
    if not snapshot_path:
        return (
            "⚠️ No evening brief snapshot found.\n\n"
            "Run the evening brief first to establish a baseline:\n"
            "  observeco pa brief --evening\n\n"
            "Once a baseline exists, --morning will diff against it."
        )

    previous = _load_snapshot(snapshot_path)
    current = collect_state()
    delta = compute_delta(previous, current)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    header = f"# Since evening brief — {timestamp}\n"

    if not delta:
        return header + "\nNo changes detected — system steady."

    return header + "\n" + format_delta(delta)


# ---------------------------------------------------------------------------
# CLI subcommand entry (called from cli.py)
# ---------------------------------------------------------------------------

def run_brief(mode: str = "morning") -> str:
    if mode == "evening":
        return evening_snapshot()
    return morning_delta()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    print(run_brief(mode))
