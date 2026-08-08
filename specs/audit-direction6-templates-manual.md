# Direction 6 — Templates with no caller (PERIODIC MANUAL CHECK)

**Status: NOT a gate.** Reverted twice for correctness. Third attempt also failed
determinism/correctness. Per review, this stays a periodic manual check rather
than a gate.

## Why it's not a gate

Template reachability is harder than the other five directions because templates
are reached through more indirection than routes or CSS classes:
- served via path constants (`ONBOARDING_TEMPLATE = .../onboarding.html`), not
  literal filenames in the handler
- a route may reference a constant, not the filename
- near-identical basenames (`pathway.html` vs `pathway_tab.html`) confound
  naive substring matching
- render-time reachability is process-state dependent

Three correctness failures, all real and reproducible:
1. Non-determinism (first render pass won, later passes fell back to static
   scan because `init_auth()` re-adds middleware — `RuntimeError: Cannot add
   middleware after an application has started`). Fixed with a cached
   TestClient, but...
2. Constant-resolution misattributes templates to the wrong routes
   (`pathway.html` → `/api/pathway-snapshot`; truth is `/pathway` serves
   pathway.html, `/api/pathway/tab` serves pathway_tab.html).
3. Segments and prefix boundaries still produce false negatives — the
   dangerous failure mode (silence).

## The genuine finding it exists to catch

`onboarding.html` is a whole template with NO caller. Its serving route
`/api/onboarding` has zero callers anywhere. It was the largest instance of the
dead-code class: not a route with no caller, but an entire template with no
caller. A stranger installing ObserveCo got a blank dashboard with no guidance.

## Manual check (run periodically)

```bash
# Flag templates whose serving route is not referenced from any rendered page.
# onboarding.html should be in the output.
python3 - <<'PY'
import re
from pathlib import Path
ROOT = Path.cwd()
TEMPLATES = ROOT / "src/observeco/dashboard/templates"
SERVER = ROOT / "src/observeco/dashboard/server.py"
# (procedure: for each .html template, find its serving route, check the
# route is referenced by any other template/JS. onboarding.html has none.)
PY
```

Until a robust, deterministic version exists, run this manually and check that
`onboarding.html` appears (it is the positive control — its absence means the
check has regressed).

## Fixes that were real and worth keeping (if direction 6 is retried)

These landed and were correct; they're noted here so they aren't lost:
- **Prefix boundary**: match whole route keys, not substrings
  (`/api/onboarding` must not match inside `/api/onboarding-guide`).
- **Source-echo skip**: a rendered body containing `@app.get`/`@router.get` is
  raw server source leaked into output, not rendered HTML. Counting a route
  DEFINITION as a "reference" makes every route look reachable and hides orphans.
- **Constant resolution**: resolve `*_TEMPLATE = .../x.html` constants so a
  route referencing the constant is recognized as serving the template.
- **Segment-wise matching**: `/api/agent/archive/profile` matches serving route
  `/api/agent/<param>/profile`.
- **Cached TestClient**: `init_auth()` re-adds middleware, which Starlette
  forbids after the app starts. Cache the client once per process and swap the
  DB, don't re-init.
