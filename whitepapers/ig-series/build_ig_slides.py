#!/usr/bin/env python3
"""
IG carousel slide generator — ObserveCo Book 1 series.

Renders portrait-native 1080x1350 HTML slides from the insight-visuals card
content. One shared CSS block guarantees token parity across every slide.

Usage:  python3 build_ig_slides.py [post_number ...]   (default: all posts)
Output: whitepapers/ig-series/postNN-slideNN-slug.html
"""
import os
import sys

OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- design system
TOKENS = """
  --canvas:#f7f6f3; --surface:#ffffff; --surface-muted:#efeee9;
  --ink:#1b1f24; --ink-2:#4a525c; --ink-3:#6b737e;
  --accent:#0e6e5c; --accent-strong:#0a5447; --accent-tint:#e7f1ee; --accent-line:#c6dcd4;
  --critical:#b42318; --critical-tint:#fbeae7;
  --warning:#9a6500; --warning-tint:#fbf0d8;
  --line:#e4e2dc;
  --font-display:'Playfair Display',Georgia,serif;
  --font-body:'Inter',system-ui,sans-serif;
"""

CSS = f"""
:root {{{TOKENS}}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:1080px; height:1350px; overflow:hidden; }}
body {{ background:var(--canvas); color:var(--ink); font-family:var(--font-body); }}

.slide {{ width:1080px; height:1350px; background:var(--canvas); display:flex;
          flex-direction:column; padding:88px 96px 72px; position:relative; }}

/* ---- furniture ---- */
.slide-head {{ display:flex; justify-content:space-between; align-items:baseline;
               padding-bottom:22px; border-bottom:1px solid var(--line); margin-bottom:52px; }}
.overline {{ font-size:17px; font-weight:600; text-transform:uppercase;
             letter-spacing:.14em; color:var(--accent); line-height:1.3; }}
.counter {{ font-size:16px; font-weight:600; color:var(--ink-3); letter-spacing:.06em; white-space:nowrap; }}

.slide-body {{ flex:1; display:flex; flex-direction:column; justify-content:center; }}
.slide-foot {{ display:flex; justify-content:space-between; align-items:center;
               padding-top:24px; border-top:1px solid var(--line); margin-top:44px; }}
.brand {{ display:flex; align-items:baseline; gap:10px; }}
.brand .word {{ font-family:var(--font-display); font-size:21px; font-weight:700;
                letter-spacing:-.02em; color:var(--ink); }}
.brand .word .dot {{ color:var(--accent); }}
.brand .loc {{ font-size:14px; color:var(--ink-3); }}
.source {{ font-size:14px; color:var(--ink-3); text-align:right; max-width:520px; line-height:1.4; }}

/* ---- logo-hero opening slide (post 02) ---- */
/* The logo is the biggest real estate on the slide; the positioning line sits
   directly beneath it, then the single claim. On a cold scroll the reader must
   learn WHO this is before WHAT it sells. */
.logo-hero {{ display:flex; flex-direction:column; align-items:center; justify-content:center;
              text-align:center; gap:0; }}
.logo-hero .lg {{ font-family:var(--font-display); font-weight:700; letter-spacing:-.035em;
                  font-size:132px; line-height:1; color:var(--ink); margin-bottom:24px; }}
.logo-hero .lg .dot {{ color:var(--accent); }}
.logo-hero .rule {{ width:132px; height:5px; background:var(--accent); border-radius:3px;
                    margin-bottom:30px; }}
.logo-hero .positioning {{ font-family:var(--font-sans); font-size:30px; font-weight:600;
                           color:var(--ink); line-height:1.4; max-width:800px; }}
.logo-hero .claim {{ font-size:24px; color:var(--ink-2); line-height:1.6; max-width:800px;
                     margin-top:22px; }}
.logo-hero .claim strong {{ color:var(--accent-strong); }}

/* ---- type ---- */
h1.cover {{ font-family:var(--font-display); font-size:76px; font-weight:800;
            line-height:1.05; letter-spacing:-.015em; }}
h2.stat-head {{ font-family:var(--font-display); font-size:54px; font-weight:800;
                line-height:1.1; letter-spacing:-.01em; margin-bottom:40px; }}
.lede {{ font-size:26px; color:var(--ink-2); line-height:1.5; margin-top:32px; }}
.hero {{ font-family:var(--font-display); font-size:132px; font-weight:800;
         line-height:0.95; letter-spacing:-.03em; color:var(--accent-strong); }}
.hero-unit {{ font-size:22px; font-weight:500; color:var(--ink-3); margin-top:16px; }}
.hero-context {{ font-size:24px; color:var(--ink-2); line-height:1.55; margin-top:28px;
                 padding-top:28px; border-top:1px solid var(--line); }}

/* ---- comparison columns ---- */
.cols {{ display:flex; gap:22px; align-items:stretch; }}
.col {{ flex:1; background:var(--surface); border:1px solid var(--line); border-radius:14px;
        padding:34px 26px 30px; position:relative; overflow:hidden; }}
.col::before {{ content:''; position:absolute; top:0; left:0; right:0; height:6px; }}
.col.rank1::before {{ background:var(--accent-strong); }}
.col.rank2::before {{ background:var(--accent); }}
.col.rank3::before {{ background:var(--warning); }}
.col-label {{ font-size:15px; font-weight:700; text-transform:uppercase; letter-spacing:.1em;
              margin-bottom:22px; }}
.col.rank1 .col-label {{ color:var(--accent-strong); }}
.col.rank2 .col-label {{ color:var(--accent); }}
.col.rank3 .col-label {{ color:var(--warning); }}
.col-value {{ font-family:var(--font-display); font-size:56px; font-weight:800;
              line-height:1; letter-spacing:-.02em; }}
.col-unit {{ font-size:16px; color:var(--ink-3); margin-top:10px; line-height:1.4;
             padding-bottom:22px; border-bottom:1px solid var(--line); }}
.col-desc {{ font-size:18px; color:var(--ink-2); line-height:1.5; padding-top:22px; }}

/* ---- horizontal bars ---- */
.bars {{ display:flex; flex-direction:column; gap:20px; }}
.bar-row {{ display:grid; grid-template-columns:230px 1fr 130px; align-items:center; gap:24px; }}
.bar-name {{ font-size:20px; color:var(--ink-2); text-align:right; line-height:1.25; }}
.bar-track {{ height:34px; background:var(--surface-muted); border-radius:7px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:7px; }}
.bar-fill.rank1 {{ background:var(--accent-strong); }}
.bar-fill.rank2 {{ background:var(--accent); }}
.bar-fill.rank3 {{ background:var(--warning); }}
.bar-val {{ font-size:22px; font-weight:700; color:var(--ink); font-variant-numeric:tabular-nums; }}

/* ---- payoff panel ---- */
.payoff {{ background:var(--accent-tint); border:1px solid var(--accent-line);
           border-radius:16px; padding:52px 54px; }}
.payoff p {{ font-size:28px; color:var(--ink-2); line-height:1.6; }}
.payoff strong {{ color:var(--accent-strong); font-weight:700; }}
.cta {{ margin-top:52px; display:flex; align-items:center; gap:18px; }}
.cta .rule {{ flex:1; height:1px; background:var(--accent-line); }}
.cta .txt {{ font-size:22px; font-weight:700; color:var(--accent-strong); letter-spacing:.02em; }}

.cols.text .col-value {{ font-size:40px; letter-spacing:-.01em; }}
/* neutral variant — equal-weight options, no ranking implied */
.cols.neutral .col::before {{ background:var(--line); }}
.cols.neutral .col-label {{ color:var(--ink-3); }}

/* ---- ledger (brand -> word -> jump; each row its own comparison) ---- */
.ledger {{ display:flex; flex-direction:column; }}
.ledger-row {{ display:grid; grid-template-columns:186px 1fr 258px; gap:20px;
               align-items:baseline; padding:17px 0; border-bottom:1px solid var(--line); }}
.ledger-row:last-child {{ border-bottom:none; }}
.l-brand {{ font-size:22px; font-weight:700; color:var(--ink); }}
.l-word {{ font-size:20px; color:var(--accent-strong); font-style:italic; line-height:1.3; }}
.l-jump {{ font-size:20px; font-weight:700; color:var(--ink); text-align:right;
           font-variant-numeric:tabular-nums; white-space:nowrap; }}

/* ---- numbered process steps (added post 02 — no token changes) ---- */
.steps {{ display:flex; flex-direction:column; gap:24px; }}
.step {{ display:grid; grid-template-columns:64px 1fr; gap:26px; align-items:start;
         background:var(--surface); border:1px solid var(--line); border-radius:14px;
         padding:24px 30px; position:relative; overflow:hidden; }}
.step::before {{ content:''; position:absolute; left:0; top:0; bottom:0; width:6px;
                 background:var(--accent-strong); }}
.step-no {{ font-family:var(--font-display); font-size:42px; font-weight:800; color:var(--accent);
            line-height:1; letter-spacing:-.02em; }}
.step-name {{ font-size:26px; font-weight:700; color:var(--ink); margin-bottom:6px; }}
.step-desc {{ font-size:19px; color:var(--ink-2); line-height:1.5; }}

/* ---- question grid — the four questions a founder cannot answer ---- */
.qgrid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.q {{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
      padding:22px 24px 22px 52px; font-size:22px; color:var(--ink); line-height:1.35;
      position:relative; }}
.q::before {{ content:''; position:absolute; left:24px; top:26px; width:9px; height:9px;
              border-radius:50%; background:var(--accent); }}

/* ---- "not" chips — what the answer is NOT ---- */
.nots {{ display:flex; flex-direction:column; gap:11px; margin:24px 0; }}
.nots span {{ font-size:20px; color:var(--ink-2); background:var(--surface-muted);
              border:1px solid var(--line); border-radius:999px; padding:11px 24px;
              align-self:flex-start; }}
.nots span::before {{ content:'\\00d7'; color:var(--warning); font-weight:800; margin-right:11px; }}

/* ---- mission line (the offer, stated as a belief) ---- */
.mission {{ margin-top:30px; font-family:var(--font-display); font-size:34px; font-weight:800;
            color:var(--accent-strong); line-height:1.22; letter-spacing:-.015em; }}

/* ---- book cover panels (posts OPEN with the real shipped cover) ---- */
/* Front cover shown full-bleed on a bare slide: the cover IS the hook. */
.cover-full {{ display:flex; flex-direction:column; align-items:center; justify-content:center;
               gap:34px; height:100%; }}
.cover-full img {{ height:960px; width:auto; border-radius:6px;
                   box-shadow:0 20px 48px rgba(27,31,36,.24), 0 2px 6px rgba(27,31,36,.10); }}
.cover-full .cap {{ font-size:23px; color:var(--ink-2); text-align:center; line-height:1.5;
                    max-width:820px; }}
.cover-full .cap strong {{ color:var(--accent-strong); }}

/* Back cover as a small proof artifact beside readable book context. */
.artifact {{ display:flex; gap:44px; align-items:center; }}
.artifact img {{ height:420px; width:auto; border-radius:5px; flex:none;
                 box-shadow:0 14px 32px rgba(27,31,36,.20), 0 1px 4px rgba(27,31,36,.10); }}
.artifact-body {{ flex:1; }}
.artifact-body .kicker {{ font-size:15px; font-weight:700; text-transform:uppercase;
                          letter-spacing:.14em; color:var(--accent); margin-bottom:18px; }}
.artifact-body p {{ font-size:24px; color:var(--ink-2); line-height:1.6; }}
.artifact-body p + p {{ margin-top:22px; }}
.artifact-body strong {{ color:var(--accent-strong); }}

/* ---- swipe cue ---- */
.swipe {{ position:absolute; right:96px; bottom:150px; display:flex; align-items:center;
          gap:12px; font-size:18px; font-weight:600; color:var(--ink-3); }}
.swipe .arrow {{ font-size:26px; color:var(--accent); }}
"""

"""ObserveCo logo — text-only wordmark with the teal period.

The old pulse/heartbeat icon was RETIRED with the consulting pivot and is banned by
`assets/brand/LOGO_STYLE_GUIDE.md` ("Do not reintroduce the old pulse/heartbeat
icon"). The brand is typographic. `verify_gates.py` enforces this.
Source of truth: the live site header (`<a class="nav-brand">ObserveCo<span class="dot">.</span></a>`).
"""
WORDMARK = ('<span class="word">ObserveCo<span class="dot">.</span></span>')

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?'
         'family=Inter:wght@400;500;600;700;800&'
         'family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet">')


def page(title, overline, counter, body, source, swipe=None, series="/ Singapore",
         bare=False):
    """series: footer wordmark series tag.

    bare: full-bleed mode for the cover slide — no header rule, no footer chrome.
    The cover artwork is the hook; slide furniture around it just adds noise.
    """
    cue = '<div class="swipe"><span>Swipe</span><span class="arrow">&rarr;</span></div>' if swipe else ''

    if bare:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
{FONTS}
<style>{CSS}
.slide.bare {{ padding:96px; }}
.slide.bare .slide-body {{ justify-content:center; }}
</style>
</head>
<body>
<div class="slide bare">
  <div class="slide-body">
{body}
  </div>
  {cue}
</div>
</body>
</html>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
{FONTS}
<style>{CSS}</style>
</head>
<body>
<div class="slide">
  <div class="slide-head">
    <div class="overline">{overline}</div>
    <div class="counter">{counter}</div>
  </div>
  <div class="slide-body">
{body}
  </div>
  <div class="slide-foot">
    <div class="brand">{WORDMARK}<span class="loc">{series}</span></div>
    <div class="source">{source}</div>
  </div>
  {cue}
</div>
</body>
</html>
"""


# =============================================================== POST 1
# Source card: 03-three-engines.html  (Part One, Ch 1)
# Values: S$494K global / S$116K govt / S$32K domestic (SingStat 2025)

P1_OVER = "Small Island, Crowded Market &middot; Part One, Ch 1"
P1_SRC = "Source: SingStat, value added per worker by industry, 2025"
BOOK = "Small Island, Crowded Market"

P1 = [
    ("cover-front", dict(
        overline="", counter="", source="", series="/ Singapore", swipe=True, bare=True,
        body='<div class="cover-full">'
             '<img src="assets/cover-front.png" alt="Small Island, Crowded Market — book cover">'
             '<p class="cap">This series is drawn from the book <strong>Small Island, '
             'Crowded Market</strong> &mdash; a study of the ground every Singapore small '
             'business competes on. Swipe for one of its core findings.</p>'
             '</div>',
    )),
    ("stat", dict(
        overline=P1_OVER, counter="02 / 06", source=P1_SRC,
        body='<h2 class="stat-head">The global worker is worth 15&times; the domestic one.</h2>'
             '<div class="hero">S$494K</div>'
             '<div class="hero-unit">value created per worker, per year</div>'
             '<p class="hero-context">Foreign multinationals selling to the world. '
             'Capital-intensive, export-oriented, backed by global demand and decades of brand trust. '
             'The domestic layer creates <strong>S$32K</strong>.</p>',
    )),
    ("cols", dict(
        overline=P1_OVER, counter="03 / 06", source=P1_SRC,
        body='<h2 class="stat-head">Same island. Three economies.</h2>'
             '<div class="cols">'
             '<div class="col rank1"><div class="col-label">Global Engine</div>'
             '<div class="col-value">S$494K</div><div class="col-unit">per worker</div>'
             '<div class="col-desc">Foreign MNCs selling to the world. Wholesale trade, finance, manufacturing.</div></div>'
             '<div class="col rank2"><div class="col-label">Govt Engine</div>'
             '<div class="col-value">S$116K</div><div class="col-unit">per worker</div>'
             '<div class="col-desc">The state&rsquo;s own workforce. No market, no competitor.</div></div>'
             '<div class="col rank3"><div class="col-label">Domestic Layer</div>'
             '<div class="col-value">S$32K</div><div class="col-unit">per worker</div>'
             '<div class="col-desc">Local shops, clinics, services. Capped at 5.9M people.</div></div>'
             '</div>',
    )),
    ("bars", dict(
        overline=P1_OVER, counter="04 / 06", source=P1_SRC,
        body='<h2 class="stat-head">The ladder, industry by industry.</h2>'
             '<div class="bars">'
             + "".join(
                 f'<div class="bar-row"><div class="bar-name">{n}</div>'
                 f'<div class="bar-track"><div class="bar-fill {c}" style="width:{w:.1f}%"></div></div>'
                 f'<div class="bar-val">{v}</div></div>'
                 for n, v, w, c in [
                     ("Wholesale Trade", "S$494K", 100, "rank1"),
                     ("Finance", "S$436K", 88.3, "rank1"),
                     ("Manufacturing", "S$282K", 57.1, "rank1"),
                     ("Education", "S$150K", 30.4, "rank2"),
                     ("Public Admin", "S$116K", 23.5, "rank2"),
                     ("Retail", "S$58K", 11.7, "rank3"),
                     ("Food &amp; Beverage", "S$32K", 6.5, "rank3"),
                 ])
             + '</div>',
    )),
    ("payoff", dict(
        overline=P1_OVER, counter="05 / 06", source=P1_SRC,
        body='<h2 class="stat-head">The gap is not about effort.</h2>'
             '<div class="payoff"><p>The global worker is not more hardworking &mdash; they are more '
             '<strong>leveraged</strong>. Three things stand behind them: the world&rsquo;s market, capital, '
             'and a brand people trust. The domestic worker has none of these. '
             '<strong>The brand is the one asset a small business can build too.</strong></p></div>'
             '<div class="cta"><div class="rule"></div><div class="txt">Which engine is your business in?</div></div>',
    )),
    ("artifact", dict(
        overline=P1_OVER, counter="06 / 06", source="", series="/ Singapore",
        body='<div class="artifact">'
             '<img src="assets/cover-back.png" alt="Back cover of Small Island, Crowded Market">'
             '<div class="artifact-body">'
             '<div class="kicker">From the book</div>'
             '<p>This finding is one of 64 in <strong>Small Island, Crowded Market</strong> &mdash; '
             'a study of the ground every Singapore small business competes on, and the industries '
             'a small business can actually win in.</p>'
             '<p>Every figure is confidence-labelled and sourced.</p>'
             '</div></div>',
    )),
]


# =============================================================== POST 2
# Source: live homepage https://observeco.com (verified 2026-09-19 via curl)
#   h1 "Differentiation strategy consultancy for Singapore small businesses"
#   S$500 one-shot · the four steps · the six brand cases · the S$500-vs-cost table

P2_OVER = "What is ObserveCo? &middot; Singapore"
P2_SRC = "Source: observeco.com &middot; Singapore registrations 2025"

P2 = [
    # OPENING SLIDE: the LOGO is the hero, not the book.
    # A cold IG reader has never heard of ObserveCo and has never heard of the book.
    # Slide 1 must answer "who is this?" before "what do they sell?". The book is
    # evidence, and evidence belongs later — it now closes the carousel only.
    ("logo-hero", dict(
        overline="", counter="", source="", series="/ Singapore", bare=True,
        body='<div class="logo-hero">'
             '<div class="lg">ObserveCo<span class="dot">.</span></div>'
             '<div class="rule"></div>'
             '<div class="positioning">Differentiation strategy consultancy for '
             '<strong>Singapore small businesses</strong></div>'
             '<div class="claim">We provide the clarity as to why your customer '
             'hasn&rsquo;t chosen you &mdash; because we observe what you can&rsquo;t '
             'see from the inside.</div>'
             '</div>',
    )),
    ("cover", dict(
        overline=P2_OVER, counter="02 / 09", source="observeco.com",
        series="/ Singapore",
        body='<h1 class="cover">You can&rsquo;t see why<br>customers don&rsquo;t<br>choose you.</h1>'
             '<p class="lede">There are many reasons a business fails to connect: an inability '
             'to explain the product, a credibility gap, a price that doesn&rsquo;t signal the '
             'value, selling to the wrong customers. <strong>ObserveCo solves the root '
             'cause.</strong></p>',
    )),
    ("stat", dict(
        overline=P2_OVER, counter="03 / 09", source=P2_SRC, series="/ Singapore",
        body='<h2 class="stat-head">Big companies have consultants. Small businesses have to '
             'figure it out themselves.</h2>'
             '<div class="hero">213</div>'
             '<div class="hero-unit">new businesses register in Singapore every day</div>'
             '<p class="hero-context">One every 7 minutes &mdash; and <strong>half don&rsquo;t '
             'survive five years</strong>. 50% of SMEs now name competition as their top concern, '
             'up from 39% a year earlier. They are not short of effort. They are short of clarity.</p>',
    )),
    ("qgrid", dict(
        overline=P2_OVER, counter="04 / 09", source="observeco.com", series="/ Singapore",
        body='<h2 class="stat-head">The businesses still finding their feet need it most.</h2>'
             '<div class="qgrid">'
             '<div class="q">Who are my real customers?</div>'
             '<div class="q">Why should they choose me?</div>'
             '<div class="q">What makes me different?</div>'
             '<div class="q">Why aren&rsquo;t people buying?</div>'
             '</div>'
             '<p class="hero-context" style="margin-top:30px;font-size:23px">'
             'And that&rsquo;s not fair &mdash; because traditional strategy consulting was '
             'never really built for them.</p>',
    )),
    ("steps", dict(
        overline=P2_OVER, counter="05 / 09", source="observeco.com", series="/ Singapore",
        body='<h2 class="stat-head">That&rsquo;s where ObserveCo comes in.</h2>'
             '<div class="steps">'
             '<div class="step"><div class="step-no">01</div><div>'
             '<div class="step-name">Observe</div><div class="step-desc">'
             'We study your market, your customers and your competitors.</div></div></div>'
             '<div class="step"><div class="step-no">02</div><div>'
             '<div class="step-name">Uncover</div><div class="step-desc">'
             'We identify the patterns and gaps you can&rsquo;t see from the inside.</div></div></div>'
             '<div class="step"><div class="step-no">03</div><div>'
             '<div class="step-name">Differentiate</div><div class="step-desc">'
             'We find the space your business can credibly own.</div></div></div>'
             '<div class="step"><div class="step-no">04</div><div>'
             '<div class="step-name">Be Chosen</div><div class="step-desc">'
             'We turn it into a clear reason for customers to choose you.</div></div></div>'
             '</div>',
    )),
    ("payoff", dict(
        overline=P2_OVER, counter="06 / 09", source="observeco.com", series="/ Singapore",
        body='<h2 class="stat-head">We find the reason people would actually choose you.</h2>'
             '<div class="payoff"><p>Not more jargon. Not a 100-page strategy deck. '
             'Not advice based on assumptions. <strong>Just a clear understanding of what makes '
             'your business matter &mdash; and how to make customers see it too.</strong></p></div>',
    )),
    # NOTE: each row is its own before/after, so the "word" is highlighted and the
    # number is an outcome — deliberately NOT a bar chart (no false proportionality).
    ("ledger", dict(
        overline=P2_OVER, counter="07 / 09", source="observeco.com", series="/ Singapore",
        body='<h2 class="stat-head">Own one word. Revenue follows.</h2>'
             '<div class="ledger">'
             + "".join(
                 f'<div class="ledger-row"><div class="l-brand">{b}</div>'
                 f'<div class="l-word">{w}</div>'
                 f'<div class="l-jump">{j}</div></div>'
                 for b, w, j in [
                     ("Airbnb", "&ldquo;Belong anywhere.&rdquo;", "$0.9B &rarr; $4.8B"),
                     ("Avis", "&ldquo;We&rsquo;re only No. 2, so we try harder.&rdquo;", "10% &rarr; 29% share"),
                     ("Domino&rsquo;s", "&ldquo;30 minutes or less, or it&rsquo;s free.&rdquo;", "1 &rarr; 5,000+ stores"),
                     ("Volvo", "&ldquo;Volvo is the safe car.&rdquo;", "40K &rarr; 113,267 cars"),
                     ("Wang Lao Ji", "&ldquo;Drink it when you&rsquo;re afraid of getting heaty.&rdquo;", "&yen;100M &rarr; &yen;16B"),
                 ])
             + '</div>'
             '<p class="hero-context" style="margin-top:26px;font-size:20px">'
             'The product did not change in a single one of these cases. Only the reason to choose '
             'it did &mdash; and revenue jumped within 1&ndash;2 years.</p>',
    )),
    ("payoff", dict(
        overline=P2_OVER, counter="08 / 09", source="observeco.com", series="/ Singapore",
        body='<h2 class="stat-head">Strategy shouldn&rsquo;t be a luxury for small businesses.</h2>'
             '<div class="payoff"><p>ObserveCo exists to make strategic thinking accessible to '
             'the businesses that need it most &mdash; not the ones who can already afford a '
             'consultancy. <strong>The clarity that decides whether you get chosen.</strong></p></div>'
             '<p class="mission">You may be small. But your strategy shouldn&rsquo;t be.</p>',
    )),
    ("artifact", dict(
        overline=P2_OVER, counter="09 / 09", source="", series="/ Singapore",
        body='<div class="artifact">'
             '<img src="assets/cover-back.png" alt="Back cover of Small Island, Crowded Market">'
             '<div class="artifact-body">'
             '<div class="kicker">How we know</div>'
             '<p>The thinking behind our method is published in <strong>Small Island, '
             'Crowded Market</strong> &mdash; 64 findings on the ground every Singapore '
             'small business competes on, and the industries a small business can '
             'actually win in.</p>'
             '<p>Every figure is confidence-labelled and sourced. It is the standard we '
             'hold our client work to.</p>'
             '</div></div>',
    )),
]


def render(post_no, slug, slides, overline=None):
    written = []
    for i, (kind, kw) in enumerate(slides, 1):
        name = f"post{post_no:02d}-slide{i:02d}-{slug}.html"
        path = os.path.join(OUT, name)
        kw = dict(kw)
        # Full-bleed slides: no header rule, no footer chrome. The artwork/wordmark
        # IS the hook, and template chrome around it just adds noise.
        if kind in ("cover-front", "logo-hero"):
            kw.setdefault("bare", True)
        with open(path, "w") as fh:
            fh.write(page(title=f"ObserveCo IG · {slug} · {i}", **kw))
        written.append((name, kind))
    return written


POSTS = {
    1: ("three-engines", P1),
    2: ("what-is-observeco", P2),
}


if __name__ == "__main__":
    want = [int(a) for a in sys.argv[1:]] or sorted(POSTS)
    total = 0
    for p in want:
        slug, slides = POSTS[p]
        for name, kind in render(p, slug, slides):
            print(f"  {kind:8s} {name}")
            total += 1
    print(f"\n{total} slides written to {OUT}")
