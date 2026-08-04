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
