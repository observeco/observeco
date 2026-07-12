# obs-spec-060 — History-Assisted Task Generation

**Spec ID:** obs-spec-060
**Title:** History-assisted task generation — mine agent conversations to propose user-defined canary tasks
**Status:** ✅ Built (2026-07-12) — all 5 deliverables implemented & verified
**Owner:** Main
**Depends on:** obs-spec-055 (task definition UI), obs-spec-057 (benchmark methodology — llm_judge assertion type)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer"

---

## 1. What It Is

A CLI command that mines real agent conversations from the Hermes session database (`~/.hermes/state.db`), clusters them by topic, and proposes canary task drafts with suggested assertions. The user reviews, edits, and approves tasks via the existing dashboard task editor (obs-spec-055). Approved tasks run alongside the 10 generic canary tasks in the daily canary.

**Two benchmark tiers, side by side:**

| Tier | Source | Ground truth | What it measures |
|------|--------|-------------|------------------|
| **Generic** (existing) | 10 built-in tasks | Assertion-based (exact_match, numeric_range, llm_judge) | Model capability on standard tasks |
| **User-defined** (this spec) | Mined from agent history, user-approved | Human-anchored success criteria | Agent quality on its actual work |

---

## 2. Why Not Fully Automated

**Rejected design:** Auto-generate tasks from history with past response as expected output.

**Why it fails:**

1. **Circular benchmarking** — using past response as "correct" anchors to prior performance, not to correctness. If the old response was bad, we're measuring "does the new model match the bad response."
2. **First message ≠ the task** — a 343-message session about "SPGG Booking Issue" isn't captured by extracting "the tennis booking failed." The real task involved multi-step browser automation across many turns.
3. **No ground truth** — the product brief's "Primary" tier was explicit: the *user* defines expected output. "Must identify SQL injection on line 42." Mining history gives "whatever the agent said last time" — that's prior performance, not correctness.
4. **Selection bias** — sessions with 3+ messages are sessions where the agent struggled. Sessions where it nailed it in one response get filtered out. We'd benchmark against hard cases only.
5. **Tool mismatch** — original sessions used browser tools, terminal, web_search. The grid's `DirectModelAdapter` can't use tools. Tasks would fail on the grid not because the model is worse, but because it has no tools.
6. **Staleness** — a task from a July 6 conversation about "session prompt compression" is irrelevant once that feature ships or dies. History-mined tasks decay.

**Adopted design:** LLM *proposes*, user *approves*. The human review step is the ground truth anchor.

---

## 3. Data Source

The Hermes session database at `~/.hermes/state.db`:

- **`sessions` table** — session metadata: id, source, model, title, started_at, message_count, tool_call_count
- **`messages` table** — full conversation: session_id, role, content, tool_calls, tool_name, timestamp

### 3.1 Session Selection Criteria

| Criterion | Rationale |
|-----------|-----------|
| `source = 'telegram'` | Real user interactions, not cron/cli/subagent |
| `message_count >= 3` | Meaningful exchanges, not one-liners |
| `started_at` within last 30 days | Relevance — older sessions reference stale features |
| Exclude sessions where `title` contains "Test" or "test" | Filter out debugging/test sessions |

### 3.2 Constraints Register

| Constraint | Type | Detail |
|-----------|------|--------|
| Hermes-only | MUST | Requires `~/.hermes/state.db`. For non-Hermes users (OpenClaw, Claude Code), `suggest-tasks` returns "No Hermes sessions found." |
| macOS only | MUST | `state.db` path is hardcoded to `~/.hermes/state.db`. Linux XDG path resolution is not supported. |
| First-run empty state | MUST | If no qualifying sessions exist (fresh install, no Telegram conversations), `suggest-tasks` returns "No qualifying sessions found. Use the agent for a few days to build history." |
| Read-only access | MUST | The feature reads `state.db` but never writes to it. No risk of corrupting Hermes session data. |
| LLM dependency | SHOULD | Assertion proposal requires an LLM API key (`OBSERVECO_LLM_API_KEY` or `OLLAMA_CLOUD_API_KEY`). Without one, drafts are created with default `contains` assertions (see §4.2a). |

### 3.2 Session Clustering

Sessions are clustered by topic using the session title and first user message. The goal is to propose diverse tasks, not 5 variations of "SPGG booking."

1. Extract `(title, first_user_message)` for all qualifying sessions
2. Group by keyword overlap in title (simple keyword extraction — split on spaces, remove stop words, group by shared keywords)
3. From each cluster, select the session with the highest `message_count` (most complex interaction)
4. Limit to `--limit N` clusters (default 10)

**ponytail:** Clustering is naive keyword overlap, not embedding similarity. Ceiling: two sessions about different aspects of the same topic (e.g., "token optimization config" vs "token optimization dashboard") would cluster together. Upgrade path: sentence-transformers embeddings with cosine similarity threshold (already a dependency in the drift monitoring spec).

---

## 4. Task Proposal Generation

For each selected session, the system generates a task draft:

### 4.1 Prompt Extraction

The prompt is the **first user message** from the session, cleaned:
- Strip Telegram metadata prefixes (`[Sean Foo]`, `[Replying to: ...]`)
- Strip quoted reply context
- Truncate to 500 words (canary prompts should be focused)

### 4.2 Assertion Proposal

An LLM (using `OBSERVECO_LLM_API_KEY` or `OLLAMA_CLOUD_API_KEY`) reads:
- The first user message (the task)
- The assistant's response (context for what a good answer looks like)
- The conversation outcome (did the agent succeed? — inferred from message count and whether the session ended naturally)

And proposes 1-3 assertions:

```yaml
assertions:
  - type: llm_judge
    criteria: "Response must correctly identify the 7-day booking window as the root cause and propose a specific alternative date within the window"
  - type: contains
    keywords: ["booking window", "7-day"]
```

**The LLM proposes, the user disposes.** The proposed assertions are suggestions, not final. The user reviews and edits them in the dashboard task editor before the task is activated.

### 4.2a Failure Modes

| Failure mode | Behavior | User sees |
|-------------|----------|-----------|
| LLM API unavailable (no key, rate limited, timeout) | Task draft created with a default `contains` assertion using the top 3 keywords extracted from the session title. Draft is marked `llm_judge_unavailable: true` | "LLM judge unavailable — review assertions manually" badge on the draft |
| Clustering produces 0 groups (all sessions same topic) | All qualifying sessions returned as individual drafts, up to `--limit` | All drafts listed, no clustering applied |
| Session has no first user message (first message is tool call or system) | Session skipped with a warning in the CLI output | "Skipped session X — no user message found" |
| Source session deleted from state.db between suggest-tasks and dashboard review | Modal shows "Original conversation no longer available (session deleted)" | Graceful message, not an error |
| LLM proposes invalid YAML assertions | Draft saved with `assertions: []` and `llm_judge_unavailable: true` | "No assertions proposed — edit manually" badge |

### 4.3 Task Draft Schema

```yaml
id: history-spgg-booking-20260710
name: "SPGG tennis court booking within 7-day window"
description: "Agent must identify booking window constraints and propose valid dates"
prompt: |
  The SPGG tennis court booking for July 20 failed. The system redirected to
  /appointment/4 instead of /appointment/4/info. Why did this happen and what
  are the next steps?
assertions:
  - type: llm_judge
    criteria: "Response must identify the 7-day booking window as the root cause and propose a specific alternative date within the window"
  - type: contains
    keywords: ["booking window", "7-day"]
timeout: 60
trials: 2
category: "operations"
difficulty: "medium"
source_session: "20260710_061127_3191ef56"
built_in: 0
```

### 4.4 Fields

| Field | Source | Notes |
|-------|--------|-------|
| `id` | Auto-generated: `history-{topic-slug}-{date}` | Unique, traceable to source |
| `name` | LLM-generated from session title | Human-readable |
| `description` | LLM-generated | 1-sentence summary of what the task tests |
| `prompt` | First user message (cleaned) | The actual task |
| `assertions` | LLM-proposed | User reviews and edits |
| `timeout` | Default 60s | User can adjust |
| `trials` | Default 2 | Lower than generic (10) — these are real prompts, more expensive |
| `category` | LLM-assigned | One of: reasoning, coding, extraction, tool_use, instructions, operations |
| `difficulty` | LLM-assigned | easy / medium / hard |
| `source_session` | Session ID from state.db | Traceability — user can review the original conversation |
| `built_in` | 0 | User-defined, not built-in |

---

## 5. CLI

```
observeco canary suggest-tasks [--agent AGENT] [--limit N] [--source SOURCE] [--approve-all]
```

- `--agent` — Agent profile to mine sessions for (default: `default`)
- `--limit` — Max number of task drafts to propose (default: 10)
- `--source` — Session source filter (default: `telegram`; can also be `cli`, `cron`, `all`)
- `--approve-all` — Skip review, auto-approve all drafts (not recommended — defeats ground truth)

**Output:**

```
🔍 Mining 2606 sessions from ~/.hermes/state.db...
   Filtered to 47 telegram sessions (3+ messages, last 30 days)
   Clustered into 10 topic groups

📋 Task Drafts:

  1. SPGG tennis court booking within 7-day window
     Source: 20260710_061127_3191ef56 (343 messages)
     Assertions: llm_judge, contains
     Category: operations · Difficulty: medium

  2. Token optimizer dashboard status inquiry
     Source: 20260708_062252_81b7d6d6 (271 messages)
     Assertions: llm_judge, contains
     Category: reasoning · Difficulty: medium

  ...

  10. Error handling in Node.js streams
     Source: 20260707_090632_abf3ea8f (457 messages)
     Assertions: llm_judge, regex
     Category: coding · Difficulty: hard

✅ 10 task drafts saved as pending review.
   Review in dashboard: Capability → Task Library → Pending
   Or approve all: observeco canary suggest-tasks --approve-all
```

---

## 6. Dashboard Integration

### 6.1 Pending Tasks Section

In the existing Task Library section (obs-spec-055), add a "Pending Review" tab/section:

- Shows task drafts from `suggest-tasks` that haven't been approved
- Each draft shows: name, source session link, proposed assertions, prompt preview
- Actions: **Approve** (saves as active task), **Edit** (opens task editor), **Reject** (deletes draft)

### 6.1a Pending Tasks Section — State Table

| State | What renders | User sees |
|-------|-------------|-----------|
| **Loading** | Skeleton list (3 grey items) with "Generating task drafts..." | Placeholder while backend processes |
| **Empty** | "No pending task drafts. Run `observeco canary suggest-tasks` to generate drafts from your agent's conversation history." | Actionable empty state with CLI command |
| **Populated** | List of draft cards with name, source link, assertions, prompt preview, Approve/Edit/Reject buttons | Full interactive list |
| **Error** | "Failed to generate task drafts — LLM API unavailable. Check your API key configuration." | Error message with remediation |

### 6.1b Source Session Modal — State Table

| State | What renders | User sees |
|-------|-------------|-----------|
| **Loading** | "Loading conversation..." spinner | Placeholder while reading state.db |
| **Populated** | First 5 messages from the source session, formatted as chat bubbles (user/assistant alternating) | Conversation context for reviewing assertions |
| **Session deleted** | "Original conversation no longer available (session deleted)" | Graceful message, not an error |
| **Error** | "Could not load conversation — database error" | Error message with remediation |

### 6.2 Source Session Link

Each history-based task has a `source_session` field. The dashboard shows a "View original conversation" link that opens a modal with the first 5 messages from the source session (read from `state.db`). This gives the user context for reviewing the proposed assertions.

### 6.3 Two-Tier Display

The canary overview card shows two scores:
- **Generic:** X% (10 built-in tasks)
- **User-defined:** Y% (N tasks) — only shown if user-defined tasks exist

---

## 7. Canary Runner Integration

The daily canary (3am cron) runs **both** tiers:

1. **Generic tasks** (built_in=1) — existing 10 tasks, `trials=10`, canary model from `OBSERVECO_CANARY_MODEL`
2. **User-defined tasks** (built_in=0) — approved history-based tasks, `trials=2`, same canary model

User-defined tasks use the **Hermes adapter** (with `-p default` — agent profile, skills, tools, SOUL.md), not the DirectModelAdapter. This is critical: the original conversations used tools, so the benchmark must also use tools.

**Design constraint — two adapters per run:** The current `CanaryRunner` uses a single adapter per `run()` call. To support two tiers with different adapters, the runner must execute two passes:

```
Pass 1: generic tasks → existing adapter chain (DirectModelAdapter or HermesAdapter)
Pass 2: user-defined tasks → HermesAdapter with -p default
```

The `built_in` column on `canary_tasks` filters which pass each task belongs to. The runner's `run()` method will accept an optional `adapter_override` parameter for the second pass. If no user-defined tasks exist, the second pass is skipped.

**ponytail:** User-defined tasks run with the agent profile but the canary model (e.g., `deepseek-v4-flash`), not the agent's production model. Ceiling: if the canary model can't use a specific tool that the original conversation required, the task will fail for model-capability reasons, not harness reasons. Upgrade path: per-task model override field (already supported in the schema) — user can set a stronger model for tool-heavy tasks.

---

## 8. Scoring

| Assertion type | Used for | Scoring method |
|----------------|----------|----------------|
| `llm_judge` | Most user-defined tasks | LLM-as-a-Verifier (1-20 scale, K=3) per obs-spec-057 |
| `contains` | Supplementary keyword checks | Keyword presence in output |
| `regex` | Pattern matching | Regex match |
| `exact_match` | Simple factual tasks | Exact string match after strip |

**User-defined tasks default to `llm_judge`** because the success criteria are qualitative ("correctly identified the root cause", "proposed a valid alternative"). The LLM judge compares the new response against the user-approved criteria.

When no `OBSERVECO_LLM_API_KEY` is configured, falls back to the algorithmic judge (extracts logic tokens from criteria, checks for presence in response) per obs-spec-057's fallback design.

---

## 9. Lifecycle

```
suggest-tasks → drafts saved as pending
                   ↓
User reviews in dashboard
                   ↓
         ┌── Approve → task activated (built_in=0, runs in daily canary)
         ├── Edit    → user modifies assertions/prompt → Approve
         └── Reject  → draft deleted
                   
Active user-defined tasks:
  - Run in daily canary alongside generic tasks
  - Drift detected on per-task basis (same as generic)
  - User can regenerate drafts anytime (old tasks stay until deleted)
  - User can manually delete stale tasks
```

**Staleness handling:** The user controls when to refresh. The system doesn't auto-expire history-based tasks. If a task becomes irrelevant (feature shipped, process changed), the user deletes it. The `suggest-tasks` command can be run periodically to propose new drafts reflecting recent work.

---

## 10. What We Don't Do

- **Auto-approve tasks.** The human review step is the ground truth anchor. `--approve-all` exists for testing but is not recommended.
- **Use past responses as expected output.** Past responses are context for assertion generation, not ground truth.
- **Run user-defined tasks on the grid.** The grid uses `DirectModelAdapter` (no tools). User-defined tasks need the Hermes adapter (with tools). Grid is for model comparison; user-defined tasks are for agent quality.
- **Mine cron/cli/subagent sessions.** These aren't real user interactions. Telegram sessions only (configurable via `--source`).
- **Auto-regenerate tasks.** Staleness is a user decision, not a system decision.

---

## 11. File Changes

| File | Change |
|------|--------|
| `src/observeco/capability/history_tasks.py` | New — session mining, clustering, LLM assertion proposal |
| `src/observeco/cli.py` | Add `canary suggest-tasks` command |
| `src/observeco/dashboard/routes/capability.py` | Add pending tasks section, source session modal |
| `src/observeco/capability/canary.py` | Modify runner to execute two passes: built_in=1 via existing adapter, built_in=0 via HermesAdapter with `-p default`. Add `adapter_override` parameter to `run()`. |
| `src/observeco/db.py` | Add migration to add `source_session` column to `canary_tasks` table |

---

## 12. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task proposal generation | < 30s for 10 drafts | CLI execution time |
| Task draft YAML validity | ≥90% of selected sessions produce valid YAML | `COUNT(valid_drafts) / COUNT(selected_sessions)` |
| User-defined task run | < 3 min for 5 tasks × 2 trials | Canary execution time |
| Assertion quality | LLM judge inter-rater agreement > 0.7 | K=3 judge consistency |
| Drift signal | User-defined tasks detect drift that generic misses | Per-task drift comparison |