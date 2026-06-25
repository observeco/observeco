# Stripe + Licensing Integration — Supabase + Vercel

**Status:** 🔴 Planned (build not started)
**Last updated:** 2026-06-01
**Owner:** Sean (spec) / Hound (build)
**Price:** Solo $9/mo only. Team tier ($49) delayed post-v1.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  User Machine                         Cloud (Free Tier)              │
│  ┌───────────────────────┐           ┌────────────────────────┐      │
│  │ ObserveCo Dashboard   │           │ Vercel (Serverless)    │      │
│  │ (FastAPI + htmx)      │───POST───→│ /api/licenses/validate │      │
│  │                       │           │ /api/trials/start      │───→──│
│  │  ~/.observeco/        │           │ /api/stripe/webhook    │      │
│  │  └─ license.json      │           │ /api/admin/licenses    │      │
│  │                       │           │ /api/admin/stats       │      │
│  │  Local trial token:    │           │                        │      │
│  │  timestamp + HMAC      │           │ Admin Dashboard         │      │
│  │  (works offline)       │           │ (static HTML, mobile)   │      │
│  └───────────────────────┘           └───────────┬────────────┘      │
│                                                   │                   │
│                    ┌───────────────────────────────┘                   │
│                    ▼                                                  │
│          ┌──────────────────────┐          ┌──────────────────┐      │
│          │ Supabase PostgreSQL  │          │ Stripe            │      │
│          │ ┌──────────────────┐ │          │ ┌──────────────┐ │      │
│          │ │ products         │ │◄─────    │ │ Solo $9/mo   │ │      │
│          │ │ licenses         │ ←───────────│ product       │ │      │
│          │ │                  │ │ Webhook  │ │ Checkout      │ │      │
│          │ │ RLS + anon key   │ │          │ └──────────────┘ │      │
│          │ └──────────────────┘ │          └──────────────────┘      │
│          └──────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### What exists already

| Component | Status | Location |
|-----------|--------|----------|
| Stripe live credentials | ✅ Done | `~/.hermes/intelligence/decisions/stripe-credentials-*` |
| Stripe product "Solo" (`prod_UZb0uXir0y6lLz`) | ✅ Done | Stripe dashboard |
| Billing endpoints in ObserveCo (`/api/billing/status`, checkout, webhook) | ✅ Done | `src/observeco/billing.py` |
| Supabase project (`vuyhjbmvyimapdbcjjt.supabase.co`) | ✅ Done | Supabase (VITE_SUPABASE_URL in .env) |
| Vercel project (observeco.com) | ✅ Done | Vercel |

### What we build

| Component | Estimated time |
|-----------|---------------|
| Supabase schema: products + licenses tables | 30 min |
| Vercel API routes (5 endpoints) | 2h |
| Admin dashboard (responsive HTML page) | 1.5h |
| ObserveCo client integration | 1h |
| Stripe webhook config + Vercel env vars | 15 min |

---

## 2. Supabase Schema

### Table: `products`

```sql
CREATE TABLE products (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  stripe_price_id TEXT,
  features JSONB DEFAULT '[]',
  trial_days INT DEFAULT 0,
  price_display TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Seed data
INSERT INTO products (name, slug, stripe_price_id, features, trial_days, price_display)
VALUES
  ('Free', 'free', NULL, '["fleet_view", "pulse_check", "circuit_breakers", "token_breakdown", "drift_trend", "error_history", "heal_button", "alerts", "memory_garden", "cli_tools"]', 0, '$0'),
  ('Solo', 'solo', '<real-price-id-from-stripe>', '["free_features", "pro_badge", "license_validation", "stripe_checkout"]', 30, '$9/mo');
```

### Table: `licenses`

```sql
CREATE TABLE licenses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_slug TEXT REFERENCES products(slug),
  email TEXT NOT NULL,
  name TEXT,
  license_key TEXT UNIQUE NOT NULL,
  status TEXT DEFAULT 'trialing' CHECK (status IN ('trialing', 'active', 'expired', 'cancelled')),
  trial_ends_at TIMESTAMPTZ,         -- set when status='trialing'; NULL otherwise
  expires_at TIMESTAMPTZ,             -- for 'active': current_period_end (Stripe); for 'cancelled': end of paid period
                                       -- for 'expired': when the licence became invalid
  stripe_subscription_id TEXT,
  stripe_customer_id TEXT,
  issued_by TEXT DEFAULT 'self' CHECK (issued_by IN ('self', 'stripe', 'admin')),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookup
CREATE INDEX idx_licenses_key ON licenses(license_key);
CREATE INDEX idx_licenses_email ON licenses(email);
CREATE INDEX idx_licenses_status ON licenses(status);
```

### RLS Policies (⚠️ placeholder — not enforcing anything with `USING (true)`; relies on Vercel middleware for validation)

```sql
-- Allow anon key to read products (public)
CREATE POLICY "products_public_read" ON products
  FOR SELECT USING (true);

-- RLS POLICY PLACEHOLDER - actual enforcement is via Vercel middleware (service key).
-- These `USING (true)` policies are open by design; Supabase RLS is not the auth layer here.
-- Replace with proper RLS if switching to direct Supabase access from the client.
```

---

## 3. Vercel API Routes

### Project name: `observeco`
Domain: `observeco.com`
Repo: `github.com/observeco/observeco` (new `api/` directory at repo root)

### Environment variables (Vercel)

| Variable | Value | Source |
|----------|-------|--------|
| `SUPABASE_URL` | `https://vuyhjbmvyimapdbcjjt.supabase.co` | Existing |
| `SUPABASE_ANON_KEY` | from Hermes config | Existing |
| `SUPABASE_SERVICE_KEY` | from Supabase dashboard | **Need from Sean** |
| `STRIPE_SECRET_KEY` | `sk_liv...dlNy` | From credentials file |
| `STRIPE_WEBHOOK_SECRET` | `whsec_a5i3m7k2l9n8p6q1r4s5t7u8v0w2x3y4z5a6b7c8d9e0f1g2h3badv` | From credentials file |
| `ADMIN_API_KEY` | Generated on deploy | Random UUID |

> `STRIPE_PUBLISHABLE_KEY` is stored in env but unused by Vercel server-side routes — it exists for future frontend-only Stripe integration (e.g., Stripe Elements in the dashboard). Server-side routes use only the secret key and webhook secret.

### Routes

#### `POST /api/stripe/webhook`

Validates Stripe signature, processes:

**`checkout.session.completed`:**
1. Extract email, subscription ID, customer ID from session
2. Generate license key: `OBS-PRO-XXXXXXXX-XXXX` (UUID v4 based, matching existing `billing.py` format)
3. Insert into `licenses` table with `status='active'`, `issued_by='stripe'`
4. Return 200

**`customer.subscription.deleted`:**
1. Look up license by `stripe_subscription_id` or `stripe_customer_id`
2. Set `status='cancelled'`, update `expires_at` to `current_period_end`
3. Return 200

#### `POST /api/licenses/validate`

Request body: `{"license_key": "..."}`

1. Look up license in DB by key
2. Check expiry date against current time
3. Return:

```json
{
  "valid": true,
  "product": "solo",
  "status": "active",
  "features": ["free_features", "pro_badge", "license_validation", "stripe_checkout"],
  "expires_at": "2027-06-01T00:00:00Z"
}
```

#### `POST /api/trials/start`

Request body: `{"email": "..."}`

1. Generate license key
2. Insert license row: `status='trialing'`, `trial_ends_at=now()+30d`
3. Return `{license_key, trial_ends_at}`

#### `GET /api/admin/licenses` — List all licenses
Protected by `Authorization: Bearer {ADMIN_API_KEY}` header.
Returns all licenses: id, email, name, product, status, created_at.

#### `POST /api/admin/licenses` — Issue free license
Protected by `Authorization: Bearer {ADMIN_API_KEY}` header.
Request body: `{"email": "...", "name": "...", "product_slug": "solo", "expires_in_days": 365}`

1. Generate license key
2. Insert with `status='active'`, `issued_by='admin'`
3. Return `{license_key, email, expires_at}`

#### `GET /api/admin/stats` — Dashboard counts
Protected by `Authorization: Bearer {ADMIN_API_KEY}` header.
Returns `{active, trialing, expired, total}`

---

## 4. Admin Dashboard

A single responsive HTML page served from Vercel (or static hosting).

### Layout

```
┌──────────────────────────────────────────────────────────┐
│ 🛡️ ObserveCo Licenses          [+ Issue Free License]     │
├──────────────────────────────────────────────────────────┤
│ Filter: [All ▼] [Active] [Trial] [Expired]               │
├──────────┬──────────┬─────────┬────────┬─────────────────┤
│ Email    │ Name     │ Product │ Status │ Created          │
├──────────┼──────────┼─────────┼────────┼─────────────────┤
│ a@b.com  │ Alice    │ Solo    │ Active │ 2026-06-01      │
│ c@d.com  │ Bob      │ Solo    │ Trial  │ 2026-06-01      │
└──────────┴──────────┴─────────┴────────┴─────────────────┘
```

### Issue Free License form (modal)

```
Email: [____________]
Name:  [____________]
Duration: [1 month ▼] [1 year] [Lifetime]
Product: Solo
     [Create License]
```

### Protection

- Protected by `ADMIN_API_KEY` sent as Bearer token
- Stored in browser localStorage on first entry
- Auto-redirects to login if not set
- Mobile-responsive (CSS breakpoints at 768px, 480px)

---

## 5. ObserveCo Client Integration

### Startup flow

```python
# On dashboard startup

LICENSE_FILE = Path.home() / ".observeco" / "license.json"

def check_license():
    """Validate local license against cloud API."""
    if not LICENSE_FILE.exists():
        # Check for local trial token first
        trial_file = Path.home() / ".observeco" / "trial.json"
        if trial_file.exists():
            trial = json.loads(trial_file.read_text())
            if time.time() < trial["expires_at"]:
                return {"pro": True, "trial": True, "days_left": ...}
        return {"pro": False, "trial": False}

    license_data = json.loads(LICENSE_FILE.read_text())
    # POST to Vercel for validation
    try:
        resp = requests.post(
            "https://observeco.com/api/licenses/validate",
            json={"license_key": license_data["key"]},
            timeout=5
        )
        result = resp.json()
        if result["valid"]:
            # Persist cached result for 24h offline tolerance
            license_data["cached_until"] = int(time.time()) + 86400
            license_data["features"] = result.get("features", [])
            LICENSE_FILE.write_text(json.dumps(license_data, indent=2))
            return {"pro": True, "features": result["features"]}
    except requests.RequestException:
        # Offline — use cached result (stale tolerance: 24h)
        if license_data.get("cached_until", 0) > time.time():
            return {"pro": True, "features": license_data.get("features", [])}

    return {"pro": False}
```

### Trial token (offline)

On first access to a Pro-gated feature, if no license exists:

```python
def start_local_trial():
    trial = {
        "started_at": int(time.time()),
        "expires_at": int(time.time()) + 30 * 86400,
    }
    trial_file = Path.home() / ".observeco" / "trial.json"
    trial_file.write_text(json.dumps(trial))
```

The trial token is local-only. No server call. 30-day clock starts on first Pro feature access.

### License entry UI

In the dashboard header or Pro tile:

```
┌────────────────────────────────┐
│ 🔒 Pro Plan                   │
│ Enter your license key:        │
│ [_______________________]      │
│ [Activate]                     │
│                                │
│ Or: [Start 30-day free trial]  │
│        [Subscribe $9/mo]       │
└────────────────────────────────┘
```

- "Activate" calls `POST /api/licenses/validate`
- "Start trial" calls `POST /api/trials/start`
- "Subscribe" opens Stripe Checkout in new tab (current `billing.py` already supports this)

---

## 6. Stripe Webhook Configuration

### Steps

1. Log into Stripe dashboard
2. Go to Developers → Webhooks
3. Add endpoint: `https://observeco.com/api/stripe/webhook`
4. Listen to events: `checkout.session.completed`, `customer.subscription.deleted`
5. Reveal signing secret → already have it in credentials file
6. Set Vercel env var `STRIPE_WEBHOOK_SECRET` to match

### Product config (already done)

| Product | Price ID | Amount |
|---------|----------|--------|
| Solo | `<real-price-id-from-stripe>` | $9/month |
| Trial period | 30 days | Set in `billing.py:subscription_data.trial_period_days` |

---

## 7. Free License Issuance (Admin)

You can issue free Pro licenses at any time:

1. Open admin dashboard: `https://observeco.com/admin` (see §4 for HTML dashboard layout) or use the API directly at `POST /api/admin/licenses`
2. Click "Issue Free License"
3. Enter email + name + duration
4. Click "Create License"
5. Copy the license key
6. Send it to the recipient
7. They enter it in their ObserveCo dashboard → `POST /api/licenses/validate` → Pro unlocked

---

## 8. Implementation Phases

### Phase 1 — Foundation (this task)
- [ ] Supabase schema: products + licenses tables
- [ ] Vercel: 5 API routes
- [ ] Admin dashboard HTML
- [ ] ObserveCo client integration (validate + trial + enter key)
- [ ] Stripe webhook config

### Phase 2 — Pro Feature Gating (next)
- [ ] Audit every Pro feature in dashboard for gate check
- [ ] Wire gate function into server.py endpoints
- [ ] Show "Unlock with Pro" banners on locked features

### Phase 3 — Future
- [ ] Team tier ($49/mo)
- [ ] Subscription management (cancel, upgrade)
- [ ] Email receipts / invoice generation
- [ ] Usage-based billing (per agent)
