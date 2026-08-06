"""Tests for the drift-data durability checks.

Covers the four structural guards that make the drift-misclassification bug
class impossible rather than detectable:
1. Refuse to start when code version < DB version (GS-019 hard fail).
2. Real SOUL.md headings match the classifier vocabulary (would have caught the
   original breakage the day the headings changed).
3. Fall-through fraction is recorded, not silent.
4. Zero-variance-across-population gate (constant columns are a detector that
   stopped measuring).

These are positive-control-style tests: each asserts the guard FIRES on the
condition it exists to catch.
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import tempfile

import pytest


# ── Test 1: refuse to start on code < DB version ────────────────────────────

def test_refuse_to_start_when_db_newer_than_code():
    """A DB schema newer than the code must refuse to start (GS-019 hard fail)."""
    from observeco.db import Database, SCHEMA_VERSION

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = Database(tmp.name)
    conn = db._get_conn()
    newer = SCHEMA_VERSION + 1
    conn.execute(
        "INSERT OR REPLACE INTO _meta (key, value) VALUES ('schema_version', ?)",
        (str(newer),),
    )
    conn.commit()
    db.close()

    # Opening must refuse when the version check runs. (Init is deferred to the
    # first _get_conn(); constructing Database() alone doesn't hit the check.)
    try:
        db2 = Database(tmp.name)
        db2._get_conn()  # triggers the deferred init + version guard
        pytest.fail("did not refuse to start with DB newer than code")
    except RuntimeError as e:
        assert "Refusing to start" in str(e)
        assert f"{newer}" in str(e) and f"{SCHEMA_VERSION}" in str(e)
    finally:
        os.unlink(tmp.name)


# ── Test 2: real SOUL.md headings match classifier vocabulary ───────────────

def test_real_soul_has_no_fully_unmatched_headings():
    """Every top-level (##) heading in the real Hermes SOUL.md must map to a
    component section. If headings drift from the vocabulary, classification
    silently degrades to all-guidance (the exact bug that killed drift for two
    weeks). This test would have failed the day the headings changed.
    """
    from observeco.chisel.trim import _load_sections, _classify_line

    sections = _load_sections()
    # Gather the vocabulary as one searchable corpus per section
    soul_path = os.path.expanduser("~/.hermes/profiles/main/SOUL.md")
    if not os.path.exists(soul_path):
        pytest.skip(f"real SOUL.md not present: {soul_path}")

    lines = pathlib.Path(soul_path).read_text(encoding="utf-8").splitlines()
    headings = [l.strip() for l in lines if l.startswith("## ")]
    assert headings, "expected ## headings in real SOUL.md"

    unmatched = [h for h in headings if _classify_line(h) == "guidance"]
    # Allow the top title line (# ...) and any intentional guidance-only headings;
    # but a heading that falls to guidance because of a vocabulary gap is a
    # regression. We assert every section-bearing heading has a non-guidance home.
    # Guidance-only headings are OK (rules/governance legitimately belong there),
    # so we only fail if a heading that should be a component maps to guidance.
    # Heuristic: headings containing protocol/dimension/contract keywords are
    # governance (guidance is fine); others must map to identity/skills/memory/tools.
    bad = [
        h for h in unmatched
        if not any(k in h.lower() for k in ("protocol", "dimension", "contract", "vision"))
    ]
    assert not bad, (
        f"real SOUL.md headings not classified into a component: {bad}. "
        "The classifier vocabulary has drifted from the headings — drift "
        "measurement is silently degrading."
    )


# ── Test 3: fall-through fraction is recorded ───────────────────────────────

def test_classifier_records_fall_through_fraction():
    """_analyse_prompt must record how much of the prompt fell through to the
    generic guidance bucket, so a total fall-through (classifier not matching
    the real structure) is observable rather than silent.
    """
    from observeco.chisel.trim import _analyse_prompt

    prompt = (
        "## Identity\nI am a test agent.\n"
        "## Skills\nI can run tools.\n"
        "## Memory\nI recall past sessions.\n"
        "## Tools\nI have a schema.\n"
        "## Guidance\nFollow these rules.\n"
    )
    res = _analyse_prompt(prompt)
    # The breakdown must attribute content to real sections, not dump all to guidance.
    assert res["breakdown"]["guidance"]["chars"] < len(prompt) * 0.5, (
        "more than half the prompt fell through to guidance — classification "
        "is not matching the structure"
    )
    # identity/skills must have non-placeholder content
    assert res["identity_tokens"] > 1, "identity got a placeholder value"
    # fallthrough_ratio must be present (the recorder exists)
    assert "fallthrough_ratio" in res, "fallthrough_ratio not recorded"
    assert 0.0 <= res["fallthrough_ratio"] <= 1.0
    # A completely unstructured prompt (all falls to guidance) must report ~1.0
    garbage = _analyse_prompt("totally unstructured text with no sections at all")
    assert garbage["fallthrough_ratio"] > 0.9, (
        "an unstructured prompt should show near-total fall-through"
    )


# ── Test 4: zero-variance gate ──────────────────────────────────────────────

def test_zero_variance_gate_flags_constant_columns(tmp_path):
    """zero_variance_metrics must flag a *_tokens column constant across the
    population (the 'stopped measuring' signature)."""
    from observeco.chisel.trim import zero_variance_metrics

    db_path = tmp_path / "zv.db"
    from observeco.db import Database
    db = Database(str(db_path))
    conn = db._get_conn()
    # Seed 4 agents, all with identity_tokens=1 (constant) but differing skills_tokens
    now = 1_700_000_000
    for i, a in enumerate(("a", "b", "c", "d")):
        conn.execute(
            "INSERT INTO chisel_trims (agent_name, identity_tokens, skills_tokens, "
            "memory_tokens, tools_tokens, guidance_tokens, total_tokens, savings_ratio, "
            "timestamp, mode) VALUES (?,1,?,1,1,1,1,0,?,'x')",
            (a, 100 + i * 10, now),
        )
    conn.commit()
    suspicious = zero_variance_metrics(db, window_seconds=99999999)
    assert "identity_tokens" in suspicious, "constant column not flagged"
    assert "skills_tokens" not in suspicious, "varying column wrongly flagged"
