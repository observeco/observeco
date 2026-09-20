# Workbench — Spawn-time provenance: per-tool-call capture (final design)

## Why the previous three attempts failed

All three assumed **one session, one repo, knowable at some fixed moment**:
- capture at session creation → CLI-only
- cwd resolver → resolves launch dir, agents work elsewhere
- lazy capture from tool calls → `working_dir` fixed at construction

Each was locally correct and discovered the next layer down. The abstraction
("the session's repo") is wrong. A session launches from home and patches
`~/.hermes/scripts/foo.py`; a delegation session may touch two repos. There is
no single moment at which "the repo" is knowable.

## The design that removes the abstraction

**Capture repo state per file-touching tool call. Append-only, many rows per
session.** For each write:
- touched path
- its enclosing repo root (`git rev-parse --show-toplevel` from the path)
- that repo's HEAD at that moment

Correct by construction — no inference about which repo the session "is in."
Handles multi-repo sessions natively. The pin for a benchmark candidate comes
from the **first write's** repo state, which is exactly what a benchmark needs.

## Kill condition (REGISTERED, per Sean's steer)

**One attempt. If per-tool-call capture does not pass the end-to-end
forge-shape test on the first try, capture is declared infeasible in this
architecture and the conversion measurement question closes with it.**

No fourth angle. The project has pre-registered kill conditions everywhere
except here; this is where one gets added.

## End-to-end test (manufactured today, not a wait)

Spawn a forge-style session deliberately: launch from home, patch a file in
`~/.hermes/scripts/`, confirm:
1. a per-write row lands with the correct repo root (`~/.hermes/scripts`)
2. HEAD is recorded
3. pin-agreement (repo matches the touched path) passes

The three-week wait was partly an artifact of never manufacturing the real
shape. It can be reproduced synthetically today.
