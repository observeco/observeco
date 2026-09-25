"""Read the full ACRA column map and answer the decisive Tier 7 question:
is there an industry/activity (SSIC) column, and is there a registration date?
"""
from __future__ import annotations

import json
import urllib.request

UA = {"User-Agent": "ObserveCo-research/1.0"}
URL = ("https://api-production.data.gov.sg/v2/public/api/datasets/"
       "d_af2042c77ffaf0db5d75561ce9ef5688/metadata")

req = urllib.request.Request(URL, headers=UA)
with urllib.request.urlopen(req, timeout=40) as r:
    m = json.loads(r.read().decode("utf-8", "replace"))["data"]

cm = m["columnMetadata"]
order = cm["order"]
name_of = cm["map"]

print(f"dataset : {m['name']}")
print(f"rows-> {m['datasetSize']:,} bytes, coverage {m['coverageStart'][:10]}"
      f" -> {m['coverageEnd'][:10]}")
print(f"columns : {len(order)}")
print()
print("full column list:")
for i, cid in enumerate(order):
    print(f"  {i:2}. {name_of.get(cid, cid)}")

cols = {name_of.get(c, c) for c in order}
print()
print("=== the Tier 7 question ===")
ssic = [c for c in cols if "ssic" in c.lower()]
date = [c for c in cols if any(
    k in c.lower() for k in ("date", "incorporation", "registration", "start"))]
print(f"SSIC / activity columns : {ssic or 'NONE FOUND'}")
print(f"date-related columns    : {date or 'NONE FOUND'}")
print()
if ssic and date:
    print("VERDICT: Tier 7 industry-filtered derivation is SUPPORTED.")
    print("  An activity code plus a registration/incorporation date is enough to")
    print("  answer 'who registered in this industry in the last N months'.")
elif date and not ssic:
    print("VERDICT: Tier 7 is PARTIAL. A registration date exists, so recency works,")
    print("  but with no activity code the result cannot be filtered to an industry")
    print("  offline -- it would need name matching against the category.")
else:
    print("VERDICT: NOT SUPPORTED from this dataset. Needs the gated ACRA API.")
