# ObserveCo — Generality Audit v2 (Reconciled)

**Date:** 2026-06-19
**First pass:** Hermes Main (DeepSeek V4 Flash) — 7 categories, 17 findings, product lens
**Second pass:** Claude Code (Claude Sonnet 4) — 10 additional findings + architectural critique
**Cost:** $0.47 (Claude Code, 16 turns, ~124K cache)

**Framing:** ObserveCo as a generic Mac agent observability product. Not our dogfood — anyone's machine.

---

## How the audits compare

| Metric | First pass (Main) | Second pass (Claude Code) |
|--------|-------------------|---------------------------|
| Categories | 7 (A-G) | 10 new findings, 1 architectural critique |
| Coverage | ~40 files | Actual grep of all ~80 files |
| Framing accuracy | Good — product lens correct | Sharpened — inverted architecture thesis |
| Key miss | `seanfzc.ics` literal username, `kepler` in discovery logic, `~/projects/openclaw`, import-time constants trap | — |
| Best insight | "Does the product require Hermes+OpenClaw?" | "Generic discovery should run first; Hermes/Ollama/Claude Code are optional adapters" |

**Overall completeness:** ~60% → **~90%** after reconciliation.

---

## ALL FINDINGS — Consolidated (27 items)

### Category A — Path Assumptions (Blockers — 4 items)

| # | Finding | File:Line | Code | Status | Verdict |
|---|---------|-----------|---|--------|---------|
| **A1** | No `hermes_home()` — 13 files hardcode `~/.hermes` | Multiple (see v1) | `Path.home() / ".hermes" / ...` | **Underestimates scope** ⚠️ | Fix is 2 tickets: add helper + convert `config_scanner.py` constants to lazy (M5) |
| **A2** | No `openclaw_home()` — 7+ files hardcode `~/.openclaw` | `config.py:111`, `db.py:2431,2463`, etc. | `Path.home() / ".openclaw" / ...` | ✅ Captured | Same pattern |
| **A3** | No `init()` — first-run configuration gap | Doesn't exist | — | ✅ Captured | |
| **A4** | `/tmp/openclaw` absolute path | `gateway_monitor.py:46` | `OPENCLAW_LOG_DIR = Path("/tmp/openclaw")` | ✅ Captured | |

### New A items (missed by first pass)

| # | Finding | File:Line | Code | Severity |
|---|---------|-----------|---|---------|
| **A5** | `seanfzc.ics` literal username in filename | `pa_brief_diff.py:100,102` | `HOME / "seanfzc.ics"`, `/tmp/seanfzc_calendar.json` | **BLOCKER** — literal username shipped in code |
| **A6** | `~/projects/openclaw` — developer project directory hardcoded | `clawforge/garden.py:30`, `clawforge/profile.py:54` | `Path.home() / "projects" / "openclaw"` | **BLOCKER** — no one else has this |
| **A7** | `~/AGENTS.md` and `~/SOUL.md` in home root | `config.py:144-145` | `Path.home() / "AGENTS.md"`, `Path.home() / "SOUL.md"` | **BLOCKER** — only on dev's machine |
| **A8** | `config_scanner.py` computes 6 path constants at **import time** — env var override unreliable | `chisel/config_scanner.py:26-31` | Module-level: `HERMES_HOME = Path.home() / ".hermes"` | **ARCHITECTURAL** — makes A1 fix insufficient |

### Category B — Agent Name Assumptions (4 items)

| # | Finding | File:Line | Code | Status |
|---|---------|-----------|---|--------|
| **B1** | `exempted_by: str = "hound"` — production default | `metric_exemptions.py:36,74,116` | Default agent name in governance schema | ✅ Captured |
| **B2** | `demo_agents = ["kepler", "hound"]` — seed data | `clawforge/plugin.py:106` | Names appear in dashboard | ✅ Captured |
| **B3** | 6 phantom agent defaults (`proxy-agent`, etc.) | See v1 | CLI option fallbacks | ✅ Captured |
| **B4** | `"kepler"` special-cased in agent name detection | `config.py:119,152` | `name = "kepler" if "kepler" in soul.read_text().lower() else name` | **MISSED** ⚠️ — detection logic forces name match, not a simple default |

### Category C — Model Assumptions (3 items)

| # | Finding | Detail | Status |
|---|---------|--------|--------|
| **C1** | 6 outdated model defaults in `chisel/llm_client.py` | `deepseek-chat`, `gpt-4o-mini`, etc. | ✅ Captured |
| **C2** | `hermes3:latest` in two compress files + `CAVEMAN_*` namespace (3 env vars, not 1) | `skill_compress.py:94`, `skill_compress_clean.py:117` | **MISSED scope** — `CAVEMAN_OLLAMA_URL`, `CAVEMAN_WORKERS` also undocumented |
| **C3** | `gpt-4o` in `llm_service/__init__.py:296` | Separate subsystem | ✅ Captured |

### Category D — Platform Command Assumptions (2 items)

| # | Finding | Detail | Status |
|---|---------|--------|--------|
| **D1** | `lsof` + `launchctl` macOS-specific | `gateway_monitor.py` | ✅ Captured |
| **D2** | `pgrep` / `ps` format differences | Multiple | **Reason wrong** — `pgrep -f` output is identical on both platforms. Real risk: `pgrep` not installed. ✅ `psutil` recommendation still correct |

### Category E — Framework Assumptions (3 items)

| # | Finding | Detail | Status |
|---|---------|--------|--------|
| **E1** | Framework enum closed — `["hermes", "openclaw", "custom"]` | `capability/probe.py` | ✅ Captured |
| **E2** | 4 fictional OpenClaw plugins in dashboard config | `dashboard/config.py:192-196` | **Underrated** ⚠️ — also hardcodes gateway (port 1234), WhatsApp bridge (8642), iMessage bridge (9120) as DOWN. Should be BLOCKER, not MEDIUM. |
| **E3** | Config schema version locking — 4 parsers, each different | Multiple | ✅ Captured |

### Category F — Port Assumptions (3 items)

| # | Finding | Detail | Status |
|---|---------|--------|--------|
| **F1** | Port 9119 hardcoded in health check | `health.py:200` | ✅ Captured |
| **F2** | Port 4318 in 10 files without shared constant | Multiple | ✅ Captured |
| **F3** | Ports 8080/9119/11434/18789 lack env var overrides | Multiple | ✅ Captured |

### Category G — Discoverability Gaps (2 items)

| # | Finding | Detail | Status |
|---|---------|--------|--------|
| **G1** | Undocumented env vars — 8 total, not 2 | `CAVEMAN_MODEL`, `CAVEMAN_OLLAMA_URL`, `CAVEMAN_WORKERS`, `OBSERVECO_PATHWAY_CRON_DIR`, `OBSERVECO_PATHWAY_SIGNALS_DIR`, `OBSERVECO_PATHWAY_SIGNAL_LIMIT`, `OBSERVECO_MACHINE_ID`, `HERMES_HOME` | **MISSED scope** — counted 2, actual count 8 |
| **G2** | No auto-discovery of install locations | Only knows `~/.hermes` | ✅ Captured |

### New items, no category match

| # | Finding | File:Line | Detail | Severity |
|---|---------|-----------|---|---------|
| **NEW1** | Env var split: `HERMES_HOME` vs `OBSERVECO_HERMES_HOME` | `gateway_monitor.py:41` vs `config.py:29` | Different env var names for the same concept | **HIGH** — no single overridable env var |
| **NEW2** | `~/Library/LaunchAgents` in DB layer | `db.py:2819` | Platform path in data layer, no Linux fallback | **MEDIUM** |
| **NEW3** | Admin key default in source | `billing.py:504` / `commercial_api.py:70` | `_ADMIN_KEY = os.environ.get(..., "observeco-admin-2026")` | **MEDIUM** — security, not generality |
| **NEW4** | LaunchAgent bundle ID namespace covers only 5 prefixes | `config.py:222-223` | `["ai.hermes.", "ai.openclaw.", ...]` — Claude Code, LangGraph, etc. undetected | **LOW** — extends existing E1 |

---

## The One Discovery Gap

**Claude Code.** The product should scan `~/.claude/projects/` at startup — it's a stable, well-documented directory structure on every machine running Claude Code. This single discovery:

1. Eliminates 5 hardcoded assumptions: SOUL.md scan, OpenClaw workspace, "custom" fallback, closed framework enum, demo_agents seeding
2. Discovers all projects automatically without SOUL.md or Hermes config
3. Surfaces real LLM spend per project
4. Maps to users who don't run Hermes at all

---

## Architectural Critique (Claude Code's thesis — I agree)

The product has the architecture inverted. Currently:

**Hermes/OpenClaw → visible. Everything else → invisible.**

It should be:

**Generic discovery (processes, ports, logs, file systems, `~/.claude/`, `ollama list`) → always runs first. Hermes, OpenClaw, Claude Code → optional enrichment adapters that annotate what generic already found.**

Every hardcoded path in the codebase is a symptom of this inverted architecture, not an independent bug. Fixing individual paths without fixing the architecture is patching symptoms.

---

## Prioritised Fix List

### Ship-stoppers (6 items — product cannot function without these)

1. **A5** — `seanfzc.ics` literal username → generic calendar discovery or remove
2. **A6** — `~/projects/openclaw` → generic workspace scan or remove
3. **A7** — `~/AGENTS.md` and `~/SOUL.md` home-root scan → remove, they only exist on dev machine
4. **A8** — `config_scanner.py` import-time path constants → make lazy (required for A1 to work)
5. **E2** — Dashboard shows 4 fake plugins + 3 fake services as DOWN → remove hardcoded entries
6. **A1 + A2** — Add `hermes_home()` + `openclaw_home()` to `dirs.py` with graceful None handling

### High (5 items — blocks external users)

7. **B4** — `"kepler"` special-cased in agent name detection → remove
8. **B1** — `"hound"` as production default exemption author → empty string or auto-detect
9. **G1** — 8 undocumented env vars → `observeco config --help` or single config file
10. **NEW1** — Split `HERMES_HOME` vs `OBSERVECO_HERMES_HOME` → consolidate to one
11. **F1** — Port 9119 health check → read from config, not hardcode

### Medium (5 items — should fix before v1.0)

12. **C2** — `CAVEMAN_*` namespace → rename to `OBSERVECO_*` and document
13. **C1 + C3** — Hardcoded model names → auto-detect via `ollama list`
14. **B2 + B3** — Demo agent names / phantom defaults → empty or "unknown"
15. **D1** — Platform-specific commands → `try/except psutil` pattern
16. **NEW2** — `~/Library/LaunchAgents` in DB layer → platform check

### Low (6 items — track but don't block)

17. **E1** — Closed framework enum → extendable (not urgent if generic discovery runs first)
18. **E3** — Config schema version locking → one shared reader
19. **F2** — Port 4318 shared constant → `dirs.py`
20. **F3** — Port env var overrides → nice to have
21. **D2** — `pgrep` not installed → `psutil` already available
22. **NEW3** — Admin key default → remove from source, document as env var
23. **NEW4** — LaunchAgent bundle ID prefixes → extends E1, not urgent

---

## Summary

| Severity | Count | Key action |
|----------|-------|------------|
| Ship-stopper | 6 | Remove literal usernames, fake plugins, fix import-time trap, add discovery helpers |
| High | 5 | Remove `kepler` special case, `hound` default, consolidate env vars, fix health check |
| Medium | 5 | Document env vars, auto-detect models, clean up defaults |
| Low | 6 | Track but don't block |

**The single most impactful change is architectural: flip the discovery layer so generic scanning runs first and framework-specific adapters enrich it.** This eliminates ~60% of these findings by design.
