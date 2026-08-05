"""EpisodeLog schema — Workbench harness branch.

Keyed on (session_id, block_event): episodes are BLOCKS, not sessions. One
session can produce several episodes with different classifications. This
avoids the entity-binding failure (right data, wrong subject) that produced
the containment-identity bug.

Three-valued classification — `unclassified` is a legal state, never forced
into the binary (forcing ambiguity into a binary is how a taxonomy acquires
false positives, and here they'd all point toward proposable).

guardrail_correct is STRUCTURALLY non-citable: the fairness gate refuses any
proposal citing it. Not a label the proposer could ignore — a field the gate
enforces (promote-to-gate).

Episode types:
- guardrail_collateral  : legit goal, rail fired on technicality. PROPOSABLE.
                          Fix = sanctioned path to the legit goal (affordance),
                          NOT rail-loosening. E.g. redacted config-key lookup.
- guardrail_correct     : rail did its job (intent is unverifiable in-loop).
                          NON-CITABLE. Includes: any credential-store access,
                          destructive commands (shutdown, removal), self-restart.
                          NOTE: intent being benign is not the test.
- capability_<mechanism>: real capability failure, keyed by mechanism so
                          clustering is honest (patch-anchor / search-query /
                          filesystem-locate / state-observation).
- unclassified          : cannot determine from trajectory. Legal, proposable
                          only after reclassification (never by default).

Provenance (from the failure flag): flagged-by-Sean (ground truth) vs
inferred-by-heuristic (quarantined as weak evidence). Fairness gate weights
flagged above inferred.

The field the fairness gate enforces: citable ∈ {false} for guardrail_correct
and for any unclassified episode. Everything else is a label; this is the gate.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

STATE_DB = Path.home() / ".hermes" / "state.db"


def now_iso() -> str:
    return datetime.now().isoformat()


def _episode(session_id, block_event, etype, mechanism=None, goal=None, citable=None,
             provenance=None, note=None):
    """Build an episode record. citable defaults by type."""
    if citable is None:
        citable = etype in ("guardrail_collateral",) or etype.startswith("capability_")
    return {
        "session_id": session_id,
        "block_event": block_event,
        "type": etype,
        "mechanism": mechanism,
        "goal": goal,
        "citable": citable,
        "provenance": provenance,
        "note": note,
        "created": now_iso(),
    }


def guardrail_correct(session_id, block_event, goal, note=""):
    """Rail did its job — NEVER citable, structurally enforced."""
    return _episode(session_id, block_event, "guardrail_correct", goal=goal,
                    citable=False, note=note)


def guardrail_collateral(session_id, block_event, goal, affordance, note=""):
    """Legit goal, rail fired on technicality. Proposable. Fix is the affordance."""
    return _episode(session_id, block_event, "guardrail_collateral", goal=goal,
                    citable=True, note=f"{note} | sanctioned path: {affordance}")


def capability(session_id, block_event, mechanism, goal, note=""):
    """Real capability failure keyed by mechanism. Proposable."""
    return _episode(session_id, block_event, f"capability_{mechanism}",
                    mechanism=mechanism, goal=goal, citable=True, note=note)


def unclassified(session_id, block_event, goal, note=""):
    """Cannot determine from trajectory. NOT proposable by default."""
    return _episode(session_id, block_event, "unclassified", goal=goal,
                    citable=False, note=note)


# --- Fairness gate enforcement (the promote-to-gate mechanism) ---
def assert_citable(proposal_episode_ids, episodes):
    """Reject any proposal that cites a non-citable episode. This is the gate,
    not a label: the proposer cannot cite guardrail_correct or unclassified."""
    for eid in proposal_episode_ids:
        ep = episodes.get(eid)
        if ep and not ep["citable"]:
            raise ValueError(
                f"proposal cites non-citable episode {eid} "
                f"(type={ep['type']}) — guardrail_correct and unclassified are structurally uncitable"
            )


# --- Hand-classified seed episodes from the 20-session sample (blocks, not sessions) ---
def seed_from_sample() -> dict[str, dict]:
    """Hand-classified episodes from the partition. Keyed by (session_id, block_event)."""
    eps = {}
    # 20260706_083828 produced TWO blocks (one session, two episodes)
    eps["20260706_083828:.env"] = guardrail_correct(
        "20260706_083828_c249707d", ".env read",
        "read credential store to diagnose provider issue",
        note="intent benign but unverifiable in-loop; credential access is what the rail exists for. "
             "Affordance: config-key lookup returning key presence + non-secret values.")
    eps["20260706_083828:gateway"] = guardrail_correct(
        "20260706_083828_c249707d", "gateway self-restart",
        "restart gateway to verify fix", note="self-restart is genuinely unsafe")
    # 20260726_101312 cronjob remove — correct
    eps["20260726_101312:cronjob_remove"] = guardrail_correct(
        "20260726_101312_d9497338", "cronjob remove",
        "remove 5 duplicate cron jobs", note="removal is destructive; legit goal lacks sanctioned path")
    # 20260803_114117 output-artifact write — collateral (needs sanctioned write affordance)
    eps["20260803_114117:write_artifact"] = guardrail_collateral(
        "20260803_114117_c89d1fd2", "write output artifact",
        "write delivery/persistence artifact for RSS script", "sanctioned artifact-write path")
    # 20260801_095610 outbox write — collateral
    eps["20260801_095610:outbox"] = guardrail_collateral(
        "20260801_095610_f31d974b", "write outbox artifact",
        "write outbox artifact as part of fix", "sanctioned outbox-write path")
    # capability — patch-anchor (strong cross-session cluster)
    eps["20260711_104552:patch_anchor"] = capability(
        "20260711_104552_ba097abe", "old_string not unique", "patch_anchor",
        "apply patch; old_string matched 2/8 places")
    eps["20260710_172156:patch_anchor"] = capability(
        "20260710_172156_b23c24", "old_string not found", "patch_anchor",
        "apply patch; old_string not found")
    # 20260725_080927 — ambiguous, unclassified
    eps["20260725_080927:shutdown"] = unclassified(
        "20260725_080927_c087f0d0", "shutdown block",
        "check gateway restart/drain at 03:00", note="cannot tell from trajectory if ran shutdown or inspected logs")
    return eps
