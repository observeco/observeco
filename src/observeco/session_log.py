"""Tamper-evident session logging with hash chain."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .platform import get_data_dir


def _hash_entry(entry: dict, prev_hash: str) -> str:
    """Compute SHA-256 hash of entry + previous hash (chain)."""
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    chain_input = f"{prev_hash}{canonical}"
    return hashlib.sha256(chain_input.encode()).hexdigest()


class SessionLogger:
    """Append-only session log with hash chain for tamper detection."""

    def __init__(self, session_id: str = None):
        self.data_dir = get_data_dir() / "sessions"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if session_id:
            self.session_id = session_id
        else:
            self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        self.log_file = self.data_dir / f"{self.session_id}.jsonl"
        self.prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Load the hash of the last entry for chaining."""
        if not self.log_file.exists():
            return "0" * 64  # Genesis hash
        try:
            with open(self.log_file) as f:
                last_line = ""
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
                if last_line:
                    entry = json.loads(last_line)
                    return entry.get("_hash", "0" * 64)
        except (json.JSONDecodeError, OSError):
            pass
        return "0" * 64

    def log(self, event_type: str, data: dict, agent_id: str = "", risk_level: str = "") -> dict:
        """Log a session event with tamper-evident hash chain."""
        entry = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "agent_id": agent_id,
            "risk_level": risk_level,
            "data": data,
        }

        # Compute hash chain
        entry_hash = _hash_entry(entry, self.prev_hash)
        entry["_hash"] = entry_hash
        entry["_prev_hash"] = self.prev_hash
        self.prev_hash = entry_hash

        # Append to log
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return entry

    def log_tool_call(self, tool_name: str, arguments: dict, risk_level: str,
                      decision: str, agent_id: str = "") -> dict:
        """Log a tool call event."""
        return self.log(
            event_type="tool_call",
            data={
                "tool_name": tool_name,
                "arguments": arguments,
                "decision": decision,
            },
            agent_id=agent_id,
            risk_level=risk_level,
        )

    def log_action(self, action: str, risk_level: str, decision: str,
                   agent_id: str = "") -> dict:
        """Log a text-based action (legacy compatibility)."""
        return self.log(
            event_type="action",
            data={
                "action": action,
                "decision": decision,
            },
            agent_id=agent_id,
            risk_level=risk_level,
        )

    def verify_chain(self) -> tuple[bool, Optional[str]]:
        """Verify the integrity of the log chain.

        Returns:
            (is_valid, error_message)
        """
        if not self.log_file.exists():
            return True, None

        expected_prev = "0" * 64
        with open(self.log_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    return False, f"Line {line_num}: invalid JSON"

                stored_hash = entry.get("_hash")
                stored_prev = entry.get("_prev_hash")

                if not stored_hash or not stored_prev:
                    return False, f"Line {line_num}: missing hash fields"

                if stored_prev != expected_prev:
                    return False, f"Line {line_num}: chain broken (prev hash mismatch)"

                # Recompute hash
                check_entry = {k: v for k, v in entry.items() if k not in ("_hash", "_prev_hash")}
                computed = _hash_entry(check_entry, expected_prev)

                if computed != stored_hash:
                    return False, f"Line {line_num}: entry modified (hash mismatch)"

                expected_prev = stored_hash

        return True, None

    def get_entries(self, limit: int = 50) -> list:
        """Get recent log entries."""
        if not self.log_file.exists():
            return []

        entries = []
        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return entries[-limit:]

    def get_summary(self) -> dict:
        """Get session summary."""
        entries = self.get_entries(limit=10000)
        tool_calls = [e for e in entries if e.get("event_type") == "tool_call"]
        actions = [e for e in entries if e.get("event_type") == "action"]

        decisions = {}
        for e in entries:
            d = e.get("data", {}).get("decision", "unknown")
            decisions[d] = decisions.get(d, 0) + 1

        return {
            "session_id": self.session_id,
            "total_events": len(entries),
            "tool_calls": len(tool_calls),
            "actions": len(actions),
            "decisions": decisions,
            "chain_valid": self.verify_chain()[0],
        }
