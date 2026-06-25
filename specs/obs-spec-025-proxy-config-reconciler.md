# obs-spec-025 — Proxy Config Reconciler

**Spec ID:** obs-spec-025
**Title:** Proxy config reconciler — never leave an agent pointing at a dead proxy
**Document version:** 2.1
**Status:** ⬜ DRAFT — for review
**Owner:** Hound (arch) → Pragma (infra) → Main (impl)
**Created:** 2026-06-16
**Implements:** obs-spec-024 task 24.6 (the `proxy-config` tier's machinery for `cost_tracking` / `tool_call_tracking`).
**Master plan ref:** v2.35 (deprecated) — this spec retires the `_original_base_url` side-channel that §4.3, §4.7, and §4.13 depended on.
**Standards:** GS-019 (Data & Observability Continuity) — §6 is mandatory and is written here as the reusable parity-spec template (Appendix A).
**Target stack:** Hermes / OpenClaw on macOS. Reads/writes provider `base_url` only through the obs-spec-024 runtime adapters, so it is version- and runtime-agnostic by construction.

---

## 1. Trigger & Context

Today, enabling exact cost/tool-call tracking rewrites the agent's `config.yaml` so each provider's `base_url` points at the ObserveCo proxy, and stores the original in a `_original_base_url` field **inside the user's config**. Three failures follow:

1. **Dead-port lockout.** If the proxy dies (SIGKILL, OOM, crash, the user stops it), the config still points at a dead `localhost:<port>`. Every LLM call is refused until the user manually reverts. This directly contradicts the deprecated master plan's promise — "if proxy is down, agents still work" — which the current mechanism cannot keep.
2. **Routing table silently empties.** §4.13 rebuilds the multi-upstream routing table by reading `_original_base_url` back out of the user's config. A Hermes upgrade that rewrites the config, or another tool (Skillclaw) that drops the field, leaves the table empty and the proxy falls back to a wrong default upstream — silently.
3. **No crash-safe undo.** A `revert` CLI command exists but nothing calls it on crash; revert state lives in a file ObserveCo doesn't control.

This spec introduces a **reconciler**: a small control loop that owns one invariant and continuously enforces it, plus an ObserveCo-owned snapshot store that makes revert and routing independent of the user's config. It is the single component that makes "the proxy can die at any instant and the agent keeps working" true.

**Important context:** The reconciler is only needed for the `proxy-config` tier (config-rewrite, opt-in). The default `proxy-launcher` tier (env injection, crash-safe by construction) needs no reconciler because nothing is written to disk. See obs-spec-024 §5.2 for the tier distinction.

---

## 2. The invariant

> **The agent's provider `base_url` points at a *live* ObserveCo proxy, XOR at the real upstream. It must never point at a dead proxy.**

There are three **resting** states (all acceptable) and one **forbidden transient** state that the loop must exit within one tick:

```
  CONVERGED_OBSERVING   config → live proxy        (desired, exact telemetry)
  CONVERGED_UPSTREAM    config → real upstream      (safe: tracking off, or relaunch budget spent)
  FOREIGN_PROXY         config → a non-ours proxy   (chain, e.g. Skillclaw — handled, not clobbered)
  ────────────────────────────────────────────────
  DEAD_PORT (forbidden) config → our proxy, dead    (every call fails — must be left within one tick)
```

The loop never relies on graceful shutdown. SIGKILL / OOM / power-loss cannot be caught, so the design treats *every* exit as ungraceful and heals on the next reconcile pass regardless of how the proxy died.

---

## 3. Architecture

### 3.1 ObserveCo-owned snapshot store

Revert and routing state live in ObserveCo's own SQLite, **never** in the user's config. Migration 22 adds:

```sql
CREATE TABLE proxy_config_snapshots (
  id                 INTEGER PRIMARY KEY,
  config_path        TEXT NOT NULL,
  runtime            TEXT NOT NULL,           -- hermes | openclaw
  provider           TEXT NOT NULL,           -- e.g. deepseek, custom-ollama
  original_base_url  TEXT NOT NULL,           -- the real upstream (source of the routing table)
  original_blob      TEXT NOT NULL,           -- full original config bytes, for byte-exact revert
  our_last_write_hash TEXT,                   -- sha256 of the file AFTER our last write
  active             INTEGER NOT NULL DEFAULT 1,
  created_at         REAL NOT NULL,
  UNIQUE(config_path, provider)
);
```

`original_base_url` per provider **is** the multi-upstream routing table (deprecated master plan §4.13), now sourced from a store ObserveCo controls. The `_original_base_url` field is removed from the user's config entirely.

### 3.2 Desired vs actual state

- **Desired** (ObserveCo's intent): `{mode: observe|off, port: <ephemeral>, providers: [...]}`, persisted in ObserveCo state.
- **Actual**: read live each pass — current `base_url` per provider (via the obs-spec-024 runtime adapter) and whether a proxy is alive on the referenced port.

```python
# src/observeco/proxy/reconciler.py
from dataclasses import dataclass, field

@dataclass
class DesiredState:
    mode: str = "off"           # "observe" | "off"
    port: int = 0               # ephemeral port from probe
    providers: list[str] = field(default_factory=list)
```

The reconciler's only job is to drive *actual* toward *desired* while never passing through the forbidden state in a way that outlives one tick.

### 3.3 The reconcile loop

Runs on four triggers, layered fastest-to-slowest so the dead-port window shrinks to near-zero in the common case:

| Trigger | Latency to heal | Covers |
|---------|------------------|--------|
| Proxy-exit signal (supervisor catches `SIGCHLD`) | ~ms | normal crash, user stop, OOM of the proxy alone |
| Reconcile tick (default 10 s, configurable) | ≤ tick | supervisor missed / bypassed |
| Boot reconcile (on ObserveCo start) | < restart | whole ObserveCo daemon died |
| launchd `KeepAlive` watchdog | < 30 s | the daemon won't restart itself (uses `can_install_launchagent`) |

**Trigger-source logging:** Every reconcile pass logs which trigger fired (SIGCHLD, tick, boot, launchd). This is critical for production observability — if the fast path (SIGCHLD) is never firing, you need to know so you can fix the supervisor wiring.

```python
# src/observeco/proxy/reconciler.py  (pseudocode)
def reconcile(state, store, adapter, proxy, trigger: str):
    log_reconcile_start(trigger)  # "SIGCHLD" | "tick" | "boot" | "launchd"
    if state.desired.mode == "off":
        for p in store.active_providers(): revert(adapter, store, p)
        return

    alive, port = proxy.ensure_alive(state.desired.port)   # relaunch w/ budget + circuit-breaker; see 3.4
    for provider in state.desired.providers:
        actual = adapter.get_base_url(state.config_path, provider)   # version-agnostic
        if actual is None:
            continue
        cls = classify(actual, proxy, port, store, provider)
        if   cls == "CONVERGED_OBSERVING": continue
        elif cls == "DEAD_PORT":
            if alive:                       # relaunched this pass → repoint to new port
                repoint(adapter, store, provider, proxy.url(port))
            else:                           # budget + circuit exhausted → fail safe
                revert(adapter, store, provider)
                alert("proxy_unrecoverable", provider)
        elif cls == "UPSTREAM":             # fresh / externally reverted; proxy is up
            snapshot_if_absent(store, adapter, provider, actual)
            repoint(adapter, store, provider, proxy.url(port))
        elif cls == "FOREIGN_PROXY":
            handle_chain(provider, actual)  # don't clobber; see 3.7
        elif cls == "DRIFTED":
            re_snapshot(store, adapter, provider, actual)  # user changed it; see 3.7
```

### 3.4 Actions & idempotency

| Actual state | Proxy alive? | Action | Result |
|--------------|--------------|--------|--------|
| CONVERGED_OBSERVING (right port) | yes | none | no-op (idempotent) |
| DEAD_PORT | relaunch succeeded | `repoint` to new port | CONVERGED_OBSERVING |
| DEAD_PORT | relaunch budget + circuit exhausted | `revert` to upstream + alert | CONVERGED_UPSTREAM (agent works, no telemetry) |
| UPSTREAM (desired=observe) | yes | snapshot-if-absent → `repoint` | CONVERGED_OBSERVING |
| FOREIGN_PROXY | n/a | chain-handle / warn | unchanged |
| DRIFTED (external edit) | n/a | re-snapshot, no clobber | unchanged |
| any (desired=off) | n/a | `revert` to upstream | CONVERGED_UPSTREAM |

**Relaunch budget + circuit-breaker.** `ensure_alive` retries the proxy up to N times in a rolling window (default 3 / 60 s). Once exhausted, a **circuit-breaker** engages: back off for 5 minutes before attempting again. This prevents a flapping proxy from hammering relaunch and config-write in a tight loop when the proxy binary is fundamentally broken (bad port, binary missing, dependency missing). The circuit-breaker state is persisted so it survives an ObserveCo restart.

The tradeoff is explicit and non-negotiable: **a working agent with degraded observation beats a broken agent with intended observation.** A revert raises a dashboard alert because it means the proxy could not be kept alive.

Every action is idempotent: a converged pass writes nothing; running `reconcile` twice back-to-back produces no second write.

### 3.5 Atomic + validated writes

All config writes go through one function:

```python
def atomic_write_base_url(path, provider, url, adapter):
    doc = adapter.load(path)
    adapter.set_base_url(doc, provider, url)
    validate_no_truncated_keys(doc)              # reject any key matching r'\.\.\.' or failing provider regex
    tmp = f"{path}.observeco.tmp"
    with open(tmp, "w") as f:
        adapter.dump(doc, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)                         # atomic rename: file is always old-or-new, never partial
    store.set_last_write_hash(path, provider, sha256_file(path))
```

`validate_no_truncated_keys` closes the key-corruption bug class: a masked/display value (`sk-68e...724a`) can never be persisted, because the write boundary rejects it. We only ever set `base_url`; all other fields are preserved exactly as the user left them.

### 3.6 Crash-safety layering

SIGTERM/SIGINT handlers attempt a clean revert/relaunch, but they are an optimization, not the guarantee. The guarantee is the layered reconcile (3.3): the boot reconcile and launchd watchdog heal the cases no handler can catch. **No correctness property depends on a graceful shutdown ever running.**

### 3.7 Concurrency & external modification

- **Single writer.** The reconciler holds an advisory lock on ObserveCo's state dir; a second ObserveCo instance refuses to manage config and logs the conflict (prevents two reconcilers fighting).
- **Clobber guard.** Before writing, compare the file's current hash to `our_last_write_hash`. A mismatch means something other than us changed the config — the reconciler does **not** blindly overwrite. If the changed value is upstream/foreign it re-snapshots (DRIFTED); if the user edited unrelated fields, those are preserved because we only set `base_url`.
- **Chain detection (Skillclaw etc.).** If the current `base_url` is a localhost proxy that isn't ours (cross-referenced against `existing_proxies` from the environment snapshot, e.g. `skillclaw:30000`), the reconciler treats it as FOREIGN_PROXY: it does not clobber. It either upstreams our proxy to the foreign one (consolidate) or surfaces a one-line warning offering consolidation — never a silent third hop.

### 3.8 Routing table from snapshot

The proxy's multi-upstream routing table is built at startup from `proxy_config_snapshots.original_base_url` (per provider), not from the user's config. This makes routing immune to config rewrites, Hermes upgrades, and field-dropping by other tools — the failure mode that empties the table today.

### 3.9 Fail-open proxy contract (referenced)

The reconciler protects the **config** side of the request path. The proxy must independently protect the **request** side: if its logging or risk engine throws, it still forwards upstream as a pass-through and returns the real response — it never 502s because observation failed. Both halves are required for "the agent never breaks." (Proxy fail-open is tracked in obs-spec-024 task 24.6; named here for completeness.)

---

## 4. Relationship to the capability layer

The reconciler is the machinery behind the `proxy-config` tier in obs-spec-024 §5. It is only ever activated when the user opts into config-rewrite (not the default). Under `proxy-launcher` (env-injection) no reconciler is needed because nothing is written to disk. It reads and writes `base_url` exclusively through the obs-spec-024 runtime adapters, which is why it needs no Hermes-version branching of its own.

---

## 5. Observability

- Every reconcile decision (converge / repoint / revert / chain / drift) is written to the existing `action_log` table (obs-spec-021), **including the trigger source** (SIGCHLD, tick, boot, launchd).
- Dashboard shows a "managed config" indicator: `Hermes config managed by ObserveCo → live proxy :51877` or `→ real upstream (tracking off)`.
- `revert` events raise an alert ("proxy unrecoverable — reverted to keep your agent working").
- Tier drift surfaces the same way obs-spec-024 §6 specifies: `cost_tracking fell exact → estimate (proxy down)`.
- Circuit-breaker state is visible in the dashboard: "Proxy relaunch paused — 5 min cooldown (3 failures in 60s)."

---

## 6. Data Continuity (GS-019 — mandatory)

> The generalized, fill-in-the-blanks version of this section is in **Appendix A** for reuse across the §12 parity specs.

**What happens to existing data?** No telemetry is migrated or deleted. Migration 22 adds one additive table (`proxy_config_snapshots`). The `_original_base_url` field is removed from the *user's* config on first managed write — but its value is captured into `original_base_url` in the snapshot store first, so no information is lost; it moves from a place ObserveCo doesn't control to one it does.

**Is backup required?** The migration is additive (no DROP/ALTER of existing tables), so no pre-migration `db.backup()` is triggered by this spec. The reconciler's own writes to the *user's config* are protected differently — by atomic rename (never a partial file) and by the `original_blob` snapshot (byte-exact revert), which is the config-file analogue of GS-019's backup-before-destructive rule.

**What does the user see if empty?** Fresh install with no managed providers → dashboard shows "config not managed" and the `proxy-config` tier is simply not active (the feature runs at a lower tier per obs-spec-024). No blank or error state. Post-revert (proxy unrecoverable) → "reverted to real upstream to keep your agent working" with a retry affordance.

**What's the recovery path?** If `proxy_config_snapshots` is lost: the reconciler can no longer prove what the original upstream was. Two branches:
- **Config currently points at our (live) proxy:** the reconciler enters **safe hold** — it will not disable tracking (since config already points at us and we're alive, the invariant holds). A recovery probe is attempted: read the provider's current config `base_url` and look for any non-proxy upstream address. If found, re-snapshot and continue. If not found (lost snapshot + config pointing at us + no trace of upstream), the reconciler cannot revert and logs a critical error requiring manual intervention: "Snapshot store lost — cannot prove original upstream for {provider}. Run `observeco proxy reset --provider {name}` to reconfigure."
- **Config currently points at the real upstream:** no action needed — the invariant is already CONVERGED_UPSTREAM. The reconciler re-snapshots on next config-rewrite opt-in.
- If a config write is interrupted: atomic rename guarantees the file is the old version, and the next tick retries.
- If the config file is missing/unreadable: the provider is skipped and surfaced in the discovery report; no crash.

**Honesty note:** There is one corner the reconciler cannot auto-heal: snapshot store lost while config points at our proxy AND no trace of upstream in config. In this case, the agent is left pointing at our proxy (which is alive), so it keeps working — but if the proxy then dies, there is no upstream to revert to. The reconciler logs a critical error and requires manual `observeco proxy reset`. The "agent never breaks" guarantee holds only while our proxy is alive; if both the snapshot and the proxy die before the next write, the guarantee degrades to "agent stops working (dead upstream) but manual fix is possible."

**Self-monitoring:** per pass record reconcile decisions, dead-port-window duration (time between proxy-death detection and heal), revert count, clobber-guard triggers, circuit-breaker state, and trigger-source distribution.

---

## 7. Tasks

| # | Task | Owner | Priority | Phase | Status |
|---|------|-------|----------|-------|--------|
| 25.1 | Migration 22: `proxy_config_snapshots` (additive, per GS-019) | Pragma | P0 | Recon-1 | ⬜ TODO |
| 25.2 | Snapshot store: capture original per provider, `original_blob`, `our_last_write_hash` | Main | P0 | Recon-1 | ⬜ TODO |
| 25.3 | `atomic_write_base_url` + `validate_no_truncated_keys` (write boundary) | Main | P0 | Recon-1 | ⬜ TODO |
| 25.4 | Reconcile loop + state classifier + idempotent actions + trigger-source logging | Hound | P0 | Recon-1 | ⬜ TODO |
| 25.5 | `proxy.ensure_alive` with relaunch budget + circuit-breaker → revert-on-exhaustion | Hound | P0 | Recon-1 | ⬜ TODO |
| 25.6 | Trigger layering: supervisor SIGCHLD, tick, boot reconcile, launchd KeepAlive | Pragma | P0 | Recon-1 | ⬜ TODO |
| 25.7 | Single-writer advisory lock + clobber guard (hash mismatch) | Main | P0 | Recon-2 | ⬜ TODO |
| 25.8 | Chain detection / FOREIGN_PROXY handling (uses `existing_proxies` from env snapshot) | Hound | P1 | Recon-2 | ⬜ TODO |
| 25.9 | Routing table from snapshot store; remove `_original_base_url` from config writer (§4.13 rework) | Hound | P0 | Recon-2 | ⬜ TODO |
| 25.10 | Observability: action_log entries (with trigger source), dashboard managed-config indicator, revert alert, circuit-breaker state | Pragma | P1 | Recon-2 | ⬜ TODO |
| 25.11 | Burn-in harness: induced SIGKILL/OOM/power-cut, 10k atomic-write kill test | Main | P0 | Recon-2 | ⬜ TODO |

---

## 8. Success criteria

- [ ] 7-day burn-in with induced proxy kills (SIGKILL/OOM/simulated power-cut): **zero** instances of the config left pointing at a dead port across a tick boundary. (25.11)
- [ ] Dead-port heal latency: p50 < 200 ms via supervisor signal; ≤ tick interval (default 10 s) if supervisor bypassed; < 30 s if the whole daemon died. (25.6)
- [ ] Atomic write: `kill -9` injected during 10,000 config writes → **zero** corrupt/partial config files (always old-or-new). (25.3, 25.11)
- [ ] Key-corruption guard: any write containing a `…`-truncated or regex-invalid key is rejected before disk. (25.3)
- [ ] Multi-provider routing reconstructed entirely from the snapshot store with **no** `_original_base_url` in the config. (25.9)
- [ ] Revert correctness: on disable/exhaustion, `base_url` restored to the snapshot's original; all other user-edited fields preserved byte-for-byte. (25.2, 25.4)
- [ ] Idempotency: a converged pass performs **zero** writes; two back-to-back passes produce no second write. (25.4)
- [ ] External-modification guard: a non-ObserveCo change to `base_url` is not clobbered; it is re-snapshotted and logged. (25.7)
- [ ] Two-instance safety: a second ObserveCo refuses to manage config and logs the conflict. (25.7)
- [ ] §4.3 promise holds: with tracking enabled and the proxy force-killed, the agent's next call succeeds (after heal) with no manual intervention. (25.5, 25.6)
- [ ] Circuit-breaker: 3 failures in 60s → 5 min cooldown; no flapping loop. (25.5)
- [ ] Trigger-source distribution logged: at least 90% of heals should come via SIGCHLD (fast path) in production. (25.4, 25.10)

---

## 9. Files added / modified

**Added**
- `src/observeco/proxy/reconciler.py` — loop, classifier, actions, circuit-breaker, trigger-source logging
- `src/observeco/proxy/snapshot_store.py` — owned snapshot CRUD
- `src/observeco/proxy/config_io.py` — `atomic_write_base_url`, key validator
- `tests/proxy/test_reconciler.py`, `tests/proxy/test_burnin.py`

**Modified**
- `src/observeco/proxy/service.py` — supervisor SIGCHLD → immediate reconcile; relaunch budget + circuit-breaker
- `src/observeco/proxy/server.py` — routing table from snapshot store (not `_original_base_url`); fail-open forward
- `src/observeco/db.py` — Migration 22
- `src/observeco/dashboard/server.py` + templates — managed-config indicator, revert alert, circuit-breaker state
- `cli` — boot reconcile on start; `observeco proxy revert` now delegates to the reconciler

---

## 10. Decision log / changelog

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-16 | Reconciler owns one invariant: config → live proxy XOR real upstream, never dead port | Makes the deprecated master plan's §4.3 promise true; eliminates the dead-port lockout class. |
| 2026-06-16 | Revert/routing state moves to ObserveCo-owned `proxy_config_snapshots`; `_original_base_url` retired | Closes silent-routing-table-emptying; revert no longer depends on a field other tools can drop. |
| 2026-06-16 | Relaunch budget exhausted → revert to upstream (fail-safe), not retry forever | A working agent with degraded observation beats a broken agent. |
| 2026-06-16 | No correctness depends on graceful shutdown; layered reconcile heals all exit modes | SIGKILL/OOM/power-loss are uncatchable; treat every exit as ungraceful. |
| 2026-06-16 | Config writes are atomic + key-validated; only `base_url` is touched | Prevents partial-file corruption and the truncated-key persistence bug. |
| 2026-06-16 | **v2.0: Circuit-breaker added.** 3 failures in 60s → 5 min cooldown before retrying. | Prevents flapping proxy from hammering relaunch and config-write in a tight loop when the proxy binary is fundamentally broken. |
| 2026-06-16 | **v2.0: Trigger-source logging added.** Every reconcile pass logs which trigger fired (SIGCHLD, tick, boot, launchd). | Critical for production observability — if the fast path (SIGCHLD) is never firing, you need to know so you can fix the supervisor wiring. |

---

## Appendix A — Reusable GS-019 §Data Continuity template

Paste into any parity spec (§12) and fill the placeholders. Every obs-spec must answer the four GS-019 questions plus the dashboard-state-matrix mapping.

```markdown
## N. Data Continuity (GS-019 — mandatory)

**What happens to existing data?**
<State whether any existing table is migrated/dropped. Name every schema change and
mark it additive or destructive. If a field/value moves location, state where it is
captured first so nothing is lost.>
- Migrations: <Migration NN — additive | destructive>
- Telemetry tables touched: <none | list>

**Is backup required?**
<If any operation is destructive (DROP/ALTER/recreate-table), `db.backup()` MUST run
before it per GS-019 §Principle 2. If purely additive, state that no backup is
triggered. For features that mutate user-owned files, state the file-level safety
mechanism (atomic rename + owned snapshot) that stands in for db backup.>

**What does the user see if empty?**
<Map each empty case to a concrete UI state — never a blank or stack trace:>
- Empty (fresh install): <what renders>
- Empty (post-upgrade): <re-probe / re-derive, not a blank>
- Empty (post-retention): <independent of feature state?>
- Error: <reason + remediation surfaced via tier tuple's description field>

**What's the recovery path?**
<For each way state can be lost or a write can fail, give the recovery:>
- Derived/cache data lost: <recompute — harmless?>
- Write interrupted: <atomic guarantee — old-or-new, retry next pass>
- Source file missing/unreadable: <skip + surface in discovery report, no crash>
- Worst case: <the safety invariant that still holds — e.g. agent never broken>

**Self-monitoring (GS-019 §Principle 5):**
<List the per-pass metrics: row counts / last insert / schema version / backup recency,
plus any feature-specific signal (tier drift, dead-port window, revert count).>
```

---

*Integrates with deprecated master plan v2.35 and obs-spec-024. On approval, add tasks 25.1–25.11 under a "Reconciler" track (Recon-1: snapshot store + atomic writes + loop + triggers + circuit-breaker; Recon-2: concurrency + chain + routing rework + burn-in). This is the highest-risk component in the capability-layer programme and should pass its 7-day burn-in before any persistent-proxy tier ships to users.*
