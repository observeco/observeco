#!/usr/bin/env python3
"""Build a print-ready book PDF from markdown via pandoc -> LaTeX -> tectonic.

Uses the memoir class for proper book typesetting: real hyphenation,
justification, float placement, front matter, TOC with page numbers.
"""
import subprocess, sys, os, re

BOOKS = {
    "book1": {
        "md": "/home/claude/hand/handover/manuscripts/book1.md",
        "title": "Small Island, Crowded Market",
        "subtitle": "What every Singapore business owner should know about the ground they compete on",
        "author": "Sean Foo, founder of ObserveCo",
        "out": "/tmp/book1-print.pdf",
        "tex": "/tmp/book1.tex",
    },
    "book2": {
        "md": "/home/claude/hand/handover/manuscripts/book2.md",
        "title": "How a Small Business Gets Chosen",
        "subtitle": "Lessons from Established Singapore Brands",
        "author": "Sean Foo, founder of ObserveCo",
        "out": "/tmp/book2-print.pdf",
        "tex": "/tmp/book2.tex",
    },
}

TEMPLATE = r"""\documentclass[10pt,twoside,openright]{memoir}

% ── Trim size: Digest 5.5 x 8.5 in (140 x 216 mm) ────────────
\setstocksize{216mm}{140mm}
\settrimmedsize{\stockheight}{\stockwidth}{*}
\setlrmarginsandblock{19mm}{15mm}{*}
\setulmarginsandblock{16mm}{18mm}{*}
\checkandfixthelayout

% ── Fonts ─────────────────────────────────────────────────────
\usepackage{adjustbox}
\usepackage{xurl}
\usepackage{imakeidx}
\makeindex[title=Index, intoc]
\usepackage{xstring}
\usepackage{array}
\usepackage{etoolbox}
\usepackage{fontspec}
% Charter has no U+2192 arrow or U+2265; without a fallback xelatex drops
% them SILENTLY and the shipped book loses the character. DejaVu Serif
% supplies both. \sym{} is used by the preprocessor below.
\newfontfamily\symbolfont{DejaVu Serif}
\newcommand{\sym}[1]{{\symbolfont #1}}
% ---------------------------------------------------------------
% FONT NOTE. On the author's Mac this line should read:
%     \setmainfont{Charter}[Numbers={OldStyle,Proportional}]
% In this Linux container the only Charter is a Type1 PFB whose BOLD
% face (bchb8a.pfb) crashes xdvipdfmx on any accented character via
% the Type1 "seac" operator. TeX Gyre Pagella is substituted here so
% the pipeline can be verified end to end. Metrics differ, so page
% counts from this container are indicative, not final.
% ---------------------------------------------------------------
\setmainfont{TeX Gyre Pagella}[
  Numbers={OldStyle,Proportional},
]
% Bitstream Charter has no true small-caps cut. Requesting one makes LaTeX
% fall back to a Type1 Charter that this TeX install cannot load (fatal
% driver error). Faked small caps keep the running-head look and build.

% CJK font unavailable in this environment; Chinese characters are
% stripped in preprocessing and the name romanised.

% ── Typography ───────────────────────────────────────────────
\linespread{1.3}   % 10pt on 13pt leading
\setlength{\parindent}{1.5em}
\setlength{\parskip}{0pt}
\frenchspacing
% Wide symbol matrices were losing their final column off the trim edge.
% Tighter column padding plus footnotesize inside every table buys about
% 25% width back, which is enough for the six-column matrices.
\setlength{\tabcolsep}{3.5pt}
\AtBeginEnvironment{tabular}{\footnotesize\hyphenpenalty=10000\exhyphenpenalty=10000}
\AtBeginEnvironment{longtable}{\scriptsize\hyphenpenalty=10000\exhyphenpenalty=10000\setlength{\tabcolsep}{2.5pt}}
\hyphenpenalty=1000
\emergencystretch=3em   % last-resort stretch so no line runs off the trim
\exhyphenpenalty=1000
\lefthyphenmin=3
\righthyphenmin=3
\brokenpenalty=10000
\clubpenalty=10000
\widowpenalty=10000
\raggedbottom

% ── Headings ─────────────────────────────────────────────────
\setsecheadstyle{\Large\bfseries\color{accent}}
\setsubsecheadstyle{\large\bfseries\color{accent}}
\setparaheadstyle{\normalsize\bfseries\color{accent}}
\setsecnumformat{}
\setcounter{secnumdepth}{0}

% ── Colour ──────────────────────────────────────────────────
\usepackage{xcolor}
\definecolor{accent}{RGB}{14,110,92}   % insight green
\definecolor{ink}{RGB}{26,26,26}

% ── Running heads ───────────────────────────────────────────
\makepagestyle{book}
\makeevenhead{book}{\small\MakeUppercase{BOOKTITLE}}{}{}
\makeoddhead{book}{}{\small\MakeUppercase{\rightmark}}{}
% Running heads must be one line. Truncate long chapter titles in the head.
\makeatletter
\renewcommand{\chaptermark}[1]{\markright{\@shortchaptertitle{#1}}}
\newcommand{\@shortchaptertitle}[1]{%
  \StrLen{#1}[\@ctlen]%
  \ifnum\@ctlen>44 \StrLeft{#1}{41}\dots\else #1\fi}
\makeatother
\makeevenfoot{book}{}{\thepage}{}
\makeoddfoot{book}{}{\thepage}{}
\pagestyle{book}

% Short running heads: use the chapter title, but memoir's \chaptermark already
% strips the number; cap length so it never wraps to two lines
\renewcommand{\chaptermark}[1]{\markright{\MakeUppercase{#1}}}

% Keep headings from stranding at the foot of a page
\newcommand{\needspacehead}{\needspace{4\baselineskip}}
\let\oldsection\section
\renewcommand{\section}{\needspacehead\oldsection}
\let\oldsubsection\subsection
\renewcommand{\subsection}{\needspacehead\oldsubsection}

% ── Front matter ─────────────────────────────────────────────
\makepagestyle{plain}
\makeevenfoot{plain}{}{}{}
\makeoddfoot{plain}{}{}{}
\makeevenhead{plain}{}{}{}
\makeoddhead{plain}{}{}{}

% ── Chapters open on a new page ───────────────────────────────
\setlength{\beforechapskip}{0pt}
\setlength{\afterchapskip}{2em}
\renewcommand{\chapterheadstart}{}
\setlength{\midchapskip}{1em}

% ── Tables ───────────────────────────────────────────────────
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{calc}
\usepackage{needspace}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\renewcommand{\arraystretch}{1.1}
% Keep short tables from breaking across pages
\let\oldtabular\tabular
\let\oldendtabular\endtabular
\renewenvironment{tabular}[1]{\needspace{8\baselineskip}\oldtabular{#1}}{\oldendtabular}

% ── Figures ─────────────────────────────────────────────────
\usepackage{graphicx}
\usepackage{float}
\usepackage{adjustbox}
\usepackage{placeins}   % \FloatBarrier to stop floats drifting into the next chapter
\graphicspath{{/Users/seanfzc/projects/observeco-main/whitepapers/visuals/}}
% pandoc wraps images in \pandocbounded; bound to both width and height so
% landscape figures scale to fit the text block without overflowing the page
\providecommand{\pandocbounded}[1]{\begin{adjustbox}{max width=\linewidth, max height=\textheight, keepaspectratio}#1\end{adjustbox}}

% ── Misc ────────────────────────────────────────────────────
\usepackage{microtype}
\usepackage{enumitem}
\setlist{nosep,leftmargin=1.5em}
\usepackage[hidelinks]{hyperref}
\hypersetup{pdftitle={BOOKTITLE}, pdfauthor={AUTHOR},
  pdfsubject={Positioning and market structure for Singapore small business},
  pdfkeywords={Singapore, small business, positioning, market structure, SME}}

% ── Rating symbols (TikZ, cannot render as tofu) ─────────────
\usepackage{tikz}
\newcommand{\rhigh}{\tikz[baseline=-0.6ex]\fill (0,0) circle (0.9ex);}
\newcommand{\rmed}{\tikz[baseline=-0.6ex]{\draw (0,0) circle (0.9ex);\fill (0,0) -- (90:0.9ex) arc (90:270:0.9ex) -- cycle;}}
\newcommand{\rlow}{\tikz[baseline=-0.6ex]\draw (0,0) circle (0.9ex);}
\newcommand{\ratingkey}{\par\smallskip\noindent{\footnotesize Key: \rhigh\ high \quad \rmed\ moderate \quad \rlow\ low}}

% ── Bibliography (natbib + chicago.bst, uses bundled bibtex) ──
\renewcommand{\bibsection}{\chapter*{References}\markright{REFERENCES}}
\appto{\bibsetup}{\raggedright\hyphenpenalty=10000\exhyphenpenalty=10000}

\begin{document}

% ── Half title ───────────────────────────────────────────────
\thispagestyle{empty}
\begin{center}
\vspace*{0.4\textheight}
{\Huge\bfseries\color{accent} TITLE }
\end{center}
\cleardoublepage

% ── Full title ───────────────────────────────────────────────
\thispagestyle{empty}
\begin{center}
\vspace*{0.3\textheight}
{\Huge\bfseries\color{accent} TITLE }\\[1em]
{\Large SUBTITLE }\\[3em]
{\large AUTHOR }
\end{center}
\cleardoublepage

% ── Copyright ────────────────────────────────────────────────
\clearpage
\thispagestyle{empty}          % no folio, no running head
\vspace*{0pt}                  % top-aligned, no fill
{\footnotesize                 % 9 pt
  \noindent Copyright \textcopyright\ 2026 Sean Foo. All rights reserved.\par
  \medskip
  \noindent No part of this book may be reproduced, stored in a retrieval system, or transmitted in any form or by any means, electronic, mechanical, photocopying, recording, or otherwise, without the prior written permission of the author, except for brief quotations in a review.\par
  \medskip
  \noindent This book is intended to inform and educate. It is not professional, financial, legal, or investment advice. The market figures and brand facts are drawn from the sources listed in the references and appendix, are confidence-labeled, and should be verified against primary sources before any business decision. The author is not affiliated with, endorsed by, or connected to any of the brands discussed, and the discussion of them is independent commentary.\par
  \medskip
  \noindent Published by ObserveCo, Singapore.\par
  \medskip
  \noindent First edition, 2026.\par
  \medskip
  \noindent ISBN: 978-XXX-XX-XXXX-X \quad\textit{(assign before printing)}\par
}
\clearpage

% ── Contents ─────────────────────────────────────────────────
\frontmatter
\setcounter{tocdepth}{0}   % parts + chapters only (2 levels)
% No hyphenation in the TOC
\begingroup
\hyphenpenalty=10000
\exhyphenpenalty=10000
% Long part titles overrun the contents line. Allow them to break.
\renewcommand{\cftpartfont}{\bfseries}
\setlength{\cftpartnumwidth}{2.2em}
\cftsetindents{part}{0em}{2.2em}
\tableofcontents*
\endgroup
\cleardoublepage

% ── Body ─────────────────────────────────────────────────────
\mainmatter
BODY

\printindex
\end{document}
"""

def build(book):
    cfg = BOOKS[book]
    # 0. Read manuscript, strip front matter (title, subtitle, author, copyright,
    #    for-the-reader, foreword, contents) so the body starts at PART ONE.
    #    The LaTeX template handles title page, copyright, and TOC itself.
    md = open(cfg["md"], encoding="utf-8").read()
    part_idx = md.find("# PART ONE")
    if part_idx < 0:
        part_idx = md.find("# PART ONE")
    body_md = md[part_idx:]

    # Strip manual "Chapter N," prefixes from ## headings (LaTeX supplies the number)
    body_md = re.sub(r'^## Chapter \d+, ', '## ', body_md, flags=re.M)

    # 1. pandoc md -> tex body
    r = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "latex",
         "--top-level-division=part"],
        input=body_md, capture_output=True, text=True)
    if r.returncode != 0:
        print("pandoc error:", r.stderr[-500:]); return False
    body = r.stdout

    # Insert \backmatter before the true back-matter sections (References, Glossary,
    # About the author) so they stop being numbered. Do NOT insert it before a
    # mid-book "Appendix" chapter — that would kill numbering for later parts.
    for sec in ["References", "Glossary", "About the author"]:
        # match \chapter{<sec>...} by prefix
        body = re.sub(rf"\\chapter{{{re.escape(sec)}[^}}]*}}",
                      lambda m: "\\backmatter\n" + m.group(0), body, count=1)

    # Insert \FloatBarrier before every \chapter so figures can't drift into the next chapter
    body = re.sub(r"(?m)^(\\chapter\{)", r"\\FloatBarrier\n\1", body)

    body = re.sub(r"(?s)(\\end\{tabular\})",
                  r"\\end{tabular}}", body)

    # Any table whose row is a long single-cell paragraph (the "Sources &
    # confidence" blocks are one giant cell) must be allowed to break as
    # ordinary text, not held in a rigid box.
    body = re.sub(r"\\begin\{tabular\}\{@\{\}p\{([\d.]+)em\}",
                  lambda m: "\\begin{tabular}{@{}p{%.1fem}" % (float(m.group(1))*0.70),
                  body)

    # pandoc emits longtable column fractions that can sum past 1.0, so the
    # last column runs off the trim. Rescale each longtable's set to sum to
    # 0.96. The fractions are one-per-line, so operate on the block.
    def _fix_lt(text):
        out, i, lines = [], 0, text.split("\n")
        while i < len(lines):
            if lines[i].lstrip().startswith(r"\begin{longtable}"):
                j = i
                while j < len(lines) and "@{}}" not in lines[j]:
                    j += 1
                block = lines[i:j+1]
                fr = [float(x) for x in re.findall(r"real\{([\d.]+)\}", "\n".join(block))]
                if fr and sum(fr) > 0.97:
                    k = 0.96 / sum(fr)
                    nb = []
                    for ln in block:
                        m = re.search(r"real\{([\d.]+)\}", ln)
                        if m:
                            ln = ln.replace(m.group(0),
                                            "real{%.4f}" % (float(m.group(1)) * k))
                        nb.append(ln)
                    block = nb
                out.extend(block); i = j + 1
            else:
                out.append(lines[i]); i += 1
        return "\n".join(out)
    body = _fix_lt(body)

    # Rating-matrix headers ("Customers hold power") sit in c-columns, which
    # cannot wrap, so the header row alone runs ~95pt past the trim. Convert
    # the rating columns to centred paragraph columns so headers break.
    body = re.sub(r"\\begin\{tabular\}\{@\{\}(p\{[\d.]+em\})(c+)@\{\}\}",
                  lambda m: r"\begin{tabular}{@{}" + m.group(1)
                            + (r">{\centering\arraybackslash}p{3.5em}" * len(m.group(2)))
                            + "@{}}", body)

    # The two symbol matrices declare fixed first-column widths (8.5em and
    # 11.2em) that push the six columns past the trim edge. Narrow them and
    # let the row labels wrap -- the symbols must stay on the page.
    body = body.replace(r"\begin{tabular}{@{}p{8.5em}ccccc@{}}",
                        r"\begin{tabular}{@{}p{6.6em}ccccc@{}}")
    body = body.replace(r"\begin{tabular}{@{}p{11.2em}ccccc@{}}",
                        r"\begin{tabular}{@{}p{9.2em}ccccc@{}}")

    # Multi-column prose tables from pandoc (the posture matrix, the
    # industry-structure table) use fixed \real{} column fractions that
    # overrun. Convert them to \small ragged-right so they compose.
    body = body.replace(r"\begin{longtable}[]{@{}", r"\begin{longtable}[]{@{}")
    body = re.sub(r"\\begin\{minipage\}\[b\]\{\\linewidth\}\\raggedright",
                  r"\\begin{minipage}[b]{\\linewidth}\\raggedright\\footnotesize", body)

    # Long URLs cannot hyphenate and blow past the margin. Let them break.
    body = re.sub(r"(https?://[^\s}]+)", r"\\url{\1}", body)

    # Five-column prose tables (the posture matrix, the structural read) run
    # ~30pt past the trim even at footnotesize. Shrink these to scriptsize
    # and tighten padding; they are reference grids, not running text.
    def _shrink_wide(text):
        out=[]
        for blk in re.split(r"(\\begin\{longtable\}|\\end\{longtable\})", text):
            if blk.count("&")>40 and "\\\\" in blk:
                blk = "{\\scriptsize\\setlength{\\tabcolsep}{2pt}" + blk + "}"
            out.append(blk)
        return "".join(out)

    # ---- Index tagging -------------------------------------------------
    # Tag the first occurrence of each term per chapter, so the index points
    # at discussions rather than every passing mention.
    import index_tag
    body = index_tag.tag(body)

    # The one-page self-assessment is a real LaTeX worksheet, not an image.
    body = body.replace("WORKSHEETPATH",
                        "/home/claude/hand/handover/build/worksheet-one-page")

    # Force every image to the text width. pandoc emits bare
    # \includegraphics{...} with no options, so LaTeX places the PNG at its
    # natural pixel size -- 1748px wide art on a 106mm measure runs off the
    # page in every direction. This is the defect that survived four builds.
    body = re.sub(r"\\includegraphics(?!\[)\{",
                  r"\\includegraphics[width=\\linewidth,keepaspectratio]{", body)

    # Wrap glyphs Charter lacks so they render instead of vanishing.
    for _ch in ("\u2192", "\u2265", "\u2264", "\u2190", "\u21d2"):
        body = body.replace(_ch, "\\sym{" + _ch + "}")

    # Fix relative image paths -> absolute (tex is written to /tmp)
    VIS_ABS = "/home/claude/hand/handover/visuals/"
    FIG_ABS = "/home/claude/hand/handover/figures/"
    body = body.replace("visuals/", VIS_ABS)
    body = body.replace("print/figures/", FIG_ABS)

    # Replace \printbibliography with \bibliography{<abs bib>} (natbib path)
    # chicago.bst is not in this TeX distribution. A hand-built
    # thebibliography block in true Chicago notes-bibliography form is
    # substituted instead: full given names, year last, uninverted second
    # author, 3-em dash for repeated authors, ragged right, no hyphenation.
    CHICAGO = open("/home/claude/hand/handover/build/chicago_bib.tex",
                   encoding="utf-8").read()
    body = body.replace("\\printbibliography[title={References}]", CHICAGO)

    # 2. Assemble full .tex
    tex = TEMPLATE
    # Replace SUBTITLE BEFORE TITLE, else the "TITLE" inside "SUBTITLE" gets clobbered
    # Order-independent substitution. The old chained .replace() calls were
    # order-dependent: "TITLE" is a substring of both "SUBTITLE" and
    # "BOOKTITLE", so replacing TITLE second turned BOOKTITLE into
    # BOOK + <title>. That produced "BOOKSmall Island, Crowded Market" on
    # 108 pages, and earlier "SUBHow a Small Business Gets Chosen".
    # Single-pass regex with longest-token-first alternation cannot recur.
    _subs = {
        "BOOKTITLE": cfg["title"],
        "SUBTITLE":  cfg["subtitle"],
        "AUTHOR":    cfg["author"],
        "TITLE":     cfg["title"],
        "BODY":      body,
    }
    _pat = re.compile("|".join(sorted(map(re.escape, _subs), key=len, reverse=True)))
    tex = _pat.sub(lambda m: _subs[m.group(0)], tex)
    with open(cfg["tex"], "w", encoding="utf-8") as f:
        f.write(tex)

    # 3. tectonic -> pdf
    # Three passes: TOC, then cross-references, then final page numbers.
    for _pass in range(3):
        r = subprocess.run(["xelatex","-interaction=nonstopmode",
                            "-output-directory=/tmp", cfg["tex"]],
                           capture_output=True, text=True)
    if not os.path.exists(cfg["tex"].replace(".tex", ".pdf")):
        print("xelatex error:", (r.stdout or "")[-2500:]); return False
    # tectonic writes .pdf next to .tex
    import shutil
    pdf = cfg["tex"].replace(".tex", ".pdf")
    if os.path.exists(pdf):
        shutil.move(pdf, cfg["out"])

    # Pad to a multiple of four pages (perfect binding requires it)
    try:
        from pypdf import PdfReader, PdfWriter
        r = PdfReader(cfg["out"])
        n = len(r.pages)
        pad = (4 - n % 4) % 4
        if pad:
            w = PdfWriter()
            for pg in r.pages:
                w.add_page(pg)
            for _ in range(pad):
                w.add_blank_page(width=r.pages[0].mediabox.width,
                                 height=r.pages[0].mediabox.height)
            # pypdf drops the document info unless it is copied over, which
            # is why Title/Author/Subject were empty in every earlier build.
            if r.metadata:
                w.add_metadata({k: v for k, v in r.metadata.items()
                                if isinstance(v, str)})
            with open(cfg["out"], "wb") as f:
                w.write(f)
            print(f"Padded {n} -> {n+pad} pages (multiple of 4)")
    except Exception as e:
        print(f"padding skipped: {e}")

    print(f"Built {cfg['out']}")
    return True

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "book1"
    ok = build(which)
    sys.exit(0 if ok else 1)
