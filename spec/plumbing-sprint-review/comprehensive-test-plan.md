# ObserveCo v0.2.0 — Engineering Test Plan (Rebuilt)

**Author:** Main
**Date:** 2026-06-10
**Scope:** Every module, API, CLI, UI, integration, security boundary, failure mode, and data path in ObserveCo + CRM.
**Gate:** P0=100%, P1≥95%, P2≥80%, P3≥50% — all counted **after** false-positive elimination.

---

## 0. Foundations (Read First)

### 0.1 Severity Scale

| Level | Meaning | Ship Block? | Response |
|-------|---------|------------|----------|
| **P0** | Data loss, security hole, broken core flow (install→trial→pro→validate) | Yes | Fix before any further testing |
| **P1** | Feature broken but workaround exists, degraded UX, incorrect behavior | Yes | Fix before human test |
| **P2** | Cosmetic issue, edge case, missing polish | No | Fix post-launch unless P0/P1 clear |
| **P3** | Nice-to-have, future optimization, documentation gap | No | Deferred to next sprint |

### 0.2 Gate Criteria

| Gate | Requirement |
|------|-------------|
| **Auto suite pass** | All 285 auto tests ✅ (0 P0/P1 failures) |
| **Manual suite pass** | All 65 manual tests ✅ on first human run |
| **E2E flows pass** | 11/11 integration flows ✅ (P0=100%) |
| **Security tests pass** | 0 exploitable findings (all severity levels) |
| **CRM tests pass** | All P0/P1 CRM tests ✅ |
| **Ready for human test (Phase 7)** | All above gates met |

### 0.3 Fixture & Isolation Strategy

Each test gets a **dedicated temp directory** under `/tmp/observeco-test-XXXXX/` with:

```
/tmp/observeco-test-<uuid>/
  ├── pulse.db          # Fresh SQLite DB (schema applied)
  ├── license.json      # Pre-seeded or empty
  ├── billing.json      # Pre-seeded or empty
  ├── agents.json       # Mock agent list
  └── config.yaml       # Minimal valid config
```

- **Tests that modify state** → use temp fixture, DB is fresh per test class
- **Tests that read state** → can share fixture
- **CRM tests** → use **production Supabase** (`observeco-license-crm`). Acceptable because CRM actions are admin-only, low volume, and reversible. Test data is clearly identifiable (email suffix: `-test@example.com`).
- **Stripe tests** → **fully mocked** via `responses` library. No real Stripe API calls in automated tests. Mock verifies: correct endpoint, correct payload, correct error handling, correct state transitions. Stripe E2E (real Checkout → redirect → success) is manual-only test 23.3.
- **HTTP mocks** → `responses` library for Stripe/Supabase API calls in automated tests
- **Timed tests** → `freezegun` library to mock `datetime.now()` for trial expiry, cooldown, pruning

### 0.4 Environment Spec

| Resource | Auto tests | Manual/E2E |
|----------|-----------|------------|
| Supabase | Production (`observeco-license-crm`). Test data suffixed `-test@example.com` | Same |
| Stripe | **Fully mocked** (`responses` library) — never calls real Stripe API | Live keys (`sk_live_...`) from billing.json |
| Dashboard | 127.0.0.1:random-port | 127.0.0.1:9121 |
| LLM | Mock (return static responses) | Real local Ollama / cloud |
| CRM Vercel | N/A (no auto CRM tests call Vercel directly — use API mocks) | `observeco-license-crm.vercel.app` |
| macOS path | `~/Library/Application Support/observeco/` | Same (documented as macOS-only) |

---

## 1. CLI Entry Point (`src/observeco/cli.py`) — 18 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 1.1 | `observeco --help` shows all commands | P0 | Auto | stdout contains all 7 top-level commands: pulse, chisel, clawforge, dashboard, billing, graph, mcp | ❓ |
| 1.2 | `observeco --version` returns semver | P0 | Auto | stdout matches `/v?\d+\.\d+\.\d+/` | ❓ |
| 1.3 | `observeco --help` exits 0 | P0 | Auto | returncode == 0 | ❓ |
| 1.4 | `observeco` (bare, no subcommand) exits 0 showing help | P1 | Auto | returncode == 0, stdout contains "Usage" | ❓ |
| 1.5 | `observeco nonexistent-subcommand` exits 2 with error msg | P1 | Auto | returncode != 0, stderr contains "Error" or "No such command" | ❓ |
| 1.6 | `observeco pulse --help` shows subcommands | P0 | Auto | Contains "check" and "circuit" | ❓ |
| 1.7 | `observeco chisel --help` shows all 7 subcommands | P1 | Auto | Contains trim, drift, compress, skills, cards, artifacts, config | ❓ |
| 1.8 | `observeco billing --help` shows 5 subcommands | P0 | Auto | Contains configure, status, checkout, activate, key | ❓ |
| 1.9 | `observeco dashboard --help` shows flags | P0 | Auto | Contains --port, --show-token, --static | ❓ |
| 1.10 | `observeco graph --help` shows subcommands | P2 | Auto | Contains index, watch | ❓ |
| 1.11 | `observeco mcp --help` shows options | P2 | Auto | Contains --port | ❓ |
| 1.12 | `observeco billing status` returns JSON with license_type field (with fixture) | P0 | Auto | Uses temp fixture, returns valid JSON with license_type key | ❓ |
| 1.13 | `observeco billing activate <key>` with valid key (fixture) | P1 | Auto | Returns is_pro=true | ❓ |
| 1.14 | `observeco billing key generate` returns OBS-PRO-XXXXXXXX-XXXX format (timeout 5s) | P1 | Auto | Matches regex `^OBS-PRO-[0-9A-F]{8}-[0-9A-F]{6}$` | ❓ |
| 1.15 | `observeco billing key list` shows table with headers | P1 | Auto | stdout contains "Issued To", "Plan", "Revoked" | ❓ |
| 1.16 | `observeco billing key revoke <key>` marks key revoked | P1 | Auto | Subsequent list shows revoked=true for that key | ❓ |
| 1.17 | `observeco billing configure --stripe-key` writes billing.json | P1 | Auto | billing.json contains stripe_secret_key with the provided value | ❓ |
| 1.18 | `observeco mcp` starts in stdio mode without crash (timeout 3s) | P3 | Auto | Process starts, doesn't crash within 3s, can be killed cleanly | ❓ |

---

## 2. Billing & Licensing (`src/observeco/billing.py`) — 26 tests

### 2.1 Unit: Config

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 2.1 | `BillingConfig()` with no args: is_active=False, keys empty | P0 | Auto | All fields at defaults as defined in dataclass | ✅ |
| 2.2 | `BillingConfig()` configure sets keys then serializes | P1 | Auto | After set + save, reloaded config has same values | ✅ |

### 2.2 Unit: Key Generation

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 2.3 | `generate_key()` returns `OBS-PRO-XXXXXXXX-XXXX` | P0 | Auto | Regex match, exactly 27 chars | ❓ |
| 2.4 | `generate_key()` called twice returns **different** keys | P1 | Auto | key1 != key2 | ❓ |
| 2.5 | `generate_key()` concurrent 10 calls returns 10 unique keys | P2 | Auto | len(set(keys)) == 10 | ❓ |
| 2.6 | `validate_key()` returns True for self-generated key | P0 | Auto | validate_key(generate_key()) == True | ❓ |
| 2.7 | `validate_key()` returns False for tampered key (wrong checksum) | P1 | Auto | validate_key("OBS-PRO-AAAAAAAAB-BBBBBB") == False | ❓ |
| 2.8 | `validate_key()` returns True for legacy format (pre-checksum) | P1 | Auto | validate_key("OBS-PRO-7DC9A444-FA24BF") == True | ❓ |
| 2.9 | `revoke_key()` on existing key: revoked=true, revoked_at set | P0 | Auto | issued_keys[key].revoked == True, revoked_at is timestamp | ❓ |
| 2.10 | `revoke_key()` on already-revoked key: idempotent, no error | P1 | Auto | Second call returns success, state unchanged | ❓ |
| 2.11 | `revoke_key()` on nonexistent key: returns error | P1 | Auto | Raises KeyError or returns error dict | ❓ |
| 2.12 | `list_keys()` returns dict with expected fields | P1 | Auto | Each entry has: issued_at, issued_to, revoked, revoked_at, plan, activated_by, activated_at | ❓ |

### 2.3 Unit: Stripe (Mocked — Never Real Keys)

All Stripe tests use `stripe.TestHelpers` or `responses` library. Never touch live Stripe.

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 2.13 | `create_checkout_session()` with test keys creates Stripe Checkout Session | P0 | Auto | Returns dict with session_id (starts with "cs_test_"), url (contains "stripe.com") | ❓ |
| 2.14 | `create_checkout_session()` with missing/empty keys returns simulated | P0 | Auto | session_id contains "simulated" | ✅ |
| 2.15 | `create_checkout_session()` with plan="team" uses team_price_id | P1 | Auto | API call to Stripe uses price_team_monthly or equivalent | ❓ |
| 2.16 | `create_checkout_session()` with invalid plan name raises error | P1 | Auto | Returns error dict, no Stripe API call made | ❓ |
| 2.17 | `handle_webhook()` with valid Stripe signature passes verification | P0 | Auto | verify_signature returns True, handler processes event | ❓ |
| 2.18 | `handle_webhook()` with tampered signature returns 400 | P1 | Auto | Signature mismatch returns error before any state change | ❓ |
| 2.19 | `handle_webhook()` checkout.session.completed activates license | P0 | Auto | After webhook, license status = "active", plan = "solo" | ❓ |
| 2.20 | `handle_webhook()` customer.subscription.deleted sets cancelled | P1 | Auto | After webhook, license status = "cancelled" | ❓ |
| 2.21 | `handle_webhook()` invoice.payment_failed sets past_due metadata | P1 | Auto | After webhook, metadata contains payment_failed=true | ❓ |
| 2.22 | `handle_webhook()` with unknown event type: no-op | P1 | Auto | No state change, returns 200 | ❓ |
| 2.23 | Webhook + manual activation race: webhook arrives during admin key activation | P2 | Auto | Both processed, no duplicate or corruption | ❓ |

### 2.4 Unit: Persistence

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 2.24 | `billing.json` missing on first use: created with defaults | P0 | Auto | File exists after config access, is_active=False | ❓ |
| 2.25 | `billing.json` corrupted (invalid JSON): falls back to defaults, reports error | P1 | Auto | Validity check returns error, default config loads | ❓ |
| 2.26 | `billing.json` with unexpected extra fields: forward-compat, no crash | P1 | Auto | Extra fields preserved, known fields readable | ❓ |

---

## 3. License State API (`licenses_api.py` + `license.py`) — 22 tests

### 3.1 Status Endpoints

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 3.1 | GET /api/licenses/status with active trial: is_pro=true, days_remaining > 0 | P0 | Auto | Fixture with fresh trial. Response has license_type="trial", is_pro=true, trial_days_remaining > 0 | ❓ |
| 3.2 | GET /api/licenses/status after trial consumed (no license): is_pro=false | P0 | Auto | Fixture with consumed trial. is_pro=false, license_type="free" | ❓ |
| 3.3 | GET /api/licenses/status with admin-key-activated Pro: is_pro=true | P0 | Auto | Fixture with issued key activated. is_pro=true, plan="solo" | ❓ |
| 3.4 | GET /api/licenses/status with revoked key: is_pro=false | P1 | Auto | Key was revoked after activation. is_pro=false after re-validation | ❓ |
| 3.5 | GET /api/licenses/status without auth token: returns 401 | P0 | Auto | Response is 401 with error message | ❓ |
| 3.6 | GET /api/licenses/status with invalid token: returns 401 | P0 | Auto | Response is 401 | ❓ |

### 3.2 Admin Key Endpoints

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 3.7 | POST /api/licenses/admin/generate with valid admin key: returns key | P0 | Auto | Returns JSON with license_key matching OBS-PRO format, issued_to, plan | ❓ |
| 3.8 | POST /api/licenses/admin/generate without admin key: 401 | P1 | Auto | 401 response | ❓ |
| 3.9 | POST /api/licenses/admin/revoke with valid key: marks revoked | P0 | Auto | GET /admin/keys shows revoked=true for that key | ❓ |
| 3.10 | POST /api/licenses/admin/revoke on nonexistent key: returns error | P1 | Auto | Returns 404 or error message | ❓ |
| 3.11 | GET /api/licenses/admin/keys with auth: returns list | P1 | Auto | Returns JSON array of keys with per-key status | ❓ |
| 3.12 | GET /api/licenses/admin/keys-page with auth: returns HTML 200 | P2 | Auto | Content-Type text/html, body contains "Generate" and "Revoke" | ❓ |

### 3.3 Activation & Trial

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 3.13 | POST /api/licenses/activate with valid key: unlocks Pro | P0 | Auto | is_pro=true, activated_at and activated_by set | ❓ |
| 3.14 | POST /api/licenses/activate with revoked key: returns error | P0 | Auto | is_pro stays false, error message cites revoked | ❓ |
| 3.15 | POST /api/licenses/activate with invalid format: returns error | P1 | Auto | Error about invalid key format | ❓ |
| 3.16 | POST /api/licenses/activate called twice with same key: idempotent | P1 | Auto | Second call returns success but doesn't double-activate | ❓ |
| 3.17 | POST /api/licenses/activate with two valid keys concurrently: both activate | P2 | Auto | Both return success, no state corruption | ❓ |
| 3.18 | POST /api/licenses/cancel-trial: trial_consumed=true, license_type=free | P0 | Auto | After cancel: license_type="free", trial_consumed=true | ❓ |
| 3.19 | POST /api/licenses/cancel-trial when already free: returns error | P1 | Auto | Returns error "No active trial to cancel" | ❓ |
| 3.20 | POST /api/licenses/cancel-trial when already Pro: returns error | P1 | Auto | Returns error "Cannot cancel trial on paid license" | ❓ |

### 3.4 Billing Endpoints

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 3.21 | POST /api/billing/portal with active subscription: returns stripe.com URL | P0 | Auto | URL contains "stripe.com" or "billing.stripe.com" | ❓ |
| 3.22 | POST /api/billing/portal without subscription: returns error | P1 | Auto | Error about no active subscription | ❓ |

---

## 4. Dashboard (`src/observeco/dashboard/server.py`) — 35 tests

### 4.1 Server Startup

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 4.1 | Dashboard starts on specified port, returns 200 on root | P0 | Auto | `--port 0` (random), root returns 200 | ❓ |
| 4.2 | Dashboard auto-finds free port (parallel instance): different port assigned | P1 | Auto | Start 2 instances, assert different ports, both respond 200 | ❓ |
| 4.3 | Dashboard without token: returns 401 on protected routes | P0 | Auto | GET /api/agents without header: 401 | ❓ |
| 4.4 | Dashboard with valid token: returns 200 | P0 | Auto | GET /api/licenses/status with valid token: 200 | ❓ |
| 4.5 | Dashboard with malformed token header: 401, no crash | P1 | Auto | Token "Bearer ", "Bearer garbage", empty: all 401 | ❓ |
| 4.6 | Dashboard root (/) redirects to /agents or renders HTML | P0 | Auto | Status 200, Content-Type text/html | ❓ |
| 4.7 | Dashboard serves static assets (CSS/fonts) | P1 | Auto | Common static paths return 200, correct Content-Type | ❓ |
| 4.8 | Dashboard --static mode generates static output | P2 | Auto | Output directory created with index.html and assets | ❓ |

### 4.2 Fleet View

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 4.9 | Fleet view renders at /api/agents | P0 | Manual | Returns HTML with agent cards — each has name, status dot, type label, framework, token bar, drift sparkline, error badge | ❓ |
| 4.10 | Type-based grouping (Agents/Services/Workflows) | P1 | Manual | Groups are collapsible, correct type label per card, mix of types renders correctly | ❓ |
| 4.11 | Health drill-down modal: click → opens with 4 sections | P1 | Manual | Pulse timeline, annotated timeline, categorized summary, latest check all present | ❓ |
| 4.12 | Guard drill-down modal: click → opens with 4 sections | P1 | Manual | Status, failure timeline, explanation, settings all present | ❓ |
| 4.13 | Error drill-down modal: click → opens with Pro upsell for >24h | P1 | Manual | Error timeline + verdict + Pro upsell banner for free users | ❓ |
| 4.14 | Fleet view empty state: no agents → shows guidance | P1 | Manual | "No agents discovered" with "Add an agent" or discovery prompt | ❓ |
| 4.15 | Fleet view: 5 clickable metric rows per card | P1 | Manual | Health/Guard/Errors/Brain size/Composition all click, open correct modals | ❓ |
| 4.16 | Token breakdown bar chart renders correctly | P2 | Manual | Colored bars per component (identity, skills, guidance, tools, memory), legend | ❓ |
| 4.17 | 7-day drift trend renders per component | P2 | Manual | 7 bars per component, color-coded (green/red), tooltip on hover | ❓ |

### 4.3 Dashboard Features

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 4.18 | Heal tab triggers diagnosis: click → result shows | P1 | Manual | Click Heal → loading spinner → diagnosis result with verdict and reasoning | ❓ |
| 4.19 | Alerts feed loads with severity colors | P1 | Manual | Red/Amber/Yellow/Green badges, NEW indicator for unviewed, cumulative downtime banner visible | ❓ |
| 4.20 | Memory Garden in Brain Analysis: shows debt score | P2 | Manual | Debt score (0-100), duplicates count, contradictions count, per-agent summary | ❓ |
| 4.21 | License status card: trial active → shows countdown + Subscribe + Cancel buttons | P0 | Manual | Correct plan name, days remaining, both buttons visible and clickable | ❓ |
| 4.22 | Pro modal opens with Subscribe (Stripe checkout) button | P0 | Manual | Modal shows plan name, price, features, Subscribe button → opens Stripe checkout | ❓ |
| 4.23 | Pro modal "Already have a license key?" field works | P0 | Manual | Enter valid admin key → Pro unlocks inline, badge updates without page reload | ❓ |
| 4.24 | Cancel Trial modal: click → confirm → trial cancelled, badge updates | P0 | Manual | Confirm modal shows warning, after confirm badge says Free | ❓ |
| 4.25 | Manage Billing button (paid users): opens Stripe Customer Portal | P1 | Manual | Opens billing portal in new tab, shows subscription and payment options | ❓ |
| 4.26 | End-of-trial banner: <7 days remaining → banner visible | P1 | Manual | Banner text includes days remaining, has Subscribe link | ❓ |
| 4.27 | Free badge in header: always visible | P1 | Manual | "Free forever · MIT license · No cloud" visible in all pages | ❓ |
| 4.28 | Communication Pathway Map renders with at least 2 graph nodes (class .graph-node in DOM) | P2 | Manual | DOM contains node elements with class .graph-node, count >= 2, edges visible, subgraph folding controls present | ❓ |
| 4.29 | Glossary & FAQ page renders | P3 | Manual | Loads without error, shows all defined entries | ❓ |
| 4.30 | Dashboard DB unreachable → shows error state, doesn't crash | P1 | Auto | Mock DB failure, dashboard returns 500 with readable error, server stays up | ❓ |
| 4.31 | **Accessibility:** Screen reader — all interactive elements have ARIA labels | P2 | Manual | Tab through fleet view: each button/modal trigger has aria-label or visible text label, not just icon | ❓ |
| 4.32 | **Accessibility:** Keyboard navigation — all flows work without mouse | P2 | Manual | Tab through fleet → Enter opens modal → Tab through modal content → Escape closes → focus returns to trigger | ❓ |
| 4.33 | **Accessibility:** Color contrast — status dots, severity badges, links meet WCAG AA (4.5:1) | P2 | Manual | Red/green dots are distinguishable without color (pattern or icon supplement) | ❓ |
| 4.34 | **Accessibility:** Focus order — modal open → focus trapped inside → close → focus returns | P2 | Manual | Tab cycling stays within open modal, doesn't reach page elements behind it | ❓ |
| 4.35 | **Accessibility:** Touch targets on mobile — all tappable areas ≥ 44×44px at 375px width | P2 | Manual | Buttons, status dots, modal triggers not clipped or overlapping at 375px viewport | ❓ |

---

## 5. Pulse Check (`src/observeco/pulse/check.py`) — 16 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 5.1 | `_probe_agent()` returns (status, rt, error, metadata) tuple | P0 | Auto | len == 4, status in ("alive","dead","error") | ✅ |
| 5.2 | `_probe_agent()` with `echo ok` → alive | P0 | Auto | status == "alive" | ✅ |
| 5.3 | `_probe_agent()` with `false` → dead | P0 | Auto | status == "dead" | ❓ |
| 5.4 | `_probe_agent()` with HTTP 200 → alive | P0 | Auto | Mock HTTP 200, status == "alive" | ❓ |
| 5.5 | `_probe_agent()` with HTTP 500 → error | P0 | Auto | Mock HTTP 500, status == "error" | ❓ |
| 5.6 | `_probe_agent()` with HTTP 404 → error | P1 | Auto | Mock HTTP 404, status == "error" or "dead" | ❓ |
| 5.7 | `_probe_agent()` with HTTP timeout (no response) → error | P0 | Auto | Mock timeout (socket hang), status == "error", error contains "timeout" | ❓ |
| 5.8 | `_probe_agent()` with connection refused → dead | P0 | Auto | Mock ECONNREFUSED, status == "dead" | ❓ |
| 5.9 | `_probe_agent()` with empty health_check string → uses pgrep | P1 | Auto | Falls back to process name check | ❓ |
| 5.10 | `_probe_agent()` timeout boundary: 9.9s is acceptable, 10.1s is not | P1 | Auto | Mock 9.9s response → alive; mock 10.1s → timeout | ❓ |
| 5.11 | `_probe_agent()` with shell metacharacters in health_check: safely executed | P1 | Auto | `echo hello; rm -rf /` — only `echo hello` runs, no side effects | ❓ |
| 5.12 | `classify_restart()` 0 → healthy | P0 | Auto | rtype == "healthy" | ✅ |
| 5.13 | `classify_restart()` SIGSEGV → crash | P0 | Auto | rtype == "crash" | ✅ |
| 5.14 | `classify_restart()` MemoryError → crash | P0 | Auto | rtype == "crash" | ✅ |
| 5.15 | `classify_restart()` FileNotFoundError + .stat() → toctou | P0 | Auto | rtype == "toctou" | ✅ |
| 5.16 | `_find_agent_log()` no log → None | P1 | Auto | Returns None | ✅ |
| 5.17 | `_read_last_n_lines()` missing file → "" | P1 | Auto | Returns "" | ✅ |
| 5.18 | `_read_last_n_lines()` file with 5 lines, n=3 → last 3 | P1 | Auto | Returns lines 3-5 | ❓ |

---

## 6. Circuit Breaker (`src/observeco/pulse/circuit.py`) — 10 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 6.1 | `run_circuit()` with no failures → no crash, state clean | P0 | Auto | Returns None or empty dict | ✅ |
| 6.2 | `run_circuit()` with 3 failures → circuit tripped (stopped) | P0 | Auto | Circuit status == "stopped" after 3rd failure | ❓ |
| 6.3 | `run_circuit()` with 2 failures → NOT tripped | P0 | Auto | Circuit status != "stopped" (1 away from trip) | ❓ |
| 6.4 | `run_circuit()` with 3 failures on one agent, 0 on another → only first trips | P0 | Auto | Agent A stopped, Agent B alive | ❓ |
| 6.5 | `run_circuit()` reset on tripped agent → clears failures | P0 | Auto | After reset, failure_count == 0, status == "active" | ❓ |
| 6.6 | `run_circuit()` reset on nonexistent agent → no crash | P1 | Auto | Returns gracefully | ✅ |
| 6.7 | `run_circuit()` cooldown: 0 failures during cooldown, no retry | P1 | Auto | Mock time — during cooldown period, circuit doesn't re-probe | ❓ |
| 6.8 | `run_circuit()` cooldown expiry: auto-retry after cooldown | P1 | Auto | Mock time — after cooldown expires, circuit re-probes agent | ❓ |
| 6.9 | Circuit state persists in DB across Dashboard restart | P1 | Auto | Start dashboard, trip circuit, restart, query circuit state — matches pre-restart | ❓ |
| 6.10 | Multiple agents with independent circuit breakers | P1 | Auto | Agent A tripped, Agent B untripped — queries return independent states | ❓ |

---

## 7. Chisel — Trim (`src/observeco/chisel/trim.py`) — 12 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 7.1 | `_classify_line()` returns correct component | P0 | Auto | identity/skills/memory/guidance based on section headers | ✅ |
| 7.2 | `_classify_line()` empty → guidance | P1 | Auto | Returns "guidance" | ✅ |
| 7.3 | `_classify_line()` edge cases | P1 | Auto | Mixed case, partial matches, non-header text | ✅ |
| 7.4 | `_estimate_tokens()` always ≥ 1 | P0 | Auto | Returns ≥ 1 | ✅ |
| 7.5 | `_estimate_tokens()` longer text → more tokens | P1 | Auto | 1000 chars > 10 chars | ✅ |
| 7.6 | `run_trim()` accepts stdin pipe | P1 | Auto | Input via pipe produces output | ✅ |
| 7.7 | `run_trim()` with --mode lite: only guidance compressed, identity/skills unchanged | P1 | Auto | Compare output — guidance section shortened, identity/skills match original exactly | ❓ |
| 7.8 | `run_trim()` with --mode full: all sections potentially compressed | P1 | Auto | Output shorter than input, token savings > 0 | ❓ |
| 7.9 | `run_trim()` --dry-run: no file changes (checksum match on all input files) | P0 | Auto | SHA256 of all input files unchanged after dry-run | ❓ |
| 7.10 | `run_trim()` with 1MB input: no OOM, produces output | P2 | Auto | Completes within 30s, output < input | ❓ |
| 7.11 | `run_trim()` with binary input: no crash, handles gracefully | P2 | Auto | Returns error message about invalid input | ❓ |
| 7.12 | `run_trim()` token budget: output is within budget limit | P1 | Auto | Estimate tokens of output ≤ 1.2× token budget (allow 20% overhead) | ❓ |

---

## 8. Chisel — Drift (`src/observeco/chisel/drift.py`) — 6 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 8.1 | `run_drift()` no crash | P0 | Auto | No unhandled exception | ✅ |
| 8.2 | Drift detects new component added between snapshots | P1 | Auto | New component flagged as "added" in drift diff | ❓ |
| 8.3 | Drift detects component removed between snapshots | P1 | Auto | Removed component flagged as "deleted" in drift diff | ❓ |
| 8.4 | Drift computes similarity score (0.0–1.0) | P1 | Auto | Score is float in [0.0, 1.0] | ❓ |
| 8.5 | Drift with no existing baseline → first sample captured | P1 | Auto | No diff, baseline stored in DB | ❓ |
| 8.6 | Drift with empty agent list → no crash, sets empty baseline | P2 | Auto | Baseline empty, no error | ❓ |

---

## 9. ClawForge — Profile (`src/observeco/clawforge/profile.py`) — 4 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 9.1 | `_estimate_tokens()` returns ≥ 1 | P0 | Auto | max(1, chars/4) | ✅ |
| 9.2 | Profile loads from fixture config path | P1 | Auto | Returns dict with name, type, framework, health_check | ❓ |
| 9.3 | Profile with missing config → returns error, not crash | P1 | Auto | Graceful error message | ❓ |
| 9.4 | `observeco clawforge profile --help` shows options | P2 | Auto | stdout contains relevant flags | ❓ |

---

## 10. ClawForge — Load (`src/observeco/clawforge/load.py`) — 6 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 10.1 | `_classify_intent("fix error bug crash") → debug | P0 | Auto | Returns "debug" | ✅ |
| 10.2 | `_classify_intent("what is going on") → status | P0 | Auto | Returns "status" | ✅ |
| 10.3 | `_classify_intent("add feature") → feature-request | P0 | Auto | Returns "feature-request" | ✅ |
| 10.4 | `_classify_intent("change config") → config-change | P0 | Auto | Returns "config-change" | ✅ |
| 10.5 | `_classify_intent("hello") → general-query | P0 | Auto | Returns "general-query" | ✅ |
| 10.6 | `run_load()` without stdin: handles gracefully | P1 | Auto | No crash, returns usage or error message | ✅ |

---

## 11. ClawForge — Garden (`src/observeco/clawforge/garden.py`) — 8 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 11.1 | `_find_duplicates()` finds exact duplicate lines | P0 | Auto | Returns list with ≥ 1 duplicate entry | ✅ |
| 11.2 | `_find_duplicates([])` → [] | P1 | Auto | Returns [] | ✅ |
| 11.3 | `_find_duplicates()` no dupes → [] | P1 | Auto | Returns [] | ✅ |
| 11.4 | `_find_contradictions()` finds contradicting statements | P0 | Auto | Returns list ≥ 1 | ✅ |
| 11.5 | `_find_contradictions([])` → [] | P1 | Auto | Returns [] | ✅ |
| 11.6 | Debt score computation returns 0–100 | P1 | Auto | Score is int in [0, 100] | ❓ |
| 11.7 | `_find_duplicates()` with 10K lines: completes under 5s | P2 | Auto | Runtime < 5s | ❓ |
| 11.8 | `_find_contradictions()` near-match semantics (not exact string): handled | P2 | Auto | Semantically contradictory but not exact string matches produce fewer false positives than exact-only | ❓ |

---

## 12. Auto-Detect (`src/observeco/auto_detect.py`) — 10 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 12.1 | `run_discover()` no crash | P0 | Auto | Returns agents list (possibly empty) | ✅ |
| 12.2 | `run_discover()` with fixture Hermes profile dir → finds agents | P1 | Auto | Mock 2 profiles with SOUL.md + config.yaml → agents found | ❓ |
| 12.3 | `run_discover()` with fixture OpenClaw config → finds agents | P1 | Auto | Mock OpenClaw config with agent entries → agents found | ❓ |
| 12.4 | `run_discover()` with fixture launchd plist → finds service | P1 | Auto | Mock plist → service discovered | ❓ |
| 12.5 | `run_discover()` with fixture cron manifest → finds workflow | P1 | Auto | Mock cron entries → workflow discovered | ❓ |
| 12.6 | `run_discover()` filters out config keys (allowed_chats, api_keys) | P1 | Auto | Config key entries not in output | ❓ |
| 12.7 | `run_discover()` on empty filesystem: returns empty, no crash | P1 | Auto | Returns empty list, no FileNotFound or crash | ❓ |
| 12.8 | `run_add("test-agent", "custom", "echo ok")` creates config entry | P1 | Auto | Agent appears in config.agents | ✅ |
| 12.9 | `run_add()` with missing name → error | P1 | Auto | Validation error returned | ❓ |
| 12.10 | Agent exclusion persist: DELETE via API → agents.json has exclusion entry | P1 | Auto | agents.json written with excluded name | ❓ |

---

## 13. Database (`src/observeco/db.py`) — 10 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 13.1 | Database initializes in temp path → schema applied | P0 | Auto | Returns Database, tables exist (agents, pulse_results, circuit_breakers, errors, turns) | ✅ |
| 13.2 | Schema migration: fresh DB creates all expected tables | P0 | Auto | Query sqlite_master, confirm all table names present | ❓ |
| 13.3 | CRUD: insert pulse result → select returns it → delete removes it | P0 | Auto | Full cycle without error | ❓ |
| 13.4 | DB close: no crash, no dangling locks | P1 | Auto | Close returns cleanly, SQLite lock released | ✅ |
| 13.5 | Concurrent write (2 threads): no IntegrityError or serialization failure | P1 | Auto | 2 threads insert 100 records each, all 200 present | ❓ |
| 13.6 | DB pruning: records older than retention window removed | P1 | Auto | Insert records with old timestamps (mocked time), run prune, confirm deleted | ❓ |
| 13.7 | DB migration from v0.1 schema to v0.2: existing data preserved | P2 | Auto | Seed v0.1 schema, run migration, query — data intact, new columns present | ❓ |
| 13.8 | DB file corruption: on open, fallback or clear error (no silent data loss) | P2 | Auto | Write corrupted bytes to .db file, open — should report error or recreate | ❓ |
| 13.9 | DB disk full: graceful error, no data corruption in existing records | P2 | Auto | Create filesystem with quota, fill disk, trigger write — error not crash | ❓ |
| 13.10 | DB query with no results: returns empty, not None | P1 | Auto | Query nonexistent agent_id → empty list, not crash | ❓ |

---

## 14. Config (`src/observeco/config.py`) — 8 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 14.1 | `load_config()` from fixture path: returns Config with agents | P0 | Auto | config.agents is list, each has name, framework, health_check | ✅ |
| 14.2 | `load_config()` from nonexistent path: returns defaults | P1 | Auto | Returns Config with default values, no crash | ❓ |
| 14.3 | Config with malformed YAML (garbage): returns default, reports parse error | P1 | Auto | Parse error logged, default config returned | ❓ |
| 14.4 | Config with empty YAML file: returns default | P1 | Auto | No crash, returns Config with empty fields | ❓ |
| 14.5 | Config with valid YAML but wrong schema (no agents key): returns Config with empty agents | P1 | Auto | Empty agents list, no crash | ❓ |
| 14.6 | Config with extra unknown fields: preserved, not stripped | P2 | Auto | After load → save → load, extra fields still present | ❓ |
| 14.7 | Config missing required field (framework): validation error | P1 | Auto | AgentConfig rejected, error raised | ❓ |
| 14.8 | Config with encoding issues (UTF-8 BOM): parsed correctly | P2 | Auto | BOM stripped, content parsed | ❓ |

---

## 15. Directory Management (`src/observeco/dirs.py`) — 5 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 15.1 | Data dir created on access: path.exists() after get_data_dir() | P0 | Auto | `~/.observeco/` created (or temp equivalent) | ❓ |
| 15.2 | Config dir resolves to absolute path | P1 | Auto | Returned path is absolute, not relative | ❓ |
| 15.3 | License dir resolves to macOS path (platform check) | P1 | Auto | On macOS: Path(`~/Library/Application Support/observeco/`). On others: Path(`~/.local/share/observeco/`) | ❓ |
| 15.4 | App support dir: created on demand | P1 | Auto | First call creates parent, second call uses existing | ❓ |
| 15.5 | Platform detection: Linux uses ~/.local/share, macOS uses ~/Library/Application Support | P2 | Auto | Both platforms return platform-appropriate path | ❓ |

---

## 16. Watch Daemon (`src/observeco/watch.py`) — 8 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 16.1 | Daemon starts without crash | P0 | Auto | Process starts, sends SIGTERM, exits cleanly | ❓ |
| 16.2 | Daemon probes agents at ~30s interval | P1 | Auto | Mock time, advance 30s, assert probe called for each agent | ❓ |
| 16.3 | Daemon detects dead agent: status written as "dead" | P0 | Auto | Mock agent returns non-zero → status "dead" in DB | ❓ |
| 16.4 | Daemon writes results to pulse_results table | P0 | Auto | After one loop, pulse_results has ≥ 1 entry per agent | ❓ |
| 16.5 | Daemon stops cleanly on SIGTERM: no orphan processes | P1 | Auto | After SIGTERM, process exits, no child processes remain | ❓ |
| 16.6 | Daemon crash recovery: if killed mid-loop, restarts on next watch start | P2 | Auto | Simulate kill, restart daemon — DB state consistent | ❓ |
| 16.7 | Daemon resource usage: CPU < 5%, memory < 50MB after 1h | P2 | Auto | Monitor resource usage over 1h (or accelerated) | ❓ |
| 16.8 | Daemon with no agents configured: starts, no crash, empty loop | P1 | Auto | Starts, runs one loop, stops cleanly | ❓ |

---

## 17. Heal (`src/observeco/heal.py`) — 8 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 17.1 | `trigger_heal("agent-name")` returns diagnosis dict | P0 | Auto | Returns dict with verdict, reasoning, action_taken | ❓ |
| 17.2 | Heal with LLM (Pro/trial): diagnosis has 7 categories | P1 | Auto | Verdict covers: crash/regression/resource/config/upstream/network/unknown | ❓ |
| 17.3 | Heal without LLM (Free after trial): static fallback, no LLM API call | P0 | Auto | Mock LLM — assert no LLM call made, static response returned | ❓ |
| 17.4 | L1 auto-recover: dead agent restarted within 5s | P1 | Auto | Mock agent dead, trigger heal, assert restart command executed within 5,000ms | ❓ |
| 17.5 | L2 proactive detection: memory bloat flagged | P2 | Auto | Inject memory usage > 90%, assert bloat detection triggered | ❓ |
| 17.6 | Heal on agent already healthy: returns "no action needed" | P1 | Auto | Returns verdict with no action taken | ❓ |
| 17.7 | Heal on unrecoverable agent: returns error, doesn't enter retry loop | P1 | Auto | After N retries, returns "unrecoverable" verdict | ❓ |
| 17.8 | Concurrent heal triggers on same agent: serialized, no race | P2 | Auto | 2 simultaneous heal calls on same agent → both return, state consistent | ❓ |

---

## 18. Snapshot / LLM Service (`src/observeco/snapshot.py`) — 9 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 18.1 | LLM service initializes: returns object with diagnose() method | P0 | Auto | Service has diagnose function that accepts context dict | ❓ |
| 18.2 | LLM diagnosis with mock LLM: returns structured verdict | P0 | Auto | Mock returns JSON → parsed to verdict dict with expected keys | ❓ |
| 18.3 | LLM gating: Free tier → no LLM call, static fallback | P0 | Auto | Mock LLM, free license — assert zero calls to LLM, static response returned | ❓ |
| 18.4 | LLM timeout (60s+): returns fallback, no crash | P1 | Auto | Mock LLM hangs → after timeout, fallback returned, server still responds | ❓ |
| 18.5 | LLM returns malformed JSON: returns fallback with parse error noted | P1 | Auto | Mock returns "garbage" → fallback returned, error logged | ❓ |
| 18.6 | LLM unreachable (network error): falls back gracefully | P1 | Auto | Mock connection refused → fallback returned, no crash | ❓ |
| 18.7 | Health diagnosis consumer: produces output | P1 | Auto | Call health consumer with mock LLM → returns diagnosis | ❓ |
| 18.8 | Error classification consumer: produces output | P1 | Auto | Call error consumer with mock LLM → returns classification | ❓ |
| 18.9 | First-run guide consumer: produces output | P1 | Auto | Call guide consumer with mock LLM → returns guidance | ❓ |

---

## 19. MCP Server (`src/observeco/mcp_server.py`) — 5 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 19.1 | MCP starts in stdio mode: ready within 3s | P0 | Auto | Process starts, sends initial message, accepts input | ❓ |
| 19.2 | MCP starts in HTTP mode: binds to port, returns 200 | P1 | Auto | GET on / returns valid response | ❓ |
| 19.3 | MCP responds to valid protocol message | P0 | Auto | Valid MCP message → valid response JSON | ❓ |
| 19.4 | MCP with invalid message: returns error, doesn't crash | P1 | Auto | Garbage input → error response, server stays up | ❓ |
| 19.5 | MCP with closed stdin (stdio mode): exits cleanly | P2 | Auto | Close stdin → process exits with code 0 | ❓ |

---

## 20. Code Graph (`src/observeco/graph/`) — 8 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 20.1 | `graph index` on fixture Python file: nodes > 0 | P0 | Auto | Returns stats with nodes > 0, edges ≥ 0 | ❓ |
| 20.2 | Graph finds functions, classes, methods in index | P0 | Auto | Query for known symbol → returns node with file, line, kind | ❓ |
| 20.3 | Graph detects unchanged files (hash): status "unchanged" | P1 | Auto | Index same file twice → second call returns "unchanged" | ❓ |
| 20.4 | Graph watch detects file change within poll interval | P1 | Auto | Modify monitored file, wait, assert re-index triggered | ❓ |
| 20.5 | Graph DB query returns callers/callees | P1 | Auto | Known function → callers and callees both non-empty | ❓ |
| 20.6 | Graph ignores __pycache__ and .git | P1 | Auto | Index project with __pycache__ → zero nodes from __pycache__ | ❓ |
| 20.7 | Index 10K-file codebase: completes in < 60s | P2 | Auto | Generate fixture files, index, assert timing | ❓ |
| 20.8 | Graph query with no results: returns empty, not error | P1 | Auto | Query for "nonexistent_symbol_xyz" → empty list | ❓ |

---

## 21. Dashboard OpenTelemetry (`src/observeco/dashboard/otel.py`) — 4 tests

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 21.1 | OTel routes mount without crash | P1 | Auto | Server starts, /api/otel/* routes respond | ❓ |
| 21.2 | OTel metrics endpoint returns valid format | P2 | Auto | GET /api/otel/metrics returns Prometheus-format text or JSON | ❓ |
| 21.3 | OTel span records correct attributes | P2 | Auto | Request with OTel header → span has method, path, status_code | ❓ |
| 21.4 | OTel with unreachable backend: server stays up, metrics dropped silently | P2 | Auto | Mock collector unreachable → server still responds to other requests | ❓ |

---

## 22. CRM (Vercel — `licensing-api/`) — 22 tests

### 22.1 Auth

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 22.1 | CRM admin page loads at /admin: 200, has HTML | P0 | Auto | HTTP 200, Content-Type text/html | ✅ |
| 22.2 | CRM auth with valid API key: dashboard unlocks, shows stats | P0 | Manual | Stats cards visible, license table populated | ❓ |
| 22.3 | CRM auth with invalid key: 401, error message shown | P1 | Auto | 401 response, error text visible | ❓ |
| 22.4 | CRM auth with empty key: 401 | P1 | Auto | 401 response | ❓ |
| 22.5 | CRM API key brute force: 5 failures in 60s → rate limited | P2 | Auto | After 5 rapid failures, 429 returned for 60s | ❓ |
| 22.6 | CRM session timeout: inactive → auto-logout after 24h | P2 | Manual | After idle period, page requires re-auth | ❓ |

### 22.2 License Management

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 22.7 | Stats match actual Supabase license data | P0 | Manual | Active + Trial + Expired + Cancelled = Total | ❓ |
| 22.8 | License table renders with all columns | P0 | Manual | Email, Name, Product, Status, License Key, Created, Expires, Actions — all present | ❓ |
| 22.9 | Search by email: filters correctly | P1 | Manual | Typing email prefix → shows only matching rows | ❓ |
| 22.10 | Status dropdown filter: shows only that status | P1 | Manual | Select "Active" → only active licenses shown | ❓ |
| 22.11 | Sort by column: reorders correctly | P1 | Manual | Click "Created" → oldest first, click again → newest first | ❓ |
| 22.12 | Issue Free License: creates entry in Supabase, shows in table | P0 | Manual | Fills email/name/duration → Create → appears in table with "active" status | ❓ |
| 22.13 | Issue License with duplicate email: returns error | P1 | Manual | Same email → error "already exists" or updates existing | ❓ |
| 22.14 | Edit License: changes persist | P1 | Manual | Change email/name/expiry → Save → table shows new values | ❓ |
| 22.15 | Suspend License: status changes to "expired" | P0 | Manual | Suspend → table shows expired, user can't validate locally | ❓ |
| 22.16 | Reinstate License: status changes back to "active" | P0 | Manual | Reinstate → table shows active, user can validate | ❓ |
| 22.17 | Delete License: status → "cancelled" | P1 | Manual | Delete → status cancelled, no longer usable | ❓ |

### 22.3 Detail & Audits

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 22.18 | Detail modal: click row → opens with full info + validations | P1 | Manual | Shows email, name, status, created/expires, issued_by, Stripe link, recent validations | ❓ |
| 22.19 | Audit Log: shows admin actions with timestamps | P1 | Manual | Every create/edit/suspend/reinstate/delete shown with timestamp and admin identity | ❓ |
| 22.20 | CSV Export: downloads valid CSV with all licenses | P1 | Manual | CSV opens in spreadsheet, all columns and rows present | ❓ |
| 22.21 | Mobile responsive: no horizontal scroll at 375px width, buttons tappable | P1 | Manual | Open CRM on phone (Safari/Chrome) or DevTools 375px emulation — no horizontal scrollbar, subscribe/suspend buttons not clipped, table scrolls vertically within parent | ❓ |
| 22.22 | CRM concurrent admin: two tabs, same key, both show same state | P2 | Manual | Suspend in tab A → refresh tab B → shows suspended | ❓ |
| 22.23 | CRM SQL injection on search: `' OR 1=1--` returns all rows (not error) | P1 | Auto | Injection query returns same results as legitimate search, no error or schema exposure | ❓ |
| 22.24 | CRM CSRF: forged POST request without auth header → 401 | P1 | Auto | POST /api/admin/licenses without Authorization → 401 | ❓ |

---

## 23. Integration — End-to-End Flows (11 flows)

**Time budget:** ~3 hours for a single pass. Each flow ≈ 10–15 min. Run in sequence; some depend on prior state (23.1 → 23.2 → 23.3 → 23.5).

**Execution protocol:**
- Flows 23.1–23.6: sequential, one macOS user, one terminal session
- Flow 23.6 (trial expiry): use `OBSERVECO_TRIAL_DAYS=0` env var to test expiry without waiting 30 days (now implemented in billing.py `__post_init__`)
- Flows 23.8–23.9: need CRM open in browser alongside dashboard
- Flow 23.10 (clean room): separate macOS user account or VM
- Flow 23.11 (resubscribe): requires active Stripe subscription to cancel first

**Setup per flow:**
- Dashboard running on :9121 with token ready
- CRM open at `https://observeco-license-crm.vercel.app/admin` with API key
- Stripe test mode credentials in billing.json (never live keys)
- Terminal window for CLI commands

**All P0. All must pass before human test.**

| # | Flow | Sev | Method | Pass Criteria |
|---|------|-----|--------|---------------|
| 23.1 | **Fresh Install:** pip install → `observeco dashboard` → opens at :9121 → auto-trial starts (is_pro=true, 30d remaining) | P0 | Manual | Dashboard on port 9121, trial shows 28-30 days, Pro features work |
| 23.2 | **Free Tier:** After trial cancel → Fleet view works, pulse works, alerts show (LLM features return static fallback) | P0 | Manual | Dashboard loads, fleet cards visible, options without Pro lock visible |
| 23.3 | **Stripe Checkout:** Click Subscribe → Stripe checkout → enter card → success page → Pro active with subscription | P0 | Manual | Stripe redirects back to success page, license status shows active with plan=solo |
| 23.4 | **Admin Key Activation:** CRM generate key → copy → dashboard Pro modal → paste → Pro unlocks | P0 | Manual | Key activates, badge updates to Pro, activated_by recorded |
| 23.5 | **Cancel Trial:** Dashboard Cancel Trial → confirm → Free downgrade → LLM features stop | P0 | Manual | License shows Free, trial_consumed=true, LLM features return static |
| 23.6 | **Trial Expiry:** Set `OBSERVECO_TRIAL_DAYS=0` env var → restart → trial shows expired → end-of-trial banner visible | P0 | Manual | Set env var, restart dashboard, /api/licenses/status shows is_pro=false, banner visible with Subscribe link |
| 23.7 | **CRM Suspend → User Loses Access:** Suspend in CRM → user re-validates → denied | P0 | Manual | After suspend, local license shows expired, features gated |
| 23.8 | **CRM Issue → User Activates:** Issue license in CRM → user enters key → Pro unlocks | P0 | Manual | Key from CRM activates local instance |
| 23.9 | **Re-install Persistence:** pip uninstall → pip install → dashboard → license file intact | P0 | Manual | Same trial/license state survives reinstall |
| 23.10 | **Clean Room:** Fresh macOS user → pip install observeco[dashboard] → observeco dashboard → full workflow | P0 | Manual | Everything works from absolute zero |
| 23.11 | **Resubscribe:** Pro → Cancel → Subscribe again → Pro re-activated | P1 | Manual | After cancelling, subscribing again restores Pro features |

---

## 24. Security (Dedicated Category) — 14 tests

| # | Test | Sev | Method | Pass Criteria |
|---|------|-----|--------|---------------|
| S.1 | License key forgery: invalid checksum, wrong format, short key → all fail validation | P1 | Auto | validate_key() returns False for all known forgery patterns |
| S.2 | Webhook signature verification: tampered payload → rejected before any state change | P1 | Auto | Signature mismatch returns 400, no DB writes |
| S.3 | CRM API key brute force: 10 rapid invalid attempts → rate limited (429) | P2 | Auto | After Nth attempt, 429 returned |
| S.4 | CRM SQL injection on search field: `' OR 1=1--` etc → no SQL error, returns safe results | P1 | Auto | Injections return safe results (escaped), no schema exposure |
| S.5 | CRM CSRF: POST without auth header → 401 | P1 | Auto | All admin POST endpoints require auth |
| S.6 | Dashboard auth uses constant-time comparison (`hmac.compare_digest`): verified in code | P2 | Auto | Source code at auth.py:118 uses `hmac.compare_digest(token, self._secret)` — confirmed | ❓ |
| S.7 | Admin key activation tampering: modify key checksum → rejected | P1 | Auto | validate_key() on modified key returns False |
| S.8 | billing.json permission check: file readable only by owner | P2 | Auto | File permissions 600 or equivalent |
| S.9 | Stripe publishable key exposure: not logged in any output or error message | P1 | Auto | grep logs for pk_live/ — should not appear |
| S.10 | License file tampering: user edits license.json to set is_pro=true → re-validation restores correct state | P1 | Auto | After tamper + revalidate, license state returns to actual state |
| S.11 | Trial bypass: delete license.json → re-run → trial consumed prevents re-trial | P1 | Auto | Fixture: seed license.json with trial_consumed=true, delete file, run discovery — trial_consumed=true prevents second trial | ❓ |
| S.12 | Revoked key reuse: old user with revoked key tries to activate → denied | P1 | Auto | Revoked key returns error, no state change |
| S.13 | Dashboard token entropy: check token is sufficiently random (no sequential or date-based) | P2 | Auto | Token passes randomness checks (entropy > 128 bits) |
| S.14 | No secrets in error messages: Stripe keys, admin key, Supabase URL never appear in 500 errors | P1 | Auto | Trigger error, check response body for key patterns |

---

## 25. Resilience & Failure Modes — 10 tests

| # | Test | Sev | Method | Pass Criteria |
|---|------|-----|--------|---------------|
| R.1 | Stripe webhook arrives but Supabase write fails (connection error): webhook returns 500, no partial state | P1 | Auto | Mock Supabase failure, process webhook — no license state changed |
| R.2 | Dashboard loses Supabase mid-request: returns error, server stays up | P1 | Auto | Kill connection mid-request → error response, server still responds to next request |
| R.3 | Health check HTTP timeout (no response, not just slow): status = "error" with timeout message | P0 | Auto | Socket hang → "error" + "timeout" in error field |
| R.4 | DNS failure for Stripe/Supabase endpoints: falls back to off-line mode | P1 | Auto | Mock DNS failure, checkout returns simulated, validation uses local DB |
| R.5 | License activation succeeds but billing.json OS crash mid-write: on restart, activation state recoverable | P2 | Auto | Simulate crash mid-write, restart — license state correct (either committed or retry) |
| R.6 | Stripe webhook arrives 24h late (eventual consistency): processed correctly | P2 | Auto | Deliver stale webhook event → correctly applied to current state |
| R.7 | Dashboard + daemon restart simultaneously: no data loss | P2 | Auto | Mock both processes, kill both, restart — assert pulse results resume from last checkpoint, license state unchanged | ❓ |
| R.8 | Multiple simultaneous Stripe webhooks: serialized, no duplicates | P2 | Auto | Fire 3 identical webhooks simultaneously — 1 processed, 2 duplicates rejected or idempotent |
| R.9 | OS crash mid-pulse check: on restart, pulse resumes from last complete cycle | P2 | Auto | Kill daemon mid-check, restart — DB consistent (no partial records) |
| R.10 | Low disk space: graceful degradation, dashboard warns | P3 | Auto | Mock disk usage > 90%, dashboard shows disk warning but continues serving |

---

## 26. Phase 7 — Structural Components — 51 tests (51 auto + 0 manual)

**Date added:** 2026-06-04 — All Phase 7 items completed and tested.

### 26.1 Event Pipeline & Event Bus (`src/observeco/event_bus.py`) — Phase 7.1 — 7 auto tests (all ✅)

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 26.1 | EventStream writes events to rotating JSONL files | P0 | Auto | File created in event_dir with correct JSONL format | ✅ |
| 26.2 | EventStream rotates when file exceeds max_bytes | P1 | Auto | Files rotated, ≥ 2 files exist after overflow writes | ✅ |
| 26.3 | EventStream limits total files (deletes oldest) | P1 | Auto | After exceeding max_files, oldest file deleted | ✅ |
| 26.4 | publish() + get_events() round-trip: all fields preserved | P0 | Auto | Events read back match written events | ✅ |
| 26.5 | get_events() filters by event_type correctly | P0 | Auto | Filtered results contain only matching type | ✅ |
| 26.6 | get_events() returns empty list for unknown type | P1 | Auto | Unknown type returns [] | ✅ |
| 26.7 | publish() handles errors gracefully (bad data, full disk) | P1 | Auto | No crash on oversized data or write errors | ✅ |

### 26.2 Watch Consumers (`src/observeco/watch_consumers.py`) — Phase 7.1 — 9 auto tests (all ✅)

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 26.8 | BaseConsumer starts and stops cleanly | P0 | Auto | Thread starts, thread stops, _running flag toggles | ✅ |
| 26.9 | BaseConsumer idempotent start (double start = no-op) | P1 | Auto | Second start doesn't create new thread | ✅ |
| 26.10 | ConsumerManager registers all 5 consumers | P0 | Auto | drift, garden, pathway, heal, prune all in manager | ✅ |
| 26.11 | ConsumerManager start_all / stop_all works | P0 | Auto | All 5 consumers start and stop together | ✅ |
| 26.12 | DriftConsumer._tick runs without crash (empty DB) | P1 | Auto | No exception with no data | ✅ |
| 26.13 | GardenConsumer._tick runs without crash | P1 | Auto | No exception | ✅ |
| 26.14 | PathwayConsumer._tick runs without crash | P1 | Auto | No exception | ✅ |
| 26.15 | HealConsumer._tick runs without crash | P1 | Auto | No exception | ✅ |
| 26.16 | PruneConsumer._tick runs without crash | P1 | Auto | No exception | ✅ |

### 26.3 Parallel Probe Engine (`src/observeco/pulse/check.py` — parallel mode) — Phase 7.2 — 3 auto tests (all ✅)

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 26.17 | Parallel probing is faster than sequential (5 agents, 0.2s each) | P0 | Auto | Total time < 0.8s (vs 1.0s sequential) | ✅ |
| 26.18 | One failing probe doesn't block other agents | P0 | Auto | 3 agents succeed, 1 fails — error doesn't propagate | ✅ |
| 26.19 | _probe_agent is importable and callable | P0 | Auto | Returns tuple of length ≥ 3 | ✅ |

### 26.4 Probe Driver Registry (`src/observeco/probe/registry.py`) — Phase 7.4 — 11 unit + 6 integration tests (all ✅)

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 26.20 | @register decorator maps scheme to probe class | P0 | Auto | Scheme appears in list_probe_types(), get_probe returns class | ✅ |
| 26.21 | get_probe("http") returns HTTP probe | P0 | Auto | Not None, is subclass of BaseProbe | ✅ |
| 26.22 | get_probe("launchd") returns launchd probe | P0 | Auto | Not None | ✅ |
| 26.23 | get_probe("docker") returns Docker probe | P0 | Auto | Not None | ✅ |
| 26.24 | BaseProbe enforces probe() method (abstract) | P0 | Auto | Incomplete subclass raises NotImplementedError | ✅ |
| 26.25 | ProbeResult has sensible defaults | P1 | Auto | Default error="", metadata="" | ✅ |
| 26.26 | ProbeResult supports all status fields | P1 | Auto | is_alive property, error string, metadata accessible | ✅ |
| 26.27 | resolve_probe resolves http:// → HttpProbe | P0 | Auto | Correct probe class returned | ✅ |
| 26.28 | resolve_probe resolves launchd: → LaunchdProbe | P0 | Auto | Correct probe class returned | ✅ |
| 26.29 | resolve_probe falls back to pgrep (no health_check) | P0 | Auto | Returns pgrep probe for agents without health_check | ✅ |
| 26.30 | resolve_probe unknown scheme falls back to shell/pgrep | P1 | Auto | Unknown:// scheme doesn't crash, returns valid probe | ✅ |
| 26.31 | _probe_agent delegates to HttpProbe (integration) | P0 | Auto | HTTP health_check → HttpProbe used | ✅ |
| 26.32 | _probe_agent delegates to LaunchdProbe (integration) | P0 | Auto | launchd: health_check → LaunchdProbe used | ✅ |
| 26.33 | _probe_agent delegates to DockerProbe (integration) | P0 | Auto | docker: health_check → DockerProbe used | ✅ |
| 26.34 | _probe_agent delegates to ShellProbe (integration) | P0 | Auto | Shell command health_check → ShellProbe used | ✅ |
| 26.35 | _probe_agent pgrep fallback works (integration) | P1 | Auto | No health_check → pgrep probe used | ✅ |
| 26.36 | resolve_probe matches old dispatch behavior | P0 | Auto | All 5 probe types (http, launchd, docker, systemd, pgrep) registered | ✅ |

### 26.5 First-Run State Machine (`src/observeco/dashboard/server.py` + `/api/phase/*`) — Phase 7.3 — 9 auto tests (all ✅)

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 26.37 | POST /api/discover/run returns 200 or 500 (LLM may fail) | P0 | Auto | Status in (200, 500, 404) | ✅ |
| 26.38 | GET /api/discover/candidates returns JSON with agents list | P0 | Auto | 200, includes "candidates" and "count" fields | ✅ |
| 26.39 | Each candidate has name and type fields | P1 | Auto | Every candidate has both fields | ✅ |
| 26.40 | Candidates list is valid (count ≥ 0) | P1 | Auto | Non-negative count | ✅ |
| 26.41 | GET /api/phase/state returns phase metadata | P0 | Auto | Response has phase, is_first_run, agents_exist | ✅ |
| 26.42 | POST /api/phase/transition moves forward (zero → setup) | P0 | Auto | Phase transitions correctly | ✅ |
| 26.43 | Invalid phase transition returns 400 | P1 | Auto | Bad phase name → 400 error | ✅ |
| 26.44 | GET /api/phase returns HTML banner | P0 | Auto | 200, Content-Type text/html | ✅ |
| 26.45 | Phase transitions are irreversible (backward == 400) | P1 | Auto | Cannot go from setup → zero | ❓ |

### 26.6 Token Tracking in Watch Daemon (`src/observeco/watch.py`) — Phase 7.5 — 3 auto tests (tests needed)

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 26.46 | Watch loop logs token data to token_logs table per cycle | P0 | Auto | After one watch cycle, token_logs has ≥ 1 entry per alive agent | ❓ |
| 26.47 | Token log fields are populated (total, identity, skills, memory, tools, guidance) | P1 | Auto | All 6 token fields present and non-negative | ❓ |
| 26.48 | Token data survives daemon restart (DB persistence) | P2 | Auto | Restart daemon, query token_logs — previous entries intact | ❓ |

### 26.7 Skill Artifacts + Cards (`observeco chisel artifacts`, `observeco chisel cards`) — Phase 7.6 — 3 auto tests (tests needed)

| # | Test | Sev | Method | Pass Criteria | Status |
|---|------|-----|--------|---------------|--------|
| 26.49 | `chisel artifacts --refresh` rebuilds compressed cache without crash | P1 | Auto | Exit code 0, .md.compressed files created | ❓ |
| 26.50 | `chisel cards` outputs top-N ranked list with token counts | P1 | Auto | Non-empty output, each entry has name, tokens, rank | ❓ |
| 26.51 | SkillOS prefers compressed cache over raw skill files | P0 | Auto | With both .md and .md.compressed present, compressed loaded first | ❓ |

---

## 27. Summary Dashboard

### Count by Module

```
|| Module                          | Total   | P0   | P1   | P2   | P3   | Auto   | Manual   | ✅ Now |
|────────────────────────────────|─────────|------|------|------|------|--------|----------|--------|
|1.  CLI Entry Point             18      7    8    2    1    18      0       4
|2.  Billing & Licensing         26      9    15   2    0    24      2       3
|3.  License State API           22      11   9    2    0    22      0       0
|4.  Dashboard                   35      9    15   10   1    9      26       0
|5.  Pulse Check                 18      11   7    0    0    18      0       9
|6.  Circuit Breaker             10      5    5    0    0    10      0       3
|7.  Chisel Trim                 12      3    7    2    0    12      0       5
|8.  Chisel Drift                6       1    4    1    0    6       0       1
|9.  ClawForge Profile           4       1    2    1    0    4       0       1
|10. ClawForge Load              6       5    1    0    0    6       0       6
|11. ClawForge Garden            8       2    4    2    0    8       0       4
|12. Auto-Detect                 10      1    9    0    0    10      0       2
|13. Database                    10      3    4    3    0    10      0       1
|14. Config                      8       1    5    2    0    8       0       1
|15. Directory Management        5       1    3    1    0    5       0       0
|16. Watch Daemon                8       3    3    2    0    8       0       0
|17. Heal                        8       2    4    2    0    8       0       0
|18. Snapshot/LLM                9       3    6    0    0    9       0       0
|19. MCP Server                  5       2    2    1    0    5       0       0
|20. Code Graph                  8       2    5    1    0    8       0       0
|21. Dashboard OTel              4       0    1    3    0    4       0       0
|22. CRM (Vercel)                24      7    14   3    0    6      18      1
|23. Integration E2E             11      10   1    0    0    0      11       0
|24. Security                    14      0    10   4    0    14      0       0
|25. Resilience & Failure        10      1    3    5    1    10      0       0
|26. Phase 7 Structural          51     16    29   6    0    42      9      45
|────────────────────────────────────────────────────────────────────────────────
|TOTAL                          350     116   176  55   3    285     65      86
```

### Already Passing
- **86 tests** (41 core + 45 Phase 7 structural)
- **1 test** (CRM page loads at /admin — auto-verified)

### Needs Writing
- **199 auto tests** (of which 158 are new — excludes 42 Phase 7 auto tests already written)
- **65 manual tests** (dashboard UI, CRM management, E2E flows, accessibility)

### Gate Status

| Gate | Target | Current | Status |
|------|--------|---------|--------|
| Auto suite pass | 285/285 ✅ | 86/285 | ❌ |
| Manual suite pass | 65/65 ✅ | 0/65 | ❌ |
| E2E flows pass | 11/11 ✅ | 0/11 | ❌ |
| Security tests pass | 14/14 ✅ | 0/14 | ❌ |
| CRM tests pass | 24/24 ✅ | 1/24 | ❌ |
| Ready for human test | All above ✅ | — | ❌ |

---

## 28. Execution Order

```
Phase 1 — Foundation (run first, block everything else)
  → 13: Database (all tables exist)
  → 14: Config (load, parse, validate)
  → 15: Directories (paths exist)

Phase 2 — Core Logic (unit tests, no external deps)
  → 5: Pulse Check
  → 6: Circuit Breaker
  → 7: Chisel Trim
  → 8: Chisel Drift
  → 9: ClawForge Profile
  → 10: ClawForge Load
  → 11: ClawForge Garden

Phase 3 — Commercial Layer
  → 2: Billing (key generation, config, Stripe mock)
  → 3: License State API
  → 1: CLI Entry Point (billing commands)

Phase 4 — Infrastructure + Phase 7 Structural (run together)
  → 26: Phase 7 Structural (Event Bus, Consumers, Parallel Probes,
       Probe Registry, First-Run State Machine, Token Tracking,
       Skill Artifacts)
  → 12: Auto-Detect
  → 16: Watch Daemon
  → 17: Heal
  → 18: Snapshot/LLM
  → 19: MCP Server
  → 20: Code Graph
  → 21: Dashboard OTel

Phase 5 — Integration
  → 4: Dashboard (auto tests: startup, auth, port)
  → 22: CRM (auto tests: auth, API endpoints)
  → 24: Security
  → 25: Resilience

Phase 6 — Manual Tests (you run)
  → 4: Dashboard (manual: UI flows)
  → 22: CRM (manual: admin actions)
  → 23: E2E (all 11 flows)

Phase 7 (Security Review) — Renamed to avoid confusion with product Phase 7
  → Full security test suite pass

Phase 8 (Human Test)
  → You run, I process
```