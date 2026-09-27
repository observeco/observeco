"""Generate the REGRADE sheet: 121 canonical businesses, one row each, six dimensions.

Sean: "I want to regrade all 121, but you can just show old score entries and I will just
overwrite and you can work off the new definitions."

So each row carries, in this order:
  1. the context he needs to judge
  2. the NEW v1.0.0 scores (the definitions he is now grading against)
  3. his OLD grades (to overwrite) and my OLD 0.9.0 scores (for reference)
  4. blank YOUR_ columns, six of them now including relative_strength

The 0.9.0 comparison and his old grades are REFERENCE ONLY and are visually separated
from the live columns so he does not grade against a stale anchor.
"""
import csv
import glob
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = json.loads((HERE / "rubric-v1.0.0.json").read_text())
OLD = json.loads((HERE / "rubric.json").read_text())

DIMS = ["relative_strength", "mental_advantage", "defensibility",
        "competitive_room", "market_headroom", "demand_reach"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}
W = V1["_meta"]["weights"]
META = V1["_meta"]


def num(x):
    x = (x or "").strip()
    if x.lower() in ("n/a", "na", "n.a.", "n.a", "-", ""):
        return None
    try:
        return float(x)
    except Exception:
        return None


# ---- his old grades, keyed by company name (normalised) ---------------------
def norm(n):
    """Normalise for joining his grades to corpus names.

    Accents must be stripped: his sheet and the corpus disagree on 'KOI Thé' vs
    'KOI The', and without NFKD they are different keys.
    """
    import unicodedata
    n = unicodedata.normalize("NFKD", str(n or ""))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower()
    n = re.sub(r"\b(singapore|sg|pte|ltd|group|the)\b", " ", n)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", n).split())


his = {}
gp = HERE / "sean-grades-raw.csv"
if gp.exists():
    for g in csv.DictReader(open(gp)):
        vals = {ABBR[k]: num(g.get("YOUR_" + ABBR[k])) for k in
                ["mental_advantage", "defensibility", "competitive_room",
                 "market_headroom", "demand_reach"]}
        vals["SCORE"] = num(g.get("YOUR_SCORE"))
        vals["BAND"] = (g.get("YOUR_BAND") or "").strip()
        # NOTE: test for NUMERIC presence only. BAND is a string that is "" when empty,
        # and "" is not None -- testing `is not None` across all values made every row
        # look graded, so all 120 businesses appeared to carry his old grades when only
        # ~56 do. That would have silently attached blanks to ungraded rows.
        if any(v is not None for v in vals.values() if not isinstance(v, str)):
            his.setdefault(norm(g["company"]), []).append(vals)

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())

rows = []
for cid, meta in sorted(idx["companies"].items(), key=lambda kv: (kv[1]["cat"], kv[0])):
    src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
    form = src.get("form", {})
    m = src.get("_meta", {})
    newp = HERE / "runs-v4" / ("jev-%s.json" % cid)
    new = json.loads(newp.read_text()) if newp.exists() else None
    oldp = HERE / "runs" / ("jev-%s.json" % meta["case"])
    old = json.loads(oldp.read_text()) if oldp.exists() else None
    rows.append(dict(
        cid=cid, name=meta["name"], cat=meta["cat"], src=meta["source_set"],
        claim=form.get("differentiator") or "",
        undercut=form.get("undercut_on") or "",
        pos=form.get("positioning_sentence") or "",
        price=form.get("your_price_point") or "",
        comps="; ".join((src.get("competitors_named") or [])[:5]),
        new=new, old=old,
        his=(his.get(norm(meta["name"])) or [None])[0],
        richness=meta.get("form_richness_chars")))

ran = [r for r in rows if r["new"]]
print("canonical businesses : %d" % len(rows))
print("with a v1.0.0 run    : %d" % len(ran))
print("with an old 0.9.0 run: %d" % len([r for r in rows if r["old"]]))
print("with his old grades  : %d" % len([r for r in rows if r["his"]]))


def disp(run, k, dims_are_new=True):
    if not run:
        return ""
    d = run.get("dimensions_display_1to5") or {}
    u = set(run.get("dimensions_unscored") or [])
    if k in u or d.get(k) is None:
        return "n/a"
    return d.get(k)


def bandtext(run):
    if not run:
        return ""
    if run.get("composite") is None:
        return "GATE(%s)" % ",".join(run.get("gates_firing") or [])
    bi = run.get("band_interval") or {}
    return " OR ".join(bi.get("bands") or [run.get("band") or ""])


def comp(run):
    if not run:
        return ""
    c = run.get("composite")
    return "GATE" if c is None else str(c)


def trunc(s, n):
    s = " ".join(str(s or "").split()).replace("|", "/")
    return s if len(s) <= n else s[:n - 1] + "…"


L = []
A = L.append
A("# REGRADE SHEET — 121 businesses, six dimensions, new definitions")
A("")
A("**Rubric v1.0.0** · %d businesses, one row each (duplicates removed) · weights: %s"
  % (len(rows), " · ".join("%s %d%%" % (ABBR[k], W[k]) for k in DIMS)))
A("")
A("## What changed since you last graded")
A("")
A("**1. A sixth dimension was added — `relative_strength` (25%).** Your feedback: the")
A("instrument had no measure of a business's strength *relative to its actual")
A("competitors*. Every old dimension was anchored to size, a hypothetical copycat, the")
A("market, or the business's own buyers — never to the named rivals. It is here now,")
A("weighted highest, and anchored on the **derived competitive set**.")
A("")
A("**Evidence it matters.** Before: McDonald's Singapore (150+ outlets, market leader)")
A("scored **47** and Jollibee Singapore (26 outlets) scored **57** — the leader ranked")
A("10 points *below* the challenger, because no dimension recorded a 5.8× footprint gap.")
A("Under v1.0.0: **McDonald's 65, Jollibee 53.** The inversion is gone.")
A("")
A("**2. `mental_advantage` was re-anchored to your construct.** It no longer asks")
A("'what would a business of this size be expected to own?' (a benchmark nobody could")
A("state). It now asks: **among the buyers you can actually serve, how strongly are you")
A("retrieved?** A home baker's addressable segment is its estate, not the island.")
A("")
A("**3. Duplicates removed.** 132 entries → 121 businesses. You graded 6 of 7 duplicate")
A("pairs identically, so the redundancy was mine, not yours.")
A("")
A("**4. Unchanged, per your calls:** `demand_reach` keeps its original definition (D2);")
A("`competitive_room` and `market_headroom` stay in the score (D3).")
A("")
A("## How to read this sheet")
A("")
A("- **My new score** = v1.0.0, the definitions you are grading against. **This is the")
A("  only column that matters for the comparison.**")
A("- **Your old grade** and **my old score** are shown ONLY so you can see what moved.")
A("  They are from the previous definitions, including the missing dimension. Do not")
A("  anchor on them — overwrite freely.")
A("- **A blank is a valid answer.** If you cannot judge a dimension from the context,")
A("  leave it blank and say why in Notes. 'Cannot judge' is itself a finding.")
A("")
A("### The six dimensions, and what each is measured against")
A("")
A("| Dim | Wt | 'Strong…' compared with WHAT? |")
A("|---|---|---|")
A("| **RS** relative_strength | 25% | **the named occupants of the derived competitive set** |")
A("| **MA** mental_advantage | 20% | **retrieval among the buyers you can actually serve** |")
A("| **DEF** defensibility | 20% | **a well-resourced copycat arriving tomorrow** (1–6) |")
A("| **CR** competitive_room | 15% | **the shape of the market** — not the business |")
A("| **MH** market_headroom | 10% | **whether buyers go unserved** — not the business |")
A("| **DR** demand_reach | 10% | **whether you have identified your buyer and a route to them** |")
A("")
for k in DIMS:
    q = V1["questions"][k]
    A("### %s — %s" % (k.upper(), k))
    A("")
    A("> " + " ".join(str(q.get("instructions", "")).split()))
    A("")
    for i, lv in enumerate(q.get("levels") or [], 1):
        A("- **%d** — %s" % (i, " ".join(str(lv).split())))
    A("")

A("---")
A("")
A("## The 121 businesses")
A("")
A("*Grouped by product category. `My new` = v1.0.0. Dims read RS/MA/DEF/CR/MH/DR.*")
A("")

cats = defaultdict(list)
for r in rows:
    cats[r["cat"]].append(r)
for cat in sorted(cats):
    A("### %s — %d" % (cat, len(cats[cat])))
    A("")
    A("| Company | What they do, and why a buyer picks them | Competes with | "
      "My new | Dims | My old | **YOUR old** | **YOUR RS** | **YOUR MA** | **YOUR DEF** | "
      "**YOUR CR** | **YOUR MH** | **YOUR DR** | Notes |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(cats[cat], key=lambda x: -(int(comp(x["new"]) or 0)
                                               if comp(x["new"]).isdigit() else 0)):
        ctx = trunc(r["claim"], 150)
        if r["price"]:
            ctx += " **Price:** %s" % trunc(r["price"], 26)
        dims = "/".join(str(disp(r["new"], k)) for k in DIMS)
        yourold = ""
        if r["his"]:
            yourold = "/".join(str(int(r["his"][a])) if r["his"][a] is not None else "-"
                               for a in ["MA", "DEF", "CR", "MH", "DR"])
        A("| %s | %s | %s | %s | %s | %s | %s |  |  |  |  |  |  |  |"
          % (trunc(r["name"], 30), ctx, trunc(r["comps"], 34),
             comp(r["new"]), dims, comp(r["old"]), yourold))
    A("")

# ---- CSV --------------------------------------------------------------------
cp = HERE / "regrade-sheet.csv"
with cp.open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["case_id", "company", "category", "source_set", "price",
                "context", "undercut_on", "competes_with",
                "my_new_RS", "my_new_MA", "my_new_DEF", "my_new_CR", "my_new_MH",
                "my_new_DR", "my_new_score", "my_new_band",
                "my_old_MA", "my_old_DEF", "my_old_CR", "my_old_MH", "my_old_DR",
                "my_old_score",
                "your_old_MA", "your_old_DEF", "your_old_CR", "your_old_MH",
                "your_old_DR",
                "YOUR_RS", "YOUR_MA", "YOUR_DEF", "YOUR_CR", "YOUR_MH", "YOUR_DR",
                "YOUR_SCORE", "YOUR_BAND", "YOUR_NOTES"])
    for r in rows:
        h = r["his"] or {}
        w.writerow([
            r["cid"], r["name"], r["cat"], r["src"], r["price"],
            r["claim"], r["undercut"], r["comps"],
            *[disp(r["new"], k) for k in DIMS],
            comp(r["new"]), bandtext(r["new"]),
            *[disp(r["old"], k) for k in
              ["mental_advantage", "defensibility", "competitive_room",
               "market_headroom", "demand_reach"]],
            comp(r["old"]),
            h.get("MA"), h.get("DEF"), h.get("CR"), h.get("MH"), h.get("DR"),
            "", "", "", "", "", "", "", "", ""])

(HERE / "REGRADE-SHEET.md").write_text("\n".join(L))
print()
print("wrote REGRADE-SHEET.md (%d lines)" % len(L))
print("wrote regrade-sheet.csv (%d rows)" % len(rows))
if ran:
    scores = [r["new"].get("composite") for r in ran if r["new"].get("composite") is not None]
    print()
    print("v1.0.0 composite: n=%d mean=%.1f range=%d-%d"
          % (len(scores), statistics.mean(scores), min(scores), max(scores)))
