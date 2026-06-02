import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const body = req.body || {};
  const { event, version, machine_id, payload } = body;

  if (!event) return res.status(400).json({ error: 'event required' });

  const supabase = createClient(supabaseUrl, supabaseServiceKey);
  const { error } = await supabase.from('telemetry_events').insert({
    event,
    version: version || 'unknown',
    machine_id: machine_id || 'unknown',
    os: body.os || null,
    python_version: body.python_version || null,
    payload: payload || {},
  });

  if (error) {
    console.error('Telemetry insert error:', error);
    return res.status(500).json({ error: 'Failed to record event' });
  }

  // Always 200 — fire-and-forget
  res.status(200).end();
}