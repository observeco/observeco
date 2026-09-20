#!/usr/bin/env python3
P = "book2-from-small-to-big-manuscript.md"
with open(P, encoding="utf-8") as f:
    lines = f.readlines()

def find(prefix, start=0):
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    raise SystemExit(f"not found: {prefix}")

# Roster 2: "## The brands that grew big in the open ground" .. before "## More Singapore brands"
r2 = find("## The brands that grew big in the open ground")
r3 = find("## More Singapore brands that positioned well")
# Roster 3 ends before "## NTUC FairPrice"
ntuc = find("## NTUC FairPrice")

print(f"r2={r2} r3={r3} ntuc={ntuc}")

# Delete roster 2 (r2..r3) and roster 3 (r3..ntuc)
# Keep the "---" separators clean: delete from r2 to ntuc, but keep one "---" before NTUC.
new_lines = lines[:r2] + lines[ntuc:]

with open(P, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("deleted rosters 2 and 3")
