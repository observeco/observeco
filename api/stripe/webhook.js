import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

export default async function handler(req, res) {
  // CORS headers for ObserveCo desktop client
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const sig = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  const stripe = new (require('stripe'))(process.env.STRIPE_SECRET_KEY);

  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
  } catch (err) {
    return res.status(400).json({ error: `Webhook signature verification failed: ${err.message}` });
  }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    const crypto = require('crypto');
    const licenseKey = `OBS-${crypto.randomBytes(4).toString('hex').toUpperCase()}-${crypto.randomBytes(2).toString('hex').toUpperCase()}`;

    const { error } = await supabase.from('licenses').insert({
      email: session.customer_email || session.customer_details?.email || 'unknown',
      name: session.customer_details?.name || null,
      product_slug: 'solo',
      license_key: licenseKey,
      status: 'active',
      stripe_subscription_id: session.subscription,
      stripe_customer_id: session.customer,
      issued_by: 'stripe',
      trial_ends_at: null,
      expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
      metadata: { session_id: session.id },
    });

    if (error) {
      console.error('Supabase insert error:', error);
      return res.status(500).json({ error: 'Failed to create license' });
    }

    console.log(`License created: ${licenseKey} for ${session.customer_email}`);
  }

  res.status(200).json({ received: true });
}

export const config = {
  api: { bodyParser: false },
};