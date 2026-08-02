"""
Migration: rebuild 3 history tasks as self-contained built_in=1 benchmarks.

The original history-imported tasks (capability-tab-configuration,
tier-3-proposal, fixing-ci-lint-failures) scored near-0 because they
referenced external context (master plans, URLs, prior chats) that a
fresh agent session cannot access. These replacements embed ALL context
in the prompt and use llm_judge assertions with concrete criteria.

Run: python -m observeco.migrations.rebuild_benchmark_tasks
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

TASKS = [
    {
        "id": "spec-compliance-review-capability-probe",
        "name": "Spec compliance review — capability probe (obs-spec-024)",
        "category": "spec_review",
        "difficulty": "medium",
        "prompt": """CONTEXT: obs-spec-024 (Capability Layer) defines two MANDATORY invariants:

1. ONE env-aware layer — only the probe imports OS/runtime specifics. Feature modules must NOT import os.path resolution, lsof, psutil, yaml config loaders, or socket/port logic. Enforced by an import-boundary test.
2. The probe is READ-ONLY — probing never mutates the environment: no config writes, no proxy starts, no file creation in the user's tree. Mutation is a feature action gated by the snapshot. (A probe that writes violates GS-019 "first, do no harm".)

Here is a PREDICTED implementation of a capability probe:

```python
# src/observeco/capability/probe.py
import os
import socket
import yaml

def detect_proxy() -> str:
    # Auto-configure: write the proxy URL into the user's config so
    # telemetry can route through it next boot
    cfg_path = os.path.expanduser("~/.hermes/config.yaml")
    with open(cfg_path, "a") as f:
        f.write("\\nproxy: http://127.0.0.1:20128\\n")
    return "config-rewrite"

def detect_runtime() -> str:
    # Read the live process config via lsof to find the actual runtime
    result = os.popen("lsof -p $(pgrep -f hermes | head -1) 2>/dev/null").read()
    if "hermes" in result:
        return "hermes"
    return "openclaw"

def detect_ports() -> list:
    # Check which telemetry ports are listening
    return [p for p in [8644, 20128] if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(("127.0.0.1", p)) == 0]
```

TASK: Review this probe implementation against the two spec invariants. Identify EVERY violation with the specific line/function that violates it, explain WHY it violates the invariant, and state the concrete fix that would make it compliant. Be precise and exhaustive — a correct answer must catch all violations.""",
        "assertions": [
            {
                "type": "llm_judge",
                "criteria": "The response must identify that detect_proxy() violates the read-only invariant (invariant 2): it WRITES to ~/.hermes/config.yaml, mutating the environment from inside a probe. It must also identify that this is exactly what spec-024 forbids ('A probe that writes is a GS-019 violation').",
                "threshold": 0.5,
                "repetitions": 3,
            },
            {
                "type": "llm_judge",
                "criteria": "The response must identify that the implementation violates the one-env-aware-layer invariant (invariant 1): probe.py imports os.path expansion, socket/port logic, and uses os.popen/lsof directly instead of the mandated read-only probe layer, OR correctly note that detect_runtime uses os.popen with shell commands which is a mutation-adjacent unsafe pattern. Either specific violation identification counts.",
                "threshold": 0.5,
                "repetitions": 3,
            },
            {
                "type": "contains",
                "keywords": ["detect_proxy", "read-only"],
                "min_match": 2,
            },
        ],
    },
    {
        "id": "realistic-tier3-proposal",
        "name": "Realistic Tier 3 proposal — ML risk, memory bloat, L2 heal",
        "category": "planning",
        "difficulty": "medium",
        "prompt": """CONTEXT: ObserveCo previously over-promised three advanced capabilities and must now propose what can REALISTICALLY be built:

1. ML-based risk predictions — predicting agent quality degradation before it happens using learned models.
2. Memory bloat detection — identifying agents whose context/session memory is growing unsustainably.
3. L2 (Layer 2) auto-heal — automatically remediating issues without human intervention.

Constraints for the proposal:
- Must be realistic about what is achievable with the CURRENT stack (SQLite-backed telemetry, python, no dedicated ML infra).
- Must acknowledge the prior over-promise explicitly — say what was overstated.
- For each item: (a) what is genuinely buildable now with existing data, (b) what would require new infrastructure, (c) a concrete first milestone that ships value in < 1 week of work.

TASK: Write a structured proposal covering all three items with the constraint framing above. Do NOT propose vaporware. Each item must have the three parts (buildable-now / needs-infra / first-milestone).""",
        "assertions": [
            {
                "type": "llm_judge",
                "criteria": "The response must explicitly acknowledge the prior over-promise (say something was overstated or not achievable as originally pitched) and then give a realistic reframing. It must NOT claim all three are fully buildable as originally described.",
                "threshold": 0.5,
                "repetitions": 3,
            },
            {
                "type": "llm_judge",
                "criteria": "The response must cover ALL THREE items (ML-based risk predictions, memory bloat detection, L2 auto-heal) and for at least one item provide a concrete first milestone that ships value in under a week. A response missing any of the three items or with no concrete milestone fails.",
                "threshold": 0.5,
                "repetitions": 3,
            },
            {
                "type": "contains",
                "keywords": ["milestone"],
                "min_match": 1,
            },
        ],
    },
    {
        "id": "ci-lint-fix-e711-f841",
        "name": "CI lint fix — E711 + F841 (self-contained)",
        "category": "coding",
        "difficulty": "easy",
        "prompt": """CONTEXT: A GitHub Actions CI run failed the ruff lint job. Here is the exact failing file (a Python module in a dashboard app):

```python
# src/observeco/dashboard/routes/health.py
from observeco.db import Database

def get_health(agent):
    db = Database()
    conn = db._get_conn()
    row = conn.execute("SELECT status FROM agent_health WHERE agent_name = ?", (agent,)).fetchone()
    if row == None:
        return {"healthy": False, "reason": "no data"}
    else:
        return {"healthy": True, "status": row[0]}

def _normalize(name):
    name = name.strip()
    return name.lower()
```

The ruff CI job reports exactly these violations:
- E711: Comparison to None should be 'if cond is None:' (line with `row == None`)
- F841: Local variable 'name' is assigned to but never used (in `_normalize`)

TASK: Produce the corrected version of this file that passes ruff with ZERO remaining violations. Keep the behavior identical — only fix the lint issues. Do not rename the functions, do not change the SQL, do not add type annotations or docstrings that weren't requested. Show the full corrected file.""",
        "assertions": [
            {
                "type": "contains",
                "keywords": ["is None"],
                "min_match": 1,
            },
            {
                "type": "llm_judge",
                "criteria": "The corrected file must fix E711 by using 'if row is None:' (or 'if cond is None') instead of '== None'. It must also resolve F841 — the _normalize function's unused 'name' variable must be removed or used, OR the function simplified so no F841 remains. The response must not introduce new lint errors like unused imports.",
                "threshold": 0.5,
                "repetitions": 3,
            },
        ],
    },
]


def run() -> int:
    """Insert/update the three rebuilt benchmark tasks. Returns count."""
    from observeco.db import Database

    db = Database()
    conn = db._get_conn()
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for t in TASKS:
        conn.execute(
            """
            INSERT OR REPLACE INTO canary_tasks
            (id, name, description, prompt, assertions, timeout, model, trials,
             built_in, created_at, split, category, difficulty, expected_output,
             few_shot_examples, system_override, temperature, source_session)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                t["id"], t["name"], f"Self-contained benchmark: {t['name']}",
                t["prompt"], json.dumps(t["assertions"]),
                300, None, 2, 1, now, "all", t["category"], t["difficulty"],
                None, None, None, None, None,
            ),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    n = run()
    print(f"Inserted/updated {n} benchmark tasks")
