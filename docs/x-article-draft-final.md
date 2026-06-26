# Your AI agents are getting dumber. Here's how to tell — before your users do.

**Format:** X Article (~2,200 words, 4 embedded images)

---

## 1. The moment I found out

I run 39 AI agents on one Mac Mini. They write code, manage infrastructure, watch my servers, and talk to each other. For months, I assumed they were working fine.

They weren't.

A user complained. "This output is wrong. Has it been wrong all week?" I checked the logs. My coding agent had been producing broken code for three hours. Running. Returning responses. Every single one garbage. Nobody knew.

My agents could be completely broken and I'd never know until someone told me.

**This is the scariest problem in AI operations.** Not that things break. That things break silently — and by the time you notice, your users have already lost trust.

---

## 2. What I found when I finally looked

Once I started digging, the problems were everywhere.

**[IMAGE: visual-card-fleet.png — Fleet overview card showing 28 alive, 11 down, 39 agents]**

**28 alive, 11 down.** From 39 total. That's a 28% failure rate I was completely blind to. Multiple agents marked "Guard: possible stale" — running, but producing who-knows-what for hours.

---

**$112.45 in token spend I couldn't trace.** One agent alone accounted for 91.5% — $102.90. The cache hit rate was 3.9%. That means 96% of every prompt was being recomputed from scratch. Tool definitions, memory loops, heartbeat calls I'd never authorized. All burning money.

**[IMAGE: visual-card-cost.png — Cost card showing hermes-agent at 91.5% spend, $102.90]**

---

**79,826 tokens of context bloat in a single agent.** The system flagged it "critically bloated." Another agent showed +709.8% token growth in a week — context expanding 8x in seven days with nobody trimming it.

**[IMAGE: visual-card-bloat.png — Bloat card showing hermes-agent at 79,826 vs other agents]**

---

These aren't edge cases. Every agent operator I talk to has this story. The only difference is how long they went without knowing.

---

## 3. The existing tools don't get it

I tried Datadog. Can't see inside system prompts. Understands servers, not agents. $15/host/month.

I tried Grafana. Still setting up exporters.

I tried LangSmith. Cloud-only. LangChain-only. $59/month.

Every tool assumes agents are servers. They're not. Servers you ping. Agents you talk to. Servers go down. Agents get **dumber**. Different problems need different solutions.

---

## 4. What I built

So I built something that runs on my machine, discovers my agents automatically, and shows me exactly what's happening — in under 60 seconds.

```
pip install observeco && observeco dashboard
```

One command. No Docker. No API keys. No cloud.

**What it shows you:**

| Feature | What it catches |
|---------|----------------|
| **Fleet Health** | 28 alive, 11 down — at a glance. Green/yellow/red. |
| **Token Breakdown** | Which agent is burning money. Per-agent, per-component. |
| **Drift Tracking** | Context growing 8x in a week. See bloat before it's a budget line. |
| **Error Timeline** | Last crash, last warning — plain-English verdicts. |
| **Memory Analysis** | Duplicates, contradictions, stale content in memory. |
| **Auto-Restart** | Detects crashes and restarts automatically. No human needed. |
| **Circuit Breaker** | Stops cascading failures when an agent crashes repeatedly. |
| **Push Alerts** | Telegram when agents go down or drift exceeds thresholds. |

**[IMAGE: visual-card-heal.png — Auto-Heal roadmap card: v0.3 available, v1.1 coming]**

**The observation banner is the key.** When the dashboard flags a problem — "79,826 tokens — critically bloated" — it tells you exactly what command would fix it. The only thing missing is permission to execute. That's coming in v1.1.

---

## 5. Why this matters

A red dot that says "go fix it" isn't good enough. By the time you see the red dot, your agent has been producing bad output for hours.

For agent systems, the gap between failure and awareness is measured in **users**, not seconds.

The scariest number from my own fleet: **11 dead agents and I didn't know.** That's 28% of my workforce silently failing. If this was a human team, it would be a crisis. With AI agents, it's Tuesday.

---

## 6. What's coming

**v0.3 — out now.** Fleet health, token analytics, brain analysis, drift tracking, error history, circuit breaker, auto-restart, push alerts. 18 features. All local. All free.

**v1.1 — ~2 weeks.** Self-healing execution — the observation banners fire automatically. Living documentation: dashboard data rendered as markdown. MCP agent queries: your agents ask each other about their health.

**v1.5 — next.** OpenClaw runtime plugin. CI gates. Eval capture.

---

## 7. Try it

```
pip install observeco && observeco dashboard
```

60 seconds. Local-first. No cloud. No telemetry. No sales team.

If you run AI agents — even one — you'll know what they're actually doing for the first time.

https://github.com/observeco/observeco

MIT. Free. Open source. No signup.

---

*I run 39 agents on a Mac Mini. This is what I built to keep them honest. The full story, 4 screenshots, and install command above.*