# Observability Industry Pricing Research
## Cross-Company Analysis for AI Agent Observability Tool Positioning

---

## 1. Datadog

**Pricing Model:** Hybrid — per-host (infra), per-GB (logs), per-instrumented-service (APM), per-metric (custom metrics), per-event/span (APM traces). Pro and Enterprise tiers.

| Signal Type | Unit | Free Tier | Paid Start |
|---|---|---|---|
| Infrastructure | Per host/month | 5 hosts, 14-day retention | ~$15/host/mo (Pro) |
| Logs | Per GB ingested | 500 MB/day | ~$0.10/GB (indexed) |
| APM | Per host (or per span) | 1M spans/month, 50 hosts | Included with Pro hosts |
| Custom Metrics | Per metric | 100 custom metrics | ~$0.05/metric/mo |
| RUM (Browser) | Per 1K sessions | 100K sessions | ~$1.50/1K sessions |

**Upgrade Drivers:** Host count, log volume, span volume, retention period, advanced features (SLOs, RUM, CI Visibility). Each product line bills independently.

**Innovations:**
- **Bits AI / Agent Observability** — new product for LLM/agent monitoring (traces, quality, cost per agent invocation)
- **Fleet Automation** — observability agent management at scale (included in platform)
- **Observability Pipelines** — reduce log volume before ingest (cost control tool)
- **Flexible Consumption** — annual commitments with on-demand overage
- **Unified billing** across infra+APM+logs+security but each dimension still separately metered

---

## 2. New Relic

**Pricing Model:** Per-GB ingested (all signals), deprecated per-host model. "One agent, one price, one platform."

| Tier | Price | Key Limits |
|---|---|---|
| Free | $0 | 100 GB/month ingest, 1 full-access user, basic alerts |
| Starter | ~$0.30/GB ingested | Same as free but pay-as-you-go beyond 100 GB |
| Pro | ~$0.55/GB ingested | All capabilities, unlimited users |
| Enterprise | Custom | Advanced governance, compliance, AI recommendations |

**Upgrade Drivers:** Ingest volume, need for unlimited users, advanced AI, compliance (FedRAMP), data retention beyond 8 days.

**Innovations:**
- **Single metric: GB ingested** — simplest pricing in the industry. No per-host, per-user, per-service confusion
- **Unlimited users on paid plans** — removed the per-seat anti-pattern
- **AI monitoring** — built-in for LLM apps; charges same GB volume
- **NRQL** — internal query language differentiator (vs PromQL)

---

## 3. Grafana Cloud

**Pricing Model:** Per-active-series (metrics), per-GB (logs via Loki), per-GB (traces via Tempo). OSS-based (free self-hosted option exists).

| Tier | Price | Key Limits |
|---|---|---|
| Free | $0 | 3 users, 14-day retention, 10K series metrics, 50 GB logs, 50 GB traces |
| Pro | Per active series/GB | Unlimited users, 30-day retention, advanced features |
| Advanced | Pro + enhanced SLAs | 30-day retention, enterprise OSS features |
| Enterprise | Annual contract | Custom retention, SSO, compliance |

**Upgrade Drivers:** Active series count, log volume, user count (3 users free), retention beyond 14 days, need for enterprise SSO/audit.

**Innovations:**
- **OSS-first** — can run the entire stack yourself for free. Cloud is paid convenience
- **Unified Loki/Tempo/Mimir** — same query experience across signals
- **K6 (synthetic)** — baked into same platform pricing
- **Grot AI** — AI assistant included (not an upsell)
- **Consumption credits** — buy credits, spend across any signal type

---

## 4. Splunk (Cloud Platform / Observability Cloud)

**Pricing Model:** Per-GB ingested (indexed logs + metrics), deprecated per-host model. Transitioning to "workload-based" / "entity-based" pricing.

| Tier | Price | Key Limits |
|---|---|---|
| Free (Splunk Free) | $0 | 500 MB/day, single user, limited features |
| Cloud Platform | ~$1.50/GB ingested (indexed logs) | Full ingest + search |
| Observability Cloud | Per GBI (ingested) + per host (infra) | Metrics, traces, logs unified |
| Enterprise | Annual contract | On-prem or cloud, custom |

**Upgrade Drivers:** Ingest volume, search volume, need for higher retention, team collaboration, enterprise compliance.

**Innovations:**
- **Workload pricing** (Observability Cloud) — "Entities" (services) as billing unit rather than raw bytes
- **Splunk DSP** (Data Stream Processor) — process/filter data before ingest (cost control)
- **Ingest Actions** — routing, masking, filtering before indexing to reduce costs
- **HEC (HTTP Event Collector)** — pay per token/connection in some models
- Historically the most expensive per-GB, driving "Splunk bill shock" as a meme

---

## 5. Sentry

**Pricing Model:** Per-event (errors + transactions). Volume-based tiers.

| Tier | Price | Key Limits |
|---|---|---|
| Developer | Free | 5K events/month, 1 user, basic error monitoring |
| Team | $29/mo | 100K errors + 50K performance events, 3 users |
| Business | $89/mo | 500K errors + 500K performance events, unlimited users |
| Enterprise | Custom | Custom event volume, dedicated support, SAML/SSO |

**Upgrade Drivers:** Event volume, need for multiple users, session replay, traces, performance monitoring features.

**Innovations:**
- **Event-based pricing** — no host or user count, purely what you send
- **Rolling budget** — set monthly event caps, auto-reject when exceeded (predictable bill)
- **Unlimited users on Business+** — eliminates seat-count friction
- **AI features at no extra cost** — autofix, AI suggest, Seer included in plan
- **Cron monitoring + Session Replay** — included in event budget
- **Cross-platform** — errors across mobile, web, backend all under same event budget

---

## 6. Honeycomb

**Pricing Model:** Per-event (traces + structured logs) + per-data-point (time series metrics). Flat rate per event tier. No per-seat charge.

| Tier | Price | Key Limits |
|---|---|---|
| Free | $0 | 20M events/mo + 100M data points |
| Pro | $130/100M events (starting) | Up to 1.5B events, 7.5B data points |
| Enterprise | Custom EPY (Events Per Year) | 10B EPY base, volume discounts, extended retention, frontend observability |

**Upgrade Drivers:** Event volume, need for longer retention (>60 days), SAML/SSO, frontend observability, advanced alerting.

**Innovations:**
- **No per-seat pricing** — unlimited users on all paid plans
- **Unlimited querying** — no charge for running queries (unlike Splunk's search-based pricing)
- **Burst Protection** — if daily volume spikes 2x above daily target, excess not counted against limit (3 free burst days/month)
- **Calendar month reset** — simple, no rollover
- **Column-based schema** — 2000 attributes per event, no extra charge for high cardinality
- **Enterprise EPY model** — annual event commitment with volume discounts
- **Transparent pricing** — published per-100M event rate ($130)
- **MCP integration** — Honeycomb builds MCP servers, letting AI agents query their own observability data

---

## 7. Chronosphere

**Pricing Model:** Per-active-metric-series (metrics) + per-span/GB (traces). Enterprise-only.

| Tier | Price | Key Limits |
|---|---|---|
| Free | N/A (no free tier) | — |
| Starter/Pro | Custom quote | Based on metric cardinality, trace volume |
| Enterprise | Annual contract | Custom, includes private cloud option |

**Upgrade Drivers:** Metric cardinality, trace volume, need for private/on-prem deployment, advanced data control.

**Innovations:**
- **Cardinality-aware pricing** — charges based on unique metric label combinations (active series) not raw metrics count
- **Data Control Plane** — decouple data routing from storage; filter/transform before sending to billing buckets
- **Downsampling engine** — auto-rollup old data to reduce storage costs
- **M3DB heritage** — built by former Uber SREs who solved massive-scale metric problems
- **"Predictable pricing" as core value prop** — contrasting with Datadog/Splunk bill shock
- **Bare-metal/self-hosted option** — for orgs that won't use cloud

---

## Cross-Industry Patterns & Takeaways

### Dominant Pricing Units
1. **Per-event/span (volume)** — Honeycomb, Sentry, Datadog (APM), Chronosphere (traces)
2. **Per-active-series/cardinality** — Grafana (metrics), Chronosphere (metrics), Datadog (custom metrics)
3. **Per-GB ingested (logs)** — Datadog, Grafana, Splunk, New Relic
4. **Per-host/entity (legacy)** — Datadog (infra), Splunk (legacy) — being phased out

### Patterns to Adopt for ObserveCo

1. **One simple metric** — GB ingested covers everything (New Relic).
   > For ObserveCo: **per agent invocation** or **per trace span** — one billing unit.

2. **No per-seat pricing** (Honeycomb, New Relic Pro+, Sentry Business+).
   > Don't charge per developer. Charge per agent run or per observation ingested.

3. **Burst Protection** (Honeycomb).
   > 10x agent volume during a load test shouldn't 10x the bill. Cap daily overage.

4. **Unlimited querying** (Honeycomb).
   > Replaying agent decision traces is free. Storing them long-term costs.

5. **OSS free tier** (Grafana).
   > Open-source SDK, paid cloud backend. Best marketing funnel in observability.

6. **Cardinality-awareness** (Chronosphere).
   > Don't penalize users for adding informative dimensions (tool name, model, prompt template).

7. **Consumption credits** (Grafana).
   > One pool of credits for traces, evaluation scores, cost data, tool call logs.

8. **Avoid "bill shock"** (the #1 competitive pain point).
   > Transparent pricing, burst protection, auto-throttling on overage (Sentry model).

### Pricing Model Recommendation for ObserveCo

```
Primary unit:   Per agent trace span / per agent invocation
Free tier:      10K agent invocations/month, 14-day retention
Paid:           Flat rate per 10K invocations (e.g., $5/10K)
                - No per-seat charge
                - 30-day retention standard
                - 90-day retention at 2x rate
Differentiator: Burst protection, unlimited querying, no cardinality penalty
Positioning:    "Predictable, volume-based pricing for agent operations"
                NOT per-host or per-user
