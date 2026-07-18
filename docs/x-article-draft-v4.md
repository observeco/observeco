# 96% of my AI agent prompts were recomputed from scratch. Here's the proof.

**Format:** X Article (~1,800 words, 4 branded data cards)

---

## 1. The moment I found out

I run 39 AI agents on one Mac Mini. They write code, manage infrastructure, watch my servers, and talk to each other. For months, I assumed they were working fine.

They weren't.

A user said "this output looks wrong." I checked the logs. One agent had been producing broken code for three hours. Running. Responding. Completely wrong. Nobody knew.

This isn't unique to me. Every agent operator I talk to has the same blind spot. The gap between failure and awareness is measured in users, not seconds.

---

## 2. What the data actually showed

When I pointed ObserveCo at my own fleet, here's what I found.

[$CARD: Fleet Problem — 28 alive, 11 down, 28% failure rate]

**28 out of 39 agents were alive. 11 were down.** A 28% failure rate I was completely blind to. Multiple agents marked "Guard: possible stale" — running, but with no guarantee they were producing anything useful.

[$CARD: Cost Waste — $149 total, hermes-agent at 87.6%, 36% cache hit]

**$149.06 in token spend I couldn't trace.** One agent (hermes-agent) was 87.6% of the total. The cache hit rate was 36% — meaning 64% of every prompt was still being recomputed from scratch. Tool definitions, memory loops, heartbeat calls I never authorized.

[$CARD: Context Bloat — hermes-agent at 79,826 tokens, 86% of fleet]

**One agent had 79,826 tokens of context bloat — 86% of the entire fleet.** The system flagged it "critically bloated." Another agent showed +709.8% token growth in a single week. Context expanding 8x in seven days with nobody trimming it.

These aren't edge cases. If you run multiple agents over time, context bloat and silent failures are the default. The only variable is how long you go without knowing.

---

## 3. What I did about it

The most revealing number wasn't the total spend. It was the **0.3% output/input ratio**. For every 100,000 tokens I was feeding into my agents, I was getting back 300 tokens of useful output. The other 99,700 were going into context that never produced anything.

That metric led me to investigate what was actually in my agents' context. What I found: **my Hermes skills were being loaded in their entirety on every turn.** Every skill file, every reference document, every template — all of it, every time, regardless of whether the agent needed it.

I used the **Brain Analysis** tab to see exactly which skills were bloated, which were stale, and which hadn't been used in weeks. Then I ran **Compression** — the semantic compression engine — to trim the fat. It deduplicated overlapping entries, pruned stale skill files, and rewrote verbose headers without changing behavior.

The result: hermes-agent went from 79,826 tokens of context bloat down to a manageable size. The skills that were actually needed stayed. The dead weight got archived.

**The key insight:** the dashboard didn't just show me a red number. It showed me the *ratio* that told me where to look. The 0.3% output/input was the breadcrumb. The Brain Analysis was the map. Compression was the tool.

---

## 4. The existing tools miss the point

I looked at the alternatives before building this.

**Arize Phoenix** (10k★, OTel-native) is strong on LLM trace-level debugging — spans, evaluations, experiments. But it has no concept of agent runtime health. No circuit breakers, no pulse checks, no memory debt, no drift detection.

**LangFuse** (29k★, MIT) is a full LLM engineering platform with tracing, prompt management, and evals. Also trace-centric. Also no agent health monitoring.

**OpenLIT** (2.5k★, Apache 2.0) offers GPU monitoring and 60+ integrations. Broad but shallow on agent health. No compression, no memory hygiene.

**The common gap:** All of them answer "what did the model return?" None of them answer "is my agent healthy?"

That's the difference between tracing and observability. Tracing tells you what happened. Observability tells you what's happening now, whether it matters, and what to do about it.

ObserveCo runs alongside your tracer. It fills the gap they don't cover.

---

## 5. What I built

One command, 60 seconds to see your fleet:

```
pip install observeco && observeco dashboard
```

No Docker. No API keys. No cloud. Your data never leaves your machine.

**What you see:**

| Feature | What it shows |
|---------|--------------|
| **Fleet Health** | Green/yellow/red per agent, live status dots |
| **Token Breakdown** | Which agent is burning money, per-component |
| **Drift Tracking** | Context growth over time — see bloat before the bill |
| **Brain Analysis** | Compression opportunities, duplicate skills, memory bloat |
| **Error Timeline** | Last crash, last trip, last warning — plain English |
| **Auto-Restart** | Detects crashes and restarts automatically |
| **Push Alerts** | Telegram when agents go down |
| **Circuit Breaker** | Stops cascading failures |

[$CARD: The Fix — Auto-Restart available now]

**The observation banners are the most important part.** When the dashboard flags "79,826 tokens — critically bloated," it tells you exactly what to run. The dashboard shows you the problem. You decide what to do about it.

---

## 6. Try it

```
pip install observeco && observeco dashboard
```

60 seconds. Local-first. No cloud. No telemetry. No sales team.

If you run AI agents — even one — you'll know what they're actually doing for the first time.

https://github.com/observeco/observeco

MIT. Free. Open source. No signup.

---

**Post your worst number.** Run `observeco dashboard`, screenshot your fleet health, and reply with your most embarrassing stat. I'll retweet the best ones.

*I run 39 AI agents on a Mac Mini. This is what I built to keep them honest.*
