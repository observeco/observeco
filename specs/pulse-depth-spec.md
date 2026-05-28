# ObserveCo — Pulse Depth Spec

**Purpose:** Full specification for the 6 new features added to ObserveCo, covering what was previously internal-only in the Hermes ecosystem.

---

## Feature 1: System Prompt Compression (`observeco chisel compress`)

### What
Port the Hermes Chisel compression engine into ObserveCo as a standalone command that can run against any agent's SOUL.md or system prompt file.

### Why This Exists Now
The compression engine was always inside Hermes Agent (`run_agent.py`) and never extracted. Users not on Hermes Agent have no way to shrink system prompts. ObserveCo can measure tokens but cannot fix them.

### Implementation
- Extract compression patterns from Hermes `run_agent.py` (Lite mode: 6 guidance blocks, Full mode: +memory, +profile, +context)
- Port as **file-in/file-out** operation — no Hermes runtime dependency
- Read SOUL.md or any system prompt file → compress → write `.compressed` version or suggest diffs
- CLI: `observeco chisel compress [--agent <name>] [--mode lite|full] [--file <path>] [--apply]`
- `--apply` flag: overwrites original with compressed version (with backup)
- Default `--mode lite` — proven safe, 22%+ savings

### Tier
| Feature | Free | Pro |
|---------|------|-----|
| `observeco chisel compress` dry-run (show savings) | ✅ | ✅ |
| `--apply` write compressed version | ✅ | ✅ |
| Auto-compression via watch daemon | ❌ | ✅ |

### Estimated Effort
~2 days

---

## Feature 2: Per-Turn Token Cost Tracking

### What
Each agent reports its token usage (prompt breakdown by section) after every conversation turn via a webhook.

### Why This Exists Now
Never built anywhere. The Chisel session hook in Hermes was one-shot at session start — it compressed the prompt but did not report per-turn cost.

### Implementation
**ObserveCo side:**
- `POST /api/chisel/trim` endpoint accepting `{agent_name, identity_tokens, skills_tokens, memory_tokens, tools_tokens, guidance_tokens, total_tokens}`
- Existing `chisel_trims` table schema supports per-agent data already
- Dashboard Tokens tab shows per-turn breakdown with timestamp

**Agent side:**
- **Hermes:** Add post-turn hook in `run_agent.py` that POSTs current prompt composition
- **OpenClaw:** Similar hook via ContextEngine lifecycle (post-turn event)
- **Other frameworks:** Can POST manually if they expose a hook

### Tier
| Feature | Free | Pro |
|---------|------|-----|
| Per-turn token display (last 24h) | ✅ | ✅ |
| Per-turn history (7d) | ✅ | ✅ |
| Per-turn history (90d) | ❌ | ✅ |
| Multiple agents aggregated view | ❌ | ✅ |

### Estimated Effort
~3 days (1d endpoint + 2d agent hooks)

---

## Feature 3: Auto-Heal Dead Agents

### What
The watch daemon automatically triggers `run_heal()` when pulse check detects a dead agent. Built-in circuit breaker prevents infinite retry loops.

### Why This Exists Now
The heal logic (`heal.py`) already exists with full circuit breaker, cooldown, and critical flagging. The only gap is the trigger — currently manual button in dashboard.

### Implementation
- In `watch.py` pulse loop: if `status == "dead"`, call `run_heal(agent.name)`
- `HEAL_CIRCUIT` dict in `heal.py` already tracks retries per agent (MAX_HEAL_RETRIES=3, COOLDOWN_HOURS=4)
- No new code needed — only a 3-line integration in the watch loop
- Dashboard heal button remains for manual trigger

### Tier
| Feature | Free | Pro |
|---------|------|-----|
| Auto-heal on dead detection | ✅ | ✅ |
| Auto-heal with configurable retry/cooldown | ❌ | ✅ |
| Auto-heal logging + notification on failure | ❌ | ✅ |

### Estimated Effort
~1 day

---

## Feature 4: Intent-Aware Loading at Runtime (OpenClaw Plugin)

### What
Drop-in Node.js plugin for OpenClaw's ContextEngine that hooks into bootstrap/ingest/pre-response lifecycle to load only what's needed per turn.

### Why This Exists Now
Spec'd in `unified-dashboard.md` §4.2.2 but never built. ObserveCo currently has only the dry-run (`clawforge load --probe`) which shows what *would* happen but cannot change OpenClaw's actual behaviour.

### Architecture
```
OpenClaw Agent
  └── ContextEngine
       └── [ClawForge Plugin] ← decides what to load/skip at runtime
            ├── bootstrap: load minimal context (SOUL.md + recent MEMORY.md summary only)
            ├── ingest: classify intent → load matching skills + MEMORY entries + workspace files
            └── pre-response: estimate tokens → demote low-value content if near window limit
                 └── reports stats to ObserveCo API (POST /api/chisel/trim)
                      └── stored in SQLite → dashboard shows savings
```

### Implementation
- Separate Node.js package (`@observeco/clawforge-plugin`) that depends on OpenClaw SDK
- Hooks into 3 lifecycle events defined in OpenClaw's ContextEngine API
- Reports per-turn stats to ObserveCo endpoint (Feature 2)
- ObserveCo side: dashboard Garden tab shows runtime savings vs dry-run estimates
- Requires OpenClaw SDK access and documentation of ContextEngine hook API

### Tier
| Feature | Free | Pro |
|---------|------|-----|
| Plugin install + basic intent-aware loading | ❌ Requires OpenClaw | ❌ Requires OpenClaw |
| Dashboard integration (savings display) | ✅ | ✅ |
| Custom intent classifier training | ❌ | ✅ |
| Multi-agent plugin fleet management | ❌ | ✅ |

### Estimated Effort
~5-7 days (2d plugin scaffold + 3d lifecycle hooks + 2d ObserveCo reporting integration)

---

## Feature 5: Push Alerts

### What
When circuit trips, drift breaches threshold, or agent goes dead, push notification to Telegram, webhook, or email.

### Why This Exists Now
Alert detection pipeline exists (circuit trips, drift breaches, heartbeat misses are all detected in the watch loop and stored in DB). Only the delivery layer is missing — currently alerts display in-dashboard only.

### Implementation
- **Alert detection:** Already done — watch loop records circuit trips, drift events, pulse failures to DB
- **Delivery module:** New module `src/observeco/alert/delivery.py`
  - Telegram: reuses existing Hermes bot connection
  - Webhook: POST to user-configured URL with JSON payload
  - Email: SMTP via stdlib
- **Config:** `~/.observeco/alerts.json` — list of channels per alert type
- **Webhook:** User provides URL, ObserveCo POSTs `{type, agent, severity, message, timestamp}`
- Stripe billing already wired; webhook handler ready for trial/conversion flow

### Delivery Channels
| Channel | Status | Notes |
|---------|--------|-------|
| In-dashboard | ✅ Already works | |
| Telegram push | 🟡 Needs integration | Reuses Hermes bot connection |
| Webhook POST | 🟡 Config + POST logic | JSON payload |
| Email (SMTP) | 🔴 Config + sending | SMTP relay or sendmail |

### Tier
| Feature | Free | Pro |
|---------|------|-----|
| In-dashboard alerts | ✅ | ✅ |
| Push alerts (Telegram) | ❌ | ✅ |
| Push alerts (webhook) | ❌ | ✅ |
| Push alerts (email) | ❌ | ✅ |
| Custom alert thresholds | ❌ | ✅ |
| Multi-channel routing | ❌ | ✅ |

### Estimated Effort
~3 days (2d delivery module + 1d config + 1d Telegram integration)

---

## Feature 6: Extended Token History (> 24h)

### What
Dashboard token history display expanded from 24h to 7 days (Free) and 90 days (Pro).

### Why This Exists Now
The SQLite database stores all data indefinitely. The 24h limit is a **display filter** in the dashboard query, not a storage limit. Simple parameter change.

### Implementation
- Change `limit=24h` query parameter in dashboard API to accept `?range=7d|30d|90d`
- Free tier: default 7d
- Pro tier: configurable up to 90d
- Token bar chart shows history with per-component trend
- Pulse, error, and drift history scaled similarly
- All data already exists in `chisel_trims` table — no schema changes needed

### Tier
| Feature | Free | Pro |
|---------|------|-----|
| Token history (24h) | ✅ | ✅ |
| Token history (7d) | ✅ | ✅ |
| Token history (90d) | ❌ | ✅ |
| Error history (7d) | ✅ | ✅ |
| Error history (90d) | ❌ | ✅ |
| Pulse history (7d) | ✅ | ✅ |
| Pulse history (90d) | ❌ | ✅ |

### Estimated Effort
~2 hours
