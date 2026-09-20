# Steps 1–3 complete

**Book 1:** *Small Island, Crowded Market* — 268 pp
**Book 2:** *How a Small Business Gets Chosen* — 252 pp
Both divisible by 4. Both with indexes. Covers built.

---

## Step 1 — Everything wired in and rebuilt

**Figures.** All twenty replaced. Three cut: `book1-ai-doors.png`,
`book1-ai-walls.png` (clip-art, no data) and `book2-process.png` (duplicated
the five-step figure). Zero `visuals/*.png` references remain in either
manuscript.

**The worksheet** is no longer an image. `worksheet-one-page.tex` is
`\input` at the point the PNG used to sit.

**Front matter.** The corrected "For the reader" and author foreword are in.
Book 2's front matter had been carrying **"the first book, *Where the Money
Is*"** — the superseded title — which is now *Small Island, Crowded Market*.

**A duplicate contents was removed.** Book 1's markdown carried a hand-typed
contents list *in addition to* the LaTeX-generated one, and it still listed
the old title. LaTeX generates the real contents with page numbers, so the
manual copy is gone.

**Text fixes from the audit:**

| | Fix |
|---|---|
| Chapter 2 | "This book **has shown** you" → "This book **will show** you". It cited three examples from sixty pages later |
| Note-to-self | "and should be refreshed at publication" deleted from the printed text |
| Enterprise counts | 371,000 vs 369,500 reconciled with an explicit note: 371,000 is all enterprises, 369,500 the SME subset, and "businesses like yours" means the second |
| Spelling | `labor`→`labour` (×3), `recognize`→`recognise`, `confidence-labelled`→`confidence-labeled` |
| Running heads | `\chaptermark` truncates any title over 44 characters, so no head wraps to two lines |
| PDF metadata | Title, Author, Subject, Keywords now set — see the bug below |

**A metadata bug found and fixed.** `hypersetup` was correct all along, but
the page-padding step rewrites the PDF with pypdf, and **pypdf drops the
document info unless you copy it explicitly.** That is why Title and Author
were empty in every earlier build even when the LaTeX was right. Both books
now report their metadata correctly.

---

## Step 2 — The index

`index_terms.py` defines 72 terms across four groups: Singapore brands,
agencies and statistical sources, positioning concepts, and the authors in
the intellectual-history chapter. `index_tag.py` tags the **first occurrence
of each term per chapter**, so the index points at discussions rather than
every passing mention.

Result: **244 entries in Book 1, 324 in Book 2**, rendering as a two-column
index with real page numbers.

One thing worth recording, because it cost me two iterations: the tagger
originally used markdown heuristics (`^#` for headings) but runs on
post-pandoc LaTeX. With no chapter boundaries detected, every term was tagged
once for the whole book and the index pointed at a single page each. Chunking
on `\chapter{` and `\section{` fixed it — 41 entries became 244.

---

## Step 3 — The covers

`cover-book1.pdf` and `cover-book2.pdf`. Full wraps: back, spine, front, at
5.5 × 8.5 in plus 3 mm bleed on all sides.

| | Pages | Spine width |
|---|---|---|
| Book 1 | 268 | **10.9 mm** |
| Book 2 | 252 | **10.2 mm** |

Calculated at 0.0032 in per leaf (80 gsm cream). **Confirm that multiplier
with your printer before final art** — a 1 mm error here makes a visibly
crooked cover, and it changes with paper stock.

They read as a series: same layout, same typography, "THE MAP AND THE METHOD
/ BOOK ONE / BOOK TWO" in the same position, different colour field —
green for the ground, rust for the move.

Book 2's back cover leads with the failures, as agreed: the brands that
widened and lost their word, the one that owned its word perfectly and lost
anyway, the one that was flawlessly different with no demand under it. The
front strap says "Including where positioning fails", so a browser who reads
only the subtitle is not misled about what the book is.

The ISBN barcode area is a marked white block, bottom right of the back
cover. Drop the real barcode in when you have it.

---

## Gate results

| | Book 1 | Book 2 |
|---|---|---|
| Severe overfull (content lost) | **0** | **0** |
| Visible overfull (>5pt) | 5 | 6 |
| Figures clipped at trim | **0** | **0** |
| Template leaks (`BOOK`, `SUB`) | **0** | **0** |
| Page count ÷ 4 | ✅ | ✅ |
| Chapter openings on verso | **0** | **0** |
| Blank pages carrying furniture | **0** | **0** |

The severe overfulls are gone. Four table cells were shortened to get there —
"Compensation-of-employees share of GDP" → "Employee share of GDP",
"~20% (S$132.8bn value added)" → "~20% (S$132.8bn)", and two posture-matrix
cells. Check you are happy with the wording.

The remaining 11 visible overfulls are 5–15pt — a hair past the margin in
table cells, not content loss. Worth one pass if you want it perfect; not
worth blocking a proof.

The one deliberate gate failure is `978-XXX-XX-XXXX-X`, which fails on
purpose so the placeholder ISBN cannot reach a printer unnoticed.

---

## What only you can do now

1. **Assign the ISBNs** and drop the barcode into the cover art.
2. **Confirm the spine multiplier** with your printer.
3. **Run the final build on your Mac** with `build_latex_MAC.py`, which keeps
   your Charter font line. My builds use TeX Gyre Pagella because this
   container's Charter bold crashes the PDF driver on accented characters, so
   **the 268 and 252 page counts will shift slightly** — and the spine widths
   with them. Recalculate after that build.
4. **Restore the CJK font** (Songti SC) if you want 顾均辉 in the references,
   or leave it romanised.
5. **Decide the Collin Seow naming** — currently the product is named, the
   person is not.
6. **Order a printed proof.** Gutter margin, figure legibility at actual
   size, and colour on press cannot be judged on screen. After nine rounds of
   screen review, that is the check that has never been done.

---

## Files

- `book1-FINAL.pdf`, `book2-FINAL.pdf` — interiors
- `cover-book1.pdf`, `cover-book2.pdf` — full wraps with bleed
- `build-pipeline-final.zip` — `build_latex.py`, `gate.py`, `index_tag.py`,
  `index_terms.py`, `chicago_bib.tex`, `worksheet-one-page.tex`, `covers.py`

Every change in `build_latex.py` carries a comment explaining what it fixes.
`gate.py` runs after each build; keep it in the loop.
