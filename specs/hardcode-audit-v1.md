# ObserveCo — Generality Audit v1

**Date:** 2026-06-19
**Analyst:** Hermes Main (DeepSeek V4 Flash)
**Goal:** Identify what prevents ObserveCo from being a generic Mac observability product — non-intrusive, auto-discovering, agent-agnostic, maximally helpful.

**Guiding principle:** The product should work on `pip install && observeco run` with zero config. Everything it can discover, it should. Nothing it can't discover should crash — it should degrade gracefully with useful partial data.

---

## Assessment Framework

Each finding is evaluated on three axes:

| Axis | Question |
|------|----------|
| **Discoverability** | Can the product auto-detect this at runtime instead of hardcoding? |
| **Optionality** | If this data isn't available, does it crash silently or gracefully skip? |
| **Maximalism** | Does the product collect everything useful or only what it was designed for? |

---

## Category A — Path Assumptions (Blockers)

These prevent ObserveCo from running at all on a non-Sean machine.

### A1. `hermes_home()` doesn't exist — 13 files hardcode `~/.hermes`

**Files:** `chisel/skill_compress.py`, `chisel/llm_client.py`, `chisel/skill_compress_clean.py`, `chisel/trim.py`, `proxy/service.py`, `capability/adapters/hermes.py`, `capability/probe.py`, `heal/watcher.py`, `heal/scanner.py`, `heal/config.py`, `pa_brief_diff.py`, `cli/billing_wire.py`, `tracking/sdk/provider_registry.py`

**Pattern:**
```python
Path.home() / ".hermes" / ...
```

**Product problem:** This assumes Hermes is installed at `~/.hermes`. If it's at `/opt/hermes`, `~/.config/hermes`, or not installed at all, every file that uses this path either crashes or returns empty results with no explanation.

**Solution:** Single `hermes_home()` function in `dirs.py`:
```python
def hermes_home() -> Path | None:
    """Discover Hermes install directory. Returns None if not found."""
    # Priority: env var > ~/.hermes > XDG config > discover via `hermes config path`
```
All 13 files import from `dirs.py`. None hardcode paths.

**Non-intrusive:** If `hermes_home()` returns `None`, the caller skips Hermes-specific scans gracefully. The dashboard shows "Hermes: not detected" instead of crashing.

---

### A2. `openclaw_home()` doesn't exist — 7+ files hardcode `~/.openclaw`

**Files:** `config.py:111`, `db.py:2431,2463`, `chisel/config_scanner.py:271`, `tracking/sdk/provider_registry.py:46,48`, `capability/probe.py:210`

**Pattern:**
```python
Path.home() / ".openclaw" / ...
```

**Product problem:** Same as A1. OpenClaw is Sean's specific framework fork. Most users won't have it.

**Solution:** Same pattern — single `openclaw_home()` in `dirs.py` returning `None` if not found. All OpenClaw scans are optional.

**Non-intrusive:** No OpenClaw? The product doesn't try to scan its agents. It just shows other data.

---

### A3. `init()` doesn't exist — first-run configuration gap

Currently there's no `observeco init` command. Users must:
1. Know where Hermes is installed
2. Know where OpenClaw is installed
3. Edit `dirs.py` to change paths (or set env vars nobody knows about)

**Product problem:** A product that requires source code edits to configure is not a product.

**Solution:** `observeco init` that auto-discovers paths and writes `~/.observeco/config.yaml`.

---

### A4. `log_dir()` should accept env override — `/tmp/openclaw` hardcode

**File:** `gateway_monitor.py:46`

**Code:**
```python
OPENCLAW_LOG_DIR = Path("/tmp/openclaw")
```

**Product problem:** Absolute path. No other machine has logs at `/tmp/openclaw`. If gateway_monitor can't find logs, it silently returns no data.

**Solution:** Make log directory configurable via env var or config file. Default to `None` (skip gateway monitoring).

---

## Category B — Agent Name Defaults (Maximalism Gap)

The product should observe *any* agent, not just Sean's named agents.

### B1. `metric_exemptions.py` — default author is a specific agent

**File:** `metric_exemptions.py:36,74,116`

```python
exempted_by: str = "hound"
```

**Product problem:** Hardcodes Sean's personal agent name as the default exemption author. A user who runs ObserveCo sees "Exempted by: hound" in their data with zero context.

**Solution:** Default to empty string `""` and require callers to provide a name. Or better: auto-detect the current agent name from the running Hermes/OpenClaw process.

**Maximalism:** If we can detect *which* agent created the exemption, we should record it. But we shouldn't assume a default that only exists on one machine.

---

### B2. `clawforge/plugin.py:106` — demo seed agents

```python
demo_agents = ["kepler", "hound"]
```

**Product problem:** These names appear in the dashboard UI. A new user sees "kepler" and "hound" as if they are real agents they should know about.

**Solution:** `observeco init` seeds with the user's actual discovered agents. Or don't seed at all — start empty, discover at runtime.

---

### B3. 6 files with fallback agent names

**Files:** `proxy/service.py`, `heal/scanner.py`, `auto_detect.py`, `cli.py`, `db.py`, `tracking/sdk/provider_registry.py`

**Pattern:** Agent name defaults like `"proxy-agent"`, `"test-agent"`, `"otel-agent"`, `"sdk-user"` used as CLI option defaults.

**Product problem:** These aren't blockers (user passes `--agent` on the command) but they create confusing "phantom agents" in the database if anyone runs a command without the flag. The product should either require `--agent` or auto-detect the current agent name.

**Solution:** Auto-detect agent name from the running process context (Hermes session, hostname, pid). Fallback to `"unknown"` instead of a fake name.

---

## Category C — Model Defaults (Outdated Assumptions)

### C1. `chisel/llm_client.py:21-51` — 6 outdated model defaults

```python
"deepseek-chat", "deepseek-v2", "gpt-4o-mini", "claude-3-haiku-20240307", ...
```

**Product problem:** These are Sean's specific model names from months ago. They probably don't exist on the user's Ollama instance. If the auto-detect runs and finds none of these, the feature silently returns "no models found."

**Solution:** Auto-detect models by querying `ollama list` or the provider's API. Don't hardcode model names at all. The product observes what's available — it doesn't tell the system what should be there.

---

### C2. `skill_compress.py` / `skill_compress_clean.py` — `hermes3:latest` default

**Files:** `chisel/skill_compress.py:94`, `chisel/skill_compress_clean.py:117`

```python
_OLLAMA_MODEL = os.environ.get("CAVEMAN_MODEL", "hermes3:latest")
```

**Product problem:** Two copies of the same default (`hermes3:latest`), gated behind an undocumented env var `CAVEMAN_MODEL`. A user has no way to know this env var exists.

**Solution:** Both files should probe `ollama list` and pick the best available model, or use a user-configured default from config.

---

### C3. `llm_service/__init__.py:296` — `gpt-4o` hardcode

**File:** `llm_service/__init__.py:296`

```python
"model": "gpt-4o",
```

**Product problem:** Assumes the user has OpenAI API access. If they don't, this silently fails.

**Solution:** Make the LLM provider configurable (config file + env var). Default to auto-detect the local Ollama instance. Only fall back to OpenAI if the user explicitly configured it.

---

## Category D — Shell Command Assumptions

### D1. `gateway_monitor.py` — `lsof` + `launchctl` specific

**File:** `gateway_monitor.py` (multiple lines)

**Problem:** `lsof` flags require `sudo` on some systems. `launchctl` is macOS-only.

**Product problem:** On macOS, `lsof` requires certain permissions. On Linux, `launchctl` doesn't exist.

**Solution:** Wrap platform-specific commands in try/except with graceful degradation. Linux: use `systemctl` or `/proc`. macOS: use `launchctl`. Unknown: skip gateway monitoring. Always handle permission errors gracefully.

**Maximalism:** Try all available methods per platform, not just one.

---

### D2. Process detection assumes `pgrep` / `ps` format

**Files:** `heal/watcher.py`, `gateway_monitor.py`, `auto_detect.py`

**Problem:** `pgrep` output format differs between macOS (BSD) and Linux. `ps -ef` columns differ. Parse failures silently return no data.

**Solution:** Use platform-aware process detection. `psutil` is already available. Use it.

---

## Category E — Framework Assumptions

### E1. Framework enum is closed — `["hermes", "openclaw", "custom"]`

**File:** `capability/probe.py`

**Product problem:** Only knows about Hermes and OpenClaw as frameworks. Any other agent framework (Claude Code, LangGraph, CrewAI, custom scripts) gets classified as "custom" with no probing.

**Solution:** Make framework detection pluggable. Add a "generic agent" probe that scans for running processes, model endpoints, and log directories without needing a known framework name.

---

### E2. Dashboard plugin config — 4 fictional OpenClaw plugins

**File:** `dashboard/config.py:192-196`

```python
OPENCLAW_PLUGIN_SOURCES = [
    PluginSource("ClawForge", "~/.openclaw/plugins/clawforge", ...),
    PluginSource("NeuralSearch", "~/.openclaw/plugins/neuralsearch", ...),
    PluginSource("DataPilot", "~/.openclaw/plugins/datapilot", ...),
    PluginSource("MemoryWeaver", "~/.openclaw/plugins/memoryweaver", ...),
]
```

**Product problem:** Four imaginary plugins appear in the dashboard for every user. They're not real products — they're Sean's development ideas. A user sees "ClawForge: not found" in their plugin dashboard.

**Solution:** Remove hardcoded plugins. Scan `OBSERVECO_PLUGIN_DIR` at runtime. Or remove the plugin dashboard entirely until plugins exist.

---

### E3. Config schema version locking

**Files:** `chisel/llm_client.py:84`, `tracking/sdk/provider_registry.py:141`, `proxy/service.py:347-397`, `capability/adapters/hermes.py`

**Product problem:** Each of these files has its own parser for Hermes YAML config, each expecting a specific layout. If the user's Hermes version has a different layout, they get `KeyError`.

**Solution:** One shared config reader with version awareness. If it can't parse, it logs a warning and skips that data source.

---

## Category F — Port Assumptions

### F1. Port 9119 hardcoded in health check

**File:** `health.py:200`

```python
urllib.request.urlopen("http://localhost:9119/health")
```

**Product problem:** Health check actively connects to `localhost:9119`. If dashboard runs on a different port, health check permanently reports the dashboard as DOWN. There's no way to override.

**Solution:** Read the dashboard port from config or the actual server instance. Default to 9119 but honour configuration.

---

### F2. Port 4318 (OTLP/HTTP) spread across 10 files without a shared constant

**Files:** `otel_listener.py`, `health.py`, `watch_consumers.py`, `startup_validation.py`, `service.py`, `cli.py` (x3)

**Product problem:** If the user starts the OTel listener on a custom port, 10 files all need editing. No single source of truth.

**Solution:** Define `OTLP_PORT` in `dirs.py` with env var override. All 10 files import from there.

---

### F3. Ports 8080, 9119, 11434, 18789 lack env-var overrides

**Product problem:** Standard ports are fine as defaults. But there's no way to say "actually, my Hermes is on port 9090." The product should honour environment variable overrides for every port it connects to.

---

## Category G — Discoverability Gap

### G1. Undocumented configuration knobs

**Env vars with no docs:**
- `CAVEMAN_MODEL` — hidden Ollama model selector
- `HERMES_HOME` — path only used in 1 file, 13 others ignore it

**Product problem:** These are valid configuration options but nobody knows they exist. A power user who wants to point ObserveCo at a custom Hermes install has no way to discover the right env var.

**Solution:** `observeco config` command that lists all supported env vars. OR: one config file at `~/.observeco/config.yaml` that's documented, and env vars override it.

---

### G2. No auto-discovery of install locations

**Product problem:** The product should scan common install locations at startup:
- `~/.hermes/` (standard Hermes)
- `/opt/hermes/` (system install)
- `~/.openclaw/` (if applicable)
- `~/.config/hermes/` (XDG convention)
- `/usr/local/etc/hermes/` (homebrew)
- Which `ollama` is on the PATH?

Currently it only knows `~/.hermes/`. If Hermes is installed via Homebrew, Docker, or system package, ObserveCo doesn't find it.

---

## Summary — 17 Findings by Priority

| Priority | Count | What |
|----------|-------|------|
| **Blockers** | 4 | No `hermes_home()`, no `openclaw_home()`, no `init()`, no `log_dir()` override |
| **High** | 4 | Agent name defaults (production + demo + phantom agents) |
| **Medium** | 6 | Model defaults outdated, port assumptions undocumented, undocumented env vars |
| **Low** | 3 | Platform commands, framework enum, config schema locking |

### Critical question that changes everything

**"Does the product require Hermes + OpenClaw to be useful?"**

If yes: the product is an ecosystem tool for Sean's specific stack. The audit is about making it work on other machines that also run Hermes + OpenClaw. Most findings are MEDIUM.

**If no: the product is a generic agent observability platform.** It should discover whatever agents are running — Hermes, Claude Code, LangGraph, custom Python scripts — and collect metrics on all of them. Most findings become CRITICAL because they reveal the product can only see Sean's specific stack.

This audit assumes **no** (generic platform). If the answer is **yes** (Hermes+OpenClaw only), re-rank accordingly.
