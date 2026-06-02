# Reddit r/AI_Agents — Beta Tester Call

---

**Title:** I built an open-source dashboard that shows what your AI agents are actually doing with every token. Looking for beta testers.

**Body:**

Been running AI agents for a while (Hermes, OpenClaw, some LangChain stuff). Kept running into the same problem: **I couldn't tell if my agents were working until they broke.**

Not like — "is the server up" working. Like:
- Is my agent's context bloating because a skill is growing out of control?
- Am I spending $50/mo on tokens I don't need?
- When did that memory drift start? Was there a trigger?
- Why did my agent suddenly start hallucinating?

So I built: **ObserveCo** (github.com/observeco/observeco)

It's:
- 🆓 MIT — free forever, open source
- 💻 Local — pip install, runs on your machine, no cloud
- ⚡ 60 seconds to first health data

What it does:
- **Pulse check** every 30s — is your agent alive, degraded, or dead?
- **Token breakdown** — exactly what's in your agent's context (skills, memory, tools, identity)
- **Drift tracking** — 7-day trend so you catch context bloat before it's a problem
- **Circuit breakers** — N-failure auto-trip so one bad agent doesn't break the fleet
- **Heal button** — one-click restart for dead agents
- **Error timeline** — not just logs, annotated events with context snapshots

Works with Hermes, OpenClaw, LangChain, CrewAI, Ollama — any framework.

**What I need from beta testers:**
- `pip install observeco && observeco dashboard` — does it work?
- Does it find your agents automatically?
- What breaks? What's confusing? What's missing?
- 5-minute feedback form after you try it

**Interested?**
- Install: `pip install observeco && observeco dashboard`
- GitHub: https://github.com/observeco/observeco
- Or DM me and I'll help you get set up

Appreciate any eyes on it.
