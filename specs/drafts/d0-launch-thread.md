# D-0 Launch Thread

---

**1/6 — The hook**

I run 7 autonomous AI agents on a single M4 Mac Mini. One was silently failing for 3 months. I only found out because a user complained.

So I built ObserveCo — runtime observability for AI agents. Open source. Local. No cloud.

Let me show you what I found. 🧵

---

**2/6 — The problem**

When I finally dug into what was happening, every agent's context was growing 15% per week. Memory had duplicates and contradictions. One agent was producing garbage for 6 hours before anyone noticed.

The scariest part? This is NORMAL. Every agent operator I talk to has a version of this story.

---

**3/6 — What it does**

ObserveCo has 3 layers:

Pulse → health checks + circuit breakers. Know which agents are alive, dead, or errored. Right now.

Chisel → context compression + drift tracking. See your system prompt grow before it becomes a problem. Per-component token breakdown.

ClawForge → memory hygiene. Finds duplicates, contradictions, stale entries. Calculates a memory debt score.

---

**4/6 — The dashboard**

All of it in one local web UI. Fleet health, token profiles, error timeline, memory debt score. No cloud. No telemetry. Your data never leaves your machine.

[Screenshot: Dashboard overview]

---

**5/6 — Why I'm not selling anything**

It's MIT open source. pip install observeco. Run observeco dashboard. You'll see your agents in 60 seconds.

v0 is observation. v1.1 (2 weeks) adds self-healing. The tool that finds the problem fixes it too.

---

**6/6 — CTA**

If you run AI agents and want to actually see what they're doing:

```
pip install observeco && observeco dashboard
```

Or check the repo: https://github.com/observeco/observeco

No signup. No account. Just open source.
