# ObserveCo — Distribution Drafts (G10)

## HN: Show HN Post

**Title:** Show HN: ObserveCo — Runtime observability for AI agents, pip install, local-first

**Body:**

We run 7 autonomous agents on an M4 Mac Mini — Hermes, Kepler, Hound, Dreamer, Aleph, PA, and an orchestrator. They communicate via ACPS signals, trigger on fswatch, get scheduled via cron, and their system prompts were growing 15% week-over-week with nobody watching.

We ran `ps aux | grep python` and hoped for the best. Then we built ObserveCo.

```
pip install observeco[dashboard] && observeco dashboard
```

What it does:
- `pulse check` — is each agent alive? Zero config for Hermes. Works with any agent that has a health endpoint
- `pulse circuit` — N-failure breaker that auto-trips and cooldowns. No more cascading failures
- `chisel trim` — pipe a system prompt, get per-component token breakdown (identity/skills/memory/tools/guidance)
- `clawforge profile` — if you use OpenClaw: MEMORY.md size, skill count, workspace bloat
- `clawforge load` — intent-aware context loader (shows which sources load per message)
- `clawforge garden` — memory hygiene: finds duplicates, contradictions, stale entries
- `dashboard` — fleet view with health dots, token bars, drift sparklines, error timeline, memory debt scores

All data local. MIT. No cloud. No telemetry. No Docker. No npm. Ships with the library.

We also run Kepler as an OpenClaw agent. Its context bloats differently — memory accumulation, not prompt composition. So we built ClawForge: intent-aware loading and memory hygiene designed for OpenClaw.

Two frameworks, two optimizers, one dashboard.

https://github.com/observeco/observeco

Happy to answer questions!

## Reddit: r/LocalLLM

**Title:** Built a local-first agent observability tool because `ps aux` wasn't cutting it

**Body:**

We run a fleet of AI agents on a Mac Mini. They talk to each other, trigger on file changes, get scheduled — and every week their system prompts grew 15% because nobody was watching.

So I built ObserveCo: pip install, local-first, MIT.

Key features:
- Health checks with circuit breakers (no cascading failures)
- Token breakdown per component (identity/skills/memory/tools/guidance)
- Drift tracking (who's growing and how fast)
- Memory hygiene for OpenClaw agents (find duplicates, contradictions, stale entries)
- Dashboard that ships with the library

No cloud, no Docker, no npm, no API keys.

Perfect for the local LLM crowd — everything runs on your machine.

## X Thread

1/ We run 7 AI agents on an M4 Mac Mini. Their system prompts grew 15% every week.
2/ We tried `ps aux`. It wasn't enough.
3/ So we built ObserveCo — `pip install`, local-first agent observability.
4/ Health checks. Circuit breakers. Token breakdown. Memory hygiene. Dashboard.
5/ MIT. No cloud. No telemetry.
6/ https://github.com/observeco/observeco — give it a star if you like keeping your agents alive.
