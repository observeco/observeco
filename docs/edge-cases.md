# Edge Cases & Troubleshooting

What happens when things aren't configured yet — and how to fix it.

---

## 1. You don't have Hermes installed

ObserveCo does not require Hermes. It works standalone.

**What you see:** A clean empty dashboard with an info banner: "No agents discovered yet." And a button `+ Missing an agent?` in the header.

**What to do:**
```
observeco agents add my-agent --framework crewai --health-check "http://localhost:8000/health"
observeco pulse check
observeco dashboard
```
The dashboard populates as soon as you've added at least one agent.

**What does NOT happen:** Crash, stack trace, blank page, or infinite spinner. Every state has a dedicated UI treatment.

---

## 2. You have Hermes but no agents

Hermes installs cleanly with no agents configured. No SOUL.md files exist yet in `~/.hermes/profiles/`.

**What you see:** Same empty-dashboard flow as §1. The auto-discovery scan (run on `observeco dashboard`) finds zero profiles and falls through to the "No agents discovered" banner.

**What to do:**
```
observeco agents add <name> --check <url-or-path>
```
Or configure agents normally. The dashboard will pick them up on next refresh (30s auto-refresh).

---

## 3. Your agent fleet is all dead

Every agent is registered but unreachable — processes stopped, containers down, health endpoints unresponsive.

**What you see:**
- Fleet summary: "0 alive · N dead"
- Each agent card shows 🔴 with "Dead" status
- Circuit breaker state shows tripped (⚡ Open) after 3 consecutive failures
- Error timeline populates with connection timeouts
- A banner appears: "N agents unreachable"

**What the system does automatically:**
- Circuit breaker enters 5-minute cooldown after 3 failures
- No repeated hammering — reduces 2,880 checks/day to ~8
- Cooldown auto-expires and retries

**What to do:**
```
# Restart agents
observeco pulse check        # Re-run health checks after restart
observeco pulse circuit      # Verify circuit breakers reset
```

---

## 4. Monitoring daemon stopped

The watch daemon (`observeco start`) that collects pulse data has been stopped for 2+ hours.

**What you see:** A warning banner: "Monitoring stopped Xh ago. Data shown is from last checkpoint."

**What to do:**
```
observeco start               # Resume monitoring
observeco dashboard           # Verify live data returns
```

**What does NOT happen:** Data disappears. The last checkpoint remains visible so you don't lose context.

---

## 5. No pulse data yet (fresh install)

First-time run — no health checks have ever been executed.

**What you see:**
- Agent cards show ⚪ (Unknown) status dots with "No pulses" text
- Each card shows a helpful note: "No pulse data — this agent may not be monitored via pulse checks. Configure a health check or use platform-specific monitoring."
- The `observeco agents list` command lists agents but shows check status as "never checked"

**What to do:**
```
observeco pulse check        # Run a full fleet health check
observeco dashboard          # Refresh — status dots populate
```

---

## 6. Config file corruption

`agents.json` or `config.yaml` is unreadable (bad JSON, permission issues, truncation from a crash).

**What you see:** A critical-error banner: "Could not read config file — check permissions."

**What to do:**
```
observeco config validate    # Find the issue
chmod 644 ~/.config/observeco/agents.json   # Fix permissions if needed
observeco agents check       # Rebuild from auto-detect if config is damaged
```

---

## 7. Port 9119 already in use

Another dashboard instance, or any other service, is using the default port.

**What happens:** Dashboard auto-falls back to the next available port (9120, 9121, etc.). The terminal prints: "Port 9119 in use — serving on 9120."

**To force a specific port:**
```
observeco dashboard --port 9200
```

---

## 8. No agents fit any status filter

You click "Alive" but every agent is dead — or you click "Down" but everything's fine.

**What you see:** Empty filter result with a clear message: "No agents match this filter. Try a different status." The filter buttons remain available so you can switch views.

**Not a bug.** This is expected — the filters are status-specific and reflect the live fleet state.

---

## 9. Stripe billing not configured

You see "Subscribe $9/mo" but clicking it doesn't open a checkout.

**Likely cause:** No `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` environment variables set. The UI renders the Pro upsell on detection of a license-free install, but Stripe integration is optional — the dashboard works fully without it.

**What to do (maintainers):**
```bash
export STRIPE_SECRET_KEY=sk_live_...
export STRIPE_PUBLISHABLE_KEY=pk_live_...
export SOLO_PRICE_ID=price_...
observeco dashboard
```

---

## 10. Unsupported platform CLI (non-macOS)

Some features (launchd daemon management, `observeco start`) are macOS-specific.

**What you see:** Commands that rely on platform-specific tooling print a clear error: "This command requires launchd (macOS only). Use `observeco watch` for cross-platform polling."

**Supported everywhere:** `pulse check`, `dashboard`, `chisel`, `clawforge`, `agents`, `config`.

---

## Summary: Dashboard Self-Diagnostics

| Symptom | Banner | Auto-Fix | User Action |
|---------|--------|----------|-------------|
| No Hermes install | ℹ️ No agents discovered | — | `agents add <name>` |
| No agents configured | ℹ️ No agents discovered | — | `agents add` / `pulse check` |
| All agents dead | ⚠️ N unreachable | Circuit breaker cooldown | Restart agents |
| Monitoring stopped 2h+ | ⚠️ Stopped Xh ago | — | `observeco start` |
| Config corrupted | ❌ Can't read config | — | `config validate`, fix permissions |
| Port in use | Terminal log only | Falls to next port | `--port` flag |
| No stripe keys | — | UI renders without billing | Set env vars (optional) |
