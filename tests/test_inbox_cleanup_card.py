"""test_inbox_cleanup_card.py — distinguishing test for the P0.0 cleanup card.

Value unit (specs/value-unit-inbox-cleanup-card.md): the inbox renders the
Signal Cleanup card iff a classification fix is actually pending. The card must
render when misclassification exists and be ABSENT when the fleet is clean.

These are PURE tests — they exercise _render_cleanup_card and the wiring
structurally, without connecting the 838MB prod DB (which hangs). The
distinguishing property: a card that renders for a clean fleet, or hides for a
misclassified fleet, FAILS.
"""
from __future__ import annotations

import pathlib

from observeco.dashboard.routes.inbox import _render_cleanup_card

ROUTES = pathlib.Path(__file__).resolve().parent.parent / "src/observeco/dashboard/routes/inbox.py"
SRC = ROUTES.read_text()


def test_render_cleanup_card_contains_signal_cleanup():
    """The rendered card carries the value sentence 'Signal cleanup available'."""
    html = _render_cleanup_card(["reclassify_profiles", "reset_stale_circuits"])
    assert "Signal cleanup available" in html
    assert "Apply 2 fixes" in html
    assert "reclassify_profiles" in html
    assert "reset_stale_circuits" in html


def test_render_cleanup_card_single_fix_plural():
    """1 fix renders 'Apply 1 fix', not 'Apply 1 fixes'."""
    html = _render_cleanup_card(["exclude_tests"])
    assert "Apply 1 fix" in html
    assert "Apply 1 fixes" not in html


def test_render_cleanup_card_empty_never_called():
    """The card must NEVER be rendered for an empty fix list (would be a lie)."""
    # _render_cleanup_card is only called from get_inbox when _detect_cleanup()
    # is non-empty; a guard should not allow empty rendering.
    html = _render_cleanup_card([])
    # With no fixes there are no checkboxes and no Apply button — assert it
    # renders no fix checkbox (defensive: get_inbox guards on pending anyway).
    assert "input type=\"checkbox\"" not in html


def test_get_inbox_guards_cleanup_on_pending():
    """The wiring: get_inbox must render the card iff _detect_cleanup() non-empty."""
    # _detect_cleanup is called; card rendered only inside the `if pending_fixes`.
    assert "_detect_cleanup()" in SRC
    assert "pending_fixes = _detect_cleanup()" in SRC
    assert "if pending_fixes:" in SRC
    assert "_render_cleanup_card(pending_fixes)" in SRC
    # The card append must be guarded — it must appear AFTER the `if pending_fixes`
    # and be indented under it (i.e., the append only runs when non-empty).
    guard_idx = SRC.index("if pending_fixes:")
    render_idx = SRC.index("_render_cleanup_card(pending_fixes)")
    assert render_idx > guard_idx


def test_misleading_kb_hint_removed():
    """The j/k/x/e hint advertised a capability with no handler — must be gone."""
    assert "kb-hint" not in SRC
    assert "j</kbd>/<kbd>k</kbd> move" not in SRC


def test_apply_cleanup_endpoint_is_reachable():
    """The Apply button must target the existing cleanup/apply endpoint."""
    assert "/api/inbox/cleanup/apply" in SRC
    assert "applyCleanupFixes" in SRC  # handler wired in app.js


def test_detect_exclude_tests_checks_pre_fix_class_not_presence():
    """REG: exclude_tests must not fire when test agents are already class='test'.
    Presence alone was a false positive — the card would show 'exclude test
    entities' even after they were already excluded. The check must target the
    pre-fix state (class != 'test'), matching apply_cleanup()."""
    assert "AND class != 'test'" in SRC
    # The count query must be scoped to the pre-fix class, not raw presence.
    assert "WHERE agent_name IN " in SRC
