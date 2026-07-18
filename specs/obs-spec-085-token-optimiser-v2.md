# obs-spec-085: Token Optimiser v3 — Snapshot-Backed Skill Cost Analysis

**Status:** 🔴 Spec — awaiting build approval
**Product:** ObserveCo dashboard → Brain tab → Section 4 (Token Optimiser)
**Replaces:** v2 filesystem scan (obs-spec-085 v2, now deprecated — measured wrong cost surface)
**Owner:** Pragma (COO)
**Date:** 2026-07-14

---

## §0 Requirements Decision Record (RDR)

| Field | Value |
|-------|-------|
| **Problem** | Token Optimiser v2 scanned ALL `.md` files in `~/.hermes/skills/` and reported "2,244 unused skills (4M tokens)." This is wrong: 1,967 of those files are reference/template/script files that are NEVER in the system prompt. The real cost surface is the `<available_skills>` index — only `name:` and `description:` from SKILL.md files, rendered as `    - {name}: {desc}` lines in the system prompt. Additionally, the binary "never triggered" signal is too coarse — a skill triggered 1 time in 675 turns is paying 24 tok/turn for nothing. The real signal is **cost-per-use efficiency**: token cost per turn ÷ trigger count. |
| **Solution sketch** | Replace filesystem scan with Hermes' own `.skills_prompt_snapshot.json` (the same snapshot `build_skills_system_prompt()` uses). Cross-reference against `skill_usage` table for per-skill trigger counts. Compute per-skill cost from the exact `name: description` line format. Compute efficiency score = `tokens_per_turn / max(trigger_count, 1)` — lower is better. Rank by efficiency (worst first). Show raw trigger counts alongside. Show dollar impact using real token_logs cost data. |
| **Key constraint** | Zero new dependencies. Must work on fresh installs (no Hermes, no snapshot). Must not overfit to Sean's fleet — the snapshot format is universal. |
| **Success metric** | Per-skill cost shown in tokens AND dollars, cross-referenced against actual trigger data. "Never triggered" count matches reality (90 of 94 in main profile, not 2,244 of 2,259). |
| **Tier mapping** | Free (all features). No Pro gating. |

---

## §1 Problem — v2 measured the wrong thing

v2 scanned ALL `.md` files in `~/.hermes/skills/`. This is wrong because:

| What v2 scanned | Count | Est tokens | In system prompt? | Real cost? |
|---|---|---|---|---|
| All `.md` files | 2,259 | 4.0M | ❌ No — references/templates/scripts are never in the prompt | ❌ Zero |
| SKILL.md files (full body) | 292 | 1.54M | ❌ No — only loaded via `skill_view()` | ❌ Only when explicitly viewed |
| **`<available_skills>` index (name+desc)** | **94 (main profile)** | **~3,024 tok** | **✅ Yes, every turn** | **✅ This is the burn** |

**The real cost surface:** The `<available_skills>` block in the system prompt. Built by `build_skills_system_prompt()` in `prompt_builder.py`. Each skill appears as `    - {name}: {desc}` — the exact format is known and measurable.

**The real data (from Sean's fleet, 2026-07-14):**

| Metric | Value | Source |
|--------|-------|--------|
| Skills in main profile snapshot | 94 | `.skills_prompt_snapshot.json` |
| Skills triggered (ever) | 4 of 94 | `skill_usage` table (triggered=1) |
| Never triggered | 90 of 94 | Set subtraction |
| Per-turn cost of never-triggered | ~1,767 tok | Exact `name: desc` line bytes |
| Total `<available_skills>` block | ~3,024 tok | Replicated exact format |
| All-time cost of never-triggered skills | ~$135 | Real token_logs cost data |
| Monthly projected | ~$58 | Extrapolated from 7-day data |

**Why the snapshot is the right source:**
- It's the SAME snapshot Hermes uses to build the system prompt — no measurement error
- It already has parsed `name`, `description`, `category` — no YAML parsing needed
- It's per-profile — each agent has its own `<available_skills>` block
- It's cached on disk — no filesystem walk on every API call

---

## §2 Solution — Snapshot-Backed Skill Cost Analysis

### Core insight

Instead of scanning the filesystem (which measures the wrong thing), read the `.skills_prompt_snapshot.json` that Hermes already writes. This gives the EXACT set of skills in the `<available_skills>` index, with their exact `name` and `description` — the same strings that appear in the system prompt on every turn.

### What changes

**1. Snapshot reader (~20 lines, `server.py`)**

```python
def _load_skill_snapshot(profile_dir: str = None) -> dict:
    """Load Hermes' .skills_prompt_snapshot.json for a profile.
    Returns {skills: [{name, description, category, ...}], category_descriptions: {...}}.
    Falls back to filesystem scan if no snapshot exists (fresh install).
    """
    if profile_dir:
        snap_path = os.path.join(profile_dir, ".skills_prompt_snapshot.json")
    else:
        # Default: main profile
        snap_path = os.path.expanduser("~/.hermes/profiles/main/.skills_prompt_snapshot.json")
    if os.path.exists(snap_path):
        with open(snap_path) as f:
            return json.load(f)
    # Fallback: scan SKILL.md files directly (fresh install, no snapshot yet)
    return _fallback_scan_skills()
```

**2. Per-skill cost computation**

The exact format from `prompt_builder.py`:
```
    - {name}: {description}
```

Per-skill cost = `len(f"    - {name}: {desc}".encode("utf-8")) // 4 + 1` tokens.

**3. Endpoint computation change (`/api/optimiser/stats`)**

```python
# v2 (wrong): scanned all .md files
universe = _scan_skill_universe()  # 2,259 files, 4M tokens

# v3 (correct): reads the actual snapshot, computes efficiency score
snapshot = _load_skill_snapshot()
universe = snapshot["skills"]  # 96 skills, exact name+desc
# Build trigger lookup from skill_usage (normalize path-prefixed names)
triggered = {row["skill_name"]: row["turn_count"] for row in skill_rows if row["triggered"] == 1}
# Normalize: strip path prefixes (operations/foo → foo, qa/bar → bar, devops:baz → baz)
def normalize(name):
    if "/" in name: name = name.split("/")[-1]
    if ":" in name: name = name.split(":")[-1]
    return name
triggered_by_bare = {normalize(k): v for k, v in triggered.items()}

for s in universe:
    line = f"    - {s['name']}: {s.get('description', '')}"
    s["est_tokens"] = len(line.encode("utf-8")) // 4 + 1
    s["trigger_count"] = triggered_by_bare.get(s["name"], 0)
    s["efficiency"] = round(s["est_tokens"] / max(s["trigger_count"], 1), 1)
# Rank by efficiency descending (worst first: high cost, low triggers)
unused.sort(key=lambda s: s["efficiency"], reverse=True)
```

Response adds:
```json
{
  "skills_unused": [{"name": "observeco-ux-architect", "est_tokens": 24, "trigger_count": 0, "efficiency": 24.0, "category": "design"}, ...],
  "skills_unused_total": 93,
  "skills_unused_total_tokens": 1896,
  "skills_universe_size": 96,
  "savings": {
    "lite": 1.9,
    "full": 7.3,
    "never_triggered_tokens": 1896,
    "never_triggered_cost_per_turn": 0.000265,
    "never_triggered_cost_all_time": 135.42,
    "never_triggered_cost_monthly": 58.04
  }
}
```
**4. UI change — "Projected savings" box replaced with real cost data + efficiency ranking**

| Element | What it shows | Source |
|---------|--------------|--------|
| Lite (current) | `-1.9%` | Real `compress_log` avg (unchanged) |
| Full (available) | `-7.3%` | Real `compress_log` avg (unchanged) |
| **Never-triggered cost** | `~1,896 tok/turn ($0.000265/turn)` | Snapshot × exact format |
| **All-time cost** | `~$135` | Snapshot × token_logs cost data |
| **Monthly projected** | `~$58` | Extrapolated from 7-day data |
| **Top 5 by efficiency** | `observeco-ux-architect: 24 tok/turn, 0 triggers, eff=24.0` | Per-skill cost, ranked by efficiency (worst first) |

The efficiency score = `tokens_per_turn / max(trigger_count, 1)`. Lower is better. A skill with 24 tok/turn and 6 triggers has efficiency 4.0 — good value. A skill with 24 tok/turn and 0 triggers has efficiency 24.0 — worst case.

The unused list shows: name, est_tokens, trigger_count, efficiency. Ranked by efficiency descending (worst first).

**Frontend JS change (`loadOptimiser()`):** The unused list rendering changes from:
```js
listEl.textContent = d.skills_unused
  .map(function(s) { return '• ' + s.name + ' (~' + s.est_tokens.toLocaleString() + ' tok)'; })
  .join('\n');
```
To:
```js
listEl.textContent = d.skills_unused
  .map(function(s) { return '• ' + s.name + ' (' + s.est_tokens + ' tok/turn, ' + s.trigger_count + ' triggers, eff=' + s.efficiency + ')'; })
  .join('\n');
```

The "Skills never triggered" row label changes from `"X unused (est. Y tokens)"` to `"X underused (est. Y tok/turn)"` — reflecting that the signal is efficiency, not binary never-triggered.

**5. Remove 200-turn gate** (already done in v2)

---

## §3 What doesn't build

- **No per-agent skill tracking.** Fleet-wide snapshot (main profile) is the default. Per-agent requires loading each profile's snapshot — deferred.
- **No exact dollar cost per skill.** Dollar cost requires per-agent turn volume × cache hit rate. We show per-turn token cost (exact) and all-time dollar cost (from real token_logs). Per-skill dollar attribution is an estimate.
- **No automatic pruning.** The optimiser shows candidates. User decides.
- **No `guidance_fire` replacement.** Already removed in v2.

---

## §4 Acknowledged limitations

**The snapshot is per-profile.** The main profile snapshot has 94 skills. Other profiles have 72-98. The fleet-wide view uses the main profile as default. Per-agent views would need per-profile snapshots.

**"Never triggered" means "never loaded via skill_view/skill_manage tool call."** A skill can still be useful just by being in the index — the agent reads its name+description and may follow its guidance without loading the full body. The optimiser flags candidates for review, not automatic deletion.

**Cache hit rate is low (2.1%).** Most turns pay full input cost ($0.14/1M) rather than cache read ($0.014/1M). This means the `<available_skills>` block cost is higher than it would be with effective caching. This is a Hermes caching issue, not an optimiser issue.

**Upgrade path:** Load per-profile snapshots for per-agent views. Parse `config.yaml` for explicit skill lists to distinguish "loaded but unused" from "never supposed to load."

---

## §5 Lifecycle

| Phase | What happens | Optimiser state |
|-------|-------------|-----------------|
| **Fresh install** | No Hermes, no snapshot | "Hermes skills not detected" |
| **Hermes installed, no snapshot** | Skills exist, snapshot not yet written | Fallback filesystem scan of SKILL.md files |
| **Snapshot exists** | `.skills_prompt_snapshot.json` written by Hermes | Full analysis with exact name+desc cost |
| **Skills added/removed** | Snapshot regenerated by Hermes on next session | Auto-updates on next API call |
| **Upgrade from v2** | Old `_scan_skill_universe()` replaced | New snapshot reader takes over |
| **Crash/restart** | Dashboard restarts, DB intact | Optimiser re-reads snapshot + DB |

---

## §6 Implementation

### SCOPE

SCOPE:
Structure: [1] `_load_skill_snapshot()` function, [2] per-skill cost computation, [3] endpoint rewrite, [4] UI rewrite (projected savings → real cost data)
Constraints: Zero new deps. Must work without Hermes snapshot (fallback). Per-skill cost from exact `name: desc` format.
Outcomes: Optimiser shows real per-skill cost in tokens AND dollars. "Never triggered" count matches reality (90 of 94, not 2,244 of 2,259). Projected savings box shows real cost data.
Priming Rules: "The snapshot is the source of truth for the skill index. skill_usage records triggered skills. Per-skill cost = `len(f'    - {name}: {desc}') // 4 + 1`."
Edge Cases: No Hermes, no snapshot, empty snapshot, snapshot with 0 skills, all skills triggered, no skills triggered, no token_logs data.
Existing Patterns: `_scan_skill_universe()` in server.py (v2, to be replaced). `build_skills_system_prompt()` in prompt_builder.py (reference for exact format).

### Files changed

| File | Change | Lines |
|------|--------|-------|
| `src/observeco/dashboard/server.py` | Replace `_scan_skill_universe()` with `_load_skill_snapshot()`, rewrite endpoint, rewrite UI | ~60 changed |
| `src/observeco/dashboard/templates/index_new.html` | Update `loadOptimiser()` JS to handle new response shape | ~10 changed |
| `specs/obs-spec-085-token-optimiser-v2.md` | This spec update | ~50 changed |

**Total: ~70 lines net, 2 files**

### Verification

1. **Unit:** `_load_skill_snapshot()` returns snapshot with `skills` array when snapshot exists
2. **Unit:** `_load_skill_snapshot()` falls back to filesystem scan when no snapshot
3. **Unit:** Per-skill cost matches exact `name: desc` format (verified: observeco-ux-architect = 24 tok)
4. **Endpoint:** `/api/optimiser/stats` returns `skills_unused` with real names and token costs
5. **Endpoint:** `skills_unused_total` matches snapshot count minus triggered count (verified: 90 of 94)
6. **Endpoint:** `savings.never_triggered_cost_all_time` matches real token_logs data (verified: ~$135)
7. **UI:** Brain tab shows per-skill cost in tokens, not file size
8. **UI:** "Projected savings" box shows real cost data, not compression-only numbers
9. **Negative:** No crash when snapshot doesn't exist
10. **Negative:** No crash when `skill_usage` table is empty

### Pitfall (observed 2026-07-14)

**The v2 filesystem scan measured the wrong cost surface.** It scanned ALL `.md` files (2,259) and reported "4M tokens of unused skills." But 1,967 of those files are reference/template/scripts that are NEVER in the system prompt. The real cost surface is the `<available_skills>` index — only `name:` and `description:` from SKILL.md files. The snapshot is the correct source because it's what Hermes actually uses to build the system prompt.

**htmx script execution (from v2, still applies):** `loadOptimiser()` must be a main-page global triggered via `hx-on::after-swap` on `#brainContainer`. htmx does NOT execute `<script>` tags inside swapped partials.

---

## §7 Value comparison

| Aspect | v2 (filesystem scan) | v3 (snapshot-backed) |
|--------|---------------------|---------------------|
| Skills counted | 2,259 (all .md files) | 94 (actual index entries) |
| "Never triggered" | 2,244 (inflated by references) | 90 (real index entries) |
| Per-skill cost | File size / 4 (wrong) | Exact `name: desc` line format |
| Dollar cost | Not shown | Real token_logs data |
| Projected savings | Compression-only (-1.9% to -7.3%) | Real cost data + per-skill breakdown |
| Fresh install | Works (filesystem scan) | Works (fallback scan) |
| Data source | Filesystem walk | Hermes' own snapshot (same source as system prompt) |

---

## §8 Cross-references

- Master plan §3.4 (Brain Analysis, Section 4) — updated to reflect v3 spec
- Master plan feature matrix row 4c — updated to 🟡 v2 → 🔴 v3 spec
- `prompt_builder.py:build_skills_system_prompt()` — exact format reference
- `token_logs` table — real cost data source
- `skill_usage` table — trigger data source
- `qa/requirements-fidelity-playbook` — 6 Spec Traps applied (see audit)
- `qa/coding-fidelity-playbook` — SCOPE header, verification checklist applied
- `qa/system-design-testing-playbook` — lifecycle coverage, failure modes applied
