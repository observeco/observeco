"""Cross-agent failure correlation — detect when one agent's failure causes another's.

Analyzes temporal patterns in failures across agents to identify:
- Cascade failures: Agent A fails → Agent B fails shortly after
- Shared root causes: Multiple agents fail on the same tool/time
- Correlation chains: A → B → C failure sequences
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Correlation:
    """A correlation between two agent failures."""
    source_agent: str
    target_agent: str
    correlation_type: str  # "cascade", "shared_root_cause", "temporal"
    confidence: float  # 0.0 - 1.0
    time_gap_seconds: float  # Time between failures
    evidence: list = field(default_factory=list)  # Supporting data points
    recommendation: str = ""


class FailureCorrelator:
    """Detect cross-agent failure correlations."""

    def __init__(self, correlation_window_seconds: int = 300):
        """Args:
            correlation_window_seconds: Max time between failures to consider correlated.
        """
        self.window = correlation_window_seconds

    def analyze(self, session_dir: str = None) -> list[Correlation]:
        """Analyze all session logs for cross-agent failure correlations."""
        failures = self._load_all_failures(session_dir)
        if len(failures) < 2:
            return []

        correlations = []

        # 1. Cascade detection: Agent A fails, then Agent B fails within window
        correlations.extend(self._detect_cascades(failures))

        # 2. Shared root cause: Multiple agents fail on same tool at similar times
        correlations.extend(self._detect_shared_causes(failures))

        # 3. Temporal clustering: Failures cluster in time across agents
        correlations.extend(self._detect_temporal_clusters(failures))

        # Deduplicate and rank
        return self._deduplicate_and_rank(correlations)

    def _load_all_failures(self, session_dir: str = None) -> list[dict]:
        """Load all failure events from session logs."""
        from pathlib import Path

        from .dirs import get_data_dir

        if session_dir:
            sessions_path = Path(session_dir)
        else:
            sessions_path = get_data_dir() / "sessions"

        if not sessions_path.exists():
            return []

        failures = []
        for session_file in sorted(sessions_path.glob("*.jsonl")):
            try:
                with open(session_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        data = entry.get("data", {})
                        if data.get("decision") in ("deny", "flag"):
                            failures.append({
                                "agent_id": entry.get("agent_id", "unknown"),
                                "tool_name": data.get("tool_name", "unknown"),
                                "risk_level": data.get("risk_level", "unknown"),
                                "decision": data.get("decision", "unknown"),
                                "timestamp": entry.get("timestamp", ""),
                                "session_id": entry.get("session_id", ""),
                            })
            except Exception:
                continue

        # Sort by timestamp
        failures.sort(key=lambda x: x.get("timestamp", ""))
        return failures

    def _detect_cascades(self, failures: list[dict]) -> list[Correlation]:
        """Detect cascade failures: Agent A fails → Agent B fails within window."""
        correlations = []
        agents = defaultdict(list)

        for f in failures:
            agents[f["agent_id"]].append(f)

        # Compare each pair of agents
        agent_list = list(agents.keys())
        for i, agent_a in enumerate(agent_list):
            for agent_b in agent_list[i+1:]:
                for fail_a in agents[agent_a]:
                    for fail_b in agents[agent_b]:
                        gap = self._time_gap(fail_a["timestamp"], fail_b["timestamp"])
                        if 0 < gap <= self.window:
                            correlations.append(Correlation(
                                source_agent=agent_a,
                                target_agent=agent_b,
                                correlation_type="cascade",
                                confidence=min(0.9, 0.5 + (1 - gap / self.window) * 0.4),
                                time_gap_seconds=gap,
                                evidence=[fail_a["tool_name"], fail_b["tool_name"]],
                                recommendation=f"Check if {agent_a} failure caused {agent_b} failure ({gap:.0f}s gap)",
                            ))

        return correlations

    def _detect_shared_causes(self, failures: list[dict]) -> list[Correlation]:
        """Detect shared root causes: Multiple agents fail on same tool."""
        correlations = []
        tool_failures = defaultdict(list)

        for f in failures:
            tool_failures[f["tool_name"]].append(f)

        for tool, fails in tool_failures.items():
            if len(fails) < 2:
                continue

            # Group by agent
            by_agent = defaultdict(list)
            for f in fails:
                by_agent[f["agent_id"]].append(f)

            if len(by_agent) < 2:
                continue

            agents = list(by_agent.keys())
            for i, agent_a in enumerate(agents):
                for agent_b in agents[i+1:]:
                    # Check if failures are temporally close
                    for fail_a in by_agent[agent_a]:
                        for fail_b in by_agent[agent_b]:
                            gap = self._time_gap(fail_a["timestamp"], fail_b["timestamp"])
                            if gap <= self.window * 2:  # Wider window for shared causes
                                correlations.append(Correlation(
                                    source_agent=agent_a,
                                    target_agent=agent_b,
                                    correlation_type="shared_root_cause",
                                    confidence=min(0.85, 0.4 + len(fails) * 0.05),
                                    time_gap_seconds=gap,
                                    evidence=[tool, f"{len(fails)} failures"],
                                    recommendation=f"Tool '{tool}' failing for both agents — check shared dependency",
                                ))

        return correlations

    def _detect_temporal_clusters(self, failures: list[dict]) -> list[Correlation]:
        """Detect temporal clusters: failures cluster in time across agents."""
        correlations = []
        if len(failures) < 3:
            return []

        # Find time windows with multiple failures from different agents
        for i, fail_a in enumerate(failures):
            cluster = [fail_a]
            for fail_b in failures[i+1:]:
                gap = self._time_gap(fail_a["timestamp"], fail_b["timestamp"])
                if gap <= 60:  # 1-minute window
                    if fail_b["agent_id"] != fail_a["agent_id"]:
                        cluster.append(fail_b)

            if len(cluster) >= 3:
                agents = set(f["agent_id"] for f in cluster)
                if len(agents) >= 2:
                    correlations.append(Correlation(
                        source_agent=list(agents)[0],
                        target_agent=list(agents)[1],
                        correlation_type="temporal",
                        confidence=min(0.8, 0.3 + len(cluster) * 0.1),
                        time_gap_seconds=self._time_gap(
                            cluster[0]["timestamp"], cluster[-1]["timestamp"]
                        ),
                        evidence=[f"{len(cluster)} failures from {len(agents)} agents"],
                        recommendation=f"Temporal cluster: {len(cluster)} failures in <1 min from {len(agents)} agents — possible system-wide issue",
                    ))

        return correlations

    def _time_gap(self, ts1: str, ts2: str) -> float:
        """Calculate time gap between two ISO timestamps in seconds."""
        try:
            dt1 = datetime.fromisoformat(ts1.replace("Z", "+00:00"))
            dt2 = datetime.fromisoformat(ts2.replace("Z", "+00:00"))
            return abs((dt2 - dt1).total_seconds())
        except Exception:
            return float("inf")

    def _deduplicate_and_rank(self, correlations: list[Correlation]) -> list[Correlation]:
        """Deduplicate and rank correlations by confidence."""
        # Simple dedup: keep highest confidence for each (source, target, type) tuple
        seen = {}
        for c in correlations:
            key = (c.source_agent, c.target_agent, c.correlation_type)
            if key not in seen or c.confidence > seen[key].confidence:
                seen[key] = c

        return sorted(seen.values(), key=lambda c: c.confidence, reverse=True)
