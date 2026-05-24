"""Memory hygiene agent for OpenClaw MEMORY.md.

Scans for duplicate entries, contradictory facts, stale entries (>30d no reads),
computes a memory debt score (0-100), and optionally applies fixes.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table

from observeco.db import Database

console = Console()
db = Database()


def _find_memory_files(agent_name: Optional[str] = None) -> list[dict]:
    """Find MEMORY.md files for all or specific agents."""
    memories = []
    search_paths = [
        Path.home() / ".hermes" / "profiles",
        Path.home() / ".hermes" / "agents",
        Path.home() / "projects" / "openclaw",
    ]

    for base in search_paths:
        if not base.exists():
            continue
        if base.is_dir():
            for entry in base.iterdir():
                if entry.is_dir():
                    mem = entry / "MEMORY.md"
                    if mem.exists():
                        memories.append({
                            "agent": entry.name,
                            "path": str(mem),
                        })
                elif entry.name == "MEMORY.md":
                    memories.append({
                        "agent": base.stem,
                        "path": str(entry),
                    })

    if agent_name:
        memories = [m for m in memories if m["agent"] == agent_name]

    return memories


def _find_duplicates(lines: list[str]) -> list[tuple[int, str, str]]:
    """Find duplicate or near-duplicate lines. Returns (line_num, text, match_reason)."""
    seen: dict[str, list[int]] = {}
    duplicates = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        # Normalize: lowercase, remove extra whitespace
        normalized = re.sub(r'\s+', ' ', stripped.lower())
        if len(normalized) < 10:
            continue  # Skip very short lines
        if normalized in seen:
            for prev_line in seen[normalized]:
                duplicates.append((i, stripped[:100], f"Exact match with line {prev_line+1}"))
        else:
            seen[normalized] = []
        seen[normalized].append(i)

    return duplicates


def _find_contradictions(lines: list[str]) -> list[tuple[int, str, str]]:
    """Find contradictory statements. Returns (line_num, text, contradiction_reason)."""
    contradictions = []
    negation_patterns = re.compile(
        r"(not|never|no longer|doesn't|don't|won't|can't|cannot)\s+(use|support|work|handle|have)",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        stripped = line.strip()
        if negation_patterns.search(stripped):
            # Check if there's a contradictory positive statement elsewhere
            lower = stripped.lower()
            # Extract the subject
            match = re.search(r"(not|never|no longer)\s+(use|support|work|handle|have)\s+(\S+)", lower)
            if match:
                subject = match.group(3)
                # Look for positive version of the same subject
                for j, other_line in enumerate(lines):
                    if abs(j - i) < 3:
                        continue  # Skip nearby lines in same paragraph
                    if subject in other_line.lower() and not negation_patterns.search(other_line.lower()):
                        contradictions.append((
                            i, stripped[:100],
                            f"Contradicts line {j+1}: \"{other_line.strip()[:60]}\""
                        ))
                        break

    return contradictions


def _find_stale(lines: list[str], memory_path: str) -> list[tuple[int, str, str]]:
    """Find entries with dates older than 30 days."""
    stale = []
    date_pattern = re.compile(
        r"(\d{4})-(\d{2})-(\d{2})"
    )
    now = time.time()
    thirty_days = 30 * 86400

    for i, line in enumerate(lines):
        match = date_pattern.search(line)
        if match:
            try:
                entry_ts = time.mktime((
                    int(match.group(1)), int(match.group(2)), int(match.group(3)),
                    0, 0, 0, 0, 0, 0
                ))
                if (now - entry_ts) > thirty_days:
                    stale.append((i, line.strip()[:100], f"Dated {match.group(0)} (>30 days old)"))
            except (ValueError, OverflowError):
                pass

    return stale


def run_garden(apply: bool = False, agent_name: Optional[str] = None) -> None:
    """Scan MEMORY.md files and report/apply memory hygiene."""
    memories = _find_memory_files(agent_name)

    if not memories:
        console.print("[yellow]No MEMORY.md files found.[/yellow]")
        console.print("Searched: ~/.hermes/profiles/*/MEMORY.md, ~/.hermes/agents/, ~/projects/openclaw/")
        return

    for mem in memories:
        path = Path(mem["path"])
        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        dupes = _find_duplicates(lines)
        contradictions = _find_contradictions(lines)
        stale = _find_stale(lines, str(path))

        # Memory debt score: weighted combination
        dupe_score = min(40, len(dupes) * 5)
        contra_score = min(30, len(contradictions) * 10)
        stale_score = min(30, len(stale) * 3)
        debt_score = min(100, dupe_score + contra_score + stale_score)

        grade = "A" if debt_score < 20 else "B" if debt_score < 40 else "C" if debt_score < 60 else "D" if debt_score < 80 else "F"  # noqa: E501

        # Build suggestions text
        suggestions_parts = []
        if dupes:
            suggestions_parts.append(f"{len(dupes)} duplicates found")
        if contradictions:
            suggestions_parts.append(f"{len(contradictions)} contradictions found")
        if stale:
            suggestions_parts.append(f"{len(stale)} stale entries found")

        suggestions = "; ".join(suggestions_parts) if suggestions_parts else "No issues found"

        db.log_garden(mem["agent"], len(dupes), len(contradictions),
                      len(stale), debt_score, suggestions)

        # Display
        table = Table(title=f"ClawForge Garden — {mem['agent']}", box=box.ROUNDED, header_style="bold green")
        table.add_column("Metric", style="bold")
        table.add_column("Count", justify="center")
        table.add_column("Score Contribution", justify="right")

        table.add_row("Duplicates found", str(len(dupes)), f"+{dupe_score}")
        table.add_row("Contradictions found", str(len(contradictions)), f"+{contra_score}")
        table.add_row("Stale entries", str(len(stale)), f"+{stale_score}")
        table.add_section()
        table.add_row("[bold]Memory Debt Score[/bold]", f"[bold]{debt_score:.0f}/100[/bold]", f"Grade: {grade}",
                      style="bold")

        console.print(table)

        if dupes and apply:
            console.print("[yellow]--apply mode: removing duplicates...[/yellow]")
            # Remove duplicate lines (first occurrence)
            seen = set()
            new_lines = []
            for i, line in enumerate(lines):
                stripped = re.sub(r'\s+', ' ', line.strip().lower())
                if len(stripped) >= 10 and stripped in seen:
                    continue  # Skip duplicate
                if len(stripped) >= 10:
                    seen.add(stripped)
                new_lines.append(line)

            path.write_text("\n".join(new_lines), encoding="utf-8")
            console.print(f"[green]Removed {len(dupes)} duplicate lines from {mem['agent']} MEMORY.md[/green]")
        elif dupes:
            console.print("[dim]Use --apply to remove duplicates[/dim]")

        console.print()
