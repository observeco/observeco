# ObserveCo

> Observability for local AI agents. Tells you if your agents are working, what they're doing, and where your money goes.

## Architecture

- **FastAPI** backend with **htmx** single-pane dashboard
- **SQLite** data layer (`observeco.db`, `pulse.db`) via SQLAlchemy
- **Jinja2** templates in `src/observeco/dashboard/templates/`
- **Chart.js** for dashboard charts (inline JS in templates)
- **Proxy server** (`src/observeco/proxy/`) — captures LLM API calls for cost tracking
- **Chisel** (`src/observeco/chisel/`) — drift detection (5 components: identity, skills, memory, tools, guidance)
- **Tracking** (`src/observeco/tracking/`) — token analytics, time-series aggregation
- **Pulse** (`src/observeco/pulse/`) — agent health monitoring
- **Auth** (`src/observeco/auth/`) — license/trial gating, SSO
- **CLI** entry point: `observeco` (typer-based, `src/observeco/cli/`)

## Key Commands

- `uv run observeco dashboard` — start dashboard on :8123
- `uv run observeco dashboard --port 8123` — explicit port
- `uv run pytest tests/ -v --tb=short` — run tests
- `uv run pytest tests/ -v -k "test_name"` — run specific test
- `uv run ruff check src/observeco/` — lint
- `uv run python src/observeco/proxy/server.py --port 9200` — start cloud proxy
- `uv run python src/observeco/proxy/server.py --port 9201 --upstream http://localhost:11434` — start local proxy

## Code Standards

- Python 3.10+, line-length 100
- Ruff linting: E, F, W, I (ignore E501)
- Black formatting (line-length 100)
- Type hints on all public functions
- Docstrings in triple-quote format
- Tests in `tests/` with pytest
- No wildcard imports
- `scripts/*`, `specs/scripts/*`, `tests/*`, `docs/*` get E402 ignored (imports after sys.path)

## Key Conventions

- **Dashboard routes** in `src/observeco/dashboard/server.py` — FastAPI + htmx endpoints
- **Data layer** in `src/observeco/db.py` — all SQLAlchemy queries
- **Token data** uses `token_history` table (daily snapshots) for fleet-wide trends, NOT `token_logs` (raw per-turn)
- **Drift** averages across all 5 components per agent per run
- **License gating** via `require_pro()` — test with Pro key `OBS-PRO-3A03F984-6BA898`
- **Billing** records saved BEFORE `start_trial()` in `billing.json`
- **Email** via Resend, sender `noreply@observeco.com`, 9 HTML templates, fire-and-forget daemon threads
- **Specs** in `specs/` — master plan at `specs/observeco-master-plan.md`
- **Dashboard color system** defined in spec §5, layout in §6

## Project Structure

```
src/observeco/
  adapters/     — external integrations
  alerts/       — notification system
  auth/         — license/trial/SSO
  chisel/       — drift detection
  clawforge/    — agent registry
  cli/          — CLI entry point
  dashboard/    — FastAPI server + templates + static
  doctor/       — health checks
  emails/       — email templates
  gate/         — feature gating
  graph/        — knowledge graph
  heal/         — auto-remediation
  lifecycle/    — agent lifecycle
  llm_service/  — LLM interaction layer
  probe/        — agent probing
  proxy/        — LLM API proxy for cost tracking
  pulse/        — health monitoring
  tracking/     — token analytics + SDK
```

## Test Patterns

- `pytest tests/ -v --tb=short` for quick feedback
- `pytest tests/ -v -m "not slow"` to skip slow tests
- `pytest tests/ -v -m integration` for integration tests
- `pytest tests/ -v -m license` for license gating tests
- Tests use `conftest.py` which adds `src/` to sys.path
