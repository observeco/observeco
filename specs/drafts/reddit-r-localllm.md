# Reddit r/LocalLLM — Beta Tester Call

---

**Title:** Your local agents are burning tokens you can't see. This free dashboard shows you exactly what.

**Body:**

If you run local agents (Ollama, llama.cpp, anything self-hosted), you probably have the same blind spot I had:

You know your agent's total token spend, but you have no idea **where** those tokens are going. Is it the system prompt? Skills? Memory? Tools? A bloated skill that keeps loading irrelevant context?

I built a local-first dashboard that sits on top of any agent stack and shows:

- **Token breakdown per component** — identity, skills, memory, tools, guidance. At a glance, "oh my skill audit section is 40% of my context, that's the problem."
- **7-day drift trend** — is your context growing? When did it start?
- **Pulse health** — alive, degraded, dead. Every 30s.
- **Circuit breakers** — auto-stop cascade failures.
- **Heal button** — one click restart.

It's fully local — `pip install observeco && observeco dashboard`. Your agent data never leaves your machine. MIT licensed.

Looking for beta testers to try it and tell me what breaks.

GitHub: https://github.com/observeco/observeco
Install: `pip install observeco[dashboard] && observeco dashboard`

Takes 60 seconds to first data. Would love your feedback.
