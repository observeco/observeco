# GitHub Discussion — Beta Testers Wanted

---

**Category:** Announcements
**Title:** 🧪 Beta testers wanted — ObserveCo agent observability dashboard

**Body:**

I'm looking for 5-10 beta testers for **ObserveCo** — an open-source, local-first dashboard for AI agent observability.

### What it does

Installs in 60 seconds. Shows you:
- Which agents are alive, degraded, or dead (pulse check every 30s)
- Where your tokens are going — per-component breakdown (skills, memory, tools, identity, guidance)
- 7-day drift trends — catch context bloat before it breaks your agent
- Error timeline with annotated events (not just raw logs)
- Circuit breakers to stop cascade failures
- One-click heal button

Works with Hermes, OpenClaw, LangChain, CrewAI, Ollama, or any framework via `observeco agent add`.

### Try it

```
pip install observeco[dashboard] && observeco dashboard
```

### What I need feedback on

1. **Install experience** — did `pip install` work cleanly?
2. **Agent detection** — did it find your agents automatically?
3. **Dashboard UX** — what's confusing? What's missing? What's great?
4. **Edge cases** — any crashes, errors, or unexpected behaviour?
5. **What would make you pay for it?** (Even though the free tier has everything)

### Respond here or DM

Post in this thread or message me directly. I'll respond to every report personally.

Thanks for helping ship this 🚀
