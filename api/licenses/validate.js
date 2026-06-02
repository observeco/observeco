import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { license_key, email } = req.body || {};
  if (!license_key) return res.status(400).json({ error: 'license_key required' });

  const supabase = createClient(supabaseUrl, supabaseServiceKey);
  const { data, error } = await supabase
    .from('licenses')
    .select('id, email, name, product_slug, status, trial_ends_at, expires_at, created_at, metadata')
    .eq('license_key', license_key)
    .single();

  if (error || !data) {
    return res.status(404).json({ valid: false, error: 'License not found' });
  }

  const now = new Date().toISOString();
  let valid = data.status === 'active';
  let expiresAt = data.expires_at;

  // Check trial expiry
  if (data.status === 'trialing' && data.trial_ends_at) {
    valid = new Date(data.trial_ends_at) > new Date();
    if (!valid) {
      // Auto-expire trial
      await supabase.from('licenses').update({ status: 'expired' }).eq('id', data.id);
    }
  }

  // Check expiry
  if (data.expires_at && new Date(data.expires_at) <= new Date()) {
    valid = false;
    if (data.status === 'active') {
      await supabase.from('licenses').update({ status: 'expired' }).eq('id', data.id);
    }
  }

  // If email provided, update it
  if (email && email !== data.email) {
    await supabase.from('licenses').update({ email }).eq('id', data.id);
  }

  res.json({
    valid,
    product: data.product_slug,
    status: valid ? data.status : 'expired',
    expires_at: expiresAt,
    trial_ends_at: data.trial_ends_at,
    created_at: data.created_at,
  });
}