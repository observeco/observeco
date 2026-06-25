# obs-spec-024 — Capability Layer

**Spec ID:** obs-spec-024
**Title:** Capability layer — design for capability, not environments
**Document version:** 4.1
**Status:** ⬜ DRAFT — for review
**Owner:** Hound (arch) → Pragma (infra) → Main (impl)
**Created:** 2026-06-16
**Master plan ref:** v2.35 (deprecated) — this spec supersedes the per-environment branching in §5.1, reframes Phase 4/5 token approaches as tiers of one feature, and becomes the substrate for the §12 agenttrace-parity work.
**Standards:** GS-019 (Data & Observability Continuity) — §6 below is mandatory.
**Target stack:** Hermes / OpenClaw on macOS (Apple Silicon + Intel). Linux/Windows are explicitly out of scope for this spec; the design makes them additive later (new probes, no feature changes).

---

## 1. Trigger & Context

The current architecture branches on **environment**: §5.1 is an OS matrix, §4.7 hardcodes `if Hermes: rewrite config.yaml … else: print export …`, and Phase 4 ships Proxy / SDK / OTel as three separate implementations with no runtime selector. Every supported (runtime × version × OS × permission) combination is its own code path, so each new variation is a break (the Hermes `config.json` path move on upgrade was one instance) and each feature re-implements its own discovery and fallback.

This spec introduces a single **capability layer**: one probe touches the messy environment and produces a flat **environment snapshot**; every feature reads the snapshot and picks the best tier it can support, never reaching down to configs, processes, or ports itself. A new environment becomes "write new probes," not "touch every feature." Within our one target stack this is still load-bearing, because "Hermes/OpenClaw on macOS" is not one environment — it spans Hermes v0.14 vs v0.16, Hermes vs OpenClaw, Full-Disk-Access granted vs not, launchd-managed vs bare process, iCloud-synced home vs not, and Apple Silicon vs Intel.

**Non-goals:** this spec does not add new telemetry schemas, does not change `token_logs`, and does not implement Linux/Windows probes. It changes *how features select an implementation*, not *what they record*.

---

## 2. Design principles & invariants

1. **One env-aware layer.** Only the probe imports OS/runtime specifics. Feature modules must not import `os.path` resolution, `lsof`, `psutil`, `yaml` config loaders, or socket/port logic. Enforced by an import-boundary test (§8).
2. **The probe is read-only.** Probing never mutates the environment — no config writes, no proxy starts, no file creation in the user's tree. Mutation is a *feature action*, gated by the snapshot. (A probe that writes is a GS-019 and a "first, do no harm" violation.)
3. **Process-first discovery.** Ground truth beats prediction: resolve the live agent's open config via `lsof`/`psutil` before consulting candidate paths. Reality is immune to version path moves.
4. **Fail loud, never silent.** A capability that can't be detected is surfaced in the discovery report with a reason and remediation hint. No silent empty routing tables, no silent fallback to a wrong default.
5. **Tiers, not booleans.** Every capability-dependent feature degrades gracefully through an ordered ladder and reports which rung it's on. The bottom rung must always be reachable (it depends only on being able to read the config, which is universal on this stack).
6. **Snapshots are cache, not source of truth.** The environment snapshot is cheap to recompute; persisted snapshots exist only for the discovery report and drift detection. Losing them is harmless.
7. **Mutation owns its undo.** Any feature that mutates the environment (e.g. config-rewrite for proxy injection) must store an ObserveCo-owned snapshot of the original and run a reconciler that maintains the invariant "config points at a live proxy XOR the real upstream — never a dead proxy." Revert state never lives in the user's file.

---

## 3. The probe — one function, one snapshot

### 3.1 The environment snapshot

A single flat dataclass. No Protocol types, no dependency graph, no TTL cache. Every probe writes its findings into this struct; every feature reads from it.

```python
# src/observeco/capability/env_snapshot.py
from __future__ import annotations
from dataclasses import dataclass, field
import time

@dataclass
class EnvSnapshot:

    # User intent
    proxy_mode: str | None = None           # None | "launcher" | "config-rewrite" — user's opt-in choice; None means "not opted in"
    
    # Runtime
    runtime: str | None = None              # "hermes" | "openclaw"
    runtime_version: str | None = None      # "0.16" | "0.14" | "unknown"
    agent_pids: dict[str, int] = field(default_factory=dict)

    # Config
    config_path: str | None = None
    config_writable: bool = False
    config_parsed: dict | None = None       # raw parsed YAML, for LLM enrichment
    config_error: str | None = None         # reason if config unreadable (Trap 3 guard)

    # Ports & proxies
    chosen_port: int | None = None          # ephemeral port we can bind
    existing_proxies: dict[str, int] = field(default_factory=dict)  # e.g. {"skillclaw": 30000}

    # Permissions
    keychain_available: bool = False
    full_disk_access: bool = False
    can_install_launchagent: bool = False
    store_location_safe: bool = False

    # Session store
    framework_emits_usage: bool = False
    session_store_path: str | None = None

    # Metadata
    host_fingerprint: str = ""
    probed_at: float = 0.0
    probe_errors: dict[str, str] = field(default_factory=dict)  # failed probe → reason

    # LLM-enriched (Phase 2+)
    anomalies: list[str] = field(default_factory=list)
    config_summary: str | None = None       # LLM-generated plain-English summary
```

**Why flat?** Two runtimes on one OS don't need a formal capability registry. A flat struct is simpler to read, simpler to test, and simpler to extend. When the third runtime arrives, promote to a formal registry — until then, this is enough.

### 3.2 The named probes

| Probe | What it detects | How | Writes to `EnvSnapshot` |
|-------|----------------|-----|------------------------|
| `_find_process()` | Running agent + its open config file | `psutil` cmdline scan for `hermes`/`openclaw`; `proc.open_files()` for ground-truth config path | `runtime`, `agent_pids`, `config_path` |
| `_read_config()` | Config file parseable + writable | Read YAML at `config_path`; check `os.access(path, W_OK)` | `config_parsed`, `config_writable` |
| `_fingerprint()` | Runtime version from config schema | Inspect config keys: `profiles` → v0.16, `providers` → v0.14, else `unknown` | `runtime_version` |
| `_find_ports()` | Available port + existing proxies | `socket.bind(("127.0.0.1", 0))` for ephemeral; `psutil.net_connections` for known listeners | `chosen_port`, `existing_proxies` |
| `_check_keychain()` | OS keychain usable | `keyring` round-trip (set/get/delete a probe key) | `keychain_available` |
| `_check_fda()` | Full Disk Access granted | Attempt read of a known TCC-protected path; catch `PermissionError` | `full_disk_access` |
| `_check_launchagent()` | Can install launchd agent | `~/Library/LaunchAgents` writable + `launchctl` on PATH | `can_install_launchagent` |
| `_check_store_location()` | SQLite dir not under sync root | Resolve store dir; assert not under iCloud/Dropbox/Drive roots | `store_location_safe` |
| `_find_session_store()` | Can read runtime's session store | Locate `~/.hermes/sessions` or equivalent; check readable | `session_store_path`, `framework_emits_usage` |

### 3.3 Representative probe implementations

```python
# src/observeco/capability/probe.py
import os, time, socket, psutil, yaml
from observeco.capability.env_snapshot import EnvSnapshot

HERMES_CANDIDATES = (
    "~/.hermes/config.yaml",
    "~/.hermes/profiles/main/config.yaml",
)
KNOWN_PORTS = {9200: "observeco", 30000: "skillclaw", 11434: "ollama", 8645: "hermes_proxy"}

def probe_environment() -> EnvSnapshot:
    snap = EnvSnapshot(probed_at=time.time())
    _find_process(snap)
    _read_config(snap)
    _fingerprint(snap)
    _find_ports(snap)
    _check_keychain(snap)
    _check_fda(snap)
    _check_launchagent(snap)
    _check_store_location(snap)
    _find_session_store(snap)
    return snap

def _find_process(snap: EnvSnapshot) -> None:
    # ponytail: psutil.process_iter can hang on zombie processes.
    # Upgrade path: use timeout=3 and catch psutil.TimeoutExpired.
    for p in psutil.process_iter(["name", "cmdline"]):
        blob = " ".join(p.info.get("cmdline") or [p.info.get("name") or ""]).lower()
        for name in ("hermes", "openclaw"):
            if name in blob:
                snap.agent_pids[name] = p.pid
                try:
                    for f in p.open_files():
                        if f.path.endswith((".yaml", ".yml", "config.json")):
                            snap.config_path = f.path  # ground truth
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
    if not snap.config_path:
        for cand in HERMES_CANDIDATES:
            p = os.path.realpath(os.path.expanduser(cand))
            if os.path.exists(p):
                snap.config_path = p
                break

def _read_config(snap: EnvSnapshot) -> None:
    if not snap.config_path:
        return
    try:
        with open(snap.config_path) as f:
            snap.config_parsed = yaml.safe_load(f) or {}
        snap.config_writable = os.access(snap.config_path, os.W_OK)
    except PermissionError:
        snap.config_error = "Permission denied — grant ObserveCo read access to the config directory"
    except yaml.YAMLError as e:
        snap.config_error = f"Config file corrupt: {e}"
    except OSError as e:
        snap.config_error = f"Config unreadable: {e}"

def _fingerprint(snap: EnvSnapshot) -> None:
    doc = snap.config_parsed or {}
    if "profiles" in doc:          snap.runtime_version = "0.16"
    elif "providers" in doc:       snap.runtime_version = "0.14"
    else:                          snap.runtime_version = "unknown"
    snap.runtime = "hermes" if "hermes" in snap.agent_pids else \
                   "openclaw" if "openclaw" in snap.agent_pids else None

def _find_ports(snap: EnvSnapshot) -> None:
    for c in psutil.net_connections(kind="inet"):
        if c.status == "LISTEN" and c.laddr and c.laddr.port in KNOWN_PORTS:
            snap.existing_proxies[KNOWN_PORTS[c.laddr.port]] = c.laddr.port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    snap.chosen_port = s.getsockname()[1]
    s.close()

def _check_keychain(snap: EnvSnapshot) -> None:
    import keyring
    from keyring.backends import fail
    kr = keyring.get_keyring()
    if isinstance(kr, fail.Keyring):
        return
    try:
        keyring.set_password("observeco-probe", "x", "1")
        snap.keychain_available = keyring.get_password("observeco-probe", "x") == "1"
        keyring.delete_password("observeco-probe", "x")
    except Exception:
        pass

def _check_fda(snap: EnvSnapshot) -> None:
    # ponytail: FDA check uses known TCC-protected paths. These are macOS-version-specific.
    # Upgrade path: use `tccutil` or `mdls` on a known path for a more reliable check.
    for path in ("~/Library/Safari/Bookmarks.plist", "~/.hermes/sessions", "~/Library/Mail/V10/MailData"):
        try:
            with open(os.path.expanduser(path)): pass
            snap.full_disk_access = True; return
        except PermissionError:
            continue

def _check_launchagent(snap: EnvSnapshot) -> None:
    la = os.path.expanduser("~/Library/LaunchAgents")
    snap.can_install_launchagent = os.access(la, os.W_OK) and \
        any(os.access(f, os.X_OK) for f in ["/bin/launchctl", "/usr/bin/launchctl"])

def _check_store_location(snap: EnvSnapshot) -> None:
    store = os.path.expanduser("~/.observeco")
    sync_roots = ["~/Library/Mobile Documents", "~/Library/CloudStorage",
                  "~/Dropbox", "~/Library/Application Support/Google/Drive"]
    snap.store_location_safe = not any(
        os.path.realpath(store).startswith(os.path.realpath(os.path.expanduser(r)))
        for r in sync_roots
    )

def _find_session_store(snap: EnvSnapshot) -> None:
    candidates = ["~/.hermes/sessions", "~/.openclaw/sessions"]
    for c in candidates:
        p = os.path.expanduser(c)
        if os.path.isdir(p) and os.access(p, os.R_OK):
            snap.session_store_path = p
            snap.framework_emits_usage = True
            break
```

### 3.4 Probe orchestration

No dependency graph, no topo-sort, no TTL cache. The probes run in a fixed order (process → config → fingerprint → ports → permissions → store). Each probe writes directly to the shared `EnvSnapshot` struct. A full cold pass targets <500 ms on the reference Mac.

**Failure cascade guard:** Each probe call is wrapped in a try/except that logs the error and continues to the next probe. A failed probe leaves its fields at default (None/False) and sets a reason string on the snapshot. No single probe failure aborts the entire pass — the snapshot is always as complete as possible, and the discovery report surfaces which probes failed and why.

```python
def probe_environment() -> EnvSnapshot:
    snap = EnvSnapshot(probed_at=time.time())
    for name, fn in PROBES:
        try:
            fn(snap)
        except Exception as e:
            snap.probe_errors[name] = str(e)
    return snap
```

Add `probe_errors: dict[str, str] = field(default_factory=dict)` to `EnvSnapshot`.

**Refresh triggers:** (1) startup, (2) explicit `observeco doctor`, (3) proxy lifecycle events (start/stop/crash), (4) config-file `watch` event, (5) periodic timer (default 60 s, configurable). The periodic timer ensures stale data never persists beyond one minute even if all other triggers fail. A full cold pass targets <500 ms on the reference Mac, so the timer is cheap enough to run every 60 s without noticeable overhead.

**Discovery report (fail-loud):** Every pass emits a structured report — per probe: what was found (or why not), and per feature: active tier + degraded reason. This is the default first-run dashboard view and the cold-start "is it broken or empty?" answer.

```
$ observeco doctor
Runtime:  hermes 0.16  (pid 48213, config ~/.hermes/profiles/main/config.yaml via process_open_files)
Probes:
  ✓ process         pids={hermes:48213}
  ✓ config          writable=true
  ✓ ports           chosen=51877  existing={skillclaw:30000, ollama:11434}
  ✓ keychain        backend=macOS
  ✗ fda             grant FDA to read protected session logs
Features:
  cost_tracking      → tier 1 (proxy-launcher)   exact, real-time
  tool_call_tracking → tier 3 (session-store)    near-exact, delayed → enable proxy for tier 1
```

### 3.5 Runtime adapters (simplified)

Per-runtime, per-version specifics live in adapters, not in probes or features. A new Hermes version = register a new adapter. No probe change, no feature change.

```python
# src/observeco/capability/adapters/hermes.py
HERMES_ADAPTERS = {
    "0.14": HermesSchemaV14,   # parser + base_url accessor for this schema
    "0.16": HermesSchemaV16,
}
```

**Phase 2 upgrade:** Replace the hardcoded adapter table with an LLM-based config extractor. The LLM reads the raw config and extracts runtime version, provider base_urls, truncated keys, and anomalies — no adapter table to maintain. See §12.

---

## 4. Feature selection — per-feature functions, no resolver

### 4.1 The pattern

Each feature gets one function. It reads the `EnvSnapshot` and returns the best tier it can support. No `Feature`/`Tier`/`ActiveFeature` types, no formal resolver, no `build()` callbacks. Just a function that returns a tuple.

```python
# src/observeco/features/cost_tracking.py
from observeco.capability.env_snapshot import EnvSnapshot

def select_cost_tracking_tier(snap: EnvSnapshot) -> tuple[str, str, str]:
    """Returns (tier_name, quality, description)"""
    if snap.chosen_port:
        if snap.proxy_mode == "launcher":
            # Launcher mode — default, crash-safe, no config changes
            return ("proxy-launcher", "exact", "real-time via env injection")
        if snap.proxy_mode == "config-rewrite" and snap.config_parsed and snap.config_writable:
            # Config-rewrite — opt-in, requires reconciler
            return ("proxy-config", "exact", "real-time via config rewrite")
        # Proxy-capable but no explicit opt-in yet; offer launcher as default
        return ("proxy-launcher", "exact", "real-time via env injection")
    if snap.session_store_path:
        return ("session-store", "near-exact", "delayed from session logs")
    return ("estimate", "approximate", "context sizing × pricing")
```

```python
# src/observeco/features/tool_call_tracking.py
def select_tool_call_tier(snap: EnvSnapshot) -> tuple[str, str, str]:
    if snap.config_parsed and snap.chosen_port:
        return ("proxy-intercept", "exact", "parse tool_calls from request/response")
    if snap.session_store_path:
        return ("session-store", "near-exact", "delayed from session logs")
    return ("disabled", "none", "enable proxy to capture tool-call data")
```

**Why functions instead of a resolver?** Two runtimes on one OS don't need a formal resolution engine. Functions are simpler to read, simpler to test, and simpler to extend. When the third runtime arrives and you have 10+ features with complex dependency chains, promote to a formal resolver — until then, this is enough.

### 4.2 Dashboard contract

The dashboard reads the tier tuple: it renders `tier_name` + `quality` as a badge ("exact · real-time" / "approximate"), and when the tier is not the best possible, it shows a one-click remediation ("Enable proxy for exact cost"). Features never tell the dashboard *how* they got their data — only which rung they're on.

**Dashboard state matrix (GS-019):**

| State | Cost tracking badge | User sees |
|-------|-------------------|-----------|
| Fresh install, no agents | "No agents detected" + guided setup | "Run `observeco run -- hermes …` to start" |
| Fresh install, agents running | `estimate · approximate` | "Cost tracking: approximate. Enable proxy for exact cost." |
| Proxy active (launcher or config) | `exact · real-time` | "Cost tracking: exact · real-time via proxy" |
| Proxy died, launcher mode | `estimate · approximate` (auto-drop) | "Cost tracking: approximate (proxy down)" |
| Proxy died, config-rewrite mode | `estimate · approximate` (revert) | "Proxy unrecoverable — reverted to keep agent working" |
| Session store only | `near-exact · delayed` | "Cost tracking: near-exact (delayed from session logs)" |
| Error (config unreadable) | `unknown` + reason | "Cost tracking unavailable — config unreadable: {reason}" |

This is also the GS-019 dashboard-state surface (populated / empty-fresh / empty-post-upgrade / error all flow through the tier tuple).

---

## 5. Worked example — Cost tracking

### 5.1 Current hardcoded form (today, documented in deprecated master plan v2.35 §4.6-4.7, §4.13)

Per the deprecated master plan, install rewrites Hermes `config.yaml` so `base_url → http://localhost:9200/v1`, stashes the original in a `_original_base_url` field *inside the user's config*, and the routing table is rebuilt by reading `_original_base_url` back out of that file. Two known failures fall out of this: (a) the routing table silently empties if a Hermes upgrade rewrites the config or another tool (Skillclaw) drops the field; (b) the promise "if proxy is down, agents still work" is contradicted by the mechanism — config pointing at a dead `:9200` means every call is refused. It is also three separate dashboard concepts (Actual / Sizing / Estimated) that are really one question — "what is this costing?" — answered at different fidelities.

### 5.2 As capabilities — one feature, four tiers

| Tier | Name | Quality | How | Default? |
|------|------|---------|-----|----------|
| 1 | `proxy-launcher` | exact, real-time | Agent launched via `observeco run --`; `*_BASE_URL` injected into child env only. Crash-safe by construction — nothing on disk to revert. | **Default** |
| 2 | `proxy-config` | exact, real-time | Persistent base_url rewrite — **but** original stored in ObserveCo's own snapshot (never `_original_base_url`), and a reconciler maintains "config → live proxy XOR real upstream, never dead port." Fail-open proxy. | Opt-in |
| 3 | `session-store` | near-exact, delayed | Read `usage` the runtime already records; no interception. | Fallback |
| 4 | `estimate` | approximate, always | Context sizing × pricing — the existing "Estimated Cost" overlay, now the guaranteed bottom rung. | Last resort |

The probe picks the highest satisfied rung; the dashboard's old "Actual / Sizing / Estimated" split collapses into one feature reporting its current fidelity. `source='proxy'|'otel'|'watch'` tagging in `token_logs` is unchanged — it now records *which tier produced the row*, which is exactly what the dashboard already keys on.

### 5.3 What the user sees

Fresh install, agent running, no proxy yet → `cost_tracking → tier 4 (estimate)` with "Run `observeco run -- hermes …` for exact cost." User runs `observeco run -- hermes …` → next probe pass resolves `tier 1`, dashboard badge flips to "exact · real-time." Hermes upgrades and moves its config → process-first discovery finds the new path with zero code change; tier is unaffected. Proxy is SIGKILLed → launcher tier means the agent's config was never touched, so the agent keeps working immediately (§4.3 promise now actually holds) and the feature drops to tier 4 until the proxy is back.

---

## 5b. Second example (declaration only) — Tool-call tracking (§12.3 P0 gap)

The §12 agenttrace-parity gap has no current implementation; in the capability model it's a function, not a new subsystem:

```python
def select_tool_call_tier(snap: EnvSnapshot) -> tuple[str, str, str]:
    if snap.config_parsed and snap.chosen_port:
        return ("proxy-intercept", "exact", "parse tool_calls from request/response")
    if snap.session_store_path:
        return ("session-store", "near-exact", "delayed from session logs")
    return ("disabled", "none", "enable proxy to capture tool-call data")
```

Same ladder shape, same dashboard contract — which is the point: parity features become functions against the snapshot rather than bespoke integrations.

---

## 6. Data Continuity (GS-019 — mandatory)

**What happens to existing data?** Nothing is migrated or deleted. `token_logs` and all existing tables are untouched; the capability layer changes *implementation selection*, not recorded data. The one schema addition is a new, additive, nullable table `capability_snapshots` (Migration 21).

**Is backup required?** No destructive operation occurs, so no pre-migration backup is triggered for this spec's migration. (`db.backup()` still runs per GS-019 §Principle 2 if any later change becomes destructive.)

**What does the user see if empty?** The discovery report is explicitly designed for the empty/fresh case: it states what was probed, what was found, and per-feature which tier is active or why disabled. The GS-019 dashboard-state matrix maps onto the tier tuple: populated (tier 1-3), empty-fresh (tier 4 on first run), empty-post-upgrade (re-probe on refresh restores tiers — never a silent blank), empty-post-retention (telemetry tables independent of capability state), error (tier "disabled" + reason).

**What's the recovery path?** Environment snapshots are cache: if lost or corrupt, the next probe pass rebuilds it (cheap, harmless). If a probe itself fails, the snapshot field stays `None` and features degrade — the system stays up in a read-only/degraded state rather than crashing. The `proxy-config` tier's reconciler guarantees the user's agent config is never left pointing at a dead proxy, independent of any snapshot state.

**Self-monitoring (GS-019 §Principle 5):** record per pass — probe duration, per-feature active tier, and tier *drift* (a feature dropping a rung between passes surfaces as an alert, e.g. "cost_tracking fell from exact to estimate — proxy down?").

---

## 7. Tasks

| # | Task | Owner | Priority | Phase | Status |
|---|------|-------|----------|-------|--------|
| 24.1 | `EnvSnapshot` dataclass + `probe_environment()` function (`src/observeco/capability/`) | Main | P0 | Cap-1 | ⬜ TODO |
| 24.2 | Probes: `_find_process`, `_read_config`, `_fingerprint`, `_find_ports`, `_check_keychain` | Main | P0 | Cap-1 | ⬜ TODO |
| 24.3 | Probes: `_check_fda`, `_check_launchagent`, `_check_store_location`, `_find_session_store` | Main | P1 | Cap-1 | ⬜ TODO |
| 24.4 | Per-feature `select_tier()` functions: `cost_tracking`, `tool_call_tracking` | Main | P0 | Cap-1 | ⬜ TODO |
| 24.5 | Discovery report + `observeco doctor` capability section | Pragma | P0 | Cap-1 | ⬜ TODO |
| 24.6 | `observeco run --` launcher tier (env injection, crash-safe) | Hound | P0 | Cap-1 | ⬜ TODO |
| 24.7 | Dashboard: tier badge + remediation; collapse Actual/Sizing/Estimated into one feature with fidelity | Pragma | P1 | Cap-2 | ⬜ TODO |
| 24.8 | Migration 21: additive `capability_snapshots` table (nullable) | Pragma | P1 | Cap-2 | ⬜ TODO |
| 24.9 | Import-boundary test: feature modules may not import os/lsof/psutil/yaml/socket | Main | P0 | Cap-1 | ⬜ TODO |
| 24.10 | Fixtures + tests: Hermes v0.14 and v0.16 config, tier resolution at each rung | Main | P0 | Cap-2 | ⬜ TODO |
| 24.11 | LLM enrichment layer: config fingerprinting, anomaly detection, `observeco doctor` NL | Main | P1 | Cap-3 | ⬜ TODO |
| 24.12 | Signal store: (diagnosis → action → outcome) for self-learning loop | Hound | P1 | Cap-3 | ⬜ TODO |
| 24.13 | Auto-configuration flow: LLM proposes, code acts, user confirms | Hound | P2 | Cap-4 | ⬜ TODO |

---

## 8. Success criteria

- [ ] Cold probe pass <500 ms on the reference Mac (M4 Pro). (24.1)
- [ ] Zero environment mutation during any probe pass — asserted by a test that snapshots the user tree before/after. (24.9)
- [ ] Hermes v0.14 → v0.16 config-path change resolves with **no feature/probe code change** — both fixtures pass via adapter fingerprint alone. (24.10)
- [ ] `cost_tracking` resolves to tier 1 under `observeco run --`, tier 2 under config-rewrite, tier 3 when only the session store is readable, tier 4 otherwise — with no `if runtime` in the feature module. (24.4, 24.10)
- [ ] Feature modules import none of: `os.path` resolution, `lsof`, `psutil`, a YAML config loader, `socket`/port logic — enforced in CI. (24.9)
- [ ] Discovery report renders on fresh install showing per-probe state and per-feature active tier + remediation. (24.5)
- [ ] Adding a hypothetical new capability requires no edit to any existing feature module (review gate). (24.4)
- [ ] Tier drift (a feature dropping a rung) is logged and surfaced as an alert. (24.5, GS-019 §6)
- [ ] LLM enrichment layer handles unknown config schemas without code changes (Phase 2). (24.11)
- [ ] LLM config extraction accuracy ≥ 95% (verified against known v0.14/v0.16 fixtures). (24.11)
- [ ] LLM anomaly detection false positive rate < 5% (Phase 2). (24.11)
- [ ] `observeco doctor` NL output rated "clear and actionable" by user in ≥ 90% of cases (Phase 2). (24.11)
- [ ] Signal store records at least 100 (diagnosis → action → outcome) entries before Phase 4 ships. (24.12)
- [ ] Auto-configuration approval rate > 80% before Phase 4 is considered stable. (24.13)

---

## 9. Files added / modified

**Added**
- `src/observeco/capability/env_snapshot.py` — `EnvSnapshot` dataclass
- `src/observeco/capability/probe.py` — `probe_environment()` + all probe functions
- `src/observeco/features/cost_tracking.py`, `tool_call_tracking.py` — `select_tier()` functions
- `src/observeco/llm/enrichment.py` — LLM enrichment layer (Phase 2)
- `src/observeco/llm/signal_store.py` — signal store for self-learning loop (Phase 3)
- `tests/capability/` — fixtures (v0.14/v0.16), tier resolution tests, import-boundary test

**Modified**
- `src/observeco/proxy/service.py` — port from probe (`chosen_port`), not hardcoded 9200; chain awareness
- `src/observeco/proxy/server.py` — fail-open forward; routing table from ObserveCo snapshot, not `_original_base_url`
- `src/observeco/tracking/sdk/provider_registry.py` — `_is_local()` consulted by probe, not by features directly
- `src/observeco/db.py` — Migration 21 (`capability_snapshots`)
- `src/observeco/dashboard/server.py` + templates — tier badges, remediation, collapsed cost view
- `cli` — `observeco doctor` capability section; `observeco run --` launcher

---

## 10. Decision log / changelog

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-16 | Capability layer introduced as the architectural spine (obs-spec-024 v3.0) | Replace per-environment branching (§5.1) with one probe + capability map; features declare needs + tier ladder. Makes the one target stack robust across version/permission variation and makes later OS expansion additive. |
| 2026-06-16 | Probe is strictly read-only; mutation is a capability-gated feature action | "First, do no harm" + GS-019: a monitoring tool must not mutate while observing. |
| 2026-06-16 | `_original_base_url` side-channel retired; revert state moves to ObserveCo-owned snapshot + reconciler | Closes the silent-empty-routing-table and dead-port-lockout failures; makes §4.3's "agent still works if proxy down" actually true. |
| 2026-06-16 | "Actual / Sizing / Estimated" recast as tiers 1–4 of one `cost_tracking` feature | Same data, one question at four fidelities; dashboard shows fidelity instead of three disconnected concepts. |
| 2026-06-16 | **v4.0: Flattened formalism.** Replaced `Capability` Protocol, topo-sort orchestrator, TTL cache, and typed resolver with a flat `EnvSnapshot` dataclass + per-feature `select_tier()` functions. | Two runtimes on one OS don't need a formal capability registry. Functions are simpler to read, test, and extend. Promote to full registry when third runtime arrives. |
| 2026-06-16 | **v4.0: Launcher tier elevated to default.** `observeco run --` is the default path for new users. Config-rewrite becomes opt-in. | Crash-safe by construction (nothing on disk). Eliminates the reconciler dependency for most users. |
| 2026-06-16 | **v4.0: Self-learning loop vision added.** 4-phase roadmap: deterministic foundation → LLM enrichment → feedback loop → auto-configuration. | Positions ObserveCo as a system that configures itself for each user's unique setup, getting smarter over time. |

---

## 11. Self-Learning Loop Vision

ObserveCo is positioned as a **modern self-learning loop** that configures itself bespokely to each user's unique setup. The system looks at the user's machine, learns from usage, adapts automatically, and gets smarter over time. This section describes the phased roadmap to that vision.

### Phase 1 — Deterministic foundation (this spec)

The probe layer + reconciler + launcher tier. This is the **safe skeleton**. The LLM has nothing to learn from and no safe way to act without this.

**What it ships:**
- Probe discovers the environment (agents, versions, ports, permissions)
- Reconciler guarantees config never points at a dead proxy
- Launcher tier is crash-safe by default
- `observeco doctor` shows a structured report

**No LLM yet.** Just reliable, deterministic discovery and safety.

### Phase 2 — LLM enrichment (adds the "learning" start)

The probe data feeds into the LLM for things code can't anticipate:

- **Config fingerprinting** — one generic LLM prompt replaces a table of hardcoded version adapters. v0.17 ships? LLM handles it. No code change.
- **Anomaly detection** — "This config has a `base_url` pointing at port 30000 but the process there is Skillclaw, not ObserveCo." Rules would miss this. LLM spots it.
- **Natural language diagnosis** — `observeco doctor` speaks English, not structured data.

**This is where "learning" starts.** The LLM spots patterns the code doesn't know about. But it only reads and explains — never acts.

### Phase 3 — Feedback loop (the actual self-learning)

A lightweight signal store records every (diagnosis → action → outcome) interaction:

```python
signal = {
    "diagnosis": "Config points at dead proxy",
    "recommendation": "Revert to upstream",
    "user_action": "accepted",  # or "rejected" or "ignored"
    "outcome": "agent working, no telemetry",
    "environment_snapshot": {...}
}
```

Over time, the system learns:
- "When the proxy crashes and the user has Skillclaw, they prefer chaining over reverting"
- "When the user has FDA disabled, they'd rather see a one-click grant link than a manual instruction"
- "When the config has `_original_base_url`, it's from an old ObserveCo version — clean it up silently"

**No ML training. No model fine-tuning.** Just a database of (diagnosis → action → outcome) that the LLM reads as context on the next interaction. The LLM gets better because it has memory of what worked before.

### Phase 4 — Auto-configuration (the vision realized)

The system proposes config changes based on what it's learned. User approves or rejects. Over time, approval rate goes up.

```
$ observeco setup
→ "I see Hermes v0.16 and Skillclaw on port 30000.
   Last time a user with this setup chose to chain proxies.
   Want me to do the same? [Y/n]"
```

**The LLM proposes. Code decides. User confirms for anything irreversible.**

### The constraint that makes this safe

The LLM never acts on the environment directly:

| Can do | Cannot do |
|--------|-----------|
| Read the probe snapshot | Write a config file |
| Generate a recommendation | Run a command |
| Explain what it found | Bind a port |
| Remember what worked before | Make a safety decision |

The code layer is the **airlock**. The LLM can suggest anything. The code only executes what's safe and verified. This is non-negotiable — without it, you're building a system that will eventually hallucinate itself into breaking a user's agent.

---

## 12. LLM Integration

ObserveCo already has an LLM feature. Here's how it slots into the capability layer across the four phases.

### 12.1 Config fingerprinting (Phase 2)

**Without LLM (Phase 1):** Hardcoded adapter table mapping version strings to parsers. Every new version needs a new adapter.

**With LLM (Phase 2):** One generic prompt. Feed the raw config to the LLM with a structured extraction schema:

```python
def llm_extract_config(doc: dict) -> dict:
    prompt = f"""Extract from this Hermes/OpenClaw config:
- runtime version
- each provider: name, base_url, api_key (masked), model
- any truncated/redacted values (containing '...')
- any non-standard fields (_original_base_url, custom fields)
Config: {json.dumps(doc, indent=2)}
Return as JSON matching this schema: {ConfigSchema.model_json_schema()}"""
    return llm.extract(prompt, schema=ConfigSnapshot)
```

**v0.17 ships with a new schema?** The LLM handles it. No code change. No adapter to write. The LLM understands YAML structure, not hardcoded path patterns.

### 12.2 Probe result enrichment (Phase 2)

After the probe runs, pass the raw snapshot through the LLM for pattern detection:

```python
def llm_enrich(snap: EnvSnapshot) -> EnvSnapshot:
    anomalies = llm.extract(
        f"Given this environment snapshot, list any anomalies, conflicts, or unusual patterns: {snap.model_dump_json()}",
        schema=AnomalyList
    )
    snap.anomalies = anomalies
    return snap
```

Catches things rules miss: "This config has a `base_url` pointing at localhost:30000 but the process on that port is Skillclaw, not ObserveCo — possible chain scenario." Or: "The API key format doesn't match the provider — likely a copy-paste error."

### 12.3 `observeco doctor` — natural language diagnosis (Phase 2)

The structured probe data feeds into a natural language summary:

```
$ observeco doctor
→ "Your agent is Hermes v0.16, config at ~/.hermes/profiles/main/config.yaml.
   Proxy is down — I've reverted to direct upstream so your agent keeps working.
   Cost tracking is now in estimate mode (approximate).
   Also: Skillclaw is running on port 30000. Want me to chain them so
   both get telemetry? Just say 'yes'."
```

One prompt covers a hundred edge cases that would each need their own `if` branch.

### 12.4 Remediation generation (Phase 2)

Instead of hardcoded error messages, generate the remediation dynamically based on the exact failure:

```python
def llm_remediation(snap: EnvSnapshot, missing: str) -> str:
    return llm.generate(
        f"User's {missing} capability failed. Environment: {snap.model_dump_json()}.
         Give a one-sentence actionable fix."
    )
```

Handles edge cases you didn't anticipate. "Your config at ~/.hermes/config.yaml is locked. Run: chmod 644 ~/.hermes/config.yaml" vs "Grant Full Disk Access in System Settings > Privacy" — the LLM picks the right one based on the actual error.

### 12.5 First-run setup wizard (Phase 2)

Interactive onboarding:

```
$ observeco setup
→ "I see you have Hermes v0.16 and Skillclaw running.
   I can set up cost tracking in launcher mode (no config changes, crash-safe).
   Or persistent mode with auto-recovery if the proxy crashes.
   Which do you prefer?"
```

The LLM reads the probe results, explains the options in plain language, and generates the config. No docs-reading required.

### 12.6 Signal store for learning (Phase 3)

```python
# src/observeco/llm/signal_store.py
@dataclass
class Signal:
    diagnosis: str
    recommendation: str
    user_action: str          # "accepted" | "rejected" | "ignored"
    outcome: str              # what happened after
    environment: EnvSnapshot
    timestamp: float
```

Fed into the LLM as context on the next interaction: "Last time a user with this setup chose X. Want to do the same?" The system gets better because it has memory of what worked before.

### 12.7 Auto-configuration (Phase 4)

The LLM proposes config changes. Code validates and executes. User confirms for anything irreversible.

```
$ observeco setup
→ "I see Hermes v0.16 and Skillclaw on port 30000.
   Last time a user with this setup chose to chain proxies.
   Want me to do the same? [Y/n]"
```

### 12.8 The pattern in one sentence

**LLM reads and explains. Code acts and decides.** The LLM makes the system conversational and adaptive to the unknown. The code makes it safe. They don't cross streams.

---

*Integrates with deprecated master plan v2.35. On approval, add tasks 24.1–24.13 to the Kanban board under a "Capability Layer" track (Cap-1: probe + launcher + features; Cap-2: dashboard + tests; Cap-3: LLM enrichment + signal store; Cap-4: auto-configuration). This spec is the substrate the §12 parity work should be built on.*
