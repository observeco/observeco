# obs-spec-014: Per-Turn Token Tracking

**Status:** Draft 2026-05-28
**Product:** ObserveCo dashboard
**Depends on:** obs-dp-003 (agent cards with detail panels)

## §1 Problem

The dashboard currently shows total token count per agent (`trim_data.total_tokens`) with a component breakdown. But there's no **per-turn tracking** — you can't see whether tokens are growing or shrinking over time, which agents are trending up, or how much variance there is between turns.

A user looking at a card with `4.2K total` can't tell:
- Is this higher or lower than yesterday?
- Is this agent's context growing monotonically or oscillating?
- Which turn had the highest token usage this session?

## §2 Requirements

1. **Per-turn token capture** — record every trim event with component breakdown + timestamp
2. **Turn-over-turn delta** — for each component, show change vs previous turn
3. **Session stats** — min/avg/max of total tokens per session
4. **Dashboard panel** — new "Token History" tab in agent detail showing trend

## §3 Database Schema

New table `token_events`:
```sql
CREATE TABLE IF NOT EXISTS token_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    session_id TEXT,
    timestamp INTEGER NOT NULL,
    total_tokens INTEGER DEFAULT 0,
    identity_tokens INTEGER DEFAULT 0,
    skills_tokens INTEGER DEFAULT 0,
    memory_tokens INTEGER DEFAULT 0,
    tools_tokens INTEGER DEFAULT 0,
    guidance_tokens INTEGER DEFAULT 0,
    delta_total INTEGER DEFAULT 0  -- vs previous turn
);
CREATE INDEX IF NOT EXISTS idx_token_events_agent_ts ON token_events(agent_name, timestamp);
```

## §4 Implementation

### Phase 1: Event capture (CLI)
- `observeco token log <agent>` — capture a snapshot and write to `token_events`
- `observeco token profile <agent>` — show trend: last 20 turns, min/avg/max, delta

### Phase 2: Dashboard panel
- New `/api/agent-detail/{name}?tab=tokens` adds "History" sub-section below current breakdown
- Inline SVG sparkline showing last 20 turn totals
- Table: turn timestamp | total | identity | skills | memory | tools | guidance | delta

### Phase 3: Auto-capture
- `observeco watch` daemon auto-logs token_events every `n` checks alongside pulse
- New config key: `track_tokens: true`

## §5 Edge Cases
- **No trim data yet** — show empty state: "No token events — run `observeco token log <agent>`"
- **Single event** — show "1 event recorded" without delta
- **0-token turn** — still record as 0, show in trend (possible if agent hasn't had a session)
- **Rapid agent** — debounce to max 1 event per 5 minutes per agent
