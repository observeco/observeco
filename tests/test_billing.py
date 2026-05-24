"""Tests for billing module — simulated checkout flow."""
import json

from observeco.billing import BillingConfig, create_checkout_session, handle_webhook


def test_billing_config_default():
    config = BillingConfig()
    assert config.stripe_publishable_key == ""
    assert config.stripe_secret_key == ""
    assert config.solo_price_id == "price_solo_monthly"
    assert config.team_price_id == "price_team_monthly"
    assert config.is_active is False


def test_billing_configure_sets_keys():
    config = BillingConfig()
    config.stripe_secret_key = "sk_test_xxx"
    config.stripe_publishable_key = "pk_test_xxx"
    assert config.stripe_secret_key == "sk_test_xxx"
    assert config.stripe_publishable_key == "pk_test_xxx"


def test_create_checkout_simulated():
    """Without real Stripe keys, checkout should return simulated session."""
    result = create_checkout_session(email="test@example.com", plan="solo")
    assert result is not None
    assert "session_id" in result
    assert "url" in result
    assert "simulated" in result.get("session_id", "") or "demo" in result.get("session_id", "")


def test_create_checkout_team_plan():
    result = create_checkout_session(email="team@example.com", plan="team")
    assert result is not None
    assert "session_id" in result


def test_handle_webhook_simulated():
    payload = json.dumps({
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_email": "test@example.com",
                "mode": "subscription",
                "amount_total": 900,
            }
        }
    })
    result = handle_webhook(payload.encode())
    assert result is not None
    assert "status" in result
