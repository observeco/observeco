"""System prompt compression with per-component token breakdown.

Reads from stdin, decomposes into identity/skills/memory/tools/guidance,
estimates tokens, and reports savings.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table

from observeco.db import Database

console = Console()
db = Database()

# Rough token estimation: ~4 chars per token for English text
CHARS_PER_TOKEN = 4.0  # Rough token estimation: ~4 chars per token for English text

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


def _compress_skill_body(body_text: str) -> tuple[str, int]:
    """Compress a skill's body text using the guidance compression engine.

    Returns (compressed_text, tokens_saved).
    """
    compressed = compress_guidance_block(body_text)
    if compressed.strip():
        before = _count_tokens(body_text)
        after = _count_tokens(compressed)
        if after < before:
            return compressed, before - after
    return body_text, 0


def compress_skill(skill_path: Path, dry_run: bool = False) -> dict | None:
    """Compress a single SKILL.md file's body text.

    Args:
        skill_path: Path to SKILL.md
        dry_run: If True, don't write changes — only report savings.

    Returns:
        dict with keys: name, saved_tokens, savings_pct, backup_path
        or None if skill has no compressible body.
    """
    body = skill_path.read_text(encoding="utf-8")

    # Split frontmatter from body
    if body.startswith("---"):
        parts = body.split("---", 2)
        frontmatter = parts[1] if len(parts) >= 2 else ""
        body_text = parts[2] if len(parts) >= 3 else ""
    else:
        frontmatter = ""
        body_text = body

    if not body_text.strip():
        return None

    before_tokens = _count_tokens(body_text)
    compressed, saved = _compress_skill_body(body_text)

    if saved == 0:
        return None

    savings_pct = round(saved / max(before_tokens, 1) * 100, 1)
    name = skill_path.parent.name

    if not dry_run:
        # Create backup
        backup_path = skill_path.with_suffix(".md.bak")
        backup_path.write_text(body, encoding="utf-8")

        # Write compressed version
        if frontmatter:
            new_content = f"---{frontmatter}---\n{compressed}"
        else:
            new_content = compressed
        skill_path.write_text(new_content, encoding="utf-8")

        # Log to compress_log (raw SQL, consistent with watch.py)
        from observeco.db import Database
        db_local = Database()
        conn = db_local._get_conn()
        after_tokens = _count_tokens(new_content)
        conn.execute(
            "INSERT INTO compress_log (agent_name, mode, before_tokens, after_tokens, savings, "
            "savings_pct, file_path, backup_path, triggered_by, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, "skill_lite", _count_tokens(body), after_tokens, saved,
             savings_pct, str(skill_path), str(backup_path), "skill_compress", int(time.time())),
        )
        conn.commit()
    else:
        backup_path = None

    return {
        "name": name,
        "path": str(skill_path),
        "before_tokens": before_tokens,
        "saved_tokens": saved,
        "savings_pct": savings_pct,
        "backup_path": str(backup_path) if backup_path else None,
        "dry_run": dry_run,
    }


def run_skills(compress: bool = False, compress_limit: int = 0, dry_run: bool = True) -> None:
    """Audit all Hermes skill files: token cost, ranked by total tokens.

    Args:
        compress: If True, compress skill body text after audit.
        compress_limit: Max number of skills to compress (0 = all compressible).
        dry_run: If True and compress=True, show savings without applying.

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
            "path": sf,
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

    # ── Compression pass ──
    if compress:
        limit = compress_limit if compress_limit > 0 else len(skills)
        compressed_count = 0
        total_saved = 0
        tag = "[yellow]Dry run:[/yellow]" if dry_run else "[green]Compressed:[/green]"
        for i, s in enumerate(skills[:limit]):
            result = compress_skill(s["path"], dry_run=dry_run)
            if result:
                compressed_count += 1
                total_saved += result["saved_tokens"]
                action = "would save" if dry_run else "saved"
                console.print(f"  {tag} {result['name']}: {action} {result['saved_tokens']} tok ({result['savings_pct']:+.1f}%)")
        if compressed_count > 0:
            console.print(f"[bold]{'[dry run] Would save' if dry_run else 'Saved'} {total_saved:,} tokens across {compressed_count} skills[/bold]")
        else:
            console.print("[dim]No compressible skills found.[/dim]")


# ── Compression (Lite/Full) ──────────────────────────────────────────────────


def compress_guidance_block(block: str) -> str:
    """Compress a single guidance block using rule-based shortening.

    Lite: compress guidance blocks only (rules → condensed).
    Full: also cull memory sections to active content, deduplicate skills,
          and refactor context references.
    """
    lines = block.splitlines()
    # Remove empty lines at start/end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    # Simple rule-based compression
    compressed = []
    seen_rules = set()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            compressed.append("")
            continue
        # Deduplicate identical guidance rules
        key = stripped.lower()
        if key in seen_rules:
            continue
        seen_rules.add(key)
        # Shorten common verbose patterns
        shortened = stripped
        shortened = shortened.replace("you MUST", "must")
        shortened = shortened.replace("You MUST", "Must")
        shortened = shortened.replace("you should", "should")
        shortened = shortened.replace("You should", "Should")
        shortened = shortened.replace("you may", "can")
        shortened = shortened.replace("You may", "Can")
        shortened = shortened.replace("do not", "don't")
        shortened = shortened.replace("Do not", "Don't")
        shortened = shortened.replace("please ", "")
        shortened = shortened.replace("Please ", "")
        if line.startswith(" ") or line.startswith("\t"):
            compressed.append("  " + shortened if not shortened.startswith((" ", "\t")) else shortened)
        else:
            compressed.append(shortened)

    return "\n".join(compressed)


def _log_compress_result(agent_name: str, mode: str, before_tokens: int, after_tokens: int,
                          savings: int, savings_pct: float, soul_path: Path,
                          backup_path: Path) -> None:
    """Log a compression result to compress_log (dashboard SSOT)."""
    from observeco.db import Database
    try:
        db = Database()
        conn = db._get_conn()
        conn.execute(
            "INSERT INTO compress_log (agent_name, mode, before_tokens, after_tokens, savings, "
            "savings_pct, file_path, backup_path, triggered_by, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_name, mode, before_tokens, after_tokens, savings, savings_pct,
             str(soul_path), str(backup_path), "cli", int(time.time())),
        )
        conn.commit()
    except Exception:
        pass


def run_compress(agent_name: str, mode: str = "lite", filepath: str | None = None) -> dict:
    """Compress an agent's SOUL.md file.

    Args:
        agent_name: Name of the agent.
        mode: 'lite' (guidance only) or 'full' (guidance + memory + skills).
        filepath: Optional explicit path to SOUL.md. If None, auto-discover.

    Returns:
        dict with keys: status, message, backup, before_tokens, after_tokens, savings_pct.

    Raises:
        FileNotFoundError: if SOUL.md can't be found.
        ValueError: if mode is invalid.
    """
    if mode not in ("lite", "full"):
        raise ValueError(f"Invalid mode '{mode}'. Use 'lite' or 'full'.")

    # Find the SOUL.md file
    if filepath:
        soul_path = Path(filepath)
    else:
        # Auto-discover from profiles directory
        profiles_dir = Path.home() / ".hermes" / "profiles"
        if (profiles_dir / agent_name / "SOUL.md").exists():
            soul_path = profiles_dir / agent_name / "SOUL.md"
        elif (Path.home() / ".hermes" / "profiles" / agent_name / "SOUL.md").exists():
            soul_path = Path.home() / ".hermes" / "profiles" / agent_name / "SOUL.md"
        else:
            # Check root .hermes
            root_soul = Path.home() / ".hermes" / "SOUL.md"
            if agent_name == "hermes" and root_soul.exists():
                soul_path = root_soul
            else:
                # Search broadly
                import glob as glob_mod
                matches = list(glob_mod.glob(str(Path.home() / ".hermes" / "**" / "SOUL.md"), recursive=True))
                # Filter matches by proximity to agent_name in path
                agent_matches = [m for m in matches if agent_name in m]
                if agent_matches:
                    soul_path = Path(agent_matches[0])
                else:
                    raise FileNotFoundError(
                        f"Could not find SOUL.md for agent '{agent_name}'. "
                        f"Searched: ~/.hermes/profiles/{agent_name}/SOUL.md"
                    )

    if not soul_path.exists():
        raise FileNotFoundError(f"SOUL.md not found at {soul_path}")

    original_text = soul_path.read_text(encoding="utf-8")
    before_tokens = _estimate_tokens(original_text)

    # Parse sections
    text = original_text

    # Lite mode: compress all content globally (section-agnostic)
    # Apply rule-based shortening to every line
    lines = text.splitlines()
    new_lines = []
    blank_count = 0
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Don't compress code blocks, headings, or empty lines
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue
        if not stripped:
            blank_count += 1
            new_lines.append(line)
            continue
        if stripped.startswith("#") and not stripped.startswith("##"):
            # Top-level heading — keep as-is
            new_lines.append(line)
            continue

        # Skip lines that are clearly structural
        if re.match(r"^[-*_]{3,}$", stripped):
            new_lines.append(line)
            continue

        blank_count = 0

        # Apply guidance compression rules to every non-heading line
        shortened = stripped
        shortened = shortened.replace("you MUST", "must")
        shortened = shortened.replace("You MUST", "Must")
        shortened = shortened.replace("you should", "should")
        shortened = shortened.replace("You should", "Should")
        shortened = shortened.replace("you may", "can")
        shortened = shortened.replace("You may", "Can")
        shortened = shortened.replace("do not", "don't")
        shortened = shortened.replace("Do not", "Don't")
        shortened = shortened.replace("please ", "")
        shortened = shortened.replace("Please ", "")
        shortened = shortened.replace("Do NOT", "Don't")
        shortened = shortened.replace("do NOT", "don't")

        # Preserve indentation
        if line.startswith(" ") or line.startswith("\t"):
            indent = line[:len(line) - len(line.lstrip())]
            shortened = indent + shortened
        new_lines.append(shortened)

    text = "\n".join(new_lines)

    # Full mode: additional compression on memory and skills
    if mode == "full":
        text = _full_compress(text)

    # Trim blank lines at boundaries
    text = text.strip()
    if not text.endswith("\n"):
        text += "\n"

    after_tokens = _estimate_tokens(text)
    savings = before_tokens - after_tokens
    savings_pct = round(savings / max(before_tokens, 1) * 100, 1)

    # Create backup
    backup_path = soul_path.with_suffix(".md.bak")
    backup_path.write_text(original_text, encoding="utf-8")

    # Write compressed version
    soul_path.write_text(text, encoding="utf-8")

    # Log to database — both chisel_trims (for analysis) and compress_log (for dashboard)
    from observeco.db import Database
    analysis = _analyse_prompt(text)
    db_local = Database()
    db_local.log_trim(
        agent_name,
        analysis["identity_tokens"], analysis["skills_tokens"],
        analysis["memory_tokens"], analysis["tools_tokens"],
        analysis["guidance_tokens"], analysis["total_tokens"],
        analysis.get("savings_ratio", 0),
        mode=mode,
    )
    # Also log to compress_log for the dashboard (Budget Planner / Brain Analysis)
    _log_compress_result(agent_name, mode, before_tokens, after_tokens, savings, savings_pct, soul_path, backup_path)

    return {
        "status": "ok",
        "agent": agent_name,
        "mode": mode,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "savings": savings,
        "savings_pct": savings_pct,
        "message": f"{mode.capitalize()} compression applied: {before_tokens} → {after_tokens} tok ({savings_pct:+.1f}%)",
        "backup": str(backup_path),
    }


def _full_compress(text: str) -> str:
    """Full compression: memory section culling + skill dedup + context refactoring."""
    lines = text.splitlines()
    result = []
    in_memory = False
    in_skills = False
    memory_lines = []
    skills_lines = []

    for i, line in enumerate(lines):
        lower = line.strip().lower()
        # Detect memory section
        if any(lower.startswith(f"## {kw}") or lower.startswith(f"# {kw}") for kw in ["memory", "context", "history", "recall"]):
            in_memory = True
            in_skills = False
            memory_lines = [line]
            continue
        # Detect skills section
        if any(lower.startswith(f"## {kw}") or lower.startswith(f"# {kw}") for kw in ["skill", "tool", "command", "function"]):
            in_skills = True
            in_memory = False
            skills_lines = [line]
            continue
        # End of a section
        if re.match(r"^#{1,4}\s+", line):
            if in_memory:
                in_memory = False
            if in_skills:
                in_skills = False
        if in_memory:
            memory_lines.append(line)
        elif in_skills:
            skills_lines.append(line)
        else:
            result.append(line)

    # Process memory: keep only lines with actual content (non-empty, non-header)
    if memory_lines:
        header = memory_lines[0]
        body = memory_lines[1:]
        # Keep lines that aren't purely formatting
        kept = [ln for ln in body if ln.strip() and not re.match(r"^[-*_]{3,}$", ln.strip())]
        # If more than 15 lines, keep first 10 + last 3
        if len(kept) > 15:
            kept = kept[:10] + ["", "... (trimmed by Full compression) ...", ""] + kept[-3:]
        result.append(header)
        result.extend(kept)

    # Process skills: deduplicate by content
    if skills_lines:
        header = skills_lines[0]
        body = skills_lines[1:]
        seen = set()
        deduped = []
        for line in body:
            key = line.strip().lower()
            if key not in seen or not line.strip():
                seen.add(key)
                deduped.append(line)
        if len(deduped) != len(body):
            deduped.append("  (duplicates removed by Full compression)")
        result.append("")
        result.append(header)
        result.extend(deduped)

    return "\n".join(result)
