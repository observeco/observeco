# ObserveCo: Expectations Gap Document

**Date:** 2026-05-24
**Author:** Main
**Status:** Current — reflects state as of this date

## The Gap Statement

> **"If kanban is empty, we are good to launch."**

This assumption is **false** in the current setup. The kanban board tracked 14 build tasks (pulse, chisel, clawforge, dashboard, infra). All 14 are done. The code exists and tests pass.

But `kanban empty ≠ launch ready`. Launch readiness requires a completely different set of deliverables that were never captured as kanban tasks.

## Why This Happened

The kanban board is a **work tracker** — it tracks what someone decided to work on. It does NOT automatically represent the full launch checklist. The 14 tasks were extracted from `unified-dashboard.md` and `execution-plan.md` specs, but the spec's own Phase Zero checklist (D-28, D-21, D-14, D-7, D-3, D-0) was never converted to kanban tasks.

The consequence: code was built, but the path to user's machine was never completed.

## The 10 Gaps Between "Code Written" and "Launch Ready"

### 🔴 CRITICAL GAPS (Block launch)

| # | Gap | Detail | Owner |
|---|-----|--------|-------|
| **G1** | **PyPI name squatted** | `observeco` returns 200 on pypi.org. If someone else published, we need a different name. If it's a stale placeholder we can claim, we need to act. | Main |
| **G2** | **No CI/CD pipeline** | Zero `.github/workflows/` files. No automated lint, test, build, publish on push or tag. Cannot ship reliably without this. | Main |
| **G3** | **GitHub org blocked** | observeco GitHub org created but `seanfzc` not added as owner. Cannot push the monorepo, cannot manage releases, cannot create the public repo. | Sean (only org admin can add) |
| **G4** | **Stripe not live** | Billing code exists with simulated mode. No real Stripe keys configured. No webhook endpoint exposed on a public URL. No checkout flow tested end-to-end. | Main |
| **G5** | **observeco.ai not registered** | `observeco.io` is registered (Cloudflare). `observeco.ai` returns NXDOMAIN. At ~$12/yr, this is domain insurance before launch day. | Sean (domain owner) |

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
