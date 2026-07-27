"""chisel_cut — Suggest, cut, verify, and learn.

v0.2 additions to Chisel. Zero external deps. stdlib only.

Three detection types for suggest:
  - duplicate_rule: identical lines across sections
  - stale_ref: file paths that don't exist on disk
  - unused_skill: skill files not referenced in prompt

Cut applies rule-based compression + removes stale refs.
Verify re-trims after cut and confirms savings.
Learn stores verified cuts for future suggestions.
"""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import time
from pathlib import Path
from typing import Optional

from .chisel_core import estimate_tokens

# ── Constants ──────────────────────────────────────────────────────────────

HOME = Path(os.path.expanduser("~"))
HERMES_HOME = HOME / ".hermes"
BACKUP_DIR = HERMES_HOME / "state" / "chisel" / "backups"

# Path patterns for stale reference detection
# Positive char class: word chars, dots, slashes, hyphens, plus, at-sign.
# Stops at backticks, commas, quotes, brackets — preventing false positives
# from markdown inline code spans like `~/.hermes/signals/`.
PATH_PATTERN = re.compile(r"(?:~|/Users/[^/\s]+|\.hermes)/[\w./+@-]+")

# ── Suggest: Duplicate Rules ─────────────────────────────────────────────


def find_duplicates(prompt: str) -> list[dict]:
    """Find duplicate non-empty lines across the prompt.

    Only exact matches (case-insensitive, stripped). Skips short lines
    (<20 chars), headings, and code fences.

    ponytail: exact match only. "Never modify config.yaml without approval"
    and "Don't edit config.yaml without permission" are not detected as
    duplicates. Ceiling: ~30% of semantic duplicates missed.
    Upgrade path: embedding-based similarity (v0.3).
    """
    lines = prompt.split("\n")
    seen: dict[str, tuple[int, str]] = {}  # normalized_line → (line_num, original)
    duplicates = []
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if len(stripped) < 20:
            continue
        if stripped.startswith("#") or stripped.startswith("```"):
            continue
        if stripped in seen:
            duplicates.append({
                "type": "duplicate_rule",
                "line": line.strip(),
                "first_seen_line": seen[stripped][1],
                "first_seen_num": seen[stripped][0],
                "line_num": i,
                "tokens": estimate_tokens(line),
            })
        else:
            seen[stripped] = (i, line.strip())
    return duplicates


# ── Suggest: Stale File References ────────────────────────────────────────


def find_stale_refs(prompt: str) -> list[dict]:
    """Find file path references in the prompt that don't exist on disk.

    ponytail: regex path extraction misses paths inside code blocks and
    inline backticks. Ceiling: ~10% of paths missed.
    Upgrade path: markdown AST parsing to distinguish code from prose.
    """
    matches = PATH_PATTERN.findall(prompt)
    stale = []
    for m in matches:
        expanded = os.path.expanduser(m)
        if not os.path.exists(expanded):
            stale.append({
                "type": "stale_ref",
                "path": m,
                "tokens": estimate_tokens(m),
            })
    return stale


# ── Suggest: Unused Skill Descriptions ────────────────────────────────────


def find_unused_skills(prompt: str, skills_dir: Optional[Path] = None) -> list[dict]:
    """Find skill files not referenced in the prompt.

    ponytail: "Not in prompt" ≠ "unused." The skill may be loaded
    dynamically by Hermes' skill system without appearing in the static
    prompt text. Ceiling: false positives on dynamically-loaded skills.
    Upgrade path: cross-reference against Hermes' skills_list API output.
    """
    if skills_dir is None:
        skills_dir = HERMES_HOME / "skills"
    if not skills_dir.is_dir():
        return []
    prompt_lower = prompt.lower()
    unused = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_name = skill_dir.name.lower()
        if skill_name not in prompt_lower:
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text(encoding="utf-8")
                unused.append({
                    "type": "unused_skill",
                    "skill": skill_dir.name,
                    "tokens": estimate_tokens(content),
                })
    return unused


# ── Suggest: Aggregate ────────────────────────────────────────────────────


def suggest(prompt: str, skills_dir: Optional[Path] = None) -> list[dict]:
    """Run all detection types and return aggregated suggestions.

    Each suggestion dict has: type, tokens, and type-specific fields.
    """
    results = []
    results.extend(find_duplicates(prompt))
    results.extend(find_stale_refs(prompt))
    results.extend(find_unused_skills(prompt, skills_dir))
    return results


# ── Cut: Rule-Based Compression ──────────────────────────────────────────


def compress_guidance_block(block: str) -> str:
    """Compress a text block using rule-based shortening + dedup.

    Source: adapted from observeco chisel/trim.py:compress_guidance_block()
    and chisel/trim.py:run_compress().

    Rules:
      - Deduplicate identical lines (case-insensitive exact match)
      - Shorten verbose patterns (you MUST → must, do not → don't, etc.)
      - Remove filler words (please, Note:, Important:)
    """
    lines = block.splitlines()
    # Remove empty lines at start/end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    compressed = []
    seen_rules: set[str] = set()
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Preserve code blocks entirely
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            compressed.append(line)
            continue
        if in_code_block:
            compressed.append(line)
            continue

        # Preserve headings
        if stripped.startswith("#"):
            compressed.append(line)
            continue

        # Preserve empty lines
        if not stripped:
            compressed.append(line)
            continue

        # Preserve separators
        if re.match(r"^[-*_]{3,}$", stripped):
            compressed.append(line)
            continue

        # Deduplicate identical rules
        key = stripped.lower()
        if key in seen_rules:
            continue
        seen_rules.add(key)

        # Apply shortenings
        shortened = stripped
        replacements = [
            ("you MUST", "must"), ("You MUST", "Must"),
            ("you should", "should"), ("You should", "Should"),
            ("you may", "can"), ("You may", "Can"),
            ("do not", "don't"), ("Do not", "Don't"),
            ("do NOT", "don't"), ("Do NOT", "Don't"),
            ("please ", ""), ("Please ", ""),
            ("Note: ", ""), ("NOTE: ", ""),
            ("Important: ", ""), ("IMPORTANT: ", ""),
        ]
        for old, new in replacements:
            shortened = shortened.replace(old, new)

        # Preserve indentation
        if line.startswith(" ") or line.startswith("\t"):
            indent = line[: len(line) - len(line.lstrip())]
            shortened = indent + shortened.lstrip()

        compressed.append(shortened)

    return "\n".join(compressed)


# ── Cut: Apply ────────────────────────────────────────────────────────────


def _unified_diff(original: str, modified: str, file_path: str = "SOUL.md") -> str:
    """Generate a unified diff string."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines, mod_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    )
    return "".join(diff)


def _strip_stale_outside_code(text: str, paths: list[str]) -> str:
    """Remove stale path strings from text, skipping inside backtick code spans.

    Splits on `code spans`, only replaces in the prose segments, rejoins.
    """
    segments = re.split(r"(`[^`]+`)", text)
    for i, seg in enumerate(segments):
        if seg.startswith("`") and seg.endswith("`"):
            continue
        for p in paths:
            seg = seg.replace(p, "")
        segments[i] = seg
    return "".join(segments)


def apply_cuts(
    file_path: str,
    suggestions: list[dict],
    apply: bool = False,
) -> dict:
    """Apply suggested cuts to a file.

    Args:
        file_path: Path to the file to cut (e.g. SOUL.md).
        suggestions: List of suggestion dicts from suggest().
        apply: If True, write the modified file and create backup.
               If False (default), only show diff.

    Returns:
        dict with: applied, file, backup, before_tokens, after_tokens,
                   tokens_saved, savings_pct, diff
    """
    path = Path(file_path)
    if not path.exists():
        return {
            "applied": False,
            "file": file_path,
            "error": f"File not found: {file_path}",
        }

    original = path.read_text(encoding="utf-8")
    backup_path: Optional[Path] = None

    if apply:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / f"{path.name}.{int(time.time())}.bak"
        backup_path.write_text(original)

    # Apply rule-based compression
    compressed = compress_guidance_block(original)

    # Remove stale references — only outside code spans
    stale_paths = [s["path"] for s in suggestions if s["type"] == "stale_ref"]
    if stale_paths:
        compressed = _strip_stale_outside_code(compressed, stale_paths)

    before_tokens = estimate_tokens(original)
    after_tokens = estimate_tokens(compressed)

    if apply:
        path.write_text(compressed)

    return {
        "applied": apply,
        "file": file_path,
        "backup": str(backup_path) if backup_path else None,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "tokens_saved": before_tokens - after_tokens,
        "savings_pct": round(
            (1 - after_tokens / max(before_tokens, 1)) * 100, 1
        ),
        "diff": _unified_diff(original, compressed, path.name),
    }


# ── Rule Hash (for learning) ─────────────────────────────────────────────


def rule_hash(text: str) -> str:
    """SHA-256 of a rule/pattern for dedup in learning."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


# ── Formatting ────────────────────────────────────────────────────────────


def format_suggestions(suggestions: list[dict]) -> str:
    """Format suggestions as a plain-text table."""
    if not suggestions:
        return "No cuttable items found. Your prompt is already lean."

    lines = []
    lines.append(f"{'Type':<20} {'Item':<50} {'Tokens':>8}")
    lines.append("-" * 80)

    total_tokens = 0
    for s in suggestions:
        item = ""
        if s["type"] == "duplicate_rule":
            item = s["line"][:48]
        elif s["type"] == "stale_ref":
            item = s["path"][:48]
        elif s["type"] == "unused_skill":
            item = s["skill"][:48]
        lines.append(
            f"{s['type']:<20} {item:<50} {s['tokens']:>8}"
        )
        total_tokens += s["tokens"]

    lines.append("-" * 80)
    lines.append(f"{'Total':<20} {'':<50} {total_tokens:>8}")
    lines.append("")
    lines.append(f"Estimated savings: {total_tokens} tokens")
    return "\n".join(lines)


def format_cut_result(result: dict) -> str:
    """Format cut result for display."""
    if result.get("error"):
        return f"Error: {result['error']}"

    lines = []
    if result["applied"]:
        lines.append(f"✅ Cut applied to {result['file']}")
        if result.get("backup"):
            lines.append(f"   Backup: {result['backup']}")
    else:
        lines.append(f"📋 Dry-run for {result['file']}")
        lines.append("   No files modified. Use --apply to apply.")

    lines.append("")
    lines.append(
        f"   Before: {result['before_tokens']} tokens"
    )
    lines.append(
        f"   After:  {result['after_tokens']} tokens"
    )
    lines.append(
        f"   Saved:  {result['tokens_saved']} tokens ({result['savings_pct']}%)"
    )
    lines.append("")
    lines.append("Diff:")
    lines.append(result.get("diff", "(no changes)"))

    return "\n".join(lines)


def format_verify_result(result: dict) -> str:
    """Format verify result for display."""
    status = result.get("status", "unknown")
    if status == "no_cut_found":
        return "No cuts to verify. Run `hermes chisel cut --apply` first."
    if status == "no_pre_cut_data":
        return (
            "Cannot verify — no pre-cut trim snapshot found. "
            "The cut was applied but there's no baseline to compare against."
        )
    if status == "verified":
        return (
            f"✅ Verified: {result['tokens_before']} → {result['tokens_after']} tokens "
            f"(saved {result['tokens_saved']}). Cut marked safe."
        )
    if status == "regression":
        return (
            f"⚠️ Regression detected: tokens went from {result['tokens_before']} "
            f"to {result['tokens_after']} (+{abs(result['tokens_saved'])}). "
            f"Cut marked as regression."
        )
    return f"Unknown status: {status}"
