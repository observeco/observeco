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
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from observeco.dirs import hermes_home

# ── Lazy path accessors (call-time, not import-time) ──────────────────

def _hermes_home() -> Path | None:
    return hermes_home()

def _config_path() -> Path | None:
    hh = hermes_home()
    return hh / "config.yaml" if hh else None

def _profiles_dir() -> Path | None:
    hh = hermes_home()
    return hh / "profiles" if hh else None

def _skills_dir() -> Path | None:
    hh = hermes_home()
    return hh / "skills" if hh else None

def _signals_dir() -> Path | None:
    hh = hermes_home()
    return hh / "signals" if hh else None

def _intelligence_dir() -> Path | None:
    hh = hermes_home()
    return hh / "intelligence" if hh else None


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


def _load_config(path: Path | None = None) -> Optional[dict]:
    """Load and parse config.yaml. Returns None on failure."""
    if path is None:
        p = _config_path()
        if p is None:
            return None
        path = p
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
                auto_fixable=True,
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
            fix_command=f"Set prompt_caching.cache_ttl to 30m in config.yaml",
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
                auto_fixable=True,
            ))

    return findings


def check_orphaned_agents(cfg: dict) -> list[Finding]:
    """Check if channel prompts reference agents with no workspace/profile."""
    findings = []
    channel_prompts = cfg.get("telegram", {}).get("channel_prompts", {})
    pd = _profiles_dir()
    if pd is None:
        return findings
    profiles_dir = pd

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
        has_workspace = False
        from observeco.dirs import openclaw_home
        oc = openclaw_home()
        if oc is not None:
            has_workspace = (oc / "workspace" / f"{agent_name}.md").exists()
        if not has_profile and not has_workspace:
            findings.append(Finding(
                check="orphaned_agents",
                severity="info",
                description=f"Channel prompt references agent '{agent_name}' with no workspace profile",
                detail=f"Mentioned in Telegram channel prompts but no profile found at {profile_dir}. "
                       f"Agent may have been removed or renamed.",
                estimated_waste_tok=50,
                auto_fixable=True,
            ))

    return findings


# ── Scanner ─────────────────────────────────────────────────────────────────


def scan_config(config_path: Path | None = None) -> ScanReport:
    """Run all checks against a Hermes config.yaml. Returns ScanReport."""
    if config_path is None:
        cp = _config_path()
        if cp is None:
            return ScanReport(config_path="(none)")
        config_path = cp
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


def _dump_yaml_safe(cfg: dict, config_path: Path) -> bool:
    """Write config dict back to YAML. Returns True on success."""
    try:
        import yaml
        text = yaml.dump(cfg, default_flow_style=False, allow_unicode=True, sort_keys=False)
        config_path.write_text(text, encoding="utf-8")
        return True
    except Exception:
        return False


def apply_fix(finding: Finding, config_path: Path | None = None) -> bool:
    """Apply an auto-fixable finding. Returns True if successful."""
    if config_path is None:
        cp = _config_path()
        if cp is None:
            return False
        config_path = cp
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

        # Step 1: Check if RS already exists in system_prompt
        sys_start = raw_text.find("system_prompt:")
        channel_start = raw_text.find("channel_prompts:")
        if sys_start < 0 or channel_start < 0:
            return False

        between_sys_channel = raw_text[sys_start:channel_start]
        has_rs_in_sys = "Reasoning Standards" in between_sys_channel

        # Step 2: Remove RS blocks from ALL channel prompt text
        after_channel = raw_text[channel_start:]
        new_after = re.sub(
            r"(?:\\n)+## Reasoning Standards \(Mandatory\)[^\"\n]*(?:\n\s+\\[^\n]*)*",
            "",
            after_channel,
        )

        # Step 3: If RS not in system_prompt yet, prepend it
        if not has_rs_in_sys:
            before_sys = raw_text[:sys_start]
            # Find the system_prompt content start (after the "system_prompt: |" line)
            sys_value_start = raw_text.find("|", sys_start)
            if sys_value_start < 0:
                sys_value_start = sys_start + len("system_prompt:")
            # Insert RS into system_prompt — add it before the first actual content line
            # Find the first non-empty line of the system_prompt value
            sys_body = raw_text[sys_value_start + 1:channel_start]
            # Prepend RS block (with a separator comment) before existing system prompt content
            nl = "\n"
            rs_as_indent = nl + rs_block.replace(nl, nl + "  ")  # indent for YAML block scalar
            new_sys_body = rs_as_indent + "\n" + sys_body
            before_sys = raw_text[:sys_value_start + 1]
            new_text = before_sys + new_sys_body + new_after
        else:
            before_channel = raw_text[:channel_start]
            new_text = before_channel + new_after

        config_path.write_text(new_text, encoding="utf-8")
        count_after = new_text.count("Reasoning Standards (Mandatory)")
        return count_after == 1  # exactly one copy, in system_prompt

    if finding.check == "duplicate_prompts" and "Reasoning Standards" not in finding.description:
        # Generic duplicate: remove redundant paragraphs from the smaller topic's prompt
        # Uses yaml.safe_load + dict manipulation + yaml.dump (safe, no raw-text regex)
        channel_prompts = cfg.get("telegram", {}).get("channel_prompts", {})
        if not channel_prompts or len(channel_prompts) < 2:
            return False

        import re as _re

        # Parse the topic IDs from the finding description
        m = _re.search(r"found in \d+ topics: ([\d, -]+)", finding.description)
        if not m:
            return False
        topic_ids_raw = [t.strip() for t in m.group(1).split(",")]

        # Normalize to match YAML-parsed keys (integers)
        topic_ids = []
        for tid in topic_ids_raw:
            try:
                topic_ids.append(int(tid))
            except ValueError:
                topic_ids.append(tid)

        # Find the shared paragraph prefix from the detail
        detail_m = _re.search(r'"(.+?)"', finding.detail)
        if not detail_m:
            return False
        para_prefix = detail_m.group(1)

        # Find which topic has the least content (remove from the smaller one)
        topic_sizes = {}
        for tid in topic_ids:
            prompt = channel_prompts.get(tid, channel_prompts.get(str(tid), ""))
            topic_sizes[tid] = len(prompt)

        keep_topic = max(topic_sizes, key=lambda k: topic_sizes[k])

        # Modify the parsed dict (safe — no raw-text regex)
        changed = False
        for tid in topic_ids:
            if tid == keep_topic:
                continue

            prompt = channel_prompts.get(tid, channel_prompts.get(str(tid), ""))
            if not prompt:
                continue

            # Find the paragraph in this prompt and remove it
            paragraphs = _re.split(r'\n(?=\n## )|\n\n', prompt)
            new_paragraphs = []
            removed = False
            for para in paragraphs:
                normalized = _re.sub(r'\s+', ' ', para).strip()
                if not removed and para_prefix[:40] in normalized and len(normalized) > 100:
                    removed = True
                    continue
                new_paragraphs.append(para)

            if removed:
                cfg['telegram']['channel_prompts'][tid] = '\n\n'.join(new_paragraphs)
                changed = True

        if changed:
            return _dump_yaml_safe(cfg, config_path)
        return False

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

    if finding.check == "stale_references":
        # Try to auto-correct the stale path by finding a valid alternative
        try:
            raw_text = config_path.read_text(encoding="utf-8")
        except Exception:
            return False

        path_match = __import__("re").search(r"stale path[^:]*: ([^\n]+)", finding.description.lower())
        if not path_match:
            return False
        stale_path = path_match.group(1).strip()

        # Try to find a valid path by checking common alternatives
        stale_p = Path(stale_path)
        alternatives = []
        # Check without "~/" prefix
        if stale_path.startswith("~/"):
            alternatives.append(Path.home() / stale_path[2:])
        # Check intelligence/ subdirs
        parts = stale_p.parts
        for i, p in enumerate(parts):
            if p in ("intelligence", "signals"):
                sub = Path(*parts[i:])
                alt = Path.home() / ".hermes" / sub
                if alt.exists():
                    alternatives.append(alt)
        # Check if parent exists and just filename changed
        if stale_p.parent.exists():
            for child in stale_p.parent.iterdir():
                if child.suffix == stale_p.suffix:
                    alternatives.append(child)

        alternative_paths = [p for p in alternatives if p.exists()]
        if alternative_paths:
            replacement = str(alternative_paths[0])
            new_text = raw_text.replace(stale_path, replacement)
            if new_text != raw_text:
                config_path.write_text(new_text, encoding="utf-8")
                return True

        # If no alternative found, flag with suggestion in the description
        return False

    if finding.check == "orphaned_agents":
        # Remove orphan agent identity lines from channel prompts
        # Uses yaml.safe_load + dict manipulation + yaml.dump (safe, no raw-text regex)
        agent_match = __import__("re").search(r"'(\w+)' with no workspace profile", finding.description)
        if not agent_match:
            return False
        agent_name = agent_match.group(1)

        import re as _re

        channel_prompts = cfg.get('telegram', {}).get('channel_prompts', {})
        if not channel_prompts:
            return False

        changed = False
        for tid in list(channel_prompts.keys()):
            prompt = channel_prompts[tid]
            if not prompt or agent_name.lower() not in prompt.lower():
                continue
            # Remove "You are {agent_name} ..." identity paragraphs
            paragraphs = prompt.split('\n\n')
            new_paragraphs = []
            for para in paragraphs:
                if _re.search(rf'You are {_re.escape(agent_name)}[\s]', para, _re.IGNORECASE):
                    changed = True
                    continue
                new_paragraphs.append(para)
            if changed:
                cfg['telegram']['channel_prompts'][tid] = '\n\n'.join(new_paragraphs)

        if changed:
            return _dump_yaml_safe(cfg, config_path)
        return False

    return False


# ── CLI entry point ─────────────────────────────────────────────────────────


def run_scan(hermes_home_path: Optional[str] = None, json_output: bool = False,
             fix: bool = False) -> ScanReport:
    """Run scan and print results. Called from observeco chisel config."""
    if hermes_home_path:
        # Override env var so lazy accessors pick it up
        os.environ["OBSERVECO_HERMES_HOME"] = hermes_home_path

    report = scan_config()

    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_report(report)

    if fix:
        auto_fixed = 0
        for f in report.findings:
            if f.auto_fixable:
                success = apply_fix(f)
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
