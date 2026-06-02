import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { email, name } = req.body || {};
  if (!email) return res.status(400).json({ error: 'email required' });

  const supabase = createClient(supabaseUrl, supabaseServiceKey);
  const crypto = require('crypto');
  const trialToken = `OBS-TRIAL-${crypto.randomBytes(6).toString('hex').toUpperCase()}`;

  const { data, error } = await supabase.from('licenses').insert({
    email,
    name: name || null,
    product_slug: 'solo',
    license_key: trialToken,
    status: 'trialing',
    trial_ends_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    issued_by: 'self',
  }).select().single();

  if (error) {
    return res.status(500).json({ error: 'Failed to create trial' });
  }

  res.json({
    license_key: trialToken,
    product: 'solo',
    status: 'trialing',
    trial_ends_at: data.trial_ends_at,
  });
}