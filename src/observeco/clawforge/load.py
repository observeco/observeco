"""Intent-aware context loader for OpenClaw agents.

Classifies incoming message by intent and reports which sources
would be loaded/skipped.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from observeco.db import Database

console = Console()
db = Database()

# Intent classes with associated keyword patterns
INTENT_CLASSES = {
    "debug": ["error", "bug", "fail", "crash", "broken", "not working", "traceback",
              "exception", "issue", "problem", "fix", "repair"],
    "feature-request": ["feature", "add", "new", "implement", "build", "create",
                        "enhance", "improve", "support", "integrate"],
    "status": ["status", "health", "check", "alive", "running", "up", "down",
               "working", "state", "report"],
    "config-change": ["config", "change", "update", "modify", "set", "edit",
                      "configure", "setting", "parameter", "option", "toggle"],
    "general-query": ["what", "how", "why", "when", "where", "who", "tell me",
                      "explain", "describe", "show"],
}

DEFAULT_SOURCES = {
    "debug": ["errors.log", "recent_failures", "circuit_state", "agent_status"],
    "feature-request": ["SOUL.md", "existing_features", "open_issues"],
    "status": ["agent_status", "pulse_log", "circuit_state"],
    "config-change": ["config.yaml", "observability_config", "current_settings"],
    "general-query": ["SOUL.md", "MEMORY.md", "skill_descriptions", "recent_activity"],
}

ALL_SOURCES = ["SOUL.md", "MEMORY.md", "skills/*", "errors.log", "agent_status",
               "pulse_log", "circuit_state", "config.yaml", "recent_activity",
               "open_issues", "existing_features", "current_settings",
               "recent_failures", "observability_config", "skill_descriptions"]


def _classify_intent(message: str) -> tuple[str, float]:
    """Classify a message into an intent class with confidence."""
    lower = message.lower()
    scores = {}
    for intent, keywords in INTENT_CLASSES.items():
        score = sum(1 for kw in keywords if kw in lower)
        scores[intent] = score

    # If no keywords matched, default to general-query
    if max(scores.values()) == 0:
        return "general-query", 0.3

    best = max(scores, key=scores.get)
    total_matches = scores[best]
    # Higher matches = higher confidence
    confidence = min(0.95, total_matches * 0.2 + 0.3)
    return best, confidence


def run_load(probe: bool = False, message: Optional[str] = None) -> None:
    """Test intent-aware classification and report source selection."""
    if not message:
        if probe:
            console.print("[yellow]No --message provided. Using sample messages:[/yellow]")
            sample_msgs = [
                "The agent crashed with a segmentation fault",
                "Can you add support for PostgreSQL?",
                "Is the fleet healthy right now?",
                "Change the polling interval to 30 seconds",
                "What does this agent do?",
            ]
        else:
            console.print("[yellow]Usage: observeco clawforge load --message \"your message\"[/yellow]")
            console.print("  Use [bold]--probe[/bold] to test with sample messages")
            return
    else:
        sample_msgs = [message]

    for msg in sample_msgs:
        intent, confidence = _classify_intent(msg)
        sources_to_load = DEFAULT_SOURCES.get(intent, ["SOUL.md", "MEMORY.md"])
        sources_to_skip = [s for s in ALL_SOURCES if s not in sources_to_load]

        # Estimate token savings
        # Rough: 500 chars per source → 125 tokens per skipped source
        tokens_saved = len(sources_to_skip) * 125

        db.log_load("test", intent, len(sources_to_load), len(sources_to_skip), tokens_saved)

        table = Table(title=f"Intent Classification Result", box=box.ROUNDED, header_style="bold cyan")
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Message", msg[:80] + ("..." if len(msg) > 80 else ""))
        table.add_row("Classified As", f"[bold]{intent}[/bold]")
        table.add_row("Confidence", f"{confidence:.0%}")
        table.add_row("Sources Loaded", str(len(sources_to_load)))
        table.add_row("Sources Skipped", str(len(sources_to_skip)))
        table.add_row("Tokens Saved (est.)", str(tokens_saved))

        console.print(table)
        if probe:
            console.print()  # spacing
