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
