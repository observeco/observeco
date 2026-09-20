#!/usr/bin/env python3
"""
Generate 26 SIMPLE, LOW-TEXT, representative infographics for two Singapore
business books. One concept per figure, generous white space, perfect alignment.

Design system: ObserveCo consulting light-first.
  Paper #f7f6f3 · Insight green #0e6e5c · Ink #1b1f24 · Secondary #4a525c
  Muted #6b737e · Light line #e4e2dc
  Serif display (Georgia) for titles/labels, sans (Helvetica) for small labels.
  A5 width 1748px @ 300dpi, height 1500px.

Layout principle: the diagram FILLS the canvas. Header occupies y 0-210, footer
at y 1460. The diagram area is y 240-1440 (~1200px tall) and x 120-1628
(~1500px wide). Elements are sized to fill this band, not float as a small
sticker in the middle.
"""
import os
import subprocess

OUT = os.path.dirname(os.path.abspath(__file__))

# ── Design tokens ──────────────────────────────────────────────
PAPER      = "#f7f6f3"
SURFACE    = "#ffffff"
INSIGHT    = "#0e6e5c"
INSIGHT_STR= "#0a5447"
INSIGHT_TINT= "#e7f1ee"
INSIGHT_LINE= "#c6dcd4"
INK        = "#1b1f24"
INK2       = "#4a525c"
INK3       = "#6b737e"
LINE       = "#e4e2dc"
LINE_STR   = "#cfccc4"
SEG_STEEL  = "#3d6b9b"
SEG_SLATE  = "#6e8b9e"
SEG_ROSE   = "#a4716f"
SEG_OLIVE  = "#7f8c5a"
SEG_TERRA  = "#b4653a"

SERIF = "Georgia, 'Times New Roman', serif"
SANS  = "Helvetica, Arial, sans-serif"

W = 1748
H = 1500
MARGIN = 120

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def svg_open():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">\n'
            f'<rect width="{W}" height="{H}" fill="{PAPER}"/>\n'
            f'<g transform="translate({W/2},{H/2}) scale(1.06) translate({-W/2},{-H/2})">\n')

def svg_close():
    return '</g>\n</svg>\n'

def text(x, y, s, size, fill=INK, font=SERIF, weight="normal", anchor="start",
         spacing=None, style=""):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp} {style}>{esc(s)}</text>\n')

def rounded(x, y, w, h, r, fill, stroke=None, sw=0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"{st}{d}/>\n'

def circle(cx, cy, r, fill, stroke=None, sw=0):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{st}/>\n'

def line(x1, y1, x2, y2, stroke, sw, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}/>\n'

def arrow_h(x1, y1, x2, y2, stroke, sw, head=16):
    s = line(x1, y1, x2 - head, y2, stroke, sw)
    s += f'<polygon points="{x2},{y2} {x2-head},{y2-head/2} {x2-head},{y2+head/2}" fill="{stroke}"/>\n'
    return s

def arrow_v(x1, y1, x2, y2, stroke, sw, head=16):
    s = line(x1, y1, x2, y2 - head, stroke, sw)
    s += f'<polygon points="{x2},{y2} {x2-head/2},{y2-head} {x2+head/2},{y2-head}" fill="{stroke}"/>\n'
    return s

def header(kicker, title):
    """Minimal header: serif title + accent rule. Kicker (book branding) removed."""
    s = ''
    s += text(MARGIN, 150, title, 56, INK, SERIF, "bold")
    s += f'<rect x="{MARGIN}" y="196" width="64" height="6" fill="{INSIGHT}"/>\n'
    return s

def footer(note):
    """Footer branding removed per review. Returns nothing."""
    return ""

# ═══════════════════════════════════════════════════════════════
# BOOK 1 · "Small Island, Crowded Market"
# ═══════════════════════════════════════════════════════════════

def book1_three_engines():
    """Three filled bars, heights strictly proportional to value per worker.
    The gap (15:5:1) is the point. Labels sit above each bar, clear of the title."""
    s = svg_open()
    s += header("", "Three Engines")
    # True proportional heights: 494 : 150 : 32  (no floor, so the ratio is honest)
    max_h = 900
    baseline = 1300
    values = [("Global", "S$494k", 494, INSIGHT), ("State", "S$150k", 150, SEG_STEEL),
              ("Domestic", "S$32k", 32, SEG_TERRA)]
    bw, gap = 440, 80
    total = 3*bw + 2*gap
    x0 = (W - total) // 2
    for i, (name, val, v, color) in enumerate(values):
        x = x0 + i*(bw + gap)
        h = (v / 494.0) * max_h          # strictly proportional
        top = baseline - h
        # filled bar (solid colour), not an empty outline
        s += rounded(x, top, bw, h, 22, color)
        # value label inside the bar, near the top, white on the fill
        s += text(x + bw/2, top + 40, val, 40, "#ffffff", SERIF, "bold", "middle")
        # name label above the bar, clear of the header (header title ends ~y200)
        s += text(x + bw/2, top - 40, name, 40, INK, SERIF, "bold", "middle")
    s += svg_close()
    return s

def book1_value_per_worker():
    """Three horizontal bars, widths proportional to value per worker."""
    s = svg_open()
    s += header("Book One · The Map", "Value per Worker")
    rows = [("Global", "S$494k", 494, INSIGHT), ("State", "S$150k", 150, SEG_STEEL),
            ("Domestic", "S$32k", 32, SEG_TERRA)]
    bar_h, gap = 200, 110
    top = 360
    max_w = 1200
    label_x = 360
    bar_x = 450
    # tinted panel behind the bars
    s += rounded(bar_x - 40, top - 40, max_w + 200, 3*bar_h + 2*gap + 80, 24, INSIGHT_TINT)
    for i, (name, val, v, color) in enumerate(rows):
        y = top + i*(bar_h + gap)
        w = (v / 494.0) * max_w
        s += text(label_x, y + bar_h/2 + 20, name, 44, INK, SERIF, "bold", "end")
        s += rounded(bar_x, y, w, bar_h, 24, color)
        s += text(bar_x + w + 60, y + bar_h/2 + 20, val, 44, INK2, SERIF, "bold")
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def _icon_fewer_children(cx, cy, color):
    """A small child figure with a minus sign."""
    s = circle(cx, cy - 130, 80, color)                       # head
    s += line(cx, cy - 50, cx, cy + 130, color, 24)           # body
    s += line(cx, cy, cx - 100, cy + 100, color, 24)           # arm
    s += line(cx, cy, cx + 100, cy + 100, color, 24)           # arm
    s += line(cx, cy + 130, cx - 80, cy + 260, color, 24)     # leg
    s += line(cx, cy + 130, cx + 80, cy + 260, color, 24)      # leg
    s += line(cx - 150, cy - 65, cx + 150, cy - 65, color, 24)  # minus
    return s

def _icon_foreign_worker(cx, cy, color):
    """A person with a suitcase."""
    s = circle(cx, cy - 130, 80, color)                        # head
    s += line(cx, cy - 50, cx, cy + 130, color, 24)           # body
    s += line(cx, cy, cx - 100, cy + 100, color, 24)          # arm
    s += line(cx, cy, cx + 100, cy + 100, color, 24)           # arm
    s += line(cx, cy + 130, cx - 80, cy + 260, color, 24)      # leg
    s += line(cx, cy + 130, cx + 80, cy + 260, color, 24)      # leg
    s += rounded(cx + 110, cy + 100, 150, 110, 14, color)      # suitcase
    s += line(cx + 185, cy + 100, cx + 185, cy + 70, color, 18)  # handle
    return s

def _icon_grey(cx, cy, color):
    """An elderly figure with a cane."""
    s = circle(cx, cy - 130, 80, color)                        # head
    s += line(cx, cy - 50, cx, cy + 130, color, 24)            # body
    s += line(cx, cy, cx - 100, cy + 100, color, 24)           # arm
    s += line(cx, cy, cx + 100, cy + 100, color, 24)           # arm
    s += line(cx, cy + 130, cx - 80, cy + 260, color, 24)      # leg
    s += line(cx, cy + 130, cx + 80, cy + 260, color, 24)      # leg
    s += line(cx + 130, cy + 65, cx + 130, cy + 260, color, 24)  # cane
    return s

def _icon_house(cx, cy, color):
    """A simple house."""
    s = rounded(cx - 150, cy + 20, 300, 240, 14, color)         # body
    s += f'<polygon points="{cx},{cy-150} {cx-200},{cy+20} {cx+200},{cy+20}" fill="{color}"/>\n'  # roof
    s += rounded(cx - 45, cy + 110, 90, 150, 10, PAPER)        # door
    return s

def book1_four_waves():
    """Four icons in a row, one word each."""
    s = svg_open()
    s += header("Book One · The Map", "Four Waves")
    items = [("Fewer children", _icon_fewer_children, SEG_STEEL),
             ("Foreign workers", _icon_foreign_worker, SEG_SLATE),
             ("The grey", _icon_grey, SEG_OLIVE),
             ("The house", _icon_house, SEG_TERRA)]
    n = len(items)
    col_w = 380
    gap = (W - 2*MARGIN - n*col_w) / (n - 1)
    cy = 800
    for i, (name, icon, color) in enumerate(items):
        cx = MARGIN + col_w/2 + i*(col_w + gap)
        s += circle(cx, cy - 20, 300, INSIGHT_TINT)   # tinted medallion behind
        s += icon(cx, cy, color)
        s += text(cx, cy + 360, name, 40, INK, SERIF, "bold", "middle")
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_care_economy():
    """One ageing figure + the phrase that changes everything."""
    s = svg_open()
    s += header("Book One · The Map", "The Care Economy")
    s += circle(W/2, 700, 360, INSIGHT_TINT)   # tinted medallion behind
    _icon_grey(W/2, 700, INSIGHT)
    s += text(W/2, 1160, "the wave that changes everything", 56, INSIGHT_STR, SERIF, "italic", "middle")
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_industry_map():
    """A simple 3x2 grid of industry tiles, name only."""
    s = svg_open()
    s += header("Book One · The Map", "The Industry Map")
    tiles = ["Retail", "F&B", "Tuition", "Health", "Finance", "Manufacturing"]
    tw, th, gap = 500, 300, 60
    total = 3*tw + 2*gap
    x0 = (W - total) // 2
    y0 = 380
    for i, name in enumerate(tiles):
        col, row = i % 3, i // 3
        x = x0 + col*(tw + gap)
        y = y0 + row*(th + gap)
        s += rounded(x, y, tw, th, 22, SURFACE, LINE_STR, 2)
        s += text(x + tw/2, y + th/2 + 18, name, 44, INK, SERIF, "bold", "middle")
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_friendly_brutal():
    """Two columns: Friendly vs Brutal, simple labels."""
    s = svg_open()
    s += header("Book One · The Map", "Friendly or Brutal")
    cols = [("Friendly", ["Tuition", "Health", "Professional"], INSIGHT, INSIGHT_TINT, INSIGHT_LINE),
            ("Brutal", ["Retail", "F&B"], SEG_ROSE, "#fbeae7", "#e8c9c5")]
    cw, gap = 700, 90
    total = 2*cw + gap
    x0 = (W - total) // 2
    top = 360
    for i, (title, items, color, tint, lc) in enumerate(cols):
        x = x0 + i*(cw + gap)
        s += rounded(x, top, cw, 130, 22, color)
        s += text(x + cw/2, top + 84, title, 44, "#ffffff", SANS, "bold", "middle", "0.08em")
        chip_h, chip_gap = 170, 55
        cy = top + 220
        for name in items:
            s += rounded(x + 60, cy, cw - 120, chip_h, 20, tint, lc, 2)
            s += text(x + cw/2, cy + chip_h/2 + 18, name, 44, INK, SERIF, "bold", "middle")
            cy += chip_h + chip_gap
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_walls_doors():
    """Two columns: Walls vs Doors, simple labels."""
    s = svg_open()
    s += header("Book One · The Map", "Walls and Doors")
    cols = [("Walls", ["Banks", "Supermarkets", "Delivery", "Telecom"], SEG_ROSE, "#fbeae7", "#e8c9c5"),
            ("Doors", ["Tuition", "Senior care", "Beauty", "Pets"], INSIGHT, INSIGHT_TINT, INSIGHT_LINE)]
    cw, gap = 700, 90
    total = 2*cw + gap
    x0 = (W - total) // 2
    top = 360
    for i, (title, items, color, tint, lc) in enumerate(cols):
        x = x0 + i*(cw + gap)
        s += rounded(x, top, cw, 130, 22, color)
        s += text(x + cw/2, top + 84, title, 44, "#ffffff", SANS, "bold", "middle", "0.08em")
        chip_h, chip_gap = 170, 55
        cy = top + 220
        for name in items:
            s += rounded(x + 60, cy, cw - 120, chip_h, 20, tint, lc, 2)
            s += text(x + cw/2, cy + chip_h/2 + 18, name, 44, INK, SERIF, "bold", "middle")
            cy += chip_h + chip_gap
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_ladder_mind():
    """A simple ladder, top rung highlighted and labeled 'the name recalled'."""
    s = svg_open()
    s += header("Book One · The Map", "The Ladder of the Mind")
    cx = W/2
    rung_w, rung_h, rung_gap = 760, 150, 70
    n = 4
    top_rung_y = 340
    rail_l = cx - rung_w/2 - 55
    rail_r = cx + rung_w/2 + 55
    bottom_y = top_rung_y + (n-1)*(rung_h + rung_gap)
    s += line(rail_l, top_rung_y - 30, rail_l, bottom_y + rung_h + 30, LINE_STR, 14)
    s += line(rail_r, top_rung_y - 30, rail_r, bottom_y + rung_h + 30, LINE_STR, 14)
    for i in range(n):
        y = top_rung_y + i*(rung_h + rung_gap)
        if i == 0:
            s += rounded(cx - rung_w/2, y, rung_w, rung_h, 22, INSIGHT)
            s += text(cx, y + rung_h/2 + 18, "the name recalled", 44, "#ffffff", SERIF, "bold", "middle")
        else:
            s += rounded(cx - rung_w/2, y, rung_w, rung_h, 22, SURFACE, LINE_STR, 2)
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_ai_doors():
    """AI opening a door. Label: one person = a team."""
    s = svg_open()
    s += header("Book One · The Map", "AI Opens Doors")
    cx = W/2
    # tinted panel behind the door
    s += rounded(cx - 200, 330, 400, 640, 24, INSIGHT_TINT)
    # door frame
    s += rounded(cx - 160, 360, 320, 560, 16, SURFACE, LINE_STR, 3)
    # door panel swung open (a parallelogram to the right)
    s += f'<polygon points="{cx+160},{360} {cx+380},{280} {cx+380},{1000} {cx+160},{920}" fill="{INSIGHT_TINT}" stroke="{INSIGHT_LINE}" stroke-width="3"/>\n'
    # arrow showing opening
    s += arrow_h(cx - 70, 640, cx + 280, 640, INSIGHT, 9, head=28)
    s += text(cx, 1160, "one person = a team", 56, INSIGHT_STR, SERIF, "italic", "middle")
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_ai_walls():
    """AI closing a wall. Label: the unpositioned incumbent is exposed."""
    s = svg_open()
    s += header("Book One · The Map", "AI Closes Walls")
    cx = W/2
    # tinted panel behind the wall
    s += rounded(cx - 250, 330, 500, 640, 24, INSIGHT_TINT)
    # wall
    s += rounded(cx - 210, 360, 420, 560, 16, SURFACE, LINE_STR, 3)
    s += text(cx, 560, "THE WALL", 40, SEG_ROSE, SANS, "bold", "middle", "0.1em")
    # crack
    s += line(cx, 360, cx - 55, 500, SEG_ROSE, 7)
    s += line(cx - 55, 500, cx + 40, 610, SEG_ROSE, 7)
    s += line(cx + 40, 610, cx - 20, 720, SEG_ROSE, 7)
    s += line(cx - 20, 720, cx + 10, 920, SEG_ROSE, 7)
    s += text(cx, 1160, "the unpositioned incumbent is exposed", 56, SEG_ROSE, SERIF, "italic", "middle")
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_six_layers():
    """Six stacked horizontal layers, one word each."""
    s = svg_open()
    s += header("Book One · The Map", "Six Layers")
    words = ["Engines", "Waves", "Industries", "Walls", "AI", "Decision"]
    bw, bh, gap = 760, 130, 45
    total = 6*bh + 5*gap
    y0 = 300
    x = (W - bw) // 2
    for i, wd in enumerate(words):
        y = y0 + i*(bh + gap)
        if i == len(words) - 1:
            s += rounded(x, y, bw, bh, 20, INSIGHT)
            s += text(W/2, y + bh/2 + 18, wd, 44, "#ffffff", SERIF, "bold", "middle")
        else:
            s += rounded(x, y, bw, bh, 20, SURFACE, LINE_STR, 2)
            s += text(W/2, y + bh/2 + 18, wd, 44, INK, SERIF, "bold", "middle")
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

def book1_one_page():
    """A simple one-page self-assessment template: a few labeled blank lines."""
    s = svg_open()
    s += header("Book One · The Map", "One Page")
    fields = ["My engine", "My wave", "My industry", "My wall or door", "My word"]
    bw = 1200
    x = (W - bw) // 2
    top = 360
    row_h, gap = 150, 60
    # tinted panel behind the form
    s += rounded(x - 60, top - 40, bw + 120, 5*row_h + 4*gap + 80, 24, INSIGHT_TINT)
    for i, f in enumerate(fields):
        y = top + i*(row_h + gap)
        s += text(x, y + 45, f, 44, INK, SERIF, "bold")
        s += line(x, y + 105, x + bw, y + 105, LINE_STR, 4)
    s += footer("Book One · Small Island, Crowded Market")
    s += svg_close()
    return s

# ═══════════════════════════════════════════════════════════════
# BOOK 2 · "How a Small Business Gets Chosen"
# ═══════════════════════════════════════════════════════════════

def book2_singapore_story():
    """A simple timeline: port war, entrepot, positioning."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "The Singapore Story")
    pts = [("Port war", 0.2), ("Entrepot", 0.5), ("Positioning", 0.8)]
    y = 800
    x0, x1 = 180, W - 180
    # tinted band behind the timeline
    s += rounded(x0 - 60, y - 120, x1 - x0 + 120, 240, 24, INSIGHT_TINT)
    s += line(x0, y, x1, y, LINE_STR, 8)
    for name, f in pts:
        x = x0 + f*(x1 - x0)
        s += circle(x, y, 34, INSIGHT)
        s += text(x, y + 90, name, 44, INK, SERIF, "bold", "middle")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_heritage_brands():
    """A century of owning a word: a long line labeled 'a century'."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "Heritage Brands")
    y = 800
    x0, x1 = 180, W - 180
    # tinted band behind the timeline
    s += rounded(x0 - 60, y - 120, x1 - x0 + 120, 240, 24, INSIGHT_TINT)
    s += line(x0, y, x1, y, LINE_STR, 8)
    # marker at the far end
    s += circle(x1, y, 40, INSIGHT)
    s += text(x1, y - 80, "a century", 52, INSIGHT_STR, SERIF, "bold", "middle")
    s += text(x0, y + 90, "owning a word", 44, INK2, SERIF, "italic", "start")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_category_creators():
    """Creating a new category: a new box appearing. Label below."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "Category Creators")
    # existing boxes
    bw, bh, gap = 300, 300, 60
    total = 3*bw + 2*gap
    x0 = (W - total) // 2
    y = 400
    # tinted panel behind the row
    s += rounded(x0 - 40, y - 40, 4*bw + 3*gap + 80, bh + 80, 24, INSIGHT_TINT)
    for i in range(3):
        x = x0 + i*(bw + gap)
        s += rounded(x, y, bw, bh, 22, SURFACE, LINE_STR, 2)
    # new highlighted box appearing to the right
    nx = x0 + 3*(bw + gap) - gap
    s += rounded(nx, y, bw, bh, 22, INSIGHT)
    s += text(nx + bw/2, y + bh/2 + 18, "NEW", 44, "#ffffff", SANS, "bold", "middle", "0.1em")
    s += text(W/2, y + bh + 130, "create a category, be first in it", 56, INSIGHT_STR, SERIF, "italic", "middle")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_challengers():
    """A challenger attacking a leader. Label: the challenger."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "Challengers")
    # tinted panel behind the scene
    s += rounded(W/2 - 420, 380, 840, 520, 24, INSIGHT_TINT)
    # leader (large circle)
    s += circle(W/2 + 260, 700, 250, SURFACE, LINE_STR, 3)
    s += text(W/2 + 260, 740, "LEADER", 40, INK2, SANS, "bold", "middle", "0.1em")
    # challenger (small triangle/arrow pointing at leader)
    ax = W/2 - 260
    s += f'<polygon points="{ax-130},{700} {ax+70},{580} {ax+70},{820}" fill="{INSIGHT}"/>\n'
    s += text(ax, 1050, "the challenger", 50, INSIGHT_STR, SERIF, "italic", "middle")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_ladder_mind():
    """Same ladder as Book 1: top rung 'the name recalled'."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "The Ladder of the Mind")
    cx = W/2
    rung_w, rung_h, rung_gap = 760, 150, 70
    n = 4
    top_rung_y = 340
    rail_l = cx - rung_w/2 - 55
    rail_r = cx + rung_w/2 + 55
    bottom_y = top_rung_y + (n-1)*(rung_h + rung_gap)
    s += line(rail_l, top_rung_y - 30, rail_l, bottom_y + rung_h + 30, LINE_STR, 14)
    s += line(rail_r, top_rung_y - 30, rail_r, bottom_y + rung_h + 30, LINE_STR, 14)
    for i in range(n):
        y = top_rung_y + i*(rung_h + rung_gap)
        if i == 0:
            s += rounded(cx - rung_w/2, y, rung_w, rung_h, 22, INSIGHT)
            s += text(cx, y + rung_h/2 + 18, "the name recalled", 44, "#ffffff", SERIF, "bold", "middle")
        else:
            s += rounded(cx - rung_w/2, y, rung_w, rung_h, 22, SURFACE, LINE_STR, 2)
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_positioning_statement():
    """Template: For [customer], I am [word], because [proof], so [benefit]."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "The Positioning Statement")
    fields = [("FOR", "[customer]"), ("I AM", "[word]"), ("BECAUSE", "[proof]"), ("SO", "[benefit]")]
    bw = 1300
    x = (W - bw) // 2
    top = 360
    row_h, gap = 160, 60
    # tinted panel behind the form
    s += rounded(x - 40, top - 40, bw + 80, 4*row_h + 3*gap + 80, 24, INSIGHT_TINT)
    for i, (label, ph) in enumerate(fields):
        y = top + i*(row_h + gap)
        s += rounded(x, y, 280, row_h, 18, INSIGHT)
        s += text(x + 140, y + row_h/2 + 18, label, 40, "#ffffff", SANS, "bold", "middle", "0.1em")
        s += text(x + 340, y + row_h/2 + 18, ph, 44, INK2, SERIF, "italic")
        s += line(x + 340, y + row_h - 32, x + bw, y + row_h - 32, LINE_STR, 4)
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_five_step():
    """Five circles in a row, one word each."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "Five Steps")
    steps = [("1", "Know"), ("2", "Map"), ("3", "Evaluate"), ("4", "Find"), ("5", "Decide")]
    n = len(steps)
    r = 130
    gap = 80
    total = n*2*r + (n-1)*gap
    x0 = (W - total) // 2 + r
    y = 700
    # tinted panel behind the row
    s += rounded(x0 - r - 40, y - r - 40, total + 80, 2*r + 80, 24, INSIGHT_TINT)
    for i, (num, wd) in enumerate(steps):
        cx = x0 + i*(2*r + gap)
        s += circle(cx, y, r, SURFACE, LINE_STR, 3)
        s += text(cx, y - 30, num, 60, INK3, SERIF, "bold", "middle")
        s += text(cx, y + 60, wd, 44, INK, SERIF, "bold", "middle")
        if i < n - 1:
            s += arrow_h(cx + r + 8, y, cx + r + gap - 8, y, INK3, 6, head=24)
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_four_postures():
    """A simple 2x2 quadrant: one word + one short phrase each."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "Four Postures")
    cells = [("Defence", "the leader", INSIGHT, INSIGHT_TINT, INSIGHT_LINE),
             ("Offence", "the challenger", SEG_STEEL, "#e8f0fb", "#c3d4e8"),
             ("Flanking", "the creator", SEG_OLIVE, "#f0f2e8", "#d3d8bd"),
             ("Guerrilla", "small & niche", SEG_TERRA, "#fbeae7", "#e8c9c5")]
    cw, ch, gap = 720, 400, 60
    total = 2*cw + gap
    x0 = (W - total) // 2
    y0 = 360
    for i, (name, phrase, color, tint, lc) in enumerate(cells):
        col, row = i % 2, i // 2
        x = x0 + col*(cw + gap)
        y = y0 + row*(ch + gap)
        s += rounded(x, y, cw, ch, 22, SURFACE, LINE_STR, 2)
        s += rounded(x, y, cw, 18, 9, color)
        s += text(x + cw/2, y + 160, name, 56, INK, SERIF, "bold", "middle")
        s += text(x + cw/2, y + 250, phrase, 38, INK2, SERIF, "italic", "middle")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_word():
    """A single word in the customer's mind: a head with one word."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "The Word")
    cx = W/2
    # tinted medallion behind the head
    s += circle(cx, 700, 360, INSIGHT_TINT)
    # head
    s += circle(cx, 700, 260, SURFACE, LINE_STR, 3)
    s += text(cx, 740, "your", 58, INK, SERIF, "bold", "middle")
    s += text(cx, 830, "word", 58, INSIGHT, SERIF, "bold", "middle")
    s += text(cx, 1120, "the word in their mind", 48, INK2, SERIF, "italic", "middle")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_price_vs_word():
    """A price tag vs a word. Label: price cannot buy a word."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "Price vs Word")
    # tinted panel behind the scene
    s += rounded(W/2 - 420, 420, 840, 520, 24, INSIGHT_TINT)
    # price tag (left)
    px = W/2 - 320
    s += f'<polygon points="{px},{540} {px+300},{540} {px+300},{840} {px+150},{940} {px},{840}" fill="{SURFACE}" stroke="{LINE_STR}" stroke-width="3"/>\n'
    s += text(px + 150, 760, "S$", 64, INK2, SERIF, "bold", "middle")
    # word bubble (right)
    bx = W/2 + 320
    s += circle(bx, 720, 150, INSIGHT)
    s += text(bx, 760, "word", 52, "#ffffff", SERIF, "bold", "middle")
    s += text(W/2, 1160, "price cannot buy a word", 56, INSIGHT_STR, SERIF, "italic", "middle")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_referral():
    """A referral loop: customer → friend → customer."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "The Referral Loop")
    cx, cy = W/2, 780
    r = 150
    # tinted panel behind the triangle
    s += rounded(cx - 360, cy - 320, 720, 560, 24, INSIGHT_TINT)
    # three nodes in a triangle
    nodes = [(cx, cy - 260), (cx - 300, cy + 170), (cx + 300, cy + 170)]
    labels = ["Customer", "Friend", "Customer"]
    for (nx, ny), lab in zip(nodes, labels):
        s += circle(nx, ny, r, SURFACE, LINE_STR, 3)
        s += text(nx, ny + 18, lab, 40, INK, SERIF, "bold", "middle")
    # arrows around the loop (clockwise): top->right, right->left, left->top
    s += arrow_h(cx + r + 8, cy - 260, cx + 300 - r - 8, cy - 260, INK3, 7, head=26)
    s += arrow_h(cx + 300 - r - 8, cy + 170, cx - 300 + r + 8, cy + 170, INK3, 7, head=26)
    # diagonal arrow from left node up to top node
    xa, ya = cx - 300 + r + 8, cy + 170
    xb, yb = cx - r - 8, cy - 260
    s += line(xa, ya, xb, yb, INK3, 7)
    s += f'<polygon points="{xb},{yb} {xb-16},{yb+9} {xb-9},{yb+22}" fill="{INK3}"/>\n'
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_process():
    """A simple 5-box process flow, one word each."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "The Process")
    steps = ["Set", "Map", "Weigh", "Slot", "Decide"]
    n = len(steps)
    bw, bh, gap = 270, 240, 45
    total = n*bw + (n-1)*gap
    x0 = (W - total) // 2
    y = 620
    # tinted panel behind the row
    s += rounded(x0 - 40, y - 40, total + 80, bh + 80, 24, INSIGHT_TINT)
    for i, wd in enumerate(steps):
        x = x0 + i*(bw + gap)
        s += rounded(x, y, bw, bh, 22, SURFACE, LINE_STR, 2)
        s += text(x + bw/2, y + bh/2 + 18, wd, 44, INK, SERIF, "bold", "middle")
        if i < n - 1:
            s += arrow_h(x + bw + 8, y + bh/2, x + bw + gap - 8, y + bh/2, INK3, 7, head=26)
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_one_page():
    """A simple one-page position template: a few labeled blanks."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "One Page")
    fields = ["My customer", "My word", "My proof", "My benefit"]
    bw = 1200
    x = (W - bw) // 2
    top = 420
    row_h, gap = 160, 70
    # tinted panel behind the form
    s += rounded(x - 60, top - 40, bw + 120, 4*row_h + 3*gap + 80, 24, INSIGHT_TINT)
    for i, f in enumerate(fields):
        y = top + i*(row_h + gap)
        s += text(x, y + 45, f, 44, INK, SERIF, "bold")
        s += line(x, y + 110, x + bw, y + 110, LINE_STR, 4)
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

def book2_where_fails():
    """Three icons: where positioning fails. One word each."""
    s = svg_open()
    s += header("Book Two · How a Small Business Gets Chosen", "Where It Fails")
    # icon 1: broken foundation (cracked base)
    # icon 2: pure commodity (plain box)
    # icon 3: can't hold one word (word slipping)
    items = [("Foundation", SEG_ROSE), ("Commodity", SEG_OLIVE), ("One word", SEG_TERRA)]
    n = 3
    col_w = 420
    gap = (W - 2*MARGIN - n*col_w) / (n - 1)
    cy = 700
    for i, (name, color) in enumerate(items):
        cx = MARGIN + col_w/2 + i*(col_w + gap)
        s += circle(cx, cy - 20, 250, INSIGHT_TINT)   # tinted medallion behind
        if i == 0:
            # cracked base
            s += rounded(cx - 130, cy - 70, 260, 180, 14, SURFACE, LINE_STR, 3)
            s += line(cx, cy - 70, cx - 35, cy + 25, color, 7)
            s += line(cx - 35, cy + 25, cx + 18, cy + 110, color, 7)
        elif i == 1:
            # plain commodity box
            s += rounded(cx - 130, cy - 70, 260, 180, 14, SURFACE, LINE_STR, 3)
            s += text(cx, cy + 25, "S$", 56, INK2, SERIF, "bold", "middle")
        else:
            # word slipping (a word falling out of a head)
            s += circle(cx, cy - 60, 110, SURFACE, LINE_STR, 3)
            s += text(cx, cy - 35, "word", 40, INK2, SERIF, "italic", "middle")
            s += text(cx, cy + 70, "word", 40, INK3, SERIF, "italic", "middle")
        s += text(cx, cy + 210, name, 40, INK, SERIF, "bold", "middle")
    s += footer("Book Two · How a Small Business Gets Chosen")
    s += svg_close()
    return s

# ═══════════════════════════════════════════════════════════════
FILES = {
    "book1-three-engines": book1_three_engines,
    "book1-value-per-worker": book1_value_per_worker,
    "book1-four-waves": book1_four_waves,
    "book1-care-economy": book1_care_economy,
    "book1-industry-map": book1_industry_map,
    "book1-friendly-brutal": book1_friendly_brutal,
    "book1-walls-doors": book1_walls_doors,
    "book1-ladder-mind": book1_ladder_mind,
    "book1-ai-doors": book1_ai_doors,
    "book1-ai-walls": book1_ai_walls,
    "book1-six-layers": book1_six_layers,
    "book1-one-page": book1_one_page,
    "book2-singapore-story": book2_singapore_story,
    "book2-heritage-brands": book2_heritage_brands,
    "book2-category-creators": book2_category_creators,
    "book2-challengers": book2_challengers,
    "book2-ladder-mind": book2_ladder_mind,
    "book2-positioning-statement": book2_positioning_statement,
    "book2-five-step": book2_five_step,
    "book2-four-postures": book2_four_postures,
    "book2-word": book2_word,
    "book2-price-vs-word": book2_price_vs_word,
    "book2-referral": book2_referral,
    "book2-process": book2_process,
    "book2-one-page": book2_one_page,
    "book2-where-fails": book2_where_fails,
}

def render(name, fn):
    svg = fn()
    svg_path = os.path.join(OUT, name + ".svg")
    png_path = os.path.join(OUT, name + ".png")
    with open(svg_path, "w") as f:
        f.write(svg)
    subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), svg_path, "-o", png_path],
                   check=True)
    return png_path

if __name__ == "__main__":
    for name, fn in FILES.items():
        p = render(name, fn)
        print("wrote", p)
