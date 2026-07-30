# Chisel — See What Your Agent's Prompt Actually Costs

![Hermes Plugin](https://img.shields.io/badge/Hermes-Plugin-7B3FE4)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Zero Deps](https://img.shields.io/badge/Dependencies-0-success)

**Decomposes your agent's system prompt into 5 functional components, estimates per-component token costs, and tracks how they drift over time. Zero external dependencies.**

---

## The Surprise

I ran this on my own Hermes agent. Here's what I found:

```
Component      Tokens    Chars        %
----------------------------------------
Identity           72      291     0.4%
Skills           1344     5376     7.9%
Memory            498     1994     2.9%
Tools             103      414     0.6%
Guidance        15059    60236    88.2%
----------------------------------------
Total           17079    68316
```

**17,079 total tokens. 88.2% is guidance — rules, constraints, policies.**

That's $821/year in API costs I was spending on instructions the model might not even be reading because they're buried in 15K tokens of policy.

And I had no idea until Chisel told me.

---

## How It Works

Chisel reads your agent's system prompt from disk (`config.yaml` + `SOUL.md` + skills + memory), then classifies every line into one of five functional layers:

| Component | What it covers | Why it matters |
|-----------|---------------|----------------|
| **Identity** | Role, persona, behavioral contract | Changes here affect every decision the agent makes |
| **Skills** | Skill descriptions, tool schemas, capability list | Defines what the agent *can* do. Grows as skills are added |
| **Memory** | Injected memory, user profile, session context | Defines what the agent *knows*. Grows over time |
| **Tools** | Tool descriptions, API specs, parameter schemas | Defines how the agent *interacts*. Fixed by the platform |
| **Guidance** | Rules, constraints, policies, output format | Defines how the agent *behaves*. Grows with every correction |

These are the five dials of agent behavior. **Chisel tells you which one is costing you.**

---

## Install

```bash
# 1. Clone into your Hermes plugins directory
git clone https://github.com/your-org/chisel ~/.hermes/plugins/chisel

# 2. Enable the plugin
hermes plugins enable chisel

# 3. Decompose your system prompt
hermes chisel trim
```

That's it. No PyPI, no pip, no API keys, no external dependencies. Just stdlib Python.

---

## Usage

```bash
# Decompose your system prompt right now
hermes chisel trim

# Decompose as JSON (for piping to other tools)
hermes chisel trim --json

# Check drift — how has your prompt changed in the last 7 days?
hermes chisel drift

# Track trend over time
hermes chisel trend --agent main --days 30

# Set a snapshot baseline
hermes chisel baseline --agent main

# Check against that baseline (exit 1 if drifted — CI gate)
hermes chisel baseline --check --agent main
```

The `on_session_start` hook also fires automatically — every new session, Chisel silently decomposes your prompt, stores it, and logs a warning if any component drifted >10% with >50 tokens.

---

## What Chisel Is Not

- **Not an auto-trimmer.** Chisel shows you the numbers. It doesn't modify your prompt. You decide what to cut.
- **Not an LLM.** Pure regex + token estimation + SQLite. No API calls, no model costs, no privacy concerns.
- **Not a dashboard.** CLI + hook only. The data is yours to export however you want.
- **Not a "prompt linter."** Linters check for errors. Chisel checks for *costs*.

---

## What Makes It Different

| Tool | What It Does | Missing Piece |
|------|-------------|---------------|
| **LLMLingua** (Microsoft) | Compresses raw text | No per-component breakdown. Stale 7 months. |
| **Mem0** (56k★) | Extractive memory management | No prompt-level analysis. |
| **ProofAgent** (arxiv) | Scores context against 7 criteria | No per-component token tracking. No drift detection. |
| **Chisel** | **Decomposes + tracks drift** | **The only tool that shows you which section costs what, and how fast it's growing.** |

---

## v0.1 Limitations

- **Token estimation is approximate.** 4 chars/token is a rough average. ±20% error on code-heavy prompts. Drift tracking is valid regardless — it compares ratios using the same estimator.
- **Keyword matching, not LLM.** Lines mentioning "tool" in a guidance context ("don't use the terminal tool") may misclassify. ~15% error ceiling on heavily cross-referenced prompts.
- **Hermes-only.** Reads Hermes-specific file locations. Framework adapters are v0.2.

---

## License

MIT. Do whatever you want with it.

---

## Why I Built It

I was debugging an agent that kept ignoring instructions. After hours of hunting, I realized: the system prompt was 17K tokens. The guidance section had grown so large — from accumulated rules, policies, and corrections — that the model was drowning in policy. It wasn't ignoring instructions. It couldn't *find* them.

I wanted a tool that would have caught this in 30 seconds. So I built it.
