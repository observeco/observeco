# The Three-Human-Experience Layers — Ecosystem Application
**Extends:** `specs/ux-testing-playbook.md`  
**Scope:** All ecosystem components beyond the ObserveCo frontend  
**Status:** Living — update as new layers fail  

---

## 1. Thesis

The UX Testing Playbook defines 3 human-experience layers (Perception, Confidence, Friction) and 6 Expectation Traps — originally for the ObserveCo dashboard frontend. But the framework is not product- or UI-specific. **It applies to every point where the ecosystem generates output that reaches a human (Sean), or where agents interact with each other.**

Any component that:
- Produces output for Sean (directly or via Telegram)
- Consumes another agent's output
- Operates autonomously with no human oversight for extended periods
- Has failure modes that are invisible until something breaks

...should be auditable through this lens.

---

## 2. The Three Layers — Generalized

| Layer | Original (UI) | Generalized | Asks |
|-------|--------------|-------------|------|
| **Perception** — does it look complete? | Page renders completely, no empty sections | Output lands in the right place, has all expected fields, feels "done" | Does the recipient see a complete, actionable artifact? |
| **Confidence** — does the recipient trust it? | API returns 200, but panel shows error | Agent reports "delivered" but content is stale/wrong/empty | Can the recipient act on this without checking? |
| **Friction** — does it feel effortless? | Click has no feedback, user clicks again | Consuming agent needs 2+ follow-ups, human needs to dig for context | Does the recipient get value without extra work? |

**Extended rule:** A feature that passes Perception but fails Confidence or Friction is not done.

---

## 3. Application to the Hermes Ecosystem

### 3.1 PA (Pickles) — Full Agent Coverage (Not Just Briefs)

The existing doc covers PA's Morning/Evening Brief output below. But PA's role is broader: calendar management, multi-channel message filtering, conflict detection, and proactive preparation. The 3-layer lens must apply to all of these, not just the brief format.

#### 3.1.1 Morning/Evening Brief — Output Quality

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the brief land at the right time with all sections populated? | PA writes to intelligence/briefs/ — cron delivers to Topic 2 | ✅ |
| **Confidence** | Can Sean act on the brief without cross-checking source data? | Briefs may contain stale data if PA filtered wrong — no "last verified" timestamp in brief body | ❌ **Trap 1 (Structural Correctness != Visual Completeness)** |
| **Friction** | Does Sean need to ask follow-up questions to get context? | Briefs omit rationale for skipping items — Sean must ask "why was X filtered?" | ❌ **Trap 5 (Empty State Unhelpful)** |

**Fix:**
- Add `last_verified_at` timestamp + `sources_checked` list to every brief
- Add a "Skipped Items" section with one-liner reasons (even if empty, say "No items skipped")
- Every section heading must have content or a meaningful empty-state explanation

#### 3.1.2 Calendar Management — Conflict Detection

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does PA read every calendar event and detect overlaps/conflicts? | PA reads calendar during hourly sweep — reads events but no conflict detection output | ❌ **Trap 1 — calendar read != conflict surfaced** |
| **Confidence** | Can Sean trust the calendar view accounts for all events across all calendars (primary, shared, school, sports)? | Calendar sweep reads from Google Calendar — but no verification that all subscribed calendars are included | ❌ **Trap 10 (Written != Maintained — the calendar view is only as complete as the last sweep's calendar list)** |
| **Friction** | Does PA proactively flag conflicts before they cause scheduling problems? | No conflict advisory output — Sean discovers overlaps when reviewing manually | ❌ **Trap 4 (Cognitive loading: Sean must detect conflicts himself)** |

**Fix:**
- Every calendar sweep output must include `conflicts_detected: N` — 0 means "no conflicts found", not "no sweep ran"
- Conflict detection rule: events <30min apart or overlapping by >5min = conflict, flagged with both event names
- Morning brief cross-references today's events against the evening brief's `prep_for_tomorrow` — surface any events added after the evening brief was written
- Calendar sweep header: `calendars_swept: [primary, school, shared-sports]` — if a calendar is unreachable, flag it explicitly

#### 3.1.3 Message Filtering — Channel Coverage Transparency

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every channel (WhatsApp, iMessage, email, Telegram) produce a sweep entry? | WhatsApp and iMessage monitored via bridges — email sweep is manual/cron-based, no unified sweep log | ❌ **Trap 5 — "email not swept" is silent, not stated** |
| **Confidence** | Can Sean trust the brief accounts for *everything*, not just what PA found interesting? | PA filters by judgment (keyword match + priority scoring) — filtered items silently dropped with no "skipped" section | ❌ **Trap 5 variant — filtered items are invisible** |
| **Friction** | Does Sean need to ask "did you check my email?" to know email was swept? | No unified channel status — Sean must mentally track which channels PA covers each time | ❌ **Trap 4 (Cognitive loading)** |

**Fix:**
- Every sweep output begins with: `channels_swept: [whatsapp, imessage, email, telegram]`
- If any channel was unreachable at sweep time, flag: `⚠️ email sweep failed — bridge not responding`
- Add a `filtered_items` section: "Skipped 3 WhatsApp messages (spam), 1 email (newsletter), 0 iMessage"
- Filtered items count surfaced even when zero: "0 items filtered" — not silence

#### 3.1.4 Evening Brief — Proactive Prep Advisory

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the evening brief set expectations for the next day? | Evening brief lists tomorrow's events | ✅ (partial — events listed) |
| **Confidence** | Can Sean trust the prep advice is complete and actionable? | No "you should prepare X before 09:00" advisory — Sean must figure out prep himself | ❌ **Trap 4 — cognitive loading: Sean must infer prep from raw event list** |
| **Friction** | Does Sean need to ask "what do I need for tomorrow?" separately? | Yes — events listed but not connected to required actions | ❌ **Trap 4 — the loading is "connect events to prep"** |

**Fix:**
- Evening brief includes a `prep_for_tomorrow` section: "You have 2 events. Recommend: review meeting notes before 09:00 standup, pack gym bag before 17:00 session"
- For each event, PA checks: (1) location? (2) materials needed? (3) follow-up action required?
- If PA cannot determine prep: "14:00 — Meeting with Alex (prep unknown — no agenda found)"
- Calendar conflicts feed into this section: "⚠️ 08:00 Gym overlaps with 08:30 Standup by 15 min"

#### 3.1.5 Multi-Sweep Coherence (Morning ↔ Evening ↔ Intraday)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the morning brief acknowledge what changed since last night's brief? | No change log — each brief is standalone, no diff from previous | ❌ **Trap 9 (Output Was Different Yesterday != It's Different Today)** |
| **Confidence** | Can Sean trust the morning brief reflects overnight changes (late emails, new calendar events)? | Morning brief re-sweeps everything — but no "since evening brief: 2 new emails, 1 calendar change" highlight | ❌ **Trap 2 (Mechanism works != user sees the delta)** |
| **Friction** | Does Sean need to scan both briefs to find what changed? | Yes — no diff between briefs, Sean must mentally compare | ❌ **Trap 4 (Cognitive loading)** |

**Fix:**
- Morning brief starts with: `Since evening brief (22:00): 2 new WhatsApp messages, 1 email, 1 calendar event added (09:00 Standup rescheduled to 10:00)`
- Intraday sweeps (if any) show cumulative changes since last brief
- Briefs carry a `previous_brief_id` field — if a brief can't identify the previous one, flag as `no_diff_possible`

---

### 3.2 Daily News Digest (cron: 0 8 * * * to Topic 29)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does it arrive at 08:00 with news items and commentary? | Cron fires, Digest produced | ✅ |
| **Confidence** | Does Sean trust the signal-to-noise ratio? | Batch_judge may have let through "same story, different source" duplicates — no dedup indicator | 🟡 **Trap 5 (Empty State Unhelpful variant: noisy state unhelpful)** |
| **Friction** | Can Sean scan and act in <30s? | No "top 3" summary at top — must read all items to find the signal | ❌ **Trap 3 (Layout Readability)** |

**Fix:**
- Add "Top 3 Signals" executive summary before the full item list
- Dedup by canonical URL (hash it) — show count of duplicates collapsed with a note
- Add `sources_cross_referenced: N` to the header so Sean knows coverage breadth at a glance

---

### 3.3 Dreamer — Morning Walk & Deep Walk (cron: 0 7 * * * to Topic 1165)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the walk produce coherent pattern observations? | Dreamer writes patterns/ to intelligence/ | ✅ |
| **Confidence** | Are the patterns grounded in actual intelligence/briefs/ data, not hallucinated? | No cross-reference trace linking patterns back to specific source files | ❌ **Trap 1** |
| **Friction** | Does Sean need to search for the source data to validate the pattern? | Dreamer writes patterns but doesn't include source citations — Sean must guess which brief/flag triggered it | ❌ **Trap 4 (Loading Experience: the loading here is cognitive — Sean has to "load the context" himself)** |

**Fix:**
- Every pattern observation must cite at least one source file from intelligence/briefs/ or intelligence/flags/
- Add `triggered_by: path/to/source` to the pattern header
- If the source is stale (>24h for data, >72h for patterns), flag it at the top

---

### 3.4 Signal Routing (signal_router.py — every minute)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every outbox file route to the correct inbox? | Router scans shared outbox/ every minute | ✅ |
| **Confidence** | Can the sender trust the signal reached its destination? | No delivery confirmation — sender writes, router picks up, no ack sent back | ❌ **Trap 2 (Mechanism Works != Feedback Registered)** |
| **Friction** | Does a sender need to poll its own inbox to confirm delivery? | No delivery receipt system — signals can land in quarantine with no notification to sender | ❌ **Trap 4 (Loading Experience — the wait here is "did it arrive?")** |

**Fix:**
- Router writes an `ack` file to a shared `signals/acks/{signal_id}.ack` after successful route
- Senders check for ack before retry (currently they retry blindly)
- Quarantine pile gets an automatic T1 flag to Sean if it exceeds 5 items (currently 17 items unattended)

---

### 3.5 Cron Jobs — Silent Failures

Every cron job is a delivery pipeline. The 3-layer lens exposes silent failures the cron exit code cannot catch.

| Scenario | Layer | Pattern | Current State | Fix |
|----------|-------|---------|---------------|-----|
| Cron fires, produces empty output | Perception | Trap 5 — Empty State Unhelpful | Cron exits 0, no flag raised | Every cron must report "output_size: 0" as a failure to its parent log |
| Cron delivers to dead target | Perception | Trap 1 — Structural Correctness | Cron fires, file written, nobody reads it | Delivery target must pass existence + liveness check before write |
| Cron output is identical to last run | Confidence | Trap 2 — Mechanism != Feedback | Cron produces same digest with same headlines | Add diff-check: if output content hash matches previous run, flag as "stale — no new data" |
| Cron writes but the writing agent is the verifying agent | Confidence | QAQC cross-model violation | Agent self-verifies its own cron output (no independent model checks) | Verify cross-model enforcement: cron producer != cron verifier |
| Cron output contains hallucinated data | Confidence | Trap 1 — Structural Correctness | No verification that data can be traced to a source | Every data claim in a cron output must cite its DB source row or API endpoint |

**Systematic fix:**
- Every cron output file must include: `sources_checked: N`, `output_hash: <sha256>`, `verifier_model: <model>`
- Output hash must differ from previous run unless the cron produced genuinely identical data (and even then, flag it)

---

### 3.6 Intelligence Layer — Shared Blackboard

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every intelligence/ directory contain only current, actionable artifacts? | Patterns/ accumulates stale entries, quarantine/ has 17 items | ❌ **Trap 1** |
| **Confidence** | Can agents read from intelligence/ and trust what they find? | No freshness metadata on individual artifacts — an agent reads a 3-day-old pattern from briefs/ and acts on stale data | ❌ **Trap 5** |
| **Friction** | Do agents need to cross-reference freshness manually for every read? | No "last_verified" or "stale_after" metadata on intelligence artifacts | ❌ **Trap 4** |

**Fix:**
- Every intelligence artifact must carry `created_at`, `valid_until`, `source_count` in its filename or header
- Staleness checker (extends freshness_rotation from AGENTS.md) runs on intelligence/ too, not just the wiki
- Quarantine items flagged to Sean after 24h unprocessed — not daily scan, but automatic escalation

---

### 3.7 Pulse Nervous System — Agent Health

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the pulse dashboard show every agent, alive or dead? | All agents shown — state_watcher reads every pulse | ✅ |
| **Confidence** | Can Sean trust a green pulse means the agent is actually working? | Pulse only checks process existence + heartbeat write time — not whether the agent processed its last signal | ❌ **Trap 2 (Mechanism Works != Function Works)** |
| **Friction** | Does a red pulse tell Sean what to do? | Red = dead — but Sean must manually check logs to understand why | ❌ **Trap 5 (Empty State/Error State Unhelpful)** |

**Fix:**
- Add `last_processed_at` to pulse heartbeat — if agent is alive but hasn't consumed its inbox in N minutes, pulse is downgraded to 🟡 (idle)
- Red pulse includes `probable_cause` + `suggested_action` — e.g. "Process not found. Run `observeco pulse restart --agent hound`"
- Pulse dashboard shows `signal_backlog: N` — how many unconsumed signals are waiting in the agent's inbox

---

### 3.8 QAQC Verification Chain (Producer → Verifier)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every deliverable have a verifier assigned and a verification result? | QAQC chain exists on paper (QAQC.md) but no runtime enforcement | ❌ **Trap 1** |
| **Confidence** | Can Sean trust that a delivered artifact passed independent verification? | No cross-model enforcement currently running — verification_bridge.py may exit 0 without actually verifying | ❌ **Trap 2** |
| **Friction** | Does a failed verification tell the producer what to fix? | Failed artifacts written to intelligence/decisions/ with status reason — but no actionable diff or fix suggestion | 🟡 Partial |

**Fix:**
- Runtime QAQC enforcement in the build orchestrator — every deliverable must have `verified_by != produced_by` before delivery
- If no verifier runs within the verification window, the deliverable is automatically downgraded to "unverified" and flagged to Sean
- Failed verification includes a diff or explicit "this must change" list (not just "verification failed")

---

### 3.9 Never-Say-Die Protocol (4-Layer Fallback)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the protocol clearly report which layer fired and why? | Session startup checks heartbeat, resumes from last layer | ✅ |
| **Confidence** | Can Sean trust the protocol didn't silently skip to a fallback that returned wrong data? | No per-layer output hash — layer 3 (qwen3.5) may return a different answer than layer 1 (deepseek) with no diff shown | ❌ **Trap 2** |
| **Friction** | Does a Layer 4 escalation tell Sean exactly what went wrong and what's at risk? | Escalation writes to signal inbox — but Sean may not see it until he starts a session | ❌ **Trap 4 (Loading Experience — the delay is "Sean doesn't know until next session")** |

**Fix:**
- Layer fallback produces a `fallback_diff` — what changed between the expected output and the fallback output
- Layer 4 escalation goes to Telegram (T1) immediately, not just signal inbox
- Per-layer output is logged with model name + output hash for audit trail

---

## 4. Application to ObserveCo Product (Beyond Dashboard UI)

The UX playbook already covers the dashboard frontend. Here the framework applies to **ObserveCo as a running product** — not its UI but its behaviour in the wild.

### 4.1 `observeco watch` — Background Daemon

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the daemon produce all its expected outputs (pulse logs, trims, drift)? | Background daemon writes to SQLite every 30s | ✅ |
| **Confidence** | If pulse check says "alive" and the agent is actually processing work, are they the same thing? | Currently they aren't — pulse = process exists, not signal consumed | ❌ **Trap 2** (see §3.7) |
| **Friction** | If the daemon crashes, does the user know without checking ps aux? | No daemon health endpoint — user must check `observeco pulse check` on the daemon itself | ❌ **Trap 4 (the loading is "monitoring the monitor")** |

**Fix:**
- Watch daemon must expose a health endpoint that reports: `{last_pulse_tick, signal_backlog, uptime, last_error}`
- `observeco status` command that checks if the watch daemon is running and operational (not just alive)
- Daemon logs errors to a `daemon_health` table — if 3 consecutive pulse loops fail, daemon writes a flag to `intelligence/flags/` (for Hermes users) or `~/.observeco/critical.log` (for everyone else)

---

### 4.2 `observeco chisel trim` — Token Analysis

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does trim output show complete breakdown (identity/skills/memory/tools/guidance)? | Yes — per-component token counts in chart | ✅ |
| **Confidence** | Can the user trust the token count reflects what actually runs in their agent? | Trim analyses SOUL.md on disk — not the rendered system prompt at runtime (which may include injected skills, memory, context that are NOT in SOUL.md) | ❌ **Trap 1 (Structural Correctness: filesystem != runtime)** |
| **Friction** | Does trim tell the user what to do about a bloated component? | Shows numbers but no guidance — "your skills section is 8K tokens" with no "here's how to reduce it" | ❌ **Trap 5** |

**Fix:**
- Add `runtime_render: true` mode that actually measures the fully assembled system prompt (with all injected context), not just SOUL.md
- Add "Worst Offenders" per-component with specific actionable advice (e.g., "Skills section: SKILL.md for 'fetch-web-content' is 1,200 tokens — 40% of it is example usage that lives in the skill body, not the description")
- Token count discrepancy between SOUL.md analysis and runtime render is itself a signal worth showing

---

### 4.3 `observeco chisel compress` — System Prompt Compression (Planned)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does compression output show before/after with percentage saved? | Spec'd as dry-run — shows savings preview | ✅ |
| **Confidence** | Can the user trust compression won't break their agent? | Lite mode (6 guidance blocks) proven safe in Hermes — Full mode (memory+profile+context) is riskier | 🟡 **Trap 4 (the loading is "will it break?")** |
| **Friction** | Does `--apply` create a backup so the user can roll back? | Spec says backup is created | ✅ |
| **Missing** | Does compress verify the compressed prompt is syntactically valid (not truncated YAML, not broken markdown)? | Not specified | ❌ **Trap 2 (Mechanism works != output is usable)** |

**Fix:**
- `--apply` mode must run syntax validation on the compressed output before overwriting the original
- Add `--safe` mode: compress, validate, show diff, ask for confirmation
- Compression engine must produce a `compression_confidence` score (100% = every compressed block has a known-safe replacement pattern, 80% = some blocks use heuristic truncation)

---

### 4.4 Auto-Heal (Planned, Feature 3.15)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does auto-heal fire when an agent dies? | 3-line integration in watch loop — should fire immediately | ✅ |
| **Confidence** | Can the user trust the healed agent is actually working, not just restarted but still broken? | Heal checks process restarted — does not verify agent processes its first signal | ❌ **Trap 2** |
| **Friction** | Does a failed heal tell the user what specifically went wrong? | Circuit breaker (3 retries, 4h cooldown) stops hammering — but user gets no diagnosis | ❌ **Trap 5** |

**Fix:**
- After restart, auto-heal must send a test query to the agent and verify it responds coherently (not just that the process is alive)
- Failed heal includes a `diagnosis` section: "Agent hound: process restarted successfully but health endpoint returns HTTP 500. Suggested action: check ~/.hermes/logs/hound/last_error.log"
- 3 consecutive heal failures => auto-escalate to T1 (Telegram/SMS to user) — not just cool down silently

---

### 4.5 Push Alerts (Planned, Feature 3.17)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the alert arrive at the right channel with the right severity? | Delivery module spec'd — Telegram, webhook, email | ✅ |
| **Confidence** | Can the user trust the alert is real and not a false positive? | No dedup or burst control — if pulse check fires 5 failures in 30s, user gets 5 alerts | ❌ **Trap 2 (Mechanism Works != Signal Is Valuable)** |
| **Friction** | Does the alert tell the user what to do next? | Spec says "type, agent, severity, message, timestamp" — but no actionable next step | ❌ **Trap 5** |

**Fix:**
- Alert dedup: same type + same agent within 5min = update existing alert, don't create new one
- Alert body includes `suggested_action: "Run \`observeco heal --agent hound\` or check dashboard"`
- Critical alerts (circuit breaker tripped, all agents dead) include a `requires_ack: true` flag — user must respond within N minutes or escalate

---

### 4.6 Memory Garden (✅ Live, Feature 3.9)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Garden output show debt score, duplicates, contradictions? | Yes — all three metrics reported | ✅ |
| **Confidence** | Is the debt score actionable — does it tell the user what to fix first? | Score is 0-100 but no prioritization — user doesn't know which duplicate or contradiction matters most | 🟡 Partial |
| **Friction** | Does the user need to read MEMORY.md manually to understand the fix? | Garden reports "duplicate entry: /agent/hound/deployed_at" but doesn't show the diff | ❌ **Trap 6 (Context preservation: user leaves Garden view to open MEMORY.md manually)** |

**Fix:**
- Debt score must include `top_3_contributors` — the specific entries costing the most debt
- Duplicate detection shows a diff or at minimum the conflicting values: "entry X says 'deployed_at: 2026-05-01', entry Y says 'deployed_at: 2026-05-15' — which is correct?"
- Contradiction detection groups by impact: HIGH (contradicts a verified fact), MEDIUM (contradicts an observed fact), LOW (contradicts a stale entry)

---

## 5. Application to OpenClaw

### 5.1 Kepler — CRO/Strategy Agent

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Kepler's output land in the right A2A mesh with all expected fields? | Kepler writes to signals/outbox/ and intelligence/market-intents/ | ✅ |
| **Confidence** | Can Sean trust Kepler's market analysis is grounded in real data? | Kepler reads from its own market intel — no independent source verification | ❌ **Trap 1** |
| **Friction** | Does a Kepler recommendation tell Sean exactly what to decide, not just what to consider? | Kepler produces evaluations and assessments — but decisions require Sean to synthesize across multiple signals | 🟡 **Trap 3 (Layout Readability — the layout here is the decision structure)** |

**Fix:**
- Kepler outputs must cite specific sources for every factual claim (similar to Dreamer pattern fix in §3.3)
- Evaluation format: one-line recommendation + supporting evidence + one-line counterargument — Sean gets the debate in a single read
- If Kepler cannot find a source for a claim, the claim is marked `confidence: inferred` with inference basis

---

### 5.2 Content Pipeline (Planned — L1 Draft → L2 Kepler → L3 Sean)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does each gate clearly show what changed and why? | Policy-only — not implemented | N/A |
| **Confidence** | Can the previous gate's reviewer trust the next gate didn't silently revert their changes? | No | ❌ **When built, apply Trap 2** |
| **Friction** | Does Sean need to re-read the full draft at L3, or just the diff? | Unknown — L3 reviewer (Sean) has least time, needs efficient review | ❌ **When built, apply Trap 3 (Layout Readability) — the layout here is the diff structure** |

**Fix (pre-emptive):**
- Each gate hand-off produces a `summary_of_changes.md` — what L1 wrote, what L2 changed, what L2 rejected from L1 with rationale
- L3 sees only: "Final draft" + "Changes from L1 to this version" (diff) + "L2 rejected these L1 choices: [with rationale]"
- No gate should force the next reviewer to re-read the full document unless the change is >50% of content

---

## 6. GS Standards Compliance — Operational Reality vs Specification

None of the 7 GS standards (5 active, 2 awaiting approval) have been run through the 3-layer lens as *operational reality* vs *written specification*. A standard that says "verifier checks measurable conditions" on paper is a Perception-only pass — the Confidence and Friction questions ask whether it's actually enforced, verifiable, and actionable.

### 6.1 GS-008: Assumption Exposure — Active

**Spec:** Every response that makes a recommendation MUST end with an assumption list. Session starts with "Here's what I understand about you and the current state."

| Layer | Question | Spec | Reality | Verdict |
|-------|----------|------|---------|---------|
| **Perception** | Is the spec written and accessible? | GS-008.md exists at `~/.hermes/standards/GS-008-assumption-exposure.md` | All agents reference it in SOUL.md behavioral contracts | ✅ |
| **Confidence** | Can Sean trust every response surfaces its assumptions? | Assumption list required after every substantive response | No runtime enforcement — relies on agent behavioral contract compliance. Main and Hound reference it, but Pragma, Kepler, Aleph have no GS-008 clause | ❌ **Trap 7 (Verification by the producer — agents self-enforce, no cross-check)** |
| **Friction** | Does the assumption list help Sean correct the agent, or is it noise? | "Which ones are wrong?" is the prompt | If assumptions are generic ("you want this done quickly"), the question is useless. Assumption quality varies per agent — Main produces specific assumptions, Kepler's are generic | ❌ **Trap 5 (Empty State Unhelpful — generic assumptions = wasted lines)** |

**Fixes:**
- Add GS-008 compliance check to Skeptical's weekly audit: sample 5 responses, check each has an assumption list with ≥1 non-obvious assumption
- Quality bar: assumption is "non-obvious" if Sean couldn't infer it from the response body alone. "You want this done quickly" fails. "I assumed the source data was from last week's sweep, not today's" passes
- GS-008 clause added to Pragma, Kepler, and Aleph SOUL.md (currently absent)

### 6.2 GS-009: Work Operations — Active

**Spec:** Card definition quality (4 fields for P0-P2), verification evidence requirement, escalation tiers (bump→blocker→alarm), schedule feasibility, weekly audit cadence.

| Layer | Question | Spec | Reality | Verdict |
|-------|----------|------|---------|---------|
| **Perception** | Does the card definition standard match what kanban actually produces? | P0-P2: all 4 fields required. P3-P4: verb + priority sufficient | Cards are created but kanban_db.sqlite query needed to verify compliance rate — no automated compliance reading exists | ❓ **Unknown — no automated compliance measurement** |
| **Confidence** | Can Hound/Kepler trust that a card marked "ready" has valid parameters? | Hound verifies by measurable condition | Hound's verification process is ad-hoc — no runtime enforcement of evidence requirement. A card can be marked "done" with no trace of verification output | ❌ **Trap 11 (Exit Code != Working Code — "verification complete" != evidence exists)** |
| **Confidence** | Does the no-self-verification rule hold at runtime? | Executor and verifier must be different agents | No runtime gate preventing same-agent verification. The spec says "no" but the code doesn't enforce it | ❌ **Trap 7 (Verification by the producer — same agent can verify its own work)** |
| **Confidence** | Do escalation tiers fire at the right thresholds? | Bump at 1-2d, Blocker at 3d, Alarm at 5d | Escalation tiers exist in spec but no automated trigger — Hound manually checks overdues. No cron or daemon monitoring overdue cards against the tier thresholds | ❌ **Trap 2 (Mechanism Works != Feedback Registered — tiers defined but not auto-enforced)** |
| **Friction** | Does the weekly audit surface failures without Sean needing to inspect? | Auto-generated report from audit_cron.py, Main only reviews failures | audit_cron.py auto-generates 3 metrics — but the audit itself isn't running yet (no confirmed cron). The weekly cadence is spec-only | ❌ **Trap 5 (Empty State — no audit output means "not audited" not "no failures")** |

**Fixes:**
- Add a kanban compliance cron that: (a) queries every active card for required fields, (b) flags cards that are "done" without a verifier field different from executor, (c) reports overdue cards by escalation tier window
- Runtime no-self-verification gate: kanban worker must reject a "mark done" request where `verified_by == produced_by`
- Escalation tier cron: checks kanban_db.sqlite every 6h, auto-fires bump/blocker/alarm signals based on card overdue duration matching tier thresholds
- Fix audit_cron.py — confirm it's running on schedule (currently no heartbeat for it)

### 6.3 GS-010: Knowledge Standards — Active

**Spec:** Intelligence must be traceable to source. Patterns need 2+ independent observations before promotion to synthesis. Contradictory patterns flagged, not merged.

| Layer | Question | Spec | Reality | Verdict |
|-------|----------|------|---------|---------|
| **Perception** | Are all intelligence outputs traceable to sources? | Every pattern must cite at least one source file | Dreamer patterns now include `triggered_by` field (§3.3 fix) — but Aleph's wiki pages don't uniformly include inline sources | 🟡 Partial — Dreamer improved, Aleph lags |
| **Confidence** | Can the "2+ observations before synthesis" rule be verified? | Patterns must have 2+ observations before promotion | No cross-reference log exists — Dreamer says "2 observations" but there's no index tracking which sources feed which patterns | ❌ **Trap 2 (Mechanism Works != Feedback Registered — the count is self-reported)** |
| **Confidence** | Are contradictions actually surfaced and not silently merged? | Contradictory patterns are flagged to Main | Dreamer has R7 (surface conflicts) in behavioral contract — but no runtime enforcement. A Dreamer session that merges instead of flagging would pass unnoticed | ❌ **Trap 7 (Verification by the producer — no cross-model check on contradiction handling)** |
| **Friction** | Does Main have enough info to resolve a flagged contradiction without searching? | Flag with both sources | Dreamer flags contradictions with source paths — but doesn't include the contradictory claim text. Main must open both files to understand the conflict | ❌ **Trap 4 (Cognitive loading: Main must fetch sources to resolve)** |

**Fixes:**
- Pattern observation count: Dreamer writes `observation_count: N` + links to observation timestamps in pattern headers. Aleph's weekly audit cross-checks this against `intelligence/patterns/` index
- Contradiction flag format: `conflict: "Source A says X (line 5), Source B says Y (line 12)"` — include the conflicting text, not just the file path
- Aleph wiki pages must include an `inline_sources: true/false` header field — if false, Aleph must explain "no source available, inferred from processing"

### 6.4 GS-013: Measurement Standards — Active

**Spec:** 20+ metrics defined (delivery latency, consumption time, error rate, heartbeats, kanban cycle times, bridge health). SLOs with targets. Intervention triggers. Dashboard cadences.

| Layer | Question | Spec | Reality | Verdict |
|-------|----------|------|---------|---------|
| **Perception** | Are all spec'd metrics producing readings on the expected cadence? | 5m real-time, daily aggregate, weekly rollup | Some metrics are spec'd but not producing (e.g., kepler_wake_latency has no data source because Kepler's session life isn't tracked). Others (disk_usage, cron_run_rate) are easy but may not have collection scripts | ❓ **Unknown — no metric source health dashboard** |
| **Confidence** | Can Sean trust the metrics reflect reality, not stale values? | Metrics are "machine-measurable" — but machine-measurable != machine-measured | A metric with no data source produces zero readings. GS-014 says "metric source silent" flags after 2 cycles — but if the metric was never wired up, it doesn't produce 0 readings, it produces no readings at all, which is a different failure mode | ❌ **Trap 2 (Mechanism Works != Function Works — spec says "measure" but no one checked the measuring tool exists)** |
| **Confidence** | Do SLO breaches actually produce flags? | Flag on every breach, kanban task on sustained breach | GS-014 (exception handling) covers breach flagging — but breach detection requires a cron that compares actual readings against SLO targets. If that cron doesn't exist, breach flags are also spec-only | ❌ **Trap 1 (Structural Correctness — SLOs defined but measurement pipeline may not be wired)** |
| **Friction** | Does a breach flag tell the operator what to do? | Flag + kanban task for sustained breach | Flag format spec'd in GS-014 includes exception type and payload — but no `recovery_command` or `suggested_first_step` | ❌ **Trap 5 (Error State Unhelpful — "delivery_latency breached" without "try restarting signal_router or check ~/.hermes/logs/signal_router/error.log")** |

**Fixes:**
- Metric wiring audit: for each of the 20+ spec'd metrics, confirm: (1) a data source exists, (2) a collection script runs, (3) a reading is produced per cadence. Unwired metrics are downgraded to "spec'd but not collecting" with an expected wiring date
- Missing-data-source detection: if a metric spec says "data source: signal_router timestamps" but no timestamp file is produced, the metric defaults to `status: no_source` — not silently absent
- Every breach flag includes a `recovery_command` field (e.g., "Run `./scripts/restart_signal_router.sh`")
- GS-013 should include a metric source health section tracking which metrics are actually producing readings (the meta-metric)

### 6.5 GS-014: Exception Handling Standards — Active

**Spec:** Exception classification (Critical/High/Medium/Low), recovery owners and response times, gap lifecycle (IDENTIFIED→CLOSED), DRI conflict arbitration, escalation tiers (T0-T4).

| Layer | Question | Spec | Reality | Verdict |
|-------|----------|------|---------|---------|
| **Perception** | Are all exception types handled with clear recovery paths? | 13 exception types defined with recovery owner, response time, and escalation path | Daemon crash and signal delivery failure have auto-recovery. Others (silent cron, config drift) are defined but rely on manual detection | 🟡 Partial — auto-recovery defined for critical paths |
| **Confidence** | Can an observer trust that auto-recovery actually recovered, not silently failed? | T0: Auto-recovery. No human sees it unless it escalates. | If launchd restarts a daemon but the daemon immediately crashes again before Hound's 5m pulse check, the first crash is invisible. Hound sees "daemon down" and recovers, but the intermediate crash cycle is lost | ❌ **Trap 2 (Mechanism Works != Feedback Registered — "auto-recovery" that recovers but doesn't log its own recovery steps)** |
| **Friction** | Does a T3 escalation (Main Decision) tell Main what to decide? | Exception payload delivered to Main's inbox | Exception payload includes type and timestamp but no `decision_required:` or `options:` fields. Main sees "DRI conflict: Kepler and Hound both claim Communication" but must research the dispute before deciding | ❌ **Trap 4 (Cognitive loading: Main must reconstruct the situation from scratch)** |
| **Friction** | Does the gap lifecycle produce visible progress? | Gap states tracked in intelligence/corrections/ | Gaps exist (17 quarantine items, GS-011 not approved) but aren't tracked through the lifecycle. A gap in "IDENTIFIED" for 30 days produces no signal because there's no stale-gap cron | ❌ **Trap 5 (Silent accumulation — gaps in IDENTIFIED stay invisible until someone checks)** |

**Fixes:**
- T0 auto-recovery logging: every recovery step writes to a `recovery_log` file (daemon crash 1 → launchd restart → crash 2 → hound restart → stable). The recovery log is checkable by pulse: "last_recovery: daemon_crash_loop, 2 restarts, resolved at 10:32"
- Every T3 escalation includes: `decision_required: "Which agent owns Communication DRI?"` + `options: ["Kepler (has GS-009 DRI)", "Hound (has GS-014 DRI)", "split domain: Kepler owns schema, Hound owns routing"]`
- Stale-gap cron: runs weekly, queries `intelligence/corrections/` for gaps in IDENTIFIED/TRIAGED/ASSIGNED state with no update >14 days. Flags them to Hound with `gap_id, age_in_days, current_state`
- Quarantine pile (17 items) tracked as a gap through the lifecycle — assign owner, set resolution timeline

### 6.6 Awaiting Standards — GS-011 (Communication/Signal) and GS-012 (Lifecycle)

These are marked ⏳ AWAIT APPROVAL in WORLD_MODEL. Their absence creates a Perception-level gap for the entire ecosystem:

| Layer | Gap | Impact |
|-------|-----|--------|
| **Perception** | No approved signal payload format or lifecycle | Each agent defines its own signal structure. Cross-agent signals (Hound→Kepler, Pragma→Hound) work by convention, not by schema. A malformed signal is routed to quarantine with no validation error explaining what was wrong |
| **Confidence** | No approved agent lifecycle (start, work, checkpoint, pause, die) | Never-Say-Die provides fallback layers but no pre-approve lifecycle for normal operation. An agent that completes a signal and goes idle has no "done" state — it just stops producing output |
| **Friction** | Quarantine pile (17 items) cannot be replayed automatically | Without GS-011's signal schema, a quarantined signal can't be automatically reformatted and re-routed. Main must manually inspect each item to understand what went wrong |

**Recommendation:** Approve GS-011 and GS-012 at minimum bar (not exhaustive — just enough to solve the quarantine pile and signal routing gap). Set a 30-day review window for v2.

---

## 7. Cross-Cutting Systemic Issues

These apply across all components.

### 7.1 The Diff Problem
Almost every component fails on the same axis: **mechanism works but output is not verifiable without manual cross-reference**.

- Cron fires ✅ but output is identical to last run — no one knows
- Signal routes ✅ but lands in dead inbox — no one knows
- Pulse says alive ✅ but agent hasn't consumed a signal in 4h — no one knows
- Heal restarts agent ✅ but agent still returns 500 — no one knows

**Systemic fix:** Every output-producing component must produce an `output_fingerprint` (hash of output content + timestamp + source count). Every component that consumes output must compare fingerprints between consecutive runs and flag identity as potential staleness.

### 7.2 The "No Independent Verification" Gap
QAQC mandates cross-model verification. Current state: many components verify themselves because no other agent is available in the timeline.

- Dreamer writes patterns → no Dreamer-inbox-based verifier exists → Accelerator is supposed to verify but doesn't have a dedicated verification cron
- PA writes briefs → Accelerator spot-checks "daily" — no schedule, no enforcement

**Systemic fix:** Every verification assignment must include `verification_timeout` and escalate if missed. If no verifier can be assigned, the output must default to `confidence: unverified` and be flagged accordingly.

### 7.3 The "Actionable Empty State" Gap
When a component produces no data (empty cron output, no brief items, no patterns found), every component currently responds with silence or a blank artifact. None explain *why*.

**Systemic fix:** Every empty output must include `reason: "<one-line explanation>"` and `expected_next_fill: "<time or condition>"`. No blank artifact ever.

---

## 8. Expectation Trap Catalogue — Expanded

### Trap 7: Verification Is Performed by the Producer (NEW)

**Pattern:** The agent that produces an output also verifies it. Cross-model enforcement (QAQC) is bypassed because no other agent is available.

**Detection:** For every output that requires verification, check: does `verified_by` differ from `produced_by`? If same, the verification is structurally invalid.

**Remedy:**
- Assign a different model or agent as verifier. If none available, mark output as `confidence: unverified` and explain why.
- Verification by the same model is better than no verification, but it must be explicitly flagged as "same-model verification — does not meet QAQC bar"

**Where this fires:** Dreamer's patterns → no dedicated verifier cron, PA's briefs → Accelerator spot-check is best-effort, not scheduled

### Trap 8: Process Exists != Agent Is Working (NEW)

**Pattern:** Pulse checks process liveness (pgrep, port open, heartbeat write time). A process can be alive but not processing signals, generating hallucinations, or stuck in a loop.

**Detection:** For every agent that reports "alive" via pulse, check `last_signal_consumed_at` against `current_time - expected_interval`. If the gap exceeds 2x the expected interval, downgrade to 🟡 (idle).

**Remedy:**
- Every agent must update a `last_processed_at` timestamp in its pulse heartbeat after processing each signal
- Pulse dashboard shows `processed_last_30m: N` alongside status dot

**Where this fires:** Any daemon agent that reports alive but isn't consuming its inbox

### Trap 9: Output Was Different Yesterday != It's Different Today (NEW)

**Pattern:** Cron produces identical output to its previous run. Human sees it's the same data. No one flags it.

**Detection:** Compare content hash of current cron output vs previous run. If identical, flag as "stale — no new data since [timestamp]"

**Remedy:**
- Every cron output file includes `output_hash: <sha256>` and `diff_from_previous: identical|changed`
- Identical output for 3+ consecutive runs = auto-skip delivery (cron still fires, but output goes to a "repeated" directory, not the delivery target)
- Human still gets a heartbeat: "News digest: no new stories since 08:00 yesterday. Last update: [timestamp]"

**Where this fires:** Daily News Digest on quiet news days, Dreamer walk when no new patterns emerge, PA brief when calendar is empty

---

## 9. Implementation Priority

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| P0 | Pulse health includes `last_processed_at` — distinguishes alive-from-working from alive-from-idle | ~2h | Catches agents that are running but silent |
| P0 | Every output file includes `output_hash` and `diff_from_previous` | ~1h per cron | Eliminates silent identical runs |
| P0 | Empty-state `reason` + `expected_next_fill` on every empty artifact | ~30min per component | Eliminates blank artifacts with no explanation |
| P1 | Cross-model verification timeouts + escalation to Sean | ~4h | Enforces QAQC |
| P1 | Kepler outputs cite sources for factual claims | ~2h | Grounds revenue strategy in data |
| P2 | Never-Say-Die `fallback_diff` per layer | ~3h | Trust in fallback outputs |
| P2 | Alert dedup (same type + agent within 5min) | ~2h | Prevents alert fatigue |
| P2 | Push alert `suggested_action` field | ~1h | Actionable alerts vs noise |
| P3 | Memory Garden top-3 contributors ranking | ~2h | Actionable debt reduction |
| P3 | Chisel trim runtime_render mode | ~4h | True vs speculative token counts |
| P3 | Content pipeline diff-based gate review | ~1d (when built) | Efficient multi-stage review |

---

## 10. Remaining Hermes Agents — Extended Coverage

### 10.1 Hound — Co-CEO / Operations

Hound delegates, verifies, and routes. It's the most operationally complex agent — and therefore the highest-risk failure point.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Hound process every signal in its inbox within the expected window? | Hound inbox watcher fires every 1m — but inbox can accumulate during off-session | 🟡 — signals pile up if Hound isn't in an active session |
| **Confidence** | Can Sean trust Hound actually executed a delegated task, not just acknowledged it? | Tasks are delegated via signals with no execution receipt — Hound says "received" but next step may not happen | ❌ **Trap 2 (Mechanism Works != Work Done)** |
| **Friction** | Does Sean need to check Hound's inbox/inbox-status manually to understand delegation gaps? | No auto-summary of what's pending — Sean must ask "what's in your queue?" | ❌ **Trap 4 (Cognitive loading)** |

**Fix:**
- Signal backlog count on every Hound heartbeat — auto-flag to Sean if >3 items remain unconsumed for >30m
- Every delegation signal includes a `deadline_at` field — if not completed within window, auto-escalate
- Weekly delegation summary: "This week Hound received 14 signals, processed 12, escalated 1, 1 pending"

---

### 10.2 Pragma — Build Executor

Pragma implements what Dreamer and Hound approve. It has no session daemon — only cron-based watchdog and signal-driven execution.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Pragma complete each build intent to spec? | Build intents arrive via signal inbox — Pragma runs and writes results | ✅ (when it runs) |
| **Confidence** | Does a zero-exit-code build mean the implementation actually works? | Pragma runs a build script, checks exit code — no functional verification of the result | ❌ **Trap 2 (Exit Code != Working Code)** |
| **Friction** | Does a failed build tell Dreamer what specifically to fix? | Pragma returns "build failed" — no diff of what didn't match spec | ❌ **Trap 5 (Error State Unhelpful)** |

**Fix:**
- Build output includes `spec_vs_result_diff` — what the build intent asked for vs what was actually produced
- Failed builds produce a `probable_cause` diagnosis (syntax error? missing dependency? logic mismatch?)
- Each build intent must have a `verifier_script` field that Pragma runs post-build to validate functionality

---

### 10.3 Skeptical — Auditor / Health Monitor

Skeptical is supposed to be the independent auditor — cron verification, silent death detection, QAQC enforcement. Currently routed to Pragma's inbox with no dedicated daemon.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Skeptical produce audit reports at scheduled times? | Cron fires at 09:00 daily — output goes to intelligence/ | ✅ |
| **Confidence** | Can Sean trust Skeptical's audits are truly independent? | Skeptical's audits run on the same model stack — no cross-model verification for the verifier itself | ❌ **Trap 7 (Verifier Produced by Same Pool)** |
| **Friction** | Does a Skeptical audit flagged as FAIL tell Sean what to do? | Audit writes to intelligence/verifications/ with FAIL result — no actionable root cause | ❌ **Trap 5** |

**Fix:**
- Skeptical audit outputs must include `verification_method: independent|same_model` to make bias transparent
- Audit FAIL includes `diagnosis:` section (3-5 bullet root cause analysis)
- Skeptical audits Pragma's build outputs at least once per week — Pragma doesn't know when

---

### 10.4 Raven — Procurement Specialist

Raven sources deals from Shopee, travel sites. It has low update cadence — its failure mode is staleness, not correctness.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Raven produce deal findings in the expected format? | Output written to intelligence/ with structured data | ✅ |
| **Confidence** | Can Sean trust a deal Raven found yesterday is still valid today? | Deals expire — Raven reports "found at" but no "valid_until" or freshness guarantee | ❌ **Trap 1 (Freshness != Recency)** |
| **Friction** | Does a stale deal entry cause Sean to waste time? | Sean clicks a link from last week → deal expired → wasted attention | ❌ **Trap 4 (Cognitive loading: user must verify freshness manually)** |

**Fix:**
- Every Raven output includes `valid_until` timestamp (price-check expiry heuristic: 24h for flash deals, 7d for standard listings)
- Raven re-verifies top-3 deals before delivering final output — if a deal expired, it notes "was $199 at time of find, not verified now"
- Output includes `freshness_confidence: fresh|stale|unverified` on each item

---

### 10.5 Kanban — Dispatcher / Task Queue Manager

Kanban manages the task queue and spawns workers. It's infrastructure — no user-facing outputs, but its failures cascade to every agent.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every queued task get assigned to the correct worker? | Kanban reads from signals/inbox/ and routes to worker agents | ✅ |
| **Confidence** | Can workers trust the tasks they receive have valid parameters and no duplicates? | Duplicate tasks can arrive if same signal gets ingested twice — no dedup key in task payload | ❌ **Trap 2 (Delivery != Correctness)** |
| **Friction** | Does a stuck task (worker never picks it up) surface to anyone? | Kanban has no timeout for unclaimed tasks — a task can sit in assign limbo indefinitely | ❌ **Trap 4 (Silent wait)** |

**Fix:**
- Every task has a unique `task_id` (sha256 of payload + timestamp) — dedup before queue insertion
- Kanban writes `task_assigned` signals with `expected_completion_by` — if no completion ack within window, escalate
- Unclaimed tasks >1h old get flagged to Hound with `task_id, target_worker, wait_time`

---

### 10.6 Aleph — Librarian / Second Brain Curator

Aleph maintains the Second Brain wiki (Topic 29). Its core risk: stale references and unprocessed ingest backlog.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Aleph process every ingested document and cross-reference existing pages? | Ingest runs daily — cross-references wiki before creating new pages | ✅ (per behavioural contract) |
| **Confidence** | Can Sean trust a wiki page Aleph wrote yesterday is still accurate today? | No freshness check on existing pages — Aleph writes, moves on, never re-verifies | ❌ **Trap 1 (Written != Maintained)** |
| **Friction** | Does Aleph flag contradictory or stale pages without being asked? | Signal-driven — Aleph only acts when triggered. Stale wiki pages accumulate silently | ❌ **Trap 5 (Silent accumulation)** |

**Fix:**
- Weekly wiki health report: pages created, pages stale (>7d without update), orphan pages, contradiction count
- Every wiki page header includes `last_verified_at` — Aleph re-verifies pages on ingest of related content
- Cross-reference validation: when new content conflicts with an existing page, surface the conflict immediately

---

## 11. ObserveCo Product — Additional Dimensions

### 10.1 `observeco pulse check` — Agent Liveness

Already covered in §3.7 (Pulse Nervous System). Additional gap: the user-side experience.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does pulse check show every discovered agent with clear status? | CLI outputs agent-by-agent status table | ✅ |
| **Confidence** | Can the user trust a green status means the agent is actually processing work? | Pulse only checks process existence + health endpoint — not signal consumption | ❌ **Trap 8** |
| **Friction** | Does the CLI tell the user what to do about a dead agent? | Shows "DEAD" status — no `observeco heal` suggestion or log path | ❌ **Trap 5** |

**Fix (in ObserveCo CLI):**
- Green status requires `last_signal_consumed_at` within expected interval — not just process alive
- Dead agent output includes: `suggested_action: "Run 'observeco heal --agent <name>' or check logs at ~/.hermes/logs/<name>/"`
- `pulse check --verbose` shows signal backlog: `hound: 3 unconsumed signals in inbox`

---

### 10.2 `observeco pulse circuit` — Circuit Breaker

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does circuit output show tripped, cooling, and healthy breakers? | Shows breakers with status, count, cooldown remaining | ✅ |
| **Confidence** | Is the circuit state machine correct — does it account for all transitions? | N-state machine exists — but edge cases (manual reset while cooling, reset during backoff) need verification | 🟡 **Trap 2** |
| **Friction** | Does trip output tell the user what failed and what to check? | Circuit shows "TRIPPED after N failures" — no failure-log excerpt | ❌ **Trap 5** |

**Fix:**
- Trip output includes `last_failure_reason: <error message from most recent failure>`
- Circuit health report: `observeco pulse circuit --report` shows trip history with timestamps and root causes
- Manual reset warns: "Breaker tripped at 09:32 for agent hound (3 failures: timeout, timeout, 500). Are you sure?"

---

### 10.3 `observeco clawforge profile` — OpenClaw Context Profiler

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does profile output show MEMORY.md size, skill count, workspace bloat? | Yes — per-component breakdown | ✅ |
| **Confidence** | Can the user trust the profile reflects what the agent actually loads at runtime? | Profile reads filesystem files — not the assembled context at runtime (which may include injected data) | ❌ **Trap 1 (filesystem != runtime)** |
| **Friction** | Does the profile tell the user which component to fix first? | Shows numbers — no prioritization or actionable advice | ❌ **Trap 5** |

**Fix:**
- Add `--runtime` flag that measures the fully assembled runtime context, not just filesystem state
- Profile output includes `Priority Fix: <component> — <reason> (<estimated savings>)` as the first line
- Delta mode: `observeco clawforge profile --diff` shows what changed since last profile run

---

### 10.4 `observeco dashboard` — Web UI

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the dashboard render every section without blank/empty panels? | Full UX playbook applies (see §3.1–3.6 above) | ✅ (per playbook) |
| **Confidence** | Can the user trust the data is live, not cached from an old run? | Dashboard reads from SQLite — no "data as of" indicator on any panel | ❌ **Trap 1** |
| **Friction** | Does the dashboard recover gracefully if the data source stops updating? | No inline "data source may be stale" banner on any panel | ❌ **Trap 4** |

**Fix:**
- Every dashboard panel shows `as of <timestamp>` at top-right — if data >5m old, yellow banner appears
- If SQLite is unreachable, dashboard shows a clear error with `suggested_action: "Run 'observeco start' to resume data collection"`
- Dashboard auto-refresh indicator: pulsing green dot when data is live, static grey when idle

---

### 10.5 `observeco` CLI — Installation / Onboarding (First Touch)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does `pip install observeco` succeed on a clean machine with no prereqs? | PyPI package built with wheels — minimal dependencies | ✅ |
| **Confidence** | Does the first command produce useful output, not a config error? | `observeco pulse check` auto-discovers Hermes configs — generic users get "No agents found" with setup instructions | 🟡 — generic user gets guidance, but Hermes user gets value immediately |
| **Friction** | Does the first-run experience feel like a product, not a debug tool? | CLI uses Typer + Rich — coloured output, formatted tables, beautiful --help | ✅ |

**Fix (generic user onboarding):**
- `observeco init` — interactive setup: prompts for agent framework, health endpoint, naming convention
- First-run auto-detection tiers: Hermes config → OpenClaw SOUL.md → health endpoint probes → manual setup
- If `observeco pulse check` finds nothing: output includes a `Next step: run 'observeco init' to configure` line

---

### 10.6 ObserveCo Error/Diagnostic Messages (All Commands)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Do all errors have a consistent format, style, and tone? | Mixed — some errors are Typer's default (red, bold), others are raw Python tracebacks | ❌ **Trap 3 (Inconsistent styling = unprofessional)** |
| **Confidence** | Can the user trust an error message tells them the real problem, not a symptom? | Some errors show "Connection refused" (symptom) instead of "Agent hound is not running" (cause) | ❌ **Trap 2** |
| **Friction** | Does every error include a suggested fix? | Many errors just say what failed, not what to do | ❌ **Trap 5** |

**Fix:**
- All user-facing errors must: (1) use Rich console markup, (2) state the problem in plain english, (3) include a `suggested_command:` line
- Raw tracebacks go to `~/.observeco/debug.log` — never to stdout
- Error format: `ERROR [component]: <problem>. Suggested: <command or action>. Debug: ~/.observeco/debug.log`

---

### 10.7 ObserveCo Configuration (`~/.observeco/config.yaml` or User Config)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the default config file have every section documented with comments? | Config file written at `observeco init` — all sections present with inline comments | ✅ |
| **Confidence** | Can the user trust a config change doesn't break auto-discovery? | Changing `agent_path` or `framework` may silently disable auto-detection — no validation on write | ❌ **Trap 2** |
| **Friction** | Does `observeco config validate` tell the user exactly which field is wrong and what the valid values are? | Config written to YAML — no validation step after write | ❌ **Trap 5** |

**Fix:**
- `observeco config validate` command: reads config, validates every field, reports issues per field
- Config file writer validates at write time — rejects `framework: hermesx` with "Did you mean 'hermes'?"
- Config includes `_schema_version` — migration path for future config format changes

---

### 10.8 Stripe Billing Integration (Pro Features)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the Stripe checkout render correctly with product details? | Specced but not implemented — no runtime observation possible | N/A |
| **Confidence** | Can a subscriber trust their billing is handled correctly (no double-charges, failed renewals silently skipped)? | Not yet battle-tested | ❌ **When live: Trap 2 (Payment Processed != Subscription Active)** |
| **Friction** | Does a failed payment tell the user what to do, or just show "Payment failed"? | Not yet implemented | ❌ **When live: Trap 5** |

**Fix (pre-emptive):**
- Stripe webhook handler must log every event with `type, id, status, processed_at`
- On subscription create/update/cancel: write verification artifact to `intelligence/billing/` with both Stripe state and local DB state
- Payment failure includes: `action_required: "Update your payment method at https://observeco.com/billing" or run 'observeco billing update'`

---

## 12. Cross-Cutting: Hermes Infrastructure

### 11.1 Session Lifecycle (Session Start / End)

Every agent session has a start and end. The gap between sessions is where signals pile up, state goes stale, and Sean experiences the system as "unresponsive."

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every session start with a clear state summary (missed signals, calendar events, prior session output)? | Session context injected from MISSIONS.json + signal inbox scan | ✅ |
| **Confidence** | Can Sean trust the state summary accounts for every missed signal since last session? | Signal inbox scan shows all unconsumed signals — but no "these arrived while you were away" grouping | 🟡 Partial |
| **Friction** | Does session startup take too long before the agent is usable? | Heavy context injection + full signal scan can delay first response | 🟡 **Trap 4** |

**Fix:**
- Session start summary format: "You were away for 6h. Received 4 signals, 2 urgent (T1). 0 missed deadlines. Calendar: 1 event in the next 8h."
- Prioritised context injection: inject MISSIONS.json + urgent signals first, then background signals asynchronously

---

### 11.2 Gateway / Communication Bridge

The gateway routes messages between Telegram, the agent runtime, and external platforms. It's the nervous system.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does the gateway start cleanly and maintain all channel connections? | Gateway state tracked in gateway_state.json — starts up, connects to Telegram | ✅ |
| **Confidence** | Can Sean trust a message sent to Telegram arrived at the agent? | Gateway processes messages from Telegram and writes signals — but no delivery confirmation loop | ❌ **Trap 2** |
| **Friction** | Does a gateway crash tell Sean anything useful, or just "disconnected"? | Gateway logs to file — no proactive flag on crash | ❌ **Trap 5** |

**Fix:**
- Gateway heartbeat includes `channels_connected: [telegram, whatsapp]` and `last_message_received_at`
- If gateway connection drops >2min, write T1 flag to intelligence/flags/ with `diagnosis + suggested restart command`
- Message round-trip verification: when Sean sends a Telegram message, signal_router must ack within 15s or gateway surfaces latency

---

### 11.3 Configuration Sync (Config File → Runtime)

Hermes config is loaded at session start. Changes made mid-session (config edits, new skills, profile changes) are invisible until restart.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does session-start config load pick up every active section? | Yes — config.yaml read at boot | ✅ |
| **Confidence** | Can Mid-session config changes be detected without restart? | No config watcher — user edits config.yaml, agent continues with stale state until next session | ❌ **Trap 1 (Filesystem != Runtime, time dimension)** |
| **Friction** | Does Sean need to restart the session to pick up a skill change? | Yes — no hot-reload mechanism | ❌ **Trap 4** |

**Fix:**
- Config-watch daemon (optional): monitors config.yaml for mtime changes — writes `config_changed` signal to agent inbox
- On detect: agent writes "Config changed at 10:32 — new skill 'fetch-web-content' detected. Reload? (y/N)"
- Hot-reload for skills only (no profile/agent identity changes — those still need restart)

---

## 13. Expectation Trap Catalogue — Expanded (Continued)

### Trap 10: Written != Maintained (NEW)

**Pattern:** An agent writes knowledge (wiki page, profile report, brief) once and never re-verifies it. The artifact becomes stale or inaccurate over time, but there's no freshness check on existing artifacts — only on creation.

**Detection:** For every knowledge artifact >7 days old, check `last_verified_at` — if absent or >7 days, the artifact is potentially stale.

**Remedy:**
- Every written artifact must carry `created_at` and `last_verified_at` metadata
- Agents maintain a rotation: re-verify N oldest artifacts per maintenance cycle
- Contradiction detected during new work → immediate re-verify of affected existing artifacts

**Where this fires:** Aleph wiki pages, intelligence patterns, Raven deal entries, Dreamer pattern observations

---

### Trap 11: Exit Code != Working Code (NEW)

**Pattern:** A script or build exits 0 but the output is functionally wrong — zero-size file, empty table, wrong data, truncated YAML. The system reports "success" because the process didn't crash.

**Detection:** After any zero-exit build/script, check: output file was written? output file is non-empty? output file passes schema validation? output content differs from input (not a no-op)?

**Remedy:**
- Every script output includes a post-execution validation step (schema check, non-empty check, content-hash check)
- Zero-exit with zero-output is flagged as a distinct failure state: "Script completed but produced no output"
- Build intents for Pragma must include `success_criteria` — not just "run this script" but "run this script and verify the result has X"

**Where this fires:** Pragma builds, cron jobs with empty output, any script that exits 0 with no side effects

---

### Trap 12: Freshness != Recency (NEW)

**Pattern:** An output is timestamped as "recent" (written 5 minutes ago) but the data inside is stale (cached from yesterday). Timestamp reflects when it was written, not when the data was last verified.

**Detection:** For every output, distinguish `written_at` (when the file was created) from `data_valid_until` (when the data inside was last confirmed accurate).

**Remedy:**
- Every output carries two timestamps: `written_at` and `last_verified_at`
- If `last_verified_at` is absent, the output defaults to `freshness: unverified`
- Data-fetch operations timestamp: `pulse check: agent responded at 10:32` — not "pulse check wrote output at 10:33"

**Where this fires:** Raven deal outputs, PA briefs with cached data, dashboard panels showing SQLite results without query timestamp

---

## 14. Updated Implementation Priority

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| P0 | Pulse `last_processed_at` — alive vs idle distinction | ~2h | Catches agents running but silent |
| P0 | Output hash + diff check on every cron run | ~1h per cron | Eliminates silent identical runs |
| P0 | Empty-state `reason` + `expected_next_fill` | ~30min per component | No blank artifacts |
| P0 | Pragma build `success_criteria` + post-build validation | ~3h | Exit 0 ≠ working code |
| P1 | Gateway message round-trip ack | ~4h | Trust in message delivery |
| P1 | Cross-model verification timeouts + Sean escalation | ~4h | Enforces QAQC |
| P1 | Session-start priority context injection | ~2h | Faster first-response time |
| P1 | Aleph weekly wiki health report | ~2h | Prevents wiki staleness |
| P1 | Config validation (`observeco config validate`) | ~1h | Prevents config breakage |
| P2 | Kanban task timeout + escalation | ~3h | Stuck task detection |
| P2 | Config hot-reload for skills | ~4h | Zero-downtime config changes |
| P2 | Hound delegation summary (weekly) | ~2h | Delegation transparency |
| P2 | Dashboard "as of" timestamps + stale banners | ~2h | Trust in live data |
| P3 | Skeptical audit bias transparency | ~1h | Honest audit |
| P3 | Memory Garden top-3 contributors | ~2h | Actionable debt reduction |
| P3 | Content pipeline diff-based gate review | ~1d (when built) | Efficient multi-stage review |

---

---

## 15. Additional Coverage — Genuinely Missing Areas

### 14.1 Second Brain Knowledge Retrieval (User-Facing)

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Aleph's answer land with the exact info Sean asked for? | Aleph reads from wiki, responds with structured answer | ✅ |
| **Confidence** | Can Sean trust the answer reflects current wiki state, not cached/recycled knowledge? | No "last_verified_at" shown in response — Sean can't tell if answer uses data from yesterday or last month | ❌ **Trap 10 (Written != Maintained)** |
| **Friction** | Does Sean need to ask "when was this written?" to assess freshness? | Yes — Aleph's answer doesn't include source freshness info unless asked | ❌ **Trap 12 (Freshness != Recency)** |

**Fix:**
- Every Aleph answer includes source freshness: `Sourced from: X page (last verified: YYYY-MM-DD)`
- If no source exists for the answer, Aleph says so: "No wiki page covers this directly — here's what I know from context"
- If sources conflict, surface the conflict immediately (per R7 — Surface Conflicts)
- Answer format: one-liner conclusion + source citation + stale flag if applicable

---

### 14.2 Intelligence Watcher Telegram Output (T1/T2/T3)

The intelligence_watcher.py routes artifacts to Telegram by tier. It's the primary way Sean sees system activity outside his session. Its output quality is a user-facing product.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every T1 artifact produce a clear, actionable Telegram message that lands in the right topic thread? | Watcher posts to Alpha Management topic threads per AGENT_THREAD_MAP | ✅ |
| **Confidence** | Can Sean trust a T1 flag is genuinely urgent — not misclassified T2 noise that landed in T1? | Tier classification is directory-based (flags/ → T1, proposals/ → T2) — a non-urgent artifact written to the wrong directory gets wrong tier | ❌ **Trap 1 (Structural Correctness != Semantic Correctness)** |
| **Friction** | Does a T1 message tell Sean what to do, or just that something happened? | Watcher posts artifact content — but no actionable "suggested decision" or "requires ack" field | ❌ **Trap 5 (Empty State Unhelpful — variant: noise state unhelpful)** |

**Fix:**
- Every T1 Telegram message includes: `Decision needed? Y/N` + `Suggested: <one-line action>` at top
- Tier misclassification detection: watcher checks artifact content against tier — if a flag says "low priority" but landed in T1, surface the tier mismatch
- T1 artifacts with no human-actionable content get auto-downgraded to T2 (e.g., "verification passed" is T2, not T1)
- Telegram message format: `[TIER] type | agent | action needed? | one-line summary`

---

### 14.3 Kepler Operational Document Delivery Chain

Hound maintains operational documents for Kepler (kepler-growth-tracker.md, marketing-readiness.md, kepler-opportunities.md). These are NOT Kepler's output — they're Hound's production pipeline documents that Kepler may or may not see.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does Hound write updated operational docs on the expected cadence? | Hound updates kepler-growth-tracker.md on discovery — no fixed cadence documented | 🟡 — ad-hoc, no heartbeat |
| **Confidence** | Can Kepler (or Sean) trust the doc reflects current reality, not last week's snapshot? | No freshness metadata on the doc — a stale growth tracker could cause Kepler to make decisions on old data | ❌ **Trap 10 (Written != Maintained)** |
| **Friction** | Does either audience know when the doc was last updated without opening it? | File mtime is visible but not surfaced in any automated notification | ❌ **Trap 4 (Cognitive loading: user must check manually)** |

**Fix:**
- Every Hound-maintained operational doc includes `last_reviewed_at` and `next_review_by` in header
- Freshness check cron: if kepler-growth-tracker.md untouched for >7d, write a correction flag
- Delivery verification: when Kepler consumes a decision that references these docs, verify the doc is fresh first

---

### 14.4 ACP Watcher Meta-System

Each agent has an ACP (Agent Communication Protocol) watcher that polls the shared outbox and delivers signals to the agent's inbox. This is the message transport layer — separate from pulse check (which checks liveness) and separate from signal routing (which routes once delivered).

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every ACP watcher poll on schedule and deliver all pending signals? | Per-agent ACP watchers run as cron daemons — logs show delivery attempts | ✅ (when running) |
| **Confidence** | Can Sean trust a delivered signal actually reached the agent's inbox? | ACP watcher writes to inbox/ directory — no read receipt, no delivery confirmation | ❌ **Trap 2 (Mechanism Works != Feedback Registered)** |
| **Friction** | Does a stalled ACP watcher tell anyone? | Stall detection exists (observer watcher) but escalation path to Sean is indirect via corrections/ | 🟡 — stall is detected but may not reach Sean fast |

**Fix:**
- Each ACP watcher writes a `last_delivered_at` timestamp to agent state — if stale >5min relative to expected poll interval, flag
- Delivery receipt: router writes ack file on successful inbox write; sender can check
- ACP watcher health dashboard in ObserveCo: shows each watcher's last poll time, last delivery, pending count

---

### 14.5 Stall Detection (Observer / Watcher-of-Watchers)

A stall observer monitors the ACP watchers themselves. If a watcher hasn't polled in >5min, the observer flags it. This is meta-monitoring — the watcher that watches the watchers.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does stall detection fire within the expected window for every watcher? | Observer scans watcher logs every 5min — correction files written when stall detected | ✅ |
| **Confidence** | Can Sean trust a "no stall" report means watchers are actually working, not that the observer itself is broken? | No cross-watcher verification — if the observer is the only thing watching watchers, a broken observer means nobody knows | ❌ **Trap 2 (Mechanism Works != Function Works)** |
| **Friction** | Does a detected stall tell Sean what to do? | Correction file written to corrections/ with timestamp — but Sean may not see it until next session | ❌ **Trap 5 (Error State Unhelpful) + Trap 4 (Loading Experience)** |

**Fix:**
- Stall detection must have cross-model verification: if observer says "all clear" but watcher A hasn't delivered in 10min and watcher B's log shows it missed 3 polls, there's a contradiction — surface it
- Stalls >10min with no auto-recovery escalate to T1 Telegram (not just corrections/)
- Observer health endpoint in ObserveCo: "stall_observer_alive, last_check, last_stall_detected, watcher_states_per_agent"

---

### 14.6 Hound's Delegation Workflow Output (User-Facing)

Hound delegates tasks to Pragma and other agents via signals. The output Sean sees is the delegation trail — he needs to know what was delegated, to whom, by when, and whether it completed.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does every delegation produce a visible trail Sean can review? | Delegations go via signal outbox → target inbox — no human-readable delegation log | ❌ **Trap 1 (Structural Correctness: signal sent != Sean can see it)** |
| **Confidence** | Can Sean trust a delegated task was completed without asking Hound? | No auto-completion notification to Sean — he must ask "is task X done?" | ❌ **Trap 2 (Mechanism Works != Work Done)** |
| **Friction** | Does Sean need to poll Hound's inbox state to understand what's pending? | Yes — currently the only way to see pending delegations is asking Hound directly | ❌ **Trap 4 (Cognitive loading)** |

**Fix:**
- Hound writes delegations to a human-readable log: `intelligence/hound-delegations/YYYY-MM-DD.md`
- Each delegation entry: `task_id, target_agent, deadline, status (pending/in_progress/done/failed), last_update`
- Weekly delegation summary (already planned in §13 P2 Hound delegation summary)
- Auto-escalation: delegation overdue by deadline → T1 flag to Sean with task details

---

### 14.7 Second Brain Wiki Index Health (User-Facing)

The wiki index.md is auto-maintained. When it's stale, the wiki feels broken — pages exist but aren't discoverable.

| Layer | Question | Current State | Verdict |
|-------|----------|---------------|---------|
| **Perception** | Does index.md list every wiki page with correct timestamps? | Aleph updates index.md on every write | ✅ (when Aleph runs) |
| **Confidence** | Can Sean trust index.md reflects the current wiki state? | Index updated during Aleph sessions — if Aleph hasn't run in 24h and pages were manually created, index is stale | ❌ **Trap 10 (Written != Maintained)** |
| **Friction** | Does a stale index tell Sean the wiki may be incomplete? | No indicator — user searches for a page, doesn't find it in index, assumes it doesn't exist | ❌ **Trap 5 (Empty State Unhelpful — the empty state here is "page not listed")** |

**Fix:**
- Index.md header includes `last_full_refresh: YYYY-MM-DD HH:MM` — if >24h, yellow banner: "Index may be stale"
- Aleph re-verifies index completeness on every session start (not just on write)
- If manual pages exist that Aleph doesn't know about, index includes a `note: N manually-created pages detected — not in index`

---

## 16. Cross-Cutting Gaps — Missed Systemic Patterns

### 15.1 The "Only When Asked" Gap

**Pattern:** Multiple components produce valuable outputs but only when Sean explicitly asks. They don't proactively surface what changed.

- Wiki pages exist but Sean must ask "what's new in the wiki?" — no proactive "3 wiki pages updated since your last visit"
- Delegation trail exists but Sean must ask "what's pending?" — no proactive delegation summary
- Kepler growth tracker exists but Sean must ask "what's Kepler's pipeline look like?" — no scheduled update

**Systemic fix:** Every component with periodic or stateful output should emit a "what changed since last visit" summary at session start. The session startup context (from §11.1) should include proactive summaries, not just a signal inbox count.

### 15.2 The "Human Reads as Agent" Gap

**Pattern:** Artifacts written for agent consumption (structured signals, YAML files) are occasionally read by Sean. He sees raw JSON and YAML instead of human-readable summaries.

- Intelligence watcher posts raw artifact JSON to Telegram (Sean sees `{"from": "hound", "to": "sean", "type": "flag", ...}`)
- Correction files are JSON — Sean must mentally parse
- Signal payloads are JSON — Sean reads them on Telegram

**Systemic fix:** Every output that reaches a human channel (Telegram, dashboard, any UI) must pass through a human-readable rendering layer. Raw JSON/artifacts go to logs. Human channel gets formatted text. This is especially critical for the Intelligence Watcher Telegram output — Sean shouldn't see `{` on his phone.

### 15.3 The "No Recency Anchor" Gap

**Pattern:** Dashboard panels show data without "as of" timestamps. Wiki pages show "last updated" but not "last verified." Every component that displays data fails to anchor the user in time.

**Systemic fix:** Every piece of displayed data must carry a recency anchor. This is already partially addressed (§10.4 dashboard fix, §10.3 clawforge profile) but the *systemic* gap is that no component defaults to showing recency — it must be retrofitted per component.

---

## 17. Updated Expectation Trap Catalogue

### Trap 13: Semantic Correctness != Tier Correctness (NEW)

**Pattern:** An artifact is written to the correct directory structure (e.g., `intelligence/flags/`) but the content inside doesn't match the tier — a low-severity notice classified as T1, or urgent data written to T3.

**Detection:** For every tiered output, check: does the artifact's content match the tier implied by its location? A flag with `severity: low` in `flags/` directory → tier mismatch.

**Remedy:**
- Intelligence watcher validates content against tier on every route — not just directory-based routing
- Mismatch produces a correction: "Flag in T1 has `severity: low` — verify tier classification"
- Writer agents must include `intended_tier` in artifact header; watcher compares against routing table

**Where this fires:** Intelligence Watcher routing, any agent writing to intelligence/ directories

### Trap 14: Signal Sent != Sean Saw It (NEW)

**Pattern:** A signal routes successfully to a target inbox, but the human-facing output doesn't exist — Sean never sees the summary, only the agent does. The signal is "delivered" but the human's need for awareness is unmet.

**Detection:** For every signal that has a human stakeholder, verify the human has a parallel notification or summary. A signal between agents that has a Sean-related outcome but no Sean notification → miss.

**Remedy:**
- Every signal with `to: "sean"` or `cc: "sean"` must produce a parallel human-readable output
- Agent-to-agent signals with decisions that affect Sean must produce a Telegram summary or intelligence log
- Signal lifecycle includes: `human_notified: true/false` field — if false and signal has human relevance, escalation

**Where this fires:** Hound delegations (agent-to-agent, Sean doesn't see), Kepler→Hound coordination (decisions made, Sean unaware), any agent debate conclusion (aligned decisions that Sean needs to know about)

### Trap 15: Process Is Running != Data Is Flowing (NEW)

**Pattern:** An ACP watcher process is running (alive, polling every N seconds) but no data is actually being delivered — empty inbox, zero writes, no errors. The watcher is healthy but useless.

**Detection:** Compare watcher process liveness against `last_delivery_time`. If process is alive but hasn't delivered anything in 3x the expected polling interval, it's running in a dry loop.

**Remedy:**
- Each watcher records both `last_poll_time` and `last_delivery_time` — not just process liveness
- Zero-delivery loop detection: if last N polls produced zero deliveries, the watcher is flagged as "healthy but stalled"
- Watcher health includes: `last_poll_time, last_delivery_time, deliveries_last_24h, pending_count`

**Where this fires:** Any ACP watcher that's alive but has no signals to deliver (common when the ecosystem is idle — the watcher is technically fine but Sean thinks "no news is good news" when actually the watcher is serving empty cycles)

---

## 18. Implementation Priority (Updated)

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| P0 | Intelligence Watcher Telegram human-readable rendering (no raw JSON) | ~3h | Eliminates "human reads as agent" gap — most visible issue |
| P0 | Session-start proactive summaries (what changed since last visit) | ~2h | Fixes "only when asked" gap — Sean sees system state without asking |
| P1 | Aleph answer freshness citation in every response | ~1h | Builds trust in every knowledge answer |
| P1 | Stall observer cross-model verification (observer contradicts watcher logs) | ~3h | Catches meta-monitoring failures |
| P1 | Hound delegation log (human-readable) | ~2h | Makes delegation trail visible without asking |
| P1 | Every dashboard panel shows "as of" timestamp | ~2h | Fixes "no recency anchor" across all panels |
| P2 | Signal lifecycle `human_notified` enforcement | ~3h | Prevents agent decisions without Sean awareness |
| P2 | Kepler operational doc freshness cron | ~1h | Prevents stale growth doc decisions |
| P2 | Index.md freshness header + stale warning | ~1h | Wiki discoverability assurance |
| P2 | Watcher health dashboard (pulse + delivery stats per watcher) | ~2d | Full ACP meta-system visibility |
| P3 | Intelligence Watcher content-tier mismatch detection | ~2d | Prevents T1/T2/T3 misclassification |

---

*This document extends `specs/ux-testing-playbook.md`. Add new traps and findings here as the ecosystem evolves.*
