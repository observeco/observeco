# ObserveCo — Commercial Scope

**Product:** ObserveCo  
**Status:** 🟡 In review — v3 billing pipeline fixes  
**Last updated:** 2026-06-14  
**Owner:** Sean (decision) → Main (build)

---

## 1A. Summary

Scale-based pricing. All features unlocked at every tier. Charge only for volume.

| Tier | Price | Invocations/mo | Retention | Seats | Distribution |
|------|-------|---------------|-----------|-------|-------------|
| **Free** | $0 | ~150 (5/day) | 7 days | 1 | `pip install observeco`, auto-enabled |
| **Solo** | $9/mo | 5,000 | 90 days | 1 | Stripe Checkout or admin-issued license key |
| **Team** | $29/mo | 50,000 | Forever | 3 | Stripe Checkout |
| **Enterprise** | Custom | Unlimited | Forever | Unlimited | Sales |

Every feature is free at every tier — auto-heal, push alerts, full compression, LLM intelligence, anomaly detection, MCP tool execution. The only gate is invocation volume.

Solo becomes worth $9/mo the moment you exceed 5 agent invocations per day. Team becomes worth $29/mo the moment you exceed 5,000/mo or need SSO.

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
Dashboard startup (or feature access that checks quota)
  → Read ~/.observeco/license.json
  → POST /api/licenses/validate { license_key }
  → Vercel CRM queries Supabase, returns { valid, status, invocation_quota, expires_at }
  → Local cache writes result with 24h TTL for offline tolerance
  → If offline: use cached result; if stale >24h: fall back to local-only invocation counting
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
| 4 | No license key → `license_type="free"`, invocation cap = 5/day | `license.py:LicenseState` |
| 5 | Dashboard renders with Free badge, **all features unlocked** but capped at 5 invocations/day | `licenses_api.py:111-118` |
| 6 | All features work (fleet, pulse, errors, tokens, heal, auto-heal, alerts, LLM, compression) | — |

**UX:** Header badge shows `🔓 Free` with a `Subscribe $9/mo` button. An "invocations today" counter in the header shows usage toward the 5-invocation daily cap.

**Edge case — daily cap:** If the user exceeds 5 invocations in a day, further invocations are queued and executed at the start of the next UTC day. The user sees a banner: "You've used all 5 free invocations for today. Upgrading to Solo ($9/mo) gives you 5,000 invocations/mo."

### Pathway 2: Start Free Trial

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | User clicks "Start Free Trial" (from header or upgrade banner) | `index.html:1634` → `/api/checkout?plan=solo&trial=30` |
| 2 | Create checkout session, user fills Stripe Checkout form (no CC required for trial) | `billing.py:create_checkout_session()` |
| 3 | Stripe sends `checkout.session.completed` webhook | `billing.py:288-306` |
| 4 | License row created in Supabase with `status='trialing'`, `trial_ends_at=now+30d`, `invocation_quota=unlimited` | `commercial_api.py` or Vercel CRM |
| 5 | Local license.json updated with trial info | `license.py:ensure_trial()` or `start_trial()` |
| 6 | **Unlimited invocations for 30 days** — no invocation cap | `license.py:is_pro → is_trial_active` |

**UX:** Header badge shows `🚀 Solo plan — 28d left` with `Cancel Trial` button only (no "Subscribe $9/mo" — you're already on trial, can't subscribe twice).

**Cancel trial:** User clicks "Cancel Trial" → confirmation modal warns it's a one-time offer → `POST /api/licenses/cancel-trial` → sets `trial_consumed=true` → **also cancels the Stripe subscription server-side** (if one exists) → locks Pro features immediately. Data preserved. User can subscribe at $9/mo (without a trial) anytime.

### Pathway 3: Subscribe via Stripe (from trial or fresh)

| Step | What happens | File/Location |
|------|-------------|---------------|
| 1 | User clicks "Subscribe $9/mo" | Header badge or upgrade banner |
| 2 | Stripe Checkout (CC required for paid subscription) | `billing.py:create_checkout_session()` |
| 3 | Stripe sends `checkout.session.completed` with `stripe_customer_id=('cus_xxx')` | `billing.py:295-304` |
| 4 | License row: `status='active'`, `expires_at=current_period_end`, `stripe_customer_id=cus_xxx`, `invocation_quota=5000/mo` | `commercial_api.py:541` |
| 5 | User enters the returned license key OR it auto-activates via webhook callback | `license.py:activate_key()` |
| 6 | Local license.json: `license_type='pro'`, `key=OBS-PRO-...`, `plan='solo'`, `invocation_quota=5000` | — |

**UX:** Header badge shows ✅ `Pro · Solo plan / Active subscription` with `Manage Billing →` button. Invocation usage shown as "1,234 / 5,000 invocations this month" in the header.

**Settings tab:** A `💳 License & Billing` card shows current license status. "Manage Billing" button appears for Stripe subscribers (opens Stripe Portal). "Cancel Trial" button appears for trial users. License-key users see their status without billing actions.

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
|| 5 | Header badge: `🔓 Free · Trial ended` with `Subscribe $9/mo` button — no trial, direct subscription | `licenses_api.py:100-109` |

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

**Problem:** Stripe subscribers can cancel via the Stripe Customer Portal (opened by "Manage Billing"), but there's no in-app cancellation.

**Fix (applied 2026-06-14):** Six changes:
1. `cancel_trial()` now also cancels the Stripe subscription server-side via `stripe.Subscription.delete()` — belt and suspenders
2. `deactivate_license()` also cancels the Stripe subscription for Pro users with `provisioning_source="stripe"`
3. "Manage Billing" button wired into Settings tab `💳 License & Billing` card — opens Stripe Customer Portal
4. "Cancel Trial" button wired into Settings tab — shows for trial users
5. `/api/checkout` and `/api/waitlist` added to `AUTH_EXEMPT` — pre-auth endpoints
6. `success_url` / `cancel_url` now derived from `request.base_url` — no more hardcoded port

### Gap 4: Manage Billing for license-key users shows irrelevant toast

**Problem:** Fixed this session. License-key users clicking "Manage Billing" now see `🔑 License key account — no Stripe billing to manage`. 

**Fix (already applied):** Detect license-key-only users and show friendly message instead of "customer_id is required" error.

### Gap 5: No auto-downgrade on validation failure

**Problem:** If admin revokes a key or Stripe subscription is cancelled:
- Local cache keeps `validated_at` fresh for 24h
- User keeps Pro for up to 24h
- If no re-validation occurs (no cron, dashboard not refreshed), user stays Pro indefinitely

**Fix:** Add a daily validation cron (already planned in §5.6). For immediate-effect revocation:
- On any Pro feature access, if `validation_stale` (24h since last check), attempt re-validation
- If re-validation fails → downgrade to Free, notify user

### Gap 6: Trial cancellation doesn't sync to CRM

**Problem:** "Cancel Trial" button only updated local `license.json` (`trial_consumed=true`). It did NOT call Vercel CRM to mark the trial as cancelled in Supabase, nor did it cancel the Stripe subscription.

**Fix (applied 2026-06-14):**
1. `cancel_trial()` now calls `_sync_cancel_to_crm(email)` — fire-and-forget POST to Vercel CRM
2. `cancel_trial()` now also cancels the Stripe subscription server-side via `stripe.Subscription.delete()` — prevents auto-charge after trial
3. `deactivate_license()` now also cancels the Stripe subscription for Pro users with `provisioning_source="stripe"`

### Gap 7: Subscribe/checkout always sends trial to Stripe regardless of user state

**Problem:** Every checkout link in the app passes `trial=30` in the URL — even for users who have already cancelled their trial, had it expire, or are re-subscribing after cancellation. The `trial` parameter was accepted by `api_checkout()` but **never passed through to Stripe** (`create_checkout_session()` always applied `config.trial_days=30` unconditionally). This meant Stripe would attempt to give a 30-day trial to a user who already used theirs — creating a scenario where someone could get unlimited free trials by repeatedly cancelling and resubscribing.

**Chain of bugs:**
1. Consumed/expired badge link: `trial=30` → Stripe tries 30-day trial for cancelled user
2. Trial badge: Shows "Subscribe $9/mo" button alongside "Cancel Trial" — contradictory UX (you're already on trial, can't subscribe twice)
3. Cancel Trial modal: "re-subscribe anytime" vs "this cannot be undone. Trial is a one-time offer" — contradictory

**Fixes applied:**
1. `billing.py:create_checkout_session()`: Added `trial_days: int | None` parameter. `None` = use config default (30). `0` = no trial. `N` = explicit override.
2. `server.py:api_checkout()`: Passes `trial` param through to Stripe. `trial=0` → no trial. `trial=30` → 30-day trial.
3. `licenses_api.py`: Consumed and expired badges now link to `trial=0` instead of `trial=30`. Button text unified to "Subscribe $9/mo" (was "Restart $9/mo" for expired).
4. Trial badge: Removed "Subscribe $9/mo" button — you're already on trial, can't subscribe twice. Only shows Cancel Trial.
5. Cancel Trial modal: Fixed contradiction. Now says "subscribe at $9/mo anytime" (not "re-subscribe") and "Free trial is a one-time offer and cannot be restored" (not "This cannot be undone. Trial is a one-time offer").

**Files changed:** `billing.py`, `server.py`, `licenses_api.py`, `index.html`

**Status:** ✅ Fixed this session

---

## 1E. Licensing Security Audit — 18 Gaps (2026-06-13)

End-to-end critical review of `license.py`, `billing.py`, `auth.py`, and the full activation→enforcement→revalidation pipeline. All 18 gaps with severity, root cause, and fix status.

### 🔴 CRITICAL (4)

#### Gap 1: `start_trial()` overwrites Pro keys

**Severity:** Critical — data loss
**Root cause:** `start_trial()` unconditionally sets `license_type = "trial"`, even when user has an active Pro key.
**Impact:** Stripe webhook `checkout.session.completed` calls `start_trial()` unconditionally (billing.py:316). If user already activated a Pro key, the webhook demotes them to trial. When trial expires, `is_pro` returns False despite valid key in `license.json`.
**File:** `license.py:391-418`
**Fix:** ✅ Added guard: `if state.license_type == "pro" and state.key: return error`

#### Gap 2: State contradiction — key exists but type is "trial"

**Severity:** Critical — orphaned key
**Root cause:** `license.json` can contain `key: "OBS-PRO-..."` AND `license_type: "trial"` simultaneously. The `is_pro` property checks `license_type == "pro"` first — fails because type is "trial". Falls through to `is_trial_active` which returns True (if trial_end is future). When trial expires, `is_pro` returns False even though a valid Pro key exists.
**Impact:** Key is in the file but never consulted after trial expires. User loses Pro despite having a valid key.
**File:** `license.py:65-79`
**Fix:** 🔄 In progress — `activate_key()` must always set `license_type = "pro"` when key is valid, and `start_trial()` must never overwrite it (see Gap 1 fix).

#### Gap 3: Optimistic activation — offline key activation is irreversible

**Severity:** Critical — license bypass
**Root cause:** `_validate_online()` checks local admin keys first. If that fails AND CRM is unreachable, returns `{"offline": True}`. `activate_key()` treats this as valid and saves `license_type = "pro"` permanently.
**Impact:** Generate a fake key `OBS-PRO-00000000-000000`, go offline, activate. Works until next revalidation (24h+).
**File:** `license.py:268-278`
**Fix:** 🔄 Pending — offline activation must validate against `billing.json:issued_keys` before optimistic fallback.

#### Gap 4: `machine_id` is trivially spoofable

**Severity:** Critical (future) — not enforced today
**Root cause:** `machine_id` uses `platform.node()` + `platform.machine()` — hostname + arch. Same machine name = same ID across reinstalls.
**Impact:** If CRM ever enforces per-device limits, trivial to fake.
**File:** `license.py:334-342`
**Fix:** 🔄 Pending — use `uuid.getnode()` (MAC address) or macOS `ioreg -rd1 -c IOPlatformExpertDevice` for hardware UUID.

---

### 🟠 SERIOUS (6)

#### Gap 5: No webhook signature verification in test mode

**Severity:** Serious — spoofable webhook
**Root cause:** `handle_webhook()` only verifies Stripe signature when Stripe is configured. In demo/simulated mode (`cs_demo_*`), accepts any payload. Also, `/api/billing/webhook` is in auth exclusion list — no token required.
**Impact:** Attacker can POST to `/api/billing/webhook` with fake payload to create phantom customers.
**File:** `billing.py:284-326`, `auth.py:108`
**Fix:** 🔄 Pending — verify signature in all modes, or reject webhook in demo mode.

#### Gap 6: Stripe keys stored in plaintext

**Severity:** Serious — credential exposure
**Root cause:** `billing.json` contains `stripe_secret_key` and `webhook_secret` in plaintext JSON.
**Impact:** Any process that can read `~/Library/Application Support/observeco/billing.json` gets full Stripe API access.
**File:** `billing.json` (disk), `billing.py:_load_config()`
**Fix:** 🔄 Pending — encrypt at rest using machine-derived key, or use macOS Keychain.

#### Gap 7: `_revalidate_key()` downgrades silently

**Severity:** Serious — no user notification
**Root cause:** If CRM says key is revoked, `_revalidate_key()` sets `license_type = "free"` and `key = None` with no UI notification, no grace period, no opportunity to re-enter a key.
**Impact:** User opens dashboard one day, Pro features are gone with no explanation.
**File:** `license.py:381-388`
**Fix:** 🔄 Pending — add `downgraded_at` timestamp, surface banner in dashboard on next load.

#### Gap 8: Trial hardening is bypassable via reinstall

**Severity:** Serious — unlimited trials
**Root cause:** `trial_consumed` flag prevents re-starting trial. BUT deleting `~/.observeco/license.json` removes the flag entirely. Fresh install = fresh trial.
**Impact:** User can get unlimited 30-day trials by deleting one file.
**File:** `license.py:190-213`
**Fix:** 🔄 Pending — tie `trial_consumed` to `machine_id` and sync to CRM. CRM should reject trial start if machine_id already consumed a trial.

#### Gap 9: No rate limiting on license activation

**Severity:** Serious — brute force vector
**Root cause:** `activate_key()` can be called unlimited times with no cooldown or attempt counting.
**Impact:** Offline mode + no rate limit = brute-forceable key space (though 2^56 is large).
**File:** `license.py:222-280`
**Fix:** 🔄 Pending — rate limit: max 5 activation attempts per hour. Track in `license.json` or temp file.

#### Gap 10: Race condition in `validate_cached()`

**Severity:** Serious — data corruption risk
**Root cause:** Two processes (dashboard + CLI) calling `validate_cached()` simultaneously both read stale state, both attempt revalidation, both write. No file locking.
**Impact:** Double-write could corrupt `license.json` (atomic rename helps, but logic race remains).
**File:** `license.py:549-604`
**Fix:** 🔄 Pending — use `fcntl.flock()` or platform-specific file lock around `load()`/`save()` pairs.

---

### 🟡 MODERATE (5)

#### Gap 11: Auth exclusions are too broad

**Severity:** Moderate — unintended access
**Root cause:** Multiple API routes excluded from token auth: `/api/discover/run`, `/api/discover/confirm`, `/api/no-llm/toggle`, `/api/trigger-heal`, `/api/billing/webhook`.
**Impact:** `/api/discover/run` can trigger agent discovery without auth. `/api/no-llm/toggle` can disable LLM features. Local-only, but broader than necessary.
**File:** `auth.py:104-108`
**Fix:** 🔄 Pending — narrow exclusions to only truly public routes (billing webhook, success/cancel pages).

#### Gap 12: No license key revocation propagation

**Severity:** Moderate — delayed enforcement
**Root cause:** `revoke_key()` marks key as revoked in `billing.json`, but if user already activated offline, they won't know until next revalidation (24h+ cache).
**Impact:** Revoked key works for up to 24h+ offline, or indefinitely if no revalidation cron.
**File:** `billing.py:377-386`, `license.py:345-388`
**Fix:** 🔄 Pending — check revocation on every `require_pro()` call when validation is stale.

#### Gap 13: `is_pro` trusts key presence without fresh validation

**Severity:** Moderate — stale trust
**Root cause:** After 24h cache expires, if CRM is unreachable, `is_pro` still returns True (trusts key presence). No maximum staleness limit.
**Impact:** User stays Pro indefinitely while offline, even if key was revoked server-side.
**File:** `license.py:65-79`
**Fix:** 🔄 Pending — add staleness cap: if `validated_at` > 7 days old, downgrade to Free regardless of key presence.

#### Gap 14: Billing success page doesn't verify session in demo mode

**Severity:** Moderate — trial spoofing
**Root cause:** In demo mode, any `cs_demo_*` session_id triggers trial activation via `/api/billing/success`. No verification.
**Impact:** Attacker crafts URL: `/api/billing/success?session_id=cs_demo_anything` → trial activated.
**File:** `billing.py:456-519`
**Fix:** 🔄 Pending — verify demo session exists in `billing.json:customers` before activating.

#### Gap 15: No trial-to-paid conversion tracking

**Severity:** Moderate — broken subscription flow
**Root cause:** Stripe webhook records customer but doesn't link trial → subscription. When trial expires and user has active Stripe subscription, no logic auto-activates Pro from the subscription.
**Impact:** User pays via Stripe, trial expires, they're back on Free despite having an active subscription.
**File:** `billing.py:284-326`
**Fix:** 🔄 Pending — on webhook `invoice.paid` or `customer.subscription.updated`, check if user has subscription and set `license_type = "pro"` with `provisioning_source = "stripe"`.

---

### 🔵 EDGE CASES (3)

#### Gap 16: Grace period has an off-by-one

**Severity:** Edge case — UX inconsistency
**Root cause:** Grace period only starts if user opens dashboard within the grace window. If user opens exactly at `trial_end + grace_period`, they skip grace entirely.
**Impact:** Some users get 3-day grace, some get 0, depending on timing of dashboard open.
**File:** `license.py:587-601`
**Fix:** 🔄 Pending — start grace period at `trial_end` (not at first dashboard open after expiry).

#### Gap 17: `first_run_at` resets on reinstall

**Severity:** Edge case — LLM grace abuse
**Root cause:** `first_run_at` is stored in `license.json`. Deleting the file (or reinstalling) resets it. New-user 30-day LLM grace restarts.
**Impact:** User gets 30 days of free deep LLM on every reinstall.
**File:** `license.py:563-566`
**Fix:** 🔄 Pending — persist `first_run_at` in a separate file (e.g., `~/.observeco/.install_state`) that survives license.json deletion.

#### Gap 18: No multi-machine detection

**Severity:** Edge case — license sharing
**Root cause:** Same license key can activate on unlimited machines. CRM receives `machine_id` but doesn't enforce limits.
**Impact:** One purchased key can be shared across unlimited devices.
**File:** `license.py:334-342`, CRM backend
**Fix:** 🔄 Pending — CRM should track `machine_id` per key and enforce device limit (e.g., max 3 machines per Solo key). Local: surface device count in dashboard.

---

### Fix Status Summary

| # | Gap | Severity | Status |
|---|-----|----------|--------|
|| 1 | start_trial() overwrites Pro keys | 🔴 Critical | ✅ Fixed |
|| 2 | State contradiction (key + trial) | 🔴 Critical | 🔄 In progress |
|| 3 | Offline activation bypass | 🔴 Critical | 🔄 Pending |
|| 4 | machine_id spoofable | 🔴 Critical | 🔄 Pending |
|| 5 | Webhook no sig verification (demo) | 🟠 Serious | 🔄 Pending |
|| 6 | Stripe keys plaintext | 🟠 Serious | 🔄 Pending |
|| 7 | Silent downgrade on revalidation | 🟠 Serious | 🔄 Pending |
|| 8 | Trial bypass via reinstall | 🟠 Serious | 🔄 Pending |
|| 9 | No rate limiting on activation | 🟠 Serious | 🔄 Pending |
|| 10 | Race condition in validate_cached | 🟠 Serious | 🔄 Pending |
|| 11 | Auth exclusions too broad | 🟡 Moderate | 🔄 Pending |
|| 12 | Revocation propagation delay | 🟡 Moderate | 🔄 Pending |
|| 13 | is_pro stale trust | 🟡 Moderate | 🔄 Pending |
|| 14 | Demo session not verified | 🟡 Moderate | 🔄 Pending |
|| 15 | No trial→paid conversion link | 🟡 Moderate | 🔄 Pending |
|| 16 | Grace period off-by-one | 🔵 Edge | 🔄 Pending |
|| 17 | first_run_at resets on reinstall | 🔵 Edge | 🔄 Pending |
|| 18 | No multi-machine detection | 🔵 Edge | 🔄 Pending |

**Files affected:** `license.py` (rewrite), `billing.py` (webhook + demo fix), `auth.py` (narrowed exclusions)
**Tests:** 339/342 passing (3 pre-existing DB migration failures unrelated to licensing)

---

## 1F. Subscriber Lifecycle Gap Analysis — What Subscribers Actually Expect (2026-06-14)

The technical plumbing (Stripe webhooks, license state machine, trial lifecycle, grace period) is solid. What's entirely absent is the **communication layer** — the product never talks to the subscriber. No emails, no proactive warnings, no reminders, no win-back, no support. The subscriber is silently upgraded and silently downgraded with no conversation.

### Stage-by-Stage Gap Map

#### Stage 1: Discovery → Trial Start
**What subscriber expects:** Clear value proposition, understand what they're getting, easy start.
**What we have:** "Start Free Trial" button → Stripe Checkout → trial begins.
| Gap | Severity | Description |
|-----|----------|-------------|
| No value proposition at trial start | Medium | User clicks "Start Trial" but never sees "here's what you get for 30 days" |
| No email collection for lifecycle emails | High | Stripe collects email, but we never use it for ObserveCo-specific communication |
| No welcome message after trial starts | Medium | Trial silently begins. No "Welcome! Your 30-day trial is active." |

#### Stage 2: During Trial (Days 1–25)
**What subscriber expects:** See value accumulating, gentle reminders of trial status.
**What we have:** Badge shows "🚀 Solo plan — 28d left". That's it.
| Gap | Severity | Description |
|-----|----------|-------------|
| No trial countdown banner | High | Only visible in tiny badge. No persistent "12 days left" banner on dashboard |
| No "here's what you'll lose" nudge | Medium | No "When your trial ends, you'll lose: Telegram alerts, auto-heal, LLM analysis" |
| No email: "Your trial is active" | Medium | No onboarding email with tips to get value from Pro features |
| No email: "Tips to get the most from ObserveCo Pro" | Low | No mid-trial engagement email |

#### Stage 3: Trial Expiring (Days 25–30) ← CRITICAL
**What subscriber expects:** Urgent, multi-channel reminders before losing access.
**What we have:** Badge shows "2 days left". That's it. No email. No banner. No nudge.
| Gap | Severity | Description |
|-----|----------|-------------|
| No trial expiry reminder email | 🔴 CRITICAL | 3 days before expiry: "Your trial ends in 3 days — subscribe to keep Pro features" |
| No 7-day warning | High | No "1 week left" nudge |
| No in-dashboard urgency banner | High | No "⚠️ Your trial ends in 3 days" persistent banner |
| No "subscribe now" CTA with urgency | High | Badge shows subscribe but no urgency framing |

#### Stage 4: Trial Expired → Grace Period (Days 30–33)
**What subscriber expects:** Clear "you've lost access, here's how to get it back" messaging.
**What we have:** 3-day grace period exists. Badge shows warning. But NO proactive notification.
| Gap | Severity | Description |
|-----|----------|-------------|
| No email: "Your trial has ended" | 🔴 CRITICAL | Email at trial expiry with subscribe CTA |
| No grace period banner in dashboard | High | "⚠️ Grace period: 2 days left — subscribe to keep Pro features" |
| No "what you're missing" comparison | Medium | Show locked features with subscribe CTA |

#### Stage 5: Grace Expired → Free Tier
**What subscriber expects:** Understand what happened, easy path back.
**What we have:** Badge silently changes to "🔓 Free · Trial ended". No explanation.
| Gap | Severity | Description |
|-----|----------|-------------|
| No email: "Your Pro access has ended" | 🔴 CRITICAL | Final email with subscribe CTA |
| No downgrade notification in dashboard | High | `downgraded_at`/`downgraded_reason` tracked but never surfaced |
| No "what you lost" summary | Medium | No comparison of Free vs what they had |
| No win-back nudge | High | No "Come back! Here's what's new" email after 7 days |

#### Stage 6: Subscription Purchase
**What subscriber expects:** Confirmation, receipt, welcome, clear next steps.
**What we have:** Stripe sends receipt. ObserveCo sends NOTHING.
| Gap | Severity | Description |
|-----|----------|-------------|
| No welcome email from ObserveCo | High | "Welcome to ObserveCo Pro! Here's how to get started." |
| No in-dashboard welcome message | Medium | No "🎉 Welcome to Pro!" banner after activation |
| No "getting started" guide | Medium | No "Here are the Pro features you now have access to" |

#### Stage 7: Active Subscription
**What subscriber expects:** Easy management, invoice access, renewal awareness.
**What we have:** Settings tab has "Manage Billing" button → Stripe Portal.
| Gap | Severity | Description |
|-----|----------|-------------|
| No invoice/receipt view in dashboard | Medium | User must go to Stripe Portal to see invoices |
| No subscription renewal reminder | Low | "Your subscription renews in 3 days" |
| No "manage subscription" prominent placement | Low | Only in Settings tab, not in main navigation |

#### Stage 8: Payment Failure ← CRITICAL
**What subscriber expects:** Clear notification, easy fix, grace period.
**What we have:** Stripe webhook marks `past_due`. NO notification to user. NO dashboard banner.
| Gap | Severity | Description |
|-----|----------|-------------|
| No email: "Payment failed" | 🔴 CRITICAL | "Your payment failed. Update your card to keep Pro access." |
| No dashboard banner for past_due | 🔴 CRITICAL | "⚠️ Payment failed. Update billing in 3 days or Pro features will lock." |
| No `invoice.payment_failed` webhook handler locally | High | CRM handles it, but local billing.py doesn't |
| No retry nudge | High | No "Update your payment method" prominent CTA |

#### Stage 9: Cancellation
**What subscriber expects:** Confirmation, clear understanding of what happens next.
**What we have:** Toast notification. That's it.
| Gap | Severity | Description |
|-----|----------|-------------|
| No cancellation confirmation email | High | "Your subscription has been cancelled. You'll keep Pro until [date]." |
| No "before you go" survey | Low | Why are you cancelling? (helps product improvement) |
| No retention offer | Low | "Stay for $5/mo for 3 months?" (optional, can add later) |

#### Stage 10: Post-Cancellation (Still in paid period)
**What subscriber expects:** Know when access ends.
**What we have:** Nothing. User keeps Pro until `expires_at` with no reminder.
| Gap | Severity | Description |
|-----|----------|-------------|
| No "access ends in X days" reminder | High | Email + dashboard banner |
| No re-subscribe CTA before expiry | Medium | "Your access ends tomorrow. Resubscribe to keep Pro features." |

#### Stage 11: Re-subscription
**What subscriber expects:** Easy re-activation, welcome back.
**What we have:** Badge shows "Subscribe $9/mo" button. No personalization.
| Gap | Severity | Description |
|-----|----------|-------------|
| No win-back email after downgrade | High | "We miss you! Here's what's new since you left." |
| No "Welcome back!" messaging | Low | No special treatment for returning subscribers |
| No incentive to return | Low | No discount or extended trial for re-subscribers |

#### Stage 12: Customer Support ← CRITICAL
**What subscriber expects:** Easy access to help when stuck.
**What we have:** Nothing. No help center. No contact link. No support channel.
| Gap | Severity | Description |
|-----|----------|-------------|
| No "Need help?" link anywhere in dashboard | 🔴 CRITICAL | User has no way to get help |
| No FAQ or troubleshooting guide | High | Common issues (trial, billing, features) undocumented |
| No support email/contact in footer | High | No visible support channel |
| No in-app feedback mechanism | Low | No "Report issue" or "Suggest feature" button |

### Where Subscribers Expect to Cancel

| Channel | Status | Notes |
|---------|--------|-------|
| Dashboard Settings tab | ✅ Now implemented | "Manage Billing" → Stripe Portal |
| Stripe Customer Portal | ✅ Works | Full subscription management |
| Email footer unsubscribe | ❌ No emails sent | Can't unsubscribe from emails that don't exist |
| Account/Profile page | ❌ No account page | No dedicated account management |
| Direct URL (`/cancel`) | ❌ No endpoint | No self-service cancellation page |
| Mobile app | N/A | No mobile app |
| CLI command (`observeco cancel`) | ❌ No CLI command | No terminal-based cancellation |

### Priority Fix Order

| # | Fix | Impact | Est. |
|---|-----|--------|------|
| 1 | **Trial expiry reminder emails** (3 days before + day of) | Prevents silent churn. Highest ROI. | 2h |
| 2 | **Payment failure notifications** (email + dashboard banner) | Prevents involuntary churn. Critical for revenue. | 2h |
| 3 | **Trial countdown banner** in dashboard | Constant visibility → urgency → conversion | 1h |
| 4 | **Grace period banner** in dashboard | Clear messaging during grace window | 30m |
| 5 | **Welcome email** after subscription purchase | First impression. Sets tone. | 1h |
| 6 | **"Need help?" link** in dashboard footer | Minimum viable support | 15m |
| 7 | **Cancellation confirmation email** | Professional expectation | 30m |
| 8 | **Post-cancellation reminder** ("access ends in X days") | Prevents surprise expiry | 1h |
| 9 | **Win-back email** (7 days after downgrade) | Recapture lost subscribers | 1h |
| 10 | **Downgrade notification banner** | `downgraded_at` is tracked but never shown | 30m |

**Total estimated build time:** ~10 hours for critical + high items.

### Email Infrastructure Required

None of the above works without email. Options:

| Provider | Cost | Pros | Cons |
|----------|------|------|------|
| **Resend** | Free tier: 100/day | Simple API, good DX | New provider |
| **SendGrid** | Free tier: 100/day | Industry standard | Complex setup |
| **Stripe built-in** | Free with Stripe | Receipts only, no custom emails | Very limited |
| **Postmark** | Free tier: 100/month | Best deliverability | Most expensive |

**Recommendation:** Resend. Simple API, generous free tier, good for ObserveCo's volume.

---

## 1G. Email Infrastructure & Subscriber Communication (Built 2026-06-14)

Email module `src/observeco/emails/` — Resend API integration, fire-and-forget threading, 9 HTML templates (welcome, trial-reminder-7d/3d/1d, trial-expired, grace-period, payment-failed, cancellation-confirmed, win-back). Dashboard banners for trial expiry, grace period, payment failure, free tier. License state properties `is_expiring_soon`, `days_until_expiry`, `days_until_grace_end`, `is_payment_failed`. Footer "Need help?" + Docs + Changelog links.

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
| Dashboard | Full read/write dashboard at port 8123 |
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

| **#** | **License state** | **Badge appearance** | **Actions shown** | **File location** |
|------|--------------|-----------------|---------------|---------------|
| 1 | Free, never trialed | `🔓 Free` | `Subscribe $9/mo` → Stripe Checkout (30d trial) | `licenses_api.py:111-118` |
| 2 | Trial consumed/expired | `🔓 Free · Trial ended` | `Subscribe $9/mo` → Stripe Checkout (no trial) | `licenses_api.py:100-109` |
| 3 | Trial active | `🚀 Solo plan — 28d left` | `Cancel Trial` only | `licenses_api.py:65-75` |
| 4 | Grace period (trial expired <3d ago) | `⚠️ Grace period — 2d left` | `Subscribe $9/mo` → Stripe Checkout (no trial) | `licenses_api.py:54-64` |
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

**Status:** ✅ Complete (provisioning_source field added — see §1D/Gap 1)

### 5.3 MCP server (NEEDS BUILD)

`src/observeco/mcp_server.py` — 9 tools, **zero license validation**. All tools currently accessible without any gate.

**What to build:** Add `require_pro()` check as decorator or wrapper on every tool handler. Free tier = resources only (read-only). Solo tier = all 9 tools.

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

### 5.7 Self-service deactivation (DONE)

License-key users can now remove their key through the UI.

**What was built:**
- "Deactivate License" button in license key modal footer
- Confirmation dialog: "Pro features will be locked. Your data is preserved."
- On confirm: `POST /api/licenses/deactivate` → clears `key`, `validated_at`, sets `license_type='free'`
- For Stripe subscribers: also cancels the Stripe subscription server-side
- Badge reverts to Free state
- User can re-activate a different key later

**Status:** ✅ Done

### 5.8 Trial → CRM sync (DONE)

Trial cancellation now syncs to Vercel CRM and cancels the Stripe subscription.

**What was built:**
- `cancel_trial()` calls `_sync_cancel_to_crm(email)` — fire-and-forget POST to Vercel CRM
- `cancel_trial()` also cancels the Stripe subscription server-side via `stripe.Subscription.delete()`
- Prevents auto-charge after trial cancellation

**Status:** ✅ Done

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

| # | Component | Est. time | Depends on | Status |
|---|-----------|-----------|------------|--------|
| 1 | **MCP server gating** — add `require_pro()` wrapper to all 9 tools | 30 min | Nothing | 🔴 Pending |
| 2 | **Plugin install trial hook** — auto-start trial on `hermes plugin install` | 20 min | #1 | 🔴 Pending |
| 3 | **Grace period** — 3-day `past_due` tolerance in `license.py` | 15 min | Nothing | ✅ Done |
| 4 | **Daily license validation cron** — Hermes cron, `POST /api/licenses/validate` | 15 min | #3 | 🔴 Pending |
| 5 | **Badge: license-key vs subscription distinction** — add `provisioning_source` field, update badge templates | 20 min | Nothing | ✅ Done |
| 6 | **Deactivate license key** — add API endpoint + UI button in license modal | 20 min | #5 | ✅ Done |
| 7 | **Trial → CRM sync** — `cancel_trial()` calls Vercel CRM | 15 min | Nothing | ✅ Done |
| 8 | **Hero Dashboard license display** — show tier, trial days left, subscription link | 10 min | #1 | ✅ Done |
| 9 | **Settings tab License & Billing card** — Manage Billing + Cancel Trial buttons | 15 min | #5 | ✅ Done |
| 10 | **cancel_trial() → Stripe cancellation** — server-side subscription cancel | 15 min | Nothing | ✅ Done |
| 11 | **checkout success/cancel URL fix** — derive from request.base_url | 10 min | Nothing | ✅ Done |

**Total build time:** ~3 hours

---

## 8. What I need from you

1. **Badge distinction** — ✅ vs 🔑 for license-key users? Or just change text from "Active subscription" to "License key"? → **Implemented: `provisioning_source` field controls badge text and button visibility**
2. **Deactivate flow** — Immediate downgrade, or show confirmation? Data preserved? → **Implemented: confirmation dialog, data preserved, Stripe sub cancelled**
3. **Admin key revocation UX** — Should revoked keys trigger a dashboard banner? ("Your license key was revoked by the administrator") → Still pending
4. **Trial → CRM sync** — Worth doing, or is local-only cancellation acceptable for v1? → **Implemented: CRM sync + Stripe cancellation**
5. **"Manage Billing" for license-key users** — The toast now explains the key-based situation. Acceptable, or should we hide the button entirely for key-only users? → **Implemented: button hidden for key-only users, shown only for Stripe subscribers**

---

## 9. Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-06-14 | **v3 billing pipeline fixes:** (1) `cancel_trial()` now cancels Stripe subscription server-side via `stripe.Subscription.delete()`. (2) `deactivate_license()` also cancels Stripe subscription for `provisioning_source="stripe"`. (3) Settings tab `💳 License & Billing` card with Manage Billing + Cancel Trial buttons wired up. (4) `/api/checkout` and `/api/waitlist` added to `AUTH_EXEMPT`. (5) `success_url`/`cancel_url` derived from `request.base_url` — no more hardcoded port. Gap 3 and Gap 6 marked fixed. Build order updated (8/11 done). | Main |
| 2026-06-14 | **§1F: Subscriber Lifecycle Gap Analysis** — 12-stage subscriber journey mapped. 50+ gaps identified across trial, payment, cancellation, support. Key finding: technical plumbing is solid but communication layer is entirely absent. No emails, no proactive warnings, no reminders, no win-back, no support. Priority fix order: (1) trial expiry emails, (2) payment failure notifications, (3) trial countdown banner, (4) grace period banner, (5) welcome email. Email infrastructure (Resend recommended) is prerequisite. ~10h build time for critical+high items. | Main |
| 2026-06-14 | **§1G: Email infrastructure + subscriber communication layer BUILT.** (1) Email module `src/observeco/emails/` — Resend API integration, fire-and-forget threading, 9 HTML templates (welcome, trial-reminder-7d/3d/1d, trial-expired, grace-period, payment-failed, cancellation-confirmed, win-back). (2) License state properties — `is_expiring_soon`, `days_until_expiry`, `days_until_grace_end`, `is_payment_failed`. (3) Dashboard banners — 4 lifecycle banners (trial expiry, grace period, payment failed, free tier) with dismiss/localStorage persistence. (4) Email wiring — `start_trial()` sends welcome, `cancel_trial()` sends cancellation confirmation, `handle_webhook()` sends payment-failed + cancellation emails, `trial-reminder-check` endpoint for banner logic. (5) Footer — "Need help?" + Docs + Changelog links. (6) AUTH_EXEMPT updated. All tests pass. | Main |
| 2026-06-13 | §1E: Full licensing security audit — 18 gaps identified (4 critical, 6 serious, 5 moderate, 3 edge). Gap 1 fixed (start_trial guard). Remaining 17 documented with severity, root cause, file location, and fix plan. | Main |
| 2026-06-10 | §1D/Gap 7: Checkout always sent trial to Stripe regardless of user state. Fixed `create_checkout_session()` to respect `trial_days` param. Removed Subscribe button from trial badge. Fixed Cancel Trial modal contradiction. Updated badge table for all states. | Main |
| 2026-06-09 | Added §1C: All 9 license pathways end-to-end. §1D: Gap analysis with 7 gaps. §4: All badge scenarios (1-9). Build order expanded. | Main |
| 2026-06-07 | Added §1B: 3-Way Licensing Architecture diagram + data flows. | Main |
| 2026-06-05 | Initial draft. Two tiers only (Free + Solo $9/mo). No Team tier. | Main |
