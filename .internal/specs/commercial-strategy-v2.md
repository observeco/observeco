# ObserveCo Commercial Strategy v2

**Date:** 2026-06-29 (updated from 2026-06-19)
**Author:** Hermes Main (DeepSeek V4 Flash)
**Status:** Live — Hermes beachhead active. Multi-framework (OpenClaw, Claude Code, Ollama) deferred to post-v1.0.

---

## 1. The Beachhead

**Target:** Hermes users on Mac Mini.
**Pricing:** Free. All features available. No gating.
**The catch:** A single banner: *"1,247 agent invocations this month — ObserveCo is free for Hermes."*

**Banner evolution (3 phases):**
1. **Phase 1 (beachhead, now):** Static value signal — "X invocations this month — ObserveCo is free for Hermes." No click-through. Frames value, builds trust.
2. **Phase 2 (Pro announced):** Clickable banner → "1,247 invocations. Pro unlocks push alerts + extended history. [Learn more]" → links to pricing/feature comparison page.
3. **Phase 3 (Pro live):** "1,247 invocations. [Start 30-day free trial]" → one-click trial activation via Stripe.

The banner never becomes a nag. At each phase, it offers a clear next action. The user always knows what to do with the number they're seeing.

**Why this works:**

Hermes users on Mac Mini are the hardest-corner case — they already optimise costs. If ObserveCo works for them, it works for anyone. The beachhead validates:

1. Generic Hermes discovery (any `~/.hermes` install, not just Sean's layout)
2. All existing features (health, tokens, drift, chisel, alerts, etc.) working for a non-Sean Hermes setup
3. Agent invocation counting built into the free tier (the tracking mechanism itself)

The banner is Honest: it tells them "this is valuable, we're counting, and we're not charging you." Free users see their agent is making 2,000+ calls/month — at $0.50/1K tokens that's $30 worth of LLM calls they're tracking for free. The banner frames the value.

---

## 2. The Tier Structure

| | Hermes (Beachhead) | Multi-Framework (Future, post-v1.0) |
||---|---|---|
| **Pricing** | Free forever | TBD |
| **Features** | All features | All features that apply |
| **Gating** | None | None |
| **Ethos** | "We support Hermes first" | "Expanding to your stack" |
| **Banner** | Agent invocation count | Agent invocation count |
| **LLM features** | BYOK (`OBSERVECO_LLM_API_KEY`) | BYOK (`OBSERVECO_LLM_API_KEY`) |

**Wait — there's no difference in the table.** That's intentional. The distinction is *who we build for first*, not *what we charge*. The pricing for Pro comes later, when we've validated the beachhead and built a real premium tier (team, cloud sync, compliance exports, etc.).

For now: **free for everyone who can make it work.** LLM features use your own API key — no inference costs on us. The agent invocation banner is the only monetisation signal — it prepares the user for eventual pricing while delivering full value today.

---

## 3. The Non-Negotiable Preconditions

Before the beachhead works, these MUST be true:

### 3.1. Agent invocation counting

Every Hermes agent turn must increment a counter. This is the banner's data source.

**How:** The post-turn hook (Feature 43) already exists — it fires `POST /api/tokens/log` after every LLM turn. The endpoint is built, the DB migration is done. The webhook payload already contains: `agent_name`, `turn_id`, `model`, `provider`, `total_tokens`.

**What exists:** The endpoint (`server.py:7006`) and DB migration 29 exist. The `turn_logs` table stores per-turn data. The Hermes hook daemon thread does **not** exist — there is no wiring between Hermes agent turns and `/api/tokens/log`. The `invocation_counter.py` module is dead code (enforces a 5/day cap, never called from real code paths) and will be deleted in Phase 0 (P0-11).

**What's needed:**
1. Fix `require_pro()` — currently checks a hardcoded 150/month cap instead of `LicenseState.is_pro` (see §6.1) — P0-10
2. Wire the post-turn hook to call `/api/tokens/log` (or `record_invocation()` if keeping the counter) — P1-1
3. Build the banner: `SELECT COUNT(*) FROM turn_logs WHERE timestamp >= date('now', 'start of month')` — single SQL query + banner div — P1-1
4. Banner shows "0 invocations this month" gracefully when no data exists (fresh install)

**Data source:** The banner queries `turn_logs` directly, not `invocation_counter.py`. The `invocation_counter.py` module is deleted in Phase 0 — it's dead code that enforces a 5/day cap and would fire immediately if wired to the post-turn hook.

**Cost:** ~2h total (P0-10: 5min + P1-1: 1h + wiring: 1h). The earlier estimate of 4h was pessimistic — the banner is one SQL query.

### 3.2. Generic Hermes discovery

The product must discover a non-Sean Hermes install. Currently it hardcodes `~/.hermes` in 13 files and `~/.openclaw` in 7 files.

**Fix needed:** A single `hermes_home()` function in `dirs.py` that:
1. Checks `OBSERVECO_HERMES_HOME` env var
2. Checks `~/.hermes/`
3. Checks XDG config (`~/.config/hermes/`)
4. Checks `hermes config path` CLI command
5. Returns `None` if none found

All 13 files import from `dirs.py`. No hardcoded paths.

**Liveness check (beyond directory existence):** A directory check is not a user check. These scenarios all pass as "Hermes user" but aren't:
- Installed Hermes once, never configured an agent
- Uninstalled Hermes but left `~/.hermes/` directory
- Primarily runs OpenClaw but has Hermes installed for a side project
- Has a stale `~/.hermes/` from a previous machine migration

**Additional verification:** After finding `hermes_home()`, verify at least one of:
- `~/.hermes/profiles/` is non-empty (at least one agent profile exists)
- Recent Hermes agent activity in `observeco.db` (agent discovered within last 30 days)
- `hermes config path` returns a valid, readable config

If directory exists but no profiles/activity/config, treat as "non-Hermes" — generic discovery only. This prevents a stale directory from unlocking features the user can't use, and prevents a legitimate OpenClaw-primary user from getting misclassified.

**Non-negotiable because:** Without this, the product doesn't find *any* Hermes install that doesn't match Sean's exact layout. The dashboard shows "no agents found."

### 3.3. No personal artifacts

- No `seanfzc.ics` or `seanfzc_calendar.json` — use generic calendar discovery or remove
- No `"kepler"` special-case in agent name detection — discover from profile directory names only
- No `~/AGENTS.md` or `~/SOUL.md` in home directory root — only scan `~/.hermes/profiles/*/`
- No 4 fake plugins (`ClawForge`, `NeuralSearch`, etc.) and 3 fake services (gateway/WAT/imessage bridge) in dashboard — remove hardcoded entries

**Non-negotiable because:** A new user sees someone else's agent names, calendar files, and DOWN services. That's not a product — it's a development environment.

**Scope note:** Phase 0 removes code-level artifacts only. Sean's existing `observeco.db` / `pulse.db` may still contain records with these names (kepler agent, fake plugins, fake services, calendar references). This is acceptable — Sean's instance is a development environment, not a product installation. A fresh `pip install observeco` on a clean machine will have no such data. No DB migration needed for Phase 0.

### 3.4. Graceful degradation

Every Hermes-specific feature handles "no Hermes found" without crashing:
- Dashboard section: "Hermes agent: not detected"
- Chisel feature: "Install Hermes to use skill compression"
- Drift detection: skips if no profiles found
- Gateway monitoring: skips if no gateway found

**Non-negotiable because:** If the product crashes on a clean Mac Mini, the free beachhead doesn't exist.

---

## 4. Framework Compatibility (Keep)

The master plan says:

> "Framework support: any framework via `observeco agent add` + health check. Full token/drift for Hermes + OpenClaw"

This stays. The discovery architecture flips to:

```
Generic scan (always runs first):
  - ollama list → discover models
  - psutil process scan → running agents
  - ~/.claude/projects/ → discover projects
  - Port scan (11434, 9119, etc.)
  - oboeveco/config.yaml → user-defined agents

Framework adapters (optional enrichment):
  - Hermes: full token tracking, chisel, drift, profile scanning
  - OpenClaw: full token tracking, plugin monitoring, intent classifier
  - Generic: health check, port monitoring, process uptime
```

No code needs to change for non-Hermes frameworks to show up. The dashboard already displays any agent that gets discovered. The only difference: Hermes gets deeper instrumentation (chisel, drift, post-turn hooks, SOUL.md health), because that's what our beachhead audience runs.

---

## 5. Product Changes Required

### Phase 0 (emergency — ship-stoppers)

| # | Change | Files affected | Effort |
|---|---|---|---|
| P0-1 | Add `hermes_home()` + `openclaw_home()` + `is_hermes_active()` to `dirs.py`. Move `hermes_home()` from `config.py` to `dirs.py` (it's a path function). `is_hermes_active()` checks: profiles non-empty, recent activity in DB, valid config.yaml. | 2 files (dirs.py created/modified, config.py import updated) | 2h |
| P0-2 | Make all path constants lazy (functions, not module-level). Fix duplicate definitions at `config.py:35-36` and `config.py:53-54`. | 1 file | 1h |
| P0-3 | Refactor **30+** `~/.hermes` hardcodes → import from `dirs.hermes_home()`. Files: `config.py`, `chisel/llm_client.py`, `chisel/skill_compress.py`, `chisel/trim.py`, `chisel/watch.py`, `chisel/config_scanner.py`, `dashboard/server.py`, `heal/__init__.py`, `clawforge/profile.py`, `clawforge/garden.py`, `db.py`, `pa_brief_diff.py`, `cli/billing_wire.py`, `capability/probe.py`, `proxy/server.py`, `tracking/sdk/provider_registry.py`, `gateway_monitor.py` | 17 files | 4h |
| P0-4 | Refactor **10+** `~/.openclaw` hardcodes → import from `dirs.openclaw_home()`. Files: `dashboard/config.py`, `db.py`, `tracking/sdk/provider_registry.py`, `gateway_monitor.py`, `clawforge/` | 5 files | 1.5h |
| P0-5 | Remove `seanfzc.ics` and `seanfzc_calendar.json` from `pa_brief_diff.py` | 1 file | 15min |
| P0-6 | Remove `"kepler"` special-case from `config.py:119,152` | 1 file | 15min |
| P0-7 | Remove `~/AGENTS.md` and `~/SOUL.md` from home-root scan in `config.py:144-145` | 1 file | 15min |
| P0-8 | Remove 4 fake plugins + 3 fake services from `dashboard/config.py` | 1 file | 15min |
| P0-9 | Change `"hound"` default to `""` in `metric_exemptions.py` | 1 file | 15min |
| P0-10 | Fix `require_pro()` in `license.py:985-998` — replace invocation-cap check with `return load().is_pro`. **Note:** This removes all gating. Banner Phase 2/3 conversion path depends on future Pro features being built — gating infrastructure stays dormant but wired. | 1 file | 5min |
| P0-11 | Delete `invocation_counter.py` — dead code that enforces 5/day cap. Banner uses `COUNT(turn_logs)` from DB, not this counter. | 1 file (deleted) | 5min |
| P0-12 | Add `OBSERVECO_LLM_API_KEY` detection to `llm_service/__init__.py:_detect_llm_providers()`. Add API key presence check to `gate.py:should_call()` — return `False` (static fallback) when no key configured. | 2 files | 1h |
| P0-13 | Add `OBSERVECO_LLM_API_KEY` detection to `chisel/llm_client.py:get_api_key()` — parallel LLM path that bypasses `llm_service/gate.py`. | 1 file | 30min |
| P0-14 | Fix `gateway_monitor.py:41-42` — replace `HERMES_HOME`/`OPENCLAW_HOME` module-level constants with imports from `dirs.hermes_home()`/`dirs.openclaw_home()`. Change env var name to `OBSERVECO_HERMES_HOME`. | 1 file | 15min |
| **Total P0** | | | **~12h** |

### Phase 1 (beachhead readiness)

| # | Change | Effort |
|---|---|---|
| P1-1 | Dashboard banner: "X agent invocations this month" from `COUNT(turn_logs)` | 1h |
| P1-2 | Graceful degradation: every Hermes-specific feature guards on `hermes_home()` returning None | 2h |
| P1-3 | Consolidate env var namespace: `OBSERVECO_HERMES_HOME` (not split) | 1h |
| P1-4 | Document all config env vars in `observeco config --help` | 30min |
| P1-5 | Add `observeco init` that runs discovery, writes `~/.observeco/config.yaml` | 2h |
| P1-6 | Fix health check (port 9119) to read from config, not hardcode | 30min |
| **Total P1** | | **~7h** |

### Phase 2 (generic discovery layer)

| # | Change | Effort |
|---|---|---|
| P2-1 | `ollama list` scanner → discover models + register as services | 3h |
| P2-2 | `~/.claude/projects/` scanner → discover Claude Code projects | 3h |
| P2-3 | Process scanner (`psutil`) → discover running agent processes | 4h |
| P2-4 | Port scanner (common ports) → discover running services | 3h |
| P2-5 | Dashboard: show per-framework tag per agent (Hermes / Claude Code / Ollama / Generic) | 3h |
| P2-6 | Integration testing + edge cases (empty scans, permission errors, stale processes) | 4h |
| **Total P2** | | **~20h (~3d)** |

**Note:** Earlier estimate of 5.5h was coding-only (no testing, no edge cases, no dashboard integration). Master plan estimate of ~3d is the conservative figure — includes test writing, edge case handling, and UI integration. Use 3d for sprint planning.

**Grand total:** ~39h (~5.5d) of work. (Phase 0: ~12h + Phase 1: ~7h + Phase 2: ~20h)

---

## 6. What Does Not Change

- The dashboard layout. All existing features stay.
- The license/trial/Pro infrastructure in `license.py` — **needs one critical fix before anything else ships.** `require_pro()` (line 985–998) does NOT check `LicenseState`. It checks a hardcoded invocation counter cap of 150/month from `invocation_counter.py:90`. This means the moment you wire any real invocation source to `record_invocation()`, every free user gets locked out of Pro-gated features at 150 invocations, regardless of license state. `require_pro()` must be changed to: `return load().is_pro`
- The Stripe integration in `billing.py` — leave it wired but dormant until Pro tier is priced.
- The /api/tokens/log endpoint — already built, already working.
- The post-turn Hermes hook — already built, already firing.
- The chisel/auto-heal/drift/alerts features — all already work for any Hermes agent.
- The test suite — all existing tests remain valid.

## 6.1. Critical Bug: `require_pro()` checks invocation count, not license state

`require_pro()` at `license.py:985-998` has a "belt-and-suspenders" enforcement that overrides the actual license:

```python
def require_pro() -> bool:
    from observeco.invocation_counter import get_stats
    stats = get_stats()
    if stats["this_month"] >= stats["monthly_limit"]:
        return False
    return True
```

`monthly_limit` is hardcoded at 150 (`invocation_counter.py:90`). This means:

- **With the commercial strategy proposed here** (free for Hermes users, all features open), this function still locks Hermes users out of Pro-gated features after 150 invocations.
- The moment we wire `record_invocation()` to anything real (the post-turn hook, the banner, etc.), this lockout becomes active.

**Fix required before anything else:**

```python
def require_pro() -> bool:
    """Check if Pro features are unlocked. Returns True if Pro or trial active."""
    state = load()
    return state.is_pro
```

This is a 5-minute change. It removes the invocation-cap logic entirely. The banner will display agent invocation count — that's a marketing signal, not an enforcement mechanism.

---

## 7. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Generic discovery finds nothing on a clean Mac Mini | Low (Ollama or Claude Code is common) | High (product seems empty) | Dashboard shows "No agents found. Install Hermes, Ollama, or Claude Code." with links |
| Agents with unusual Hermes layouts fail silently | Medium | Medium | Graceful degradation at every level — no crash, component just shows N/A |
| Beachhead users expect free forever and don't convert | High | Low (we knew this) | The banner evolves through 3 phases (see §1): static value signal → clickable "Learn more" → one-click trial. Each phase offers a clear next action. When Pro ships, free users see "1,247 invocations — [Start 30-day free trial]." |
| Someone discovers `OBSERVECO_ADMIN_KEY` default in source | Low | Low (env var override exists) | Remove from source. Already low priority. |

---

## 8. Summary — One Sentence

> Make ObserveCo work on `pip install observeco && observeco dashboard` on any Mac Mini running Hermes, count every agent invocation, show a banner with the count, and ship all features free.

The commercial strategy is not pricing. It's **proving the product works on someone else's machine.** The banner is the only monetisation signal until that's proven.
