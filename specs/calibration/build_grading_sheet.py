"""Generate GRADING-SHEET.md + grading-sheet.csv.

Two deliverables:
  1. GRADING-SHEET.md — the context Sean needs to judge each company, my scores, and
     blank columns for his.
  2. grading-sheet.csv — the same cases in a file he can fill in and hand back, because
     typing into 660 markdown cells is not a real option.

HONEST DESIGN CONSTRAINT: 132 cases x 5 dimensions is ~660 judgements. That is not a
feasible ask, and pretending otherwise wastes his time. So the sheet is TIERED:

  CORE (40 cases)  — grade these first; this alone decides whether the rubric agrees
                     with an independent judge. Mixed across all three sets and across
                     my score range, with the disagreements and edge cases IN.
  EXTRA (the rest) — for deeper inspection if the core holds up.

A case whose run is missing is NOT included at all (never emit a case with no score).
"""
import csv
import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "rubric.json").read_text())
META = R["_meta"]
BANDS, WEIGHTS = META["bands"], META["weights"]
FLOOR, NOISE = META["display_floor"], META["band_noise"]

DIM_ORDER = ["mental_advantage", "defensibility", "competitive_room",
             "market_headroom", "demand_reach"]
ABBR = {"mental_advantage": "MA", "defensibility": "DEF", "competitive_room": "CR",
        "market_headroom": "MH", "demand_reach": "DR"}


def run_for(case_id):
    p = HERE / "runs" / ("jev-%s.json" % case_id)
    return json.loads(p.read_text()) if p.exists() else None


rows = []

# ---- S1: original corpus ----
for p in sorted(glob.glob(str(HERE / "inputs" / "*.json"))):
    spec = json.loads(Path(p).read_text())
    m, form = spec.get("_meta", {}), spec.get("form", {})
    cid = m.get("case")
    if not cid:
        continue
    run = run_for(cid)
    if run is None:
        continue
    rows.append(dict(set_name="S1 original corpus", cid=cid,
                     name=form.get("business_name") or m.get("business") or cid,
                     cat=str(m.get("category") or form.get("category") or "—"),
                     claim=form.get("differentiator") or "",
                     undercut=form.get("undercut_on") or "",
                     comps="; ".join((spec.get("competitors_named") or [])[:4]),
                     price=form.get("your_price_point") or "—",
                     label=(m.get("PRE_REGISTERED_PREDICTION")
                            or m.get("PRE_REGISTERED_LABEL") or "—"),
                     label_src=(m.get("LABEL_SOURCE") or m.get("purpose") or ""),
                     run=run, cat_key="S1", run_id=m.get("case")))

# ---- S2 and S3 ----
for setname, dirn, progname, catkey in (
        ("S2 55-company cross-category", "inputs-v2", "v2_progress.json", "S2"),
        ("S3 52 home-based business", "inputs-v3", "v3_progress.json", "S3")):
    idx = json.loads((HERE / dirn / "_index.json").read_text())
    for cid, v in idx["companies"].items():
        spec = json.loads((HERE / dirn / (cid + ".json")).read_text())
        form, m = spec.get("form", {}), spec.get("_meta", {})
        run = run_for(m.get("case"))
        if run is None:
            continue
        rows.append(dict(set_name=setname, cid=cid, name=v["name"],
                         cat=str(v.get("cat", "—")),
                         claim=form.get("differentiator") or "",
                         undercut=form.get("undercut_on") or "",
                         comps="; ".join((spec.get("competitors_named") or [])[:4]),
                         price=str(v.get("price") or "—"),
                         label=str(v.get("label") or v.get("prediction") or "—"),
                         label_src=str(v.get("label_source") or m.get("LABEL_SOURCE") or ""),
                         run=run, cat_key=catkey, run_id=m.get("case")))


def sc(r):
    return (r["run"] or {}).get("composite")


scored = [r for r in rows if sc(r) is not None]
gated = [r for r in rows if sc(r) is None]

# ---------------------------------------------------------------------------
# CORE selection — must be a fair test, not the easy cases
# ---------------------------------------------------------------------------
core = []
core_ids = set()          # keyed on (set, cid) -- cids are NOT globally unique


def key_of(r):
    """A case's unique key. `cid` alone is NOT unique across sets: S2 uses HB01-HB04
    for health & beauty while S3 uses HB01-HB10 for home-baking, so keying on cid
    silently dropped 4 cases from both the core and the extra list."""
    return (r["set_name"], r["cid"])


def take(r, why, cap=None, bucket=None):
    if key_of(r) in core_ids:
        return False
    if cap is not None and len(bucket) >= cap:
        return False
    r["_why"] = why
    core.append(r)
    core_ids.add(key_of(r))
    if bucket is not None:
        bucket.append(r)
    return True


# P1 — every refusal and every statutorily-prohibited business. The gate is the most
# testable claim in the rubric, and statute is the hardest external label I have.
p1 = []
for r in gated + scored:
    if r["label"] == "refused" or sc(r) is None:
        take(r, "refused — is the refusal right?", bucket=p1)
# P2 — external OUTCOME labels: documented deaths and documented moves out of the home
p2 = []
for r in scored:
    if r["label"] in ("dead", "graduated"):
        take(r, "external outcome label (died / outgrew the home)", bucket=p2)
# P3 — band-boundary cases, where the verdict WORD can flip on a re-run. Capped, because
# there are many and they test the same thing.
p3 = []
for r in sorted([r for r in scored if key_of(r) not in core_ids],
                key=lambda r: (r["run"] or {}).get("band_interval", {})
                .get("distance_to_boundary", 99)):
    bi = (r["run"] or {}).get("band_interval") or {}
    if bi.get("bands") and len(bi["bands"]) > 1:
        take(r, "band-boundary — verdict word can flip", cap=6, bucket=p3)
# P4 — one mid-range representative per (set, label), so no label goes ungraded. Capped.
p4 = []
by = defaultdict(list)
for r in scored:
    by[(r["cat_key"], r["label"])].append(r)
for k in sorted(by):
    v = by[k]
    take(sorted(v, key=lambda r: sc(r))[len(v) // 2],
         "representative of %s/%s" % k, cap=14, bucket=p4)
# P5 — fill to 40 across the whole score range, so the core is not all extremes
rest = sorted([r for r in scored if key_of(r) not in core_ids], key=lambda r: sc(r) or 0)
step = max(1, len(rest) // 12)
for r in rest[::step]:
    if len(core) >= 40:
        break
    take(r, "spread across the score range")

core.sort(key=lambda r: (r["set_name"], r["cat"], -(sc(r) or 999)))
print("cases with a recorded run : %d (scored %d, refused %d)" %
      (len(rows), len(scored), len(gated)))
print("CORE set                 : %d   (P1 refusals %d, P2 outcomes %d, "
      "P3 band-edge %d, P4 representatives %d)"
      % (len(core), len(p1), len(p2), len(p3), len(p4)))
print("EXTRA set                : %d" % (len(rows) - len(core)))


def dims_of(r):
    run = r["run"] or {}
    d = run.get("dimensions_display_1to5") or {}
    uns = set(run.get("dimensions_unscored") or [])
    out = []
    for k in DIM_ORDER:
        out.append("n/a" if k in uns else (str(d.get(k, "?")) if d else "?"))
    return out


def trunc(s, n):
    s = (s or "").replace("\n", " ").replace("|", "/").replace("**", "").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def band_text(r):
    run = r["run"] or {}
    if sc(r) is None:
        return "GATE (%s)" % ",".join(run.get("gates_firing") or [])
    bi = run.get("band_interval") or {}
    return " OR ".join(bi.get("bands") or [run.get("band") or "—"])


L = []
A = L.append
A("# GRADING SHEET — your independent judgement vs the rubric")
A("")
A("**Rubric %s** · band noise ±%.1f · display floor %s · %d cases scored across 3 sets"
  % (META["version"], NOISE, FLOOR, len(rows)))
A("")
A("## Read this first")
A("")
A("**What I want from you is a judgement, not a check of my arithmetic.** Grade")
A("independently — ideally without reading my column first. An echo of my own scores")
A("would be worthless; a disagreement is the most useful thing you can give me.")
A("")
A("**Grade the CORE 40 first.** 132 cases × 5 dimensions is ~660 judgements and that is")
A("not a fair ask. The core 40 is chosen to be a real test: it includes every refused")
A("case, every external outcome label (documented death, documented move out of home),")
A("every statutorily-prohibited business, the band-boundary cases where the verdict word")
A("can flip, and a spread across the whole score range. If the core does not hold up,")
A("the extra 92 will not rescue it, and you will have saved your time.")
A("")
A("**Two ways to give me the numbers:**")
A("")
A("1. **`grading-sheet.csv`** (same folder) — edit the `YOUR_*` columns and hand it back.")
A("   This is the practical route. 660 markdown cells is not.")
A("2. **This markdown** — the `YOUR` columns are there if you prefer reading context here")
A("   and writing scores on paper. I can take them as a list.")
A("")
A("**A blank is a valid answer.** If you cannot judge a dimension, leave it blank and")
A("note why. \"Cannot judge\" is itself a finding — the instrument may be answering a")
A("question a human cannot answer from the same information, which would be a defect.")
A("")

A("---")
A("")
A("## How to grade (so your numbers mean the same as mine)")
A("")
A("Score each dimension **1–5**; **defensibility is 1–6**. Higher is always better.")
A("")
A("| Dim | 1 | 2 | 3 | 4 | 5 | 6 |")
A("|---|---|---|---|---|---|---|")
for k in DIM_ORDER:
    lv = list(R["questions"][k].get("levels") or [])
    cells = [trunc(x, 44) for x in lv]
    while len(cells) < 6:
        cells.append("—")
    A("| **%s** (%s) | %s |" % (ABBR[k], k, " | ".join(cells[:6])))
A("")
A("**Weights:** " + " · ".join("%s %d%%" % (ABBR[k], WEIGHTS[k]) for k in DIM_ORDER))
A("")
A("**Bands:** " + " · ".join("%s %d–%d" % (n, lo, hi) for n, lo, hi in BANDS))
A("")
A("### Four things about the scales that will change your numbers")
A("")
A("1. **`mental_advantage` is RELATIVE to business size.** A sole operator is NOT")
A("   compared with a national chain on absolute recall — each is judged against what a")
A("   business *its size* would be expected to own. A home baker owning its estate's")
A("   birthday occasions can score 4.")
A("2. **`defensibility` is TIME-TO-COPY and OBSTRUCTION**, never effort spent. Level 3 =")
A("   real development work but fully visible (a committed rival arrives in months).")
A("   Level 4+ needs a barrier beyond effort: a trade secret, patent, undisclosed process,")
A("   or a supply arrangement rivals cannot obtain.")
A("3. **`market_headroom` is DEMAND vs SUPPLY, not crowdedness.** I mark it **n/a** where")
A("   capacity is elastic (rivals can add supply, so unmet demand cannot persist). Grade")
A("   it only where buyers genuinely cannot get what they want.")
A("4. **`competitive_room` is CHALLENGER-FRAMED.** High = fragmented, room for a small")
A("   operator. A dominant incumbent therefore *lowers* this score. If that reads wrong")
A("   for a market leader, say so — it is one of the five things I most want attacked.")
A("")

A("---")
A("")
A("## The CORE %d — grade these" % len(core))
A("")
A("*`My dims` = MA/DEF/CR/MH/DR. `n/a` = not scored (see note 3).*")
A("")

for group_name, group in (("CORE", core),
                          ("EXTRA", [r for r in rows if key_of(r) not in core_ids])):
    if group_name == "EXTRA":
        A("---")
        A("")
        A("## The EXTRA %d — only if the core holds up" % len(group))
        A("")
    for setname in sorted(set(r["set_name"] for r in group)):
        srows = [r for r in group if r["set_name"] == setname]
        A("### %s — %d cases" % (setname, len(srows)))
        A("")
        catg = defaultdict(list)
        for r in srows:
            catg[r["cat"]].append(r)
        for cat in sorted(catg):
            A("#### %s" % cat)
            A("")
            if group_name == "CORE":
                A("| ID | Company | Context: what they do, why a buyer picks them | "
                  "Why it is in the core | My label | My score | My dims | "
                  "**YOUR MA** | **YOUR DEF** | **YOUR CR** | **YOUR MH** | **YOUR DR** | "
                  "**YOUR SCORE** | **YOUR BAND** | Notes |")
                A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
            else:
                A("| ID | Company | Context | My label | My score | My dims | "
                  "**YOUR SCORE** | Notes |")
                A("|---|---|---|---|---|---|---|---|")
            for r in catg[cat]:
                d = dims_of(r)
                ctx = trunc(r["claim"], 170)
                if r["undercut"]:
                    ctx += " **Undercut:** " + trunc(r["undercut"], 80)
                ctx += " **Price:** " + trunc(r["price"], 18)
                if group_name == "CORE":
                    A("| %s | %s | %s | %s | %s | %s | %s |  |  |  |  |  |  |  |  |"
                      % (r["cid"], trunc(r["name"], 32), ctx,
                         trunc(r.get("_why", ""), 32), trunc(r["label"], 30),
                         sc(r) if sc(r) is not None else "GATE", "/".join(d)))
                else:
                    A("| %s | %s | %s | %s | %s | %s |  |  |"
                      % (r["cid"], trunc(r["name"], 32), ctx, trunc(r["label"], 30),
                         sc(r) if sc(r) is not None else "GATE", "/".join(d)))
            A("")

A("---")
A("")
A("## My reasoning per case (read AFTER grading)")
A("")
A("The `Label source` is the external fact I recorded before scoring. If a label is")
A("wrong, that is as useful to know as a score disagreement.")
A("")
for r in rows:
    run = r["run"] or {}
    d = run.get("dimensions_display_1to5") or {}
    uns = set(run.get("dimensions_unscored") or [])
    A("**%s · %s** — `%s`" % (r["cid"], r["name"], r["cat"]))
    A("")
    A("- **My label:** %s" % trunc(r["label"], 150))
    A("- **Label source:** %s" % trunc(r["label_src"], 380))
    A("- **My dims:** " + ", ".join(
        "%s %s" % (ABBR[k], ("n/a" if k in uns else d.get(k, "?"))) for k in DIM_ORDER))
    A("- **My composite:** %s  ·  %s" % (
        sc(r) if sc(r) is not None else "—", band_text(r)))
    A("- **YOUR dims:** MA [ ] DEF [ ] CR [ ] MH [ ] DR [ ] → SCORE [ ] BAND [ ]")
    A("- **YOUR notes:**")
    A("")

A("---")
A("")
A("## My scores at a glance")
A("")
by_set = defaultdict(list)
for r in scored:
    by_set[r["set_name"]].append(sc(r))
A("| Set | n scored | mean | sd | range | refused |")
A("|---|---|---|---|---|---|")
for s in sorted(set(r["set_name"] for r in rows)):
    v = by_set.get(s, [])
    ng = len([r for r in gated if r["set_name"] == s])
    A("| %s | %d | %s | %s | %s | %d |" % (
        s, len(v),
        "%.1f" % statistics.mean(v) if v else "—",
        "%.1f" % statistics.stdev(v) if len(v) > 1 else "—",
        "%d–%d" % (min(v), max(v)) if v else "—", ng))
A("")
A("## The five things I most want you to attack")
A("")
A("1. **`market_headroom` is dropped for most cases** (elastic capacity). Is that")
A("   correct, or am I excusing a dimension that simply does not work?")
A("2. **`competitive_room` is challenger-framed** — an incumbent scores *lower* on it.")
A("   Read the levels, then tell me if that reads wrong for a market leader.")
A("3. **Ordering.** The *means* separate across labels, but individual pairs invert")
A("   (29 mid-vs-strong on the HBB set). Where you disagree on **ordering** is the most")
A("   valuable signal in this whole sheet.")
A("4. **The refusals.** Two of five statutorily-prohibited home businesses scored")
A("   normally, and the three that refused did so on *market-structure* grounds — but")
A("   massage and pet grooming ARE competitive markets. The refusal looks coincidental,")
A("   not principled. Should there be a legal/eligibility gate?")
A("5. **My weakest labels.** Where `Label source` is a purpose statement rather than a")
A("   published fact, the label is my opinion wearing a finding's clothes. Treat those")
A("   as low-weight, and tell me which ones you would not have written.")
A("")

# ---------------------------------------------------------------------------
# CSV for entry
# ---------------------------------------------------------------------------
csv_path = HERE / "grading-sheet.csv"
with csv_path.open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["set", "tier", "case_id", "run_id", "company", "category", "price",
                "context_what_they_do", "undercut_on", "competes_with",
                "my_label", "label_source_external",
                "my_MA", "my_DEF", "my_CR", "my_MH", "my_DR", "my_score", "my_band",
                "YOUR_MA", "YOUR_DEF", "YOUR_CR", "YOUR_MH", "YOUR_DR",
                "YOUR_SCORE", "YOUR_BAND", "YOUR_NOTES"])
    for r in sorted(core, key=lambda r: (r["set_name"], r["cat"], -(sc(r) or -1))) + \
            sorted([r for r in rows if key_of(r) not in core_ids],
                   key=lambda r: (r["set_name"], r["cat"], -(sc(r) or -1))):
        run = r["run"] or {}
        d = run.get("dimensions_display_1to5") or {}
        uns = set(run.get("dimensions_unscored") or [])
        w.writerow([
            r["set_name"], "CORE" if key_of(r) in core_ids else "EXTRA",
            r["cid"], r["run_id"], r["name"], r["cat"], r["price"],
            r["claim"], r["undercut"], r["comps"], r["label"], r["label_src"],
            *[("n/a" if k in uns else d.get(k, "")) for k in DIM_ORDER],
            sc(r) if sc(r) is not None else "GATE",
            band_text(r), "", "", "", "", "", "", "", ""])

(HERE / "GRADING-SHEET.md").write_text("\n".join(L))
print("wrote GRADING-SHEET.md (%d lines)" % len(L))
print("wrote grading-sheet.csv (%d rows)" % (len(rows) + 1))
