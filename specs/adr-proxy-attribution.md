# ADR: Proxy Architecture & Traffic Attribution

**Status:** ~~v3 — 2026-06-15~~ **DEPRECATED 2026-06-19.** Proxy replaced by SDK-sidecar. Feature row §42 struck from master plan. This ADR retained as historical record and deprecation reference.
**Author:** Main
**Reviewer:** Pragma (Independent)

**Supersedes:** §6 scope boundary "Observer, not proxy" — the proxy now exists.
**Single source of truth:** Feature rows §42/§43/§44 + scope boundary §6 in `observeco-master-plan.md`. If this ADR conflicts with the master plan, the master plan wins.

---

> **⚠️ DEPRECATED 2026-06-19** — This ADR described the MITM proxy that has been removed. SDK-sidecar (`observeco instrument`) replaces it. Proxy was in the execution path with SSE torn-read risk and no supervisor process. SDK instrumentation is out-of-band, framework-aware, and zero crash risk. Retained as historical record.

---

## Context

ObserveCo needs to track token usage across local LLMs (ollama, llama.cpp) and cloud LLM providers (OpenAI, Anthropic, DeepSeek) at per-agent granularity.

**The proxy was originally built to solve both problems from one observation point.** After review, this approach has fundamental problems for cloud tracking (crash risk, streaming fragility, no component breakdown, attribution dependency on a custom header that doesn't exist yet).

**Redesigned architecture:**

| Target | Mechanism | Attribute | Risk |
|--------|-----------|-----------|------|
| **Local LLM** (ollama, llama.cpp) | MITM proxy (`observeco proxy`) | None needed — local tokens cost $0 | Proxy crash kills local-only tracking. No cloud impact. |
| **Cloud LLM** (OpenAI, Anthropic, DeepSeek) | Post-turn webhook — Hermes POSTs token payload to `POST /api/tokens/log` after every turn | Full: agent_name + model + provider + component breakdown | Zero — fire-and-forget, doesn't block agent response |
| **Cloud LLM catch-all** | Provider billing API (read-only query) | Aggregate per-provider only. Gap % vs webhook total. | Low — read-only query |

The proxy is no longer stretched to cover cloud. Cloud tracking is delegated to out-of-band mechanisms — the industry-standard approach used by Langfuse, Helicone, LangSmith, Datadog, and Braintrust.

---

## Options Considered

### Option 1: Post-turn webhook (Selected — cloud primary)

Hermes POSTs token data to ObserveCo after every turn. Fire-and-forget, doesn't block the agent.

**Wins:** Zero crash risk. Full component breakdown (identity/skills/memory/tools/guidance). Agent self-identifies. Works across ALL cloud providers. The proxy is structurally blind to component breakdown — the webhook isn't.

**Loses:** Requires agent-side hook (Hermes). OpenClaw needs separate plugin (§16). Non-instrumented agents are invisible to the webhook (fallback: provider billing API).

### Option 2: Provider billing API fallback

Query OpenAI/Anthropic/DeepSeek usage endpoints. Compare aggregate totals against webhook data. Compute attribution gap percentage.

**Wins:** Catches everything — instrumented or not. Historical data exists (~90d). Low effort.

**Loses:** No per-agent breakdown. No component breakdown. Aggregate only.

### Option 3: MITM Proxy (Selected — local LLM only)

Transparent proxy intercepts all HTTP calls to local LLM servers. Captures token usage on the way back.

**Wins:** Only way to track local LLMs (no billing API, no SDK). Already built.

**Loses:** In the execution path. No component breakdown. Header-based attribution fragile. Streaming parsing brittle. No per-topic routing awareness.

### Option 4: SDK-level callback (Rejected as primary — complementary only)

Inject token-counting callbacks into the agent's SDK client. Works for OpenAI SDK, Anthropic SDK, LiteLLM.

**Wins:** Zero infrastructure. No proxy needed.

**Loses:** Only works for the specific SDKs that support callbacks. Raw curl scripts bypass it entirely. OpenClaw uses Node.js SDK — different instrumentation path.

### Option 5: OTel instrumentation (Future)

Use OpenTelemetry spans for token tracking. Aligns with master plan §22 Layer 2.

**Wins:** Single observability surface. Strategic alignment.

**Loses:** Overkill for v1. Requires OTel exporter setup. No streaming token parsing.

---

## Decision

**Selected: Three-lane architecture.**

| Lane | Mechanism | Scope | Status |
|------|-----------|-------|--------|
| **L1 — Local proxy** | `observeco proxy` on :9200 | ollama, llama.cpp | ✅ Built |
| **L2 — Hermes webhook** | Post-turn POST to `/api/tokens/log` | All Hermes cloud calls | 🔴 Hermes-side hook not built |
| **L3 — Provider API** | Query billing endpoints | Any cloud call, any agent | 🔴 Planned |

L1 and L2 are independent — the proxy does NOT route cloud traffic. Hermes can call cloud providers directly AND also POST token data to ObserveCo. No single point of failure.

---

## Architecture

### Three-lane data flow

```
┌───────────────────────────────────────────────────────────┐
│                     YOUR SYSTEM                            │
│                                                           │
│  ┌────────────────────┐   ┌────────────────────┐          │
│  │  Local LLM         │   │  Cloud LLM         │          │
│  │  (ollama:11434)    │   │  (api.openai.com)   │          │
│  └────────┬───────────┘   └────────┬───────────┘          │
│           │                        │                       │
│           ▼                        │                       │
│  ┌────────────────────┐            │                       │
│  │  Proxy (:9200)     │            │ (direct, no proxy)    │
│  │  Captures tokens   │            │                       │
│  │  Logs to DB        │            ▼                       │
│  └────────┬───────────┘   ┌────────────────────┐          │
│           │               │  Hermes Agent      │          │
│           │               │  POSTs after turn  │          │
│           │               │  → /api/tokens/log│          │
│           │               └────────┬───────────┘          │
│           │                        │                       │
│           ▼                        ▼                       │
│  ┌───────────────────────────────────────────┐            │
│  │  ObserveCo DB (token_logs + turn_log)      │            │
│  │                                           │            │
│  │  Local tokens: proxy writes               │            │
│  │  Cloud tokens: webhook writes             │            │
│  │  Gap: provider API reconciles             │            │
│  └───────────────────────────────────────────┘            │
└───────────────────────────────────────────────────────────┘
```

### Hermes post-turn webhook payload

```
POST /api/tokens/log
{
  "agent_name": "main",
  "turn_id": "turn_abc123",
  "model": "deepseek-v4-flash",
  "provider": "custom-ollama",
  "total_tokens": 8432,
  "components": {
    "identity": 420,
    "skills": 3200,
    "memory": 1800,
    "tools": 600,
    "guidance": 200
  },
  "latency_ms": 3400,
  "tool_calls": ["search_files", "read_file"],
  "topic_id": "29"         // optional, Hermes-specific
}
```

Key constraint: fire-and-forget, max 4KB, cache 3s on failure. Never block the agent response.

### Provider billing API reconciliation

```
Provider API total:     1,200,000 tokens (last 24h)
Webhook total:          1,100,000 tokens (last 24h)
Attribution gap:        8.3%     → Dashboard indicator
```

---

## Blind Spots (Documented)

These are not bugs — they're explicit scope limits communicated to users.

| # | Scenario | Why | Impact |
|---|----------|-----|--------|
| 1 | Non-Hermes agents without their own hook | No webhook. No provider API attribution. | Tokens in gap % only. |
| 2 | OpenClaw agents without §16 plugin | Different SDK, separate instrumentation required. | No per-agent or component data. |
| 3 | Two agents named "main" | Webhook uses config-level agent_name. | Dashboard merges both into one line. |

**Mitigation:** Provider billing API captures total cloud spend. Gap % tells users how much is missing. If it's high, they know they have uninstrumented agents.

---

## Risks & Mitigations

| Risk | Severity | Mitigation | Status |
|------|----------|-----------|--------|
| Proxy crash kills local LLM tracking | Medium | Local LLMs only — no cloud impact. Restart proxy manually. | Accepted |
| Streaming token extraction from proxy | Low (local only) | SSE parsing for ollama. Fallback: estimate from prompt length. | ✅ Works for ollama |
| Webhook payload lost on network failure | Low | Cache in agent for 3s, retry. If lost, provider API catches the gap. | ✅ Caching planned |
| Provider billing API rate-limited | Low | Query hourly instead of per-turn. Cache results for 1h. | 🔴 Planned |
| Two agents named identically | Low | User-fixable. Config validation warning (planned). | 🔴 Planned |

---

## Updated Scope Boundary

**Previous (§6, outdated):** "Inline API proxying / request blocking — ObserveCo is not in the execution path — Observer, not proxy."

**Updated (§6, 2026-06-15):** ObserveCo provides a local MITM proxy for **local LLM token tracking only** (ollama, llama.cpp). **Opt-in** (`observeco proxy start`). Cloud LLM tracking uses post-turn webhook (§43) + provider billing API fallback (§44) — out-of-band, zero crash risk.

**Three documented blind spots** — see §14 "What This Still Doesn't Catch."

---

## Key Decision Record

| Decision | Chosen | Rejected |
|----------|--------|----------|
| Cloud token tracking mechanism | Post-turn webhook from agent | MITM proxy (crash risk, no component breakdown) |
| Cloud token catch-all | Provider billing API | Nothing (gap is visible) |
| Local token tracking | MITM proxy | Nothing else works for local LLMs |
| Attribution method | Agent self-reports in webhook payload | `X-Request-Source` header on proxy |
| Component breakdown | Available in webhook (not proxy) | Proxy cannot provide it |
| OpenClaw tracking | §16 plugin (separate) | Same webhook (different SDK) |

---

## References

- `observeco-master-plan.md` §42 — Proxy (local LLM only)
- `observeco-master-plan.md` §43 — Post-turn webhook (cloud primary)
- `observeco-master-plan.md` §44 — Provider billing API (cloud fallback)
- `observeco-master-plan.md` §14 — Deep dive: Cloud token tracking
- `observeco-master-plan.md` §6 — Scope boundary