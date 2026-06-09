# Agent Signal Infrastructure v1 (formerly obs-spec-019) — Implementation Spec

**Spec ID:** obs-spec-019
**Author:** Hound (per Sean direction 2026-06-09)
**Status:** Approved
**Location:** `specs/obs-spec-019-agent-signal-infrastructure-v1.md`
**Derived from:** Debate between Hound × Kepler (2026-06-09) — convergence on feedback protocol architecture with 3 unresolved implementation gaps.

---

## §1 One-Liner

The debate converged on a feedback protocol (4 categories, exception-based emission, 3 surfaces, sticky uncertainty propagation). Three concrete implementation gaps remain that need design decisions before building: **session-scoped state tracking**, **limitation bag compression**, and **process transparency capture**. This spec resolves those gaps for v1.

---

## §2 Problem

### §2.1 What's Converged (not re-debating)

| Dimension | Decision | 
|-----------|----------|
| **Protocol shape** | 4 categories: Limitation, Confidence Calibration, Boundary Notification, Process Transparency |
| **Emission model** | Exception-based, not constant. Emit only on new limitation, confidence deviation, or delegation uncertainty |
| **Surfaces** | 3-tier: metadata (always-on, invisible), conversational (1-2 lines on exception), summary (session-end markdown debrief, opt-in) |
| **Uncertainty in delegation** | Sticky — each hop resolves or propagates. Silent drops = protocol violation |

### §2.2 Three Unresolved Implementation Gaps

**Gap 1 — Session-scoped state tracking.** Exception-based emission requires the agent to know "did I already flag this limitation in this session?" Current agents are stateless per-turn. There is no session-scoped registry of emitted feedback.

**Gap 2 — Limitation bag compression function.** "Compress by materiality at presentation level" is a design principle, not an algorithm. What does compression actually do? Dedup identical flags across hops? Summarize 5 Pragma-level uncertainties into "3 minor tool variances"?

**Gap 3 — Process transparency capture.** The agent needs to emit what it actually did — sources consulted, reasoning steps, alternatives considered, tools called. No structured process log exists today.

---

## §3 Requirements

1. **Session feedback registry** — a per-session file that tracks which feedback events have been emitted, to enable dedup-at-source
2. **Compression rules** — deterministic algorithm for compressing N raw limitation flags into N' surfaced items, with tier-preserving behavior (Critical never compressed into minor)
3. **Process transparency log** — structured per-session file capturing: sources read, tools called, reasoning steps, alternatives considered/rejected, confidence per step
4. **All three surfaces populated** — metadata field on outbound payloads, conversational inline on exception, session-end markdown summary
5. **No UI framework dependency** — v1 layers on existing signal infrastructure. Markdown files + JSON metadata payloads only.

---

## §4 Architecture

### §4.1 Session Feedback Registry

```
~/.hermes/state/feedback_registry/<session_id>.json
```

**Schema:**
```json
{
  "session_id": "hound_20260609_analysis",
  "agent": "hound",
  "started_at": "2026-06-09T08:00:00+08:00",
  "emitted_flags": [
    {
      "flag_id": "lim_tool_timeout_001",
      "category": "limitation",
      "fingerprint": "limitation:stripe_auth_failure",
      "tier": "critical",
      "emitted_at": "2026-06-09T08:15:00+08:00",
      "surface": "metadata",
      "resolved": false,
      "resolved_at": null,
      "propagated_from": null,
      "propagated_to": ["flag_id_of_downstream_uncertainty"]
    }
  ],
  "resolved_at": null,
  "open_uncertainty_chain": [
    {
      "hop": 2,
      "from": "kepler",
      "topic": "revenue_projection",
      "confidence": 0.65,
      "resolved": false
    }
  ]
}
```

**Ownership:** The ACPS session runner creates the empty registry template at session start (before the LLM prompt is built). The LLM writes the full registry file exclusively — it reads the existing file for dedup checks and writes updated JSON after each flag emission. The session runner never touches the file after creation. At session end, the session runner reads the final registry to populate summary surfaces.

**Dedup mechanism:** Each flag has a `fingerprint` — the full `category + ":" + detail_slug` string (not a hash). Before emitting a limitation, the LLM checks: does this fingerprint already exist in the registry? If yes, skip. If no, append. Hash optimization deferred to v2 — using full plaintext avoids collision risk.

**Resolution semantics:** A flag resolves when the condition that caused it no longer holds. The LLM checks on each subsequent turn whether prior limitations still apply. If `resolved_at` is set, the flag is excluded from summary surfaces but retained in metadata for audit.

**Cross-session (v2 gap):** Each session starts clean — resolved flags do not persist. This is intentional for v1 but creates alarm fatigue: the same recurring limitation (e.g., a Stripe auth routing quirk) flags as Critical in every session. V2 should add a persistent `known_limitations.json` at `~/.hermes/state/known_limitations.json` with schema: `{ fingerprint, category, tier, first_seen, last_seen, occurrence_count, resolved }`. Session-start loads this and pre-populates the registry. Resolved items (confirmed by 2 consecutive sessions without recurrence) archived. The v1 schema does not prevent this addition — the `fingerprint` field provides the natural join key.

**Lifecycle:** Created at session start. Destroyed when the session-end summary is written and delivered. Survives session runner restarts (disk-backed, not in-memory).

**Crash recovery:** JSON file writes are not atomic on most filesystems. The LLM writes the registry using a write-to-temp-then-rename pattern: write to `~/.hermes/state/feedback_registry/<session_id>.json.tmp`, then `mv` to `<session_id>.json`. The `mv` (rename) is atomic on the same filesystem. If the session runner reads the registry and finds corrupt JSON (e.g., from a prior crash before rename completed), it creates a fresh empty registry and logs a warning — empty registry is always better than corrupt state.

### §4.2 Limitation Bag Compression

**Three compression passes, applied in order:**

**Pass 1 — Exact dedup.** Same fingerprint → collapse into one entry with `count: N`. Emitted once, not N times. This handles multi-hop where the same limitation propagates unchanged.

**Pass 2 — Tier-preserving summarization.** Within each tier (Critical, Major, Minor, Pragma), group flags by shared root cause:

| Tier | Compression rule | Example |
|------|-----------------|---------|
| Critical | Never compress. Every Critical flag emitted individually. | "Stripe API returned auth failure" → individual flag |
| Major | Group by root cause. Max 1 summary row per root cause + count. | "3 tool timeout errors on weather API" → 1 row |
| Minor | Group by category. Max 2 summary rows per minor category + count. | "5 minor parsing warnings across 3 tools" → 2 rows max |
| Pragma | Single summary row per 5 identical-type flags. If <5, dropped at human surface (retained in metadata). | "12 timestamp formatting inconsistencies" → "Minor formatting variances noted" |

**Pass 3 — Size-bounded output.** The surfaced list (conversational + summary surfaces) is capped at 5 items total. Exception: if all remaining items after Pass 2 are Critical, the cap is raised to accommodate all Critical flags. The 5-item cap applies only when mixed-tier output exists. Rationale: suppressing a Critical flag is worse than a longer summary. Log a warning when cap is exceeded so we can tune thresholds. If compression passes produce >5 under the normal rule, the lowest-tier items are dropped from the human-visible surfaces but retained in the metadata block. The summary surface includes a `"N more items in metadata"` footer.

**Tie-breaking within same tier:** When items must be dropped and multiple items share the same lowest tier (e.g., 7 Major items, must drop 2), sort within the tier by emission timestamp (newest first) and drop the newest. Rationale: the OLDEST flag in the chain is most likely the root cause — dropping it while keeping downstream symptoms gives an incomplete picture. Keeping the oldest preserves the root-cause-first invariant. This is deterministic across runs.

**Zero-item edge case:** If zero items survive compression for human-visible surfaces, emit a single placeholder: `[No significant issues in this session. N minor items logged in metadata.]` This prevents silent-zero confusion where a human reading empty feedback might assume the system is broken.

**Invariant:** Compression never drops a Critical flag from any surface. Critical flags always appear in both human-visible and metadata surfaces.

### §4.3 Process Transparency Log

```
~/.hermes/state/process_log/<session_id>.jsonl
```

One JSONL entry per significant action:

```jsonl
{"ts": "2026-06-09T08:10:00+08:00", "type": "source_load", "detail": "consulted AGENTS.md for kepler identity", "tokens": 312}
{"ts": "2026-06-09T08:11:00+08:00", "type": "tool_call", "detail": "search_second_brain(topic: feedback protocol, query: limitation propagation)", "result_count": 3, "latency_ms": 1200}
{"ts": "2026-06-09T08:12:00+08:00", "type": "reasoning_step", "detail": "evaluated 3 alternatives: (1) direct write to inbox, (2) signal via router, (3) wake flag", "selected": "direct write (fastest path for ACPS)", "rejected": ["router (1m latency too high)", "wake flag (no payload container)"]}
{"ts": "2026-06-09T08:13:00+08:00", "type": "confidence", "detail": "confidence in tool record retrieval: 0.85", "basis": "3 of 3 queries returned consistent results"}
```

**Collection mechanism:** The ACPS session runner pre-pends a `process_log` instruction to the prompt: "For each significant action you take, write a structured JSONL line to the process log at `<path>`. Include: timestamp, action type, detail, and relevant metrics (tokens, latency, result count)." The LLM writes to the file mid-session.

**Alternative (post-hoc extraction):** If mid-session writing adds too much overhead or prompt bloat, fall back to a post-session extraction prompt: the LLM's full transcript is fed to a secondary extraction that produces the JSONL. This is less accurate (reasoning steps are implicit in the transcript, not explicit) but zero impact on session cost.

**v1 recommendation:** Post-hoc extraction. It costs one extra summarization pass but adds zero tokens to every production session. Only migrate to mid-session writing if post-hoc quality is insufficient.

**Post-hoc extraction validation:** After the extraction prompt produces the JSONL file, a validation gate runs before any downstream consumer reads it:
1. Every line must parse as valid JSON (skip malformed lines, log warning with line count)
2. At least 3 of 4 entry types must be present (`source_load`, `tool_call`, `reasoning_step`, `confidence`)
3. If validation fails, log a warning in the session runner and produce a minimal placeholder summary instead of garbage: `[Process log extraction failed — post-hoc quality gate did not pass. Raw summary: X lines, Y skipped. Consider retrying with mid-session flag write.]`

### §4.4 Surface Population

**Metadata surface (always-on):**
A `feedback` field appended to every outbound signal payload:

```json
{
  "payload": { ... },
  "feedback": {
    "limitations": [ { "tier": "minor", "fingerprint": "...", "detail": "..." } ],
    "confidence": { "overall": 0.88, "per_step": [...] },
    "boundaries": [ "max_tool_calls: 3 of 5 used" ],
    "process": { "sources_consulted": 3, "tools_called": 2, "reasoning_steps": 4 }
  }
}
```

**Conversational surface (on exception):**
When a new limitation of tier Critical or Major is emitted, the agent appends 1-2 natural language sentences to its primary response, prefixed with a subtle marker:

> *[Note: Confidence in the Stripe auth status is low (0.45). The last successful check was 12 hours ago. Consider verifying manually.]*

**Per-session throttle:** Maximum 3 conversational notes per session. Beyond that, new Critical/Major flags are recorded in the metadata surface only, with a footnote: `[+N flags in metadata — conversational surface saturated]`. Rationale: a session where every turn generates a new Critical limitation is noise, not signal. The human is already aware of the problem from the first 3 notes. Additional notes after the throttle trigger degrade trust in the feedback system itself (user perception: "it's broken AND it won't stop telling me it's broken"). The 3-threshold is configurable via a feedback_conversational_limit config key for environments that want more/less verbosity. Setting to 0 disables conversational surface entirely (metadata-only mode).

**Summary surface (session-end, opt-in):**
A markdown document written to `~/.hermes/state/feedback_summary/<session_id>.md`:

```markdown
# Session Feedback Summary — hound_20260609_analysis

**Category counts:** 1 limitation · 2 confidence flags · 0 boundaries · 4 process steps

## Limitations
- 🔴 **Critical:** Stripe API auth check failed (propagated from kepler — unresolved)
- 🟡 **Major:** Weather API timed out on 3 of 5 calls

## Confidence
| Step | Confidence | Basis |
|------|-----------|-------|
| Stripe auth | 0.45 | Last check 12h old |
| Tool record retrieval | 0.85 | 3/3 queries consistent |

## Process Trace (sources & tools)
| Action | Detail | Outcome |
|--------|--------|---------|
| Source load | AGENTS.md (kepler identity) | 312 tokens |
| Tool call | search_second_brain(protocol) | 3 results |
| Reasoning | 3 alternatives evaluated | Direct write selected |

*Full metadata available in signal payload. N additional pragma-level items not shown.*
```

---

## §5 Implementation Phases

### Phase 1 — Process Transparency Log (post-hoc extraction)

**Goal:** Ship the simplest path first — extract process transparency from existing session transcripts. No session runner changes.

**Files to create:**
- `~/.hermes/state/process_log/` — directory (created if absent)
- Extraction prompt template (agents can reference regardless of profile)

**Verification:** A test session produces a valid process_log JSONL file. At minimum: source_load, tool_call, reasoning_step, and confidence entries present.

**Rollback:** Delete the extraction prompt reference. Log files are inert — no system dependency.

---

### Phase 2 — Session Feedback Registry

**Goal:** Create session-scoped state so exception-based emission has a dedup mechanism.

**Files to create:**
- `~/.hermes/state/feedback_registry/` — directory
- ACPS session runner integration: create empty registry at session start, inject `<feedback_registry>` block into prompt preamble
- Registry read/write instructions in prompt preamble

**Verification:** Run a test session with 2 consecutive turns requesting the same API. The limitation flag appears once, not twice.

**Rollback:** Remove registry injection from prompt preamble. Delete registry files.

---

### Phase 3 — Limitation Bag Compression

**Goal:** Implement the 3-pass compression algorithm so summary surfaces are readable.

**Note:** This is a pure function — can be tested independently without any session runner changes. Can ship as a standalone utility as soon as Phase 1 provides real test data. No need to gate on Phase 4. The compressed output can be validated against known inputs independently.

**Files to create:** `~/.hermes/state/compression/compress.py` — standalone Python script, not an agent dependency. Or implement as an inline prompt instruction.

**Design decision needed:** Algorithm in code (deterministic, testable) vs algorithm in prompt (simpler but no dependency). **Recommendation:** Python utility for v1. Rationale: (a) compression is a pure function — deterministic across all model providers, even non-LLM shells. (b) A Python script is testable with known inputs: feed 12 flags, assert output ≤5, assert all Critical retained, assert Pragma <5 dropped. (c) Prompt-level means every session pays the token cost of re-deriving the same logic, with model-dependent output variance. (d) The trigger point (end-of-session) is well-defined: the script runs after the registry is finalized, before surfaces are populated. Implement as `~/.hermes/state/compression/compress.py`, callable with a registry JSON path. Prompt-level is a valid fallback only if Python execution is unavailable.

**Verification:** Feed a known set of 12 flags (3 Critical, 4 Major, 3 Minor, 2 Pragma) through the compressor. Verify output ≤5 items, all Critical flags retained, Pragma with <5 count dropped from human surface.

**Rollback:** Remove compression instructions from prompt. All flags pass through raw.

---

### Phase 4 — Metadata + Conversational + Summary Surface Wiring

**Goal:** All three surfaces populated and delivered.

**Files to create:**
- Metadata `feedback` field appended to every outbound signal in the ACPS session writer
- Summary markdown written to `~/.hermes/state/feedback_summary/<session_id>.md`
- Conversational emission logic in prompt instructions (append 1-2 lines on Critical/Major new-limitation events)

**Verification:** A test session produces: (1) outbound signal carrying `feedback` field, (2) summary markdown file with all sections populated, (3) conversation response includes a *[Note: ...]* line for a new Critical limitation.

**Rollback:** Remove feedback field from signal writer. Delete summary directory.

---

## §6 Implementation Order

### First — Phase 1 (Process Transparency, post-hoc)
No session runner changes. Lowest risk. Produces immediately useful artifact.

### Second — Phase 2 (Feedback Registry)
Requires ACPS session runner modification (prompt injection). Test on Hound first (lowest stakes).

### Third — Phase 3 (Compression)
Pure logic, independent of all other phases. Can ship as standalone utility as soon as Phase 1 provides real test data. The compressed output can be validated against known inputs without waiting for Phase 4.

### Fourth — Phase 4 (Surfaces)
Depends on Phases 1-3 all working. Metadata field depends on registry (Phase 2). Summary depends on process log (Phase 1) + compression (Phase 3). Conversational depends on registry (Phase 2).

---

## §7 Rollback Plan Per Phase

| Phase | Rollback |
|-------|----------|
| Phase 1 | Delete process log extraction instructions from prompts. Log files are inert. |
| Phase 2 | Remove registry injection from ACPS runner template. Delete registry files. |
| Phase 3 | Remove compression instructions from prompt. All flags pass through raw. |
| Phase 4 | Remove feedback field from signal writer. Delete summary directory. Remove conversational emission instructions. |

---

## §8 Risks & Mitigations

|| Risk | Likelihood | Impact | Mitigation |
||------|-----------|--------|------------|
|| **Prompt bloat from registry injection** | Medium | Medium | Registry block is ~200 chars + N×100 per flag. Cap registry at 20 flags max. Beyond 20, truncation priority (first to drop): Pragma → Minor → Major. Critical flags are never truncated. |
|| **LLM doesn't reliably write to registry mid-session** | Medium | High | Phase 1 fallback: post-hoc extraction exists. If mid-session writing is unreliable, fall back to post-hoc for the registry as well. |
|| **Compression drops a Critical flag** | Low | High | Invariant in Phase 3 spec: Critical flags never compress. Test with adversarial input (all Critical) before production. |
|| **Fingerprint collision suppresses genuine limitation** | Low | Medium | De-duplication uses full plaintext `category:detail_slug` as key (not a hash). Hash optimization deferred to v2 — collision impossible with plaintext keys. |
|| **Process log JSONL parsing errors** | Low | Low | Each line is independent. Parse errors skip one line, don't break the rest. Fallback: show raw lines. JSONL append is not atomic per-line — individual lines may be partial after a crash; the parser already handles this by skipping malformed lines. |
|| **Metadata field adds noise to every signal** | Low | Medium | Metadata field is 2-5% of payload size. If performance impact materializes, gate on `feedback_enabled: true` config flag (default: off). |
|| **Fingerprint canonicalization drift** | Medium | Medium | Fingerprints are LLM-written — the same issue may produce `stripe_auth_failure` in one session and `stripe_api_authentication_error` in another. Mitigation: (a) canonical slug taxonomy in prompt preamble, (b) post-hoc fuzzy-match normalization, (c) v2 slug registry. |

---

## §9 Verification Checklist (Post-Build)

- [ ] Phase 1: A test session produces a process_log JSONL with ≥3 entry types (source_load, tool_call, reasoning_step)
- [ ] Phase 2: Two consecutive turns requesting the same API produce one limitation flag, not two
- [ ] Phase 3: 12 input flags compress to ≤5 output items. All Critical tiers retained. Pragma <5 dropped from human surface.
- [ ] Phase 4: Outbound signal includes `feedback` field. Summary markdown has all 4 sections. Conversational surface fires on Critical/Major limitation.
- [ ] Rollback: Each phase rollback verified — no stale files, no orphaned prompt instructions.
- [ ] Edge case: Zero-limitation session produces empty feedback with no errors.
- [ ] Edge case: Session interrupted mid-write — registry file is valid JSON (file write is atomic).

---

## §10 Lifecycle & Hygiene

**Mandatory:** Every artifact created by the feedback protocol must have a documented deletion policy. Unbounded disk growth degrades search and creates operational debt.

### §10.1 Archival & Deletion Windows

| Artifact | Path | Archive after | Delete after | Rationale |
|----------|------|--------------|-------------|-----------|
| Process log (JSONL) | `~/.hermes/state/process_log/` | 7 days (tarball + rename) | 30 days | Most recent week for debugging; historical logs rarely valuable after 30 days |
| Feedback registry (JSON) | `~/.hermes/state/feedback_registry/` | N/A — deleted at session end per §4.1 | Session end | Registry is purely session-scoped per spec; enforcing this prevents orphan accumulation |
| Summary markdown | `~/.hermes/state/feedback_summary/` | 14 days | 60 days | Summaries are human-readable — users may reference them for ~2 weeks. 60-day retention before deletion gives a safety margin |
| Known limitations (v2) | `~/.hermes/state/known_limitations.json` | N/A | N/A — single file, indefinite | Persists across sessions by design. Entries archived internally when `resolved` is confirmed by 2 consecutive clean sessions |

### §10.2 Enforcement Mechanism

A cron job runs daily at 02:00 local time:

```bash
# Archive process logs older than 7 days
find ~/.hermes/state/process_log/ -name '*.jsonl' -mtime +7 \
  -exec tar rf /tmp/process_log_archive.tar {} + \
  -delete

# Delete archived logs older than 30 days
find ~/.hermes/state/process_log/ -name '*.jsonl' -mtime +30 -delete

# Delete summaries older than 14 days (direct, no archive)
find ~/.hermes/state/feedback_summary/ -name '*.md' -mtime +14 -delete
```

**Registration:** Hook this into the existing `hermes cron create` pattern (see GS-011) so it survives host reboots without manual setup.

### §10.3 Disaster Recovery

- **Accidental deletion before summary delivery:** The session runner holds the final registry in memory until summary is written. If summary writing fails, the registry is preserved on disk for retry. The cron job's mtime-based check gives a 24-hour window before archiving applies — a failing summary delivery would trigger alerts long before then.
- **Artifact explosion from a runaway session:** A single session producing 1000+ process_log entries (e.g., infinite loop) is capped by the session runner's turn limit. Post-session, the single large file is archived/deleted on the normal schedule. No special handling needed.
- **Cron failure:** If the daily cron skips a run, the mtime-based checks catch up on the next run. The deletion windows are generous enough (7/14/30/60 days) that a single missed day is harmless. Two consecutive missed days → flag for human review.