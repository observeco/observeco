#!/usr/bin/env python3
"""Config hygiene scanner — flags token waste in Hermes config.yaml.

Discovers the same class of findings that saved ~10K tok/session:
- Duplicated prompt sections in channel prompts
- Low prompt cache TTL
- Stale file references in prompts
- Orphaned agent mentions (topics pointing to dead workspaces)

Shares _count_tokens() and YAML utilities from chisel/skill_compress.py.

Usage:
    python3 -m observeco.chisel.config_scanner  # single scan
    python3 -m observeco.chisel.config_scanner --fix  # apply auto-fixable
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Config ──────────────────────────────────────────────────────────────────

HERMES_HOME = Path.home() / ".hermes"
CONFIG_PATH = HERMES_HOME / "config.yaml"
PROFILES_DIR = HERMES_HOME / "profiles"
SKILLS_DIR = HERMES_HOME / "skills"
SIGNALS_DIR = HERMES_HOME / "signals"
INTELLIGENCE_DIR = HERMES_HOME / "intelligence"


# ── Types ───────────────────────────────────────────────────────────────────


@dataclass
class Finding:
    check: str           # name of the check
    severity: str        # "critical" | "warning" | "info"
    description: str     # human-readable summary
    detail: str          # technical detail / recommendation
    estimated_waste_tok: int = 0
    auto_fixable: bool = False
    fix_command: str = ""


@dataclass
class ScanReport:
    config_path: str
    findings: list[Finding] = field(default_factory=list)
    config_health_score: int = 100
    total_waste_tok: int = 0
    scan_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "config_path": self.config_path,
            "config_health_score": self.config_health_score,
            "total_waste_tok": self.total_waste_tok,
            "scan_duration_ms": round(self.scan_duration_ms, 1),
            "findings": [
                {"check": f.check, "severity": f.severity,
                 "description": f.description, "detail": f.detail,
                 "estimated_waste_tok": f.estimated_waste_tok,
                 "auto_fixable": f.auto_fixable}
                for f in self.findings
            ],
        }


# ── Helpers ─────────────────────────────────────────────────────────────────


def _count_tokens(text: str) -> int:
    """Rough token estimate (chars/4). Shared convention with skill_compress.py."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        pass
    return max(1, int(len(text) / 4))


def _load_config(path: Path = CONFIG_PATH) -> Optional[dict]:
    """Load and parse config.yaml. Returns None on failure."""
    if not path.exists():
        return None
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── Checks ──────────────────────────────────────────────────────────────────


def check_duplicate_prompts(cfg: dict) -> list[Finding]:
    """Scan channel_prompts for identical sections >100 chars."""
    findings = []
    channel_prompts = cfg.get("telegram", {}).get("channel_prompts", {})

    if not channel_prompts:
        return findings

    # Collect all prompt bodies as text
    prompt_bodies = {}
    for topic_id, raw_prompt in channel_prompts.items():
        prompt_bodies[str(topic_id)] = raw_prompt

    if len(prompt_bodies) < 2:
        return findings

    # Find common long substrings (duplicated sections)
    # Strategy: split each prompt on double-newlines or markdown headings
    # and count repeated blocks

    # First, find repeated substrings by normalizing whitespace

    # Find the most duplicated section — look for Reasoning Standards block
    rs_pattern = re.compile(
        r"## Reasoning Standards \(Mandatory\).*?(?=## |$)", re.DOTALL
    )
    prompt_count_with_rs = sum(1 for body in prompt_bodies.values()
                               if "Reasoning Standards" in body)
    if prompt_count_with_rs > 1:
        # Calculate waste if they were externalized
        sample_rs = rs_pattern.search(list(prompt_bodies.values())[0])
        rs_tok = 0
        if sample_rs:
            rs_tok = _count_tokens(sample_rs.group(0))
        waste = rs_tok * (prompt_count_with_rs - 1)
        findings.append(Finding(
            check="duplicate_prompts",
            severity="warning",
            description=f"Reasoning Standards boilerplate duplicated in {prompt_count_with_rs} channel prompts",
            detail=f"Duplicated in {prompt_count_with_rs} topics. Move to system_prompt (shared, cached). "
                   f"Saves ~{rs_tok} tok per topic per turn = ~{waste} tok per session.",
            estimated_waste_tok=waste,
            auto_fixable=True,
        ))

    # Check for other duplicated long blocks (>100 chars appearing in 2+ prompts)
    all_paragraphs = {}  # content -> list of topic_ids
    for tid, body in prompt_bodies.items():
        # Split on double newlines or heading boundaries
        paragraphs = re.split(r"\n\s*\n|(?=\n## )", body)
        for para in paragraphs:
            para_clean = re.sub(r"\s+", " ", para).strip()
            if len(para_clean) > 100:
                if para_clean not in all_paragraphs:
                    all_paragraphs[para_clean] = []
                all_paragraphs[para_clean].append(tid)

    for para_text, topic_ids in all_paragraphs.items():
        if len(topic_ids) > 1 and "Reasoning Standards" not in para_text:
            tok = _count_tokens(para_text)
            findings.append(Finding(
                check="duplicate_prompts",
                severity="info",
                description=f"Duplicate paragraph ({tok} tok) found in {len(topic_ids)} topics: {', '.join(topic_ids)}",
                detail=f"\"{para_text[:80]}...\" — appears in topics {', '.join(topic_ids)}",
                estimated_waste_tok=tok * (len(topic_ids) - 1),
            ))

    return findings


def check_cache_ttl(cfg: dict) -> list[Finding]:
    """Flag low prompt cache TTL."""
    findings = []
    cache_ttl = cfg.get("prompt_caching", {}).get("cache_ttl", "5m")

    # Parse TTL string
    ttl_str = str(cache_ttl).lower().strip()
    ttl_minutes = 0

    if ttl_str.endswith("m"):
        ttl_minutes = int(ttl_str[:-1])
    elif ttl_str.endswith("h"):
        ttl_minutes = int(ttl_str[:-1]) * 60
    elif ttl_str.endswith("s"):
        ttl_minutes = int(ttl_str[:-1]) / 60
    else:
        try:
            ttl_minutes = int(ttl_str)
        except ValueError:
            ttl_minutes = 0

    if ttl_minutes < 15:
        cache_hit_rate = min(ttl_minutes / 30.0, 1.0)
        findings.append(Finding(
            check="low_cache_ttl",
            severity="warning" if ttl_minutes < 10 else "info",
            description=f"Prompt cache TTL is {ttl_str} ({ttl_minutes}m) — sessions likely miss cache",
            detail=f"TTL < 15m means gaps >{ttl_minutes}m between turns reset the cache. "
                   f"Recommended: 30m. Estimated cache hit rate: ~{int(cache_hit_rate*100)}% vs "
                   f"~100% at 30m. Each miss costs ~3x on the cached prefix.",
            estimated_waste_tok=2000,
            auto_fixable=True,
            fix_command=f"Set prompt_caching.cache_ttl to 30m in {CONFIG_PATH}",
        ))

    return findings


def check_stale_references(cfg: dict) -> list[Finding]:
    """Check if paths referenced in prompts actually exist on disk."""
    findings = []
    channel_prompts = cfg.get("telegram", {}).get("channel_prompts", {})

    if not channel_prompts:
        return findings

    # Collect all file path references from channel prompts
    path_refs = set()
    for topic_id, raw_prompt in channel_prompts.items():
        for m in re.finditer(r"~?/[\w./\-_]+", raw_prompt):
            path_str = m.group(0)
            if path_str.startswith("~"):
                path_str = str(Path.home()) + path_str[1:]
            if ".hermes" in path_str or "intelligence/" in path_str or "signals/" in path_str:
                path_refs.add(path_str)

    for ref_path in sorted(path_refs):
        p = Path(ref_path)
        exists = p.exists()
        if not exists:
            waste = _count_tokens(ref_path) * 3
            findings.append(Finding(
                check="stale_references",
                severity="warning",
                description=f"Stale path reference in channel prompts: {ref_path}",
                detail=f"Path '{ref_path}' does not exist on disk. Agent following this instruction "
                       f"will encounter a dead end. Recommend updating prompt to point to active path.",
                estimated_waste_tok=waste,
                auto_fixable=False,
            ))

    return findings


def check_orphaned_agents(cfg: dict) -> list[Finding]:
    """Check if channel prompts reference agents with no workspace/profile."""
    findings = []
    channel_prompts = cfg.get("telegram", {}).get("channel_prompts", {})
    profiles_dir = PROFILES_DIR

    # Extract agent names from "You are [Name]" patterns in prompts
    mentioned_agents = set()
    for tid, raw_prompt in channel_prompts.items():
        for m in re.finditer(r"You are (\w+)", raw_prompt):
            name = m.group(1)
            if name not in ("NOT", "the", "an", "a"):
                mentioned_agents.add(name.lower())

    # Known false positives — words that look like agent names but aren't
    NOT_AGENTS = {
        "not", "the", "an", "a", "reliable", "consistent", "hourly",
        "halfway", "honest", "present", "economical", "behind",
    }

    for agent_name in sorted(mentioned_agents):
        if agent_name in NOT_AGENTS:
            continue
        profile_dir = profiles_dir / agent_name
        has_profile = profile_dir.exists()
        has_workspace = (Path.home() / ".openclaw" / "workspace" / f"{agent_name}.md").exists()
        if not has_profile and not has_workspace:
            findings.append(Finding(
                check="orphaned_agents",
                severity="info",
                description=f"Channel prompt references agent '{agent_name}' with no workspace profile",
                detail=f"Mentioned in Telegram channel prompts but no profile found at {profile_dir}. "
                       f"Agent may have been removed or renamed.",
                estimated_waste_tok=50,
                auto_fixable=False,
            ))

    return findings


# ── Scanner ─────────────────────────────────────────────────────────────────


def scan_config(config_path: Path = CONFIG_PATH) -> ScanReport:
    """Run all checks against a Hermes config.yaml. Returns ScanReport."""
    start_ts = time.monotonic()
    report = ScanReport(config_path=str(config_path))

    cfg = _load_config(config_path)
    if cfg is None:
        report.findings.append(Finding(
            check="load_failure",
            severity="critical",
            description=f"Cannot read config at {config_path}",
            detail="File missing, unreadable, or invalid YAML",
        ))
        report.config_health_score = 0
        return report

    # Run all checks
    report.findings.extend(check_duplicate_prompts(cfg))
    report.findings.extend(check_cache_ttl(cfg))
    report.findings.extend(check_stale_references(cfg))
    report.findings.extend(check_orphaned_agents(cfg))

    # Calculate health score
    # Start at 100, deduct for each finding
    deductions = {
        "critical": 25,
        "warning": 10,
        "info": 2,
    }
    for f in report.findings:
        report.config_health_score -= deductions.get(f.severity, 5)
    report.config_health_score = max(0, report.config_health_score)

    report.total_waste_tok = sum(f.estimated_waste_tok for f in report.findings)
    report.scan_duration_ms = (time.monotonic() - start_ts) * 1000

    return report


# ── Fix operations ──────────────────────────────────────────────────────────


def apply_fix(finding: Finding, config_path: Path = CONFIG_PATH) -> bool:
    """Apply an auto-fixable finding. Returns True if successful."""
    if not finding.auto_fixable:
        return False

    cfg = _load_config(config_path)
    if cfg is None:
        return False

    if finding.check == "duplicate_prompts" and "Reasoning Standards" in finding.description:
        channel_prompts = cfg.get("telegram", {}).get("channel_prompts", {})
        if not channel_prompts:
            return False

        rs_pattern = re.compile(r"## Reasoning Standards \(Mandatory\).*", re.DOTALL)
        rs_block = None
        for raw_prompt in channel_prompts.values():
            m = rs_pattern.search(raw_prompt)
            if m:
                rs_block = m.group(0)
                break
        if not rs_block:
            return False

        try:
            raw_text = config_path.read_text(encoding="utf-8")
        except Exception:
            return False

        count_before = raw_text.count("Reasoning Standards (Mandatory)")
        channel_start = raw_text.find("channel_prompts:")
        if channel_start < 0:
            return False
        before_channel = raw_text[:channel_start]
        after_channel = raw_text[channel_start:]
        new_after = re.sub(
            r"(?:\\n)+## Reasoning Standards \(Mandatory\)[^\"\n]*(?:\n\s+\\[^\n]*)*",
            "",
            after_channel,
        )
        new_text = before_channel + new_after
        config_path.write_text(new_text, encoding="utf-8")
        count_after = new_text.count("Reasoning Standards (Mandatory)")
        return count_after < count_before

    if finding.check == "low_cache_ttl":
        try:
            raw_text = config_path.read_text(encoding="utf-8")
        except Exception:
            return False
        new_text = re.sub(
            r"(cache_ttl:\s*)[0-9a-zA-Z]+",
            r"\g<1>30m",
            raw_text,
        )
        if new_text != raw_text:
            config_path.write_text(new_text, encoding="utf-8")
            return True

    return False


# ── CLI entry point ─────────────────────────────────────────────────────────


def run_scan(hermes_home: Optional[str] = None, json_output: bool = False,
             fix: bool = False) -> ScanReport:
    """Run scan and print results. Called from observeco chisel config."""
    global HERMES_HOME, CONFIG_PATH, PROFILES_DIR, SKILLS_DIR, SIGNALS_DIR, INTELLIGENCE_DIR

    if hermes_home:
        HERMES_HOME = Path(hermes_home)
        CONFIG_PATH = HERMES_HOME / "config.yaml"
        PROFILES_DIR = HERMES_HOME / "profiles"
        SKILLS_DIR = HERMES_HOME / "skills"
        SIGNALS_DIR = HERMES_HOME / "signals"
        INTELLIGENCE_DIR = HERMES_HOME / "intelligence"

    report = scan_config(CONFIG_PATH)

    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_report(report)

    if fix:
        auto_fixed = 0
        for f in report.findings:
            if f.auto_fixable:
                success = apply_fix(f, CONFIG_PATH)
                if success:
                    auto_fixed += 1
        if auto_fixed > 0:
            print(f"\n  ✅ Auto-fixed {auto_fixed} finding(s). Re-run scan to verify.")

    return report


def _print_report(report: ScanReport) -> None:
    """Print a human-readable scan report."""
    print(f"\n🔍 Config Hygiene Scan — {report.config_path}")
    print(f"  Health score: {report.config_health_score}/100")
    print(f"  Estimated token waste: {report.total_waste_tok} tok/session")
    if report.findings:
        print(f"  Findings: {len(report.findings)}")
        for i, f in enumerate(report.findings, 1):
            severity_icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(f.severity, "?")
            fixable = " [auto-fixable]" if f.auto_fixable else ""
            waste = f" (~{f.estimated_waste_tok} tok/session)" if f.estimated_waste_tok else ""
            print(f"\n  {i}. {severity_icon} [{f.severity.upper()}]{fixable}{waste}")
            print(f"     {f.description}")
            print(f"     {f.detail}")
    else:
        print("\n  ✅ No issues found.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Config hygiene scanner")
    parser.add_argument("--hermes-home", help="Custom Hermes home path")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--fix", action="store_true", help="Apply auto-fixable findings")
    args = parser.parse_args()

    run_scan(
        hermes_home=args.hermes_home,
        json_output=args.json,
        fix=args.fix,
    )
