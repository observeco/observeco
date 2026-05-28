"""System prompt compression with per-component token breakdown.

Reads from stdin, decomposes into identity/skills/memory/tools/guidance,
estimates tokens, and reports savings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

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


def _analyse_prompt(prompt: str) -> dict:
    """Analyse a prompt and return token breakdown dict.

    Returns dict with identity, skills, memory, tools, guidance, total tokens and savings_ratio.
    """
    total_chars = len(prompt)
    total_tokens = _estimate_tokens(prompt)

    lines = prompt.split("\n")
    section_texts: dict[str, list[str]] = {
        "identity": [], "skills": [], "memory": [], "tools": [], "guidance": [],
    }

    current_section = "guidance"
    for line in lines:
        classified = _classify_line(line)
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
    savings_ratio = min(0.25, max(0.0, guidance_t / max(total_tokens, 1)))

    return {
        "identity_tokens": identity_t,
        "skills_tokens": skills_t,
        "memory_tokens": memory_t,
        "tools_tokens": tools_t,
        "guidance_tokens": guidance_t,
        "total_tokens": total_tokens,
        "savings_ratio": savings_ratio,
        "breakdown": breakdown,
        "total_chars": total_chars,
    }


def run_trim() -> None:
    """Read prompt from stdin, decompose, and display breakdown."""
    prompt = sys.stdin.read()
    if not prompt or not prompt.strip():
        console.print("[yellow]No input received. Pipe a prompt:[/yellow]")
        console.print("  [bold]echo \"your prompt\" | observeco chisel trim[/bold]")
        return

    result = _analyse_prompt(prompt)

    db.log_trim("stdin",
                result["identity_tokens"], result["skills_tokens"],
                result["memory_tokens"], result["tools_tokens"],
                result["guidance_tokens"], result["total_tokens"],
                result["savings_ratio"])

    # Display
    table = Table(title="Chisel Trim — Token Breakdown", box=box.ROUNDED, header_style="bold green")
    table.add_column("Component", style="bold")
    table.add_column("Chars", justify="right")
    table.add_column("Est. Tokens", justify="right")
    table.add_column("% of Total", justify="right")

    for section, data in result["breakdown"].items():
        pct = f"{data['tokens'] / max(result['total_tokens'], 1) * 100:.1f}%"
        table.add_row(section.capitalize(), str(data["chars"]), str(data["tokens"]), pct)

    table.add_section()
    table.add_row("[bold]Total[/bold]", str(result["total_chars"]), str(result["total_tokens"]), "100%",
                  style="bold")

    console.print(table)
    console.print(f"[dim]Estimated savings: {result['savings_ratio']*100:.0f}% via guideline trimming[/dim]")


def run_trim_file(agent_name: str, file_path: str) -> dict | None:
    """Analyse an agent's SOUL.md and log trim data to the database.

    Args:
        agent_name: Name of the agent (used for DB lookup)
        file_path: Path to the SOUL.md file

    Returns:
        Analysis dict or None if file doesn't exist.
    """
    path = Path(file_path)
    if not path.exists():
        return None

    prompt = path.read_text(encoding="utf-8")
    if not prompt.strip():
        return None

    result = _analyse_prompt(prompt)
    db.log_trim(agent_name,
                result["identity_tokens"], result["skills_tokens"],
                result["memory_tokens"], result["tools_tokens"],
                result["guidance_tokens"], result["total_tokens"],
                result["savings_ratio"])
    return result


# ── Skill Audit ──────────────────────────────────────────────────────────────


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken if available, fall back to chars/4."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return max(1, int(len(text) / 4.0))


def _parse_skill_yaml(path: Path) -> dict | None:
    """Parse YAML frontmatter from a SKILL.md file. Returns dict or None."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    _, frontmatter, *_rest = content.split("---", 2)
    try:
        import yaml
        return yaml.safe_load(frontmatter)
    except ImportError:
        # Fallback: minimal YAML parser for known fields
        meta: dict[str, str | list[str]] = {}
        for line in frontmatter.strip().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if val.startswith("[") and val.endswith("]"):
                    val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
                elif val.startswith(">") or val.startswith("|"):
                    continue  # skip block scalars in minimal mode
                else:
                    val = val.strip('"').strip("'")
                meta[key] = val
        return meta if meta else None


def run_skills() -> None:
    """Audit all Hermes skill files: token cost, ranked by total tokens.

    Walks ~/.hermes/skills/, finds SKILL.md files, parses YAML frontmatter,
    measures token counts, and reports a ranked table with per-category totals.
    """
    skills_dir = Path.home() / ".hermes" / "skills"
    if not skills_dir.is_dir():
        console.print(f"[yellow]Skills directory not found: {skills_dir}[/yellow]")
        return

    skills: list[dict] = []
    skill_files = sorted(skills_dir.rglob("SKILL.md"))

    for sf in skill_files:
        try:
            meta = _parse_skill_yaml(sf)
        except Exception:
            meta = None

        body = sf.read_text(encoding="utf-8")

        # Split frontmatter from body
        if body.startswith("---"):
            parts = body.split("---", 2)
            desc_text = parts[1] if len(parts) >= 2 else ""
            body_text = parts[2] if len(parts) >= 3 else ""
        else:
            desc_text = ""
            body_text = body

        desc_tokens = _count_tokens(desc_text)
        body_tokens = _count_tokens(body_text)
        total = desc_tokens + body_tokens

        name = (meta or {}).get("name", sf.parent.name)
        tags_raw = (meta or {}).get("tags", [])
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        else:
            tags = list(tags_raw) if isinstance(tags_raw, list) else []
        category = sf.parent.parent.name if sf.parent.parent.name != "skills" else "uncategorized"

        skills.append({
            "name": str(name),
            "category": category,
            "desc_tokens": desc_tokens,
            "body_tokens": body_tokens,
            "total": total,
            "tags": tags,
        })

    if not skills:
        console.print("[yellow]No SKILL.md files found.[/yellow]")
        return

    # Sort descending by total tokens (worst offenders first)
    skills.sort(key=lambda s: s["total"], reverse=True)

    # ── Ranked table ──
    rank_table = Table(
        title=f"Skill Audit — {len(skills)} Skills Ranked by Token Cost",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    rank_table.add_column("#", justify="right", style="dim")
    rank_table.add_column("Skill", style="bold")
    rank_table.add_column("Category")
    rank_table.add_column("Desc Tokens", justify="right")
    rank_table.add_column("Body Tokens", justify="right")
    rank_table.add_column("Total", justify="right")
    rank_table.add_column("Tags")

    for i, s in enumerate(skills, 1):
        tags_str = ", ".join(s["tags"][:5])
        if len(s["tags"]) > 5:
            tags_str += f"…(+{len(s['tags'])-5})"
        rank_table.add_row(
            str(i),
            s["name"],
            s["category"],
            str(s["desc_tokens"]),
            str(s["body_tokens"]),
            str(s["total"]),
            tags_str,
        )

    console.print()
    console.print(rank_table)

    # ── Per-category cumulative totals ──
    cat_totals: dict[str, dict] = {}
    for s in skills:
        cat = s["category"]
        if cat not in cat_totals:
            cat_totals[cat] = {"count": 0, "desc_tokens": 0, "body_tokens": 0, "total": 0}
        cat_totals[cat]["count"] += 1
        cat_totals[cat]["desc_tokens"] += s["desc_tokens"]
        cat_totals[cat]["body_tokens"] += s["body_tokens"]
        cat_totals[cat]["total"] += s["total"]

    cat_table = Table(
        title="Per-Category Cumulative Token Cost",
        box=box.ROUNDED,
        header_style="bold yellow",
    )
    cat_table.add_column("Category", style="bold")
    cat_table.add_column("Skills", justify="right")
    cat_table.add_column("Desc Tokens", justify="right")
    cat_table.add_column("Body Tokens", justify="right")
    cat_table.add_column("Total", justify="right")

    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1]["total"], reverse=True)
    for cat, data in sorted_cats:
        cat_table.add_row(
            cat,
            str(data["count"]),
            str(data["desc_tokens"]),
            str(data["body_tokens"]),
            str(data["total"]),
        )

    grand = sum(s["total"] for s in skills)
    cat_table.add_section()
    cat_table.add_row(
        "[bold]Grand Total[/bold]",
        str(len(skills)),
        str(sum(s["desc_tokens"] for s in skills)),
        str(sum(s["body_tokens"] for s in skills)),
        str(grand),
        style="bold",
    )

    console.print(cat_table)
    console.print(f"[dim]Total skill tokens across {len(skills)} files: {grand:,}[/dim]")
