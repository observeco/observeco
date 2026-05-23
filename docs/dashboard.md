# Dashboard

The ObserveCo dashboard is a single-pane web UI showing your entire agent fleet's health, token profiles, drift detection, and memory hygiene.

## Opening the Dashboard

```bash
pip install observeco[dashboard]
observeco dashboard
```

Opens at `http://127.0.0.1:9119`. Auto-refreshes every 30 seconds.

## Dashboard Sections

### Fleet Summary
Total agents, alive count, dead count, error count.

### Agent Fleet Cards
Each agent shows: name, framework, status dot (🟢 alive / 🔴 dead / 🟡 error), latency, circuit breaker state.

### Token Profile
Per-component token breakdown (identity, skills, memory, tools, guidance) as horizontal bars with totals.

### Drift Breaches
7-day token allocation changes flagged when >10% component drift is detected.

### Memory Health
ClawForge garden scores: duplicate count, contradictions, stale entries, memory debt grade (A–F).

### Error Timeline
Recent errors with timestamp, agent, type, and message. Errors from circuit breaker trips and pulse failures appear here.
