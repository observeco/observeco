# ObserveCo — Master Plan

**Company:** ObserveCo
**Product:** agentscope
**Package:** `pip install agentscope` / `npm install -g agentscope`
**CTA:** `pip install agentscope — you'll see your agents in 60 seconds.`

> **Name convention (post-review):** ObserveCo = company name. agentscope = product name and package name. All marketing uses "agentscope" as the product. ObserveCo is only used for legal entity, domain, and company branding.

**Version:** 2.35 (2026-06-16 — §12 Agenttrace Competitive Gap — 7 capability gaps mapped with closure plan)
**Last Updated:** 2026-06-16
**Owner:** Hound (CEO) → Kepler (Revenue) → Pragma (COO)
**Status:** Active — Brain Analysis UX fully rebuilt (obs-spec-brain-analysis-ux-redesign), CHISEL caveman engine wired
**Review:** Plumbing audit complete — 17 gaps identified, 4 critical

---

## 1. Vision

**See it. Fix it.**

ObserveCo makes AI agent failures visible, diagnosable, and fixable. We sit between agent runtimes and human operators, providing the visibility layer that every multi-agent system needs but nobody has built.

**The enemy:** Invisible chaos. Agents breaking silently. Token spend disappearing. No audit trail. No accountability.

**The customer:** Anyone running AI agents in production — from solo developers with Claude Code to enterprises with fleets of OpenClaw agents across Slack, Discord, and Telegram.

---

## 2. Product Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   OBSERVECO PLATFORM                     │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │           Fleet Dashboard (Web)              │       │
│  │  • Real-time agent monitoring                │       │
│  │  • Risk breakdown & audit trail              │       │
│  │  • Multi-agent fleet view                    │       │
│  │  • Team policy management                    │       │
│  └──────────────────┬──────────────────────────┘       │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────┐       │
│  │         Event Ingestion Layer                │       │
│  │  • Webhook receiver (universal)              │       │
│  │  • Channel adapters (Slack, Discord, etc.)  │       │
│  │  • Agent adapters (OpenClaw, Claude, etc.)  │       │
│  │  • Standardized event format (OEF)          │       │
│  └──────────────────┬──────────────────────────┘       │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────┐       │
│  │           Risk Engine (Core)                 │       │
│  │  • Tool call parser (structured JSON)        │       │
│  │  • Risk classification (low/med/high/crit)  │       │
│  │  • Policy enforcement                       │       │
│  │  • ML-based predictive scoring (Phase 3)    │       │
│  └──────────────────┬──────────────────────────┘       │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────┐       │
│  │           Storage & Security                 │       │
│  │  • Session logs (tamper-evident)             │       │
│  │  • Audit trail (append-only)                │       │
│  │  • OS keychain for secrets                  │       │
│  │  • User authentication (SSO/SAML)           │       │
│  └─────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
         ▲                                    │
         │                                    ▼
┌────────┴────────┐              ┌────────────────────┐
│  Agent Runtimes  │              │  Communication     │
│  • OpenClaw      │              │  Channels          │
│  • Claude Code   │              │  • Slack            │
│  • Cursor        │              │  • Discord          │
│  • Codex         │              │  • Telegram         │
│  • CrewAI        │              │  • Teams            │
│  • LangGraph     │              │  • Email            │
└─────────────────┘              └────────────────────┘
```

---

## 3. Phased Roadmap

### Phase 1 — Foundation (Week 1-4)

**Goal:** CLI works cross-platform, published to PyPI, one real integration.

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 1.1 | Resolve naming: ObserveCo (company) + agentscope (product/pkg) | Kepler | ✅ DONE | P0 |
| 1.2 | Fix README — remove npm install claim, keep pip install agentscope | Main | ✅ DONE | P0 |
| 1.3 | Publish to PyPI with pyproject.toml | Pragma | ⬜ TODO | P0 |
| 1.4 | Cross-platform path handling (platformdirs for %APPDATA%) | Main | ✅ DONE | P0 |
| 1.5 | Cross-platform ANSI colors (colorama) + headless/TTY detection | Main | ✅ DONE | P0 |
| 1.6 | Replace keyword risk engine with tool-call JSON parser | Main | ✅ DONE | P0 |
| 1.7 | Platform-aware dangerous patterns (Windows/Linux specifics) | Main | ✅ DONE | P0 |
| 1.8 | Add OpenClaw hook integration | Hound | ✅ DONE | P0 |
| 1.9 | Tamper-evident session logs (hash chain) | Pragma | ⬜ TODO | P1 |
| 1.10 | OS keychain for secrets (keyring) | Pragma | ⬜ TODO | P1 |
| 1.11 | Security audit | Hound | ⬜ TODO | P1 |

**Phase 1 Success Criteria:**
- [ ] `pip install agentscope` works on Windows, macOS, Linux
- [ ] `agentscope run "Fix login bug"` shows correct risk on all 3 OSes
- [ ] Colors render correctly on cmd.exe, PowerShell, Terminal, iTerm
- [ ] Colors degrade gracefully in headless/TTY-less environments (Docker, CI)
- [ ] Config stored in OS-standard location (via platformdirs)
- [ ] At least one real agent integration (OpenClaw hooks)
- [ ] Session logs can't be tampered with
- [ ] Secrets stored in OS keychain, not plaintext

### Phase 2 — Production Ready (Week 5-8)

**Goal:** MCP server, channel adapters, web dashboard, team features.

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 2.1 | MCP server (universal agent adapter) | Pragma | ✅ DONE | P0 |
| 2.2 | Slack adapter (bot events, audit logs) | Pragma | ✅ DONE | P0 |
| 2.3 | Discord adapter (bot messages, slash commands) | Pragma | ✅ DONE | P0 |
| 2.4 | Telegram adapter (bot API updates) | Pragma | ✅ DONE | P1 |
| 2.5 | Dashboard framework + session history (htmx + FastAPI) | Pragma | ✅ DONE | P0 |
| 2.6 | Dashboard real-time monitoring (add WebSocket to existing dashboard) | Pragma | ✅ DONE | P1 |
| 2.7 | Team features — shared permission policies | Pragma | ⬜ TODO | P0 |
| 2.8 | Team features — audit log | Pragma | ⬜ TODO | P0 |
| 2.9 | Claude Code adapter (hooks integration) | Kepler | ⬜ TODO | P0 |
| 2.10 | Cursor adapter (extension) | Kepler | ⬜ TODO | P1 |
| 2.11 | Docker image for self-hosted deployment | Pragma | ✅ DONE | P1 |
| 2.12 | Standardized Event Format (OEF) — formalize §4.2 into standalone spec | Hound | ✅ DONE | P1 |
| 2.13 | User authentication (OAuth2) | Pragma | ✅ DONE | P0 |
| **2.14** | **Webhook ingestion server — translate platform webhooks → OEF → risk engine** | **Hound** | **⬜ TODO** | **P0** |
| **2.15** | **Event processing pipeline — adapter → OEF → risk engine → session log → alerts** | **Hound** | **⬜ TODO** | **P0** |
| **2.16** | **Persist auth sessions to SQLite (OAuth2 + SAML)** | **Hound** | **⬜ TODO** | **P0** |
| **2.17** | **Discord signature verification — fail-closed when pynacl missing** | **Hound** | **⬜ TODO** | **P0** |
| **2.18** | **Outbound rate limiting + retry (Slack/Discord/Telegram 429 handling)** | **Hound** | **⬜ TODO** | **P1** |
| **2.19** | **API tokens — encrypt at rest, rotation, expiry** | **Hound** | **⬜ TODO** | **P1** |
| **2.20** | **Stripe webhook secret — read from config, not hardcoded** | **Hound** | **⬜ TODO** | **P1** |
| **2.21** | **Dead letter queue for failed event ingestion** | **Hound** | **⬜ TODO** | **P1** |
| **2.22** | **Watch daemon self-check (health heartbeat file)** | **Hound** | **⬜ TODO** | **P2** |
| **2.23** | **SQLite WAL backup schedule + thread-safety audit** — wire `db.backup()` before migrations, add pre/post row count verification (GS-019, see §4.2) | **Pragma** | **✅ Done** | **P0** |
| **2.24** | **Database migration infrastructure** — recovery check for recreate-table, downgrade guard, `observeco doctor` data health, decouple migration runner from `Database()` constructor (GS-019, see §4.2) | **Pragma** | **✅ Done** | **P0** |
| **2.24a** | **Migration restore mechanism** — `db.restore()` method, auto-restore on failure, CLI commands (`observeco backup/restore`), dashboard notification banner (GS-019, see obs-spec-022 Fix 7) | **Pragma** | **⬜ TODO** | **P0** |
| **2.25** | **Gateway Health Monitor — sidecar for OpenClaw + Hermes gateways** | **Hound** | **⬜ TODO** | **P0** |
| **2.26** | **Connection pool exhaustion auto-recovery** | **Hound** | **⬜ TODO** | **P0** |
| **2.27** | **Memory leak detection + graceful restart** | **Hound** | **⬜ TODO** | **P1** |

> **Note:** Codex adapter deferred to Phase 3 pending API feasibility verification.
> **Note:** Task 2.5 and 2.6 are sequenced: 2.5 builds dashboard framework, 2.6 adds WebSocket to it.
> **Note (2026-06-10):** Tasks 2.25-2.27 added after Hermes gateway pool exhaustion failure (325 errors, 3 days undetected). See §11.4.

**Phase 2 Success Criteria:**
- [ ] MCP server works with any MCP-compatible agent
- [ ] Slack app has 3+ workspaces with >10 events/day each
- [ ] Discord bot in 10+ servers with ≥1 event per server per day
- [ ] Dashboard shows real-time agent activity with <5s latency
- [ ] Team admin can create and enforce permission policies
- [ ] Docker image runs `docker run agentscope` and works
- [ ] Any agent can send events via webhook (POST /api/v1/events)

### Phase 3 — World Class (Month 3-4)

**Goal:** Fleet dashboard, universal pathway map, ML risk scoring.

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 3.1 | Fleet dashboard — multi-agent, multi-channel view | Pragma | ✅ DONE | P0 |
| 3.2 | Universal pathway map (any communication protocol) | Hound | ✅ DONE | P0 |
| 3.3 | ML-based predictive risk scoring | Pragma | ✅ DONE | P1 |
| 3.4 | Cross-agent failure correlation | Hound | ✅ DONE | P1 |
| 3.5 | Windows MSI installer | Kepler | ✅ DONE | P1 |
| 3.6 | Homebrew formula | Kepler | ⬜ TODO | P2 |
| 3.7 | Mobile monitoring app | Kepler | ⬜ TODO | P2 |
| 3.8 | Enterprise SSO/SAML | Pragma | ✅ DONE | P1 |
| 3.9 | API for third-party integrations | Pragma | ✅ DONE | P0 |
| 3.10 | On-prem deployment option | Pragma | ⬜ TODO | P2 |
| 3.11 | macOS LaunchAgent for auto-start | Pragma | ⬜ TODO | P2 |
| 3.12 | macOS notarization for Gatekeeper | Kepler | ⬜ TODO | P2 |
| 3.13 | Codex adapter (pending API verification) | Kepler | ⬜ TODO | P2 |
| **3.14** | **SAML response signature validation (replace placeholder)** | **Hound** | **⬜ TODO** | **P1** |
| **3.15** | **OAuth state as dict (concurrent login support)** | **Hound** | **⬜ TODO** | **P2** |
| **3.16** | **Pathway scan — detect Discord/Slack/webhook delivery (not just Telegram)** | **Hound** | **⬜ TODO** | **P2** |
| **3.17** | **Session log rotation + compaction** | **Hound** | **⬜ TODO** | **P2** |
| **3.18** | **Graceful shutdown for dashboard (SIGTERM handling)** | **Hound** | **⬜ TODO** | **P2** |
|| **3.19** | **Unified Action Log — capture all ObserveCo actions in one table (obs-spec-021)** | **Main** | **✅ Done** | **P0** |
| **3.20** | **Service Architecture — health monitoring, auto-recovery, update system (obs-spec-023)** | **Pragma** | **✅ Done** | **P0** |
| **3.21** | **Health System — Level 1+2 checks, auto-restart, dashboard status bar** | **Pragma** | **✅ Done** | **P0** |
| **3.22** | **Service Manager — start/stop components, process management** | **Pragma** | **✅ Done** | **P0** |
| **3.23** | **Update System — GitHub releases check, version comparison, auto-update** | **Pragma** | **✅ Done** | **P0** |
| **3.24** | **Minimum Viable Install — first run flow, empty state handling** | **Pragma** | **⬜ TODO** | **P0** |
| **3.25** | **Backup Storm Fix — rotation (5 max), cooldown (4hr), _init_db() fix** | **Pragma** | **✅ Done** | **P0** |
| **3.26** | **Brain Analysis UX Redesign — full rebuild per obs-spec: 4 sections (Save Tokens, Compression, Content Cleanup, Input Tokens), per-skill compress buttons, dynamic agent cards, CHISEL caveman engine wired** | **Main** | **✅ Done** | **P0** |
| **3.27** | **CHISEL Engine Wiring — backend endpoint `/api/chisel/compress-skill` with mode mapping (lite→rule, full→caveman), display name→directory name resolution, per-skill logging** | **Main** | **✅ Done** | **P0** |

**Phase 3 Success Criteria:**
- [ ] Dashboard shows all agents across all channels
- [ ] Pathway map visualizes agent communication in real-time
- [ ] Risk engine predicts failures before they happen
- [ ] One agent's failure automatically alerts related agents
- [ ] `choco install observeco` works on Windows

### Phase 4 — Accurate Token Cost Attribution (Month 5-6)

**Goal:** Every user gets accurate cloud-LLM cost data from day one, without manual OTel wiring.

**Problem:** Token analytics currently conflates system prompt sizing data (watch daemon polls) with actual API call costs (otel spans). Users see inflated "token burn" numbers that represent capacity measurements, not real usage. Industry platforms (LangSmith, Helicone, LangFuse) all assume SDK instrumentation — none poll system prompt components. ObserveCo's watch data is a unique capability, but must be separated from actual cost data.

**Three data categories:**

| Category | Source | Measures | Cost |
|---|---|---|---|
| **Actual cost** | Proxy / OTel | Real API calls with input+output tokens | Real provider pricing |
| **Sizing** | Watch daemon | System prompt component sizes (capacity) | $0 — no API call happened |
| **Estimated cost** | Sizing × pricing | What it *would* cost if sent as one turn | Projection, not actual |

**Approach A: Transparent API Proxy (primary — universal)**

During `observeco install`, set up a local reverse proxy that sits between agents and LLM providers. Agents point their `base_url` at the proxy (`http://localhost:9200/v1`). The proxy:

- Passes every request through unchanged (zero overhead)
- Captures token usage from response `usage` fields
- Logs to `token_logs` with `source='proxy'`
- Works with ANY HTTP client — OpenAI SDK, raw curl, LangChain, Hermes, anything
- No code changes needed — user changes one env var

```
Agent → http://localhost:9200/v1/chat/completions → Proxy → https://api.openai.com/v1/chat/completions
                    ↓ captures usage from response
              ObserveCo DB (source='proxy')
```

**Auto-configuration during install:**
1. Detect existing provider configs (Hermes `config.yaml`, OpenClaw, env vars)
2. Start proxy on `localhost:9200`
3. For Hermes: auto-update provider `base_url` to `http://localhost:9200/v1`
4. For others: print `export OPENAI_BASE_URL=http://localhost:9200/v1`
5. Proxy handles authentication passthrough (API keys forwarded, never stored)

**Approach B: SDK Auto-Instrumentation (cleaner data, secondary)**

During install, detect installed Python/Node packages and auto-patch:

| Package | Patch Target | What It Captures |
|---|---|---|
| `openai` | `ChatCompletion.create()` | Per-call latency, model, tokens, cost |
| `langchain` | Callback handler | Chain-level trace + token breakdown |
| `llama_index` | Callback handler | Index query + token breakdown |
| `anthropic` | `client.messages.create()` | Per-call latency, model, tokens |

Auto-instrumentation gives richer data (per-call timing, error rates, model name) but requires the agent to use a known SDK. The proxy catches everything else.

**Approach C: OTel Collector Auto-Config (deferred — standard but least universal)**

Auto-generate an OTel collector config that:
- Receives spans from any OTel-instrumented code
- Exports to ObserveCo's listener
- Auto-discovers providers from environment variables

Deferred because it requires users to have `opentelemetry-sdk` installed and their code instrumented — least universal of the three approaches.

**Token Analytics Dashboard Changes:**

The dashboard separates the three data categories:

- **"Actual Cost"** tab — `source='proxy'` + `source='otel'` rows only. Real cloud burn. This is what users care about.
- **"System Prompt Size"** section — `source='watch'` rows. Capacity metrics, drift detection, growth alerts. Marketed as a unique feature (no competitor offers this).
- **"Estimated Cost"** overlay — sizing × pricing table. What it *would* cost. Clearly labeled as projection.

**Multi-upstream routing (4.13):** The proxy auto-discovers its routing table from Hermes `config.yaml` at startup. For each provider with a `_original_base_url`, the proxy maps `provider_name → original_base_url`. When a request arrives, the proxy:

1. Reads the `model` field from the request body
2. Calls `detect_provider(upstream_url, model)` to identify which provider this model belongs to
3. Looks up the provider's original upstream URL from the routing table
4. Forwards the request to the correct upstream
5. Falls back to the default upstream if no match (backward compatible)

```python
# Routing table auto-discovered from config.yaml
routing_table = {
    "custom-ollama": "https://token-plan-sgp.xiaomimimo.com/v1",
    "deepseek": "https://api.deepseek.com",
    "zhipuai": "https://api.z.ai/api/paas/v4",
    "xiaomi": "https://token-plan-sgp.xiaomimimo.com/v1",
}
```

The local proxy on `:9201` stays single-upstream (ollama-local only). The cloud proxy on `:9200` becomes multi-upstream.

**Data flow architecture (updated):**

```
┌─────────────────────────────────────────────────────────┐
│                    User's Agents                         │
│  Hermes │ OpenClaw │ LangChain │ Raw SDK │ Claude Code  │
└────┬────┴────┬─────┴─────┬─────┴────┬────┴──────┬──────┘
     │         │           │          │           │
     ▼         ▼           ▼          ▼           ▼
┌─────────────────────────────────────────────────────────┐
│              ObserveCo Proxy (port 9200)                 │
│  • Transparent pass-through                              │
│  • Captures response.usage (input/output/cache tokens)   │
│  • Extracts model name, latency, error status            │
│  • Logs to token_logs with source='proxy'                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   ObserveCo DB                           │
│  source='proxy'  → Actual Cost (real API calls)         │
│  source='otel'   → Actual Cost (OTel-instrumented)      │
│  source='watch'  → System Prompt Sizing (capacity)      │
│  source='cli'    → CLI Usage (manual invocations)       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Fleet Dashboard                             │
│  Token Analytics: Actual Cost | Prompt Size | Est. Cost  │
│  Per-agent breakdown with accurate cost attribution      │
└─────────────────────────────────────────────────────────┘
```

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 4.1 | **API Proxy core** — async HTTP proxy (httpx/aiohttp), capture response usage, log to token_logs with source='proxy' | Hound | ✅ DONE | P0 |
| 4.2 | **Proxy auth passthrough** — forward Authorization/API-Key headers, never log or store API keys | Hound | ✅ DONE | P0 |
| 4.3 | **Proxy resilience** — connection pooling, retry upstream on failure, graceful degradation (if proxy down, agent still works) | Hound | ✅ DONE | P0 |
| 4.4 | **SDK auto-instrumentation detector** — scan installed packages, generate monkey-patch or callback registration | Hound | ✅ DONE | P1 |
| 4.5 | **SDK patchers** — openai, langchain, llama_index, anthropic wrappers that log to token_logs with source='sdk' | Hound | ✅ DONE | P1 |
| 4.6 | **Install flow integration** — `observeco install` starts proxy, detects providers, auto-configures base URLs | Hound | ✅ DONE | P0 |
| 4.7 | **Hermes auto-config** — update provider base_url in config.yaml to point at proxy | Hound | ✅ DONE | P0 |
| 4.8 | **Dashboard: separate Actual Cost vs Sizing** — token analytics filters by source, new UI sections | Hound | ✅ DONE | P0 |
| 4.9 | **System Prompt Sizing section** — watch data displayed as capacity metrics, not cost. Drift detection, growth alerts | Hound | ✅ DONE | P1 |
| 4.10 | **Estimated Cost overlay** — sizing × pricing table, clearly labeled as projection | Hound | ✅ DONE | P2 |
| 4.11 | **Provider config registry** — detect Hermes, OpenClaw, LangChain, raw SDK configs and generate appropriate wiring instructions | Hound | ✅ DONE | P1 |
|| 4.12 | **Proxy dashboard panel** — real-time view of proxied requests, latency, error rate, token flow | Hound | ✅ DONE | P1 |
|| 4.13 | **Multi-upstream proxy routing** — replace single-upstream `ProxyServer` with routing table that maps provider name → upstream URL. Auto-discovered from Hermes `config.yaml` at proxy startup using `_original_base_url` values. Proxy reads model name from request body, detects provider via `detect_provider()`, routes to correct upstream. Backward compatible: single upstream = no routing table = existing behaviour. | Hound | ⬜ TODO | P0 |
|
|**Phase 4 Success Criteria:**
- [x] `observeco install` starts proxy and auto-configures at least one provider (4.6, 4.7)
- [x] Proxy captures actual API token usage with correct cost attribution (4.1, 4.2, 4.3)
- [x] Token Analytics shows "Actual Cost" from proxy/otel, separate from "System Prompt Size" from watch (4.8, 4.9, 4.10)
- [x] Users with Hermes/OpenClaw get zero-config proxy wiring (4.7, 4.11)
- [x] Users with raw SDK get env var instruction printed (4.4, 4.5)
- [x] If proxy is down, agents still work (graceful degradation) (4.3)
- [x] No API keys logged or stored by proxy (4.2)
- [x] SDK auto-instrumentation detects and patches openai/anthropic/langchain (4.4, 4.5)
- [x] Provider config registry detects Hermes/OpenClaw configs (4.11)
- [x] Proxy dashboard panel shows traffic stats (4.12)

---

### Phase 5 — Local LLM Usage Tracking (Month 6-7)

**Goal:** Every user sees actual local LLM usage (ollama, llama.cpp, vLLM) alongside cloud API costs — one unified view of all token consumption.

**Problem:** The dashboard currently shows cloud API costs (Actual Cost) and system prompt sizing (System Prompt Size) as separate views. Local LLM calls through ollama are invisible — users see "pa: 15M tokens" in All Data and think it's actual usage, but it's just prompt size polls. Users running local models get no real usage data.

**Solution:** Extend the proxy to handle local LLM servers. When enabled, route local ollama/llama.cpp traffic through the proxy to capture actual input/output tokens per call.

**Architecture:**

```
Agent → http://localhost:9200/v1 → Proxy → http://localhost:11434/v1 (ollama)
                    ↓ captures usage from ollama's response format
              ObserveCo DB (source='proxy', provider='ollama')
```

**Key design decisions:**

1. **Opt-in toggle** — `observeco proxy --track-local` or config `proxy.track_local: true`. Default: off (backward compatible). Local traffic is only proxied when explicitly enabled.
2. **Dual-instance mode** — The proxy currently supports a single upstream URL. When `--track-local` is enabled, the proxy spawns a second instance on a different port for local LLMs. The SDK auto-config routes agents to the correct proxy instance based on their provider URL (cloud → cloud proxy, local → local proxy). This avoids refactoring `ProxyServer` for multi-upstream routing.
3. **Ollama v1 endpoint already works** — Ollama's `/v1/chat/completions` returns standard OpenAI-compatible JSON with `usage.prompt_tokens`/`usage.completion_tokens`. The existing `_extract_from_json()` handles it. No custom parser needed for the v1 path. A secondary adapter for ollama's native `/api/generate` format (`prompt_eval_count`/`eval_count`) is a P2 addition.
4. **SDK toggle, not proxy toggle** — The localhost skip logic lives in `src/observeco/tracking/sdk/provider_registry.py` (`LOCALHOST_PATTERNS` + `_is_local()`). The `--track-local` flag modifies the SDK's auto-config behaviour to NOT skip localhost URLs when routing agents through the proxy. The proxy itself has no localhost filter.
5. **No cost attribution** — local models cost $0. The proxy logs tokens but sets `cost=0` and `cost_computed='flat'` (the existing `'flat'` value — `'local'` is not a valid `cost_computed` value in the codebase). Dashboard shows token counts but no cost column for local-only agents.
6. **Dashboard label update** — rename "All Data" to "Combined" in the source dropdown. The glossary tooltip already describes it as "Combined view" — this is a UI-only change.

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 5.1 | **Verify ollama v1 works with existing parser** — test that `_extract_from_json()` correctly parses ollama's `/v1/chat/completions` response. Add `_extract_from_ollama_native()` for `/api/generate` format (`prompt_eval_count`/`eval_count`) as secondary adapter | Hound | ⬜ TODO | P0 |
| 5.2 | **SDK local proxy toggle** — add `proxy.track_local` config option and `--track-local` CLI flag. When enabled, `_is_local()` in `provider_registry.py` returns False so SDK auto-config routes local providers through the proxy. NOT a proxy server change — the proxy has no localhost filter | Hound | ⬜ TODO | P0 |
| 5.3 | **Dual-instance proxy mode** — when `--track-local` is enabled, spawn a second proxy instance on port 9201 for local LLMs. Cloud proxy stays on 9200. SDK auto-config routes agents to the correct instance based on provider URL | Hound | ⬜ TODO | P0 |
| 5.4 | **Local cost attribution** — proxy sets `cost=0`, `cost_computed='flat'` for ollama rows. Dashboard hides cost column for local-only agents (those with only `source='proxy'` and `cost=0`) | Hound | ⬜ TODO | P1 |
| 5.5 | **Dashboard: rename "All Data" to "Combined"** — update source dropdown label from `📊 All Data` to `📊 Combined`. Glossary tooltip already describes it correctly | Hound | ⬜ TODO | P1 |
| 5.6 | **Dashboard: local agent label** — agents with only local/proxy data show a "🖥️ Local" badge instead of cost. Agents with cloud data show cost as normal | Hound | ⬜ TODO | P2 |
| 5.7 | **llama.cpp format adapter** — add `_extract_from_llamacpp()` for `tokens_predicted`/`tokens_evaluated` format | Hound | ⬜ TODO | P2 |
| 5.8 | **Auto-config for local proxy** — `observeco proxy configure --track-local` detects ollama/llama.cpp running on localhost and updates agent configs to route through proxy | Hound | ⬜ TODO | P2 |
| 5.9 | **Tests** — unit tests for ollama native format adapter, integration test with SDK toggle, verify dashboard shows correct data. Accuracy target: ollama v1 streaming captures ≥95% of total tokens vs direct API call; non-streaming captures 100% | Hound | ⬜ TODO | P1 |

**Phase 5 Success Criteria:**
- [ ] Ollama v1 endpoint captured correctly by existing parser (5.1)
- [ ] `observeco proxy --track-local` enables local tracking without breaking cloud proxy (5.2)
- [ ] Dual proxy instances run simultaneously on different ports (5.3)
- [ ] Local rows show $0 cost, cloud rows show real cost (5.4)
- [ ] Dashboard source dropdown clearly labels "Combined" with explanation (5.5)
- [ ] Users can see all agents' actual LLM usage in one view (5.1-5.6)
- [ ] No breaking changes to existing proxy/cloud functionality (5.2, 5.3)
- [ ] Ollama native format adapter has unit tests (5.9)
- [ ] Streaming capture accuracy ≥95% (5.9)

**Generic applicability:** This works for any user running local LLMs. The proxy is provider-agnostic — ollama, llama.cpp, vLLM, LocalAI, any OpenAI-compatible local server. Each needs a response format adapter (~10-20 lines each). The dual-instance architecture handles any mix of cloud + local providers.

---

### 4.1 Risk Engine v2 (Replaces Keyword Matching)

**Current (v0.1):** Keyword matching on text strings.
**New (v1.0):** Structured tool call parser.

```python
# Input: structured tool call from agent runtime
tool_call = {
    "name": "exec",
    "arguments": {
        "command": "rm -rf /var/data/backups",
        "workdir": "/app"
    }
}

# Risk classification
risk = classify_tool_call(tool_call)
# → RISK_CRITICAL (destructive + critical path)

# vs. harmless text
tool_call = {
    "name": "read",
    "arguments": {"path": "src/auth/login.ts"}
}
risk = classify_tool_call(tool_call)
# → RISK_LOW (read-only)
```

**Tool call risk matrix:**

| Tool | Args Pattern | Risk |
|---|---|---|
| read | any | LOW |
| write/edit | non-sensitive path | MEDIUM |
| write/edit | config/secrets/env | HIGH |
| exec | `rm`, `drop`, `delete` | CRITICAL |
| exec | `git push`, `deploy` | HIGH |
| exec | `curl`, `ssh` | MEDIUM (allowlist) |
| memory_write | any | MEDIUM |
| browser_* | any | MEDIUM |

### 4.2 Standardized Event Format (OEF)

All agents, regardless of runtime, send events in this format:

```json
{
  "version": "1.0",
  "event_id": "uuid",
  "timestamp": "ISO8601",
  "agent_id": "string",
  "runtime": "openclaw|claude-code|cursor|codex|crewai|langgraph",
  "channel": "slack|discord|telegram|teams|email|webhook",
  "event_type": "tool_call|response|error|heartbeat",
  "payload": {
    "tool_name": "string",
    "tool_args": {},
    "result": {},
    "risk_level": "low|medium|high|critical",
    "decision": "auto_approved|flagged|denied"
  },
  "context": {
    "session_id": "string",
    "user_id": "string",
    "task_id": "string"
  }
}
```

### 4.3 Channel Adapters

**Slack Adapter:**
- Receives events via Slack Events API (bot events, app mentions)
- Sends alerts to designated Slack channels
- Reads audit logs for agent activity
- Supports Slack Block Kit for rich notifications

**Discord Adapter:**
- Receives events via Discord bot (slash commands, messages)
- Sends alerts to designated Discord channels
- Supports Discord embeds for rich notifications

**Telegram Adapter:**
- Receives events via Telegram Bot API
- Sends alerts to designated Telegram groups/chats
- Supports inline keyboards for approval workflows

**Webhook Receiver (Universal):**
- `POST /api/v1/events` — accepts OEF events from any source
- Validates event signature (HMAC-SHA256)
- Rate limiting per source
- Dead letter queue for failed processing

### 4.4 Dashboard Components

**Session History:**
- Timeline view of all agent sessions
- Filter by agent, risk level, time range
- Drill-down into individual tool calls

**Risk Breakdown:**
- Pie chart: auto-approved vs flagged vs denied
- Bar chart: risk distribution over time
- Table: top risky actions with details

**Real-Time Monitor:**
- Live feed of incoming events
- WebSocket connection for instant updates
- Pause/resume filtering

**Team Policies:**
- CRUD for permission policies
- Policy versioning
- Rollback capability

### 4.5 Security Model

**Tamper-Evident Logs:**
- Each session log entry includes SHA-256 hash of previous entry
- Chain can be verified to detect tampering
- Format: `{...entry, "prev_hash": "sha256", "entry_hash": "sha256"}`

**OS Keychain Integration:**
- macOS: Keychain Services
- Windows: Credential Manager
- Linux: Secret Service (gnome-keyring, kwallet)
- Library: `keyring` (Python)

**User Authentication:**
- Phase 2: OAuth2 (Google, GitHub)
- Phase 3: SSO/SAML (Enterprise)
- Session tokens with expiry

---

### 4.2 Migration Infrastructure (GS-019 Implementation)

**Status:** 🟡 PARTIAL — `_init_db()` and `MIGRATIONS` exist, but 4 HIGH-severity gaps identified in playbook audit.

**Current state:** `db.py` has a dual-definition pattern:
- `_SCHEMA_SQL` (line 352) creates all tables with `IF NOT EXISTS` — runs every startup
- `MIGRATIONS` (line 22) has 16 versioned migrations — runs sequentially on upgrade

**Audit findings (playbook-applied):**

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | 10 tables orphaned in `_SCHEMA_SQL` with no migration provenance | HIGH | ⬜ FIX |
| 2 | `db.backup()` defined (line 664) but never called — no pre-migration backup | HIGH | ⬜ FIX |
| 3 | No downgrade path — version force-set on mismatch | HIGH | ⬜ FIX |
| 4 | Recreate-table pattern (migrations 11, 15) has data-loss window | MEDIUM | ⬜ FIX |
| 5 | Migration runner tightly coupled to `Database()` constructor — runs on every instantiation (30+ sites) | MEDIUM | ⬜ FIX |
| 6 | `_SCHEMA_SQL` bootstrap can mask partial-failure data loss on retry | MEDIUM | ⬜ FIX |

**Required changes (per GS-019 §3):**

1. **Wire `db.backup()` before migration loop** — one line in `_init_db()`:
   ```python
   if self._has_data(conn):
       self.backup()  # GS-019 §Principle 2
   ```

2. **Add recovery check for recreate-table migrations** — on startup, if `_v11` table exists but original doesn't, recover:
   ```python
   if table_exists(conn, "pathway_nodes_v11") and not table_exists(conn, "pathway_nodes"):
       conn.execute("ALTER TABLE pathway_nodes_v11 RENAME TO pathway_nodes")
   ```

3. **Add pre/post migration row counts** — log counts before migration, verify after:
   ```python
   pre_counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] 
                 for t in affected_tables}
   # ... run migration ...
   post_counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] 
                  for t in affected_tables}
   if pre_counts != post_counts:
       logger.error(f"GS-019 VIOLATION: row count mismatch after migration")
   ```

4. **Add `observeco doctor` data health check** — verify schema version, row counts, backup recency

**Full spec:** `obs-spec-022-migration-infrastructure.md`
**Standard:** `GS-019-data-observability-continuity.md` (§3 Schema Evolution Rules)

---

## 5. Cross-Platform Compatibility

### 5.1 OS Support Matrix

| Feature | macOS | Linux | Windows |
|---|---|---|---|
| CLI | ✅ | ✅ | ✅ (with fixes) |
| Config location | ~/.agentscope/ | ~/.agentscope/ | %APPDATA%/agentscope/ |
| Colors | ✅ | ✅ | ✅ (colorama) |
| Headless mode | N/A | ✅ (no ANSI) | N/A |
| Keychain | Keychain | Secret Service | Credential Manager |
| Installer | Homebrew | apt/snap | MSI/Chocolatey |
| Background service | LaunchAgent | Systemd | Windows Service |

### 5.2 Communication Channel Support

| Channel | Phase 2 | Phase 3 |
|---|---|---|
| Slack | ✅ | ✅ |
| Discord | ✅ | ✅ |
| Telegram | ✅ | ✅ |
| Teams | — | ✅ |
| Email | — | ✅ |
| Webhook (any) | ✅ | ✅ |

### 5.3 Agent Runtime Support

| Runtime | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| OpenClaw | ✅ (hooks) | ✅ | ✅ |
| Claude Code | — | ✅ (hooks) | ✅ |
| Cursor | — | ✅ (extension) | ✅ |
| Codex | — | ✅ (API) | ✅ |
| CrewAI | — | ✅ (MCP) | ✅ |
| LangGraph | — | ✅ (MCP) | ✅ |
| Any MCP | — | ✅ | ✅ |

---

## 6. Pricing

| Tier | Price | Includes |
|---|---|---|
| **Solo** | $0/mo | Local CLI, unlimited tasks, basic risk detection, 7-day history |
| **Team** | $19/mo | Everything in Solo + shared policies, audit log, custom rules, MCP, priority support |
| **Enterprise** | Custom | Everything in Team + SSO/SAML, compliance rules, on-prem, SLA |

---

## 7. Marketing Alignment

**Product name:** agentscope
**Company name:** ObserveCo
**Positioning:** "See it. Fix it."

**Launch phases** (from marketing-plan.md — dates to be synced with engineering):
1. Ghost (D-7): Anonymous Reddit comment → 3-5 beta testers
2. Tease (D-3): One X post, no link → imagination
3. Revelation (D-0): X article + HN Show HN + Reddit → 50-100 stars
4. Payoff (D+14): X thread → "when auto-fix?" → v1.1 drop

**CTA:** `pip install agentscope — you'll see your agents in 60 seconds.`

**Anti-patterns (from marketing plan):**
- No "we" language
- No feature lists before pain is shown
- No "company" language in launch posts
- No cold outreach
- No announcing v1.1 at launch

> **Marketing-engineering sync:** D-0 launch date must be AFTER Phase 1 completion. Add go/no-go gate: Phase 1 success criteria must pass before marketing Phase 3 begins.

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PyPI publish fails | Low | Critical | Test with test.pypi.org first |
| Windows colorama breaks | Medium | High | Test on 3 Windows terminal types |
| MCP server spec changes | Medium | High | Pin MCP version, monitor upstream |
| Slack API rate limits | Medium | Medium | Batch events, exponential backoff |
| Dashboard performance at scale | Low | High | Implement pagination, virtual scrolling |
| Security audit failure | Medium | Critical | Run security audit in Phase 1 |
| Discord webhook signature bypass (pynacl missing) | High | Critical | Fail-closed: reject if pynacl not installed |
| Auth session loss on restart | High | High | Persist sessions to SQLite |
| API tokens in plaintext JSON | Medium | High | Encrypt at rest via keyring or AES |
| No event processing pipeline | High | Critical | Build adapter → OEF → risk engine → log pipeline |
| Hardcoded Stripe webhook secret | Medium | High | Read from billing config |
| Outbound rate limit silent drops | Medium | Medium | Retry + exponential backoff on 429 |
| OAuth concurrent login race | Low | Low | State dict instead of single string |
| SAML no signature validation | Medium | High | Integrate xmlsec for production SAML |

---

## 9. Dependencies

| Dependency | Type | Phase | Status |
|---|---|---|---|
| colorama | Python | 1 | ⬜ Install |
| platformdirs | Python | 1 | ⬜ Install |
| keyring | Python | 1 | ⬜ Install |
| mcp | Python | 2 | ⬜ Install |
| fastapi | Python | 2 | ⬜ Install |
| uvicorn | Python | 2 | ⬜ Install |
| websockets | Python | 2 | ⬜ Install |
| htmx | Frontend | 2 | ⬜ CDN reference |
| slack-sdk | Python | 2 | ⬜ Install |
| discord.py | Python | 2 | ⬜ Install |
| python-telegram-bot | Python | 2 | ⬜ Install |

> **Frontend decision (post-review):** htmx for dashboard (lightweight, no build step, works with FastAPI templates). If complexity grows, migrate to React/Svelte in Phase 3.

---

## 9.5 Standing Principles & Standards

These are non-negotiable constraints that apply to **every spec, every build, every migration** across all phases.

### GS-019: Data & Observability Continuity ✅ ACTIVE

**Why:** ObserveCo is an observability company. We cannot lose our own data during upgrades. "We lost your data during an upgrade" is an existential failure for this product.

**Core rules:**
1. **No silent data loss** — every deletion logged, auditable, reversible
2. **Backup before destructive operations** — `db.backup()` before any DROP, ALTER, or recreate-table
3. **Verify after migration** — row counts + `PRAGMA table_info` before/after
4. **Dashboard state matrix** — every section handles: populated, empty (fresh), empty (post-upgrade), empty (post-retention), error
5. **Self-monitoring** — row counts, last insert, schema version, backup recency tracked

**Mandatory for every obs-spec:**
- Must include a §Data Continuity section
- Must answer: What happens to existing data? Is backup required? What does the user see if empty? What's the recovery path?

**Full standard:** `~/.hermes/standards/GS-019-data-observability-continuity.md`
**Quick reference:** `~/.hermes/standards/GS-019-quick-reference.md`

---

## 10. Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-29 | Cross-platform gaps identified | 6 critical categories blocking adoption |
| 2026-05-29 | MCP server prioritized for Phase 2 | Universal adapter — solves agent compatibility in one shot |
| 2026-05-29 | OEF spec created | Standardized event format enables any channel integration |
| 2026-05-29 | Phase 1 focused on CLI fixes | Must work before anything else can be built on top |
| 2026-05-30 | Plumbing audit: 17 gaps identified (4 critical, 5 high, 5 medium, 3 low) | Adapters are output-only; ingestion, auth persistence, signature verification, and event pipeline missing |
| 2026-05-30 | Phase 2 tasks 2.1-2.6, 2.11-2.13 marked DONE (built 2026-05-29) | Master plan was stale — corrected |
| 2026-05-30 | Phase 3 tasks 3.1-3.4, 3.5, 3.8-3.9 marked DONE (built 2026-05-29) | Master plan was stale — corrected |
| 2026-06-11 | Token Analytics Dashboard shipped (obs-spec-020) | Chart.js time-series + breakdown + summary cards + drill-down modal + component toggle + CDN fallback. On-the-fly aggregation from token_logs (38K+ rows, <100ms). New columns: workflow_name, service_name, session_id, system_prompt_hash (Migration 17). |
| 2026-06-11 | Token cost bug fixed — watch.py bypassed compute_cost() | 38,605 rows had $0 cost. db.log_token_turn() now auto-computes cost when provider given. Backfilled to $5.11 total. |
| 2026-06-11 | §10 spec'd: Input/Output/Cache token breakdown | Tiered pricing (input vs output vs cache), OTel → token_logs routing, Migration 18 (4 new columns). Defers to Phase 2-4. |
| 2026-06-11 | §10 expanded: prompt caching detection + per-message attribution | Cache hit detection (provider-reported + heuristic fallback). New table token_message_breakdown for per-message cost isolation. Migration 19. |
| 2026-06-11 | §10 audited + gaps fixed (10 items) | Double-counting prevention (§10.4), cost_computed column, FK orphan handling, migration rollback/logging, CLI caller, cache heuristic accuracy bound, agent non-compliance fallback, resolve_provider(), regression constraint register. |
| 2026-06-11 | §10 built + verified | Migration 18 (6 cols) + 19 (token_message_breakdown). compute_cost_tiered, resolve_provider, detect_cache_savings. OTel+watch+cli routing updated. 38K rows backfilled. Independent verifier: 11/11 checks pass (1 bug caught + fixed: span_id undefined). |
| 2026-06-11 | Unified Action Log built (obs-spec-021) |
| 2026-06-11 | obs-spec-021 built + verified | Migration 20 (action_log table + 4 indexes). db.log_action() + get_actions() + backfill_action_log(). 6 API endpoints (JSON + HTML). trim.py, skill_compress.py, heal/__init__.py wired. Backfilled 19 rows from compress_log/heal_events/restart_log. Free/Pro cards in Brain Analysis/Skills Audit/Token Optimiser. 6 files modified, 15/15 tests pass. | Every ObserveCo action (compression, healing, drift, config fixes) logs to a single `action_log` table. Brain Analysis gets "Your ObserveCo Impact" card. Skills Audit shows compression history. Token Optimiser feed shows real actions. Migration 18. Backfill from existing siloed tables. |
| 2026-06-11 | Action Log spec v2: per-skill, no_action, Free vs Pro | Per-skill logging for skill_compress (one row per skill, not aggregate). no_action results logged when compression yields ≤5% savings. Free users see upsell banners, Pro users see real data. Empty states for fresh installs. 7 quantitative success metrics. Playbook audit applied (6 traps closed). |
| 2026-06-11 | GS-019: Data & Observability Continuity standard | Core principle: no silent data loss. Backup before destructive operations. Verify after migration. Dashboard state matrix (populated/empty/error). Self-monitoring metrics. Every obs-spec must include §Data Continuity section. |
| 2026-06-11 | Migration infrastructure spec'd (obs-spec-022) | Playbook audit: 4 HIGH findings (backup never called, no downgrade guard, recreate-table data-loss, bootstrap masks loss). 6 fixes: wire backup, pre/post row counts, stranded table recovery, downgrade guard, `observeco doctor` data health, retention sweep backup. Tasks 2.23-2.24 upgraded P2→P0. |
| 2026-05-30 | New Phase 2 tasks 2.14-2.24 added for plumbing remediation | P0: webhook ingestion, event pipeline, session persistence, Discord sig fix |
| 2026-06-13 | Brain Analysis UX fully rebuilt (obs-spec-brain-analysis-ux-redesign) | 4 sections: Save Tokens (dynamic agent cards, traffic lights), Compression (global toggle + auto-preview + Compress Top 20 + per-skill ⚡ buttons), Content Cleanup (stale item detection + Remove actions), Input Tokens (90-day trend + per-component table). 113K-char JS rewrite. |
| 2026-06-13 | CHISEL compression engine wired to backend | `/api/chisel/compress-skill` now maps mode→engine (lite→rule, full→caveman). `compress_skill_to_artifacts()` used instead of `compress_skill()`. Display names resolve to directory names via YAML frontmatter. Per-skill logging. |
| 2026-06-13 | Skill compression: "Compress Top 20" replaces "Apply All Bloated" | Caps batch to top 20 by token count (cost/time limit). Per-skill ⚡ Compress buttons on every skill row. Threshold: savings ≤10 tokens = "Already compressed". Sequential processing with live progress. |
| 2026-06-13 | Licensing security audit — 18 gaps fixed | Full end-to-end audit of license.py/billing.py/auth.py. 4 critical (start_trial overwrite, state contradiction, offline bypass, machine_id spoofable), 6 serious (webhook verification, stripe encryption, silent downgrade, trial bypass, rate limiting, race condition), 5 moderate (auth exclusions, revocation propagation, stale trust, demo session, trial→paid link), 3 edge (grace period, first_run_at, multi-machine). All 18 fixed. 339/342 tests passing. |
| 2026-06-13 | Migration restore mechanism spec'd (obs-spec-022 Fix 7) | Backup exists but no restore path. Gap: user never notified on failure, no CLI restore, no auto-restore. Fix 7: db.restore(), auto-restore on failure, CLI commands, dashboard notification. Task 2.24a added (P0). |
| 2026-06-14 | Phase 4 spec'd: API Proxy + SDK auto-instrumentation | Token analytics conflates sizing (watch) with actual API cost (otel). Research: no industry platform separates these. Three categories: Actual Cost (proxy/otel), Sizing (watch), Estimated Cost (sizing × pricing). Proxy is universal (any HTTP client). SDK auto-instrumentation gives richer data for known packages. OTel collector deferred (least universal). 12 tasks, P0-P2. |
| 2026-06-14 | Tasks 4.8-4.9 DONE: Dashboard source filtering + sizing view | `include_source` param added to `_build_where`, `aggregate_tokens`, `get_chart_data`, `get_breakdown`. API endpoints accept `source` param. Dashboard UI: "Data Type" dropdown defaults to 💰 Actual Cost (proxy,otel). Sizing view: cost card hidden, labels adapt (Prompt Size, Polls), breakdown table hides cost column, stacked chart uses drift components (identity/skills/memory/tools/guidance). Initial render delegates to `taRefresh()` for consistent source filtering. Verified: actual=9.7M tokens, sizing=67M tokens, all=76.7M. |
| 2026-06-14 | Task 4.10 DONE: Estimated Cost overlay in sizing view | Provider dropdown (6 providers from token_pricing table) visible only in sizing mode. "Projected Cost" card shows sizing tokens × provider input rate. Labeled as "⚡ ESTIMATE" with provider attribution. Uses existing `/api/token-pricing` endpoint. Example: 67.7M sizing tokens → $169.23 (GPT-4o), $10.15 (DeepSeek), $16.92 (Haiku). |
| 2026-06-14 | Tasks 4.1-4.3 DONE: Proxy core + auth passthrough + resilience | Built proxy/__init__.py + proxy/server.py + tests/test_proxy.py. Starlette ASGI app, httpx upstream client, captures response.usage from JSON + SSE streams. Auth passthrough (Authorization/api-key headers forwarded, never logged). Retry (2 attempts), timeout (300s), connection pooling. 16/16 unit tests pass. DB logging verified: source='proxy' with tiered cost computation ($0.0045 for 1800 openai tokens). Provider detection: 9 providers. ⚠ Live API test requires OPENAI_API_KEY (not in env). |
| 2026-06-14 | Tasks 4.6-4.7 DONE: CLI commands + Hermes auto-config | proxy/service.py: start/stop/status lifecycle with PID file management. CLI: `observeco proxy start/stop/status/configure`. Hermes auto-config: updates provider base_urls to proxy (http://localhost:9200/v1), preserves localhost providers (ollama), stores originals for revert. 7 service tests + 4 auto-config tests pass. |

---

## 11. Plumbing Gap Audit (2026-05-30)

**Trigger:** "What's missing" exercise after Phase 2/3 build. Adapters (Slack, Discord, Telegram) appeared complete from the outside but lacked integration plumbing.

### 11.1 Gap Categories

| Category | Gaps | Pattern |
|----------|------|--------|
| **Integration Pipeline** | #1, #4 | Adapters have send/receive but no ingestion server or processing pipeline |
| **Auth & Security** | #2, #3, #5, #7, #16 | Sessions in-memory, sig bypass, plaintext tokens, hardcoded secrets, no SAML validation |
| **Resilience** | #6, #9, #10, #11, #12 | No rate limiting, no DLQ, no self-check, no backup, no migrations |
| **Multi-Tenancy** | #8 | Single-user data model blocks Team tier |
| **Polish** | #13, #14, #15, #17 | OAuth race, pathway=Telegram only, no log rotation, no graceful shutdown |

### 11.2 Critical Path (Must Fix Before Launch)

1. **Webhook ingestion server** — platform webhooks (Slack Events API, Discord interactions, Telegram updates) → OEF translation → risk engine → session log. Without this, adapters are notification-only.
2. **Event processing pipeline** — the connective tissue: adapter output → OEF normalization → risk classification → session log write → alert dispatch → circuit breaker update.
3. **Persist auth sessions** — `_sessions` dict dies on restart. Migrate to SQLite `sessions` table.
4. **Discord signature fail-closed** — if pynacl not installed, reject (not accept) webhook requests.

### 11.3 Task Mapping

| Gap # | Task | Phase | Priority |
|-------|------|-------|----------|
| 1 | 2.14 Webhook ingestion server | 2 | P0 |
| 4 | 2.15 Event processing pipeline | 2 | P0 |
| 2 | 2.16 Persist auth sessions | 2 | P0 |
| 3 | 2.17 Discord sig fail-closed | 2 | P0 |
| 6 | 2.18 Outbound rate limiting | 2 | P1 |
| 5 | 2.19 API token encryption | 2 | P1 |
| 7 | 2.20 Stripe webhook secret from config | 2 | P1 |
| 9 | 2.21 Dead letter queue | 2 | P1 |
| 10 | 2.22 Watch daemon self-check | 2 | P2 |
| 11 | 2.23 SQLite backup + thread safety | 2 | P0 (GS-019) |
| 12 | 2.24 DB migration infrastructure | 2 | P0 (GS-019) |
| 16 | 3.14 SAML signature validation | 3 | P1 |
| 13 | 3.15 OAuth state dict | 3 | P2 |
| 14 | 3.16 Pathway multi-channel | 3 | P2 |
| 15 | 3.17 Session log rotation | 3 | P2 |
| 17 | 3.18 Graceful shutdown | 3 | P2 |

> **Note:** Gap #8 (Multi-Tenancy — single-user data model blocks Team tier) is acknowledged in §11.1 but **deferred** — requires full data model redesign (workspace/team/role tables). tracked as a Phase 3 design task, not part of this plumbing remediation cycle.

---

## 11.4 Gateway Health Monitor (2026-06-10)

**Trigger:** Hermes gateway Telegram connection pool exhaustion ran for 3 days undetected (June 7-10). 325 "Pool timeout" errors, 562MB memory growth, zero agent activations. Required manual kill + restart.

**Root cause:** No monitoring layer on gateway infrastructure. Failure was invisible until agents stopped responding.

**Solution:** Lightweight Python sidecar that monitors both OpenClaw and Hermes gateways.

### Architecture

```
┌──────────────────────┐     ┌──────────────────────┐
│   OpenClaw Gateway    │     │   Hermes Gateway      │
│   (port 18789)       │     │   (PID-based)         │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           ▼                            ▼
┌──────────────────────────────────────────────────┐
│            Gateway Monitor Sidecar                │
│  • Reads logs every 60s                          │
│  • Parses gateway_state.json                     │
│  • Tracks error rates, memory, pool health       │
│  • Threshold alerting → Telegram                  │
│  • Auto-recovery: pool recycle, graceful restart  │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Alert Channel  │
              │  (Telegram)     │
              └────────────────┘
```

### Metrics Collected

| Metric | Source | Frequency | Threshold |
|--------|--------|------------|-----------|
| Pool timeout count | gateway.error.log | 60s | >5 in 10min → CRITICAL |
| Memory RSS | gateway_state.json / psutil | 60s | >50MB/hour growth → WARN |
| Error rate | gateway.error.log | 60s | >1% of requests → WARN |
| Active agents | gateway_state.json | 60s | 0 for >15min → CRITICAL |
| Platform connectivity | gateway_state.json | 60s | disconnected → CRITICAL |
| Gateway uptime | process start time | 60s | >24h → WARN |

### Auto-Recovery Actions

| Condition | Action |
|-----------|--------|
| Pool exhaustion (>5 timeouts/10min) | SIGTERM gateway, let launchd restart |
| Memory >800MB | SIGTERM gateway, let launchd restart |
| Platform disconnected | Log warning, attempt reconnect |
| Zero agents >15min | Wake agents via signal inbox |

### Success Criteria

- [ ] Sidecar runs as launchd agent, auto-starts on boot
- [ ] Alerts arrive in Telegram within 60s of threshold breach
- [ ] Pool exhaustion triggers auto-restart within 2 minutes
- [ ] Memory leak detected before RSS exceeds 800MB
- [ ] Zero false positives in 7-day burn-in

---

## 11.5 Brain Analysis UX Redesign (2026-06-13)

**Trigger:** User feedback on Brain Analysis tab — 5 issues: naming conflicts, compression scope confusion, missing collapsible logs, Content Cleanup hard to understand, token usage placement unclear. User chose "Full rebuild" over incremental fixes.

**Spec:** `~/.hermes/obs-specs/brain-analysis-ux-redesign.md`
**Mockup:** `~/.hermes/mockups/brain-analysis-redesign-v2.html`

### What Changed

| Section | Before | After |
|---------|--------|-------|
| Health Pulse | Conflicting name, static cards | **Save Tokens** — dynamic agent cards from `/api/brain` data, traffic lights (🟢🟡🔴), click→scroll |
| Compression | 7 buttons, confusing scope | **Compression** — global Lite/Full toggle, auto-preview diff, "Compress Top 20" (capped), per-skill ⚡ buttons |
| Content Cleanup | "Config Health" — technical jargon | **Content Cleanup** — stale item detection, Remove/Remove All Stale actions |
| Input Tokens | Small chart, unclear label | **Input Tokens** — full-width 90-day trend (Pro), per-component table sorted worst-first |
| Activity logs | Disconnected, always visible | Collapsible per-section logs with context-proximate entries |

### Compression Engine

| Mode | Engine | What It Does | Savings |
|------|--------|-------------|---------|
| Lite | `rule` | String replacements on guidance blocks | ~0% (idempotent) |
| Full | `caveman` | LLM compresses prose paragraphs (provider-agnostic) | 5-20% |

**Backend:** `/api/chisel/compress-skill` (POST) — maps `mode`→`engine`, resolves display names→directory names via YAML frontmatter, logs per-skill to `compress_log` table.

**Provider Abstraction (2026-06-14):**
- Supports 7 providers: DeepSeek, OpenAI, Anthropic, Google, Ollama, Hermes, Lite (fallback)
- Auto-detection chain: Hermes → Ollama → DeepSeek → OpenAI → Anthropic → Google → Lite
- Config: `COMPRESSION.provider` (auto|deepseek|openai|anthropic|google|ollama|hermes|lite)
- API key detection: env var → `.env` file → `config.yaml`
- API: `GET /api/chisel/providers` lists providers with status

**Top 20 cap:** Batch "Compress Top 20" sorts skills by token count descending, takes first 20, processes sequentially with live progress updates. Cost limit: ~$0.10-0.20 per run.

**Threshold:** Savings ≤10 tokens treated as "Already compressed" — prevents repeat no-op compressions.

### Free vs Pro

| Feature | Free | Pro |
|---------|------|-----|
| Agent cards status | ✅ | ✅ |
| Auto-fix (🟡/🔴) | 🔒 | ✅ |
| Lite compression | ✅ | ✅ |
| Full compression | 🔒 | ✅ |
| Content Cleanup scan | ✅ | ✅ |
| Content Cleanup remove | 🔒 | ✅ |
| Input Tokens 90-day trend | 🔒 | ✅ |
| Input Tokens table | ✅ | ✅ |

### Files Modified
- `src/observeco/dashboard/templates/index.html` — full JS rewrite (Script 3: ~113K chars)
- `src/observeco/dashboard/server.py` — compress endpoint rewrite, auth token handling
- `src/observeco/chisel/skill_compress.py` — existing `compress_skill_to_artifacts()` now used by dashboard

---

---

## 12. Agenttrace Competitive Gap (2026-06-16)

**Trigger:** Real agenttrace output on 9,782 Hermes sessions revealed 7 capabilities ObserveCo must match to be a viable replacement.

**Context:** agenttrace is the current manual/decentralized analytics agents use to understand their own behaviour. It produces per-session and aggregate reports. ObserveCo must match or beat these 7 metrics before users will switch.

### 12.1 The 7 Capabilities

| # | Capability | agenttrace Example | ObserveCo Gap |
|---|-----------|-------------------|---------------|
| 1 | **Total estimated cost** across all sessions | $1,740.74 for 9,782 sessions | ✅ Proxy captures actual cost. Needs aggregate cost summary at fleet level |
| 2 | **Total token consumption** (input + output) | 7.72B tokens | ✅ Dashboard shows per-agent tokens. Need fleet-wide aggregate rollup |
| 3 | **Tool call tracking with success/failure rate** | 81,368 calls, 0% failure rate | ❌ No tool call instrumentation — no data on which tools agents call, success rate, or latency |
| 4 | **Agent health scoring** | 100% average health | ❌ No health scoring model — no per-session or per-agent health metric defined |
| 5 | **Provider-level cost breakdown** | Top burn: deepseek-v4-flash ($783), MiMo-V2.5 ($504), GLM-5.1 ($180) | ✅ Proxy captures per-provider cost via `detect_provider()`. Needs aggregate provider cost summary view |
| 6 | **Per-session drill-down (most expensive session)** | Single session: $3.27, 23M tokens | ✅ Dashboard session detail view exists. Verify it shows cost + tokens at session level |
| 7 | **Anomaly detection** | 12 "no_tools" sessions flagged | ❌ No anomaly detection — no automated flagging of sessions with abnormal behaviour patterns |

### 12.2 Gap Closure Plan

| # | Task | Owner | Priority | Phase |
|---|------|-------|----------|-------|
| 12.1 | **Fleet-wide aggregate cost/token summary** — top-level dashboard card showing total cost, total tokens, total sessions across all agents | Hound | P1 | Phase 4+ |
| 12.2 | **Provider cost breakdown view** — bar/pie chart showing cost by provider across fleet, with drill-down to per-agent | Hound | P1 | Phase 4+ |
| 12.3 | **Tool call instrumentation** — capture which tool calls agents make, success rate, latency. Wire into proxy or add agent-side hook | Hound | P0 | Phase 4+ |
| 12.4 | **Health scoring model** — define formula (success rate, error rate, latency, cost efficiency) and compute per-session + per-agent | Hound | P1 | Phase 5 |
| 12.5 | **Anomaly detection engine** — detect `no_tools`, high-cost, high-latency, zero-activity sessions. Flag and surface in dashboard | Hound | P1 | Phase 5 |
| 12.6 | **Session drill-down verify** — confirm dashboard session view shows cost, tokens, tool calls, health score, and anomalies | Hound | P2 | Phase 4+ |

### 12.3 Success Criteria

- [ ] Fleet dashboard shows total sessions, total cost, total tokens at top (12.1)
- [ ] Provider cost breakdown chart shows top-N providers with absolute cost (12.2)
- [ ] Dashboard captures and surfaces tool call success/failure rates per agent (12.3)
- [ ] Each agent has a health score (0-100) derived from session data (12.4)
- [ ] Anomalies are detected and flagged in dashboard automatically (12.5)
- [ ] Single session view shows all 7 metrics like agenttrace (12.6)

---

*This document is the single source of truth for ObserveCo's product roadmap. All tasks flow from here to Kanban boards. All agents reference this for context.*
