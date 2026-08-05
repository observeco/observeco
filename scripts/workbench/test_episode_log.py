"""Tests for the EpisodeLog schema — the harness branch's correctness gate.

Guards the three corrections:
1. Episodes are BLOCKS, not sessions — one session can yield multiple episodes
   with different classifications (the entity-binding fix from containment-identity).
2. Three-valued classification — `unclassified` is a legal state, not forced
   into the binary; and it is NOT proposable by default.
3. guardrail_correct is STRUCTURALLY non-citable — the fairness gate rejects
   any proposal citing it, so it's a mechanism, not a convention.

Also: the .env case is guardrail_correct (intent is unverifiable in-loop),
NOT collateral — the one misclassification that would poison the corpus.
"""
import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).parent / "episode_log.py"


def _load():
    spec = importlib.util.spec_from_file_location("episode_log", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def test_episodes_keyed_to_blocks_not_sessions():
    """One session (20260706_083828) yields TWO episodes with different types.
    Keying on (session_id, block_event) must allow that."""
    eps = mod.seed_from_sample()
    env = eps["20260706_083828:.env"]
    gw = eps["20260706_083828:gateway"]
    assert env["session_id"] == gw["session_id"]
    assert env["type"] == "guardrail_correct"
    assert gw["type"] == "guardrail_correct"
    assert env["block_event"] != gw["block_event"]


def test_env_access_is_guardrail_correct_not_collateral():
    """The .env credential read is CORRECT (rail doing its job), not collateral.
    Intent being benign is not the test — intent is unverifiable in-loop. The
    citable flag must be False so a future proposer cannot cite 'agent blocked
    from reading credentials'."""
    env = mod.seed_from_sample()["20260706_083828:.env"]
    assert env["type"] == "guardrail_correct"
    assert env["citable"] is False
    assert "credential" in (env["note"] or "").lower()


def test_three_valued_classification_has_unclassified():
    """unclassified is a legal third state; ambiguous cases are not forced into
    collateral. 20260725_080927 is unclassified and NOT citable by default."""
    eps = mod.seed_from_sample()
    amb = eps["20260725_080927:shutdown"]
    assert amb["type"] == "unclassified"
    assert amb["citable"] is False


def test_guardrail_correct_structurally_uncitable():
    """The fairness gate must reject any proposal citing a guardrail_correct
    episode — a mechanism, not a label. assert_citable raises."""
    eps = mod.seed_from_sample()
    import pytest
    with pytest.raises(ValueError):
        mod.assert_citable(["20260706_083828:.env"], eps)
    # and it allows a genuinely citable episode
    mod.assert_citable(["20260711_104552:patch_anchor"], eps)  # no raise


def test_capability_cluster_keyed_by_mechanism():
    """capability episodes carry a mechanism so clustering is honest —
    patch_anchor across 3 sessions is the strong cluster, not the misc."""
    eps = mod.seed_from_sample()
    anchors = [e for e in eps.values() if e.get("mechanism") == "patch_anchor"]
    assert len(anchors) >= 2, "patch_anchor must be a cross-session cluster"
    for a in anchors:
        assert a["citable"] is True
