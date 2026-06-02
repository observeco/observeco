import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;
const ADMIN_KEY = process.env.OBSERVECO_ADMIN_KEY || 'admin-token';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Key');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const token = req.headers['x-admin-key'];
  if (token !== ADMIN_KEY) return res.status(401).json({ error: 'Unauthorized' });

  const supabase = createClient(supabaseUrl, supabaseServiceKey);

  const { data: counts, error } = await supabase
    .from('licenses')
    .select('status', { count: 'exact', head: false });

  if (error) return res.status(500).json({ error: error.message });

  const stats = { total: 0, active: 0, trialing: 0, expired: 0, cancelled: 0 };
  for (const row of counts) {
    stats.total++;
    if (stats[row.status] !== undefined) stats[row.status]++;
  }

  const { count: telemetryCount } = await supabase
    .from('telemetry_events')
    .select('*', { count: 'exact', head: true });

  res.json({ ...stats, telemetry_events: telemetryCount || 0 });
}