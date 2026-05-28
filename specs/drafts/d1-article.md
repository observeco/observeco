# Your AI agents are getting dumber. Here's how to find out before your users do.

**Subtitle:** I spent 6 months running 7 autonomous agents on one Mac Mini. One was failing silently. A user told me. I built ObserveCo so you never hear it from a user.

---

## The Fear

I run 7 AI agents on a single M4 Mac Mini. They handle my email, my calendar, my research, my code reviews, my deal scouting, my knowledge base. They talk to each other through signals. They schedule tasks via cron. They run around the clock.

For three months, one of them was silently producing broken output. Not crashing — not throwing errors that would show up in a log somewhere. Just... wrong. Subtly wrong. Plausible-looking garbage that passed every automated check but failed every human test.

I only found out when a user told me.

That moment — discovering your agent has been broken for hours and you had no idea — is the worst feeling in AI engineering. It's not the failure itself. It's the gap between when it broke and when you found out. Minutes, hours, sometimes days.

Your agents could be degrading right now. You wouldn't know.

## The Investigation

When I finally dug into what was happening, I found three things.

**Context was growing 15% per week.** Every component — tool definitions, memory files, notes, command shortcuts, skill descriptions — was being loaded on every single call. No pruning. No awareness of what was actually needed. The system prompt was 10,000 tokens before the agent even started thinking. Some agents were pushing 200,000 tokens per turn.

**Memory had duplicated entries.** Seven copies of the same fact. Two contradictions — the agent had been told opposite things and was confused about which was true. A stale entry from three months ago that the agent still treated as current. Nobody was watching. Nobody even knew there was a place to look.

**One agent had been failing for 6 hours before I noticed.** Not crashing. Producing output that looked right but wasn't. The failure wasn't dramatic — it was a slow degradation that accumulated over time. By the time I found out, the damage was done.

I was spending roughly $120 a day on API tokens. Not because my agents were doing too much work. Because they were doing things I never asked them to do, loading context they didn't need, and processing tokens that were wasted on duplicates and contradictions. I couldn't see any of it. I was paying for a black box.

## What I Built

ObserveCo is a tool that tells you if your AI agents are working, what they're doing, and where your money goes.

It runs on your machine. One install. No cloud. No accounts. No telemetry.

**[Screenshot 1: Fleet view — agent cards with health status, token bars, error badges]**

The fleet view shows every agent you're running. Green dot means working. Red dot means something's wrong. Yellow means degraded — still running, but not healthy. You see the status of every agent in one place, updated every 30 seconds.

**[Screenshot 2: Token breakdown — bar chart showing what's inside an agent's context]**

The token breakdown shows you exactly what's inside each agent's system prompt. How much is identity. How much is skills. How much is memory. How much is tools. How much is guidance. You see the numbers. You see the proportions. You see what's eating your tokens.

**[Screenshot 3: Drift chart — 7-day line showing context growth]**

The drift chart shows whether each component is growing, stable, or shrinking over 7 days. When you see a steady upward line, you know context is accumulating. You can see it before the bill arrives.

**[Screenshot 4: Error history — annotated timeline of failures]**

The error history shows every failure, when it happened, and what went wrong. Not just "error" — but the actual error message, categorized by type. Timeout. Connection refused. HTTP 500. Resource not found. You see what broke, not just that something broke.

**[Screenshot 5: Circuit breaker — tripped state with cooldown]**

The Safety Guard trips when an agent fails repeatedly — 3 consecutive failures, then it stops probing and enters cooldown. It prevents alert fatigue and keeps your logs clean. Without it, a dead agent generates 2,880 checks and 5,760 DB writes per day. With it: ~8 checks, ~16 writes. 99.7% reduction.

**[Screenshot 6: Memory garden — duplicates, contradictions, debt score]**

The Memory Garden finds duplicates, contradictions, and stale entries in your agent's memory. It calculates a debt score. You see what needs cleaning before it causes problems.

**[Screenshot 7: In-dashboard alerts — discovery gap badges]**

The in-dashboard alerts show every circuit trip, drift breach, and heartbeat miss. But here's the design: each alert carries a discovery gap badge showing how late you found out.

> *"Kepler circuit tripped — happened 03:15 · You discovered 07:00 (when you opened dashboard) — 3h 45m gap"*

A cumulative banner totals the undiscovered downtime. This number grows the longer you go between dashboard visits. It's the pain point that makes push alerts worth paying for.

**[Screenshot 8: Dashboard overview — all panels visible]**

All of it in one place. Fleet health, token profiles, error timeline, memory debt, alerts. A single screen that tells you everything about your agents.

**[Terminal GIF: pip install observeco → observeco dashboard → agents visible in 15 seconds]**

And if you prefer the command line, every feature is also available as a CLI command. `observeco pulse check` shows agent health. `observeco chisel trim` compresses your system prompt. `observeco clawforge garden` finds memory problems.

## What Everyone Else Is Missing

There are dozens of monitoring tools on the market. Datadog, Grafana, LangSmith, LangFuse, LangWatch, Helicone, Braintrust.

None of them understand agents.

They understand services. They understand HTTP requests. They understand log lines. But agents are not services. They're reasoning systems with state, context, and autonomy. The failure mode of an agent isn't "HTTP 500." It's "the agent has a 200K context window and it's losing the plot." It's "memory has 7 duplicates and 2 contradictions and the agent is confused about which one is true." It's "context grew 15% last week and nobody noticed."

The tools that do understand agents — LangSmith, LangFuse — are cloud-based. They send your data to someone else's servers. If your agents handle sensitive information, if you care about data privacy, if you run offline — they don't work.

ObserveCo is the opposite. Everything runs on your machine. Your data never leaves your laptop. The dashboard renders from a local server that connects to a local database. No cloud. No accounts. No telemetry.

This is not a hosted service. It's a tool you install and own.

## What Ships When

I open-sourced it under MIT. The code is on GitHub. The package is on PyPI.

**v0.1 is what's live today.** 12 features — fleet view, pulse check, safety guard, token breakdown, drift tracking, error history, heal button, in-dashboard alerts, memory garden, full CLI. All local. All free. `pip install observeco && observeco dashboard` — you'll see your agents in 60 seconds.

**v0.2 (D+3) adds auto-heal + extended history.** The watch daemon detects crashes and recovers agents in ~5 seconds. Layer 1 (reactive) handles ~75% of failures. Layer 2 (proactive) tracks degradation trends — memory bloat, stuck agents, hallucination drift — and pre-empts the crash before it happens. Together: 93% of all failures resolve without human touch. Extended history keeps all data from day of install instead of pruning to 7 days. Your trend baselines compound.

**v0.3 (D+7) adds Chisel compression + push alerts.** System prompt compression: Lite (free, 22% savings) and Full (Pro, 35% savings). Every SOUL.md edit triggers auto-compression. Push alerts deliver to Telegram, webhook, or email — zero discovery gap. But only when auto-heal can't fix it. Routine crashes heal silently. Stuck crashes buzz immediately.

**v1.1 (D+14) adds the OpenClaw runtime plugin.** `@observeco/clawforge-plugin` hooks into OpenClaw ContextEngine. Agents load only what they need per turn instead of loading everything every time. The tool that sees the problem is the tool that fixes it.

Every yellow banner in v0.1 ends with the exact command that will work in v1.1. Users learn the syntax by reading. The transition from "see" to "fix" is invisible.

```bash
pip install observeco && observeco dashboard
```

You'll see your agents in under 60 seconds.

---

*Sean Foo. I run 7 AI agents. I built a tool to see what they're doing. Now you can too.*
