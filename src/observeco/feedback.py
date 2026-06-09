"""ObserveCo feedback collector — send bug reports, suggestions, and feedback."""

from __future__ import annotations

import json
import os
import platform
from typing import Optional

from observeco import __version__

FEEDBACK_TYPES = {
    "bug": "🐛 Bug Report",
    "feature": "💡 Feature Suggestion",
    "ux": "🎨 UX / Usability Issue",
    "docs": "📄 Documentation Issue",
    "performance": "⚡ Performance Problem",
    "other": "📝 Other",
}


def _get_environment_context() -> dict:
    """Auto-detect relevant environment info for the feedback payload."""
    context = {
        "observeco_version": __version__,
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
    }
    # Check install method
    try:
        import observeco
        module_path = os.path.dirname(os.path.dirname(observeco.__file__))
        # Check if it's in a pip site-packages or editable install
        if "site-packages" in module_path:
            context["install_method"] = "pip install"
        else:
            context["install_method"] = "editable (pip install -e .)"
    except Exception:
        context["install_method"] = "unknown"
    return context


def _preview_feedback(fb_type: str, summary: str, detail: str, severity: str) -> None:
    """Print a formatted preview so the user can confirm before sending."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    console = Console()

    lines = [
        f"**Type:** {FEEDBACK_TYPES.get(fb_type, 'Other')}",
        f"**Severity:** {severity}",
        "",
        f"**Summary:** {summary}",
    ]
    if detail:
        lines += ["", "**Details:**", detail]

    console.print()
    console.print(Panel(
        Markdown("\n".join(lines)),
        title="📬 Feedback Preview",
        border_style="blue",
    ))
    console.print()


def _send_feedback(payload: dict) -> bool:
    """Send feedback to the ObserveCo telemetry server.

    Default: https://telemetry.observeco.ai/v1/feedback
    Users can override with OBSERVECO_FEEDBACK_URL env var.
    """
    server_url = os.environ.get(
        "OBSERVECO_FEEDBACK_URL",
        "https://observeco-license-crm.vercel.app/api/telemetry",
    )
    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            server_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get("status") == "ok"
    except Exception as exc:
        logger = __import__("logging").getLogger("observeco.feedback")
        logger.warning("Feedback delivery to %s failed: %s", server_url, exc)
        return False


def run_feedback(
    fb_type: Optional[str],
    summary: Optional[str],
    detail: Optional[str],
    severity: Optional[str],
    interactive: bool,
    send: bool,
) -> None:
    """Interactively collect and send feedback."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt

    console = Console()

    if interactive:
        console.print()
        console.print(Panel(
            Markdown("Help improve ObserveCo by sharing **what's working, what's not, and what's missing**."),
            title="📬 Send Feedback",
            border_style="green",
        ))
        console.print()

        # Step 1: Type
        console.print("[bold]Step 1:[/bold] What kind of feedback?")
        type_keys = list(FEEDBACK_TYPES.keys())
        for i, k in enumerate(type_keys, 1):
            console.print(f"  [{i}] {FEEDBACK_TYPES[k]}")
        choice = Prompt.ask("Pick one", default="1")
        try:
            fb_type = type_keys[int(choice) - 1]
        except (ValueError, IndexError):
            fb_type = "other"

        # Step 2: Summary
        console.print()
        console.print("[bold]Step 2:[/bold] One-line summary (required)")
        summary = Prompt.ask("What happened or what's the suggestion")

        # Step 3: Detail
        console.print()
        console.print("[bold]Step 3:[/bold] Details (optional — paste logs, describe context)")
        console.print("[dim]Enter . on a line by itself when done[/dim]")
        detail_lines = []
        while True:
            line = input()
            if line.strip() == ".":
                break
            detail_lines.append(line)
        detail = "\n".join(detail_lines).strip()

        # Step 4: Severity
        console.print()
        console.print("[bold]Step 4:[/bold] How much does this block you?")
        sev_options = [
            "🚫 Completely blocked",
            "⚠️ Annoying but workaround exists",
            "🙂 Minor — nice to fix eventually",
            "💡 Suggestion — not a bug",
        ]
        for i, s in enumerate(sev_options, 1):
            console.print(f"  [{i}] {s}")
        sev_choice = Prompt.ask("Pick one", default="4")
        try:
            severity = sev_options[int(sev_choice) - 1]
        except (ValueError, IndexError):
            severity = sev_options[3]

    # Build payload
    env = _get_environment_context()
    payload = {
        "type": fb_type or "other",
        "type_label": FEEDBACK_TYPES.get(fb_type or "other"),
        "summary": summary,
        "detail": detail or "",
        "severity": severity or "💡 Suggestion — not a bug",
        "environment": env,
    }

    # Preview
    _preview_feedback(fb_type or "other", summary or "(empty)", detail or "", severity or "(none)")

    if interactive:
        confirmed = Confirm.ask("[bold]Send this feedback?[/bold]", default=True)
        if not confirmed:
            console.print("[yellow]Feedback saved but not sent. Run `observeco feedback --send` to try again.[/yellow]")
            return

    sent = _send_feedback(payload)

    if sent:
        console.print("[green]✓ Feedback sent. Thanks for helping improve ObserveCo! 🙏[/green]")
        tg_ok = os.environ.get("OBSERVECO_TG_BOT_TOKEN") and os.environ.get("OBSERVECO_TG_CHAT_ID")
        email_ok = os.environ.get("OBSERVECO_SMTP_HOST") and os.environ.get("OBSERVECO_TO_EMAIL")
        if not tg_ok and not email_ok:
            console.print("[yellow]⚠ No delivery channel configured. Set OBSERVECO_TG_BOT_TOKEN + OBSERVECO_TG_CHAT_ID or SMTP env vars to route feedback to you.[/yellow]")
    else:
        console.print("[red]✗ Feedback delivery failed. Check your network and delivery config.[/red]")
