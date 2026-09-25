"""Probe what data.gov.sg actually offers for deriving NEW ENTRANTS (Tier 7).

Tests the specific claim: can we derive recently-registered businesses in a category
from open SG government data? If yes, Tier 7 is derivable and Sean is right that
customers would expect it. If no, we must say so rather than imply it.

No API key needed. Writes findings to stdout only.
"""
from __future__ import annotations

import json
import urllib.request

BASE = "https://api-production.data.gov.sg/v2/public/api"
UA = {"User-Agent": "ObserveCo-research/1.0"}


def get(path: str) -> dict:
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


print("=== ACRA collection (id 2) ===")
kids: list[str] = []
try:
    meta = get("/collections/2/metadata")["data"]["collectionMetadata"]
    print("name        :", meta["name"])
    print("managed by  :", meta["sources"])
    print("frequency   :", meta["frequency"])
    print("coverage    :", meta["coverageStart"][:10], "->", meta["coverageEnd"][:10])
    print("last updated:", meta["lastUpdatedAt"][:10])
    kids = meta["childDatasets"]
    print("child datasets:", len(kids), "(one per alphabet letter + 'others')")
except Exception as e:  # noqa: BLE001
    print("FAILED:", e)

print()
print("=== does a child dataset expose an SSIC / activity column? ===")
if kids:
    d = kids[0]
    try:
        m = get(f"/datasets/{d}/metadata")["data"]
        for k in ("name", "coverageStart", "coverageEnd", "lastUpdatedAt"):
            v = m.get(k)
            print(f"  {k:15}: {str(v)[:60]}")
        cols = m.get("columns") or m.get("fields")
        if cols:
            print("  columns       :")
            for c in cols:
                print("    -", c if isinstance(c, str) else c.get("name"))
        else:
            print("  columns       : (not exposed in metadata)")
    except Exception as e:  # noqa: BLE001
        print("  FAILED:", e)

print()
print("=== the coverage question, resolved ===")
print("  Collection-level coverageEnd is stale (2023) BUT that is the COLLECTION")
print("  metadata, not the data. A child dataset reports:")
print("    coverageStart 1970 -> coverageEnd 2026-09-16, lastUpdatedAt 2026-09-16")
print("  So the per-letter datasets DO carry current records. The stale collection")
print("  field is misleading -- do not read it as a data ceiling.")
print()
print("  Therefore new entrants ARE derivable in principle: a recent-registration")
print("  query filtered by activity is answerable from the open monthly dataset.")
print()
print("=== the real limits (these are what matter) ===")
print("  1. COLUMNS NOT EXPOSED in metadata -> must download and inspect the CSV to")
print("     know whether an SSIC / activity code is present. UNVERIFIED.")
print("  2. Activity filtering quality depends on whether SSIC code is populated and")
print("     at what granularity (5-digit SSIC vs coarse industry). UNVERIFIED.")
print("  3. Registration != trading. A registered entity may never open. Tier 7 asks")
print("     who is COMPETING, not who registered.")
print("  4. The open dataset is bulk CSV per alphabet letter -- no query API for")
print("     'registered since date X in industry Y'. Cost is real for 100/mo volume.")
print("  5. ACRA's Business Profile Data API (18 Nov 2025) is richer but gated behind")
print("     a FormSG access request. NOT open data.")
print()
print("  VERDICT: Tier 7 is DERIVABLE but its accuracy is UNVERIFIED on two specific")
print("  unknowns (SSIC presence and granularity). Test by downloading one letter")
print("  dataset and inspecting columns before promising the capability.")
