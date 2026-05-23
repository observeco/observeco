# ObserveCo — Comprehensive Launch Plan (D-28 to D-0)

## Executive Summary

**Current state:** Code built (pulse, chisel, clawforge, dashboard backend). 
**Missing:** Dashboard frontend (doesn't render), auto-collection daemon (no zero-code data), OTel compatibility (no ecosystem integration), 2 D-28 items (Stripe, domain), and 5 D-21 items (beta testers, code freeze prep, distribution drafts, polished assets, integration tests).

## Competitor Pattern Integration

We studied 5 competitors. Here's what each does and what we should adopt:

### 1. Arize Phoenix — OpenTelemetry-native
**Their pattern:** `register()` call sets up OTel instrumentation. OpenInference wrappers auto-capture LLM calls from any OTel-compatible framework (LangChain, LlamaIndex, OpenAI SDK, etc.). Data flows to their server via OTLP.
**Our adoption:** Add an OTel HTTP endpoint to the dashboard (`/v1/traces`). Any OTel-instrumented agent automatically feeds pulse data. This makes ObserveCo compatible with the entire Python/JS AI ecosystem without writing per-framework wrappers.

### 2. Helicone — Proxy intercept
**Their pattern:** User changes `baseURL` to their proxy URL. Proxy captures every request/response, logs to ClickHouse, provides dashboard.
**Our adoption:** `observeco watch` daemon that: (a) watches Hermes configs for running agents, (b) monitors `.hermes/agents/` for new agent configs, (c) polls health endpoints on a configurable interval. No user action after `pip install`.

### 3. LangFuse — Dual ingestion (SDK + OTel API)
**Their pattern:** Python SDK wraps LLM calls directly. Plus OTel API endpoint that accepts OTLP traces. Supports both structured SDK logging and open ecosystem ingestion.
**Our adoption:** Keep our CLI commands (manual collection) but add OTel endpoint (ecosystem compatibility) and `observeco watch` daemon (automatic collection). Three-tier collection: manual CLI → auto-daemon → OTel ingestion.

### 4. OpenLIT — Per-framework monkey-patching (wrap_function_wrapper)
**Their pattern:** `openlit.init()` wraps 50+ libraries (OpenAI, Anthropic, Chroma, etc.) using Python's wrapt library. Each wrapper captures traces + metrics per call.
**Our adoption:** Not for v1 — too fragile (version-dependent, breaks on library upgrades). But the pattern is useful for `observeco pulse check --auto` where we wrap known framework health endpoints.

### 5. RagaAI Catalyst — Decorator-based tracing (@trace_agent, @trace_llm, @trace_tool)
**Their pattern:** Python decorators that capture spans with attributes. Supports async functions. Exports to their cloud or local.
**Our adoption:** Not for v1 (requires code changes from users). Consider for v2 as `observeco.instrument()` API.

## Competitor Features ObserveCo Should Integrate (By Launch or v1.1)

| Feature | Competitor Source | Priority | Complexity | Our Implementation |
|---------|------------------|----------|------------|-------------------|
| OTel trace ingestion endpoint | Phoenix, LangFuse, OpenLIT | **P0 — launch** | Medium | Add `/v1/traces` POST endpoint to dashboard server. Uses standard OTLP JSON format. ~200 lines. |
| Auto-collection daemon (`observeco watch`) | Helicone (proxy pattern) | **P0 — launch** | Medium | Background daemon: polls health endpoints, checks agent configs, writes to SQLite every 30s. ~300 lines. |
| Per-component token drilldown in dashboard | Phoenix (span explorer) | **P1 — v1.1** | Low | Expand agent card to show per-component bar chart. CSS + htmx only. |
| Agent-level error attribution | RagaAI (span trace tree) | **P1 — v1.1** | Medium | Link circuit breaker events to error spans. Requires OTel trace_id correlation. |
| Skill usage heatmap (ClawForge) | OpenLIT (per-instrumentor metrics) | **P2 — v1.2** | Low | Already planned in spec. Visualize per-skill fire count. |
| Multi-machine fleet relay | Helicone (proxy gateway) | **P2 — v1.2** | High | Agents on different machines send pulse data to a central ObserveCo instance. |

## What's Missing vs Execution Plan

### Code: Critical (blocks launch)

| Item | Spec Reference | Current State | Remaining Work | Est. Effort |
|------|---------------|---------------|----------------|-------------|
| **Dashboard index.html** | §2.2 "Dashboard IS the product" | ❌ Missing — returns "Template not found" | Single HTML file with htmx-included fragments. Sticky header, left rail (agent cards), right rail (alerts), error timeline. | 4h |
| **Dashboard static CSS** | §5 Color System | ❌ Missing | Stylesheet matching spec: dark theme (#0F172A bg), semantic colors, responsive layout. | 2h |
| **OTel ingestion endpoint** | §4.1 Framework support table | ❌ Not planned | `/v1/traces` endpoint accepting OTLP JSON. Maps to pulse_log and error tables. | 3h |
| **Auto-collection daemon** | §6.2 Onboarding funnel | ❌ Not planned | `observeco watch` command. Background loop: health checks → write SQLite. | 4h |
| **Dashboard port conflict handling** | §6.2 Fragile step mitigations | ❌ Missing | Auto-detect next available port. Print URL. Browser-fallback for headless. | 30m |
| **Cross-platform path handling** | §6.2 Fragile step mitigations | ❌ Missing | Use `platformdirs` instead of hardcoded `~/.observeco/` | 30m |

### Launch Assets: High Priority

| Item | Spec Reference | Current State | Remaining | Est. |
|------|---------------|---------------|-----------|------|
| **Terminal demo GIF** | §2.2 Quick demo GIF | ❌ SVG screenshot exists | Record asciinema of full `pip install → pulse check → chisel trim → dashboard` (15s) | 2h |
| **Dashboard mockup screenshot** | §2.4 Dashboard mockup | ❌ Missing | Run dashboard against Hermes data → screenshot real output | 1h |
| **docs/commands.md** | §2.3 Documentation | ❌ Missing | Auto-generate from `observeco --help`. List every flag + argument + example. | 2h |
| **docs/installation.md** | §2.3 Documentation | ❌ Missing | pip install, Python version, OS support, platformdirs | 1h |
| **docs/dashboard.md** | §2.3 Documentation | ❌ Missing | Screenshots, what each section shows, Pro features | 1h |
| **CONTRIBUTING.md** | §2.3 Documentation | ❌ Missing (exists at repo level but minimal) | Dev env setup, test instructions, code style, PR process | 1h |
| **LICENSE file** | §2.0 Packaging | ✅ MIT declared in pyproject.toml | Need LICENSE file in repo root | 5m |
| **GitHub repo description + topics** | §3.4 GitHub Profile Polish | ❌ Missing | Set description, topics, social preview | 15m |
| **GitHub issue templates** | §3.4 GitHub Profile Polish | ❌ Missing | Bug report + Feature request issue templates | 30m |

### Integration & Testing: High Priority

| Item | Spec Reference | Current State | Remaining | Est. |
|------|---------------|---------------|-----------|------|
| **Integration test: `pip install` from clean env** | §6.2 Fragile step mitigations | ❌ Missing | Docker or VM-based test. Confirms `pip install observeco` → all commands work. | 3h |
| **Integration test: dashboard opens** | D-21 code freeze gate | ❌ Missing | Test that `observeco dashboard` starts and browser opens | 2h |
| **Integration test: auto-detect Hermes** | D-21 code freeze gate | ❌ Missing | Test with mock Hermes config files | 2h |
| **Cross-OS tests (Linux, Windows WSL)** | §1.2 Beta validation | ❌ Missing | Run test suite on Ubuntu + Python 3.10-3.13 in CI | 2h |
| **Test coverage >70%** | §2.2 CI/CD | ~50% (40 tests, modules have ~80% coverage) | Add tests for dashboard, auto_detect, billing (real mode), db | 4h |

### Launch Operations: Must Happen

| Item | Spec Reference | Current State | Remaining | Est. |
|------|---------------|---------------|-----------|------|
| **Stripe keys configured** | §3.1 D-28 → D-14 | ❌ Blocked on Sean | Create Stripe account → set up products → wire webhooks | Sean |
| **observeco.ai registered** | §3.1 D-28 | ❌ Blocked on Sean | Cloudflare Registrar → ~$12/yr | Sean |
| **GH org access (seanfzc as owner)** | §3.1 D-28 | ✅ Already works (push succeeds) | — | — |
| **PyPI publish (v0.1.0-alpha)** | §3.1 D-28 | ❌ Not done | `pip install build && python -m build && twine upload dist/*` | 30m |
| **Beta testers recruited** | §3.1 D-21 | ❌ Not started | Reddit r/AI_Agents + Discord + personal network | Sean |
| **Beta package shared** | §3.1 D-14 | ❌ Depends on Stripe + PyPI | Share PyPI test package + GitHub link | Main |
| **Terminal GIF recorded** | §3.1 D-7 | ❌ Needs asciinema | Record on Hermes machine | Main |
| **HN post draft** | §3.1 D-1 | ✅ Drafted in docs/launch-drafts.md | Review & finalize | Main |
| **Reddit posts draft** | §3.1 D-1 | ✅ Drafted in docs/launch-drafts.md | Review & finalize | Main |
| **X thread draft** | §3.1 D-1 | ✅ Drafted in docs/launch-drafts.md | Review & finalize | Main |

## Revised Kanban Tasks

### Phase 1: Launch-Blocking (P0 — must ship at D-0)

| ID | Task | Est. | Dependencies |
|----|------|------|-------------|
| **obs-L-001** | Dashboard: create index.html with htmx layout (fleet header, agent cards, alerts rail, error timeline) | 4h | — |
| **obs-L-002** | Dashboard: create static CSS (dark theme, semantic colors, responsive layout per spec §5, §6) | 2h | obs-L-001 |
| **obs-L-003** | Dashboard: implement OTel ingestion endpoint (`/v1/traces`, OTLP JSON → pulse_log + errors) | 3h | — |
| **obs-L-004** | Daemon: implement `observeco watch` — background auto-collector (health polls, config scanning, SQLite writes) | 4h | — |
| **obs-L-005** | Infrastructure: port conflict handling + cross-platform paths (platformdirs) + browserless fallback | 1h | — |
| **obs-L-006** | Launch: publish v0.1.0-alpha to PyPI (trusted publishing via GitHub Actions) | 30m | obs-L-001 through obs-L-005 |
| **obs-L-007** | QAQC: integration test — `pip install` from clean env + all 6 CLI commands pass + dashboard opens | 4h | obs-L-006 |
| **obs-L-008** | QAQC: test suite on CI matrix (3.10-3.13, macOS+Ubuntu) — all pass | 2h | — |

### Phase 2: Launch Assets (P1 — must be ready before public launch)

| ID | Task | Est. | Dependencies |
|----|------|------|-------------|
| **obs-L-009** | Assets: record asciinema terminal demo GIF (15s: install → pulse → chisel → dashboard) | 2h | obs-L-006 |
| **obs-L-010** | Assets: take dashboard screenshot with real Hermes data | 1h | obs-L-001, obs-L-002 |
| **obs-L-011** | Docs: write docs/commands.md (auto-generate from --help, list all flags) | 2h | obs-L-006 |
| **obs-L-012** | Docs: write docs/installation.md + docs/dashboard.md + docs/pro.md | 3h | obs-L-001 |
| **obs-L-013** | Docs: write CONTRIBUTING.md (dev setup, tests, PRs) + add LICENSE file | 1h | — |
| **obs-L-014** | GitHub: set repo description, topics, social preview image, issue templates | 30m | — |

### Phase 3: Stripe & Beta (P1 — depends on Sean)

| ID | Task | Est. | Dependencies | Blocked on |
|----|------|------|-------------|------------|
| **obs-L-015** | Stripe: create account, set up Solo ($9/mo) + Team ($49/mo) products | 2h | — | Sean (Stripe account) |
| **obs-L-016** | Stripe: wire real keys → test end-to-end checkout → expose webhook endpoint | 2h | obs-L-015 | Sean (keys) |
| **obs-L-017** | Domain: register observeco.ai via Cloudflare Registrar (~$12/yr) | 15m | — | Sean (Cloudflare login) |
| **obs-L-018** | Beta: recruit 5-10 testers (r/AI_Agents, Discord, personal network) | 2h | obs-L-006 | Sean (network) |
| **obs-L-019** | Beta: share PyPI test package + GitHub link with testers | 30m | obs-L-006, obs-L-015 | — |

### Phase 4: Launch Distribution (P2)

| ID | Task | Est. | Dependencies |
|----|------|------|-------------|
| **obs-L-020** | Review & approve HN post draft (docs/launch-drafts.md) | 30m | Sean approval |
| **obs-L-021** | Review & approve Reddit posts (docs/launch-drafts.md) | 30m | Sean approval |
| **obs-L-022** | Review & approve X thread (docs/launch-drafts.md) | 30m | Sean approval |
| **obs-L-023** | Final: verify ALL items done → tag v0.1.0 → push to PyPI → post distribution | 1h | All above |

## Success Criteria (Kanban Cleared = Launch Ready)

1. ❌ `pip install observeco[dashboard] && observeco dashboard` opens working dashboard in browser
2. ❌ Dashboard shows agents with health dots, token bars, drift, circuit state, error timeline
3. ❌ OTel endpoint accepts traces from any compatible agent
4. ❌ `observeco watch` daemon auto-collects data without user action
5. ❌ CI/CD pipeline green on all matrix builds
6. ❌ PyPI v0.1.0-alpha published
7. ❌ Stripe billing live (Solo $9/mo, Team $49/mo)
8. ❌ observeco.ai domain registered
9. ❌ 5+ beta testers with working installs
10. ❌ All assets (GIF, screenshots, docs) published in repo
11. ✅ Distribution drafts written (HN, Reddit, X)
12. ❌ Distribution posts approved and ready to fire

## Current Gaps Map

```
Build Code (17 tasks) → ✅ DONE
├── pulse check + circuit → ✅ 
├── chisel trim + drift → ✅
├── clawforge profile + load + garden → ✅
├── dashboard backend (6 endpoints) → ✅
├── CLI (8 command groups) → ✅
├── SQLite data layer (10 tables) → ✅
└── billing (simulated) → ✅

Launch Prep (11 previous tasks) → 9/11 DONE
├── G1 PyPI → ✅
├── G2 CI/CD → ✅
├── G3 GH org → ✅
├── G4 Stripe → ❌ NEEDS YOU
├── G5 Domain → ❌ NEEDS YOU
├── G6 README → ✅
├── G7 Assets → ✅ (SVG only)
├── G8 Tests → ✅ (40/40)
├── G9 Beta → ✅ (drafted)
├── G10 Distribution drafts → ✅
└── G11 Comparison → ✅

Launch Gaps (this document) → 0/23 DONE
├── obs-L-001 through obs-L-023 → ALL PENDING
```
