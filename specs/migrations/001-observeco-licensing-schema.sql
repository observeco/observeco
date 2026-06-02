-- ============================================================
-- ObserveCo Licensing — Supabase Migration
-- Project: qivlbpklmwghtgeyxncg.supabase.co
-- Run this in the Supabase Dashboard → SQL Editor
-- ============================================================

-- 1. Products table
CREATE TABLE IF NOT EXISTS public.products (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  stripe_price_id TEXT,
  features JSONB DEFAULT '[]'::jsonb,
  trial_days INT DEFAULT 0,
  price_display TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Licenses table
CREATE TABLE IF NOT EXISTS public.licenses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_slug TEXT REFERENCES public.products(slug),
  email TEXT NOT NULL,
  name TEXT,
  license_key TEXT UNIQUE NOT NULL,
  status TEXT DEFAULT 'trialing' CHECK (status IN ('trialing', 'active', 'expired', 'cancelled')),
  trial_ends_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  stripe_subscription_id TEXT,
  stripe_customer_id TEXT,
  issued_by TEXT DEFAULT 'self' CHECK (issued_by IN ('self', 'stripe', 'admin')),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_licenses_key ON public.licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_licenses_email ON public.licenses(email);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON public.licenses(status);

-- 4. RLS
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.licenses ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies
CREATE POLICY "products_public_read" ON public.products
  FOR SELECT USING (true);

CREATE POLICY "licenses_anon_insert" ON public.licenses
  FOR INSERT WITH CHECK (true);

CREATE POLICY "licenses_anon_select" ON public.licenses
  FOR SELECT USING (true);

-- 6. Seed data
INSERT INTO public.products (name, slug, stripe_price_id, features, trial_days, price_display)
VALUES
  ('Free', 'free', NULL, '["fleet_view", "pulse_check", "circuit_breakers", "token_breakdown", "drift_trend", "error_history", "heal_button", "alerts", "memory_garden", "cli_tools"]'::jsonb, 0, '$0'),
  ('Solo', 'solo', 'price_solo_monthly', '["free_features", "pro_badge", "license_validation"]'::jsonb, 30, '$9/mo')
ON CONFLICT (slug) DO NOTHING;

-- 7. Auto-update trigger for licenses.updated_at
CREATE OR REPLACE FUNCTION public.update_licenses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_licenses_updated_at ON public.licenses;
CREATE TRIGGER trigger_licenses_updated_at
  BEFORE UPDATE ON public.licenses
  FOR EACH ROW
  EXECUTE FUNCTION public.update_licenses_updated_at();
