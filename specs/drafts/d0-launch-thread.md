# D-0 Launch Thread

---

**1/6 — The hook**

I run 7 autonomous AI agents on a single M4 Mac Mini. One was silently failing for 3 months. I only found out because a user complained.

So I built ObserveCo. It tells you if your AI agents are working, what they're doing, and where your money goes. Open source. Local. No cloud.

12 features. One install. 🧵

---

**2/6 — The problem**

When I finally dug into what was happening, every agent's context was growing 15% per week. Memory had duplicates and contradictions. One agent was producing garbage for 6 hours before anyone noticed.

The scariest part? This is NORMAL. Every agent operator I talk to has a version of this story.

---

**3/6 — What v0.1 ships today**

ObserveCo v0.1 has 12 features:

🟢 Fleet view — every agent in one place, live status dots
💓 Pulse check — alive/dead/error every 30 seconds
🛡️ Safety Guard — circuit breaker, stops probing after 3 failures
📊 Token breakdown — see what's inside each agent's system prompt
📈 Drift tracking — 7-day trend per component, spot bloat before the bill
🔴 Error history — every failure, annotated with plain-English verdict
💊 Heal button — diagnose + restart dead agents in one click
⚠️ In-dashboard alerts — circuit trips, drift breaches, discovery gap badges
🌱 Memory Garden — duplicates, contradictions, debt score
🔧 ClawForge CLI — profile, load, garden, history
💻 Full CLI — pulse, circuit, chisel, clawforge
💾 Local SQLite — zero cloud, zero telemetry

---

**4/6 — The dashboard**

All of it in one local web UI. Fleet health, token profiles, error timeline, memory debt score. No cloud. No telemetry. Your data never leaves your machine.

Every banner ends with the exact command to fix the problem. You learn the syntax by reading. In v0.2 (D+3), those commands fire automatically.

[Screenshot: Dashboard overview with yellow observation banners]

---

**5/6 — What's coming**

v0.1 (now) → 12 features. Full monitoring + diagnostics.
v0.2 (D+3) → Auto-heal. Crashes recover in ~5 seconds. No human click.
v0.3 (D+7) → Chisel compression + push alerts to Telegram. Measure AND fix token bloat.
v1.1 (D+14) → OpenClaw runtime plugin. Agents load only what they need per turn.

Every yellow banner in v0.1 is deliberate. It shows you the problem and the fix command. The fix is coming.

---

**6/6 — CTA**

If you run AI agents and want to actually see what they're doing:

```
pip install observeco && observeco dashboard
```

Or check the repo: https://github.com/observeco/observeco

MIT open source. No signup. No account. You'll see your agents in 60 seconds.
