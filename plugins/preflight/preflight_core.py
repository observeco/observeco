"""preflight_core — Context quality scoring. Zero external deps.

7 criteria from arxiv 2607.14275 ("AI Agents Do Not Fail Alone"),
adapted from ProofAgent (Bousetouane, U Chicago / ProofAgent.ai).

Our contribution: runtime integration, trending, baseline enforcement.
The 7-criteria construct is cited, not ours.

Regex-only pass. LLM pass deferred to v0.2 (requires API key).
Each criterion scored 0-10. Overall: Strong (≥8), Adequate (≥5), Weak (<5).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

# ── Paths ──────────────────────────────────────────────────────────────────

HERMES_HOME = Path.home() / ".hermes"
CONFIG_PATH = HERMES_HOME / "config.yaml"
SOUL_PATH = HERMES_HOME / "SOUL.md"


# ── Prompt loading ─────────────────────────────────────────────────────────


def load_system_prompt() -> str:
    """Extract system_prompt from config.yaml (best-effort regex)."""
    if not CONFIG_PATH.exists():
        return ""
    text = CONFIG_PATH.read_text(encoding="utf-8")
    m = re.search(r"system_prompt:\s*'(.*?)'(?:\s*\n\s*\w)", text, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"system_prompt:\s*'(.*)", text, re.DOTALL)
    if m:
        return m.group(1).rsplit("\n", 1)[0] if "\n" in m.group(1) else m.group(1)
    return ""


def load_soul() -> str:
    if SOUL_PATH.exists():
        return SOUL_PATH.read_text(encoding="utf-8")
    return ""


def _extract_section(prompt: str, section_name: str) -> str:
    """Extract a section by its ## heading."""
    pattern = rf"^\s*##\s*{re.escape(section_name)}\b.*?(?=^\s*##\s|\Z)"
    m = re.search(pattern, prompt, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return m.group(0).strip() if m else ""


# ── Pass 1: Regex checks (structural) ──────────────────────────────────────


def _regex_role_clarity(prompt: str, soul: str) -> Tuple[int, list, list]:
    score = 0
    evidence = []
    findings = []
    checks = [
        (r"\b(?:I am|You are)\s+\w+", "Has agent identity"),
        (r"\b(?:role|identity|persona)\b", "Has role definition"),
        (r"\b(?:scope|boundar|limit|within)\b", "Has scope boundaries"),
        (r"\b(?:success|goal|objective|purpose)\b", "Has success criteria"),
        (r"\b(?:output|response|format|deliverable)\b", "Has output contract"),
    ]
    for pattern, finding in checks:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 2
            evidence.append(finding)
        else:
            findings.append(f"Missing: {finding}")
    if soul:
        score += 1
        evidence.append("SOUL.md provides additional identity context")
    return min(score, 10), evidence, findings


def _regex_guardrail_coverage(prompt: str) -> Tuple[int, list, list]:
    score = 0
    evidence = []
    findings = []
    checks = [
        (r"## Refusal Rules", "Has dedicated refusal rules section"),
        (r"escalat", "Has escalation path"),
        (r"\b(?:PII|personal|private|sensitive)\b", "Has PII handling rules"),
        (r"\b(?:safety|unsafe|dangerous|harmful)\b", "Has safety boundaries"),
        (r"\b(?:restrict|forbid|prohibit|must not|cannot)\b", "Has restricted actions"),
        (r"\b(?:confirm|approval|permission|consent)\b", "Has confirmation requirements"),
    ]
    for pattern, finding in checks:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 1.5
            evidence.append(finding)
        else:
            findings.append(f"Missing: {finding}")
    refusals = re.findall(r"\b(?:refuse|refusal)\b", prompt, re.IGNORECASE)
    if len(refusals) >= 3:
        score += 1
        evidence.append(f"{len(refusals)} refusal mentions")
    return min(score, 10), evidence, findings


def _regex_instruction_consistency(prompt: str) -> Tuple[int, list, list]:
    score = 5
    evidence = []
    findings = []
    sections = re.findall(r"^\s*##\s+(.+)", prompt, re.MULTILINE)
    if len(sections) >= 5:
        score += 2
        evidence.append(f"{len(sections)} organized sections")
    else:
        findings.append(f"Only {len(sections)} sections — may lack structure")
    if re.search(r"\b(?:precedence|priority|override|trump|hierarchy)\b", prompt, re.IGNORECASE):
        score += 2
        evidence.append("Has precedence/priority rules")
    else:
        findings.append("Missing precedence rules")
    if "TRUST BOUNDARY" in prompt:
        score += 1
        evidence.append("Trust boundary markers present")
    return min(score, 10), evidence, findings


def _regex_tool_schema_quality(prompt: str) -> Tuple[int, list, list]:
    score = 0
    evidence = []
    findings = []
    checks = [
        (r"side.effect|read_only|read_write|destructive", "Has tool side-effect classification"),
        (r"tool.use|tool.call|when to use", "Has tool-use guidance"),
        (r"classify.command|context.dependent", "Has terminal command classification"),
        (r"\b(?:error|fail|exception|timeout)\b", "Has error handling guidance"),
    ]
    for pattern, finding in checks:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 2.5
            evidence.append(finding)
        else:
            findings.append(f"Missing: {finding}")
    return min(score, 10), evidence, findings


def _regex_grounding_sufficiency(prompt: str) -> Tuple[int, list, list]:
    score = 0
    evidence = []
    findings = []
    checks = [
        (r"cite its source|MUST cite", "Requires source citation"),
        (r"unverified", "Labels unverified claims"),
        (r"\b(?:ground|evidence|source|reference|provenance)\b", "Has grounding rules"),
        (r"\b(?:memory|recall|session.search|persistent)\b", "Has memory/recall grounding"),
    ]
    for pattern, finding in checks:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 2.5
            evidence.append(finding)
        else:
            findings.append(f"Missing: {finding}")
    return min(score, 10), evidence, findings


def _regex_injection_hardening(prompt: str) -> Tuple[int, list, list]:
    score = 0
    evidence = []
    findings = []
    checks = [
        (r"TRUST BOUNDARY", "Has trust boundary markers"),
        (r"TRUSTED and MUST NOT", "Has instruction hierarchy"),
        (r"UNTRUSTED CONTENT", "Labels untrusted content"),
        (r"## Refusal Rules", "Has refusal rules"),
        (r"DATA, not instruction", "Explicitly states content is data"),
    ]
    for pattern, finding in checks:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 2
            evidence.append(finding)
        else:
            findings.append(f"Missing: {finding}")
    return min(score, 10), evidence, findings


def _regex_token_efficiency(prompt: str) -> Tuple[int, list, list]:
    score = 5
    evidence = []
    findings = []
    char_count = len(prompt)
    if char_count < 500:
        findings.append(f"Very short ({char_count} chars) — may lack detail")
        score -= 2
    elif char_count > 50000:
        findings.append(f"Very long ({char_count} chars) — likely bloated")
        score -= 2
    else:
        score += 2
        evidence.append(f"Reasonable length ({char_count} chars)")
    # Check for repeated boilerplate
    lines = prompt.split("\n")
    seen = set()
    duplicates = 0
    for line in lines:
        stripped = line.strip().lower()
        if len(stripped) > 30 and stripped in seen:
            duplicates += 1
        seen.add(stripped)
    if duplicates > 5:
        score -= 2
        findings.append(f"{duplicates} duplicate lines (>30 chars)")
    elif duplicates == 0:
        score += 1
        evidence.append("No significant duplication")
    return max(0, min(score, 10)), evidence, findings


# ── Score combination ──────────────────────────────────────────────────────


def score_prompt(prompt: str = "", soul: str = "") -> dict:
    """Run all 7 regex checks and return scored result.

    Args:
        prompt: System prompt text (auto-loaded if empty)
        soul: SOUL.md text (auto-loaded if empty)
    Returns:
        dict with overall_score, grade, criteria list
    """
    if not prompt:
        prompt = load_system_prompt()
    if not soul:
        soul = load_soul()

    if not prompt:
        return {"error": "Could not load system prompt"}

    criteria_defs = [
        ("role_clarity", "Role Clarity",
         lambda p, s: _regex_role_clarity(p, s)),
        ("guardrail_coverage", "Guardrail Coverage",
         lambda p, s: _regex_guardrail_coverage(p)),
        ("instruction_consistency", "Instruction Consistency",
         lambda p, s: _regex_instruction_consistency(p)),
        ("tool_schema_quality", "Tool Schema Quality",
         lambda p, s: _regex_tool_schema_quality(p)),
        ("grounding_sufficiency", "Grounding Sufficiency",
         lambda p, s: _regex_grounding_sufficiency(p)),
        ("injection_hardening", "Injection Hardening",
         lambda p, s: _regex_injection_hardening(p)),
        ("token_efficiency", "Token Efficiency",
         lambda p, s: _regex_token_efficiency(p)),
    ]

    results = []
    total = 0.0
    for key, name, regex_fn in criteria_defs:
        score, evidence, findings = regex_fn(prompt, soul)
        total += score
        results.append({
            "key": key,
            "name": name,
            "score": score,
            "evidence": "; ".join(evidence),
            "findings": findings,
        })

    overall = total / len(criteria_defs)
    grade = "Strong" if overall >= 8 else "Adequate" if overall >= 5 else "Weak"

    return {
        "overall_score": round(overall, 1),
        "grade": grade,
        "criteria": results,
        "prompt_chars": len(prompt),
        "soul_present": bool(soul),
        "source": "arxiv 2607.14275 (Bousetouane, ProofAgent.ai)",
    }


# ── Formatting ──────────────────────────────────────────────────────────────


def format_report(result: dict) -> str:
    """Format the preflight result as a readable report."""
    if "error" in result:
        return f"Error: {result['error']}"

    lines = [
        "=" * 60,
        "  CONTEXT-QUALITY PREFLIGHT REPORT",
        f"  {result.get('source', 'arxiv 2607.14275')}",
        "=" * 60,
        "",
        f"  Overall: {result['overall_score']}/10 — {result['grade']}",
        f"  Prompt: {result['prompt_chars']:,} chars  |  SOUL.md: {'yes' if result['soul_present'] else 'no'}",
        "",
    ]
    for c in result["criteria"]:
        bar = "█" * int(c["score"]) + "░" * (10 - int(c["score"]))
        lines.append(f"  {c['name']:<25} {bar} {c['score']:.0f}/10")
        if c["evidence"]:
            lines.append(f"    ✅ {c['evidence'][:70]}")
        for f in c["findings"][:2]:
            lines.append(f"    ❌ {f[:70]}")
    lines.append("=" * 60)
    return "\n".join(lines)