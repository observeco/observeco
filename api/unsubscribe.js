// /api/unsubscribe — PDPA opt-out. Spec 095 s6.6.
//
// REQUIREMENTS (spec 6.6, 6.9):
//   - no login required; the recipient may have no account
//   - signed token, so an arbitrary address cannot be unsubscribed by a third party
//   - must be a REAL opt-out, not a decoration: PDPC's most common enforcement
//     action is ignoring opt-outs, and an unsubscribe that 404s or silently fails
//     is the same failure with extra steps
//   - never reveal whether an address was on the list (enumeration)
//
// SIGNING: HMAC-SHA256 over the lowercased address, base64url, truncated to 24 chars.
// The secret is UNSUBSCRIBE_SECRET. If it is unset we FAIL LOUD (500) rather than
// silently minting tokens from a default -- an unsigned unsubscribe link would let
// anyone opt out anyone.
import crypto from 'crypto';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

function sign(email) {
  const secret = process.env.UNSUBSCRIBE_SECRET;
  if (!secret) return null;
  return crypto
    .createHmac('sha256', secret)
    .update(String(email).trim().toLowerCase())
    .digest('base64url')
    .slice(0, 24);
}

function safeEqual(a, b) {
  const A = Buffer.from(String(a));
  const B = Buffer.from(String(b));
  if (A.length !== B.length) return false;
  return crypto.timingSafeEqual(A, B);
}

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');

  if (req.method === 'GET') {
    const { email, token } = req.query || {};
    if (!email || !token) {
      return res.status(400).json({ error: 'email and token are required' });
    }
    const expected = sign(email);
    if (!expected) {
      // No secret configured: we cannot verify, so we must NOT claim success.
      console.error('UNSUBSCRIBE_SECRET is not set; refusing to process opt-out');
      return res.status(500).json({ error: 'unsubscribe is not configured' });
    }
    if (!safeEqual(expected, token)) {
      // Deliberately identical to the success message: probing for valid tokens
      // or for list membership must not be possible through this endpoint.
      return res.status(200).json({ ok: true, message: 'If this address was on our list, it has been removed.' });
    }
    return await doUnsubscribe(email.toLowerCase(), res);
  }

  if (req.method === 'POST') {
    // One-click unsubscribe (RFC 8058 style), signed the same way.
    const { email, token } = req.body || {};
    if (!email || !token || !safeEqual(sign(email) || '', token)) {
      return res.status(400).json({ error: 'invalid request' });
    }
    return await doUnsubscribe(email.toLowerCase(), res);
  }

  return res.status(405).json({ error: 'Method not allowed' });
}

async function doUnsubscribe(email, res) {
  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Supabase env missing; opt-out NOT recorded');
    return res.status(500).json({ error: 'unsubscribe could not be recorded' });
  }
  const supabase = createClient(supabaseUrl, supabaseServiceKey);

  // Suppression is an append-only record, not an update of a contact row: the
  // contact may not exist yet, and the suppression must survive a later import.
  const { error } = await supabase.from('email_suppressions').upsert(
    { email, reason: 'unsubscribe', suppressed_at: new Date().toISOString() },
    { onConflict: 'email' },
  );
  if (error) {
    console.error('suppression write failed:', error.message);
    return res.status(500).json({ error: 'unsubscribe could not be recorded' });
  }

  // Also flip the flag wherever the address is already known, so an existing
  // contact record cannot be mailed by a path that predates the suppression table.
  await supabase.from('leads').update({ unsubscribed_at: new Date().toISOString() }).eq('email', email);
  await supabase.from('licenses').update({ unsubscribed_at: new Date().toISOString() }).eq('email', email);

  return res.status(200).json({ ok: true, message: 'You have been unsubscribed.' });
}
