# ObserveCo Development Workflow

## Branch Strategy

```
main ──●──●──●──●── (stable, bug-fix-only)
        \     \     \
         spec/<name>    spec/<name>    spec/<name>
```

- **`main`** = stable release. Only bug fixes and completed specs land here.
- **`spec/<name>`** = one branch per spec/feature, branched from `main`.
- Bug fixes go to `main` first → rebase your spec branch to pick them up.
- Merge spec → `main` only when tests pass and you'd ship it.

## Commands

```bash
# Start a new spec
git checkout main
git pull
git checkout -b spec/analysis-layer

# Pick up bug fixes from main
git checkout spec/analysis-layer
git rebase main

# Merge completed spec to main
git checkout main
git merge spec/analysis-layer
git push origin main
```

## Running Two Instances Side by Side

Each spec branch gets its own data directory and port:

```bash
# Instance A — spec/analysis-layer, port 9119
OBSERVECO_HOME=~/.observeco-spec-a observeco dashboard --port 9119

# Instance B — spec/auto-heal-ui, port 9120
OBSERVECO_HOME=~/.observeco-spec-b observeco dashboard --port 9120
```

Each gets its own SQLite DB, config, and agent registry. No cross-contamination.

## Testing

```bash
# Run tests for current branch
uv run pytest tests/ -v --tb=short

# Run tests with isolated data dir (matches CI)
OBSERVECO_HOME=/tmp/observeco-test uv run pytest tests/ -v --tb=short
```

## CI

All three workflows run on every push to any branch:
- **CI** — 8 matrix runners (Python 3.10–3.13, ubuntu + macos)
- **Master Fidelity Gate** — import check + first-run audit
- **First-Run Audit** — clean install + dashboard smoke test

Green CI is the gate to merge.
