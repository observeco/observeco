"""CLI commands for the Context Quality Preflight plugin."""

from __future__ import annotations

import argparse
import json
import sys

from .preflight_core import score_prompt, format_report, load_system_prompt, load_soul


def register_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="preflight_action")

    scan_p = subs.add_parser("scan", help="Score context quality")
    scan_p.add_argument("--json", action="store_true", help="Output as JSON")

    subparser.set_defaults(func=preflight_command)


def preflight_command(args: argparse.Namespace) -> int:
    action = getattr(args, "preflight_action", None)
    if not action:
        print("Usage: hermes preflight {scan}")
        return 2

    try:
        if action == "scan":
            return _cmd_scan(args)
        else:
            print(f"Unknown preflight action: {action}")
            return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_scan(args) -> int:
    prompt = load_system_prompt()
    soul = load_soul()
    if not prompt:
        print("Could not load system prompt from config.yaml")
        return 1

    result = score_prompt(prompt, soul)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))

    return 0 if result.get("grade") != "Weak" else 1