"""Build a CORROBORATION PACKAGE for a case — everything needed to audit a score.

Sean's requirement: "for the exact tests you wish me to perform blind, you should show me
your score, confidence and reasons for scoring, in order for me to corroborate."

WHY THIS FILE EXISTS. Jev is a LABELLER, not a reasoner. The API returns exactly:
    {type, score, legend, probabilities, confidence}   (~17 output tokens)
There is NO free-text field and no reasoning channel. So a "reason for scoring" cannot be
obtained from the model.

This package therefore separates three things and never blends them:

  1. WHAT JEV SAID       -- the number, distribution, interval, coverage. Verbatim.
  2. WHAT THE NUMBER MEANS -- the rubric level carrying the most mass, quoted verbatim.
                              A structural fact about the distribution, not a narrative.
  3. WHAT IT SAW         -- the evidence actually present in the state: the owner's claims,
                              the derived competitive set, and the owner-vs-derived delta.
  4. REASON PROVENANCE   -- an explicit statement of what is measured vs inferred vs unknowable.

Anything resembling a narrative is marked DERIVED and is never presented as the model's own
explanation. Where a cause cannot be established, the package says "not established" rather
than inventing one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

DISPLAY = {
    "market_headroom": "Market headroom",
    "competitive_room": "Competitive room",
    "mental_advantage": "Mental advantage",
    "position_availability": "Position availability (RETIRED)",
    "defensibility": "Defensibility",
    "demand_reach": "Demand reach",
}


def load(case: str) -> tuple[dict, dict]:
    """Return (input payload, run artifact). Raises if either is missing."""
    run = HERE / "runs" / f"jev-{case}.json"
    if not run.exists():
        raise SystemExit(f"no run artifact: {run}")
    r = json.loads(run.read_text())
    # find the input whose _meta.case matches
    for p in sorted((HERE / "inputs").glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        if (d.get("_meta") or {}).get("case") == case:
            return d, r
    raise SystemExit(f"no input file with _meta.case == {case}")


def top_level(dist: dict, legend: dict) -> tuple[str, str, float]:
    """The level carrying the most mass — the score's centre of gravity."""
    if not dist:
        return "", "", 0.0
    k = max(dist, key=lambda x: dist[x])
    return k, legend.get(k, ""), dist[k]


def evidence_trail(payload: dict) -> dict:
    form = payload.get("form") or {}
    derived = payload.get("derived_competitive_set") or {}
    tiers = {}
    for k, v in derived.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        members = v.get("members") or []
        tiers[k] = {
            "members": members,
            "why": v.get("why", ""),
            "price_floor": v.get("price_floor"),
        }
    named = payload.get("competitors_named") or []
    t2 = tiers.get("tier_2_direct_set", {}).get("members") or []
    t3 = tiers.get("tier_3_category_incumbent", {}).get("members") or []
    return {
        "owner_claims": {
            "positioning_sentence": form.get("positioning_sentence"),
            "differentiator": form.get("differentiator"),
            "undercut_on": form.get("undercut_on"),
        },
        "owner_named_competitors": named,
        "derived_tiers": tiers,
        "blindspot": {
            "owner_named_count": len(named),
            "derived_direct_set_count": len(t2),
            "tier_3_incumbent": t3,
            "note": ("The owner's list is a BLINDSPOT PROBE, not input data. The gap between "
                     "what they named and what was derived is the report's first finding."),
        },
    }


def build(case: str) -> str:
    payload, r = load(case)
    dims = r.get("dimensions_display_1to5") or {}
    raw = r.get("raw_jev_scores_0to4") or {}
    cov = r.get("evidence_coverage") or {}
    dist = r.get("probabilities") or {}
    iv = r.get("judgment_intervals") or {}
    unscored = r.get("dimensions_unscored") or []
    ev = evidence_trail(payload)

    L = []
    A = L.append
    A(f"# Corroboration package — {case}")
    A("")
    A(f"**Model:** `{r.get('model_id')}` · **rubric** `{r.get('rubric_version')}` · "
      f"**generated** {r.get('generated_at')}")
    A("")
    A(f"**Verdict:** composite **{r.get('composite')}** · band **{r.get('band')}**"
      + (f" · gates firing **{r['gates_firing']}**" if r.get("gates_firing") else " · no gates fired"))
    A("")

    A("---")
    A("")
    A("## 1. What Jev said")
    A("")
    A("| dimension | score | raw (0-4) | coverage | 80% interval | most-mass level |")
    A("|---|---:|---:|---:|---|---|")
    for k in ("market_headroom", "competitive_room", "mental_advantage",
              "position_availability", "defensibility", "demand_reach"):
        if k not in dims:
            continue
        if k in unscored:
            A(f"| {DISPLAY.get(k,k)} | **withheld** | {raw.get(k)} | "
              f"{cov.get(k)} | — | below coverage floor — no judgment |")
            continue
        band = (iv.get(k) or {}).get("band_80pct_display_1to5")
        bs = f"{band[0]}–{band[1]}" if band else "—"
        ld = (dist.get(k) or {})
        lv, _lt, m = top_level(ld, {})
        A(f"| {DISPLAY.get(k,k)} | **{dims[k]}/5** | {raw.get(k)} | {cov.get(k)} | "
          f"{bs} | level {int(lv)+1 if lv!='' else '—'} @ {m:.2f} |")
    A("")
    A(f"Input sufficiency: **{r.get('input_sufficiency')}**")
    A("")

    A("### The exact distributions")
    A("")
    A("```")
    for k in dims:
        if k in unscored:
            continue
        A(f"{DISPLAY.get(k,k):34} {json.dumps(dist.get(k))}")
    A("```")
    A("")

    A("---")
    A("")
    A("## 2. What the number means")
    A("")
    A("**The rubric level matching the displayed score, quoted verbatim.** This is a structural "
      "fact about the distribution — not an explanation the model produced. Where the "
      "highest-mass level differs from the displayed score, that is flagged: it means the "
      "judgment sits BETWEEN two levels and the rounded display is hiding it.")
    A("")
    rubric = json.loads((HERE / "rubric.json").read_text())
    qs = rubric.get("questions") or {}
    for k in dims:
        if k in unscored:
            continue
        ld = dist.get(k) or {}
        if not ld:
            continue
        # level text for the DISPLAYED score (display = raw_rounded + 1)
        shown_idx = str(int(dims[k]) - 1)
        mass_idx, _lt, mass_m = top_level(ld, {})
        spec = qs.get(k) or {}
        if not spec:
            spec = ((rubric.get("_meta") or {}).get("_superseded") or {}).get(k, {}).get("definition", {})
        levels = spec.get("levels") or []
        try:
            text = levels[int(shown_idx)]
        except (ValueError, IndexError, TypeError):
            text = "(level text unavailable)"
        A(f"- **{DISPLAY.get(k,k)} = {dims[k]}/5** — level {int(shown_idx)+1}:")
        A(f"  > {text}")
        if mass_idx and mass_idx != shown_idx:
            try:
                mtext = levels[int(mass_idx)]
            except (ValueError, IndexError, TypeError):
                mtext = "(unavailable)"
            A(f"  - ⚠️ **rounding warning:** the highest mass is on level {int(mass_idx)+1} "
              f"({mass_m:.0%}) — the raw value {raw.get(k)} sits between level "
              f"{int(shown_idx)+1} and level {int(mass_idx)+1}. Treat the display as approximate.")
            A(f"    > {mtext}")
    A("")

    A("---")
    A("")
    A("## 3. What it saw")
    A("")
    A("### The owner's own claims (verbatim from the submission)")
    A("")
    for key, val in ev["owner_claims"].items():
        if val:
            A(f"- **{key}:** {val}")
    A("")
    A("### Owner-named competitors")
    A("")
    for c in ev["owner_named_competitors"]:
        A(f"- {c}")
    A("")
    A("### The derived competitive set (what the scorer was actually given)")
    A("")
    for tier in ("tier_0_default", "tier_1_cheap_substitute", "tier_2_direct_set",
                 "tier_3_category_incumbent", "tier_4_adjacent_crossover",
                 "tier_5_professional_route", "tier_6_indirect"):
        t = ev["derived_tiers"].get(tier)
        if not t:
            continue
        A(f"**{tier.replace('_',' ').upper()}**")
        for m in t["members"]:
            A(f"  - {m}")
        if t.get("why"):
            A(f"  - *why:* {t['why']}")
        A("")
    A("### The blindspot delta")
    A("")
    bs = ev["blindspot"]
    A(f"- owner named: **{bs['owner_named_count']}** · derived direct set: "
      f"**{bs['derived_direct_set_count']}**")
    A(f"- tier-3 incumbent the owner may not see: {bs['tier_3_incumbent']}")
    A("")

    A("---")
    A("")
    A("## 4. Reason provenance — read this before judging the reasons")
    A("")
    A("**Jev returns no reasoning.** The API response is a typed answer only — score, "
      "legend, probabilities, confidence — measured at ~17 output tokens. The documentation "
      "states System One models are built for fast, focused judgments and that 'analyse this "
      "and determine the best course of action' is the wrong shape of question for them.")
    A("")
    A("So the rows above are, precisely:")
    A("")
    A("| element | provenance |")
    A("|---|---|")
    A("| score, distribution, interval, coverage | **MEASURED** — returned by the model |")
    A("| the most-mass level text | **QUOTED** from the rubric — a fact about the distribution |")
    A("| the evidence basis | **RECORDED** — the state that was sent |")
    A("| the blindspot delta | **COMPUTED** — owner list vs derived set |")
    A("| *any causal story ('it scored 2 because…')* | **NOT ESTABLISHED.** Not measured, not "
      "returned by the model, and deliberately not invented here. |")
    A("")
    A("**Where a cause CAN be established, it is established by perturbation, not by "
      "narration** — running the same case with one input changed and measuring the movement. "
      "The project already holds several such measurements (e.g. removing KOI's differentiator "
      "moves `mental_advantage` 4→2; adding a 'new pet' cue to Pet Lovers Centre moves it 0). "
      "Those are real reasons. This package does not generate them for cases where they have "
      "not been run.")
    A("")
    A("---")
    A("")
    A("## 5. What I am asking you to do")
    A("")
    A("Judge the **score**, given the evidence in section 3. Not the reasons — because there "
      "are no reasons to judge, only a number and the evidence it was given. Specifically:")
    A("")
    A("1. Is each score **within one level** of what you would give, given the SAME evidence?")
    A("2. Where you disagree — is it the score that is wrong, or the **evidence** that is "
      "wrong (section 3 is what the scorer saw; if it is missing something you know, that is "
      "an input defect, not a scoring defect)?")
    A("3. Is there a dimension you would **withhold** that was scored, or one that was "
      "withheld you would score?")
    A("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = Path(args.out) if args.out else (HERE / "corroboration")
    out.mkdir(exist_ok=True)
    for c in args.cases:
        md = build(c)
        p = out / f"{c}.md"
        p.write_text(md)
        print(f"wrote {p.relative_to(HERE)}  ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
