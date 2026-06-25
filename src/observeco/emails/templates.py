"""HTML email templates for ObserveCo transactional emails.

Each template is a ``(subject, html_body)`` tuple rendered via simple
``{{variable}}`` substitution (no Jinja dependency).

Templates are defined as plain strings and rendered on demand by
``get_template(name, variables)``.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Shared HTML fragments
# ---------------------------------------------------------------------------

_BRAND_COLOR = "#2563eb"  # Blue-600
_BG_COLOR = "#f8fafc"
_TEXT_COLOR = "#1e293b"
_MUTED_COLOR = "#64748b"
_BORDER_COLOR = "#e2e8f0"

_UNSUBSCRIBE_LINK = (
    '<a href="https://observeco.com/unsubscribe" '
    'style="color:{muted};text-decoration:underline;">Unsubscribe</a>'
).format(muted=_MUTED_COLOR)


def _wrapper(content: str) -> str:
    """Wrap content in a responsive, mobile-friendly email shell."""
    return (
        "<!DOCTYPE html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        "<title>ObserveCo</title>"
        "</head>"
        '<body style="margin:0;padding:0;background-color:{bg};'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,'
        "Helvetica,Arial,sans-serif;\">"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background-color:{bg};"><tr><td align="center" style="padding:32px 16px;">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="max-width:600px;width:100%;">'
        # Logo / brand header
        '<tr><td style="padding-bottom:24px;text-align:center;">'
        '<!-- LOGO: Replace src with your hosted logo URL -->'
        '<img src="https://observeco.com/logo.png" alt="ObserveCo" width="40" '
        'style="width:40px;height:auto;display:inline-block;vertical-align:middle;">'
        ' <span style="font-size:22px;font-weight:700;color:{brand};'
        "vertical-align:middle;\">ObserveCo</span>"
        "</td></tr>"
        # Content card
        '<tr><td style="background-color:#ffffff;border-radius:8px;'

        'border:1px solid {border};padding:32px;">'
        "{content}"
        "</td></tr>"
        # Footer
        '<tr><td style="padding-top:24px;text-align:center;font-size:12px;'
        'color:{muted};line-height:1.6;">'
        "ObserveCo &mdash; Runtime observability for AI agent systems.<br>"
        '{unsubscribe} &bull; '
        '<a href="https://observeco.com/privacy" style="color:{muted};'
        'text-decoration:underline;">Privacy Policy</a> &bull; '
        '<a href="https://observeco.com/support" style="color:{muted};'
        'text-decoration:underline;">Support</a>'
        "</td></tr>"
        "</table></td></tr></table>"
        "</body></html>"
    ).format(
        bg=_BG_COLOR,
        brand=_BRAND_COLOR,
        border=_BORDER_COLOR,
        muted=_MUTED_COLOR,
        unsubscribe=_UNSUBSCRIBE_LINK,
        content=content,
    )


def _btn(url: str, label: str) -> str:
    """Render a branded CTA button (inline CSS for email clients)."""
    return (
        '<a href="{url}" style="display:inline-block;padding:12px 28px;'
        "background-color:{brand};color:#ffffff;font-size:15px;font-weight:600;"
        "text-decoration:none;border-radius:6px;margin:16px 0;\">"
        "{label}</a>"
    ).format(url=url, brand=_BRAND_COLOR, label=label)


def _p(text: str, **extra_css: str) -> str:
    """Render a <p> with standard body styling."""
    style = (
        "color:{color};font-size:15px;line-height:1.6;"
        "margin:0 0 12px 0;"
    ).format(color=_TEXT_COLOR)
    for k, v in extra_css.items():
        style += f"{k}:{v};"
    return '<p style="{style}">{text}</p>'.format(style=style, text=text)


def _heading(text: str, level: int = 1) -> str:
    """Render a heading."""
    size = {1: 22, 2: 18}.get(level, 18)
    return (
        '<h{level} style="color:{color};font-size:{size}px;'
        'margin:0 0 16px 0;font-weight:700;">{text}</h{level}>'
    ).format(level=level, color=_TEXT_COLOR, size=size, text=text)


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, tuple[str, str]] = {}


def _register(name: str, subject: str, body_content: str) -> None:
    _TEMPLATES[name] = (subject, _wrapper(body_content))


# ── 1. Welcome ────────────────────────────────────────────────────────────

_register(
    "welcome",
    "Welcome to ObserveCo! 🎉",
    _heading("Welcome aboard, {{first_name}}!")
    + _p(
        "Thanks for signing up for ObserveCo. You now have real-time "
        "observability for your AI agent systems — traces, metrics, "
        "and alerts, all in one place."
    )
    + _p(
        "Your trial starts now. You have <strong>{{trial_days_left}} days</strong> "
        "to explore every feature — no credit card required."
    )
    + _btn("{{subscribe_url}}", "Open Your Dashboard")
    + _p(
        "Need help getting started? Reply to this email or reach us at "
        '<a href="mailto:{{support_email}}" style="color:{brand};text-decoration:underline;">'
        "{{support_email}}</a>.".format(brand=_BRAND_COLOR),
    ),
)

# ── 2. Trial Reminder — 7 Days ──────────────────────────────────────────

_register(
    "trial_reminder_7d",
    "Your ObserveCo trial — 7 days left",
    _heading("Your trial is going strong 💪")
    + _p(
        "Hi {{first_name}}, you have <strong>{{trial_days_left}} days</strong> remaining in your "
        "ObserveCo trial. Plenty of time to explore dashboards, alerts, "
        "and agent health monitoring."
    )
    + _p("Here are a few things to try:")
    + _p("• Set up an alert for agent latency spikes")
    + _p("• Explore the trace timeline view")
    + _p("• Check your agent health score on the dashboard")
    + _btn("{{subscribe_url}}", "Continue Exploring")
    + _p(
        "Questions? Reach us at "
        '<a href="mailto:{{support_email}}" style="color:{brand};text-decoration:underline;">'
        "{{support_email}}</a>.".format(brand=_BRAND_COLOR),
    ),
)

# ── 3. Trial Reminder — 3 Days ──────────────────────────────────────────

_register(
    "trial_reminder_3d",
    "3 days left — keep your ObserveCo setup",
    _heading("Only 3 days left ⏳")
    + _p(
        "Your ObserveCo trial ends in <strong>{{trial_days_left}} days</strong>. "
        "After that, your dashboards and alert configurations will be paused."
    )
    + _p(
        "Subscribe now to keep everything running — plans start at just $9/month."
    )
    + _btn("{{subscribe_url}}", "Subscribe Now")
    + _p(
        "You can manage your account anytime at "
        '<a href="{{manage_url}}" style="color:{brand};text-decoration:underline;">'
        "{{manage_url}}</a>.".format(brand=_BRAND_COLOR),
    ),
)

# ── 4. Trial Reminder — 1 Day ──────────────────────────────────────────

_register(
    "trial_reminder_1d",
    "Last day of your ObserveCo trial",
    _heading("Final day ⚡")
    + _p(
        "Your ObserveCo trial expires <strong>tomorrow</strong>. "
        "Your data and dashboards will be paused until you subscribe."
    )
    + _btn("{{subscribe_url}}", "Subscribe Before It Expires")
    + _p(
        "Don't lose access to your agent monitoring setup. "
        "Plans start at $9/month.",
    ),
)

# ── 5. Trial Expired ────────────────────────────────────────────────────

_register(
    "trial_expired",
    "Your ObserveCo trial has ended",
    _heading("Your trial has ended")
    + _p(
        "Hi {{first_name}}, your ObserveCo trial has now expired. "
        "Your dashboards and alerts are paused, but your data is preserved "
        "for 30 days."
    )
    + _p("Subscribe to restore full access:")
    + _btn("{{subscribe_url}}", "Resubscribe")
    + _p(
        "Manage your account: "
        '<a href="{{manage_url}}" style="color:{brand};text-decoration:underline;">'
        "{{manage_url}}</a>.".format(brand=_BRAND_COLOR),
    ),
)

# ── 6. Grace Period ─────────────────────────────────────────────────────

_register(
    "grace_period",
    "Action needed — payment issue on ObserveCo",
    _heading("We couldn't process your payment")
    + _p(
        "Hi {{first_name}}, we had trouble charging your card for ObserveCo. "
        "Your account is in a <strong>7-day grace period</strong> — your "
        "dashboards are still active."
    )
    + _p(
        "Please update your payment method to avoid any interruption."
    )
    + _btn("{{manage_url}}", "Update Payment Method")
    + _p(
        "If you need help, contact us at "
        '<a href="mailto:{{support_email}}" style="color:{brand};text-decoration:underline;">'
        "{{support_email}}</a>.".format(brand=_BRAND_COLOR),
    ),
)

# ── 7. Payment Failed ───────────────────────────────────────────────────

_register(
    "payment_failed",
    "Payment failed — ObserveCo subscription",
    _heading("Payment failed ❌")
    + _p(
        "Hi {{first_name}}, we were unable to process your latest ObserveCo "
        "payment. Your subscription has been paused."
    )
    + _p(
        "Update your payment details to restore access:"
    )
    + _btn("{{manage_url}}", "Fix Payment Method")
    + _p(
        "If you believe this is an error, please reach out to "
        '<a href="mailto:{{support_email}}" style="color:{brand};text-decoration:underline;">'
        "{{support_email}}</a>.".format(brand=_BRAND_COLOR),
    ),
)

# ── 8. Cancellation Confirmed ───────────────────────────────────────────

_register(
    "cancellation_confirmed",
    "Your ObserveCo subscription has been cancelled",
    _heading("Subscription cancelled")
    + _p(
        "Hi {{first_name}}, your ObserveCo subscription has been cancelled "
        "as requested. You'll retain access until the end of your current "
        "billing period."
    )
    + _p(
        "We're sorry to see you go. If you change your mind, "
        "you can resubscribe anytime:"
    )
    + _btn("{{subscribe_url}}", "Resubscribe")
    + _p(
        "We'd love to hear your feedback — what could we do better? "
        "Reply to this email or contact "
        '<a href="mailto:{{support_email}}" style="color:{brand};text-decoration:underline;">'
        "{{support_email}}</a>.".format(brand=_BRAND_COLOR),
    ),
)

# ── 9. Win-back ─────────────────────────────────────────────────────────

_register(
    "win_back",
    "We miss you at ObserveCo 💙",
    _heading("We'd love to have you back")
    + _p(
        "Hi {{first_name}}, it's been a while since you used ObserveCo. "
        "We've shipped some great new features since then:"
    )
    + _p("• AI-powered anomaly detection")
    + _p("• Multi-agent correlation traces")
    + _p("• Slack & Teams alert integrations")
    + _p("• Custom dashboard builder")
    + _p(
        "Come back and see what's new — your agent teams deserve it."
    )
    + _btn("{{subscribe_url}}", "Welcome Back — Subscribe Now")
    + _p(
        "Questions? We're at "
        '<a href="mailto:{{support_email}}" style="color:{brand};text-decoration:underline;">'
        "{{support_email}}</a>.".format(brand=_BRAND_COLOR),
    ),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_template(name: str, variables: dict[str, Any]) -> tuple[str, str]:
    """Render a named template with the given variables.

    Parameters
    ----------
    name:
        Template key (one of the registered names).
    variables:
        Dict of ``{{key}}`` replacement values.  Unknown keys are
        left as-is.  Missing keys leave their placeholder untouched.

    Returns
    -------
    tuple[str, str]
        ``(subject, html_body)`` with all ``{{…}}`` placeholders replaced.

    Raises
    ------
    KeyError
        If *name* is not a registered template.
    """
    if name not in _TEMPLATES:
        available = ", ".join(sorted(_TEMPLATES.keys()))
        raise KeyError(
            f"Unknown email template {name!r}. Available: {available}"
        )

    subject_template, body_template = _TEMPLATES[name]

    # Simple {{variable}} substitution
    def _render(text: str) -> str:
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            text = text.replace(placeholder, str(value))
        return text

    return _render(subject_template), _render(body_template)


def list_templates() -> list[str]:
    """Return the names of all registered templates."""
    return sorted(_TEMPLATES.keys())
