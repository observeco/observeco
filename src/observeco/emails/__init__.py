"""Transactional email module — Resend API integration.

Fire-and-forget sending via background threads. Never blocks the caller,
never raises — all failures are logged as warnings.

Usage::

    from observeco.emails import send_email

    send_email("user@example.com", "welcome", {"first_name": "Alice"})
"""

from observeco.emails.sender import send_email

__all__ = ["send_email"]
