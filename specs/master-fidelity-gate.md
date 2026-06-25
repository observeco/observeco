# Master Fidelity Gate — The Integration Gate

**Product:** ObserveCo (and all future software projects)
**Status:** Living — update as lessons accumulate
**Version:** 3.15 — 2026-06-19 (Installation Testing Layer J)
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-05-30 | Initial creation — 25-point combined checklist, escape tracking, human override, post-ship review |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory, standard lessons entry |
| 3.0 | 2026-05-31 | **Added Layer F: First-Run Audit** (8 pts then 9, all-items-must-pass) — forces every PR to verify fresh-install, incognito-load, empty-state, port-collision, cross-platform, headless, daemon-auto-start, and first-30-seconds experience. Total score increased 61→69→70, threshold 48→56. Lessons Learned: escape post-mortem from shallow risk assessment. |
| 3.1 | 2026-05-31 | **Layer F hardened**: 8→9 items (added F9: telemetry opt-in / security warning). All evidence requirements made CI-enforceable (exact curl/grep/TestClient commands). Added cross-reference to requirements-fidelity-playbook.md Traps 1-3. Scoring table updated 69→70. Thesis "four lenses"→"six lenses" fixed. Duplicate empty tag removed. Lessons Log date inconsistency fixed. CI yaml threshold corrected 48→56 and total 61→69→70. |
| 3.11 | 2026-06-01 | **Windows + Telemetry Hardening**: watch.py fully cross-platform (DETACHED_PROCESS, taskkill fallback, signal guards). Telemetry client gated on local opt-in file. Three new dashboard endpoints for opt-in prompt. CI audit searches `<body>` content. Cross-platform matrix updated. Lessons Learned entries added. |
| 3.12 | 2026-06-10 | **Added Layer G: Payment-to-Feature Fidelity** (3 items, 8 pts). Updated scoring table to include Layer G. Updated version history. |
| 3.13 | 2026-06-10 | **Added Layer H: UX Interaction Fidelity** (2 items, 4 pts: H1 modal stacking, H2 scroll-first actions). Scoring table updated 78→82, threshold 60→63. |
| 3.14 | 2026-06-18 | **Added Layer I: Observability Fail-Safes** (4 items, 12 pts: I1 data integrity, I2 disk space, I3 startup validation, I4 staleness detection). Scoring table updated 82→94, threshold 63→72. |
| 3.15 | 2026-06-19 | **Added Layer J: Installation Testing** (6 binary pass/fail items, 6 pts). Updated scoring table 94→100, threshold 72→76. Registered installation-test-playbook.md. |
**Source:** Real need — the 12-playbook system (see installation-test-playbook.md §Playbook Inventory) all work independently, but nothing forces them to run TOGETHER before shipping.

This is the **single source of truth for "is this ready to ship?"** It combines all ten layers into one weighted gate that must pass before any change reaches production.

---

## 1. Thesis

**A feature that passes all ten playbooks independently can still fail when they aren't checked together.**

The requirements spec says "show live data." The coding fidelity says "cards render correctly." The UX says "the cards feel populated." The system-design says "the daemon survives restart." But nobody checked that the REQUIREMENTS spec's "live data" means the SAME THING as the SYSTEM-DESIGN daemon's 30-second interval. The feature ships. The data is stale. The user is confused.

This document is the **integration gate** — the single checklist that forces all eight layers to converge before anything ships.

---

## 2. The 45-Point Combined Checklist (Weighted, 10 Layers A–J)

Each item has a weight: 1 (informational), 2 (important), or 3 (critical). Minimum pass threshold: 80% of total possible score.

### Layer A: Requirements Fidelity (6 items, max 14 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| A1 | RDR written and approved | 3 | ☐ | RDR document linked in PR |
| A2 | All 6 spec traps checked and clean | 3 | ☐ | Trap-by-trap audit output |
| A3 | State matrix with ≥4 states per story | 2 | ☐ | State enumeration table |
| A4 | Success metrics defined and measurable | 3 | ☐ | Metric names + targets + measurement methods |
| A5 | Constraints register filled | 2 | ☐ | Hard/soft constraints documented |
| A6 | Cross-references verified current | 1 | ☐ | cross-ref-verify.sh output |

Max Layer A: 14 pts **Pass threshold: ≥11**

### Layer B: Coding Fidelity (6 items, max 14 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| B1 | Spec grounding: spec re-read before code | 2 | ☐ | Quoted spec paragraph in PR |
| B2 | Implementation fidelity: every spec section exists in output | 3 | ☐ | Section-by-section mapping table |
| B3 | No f-string leaks, no document.write() | 3 | ☐ | Regex scan output |
| B4 | TestClient spec-fidelity assertions pass | 3 | ☐ | Test output |
| B5 | Dependency verification: all imports exist | 1 | ☐ | pip list / npm ls output |
| B6 | Master plan status updated | 2 | ☐ | Diff to master-plan.md |

Max Layer B: 14 pts **Pass threshold: ≥11**

### Layer C: UX Fidelity (5 items, max 11 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| C1 | Perception: all sections look populated (not empty/skeleton) | 3 | ☐ | Full-page screenshot |
| C2 | Confidence: no inline errors, tracebacks, or broken panels | 3 | ☐ | browser_console() output — zero errors |
| C3 | Friction: all interactions respond in <200ms | 2 | ☐ | Interaction timing log |
| C4 | Accessibility: keyboard-navigable, contrast ≥4.5:1 | 2 | ☐ | Tab-through + contrast audit |
| C5 | Emotional load: first-time user can answer "what should I do first?" | 1 | ☐ | Written walkthrough for new user |

Max Layer C: 11 pts **Pass threshold: ≥9**

### Layer D: System-Design Fidelity (6 items, max 18 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| D1 | Data pipeline map: every table has known writer | 3 | ☐ | data-pipeline-audit.sh output |
| D2 | Lifecycle tests all 12 pass | 3 | ☐ | Lifecycle test output |
| D3 | 9-lens scores each ≥4, total ≥32/45 | 3 | ☐ | Lens scoring table |
| D4 | Heartbeat contract: pid + timestamp + status + cycle | 3 | ☐ | Heartbeat file contents |
| D5 | Cross-platform parity: POSIX tested, Windows documented | 3 | ☐ | Cross-platform matrix filled |
| D6 | Crash resilience: per-agent + per-sweep error isolation | 3 | ☐ | Crash mode enumeration |

Max Layer D: 18 pts **Pass threshold: ≥14**

### Layer E: Agent Session Governance (2 items, max 4 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| E1 | Session log complete (rework cycles, decisions, verification gaps) | 2 | ☐ | Session log file |
| E2 | Checkpoint discipline: all checkpoints signed off | 2 | ☐ | Checkpoint decision logs |

Max Layer E: 4 pts **Pass threshold: ≥3**

### Layer F: First-Run Audit (9 items, max 9 pts) — HIGHEST WEIGHT, BINARY PASS

Layer F exists because layers A–E all assume a running system with data. They miss the class of failure where the system is *architecturally correct* but a first-time user on a clean machine sees nothing, gets confused, and leaves. **Every item has weight 1. ALL 9 must pass — this layer is binary. No exceptions.**

Layer F directly covers the cold-user states enumerated in requirements-fidelity-playbook.md §2 Trap 1 (happy path only), Trap 2 (visuals without states), and Trap 3 (lifecycle not specified). It forces the spec to answer those traps for the first-run experience before any code is written.

| # | Item | Weight | Check | Evidence required (CI-enforceable) |
|---|------|--------|-------|-------------------------------------|
| F1 | Fresh pip install in clean venv | 1 | ☐ | CI run: `python3 -m venv /tmp/test-venv && /tmp/test-venv/bin/pip install observeco && /tmp/test-venv/bin/observeco --version` exits 0. Add to .github/workflows/install-test.yml |
| F2 | First dashboard load (incognito, no localStorage) | 1 | ☐ | CI run: Install in clean venv, start on dynamic port, curl root page. Assert: `curl -s http://localhost:$PORT/ | head -c 500 | grep -cE 'guided\|setup\|wizard\|agent-card\|first.time'` returns ≥1. Add TestClient variant to ux-audit.py: `r = client.get('/'); assert any(kw in r.text.lower() for kw in ['guided', 'setup', 'first time', 'add an agent', 'detect agents']), 'No first-run experience'` |
| F3 | No agents detected state | 1 | ☐ | CI TestClient on system with zero agent configs: `r = client.get('/api/agents'); assert 'No agents' not in r.text.split('class=\"agents\"')[0] or 'setup' in r.text.lower() or 'detect' in r.text.lower()`. Empty fleet without next action = FAIL |
| F4 | Port collision handled | 1 | ☐ | CI run: Start instance A on port 9120. Start instance B on default (tries 9119, falls to 9121+). Assert B's first stdout line matches `/Port \d+ in use — serving on \d+/`. Capture B's actual port, curl it, confirm dashboard renders |
| F5 | Cross-platform / Docker / headless | 1 | ☐ | CI matrix: ubuntu-latest + macos-latest both run F1+F2. `Dockerfile` exists and `docker build --tag observeco . && docker run observeco --version` exits 0. Windows status documented in README known-limitations table |
| F6 | No browser (headless + CLI-only) | 1 | ☐ | CI run: `observeco watch --daemon --once` starts, writes at least one heartbeat file to `~/.observeco/heartbeat.json`, exits 0. Verify heartbeat contains pid, timestamp, status, cycle fields |
| F7 | Daemon auto-start on dashboard launch | 1 | ☐ | CI TestClient: Kill any existing daemon. Start TestClient session (`client.get('/api/heal-log')` triggers `_ensure_watch_running`). Wait 5s. Verify heartbeat file exists and cycle ≥1. If daemon start fails, dashboard endpoint `/api/delay-banner` shows inline error with recovery action string: `observeco watch --daemon` or equivalent |
| F8 | First 30 seconds experience | 1 | ☐ | CI automated walkthrough script `specs/scripts/first-run-audit.py`: (1) curl `/` — "What is this for?" answered in first 200 chars of body text; (2) curl `/api/agents` — "What should I do first?" answered via presence of action button text "detect" or "add" or "setup" in the response; (3) curl `/api/phase` — phase-done banner visible or phase-0->phase-1 transition guidance present. Any fail = report the exact blank moment |
| F9 | Telemetry opt-in / security warning on first run | 1 | ☐ | First-run dashboard view or CLI must show ONE of: (a) telemetry opt-in prompt with "yes/no" choice, (b) localhost security warning ("Dashboard accessible to any process on this machine — do not expose to the internet"), (c) data residency notice if telemetry sends to external endpoint. CI test: `curl -s http://localhost:$PORT/ | grep -cE 'telemetry\|data.*shared\|localhost.*warning\|opt.in\|privacy\|local only'` returns ≥1. Add TestClient variant to ux-audit.py: `r = client.get('/'); assert any(kw in r.text[:500].lower() for kw in ['telemetry', 'localhost', 'warning', 'opt.in', 'privacy', 'local only']), 'No telemetry/privacy/security notice in first 500 chars'`. If feature has a telemetry endpoint, first-run must require explicit opt-in before first `/api/telemetry-event` fires |

Max Layer F: 9 pts **Pass threshold: 9/9 (ALL items must pass — this layer is binary)**

**If F1–F9 are not ALL checked green, the feature ships without a verifiable first-run experience — which is the highest-probability failure mode for a CLI-to-web product aimed at a general audience. No exception process for this layer. If one fails, the feature does not ship.**

### Layer G: Payment-to-Feature Fidelity (3 items, max 8 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| G1 | Payment success → feature unlock verified | 3 | ☐ | End-to-end test: complete payment, verify Pro activated within 30s |
| G2 | Email receipt sent from payment platform | 2 | ☐ | Stripe Dashboard → Payments → verify email sent flag |
| G3 | Cancel/deactivate → badge updates without reload | 3 | ☐ | Open modal → cancel → verify badge changes without page reload |

Max Layer G: 8 pts **Pass threshold: ≥6**

**Success metric for this layer:** "% of first-run users seeing ≥1 agent card or guided setup wizard. Target: >90%. Measured via opt-in telemetry on /api/agents first call. Published as dashboard-accessible metric within 30 days of launch."

### Layer H: UX Interaction Fidelity (2 items, max 4 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| H1 | Modal stacking guard — no two overlays active simultaneously | 2 | ☐ | For every "Full Details" / "Details" button inside a modal: verify parent modal is closed before child opens |
| H2 | Scroll-first actions — primary buttons visible without scrolling | 2 | ☐ | Open each modal with action buttons: confirm Apply/Save/Full Details are above the fold, not below a large scrollable detail section |

Max Layer H: 4 pts **Pass threshold: ≥3**

---

### Layer I: Observability Fail-Safes (4 items, max 12 pts)

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| I1 | Data integrity verification — PRAGMA checks pass on startup | 3 | ☐ | `run_integrity_check()` output — passed=True |
| I2 | Disk space monitoring — pre-write check active with 30s cache | 3 | ☐ | `check_disk_space()` returns status != 'critical' |
| I3 | Startup validation — all 5 checks pass before service start | 3 | ☐ | `run_checks()` output — passed=True |
| I4 | Staleness detection — every time-series endpoint returns last_updated | 3 | ☐ | grep for `add_last_updated` in all `/api/` time-series endpoints |

Max Layer I: 12 pts **Pass threshold: ≥9**

### Layer J: Installation Testing (6 items, max 6 pts) — BINARY PASS

Layer J exists because layers A–I all assume the product is already installed. They miss the class of failure where `pip install observeco` fails, or `observeco dashboard` crashes on a machine that has never seen it. **Every item has weight 1. ALL 6 must pass — this layer is binary. No exceptions.**

Layer J directly covers the scenarios enumerated in installation-test-playbook.md §2 (13 scenarios across fresh install, upgrade, downgrade, and failure modes). See that document for detailed simulation commands.

| # | Item | Weight | Check | Evidence required |
|---|------|--------|-------|-------------------|
| J1 | Fresh install on clean machine (no Hermes, no config) | 1 | ☐ | CI run: `python3 -m venv /tmp/j1-venv && /tmp/j1-venv/bin/pip install observeco && timeout 5 /tmp/j1-venv/bin/observeco dashboard --no-browser 2>&1` exits 0 or is killed by timeout (dashboard started successfully and is waiting for connections). If it exits non-zero before timeout, the install is broken. |
| J2 | Fresh install with Hermes present (auto-discovery) | 1 | ☐ | Same as J1 but on a machine with `~/.hermes/` present. Verify: `curl -s http://localhost:9119/api/agents | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>0, 'No agents discovered'"` |
| J3 | Upgrade preserves data (DB migration) | 1 | ☐ | Install old version → start dashboard → create data → upgrade → verify data preserved (row counts match). See installation-test-playbook.md §Scenario 4 for exact commands. |
| J4 | Downgrade detected gracefully (newer schema) | 1 | ☐ | Bump `PRAGMA user_version` ahead → start dashboard → verify graceful message, no crash. See installation-test-playbook.md §Scenario 5 for exact commands. |
| J5 | Uninstall + reinstall preserves data | 1 | ☐ | `pip uninstall observeco -y` → verify data dir exists → `pip install observeco` → start dashboard → verify historical data available. See §Scenario 6. |
| J6 | Corrupted DB handled gracefully | 1 | ☐ | Corrupt `pulse.db` with garbage bytes → start dashboard → verify no crash, user-visible error, recovery path exists. See §Scenario 8. |

Max Layer J: 6 pts **Pass threshold: 6/6 (ALL items must pass — this layer is binary)**

---

## 3. Scoring

| Layer | Max | Threshold | Actual | Pass? |
|-------|-----|-----------|--------|-------|
| A — Requirements | 14 | ≥11 | ___ | ☐ |
| B — Coding | 14 | ≥11 | ___ | ☐ |
| C — UX | 11 | ≥9 | ___ | ☐ |
| D — System Design | 18 | ≥14 | ___ | ☐ |
| E — Agent Session | 4 | ≥3 | ___ | ☐ |
| F — First-Run | 9 | =9 (ALL MUST PASS) | ___ | ☐ |
| G — Payment Pipeline | 8 | ≥6 | ___ | ☐ |
| H — UX Interaction | 4 | ≥3 | ___ | ☐ |
| I — Observability Fail-Safes | 12 | ≥9 | ___ | ☐ |
| J — Installation Testing | 6 | =6 (ALL MUST PASS) | ___ | ☐ |
| **Total** | **100** | **≥76** | **___** | **☐** |

---

## 4. Automated + Human Gate Protocol

### 4.1 The Automated Gate (CI, runs on every push)

```yaml
# .github/workflows/fidelity-gate.yml — runs on every push to main/pre-release

jobs:
  requirements-audit:
    runs-on: ubuntu-latest
    steps:
      - run: bash specs/scripts/cross-ref-verify.sh
      - run: bash specs/scripts/data-pipeline-audit.sh

  coding-fidelity:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ -k "spec_fidelity"
      - run: python3 -c "from observeco.dashboard.server import app; print('Import OK')"
      - run: bash specs/scripts/fstring-leak-detect.sh

  system-tests:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ -k "lifecycle"
      - run: pytest tests/ -k "cross_platform"

  first-run-audit:
    runs-on: ubuntu-latest
    steps:
      - name: First-Run Audit (skip if script not yet committed)
        run: |
          if [ -f specs/scripts/first-run-audit.py ]; then
            python3 specs/scripts/first-run-audit.py
          else
            echo "⚠️ first-run-audit.py not yet in repo — add before shipping any Layer F feature"
          fi
      - name: Install test (clean venv)
        run: |
          python3 -m venv /tmp/test-venv
          /tmp/test-venv/bin/pip install observeco
          /tmp/test-venv/bin/observeco --version
      - name: F2 — first-run keywords in root page
        run: |
          PYTHONPATH=src python3 -c "
from fastapi.testclient import TestClient
from observeco.dashboard.server import app
client = TestClient(app)
r = client.get('/')
assert any(kw in r.text.lower() for kw in ['guided', 'setup', 'first time', 'add an agent', 'detect agents']), 'FAIL: No first-run experience keywords in /'
          "
      - name: F9 — telemetry/security/privacy keywords
        run: |
          PYTHONPATH=src python3 -c "
from fastapi.testclient import TestClient
from observeco.dashboard.server import app
client = TestClient(app)
r = client.get('/')
assert any(kw in r.text.lower() for kw in ['telemetry', 'localhost', 'warning', 'opt.in', 'privacy', 'local only']), 'FAIL: No telemetry/security/privacy notice'
          "

  combined-score:
    needs: [requirements-audit, coding-fidelity, system-tests, first-run-audit]
    runs-on: ubuntu-latest
    steps:
      - run: python3 specs/scripts/score-gate.py
      - name: Fail if below threshold
        run: python3 -c "
          import json;
          score = json.load(open('gate-score.json'));
          assert score['total'] >= 72, f'Gate FAIL: {score[total]}/94'
        "
```

### 4.2 The Human Gate (mandatory before any merge)

Even if all automated gates pass, the human must:

1. Review the **evidence bundle** — screenshots, test output, API responses, session log
2. Check the **combined score** ≥72/94
3. Verify the **"Human Lens Override"** rule: if anything feels wrong, reject regardless of score
4. **Sign off** by replying "GATE PASSED — [name] — [date]"

### 4.3 The Human Lens Override Rule

**Rule:** Even if ALL automated gates pass, if the human says "this still feels wrong," the gate re-opens.

This is not optional. The human override exists for scenarios the playbooks cannot capture:
- A feature that passes all metrics but adds cognitive load
- An architecture that scores ≥4 on all lenses but costs too much
- A spec that is technically complete but fundamentally the wrong product

**Override protocol:**
1. Human says "this feels wrong"
2. Agent does NOT argue. Agent asks: "which layer feels wrong? Requirements? UX? Architecture?"
3. Agent opens the relevant playbook and the human describes the feeling
4. If the playbook missed it: THAT is the playbook gap — document in Lessons Learned
5. If the playbook covered it but implementation was wrong: fix the gap, re-run gate
6. If the playbook covered it and implementation was correct: the spec was wrong — revise spec, re-run from Layer A

---

## 5. Trade-off & Risk Decision Framework

All ten playbooks are score-based (pass/fail, ≥threshold, ≥4/5). Real shipping involves deliberate trade-offs: "We accept partial Windows support for 2 weeks because Mac/Linux is 95% of users."

Without a risk framework, the playbooks become religious dogma that slows shipping instead of protecting it.

### 5.1 The Decision Risk Matrix

Every ADR, every PR with exceptions, and every "accept this trade-off" decision must fill this matrix:

```markdown
## Risk Decision Matrix — [Decision Name]

### Decision
[One sentence: what we are deciding to do, de-prioritise, or accept]

### Impact Assessment (1-5 scale, higher = worse)

| Dimension | Impact (1-5) | Rationale |
|-----------|-------------|-----------|
| UX Layer (perception, confidence, friction) | | |
| Coding Fidelity (spec match, correctness) | | |
| System-Design lenses (lifecycle, coverage, cross-platform, etc.) | | |
| Requirements completeness (state coverage, success metrics) | | |
| Future maintenance burden | | |
| User-facing risk (data loss, broken experience) | | |

### Time Cost vs Value

| Factor | Detail |
|--------|--------|
| Time saved by this trade-off | |
| Value delivered sooner | |
| Time to fix if wrong | |
| Maximum acceptable reversion cost | |

### Reversion Plan
[Concrete steps to reverse this decision if it proves wrong:
- What trigger event would cause reversal?
- Who decides it's time to reverse?
- How long does reversal take?
- What data would prove the trade-off was wrong?]

### Risk Owner
[Who is accountable for monitoring this trade-off and initiating reversal if needed]

### Sign-Off
[Human: I acknowledge the trade-off and accept the risk. Signed: ________ Date: ________]
```

### 5.2 When to Use the Risk Matrix

| Use | Required | Example |
|-----|----------|---------|
| Any "NO" in a Golden Gate | YES | "Cross-platform: NOT tested on Windows → must fill Risk Matrix" |
| Any lens score <4 | YES | "Lens 5 (Cross-Platform) score 2/5 → must fill Risk Matrix" |
| Any layer threshold missed | YES | "Layer D scored 12/18, threshold is 14" |
| Any feature that ships with known exceptions | YES | "Auto-heal not implemented for Windows v1" |
| Any trade-off that reduces quality for speed | YES | "Skip 12 lifecycle tests to ship today" |
| Any decision that adds technical debt | RECOMMENDED | "Using thread instead of daemon for MVP" |

### 5.3 The "No-Risk" Default

**Rule:** If no Risk Matrix is filled, the default assumption is ZERO risk tolerance. All gates must pass at full threshold. Any "NO" blocks merge.

The Risk Matrix exists so trade-offs can be MADE — not so they can be HIDDEN. Filling one out is not a license to skip quality; it is a record that the skip was deliberate, scoped, and reversible.

### 5.4 Risk Audit Trail

Every Risk Matrix becomes a permanent record:

```
~/.observeco/risk-decisions/
├── 2026-05-30-windows-watch-v1.md
├── 2026-06-01-pro-auto-heal-skip.md
└── ...
```

These are reviewed quarterly. Any risk that has not been resolved within 3 months is automatically escalated to the product owner.

---

## 6. Post-Ship 24-Hour Review

### 6.1 When to Review

Every feature that passes the gate and ships MUST have a 24-hour review:

```markdown
## Post-Ship Review — [Feature Name]

### Ship time: [YYYY-MM-DD HH:MM]
### Review time: [YYYY-MM-DD HH:MM + 24h]

### Real-world observation
- What did actual users see? (screenshot from production)
- Any error logs in the first 24h? (grep agent.log)
- Any support tickets or user complaints?
- Any dashboard anomalies?

### What the gates missed
| Playbook layer | What was caught | What wasn't |
|---------------|----------------|-------------|
| Requirements | | |
| Coding Fidelity | | |
| UX | | |
| System Design | | |
| Session Governance | | |

### Escape-rate tracking
- Bug reached user? Y/N
- If yes: which playbook was supposed to catch it?
- If caught: what was the gap in the playbook?
- Action: update the playbook's Lessons Learned section
```

### 6.2 The Escape-Rate Rule

**Rule:** Every bug that reaches the user gets logged back into the relevant playbook's Lessons Learned. If a playbook's escape rate exceeds 20%, the playbook itself goes through a "spec hardening" process.

```markdown
### Playbook Health Metrics
| Playbook | Escapes this sprint | Total bugs | Escape rate | Target |
|----------|-------------------|------------|-------------|--------|
| Requirements | ___ | ___ | ___% | <20% |
| Coding Fidelity | ___ | ___ | ___% | <20% |
| UX | ___ | ___ | ___% | <20% |
| System Design | ___ | ___ | ___% | <20% |
| Session Governance | ___ | ___ | ___% | <20% |

### Escape Post-Mortem Template
Bug: [description]
Layer: [requirements / coding / UX / system / session]
Playbook that should have caught it: [name + section]
Why it escaped: [reason]
Fix: [playbook update applied]
```

---

## 7. The Golden Gate — Pre-Ship Sign-Off

Before ANY change reaches production:

```
|□ 1. Combined score ≥72/94
|□ 2. All 9 layer thresholds met (A≥11, B≥11, C≥9, D≥14, E≥3, F=9/9, G≥6, H≥3, I≥9)
|□ 3. Automated CI gate green
|□ 4. Human gate signed off (no override)
|□ 5. Evidence bundle attached (screenshots, test output, API responses, session log)
|□ 6. Post-ship 24h review scheduled
|□ 7. Master plan status updated to ✅ Live
|□ 8. Playbook Lessons Learned updated (if any gap was discovered)
|□ 9. Escape-rate metrics updated (if any bug found)
|□ 10. If infrastructure change: lifecycle tests committed to repository
|□ 11. Risk Matrix filled if any exceptions accepted
|□ 12. **Layer F (First-Run Audit) ALL PASS — no exceptions permitted for this layer**
|□ 13. Cross-refs verified: spec-gated-workflow-playbook.md, orchestration-anti-patterns-playbook.md, security-stride-playbook.md all referenced in relevant ADR/PR context
```

**The final sign-off message must be:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MASTER FIDELITY GATE — [FEATURE NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
|Combined score: ___/94 (threshold ≥72)
|Layer A (Requirements): ___/14 ≥11 ☐
|Layer B (Coding): ___/14 ≥11 ☐
|Layer C (UX): ___/11 ≥9 ☐
|Layer D (System): ___/18 ≥14 ☐
|Layer E (Session): ___/4 ≥3 ☐
|Layer F (First-Run): ___/9 =9 (ALL MUST PASS) ☐
|Layer G (Payment): ___/8 ≥6 ☐
|Layer H (UX Interaction): ___/4 ≥3 ☐
|Layer I (Observability Fail-Safes): ___/12 ≥9 ☐
Human override: NONE
Risk Matrix: [NONE / filled — linked to ___]
Post-ship review: SCHEDULED

STATUS: ✅ GATE PASSED — [signing authority] — [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 8. Lessons Learned Log

### 8.1 2026-05-30 — Initial Creation

| What was missing | What happened | Gap | Fix applied |
|-----------------|---------------|-----|-------------|
| No combined gate | Five playbooks existed but weren't run together | Integration gap | Created §2 unified checklist with weighted scoring |
| No escape tracking | Bugs discovered post-ship never traced back to playbooks | Feedback loop gap | Added §6.2 escape-rate tracking with per-playbook metrics |
| No human override | Automated gates become dogma | Process rigidity | Added §4.3 Human Lens Override Rule |
| No post-ship review | "Ship and forget" cycle | Observability gap | Added §6.1 24-hour review protocol |
| No risk framework | Playbooks become dogma, trade-offs avoided or hidden | Decision gap | Added §5 Risk Decision Matrix with reversion plans and audit trail |

### 2026-05-31 — Layer F Added After Risk Assessment Escape

| What was missing | What happened | Gap | Fix applied |
|-----------------|---------------|-----|-------------|
| No first-run audit layer | Agent produced a shallow risk assessment that covered only known-unknowns — never considered fresh-install, incognito, port-collision, or headless states | Requirements gap — first-run experience never specified | Added §2 Layer F: First-Run Audit with 8 mandatory items. All must pass (binary layer, no exceptions). Success metric with telemetry target added. |

### 2026-05-31 — Standardization Pass (preserved from v2.1)

| What was missing | What happened | Gap | Fix applied |
|-----------------|---------------|-----|-------------|
| No Version History table | Missing metadata | Versioning gap | Added Version History table with 1.0 → 2.1 entries. |
| No cross-reference to Playbook Inventory | Cross-reference gap | Integration gap | Added reference to requirements-fidelity-playbook.md §Playbook Inventory. |
| Lessons entry said "Three playbooks" — inaccurate | Stale count | Feedback loop gap | Fixed to "Five playbooks" — the actual count at creation time. |

### 2026-05-31 — v3.1 Layer F Hardening

| What was missing | What happened | Gap | Fix applied |
|-----------------|---------------|-----|-------------|
| F evidence too vague for CI | Human-review-only items (screenshots, narratives) not enforceable | Verification autonomy failure | All F items now CI-enforceable: exact curl/TestClient/Python commands, exit-code assertions, grep patterns |
| Telemetry/privacy opt-in absent from first-run | No security warning or data-sharing disclosure on first load | Requirements gap — Trap 5 (constraints) | Added F9: first-run dashboard must show telemetry opt-in, localhost warning, or data residency notice |
| Layer F not cross-referenced to requirements-fidelity traps | Cold-user states from requirements §2 Trap 1/2/3 had no gate enforcement | Cross-reference gap | Added cross-reference paragraph at top of Layer F docstring |
| Thesis still said "four lenses" after six-layer addition | Master plan status drift — line 24 stale | Coding-fidelity Bug Pattern 4.16 | Fixed to "six lenses" on line 25 |
| CI yaml assert referenced old /61 total | score-gate.py assertion would pass with wrong threshold | Coding-fidelity Bug Pattern 4.3 (spec-to-implementation gap) | Fixed to /70 in combined-score job |
| Lessons Log 2026-06-01 entry created at wrong date | Self-inflicted regression — the v2.1 standardization happened 2026-05-31 | Inconsistent metadata | Fixed date to 2026-05-31 |
| Stray <FILE> tag left in 7 files | Empty file-boundary markers from template rendering | Tool output hygiene | Stripped all <FILE> tags across the 7 playbooks |

### 2026-06-01 — Windows + Telemetry Hardening Sprint

| What was missing | What happened | Gap | Fix applied |
|-----------------|---------------|-----|-------------|
| Windows daemon used raw POSIX signal API without guards | `signal.signal(signal.SIGTERM, ...)` and `os.fork()` crash on Windows | System-design Lens 5 (Cross-Platform Parity) | Added `_start_windows()`, `_windows_kill()`, signal handler guard via `hasattr(signal, "SIGTERM")`, graceful fallback messages |
| Telemetry client sent data on env-var default | `OBSERVECO_TELEMETRY=on` meant telemetry fired on install without explicit consent | Layer F F9 (Telemetry opt-in) | Added local opt-in file gate (`~/.observeco/.telemetry_opt_in`), `set_opt_in()` accessor, all `send()` functions check opt-in first |
| No opt-in prompt on dashboard first load | User could see dashboard without ever being asked about telemetry | UX Layer C Confidence | Three new server endpoints (`/api/telemetry-status`, `/api/telemetry-opt-in`, `/api/telemetry-prompt`) + htmx loaded banner with Yes/No buttons |
|| CI F9 check searched raw HTTP for keywords | 30KB inline CSS in `<head>` pushed `<body>` past 500-char window | Verification autonomy | Audit scripts now search `<body>` content exclusively for keyword checks |

|### 2026-06-01 — Team Shared-View Sprint

|| What was missing | What happened | Gap | Fix applied |
||-----------------|---------------|-----|-------------|
|| No shared-view mode for multi-user fleet | 5 team members, 5 independent instances, everyone sees different data | Requirements gap — Trap 5 (constraints not called out) | Added `--shared <path>` flag, WAL-mode concurrency, `instance_id` in pulse_log, `/api/instances` endpoint, shared-fleet badge in dashboard |
|| No shared-mode security warning on first load | Admin starts shared mode without knowing the security implications | Layer F F9 analogue (security warning) | Added `/api/shared-warning` — one-time banner on first shared-mode load with network share risks |
|| Shared path unwritable causes silent fallback | User specifies invalid path, no error message | First-run safety (Layer F) | `get_shared_db_path()` now does write-test on parent dir; returns None (local mode) if unwritable |
|| Schema migration not documented as idempotent for multi-instance | Team upgrades from v7→v8 simultaneously — risk of race on ALTER TABLE | System-design Lens 9 (multi-instance safety) | Added SAFE & IDEMPOTENT comment referencing Trap 3 and Lens 9 in migration 8 |
||| Lens 9 scorecard didn't cover shared mode | Score was 3/5 — missing shared-mode safety criteria | System-design playbook gap | Updated Lens 9 score 4: shared-mode (WAL, instance_id, path validation); score bumped 3→4 |

|### 2026-06-01 — Scale >100 Agents Sprint

| What was missing | What happened | Gap | Fix applied |
|-----------------|---------------|-----|-------------|
| No pagination/search/filter on agent cards | 100+ agents rendered as all-cards grid — server response scaled linearly with agent count | System-design Lens 9 — implicit single-page assumption | Added page/per_page/q/status params to /api/agents. Paginated rendering (default 25/page). Search bar + filter chips in template. Performance budget in Layer F audit. |

|### 2026-06-01 — Security Hardening + Desktop App Sprint

| What was missing | What happened | Gap | Fix applied |
|-----------------|---------------|-----|-------------|
| Localhost dashboard open to any process on the machine | No access control — any process on local machine could curl /api/agents and see agent data, health status, token counts | Layer F — security constraint (Trap 5) | Added `DashboardAuthMiddleware`: random crypto-secure token (`secrets.token_urlsafe(32)`) required via `X-ObserveCo-Token` header or `?token=` query param. All `/api/` routes protected except `/api/phase`, `/api/agent-count`, `/api/licenses/validate`. CSP, nosniff, Referrer-Policy headers on every response. |
| Dashboard token not surfaced to user | First launch gives no indication that the dashboard is now protected | UX Layer C — Confidence | Added `observeco dashboard --show-token` CLI flag. Token printed on first run. `window.__OBSERVECO_TOKEN` injected into root page for htmx auto-attach. |
| No desktop-native experience | Users forced into browser + terminal | Requirements gap — Trap 5 (constraints) | Created `src/observeco/desktop.py` with pywebview native window (1200×800), system tray (Open/Token/Restart/Quit), graceful fallback to browser if pywebview not installed. Added `observeco desktop` CLI command. Optional dep `observeco[desktop]`. |
| Audit script couldn't test protected endpoints | F3 and Perf checks returned 401 instead of agent data | Verification autonomy — Pitfall 4.12 | Added `_AUTH_HEADERS` with dashboard secret to first-run-audit.py. Added `Check: Auth token blocks unauthorized /api/agents` assertion. Added `Check: observeco desktop --help works`. |

---

## Appendix A: Quick Reference — 30-Second Gate Check

1. Run the data-pipeline-audit.sh
2. Run cross-ref-verify.sh
3. Check combined score ≥72/94
4. Verify Layer F (First-Run) ALL 9 items pass — this layer has NO exceptions
5. Get human sign-off
6. Ship

## Appendix B: Scripts Directory

```
specs/scripts/
├── cross-ref-verify.sh        # Verify all spec cross-references
├── data-pipeline-audit.sh     # Audit writer/reader per table
├── fstring-leak-detect.sh     # Detect f-string leaks in responses
├── lifecycle-test-suite.py    # 12 lifecycle tests for daemons
├── first-run-audit.py          # CI-enforceable first-run state assertions (F1-F9)
└── score-gate.py              # Calculate combined gate score
```

---

A feature that passes all ten playbooks independently can still fail when they aren't checked together. This gate prevents that — by forcing convergence before every ship.
