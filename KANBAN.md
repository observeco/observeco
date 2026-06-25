# ObserveCo Kanban Board

**Board:** P0 Hardening (2026-06-18)
**Source:** Claude cross-assessment + playbook audit — 6 spec'd fail-safes to build

---

## ✅ Phase 1 Complete — Code Hardening (6 items)

| # | Task | Status | Verification |
|---|------|--------|-------------|
| P0-1 | **Lazy Database() init** — wrap `Database()` in lazy decorator | ✅ Done | `ruff clean` |
| P0-2 | **Wrap replace_process import** — non-Hermes users don't crash | ✅ Done | `ruff clean` |
| P0-3 | **Annotate bare `except: pass`** — 20+ blocks with logging + ponytail | ✅ Done | `ruff clean` |
| P0-4 | **Wire require_pro() to invocation counter** | ✅ Done | `uv run python src/observeco/invocation_counter.py` |
| P0-5 | **Verify watch daemon after launch** — 3s poll + retry | ✅ Done | `uv run python tests/test_watch_heartbeat_selfcheck.py` |
| P0-6 | **Unify auth secret init** — single init, no race | ✅ Done | `ruff clean` |

---

## 🔴 Phase 2 — Spec'd P0 Fail-Safes (Build Now)

| # | Task | Spec | Status | Build Command |
|---|------|------|--------|---------------|
| P0-7 | **Process supervision** — launchd/systemd auto-restart, PID-file fallback with crash-loop protection | §17.1 | □ To do | `claude -p "Build process supervision"` |
| P0-8 | **Startup validation** — 5 checks with structured error messages, FATAL vs WARNING | §17.2 | □ To do | `claude -p "Build startup validation"` |
| P0-9 | **Stale data per-metric** — `last_updated` on all time-series endpoints, `renderStaleness()` JS | §17.3 | □ To do | `claude -p "Build stale data detection"` |
| P0-10 | **Disk space management** — pre-write check with WAL awareness, auto-resume, 30s cache | §17.4 | □ To do | `claude -p "Build disk space management"` |
| P0-11 | **Data integrity verification** — `PRAGMA integrity_check`/`quick_check`, degraded mode, foreign key check | §17.5 | □ To do | `claude -p "Build data integrity verification"` |
| P0-12 | **Self-monitoring** — heartbeat with PID/cycle_count, corruption handling, `observeco status` | §17.6 | □ To do | `claude -p "Build self-monitoring"` |

---

## 🟡 P1 — Build Soon

| # | Task | Status | Notes |
|---|------|--------|-------|
| P1-1 | Config file permission validation | □ To do | Warn if `~/.observeco/` or `pulse.db` world-readable |
| P1-2 | Event deduplication on daemon restart | □ To do | Idempotency key on pulse_log |
| P1-3 | WAL checkpoint management | □ To do | `PRAGMA wal_autocheckpoint` on long-running daemon |
| P1-4 | `observeco doctor` self-check | □ To do | First-run validation wizard |
| P1-5 | Degraded mode (read-only dashboard) | □ To do | Dashboard serves cached data on DB corruption |

---

## 🔵 P2 — Post-Launch

| # | Task | Notes |
|---|------|-------|
| P2-1 | Audit trail for sensitive operations | Who killed an agent, changed config |

---

## 🟢 P3 — Ecosystem Gap Scanner (`observeco discover`)

| # | Task | Status | Notes |
|---|------|--------|-------|
| D-1 | **Scanner module** — scan cron jobs (`jobs.json`), agent configs (profiles, config.yaml), running processes (`psutil`), cross-ref DB | ✅ Done | `src/observeco/discover/scanner.py` |
| D-2 | **Discover API** — `GET /api/discover/gaps` (cached 5min) + `POST /api/discover/add` (register gap as agent) | ✅ Done | `src/observeco/discover/api.py` |
| D-3 | **Wire into server.py** — `include_router(discover_router)` | ✅ Done | Single line in `server.py` |
| D-4 | **Dashboard widget** — badge in header with gap count, expandable list with Add buttons, auto-load on page load | ✅ Done | htmx-free JS widget in `index.html` |
| D-5 | **Smoke test** — verify API returns gaps, Add registers agent, badge updates | ✅ Done | TestClient: GET 200 (87 gaps), POST 200 (registered), POST 409 (duplicate) |
| D-6 | **Process filter tuning** — refine `NOT_AGENTS` list to avoid false positives on macOS | ✅ Done | 2 clean process gaps (Ollama, llama-server) |
| D-7 | **Health check on add** — each gap includes `health_check` (e.g. `pgrep -f ollama`), passed through API to `register_agent()`. Pulse probes it immediately. | ✅ Done | scanner → API → JS → DB → pulse probe chain verified |
| P2-2 | API key leak detection in logs | Scan for `sk-...`, `OBS-PRO-...` |
| P2-3 | Transactional boundaries for multi-table writes | pulse_log + errors atomic |
| P2-4 | Graceful shutdown timeout enforcement | SIGTERM → 5s → SIGKILL |
| P2-5 | Timezone handling policy | All UTC, convert only in UI |
| P2-6 | File descriptor leak detection | Monitor open FD count in long-running daemon |
| P2-7 | Session Intelligence Layer (#57-63) | Post-launch features |
| P2-8 | Token Rogue Guardrails | Phase G1-G3 |
| P2-9 | Full reconciler framework | Extract after standalone modules proven |

---

## Process

1. **Build:** `ponytail:` tags on shortcuts, runnable self-check on non-trivial logic
2. **Verify:** `ruff check src/observeco/` clean, self-checks pass
3. **Audit:** coding-fidelity-playbook.md, test-guard.md, master-fidelity-gate.md
4. **Report:** Completion summary to Sean
