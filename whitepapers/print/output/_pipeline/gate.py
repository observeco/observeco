#!/usr/bin/env python3
"""Verification gate. Run after every build, before showing anyone the PDF."""
import subprocess, sys, re, os, tempfile
import numpy as np
from PIL import Image

def pages_text(pdf):
    t = subprocess.run(["pdftotext","-layout",pdf,"-"],capture_output=True,text=True).stdout
    return t.split("\f")

def fig_pages(pdf):
    out = subprocess.run(["pdfimages","-list",pdf],capture_output=True,text=True).stdout
    return sorted({int(l.split()[0]) for l in out.splitlines()[2:] if l.split()})

def raster(pdf,p,dpi=100):
    d=tempfile.mkdtemp()
    subprocess.run(["pdftoppm","-png","-r",str(dpi),"-f",str(p),"-l",str(p),pdf,d+"/p"],
                   capture_output=True)
    f=[x for x in os.listdir(d) if x.endswith(".png")]
    return np.asarray(Image.open(os.path.join(d,f[0])).convert("L")) if f else None

def check(pdf,name):
    fails=[]
    pages=pages_text(pdf)
    n=len(pages)-1

    # 1. template label leakage + bracketed markers
    full="\n".join(pages)
    for pat in [r'BOOK(?=[A-Z][a-z])',r'SUB(?=[A-Z][a-z])',r'\[VERIFY',r'\[AUTHOR',r'\[truncated\]',
                r'\[to be assigned',r'\[to complete',r'\bTITLE\b',r'\bBODY\b',r'978-XXX-XX-XXXX-X']:
        m=re.findall(pat,full)
        if m: fails.append(f"template/marker leak {pat!r} x{len(m)}")

    # 2. page count divisible by 4
    if n%4: fails.append(f"page count {n} not divisible by 4")

    # 3. chapter openings all recto
    off=None
    for i,p in enumerate(pages):
        L=[l.strip() for l in p.split("\n") if l.strip()]
        if L and re.fullmatch(r"\d{1,3}",L[-1]): off=(i+1)-int(L[-1]); break
    if off:
        verso=sum(1 for i,p in enumerate(pages)
                  if p.strip().startswith("Chapter ") and ((i+1)-off)%2==0)
        if verso: fails.append(f"{verso} chapter openings on verso")

    # 4. content past the right margin. LaTeX's own Overfull \\hbox warnings
    #    are authoritative -- they are measured by the typesetter in points.
    #    Anything over 5pt is visible on the page; over 20pt loses content.
    log = pdf.replace("-print.pdf",".log").replace("/tmp/","/tmp/")
    if os.path.exists(log):
        _pat_ov = "Overfull " + chr(92)*2 + "hbox " + r"\(([\d.]+)pt"
        ov=[float(x) for x in re.findall(_pat_ov, open(log,errors="ignore").read())]
        bad=[x for x in ov if x>5]; severe=[x for x in ov if x>20]
        if severe:
            fails.append(f"{len(severe)} SEVERE overfull lines (>20pt, content lost); worst {max(severe):.0f}pt")
        if bad:
            fails.append(f"{len(bad)} visible overfull lines (>5pt)")

    # 5. blank pages carrying furniture (head or folio on an otherwise empty page)
    furn=[]
    for i,p in enumerate(pages):
        L=[l.strip() for l in p.split("\n") if l.strip()]
        body=[l for l in L if not re.fullmatch(r"\d{1,3}",l)]
        if L and not body: furn.append(i+1)
    if furn: fails.append(f"{len(furn)} blank pages carry a head/folio: {furn[:8]}")

    # 6. every figure page: ink near the trim edge = clipped or oversized art
    for p in fig_pages(pdf):
        a=raster(pdf,p)
        if a is None: continue
        h,w=a.shape; m=max(2,int(w*0.02))
        if (a[:, :m]<170).sum()>60 or (a[:, -m:]<170).sum()>60:
            fails.append(f"figure p{p}: ink at the trim edge (clipped/oversized)")

    print(f"=== {name}: {n} pages")
    if fails:
        for f in fails: print("  FAIL:",f)
    else:
        print("  all checks pass")
    return not fails

ok=True
for pdf,name in [("/tmp/book1-print.pdf","Book 1"),("/tmp/book2-print.pdf","Book 2")]:
    ok &= check(pdf,name)
sys.exit(0 if ok else 1)
