# ObserveCo — Distribution Drafts (1000x Version)

**These are written to hit Token Anxiety, Ignorance Dread, and Competence Shame — not feature lists.**
**Every draft assumes: zero credibility, zero audience, zero stars. The only move is authenticity.**

---

## 1. Show HN Post (The Most Important 2,000 Words of the Launch)

**Title:** Show HN: My agents were burning $120/day. I built a dashboard to watch them.

**Body:**

I run 7 AI agents on one Mac Mini. They write code, manage tasks, talk to each other. For six months I assumed they were fine. They weren't.

One agent had been producing broken output for three hours before a user told me. Another was burning $40/day on tokens I couldn't trace — tool definitions, memory loops, heartbeat calls I'd never authorized. My system prompts were growing 15% per week. Nobody was watching.

I tried the existing tools. Datadog wanted $15/host/month and couldn't see inside an agent's context. Grafana needed a Prometheus server I didn't want to maintain. LangSmith was cloud-only and LangChain-locked.

So I built something that works on my machine — and open-sourced it.

**What it does:**
- Discovers your agents automatically (Hermes, OpenClaw, LangGraph, CrewAI, custom)
- Shows fleet health: green/alive, red/dead, yellow/degraded — at a glance
- Breaks down token usage per agent, per component (identity, memory, skills, tools, guidance)
- Tracks context drift over 7+ days — see exactly which agents are growing and how fast
- Circuit breaker: stops cascading failures when an agent crashes repeatedly
- Memory hygiene: finds duplicates and contradictions in MEMORY.md
- Observation mode: detects crash patterns, drift, memory debt — and suggests exactly what to run

**One command, 60 seconds:**

```
pip install observeco && observeco dashboard
```

No Docker. No API keys. No cloud. Every bit of data stays on your machine.

**Why this is different:**

| Tool | Works offline | Sees agent context | Locally fixable | Open source | Cost |
|------|-------------|-------------------|----------------|-------------|------|
| Datadog | ❌ | ❌ | ❌ | ❌ | $15+/host/mo |
| Grafana+Prome | ⚠️ requires setup | ❌ | ❌ | ✅ | Free + infra |
| LangSmith | ❌ | ⚠️ LangChain only | ❌ | ❌ | $59/mo |
| **ObserveCo** | ✅ | ✅ Hermes+OpenClaw+any | ✅ (v1.1) | ✅ MIT | Free |

**What's next (v1.1, ~2 weeks):** Self-healing execution, living snapshot docs, MCP agent queries. The observation mode you'll see today shows you EXACTLY what auto-heal will do — every yellow banner is a pre-order.

https://github.com/observeco/observeco

---

## 2. X Article (Long-Form, ~3,000 Words, Published D-1)

**Title:** Your AI agents are getting dumber every day. Here's how to catch it before your users do.

**Format:** X Article, 3,000 words, 7 embedded visuals

**Full text:**

### 1. The Moment I Found Out

I run 7 AI agents on one Mac Mini. They write code, manage my infrastructure, watch my servers, and talk to each other. For six months, I assumed they were working fine.

They weren't.

The first sign was a user complaint. "This output is wrong. Has it been wrong all week?" I checked the logs. My coding agent had been producing broken code for three hours. The agent was running. It was returning responses. Every single one was garbage. Nobody knew.

That's when I realized: my agents could be completely broken and I'd never know until someone told me.

[SCREENSHOT 1: Fleet view showing 7 agents, 2 dead, 1 error]

### 2. What I Found When I Dug In

Once I started looking, the problems were everywhere:

- **15% context growth per week.** My agents' system prompts were expanding every session. Nobody was trimming them. The "memory" section of Kepler was 5,600 tokens — it should have been 1,800.

[SCREENSHOT 2: Token breakdown showing Kepler's memory at 5,600 tokens, 3x normal]

- **$120/day in wasted tokens.** OpenClaw sends tool definitions, memory, notes, commands, and script locations on every call. My agents were burning money on heartbeats, cron checks, and function calls that didn't need an LLM. I was paying for work I never authorized.

[SCREENSHOT 3: Drift chart showing 7-day context growth line]

- **Memory was a mess.** Kepler's memory file had 7 duplicate entries and 2 contradictions. The agent was confused by its own history — and I had no way to know.

[SCREENSHOT 4: Memory garden showing 7 duplicates, 2 contradictions]

- **Cascading failures.** When one agent crashed, it dragged down others. By the time I noticed, three agents were down. The cascade was silent.

[SCREENSHOT 5: Circuit breaker showing 3/3 failures, 300s cooldown]

### 3. The Existing Tools Don't Get It

I tried Datadog. It's built for servers, not agents. It can't see inside system prompts. It doesn't understand tokens. And it costs $15/host/month for cloud-only data.

I tried Grafana. I'd still be setting up exporters. The "two-hour setup" is optimistic for anyone who just wants to see if their agents are alive.

I tried LangSmith. Cloud-only. LangChain-only. $59/month.

Every tool assumes your agents are servers. They're not. Servers you ping. Agents you talk to. Servers go down. Agents get dumber. These are fundamentally different problems with fundamentally different solutions.

### 4. What I Built

So I built something that runs on my machine, discovers my agents automatically, and shows me exactly what's happening — in under 60 seconds.

[TERMINAL GIF: pip install observeco && observeco dashboard → browser opens with 7 agents visible in 15 seconds]

One command. No Docker. No API keys. No cloud.

It shows you:
- **Fleet health** — green dots, red dots, yellow warnings
- **Token breakdown** — exactly where every token goes
- **Drift tracking** — context changes over time
- **Error timeline** — last crash, last trip, last warning
- **Memory hygiene** — duplicates, contradictions, stale files
- **Observation mode** — detects problems and shows you exactly what to run

[SCREENSHOT 6: Yellow observation banner — "Agent Kepler: 3 memory errors detected. Suggested: restart with memory cap"]

The observation banners are the most important part of the product. They tell you EXACTLY what's wrong and EXACTLY what command would fix it. The only thing missing is permission to execute. That's v1.1.

### 5. Why This Matters

The scariest part of running AI agents isn't that things break. It's that things break silently, and by the time you notice, your users have already lost trust.

A monitoring tool that shows you a red dot and says "go fix it" is not good enough for AI agents. By the time you see the red dot, your agent has been producing bad output for hours. For agent systems, the gap between failure and awareness is measured in users, not seconds.

### 6. The Roadmap

v0 is out now. Observation mode. Dashboard. CLI. Free. Open source. MIT.

**v1.1 in ~2 weeks:** Self-healing execution. The observation mode you see today shows you exactly what auto-heal will do. When v1.1 ships, it just does it.

Living snapshot documentation. Your dashboard data, rendered as markdown + SVGs. Documentation that writes itself.

MCP agent queries. Your other agents can ask about each other's health. Programmatic observability.

### 7. Try It

```
pip install observeco && observeco dashboard
```

60 seconds. Local-first. No cloud. No telemetry. No "talk to our sales team."

If you run AI agents — even one — you'll know what they're actually doing for the first time.

https://github.com/observeco/observeco

---

## 3. X Thread (D-0 Launch Post)

**1/** Your AI agents could be broken right now and you'd have no idea.

No log. No alert. Just suddenly dumber responses.

**2/** I found out when a user complained. My agent had been producing garbage for 3 hours. Running. Working. Wrong.

**3/** I checked the tokens. $120/day going to tool definitions, memory loops, heartbeat calls I'd never authorized.

No visibility. No control.

**4/** So I built a dashboard that sees everything.

Fleet health. Token breakdown. Context drift. Circuit breakers. Memory hygiene.

In under 60 seconds. No cloud. No Docker. MIT.

pip install observeco && observeco dashboard

**5/** Every dashboard shows yellow banners: "3 memory errors detected. Suggested: restart with memory cap."

The tool knows exactly what's wrong. It just won't fix it. (Yet.)

v1.1 in ~2 weeks: auto-heal execution. The banners are pre-orders.

**6/** I wrote the full story — 3,000 words, 7 screenshots, all the data I found.

[link to X Article]

**7/** https://github.com/observeco/observeco

---

## 4. Reddit: r/LocalLLM

**Title:** My 7 AI agents were slowly getting dumber. I built a dashboard to see what was happening.

**Body:**

I run 7 AI agents on one Mac Mini. They talk to each other, write code, manage tasks.

For months I'd notice they'd get progressively worse at basic things. Context drift. Memory confusion. Silent crashes.

Turns out one agent had 7 duplicate entries and 2 contradictions in its memory file. Another was burning $40/day on tokens I couldn't trace. The system prompts were growing 15% per week.

I could have bought Datadog or set up Grafana. But those tools don't understand agents — they understand servers. Agents get dumber, servers go down. Different problems.

So I built a dashboard that discovers agents automatically and shows you what's happening. Works with Hermes, OpenClaw, LangGraph, CrewAI, or anything with a health endpoint.

pip install observeco and run `observeco dashboard`. You'll see your agents in under 60 seconds. MIT. Free. All local.

Also wrote a full post about what I found: [link to X Article]

---

## 5. The Ghost Comment (D-7, Anonymous Reddit Account)

Post this on the r/openclaw pricing thread:

> *"I built a tool that shows you exactly where every token goes. Per-agent, per-tool, per-session breakdown of costs. It runs locally — no cloud, no data leaves your machine. Works with OpenClaw, Hermes, any agent setup. Happy to share early access if you want to try it — DM me."*

**Goal:** 3-5 DMs. Those become the first beta testers. They're not users who were sold to — they're people who ASKED for it.

---

## 6. Appendix: Tone Guide

| Do | Don't |
|----|-------|
| "I built this because my agents were breaking" | "We are ObserveCo, a company building..." |
| "pip install observeco" | "Sign up for early access" |
| "MIT. Free. Open source." | "Free trial. Limited time offer." |
| "The tool shows you what's wrong" | "Our patented AI-powered observability platform" |
| "Here's what I found running 7 agents" | "Here's why you need observability" |
| "v1.1 in ~2 weeks: auto-heal" | "Check out our product roadmap" |
