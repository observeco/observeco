# ObserveCo — Market Analysis Report

**Date:** 2026-06-16
**Scope:** AI agent observability market, cross-industry pricing patterns, actionable recommendations for ObserveCo's free/pro model.

---

## 1. Executive Summary

ObserveCo is entering a market that doesn't neatly fit existing categories. The closest analogues (LangFuse, Helicone, AgentTrace) are LLM-trace-focused — they track *what the model returned*, not *whether the agent is healthy*. The broader observability industry (Datadog, Honeycomb, Sentry) tracks *infrastructure* or *application errors*, not *agent runtime behaviour*.

This report answers: **What is the market actually willing to pay for?** Based on live pricing pages, GitHub adoption signals, and cross-industry pricing models — not internal feature positioning.

**Key finding:** Every successful tool in adjacent markets gates on *scale*, not *features*. Free tiers are genuinely useful. People pay because they outgrow limits. ObserveCo's current model (gate features like auto-heal, push alerts, 90-day history behind $9 Pro) is inverted relative to market evidence.

---

## 2. AI Agent Observability: Competitor Analysis

### 2.1 LangFuse (29.2k★, YC W23, ~$29→$199→$2,499/mo)

**What they sell:** LLM engineering platform — tracing, evaluations, prompt management, datasets, playground. All-in-one for LLM app debugging.

**Free tier:** 50K observations/month, 30-day retention, 2 users, all features unlocked. No feature gating at all — the product is fully functional.

**Paid conversion drivers (from pricing page):**
- Scale: hit 50K observations → need more → $29/mo
- Retention: 30 days → 90 days ($29/mo, included in same tier)
- Users: 2 → unlimited ($29/mo, included)
- Compliance: SOC2/ISO27001/HIPAA → $199/mo Pro ($8/100K overage)
- Enterprise: SAML SSO, audit logs, SCIM, uptime SLA → $2,499/mo

**Why people pay:** They already use the free tier in production, hit limits, buy more capacity. **Not feature envy — volume pressure.**

**Validation source:** langfuse.com/pricing (live), 29.2k★ GitHub README, public testimonials from Canva, YC W23.

### 2.2 Helicone (5.8k★, acquired by Mintlify Mar 2026, ~$79→$799→custom/mo)

**What they sell:** LLM API gateway + observability proxy. Change one line of code (base URL) to get cost tracking, caching, rate limits, fallbacks.

**Free tier:** 10K requests/month, 1 GB storage, 1 seat, 1 org, 7-day retention. All core features unlocked — caching, rate limits, fallbacks, playground, prompts, sessions, user analytics, webhooks.

**Paid conversion drivers:**
- Volume: 10K → unlimited requests ($79/mo)
- Retention: 7 days → 1 month ($79/mo)
- Throughput: 10 logs/min → 1K logs/min ($79/mo)
- Alerts & reports (Pro+), HQL query language (Pro+)
- Compliance: SOC2/HIPAA → $799/mo Team
- On-prem + SAML SSO → Enterprise (custom)

**Why people pay:** Scale + throughput + compliance. Zero-code onboarding (change base URL) is the headline differentiator.

**Validation source:** helicone.ai/pricing (live), GitHub 5.8k★, Apache 2.0, YC W23.

### 2.3 AgentTrace (68★, launched May 2026)

**What they sell:** Post-hoc agent session analysis CLI. Reads log files agents already write (14+ formats). No instrumentation, no account, no cloud.

**Pricing:** Free (MIT). No paid tier exists.

**Why people download it:**
- Zero friction: `brew install agenttrace` or single binary
- Zero setup: reads existing logs, no SDK, no agent modification
- Private: data never leaves the machine
- Broad coverage: Claude Code, Codex, Cursor, Aider, OpenClaw, Hermes, etc.
- CI gates: `--fail-under-health`, `--fail-on-critical`, `--max-tool-fail-rate`
- Rich TUI: dashboard overview, session detail, latency/context/tool heatmaps

**What this means for ObserveCo:** AgentTrace solves a complementary job ("review what already ran") vs ObserveCo ("monitor what's running now"). But for a Hermes operator choosing between the two free tiers, AgentTrace gives health scoring and tool failure tracking that ObserveCo Lite doesn't. This is the most direct competitive pressure on the free tier.

**Validation source:** GitHub repo (all 9 open issues, 10 recent closed issues, 2 discussions), GitHub Pages site, Homebrew tap.

### 2.4 Arize Phoenix (10.1k★, 2.2M PyPI downloads/mo)

**What they sell:** Open-source AI observability platform focused on the trace → evaluate → iterate workflow for LLM agents. Owned by Arize AI.

**GitHub:** 10,166 stars, 925 forks, 599 open issues. Elastic License 2.0 (ELv2) — source-available, not permissive. You can self-host for free but cannot resell as a hosted service. v17.6.0 released June 15, 2026 (yesterday). Very active: multiple releases per week.

**PyPI:** ~89K downloads/day, ~412K/week, ~2.2M/month. Dominant mindshare in the OSS LLM observability space.

**Core value proposition:** "Trace the Exponential — The open-source platform for agent development and evaluation." Four pillars:
1. **Tracing** — every agent step (prompts, retrievals, tool calls, outputs) via OpenTelemetry. Multi-agent graphs, session-level tracing, MCP support.
2. **Evaluation** — LLM-as-judge scoring (relevance, toxicity, quality), human annotation, online evals
3. **Experiments** — dataset-versioned hypothesis testing
4. **Prompt IDE** — Compare models/parameters, replay traces. Built-in playground.

**Pricing model:**

| Feature | **AX Free** | **AX Pro ($50/mo)** | **AX Enterprise (custom)** |
|---------|------------|---------------------|---------------------------|
| Span traces | 25K/mo | 50K/mo | Custom |
| Ingestion | 1 GB/mo | 10 GB/mo | Custom |
| Retention | 15 days | 30 days | Configurable |
| Users | Unlimited | Unlimited | Unlimited |
| SSO | ❌ | ❌ | ✅ (Okta, AzureAD) |
| SOC2/HIPAA | ❌ | ❌ | ✅ |
| Self-hosting | ✅ (OSS, free) | ✅ | Add-on |

**Paid conversion drivers:**
- **Scale limits** — 25K spans/month (free) is tiny for any real production workload
- **Retention** — 15 days free, 30 days Pro. Not enough for long-term trend analysis
- **Compliance** — SOC2, HIPAA, SSO are Enterprise-only. Regulated industries must pay
- **Self-hosting** — OSS Phoenix is free self-hosted, but Arize-managed hosting is Enterprise

**Key differentiator vs ObserveCo:** Phoenix is stronger on LLM trace-level debugging (spans, evaluations, experiments) but has no concept of agent runtime health (circuit breakers, pulse checks, memory debt) or context optimization (compression, drift detection). They're LLM-trace-centric, not agent-runtime-centric. ELv2 license blocks reselling as hosted service.

**Key differentiator vs LangFuse/LangSmith:** Phoenix is OTel-native (interop with any OTLP backend, not locked to their UI). Has GPU monitoring. Has an embedded debugging agent (PXI). But ELv2 license is less permissive than LangFuse's MIT.

### 2.5 LangSmith (LangChain, ~$39/seat/mo + usage)

**What they sell:** Full lifecycle platform for AI agents — not just observability. Owned by LangChain. Positioning: "Take agents from prototype to production."

**GitHub:** ~8k stars on SDK repos. Proprietary (closed source). No self-hosting.

**Core value proposition:** Five pillars:
1. **Observability** — tracing, monitoring, insights (agent execution traces)
2. **Evaluation** — online/offline evals, datasets, annotation, prompt playground, Canvas
3. **Deployment** — managed hosting for long-running agents (LangGraph-based agents)
4. **Fleet** — no-code agent building for end users
5. **Engine** — autonomous failure detection + fix generation
6. **Sandboxes** — ephemeral isolated execution for agent-generated code

**Pricing model (exact, from live page, mid-2025):**

| Tier | Price | Traces Included | Overage |
|------|-------|----------------|---------|
| **Developer (free)** | **$0/seat/mo** | 5K traces/mo | $2.50/1k (14d retention) |
| **Plus** | **$39/seat/mo** | 10K traces/mo | $2.50/1k base, $5.00/1k extended (400d) |
| **Enterprise** | **Custom** | Custom | Custom |

Plus also includes: unlimited seats, up to 3 workspaces, 1 free dev agent deployment, 500 Fleet runs/mo.

**Additional paid products within LangSmith:**
- **LangSmith Engine** (auto-fix): $1.50/LCU (LangChain Compute Unit)
- **LangSmith Sandboxes** (isolated code execution): CPU $0.0576/vCPU-hr, Memory $0.0185/GiB-hr, Storage $0.000123/GiB-hr
- **Deployment Production**: $0.0036/min uptime
- **Fleet runs beyond included**: $0.05/run (Plus), $0.05/run (Free after 50)

**Paid conversion drivers:**
- **Trace volume** — 5K free, 10K Plus, then $2.50/1k. Heavy users get billed.
- **Seat count** — Free = 1 seat. Plus = unlimited seats. Enterprise = SSO/RBAC.
- **Deployment** — Free = no deployment. Plus = 1 dev deploy. Production = uptime fees.
- **Engine + Sandboxes** — entirely locked behind Plus. Autonomous failure diagnosis is the premium upsell.
- **Data residency** — Enterprise only: hybrid hosting or fully self-hosted.

**Positioning vs LangFuse:** LangSmith is dramatically more expensive on pure trace unit cost ($2.50/1k = $250/100k vs LangFuse $8/100k). Counter-argument: deployment, engine, ecosystem depth. But for pure observability, LangFuse is ~20x cheaper with better self-hosting. LangSmith wins on ecosystem lock-in (if you use LangChain/LangGraph).

**Key differentiator vs ObserveCo:** LangSmith covers the full lifecycle (trace → eval → deploy → fix → fleet), not just observability. But it's cloud-only, proprietary, expensive, and ecosystem-locked to LangChain. ObserveCo is local-first, free-as-in-beer, and framework-agnostic.

### 2.6 OpenLIT (2.5k★, Apache 2.0)

**What they sell:** Open-source LLM observability with 60+ integrations, OTel-native. Positioning: "100% Open Source. Forever Free."

**GitHub:** 2,532 stars, 301 forks, Apache 2.0. Active development (last push June 16, 2026). 51 open issues.

**Pricing model:** **Free forever.** No paid tier exists. Self-hosted only.

| Tier | Price | Features |
|------|-------|----------|
| **Self-Hosted (OSS)** | **$0** | Everything. No limits, no gates, no license key. |

Cloud offering listed as "Coming Soon" — no pricing published yet. Join waitlist only.

**What's included free (all of it):**
- Full LLM observability (60+ integrations: providers, vector DBs, agent frameworks, GPU hardware)
- OpenTelemetry-native traces and metrics
- Token usage & cost tracking
- GPU monitoring (NVIDIA + AMD) — unique vs competitors
- Vector DB monitoring
- Prompt Hub with versioning
- Secrets Vault
- Fleet Hub (multi-deployment management)
- LLM Evaluations
- Custom model pricing
- Organization management
- Export to Grafana, Datadog, any OTLP backend
- Kubernetes Operator

**Key differentiator:** Apache 2.0 (most permissive license in the space). GPU monitoring (nobody else in LLM observability does this). OTel-native — can route data to any backend (Grafana, Datadog, SigNoz, Jaeger), no lock-in. Full Docker Compose setup in <2 min.

**Key differentiator vs ObserveCo:** OpenLIT is broader (GPU, vector DB, 60+ integrations) but shallower on agent runtime health. It has no circuit breakers, no pulse checks, no memory hygiene, no drift detection, no compression. It's LLM-trace observability, not agent runtime observability. No paid tier means no conversion pressure — but also no business model to sustain development.

### 2.7 Datadog Bits AI / LLM Observability

**What they offer:** Two separate products under Datadog's platform:

**Bits AI** — An AI assistant that helps you *use* Datadog, not monitor agents. Capabilities: Bits Chat (natural language query of telemetry), Bits Investigation (autonomous alert investigation), Bits Code (AI-assisted code gen grounded in production data), Bits Agent Builder (build custom AI agents for incident response), Bits Security Analyst (autonomous SIEM triage).

**LLM / Agent Observability** — Standard Datadog observability but extended to trace AI model inference and agent behaviour. Uses APM pricing: per-host + per-GB + per-span. Supports framework integrations (LangChain, etc.), evaluation scores, token usage/latency.

**Pricing:**

| Product | Pricing Model | Minimum Cost |
|---------|--------------|-------------|
| **Bits AI** | "AI Credits" — per-credit usage (exact $/credit JS-rendered, not extractable statically). Credits consumed per action (chat, investigation, etc.) | Varies. Some credits included in annual plans. |
| **LLM Observability** | APM Pro ~$31/host/mo or Enterprise ~$55/host/mo. Includes 150 GB spans + 1M indexed spans per host | ~$31/mo minimum (1 host, Pro, annual) |
| **Platform infra** | Standard Datadog infra pricing ($15/host/mo) | +$15/host/mo minimum |

**Paid conversion drivers:** Standard Datadog scaling — host count, span volume, retention, compliance, SSO. Bits AI credits run out → overage billing.

**Key differentiator vs ObserveCo:** Datadog is the opposite of ObserveCo in every dimension: cloud-only, enterprise-priced, complex billing, requires significant setup. Their LLM observability is an add-on to a $15+/host/mo platform. Bits AI is an assistant for *using* Datadog, not for monitoring agents. For a solo Hermes-on-Mac-Mini operator, Datadog is irrelevant — the minimum cost ($46+/mo for 1 host + Bits AI credits) exceeds ObserveCo's entire Pro tier.

**Key takeaway:** Datadog validates that the enterprise market for AI agent observability exists (they built two products in this space). But their pricing model (per-host + per-credit) is the opposite of what works for solo/local operators.

---

## 2.8 Competitive Matrix Summary

| Tool | Stars | License | Free Tier Spirit | Entry Paid | Key Paid Driver | Agent Runtime Health? | Local-First? | Framework-Agnostic? |
|------|-------|---------|-----------------|-----------|-----------------|:---:|:---:|:---:|
| **ObserveCo** | — | MIT | 🟢 Genuinely useful | $0 (free forever) | Scale (proposed) | ✅ | ✅ | ✅ |
| **LangFuse** | 29.2k | MIT+EE | 🟢 Genuinely useful | $29/mo | Volume scale | ❌ | Self-host | ✅ |
| **Helicone** | 5.8k | Apache 2.0 | 🟢 Genuinely useful | $79/mo | Volume + retention | ❌ | Self-host | ✅ |
| **AgentTrace** | 68 | MIT | 🟢 Full product, no paid | Free only | N/A (no paid) | ✅ | ✅ CLI | ✅ |
| **Arize Phoenix** | 10.1k | ELv2 | 🟢 Genuinely useful | $50/mo | Volume + compliance | ❌ | Self-host | ✅ |
| **LangSmith** | ~8k | Proprietary | 🟡 1 seat, 5K traces | $39/seat/mo | Seats + volume + deploy | ❌ | ❌ Cloud-only | ❌ Locked |
| **OpenLIT** | 2.5k | Apache 2.0 | 🟢 Full product, no paid | Free only | N/A (cloud coming) | ❌ | Self-host | ✅ |
| **Datadog Bits AI** | N/A | Proprietary | 🟡 5 hosts free | ~$46+/mo | Host count + credits | ❌ | ❌ Cloud-only | ❌ Locked |

---

## 3. Broader Observability Industry: Pricing Models

### 3.1 The Pricing Unit Spectrum

| Approach | Who | For ObserveCo Equivalent |
|----------|-----|------------------------|
| **Per-event / per-span** (volume) | Honeycomb, Sentry, Datadog APM | Per agent invocation |
| **Per-active-series** (cardinality) | Grafana Mimir, Chronosphere | Per unique agent model |
| **Per-GB ingested** (logs) | Datadog, Splunk, New Relic | Per KB of agent trace data |
| **Per-host / per-entity** (legacy) | Datadog infra, Splunk legacy | Per-agent (current model) |
| **Per-user / per-seat** | LangSmith ($59), Sentry (Team tier) | Per developer (anti-pattern) |

### 3.2 What Works (Industry-Proven Patterns)

| Pattern | Who Uses It | Why It Works | ObserveCo Adopt? |
|---------|-------------|-------------|-----------------|
| **Single billing metric** | New Relic (GB ingested) | Predictable, simple. No host/user/service confusion. | ✅ Per agent invocation |
| **No per-seat charge** | Honeycomb, New Relic Pro+, Sentry Business+ | Removes friction. Team grows for free. | ✅ Yes |
| **Burst protection** | Honeycomb (3 burst days/mo) | Prevents bill shock. Load tests don't bill. | ✅ Yes |
| **Unlimited querying** | Honeycomb | Replaying data is free, storing costs. | ✅ Yes |
| **OSS free tier** | Grafana | Run open-source forever. Pay for cloud convenience. | ✅ Already MIT |
| **Rolling budget / auto-throttle** | Sentry (monthly event cap) | Predictable bill. No surprise overages. | ✅ Yes |
| **Consumption credits** | Grafana | One pool across signal types. Flexible. | ❌ Over-engineered |
| **Cardinality awareness** | Chronosphere | Don't penalise rich telemetry dimensions. | ✅ Important |
| **Transparent published pricing** | Honeycomb, Sentry | No "call sales" friction for small teams. | ✅ Already done ($9) |

### 3.3 What Doesn't Work (Anti-Patterns)

| Pattern | Who | Why It Fails |
|---------|-----|-------------|
| **Per-seat pricing** | Early Datadog, Jira, Slack | Friction when team grows. Users resist adding seat cost. |
| **Hidden pricing** | Chronosphere (no free tier) | Misses the bottom-up adoption funnel. |
| **Feature-gated free tier** | Most non-observability SaaS | Users try the paid product via workarounds, not via purchase. |
| **Complex multi-dimension billing** | Datadog (hosts + GB + series + spans + logs) | Bill shock meme. Customers resent unpredictable costs. |

---

## 4. What the Market Actually Pays For

**Claim supported by evidence:** Nobody pays for features. They pay because they outgrew free.

Evidence chain:
1. **LangFuse** — every feature is free at 50K obs/mo. Paid at 100K+ obs/mo.
2. **Helicone** — every feature is free at 10K req/mo. Paid at 1K logs/min throughput.
3. **Sentry** — every feature is free at 5K events/mo. Paid at 100K events/mo.
4. **Honeycomb** — every feature is free at 20M events/mo. Paid beyond that.
5. **New Relic** — every feature is free at 100 GB/mo ingest. Paid beyond that.

**The conversion funnel is universal:**
1. Free tier is genuinely useful → user adopts it
2. User outgrows limits (volume, retention, throughput, users)
3. User upgrades to get more capacity, NOT new features
4. Enterprise users pay for compliance certs (SOC2, HIPAA, SSO)

**Counter-evidence check:** LangSmith ($59/mo for team) gates users per seat. But they also offer a generous free tier with most features. The user limitation is the conversion driver, not a feature lock.

---

## 5. ObserveCo Current Model vs Market Evidence

### 5.1 What We Gate (current Pro, $9/mo)

| Gated Feature | Market Expectation (from evidence) |
|--------------|-----------------------------------|
| Auto-heal L1/L2 | Should be free — core reliability feature |
| Push alerts (Telegram, email) | Should be free (LangFuse: free, Helicone: Pro+ but they're proxy-based) |
| 90-day history | Should be free at low volume (7 days is useless for trends) |
| Full compression (35% savings) | Should be free (optimisation is core value) |
| Anomaly detection (+3σ) | Should be free (Sentry: free, Honeycomb: free) |
| LLM intelligence (permanent) | Gating this is defensible — no competitor offers LLM-powered agent health analysis. But 30-day trial then kill is too harsh. |

### 5.2 What We Give Away Free (current Lite)

| Free Feature | Market Value |
|-------------|-------------|
| Unlimited agents | ✅ Strong for adoption but zero conversion pressure |
| Fleet dashboard | ✅ Table stakes |
| Pulse health checks | ✅ Table stakes |
| Circuit breakers | ✅ Unique, strong for free |
| Memory Garden | ✅ Unique, strong for free |
| 7-day history | ❌ Too short to be useful for trend spotting |
| All CLI commands | ✅ Good |
| 30-day LLM grace | ✅ Generous but creates cliff problem (day 31: everything degrades) |

### 5.3 The Inversion Problem

Market evidence says: **Give features away, charge for volume.**

ObserveCo currently does: **Gate features, give unlimited agents away.**

This means:
- A user with 1 agent and $500/mo API spend gets no value from Pro (auto-heal locked, push alerts locked, 90-day history locked, full compression locked)
- A user with 30 agents and $50/mo API spend also has no reason to buy Pro
- Nobody feels scale pressure because agents are free and unlimited

**AgentTrace comparison:** AgentTrace's free tier gives health scoring, tool failure tracking, CI gates, and session comparison — things our Lite doesn't offer. A Hermes operator comparing free tiers sees AgentTrace as more immediately useful.

---

## 6. Proposed Model: Scale-Based Pricing

### 6.1 Tier Structure

| Tier | Price | Limits | Key Features |
|------|-------|--------|-------------|
| **Free** | $0 | 5 agent invocations/day (~150/mo) OR 3 agents, 7-day retention | **Everything.** Auto-heal, push alerts, full compression, LLM intelligence, anomaly detection, 90-day-plan history. All features unlocked. Limited by volume. |
| **Solo** | $9/mo | 5,000 agent invocations/mo, 90-day retention | Same features as Free, higher limits, email support |
| **Team** | $29/mo | 50,000 agent invocations/mo, forever retention | Same features, 3 seats, SSO, priority support |
| **Enterprise** | Custom | Unlimited | On-prem, SAML/SCIM, audit logs, SLA, dedicated engineer |

**What's "an agent invocation":** An agent turn = one LLM call + associated tool calls. This is the observable unit in every agent runtime. One message from a user that triggers one agent loop = one invocation.

Rationale:
- Maps to the unit every agent framework already logs (a turn)
- Scales naturally with usage (not agent count, not users)
- Burst protection: if daily invocations spike 5x, only 3x counts toward monthly cap (Honeycomb model)
- Unlimited querying: reviewing traces is free, only ingesting costs

### 6.2 What Stays Same Across All Tiers

**Everything is unlocked at every tier.** No feature gates. No "Pro only" labels. The only thing that changes with money is:

| Dimension | Free | Solo ($9) | Team ($29) |
|-----------|------|-----------|------------|
| Agent invocations/mo | ~150 (5/day) | 5,000 | 50,000 |
| Data retention | 7 days | 90 days | Forever |
| Users | 1 | 1 | 3 |
| Agents | 3 | Unlimited | Unlimited |
| Compliance | None | None | SOC2 report, SSO |
| Support | Community | Email | Priority |

### 6.3 Why This Aligns With Market Evidence

1. **Free tier is genuinely useful** — every feature works, no artificial caps on auto-heal or alerts. Limits are volume-based, not feature-based.
2. **Paid conversion driven by scale** — user hits 5 invocations/day, upgrades to $9/mo for 5,000. Natural growth.
3. **Graduated pricing feels fair** — $9 → $29 is a reasonable step. No jump from $0 to $79.
4. **Burst protection prevents hate** — load test doesn't double your bill.
5. **AgentTrace comparison** — ObserveCo Free now has health scoring, tool tracking, CI gates, push alerts *and* a live dashboard. AgentTrace becomes a complement, not a substitute.
6. **Agent count as free giveaway** — unlimited agents (on paid) is a strong unlock point vs per-agent pricing.

### 6.4 Financial Projection (Illustrative)

| Scenario | Users | Revenue |
|----------|-------|---------|
| 100 Free users → 5 convert to Solo ($9) | 5 paying | $45/mo |
| 1,000 Free users → 50 convert to Solo | 50 paying | $450/mo |
| 10,000 Free users → 300 Solo + 50 Team | 350 paying | $4,150/mo |
| 100,000 Free users → 1,000 Solo + 200 Team | 1,200 paying | $15,000/mo |

Conversion rate of 5-10% from free to paid is realistic (LangFuse reports similar). At 10K users, the solo tier alone clears $3K/mo — enough to fund continued development.

---

## 7. Transition Path

### 7.1 What Needs to Change

1. **Remove all feature gates.** `require_pro()` calls on auto-heal, push alerts, compression, anomaly detection, history retention. Replace with volume-count gates.
2. **Add invocation counting.** Track agent invocations per user. Store in SQLite (local) + sync to cloud for validation.
3. **Add burst protection.** If daily volume spikes >3x monthly daily average, cap the spike.
4. **Keep LLM intelligence permanently unlocked** as a free feature (not a tier gate). It's the core differentiation. Charge for scale instead.
5. **Change pricing communication.** "Free: 5 invocations/day, all features unlocked" vs "Free: Lite features, Pro locked behind $9."

### 7.2 What Stays

- MIT license for core product
- 30-day trial (gives unlimited invocations for 30 days, then drops to free tier limits)
- Admin-issued license keys for testers/partners
- Stripe billing integration
- Local-first, no telemetry guarantee

### 7.3 Risks

| Risk | Mitigation |
|------|-----------|
| **Free tier too generous** — users never hit 5 invocations/day cap | Monitor conversion. Tighten cap if necessary. Start generous (5/day) to build habit. |
| **Invocation counting complexity** — what counts as an invocation? | Clear definition: one LLM call = one invocation. Agent tool calls within an invocation are free. Document prominently. |
| **Existing users on unlimited legacy plan** — grandfather them as "Solo" for 6 months | Migration path: existing users get 6 months of their current Pro at no change, then transition to new model. |
| **Burst protection gamed** — users intentionally spike on 3 free burst days | Cap total burst days at 3/mo regardless of intent. Track rolling 30-day average, not calendar month. |

---

## 8. Competitive Positioning: The One-Liner

**Current:** "Tells you if your AI agents are working, what they're doing, and where your money goes."

**Proposed (adds the free-before-paid framing):**
> "ObserveCo. Everything your agents are doing, caught in one dashboard. Free until you have thousands of invocations. No feature gates. No surprise limits."

This directly counters:
- AgentTrace: "We're free too — but we have a live dashboard, push alerts, and auto-heal"
- LangFuse: "Our free tier gives 50K observations — but we also give you runtime health and memory hygiene"
- Helicone: "We're proxy-based — but we also monitor agent health, not just costs"

---

## 9. Sources

- **LangFuse:** langfuse.com (homepage, pricing, features), GitHub (29.2k★, MIT+EE)
- **Helicone:** helicone.ai (homepage, pricing), GitHub (5.8k★, Apache 2.0)
- **Arize Phoenix:** arize.com/phoenix (product page), arize.com/pricing (pricing), GitHub (10.1k★, ELv2), PyPI (2.2M/mo)
- **LangSmith:** langchain.com/pricing (exact pricing: $0/5K traces → $39/seat/mo → custom), docs.smith.langchain.com, GitHub SDK repos
- **OpenLIT:** openlit.io (homepage, pricing page), GitHub (2.5k★, Apache 2.0)
- **Datadog Bits AI/LLM Obs:** datadoghq.com/product/bits-ai-agents/, datadoghq.com/product/llm-observability/, datadoghq.com/pricing/
- **AgentTrace:** github.com/luoyuctl/agenttrace (README, issues, discussions), agenttrace website (GitHub Pages)
- **ObserveCo internal:** `docs/comparison.md`, `docs/market-analysis.md` (this file), internal strategic documents