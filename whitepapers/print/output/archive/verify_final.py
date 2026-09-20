#!/usr/bin/env python3
"""Verify the PDFs that are actually being shipped.

Runs on the delivered files, not on build output, and depends on nothing but
pypdf. Prints a SHA-256 for each file so the thing that was checked and the
thing that was sent can be shown to be the same file.

    python3 verify_final.py book1-FINAL.pdf book2-FINAL.pdf

Exit code 0 = all checks pass. Anything else = do not ship.
"""
import sys, re, hashlib
import pypdf

LEAF_IN = 0.0032          # inches per leaf, 80 gsm cream — confirm with printer
COVER_IN = 0.0            # add cover board thickness here if perfect bound

HEAD = re.compile(r"[A-Z0-9][A-Z0-9 ,&’'\-–—\.:;\?!\(\)]{3,}")
FOLIO = re.compile(r"\d{1,3}")


def pages_text(path):
    r = pypdf.PdfReader(path)
    return [(p.extract_text() or "").strip() for p in r.pages], r


def lines(t):
    return [l.strip() for l in t.split("\n") if l.strip()]


def check(path):
    fails, notes = [], []
    txt, reader = pages_text(path)
    n = len(txt)

    # 1. page count divisible by 4
    if n % 4:
        fails.append(f"page count {n} is not divisible by 4")

    # 2. chapter openings on recto. PDF page 1 is a recto, so openings are odd.
    verso = [i + 1 for i, t in enumerate(txt)
             if t.startswith("Chapter ") and (i + 1) % 2 == 0]
    if verso:
        fails.append(f"chapter opening on a verso: {verso}")

    # 3. pages that are empty except for a running head and/or a folio
    furn = []
    for i, t in enumerate(txt):
        L = lines(t)
        body = [l for l in L if not FOLIO.fullmatch(l) and not HEAD.fullmatch(l)]
        if L and not body:
            furn.append(i + 1)
    if furn:
        fails.append(f"blank pages carrying a head/folio: {furn}")

    # 4. a chapter opening with no text under it
    empty_ch = [i + 1 for i, t in enumerate(txt)
                if lines(t) and lines(t)[0].startswith("Chapter ") and len(lines(t)) <= 2]
    if empty_ch:
        fails.append(f"chapter opening with no body text: {empty_ch}")

    # 5. front matter: at most one blank leaf before the contents
    toc = next((i for i, t in enumerate(txt) if t.startswith("Contents")), None)
    if toc is None:
        fails.append("no contents page found")
    else:
        fm_blank = [i + 1 for i in range(toc) if not txt[i]]
        if len(fm_blank) > 1:
            fails.append(f"{len(fm_blank)} blank pages in front matter {fm_blank}; "
                         "copyright belongs on the title verso")

    # 6. the References heading appears once, not twice
    ref = [i + 1 for i, t in enumerate(txt) if lines(t) and lines(t)[0] == "References"]
    if len(ref) > 1:
        fails.append(f"'References' heading printed {len(ref)} times: {ref}")

    # 7. the index rendered, with real entries pointing at real pages
    idx = next((i for i, t in enumerate(txt) if t.startswith("Index")), None)
    if idx is None:
        fails.append("no index in the PDF — makeindex did not run or the .ind is missing")
    else:
        body = "\n".join(txt[idx:])
        entries = [l for l in body.split("\n") if re.search(r",\s*\d", l)]
        multi = [l for l in entries if len(re.findall(r"\d+", l)) > 1]
        if len(entries) < 150:
            fails.append(f"index has only {len(entries)} entries — expected 240+. "
                         "The per-chapter chunking in index_tag.py did not take.")
        if entries and len(multi) < 0.2 * len(entries):
            fails.append(f"only {len(multi)}/{len(entries)} index entries carry more "
                         "than one page number — terms tagged once for the whole book")
        notes.append(f"index: {len(entries)} entries starting p{idx+1}")

    # 8. placeholder ISBN must not reach a printer
    if "978-XXX-XX-XXXX-X" in "\n".join(txt):
        fails.append("placeholder ISBN 978-XXX-XX-XXXX-X still in the text")

    # 9. PDF metadata survived the padding rewrite
    meta = reader.metadata or {}
    for k in ("/Title", "/Author"):
        if not (meta.get(k) or "").strip():
            fails.append(f"PDF metadata {k} is empty (pypdf drops it unless copied)")

    blanks = [i + 1 for i, t in enumerate(txt) if not t]
    notes.append(f"{len(blanks)} blank pages: {blanks}")
    notes.append(f"spine at {LEAF_IN} in/leaf: {(n/2)*LEAF_IN*25.4 + COVER_IN:.1f} mm")
    return n, fails, notes


def main(paths):
    ok = True
    for path in paths:
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
        n, fails, notes = check(path)
        print(f"\n=== {path}")
        print(f"    sha256 {sha}")
        print(f"    {n} pages")
        for note in notes:
            print(f"    {note}")
        if fails:
            ok = False
            for f in fails:
                print(f"    FAIL: {f}")
        else:
            print("    all checks pass")
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["book1-FINAL.pdf", "book2-FINAL.pdf"]))
