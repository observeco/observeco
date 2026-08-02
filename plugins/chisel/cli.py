"""CLI commands for the Chisel plugin.

Registered via register_cli(subparser) — auto-discovered by Hermes'
plugin CLI discovery mechanism.
"""

from __future__ import annotations

import argparse
import json
import time
import sys

from .chisel_core import (
    COMPONENT_ORDER,
    decompose,
    format_breakdown,
    format_drift,
    prompt_hash,
)
from .chisel_cut import (
    apply_cuts,
    format_cut_result,
    format_suggestions,
    format_verify_result,
    rule_hash,
    suggest,
)
from . import (
    get_all_agents,
    get_drift_log,
    get_last_cut,
    get_last_trim_time,
    get_recent_trims,
    get_trim_before_cut,
    get_trims_since,
    get_verified_rules,
    read_system_prompt,
    store_cut,
    store_trim,
    store_drift,
    update_cut_verified,
    check_drift,
)


def register_cli(subparser: argparse.ArgumentParser) -> None:
    """Register chisel subcommands."""
    subs = subparser.add_subparsers(dest="chisel_action")

    # trim
    trim_p = subs.add_parser("trim", help="Decompose system prompt into 5 components")
    trim_p.add_argument("--agent", default="main", help="Agent name (default: main)")
    trim_p.add_argument("--json", action="store_true", help="Output as JSON")

    # drift
    drift_p = subs.add_parser("drift", help="Show drift report for an agent")
    drift_p.add_argument("--agent", default="", help="Agent name (default: all agents)")

    # trend
    trend_p = subs.add_parser("trend", help="Show historical trend for an agent")
    trend_p.add_argument("--agent", required=True, help="Agent name")
    trend_p.add_argument("--days", type=int, default=30, help="Days of history (default: 30)")

    # baseline
    baseline_p = subs.add_parser("baseline", help="Set or check baseline")
    baseline_p.add_argument("--agent", default="main", help="Agent name (default: main)")
    baseline_p.add_argument("--check", action="store_true", help="Check against baseline (exit 1 if drift > threshold)")

    # ── v0.2: Suggest + Cut + Verify ──

    # suggest
    suggest_p = subs.add_parser("suggest", help="Suggest what can be cut from the system prompt")
    suggest_p.add_argument("--agent", default="main", help="Agent name (default: main)")

    # cut
    cut_p = subs.add_parser("cut", help="Cut redundant/stale content from the system prompt")
    cut_p.add_argument("--agent", default="main", help="Agent name (default: main)")
    cut_p.add_argument("--apply", action="store_true", help="Apply cuts (default: dry-run only)")

    # verify
    verify_p = subs.add_parser("verify", help="Verify last cut — re-trim and confirm savings")
    verify_p.add_argument("--agent", default="main", help="Agent name (default: main)")

    subparser.set_defaults(func=chisel_command)


def chisel_command(args: argparse.Namespace) -> int:
    """Dispatch chisel commands."""
    action = getattr(args, "chisel_action", None)
    if not action:
        print("Usage: hermes chisel {trim|drift|trend|baseline|suggest|cut|verify}")
        return 2

    try:
        if action == "trim":
            return _cmd_trim(args)
        elif action == "drift":
            return _cmd_drift(args)
        elif action == "trend":
            return _cmd_trend(args)
        elif action == "baseline":
            return _cmd_baseline(args)
        elif action == "suggest":
            return _cmd_suggest(args)
        elif action == "cut":
            return _cmd_cut(args)
        elif action == "verify":
            return _cmd_verify(args)
        else:
            print(f"Unknown chisel action: {action}")
            return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_trim(args) -> int:
    """Decompose system prompt and show breakdown."""
    agent = args.agent
    prompt = read_system_prompt(agent)

    if not prompt or len(prompt) < 100:
        print(f"Assembled system prompt is only {len(prompt)} chars. "
              "This may indicate a minimal config. Check config.yaml and SOUL.md.")
        # Still produce a breakdown (even if all zeros)
        if not prompt:
            prompt = ""

    result = decompose(prompt)
    store_trim(agent, result, prompt)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Chisel Trim — {agent}")
        print(f"Prompt hash: {prompt_hash(prompt)[:16]}...")
        print()
        print(format_breakdown(result))

    return 0


def _cmd_drift(args) -> int:
    """Show drift report for one or all agents."""
    agents = [args.agent] if args.agent else get_all_agents()

    if not agents:
        print("No trim data found. Run `hermes chisel trim` to establish a baseline.")
        return 0

    for agent in agents:
        recent = get_recent_trims(agent, limit=50)
        if len(recent) < 2:
            print(f"{agent}: Need at least 2 trim snapshots to calculate drift "
                  f"(have: {len(recent)}). Run `hermes chisel trim` to collect more data.")
            continue

        # Compute 7-day rolling average
        now = time.time()
        week_ago = now - 7 * 86400
        week_entries = [r for r in recent if r["timestamp"] >= week_ago]
        if not week_entries:
            week_entries = recent

        baseline = {
            "identity_tokens": sum(r["identity_tokens"] for r in week_entries) // len(week_entries),
            "skills_tokens": sum(r["skills_tokens"] for r in week_entries) // len(week_entries),
            "memory_tokens": sum(r["memory_tokens"] for r in week_entries) // len(week_entries),
            "tools_tokens": sum(r["tools_tokens"] for r in week_entries) // len(week_entries),
            "guidance_tokens": sum(r["guidance_tokens"] for r in week_entries) // len(week_entries),
            "total_tokens": sum(r["total_tokens"] for r in week_entries) // len(week_entries),
        }

        latest = recent[0]
        drift_results = []
        for comp in COMPONENT_ORDER:
            key = f"{comp}_tokens"
            cur_val = latest[key]
            base_val = baseline[key]
            delta_pct, delta_tokens, breached = check_drift(cur_val, base_val)
            drift_results.append({
                "component": comp,
                "current_tokens": cur_val,
                "baseline_tokens": base_val,
                "delta_pct": round(delta_pct, 1),
                "delta_tokens": delta_tokens,
                "breached": breached,
            })

        print(f"Chisel Drift — {agent}")
        print(f"Window: 7-day rolling average ({len(week_entries)} snapshots)")
        print()
        print(format_drift(drift_results))
        print()

    return 0


def _cmd_trend(args) -> int:
    """Show historical trend for an agent."""
    agent = args.agent
    days = max(1, min(args.days, 365))
    since = time.time() - days * 86400

    entries = get_trims_since(agent, since)
    if not entries:
        print(f"No trim data for {agent} in the last {days} days.")
        return 0

    print(f"Chisel Trend — {agent} (last {days} days, {len(entries)} snapshots)")
    print()
    print(f"{'Date':<16} {'Identity':>8} {'Skills':>8} {'Memory':>8} {'Tools':>8} {'Guidance':>8} {'Total':>8}")
    print("-" * 72)
    for e in entries:
        from datetime import datetime
        dt = datetime.fromtimestamp(e["timestamp"])
        date_str = dt.strftime("%Y-%m-%d %H:%M")
        print(
            f"{date_str:<16} {e['identity_tokens']:>8} {e['skills_tokens']:>8} "
            f"{e['memory_tokens']:>8} {e['tools_tokens']:>8} {e['guidance_tokens']:>8} "
            f"{e['total_tokens']:>8}"
        )

    return 0


def _cmd_baseline(args) -> int:
    """Set or check baseline."""
    agent = args.agent

    if args.check:
        # Check mode: compare current against baseline
        from . import _get_db
        db = _get_db()
        try:
            row = db.execute(
                "SELECT identity_tokens, skills_tokens, memory_tokens, tools_tokens, "
                "guidance_tokens, total_tokens FROM baseline WHERE agent_name = ?",
                (agent,),
            ).fetchone()
        finally:
            db.close()

        if not row:
            print(f"No baseline set for {agent}. Run `hermes chisel baseline --agent {agent}` to set one.")
            return 1

        baseline = {
            "identity_tokens": row[0],
            "skills_tokens": row[1],
            "memory_tokens": row[2],
            "tools_tokens": row[3],
            "guidance_tokens": row[4],
            "total_tokens": row[5],
        }

        prompt = read_system_prompt(agent)
        if not prompt:
            print(f"Cannot read system prompt for {agent}.")
            return 1

        current = decompose(prompt)
        any_breach = False
        for comp in COMPONENT_ORDER:
            key = f"{comp}_tokens"
            _, _, breached = check_drift(current[key], baseline[key])
            if breached:
                print(f"🔴 {comp}: {current[key]} vs baseline {baseline[key]} — BREACH")
                any_breach = True

        if any_breach:
            return 1
        print(f"✅ {agent}: all components within threshold vs baseline")
        return 0

    # Set mode: store current composition as baseline
    prompt = read_system_prompt(agent)
    if not prompt:
        print(f"Cannot read system prompt for {agent}.")
        return 1

    result = decompose(prompt)
    from . import _get_db
    db = _get_db()
    try:
        db.execute(
            """INSERT OR REPLACE INTO baseline
               (agent_name, identity_tokens, skills_tokens, memory_tokens,
                tools_tokens, guidance_tokens, total_tokens, set_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent, result["identity_tokens"], result["skills_tokens"],
                result["memory_tokens"], result["tools_tokens"],
                result["guidance_tokens"], result["total_tokens"],
                time.time(),
            ),
        )
        db.commit()
    finally:
        db.close()

    print(f"Baseline set for {agent}: {result['total_tokens']} total tokens")
    return 0


# ── v0.2: Suggest ─────────────────────────────────────────────────────────


def _cmd_suggest(args) -> int:
    """Suggest what can be cut from the system prompt."""
    agent = args.agent
    prompt = read_system_prompt(agent)

    if not prompt or len(prompt) < 100:
        print(f"Assembled system prompt is only {len(prompt)} chars. "
              "This may indicate a minimal config. Check config.yaml and SOUL.md.")
        return 0

    from pathlib import Path
    skills_dir = Path.home() / ".hermes" / "skills"
    suggestions = suggest(prompt, skills_dir)

    # Check for previously verified rules
    verified = get_verified_rules(agent)
    for s in suggestions:
        if s["type"] == "duplicate_rule":
            h = rule_hash(s["line"])
            if h in verified:
                s["previously_verified"] = True

    print(f"Chisel Suggest — {agent}")
    print()
    print(format_suggestions(suggestions))

    verified_count = sum(1 for s in suggestions if s.get("previously_verified"))
    if verified_count:
        print(f"  ({verified_count} items previously verified safe)")

    return 0


# ── v0.2: Cut ─────────────────────────────────────────────────────────────


def _cmd_cut(args) -> int:
    """Cut redundant/stale content from the system prompt."""
    agent = args.agent
    prompt = read_system_prompt(agent)

    if not prompt or len(prompt) < 100:
        print(f"Assembled system prompt is only {len(prompt)} chars. "
              "This may indicate a minimal config. Check config.yaml and SOUL.md.")
        return 0

    # Run suggest automatically if no suggestions were pre-computed
    from pathlib import Path
    skills_dir = Path.home() / ".hermes" / "skills"
    suggestions = suggest(prompt, skills_dir)

    if not suggestions:
        print("No cuttable items found. Your prompt is already lean.")
        return 0

    # Find the SOUL.md file
    soul_path = Path.home() / ".hermes" / "SOUL.md"
    if not soul_path.exists():
        print(f"SOUL.md not found at {soul_path}")
        return 1

    result = apply_cuts(str(soul_path), suggestions, apply=args.apply)

    if args.apply:
        # Log the cut
        details = json.dumps([s for s in suggestions if s["type"] in ("duplicate_rule", "stale_ref")])
        store_cut(
            agent_name=agent,
            file_path=str(soul_path),
            cut_type="full",
            tokens_before=result["before_tokens"],
            tokens_after=result["after_tokens"],
            backup_path=result.get("backup", ""),
            details=details,
        )

    print(format_cut_result(result))
    return 0


# ── v0.2: Verify ──────────────────────────────────────────────────────────


def _cmd_verify(args) -> int:
    """Verify last cut — re-trim and confirm savings."""
    agent = args.agent

    last_cut = get_last_cut(agent)
    if not last_cut:
        print("No cuts to verify. Run `hermes chisel cut --apply` first.")
        return 0

    # Re-read the file and decompose
    prompt = read_system_prompt(agent)
    if not prompt:
        print(f"Cannot read system prompt for {agent}.")
        return 1

    result = decompose(prompt)
    store_trim(agent, result, prompt)

    # Compare against pre-cut trim
    pre_cut = get_trim_before_cut(agent, last_cut["timestamp"])
    if not pre_cut:
        print("Cannot verify — no pre-cut trim snapshot found. "
              "The cut was applied but there's no baseline to compare against.")
        return 0

    saved = pre_cut["total_tokens"] - result["total_tokens"]
    verified_status = 1 if saved > 0 else -1
    update_cut_verified(last_cut["id"], verified_status)

    verify_result = {
        "status": "verified" if verified_status == 1 else "regression",
        "tokens_before": pre_cut["total_tokens"],
        "tokens_after": result["total_tokens"],
        "tokens_saved": saved,
    }
    print(format_verify_result(verify_result))
    return 0 if verified_status == 1 else 1
