# ObserveCo Plugin Ideas — Master Document

Catalog of self-evolution mechanisms from the Hermes/ObserveCo ecosystem
that are candidates for extraction as standalone Hermes plugins.

**Default answer: skip. Each entry must argue why it deserves to exist.**

---

## Ranking

| Rank | Plugin | Original? | Viral Potential | Extraction Effort | Status |
|------|--------|-----------|----------------|-------------------|--------|
| 1 | Chisel (Trim + Drift) | ✅ | High | Low | **Built v0.2** |
| 2 | Anomaly Detection | ✅ | High | Low | **Built v0.1** |
| 3 | Prevention Skill Auto-Creation | ✅ | Medium | High | Pending |
| 4 | Context Quality Preflight | ❌ ProofAgent | Medium | Low | **Built v0.1** |
| 5 | Harness D1-D6 Tagger | ❌ MemoHarness | Medium | Medium | Pending |
| 6 | Pulse Check (liveness + crash classification) | ✅ | Medium | Medium | Pending |
| 7 | Ecosystem Gap Scanner | ✅ | Low | Medium | Pending |
| 8 | Turn Capture | ✅ | Low | Low | Pending |
| 9 | Inbox Correlation | ✅ | Low | Medium | Pending |
| 10 | Efficiency Metrics (11 metrics) | ✅ | Medium | Medium | Deferred → Chisel Pro v0.3 |

---

## 1. Chisel — System Prompt Decomposition + Drift Detection

**What it does:** Decomposes any agent's system prompt into 5 functional
components (identity, skills, memory, tools, guidance), estimates
per-component token costs, and tracks how those components drift over time.

**Why it's #1:**
- Universal pain — every agent operator has prompt bloat, nobody knows which section costs the most
- Zero external deps — regex + token estimation + SQLite, no LLM, no API keys
- Original — no paper source, the 5-component decomposition is ours
- Instant "aha" screenshot — "Memory is 42% of your context and grew 31% this week"
- Inherently shareable — the breakdown table is a tweet

**Source files:**
- `src/observeco/chisel/trim.py` (823 lines) — decomposition + token estimation
- `src/observeco/chisel/drift.py` (118 lines) — 7-day rolling drift detection
- `src/observeco/chisel/config_scanner.py` — config hygiene checks
- `src/observeco/chisel/skill_compress.py` — skill-specific compression

**Competitor landscape:**
- LLMLingua (Microsoft, 6.2k★) — compresses raw text, no per-component breakdown, stale 7mo
- Mem0 (56k★) — extractive memory, no prompt decomposition
- Nothing does per-component token decomposition + drift tracking — **greenfield**

**Spec:** `./chisel/SPEC.md`

---

## 2. Anomaly Detection

**What it does:** Scans existing agent data for 4 anomaly types:
- `no_tools`: Agent session had API calls but zero tool invocations
- `high_cost`: Token cost spike >3σ above 7-day rolling average
- `long_gaps`: Gap between consecutive pulses >15 minutes
- `retry_loops`: Same error type for same agent >3 times in 10 minutes

**Why it's #2:**
- "Your agent stopped using tools" is a great alert
- Pure SQL, no LLM, no external deps
- Original — no paper source

**Source files:**
- `src/observeco/anomaly/__init__.py` (233 lines)

**Extraction notes:**
- Needs a generic data source (currently reads ObserveCo's pulse_log + token_logs tables)
- Plugin hook: `on_session_end` → check anomalies → emit alert

---

## 3. Prevention Skill Auto-Creation

**What it does:** After healing an agent failure, extracts an error signature
(normalized — strips timestamps, PIDs, file paths), writes a prevention
SKILL.md. On the next failure, FTS5-matches the error against existing
prevention skills. If a skill matches, the known fix is applied directly —
skipping the LLM diagnosis pipeline. The system gets cheaper as it learns.

**Why it's #3:**
- Self-learning loop is novel — "my agent writes its own fix playbook"
- FTS5 matching is zero-cost (SQLite built-in)
- Original — no paper source

**Source files:**
- `src/observeco/heal/prevention.py` (287 lines)
- `src/observeco/heal/prevention_api.py`

**Extraction notes:**
- Coupled to ObserveCo's heal pipeline — needs decoupling
- The error signature extraction + FTS5 matching is the portable part
- The heal action execution is ecosystem-specific

---

## 4. Context Quality Preflight (adapted from ProofAgent)

**What it does:** Scores agent context against 7 criteria from arxiv
2607.14275 ("AI Agents Do Not Fail Alone"): role clarity, guardrail coverage,
instruction consistency, tool schema quality, grounding sufficiency, injection
hardening, token efficiency. Two-pass: regex (free) + LLM (accurate).

**Provenance:** 7-criteria construct from Bousetouane (U Chicago / ProofAgent.ai).
Our contribution: runtime integration, trending, baseline enforcement.

**Source files:**
- `~/.hermes/scripts/context-quality-preflight.py` (619 lines)

**Extraction notes:**
- Must cite arxiv 2607.14275 prominently
- ProofAgent-Harness exists as open source — we're not first, we're first
  to wire it into a live agent as a pre-session hook
- Differentiation: runtime scoring + trending, not the criteria themselves

---

## 5. Harness Failure Dimension Tagger (adapted from MemoHarness)

**What it does:** Classifies agent session failures into D1-D6 dimensions
(Context, Tool, Generation, Orchestration, Memory, Output) using LLM.
Writes failure_diagnosis signals. Loop controller counts annotations,
triggers fix tasks at threshold (≥20 annotations, ≥70% single dimension).

**Provenance:** D1-D6 taxonomy from MemoHarness (arxiv 2607.14159,
github.com/HowieHwong/MemoHarness). Our contribution: LLM classification
of real production sessions, signal-based annotation, loop controller.

**Source files:**
- `~/.hermes/scripts/harness-dimension-tagger.py` (306 lines)
- `~/.hermes/scripts/harness-dimension-tagger-sessions.py` (344 lines)
- `~/.hermes/scripts/harness-loop-controller.py` (329 lines)

**Extraction notes:**
- Must cite arxiv 2607.14159 prominently
- The tagger alone is diagnostic — the loop controller (kanban tasks,
  verification crons) is where the self-evolution happens
- Needs LLM provider abstraction (currently hardcoded to DeepSeek via Ollama Cloud)

---

## 6. Pulse Check (liveness + crash classification)

**What it does:** Probes agents via health endpoints, classifies daemon
restarts into healthy/TOCTOU/crash based on log evidence + exit codes.

**Source files:**
- `src/observeco/pulse/check.py` (289 lines)

**Extraction notes:**
- Coupled to Hermes process model (launchd, specific agent names)
- The crash classification logic (healthy/TOCTOU/crash) is portable
- The probe dispatch is Hermes-specific

---

## 7. Ecosystem Gap Scanner

**What it does:** Scans running processes + cron jobs + config files to find
agents that exist but aren't being monitored. Maintains a deny-list of known
non-agent system processes.

**Source files:**
- `src/observeco/discover/scanner.py` (280 lines)

**Extraction notes:**
- Useful for multi-agent operators
- The process scanning + deny-list is portable
- The ObserveCo-specific gap reporting is not

---

## 8. Turn Capture

**What it does:** Shell hook handler that records real turns and skill usage
to SQLite. Runs as a 5s-timeout subprocess spawned by Hermes' native
shell-hook system. sqlite3 + stdlib only, exit 0 on any failure.

**Source files:**
- `src/observeco/turn_capture.py` (136 lines)

**Extraction notes:**
- Already a hook handler — minimal extraction needed
- But it's infrastructure, not a standalone feature — it feeds ObserveCo's
  data pipeline. As a standalone plugin it has no consumer.
- Low viral potential on its own — it's a data collector, not a product

---

## 9. Inbox Correlation

**What it does:** Folds related alerts into parent items. Rule: same class
+ first_seen within ±10 minutes + ≥3 distinct agents → parent
`circuit_event` with folded_count=N.

**Source files:**
- `src/observeco/inbox/correlate.py` (197 lines)

**Extraction notes:**
- Useful for multi-agent operators who get alert storms
- The correlation rule is simple and portable
- But it needs an inbox/alert system to be useful — standalone it does nothing

---

## 10. Efficiency Metrics (11 metrics)

**What it does:** 11 deterministic context-efficiency metrics from session
JSONL: read-before-write ratio, tool diversity, retry patterns, bash
efficiency, file edit patterns, etc. No model calls, no external APIs.

**Source files:**
- `src/observeco/efficiency/metrics.py` (540 lines)

**Extraction notes:**
- Hermes session JSONL format specific — needs adapter layer
- The metrics themselves are interesting but the output is a data table,
  not an actionable alert. Needs a consumer (dashboard, alert, score)
- Could be combined with Chisel as "Chisel Pro" — prompt costs + behavior costs

---

## Decision Framework

For each candidate, answer before building:

1. **Does anyone else already do this?** If yes, what's our differentiation?
2. **Is this solving a real problem or just cool tech?** Would I install this
   myself as a new agent user?
3. **Can this be extracted without our specific identities/configs?** What
   needs parameterization?
4. **Is this a $0.99 problem or a $99 problem?** Prompt bloat costs real
   money every API call. That's a $99 problem.
5. **What's the screenshot?** If you can't picture the "wow" image, it won't
   go viral.