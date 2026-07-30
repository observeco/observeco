# UX Gap Analysis + Frontend Roadmap — 2026-07-20

**Status:** Active roadmap — pending Sean's phase-order decisions
**Author:** Spectrum (Product Designer)
**Date:** 2026-07-20
**Branch context:** `merge-capability-a23c231` + uncommitted 2026-07-20 revamp (fleet batching, partial extraction, `/api/fleet/state`)
**Inputs:** `observeco-master-plan.md`, `design/ObserveCo - Data Presentation Architecture.md` (DPA), `specs/obs-spec-analysis-layer-value-proposition.md`, `specs/playbook-audit-2026-07-20.md`, full backend inventory (~170 endpoints, 79 tables), full frontend inventory (index_new.html + partials + app.js), Jun-30 mockup set (`design/ObserveCo - *.html`)

---

## 1. The Verdict

ObserveCo has ~170 API endpoints and 79 DB tables of genuine intelligence, but the dashboard only *answers questions* on one surface (Fleet). Everywhere else, it shows data and asks the user to do the synthesis.

DPA §5 rule: *"if you can only show the left column, the feature isn't done — the right column is the deliverable."* The right column ("so what") exists on fleet cards. It is absent everywhere else.

**Counterargument that holds:** the Fleet tab is genuinely good — verdict-as-sentence (DPA §2-B), health state machine (§2-A), data-quality chips (§2-D), so-what cards (§5). The problem is that Fleet is the *only* finished surface, and the two surfaces that would make the backend's depth legible — a cross-signal **Anomalies Inbox** and a real **Agent Detail view** — are exactly the two that don't exist.

---

## 2. Today's Revamp (2026-07-20), Accounted For

Uncommitted diff: `alerts.py` +112, `capability.py` rework, `fleet.py` +330, `harness_opt.py` +136, `error_timeline.py`, `efficiency.py`, `token_analytics.py`, `detail.py`, `db.py` +74, `index_new.html`, `pathway_tab.html`, `app.js`, CSS +102, new `templates/partials/` (42 files, c24–c65).

**It was a plumbing revamp, not a UX revamp:**

| Delivered today | Not touched today |
|---|---|
| N+1 elimination (`_fetch_fleet_data()` batching in fleet.py + db.py) | Information architecture |
| Unified `GET /api/fleet/state` poll (OOB: verdict + header + agg strip + grid) | Cross-signal synthesis |
| 42 Jinja partials extracted (`cNN.html`) — many are `{{ html|safe }}` wrappers | So-what coverage beyond fleet cards |
| Fleet sort dropdown (status/name/tokens/drift/cost) + agg strip | Actionable alerts (ack API exists, zero UI) |
| Drift tab: canary drift chart + config timeline containers | 5 hidden tabs, 6 placeholder tabs |
| Lazy tab loading (`load` → `revealed once`) | Anomalies tab (wired but click-blocked) |
| Pathway restyle (inline styles → `pw-*` classes) | Agent Detail Modal v2 (Jun-30 mockup) |
| Specs 089 (SLI/SLO), 090 (escalation), 091 (fleet baseline) written + playbook-audited | — |

**Loose threads left by today's revamp:**
1. Divergent fleet endpoints: auto-refresh (30s, app.js) + `applyFilter()` still call legacy `/api/fleet/agents`; search/sort call `/api/fleet/state`. Two paths, same grid.
2. Verdict crit branch hardcodes "1 of {total} operating normally" (`fleet.py` `_fleet_verdict()`).
3. `cNN.html` numbered partial names are unmaintainable; most wrap still-inline f-string HTML via `{{ html|safe }}` (Jinja autoescape bypassed — XSS surface).

---

## 3. The Gap Map — Backend Knows vs UI Shows

| Backend capability (verified live) | UI surface today | The answer the user never gets |
|---|---|---|
| Canary + drift z-tests + per-task accuracy trajectories (`canary_*`, `drift_events`) | Run tables in Capability tab | "Your agent got 12pp worse at coding tasks since Tuesday's SOUL.md edit" |
| `l2_trending` proactive signals (degradation *before* errors) | `/api/l2-trends` endpoint, no tab | "You have a window to fix this before it breaks" |
| `config_snapshots` (what changed, when) | Config timeline on Drift tab (added today) | Correlation: "errors started same day as this edit" |
| `clawforge_garden` memory debt + contradictions | Fleet summary + thin modal | "5 contradictions are causing Dreamer's tool failures" |
| `token_logs` anomaly scores, cost per component | 5-chart grid, no attribution gap | "Y costs 15× more than X for the same task — here's why" |
| `trace_spans` (full OTEL tree) | One raw JSON endpoint (`/api/agent/{n}/traces`) | Waterfall of agent handoff chains |
| `prevention_skills` (L3 learning loop, spec-081) | Indirect in heal-log | "This failure is now a known fix — zero LLM cost" |
| Harness frontier/candidates/experience bank (`harness_*` 8 tables) | Runs list + gate-test form | "What improved my agent, and was it real or search noise?" |
| Auto-Heal, Restarts, Harness tabs (**fully built**) | **No nav entry — unreachable** (keyboard tabMap only) | Everything on them |
| Anomalies tab + `/api/anomalies` (live) | Nav shows `soon` badge; app.js **blocks the click** | The activation moment |
| `POST /api/alerts/ack/{agent}/{category}` | Nothing in UI | Ack/snooze/resolve anywhere |
| `canary_judge_cache` (LLM-judge rationales) | Single JSON endpoint | "Why the judge failed this task," browsable |
| `token_message_breakdown`, `benchmark_*`, `dead_letter_queue`, `skill_usage`, `guidance_fire` | None / aggregates only | Per-message cost, benchmark scores, failed deliveries, skill/guidance telemetry |

---

## 4. Roadmap

Organized by the 3am operator journey (5s: is fleet OK? → 30s: what do I do? → 5min: why did it happen?).
**P0 and P1 require almost zero new backend** — synthesis layers over data that already exists.

### P0 — The Three Answer Surfaces (~4–5d) — *the missing product*

**P0.1 — Anomalies Inbox, promoted to first-class (1.5–2d)**
Master-plan §33 calls this "the activation moment — *your agent has 3 problems right now*."
- **Design mockup (built 2026-07-20):** `mockups/anomalies-inbox-v2.html` — P0.0+P0.1 combined, verified against live data (browser-tested, zero console errors). Contains: signal-cleanup card, verdict sentence, deduplicated feed, evidence drawers, auto-triage drawer
- **Implementation spec (written 2026-07-20):** `specs/obs-spec-092-anomalies-inbox.md` — detector registry, correlation pass, classification rules, endpoints, Pro gating, success criteria. Ready for Pragma handoff
- One prioritized feed reading across: `pulse_log`, `drift_events`, `chisel_drift`, `l2_trending`, `clawforge_garden`, `circuit_breakers`, `token_logs` anomaly scores (>3σ), canary accuracy regressions, `config_snapshots`
- Each item: severity + plain-English explanation + attribution ("started Tuesday, same day as SOUL.md edit") + action link
- The thin `anomaly/` module (no_tools / high_cost / long_gaps) becomes one detector among seven
- **Step zero (5 min): delete the `soon` badge + app.js click-block — `/api/anomalies` is already live**
- Reference: `mockups/anomalies-inbox.html`, `obs-spec-analysis-layer-value-proposition.md` §2 Example 5

**P0.2 — Agent Detail Modal v2 (1.5–2d)**
Jun-30 mockup (`mockups/agent-profile.html`) predates the six-tab live modal (Health/Guard/Errors/Tokens/Memory/Efficiency).
- **Design mockup v4 (built 2026-07-20, approved 2026-07-21):** `mockups/agent-profile-v4.html` — **four pillars** (Quality·canary_runs, Reliability·pulse/guard/errors/l2, Usage·token_logs, Memory·clawforge_garden), drift as tile modifier, traceable drawer. **Spec: `specs/obs-spec-093-agent-profile.md`** — composite `agent_profile_service`, binding language rules, pillar model as shared vocabulary (modal + inbox + so-what cards)
- One view per agent: verdict, pulse timeline w/ latency per beat, component breakdown + drift, cost by model, error clusters, memory garden, canary trend, "what changed" rail
- Every alert, anomaly, and so-what action link lands here
- Needs spec'd `agent_profile_service` (master-plan T4/§3.35): one `/api/agent/{id}/profile` composite endpoint replacing 6 separate fetches
- Unlocks cheap cross-tab deep links (`?agent=X`)

**P0.3 — Fleet polish + so-what actions (0.5–1d)**
- Wire `.act` action links into `fleet.py::_so_what_insights` (CSS class exists; renderer never emits action elements) → "Preview compression →", "Open drift detail →"
- Fix "1 of {total}" verdict bug
- Collapse `/agents` vs `/state` divergence (one grid path)
- Convert agg-strip counts into 3 fleet-level *findings* ("worst drift: hound skills +18%", "highest cost: kepler $2.10/turn")

### P1 — Surface the Hidden Value (~3–4d) — *unblock what you already built*

- **P1.1 — Nav honesty (0.5d).** Add Auto-Heal, Restarts, Harness to nav (or merge into IA). Hide Plugin/Settings/Config/Billing/Traces/Health Score until real — six "coming soon" tiles tax every live surface. **Policy: no tab ships without a nav entry; no nav entry ships as a placeholder.**
- **P1.2 — Actionable alerts (1d).** `POST /api/alerts/ack` exists with zero UI. Add ack/snooze/resolve to rail + Alert Center, delivery status per channel. Foundation for spec-090 escalation chains.
- **P1.3 — Capability tab → operator framing (1d).** Add verdict row above the run tables: accuracy trend arrow, "getting worse at X" callouts, judge reasoning *summarized* ("failed because output skipped the summary step"), config-change annotations on the accuracy chart. Tables move below the fold for engineers.
- **P1.4 — Token Analytics v2 gaps (0.5–1d).** The Jun-30 mockup's two missing framings: attribution gap ("8% of spend unattributed") and per-agent cost comparison ("X vs Y, same task, 15×").

### P2 — The Reliability Layer (~3d, per today's specs)

- **P2.1 — SLI/SLO (obs-spec-089):** SLO badges on fleet cards + error-budget burn in Agent Detail. Consumes `pulse_log`/`errors` — data with no reliability UX today.
- **P2.2 — Escalation chains (obs-spec-090):** config UI in Alert Center on top of P1.2's ack model.
- **P2.3 — Fleet baseline diffing (obs-spec-091):** diff view inside the Compare tab ("fleet vs last Tuesday"), **not a new tab**.

### P3 — Structural Hygiene (ongoing, low effort)

- Cross-tab deep links (`?agent=X&tab=Y`) — cheap with htmx, unlocks every action link above
- Rename `cNN.html` partials → semantic names; replace `{{ html|safe }}` wrappers with real Jinja context (autoescape) as templates get touched
- Empty-state audit per master-plan §3.1 table (what's missing / why / when it appears / what to do)
- Verify efficiency endpoints wired (see `specs/brain-tab-gap-2026-07-14.md` — 3 sections backend-complete/frontend-unwired as of 07-14)

---

## 5. The Stop-Doing List (review gates)

1. **No new tabs for new features.** New capability hangs off Fleet / Inbox / Agent Detail first; a tab is the last resort, not the default.
2. **No raw table ships without a verdict row.** If a surface can't say "so what," it's not done (DPA §5 enforced as a gate).
3. **No more mockups that don't get wired.** The Jun-30 set (Agent Detail Modal v2, Token Analytics v2, So-What `.act`) is three weeks old and mostly unbuilt — P0/P1 closes exactly that list.

---

## 6. Open Decisions (Sean's call)

| # | Question | Default assumption | If flipped |
|---|----------|-------------------|------------|
| 1 | Primary persona: 3am operator (Sean) vs first-run external user | 3am operator → P0 depth-synthesis first | External user → Journey/Onboarding (master-plan §35) jumps to P1 |
| 2 | Synthesis-first vs reliability-first | Synthesis (no new backend) | SLI/SLO (P2.1) swaps with P1.3 |
| 3 | Stack: htmx + vanilla JS stays | Yes — all of P0–P2 fits current stack | React migration = different roadmap entirely |
| 4 | First build: Anomalies Inbox mockup vs Agent Detail Modal v2 | Inbox (activation moment) | Modal (drill-down terminus) |

---

## 8. Live Pass Addendum (2026-07-20 21:30, dashboard :8897, pulse.db 641MB, 39 agents)

Verified against the running instance. **The gap map holds — and live data revealed signal-integrity problems invisible in code review.**

### Confirmed with real data
| Gap-map claim | Live evidence |
|---|---|
| So-what cards fire but have no actions | 17 cards live (5 DEGRADING, 12 ERRORS), **0 `.act` links** |
| Anomalies surface unfinished | `/api/anomalies` returns **raw JSON** (`{"ok":true,"anomalies":[...]}`) — the tab's `hx-swap="innerHTML"` would inject a JSON dump. The `soon` click-block is accidentally load-bearing. P0.1 needs an HTML partial, not just unblocking |
| Alerts passive + noisy | **29 "CRITICAL"** circuit-trips in rail: blueprint 23,300 failures, benchmark 17,364, test-config-agent 9,930 — stale/test agents crying wolf. No ack/triage in UI |
| Harness runs uninterpreted | 9 runs, **0 promoted**, dev/test 0.0% — no "what does 0-for-9 mean" |
| Drift table without "so what" | **accelerator memory +731.6%**, main +731%, 181–1,094 breaches/agent — huge real signal, rendered as raw numbers |
| Token Analytics so-what exists but buggy | Spend verdict works ("hermes-agent alone is 84% of spend — review its system-prompt size first"), 91% attributed shown — but "1826.7M **calls** indexed" mislabels tokens as calls; "100% fleet cache hit" implausible |

### New findings (live-data only)
1. **Data quality 0% OTEL** — verdict bar chip: all 39 agents watch-only (estimated tier). Token data is heuristic, and the chip honestly says so.
2. **Agent registry pollution** — 39 discovered "agents" include `test-config-agent`, `my_new_agent`, `kanban` (dead 110 pulse checks), `workspace`. Dead/test entities flow through alerts, anomalies, drift. Fleet has per-agent delete (×) but nothing prompts triage.
3. **DPA UNKNOWN≠CRITICAL violated in practice** — Hermes profiles (spectrum, kanban, workspace) that don't run daemons get probed, fail 110×, flagged "dead/critical anomaly." They're idle, not dead. Agent-class-aware pulse semantics needed (profile vs daemon vs service).
4. **Formatting bugs** — "38810.25314331055ms" raw floats in modal, "32s ago ago" duplication, calls-vs-tokens mislabel.
5. **L2 trends real but homeless** — live signals (dreamer stuck critical 14m, hermes-agent upstream_fail ×4) on `/api/l2-trends` with no nav surface; returns historical duplicates, not current state.
6. **Agent modal richer than code review suggested** — 6 tabs (Health/Guard/Errors/Tokens/Memory/Efficiency), pulse timeline, failure timeline all live — undermined by raw formatting.

### Roadmap delta from live pass
- **New P0.0 — Signal integrity pass (0.5–1d), gates P0.1.** Agent-class-aware pulse semantics (idle profile ≠ dead daemon), stale/test-agent triage flow (bulk exclude from monitoring + alerts), alert-fatigue fix (29 false criticals → real ones). *Without this, the Anomalies Inbox inherits and amplifies the noise.*
- **P0.1 scope correction:** needs the HTML partial + detector synthesis, not just unblocking (JSON-endpoint finding above).
- **P0.3 adds:** number formatting pass (latency, "ago ago", calls-vs-tokens labels) + L2-current-state endpoint cleanup.

---

## 9. Evidence Index

- Backend inventory: 22 feature modules, ~170 endpoints, 79 CREATE TABLEs (`src/observeco/db.py`, `dashboard/routes/*`, `server.py`)
- Frontend inventory: `templates/index_new.html` (484 lines, 19 tab-content divs), `static/js/app.js` (660 lines), `templates/partials/` (42 new)
- Hidden tabs: `tabHeal`, `tabRestarts`, `tabHarness`, `tabPlugin`, `tabSettings` — in DOM, working endpoints, no nav entry
- Click-blocked: `app.js` — `if (tab.querySelector('.soon')) return;` gates Anomalies despite live `/api/anomalies`
- Fleet so-what: `fleet.py:90 _so_what_insights()` — 3 signal types (drift/tokens/errors), no `.act` elements
- Health state machine: `fleet.py:143 _classify_agent()` (DPA §2-A compliant)
- Verdict: `fleet.py:182 _fleet_verdict()` (DPA §2-B; crit-branch count bug)
- Live data note: local DBs (`~/.observeco/pulse.db` 0 bytes, repo `observeco.db` stale 06-25) — review is code-based, not live-instance-based. Dashboard was not running locally at review time.
