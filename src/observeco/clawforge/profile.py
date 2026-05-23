"""Context profiler for OpenClaw agents.

Reads OpenClaw agent config (SOUL.md / AGENTS.md), MEMORY.md, skills directory,
workspace files, and estimates tokens per source.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from observeco.db import Database

console = Console()
db = Database()

CHARS_PER_TOKEN = 4.0


def _find_openclaw_agent(agent_name: Optional[str] = None) -> list[dict]:
    """Find OpenClaw agents by scanning common locations."""
    agents = []
    search_locations = []

    # ~/.hermes/profiles/<name>/SOUL.md
    profiles_dir = Path.home() / ".hermes" / "profiles"
    if profiles_dir.exists():
        for entry in profiles_dir.iterdir():
            if entry.is_dir():
                soul = entry / "SOUL.md"
                if soul.exists():
                    agents.append({
                        "name": entry.name,
                        "config_path": str(soul),
                        "config_dir": str(entry),
                    })

    # Also check ~/.hermes/agents/
    agents_dir = Path.home() / ".hermes" / "agents"
    if agents_dir.exists():
        for entry in agents_dir.iterdir():
            if entry.suffix == ".md" or entry.is_dir():
                name = entry.stem if entry.suffix else entry.name
                agents.append({
                    "name": name,
                    "config_path": str(entry) if entry.is_file() else str(entry / "SOUL.md"),
                    "config_dir": str(entry) if entry.is_dir() else str(entry.parent),
                })

    # OpenClaw workspace
    oc_workspace = Path.home() / "projects" / "openclaw"
    if oc_workspace.exists():
        agents.append({
            "name": "openclaw",
            "config_path": str(oc_workspace / "AGENTS.md") if (oc_workspace / "AGENTS.md").exists() else str(oc_workspace),
            "config_dir": str(oc_workspace),
        })

    # Deduplicate by name
    seen = set()
    deduped = []
    for a in agents:
        if a["name"] not in seen:
            seen.add(a["name"])
            deduped.append(a)

    if agent_name:
        deduped = [a for a in deduped if a["name"] == agent_name]

    return deduped


def _count_file_size(path: Path) -> int:
    """Count characters in a file."""
    if path.exists() and path.is_file():
        try:
            return len(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return 0
    return 0


def _count_dir_size(directory: Path, glob_pattern: str = "*.md") -> int:
    """Total chars of all matching files in a directory."""
    total = 0
    if directory.exists():
        for f in directory.glob(glob_pattern):
            total += _count_file_size(f)
    return total


def _estimate_tokens(chars: int) -> int:
    return max(1, int(chars / CHARS_PER_TOKEN))


def run_profile(agent_name: Optional[str] = None) -> None:
    """Display context profile for OpenClaw agents."""
    agents = _find_openclaw_agent(agent_name)

    if not agents:
        console.print("[yellow]No OpenClaw agents found.[/yellow]")
        console.print("Searched: ~/.hermes/profiles/*/SOUL.md, ~/.hermes/agents/, ~/projects/openclaw/")
        return

    for agent in agents:
        config_dir = Path(agent["config_dir"])
        name = agent["name"]

        # MEMORY.md
        memory_path = config_dir / "MEMORY.md"
        memory_chars = _count_file_size(memory_path)
        memory_tokens = _estimate_tokens(memory_chars)

        # Skills directory
        skills_dir = config_dir / "skills"
        skill_count = 0
        skill_chars = 0
        if skills_dir.exists():
            skill_count = len([f for f in skills_dir.iterdir() if f.suffix in (".md", ".yaml", ".yml")])
            skill_chars = _count_dir_size(skills_dir, "*.md") + _count_dir_size(skills_dir, "*.yaml")

        # Workspace files
        workspace_files = len([f for f in config_dir.iterdir() if f.is_file()])
        workspace_chars = _count_dir_size(config_dir, "*.*")

        # History / bootstrap
        history_file = config_dir / "BOOTSTRAP.md"
        history_chars = _count_file_size(history_file)
        history_tokens = _estimate_tokens(history_chars)

        total_tokens = memory_tokens + _estimate_tokens(skill_chars) + history_tokens

        db.log_profile(name, memory_chars, skill_count, workspace_files,
                       history_tokens, total_tokens)

        table = Table(title=f"ClawForge Profile — {name}", box=box.ROUNDED, header_style="bold blue")
        table.add_column("Source", style="bold")
        table.add_column("Size (chars)", justify="right")
        table.add_column("Est. Tokens", justify="right")

        table.add_row("MEMORY.md", str(memory_chars), str(memory_tokens))
        table.add_row(f"Skills ({skill_count} files)", str(skill_chars), str(_estimate_tokens(skill_chars)))
        table.add_row("Workspace files", str(workspace_chars), str(_estimate_tokens(workspace_chars)))
        table.add_row("BOOTSTRAP.md", str(history_chars), str(history_tokens))
        table.add_section()
        table.add_row("[bold]Total[/bold]", "", str(total_tokens), style="bold")

        console.print(table)
