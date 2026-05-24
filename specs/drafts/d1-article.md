# Your AI agents are getting dumber. Here's how to find out before your users do.

**Subtitle:** I spent 6 months running 7 autonomous agents on one M4 Mac Mini. One was failing silently. A user told me. I built ObserveCo so you never hear it from a user.

---

## The Fear

I run 7 AI agents on a single M4 Mac Mini. Hermes, Kepler, Hound, Dreamer, Aleph, PA, and an orchestrator. They communicate via signals. They trigger on file changes. They schedule tasks via cron.

For three months, one of them was silently producing broken output. I only found out when a user told me.

That feeling — discovering your agent has been broken for hours and you had no idea — is the worst feeling in AI engineering. It's not the failure itself. It's the gap between when it broke and when you found out.

Your agents could be degrading right now. You wouldn't know.

## The Investigation

When I finally dug into what was happening, I found three things:

1. **Context was growing 15% per week.** Every component — tool definitions, memory, notes, shortcuts — was being loaded on every call. No pruning. No awareness. The system prompt was 10,000 tokens before the agent even started thinking.

2. **Memory had duplicated entries.** Seven copies of the same fact, two contradictions, and a stale entry from 3 months ago that the agent still treated as current.

3. **One agent had been failing for 6 hours before I noticed.** Not crashing — producing plausible-looking garbage. The circuit breaker was a mental exercise, not an automated check.

I was burning roughly $120/day in wasted tokens. Not because the agents were doing too much. Because they were doing things I never asked them to do, and I had no visibility into any of it.

## What I Built

ObserveCo is a runtime observability tool for AI agents. It runs locally. No cloud. No telemetry. One pip install.

> **[Fleet view screenshot — 7 agents with alive/dead/error status]**

It has four layers:

**Pulse** — Agent health monitoring with configurable checks. Alive/dead/error per agent, zero config for Hermes users. Circuit breaker with auto-cooldown and manual reset.

> **[Circuit breaker screenshot — N-failure trip with cooldown timer]**

**Chisel** — Context compression. Shows you exactly what's in every agent's system prompt. Per-component token breakdown. Drift tracking over 7 days — so you can see context growing before it becomes a problem.

> **[Drift chart screenshot — 15% week-over-week context growth]**

**ClawForge** — Memory hygiene. Finds duplicates, contradictions, stale entries. Calculates a memory debt score. Shows you what to prune.

> **[Memory debt dashboard screenshot — grade scores and suggestions]**

**Dashboard** — Local web UI. Fleet health, token profiles, error timeline, memory debt score. All in one page.

> **[Dashboard overview screenshot — all panels visible]**

## What Everyone Else Is Missing

There are dozens of observability tools on the market. Datadog, Grafana, LangSmith, LangFuse, LangWatch, Helicone, Braintrust.

None of them understand agents.

They understand services. They understand traces. They understand logs. But agents are not services — they're reasoning systems with state, context, and autonomy. The failure mode of an agent isn't "HTTP 500." It's "the agent has a 200KB system prompt and it's losing the plot."

The tools that DO understand agents (LangSmith, LangFuse) are cloud-based. They send your data to someone else's servers. If you care about data privacy, latency, or running offline, they don't work.

ObserveCo is the opposite. Everything runs locally. Your data never leaves your machine. The dashboard renders from a Python server that connects to your local SQLite database.

This is not a hosted service. It's a tool you install and own.

## The Future

I open-sourced it under MIT. The code is on GitHub. The package is on PyPI.

**v0** is observation mode. You can see everything your agents are doing. You can see when they're drifting. You can see when they're failing.

**v1.1** (coming in ~2 weeks) will add self-healing. The tool that identifies the drift will be the same tool that fixes it.

```
pip install observeco && observeco dashboard
```

You'll see your agents in under 60 seconds.

---

*Sean Foo. I build agents. I build tools for agents. This is one of them.*
