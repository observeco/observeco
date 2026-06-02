# Discord Posts — Beta Tester Recruitment

---

## Hermes Discord / OpenClaw Discord / AI Agent Communities

### Post (for #showcase or #general)

**Title:** ObserveCo — open-source agent observability dashboard

Hey everyone — I built a dashboard that tells you what your AI agents are actually doing with every token. Open source, local-first, MIT licensed.

Features:
- Pulse check (30s intervals — alive, degraded, dead)
- Token breakdown by component (skills, memory, tools, identity, guidance)
- 7-day drift trends
- Circuit breakers + heal button
- Error timeline with context snapshots
- Works with any agent framework (Hermes, OpenClaw, LangChain, CrewAI, Ollama)

```
pip install observeco && observeco dashboard
```

60 seconds to first health data. Your data never leaves your machine.

Looking for beta testers to try it, break it, and tell me what's missing.

GitHub: https://github.com/observeco/observeco
Docs: https://github.com/observeco/observeco#readme

---

### Follow-up DM template for interested people

Hey! Thanks for checking out ObserveCo. Here's the quickstart:

1. `pip install observeco[dashboard] && observeco dashboard`
2. Opens at http://localhost:8080
3. Auto-detects your agents from config files

If you hit any issues, please let me know:
- Did `pip install` work?
- Did it find your agents?
- Is anything confusing in the dashboard?

Appreciate the help!
