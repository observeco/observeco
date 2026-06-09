# ObserveCo — Commercial Scope

**Product:** ObserveCo  
**Status:** 🟡 In review — v2 comprehensive update with all license pathways  
**Last updated:** 2026-06-09  
**Owner:** Sean (decision) → Main (build)

---

## 1. Summary

Two tiers only. No $49/mo Team tier — deferred post-v1.

| Tier | Price | Trial | Distribution |
|------|-------|-------|-------------|
| **Free** | $0 | N/A | `pip install observeco`, auto-enabled |
| **Solo** | $9/mo | 30-day free trial | Stripe Checkout or admin-issued license key |

The Free tier is a genuine product, not a demo. It delivers real value for solo operators who just want fleet visibility. The Solo tier adds Pro features (alerts via Telegram, heal escalation, LLM-enriched analysis, long data retention, MCP tool execution for Hermes plugin users).

Solo becomes worth $9/mo the moment a single silent failure would have cost more than a coffee subscription to catch.

---

## 1B. 3-Way Licensing Architecture (Stripe ↔ Vercel CRM ↔ Local)

The licensing system is a three-way sync between Stripe (billing source of truth),
Vercel CRM (cloud API + admin interface), and the local ObserveCo dashboard
(client-side gate). All three share the same Supabase `licenses` table.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  User Machine                          Cloud (Vercel CRM)            │
│  ┌──────────────────────┐             ┌─────────────────────────┐    │
│  │ ObserveCo Dashboard  │───validate──→│ /api/licenses/validate  │    │
│  │ (FastAPI + htmx)     │───trial────→│ /api/trials/start       │──→│
│  │                      │───webhook──→│ /api/stripe/webhook     │    │
│  │                      │             │ /api/admin/licenses/*   │    │
│  │  ~/.observeco/       │             │ /api/admin/stats        │    │
│  │  └─ license.json     │             │ /api/admin/audit-log    │    │
│  │  └─ billing.json     │             │                         │    │
│  │                      │             │ Admin Dashboard          │    │
│  │  Local commercial    │             │ (HTMX, /admin/*)        │    │
│  │  API (port 9125)     │             └───────────┬─────────────┘    │
│  │  /api/commercial/    │                         │                   │
│  │  └─ /licenses/       │                         ▼                   │
│  │  └─ /trials/         │            ┌──────────────────────┐       │
│  │  └─ /stripe/webhook  │            │ Supabase PostgreSQL   │       │
│  │  └─ /admin/*         │            │ ┌──────────────────┐  │       │
│  └──────────────────────┘            │ │ licenses table    │  │       │
│                                       │ │ products table    │◄─┘       │
│  ┌──────────────────────┐            │ │ validations_log   │          │
│  │ Stripe                │            │ │ RLS: anon-key r/o │          │
│  │ ┌──────────────────┐ │──webhook──→│ └──────────────────┘  │          │
│  │ │ Solo $9/mo       │ │            └──────────────────────┘          │
│  │ │ Checkout Session │ │                                             │
│  │ │ customer.sub.    │ │     Both CRMs (Vercel & local) share         │
│  │ │ deleted/updated  │ │     the SAME Supabase `licenses` table.      │
│  │ └──────────────────┘ │     Actions from one propagate instantly.    │
│  └──────────────────────┘                                               │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow

#### A. Subscription Purchase (Stripe → Webhook → Supabase)
```
User clicks "Subscribe $9/mo"
  → Stripe Checkout (hosted page)
  → Stripe sends webhook to Vercel CRM (/api/stripe/webhook)
  → Webhook handler:
    checkout.session.completed → insert license row (status='active', issued_by='stripe', stripe_customer_id='cus_xxx')
    customer.subscription.created → insert or update license (handles trial→paid transition)
    customer.subscription.updated → handle past_due → expired, or extend expires_at
    customer.subscription.deleted → status='cancelled'
  → Supabase licenses table updated
```

#### B. License Validation (Local Dashboard → Vercel CRM)
```
Dashboard startup (or Pro feature access)
  → Read ~/.observeco/license.json
  → POST /api/licenses/validate { license_key }
  → Vercel CRM queries Supabase, returns { valid, status, features, expires_at }
  → Local cache writes result with 24h TTL for offline tolerance
  → If offline: use cached result; if stale >24h: downgrade to Free
```

#### C. Trial Flow (Local → Vercel CRM)
```
First Pro feature access (explicit "Start Free Trial" button)
  → Dashboard calls POST /api/trials/start { email, name, phone }
  → Vercel CRM creates license row (status='trialing', trial_ends_at=now+30d)
  → Returns license_key, stored locally in ~/.observeco/trial.json
  → Trial unlocks ALL Pro features for 30 days
  → At expiry: auto-downgrade to Free, lock Pro features
  → Subscription mid-trial: upgrade to full Solo, no double-billing
```

#### D. Admin Operations (Vercel CRM ↔ Supabase ↔ Local)
```
Admin creates/suspends/reinstates/deletes license
  → Vercel CRM /api/admin/* updates Supabase directly
  → Local dashboard (port 9125) has identical /api/commercial/admin/* routes
  → Both CRMs share the same Supabase table — no sync delay
```

---

## 1C. All License Pathways (End-to-End)

This section enumerates every possible way a user can obtain, lose, or manage a license. Each pathway includes the user journey, code flow, and expected UX.

### Pathway 1: Free (pip install → dashboard)

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | User runs `pip install observeco` | — |
| 2 | User runs `observeco dashboard` | `cli.py` → `server.py` |
| 3 | First run sets `first_run_at` in license.json | `license.py:load()` |
| 4 | No license key → `license_type="free"` | `license.py:LicenseState` |
| 5 | Dashboard renders with Free badge, all Pro features gated | `licenses_api.py:111-118` |
| 6 | All core features work (fleet, pulse, errors, tokens, heal button) | — |

**UX:** Header badge shows `🔓 Free` with a `Subscribe $9/mo` button. Pro features show locked banners.

**Edge case — 30-day LLM grace:** New users get 30 days of Tier 1 (deep) LLM features without any license. `LicenseState.NEW_USER_LLM_GRACE_DAYS = 30`. This is invisible to the user — they just see Pro features working until day 31.

### Pathway 2: Start Free Trial

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | User clicks "Start Free Trial" (from Pro upsell modal or header) | `index.html:1634` → `/api/checkout?plan=solo&trial=30` |
| 2 | Create checkout session, user fills Stripe Checkout form (no CC required for trial) | `billing.py:create_checkout_session()` |
| 3 | Stripe sends `checkout.session.completed` webhook | `billing.py:288-306` |
| 4 | License row created in Supabase with `status='trialing'`, `trial_ends_at=now+30d` | `commercial_api.py` or Vercel CRM |
| 5 | Local license.json updated with trial info | `license.py:ensure_trial()` or `start_trial()` |
| 6 | All Pro features unlock for 30 days | `license.py:is_pro → is_trial_active` |

**UX:** Header badge shows `🚀 Solo plan — 28d left` with `Subscribe $9/mo` and `Cancel Trial` buttons.

**Cancel trial:** User clicks "Cancel Trial" → `POST /api/licenses/cancel-trial` → sets `trial_consumed=true` → locks Pro features immediately. Data preserved.

### Pathway 3: Subscribe via Stripe (from trial or fresh)

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | User clicks "Subscribe $9/mo" | Header badge or Pro modal |
| 2 | Stripe Checkout (CC required for paid subscription) | `billing.py:create_checkout_session()` |
| 3 | Stripe sends `checkout.session.completed` with `stripe_customer_id=('cus_xxx')` | `billing.py:295-304` |
| 4 | License row: `status='active'`, `expires_at=current_period_end`, `stripe_customer_id=cus_xxx` | `commercial_api.py:541` |
| 5 | User enters the returned license key OR it auto-activates via webhook callback | `license.py:activate_key()` |
| 6 | Local license.json: `license_type='pro'`, `key=OBS-PRO-...`, `plan='solo'` | — |

**UX:** Header badge shows ✅ `Pro · Solo plan / Active subscription` with `Manage Billing →` button. This button opens the Stripe Customer Portal for payment method changes, invoice viewing, and subscription cancellation.

| Step | What happens on cancellation (from Stripe Portal) |
|------|---------------------------------------------------|
| 1 | User cancels in Stripe Customer Portal |
| 2 | Stripe sends `customer.subscription.deleted` webhook |
| 3 | Vercel CRM sets `status='cancelled'`, updates `expires_at` to `current_period_end` |
| 4 | Local validation next day detects cancelled status |
| 5 | At `expires_at`: auto-downgrade to Free |

### Pathway 4: Admin-Issued License Key (e.g., tester, alpha, partner)

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | Admin generates key via Vercel CRM or CLI | `billing.py:generate_key()` |
| 2 | Key stored in `billing.json:issued_keys` with `revoked: false` | — |
| 3 | User receives key out-of-band (Sean sends it) | — |
| 4 | User clicks "Pro License Key" on dashboard header | `index.html:e9` |
| 5 | Modal: "Activate Pro License Key" input `OBS-PRO-XXXXXXXX-XXXX` | `index.html:2388-2404` |
| 6 | `POST /api/licenses/activate` → `license.py:activate_key()` | — |
| 7 | Validated locally against `billing.json:issued_keys` FIRST | `license.py:_validate_online()` → `billing.py:validate_admin_key()` |
| 8 | Fallback: validated against Vercel CRM API | — |
| 9 | On success: `license_type='pro'`, Pro features unlocked | — |

**UX:** Header badge shows ✅ `Pro · Solo plan / Active subscription` with `Manage Billing →` button.

**⚠️ THIS IS THE BUG:** For Pathway 4 (admin-issued key), there is:
- ❌ No Stripe customer (no `cus_xxx` in billing.json)
- ❌ No subscription to manage
- ❌ No way to deactivate the key (remove it)
- ❌ No way to switch to a different key
- ❌ Misleading "Active subscription" label when there's no subscription
- ✅ "Manage Billing" now shows a license-key-specific toast (fixed this session)

### Pathway 5: License Key Revoked by Admin

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | Admin sets `revoked: true` on the key in billing.json or Vercel CRM | `billing.py:revoke_key()` |
| 2 | Local dashboard has 24h cached validation — user keeps Pro for up to 24h | `license.py:CACHE_TTL` |
| 3 | Next validation: `validate_admin_key()` returns `valid: false` | — |
| 4 | Fallback to CRM API: also returns invalid | — |
| 5 | `activate_key()` returns `status: "error"` | — |
| 6 | Local state stays Pro but `validation_stale=true` → badge shows stale warning | — |
| 7 | **GAP:** No auto-downgrade on validation failure. User keeps Pro until 24h cache expires AND a re-validation is attempted. If re-validation never happens (e.g., no cron), user stays Pro indefinitely despite revocation. |

### Pathway 6: License Key Expired (has `expires_at`)

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | `license.json` has `expires_at` (timestamp) | — |
| 2 | `LicenseState.is_pro` checks: `if expires_at and now >= expires_at: return False` | `license.py:66-67` |
| 3 | User is downgraded to Free at runtime | — |
| 4 | Dashboard shows Free badge, Pro features locked | — |

**UX:** Clean — no cloud dependency, instant downgrade.

### Pathway 7: Trial → Subscribe Conversion

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | Trial active, user clicks "Subscribe $9/mo" | — |
| 2 | Stripe Checkout creates subscription, webhook fires | — |
| 3 | Supabase license updated: `status='active'`, `trial_ends_at` cleared | — |
| 4 | Local validation: returns `status='active'`, no trial — user is `pro + not trial` | — |
| 5 | Badge changes from trial to subscription badge | — |

**UX:** Smooth transition. No interruption. User sees badge change from trial to subscription.

### Pathway 8: Trial Expired (no conversion)

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | Trial end timestamp reached | — |
| 2 | `LicenseState.is_trial_active` returns `False` | `license.py:49-52` |
| 3 | `is_pro` returns `False` (no key, no active trial) | — |
| 4 | Pro features lock at next dashboard load | — |
| 5 | Header badge: `🔓 Free · Trial ended` with `Restart $9/mo` button | `licenses_api.py:100-109` |

**UX:** Clear messaging. Data preserved. User can restart subscription.

### Pathway 9: Stripe Subscription Cancelled (but still in paid period)

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | User cancels in Stripe Portal → `customer.subscription.deleted` webhook | — |
| 2 | Supabase: `status='cancelled'`, `expires_at=current_period_end` | — |
| 3 | Local validation: still returns `status='active'` because `expires_at` hasn't passed | — |
| 4 | User keeps Pro until `expires_at` | — |
| 5 | At `expires_at`: auto-downgrade to Free | — |

**UX:** User keeps what they paid for. No surprise downgrade.

---

## 1D. Gap Analysis & Required Fixes

### Gap 1: Misleading badge for license-key users

**Problem:** Admin-issued key users see `Pro · Solo plan / Active subscription` — implies a recurring Stripe subscription exists. No distinction between key-based and subscription-based Pro.

**Fix:** Change badge content based on provisioning source:

| Scenario | Badge text | Actions |
|----------|-----------|---------|
| Pro via Stripe subscription | ✅ `Pro · Solo plan / Active subscription` | `Manage Billing →` (Stripe Portal) |
| Pro via admin-issued key | ✅ `Pro · Solo plan / License key` | `Manage Key →` (opens license key modal) |
| Pro via license key + also has Stripe sub | ✅ `Pro · Solo plan / Active subscription` | `Manage Billing →` + `License Key →` |

**Implementation:** The license state needs a new field: `provisioning_source: "stripe" | "admin_key"`. Set when `activate_key()` succeeds. `validate_admin_key()` returning `valid=true` → source = `admin_key`. CRM validation returning `stripe_customer_id` present → source = `stripe`.

### Gap 2: No "Deactivate License Key" for key-based users

**Problem:** If user has an admin-issued key, there's no UI to remove it. No way to:
- Switch to a different key
- Go back to Free voluntarily
- Enter a Stripe-purchased key after using an admin key

**Fix:** Add "Deactivate License" button in the license key modal for Pro users. This:
1. Sets `license_type` back to `free` in license.json
2. Clears `key`, `validated_at`
3. Does NOT delete trial data (can't restart a consumed trial)
4. Does NOT touch billing.json (admin keys are admin-managed)

**Location:** License key modal footer — "Deactivate License" link, with confirmation dialog ("Are you sure? Pro features will be locked.").

### Gap 3: No self-service "Cancel Subscription" for Stripe users

**Problem:** Stripe subscribers can cancel via the Stripe Customer Portal (opened by "Manage Billing"), but there's no in-app cancellation. This is acceptable for v1 — Stripe Portal handles this well — but the dashboard should link to it more clearly.

**Fix:** On the "Manage Billing" flow for Stripe subscribers: works as-is (opens portal). No change needed for v1, but document that in-app cancellation is a future enhancement.

### Gap 4: Manage Billing for license-key users shows irrelevant toast

**Problem:** Fixed this session. License-key users clicking "Manage Billing" now see `🔑 License key account — no Stripe billing to manage`. 

**Fix (already applied):** Detect license-key-only users and show friendly message instead of "customer_id is required" error.

### Gap 5: No auto-downgrade on validation failure

**Problem:** If admin revokes a key or Stripe subscription is cancelled:
- Local cache keeps `validated_at` fresh for 24h
- User keeps Pro for up to 24h
- If no re-validation occurs (no cron, dashboard not refreshed), user stays Pro indefinitely

**Fix:** Add a daily validation cron (already planned in §4.6). For immediate-effect revocation:
- On any Pro feature access, if `validation_stale` (24h since last check), attempt re-validation
- If re-validation fails → downgrade to Free, notify user

### Gap 6: Trial cancellation doesn't sync to CRM

**Problem:** "Cancel Trial" button only updates local `license.json` (`trial_consumed=true`). It does NOT call Vercel CRM to mark the trial as cancelled in Supabase.

**Fix:** `cancel_trial()` should POST to `POST /api/trials/cancel` on Vercel CRM.

### Gap 7: License key expiry not shown to user

**Problem:** If an admin key has an expiry date (set in billing.json metadata), the user has no visibility into when their key expires.

**Fix:** Badge for license-key users should show `Pro · Solo plan / License key — expires 2026-07-01` when `expires_at` is set. If no `expires_at` (perpetual key), show `License key (perpetual)`.

---

## 2. Free Tier ($0)

### What you get

All of ObserveCo's core monitoring, fully functional:

| Feature | Detail |
|---------|--------|
| Fleet dashboard | Live agent cards with status dots, error count, last pulse |
| Pulse health checks | Every 30s per agent — alive/dead/error |
| Circuit breakers | Auto-trip after N consecutive failures, auto-recover |
| Agent discovery | Auto-detect Hermes, OpenClaw, Ollama agents |
| Token tracking | Per-agent token usage, breakdowns, cost totals |
| Drift trends | 7-day view of token drift per agent |
| Error history | Last 24h errors, grouped by type |
| Memory garden | MEMORY.md folder analysis and hygiene suggestions |
| CLI tools | All `observeco` CLI commands work |
| Heal button | Manual heal — trigger agent recovery from dashboard (one-click) |
| Dashboard | Full read/write dashboard at port 9119 |
| MCP server | **Resources only** (read-only). Tools are locked. |
| Retention | 7-day data retention (auto-pruned) |
| Alerts | Dashboard banner alerts only — no push/notifications |
| Artifacts | Core binary + docs — no external dependencies to download |

### What you DON'T get

Locked behind Solo:

| Feature | Reason for lock |
|---------|-----------------|
| Push alerts (Telegram) | Notification delivery costs real infra |
| Heal escalation (LLM auto-diagnosis) | LLM API calls cost money |
| Auto-heal (self-healing without human click) | Risk mitigation requires pro supervision |
| LLM-enriched alert analysis | Same — LLM API cost |
| MCP tool execution | MCP tool use is the Hermes plugin's primary value — must gate to prevent free-tier abuse |
| Long retention (>7 days) | Storage cost grows with fleet size |
| Pro badge/upsell removal | Incentive to convert |

### Flow

```
pip install observeco
observeco dashboard
  → Free tier active immediately
  → Dashboard runs with full Free feature set
  → Pro features show "Unlock with Pro" banners / locked tiles
  → Pro badge in title bar (removed on Solo subscription)
```

---

## 3. Solo Tier ($9/mo)

### What you get

Everything in Free, plus:

| Feature | Detail |
|---------|--------|
| Push alerts (Telegram, Email, Webhook) | Real-time notification on agent health changes |
| Auto-heal | Self-healing without human click — circuit breaker trips auto-recovery |
| Heal escalation | LLM analysis of root cause, suggested fix, auto-apply |
| LLM-enriched alerts | Alert messages enhanced with root cause analysis |
| MCP tool execution | Full read/write access — `Snapshot`, `Heal`, `PulseCheck`, `GraphQuery`, `HealthLog`, `JobAutoFix`, `RecentSession`, `PathwayExec`, `LayersExplain` |
| Long retention | Configurable up to 90 days |
| No Pro badge | Clean UI without upgrade prompts |
| License validation | Cloud-verified license key (works offline for 24h cached) |
| Priority support | Direct Telegram access for bugs/issues |

### Distribution

1. **Stripe Checkout** — Primary channel. User clicks "Subscribe $9/mo" → Stripe Checkout → webhook provisions license → license key stored locally in `~/.observeco/license.json`
2. **Admin-issued license** — Sean can issue free Pro licenses from admin dashboard for testers, alpha users, partners

### Trial

30-day free trial. Starts on first Pro feature access (not on install).

- No credit card required for trial
- Trial token is local-only (`~/.observeco/trial.json`), works offline
- At trial end: auto-downgrade to Free, ALL Pro features lock
- Stripe Checkout handles subscription billing after trial

#### Trial flow

```
User clicks any Pro-gated feature
  → No license file exists
  → No trial token exists
  → Create ~/.observeco/trial.json (30-day clock starts)
  → Unlock all Pro features for 30 days
  → Dashboard shows "14 days remaining" banner
  → At expiry: lock Pro features, show "Your trial has ended. Subscribe for $9/mo."
  → If user enters a license key mid-trial: upgrade to full Solo, no double-billing
```

---

## 4. Badge Scenarios (All States)

The header badge is the primary license status indicator. It must cover all states:

| # | License state | Badge appearance | Actions shown | File location |
|---|--------------|-----------------|---------------|---------------|
| 1 | Free, never trialed | `🔓 Free` | `Subscribe $9/mo` → Stripe Checkout | `licenses_api.py:111-118` |
| 2 | Free, trial expired | `🔓 Free · Trial ended` | `Restart $9/mo` → Stripe Checkout | `licenses_api.py:100-109` |
| 3 | Trial active | `🚀 Solo plan — 28d left` | `Subscribe $9/mo` + `Cancel Trial` | `licenses_api.py:65-75` |
| 4 | Grace period (trial expired <3d ago) | `⚠️ Grace period — 2d left` | `Subscribe $9/mo` | `licenses_api.py:54-64` |
| 5 | Pro via Stripe subscription | `✅ Pro · Solo / Active subscription` | `Manage Billing →` (Stripe Portal) | `licenses_api.py:76-89` |
| 6 | Pro via admin license key | `✅ Pro · Solo / License key` | `Manage Key →` (key modal, deactivate) | **NEEDS BUILD** |
| 7 | Pro via license key + Stripe | `✅ Pro · Solo / Active subscription` | `Manage Billing →` + `License Key →` | **NEEDS BUILD** |
| 8 | Pro, validation stale | `⚠️ Pro · Solo / Validation stale (>24h)` | `Re-validate` button | `licenses_api.py:78-80` already handles |
| 9 | Revoked/expired key (detected) | `🔓 Free · License revoked` | `Contact support` or `Subscribe $9/mo` | **NEEDS BUILD** |

---

## 5. Gating Architecture

### 5.1 Dashboard (already built)

`src/observeco/dashboard/server.py` — `_pro_or_upsell()`, `_pro_response()` handle gate checks. `PRO_FEATURES` list (6 items: alerts, auto-heal, LLM enrichment, auto-fix entry, telegram integration, pro badge). Frontend JS `isPro` check controls tile visibility.

**Status:** ✅ Complete

### 5.2 License validation (already built)

`src/observeco/license.py` — `LicenseState` dataclass, local `~/.observeco/license.json` cache with `CACHE_TTL=86400` (24h offline tolerance), `require_pro()` hook. Trial auto-start on first Pro access.

**Status:** ✅ Complete (except `provisioning_source` field — see §1D/Gap 1)

### 5.3 MCP server (NEEDS BUILD)

`src/observeco/mcp_server.py` — 12 tools, **zero license validation**. All tools currently accessible without any gate.

**What to build:** Add `require_pro()` check as decorator or wrapper on every tool handler. Free tier = resources only (read-only). Solo tier = all 12 tools.

**Status:** 🔴 Gap — must build

### 5.4 Plugin install trial hook (NEEDS BUILD)

When `hermes plugin install observeco` runs, no trial is currently triggered.

**What to build:** Add a post-install script that:
1. Checks if `~/.observeco/trial.json` exists
2. If not, creates it (same 30-day clock as dashboard trial)
3. Optionally calls `POST /api/trials/start` to register email on the cloud

**Status:** 🔴 Gap — must build

### 5.5 Grace period for past_due (NEEDS BUILD)

When Stripe subscription goes `past_due` (payment failure), the license should not immediately revoke.

**What to build:** Add 3-day grace period in `license.py`:
- `past_due` status → 3-day countdown before downgrade to Free
- Dashboard shows "Payment failed — update billing info in 3 days" banner
- After 3 days: auto-downgrade, lock Pro features

**Status:** 🔴 Gap — must build

### 5.6 Daily license validation cron (NEEDS BUILD)

No periodic check to ensure local license is still valid against cloud API.

**What to build:** Hermes cron job running daily:
- `POST /api/licenses/validate` with local license key
- If invalid: downgrade local state, notify user
- If `past_due`: start/continue grace period countdown
- Log result to `~/.observeco/audit.log`

**Status:** 🔴 Gap — must build

### 5.7 Self-service deactivation (NEEDS BUILD)

License-key users cannot remove their key through the UI.

**What to build:** Add "Deactivate License" option in the license key modal:
- Confirmation dialog: "Pro features will be locked. Your data is preserved."
- On confirm: `POST /api/licenses/deactivate`
  - Clears `key`, `validated_at`, sets `license_type='free'`
  - Does NOT touch trial data or billing.json
- Badge reverts to Free state
- User can re-activate a different key later

**Status:** 🔴 Gap — must build (see §1D/Gap 2)

### 5.8 Trial → CRM sync (NEEDS BUILD)

Trial cancellation is local-only — does not sync to Vercel CRM.

**What to build:** `cancel_trial()` should POST to `POST /api/trials/cancel` with the trial token, so CRM knows to invalidate it server-side.

**Status:** 🔴 Gap — must build (see §1D/Gap 6)

---

## 6. Feature Matrix (Free vs Solo)

| Feature | Free | Solo ($9/mo) |
|---------|:----:|:------------:|
| Fleet dashboard | ✅ | ✅ |
| Pulse health checks | ✅ | ✅ |
| Circuit breakers | ✅ | ✅ |
| Agent discovery | ✅ | ✅ |
| Token tracking | ✅ | ✅ |
| Drift trends (7-day) | ✅ | ✅ |
| Error history (24h) | ✅ | ✅ |
| Memory garden | ✅ | ✅ |
| CLI tools | ✅ | ✅ |
| Heal button (manual) | ✅ | ✅ |
| MCP resources (read-only) | ✅ | ✅ |
| 7-day retention | ✅ | ✅ ** |
| Dashboard banner alerts | ✅ | ✅ |
| Push alerts (Telegram/Email) | ❌ | ✅ |
| Auto-heal | ❌ | ✅ |
| Heal escalation (LLM) | ❌ | ✅ |
| LLM-enriched alert analysis | ❌ | ✅ |
| MCP tool execution | ❌ | ✅ |
| Long retention (>7 days, up to 90d) | ❌ | ✅ |
| Pro badge / upgrade prompts | Shown | Hidden |
| License validation (cloud) | N/A | ✅ |
| Offline mode (24h cache) | ✅ | ✅ |
| Priority support | ❌ | ✅ |

> ** Solo tier users still get 7-day minimum retention. Long retention is optional/configurable up to 90 days.

---

## 7. Build Order

| # | Component | Est. time | Depends on |
|---|-----------|-----------|------------|
| 1 | **MCP server gating** — add `require_pro()` wrapper to all 12 tools | 30 min | Nothing |
| 2 | **Plugin install trial hook** — auto-start trial on `hermes plugin install` | 20 min | #1 |
| 3 | **Grace period** — 3-day `past_due` tolerance in `license.py` | 15 min | Nothing |
| 4 | **Daily license validation cron** — Hermes cron, `POST /api/licenses/validate` | 15 min | #3 |
| 5 | **Badge: license-key vs subscription distinction** — add `provisioning_source` field, update badge templates | 20 min | Nothing |
| 6 | **Deactivate license key** — add API endpoint + UI button in license modal | 20 min | #5 |
| 7 | **Trial → CRM sync** — `cancel_trial()` calls Vercel CRM | 15 min | Nothing |
| 8 | **Hero Dashboard license display** — show tier, trial days left, subscription link | 10 min | #1 |

**Total build time:** ~2.5 hours

---

## 8. What I need from you

1. **Badge distinction** — ✅ vs 🔑 for license-key users? Or just change text from "Active subscription" to "License key"?
2. **Deactivate flow** — Immediate downgrade, or show confirmation? Data preserved?
3. **Admin key revocation UX** — Should revoked keys trigger a dashboard banner? ("Your license key was revoked by the administrator")
4. **Trial → CRM sync** — Worth doing, or is local-only cancellation acceptable for v1?
5. **"Manage Billing" for license-key users** — The toast now explains the key-based situation. Acceptable, or should we hide the button entirely for key-only users?

---

## 9. Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-06-05 | Initial draft. Two tiers only (Free + Solo $9/mo). No Team tier. | Main |
| 2026-06-07 | Added §1B: 3-Way Licensing Architecture diagram + data flows. | Main |
| 2026-06-09 | Added §1C: All 9 license pathways end-to-end. §1D: Gap analysis with 7 gaps. §4: All badge scenarios (1-9). Build order expanded. | Main |
