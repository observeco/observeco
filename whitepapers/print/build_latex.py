#!/usr/bin/env python3
"""Build a print-ready book PDF from markdown via pandoc -> LaTeX -> tectonic.

Uses the memoir class for proper book typesetting: real hyphenation,
justification, float placement, front matter, TOC with page numbers.
"""
import subprocess, sys, os, re

BOOKS = {
    "book1": {
        "md": "/Users/seanfzc/projects/observeco-main/whitepapers/book1-map-manuscript.md",
        "title": "Small Island, Crowded Market",
        "subtitle": "What every Singapore business owner should know about the ground they compete on",
        "author": "Sean Foo, founder of ObserveCo",
        "out": "/tmp/book1-print.pdf",
        "tex": "/tmp/book1.tex",
        "bib": "/Users/seanfzc/projects/observeco-main/whitepapers/print/figures/references-book1",
    },
    "book2": {
        "md": "/Users/seanfzc/projects/observeco-main/whitepapers/print/output/ebook/book2-manuscript-CURRENT.md",
        "title": "How a Small Business Gets Chosen",
        "subtitle": "Lessons from Established Singapore Brands",
        "author": "Sean Foo, founder of ObserveCo",
        "out": "/tmp/book2-print.pdf",
        "tex": "/tmp/book2.tex",
        "bib": "/Users/seanfzc/projects/observeco-main/whitepapers/print/figures/references",
    },
}

TEMPLATE = r"""\documentclass[10pt,twoside,openany]{memoir}

% ── Trim size: Digest 5.5 x 8.5 in (140 x 216 mm) ────────────
\setstocksize{216mm}{140mm}
\settrimmedsize{\stockheight}{\stockwidth}{*}
\setlrmarginsandblock{19mm}{15mm}{*}
\setulmarginsandblock{16mm}{18mm}{*}
\checkandfixthelayout

% ── Fonts ─────────────────────────────────────────────────────
\usepackage{fontspec}
\setmainfont{Charter}[
  Numbers={OldStyle,Proportional},
  SmallCapsFeatures={Letters=SmallCaps},
]
\newfontfamily\cjkfont{Songti SC}
\usepackage{xeCJK}
\setCJKmainfont{Songti SC}
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt

% ── Typography ───────────────────────────────────────────────
\linespread{1.3}   % 10pt on 13pt leading
\setlength{\parindent}{1.5em}
\setlength{\parskip}{0pt}
\frenchspacing
\hyphenpenalty=1000
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
\makeevenhead{book}{\small\scshape TITLE}{}{}
\makeoddhead{book}{}{\small\scshape\rightmark}{}
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
% (no plain pagestyle override — memoir default keeps page numbers everywhere)

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

% ── Rating symbols (TikZ, cannot render as tofu) ─────────────
\usepackage{tikz}
\newcommand{\rhigh}{\tikz[baseline=-0.6ex]\fill (0,0) circle (0.9ex);}
\newcommand{\rmed}{\tikz[baseline=-0.6ex]{\draw (0,0) circle (0.9ex);\fill (0,0) -- (90:0.9ex) arc (90:270:0.9ex) -- cycle;}}
\newcommand{\rlow}{\tikz[baseline=-0.6ex]\draw (0,0) circle (0.9ex);}
\newcommand{\ratingkey}{\par\smallskip\noindent{\footnotesize Key: \rhigh\ high \quad \rmed\ moderate \quad \rlow\ low}}

% ── Bibliography (natbib + chicago.bst, uses bundled bibtex) ──
\usepackage{natbib}
\bibliographystyle{chicago}
\renewcommand{\bibsection}{\chapter*{References}\markright{REFERENCES}}
\appto{\bibsetup}{\raggedright\hyphenpenalty=10000\exhyphenpenalty=10000}

\begin{document}
\sloppy  % prevent overfull hbox by allowing wider spacing

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
  \noindent ISBN: [to be assigned at publication]\par
}
\clearpage

% ── Contents ─────────────────────────────────────────────────
\frontmatter
\setcounter{tocdepth}{0}   % parts + chapters only (2 levels)
% No hyphenation in the TOC
\begingroup
\hyphenpenalty=10000
\exhyphenpenalty=10000
\tableofcontents*
\endgroup

% ── Body ─────────────────────────────────────────────────────
\pagenumbering{arabic}
BODY

\end{document}
"""

def build(book):
    cfg = BOOKS[book]
    # 0. Read manuscript, strip front matter (title, subtitle, author, copyright)
    #    but KEEP "For the reader", "Foreword", "Why I wrote this book".
    #    The LaTeX template handles title page, copyright, and TOC itself.
    md = open(cfg["md"], encoding="utf-8").read()
    part_idx = md.find("# PART ONE")
    if part_idx < 0:
        part_idx = md.find("# PART ONE")
    front_md = md[:part_idx]

    # Extract front matter sections we want to KEEP (For the reader, Foreword, Why)
    keep_headings = ["For the reader", "Foreword", "Why I wrote this book"]
    front_sections = re.split(r'(?=^## )', front_md, flags=re.M)
    kept = [s.strip() for s in front_sections if any(h in s for h in keep_headings)]

    body_md = "\n\n".join(kept) + "\n\n" + md[part_idx:]

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

    # Convert back-matter chapter headings to section headings so they
    # stay on the same page as their content (bibliography, glossary text).
    body = re.sub(r"\\chapter\{References\}", r"\\section*{References}", body)
    body = re.sub(r"\\chapter\{Glossary\}", r"\\section*{Glossary}", body)
    body = re.sub(r"\\chapter\{About the author\}", r"\\section*{About the author}", body)

    # Insert \FloatBarrier before every \chapter and every figure
    # so figures can't drift to wrong locations
    body = re.sub(r"(?m)^(\\chapter\{)", r"\\FloatBarrier\n\1", body)
    body = re.sub(r"(\\includegraphics)", r"\\FloatBarrier\n\1", body)

    # Reduce array stretch for tighter table rows
    body = re.sub(
        r"(\\begin\{longtable\})",
        r"{\\renewcommand{\\arraystretch}{0.9}\1",
        body
    )

    # The one-page self-assessment is a real LaTeX worksheet. Rewrite the
    # relative \input{print/worksheet-one-page} to an absolute path, because
    # tectonic writes the .tex to /tmp and resolves relative inputs there.
    WORKSHEET_ABS = "/Users/seanfzc/projects/observeco-main/whitepapers/print/worksheet-one-page"
    body = body.replace("\\input{print/worksheet-one-page}",
                        "\\input{" + WORKSHEET_ABS + "}")

    # Fix relative image paths -> absolute (tex is written to /tmp)
    VIS_ABS = "/Users/seanfzc/projects/observeco-main/whitepapers/visuals/"
    FIG_ABS = "/Users/seanfzc/projects/observeco-main/whitepapers/print/figures/"
    body = body.replace("visuals/", VIS_ABS)
    body = body.replace("print/figures/", FIG_ABS)

    # Replace \printbibliography with \bibliography{<abs bib>} (natbib path).
    # Each book now points at its own bib: Book 1 = references-book1 (SG gov
    # sources), Book 2 = references (academic positioning works).
    body = body.replace("\\printbibliography[title={References}]",
                        f"\\nocite{{*}}\n\\bibliography{{{cfg['bib']}}}")
    # 2. Assemble full .tex
    tex = TEMPLATE
    # Replace SUBTITLE BEFORE TITLE, else the "TITLE" inside "SUBTITLE" gets clobbered
    tex = tex.replace("SUBTITLE", cfg["subtitle"])
    tex = tex.replace("TITLE", cfg["title"])
    tex = tex.replace("AUTHOR", cfg["author"])
    
    tex = tex.replace("BODY", body)
    with open(cfg["tex"], "w", encoding="utf-8") as f:
        f.write(tex)

    # 3. tectonic -> pdf
    r = subprocess.run(["tectonic", cfg["tex"]], capture_output=True, text=True)
    if r.returncode != 0:
        print("tectonic error:", r.stderr[-800:]); return False
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
