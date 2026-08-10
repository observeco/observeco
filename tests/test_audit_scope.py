"""Positive tests for the referential-integrity audit.

The discipline: every scope fix must have a positive test. After teaching the
audit about inline <style>, plant a genuinely-undefined var and confirm it STILL
fires. Otherwise we converge on green by teaching the script to look away —
rebuilding `|| echo` with better manners.

These tests call the audit's pure functions directly (no DB, no server).
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

_AUDIT_PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "audit_referential_integrity.py"
_spec = importlib.util.spec_from_file_location("audit_ref_int", _AUDIT_PATH)
assert _spec and _spec.loader, "could not load audit script"
audit = importlib.util.module_from_spec(_spec)
sys.modules["audit_ref_int"] = audit
assert _spec.loader
_spec.loader.exec_module(audit)


def test_undefined_var_still_fires_after_inline_style_scope():
    """A var defined ONLY in inline <style> must NOT be reported undefined."""
    defined = audit._css_vars_defined()
    # --sec is defined in pathway.html's inline <style>; with the scope fix it
    # must be in the defined set (it was a false-positive before the fix).
    assert "sec" in defined, (
        "--sec is defined in pathway.html's inline <style>; "
        "the scope fix should have made it a defined var"
    )


def test_undefined_var_detection_is_positive():
    """A genuinely-undefined var must still be caught (positive control).

    --definitely-not-a-real-token should not exist anywhere, so it must be in
    the undefined set if the audit's detection logic works at all.
    """
    # Inject a fake reference and confirm direction2's referenced set catches it.
    fake_refs = audit._css_vars_referenced("color: var(--definitely-not-a-real-token)")
    assert "definitely-not-a-real-token" in fake_refs
    # The defined set (real) must not contain our fake — proving it's truly
    # not defined anywhere, so if referenced it WOULD be flagged as undefined.
    assert "definitely-not-a-real-token" not in audit._css_vars_defined()


def test_inline_style_class_not_orphaned():
    """A class defined in inline <style> must NOT be reported orphaned."""
    defined = audit._all_defined_css_classes()
    # graph-card is styled in pathway.html's inline <style> — not an orphan.
    assert "graph-card" in defined, (
        "graph-card is defined in pathway.html's inline <style>; "
        "the scope fix should have made it a defined class"
    )


def test_post_route_detection_is_positive():
    """A genuinely-orphaned POST route must still be caught (positive control).

    The control is a SYNTHETIC route set the test owns — NOT a real production
    route. Tying the control to /api/chisel/revert-skill meant that route could
    never be deleted even if it should be, and the audit carried a permanent
    finding that meant nothing. Now: if a route with no reference isn't flagged,
    or a referenced route is wrongly flagged, the extraction has learned to look
    away and the discipline is broken.
    """
    # An orphaned route (no reference) MUST be caught.
    orphaned = audit._orphaned_post_routes(
        {"/api/fixture/orphaned"}, set()
    )
    assert "/api/fixture/orphaned" in orphaned, (
        "a synthetic route with no reference anywhere must be flagged orphaned"
    )
    # A referenced route MUST NOT be flagged (no false positive).
    clean = audit._orphaned_post_routes(
        {"/api/fixture/used"}, {"/api/fixture/used"}
    )
    assert "/api/fixture/used" not in clean, (
        "a referenced route must not be reported orphaned"
    )
    # A concrete-id reference resolves a <param> route (no false positive).
    resolved = audit._orphaned_post_routes(
        {"/api/inbox/<param>/split"},
        {"/api/inbox/agent_dead::__fleet__::2026-08-04T12:35:35/split"},
    )
    assert "/api/inbox/<param>/split" not in resolved, (
        "a concrete-id reference must resolve the <param> route"
    )
    # Sanity: direction4 still surfaces the real orphan set (revert-skill is now
    # a normal entry, not the control).
    orphaned_all = audit.direction4_orphaned_post_routes()
    assert isinstance(orphaned_all, list) and len(orphaned_all) > 0


def test_bare_api_anchor_detection_is_positive():
    """A bare <a href=/api/...> anchor must be caught (positive control).

    Direction 5 flags anchors that full-page-navigate to a token-protected
    /api/ route (they 401 — the header-auth navigation-failure class). A bare
    anchor with no hx-* and no fetch/htmx.ajax onclick MUST be flagged. If the
    classifier ever stops matching it, the direction has learned to look away.
    """
    # The two dead links we fixed are now onclick-driven, so they must NOT be
    # flagged (proves the exclusion works).
    bad = audit.direction5_bare_api_anchors()
    assert "/api/token-analytics" not in bad
    assert "/api/brain/hermes-agent" not in bad
    # Positive control: a bare anchor IS flagged; htmx/fetch-driven ones are not.
    assert audit._is_bare_api_anchor('<a class="act" href="/api/some-route">x</a>') is True
    assert audit._is_bare_api_anchor('<a href="/api/some-route" hx-get="/api/some-route">x</a>') is False
    assert audit._is_bare_api_anchor('<a href="/api/some-route" onclick="fetch(\'/api/some-route\')">x</a>') is False


def test_init_auth_is_idempotent():
    """init_auth() must be safe to call twice on the same app.

    Regression: init_auth() re-added middleware on every call, which Starlette
    forbids after the app has started. The test suite and the audit both call it
    over the shared process-global `app`, so under some orderings the second
    call raised "Cannot add middleware after an application has started" — and
    the audit's render pass silently fell back to static scan, reporting green
    while direction 5 never actually ran. Calling it twice must not raise.
    """
    from observeco.dashboard.auth import init_auth
    from observeco.dashboard.server import app
    # First call (may already be initialized by another test module — that's
    # the point: it must be safe regardless of prior state).
    init_auth(app)
    # Second call must NOT raise.
    init_auth(app)


def test_hardcoded_metric_literal_detection_is_positive():
    """A planted fake metric string MUST be caught (positive control).

    Direction 6 flags hardcoded comma-grouped numbers adjacent to a unit word
    ("tokens", "$", "%", "ms") inside rendered content — the "47,812 tokens
    saved" fabrication class. This direction's failure mode is silence, so the
    control must prove it fires on a fake and does NOT fire on legitimate
    variable-driven renders or non-metric literals.
    """
    # Positive: a planted fake metric MUST fire.
    fake = 'Cumulative fleet savings this week: 47,812 tokens saved'
    assert "47,812" in audit._metric_literals_in_text(fake), (
        "a hardcoded '47,812 tokens saved' must be flagged as a fabricated metric"
    )
    # The production source must no longer contain the real 47,812.
    server_src = (pathlib.Path(__file__).resolve().parent.parent
                  / "src" / "observeco" / "dashboard" / "server.py").read_text()
    assert "47,812" not in server_src, (
        "the fabricated 47,812 must be removed from the Brain auto-compression tab"
    )

    # Negative: a variable-driven render must NOT fire (brace is stripped).
    variable = "Cumulative savings this week: {cumulative:,} tokens saved"
    assert "cumulative" not in audit._metric_literals_in_text(variable)
    assert audit._metric_literals_in_text(variable) == [], (
        "an f-string expression {cumulative:,} is a variable, not a hardcoded literal"
    )

    # Negative: a non-metric literal (no unit word adjacency) must NOT fire.
    no_unit = "The report shows 47,812 entries in the table"
    assert audit._metric_literals_in_text(no_unit) == [], (
        "a comma-grouped number not adjacent to a unit word is not a rendered metric"
    )

    # Negative: ports / status codes / years must NOT fire.
    assert audit._metric_literals_in_text("listening on 9,120 ms") == []
    assert audit._metric_literals_in_text("HTTP 404, retrying") == []
    assert audit._metric_literals_in_text("in 2024, the fleet grew") == []

    # f-string semantics: a LITERAL inside an f-string must still fire (the
    # brace-strip removes {expr} but not literal digits); a variable {expr}
    # must not. This is the hole the reviewer flagged — 'skip any f-string'
    # would let fabrication hide exactly where it's likeliest.
    lit_in_fstring = 'f"fleet saved: 47,812 tokens this week"'
    assert "47,812" in audit._metric_literals_in_text(lit_in_fstring), (
        "a literal 47,812 inside an f-string must fire — the skip removes "
        "{expr}, not literal digits"
    )


def test_hardcoded_metric_literal_scan_covers_templates():
    """Direction 7 must scan .html templates, not just .py.

    A hardcoded metric in a Jinja template is the same defect as one in an
    f-string — arguably likelier, since that's where mockup content lands.
    If the scan only handled quoted Python strings, it would miss templates
    entirely (a template is not wrapped in quotes).
    """
    py = {p.name for p in audit._files(
        audit.ROOT / "src/observeco/dashboard", {".py"})}
    html = {p.name for p in audit._files(
        audit.ROOT / "src/observeco/dashboard/templates", {".html"})}
    assert "index_new.html" in html, "template scan path must include the main template"
    # The positive control must hold for a template-shaped body too.
    template_body = "<span>fleet savings: 47,812 tokens saved</span>"
    assert "47,812" in audit._metric_literals_in_text(template_body)
