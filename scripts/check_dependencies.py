#!/usr/bin/env python3
"""Dependency freshness check — runs pip-audit, outputs only if vulnerabilities found."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from watchdog_flag_writer import write_flag


def main():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json", "--output", "-"],
            capture_output=True, text=True, timeout=120,
            cwd="/Users/seanfzc/projects/observeco",
        )
    except FileNotFoundError:
        # pip-audit not installed — try safety
        try:
            result = subprocess.run(
                [sys.executable, "-m", "safety", "check", "--json"],
                capture_output=True, text=True, timeout=120,
                cwd="/Users/seanfzc/projects/observeco",
            )
        except FileNotFoundError:
            print("⚠️ DEPENDENCY CHECK: Neither pip-audit nor safety installed. Run: pip install pip-audit")
            return

    except subprocess.TimeoutExpired:
        print("⚠️ DEPENDENCY CHECK: Timed out after 120s")
        return

    output = result.stdout.strip()
    if not output:
        # No vulnerabilities — silent
        return

    try:
        data = json.loads(output)
        # pip-audit returns list of {name, version, vulns: [...]}
        # But can also return bare dict/str in edge cases
        if not isinstance(data, list):
            return  # no vulns or unexpected format — silent
        vulns = [d for d in data if d.get("vulns")]
        if not vulns:
            return  # clean

        lines = ["🔒 DEPENDENCY VULNERABILITIES", ""]
        for pkg in vulns:
            lines.append(f"  • {pkg['name']}=={pkg['version']}")
            for v in pkg["vulns"]:
                vid = v.get("id", "unknown")
                fix = v.get("fix_versions", ["no fix"])[0] if v.get("fix_versions") else "no fix"
                lines.append(f"    {vid} → fix: {fix}")
        lines.append("")
        lines.append("Run: cd /Users/seanfzc/projects/observeco && pip-audit")
        print("\n".join(lines))

        # Write flag for Hound
        write_flag(
            source="check_dependencies",
            severity="critical",
            summary=f"{len(vulns)} packages with known vulnerabilities",
            investigation_type="security",
            context={
                "vulnerable_packages": [
                    {"name": d["name"], "version": d["version"],
                     "vulns": [{"id": v.get("id"), "fix": v.get("fix_versions", ["no fix"])[0] if v.get("fix_versions") else "no fix"} for v in d.get("vulns", [])]}
                    for d in vulns
                ],
            },
            proposed_action=(
                f"Assess {len(vulns)} vulnerable packages. "
                f"Packages with available fixes should be updated. "
                f"Packages without fixes need risk assessment."
            ),
        )

    except (json.JSONDecodeError, KeyError):
        # Non-JSON output — surface raw if it looks like findings
        if "vulnerab" in output.lower() or "found" in output.lower():
            print(f"🔒 DEPENDENCY CHECK:\n{output[:500]}")


if __name__ == "__main__":
    main()
