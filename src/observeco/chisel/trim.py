"""System prompt compression with per-component token breakdown.

Reads from stdin, decomposes into identity/skills/memory/tools/guidance,
estimates tokens, and reports savings.
"""

from __future__ import annotations

import re
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from observeco.db import Database

console = Console()
db = Database()

# Rough token estimation: ~4 chars per token for English text
CHARS_PER_TOKEN = 4.0

SECTIONS = {
    "identity": ["identity", "role", "persona", "who you are", "you are", "i am"],
    "skills": ["skill", "tool", "command", "function", "available action", "you can use",
               "you have access to"],
    "memory": ["memory", "context", "history", "previous", "conversation", "recall",
               "user profile", "personal info"],
    "tools": ["tool description", "tool schema", "api spec", "json schema", "parameter",
              "endpoint", "request format"],
    "guidance": ["guideline", "rule", "instruction", "constraint", "policy", "format",
                 "output format", "do not", "never", "always", "must", "should"],
}


def _classify_line(line: str) -> str:
    """Classify a line into a component section."""
    lower = line.lower()
    for section, keywords in SECTIONS.items():
        for kw in keywords:
            if kw in lower:
                return section
    return "guidance"  # Default catch-all


def _estimate_tokens(text: str) -> int:
    """Quick token estimate: chars / chars_per_token."""
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def run_trim() -> None:
    """Read prompt from stdin, decompose, and display breakdown."""
    prompt = sys.stdin.read()
    if not prompt or not prompt.strip():
        console.print("[yellow]No input received. Pipe a prompt:[/yellow]")
        console.print("  [bold]echo \"your prompt\" | observeco chisel trim[/bold]")
        return

    total_chars = len(prompt)
    total_tokens = _estimate_tokens(prompt)

    # Simple classification based on section headers and keywords
    lines = prompt.split("\n")
    section_texts: dict[str, list[str]] = {
        "identity": [], "skills": [], "memory": [], "tools": [], "guidance": [],
    }

    current_section = "guidance"
    for line in lines:
        classified = _classify_line(line)
        # Section headers override
        if re.match(r"^#{1,4}\s+", line):
            current_section = classified
        elif any(line.lower().startswith(f"## {s}") or line.lower().startswith(f"# {s}")
                 for s in ["identity", "skills", "memory", "tools", "guidance"]):
            for s in SECTIONS:
                if line.lower().startswith(("#", "##")) and any(kw in line.lower() for kw in SECTIONS[s]):
                    current_section = s
                    break
            else:
                current_section = classified
        section_texts[current_section].append(line)

    breakdown = {}
    for section in section_texts:
        text = "\n".join(section_texts[section]).strip()
        breakdown[section] = {
            "chars": len(text),
            "tokens": _estimate_tokens(text),
        }

    identity_t = breakdown["identity"]["tokens"]
    skills_t = breakdown["skills"]["tokens"]
    memory_t = breakdown["memory"]["tokens"]
    tools_t = breakdown["tools"]["tokens"]
    guidance_t = breakdown["guidance"]["tokens"]

    # Calculate savings (if compressed: removing redundant guidelines)
    savings_ratio = min(0.25, max(0.0, guidance_t / max(total_tokens, 1)))

    db.log_trim("stdin", identity_t, skills_t, memory_t, tools_t, guidance_t,
                total_tokens, savings_ratio)

    # Display
    table = Table(title="Chisel Trim — Token Breakdown", box=box.ROUNDED, header_style="bold green")
    table.add_column("Component", style="bold")
    table.add_column("Chars", justify="right")
    table.add_column("Est. Tokens", justify="right")
    table.add_column("% of Total", justify="right")

    for section, data in breakdown.items():
        pct = f"{data['tokens'] / max(total_tokens, 1) * 100:.1f}%"
        table.add_row(section.capitalize(), str(data["chars"]), str(data["tokens"]), pct)

    table.add_section()
    table.add_row("[bold]Total[/bold]", str(total_chars), str(total_tokens), "100%",
                  style="bold")

    console.print(table)
    console.print(f"[dim]Estimated savings: {savings_ratio*100:.0f}% via guideline trimming[/dim]")
    console.print(f"[dim]Run with --agent <name> to store per-agent history[/dim]")
