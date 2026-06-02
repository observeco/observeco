import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;
const ADMIN_KEY = process.env.OBSERVECO_ADMIN_KEY || 'admin-token';

function auth(req) {
  const token = req.headers['x-admin-key'];
  return token === ADMIN_KEY;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Key');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (!auth(req)) return res.status(401).json({ error: 'Unauthorized' });

  const supabase = createClient(supabaseUrl, supabaseServiceKey);

  if (req.method === 'GET') {
    const { status, email } = req.query;
    let query = supabase.from('licenses').select('*').order('created_at', { ascending: false });
    if (status) query = query.eq('status', status);
    if (email) query = query.ilike('email', `%${email}%`);
    const { data, error } = await query;
    if (error) return res.status(500).json({ error: error.message });
    return res.json(data);
  }

  if (req.method === 'POST') {
    const { email, name, product_slug } = req.body || {};
    if (!email) return res.status(400).json({ error: 'email required' });
    const crypto = require('crypto');
    const licenseKey = `OBS-ADMIN-${crypto.randomBytes(4).toString('hex').toUpperCase()}`;
    const { data, error } = await supabase.from('licenses').insert({
      email, name: name || null,
      product_slug: product_slug || 'solo',
      license_key: licenseKey,
      status: 'active',
      expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
      issued_by: 'admin',
    }).select().single();
    if (error) return res.status(500).json({ error: error.message });
    return res.json(data);
  }

  res.status(405).json({ error: 'Method not allowed' });
}