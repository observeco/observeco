#!/usr/bin/env python3
"""Golden-master snapshot: capture current rendered HTML for every Phase 1 endpoint.

Run with the project venv:
    .venv/bin/python3 .refactor/snapshot.py

Output: .refactor/golden/<slug>.html + golden/index.json
The index is the contract: verify.py re-hits the same URLs and diffs.
"""
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error

BASE_DIR = "/Users/seanfzc/observeco"
GOLDEN = os.path.join(BASE_DIR, ".refactor", "golden")
SERVER = "http://127.0.0.1:8897"

sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from observeco.dashboard.server import _dash_secret as TOKEN  # noqa: E402

# Endpoints with side effects or non-deterministic heavy work — never snapshot,
# verify manually after conversion.
MANUAL_VERIFY = {
    "/api/trigger-heal",      # GET but triggers heal diagnoses
    "/api/l2-scan",           # may trigger L2 analysis
    "/api/pathway-scan",      # may trigger scan
    "/api/check-drift-alerts",
}

# Query-param combos to snapshot per endpoint ("" = no params)
PARAM_MAP = {
    "/api/fleet/agents": ["", "?sort=status", "?sort=name", "?sort=cost", "?sort=drift", "?sort=tokens"],
    "/api/analytics/tokens": ["", "?days=1", "?days=30", "?hours=1"],
    "/api/capability/page": ["?agent=default"],
    "/api/capability/drift/chart": ["?agent=default"],
    "/api/capability/grid/table": ["?agent=default"],
    "/api/capability/timeline/events": ["?agent=default"],
    "/api/agent-detail/{agent_name}": ["?tab=health"],
}

def slug(endpoint, query):
    s = endpoint.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    if query:
        q = query.lstrip("?").replace("=", "-").replace("&", "_")
        s += "__" + q
    return s or "root"

def agent_names():
    from observeco.db import Database
    d = Database()
    return [a["agent_name"] for a in d.get_agents()]

def first_task_id():
    from observeco.db import Database
    d = Database()
    try:
        rows = d._get_conn().execute("SELECT id FROM canary_tasks LIMIT 1").fetchall()
        return rows[0]["id"] if rows else None
    except Exception:
        return None

def resolve_path(endpoint, agents, task_id):
    """Fill path params with real values. Returns None if unresolvable."""
    if "{agent_name}" in endpoint or "{name}" in endpoint:
        if not agents:
            return None
        return endpoint.replace("{agent_name}", agents[0]).replace("{name}", agents[0])
    if "{topic}" in endpoint:
        return endpoint.replace("{topic}", "auto-heal")
    if "{task_id}" in endpoint:
        return endpoint.replace("{task_id}", task_id) if task_id else None
    if "{feature_id}" in endpoint:
        return endpoint.replace("{feature_id}", "auto-heal")
    if "{run_id}" in endpoint or "{snapshot_id}" in endpoint:
        return None  # no stable fixture — skip
    return endpoint

def fetch(url):
    req = urllib.request.Request(url, headers={"X-ObserveCo-Token": TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", e.read()
    except Exception as e:
        return 0, "", str(e).encode()

def main():
    os.makedirs(GOLDEN, exist_ok=True)
    manifest = json.load(open(os.path.join(BASE_DIR, ".refactor", "manifest.json")))
    agents = agent_names()
    task_id = first_task_id()
    index = []
    for chunk in manifest["work"]:
        ep = chunk["endpoint"]
        if ep in MANUAL_VERIFY:
            index.append({"chunk": chunk["chunk_id"], "endpoint": ep, "skipped": "manual-verify"})
            continue
        queries = PARAM_MAP.get(ep, [""])
        for q in queries:
            resolved = resolve_path(ep, agents, task_id)
            if resolved is None:
                index.append({"chunk": chunk["chunk_id"], "endpoint": ep, "skipped": "no-fixture"})
                break
            url = SERVER + resolved + q
            status, ctype, body = fetch(url)
            sl = slug(resolved, q)
            entry = {
                "chunk": chunk["chunk_id"], "endpoint": resolved, "query": q,
                "url": resolved + q, "status": status, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest()[:16],
                "file": sl + ".html",
            }
            if status == 200 and body:
                with open(os.path.join(GOLDEN, sl + ".html"), "wb") as f:
                    f.write(body)
            else:
                entry["no_golden"] = True
            index.append(entry)
            print(f"{'OK ' if status == 200 else '!! '}{status} {resolved + q} ({len(body)}b)")
    with open(os.path.join(GOLDEN, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    ok = sum(1 for e in index if e.get("status") == 200)
    print(f"\n{ok}/{len(index)} snapshots golden. Index: {GOLDEN}/index.json")

if __name__ == "__main__":
    main()
