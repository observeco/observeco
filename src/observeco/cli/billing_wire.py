"""Wire Stripe live credentials from intelligence layer into billing config.

Reads: ~/.hermes/intelligence/decisions/stripe-credentials-*.json
Writes: ~/.observeco/billing.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from observeco.dirs import get_data_dir, hermes_home  # noqa: E402 - late import to control side effects

BILLING_DIR = get_data_dir()
BILLING_FILE = BILLING_DIR / "billing.json"


def _intelligence_dir() -> Path | None:
    """Return the intelligence decisions directory, or None if Hermes not found."""
    hh = hermes_home()
    if hh is None:
        return None
    return hh / "intelligence" / "decisions"


def find_latest_credentials() -> dict | None:
    """Find the most recent Stripe credentials decision artifact."""
    intel_dir = _intelligence_dir()
    if intel_dir is None or not intel_dir.exists():
        return None

    creds_files = sorted(intel_dir.glob("stripe-credentials-*.json"))
    if not creds_files:
        return None

    latest = creds_files[-1]
    try:
        data = json.loads(latest.read_text())
        return data.get("payload") or data
    except (json.JSONDecodeError, KeyError):
        return None


def wire_credentials() -> dict:
    """Wire credentials into billing config. Returns status dict."""
    creds = find_latest_credentials()
    if not creds:
        return {"status": "error", "message": "No Stripe credentials found in intelligence layer"}

    secret_key = creds.get("STRIPE_SECRET_KEY", "")
    publishable_key = creds.get("STRIPE_PUBLISHABLE_KEY", "")
    webhook_secret = creds.get("STRIPE_WEBHOOK_SECRET", "")
    product_ids = creds.get("product_ids", {})

    if not secret_key or not publishable_key:
        return {"status": "error", "message": "Credentials missing required keys"}

    from observeco.billing import configure
    configure(
        stripe_secret=secret_key,
        stripe_publishable=publishable_key,
        solo_price=product_ids.get("solo", ""),
        team_price=product_ids.get("team", ""),
        webhook_secret=webhook_secret,
    )

    return {
        "status": "configured",
        "mode": "live",
        "published_key": publishable_key[:14] + "..." if publishable_key else "",
        "has_products": bool(product_ids),
        "timestamp": int(time.time()),
    }


def verify_config() -> dict:
    """Verify billing config is active and live."""
    from observeco.billing import get_billing_status
    return get_billing_status()


if __name__ == "__main__":
    result = wire_credentials()
    print(json.dumps(result, indent=2))
    if result["status"] == "configured":
        status = verify_config()
        print(f"\nBilling status: configured={status.get('configured')}, "
              f"mode={'live' if status.get('configured') else 'demo'}")
