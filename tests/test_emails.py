"""Tests for the observeco.emails module."""
from __future__ import annotations

from observeco.emails import send_email
from observeco.emails.templates import get_template, list_templates


def test_list_templates_returns_all_nine():
    names = list_templates()
    assert len(names) == 9
    assert "welcome" in names
    assert "trial_reminder_7d" in names
    assert "trial_reminder_3d" in names
    assert "trial_reminder_1d" in names
    assert "trial_expired" in names
    assert "grace_period" in names
    assert "payment_failed" in names
    assert "cancellation_confirmed" in names
    assert "win_back" in names


def test_template_rendering():
    subject, html = get_template("welcome", {
        "first_name": "Alice",
        "trial_days_left": "30",
        "subscribe_url": "https://observeco.dev/sub",
        "manage_url": "https://observeco.dev/manage",
        "support_email": "support@observeco.dev",
    })
    assert "Welcome to ObserveCo" in subject
    assert "Alice" in html
    assert "30 days" in html
    assert "{{first_name}}" not in html
    assert "{{trial_days_left}}" not in html
    assert "<!DOCTYPE html>" in html


def test_template_unknown_key_raises():
    import pytest
    with pytest.raises(KeyError, match="Unknown email template"):
        get_template("nonexistent", {})


def test_template_partial_vars():
    """Missing variables are left as-is."""
    subject, html = get_template("trial_reminder_7d", {})
    assert "{{first_name}}" in html  # Not replaced — left as placeholder
    assert "7 days left" in subject


def test_dry_run():
    """send_email dry_run returns True without sending."""
    result = send_email("test@example.com", "welcome", {"first_name": "Bob"}, dry_run=True)
    assert result is True


def test_send_email_unknown_template():
    """Unknown template returns False."""
    result = send_email("test@example.com", "nonexistent", {})
    assert result is False
