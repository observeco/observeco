# Chisel — Decompose, Drift, Suggest, Cut

**Plugin name:** `chisel`
**Version:** 0.2.0
**License:** MIT
**Author:** ObserveCo

---

## Problem

Agent system prompts grow. Identity sections bloat with accumulated
rules. Memory sections expand with every session. Skill descriptions
multiply. Nobody knows which section costs the most — until the model
starts ignoring instructions because the prompt is 15K tokens.

Token cost is per-API-call. A 12K-token system prompt at 50 turns/day =
600K wasted tokens/day if half of it is stale. At $3/Mtok input, that's
$1.80/day per agent. Five agents = $9/day = $3,285/year. For something
nobody can see.

**The problem has two layers:**
1. **Invisible** — no tool decomposes a prompt into functional components
   and shows which one is bloated
2. **Irreversible without help** — even when you find the bloat, cutting
   it safely (without removing something the agent needs) requires
   knowing what's redundant, what's stale, and what's never used

Chisel v0.2 solves both: it shows you the breakdown (v0.1), then
*suggests* what to cut, shows you the diff, and lets you apply it with
a backup. It learns which cuts were safe and suggests them again.

---

## Solution

Chisel decomposes any system prompt into 5 functional components,
estimates per-component token costs, and tracks drift over time.

### The 5-Component Taxonomy

| Component | What it covers | Why it matters |
|-----------|---------------|----------------|
| **Identity** | Role, persona, behavioral contract, voice | Defines who the agent is. Changes here affect every decision. |
| **Skills** | Skill descriptions, tool schemas, capability list | Defines what the agent can do. Grows as skills are added. |
| **Memory** | Injected memory, user profile, session context | Defines what the agent knows. Grows over time. |
| **Tools** | Tool descriptions, API specs, parameter schemas | Defines how the agent interacts. Fixed by the platform. |
| **Guidance** | Rules, constraints, policies, output format | Defines how the agent behaves. Grows with every correction. |

These are functional layers, not arbitrary sections. Changing each one
affects a different aspect of agent performance:
- Identity change → behavior shift
- Skills change → capability change
- Memory change → knowledge shift
- Tools change → interface change
- Guidance change → policy shift

## The 6-Step Self-Evolution Loop

```
1. trim    → "Here's your breakdown"                    (diagnose)
2. drift   → "Guidance grew 12% this week"               (monitor)
3. suggest → "23 duplicate rules, 4 stale refs, 2 unused skills.
              Estimated savings: 2,100 tokens (12%)."   (analyze)
4. cut     → Shows diff. Requires --apply to execute.   (execute)
5. verify  → Re-trims, confirms savings.                 (confirm)
6. learn   → Stores safe cuts. Suggests them next time.  (evolve)
```

The name works because the tool actually chisels — it finds the
cracks, marks the waste, and removes it. The learn step makes it
self-evolving: every verified cut teaches the system what's safe to
cut next time.

### Safety Constraints

- **`dry_run` is the default.** `hermes chisel cut` without `--apply`
  shows the diff only. No files are modified.
- **The hook never cuts.** `on_session_start` only trims + drifts.
  Cuts require explicit CLI invocation with `--apply`.
- **Every cut creates a backup.** Before any file is modified,
  Chisel copies the original to `~/.hermes/state/chisel/backups/`.
- **The user reviews every diff.** No silent modifications. The
  Hermes AGENTS.md principle: "A mitigation that kills the feature's
  purpose is the wrong mitigation." Silently cutting someone's prompt
  could kill their agent's behavior.

---

## Plugin Architecture

### Data Access: Read from Disk, Not from Hooks

The `on_session_start` hook in Hermes does NOT pass the system prompt
to plugins — it only passes `session_id`, `model`, and `platform`.
The system prompt is built on `agent._cached_system_prompt` (a private
attribute) two lines before the hook fires, but is never forwarded.

**Chisel reads the system prompt from disk directly** rather than
depending on hook internals. This is more robust and portable:

1. Read `~/.hermes/config.yaml` → extract the agent's system prompt sections
2. Read `~/.hermes/SOUL.md` → extract identity + behavioral contract
3. Read `~/.hermes/skills/` → extract skill descriptions
4. Read `~/.hermes/memory/` → extract injected memory entries
5. Assemble the full prompt, decompose into 5 components

The `on_session_start` hook is used as a **trigger** (run decomposition
now) rather than a data source. This means Chisel works identically
whether invoked via hook or CLI — both read the same files.

### Hook: `on_session_start` (trigger only)

```
on_session_start(session_id, model, platform)
  → read system prompt from disk (config.yaml + SOUL.md + skills + memory)
  → decompose into 5 components
  → estimate per-component tokens
  → write to chisel.db (trim_log table)
  → compare against 7-day rolling average
  → if any component drifts >10% with >50 token delta:
      → emit drift alert (log warning + optional webhook)
```

**Time-gate:** Drift check is skipped if the last trim for this agent
was <1 hour ago. This prevents redundant drift checks when the hook
fires on session resumption (not just new sessions).

### Hook: `on_session_end` (not used in v0.2)

The `on_session_end` hook fires on EVERY `run_conversation` call, not
just at session boundaries. Running drift detection on every turn is
wasteful. v0.1 relies on `on_session_start` (time-gated) + manual
`hermes chisel drift` command. v0.2 may add a daily cron trigger.

### CLI Commands

```bash
# ── v0.1: Diagnose + Monitor ──

# Decompose the current agent's system prompt
hermes chisel trim
# Output: breakdown table (identity, skills, memory, tools, guidance, total)

# Decompose a specific agent's prompt
hermes chisel trim --agent forge

# Show drift report for all agents
hermes chisel drift

# Show drift for a specific agent
hermes chisel drift --agent forge

# Show historical trend (last 30 days)
hermes chisel trend --agent forge --days 30

# Export breakdown as JSON (for piping to other tools)
hermes chisel trim --json

# ── v0.2: Suggest + Cut + Verify + Learn ──

# Suggest what can be cut
hermes chisel suggest
# Output: list of duplicate rules, stale file references, unused skills,
#         with per-item token savings and total estimated savings

# Suggest for a specific agent
hermes chisel suggest --agent forge

# Show what would be cut (dry-run — DEFAULT, no files modified)
hermes chisel cut
# Output: unified diff of proposed changes, total savings estimate

# Actually apply the cuts (requires --apply)
hermes chisel cut --apply
# Creates backup, writes compressed SOUL.md, logs to cut_log

# Cut a specific agent
hermes chisel cut --agent forge --apply

# Verify last cut — re-trim and confirm savings
hermes chisel verify
# Output: before/after comparison, savings confirmed or denied

# Set baseline (approve current composition)
hermes chisel baseline --agent forge

# Check against baseline (exit 1 if drift > threshold — CI gate mode)
hermes chisel baseline --check --agent forge
```

---

## Data Model

### SQLite: `chisel.db`

Location: `~/.hermes/state/chisel.db` (or `OBSERVECO_CHISEL_DB` env override)

```sql
CREATE TABLE trim_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    timestamp REAL NOT NULL,
    identity_tokens INTEGER NOT NULL,
    skills_tokens INTEGER NOT NULL,
    memory_tokens INTEGER NOT NULL,
    tools_tokens INTEGER NOT NULL,
    guidance_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    savings_ratio REAL NOT NULL,
    raw_prompt_hash TEXT NOT NULL  -- SHA-256 of prompt, for change detection
);

CREATE TABLE drift_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    component TEXT NOT NULL,  -- identity|skills|memory|tools|guidance
    current_tokens INTEGER NOT NULL,
    baseline_tokens INTEGER NOT NULL,
    delta_pct REAL NOT NULL,
    delta_tokens INTEGER NOT NULL,
    breached INTEGER NOT NULL,  -- 0 or 1
    method TEXT NOT NULL,  -- rolling|wow|absolute
    timestamp REAL NOT NULL
);

CREATE TABLE baseline (
    agent_name TEXT PRIMARY KEY,
    identity_tokens INTEGER NOT NULL,
    skills_tokens INTEGER NOT NULL,
    memory_tokens INTEGER NOT NULL,
    tools_tokens INTEGER NOT NULL,
    guidance_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    set_at REAL NOT NULL
);

-- v0.2: Cut logging + learning
CREATE TABLE cut_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    timestamp REAL NOT NULL,
    file_path TEXT NOT NULL,           -- which file was cut (SOUL.md, skill, etc.)
    cut_type TEXT NOT NULL,            -- duplicate_rule|stale_ref|unused_skill|verbose_rule
    tokens_before INTEGER NOT NULL,
    tokens_after INTEGER NOT NULL,
    tokens_saved INTEGER NOT NULL,
    backup_path TEXT NOT NULL,         -- path to backup file
    verified INTEGER DEFAULT 0,        -- 0=pending, 1=verified safe, -1=caused regression
    verified_at REAL,                   -- when verify ran
    rule_hash TEXT,                    -- hash of the specific rule/pattern cut (for learning)
    details TEXT                       -- JSON: what was cut, for display
);

CREATE INDEX idx_trim_agent ON trim_log(agent_name, timestamp);
CREATE INDEX idx_drift_agent ON drift_log(agent_name, timestamp);
CREATE INDEX idx_cut_agent ON cut_log(agent_name, timestamp);
CREATE INDEX idx_cut_verified ON cut_log(verified);
CREATE INDEX idx_cut_rule_hash ON cut_log(rule_hash);
```

WAL mode, `busy_timeout=5000`. Same pattern as pulse.db.

---

## Decomposition Algorithm

### Section Classification

The decomposer classifies each line of the system prompt into one of
the 5 components using keyword matching + markdown heading tracking.

**Algorithm:**
1. Split prompt into lines
2. For each line:
   a. If it's a markdown heading (`#`, `##`, `###`), classify the heading
      by keyword match → set `current_section`
   b. Otherwise, classify the line by keyword match → assign to
      `current_section` (or the classified section if stronger match)
3. Join lines per section, estimate tokens

**Keyword defaults** (configurable via `config.yaml`):

```yaml
chisel:
  sections:
    identity: ["identity", "role", "persona", "who you are", "you are", "i am"]
    skills: ["skill", "tool", "command", "function", "available action", "you can use", "you have access to"]
    memory: ["memory", "context", "history", "previous", "conversation", "recall", "user profile", "personal info"]
    tools: ["tool description", "tool schema", "api spec", "json schema", "parameter", "endpoint", "request format"]
    guidance: ["guideline", "rule", "instruction", "constraint", "policy", "format", "output format", "do not", "never", "always", "must", "should"]
```

**Unmatched lines** default to `guidance` (the catchall for rules and
policies — the most common bloat source).

** ponytail:** Keyword matching is naive — it misclassifies lines that
mention "tool" in a guidance context ("do not use the terminal tool
without approval"). Ceiling: ~15% misclassification on prompts with heavy
cross-references. Upgrade path: LLM-assisted classification with
confidence threshold, fallback to keyword on low confidence.

### Token Estimation

```python
CHARS_PER_TOKEN = 4.0  # English text approximation

def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))
```

** ponytail:** 4 chars/token is a rough estimate. Actual tokenization
varies by content (code ~3.5 chars/token, prose ~4.5, JSON ~3). Ceiling:
±20% error on code-heavy prompts. Upgrade path: use the agent's actual
tokenizer if available (tiktoken for OpenAI, transformers for local
models). The drift tracking is valid regardless of absolute accuracy —
it compares ratios over time using the same estimator.

### Drift Detection

```python
FLOOR = 50  # minimum tokens for drift calculation (noise floor)
DRIFT_THRESHOLD_PCT = 10.0  # % change to flag
DRIFT_THRESHOLD_ABS = 50  # absolute token change to flag (both must be true)

def check_drift(current: int, baseline: int) -> tuple[float, int, bool]:
    delta_pct = ((current - baseline) / max(baseline, FLOOR)) * 100
    delta_tokens = current - baseline
    breached = abs(delta_tokens) > DRIFT_THRESHOLD_ABS and abs(delta_pct) > DRIFT_THRESHOLD_PCT
    return delta_pct, delta_tokens, breached
```

A drift breach requires BOTH:
- >10% relative change (catches proportional growth)
- >50 token absolute change (catches noise on small sections)

### Suggest (v0.2)

Analyzes the system prompt and returns a list of cuttable items with
estimated savings. Three detection types — all pure regex/string ops,
zero LLM, zero external deps:

**1. Duplicate Rules** (`duplicate_rule`)

Scans all 5 components for identical lines (case-insensitive, after
stripping whitespace). Identical rules appearing in multiple sections
(e.g., "Never modify config.yaml without approval" in both Identity
and Guidance) are flagged. Only exact matches — no semantic dedup.

```python
def find_duplicates(prompt: str) -> list[dict]:
    """Find duplicate non-empty lines across the prompt."""
    lines = prompt.split("\n")
    seen = {}  # normalized_line → (section, original_line, line_num)
    duplicates = []
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if len(stripped) < 20:  # skip short lines (headings, separators)
            continue
        if stripped.startswith("#") or stripped.startswith("```"):
            continue
        if stripped in seen:
            duplicates.append({
                "type": "duplicate_rule",
                "line": line,
                "first_seen": seen[stripped],
                "line_num": i,
                "tokens": estimate_tokens(line),
            })
        else:
            seen[stripped] = (i, line)
    return duplicates
```

Source: adapted from `chisel/trim.py:compress_guidance_block()` (line 490)
which already implements exact-match dedup.

**2. Stale File References** (`stale_ref`)

Scans the prompt for file paths (regex: `~/...` or `/Users/...` or
`\.hermes/...`) and checks if each path exists on disk. Dead references
mean either the file was moved or the prompt is stale.

```python
def find_stale_refs(prompt: str) -> list[dict]:
    """Find file path references that don't exist on disk."""
    import os, re
    path_pattern = r'(?:~|/Users/[^/]+|\.hermes)/[^\s"\'\)]+'
    matches = re.findall(path_pattern, prompt)
    stale = []
    for m in matches:
        expanded = os.path.expanduser(m)
        if not os.path.exists(expanded):
            stale.append({
                "type": "stale_ref",
                "path": m,
                "tokens": estimate_tokens(m),
            })
    return stale
```

Source: adapted from `chisel/config_scanner.py:check_stale_references()` (line 234).

** ponytail:** Regex path extraction misses paths inside code blocks and
inline backticks. Ceiling: ~10% of paths missed. Upgrade path: markdown
AST parsing to distinguish code from prose.

**3. Unused Skill Descriptions** (`unused_skill`)

Cross-references skills listed in `~/.hermes/skills/` against the
system prompt. If a skill's name doesn't appear in the prompt, it may
be loaded but unused. Requires reading the skills directory.

```python
def find_unused_skills(prompt: str, skills_dir: Path) -> list[dict]:
    """Find skill files not referenced in the prompt."""
    if not skills_dir.is_dir():
        return []
    prompt_lower = prompt.lower()
    unused = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_name = skill_dir.name.lower()
        if skill_name not in prompt_lower:
            # Read the SKILL.md to estimate token cost
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text()
                unused.append({
                    "type": "unused_skill",
                    "skill": skill_dir.name,
                    "tokens": estimate_tokens(content),
                })
    return unused
```

** ponytail:** "Not in prompt" ≠ "unused." The skill may be loaded
dynamically by Hermes' skill system without appearing in the static
prompt text. Ceiling: false positives on dynamically-loaded skills.
Upgrade path: cross-reference against Hermes' `skills_list` API output.

### Cut (v0.2)

Applies the suggested cuts to the prompt file. Two modes:

**Dry-run (default):** Shows a unified diff of all proposed changes.
No files modified. User reviews before applying.

**Apply (`--apply` flag):** Creates a backup, writes the compressed
file, logs the cut to `cut_log`.

```python
def apply_cuts(file_path: str, suggestions: list[dict], apply: bool = False) -> dict:
    """Apply suggested cuts to a file. Returns result with savings."""
    original = Path(file_path).read_text()
    backup_path = None

    if apply:
        backup_dir = Path.home() / ".hermes" / "state" / "chisel" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{Path(file_path).name}.{int(time.time())}.bak"
        backup_path.write_text(original)

    # Apply rule-based compression (from chisel/trim.py:compress_guidance_block)
    compressed = compress_guidance_block(original)

    # Remove stale references
    for s in suggestions:
        if s["type"] == "stale_ref":
            compressed = compressed.replace(s["path"], "")

    before_tokens = estimate_tokens(original)
    after_tokens = estimate_tokens(compressed)

    if apply:
        Path(file_path).write_text(compressed)
        # Log to cut_log
        log_cut(file_path, before_tokens, after_tokens, backup_path, suggestions)

    return {
        "applied": apply,
        "file": file_path,
        "backup": str(backup_path) if backup_path else None,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "tokens_saved": before_tokens - after_tokens,
        "savings_pct": round((1 - after_tokens / max(before_tokens, 1)) * 100, 1),
        "diff": _unified_diff(original, compressed),
    }
```

Source: adapted from `chisel/trim.py:run_compress()` (line 559) which
already implements read/backup/write + logging.

**Rule-based compression rules** (from `chisel/trim.py:519-534`):

| Pattern | Replacement |
|---------|-------------|
| `you MUST` | `must` |
| `You MUST` | `Must` |
| `you should` | `should` |
| `You should` | `Should` |
| `you may` | `can` |
| `You may` | `Can` |
| `do not` | `don't` |
| `Do not` | `Don't` |
| `Do NOT` | `Don't` |
| `do NOT` | `don't` |
| `please ` | `` (removed) |
| `Please ` | `` (removed) |
| `Note: ` | `` (removed) |
| `Important: ` | `` (removed) |

Plus: deduplication of identical lines (case-insensitive exact match).

### Verify (v0.2)

After a cut is applied, verify re-runs `trim` and compares:

```python
def verify_cut(agent_name: str) -> dict:
    """Re-trim after last cut, confirm savings."""
    # Get the most recent cut
    last_cut = get_last_cut(agent_name)
    if not last_cut:
        return {"status": "no_cut_found"}

    # Re-read the file and decompose
    prompt = read_system_prompt(agent_name)
    result = decompose(prompt)
    store_trim(agent_name, result, prompt)

    # Compare against pre-cut trim
    pre_cut = get_trim_before_cut(agent_name, last_cut["timestamp"])
    if not pre_cut:
        return {"status": "no_pre_cut_data"}

    saved = pre_cut["total_tokens"] - result["total_tokens"]

    # Mark cut as verified
    verified_status = 1 if saved > 0 else -1  # 1=safe, -1=regression
    update_cut_verified(last_cut["id"], verified_status)

    return {
        "status": "verified" if verified_status == 1 else "regression",
        "tokens_before": pre_cut["total_tokens"],
        "tokens_after": result["total_tokens"],
        "tokens_saved": saved,
    }
```

### Learn (v0.2)

The learning loop is simple and deterministic — no FTS5, no LLM:

1. After a cut is verified safe (`cut_log.verified = 1`), the
   `rule_hash` of each cut item is stored
2. On the next `suggest` run, the system queries `cut_log` for
   verified cuts with the same `rule_hash`
3. If a rule was cut and verified safe before, `suggest` marks it
   as "previously verified safe" in the output

```python
def get_verified_rules(agent_name: str) -> set[str]:
    """Get rule_hashes of cuts that were verified safe for this agent."""
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT rule_hash FROM cut_log WHERE agent_name = ? AND verified = 1 AND rule_hash IS NOT NULL",
            (agent_name,),
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        db.close()
```

** ponytail:** This is per-agent learning, not cross-agent. Agent A's
verified cuts don't influence Agent B's suggestions. Ceiling: no
fleet-level pattern learning. Upgrade path: cross-agent FTS5 match
on rule_hash + agent_name, suggesting cuts that were safe across
multiple agents.

---

## Config

In `config.yaml` (not env vars — per Hermes AGENTS.md convention):

```yaml
chisel:
  enabled: true
  # Override the 5 component keywords (optional)
  sections:
    identity: ["identity", "role", "persona"]
    # ... (omit to use defaults)
  # Drift thresholds
  drift:
    threshold_pct: 10.0
    threshold_abs: 50
    window_days: 7
  # Token estimation
  chars_per_token: 4.0
  # Alert on drift breach (optional)
  alert:
    enabled: false
    webhook_url: ""  # POST JSON alert on breach
```

---

## Dependencies

**Zero external runtime dependencies.**

- `sqlite3` (stdlib)
- `hashlib` (stdlib)
- `re` (stdlib)
- `json` (stdlib)
- `difflib` (stdlib — for unified diff in `cut` dry-run)
- `urllib.request` (stdlib, only if webhook alert enabled)

No `rich`, no `typer`, no `click`. The plugin hooks write to SQLite
silently. CLI output uses plain text tables (stdlib `print`).

** ponytail:** Plain text tables are ugly. If the user has `rich`
installed (Hermes bundles it), the CLI can use it for nicer output.
But the plugin must not require it. Detection: `try: import rich; except ImportError: use_plain_text()`.

---

## What's NOT in v0.2

- **LLM-assisted classification.** The keyword matcher is the v0.1 approach.
  LLM classification is a v0.3 upgrade for users who want higher accuracy.
- **Semantic dedup.** Only exact-match duplicate detection. "Never modify
  config.yaml without approval" and "Don't edit config.yaml without
  permission" are not detected as duplicates. v0.3 may add embedding-based
  similarity.
- **Cross-agent learning.** Verified cuts are per-agent. Agent A's safe
  cuts don't influence Agent B. v0.3 may add fleet-level pattern matching.
- **Auto-cut.** The hook never cuts. Cuts require explicit `hermes chisel
  cut --apply`. The user reviews every diff. The system suggests, the
  human decides.
- **Per-skill breakdown.** v0.2 classifies all skill descriptions as
  "skills". v0.3 may break down per-skill token costs.
- **Web dashboard.** v0.2 is CLI + hook only. The dashboard is ObserveCo's
  job, not the plugin's.
- **Multi-framework support.** v0.2 targets Hermes (reads config.yaml +
  SOUL.md structure). v0.3 may add adapters for other frameworks.

---

## Empty States

Every user-facing path must handle the case where data doesn't exist yet.

| State | Trigger | Behavior |
|-------|---------|----------|
| **First run** | No rows in `trim_log` for this agent | `hermes chisel trim` runs decomposition and stores first baseline. `hermes chisel drift` shows: "No baseline data yet. Run `hermes chisel trim` to establish a baseline. Drift tracking begins after 2+ snapshots." |
| **Missing config** | `~/.hermes/config.yaml` not found or unreadable | Show: "No config.yaml found at ~/.hermes/config.yaml. Chisel reads your agent's system prompt from config.yaml + SOUL.md. Create a config first." Exit 1. |
| **Missing SOUL.md** | `~/.hermes/SOUL.md` not found | Continue with config.yaml only. Identity section will be empty (0 tokens). Show warning: "SOUL.md not found — identity section will be empty. Create ~/.hermes/SOUL.md for a complete breakdown." |
| **Empty prompt** | All sources read but assembled prompt is <100 chars | Show: "Assembled system prompt is only N chars. This may indicate a minimal config. Check config.yaml and SOUL.md." Still produce a breakdown (even if all zeros). |
| **Insufficient drift data** | <2 trim snapshots for this agent | Show: "Need at least 2 trim snapshots to calculate drift (have: N). Run `hermes chisel trim` to collect more data." |
| **Missing config section** | `chisel:` block not in config.yaml | Use default keywords silently. No warning — defaults are sensible. |
| **DB corruption** | `sqlite3.OperationalError` on read/write | Auto-recreate chisel.db from schema on next write. Log warning: "chisel.db was corrupted — recreated from schema. Historical data lost." |
| **No suggestions** | `suggest` finds nothing cuttable | Show: "No cuttable items found. Your prompt is already lean." Exit 0. |
| **Cut with no suggestions** | `cut` called but no `suggest` was run | Run suggest automatically, then show diff. No error. |
| **Verify with no prior cut** | `verify` called but `cut_log` is empty | Show: "No cuts to verify. Run `hermes chisel cut --apply` first." Exit 0. |
| **Verify with no pre-cut data** | `verify` finds cut but no pre-cut trim snapshot | Show: "Cannot verify — no pre-cut trim snapshot found. The cut was applied but there's no baseline to compare against." Mark cut as `verified=0` (pending). |
| **Backup directory missing** | `~/.hermes/state/chisel/backups/` doesn't exist on `cut --apply` | Create it automatically. No error. |
| **Cut causes regression** | `verify` finds tokens went UP after cut | Mark `cut_log.verified = -1`. Show: "⚠️ Regression detected: tokens went from N to M (+K). Consider restoring from backup: {backup_path}" |

---

## Lifecycle

| Event | Behavior |
|-------|----------|
| **Plugin enabled** | Runs trim on next `on_session_start`. Stores first baseline. No historical data exists — drift tracking begins after 2+ snapshots. |
| **Plugin disabled** | Leaves `chisel.db` intact. Data survives re-enable. No cleanup. |
| **DB corruption** | Auto-recreate from schema on next write. `CREATE TABLE IF NOT EXISTS` for all DDL. `sqlite3.OperationalError` caught, DB recreated, warning logged. |
| **Migration** | `schema_version` table tracks DB version. On plugin init: if version < current, run migration SQL. v0.1 starts at schema_version=1. |
| **Agent renamed** | Old agent's data remains in chisel.db under old name. New agent name starts fresh. No automatic migration — user can export/import via JSON if needed. |
| **Multi-profile** | Each Hermes profile has its own `~/.hermes/state/chisel.db`. No cross-profile data sharing. |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Decomposition accuracy** | ≥85% of tokens correctly classified | Validated against manual labeling of 10 diverse system prompts (Hermes default, minimal, heavily customized, multi-agent, non-English). Publish accuracy table in README. |
| **Drift false-positive rate** | <5% of breach alerts are noise | Tracked over 30 days: breach alerts ÷ total drift checks. Breach = both thresholds triggered. Noise = breach where manual review confirms no actual bloat. |
| **Performance** | Decomposition completes in <50ms | Measured on a 15K-token prompt. Must not add perceptible latency to session start. |
| **Token estimation error** | ±20% vs actual tokenizer | Validated against tiktoken (OpenAI) and llama.cpp tokenizer on the same 10 prompts. Published in README as known limitation. |
| **Suggest precision** | ≥80% of suggested cuts are actionable | Of all items suggested, 80%+ should be real duplicates, real stale refs, or real unused skills. False positives = suggested items that the user rejects on review. |
| **Cut savings** | ≥5% token reduction per cut | Each applied cut should save at least 5% of total prompt tokens. Below 5% = not worth the risk. |
| **Verify accuracy** | 100% of verified cuts confirm savings | Every `verify` run should find the post-cut prompt smaller than the pre-cut prompt. If tokens went up, that's a regression (logged as `verified=-1`). |
| **Learn recall** | ≥50% of repeat suggestions include verified rules | After 3+ cut cycles, at least half of the suggestions should reference previously verified cuts. |

---

## Extraction Plan

### What stays in ObserveCo

- `src/observeco/chisel/` — the full-featured version with rich tables,
  dashboard integration, config_scanner, skill_compress, migrations
- ObserveCo dashboard chisel routes
- ObserveCo's `db.get_trims()`, `db.log_drift()` — these are ObserveCo's
  DB methods, the plugin uses its own SQLite

### What moves to the plugin

- The decomposition algorithm (`_analyse_prompt`, `_classify_line`,
  `_estimate_tokens`) — extracted as standalone functions
- The drift detection logic (`check_drift`) — extracted as standalone
- The 5-component taxonomy + keyword defaults
- A new `chisel.db` SQLite schema (not ObserveCo's DB)
- `compress_guidance_block()` — rule-based compression (from `trim.py:490`)
- `run_compress()` — backup + write + log pattern (adapted from `trim.py:559`)
- `check_stale_references()` — dead file path detection (from `config_scanner.py:234`)
- `cut_log` table + learn query — new, not in ObserveCo

### Extraction steps

1. Create `plugins/context_engine/chisel/` in the plugin repo
2. Write `plugin.yaml` — hook declarations for `on_session_start`
3. Write `__init__.py` — hook handler: decompose → store → drift check
4. Write `chisel_core.py` — standalone decomposition + drift (no ObserveCo imports)
5. Write `chisel_cut.py` — suggest + cut + verify + learn (v0.2 additions)
6. Write `cli.py` — `hermes chisel trim/drift/trend/suggest/cut/verify/baseline`
7. Write `SPEC.md` (this file)
8. Write `README.md` — the user-facing doc with the "aha" screenshot
9. Test: install on a clean Hermes, run `hermes chisel trim`, verify output
10. Test: run `hermes chisel suggest`, verify duplicate/stale detection
11. Test: run `hermes chisel cut` (dry-run), verify diff output
12. Test: run `hermes chisel cut --apply`, verify backup created + file modified
13. Test: run `hermes chisel verify`, verify savings confirmed

### Files

```
plugins/context_engine/chisel/
├── plugin.yaml          # Hook declarations
├── __init__.py          # Hook handler (on_session_start → decompose + drift)
├── chisel_core.py       # Decomposition + drift + formatting (zero deps)
├── chisel_cut.py        # Suggest + cut + verify + learn (v0.2)
├── cli.py               # CLI commands (hermes chisel trim/drift/trend/suggest/cut/verify/baseline)
├── SPEC.md              # This file
├── README.md            # User-facing doc
└── test_self_check.py   # Self-check tests
```

---

## Testing

### Self-check (no framework needed)

```python
# ── v0.1: Decomposition + Drift ──

def test_decompose():
    prompt = "# Identity\nYou are a helpful agent.\n# Skills\nYou have tools.\n# Memory\nRemember things."
    result = analyse_prompt(prompt)
    assert result["identity_tokens"] > 0
    assert result["skills_tokens"] > 0
    assert result["memory_tokens"] > 0
    assert abs(result["total_tokens"] - sum of components) <= 2  # rounding tolerance

def test_check_drift():
    _, _, breached = check_drift(100, 100)
    assert not breached  # no change
    _, _, breached = check_drift(200, 100)
    assert breached  # 100% + 100 tokens

# ── v0.2: Suggest + Cut + Verify + Learn ──

def test_find_duplicates():
    prompt = "# Guidance\nNever modify config.yaml without approval.\n## Identity\nNever modify config.yaml without approval."
    dupes = find_duplicates(prompt)
    assert len(dupes) == 1
    assert dupes[0]["type"] == "duplicate_rule"

def test_find_stale_refs():
    prompt = "# Memory\nSee ~/nonexistent/path/to/file.md for details."
    stale = find_stale_refs(prompt)
    assert len(stale) == 1
    assert stale[0]["type"] == "stale_ref"
    assert "nonexistent" in stale[0]["path"]

def test_compress_guidance_block():
    text = "You MUST not do this. You should always do that. Please be careful."
    compressed = compress_guidance_block(text)
    assert "must not do this" in compressed.lower()
    assert "should always do that" in compressed.lower()
    assert "please" not in compressed.lower()
    assert len(compressed) < len(text)

def test_cut_dry_run():
    # Dry-run should not modify files
    result = apply_cuts("/tmp/test_soul.md", suggestions=[], apply=False)
    assert result["applied"] == False
    assert "diff" in result

def test_verify_no_cut():
    result = verify_cut("test_agent")
    assert result["status"] == "no_cut_found"
```

### Manual verification

```bash
# v0.1
hermes chisel trim
# Should show a 5-row table with token counts per component

hermes chisel drift
# First run: "No baseline data yet — run 'hermes chisel trim' to start tracking"
# After 2+ runs on different days: drift table with Δ% and breach status

# v0.2
hermes chisel suggest
# Should show: "Found N duplicate rules, M stale references, K unused skills.
#              Estimated savings: X tokens (Y%)."

hermes chisel cut
# Should show: unified diff of proposed changes. No files modified.

hermes chisel cut --apply
# Should show: "Backup created at ~/.hermes/state/chisel/backups/SOUL.md.{ts}.bak
#               Cut applied: N tokens → M tokens (saved K, Y%)"

hermes chisel verify
# Should show: "Verified: N tokens → M tokens (saved K). Cut marked safe."
# Or: "⚠️ Regression: tokens went from N to M (+K). Backup at {path}"
```

---

## Provenance

**Original work.** No paper source. The 5-component taxonomy
(identity/skills/memory/tools/guidance) was designed for ObserveCo's
chisel module. The drift detection algorithm is original.

**Related but distinct:**
- LLMLingua (Microsoft) — compresses raw text, no functional decomposition
- Mem0 — extractive memory management, no prompt-level analysis
- MemoHarness (arxiv 2607.14159) — uses D1-D6 taxonomy for harness
  optimization, but does not decompose the system prompt itself
- ProofAgent (arxiv 2607.14275) — scores context quality against 7
  criteria, but does not track per-component token drift

Chisel is the only tool that decomposes a system prompt into functional
components and tracks how each component drifts over time.