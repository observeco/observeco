# ObserveCo Privacy Policy

**Effective date:** June 6, 2026
**Last updated:** June 6, 2026

---

## The Short Version

ObserveCo runs entirely on your machine. Your data never leaves your computer unless you explicitly opt in to telemetry. We don't run servers that store your data. We don't have user accounts. We don't sell your data because we never see it.

---

## 1. What ObserveCo Is

ObserveCo is a local-first AI agent monitoring tool. It runs as a CLI and dashboard on your machine, monitoring your AI agents' health, token usage, and configuration. It stores all data in a local SQLite database on your computer.

ObserveCo is not a cloud service. There are no ObserveCo servers that process or store your data.

---

## 2. What Data We Collect

### 2.1 Data Stored Locally (Always)

ObserveCo stores the following data **on your machine only** in `~/.observeco/pulse.db`:

| Data Type | What It Is | Why We Store It |
|-----------|-----------|----------------|
| Agent health pulses | Agent name, status, PID, uptime, memory usage | Dashboard display, health monitoring |
| Token usage logs | Token counts per turn, cost estimates, provider | Cost tracking, anomaly detection |
| Error logs | Agent error messages, timestamps | Error analysis, auto-heal |
| Circuit breaker state | Failure counts, cooldown timers | Auto-heal logic |
| Chisel compression data | Before/after token counts, savings | Compression dashboard |
| Plugin tracking stats | Plugin name, cost per call, error rate | Plugin Firewall feature |
| Drift measurements | Drift scores over time | Drift trend charts |
| Anomaly records | Detected issues, severity, status | Anomaly Inbox |
| Alert history | Alerts sent, delivery status | Alert Management |
| Session checkpoints | Context snapshots for restore | Session Insurance feature |
| Configuration events | SOUL.md edits, plugin installs | Relapse Prevention feature |

**This data never leaves your machine** unless you explicitly opt in to telemetry (see §2.2).

### 2.2 Telemetry (Opt-In Only)

ObserveCo has an **optional** telemetry system. It is **disabled by default**.

When telemetry is enabled (via the opt-in file at `~/.observeco/.telemetry_opt_in`), we receive:

| Data Sent | Frequency | Purpose |
|-----------|-----------|---------|
| Machine ID (random hash) | Once | Aggregate unique-user counts |
| Event type (e.g., "plugin_installed", "chisel_ran") | Per event | Feature usage analytics |
| ObserveCo version | Per event | Version adoption tracking |
| OS platform | Per event | Platform compatibility |

**We never receive:**
- Your agent names, configurations, or content
- Your token usage data or cost information
- Your SOUL.md files, MEMORY.md, or any agent memory
- Your API keys, license keys, or credentials
- Your chat messages or conversation content
- Any personally identifiable information

Telemetry is fire-and-forget — each event is a small JSON payload sent over HTTPS and discarded. We don't maintain telemetry databases that link events to users.

### 2.3 License Validation

When you have an active Pro subscription, ObserveCo validates your license key:

- License key is stored locally in `~/.observeco/license.json` with restricted permissions (0600)
- Validation checks against our license server once every 24 hours
- The validation request contains only your license key (no usage data, no agent data)
- Validation result is cached locally for 24 hours — if the server is unreachable, your Pro features continue working from cache

---

## 3. What We Never Do

- **We never read your agent content.** We see token counts and file sizes, never the content of your SOUL.md, MEMORY.md, chat messages, or agent outputs.
- **We never run servers that store your data.** Your data lives in `~/.observeco/pulse.db` on your machine. Period.
- **We never sell your data.** We don't have a business model based on data. We sell a software product (Pro tier).
- **We never track you across the web.** ObserveCo has no cookies, no analytics scripts, no tracking pixels.
- **We never access your machine remotely.** ObserveCo runs locally. We have no remote access capability.
- **We never share your data with third parties.** There are no third-party data processors.

---

## 4. How We Protect Your Data

### 4.1 Local Storage

- All data stored in SQLite (`~/.observeco/pulse.db`) with WAL mode for concurrent access safety
- License key file (`~/.observeco/license.json`) stored with 0600 permissions (owner read/write only)
- No data is stored in world-readable directories
- Database pruning runs daily — Free tier retains 7 days, Pro tier retains data per your configuration

### 4.2 Network Communication

- License validation uses HTTPS to our license server (encrypted in transit)
- Telemetry (if enabled) uses HTTPS to our telemetry endpoint (encrypted in transit)
- Dashboard binds to localhost only (127.0.0.1:8090) — not accessible from your network
- No data is sent to ObserveCo over unencrypted connections

### 4.3 Plugin Communication

- The ClawForge OpenClaw plugin communicates with ObserveCo via localhost HTTP (`http://localhost:8420`)
- No plugin data is sent over the network — all communication is local
- Plugin stats are stored in your local SQLite database

---

## 5. Your Rights

Since ObserveCo is local-first, you have full control:

- **Access:** Your data is in `~/.observeco/pulse.db` — you can open it with any SQLite tool
- **Delete:** Delete `~/.observeco/pulse.db` to remove all ObserveCo data
- **Export:** Query the SQLite database directly — no export API needed because you already have the data
- **Opt out of telemetry:** Delete `~/.observeco/.telemetry_opt_in` or never create it
- **Disable Pro features:** Change your license to Free tier — all data remains local

---

## 6. Children's Privacy

ObserveCo is not directed at children under 13. We do not knowingly collect data from children. Since ObserveCo is a local tool that doesn't transmit personal data, this section exists for completeness.

---

## 7. Changes to This Policy

We will update this policy when our data practices change. The "Last updated" date at the top will reflect the most recent change. We will not retroactively change how existing data is handled.

---

## 8. Contact

For privacy questions, contact us at:

- **Email:** privacy@observeco.ai
- **GitHub:** [open an issue](https://github.com/observeco/observeco/issues) (for public, non-sensitive questions)

---

## 9. Open Source

ObserveCo is open source under the MIT license. You can verify our privacy claims by reading the source code:

- `src/observeco/db.py` — local data storage (no outbound calls)
- `src/observeco/telemetry_client.py` — opt-in telemetry (disabled by default)
- `src/observeco/dashboard/server.py` — dashboard (localhost-only binding)
- `src/observeco/alert/delivery.py` — push alerts (sends only to your configured channels)

**Trust, don't verify — then verify anyway.**

---

*ObserveCo: Your agents. Your data. Your machine.*
