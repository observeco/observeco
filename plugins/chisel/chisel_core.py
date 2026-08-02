"""chisel_core — System prompt decomposition + drift detection.

Zero external dependencies. stdlib only: re, json, hashlib, sqlite3.

Two operations:
  - trim: decompose a system prompt into 5 components, estimate tokens
  - drift: compare current composition against rolling baseline
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────

CHARS_PER_TOKEN = 4.0  # English text approximation
FLOOR = 50  # minimum tokens for drift calculation (noise floor)
DRIFT_THRESHOLD_PCT = 10.0  # % change to flag
DRIFT_THRESHOLD_ABS = 50  # absolute token change to flag (both must be true)

SECTIONS: dict[str, list[str]] = {
    "identity": [
        "identity", "role", "persona", "who you are", "you are", "i am",
    ],
    "skills": [
        "skill", "tool", "command", "function", "available action",
        "you can use", "you have access to",
    ],
    "memory": [
        "memory", "context", "history", "previous", "conversation",
        "recall", "user profile", "personal info",
    ],
    "tools": [
        "tool description", "tool schema", "api spec", "json schema",
        "parameter", "endpoint", "request format",
    ],
    "guidance": [
        "guideline", "rule", "instruction", "constraint", "policy",
        "format", "output format", "do not", "never", "always",
        "must", "should",
    ],
}

COMPONENT_ORDER = ["identity", "skills", "memory", "tools", "guidance"]


# ── Token Estimation ──────────────────────────────────────────────────────


def estimate_tokens(text: str) -> int:
    """Quick token estimate: chars / chars_per_token."""
    return max(1, int(len(text) / CHARS_PER_TOKEN))


# ── Section Classification ────────────────────────────────────────────────


def _classify_line(line: str) -> str:
    """Classify a single line into a component section by keyword match."""
    lower = line.lower()
    for section, keywords in SECTIONS.items():
        for kw in keywords:
            if kw in lower:
                return section
    return "guidance"  # default catchall


# ── Decomposition ─────────────────────────────────────────────────────────


def decompose(prompt: str) -> dict:
    """Decompose a system prompt into 5 components with token estimates.

    Returns dict with:
      identity_tokens, skills_tokens, memory_tokens, tools_tokens,
      guidance_tokens, total_tokens, savings_ratio, breakdown, total_chars
    """
    total_chars = len(prompt)
    total_tokens = estimate_tokens(prompt)

    lines = prompt.split("\n")
    section_texts: dict[str, list[str]] = {s: [] for s in SECTIONS}

    current_section = "guidance"
    for line in lines:
        # Markdown heading → classify heading text
        heading_match = re.match(r"^#{1,4}\s+(.+)", line)
        if heading_match:
            heading_text = heading_match.group(1)
            classified = _classify_line(heading_text)
            current_section = classified
        else:
            # Check for section-start patterns like "## Identity" or "# Skills"
            for s in SECTIONS:
                if any(kw in line.lower() for kw in SECTIONS[s]):
                    # Only switch if the line is predominantly about this section
                    # (heuristic: first keyword match wins for section headers)
                    if line.strip().startswith("#") or any(
                        line.lower().startswith(kw) for kw in SECTIONS[s]
                    ):
                        current_section = s
                        break
            else:
                # No section header found — classify by content
                current_section = _classify_line(line)

        section_texts[current_section].append(line)

    breakdown = {}
    for section in section_texts:
        text = "\n".join(section_texts[section]).strip()
        breakdown[section] = {
            "chars": len(text),
            "tokens": estimate_tokens(text),
        }

    identity_t = breakdown["identity"]["tokens"]
    skills_t = breakdown["skills"]["tokens"]
    memory_t = breakdown["memory"]["tokens"]
    tools_t = breakdown["tools"]["tokens"]
    guidance_t = breakdown["guidance"]["tokens"]

    # ponytail: savings_ratio is a rough heuristic — guidance is the most
    # compressible section (rules tend to be verbose and redundant).
    # Ceiling: overestimates savings on prompts where guidance is already tight.
    # Upgrade path: per-section compressibility analysis using actual tokenizer.
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


# ── Drift Detection ───────────────────────────────────────────────────────


def check_drift(current: int, baseline: int) -> tuple[float, int, bool]:
    """Compare current vs baseline. Returns (delta_pct, delta_tokens, breached).

    A breach requires BOTH:
      - >10% relative change (catches proportional growth)
      - >50 token absolute change (catches noise on small sections)
    """
    delta_pct = ((current - baseline) / max(baseline, FLOOR)) * 100
    delta_tokens = current - baseline
    breached = (
        abs(delta_tokens) > DRIFT_THRESHOLD_ABS
        and abs(delta_pct) > DRIFT_THRESHOLD_PCT
    )
    return delta_pct, delta_tokens, breached


def compute_drift(
    current: dict,
    baseline: dict,
) -> list[dict]:
    """Compare current decomposition against baseline.

    current and baseline are dicts from decompose().
    Returns list of drift entries, one per component that breached.
    """
    results = []
    for comp in COMPONENT_ORDER:
        key = f"{comp}_tokens"
        cur_val = current.get(key, 0)
        base_val = baseline.get(key, 0)
        delta_pct, delta_tokens, breached = check_drift(cur_val, base_val)
        results.append({
            "component": comp,
            "current_tokens": cur_val,
            "baseline_tokens": base_val,
            "delta_pct": round(delta_pct, 1),
            "delta_tokens": delta_tokens,
            "breached": breached,
        })
    return results


# ── Prompt Assembly from Hermes Files ─────────────────────────────────────


def assemble_prompt(
    config_yaml: str,
    soul_md: str = "",
    skill_texts: Optional[list[str]] = None,
    memory_texts: Optional[list[str]] = None,
) -> str:
    """Assemble a Hermes system prompt from its source files.

    This approximates what Hermes' _build_system_prompt() produces.
    It's not byte-identical — Hermes has additional layers (tool schemas,
    per-session memory injection, timestamp). But it captures the bulk
    of the token cost.

    ponytail: This is a best-effort reconstruction. Hermes' actual prompt
    includes dynamically-injected tool schemas, per-turn memory, and
    session metadata that we can't reconstruct from static files.
    Ceiling: ~70-80% of actual token count captured.
    Upgrade path: read from agent._cached_system_prompt via a context
    engine plugin (v0.2).
    """
    parts = []

    # SOUL.md → identity section
    if soul_md.strip():
        parts.append(soul_md.strip())

    # config.yaml → extract system_message if present
    # Simple heuristic: look for system_message or system_prompt in config
    for line in config_yaml.split("\n"):
        if re.match(r"^\s*(system_message|system_prompt|prompt):\s*['\"]?", line):
            val = re.sub(r"^\s*(system_message|system_prompt|prompt):\s*['\"]?", "", line)
            val = val.strip().rstrip("'\"")
            if val:
                parts.append(val)

    # Skills
    if skill_texts:
        parts.append("\n\n".join(skill_texts))

    # Memory
    if memory_texts:
        parts.append("\n\n".join(memory_texts))

    return "\n\n".join(parts)


# ── Prompt Hash ────────────────────────────────────────────────────────────


def prompt_hash(prompt: str) -> str:
    """SHA-256 of prompt for change detection."""
    return hashlib.sha256(prompt.encode()).hexdigest()


# ── Formatting ────────────────────────────────────────────────────────────


def format_breakdown(result: dict) -> str:
    """Format decomposition result as a plain-text table."""
    lines = []
    lines.append(f"{'Component':<12} {'Tokens':>8} {'Chars':>8} {'%':>8}")
    lines.append("-" * 40)
    for comp in COMPONENT_ORDER:
        info = result["breakdown"][comp]
        pct = (info["tokens"] / max(result["total_tokens"], 1)) * 100
        lines.append(
            f"{comp.capitalize():<12} {info['tokens']:>8} {info['chars']:>8} {pct:>7.1f}%"
        )
    lines.append("-" * 40)
    lines.append(f"{'Total':<12} {result['total_tokens']:>8} {result['total_chars']:>8}")
    lines.append("")
    lines.append(f"Savings estimate: {result['savings_ratio']*100:.0f}%")
    return "\n".join(lines)


def format_drift(drift_results: list[dict]) -> str:
    """Format drift results as a plain-text table."""
    lines = []
    lines.append(f"{'Component':<12} {'Current':>8} {'Baseline':>8} {'Δ%':>8} {'Δ tok':>8} {'Status':<8}")
    lines.append("-" * 56)
    for d in drift_results:
        status = "🔴 BREACH" if d["breached"] else "✅ OK"
        lines.append(
            f"{d['component'].capitalize():<12} {d['current_tokens']:>8} "
            f"{d['baseline_tokens']:>8} {d['delta_pct']:>+7.1f}% "
            f"{d['delta_tokens']:>+8} {status}"
        )
    return "\n".join(lines)
