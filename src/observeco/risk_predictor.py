"""ML-based risk prediction — analyze historical patterns to predict future risks.

Uses lightweight statistical analysis (no heavy ML dependencies):
- Frequency analysis: which tools fail most often
- Time-series patterns: when failures cluster
- Agent-specific risk profiles: per-agent failure patterns
- Tool-call sequences: which tool combinations lead to failures
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .session_log import SessionLogger
from .risk_engine import RiskLevel


@dataclass
class RiskPrediction:
    """A risk prediction for a tool call."""
    tool_name: str
    predicted_risk: str  # low, medium, high, critical
    confidence: float  # 0.0 - 1.0
    reason: str
    historical_failures: int
    historical_total: int
    agent_id: str = ""
    pattern: str = ""  # "frequent_failure", "time_cluster", "sequence_risk", "agent_specific"


@dataclass
class RiskProfile:
    """Risk profile for an agent or tool."""
    entity: str  # agent_id or tool_name
    entity_type: str  # "agent" or "tool"
    total_calls: int = 0
    failures: int = 0
    failure_rate: float = 0.0
    risk_distribution: dict = field(default_factory=dict)  # {risk_level: count}
    recent_trend: str = "stable"  # "improving", "stable", "degrading"
    last_failure: Optional[str] = None


class RiskPredictor:
    """Predict risk based on historical patterns."""

    def __init__(self):
        self._cache: dict = {}

    def predict(self, tool_name: str, tool_args: dict = None,
                agent_id: str = "") -> RiskPrediction:
        """Predict risk for a tool call based on history."""
        # Get historical data
        history = self._get_tool_history(tool_name)
        agent_history = self._get_agent_history(agent_id) if agent_id else []

        total = len(history)
        failures = sum(1 for h in history if h.get("decision") == "deny")

        # Base risk from static rules
        from .risk_engine import ToolCall, classify_tool_call
        tc = ToolCall(name=tool_name, arguments=tool_args or {})
        base_result = classify_tool_call(tc)

        # Adjust based on history
        if total == 0:
            # No history — use base classification
            return RiskPrediction(
                tool_name=tool_name,
                predicted_risk=base_result.level.value,
                confidence=0.5,
                reason="No historical data — using static rules",
                historical_failures=0,
                historical_total=0,
                agent_id=agent_id,
                pattern="no_history",
            )

        failure_rate = failures / total if total > 0 else 0

        # Pattern: frequent failure
        if failure_rate > 0.3 and total >= 5:
            risk = "high" if failure_rate > 0.5 else "medium"
            return RiskPrediction(
                tool_name=tool_name,
                predicted_risk=risk,
                confidence=min(0.9, 0.5 + failure_rate * 0.5),
                reason=f"High failure rate: {failure_rate:.0%} ({failures}/{total} historical calls)",
                historical_failures=failures,
                historical_total=total,
                agent_id=agent_id,
                pattern="frequent_failure",
            )

        # Pattern: agent-specific risk
        if agent_id and agent_history:
            agent_failures = sum(1 for h in agent_history if h.get("decision") == "deny")
            agent_total = len(agent_history)
            agent_failure_rate = agent_failures / agent_total if agent_total > 0 else 0
            if agent_failure_rate > 0.2 and agent_total >= 3:
                return RiskPrediction(
                    tool_name=tool_name,
                    predicted_risk="medium",
                    confidence=0.6,
                    reason=f"Agent '{agent_id}' has {agent_failure_rate:.0%} failure rate",
                    historical_failures=failures,
                    historical_total=total,
                    agent_id=agent_id,
                    pattern="agent_specific",
                )

        # Pattern: time clustering (failures in last hour)
        recent = [h for h in history if self._is_recent(h, hours=1)]
        recent_failures = sum(1 for h in recent if h.get("decision") == "deny")
        if recent_failures >= 3:
            return RiskPrediction(
                tool_name=tool_name,
                predicted_risk="high",
                confidence=0.8,
                reason=f"{recent_failures} failures in the last hour",
                historical_failures=failures,
                historical_total=total,
                agent_id=agent_id,
                pattern="time_cluster",
            )

        # No elevated risk — use base classification with confidence boost
        confidence = min(0.9, 0.5 + (total / 100) * 0.4)  # More data = more confidence
        return RiskPrediction(
            tool_name=tool_name,
            predicted_risk=base_result.level.value,
            confidence=confidence,
            reason=f"Base classification (history: {total} calls, {failures} failures)",
            historical_failures=failures,
            historical_total=total,
            agent_id=agent_id,
            pattern="baseline",
        )

    def get_tool_profile(self, tool_name: str) -> RiskProfile:
        """Get risk profile for a tool."""
        history = self._get_tool_history(tool_name)
        return self._build_profile(tool_name, "tool", history)

    def get_agent_profile(self, agent_id: str) -> RiskProfile:
        """Get risk profile for an agent."""
        history = self._get_agent_history(agent_id)
        return self._build_profile(agent_id, "agent", history)

    def get_fleet_profiles(self) -> list[RiskProfile]:
        """Get risk profiles for all agents."""
        from .db import Database
        db = Database()
        agents = db.get_agents()
        profiles = []
        for agent in agents:
            name = agent.get("agent_name", agent.get("name", ""))
            if name:
                profiles.append(self.get_agent_profile(name))
        return sorted(profiles, key=lambda p: p.failure_rate, reverse=True)

    def _build_profile(self, entity: str, entity_type: str, history: list) -> RiskProfile:
        """Build a risk profile from history."""
        total = len(history)
        failures = sum(1 for h in history if h.get("decision") == "deny")

        risk_dist = Counter(h.get("risk_level", "unknown") for h in history)

        # Trend: compare recent vs older
        recent = [h for h in history if self._is_recent(h, hours=24)]
        older = [h for h in history if not self._is_recent(h, hours=24)]
        recent_rate = sum(1 for h in recent if h.get("decision") == "deny") / len(recent) if recent else 0
        older_rate = sum(1 for h in older if h.get("decision") == "deny") / len(older) if older else 0

        if recent_rate > older_rate * 1.5:
            trend = "degrading"
        elif recent_rate < older_rate * 0.5:
            trend = "improving"
        else:
            trend = "stable"

        last_failure = None
        for h in reversed(history):
            if h.get("decision") == "deny":
                last_failure = h.get("timestamp", "")
                break

        return RiskProfile(
            entity=entity,
            entity_type=entity_type,
            total_calls=total,
            failures=failures,
            failure_rate=failures / total if total > 0 else 0,
            risk_distribution=dict(risk_dist),
            recent_trend=trend,
            last_failure=last_failure,
        )

    def _get_tool_history(self, tool_name: str) -> list:
        """Get historical calls for a tool across ALL session files."""
        try:
            from .dirs import get_data_dir
            results = []

            # Primary: Hermes session directory (ObserveCo data dir is secondary)
            session_paths = [
                get_data_dir() / "sessions",
                Path.home() / ".hermes" / "sessions",
            ]

            for sessions_dir in session_paths:
                if not sessions_dir.exists():
                    continue

                for session_file in sorted(sessions_dir.glob("*.jsonl"), reverse=True)[:20]:
                    try:
                        with open(session_file) as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                entry = json.loads(line)
                                # Support both ObserveCo JSONL format and Hermes session format
                                if (
                                    entry.get("event_type") == "tool_call"
                                    and entry.get("data", {}).get("tool_name") == tool_name
                                ):
                                    results.append(entry.get("data", {}))
                                elif (
                                    entry.get("role") == "tool"
                                    and entry.get("name") == tool_name
                                ):
                                    results.append({
                                        "tool_name": tool_name,
                                        "decision": "deny" if entry.get("is_error") else "allow",
                                        "risk_level": "high" if entry.get("is_error") else "low",
                                        "arguments": entry.get("arguments", ""),
                                        "timestamp": entry.get("timestamp", ""),
                                    })
                    except Exception:
                        continue
                if len(results) >= 500:
                    break

            return results[:500]  # Cap at 500 entries
        except Exception:
            return []

    def _get_agent_history(self, agent_id: str) -> list:
        """Get historical calls for an agent across ALL session files."""
        try:
            from .dirs import get_data_dir
            results = []

            # Primary: Hermes session directory
            session_paths = [
                get_data_dir() / "sessions",
                Path.home() / ".hermes" / "sessions",
            ]

            for sessions_dir in session_paths:
                if not sessions_dir.exists():
                    continue

                for session_file in sorted(sessions_dir.glob("*.jsonl"), reverse=True)[:20]:
                    try:
                        with open(session_file) as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                entry = json.loads(line)
                                # Support both formats
                                if entry.get("agent_id") == agent_id:
                                    results.append(entry.get("data", {}))
                                elif entry.get("role") == "user" and agent_id in str(entry.get("content", "")):
                                    # Fuzzy match: look for agent name in message content
                                    results.append({
                                        "decision": "allow",
                                        "risk_level": "low",
                                        "timestamp": entry.get("timestamp", ""),
                                    })
                    except Exception:
                        continue
                if len(results) >= 500:
                    break

            return results[:500]  # Cap at 500 entries
        except Exception:
            return []

    def _is_recent(self, entry: dict, hours: int = 1) -> bool:
        """Check if an entry is within the last N hours."""
        ts = entry.get("timestamp", "")
        if not ts:
            return False
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = (now - dt).total_seconds()
            return diff < hours * 3600
        except Exception:
            return False
