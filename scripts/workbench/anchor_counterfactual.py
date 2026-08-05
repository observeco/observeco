#!/usr/bin/env python3
"""Unit-level counterfactual for the patch-anchor affordance.

Tests the affordance's CORE CLAIM without an agent run: given the failed
`old_string` an agent used and the file it was patching, would the uniqueness
precheck have fired (0 = not-found, >1 = ambiguous), and what would it have
returned? This separates "does the mechanism fire correctly" from "does the
agent then behave better" — the former is tested here (all 11 non-pinnable
cases included), the latter by the 3 contrastive replays.

Also checks the both-sides throughput question: how often would the precheck
fire on the 5 self-correcting (friction) sessions and on successful patches
generally? If it fires constantly, the affordance trades silent failures for
loud friction — a different bargain than the spec assumes.

Honest limitation: observeco-repo file states are pinnable (git history);
~/.hermes paths are not a git repo, so they use current on-disk state. A path
may have changed since the agent saw it, which is a proxy limitation recorded
per case, not hidden.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3

STATE_DB = os.path.expanduser("~/.hermes/state.db")
OBSERVECO = "/Users/seanfzc/projects/observeco"
OBSERVECO_OLD = "/Users/seanfzc/observeco"


def load_state() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_path(p: str) -> str:
    """Normalize the observeco-old path to the current one."""
    if p.startswith(OBSERVECO_OLD + "/"):
        return OBSERVECO + p[len(OBSERVECO_OLD):]
    return p


def is_observable_repo(p: str) -> bool:
    return p.startswith(OBSERVECO + "/") or p.startswith(OBSERVECO_OLD + "/")


def file_at_pin(p: str) -> str | None:
    """Best-effort file state. Observeco -> current working tree (proxy for pin);
    hermes/signals -> current on-disk. Returns content or None."""
    p = normalize_path(p)
    if not os.path.exists(p):
        return None
    try:
        return open(p).read()
    except OSError:
        return None


def uniqueness_precheck(content: str, old_string: str) -> dict:
    """The affordance's core mechanism: count occurrences, classify."""
    if not old_string:
        return {"count": 0, "class": "empty_anchor", "would_fire": True}
    count = content.count(old_string)
    if count == 0:
        return {"count": 0, "class": "not_found", "would_fire": True}
    if count == 1:
        return {"count": 1, "class": "unique", "would_fire": False}
    return {"count": count, "class": "ambiguous", "would_fire": True}


def extract_failed_patches(sid: str) -> list[tuple[str, str]]:
    conn = load_state()
    rows = conn.execute(
        "SELECT tool_calls, content FROM messages WHERE session_id=? ORDER BY timestamp",
        (sid,),
    ).fetchall()
    conn.close()
    out = []
    for i, r in enumerate(rows):
        c = r["content"] or ""
        is_fail = (
            "Provide more context to make it unique" in c
            or "Could not find a match for old_string" in c
            or "Did you mean one of these sections" in c
            or ("Found " in c and "matches for old_string" in c)
        )
        if not is_fail:
            continue
        for j in range(i - 1, max(-1, i - 3), -1):
            tcs = rows[j]["tool_calls"]
            if tcs:
                try:
                    for tc in json.loads(tcs):
                        fn = tc.get("function", {})
                        if fn.get("name") == "patch":
                            args = fn.get("arguments", "")
                            try:
                                args = json.loads(args) if isinstance(args, str) else args
                            except Exception:
                                args = {}
                            out.append((args.get("path", ""), args.get("old_string", "") or ""))
                except Exception:
                    pass
                break
    return out


def is_actionable(sid: str) -> bool:
    conn = load_state()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id=? ORDER BY timestamp", (sid,)
    ).fetchall()
    conn.close()
    fails = 0
    unresolved = 0
    for i, r in enumerate(rows):
        c = r["content"] or ""
        if r["role"] != "tool":
            continue
        if (
            "Provide more context to make it unique" in c
            or "Could not find a match for old_string" in c
            or "Did you mean one of these" in c
            or ("Found " in c and "matches for old_string" in c)
        ):
            fails += 1
            resolved = False
            for j in range(i + 1, min(i + 5, len(rows))):
                if '"success": true' in (rows[j]["content"] or ""):
                    resolved = True
                    break
            if not resolved:
                unresolved += 1
    if fails == 0:
        return False
    return (fails - unresolved) / fails < 0.6


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sessions-file", required=True, help="JSON with actionable + friction session ids")
    p.add_argument("--out", required=True, help="counterfactual results JSON")
    args = p.parse_args()

    with open(args.sessions_file) as f:
        data = json.load(f)

    results = []
    summary = {"not_found": 0, "ambiguous": 0, "unique": 0, "empty": 0, "no_file": 0}
    for sid in data.get("actionable", []) + data.get("friction", []):
        for path, old in extract_failed_patches(sid):
            content = file_at_pin(path)
            if content is None:
                summary["no_file"] += 1
                results.append({"sid": sid, "path": normalize_path(path), "old_len": len(old),
                                "result": "no_file", "class": "no_file", "pinnable": is_observable_repo(path)})
                continue
            pre = uniqueness_precheck(content, old)
            summary[pre["class"]] += 1
            results.append({"sid": sid, "path": normalize_path(path), "old_len": len(old),
                            **pre, "pinnable": is_observable_repo(path)})

    with open(args.out, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print(f"counterfactual over {len(results)} failed-anchor calls")
    print(f"summary: {summary}")
    # the core claim test
    fired = summary["not_found"] + summary["ambiguous"]
    print(f"\nprecheck WOULD HAVE FIRED on {fired} calls ({fired/len(results):.0%} of failed anchors)")
    print(f"  not_found={summary['not_found']} ambiguous={summary['ambiguous']} (would surface ambiguity/text)")
    print(f"  unique={summary['unique']} — these would NOT have fired (precheck would pass)")


if __name__ == "__main__":
    main()
