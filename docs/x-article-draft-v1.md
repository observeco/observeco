# Your AI agents are getting dumber. Here's how to tell — before your users do.

**Title:** Your AI agents are getting dumber every day. Here's how to catch it before your users do.

**Format:** X Article (~2,500 words, 4 embedded screenshots)

---

## 1. The moment I found out

I run 39 AI agents on one Mac Mini. They write code, manage infrastructure, watch my servers, and talk to each other. For months, I assumed they were working fine.

They weren't.

The first sign was a user complaint. "This output is wrong. Has it been wrong all week?" I checked the logs. My coding agent had been producing broken code for three hours. The agent was running. It was returning responses. Every single one was garbage. Nobody knew.

That's when it hit me: my agents could be completely broken and I'd never know until someone told me.

**This is the scariest problem in AI operations right now.** Not that things break. That things break silently — and by the time you notice, your users have already lost trust.

---

## 2. What I found when I finally looked

Once I started digging, the problems were everywhere.

**28 agents alive, 11 down.** From 39 total. That's a 28% failure rate I was completely blind to. Multiple agents marked with "Guard: possible stale" — running, but producing who-knows-what for hours.

[SCREENSHOT: Fleet dashboard — 28 alive, 11 down, warning banners visible]

**$112.45 in token spend I couldn't trace.** One agent alone (hermes-agent) accounted for 91.5% of the total. The cache hit rate was 3.9% — meaning 96% of every prompt was being recomputed from scratch. Tool definitions, memory loops, heartbeat calls I'd never authorized. All of it burning money.

[SCREENSHOT: Token Analytics — $112.45, hermes-agent 91.5%, 3.9% cache hit rate]

**79,826 tokens of context bloat in a single agent.** The system identified it as "critically bloated." Another agent showed "+709.8% token growth this week" — context expanding 8x in seven days with nobody trimming it.

**The "Memory Garden" found 0 duplicates and 0 contradictions (today).** But the system needed to scan for them. The fact that a dedicated tool needed to check meant nobody was looking before.

[SCREENSHOT: Brain Analysis — hermes-agent critically bloated at 79,826 tokens]

These aren't edge cases. Every agent operator I've talked to has a version of this story. The only difference is how long they went without knowing.

---

## 3. The existing tools don't get it

I tried Datadog. It's built for servers, not agents. It can't see inside system prompts. It doesn't understand tokens. And it costs $15/host/month for cloud-only data.

I tried Grafana. I'd still be setting up exporters.

I tried LangSmith. Cloud-only. LangChain-only. $59/month.

Every tool assumes your agents are servers. They're not. Servers you ping. Agents you talk to. Servers go down. Agents get **dumber**. These are fundamentally different problems requiring fundamentally different solutions.

---

## 4. What I built

So I built something that runs on my machine, discovers my agents automatically, and shows me exactly what's happening — in under 60 seconds.

```bash
pip install observeco && observeco dashboard
```

One command. No Docker. No API keys. No cloud. Every bit of data stays on your machine.

**What it shows you:**

| Feature | What it catches |
|---------|----------------|
| **Fleet Health** | 28 alive, 11 down — at a glance. Status dots per agent. Green/yellow/red. |
| **Token Breakdown** | Which agent is burning money. Per-agent, per-component. $112.45 traced to source. |
| **Drift Tracking** | Context growing +709.8% in a week. See bloat before it becomes a budget line item. |
| **Error Timeline** | Last crash, last trip, last warning — with plain-English verdicts. |
| **Memory Analysis** | Duplicates, contradictions, stale content. Keep your agent's knowledge clean. |
| **Auto-Heal** | Restarts crashed agents automatically. Proactive maintenance fixes bloat before failure. |
| **Circuit Breaker** | Stops cascading failures when an agent crashes repeatedly. |
| **Push Alerts** | Telegram notifications when agents go down or drift exceeds thresholds. |

[SCREENSHOT: Auto-Heal page — with configuration options and heal event log]

**The observation banners are the most important part.** When the dashboard detects a problem — "3 memory errors detected," "hermes-agent critically bloated at 79,826 tokens" — it tells you exactly what command would fix it. The only thing missing is permission to execute. That's coming.

---

## 5. Why this matters

A monitoring tool that shows a red dot and says "go fix it" is not good enough for AI agents. By the time you see the red dot, your agent has been producing bad output for hours.

For agent systems, the gap between failure and awareness is measured in **users**, not seconds.

The scariest data point from my own fleet: **I had 11 dead agents and didn't know.** That's 28% of my workforce silently failing. If that was a human team, it would be a crisis. With AI agents, it's just Tuesday.

---

## 6. What's coming

**v0.3 is out now.** Fleet dashboard, token analytics, brain analysis, drift tracking, error history, circuit breaker, auto-heal, push alerts. 18 features. All local. All free.

**v1.1 (~2 weeks):** Self-healing execution — the observation banners you see today will fire automatically. Living documentation: your dashboard data rendered as markdown. MCP agent queries: your agents can ask about each other's health programmatically.

---

## 7. Try it

```bash
pip install observeco && observeco dashboard
```

60 seconds. Local-first. No cloud. No telemetry. No "talk to our sales team."

If you run AI agents — even one — you'll know what they're actually doing for the first time.

https://github.com/observeco/observeco

MIT. Free. Open source. No signup.

---

*I run 39 agents on a Mac Mini. This is what I built to keep them honest. The full story, screenshots, and install command above.*