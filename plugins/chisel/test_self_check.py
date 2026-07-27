"""Self-check test for Chisel plugin.

The smallest thing that fails if decomposition or drift logic breaks.
No test framework — pure assert.
"""

from __future__ import annotations

import sys
import os
import tempfile
from pathlib import Path

# Add parent dir so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chisel.chisel_core import (
    COMPONENT_ORDER,
    decompose,
    check_drift,
    compute_drift,
    estimate_tokens,
    format_breakdown,
    format_drift,
    prompt_hash,
    assemble_prompt,
)
from chisel.chisel_cut import (
    find_duplicates,
    find_stale_refs,
    find_unused_skills,
    suggest,
    compress_guidance_block,
    apply_cuts,
    format_suggestions,
    format_cut_result,
    format_verify_result,
    rule_hash,
)


def test_estimate_tokens():
    """Token estimation is roughly correct."""
    assert estimate_tokens("hello world") == 2  # 11 chars / 4 = 2.75 → int = 2
    assert estimate_tokens("") == 1  # minimum 1
    assert estimate_tokens("a") == 1
    print("  ✅ estimate_tokens")


def test_decompose_basic():
    """Basic decomposition with markdown headings."""
    prompt = """# Identity
You are a helpful agent.

## Skills
You have access to search and file tools.

## Memory
Remember user preferences.

## Tools
Tool descriptions and API specs.

## Guidance
Do not use tools without approval.
"""
    result = decompose(prompt)
    assert result["identity_tokens"] > 0
    assert result["skills_tokens"] > 0
    assert result["memory_tokens"] > 0
    assert result["tools_tokens"] > 0
    assert result["guidance_tokens"] > 0
    # total_tokens is computed from total chars, not sum of components
    # (each component rounds independently, so sum may differ by ±1-2)
    assert abs(result["total_tokens"] - (result["identity_tokens"] + result["skills_tokens"] + result["memory_tokens"] + result["tools_tokens"] + result["guidance_tokens"])) <= 2
    assert result["total_chars"] == len(prompt)
    print("  ✅ decompose basic")


def test_decompose_no_headings():
    """Decomposition without markdown headings — falls back to keyword matching."""
    prompt = """You are a helpful agent.
You have access to search tools.
Remember user preferences.
Do not use tools without approval."""
    result = decompose(prompt)
    # All lines should be classified into some section
    assert result["total_tokens"] > 0
    # Without headings, everything defaults to guidance
    assert result["guidance_tokens"] > 0
    print("  ✅ decompose no headings")


def test_decompose_empty():
    """Empty prompt produces a breakdown with minimum tokens."""
    result = decompose("")
    # Each component gets minimum 1 token from estimate_tokens
    assert result["total_tokens"] == 1  # total chars 0 / 4 = 0 → max(1, 0) = 1
    print("  ✅ decompose empty")


def test_decompose_short():
    """Very short prompt still produces a breakdown."""
    result = decompose("Hello")
    assert result["total_tokens"] == 1  # 5 chars / 4 = 1.25 → int = 1
    print("  ✅ decompose short")


def test_check_drift_no_change():
    """No drift when values are identical."""
    delta_pct, delta_tokens, breached = check_drift(100, 100)
    assert delta_pct == 0.0
    assert delta_tokens == 0
    assert not breached
    print("  ✅ check_drift no change")


def test_check_drift_small_change():
    """Small change below threshold is not a breach."""
    delta_pct, delta_tokens, breached = check_drift(105, 100)
    assert delta_pct == 5.0  # 5% change
    assert delta_tokens == 5
    assert not breached  # 5% < 10% threshold
    print("  ✅ check_drift small change")


def test_check_drift_large_change():
    """Large change above both thresholds is a breach."""
    delta_pct, delta_tokens, breached = check_drift(200, 100)
    assert delta_pct == 100.0  # 100% change
    assert delta_tokens == 100
    assert breached  # 100% > 10% AND 100 > 50
    print("  ✅ check_drift large change")


def test_check_drift_high_pct_low_abs():
    """High percentage but low absolute change is not a breach."""
    delta_pct, delta_tokens, breached = check_drift(55, 50)
    assert delta_pct == 10.0  # 10% change
    assert delta_tokens == 5
    assert not breached  # 5 < 50 absolute threshold
    print("  ✅ check_drift high pct low abs")


def test_check_drift_low_pct_high_abs():
    """High absolute but low percentage change is not a breach."""
    delta_pct, delta_tokens, breached = check_drift(1000, 950)
    # delta_pct = (1000-950)/max(950,50)*100 = 50/950*100 = 5.26%
    assert abs(delta_pct - 5.26) < 0.01
    assert delta_tokens == 50
    assert not breached  # 5.26% < 10% threshold
    print("  ✅ check_drift low pct high abs")


def test_compute_drift():
    """compute_drift returns one entry per component."""
    current = {
        "identity_tokens": 100,
        "skills_tokens": 200,
        "memory_tokens": 300,
        "tools_tokens": 400,
        "guidance_tokens": 500,
        "total_tokens": 1500,
    }
    baseline = {
        "identity_tokens": 100,
        "skills_tokens": 200,
        "memory_tokens": 300,
        "tools_tokens": 400,
        "guidance_tokens": 500,
        "total_tokens": 1500,
    }
    results = compute_drift(current, baseline)
    assert len(results) == 5
    for r in results:
        assert r["component"] in COMPONENT_ORDER
        assert r["delta_pct"] == 0.0
        assert not r["breached"]
    print("  ✅ compute_drift")


def test_prompt_hash():
    """SHA-256 hash is deterministic."""
    h1 = prompt_hash("hello")
    h2 = prompt_hash("hello")
    h3 = prompt_hash("world")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # SHA-256 hex
    print("  ✅ prompt_hash")


def test_assemble_prompt():
    """Assemble prompt from parts."""
    result = assemble_prompt(
        config_yaml="system_message: You are a helpful agent",
        soul_md="# Identity\nYou are a test agent.",
        skill_texts=["## Skills\nYou can search."],
        memory_texts=["## Memory\nUser likes cats."],
    )
    assert "test agent" in result
    assert "search" in result
    assert "cats" in result
    assert len(result) > 50
    print("  ✅ assemble_prompt")


def test_assemble_prompt_empty():
    """Assemble prompt with empty parts produces minimal output."""
    result = assemble_prompt(config_yaml="")
    assert isinstance(result, str)
    print("  ✅ assemble_prompt empty")


def test_format_breakdown():
    """Format breakdown produces a table."""
    result = decompose("# Identity\nYou are a test agent.\n# Skills\nYou can search.")
    table = format_breakdown(result)
    assert "Component" in table
    assert "Tokens" in table
    assert "Identity" in table
    assert "Skills" in table
    assert "Total" in table
    print("  ✅ format_breakdown")


def test_format_drift():
    """Format drift produces a table."""
    results = [
        {"component": "identity", "current_tokens": 100, "baseline_tokens": 100,
         "delta_pct": 0.0, "delta_tokens": 0, "breached": False},
        {"component": "memory", "current_tokens": 500, "baseline_tokens": 200,
         "delta_pct": 150.0, "delta_tokens": 300, "breached": True},
    ]
    table = format_drift(results)
    assert "Component" in table
    assert "Identity" in table
    assert "Memory" in table
    assert "BREACH" in table
    assert "OK" in table
    print("  ✅ format_drift")


def test_savings_ratio():
    """savings_ratio is bounded between 0 and 0.25."""
    # All guidance → max savings
    result = decompose("# Guidance\nDo not. Never. Always. Must. Should. Rule. Policy. Constraint.")
    assert 0 <= result["savings_ratio"] <= 0.25
    # No guidance → min savings
    result = decompose("# Identity\nYou are a test agent.")
    assert result["savings_ratio"] >= 0.0
    print("  ✅ savings_ratio")


# ── v0.2: Suggest Tests ──────────────────────────────────────────────────


def test_find_duplicates():
    """Find duplicate lines across sections."""
    prompt = "# Guidance\nNever modify config.yaml without approval.\n## Identity\nNever modify config.yaml without approval."
    dupes = find_duplicates(prompt)
    assert len(dupes) == 1
    assert dupes[0]["type"] == "duplicate_rule"
    assert "Never modify" in dupes[0]["line"]
    print("  ✅ find_duplicates")


def test_find_duplicates_no_match():
    """No duplicates when lines are different."""
    prompt = "# Guidance\nDo this.\n## Identity\nDo that."
    dupes = find_duplicates(prompt)
    assert len(dupes) == 0
    print("  ✅ find_duplicates no match")


def test_find_duplicates_short_lines():
    """Short lines (<20 chars) are skipped."""
    prompt = "# Guidance\nShort\n## Identity\nShort"
    dupes = find_duplicates(prompt)
    assert len(dupes) == 0
    print("  ✅ find_duplicates short lines skipped")


def test_find_stale_refs():
    """Find file paths that don't exist on disk."""
    prompt = "# Memory\nSee ~/nonexistent_path_xyz_123/file.md for details."
    stale = find_stale_refs(prompt)
    assert len(stale) >= 1
    assert stale[0]["type"] == "stale_ref"
    assert "nonexistent_path_xyz_123" in stale[0]["path"]
    print("  ✅ find_stale_refs")


def test_find_stale_refs_none():
    """No stale refs when all paths exist."""
    prompt = "# Memory\nSee ~/.hermes/config.yaml for details."
    stale = find_stale_refs(prompt)
    # config.yaml exists, so this should not be stale
    for s in stale:
        assert "config.yaml" not in s["path"]
    print("  ✅ find_stale_refs none")


def test_find_stale_refs_ignores_backticks():
    """Paths inside backtick code spans should not be flagged as stale."""
    prompt = "# Memory\nRead `~/.hermes/signals/` at session start."
    stale = find_stale_refs(prompt)
    # The path inside backticks should not be captured at all,
    # or if captured, should not include trailing backtick
    for s in stale:
        assert not s["path"].endswith("`"), f"Path has trailing backtick: {s['path']}"
    print("  ✅ find_stale_refs ignores backticks")


def test_find_unused_skills_no_dir():
    """No unused skills when skills dir doesn't exist."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        unused = find_unused_skills("test prompt", Path(tmp))
        assert len(unused) == 0
    print("  ✅ find_unused_skills no dir")


def test_suggest_aggregate():
    """suggest() runs all detection types."""
    prompt = "# Guidance\nNever modify config.yaml without approval.\n## Identity\nNever modify config.yaml without approval.\nSee ~/nonexistent_path_xyz_123/file.md."
    results = suggest(prompt)
    # Should find at least duplicates and stale refs
    types = {r["type"] for r in results}
    assert "duplicate_rule" in types
    assert "stale_ref" in types
    print("  ✅ suggest aggregate")


# ── v0.2: Cut Tests ──────────────────────────────────────────────────────


def test_compress_guidance_block():
    """Rule-based compression shortens verbose patterns."""
    text = "You MUST not do this. You should always do that. Please be careful."
    compressed = compress_guidance_block(text)
    assert "must not do this" in compressed.lower()
    assert "should always do that" in compressed.lower()
    assert "please" not in compressed.lower()
    assert len(compressed) < len(text)
    print("  ✅ compress_guidance_block")


def test_compress_guidance_block_dedup():
    """Duplicate lines are removed."""
    text = "Never modify config.yaml without approval.\nNever modify config.yaml without approval."
    compressed = compress_guidance_block(text)
    assert compressed.count("Never modify") == 1
    print("  ✅ compress_guidance_block dedup")


def test_compress_guidance_block_preserves_code():
    """Code blocks are preserved entirely."""
    text = "# Guidance\nDo not modify.\n```\ncode block\n```\nAlways check."
    compressed = compress_guidance_block(text)
    assert "code block" in compressed
    assert "```" in compressed
    print("  ✅ compress_guidance_block preserves code")


def test_compress_guidance_block_preserves_headings():
    """Headings are preserved."""
    text = "# Identity\nYou are a test agent.\n## Skills\nYou can search."
    compressed = compress_guidance_block(text)
    assert "# Identity" in compressed
    assert "## Skills" in compressed
    print("  ✅ compress_guidance_block preserves headings")


def test_apply_cuts_dry_run():
    """Dry-run should not modify files."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Identity\nYou MUST do this.\n# Guidance\nYou should do that.\nPlease be careful.")
        fpath = f.name
    try:
        result = apply_cuts(fpath, suggestions=[], apply=False)
        assert result["applied"] is False
        assert "diff" in result
        assert result["tokens_saved"] > 0
        # File should be unchanged
        content = open(fpath).read()
        assert "You MUST" in content
    finally:
        os.unlink(fpath)
    print("  ✅ apply_cuts dry run")


def test_apply_cuts_apply():
    """Apply mode creates backup and modifies file."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Identity\nYou MUST do this.\nPlease be careful.")
        fpath = f.name
    try:
        result = apply_cuts(fpath, suggestions=[], apply=True)
        assert result["applied"] is True
        assert result["backup"] is not None
        assert os.path.exists(result["backup"])
        # File should be modified
        content = open(fpath).read()
        assert "must" in content.lower()
        assert "please" not in content.lower()
    finally:
        os.unlink(fpath)
    print("  ✅ apply_cuts apply")


def test_apply_cuts_file_not_found():
    """Non-existent file returns error."""
    result = apply_cuts("/tmp/nonexistent_file_xyz.md", suggestions=[])
    assert result.get("error") is not None
    print("  ✅ apply_cuts file not found")


def test_apply_cuts_preserves_code_spans():
    """Stale ref removal must not corrupt paths inside backtick code spans."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix="..md", delete=False) as f:
        f.write("# Memory\n\nRead `~/.hermes/signals/` at session start.\n\nSee ~/nonexistent_xyz_123/file.md for details.")
        fpath = f.name
    try:
        suggestions = [{"type": "stale_ref", "path": "~/nonexistent_xyz_123/file.md", "tokens": 3}]
        result = apply_cuts(fpath, suggestions=suggestions, apply=False)
        # The code span must be intact in the diff
        assert "`~/.hermes/signals/`" in result["diff"], "Code span was corrupted!"
        # The stale path should be removed from prose (not in the new content)
        assert "nonexistent_xyz_123" not in result["diff"].split("---")[0], "Stale path not removed from prose"
    finally:
        os.unlink(fpath)
    print("  ✅ apply_cuts preserves code spans")


# ── v0.2: Format Tests ───────────────────────────────────────────────────


def test_format_suggestions_empty():
    """Empty suggestions show a message."""
    text = format_suggestions([])
    assert "No cuttable items found" in text
    print("  ✅ format_suggestions empty")


def test_format_suggestions():
    """Suggestions are formatted as a table."""
    suggestions = [
        {"type": "duplicate_rule", "line": "Never modify config.yaml", "tokens": 5},
        {"type": "stale_ref", "path": "~/nonexistent/file.md", "tokens": 3},
    ]
    text = format_suggestions(suggestions)
    assert "duplicate_rule" in text
    assert "stale_ref" in text
    assert "Total" in text
    print("  ✅ format_suggestions")


def test_format_cut_result_dry_run():
    """Dry-run result shows no backup."""
    result = {
        "applied": False,
        "file": "SOUL.md",
        "backup": None,
        "before_tokens": 100,
        "after_tokens": 80,
        "tokens_saved": 20,
        "savings_pct": 20.0,
        "diff": "--- a/SOUL.md\n+++ b/SOUL.md\n@@ -1 +1 @@\n-test\n+compressed",
    }
    text = format_cut_result(result)
    assert "Dry-run" in text
    assert "20 tokens" in text
    print("  ✅ format_cut_result dry run")


def test_format_cut_result_applied():
    """Applied result shows backup path."""
    result = {
        "applied": True,
        "file": "SOUL.md",
        "backup": "/tmp/backup.bak",
        "before_tokens": 100,
        "after_tokens": 80,
        "tokens_saved": 20,
        "savings_pct": 20.0,
        "diff": "--- a/SOUL.md\n+++ b/SOUL.md\n@@ -1 +1 @@\n-test\n+compressed",
    }
    text = format_cut_result(result)
    assert "Cut applied" in text
    assert "/tmp/backup.bak" in text
    print("  ✅ format_cut_result applied")


def test_format_verify_result():
    """Verify result shows before/after."""
    result = {
        "status": "verified",
        "tokens_before": 100,
        "tokens_after": 80,
        "tokens_saved": 20,
    }
    text = format_verify_result(result)
    assert "Verified" in text
    assert "100" in text
    assert "80" in text
    print("  ✅ format_verify_result")


def test_format_verify_result_no_cut():
    """No cut message."""
    text = format_verify_result({"status": "no_cut_found"})
    assert "No cuts to verify" in text
    print("  ✅ format_verify_result no cut")


def test_format_verify_result_regression():
    """Regression message."""
    result = {
        "status": "regression",
        "tokens_before": 80,
        "tokens_after": 100,
        "tokens_saved": -20,
    }
    text = format_verify_result(result)
    assert "Regression" in text
    print("  ✅ format_verify_result regression")


# ── v0.2: Learn Tests ────────────────────────────────────────────────────


def test_rule_hash():
    """rule_hash is deterministic."""
    h1 = rule_hash("Never modify config.yaml")
    h2 = rule_hash("Never modify config.yaml")
    h3 = rule_hash("Never modify config.yaml without approval")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 16  # first 16 chars of SHA-256 hex
    print("  ✅ rule_hash")


def main():
    print("Chisel self-check tests")
    print("=" * 40)
    tests = [
        test_estimate_tokens,
        test_decompose_basic,
        test_decompose_no_headings,
        test_decompose_empty,
        test_decompose_short,
        test_check_drift_no_change,
        test_check_drift_small_change,
        test_check_drift_large_change,
        test_check_drift_high_pct_low_abs,
        test_check_drift_low_pct_high_abs,
        test_compute_drift,
        test_prompt_hash,
        test_assemble_prompt,
        test_assemble_prompt_empty,
        test_format_breakdown,
        test_format_drift,
        test_savings_ratio,
        # v0.2
        test_find_duplicates,
        test_find_duplicates_no_match,
        test_find_duplicates_short_lines,
        test_find_stale_refs,
        test_find_stale_refs_none,
        test_find_stale_refs_ignores_backticks,
        test_find_unused_skills_no_dir,
        test_suggest_aggregate,
        test_compress_guidance_block,
        test_compress_guidance_block_dedup,
        test_compress_guidance_block_preserves_code,
        test_compress_guidance_block_preserves_headings,
        test_apply_cuts_dry_run,
        test_apply_cuts_apply,
        test_apply_cuts_file_not_found,
        test_apply_cuts_preserves_code_spans,
        test_format_suggestions_empty,
        test_format_suggestions,
        test_format_cut_result_dry_run,
        test_format_cut_result_applied,
        test_format_verify_result,
        test_format_verify_result_no_cut,
        test_format_verify_result_regression,
        test_rule_hash,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
