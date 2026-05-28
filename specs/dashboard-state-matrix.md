# Dashboard State Matrix — UX Audit Reference

**Last updated:** 2026-05-28
**Audits:** 18 API endpoints (16 htmx + 2 JS-fetched)

## Endpoint: `/` (root index)

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | Dashboard running | Full HTML page with header, fleet bar, agents, alerts, timeline, heal | `curl http://localhost:9119/` → 200, contains `<!DOCTYPE html>` |
| Server down | Server killed | Connection refused (browser error page) | `pkill -f observeco.*dashboard` → curl returns 7 |
| DB empty | Fresh install | Error banners from `/api/error-state` populate phase-banner div | Check `#phase-banner` contains text (not blank) |

## Endpoint: `/api/error-state`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| DB not exists | `~/.observeco/pulse.db` missing | Warning banner: "No monitoring data yet" | Response contains "No monitoring data" |
| DB empty | pulse.db exists, 0 bytes | Warning banner: "Health database is empty" | Response contains "empty" |
| Daemon stale | Last pulse > 2h ago | Warning banner: "Monitoring stopped" + hours | Response contains "stopped" |
| No agents | agents table empty | Info banner: "No agents discovered yet" | Response contains "No agents discovered" |
| Config unreadable | `agents.json` corrupted | Critical banner: "Could not read config" | Response contains "permissions" |
| All clear | Everything fine | Empty response (no HTML) | Response body is empty string |

## Endpoint: `/api/delay-banner` (obs-dp-006)

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| No overdue agents | all pulses < 10m ago | Empty response (no HTML) | Body is empty string |
| Some overdue | 1+ agents with delay > 10m | Warning banner: "X of Y agents overdue: name1, name2" | Contains "delay-banner", contains "overdue" |
| Critical overdue | 1+ agents with delay > 1h | Critical banner with count | Contains "critical", icon "🔴" |
| All agents new / no pulses | agents exist but no pulse data | Banner shows total delay from creation | Returns 200, contains "overdue" or "delay-banner" element |

## Endpoint: `/api/fleet-summary`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | agents + pulses in DB | Fleet stats: total/alive/dead/errors counts + optional trip badge + drift | Response contains "Agents", "Alive", "Dead" stat boxes |
| No agents | agents table empty | Stats with 0 values | Contains "0" + "Agents" |
| No pulses | pulses table empty | Stats with agents=count, rest=0 | Contains total count > 0, alive=0 |
| Tripped circuits | circuit_breakers tripped | Trip badge rendered | Contains "tripped" |
| Drift data | drift table has breached rows | Drift stat box rendered | Contains "Tokens:" + "+" or "-" |

## Endpoint: `/api/agents`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | agents + pulses + trims + drift | Agent cards in 3 sections with status dots, token bars, drift sparklines | Contains "section-hermes", "agent-card", "status-dot" |
| No agents | agents table empty | Empty section divs (no cards) | Sections exist, card count = 0 |
| Single agent | 1 agent configured | Single card in correct section | One `.agent-card` element |
| Mixed frameworks | Hermes + OpenClaw agents | Both sections rendered | Contains "section-hermes" AND "section-openclaw" |
| No trim data | trims table empty | Cards without token bar (no bar segment) | Card rendered without `<span style="display:inline-block;height:100%"` or similar bar CSS |
| All dead | all agents status=dead | Cards with red dots, dead badge | Each section-hermes card shows red dot |
| Unknown framework | framework field absent/null | Card lands in "Others" section | Rendered inside "section-other" |

## Endpoint: `/api/agent-detail/{name}`?tab={tab}

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Health tab, normal | pulses exist | 24h pulse history + latest checks | Contains last check time, pulse rows |
| Health tab, no pulses | agent has no pulses | "No pulse data yet" | Contains "No pulse data" or empty state text |
| Tokens tab, normal | trims exist | Token breakdown table | Contains component names (identity/skills/memory/tools/guidance) |
| Tokens tab, no data | no trims | "No token data" | Contains "No token data" |
| Memory tab, normal | garden data exists | Garden metrics + contradictions | Contains "Memory Debt" or "Contradictions" |
| Memory tab, no data | no garden | "No garden data yet" | Contains "No garden data yet" |
| Unknown agent | name not in DB | Graceful error (not 500) | Response 200, contains error text (not 500) |

## Endpoint: `/api/errors`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | errors in DB | Timestamped error items | Contains `error-item`, formatted with time + agent + message |
| No errors | errors table empty | "No errors in the last 24h" | Contains "No errors" |
| Multiple errors | 10+ errors | Most recent 30 items | Count of `error-item` divs ≤ 30 |

## Endpoint: `/api/alerts`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | circuit trips + drift breaches + pulses | Severity-coded alert rows + Pro tiles | Contains "severity-critical", "severity-warning", "pro-tile" |
| No alerts | all clear | "All clear — no alerts" | Contains "All clear" |
| Pro tiles only | no alerts, Pro configured | Pro locked tiles with data previews | Contains "pro-tiles-section" |
| Missing Pro data | all DB empty | Pro tiles with "no recent alerts" text | Contains "no recent alerts" or similar |

## Endpoint: `/api/phase`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Pre-install | No DB | `phase-0` | Exact string "phase-0" |
| Discovering | DB exists, no pulses | `phase-1` | Exact string "phase-1" |
| Learning | Pulses exist, < 10min fresh data | `phase-1` | String "phase-1" |
| Has health | Pulses >= 10min, no trims | `phase-2` | Exact string "phase-2" |
| Full data | Pulses + trims exist | `phase-3` | Exact string "phase-3" |

## Endpoint: `/api/heal-log`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | heal investigations exist | Heal entries with diagnosis + action | Contains `heal-entry`, diagnosis text |
| No events | no heal logs, no tripped breakers | "No self-heal events recorded" | Contains "No self-heal events" |
| Active issues | tripped circuit breakers | "Active Issues" section | Contains "Active Issues" |
| Trigger button | always | Heal trigger link | Contains `/api/trigger-heal` |

## Endpoint: `/api/trigger-heal`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | agents with pulses/breakers | Diagnosis entries | Contains `heal-entry` rows |
| No data | no pulses, no breakers | "No agent data to diagnose" | Contains "No agent data" |
| All healthy | agents alive, no issues | "All agents appear healthy" | Contains "All agents" AND "healthy" |

## Endpoint: `/api/graph/overview`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | graph DB exists | Stats card (Symbols/Relations/Files) + search input | Contains "Symbols", "Relations", "Files", "graph-search-input" |
| Empty index | graph DB empty | Stats with 0 values | Contains "0" counts |

## Endpoint: `/api/graph/search?q=...`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Results found | matching symbols | Symbol list with kind icon, qual name, file path | Contains "graph-result" |
| No results | no matches | "No results" | Contains "No results" |
| Empty query | q="" | "Enter a search term" | Contains "Enter a search term" |

## Endpoint: `/api/graph/symbol?name=...`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Symbol found | name matches a symbol | Symbol detail with callers + callees | Contains "Called by", "Calls" |
| Not found | name doesn't match | "Symbol not found" | Contains "Symbol not found" |
| Empty name | name="" | Empty response | Body is empty |

## Endpoint: `/api/pro-preview/{feature_id}`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Known feature | valid feature_id | Pro preview modal with data | Contains "pro-preview-modal", your data |
| Unknown feature | invalid feature_id | "Unknown feature" | Contains "Unknown feature" |

## Endpoint: `/api/reset-circuit/{agent_name}`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Normal | agent exists | "Circuit reset for {agent}" | Contains "Circuit reset" |
| Unknown agent | agent doesn't exist | 200 response with message | Non-500 response |

## Endpoint: `/api/checkout?plan=...`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| Stripe configured | STRIPE_API_KEY set | Redirect to Stripe | 302 redirect |
| Stripe not configured | no key | Email capture form | Contains "Pro Licensing Coming Soon" |

## Endpoint: `/static/htmx.min.js`

| State | Trigger | Expected output | Detection |
|-------|---------|-----------------|-----------|
| File exists | htmx.min.js present | JavaScript file | 200, Content-Type is application/javascript |
| File missing | static/ dir not found | 404 | 404 response |
