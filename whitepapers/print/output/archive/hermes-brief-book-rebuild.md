# Task brief: rebuild book1 and book2 interiors

## Why this task exists

The last delivery report said the index fix landed — 244 entries in Book 1,
324 in Book 2. The shipped PDFs have 41 single-page entries in Book 1 and no
index at all in Book 2. The fix is present in `index_tag.py`; it never reached
the files that were handed over. Assume the same can happen again. The
contract below is written so that it cannot.

## The rule

**A claim about the PDFs is only true if `verify_final.py` says so, run against
the exact file being delivered.** Paste its raw output, including the SHA-256,
into the report. Do not summarise it, do not describe a fix as done without the
matching line in that output, and do not report on build output that is not the
file being shipped.

If a check cannot be made to pass, say so and leave it failing. A failing check
that is named is fine. A passing claim that the verifier does not support is not.

## Inputs

- `manuscripts/book1.md`, `manuscripts/book2.md`
- `figures/` (17 PNGs)
- `build/`: `build_latex_MAC.py`, `gate.py`, `index_tag.py`, `index_terms.py`,
  `chicago_bib.tex`, `worksheet-one-page.tex`, `covers.py`
- `blank-page-fixes.md` — the three code edits, with the exact snippets
- `verify_final.py` — the acceptance check

Build with `build_latex_MAC.py` so the Charter font line is kept. Do not
substitute a font.

## The work

1. Apply the three edits in `blank-page-fixes.md`: front matter, duplicate
   References heading, `gate.py` furniture check. Add the two new gate checks
   in section 4 of that file.
2. Establish why the index did not render. Book 2 produced no `.ind` at all,
   so this is a build-sequence problem, not a tagging problem: `makeindex` has
   to run between LaTeX passes, and the passes have to rerun after it. Confirm
   `.idx` is non-empty for both books before blaming anything else.
3. Investigate the three items in section 5 of `blank-page-fixes.md`:
   Book 1 p239 (chapter with no body), p63 (orphan text under Chapter 9's
   running head), p165 (stray page break). These are in the markdown, not the
   template.
4. Rebuild, run `verify_final.py`, iterate until it exits 0 apart from the ISBN.
5. Recalculate spine widths from the new page counts and rerun `covers.py`.

## Acceptance

`python3 verify_final.py book1-FINAL.pdf book2-FINAL.pdf` exits 0, with these
exceptions and no others:

- the placeholder ISBN failure, which is deliberate until Sean assigns the
  real ones
- Book 1 p247, the worksheet chapter, whose opening page carries only the
  title with the worksheet overleaf. Confirm with Sean whether that is
  intended before changing it.

For reference, the current files fail with:

    book1: furniture pages [52, 165]; empty chapter openings [239, 247];
           3 front-matter blanks; References printed twice [259, 261];
           index 41 entries, 0 of them with more than one page number
    book2: 3 front-matter blanks; References printed twice [239, 241];
           no index

## Do not

- Delete blank pages from the finished PDFs. Removing a page flips every page
  after it from recto to verso and puts chapter openings on the wrong side.
  Blanks are fixed in the source or not at all.
- Change wording, cut table cells, or reflow content to hit a page count.
  Page count follows from the text; the spine follows from the page count.
- Report page counts or spine widths from any build other than the Mac build.
