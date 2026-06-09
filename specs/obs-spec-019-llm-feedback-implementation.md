# obs-spec-019: LLM-to-Human Feedback Protocol — Implementation Spec

**Spec ID:** obs-spec-019
**Author:** Hound (per Sean direction 2026-06-09)
**Status:** Approved
**Location:** `specs/obs-spec-019-llm-feedback-implementation.md`
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
      "fingerprint": "hash(limitation_type + detail_slug)",
      "emitted_at": "2026-06-09T08:15:00+08:00",
      "surface": "metadata",
      "resolved": false
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

**Ownership:** The ACPS session runner creates the registry at session start (before the LLM prompt is built). The LLM reads it via a prompt injection (`<feedback_registry>...</feedback_registry>`) and appends flags as it emits them. The session runner writes the file; the LLM reads and appends.

**Dedup mechanism:** Each flag has a `fingerprint` — the full `category + ":" + detail_slug` string (not a hash). Before emitting a limitation, the LLM checks: does this fingerprint already exist in the registry? If yes, skip. If no, append. Hash optimization deferred to v2 — using full plaintext avoids collision risk.

**Resolution semantics:** A flag resolves when the condition that caused it no longer holds. The LLM checks on each subsequent turn whether prior limitations still apply. If `resolved_at` is set, the flag is excluded from summary surfaces but retained in metadata for audit. Cross-session: resolved flags do not persist — each session starts clean.

**Lifecycle:** Created at session start. Destroyed when the session-end summary is written and delivered. Survives session runner restarts (disk-backed, not in-memory).

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

**Design decision needed:** Algorithm in code (deterministic, testable) vs algorithm in prompt (simpler but model-dependent). **Recommendation:** Prompt-level for v1. The 3-pass logic is simple enough to express as instructions. Only extract to Python if we need deterministic behavior across model providers.

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

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Prompt bloat from registry injection** | Medium | Medium | Registry block is ~200 chars + N×100 per flag. Cap registry at 20 flags max. Beyond 20, truncation priority (first to drop): Pragma → Minor → Major. Critical flags are never truncated. |
| **LLM doesn't reliably write to registry mid-session** | Medium | High | Phase 1 fallback: post-hoc extraction exists. If mid-session writing is unreliable, fall back to post-hoc for the registry as well. |
| **Compression drops a Critical flag** | Low | High | Invariant in Phase 3 spec: Critical flags never compress. Test with adversarial input (all Critical) before production. |
| **Fingerprint collision suppresses genuine limitation** | Low | Medium | De-duplication uses full plaintext `category:detail_slug` as key (not a hash). Hash optimization deferred to v2 — collision impossible with plaintext keys. |
| **Process log JSONL parsing errors** | Low | Low | Each line is independent. Parse errors skip one line, don't break the rest. Fallback: show raw lines. JSONL append is not atomic per-line — individual lines may be partial after a crash; the parser already handles this by skipping malformed lines. |
| **Metadata field adds noise to every signal** | Low | Medium | Metadata field is 2-5% of payload size. If performance impact materializes, gate on `feedback_enabled: true` config flag (default: off). |

---

## §9 Verification Checklist (Post-Build)

- [ ] Phase 1: A test session produces a process_log JSONL with ≥3 entry types (source_load, tool_call, reasoning_step)
- [ ] Phase 2: Two consecutive turns requesting the same API produce one limitation flag, not two
- [ ] Phase 3: 12 input flags compress to ≤5 output items. All Critical tiers retained. Pragma <5 dropped from human surface.
- [ ] Phase 4: Outbound signal includes `feedback` field. Summary markdown has all 4 sections. Conversational surface fires on Critical/Major limitation.
- [ ] Rollback: Each phase rollback verified — no stale files, no orphaned prompt instructions.
- [ ] Edge case: Zero-limitation session produces empty feedback with no errors.
- [ ] Edge case: Session interrupted mid-write — registry file is valid JSON (file write is atomic).