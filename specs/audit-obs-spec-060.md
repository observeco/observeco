## Spec Audit — obs-spec-060 (History-Assisted Task Generation)

### Trap 1: Happy Path Only

**Finding: 🟡 MEDIUM — Missing failure states for LLM assertion proposal**

The spec describes the happy path: LLM reads session → proposes assertions → user approves. But it doesn't describe:

- **What happens when the LLM call fails** (API down, rate limited, empty response)? The spec says "An LLM (using `OBSERVECO_LLM_API_KEY` or `OLLAMA_CLOUD_API_KEY`) reads..." but no fallback if neither key is configured or the call fails. The task draft should still be created with a default `contains` assertion and a note "LLM judge unavailable — review assertions manually."
- **What happens when clustering produces 0 groups** (all sessions are about the same topic)? The spec says "Limit to `--limit N` clusters" but doesn't handle the case where clustering produces fewer groups than the limit.
- **What happens when a session has no first user message** (e.g., the first message is a tool call or system message)? The prompt extraction would produce an empty string.
- **What happens when the source session is deleted from state.db** between `suggest-tasks` and the user clicking "View original conversation"? The modal would fail to load.

**Fix:** Add fallback behavior for each failure mode. Add a `--force` flag to skip sessions with empty first messages.

---

### Trap 2: Visuals Without States

**Finding: 🟡 MEDIUM — Dashboard pending-review section has no loading/empty/error states**

§6.1 describes the pending tasks section but doesn't specify:
- **Loading state:** What does the user see while drafts are being generated? (The CLI runs synchronously, but the dashboard needs to show "Generating task drafts..." while the backend processes.)
- **Empty state:** "No pending task drafts. Run `observeco canary suggest-tasks` to generate drafts from your agent's conversation history."
- **Error state:** "Failed to generate task drafts — LLM API unavailable. Check your API key configuration."
- **Source session modal:** §6.2 describes a modal with "first 5 messages" but doesn't specify loading/empty/error states for the modal itself.

**Fix:** Add state tables for the pending-review section and source session modal (per obs-spec-055's pattern).

---

### Trap 3: Lifecycle Not Specified

**Finding: ✅ PASS — Lifecycle is well-specified**

§9 describes the full lifecycle: suggest-tasks → drafts saved as pending → user reviews → approve/edit/reject → active tasks run in daily canary → user deletes stale tasks. Staleness handling is explicitly user-controlled. The "What We Don't Do" section (§10) clarifies boundaries.

---

### Trap 4: No Success Metrics (or Wrong Metrics)

**Finding: 🟡 MEDIUM — One metric is unmeasurable at spec time**

§12 lists 5 success metrics. 4 are measurable:
- Task proposal generation < 30s — measurable at build time
- User-defined task run < 3 min — measurable at build time
- Assertion quality (K=3 inter-rater agreement > 0.7) — measurable after first run
- Drift signal — measurable after weeks of data

**But "User approval rate > 30%"** is a product metric, not a spec metric. It depends on how many users use the feature and how good the LLM proposals are. At spec time, we can't set a target. This should be a post-launch tracking metric, not a spec acceptance criterion.

**Fix:** Replace with a measurable build-time metric: "Task draft generation produces valid YAML for ≥90% of selected sessions."

---

### Trap 5: Hidden Constraints

**Finding: 🟡 MEDIUM — Two unstated constraints**

1. **Hermes-only.** The spec assumes `~/.hermes/state.db` exists. For non-Hermes users (OpenClaw, Claude Code), this feature produces zero results. The spec should state: "Requires Hermes session database at `~/.hermes/state.db`. For non-Hermes users, this command returns 'No Hermes sessions found.'"
2. **macOS only.** The spec doesn't state the platform constraint. `state.db` path resolution may differ on Linux (XDG vs `~/.hermes`). Should state: "macOS only — Hermes session path is hardcoded to `~/.hermes/state.db`."

**Fix:** Add a constraints register to §3 with these two items.

---

### Trap 6: Contradictory Refs

**Finding: ✅ PASS — No contradictions found**

Cross-referenced against:
- obs-spec-055 (task definition UI) — `built_in` column exists, task editor exists, YAML schema matches
- obs-spec-057 (benchmark methodology) — `llm_judge` assertion type exists, K=3 scoring exists, algorithmic fallback exists
- Master plan row 60 — matches spec description
- `canary_tasks` table schema — `built_in` column exists (0/1), `source_session` column does NOT exist yet (will be added)

**One minor note:** The spec claims `source_session` as a field in the task draft schema (§4.3) but the `canary_tasks` table doesn't have this column. It will need a migration. This is expected for a new feature — not a contradiction, but should be noted in §11 File Changes.

---

### Coding Fidelity Check

**Finding: ✅ PASS — All code-referenced claims verified**

| Claim | Verification | Result |
|-------|-------------|--------|
| `state.db` has `sessions` table with `source`, `message_count`, `title`, `started_at` | ✅ Verified — all columns exist | PASS |
| `state.db` has `messages` table with `session_id`, `role`, `content` | ✅ Verified — all columns exist | PASS |
| `canary_tasks` has `built_in` column | ✅ Verified — column exists (0/1) | PASS |
| 9 built-in tasks exist | ✅ Verified — 9 tasks with built_in=1 | PASS |
| `CanaryRunner.run()` exists | ✅ Verified — method exists | PASS |
| `create_task()` exists | ✅ Verified — method exists in canary.py:725 | PASS |
| 122 telegram sessions with 3+ messages in last 30 days | ✅ Verified — data source is viable | PASS |

---

### System Design Check

**Finding: 🟡 MEDIUM — Data pipeline has a gap**

The spec says user-defined tasks run via the **Hermes adapter** (with `-p default`), not the DirectModelAdapter. But the current `CanaryRunner` doesn't filter by `built_in` — it runs all tasks. The spec needs to clarify:

1. **How does the runner distinguish generic vs user-defined tasks?** The `built_in` column exists but the runner doesn't filter on it yet. This is implementation work, not a spec gap — but the spec should call out that the runner needs modification.
2. **How does the runner know to use the Hermes adapter for user-defined tasks and the DirectModelAdapter for generic tasks?** Currently the runner uses one adapter per run. The spec implies two adapters per run — this is a design decision that needs to be explicit.

**Fix:** Add a note to §7: "The canary runner will execute two passes: generic tasks via the existing adapter chain, user-defined tasks via the Hermes adapter with `-p default`. The `built_in` column filters which pass each task belongs to."

---

### Master Fidelity Gate Score

| Layer | Max | Score | Notes |
|-------|-----|-------|-------|
| A: Requirements Fidelity | 14 | 10 | Traps 1, 4, 5 have gaps |
| B: Coding Fidelity | 14 | 14 | All code claims verified |
| C: UX Fidelity | 14 | 10 | Trap 2 — missing state tables |
| D: System Design | 18 | 14 | Data pipeline gap noted |
| **Total** | **60** | **48** | **PASS (threshold 47)** |

---

### Summary

| Severity | Count | Items |
|----------|-------|-------|
| 🚩 CRITICAL | 0 | — |
| 🚩 HIGH | 0 | — |
| 🟡 MEDIUM | 4 | Trap 1 (failure states), Trap 2 (state tables), Trap 4 (unmeasurable metric), Trap 5 (unstated constraints) |
| 🟢 LOW | 1 | Missing `source_session` column in DB migration list |
| ✅ PASS | 3 | Trap 3 (lifecycle), Trap 6 (refs), Coding Fidelity |

**Verdict: PASS (48/60).** The spec is structurally sound. The 4 MEDIUM findings are gaps in failure-mode coverage and state tables — not architectural flaws. Fix them before building.
