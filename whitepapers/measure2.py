#!/usr/bin/env python3
import re
for path in ["book1-map-manuscript.md", "book2-from-small-to-big-manuscript.md"]:
    with open(path, encoding="utf-8") as f:
        t = f.read()
    words = len(t.split())
    honest = len(re.findall(r'\bhonest(ly)?\b', t, re.I))
    emdash = t.count("—")
    notA = len(re.findall(r'\bis not\b[^.]{0,40}\b\.\s*It is\b', t))
    honest_chance = len(re.findall(r'the honest chance', t))
    honest_reading = len(re.findall(r'the honest reading', t))
    honest_close = len(re.findall(r'the honest close', t))
    print(f"{path}: {words}w | honest={honest} | emdash={emdash} | notA={notA} | honest_chance={honest_chance} | honest_reading={honest_reading} | honest_close={honest_close}")
