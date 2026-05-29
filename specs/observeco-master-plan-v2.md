# ObserveCo — Master Plan

**Company:** ObserveCo
**Product:** agentscope
**Package:** `pip install agentscope` / `npm install -g agentscope`
**CTA:** `pip install agentscope — you'll see your agents in 60 seconds.`

> **Name convention (post-review):** ObserveCo = company name. agentscope = product name and package name. All marketing uses "agentscope" as the product. ObserveCo is only used for legal entity, domain, and company branding.

**Version:** 2.1 (post-review)
**Last Updated:** 2026-05-29
**Owner:** Hound (CEO) → Kepler (Revenue) → Pragma (COO)
**Status:** Active — Phase 1 Build
**Review:** Passed with issues (all resolved below)

---

## 1. Vision

**See it. Fix it.**

ObserveCo makes AI agent failures visible, diagnosable, and fixable. We sit between agent runtimes and human operators, providing the visibility layer that every multi-agent system needs but nobody has built.

**The enemy:** Invisible chaos. Agents breaking silently. Token spend disappearing. No audit trail. No accountability.

**The customer:** Anyone running AI agents in production — from solo developers with Claude Code to enterprises with fleets of OpenClaw agents across Slack, Discord, and Telegram.

---

## 2. Product Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   OBSERVECO PLATFORM                     │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │           Fleet Dashboard (Web)              │       │
│  │  • Real-time agent monitoring                │       │
│  │  • Risk breakdown & audit trail              │       │
│  │  • Multi-agent fleet view                    │       │
│  │  • Team policy management                    │       │
│  └──────────────────┬──────────────────────────┘       │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────┐       │
│  │         Event Ingestion Layer                │       │
│  │  • Webhook receiver (universal)              │       │
│  │  • Channel adapters (Slack, Discord, etc.)  │       │
│  │  • Agent adapters (OpenClaw, Claude, etc.)  │       │
│  │  • Standardized event format (OEF)          │       │
│  └──────────────────┬──────────────────────────┘       │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────┐       │
│  │           Risk Engine (Core)                 │       │
│  │  • Tool call parser (structured JSON)        │       │
│  │  • Risk classification (low/med/high/crit)  │       │
│  │  • Policy enforcement                       │       │
│  │  • ML-based predictive scoring (Phase 3)    │       │
│  └──────────────────┬──────────────────────────┘       │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────┐       │
│  │           Storage & Security                 │       │
│  │  • Session logs (tamper-evident)             │       │
│  │  • Audit trail (append-only)                │       │
│  │  • OS keychain for secrets                  │       │
│  │  • User authentication (SSO/SAML)           │       │
│  └─────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
         ▲                                    │
         │                                    ▼
┌────────┴────────┐              ┌────────────────────┐
│  Agent Runtimes  │              │  Communication     │
│  • OpenClaw      │              │  Channels          │
│  • Claude Code   │              │  • Slack            │
│  • Cursor        │              │  • Discord          │
│  • Codex         │              │  • Telegram         │
│  • CrewAI        │              │  • Teams            │
│  • LangGraph     │              │  • Email            │
└─────────────────┘              └────────────────────┘
```

---

## 3. Phased Roadmap

### Phase 1 — Foundation (Week 1-4)

**Goal:** CLI works cross-platform, published to PyPI, one real integration.

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 1.1 | Resolve naming: ObserveCo (company) + agentscope (product/pkg) | Kepler | ✅ DONE | P0 |
| 1.2 | Fix README — remove npm install claim, keep pip install agentscope | Kepler | ⬜ TODO | P0 |
| 1.3 | Publish to PyPI with pyproject.toml | Pragma | ⬜ TODO | P0 |
| 1.4 | Cross-platform path handling (platformdirs for %APPDATA%) | Pragma | ⬜ TODO | P0 |
| 1.5 | Cross-platform ANSI colors (colorama) + headless/TTY detection | Pragma | ⬜ TODO | P0 |
| 1.6 | Replace keyword risk engine with tool-call JSON parser | Pragma | ⬜ TODO | P0 |
| 1.7 | Platform-aware dangerous patterns (Windows/Linux specifics) | Pragma | ⬜ TODO | P0 |
| 1.8 | Add OpenClaw hook integration | Hound | ✅ DONE | P0 |
| 1.9 | Tamper-evident session logs (hash chain) | Pragma | ⬜ TODO | P1 |
| 1.10 | OS keychain for secrets (keyring) | Pragma | ⬜ TODO | P1 |
| 1.11 | Security audit | Hound | ⬜ TODO | P1 |

**Phase 1 Success Criteria:**
- [ ] `pip install agentscope` works on Windows, macOS, Linux
- [ ] `agentscope run "Fix login bug"` shows correct risk on all 3 OSes
- [ ] Colors render correctly on cmd.exe, PowerShell, Terminal, iTerm
- [ ] Colors degrade gracefully in headless/TTY-less environments (Docker, CI)
- [ ] Config stored in OS-standard location (via platformdirs)
- [ ] At least one real agent integration (OpenClaw hooks)
- [ ] Session logs can't be tampered with
- [ ] Secrets stored in OS keychain, not plaintext

### Phase 2 — Production Ready (Week 5-8)

**Goal:** MCP server, channel adapters, web dashboard, team features.

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 2.1 | MCP server (universal agent adapter) | Pragma | ⬜ TODO | P0 |
| 2.2 | Slack adapter (bot events, audit logs) | Pragma | ⬜ TODO | P0 |
| 2.3 | Discord adapter (bot messages, slash commands) | Pragma | ⬜ TODO | P0 |
| 2.4 | Telegram adapter (bot API updates) | Pragma | ⬜ TODO | P1 |
| 2.5 | Dashboard framework + session history (htmx + FastAPI) | Pragma | ⬜ TODO | P0 |
| 2.6 | Dashboard real-time monitoring (add WebSocket to existing dashboard) | Pragma | ⬜ TODO | P1 |
| 2.7 | Team features — shared permission policies | Pragma | ⬜ TODO | P0 |
| 2.8 | Team features — audit log | Pragma | ⬜ TODO | P0 |
| 2.9 | Claude Code adapter (hooks integration) | Kepler | ⬜ TODO | P0 |
| 2.10 | Cursor adapter (extension) | Kepler | ⬜ TODO | P1 |
| 2.11 | Docker image for self-hosted deployment | Pragma | ⬜ TODO | P1 |
| 2.12 | Standardized Event Format (OEF) — formalize §4.2 into standalone spec | Hound | ⬜ TODO | P1 |
| 2.13 | User authentication (OAuth2) | Pragma | ⬜ TODO | P0 |

> **Note:** Codex adapter deferred to Phase 3 pending API feasibility verification.
> **Note:** Task 2.5 and 2.6 are sequenced: 2.5 builds dashboard framework, 2.6 adds WebSocket to it.

**Phase 2 Success Criteria:**
- [ ] MCP server works with any MCP-compatible agent
- [ ] Slack app has 3+ workspaces with >10 events/day each
- [ ] Discord bot in 10+ servers with ≥1 event per server per day
- [ ] Dashboard shows real-time agent activity with <5s latency
- [ ] Team admin can create and enforce permission policies
- [ ] Docker image runs `docker run agentscope` and works
- [ ] Any agent can send events via webhook (POST /api/v1/events)

### Phase 3 — World Class (Month 3-4)

**Goal:** Fleet dashboard, universal pathway map, ML risk scoring.

| # | Task | Owner | Status | Priority |
|---|---|---|---|---|
| 3.1 | Fleet dashboard — multi-agent, multi-channel view | Pragma | ⬜ TODO | P0 |
| 3.2 | Universal pathway map (any communication protocol) | Hound | ⬜ TODO | P0 |
| 3.3 | ML-based predictive risk scoring | Pragma | ⬜ TODO | P1 |
| 3.4 | Cross-agent failure correlation | Hound | ⬜ TODO | P1 |
| 3.5 | Windows MSI installer | Kepler | ⬜ TODO | P1 |
| 3.6 | Homebrew formula | Kepler | ⬜ TODO | P2 |
| 3.7 | Mobile monitoring app | Kepler | ⬜ TODO | P2 |
| 3.8 | Enterprise SSO/SAML | Pragma | ⬜ TODO | P1 |
| 3.9 | API for third-party integrations | Pragma | ⬜ TODO | P0 |
| 3.10 | On-prem deployment option | Pragma | ⬜ TODO | P2 |
| 3.11 | macOS LaunchAgent for auto-start | Pragma | ⬜ TODO | P2 |
| 3.12 | macOS notarization for Gatekeeper | Kepler | ⬜ TODO | P2 |
| 3.13 | Codex adapter (pending API verification) | Kepler | ⬜ TODO | P2 |

**Phase 3 Success Criteria:**
- [ ] Dashboard shows all agents across all channels
- [ ] Pathway map visualizes agent communication in real-time
- [ ] Risk engine predicts failures before they happen
- [ ] One agent's failure automatically alerts related agents
- [ ] `choco install observeco` works on Windows

---

## 4. Technical Specifications

### 4.1 Risk Engine v2 (Replaces Keyword Matching)

**Current (v0.1):** Keyword matching on text strings.
**New (v1.0):** Structured tool call parser.

```python
# Input: structured tool call from agent runtime
tool_call = {
    "name": "exec",
    "arguments": {
        "command": "rm -rf /var/data/backups",
        "workdir": "/app"
    }
}

# Risk classification
risk = classify_tool_call(tool_call)
# → RISK_CRITICAL (destructive + critical path)

# vs. harmless text
tool_call = {
    "name": "read",
    "arguments": {"path": "src/auth/login.ts"}
}
risk = classify_tool_call(tool_call)
# → RISK_LOW (read-only)
```

**Tool call risk matrix:**

| Tool | Args Pattern | Risk |
|---|---|---|
| read | any | LOW |
| write/edit | non-sensitive path | MEDIUM |
| write/edit | config/secrets/env | HIGH |
| exec | `rm`, `drop`, `delete` | CRITICAL |
| exec | `git push`, `deploy` | HIGH |
| exec | `curl`, `ssh` | MEDIUM (allowlist) |
| memory_write | any | MEDIUM |
| browser_* | any | MEDIUM |

### 4.2 Standardized Event Format (OEF)

All agents, regardless of runtime, send events in this format:

```json
{
  "version": "1.0",
  "event_id": "uuid",
  "timestamp": "ISO8601",
  "agent_id": "string",
  "runtime": "openclaw|claude-code|cursor|codex|crewai|langgraph",
  "channel": "slack|discord|telegram|teams|email|webhook",
  "event_type": "tool_call|response|error|heartbeat",
  "payload": {
    "tool_name": "string",
    "tool_args": {},
    "result": {},
    "risk_level": "low|medium|high|critical",
    "decision": "auto_approved|flagged|denied"
  },
  "context": {
    "session_id": "string",
    "user_id": "string",
    "task_id": "string"
  }
}
```

### 4.3 Channel Adapters

**Slack Adapter:**
- Receives events via Slack Events API (bot events, app mentions)
- Sends alerts to designated Slack channels
- Reads audit logs for agent activity
- Supports Slack Block Kit for rich notifications

**Discord Adapter:**
- Receives events via Discord bot (slash commands, messages)
- Sends alerts to designated Discord channels
- Supports Discord embeds for rich notifications

**Telegram Adapter:**
- Receives events via Telegram Bot API
- Sends alerts to designated Telegram groups/chats
- Supports inline keyboards for approval workflows

**Webhook Receiver (Universal):**
- `POST /api/v1/events` — accepts OEF events from any source
- Validates event signature (HMAC-SHA256)
- Rate limiting per source
- Dead letter queue for failed processing

### 4.4 Dashboard Components

**Session History:**
- Timeline view of all agent sessions
- Filter by agent, risk level, time range
- Drill-down into individual tool calls

**Risk Breakdown:**
- Pie chart: auto-approved vs flagged vs denied
- Bar chart: risk distribution over time
- Table: top risky actions with details

**Real-Time Monitor:**
- Live feed of incoming events
- WebSocket connection for instant updates
- Pause/resume filtering

**Team Policies:**
- CRUD for permission policies
- Policy versioning
- Rollback capability

### 4.5 Security Model

**Tamper-Evident Logs:**
- Each session log entry includes SHA-256 hash of previous entry
- Chain can be verified to detect tampering
- Format: `{...entry, "prev_hash": "sha256", "entry_hash": "sha256"}`

**OS Keychain Integration:**
- macOS: Keychain Services
- Windows: Credential Manager
- Linux: Secret Service (gnome-keyring, kwallet)
- Library: `keyring` (Python)

**User Authentication:**
- Phase 2: OAuth2 (Google, GitHub)
- Phase 3: SSO/SAML (Enterprise)
- Session tokens with expiry

---

## 5. Cross-Platform Compatibility

### 5.1 OS Support Matrix

| Feature | macOS | Linux | Windows |
|---|---|---|---|
| CLI | ✅ | ✅ | ✅ (with fixes) |
| Config location | ~/.agentscope/ | ~/.agentscope/ | %APPDATA%/agentscope/ |
| Colors | ✅ | ✅ | ✅ (colorama) |
| Headless mode | N/A | ✅ (no ANSI) | N/A |
| Keychain | Keychain | Secret Service | Credential Manager |
| Installer | Homebrew | apt/snap | MSI/Chocolatey |
| Background service | LaunchAgent | Systemd | Windows Service |

### 5.2 Communication Channel Support

| Channel | Phase 2 | Phase 3 |
|---|---|---|
| Slack | ✅ | ✅ |
| Discord | ✅ | ✅ |
| Telegram | ✅ | ✅ |
| Teams | — | ✅ |
| Email | — | ✅ |
| Webhook (any) | ✅ | ✅ |

### 5.3 Agent Runtime Support

| Runtime | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| OpenClaw | ✅ (hooks) | ✅ | ✅ |
| Claude Code | — | ✅ (hooks) | ✅ |
| Cursor | — | ✅ (extension) | ✅ |
| Codex | — | ✅ (API) | ✅ |
| CrewAI | — | ✅ (MCP) | ✅ |
| LangGraph | — | ✅ (MCP) | ✅ |
| Any MCP | — | ✅ | ✅ |

---

## 6. Pricing

| Tier | Price | Includes |
|---|---|---|
| **Solo** | $0/mo | Local CLI, unlimited tasks, basic risk detection, 7-day history |
| **Team** | $19/mo | Everything in Solo + shared policies, audit log, custom rules, MCP, priority support |
| **Enterprise** | Custom | Everything in Team + SSO/SAML, compliance rules, on-prem, SLA |

---

## 7. Marketing Alignment

**Product name:** agentscope
**Company name:** ObserveCo
**Positioning:** "See it. Fix it."

**Launch phases** (from marketing-plan.md — dates to be synced with engineering):
1. Ghost (D-7): Anonymous Reddit comment → 3-5 beta testers
2. Tease (D-3): One X post, no link → imagination
3. Revelation (D-0): X article + HN Show HN + Reddit → 50-100 stars
4. Payoff (D+14): X thread → "when auto-fix?" → v1.1 drop

**CTA:** `pip install agentscope — you'll see your agents in 60 seconds.`

**Anti-patterns (from marketing plan):**
- No "we" language
- No feature lists before pain is shown
- No "company" language in launch posts
- No cold outreach
- No announcing v1.1 at launch

> **Marketing-engineering sync:** D-0 launch date must be AFTER Phase 1 completion. Add go/no-go gate: Phase 1 success criteria must pass before marketing Phase 3 begins.

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PyPI publish fails | Low | Critical | Test with test.pypi.org first |
| Windows colorama breaks | Medium | High | Test on 3 Windows terminal types |
| MCP server spec changes | Medium | High | Pin MCP version, monitor upstream |
| Slack API rate limits | Medium | Medium | Batch events, exponential backoff |
| Dashboard performance at scale | Low | High | Implement pagination, virtual scrolling |
| Security audit failure | Medium | Critical | Run security audit in Phase 1 |

---

## 9. Dependencies

| Dependency | Type | Phase | Status |
|---|---|---|---|
| colorama | Python | 1 | ⬜ Install |
| platformdirs | Python | 1 | ⬜ Install |
| keyring | Python | 1 | ⬜ Install |
| mcp | Python | 2 | ⬜ Install |
| fastapi | Python | 2 | ⬜ Install |
| uvicorn | Python | 2 | ⬜ Install |
| websockets | Python | 2 | ⬜ Install |
| htmx | Frontend | 2 | ⬜ CDN reference |
| slack-sdk | Python | 2 | ⬜ Install |
| discord.py | Python | 2 | ⬜ Install |
| python-telegram-bot | Python | 2 | ⬜ Install |

> **Frontend decision (post-review):** htmx for dashboard (lightweight, no build step, works with FastAPI templates). If complexity grows, migrate to React/Svelte in Phase 3.

---

## 10. Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-29 | Cross-platform gaps identified | 6 critical categories blocking adoption |
| 2026-05-29 | MCP server prioritized for Phase 2 | Universal adapter — solves agent compatibility in one shot |
| 2026-05-29 | OEF spec created | Standardized event format enables any channel integration |
| 2026-05-29 | Phase 1 focused on CLI fixes | Must work before anything else can be built on top |

---

*This document is the single source of truth for ObserveCo's product roadmap. All tasks flow from here to Kanban boards. All agents reference this for context.*
