"""Live end-to-end test of the 4.6 scanner wiring. Run from specs/calibration."""
import json
import sys

sys.path.insert(0, ".")
from competitor_scan import scan, to_competitive_set

res = scan("bubble tea", "Singapore", [], per_url_timeout=15)
print("VERDICT:", res["_meta"]["verdict"])
print("SUMMARY:", res["_meta"]["capture_summary"])
cs = to_competitive_set(res)
members = (cs.get("SCANNED OCCUPANTS OF THE CATEGORY") or {}).get("members") or []
print("MEMBERS:", len(members))
for m in members[:8]:
    print("   -", m[:150])
json.dump(cs, open("/tmp/derived-set.json", "w"), indent=1)
print("WROTE /tmp/derived-set.json")
