# ObserveCo: Expectations Gap Document

**Date:** 2026-06-17
**Author:** Main
**Status:** As of 2026-06-17 — under review, gaps may now be resolved
**Next step:** 6 P0 items added to KANBAN.md — execute those before launch

## 2026-06-17 Update — 6 P0 Items (Claude Cross-Assessment)

Independent external review identified 6 items that cause Day-1 trust erosion:

| P0 | Item | Source | What Happens |
|----|------|--------|-------------|
| **1** | **Database() import-time crash** | server.py:48 | First install = dashboard crashes with raw traceback if data dir missing |
| **2** | **replace_process import crash** | server.py:6157 | Non-Hermes users can't start dashboard |
| **3** | **50+ bare `except: pass` blocks** | Across codebase | Every error is invisible. User has zero debug path. |
| **4** | **require_pro() is a no-op** | license.py:987-989 | Pricing model promises 5/day cap that doesn't exist |
| **5** | **Watch daemon not verified after launch** | server.py:6088-6094 | "Let's find your agents" shown when daemon is dead |
| **6** | **Auth secret init race** | server.py:77 vs 6117 | Intermittent auth failures with no explanation |

**Tracked in:** `KANBAN.md` (P0 section). Each item uses ponytail shortcuts, runnable self-checks, and passes the relevant playbook audits.

---

## The Gap Statement

> **"If kanban is empty, we are good to launch."**

This assumption is **false** in the current setup. The kanban board tracked 14 build tasks (pulse, chisel, clawforge, dashboard, infra). All 14 are done. The code exists and tests pass.

But `kanban empty ≠ launch ready`. Launch readiness requires a completely different set of deliverables that were never captured as kanban tasks.

## Why This Happened

The kanban board is a **work tracker** — it tracks what someone decided to work on. It does NOT automatically represent the full launch checklist. The 14 tasks were extracted from `unified-dashboard.md` and `execution-plan.md` specs, but the spec's own Phase Zero checklist (D-28, D-21, D-14, D-7, D-3, D-0) was never converted to kanban tasks.

The consequence: code was built, but the path to user's machine was never completed.

## The 13 Gaps Between "Code Written" and "Launch Ready"

### 🔴 CRITICAL GAPS (Block launch)

| # | Gap | Detail | Owner |
|---|-----|--------|-------|
| **G1** | **PyPI name squatted** | `observeco` returns 200 on pypi.org. If someone else published, we need a different name. If it's a stale placeholder we can claim, we need to act. | Main |
| **G2** | **No CI/CD pipeline** | Zero `.github/workflows/` files. No automated lint, test, build, publish on push or tag. Cannot ship reliably without this. | Main |
| **G3** | **GitHub org blocked** | observeco GitHub org created but `seanfzc` not added as owner. Cannot push the monorepo, cannot manage releases, cannot create the public repo. | Sean (only org admin can add) |
| **G4** | **Stripe not live** | Billing code exists with simulated mode. No real Stripe keys configured. No webhook endpoint exposed on a public URL. No checkout flow tested end-to-end. | Main |
| **G5** | **observeco.ai not registered** | `observeco.io` is registered (Cloudflare). `observeco.ai` returns NXDOMAIN. At ~$70+/yr (`.ai` registry requires 2-year minimum at ~$35-70/yr), this needs a decision before launch day. | Sean (domain owner) |

### 🟡 HIGH PRIORITY GAPS (Launch quality)

| # | Gap | Detail | Owner |
|---|-----|--------|-------|
| **G6** | **README is 38 lines** | Spec calls for a polished README with hero, demo GIF, badges, dogfood story, highlights, quick start, "why not X" table, roadmap. Current state is barely a skeleton. | Main |
| **G7** | **No launch assets** | No logo (SVG), no banner image (1280×640 GH social preview), no terminal GIF demo. Spec says D-14 deadline for all three. | Main |
| **G8** | **Single test file, no integration tests** | 10 tests in 1 file (`test_cli.py`). No tests for dashboard, billing, auto_detect, clawforge modules. No `pip install` from clean env test. No cross-OS tests. | Main |
| **G9** | **No beta testers recruited** | Spec requires 5–10 external testers before HN launch. Zero recruited. No beta invite mechanism exists. | Main |
| **G10** | **No distribution material drafted** | No HN post, no Reddit posts, no X thread drafted. Spec says D-1 deadline. Without this, launch day is silent. | Main |

### 🔵 LAUNCH POLISH (Can ship post-launch but better to have)

| # | Gap | Detail | Owner |
|---|-----|--------|-------|
| **G11** | **Competitor "why not X" page** | The spec has a table. The code/docs don't have a rendered version. Needed for README and docs site. | Main |
| **G12** | **ObserveCo.io landing page** | Domain is parked. No landing page redirecting to GitHub/README. | Main |
| **G13** | **Dashboard tested on clean install** | Dashboard was built but never tested from `pip install observeco[dashboard]` in a clean macOS/Linux VM. | Main |

## The Fix

These gaps must be tracked as kanban tasks with `kw-obslaunch-` prefix. Each gap is atomic and can be worked independently. G1–G5 block launch. G6–G10 define launch quality. G11–G13 are polish.

**Kanban must change its contract:** going forward, every major spec MUST have its full launch checklist converted to kanban tasks, not just the build tasks. "All build tasks done" is a status update. "All launch tasks done" is a launch gate.

---

*This document is the source of truth for the expectations gap. When a gap is resolved, mark it here with resolution date.*

---

## 2026-06-18 Update — Missing Observability Fail-Safes

Independent analysis identified 15 fail-safes that typical observability solutions (Datadog, Grafana, New Relic, Sentry) provide but ObserveCo doesn't. Ranked by trust-erosion severity.

| # | Fail-Safe | Severity | Partially Covered? | Notes |
|---|-----------|----------|--------------------|-------|
| **1** | **Process supervision** — launchd/systemd integration, auto-restart on crash/reboot | **P0** | ❌ Not spec'd | Daemon dies silently. No auto-restart. |
| **2** | **Startup validation** — verify deps (DB, ports, config) with clear error messages | **P0** | ❌ Not spec'd | Raw traceback if data dir missing. |
| **3** | **Stale data detection per-metric** — every chart shows "last updated X ago" | **P0** | ⚠️ Partial — global banner exists (§8.4 of obs-spec-023) but no per-metric staleness | User can't tell which metric is stale. |
| **4** | **Disk space management** — monitor before write, alert before filling disk | **P0** | ⚠️ Partial — spec'd in obs-spec-023 §7.3/§8.1 but not implemented | Zero runtime disk checks. |
| **5** | **Data integrity verification** — SQLite PRAGMA integrity_check, schema validation, WAL recovery | **P0** | ❌ Not spec'd | No integrity checks on startup. |
| **6** | **Self-monitoring / Meta-monitoring** — daemon heartbeat, cycle counter, escalation if ticking stops | **P0** | ⚠️ Partial — heartbeat file exists (§9.3 of obs-spec-023) but no meta-monitor that escalates | If daemon stops, no one escalates. |
| **7** | **Bounded data retention** — configurable policy with clear what-gets-dropped-when rules | **P1** | ⚠️ Partial — spec'd in obs-spec-023 §7.4 but not implemented | Unbounded growth in practice. |
| **8** | **Graceful degradation under load** — drop samples rather than crash when overwhelmed | **P1** | ❌ Not spec'd | No backpressure mechanism. |
| **9** | **Upgrade safety** — migration verification, pre-upgrade health checks, rollback | **P1** | ⚠️ Partial — spec'd in obs-spec-023 §10 but not implemented | No upgrade mechanism exists. |
| **10** | **Configuration validation** — validate config on startup, warn about invalid values | **P1** | ❌ Not spec'd | Invalid config values pass silently. |
| **11** | **Health endpoint** — expose /health or /ready for external monitoring | **P1** | ⚠️ Partial — spec'd in obs-spec-023 §8 but not implemented | No endpoint exists. |
| **12** | **Structured logging** — consistent log levels, structured output | **P1** | ❌ Not spec'd | Mix of print() and logger.warning(). |
| **13** | **Backup/restore** — export/import or backup mechanisms | **P2** | ⚠️ Partial — spec'd in obs-spec-023 §7.2/§7.3 but not implemented | No backup mechanism exists. |
| **14** | **Rate limiting on ingestion** — prevent misconfigured agents from flooding DB | **P2** | ❌ Not spec'd | Any agent can write unlimited data. |
| **15** | **Data pipeline monitoring** — track events ingested/processed/stored, alert on pipeline lag | **P2** | ❌ Not spec'd | No pipeline metrics tracked. |

**P0 = trust erosion on Day 1.** P1 = trust erosion within first week. P2 = nice-to-have.

**Cross-references:** obs-spec-023 §1 (state enumeration), §3.2 (failure modes), §7 (data continuity), §8 (health system), §9 (auto-recovery), §10 (update system). See also `observeco-master-plan.md §16` for the full priority table.

**Tracked in:** `KANBAN.md` (P0 section). Each item uses ponytail shortcuts, runnable self-checks, and passes the relevant playbook audits.

---

## 2026-06-18 Update — Additional Missed Fail-Safes (Claude Evaluation)

Independent evaluation identified 12 additional fail-safes beyond the original 15:

### P1 — Should Add Before Launch

| # | Fail-Safe | Why It Matters |
|---|-----------|----------------|
| M1 | Config file permission validation — warn if ~/.observeco/ or pulse.db is world-readable | SQLite DB contains agent names, error messages, token patterns. Single-user tool ≠ single-process machine. |
| M2 | Event deduplication — skip duplicate pulse_log entries on daemon restart | If daemon crashes mid-cycle and restarts, it re-probes agents and writes duplicates. No idempotency key on pulse_log. |
| M3 | WAL checkpoint management — prevent WAL from growing unbounded | SQLite WAL can exceed main DB on long-running daemon (30+ days). No PRAGMA wal_autocheckpoint in spec. |
| M4 | "Am I set up correctly?" self-check — observeco doctor or dashboard wizard | First-run users have no way to verify the system is working beyond "the dashboard loaded." |
| M5 | Degraded mode — dashboard continues (read-only) when DB corrupted or disk full | Currently spec says "stop data collection" or "print error." Dashboard should still serve cached data so user can see what happened. |

### P2 — Target D+30

| # | Fail-Safe |
|---|-----------|
| M6 | Audit trail for sensitive operations (who killed an agent, changed config) |
| M7 | API key leak detection in logs (scan for sk-..., OBS-PRO-..., bearer tokens) |
| M8 | Transactional boundaries for multi-table writes (pulse_log + errors atomic) |
| M9 | Connectivity test between dashboard and daemon |
| M10 | Graceful shutdown timeout enforcement (SIGTERM → 5s → SIGKILL) |
| M11 | Timezone handling policy (all UTC, convert only in UI) |
| M12 | File descriptor leak detection in long-running daemon |

**Cross-references:** obs-spec-023 §17 now includes implementation guidance for all P0 items. See also observeco-master-plan.md §16 for the full priority table.
