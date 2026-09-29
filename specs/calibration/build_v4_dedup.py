"""Build the DEDUPED rebuilt corpus (v4) and the six-dimension rubric spec.

Sean's decisions:
  D1  mental_advantage AMENDED to his construct, size-anchored on the ADDRESSABLE segment.
  D2  demand_reach UNCHANGED (my definition -- it measures how well a business has
      described itself and identified its customer group).
  D3  competitive_room + market_headroom stay in the score.
  NEW position_strength -- quality of the current position relative to competitors.
  D4  rebuild the corpus, dedupe, add the dimension, let him regrade.

Dedup rule: one canonical entry per BUSINESS. Where duplicates exist across sets, keep the
richest/most complete form and record the others as repeat datapoints.
"""
import glob
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def norm(name):
    """Normalise a business name for duplicate detection.

    Accents MUST be stripped before tokenising: '\bthe\b' does not match 'Th é', so
    'KOI Thé Singapore' and 'KOI The Singapore' normalised differently and both survived
    dedup. NFKD + combining-mark removal collapses them.
    """
    n = unicodedata.normalize("NFKD", str(name or ""))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower()
    n = re.sub(r"[^a-z0-9]+", " ", n)
    return " ".join(t for t in n.split()
                    if t not in {"singapore", "sg", "pte", "ltd", "group", "the"})


# ---- gather every case with its metadata and form richness -------------------
entries = []
for dirn, setname in (("inputs", "S1"), ("inputs-v2", "S2"), ("inputs-v3", "S3")):
    idx_p = HERE / dirn / "_index.json"
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else None
    for p in sorted(glob.glob(str(HERE / dirn / "*.json"))):
        if p.endswith("_index.json"):
            continue
        try:
            s = json.loads(Path(p).read_text())
        except Exception:
            continue
        m = s.get("_meta", {})
        cid = m.get("case")
        if not cid:
            continue
        f = s.get("form", {})
        if idx:
            e = idx["companies"].get(Path(p).stem) or {}
            nm = e.get("name")
            cat = e.get("cat")
        else:
            nm = f.get("business_name") or m.get("business") or cid
            cat = m.get("product_category") or m.get("category")
        # S1 cases carry no _index.json -- their category lives in form.category as prose.
        # Fall back to it and reduce to a stable category key for grouping/comparison.
        if not cat:
            cat = f.get("category") or ""
            c = str(cat).lower()
            for key, pats in (
                    ("bubble-tea", ["bubble tea", "milk tea"]),
                    ("health-beauty", ["health and beauty", "beauty retail"]),
                    ("supermarket", ["supermarket", "grocery"]),
                    ("gym", ["gym", "fitness", "sports facilit"]),
                    ("hawker", ["bak chor mee", "hawker"]),
                    ("tcm", ["traditional chinese medicine", "tcm"]),
                    ("b2b-it", ["managed it", "cybersecurity"]),
                    ("semiconductor", ["semiconductor", "lithography"]),
                    ("ecommerce", ["online retail", "delivery"]),
                    ("supplements", ["supplement"]),
                    ("aviation", ["aircraft"]),
                    ("inspection", ["vehicle inspection", "technical testing"]),
                    ("consulting", ["consulting"]),
                    ("pet-retail", ["pet retail", "pet care"])):
                if any(x in c for x in pats):
                    cat = key
                    break
            else:
                cat = " ".join(str(cat).split()[:3]) or "?"
        # form richness: total characters of substantive answers
        rich = sum(len(str(v)) for k, v in f.items()
                   if k not in ("city", "role", "company_size_band", "website"))
        rp = HERE / "runs" / ("jev-%s.json" % cid)
        entries.append(dict(set=setname, dirn=dirn, cid=cid, stem=Path(p).stem,
                            name=nm or cid, nkey=norm(nm or cid), cat=cat,
                            richness=rich, path=str(p),
                            has_run=rp.exists()))

groups = defaultdict(list)
for e in entries:
    groups[e["nkey"]].append(e)

print("=" * 84)
print("DEDUP — canonical selection")
print("=" * 84)
print()
print("entries: %d   distinct businesses: %d   removed: %d"
      % (len(entries), len(groups), len(entries) - len(groups)))
print()

canonical = []
repeats = []
for k in sorted(groups):
    v = groups[k]
    if len(v) == 1:
        canonical.append(v[0])
        continue
    # prefer a case that has a recorded run, then the richest form
    best = sorted(v, key=lambda e: (not e["has_run"], -e["richness"]))[0]
    canonical.append(best)
    for e in v:
        if e is not best:
            repeats.append((best, e))
    print("  %-32s keep %-24s (%d chars)   drop %s"
          % (best["name"][:31], best["dirn"] + "/" + best["stem"], best["richness"],
             ", ".join(x["dirn"] + "/" + x["stem"] for x in v if x is not best)))

print()
print("canonical corpus: %d businesses" % len(canonical))
bycat = defaultdict(int)
for e in canonical:
    bycat[e["cat"] or "?"] += 1
print()
for c in sorted(bycat, key=lambda x: (-bycat[x], x)):
    print("   %-22s %d" % (c, bycat[c]))

# ---- write the v4 manifest ---------------------------------------------------
out = HERE / "inputs-v4"
out.mkdir(exist_ok=True)
manifest = {
    "n": len(canonical),
    "built": "2026-09-27",
    "purpose": ("REBUILT corpus after D1-D3 realignment + new relative_strength "
                "dimension + dedup. One canonical entry per business."),
    "dedup": {
        "entries_before": len(entries),
        "businesses_after": len(canonical),
        "removed": len(entries) - len(canonical),
        "rule": ("one entry per business; prefer a case with a recorded run, then the "
                 "richest form. Duplicates retained as repeat datapoints."),
    },
    "repeats": [{"kept": b["dirn"] + "/" + b["stem"], "dropped": d["dirn"] + "/" + d["stem"],
                 "business": b["name"]} for b, d in repeats],
    "companies": {},
}

# KEY ON THE CASE ID, NEVER THE STEM. The stem is unique within a set but NOT across
# sets: S2 uses HB01-HB04 for health & beauty while S3 uses HB01-HB10 for home-baking,
# so keying on the stem silently overwrote Guardian/Pinch Bakehouse, Unity/Sanwichio and
# Sephora/Egyptian Baker -- 121 businesses collapsed to 118 with no error. The case id
# is globally unique by construction. Assert it rather than trust it.
keys = [e["cid"] for e in canonical]
dupes = {k for k in keys if keys.count(k) > 1}
if dupes:
    raise SystemExit("FATAL: case ids are not globally unique: %s" % sorted(dupes))
if len(set(keys)) != len(canonical):
    raise SystemExit("FATAL: %d canonical entries but %d unique keys"
                     % (len(canonical), len(set(keys))))

for e in canonical:
    src = json.loads(Path(e["path"]).read_text())
    manifest["companies"][e["cid"]] = {
        "name": e["name"], "cat": e["cat"], "source_set": e["set"],
        "source": e["dirn"] + "/" + e["stem"], "case": e["cid"],
        "stem": e["stem"], "form_richness_chars": e["richness"],
    }
    (out / (e["cid"] + ".json")).write_text(json.dumps(src, indent=2))
(out / "_index.json").write_text(json.dumps(manifest, indent=2))
print()
print("wrote %s/ (%d case files + _index.json)" % (out.name, len(canonical)))
print("  removed %d duplicate entries" % (len(entries) - len(canonical)))
print("  manifest companies: %d  (must equal %d)"
      % (len(manifest["companies"]), len(canonical)))
assert len(manifest["companies"]) == len(canonical), "manifest lost entries -- key collision"
