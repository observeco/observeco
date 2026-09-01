/* ============================================================
   ObserveCo Consulting — White Paper infographic library
   Inline SVG, zero dependencies. Each infographic is 1200px wide,
   drawn on the consulting paper canvas with the design-system
   tokens (light-first, insight teal, serif display + Inter + mono).

   Every figure is REAL and confidence-labelled in the white papers
   (whitepapers/01-06). No fabricated data.

   Usage on any page:
     <div data-wp-graphic="01"></div>
   ...then include this file. It injects the SVG on DOMContentLoaded.
   Vanilla JS, static only — no build step.
   ============================================================ */
(function () {
  'use strict';

  /* ---- consulting design tokens (light-first) ---- */
  var TOK = {
    paper: '#f7f6f3',
    surface: '#ffffff',
    surface2: '#f1f0ec',
    line: '#e4e2dc',
    lineStrong: '#cfccc4',
    ink: '#1c1f24',
    ink2: '#4a525c',
    ink3: '#6b737e',
    teal: '#0e6e5c',
    tealStrong: '#0a5447',
    tealTint: '#e7f1ee',
    tealLine: '#c6dcd4',
    coral: '#b84a2f',
    amber: '#c99a3f',
    steel: '#3d6b9b',
    olive: '#7f8c5a',
    terracotta: '#b4653a'
  };
  var D = "'Iowan Old Style',Georgia,'Times New Roman',serif";
  var S = "'Inter',-apple-system,BlinkMacSystemFont,sans-serif";
  var M = "'JetBrains Mono',Menlo,Consolas,monospace";

  /* shared small label chip */
  function chip(x, y, w, label) {
    var h = 40;
    return (
      '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="20" fill="' + TOK.surface2 + '" stroke="' + TOK.line + '"/>' +
      '<text x="' + (x + w / 2) + '" y="' + (y + 24) + '" text-anchor="middle" font-family="' + S + '" font-size="13" font-weight="500" fill="' + TOK.ink2 + '">' + label + '</text>'
    );
  }
  /* header block reused by every graphic */
  function head(no, title, sub) {
    return (
      '<rect width="1200" height="720" fill="' + TOK.paper + '"/>' +
      '<text x="60" y="42" font-family="' + M + '" font-size="12" font-weight="500" letter-spacing="3" fill="' + TOK.teal + '">WHITE PAPER ' + no + '</text>' +
      '<text x="60" y="84" font-family="' + D + '" font-size="40" font-weight="600" fill="' + TOK.ink + '">' + title + '</text>' +
      '<text x="60" y="112" font-family="' + S + '" font-size="16" fill="' + TOK.ink2 + '">' + sub + '</text>'
    );
  }
  /* ascending annotation arrow (WP2/WP3) */
  function rise(x1, y1, x2, y2, color) {
    return (
      '<path d="M' + x1 + ' ' + y1 + ' C ' + ((x1 + x2) / 2) + ' ' + y1 + ', ' + ((x1 + x2) / 2) + ' ' + y2 + ', ' + x2 + ' ' + y2 + '" fill="none" stroke="' + color + '" stroke-width="4" stroke-linecap="round"/>' +
      '<path d="M' + (x2 - 6) + ' ' + (y2 - 12) + ' L ' + x2 + ' ' + y2 + ' L ' + (x2 - 12) + ' ' + (y2 - 6) + '" fill="none" stroke="' + color + '" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    );
  }

  var g = {};

  /* ============ WP1 · Two Economies ============ */
  g.WP01 = function () {
    return (
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="One island, two economies. The engine: a small number of global firms with most of the value. The domestic layer: most firms serving a market capped at 5.9 million people. Engine payroll flows down into domestic demand." font-family="' + S + '">' +
      head('1 · THE LANDSCAPE', 'One island, two economies', 'The engine pays the world. The domestic layer serves the island — and lives on the engine\u2019s payroll.') +
      '<rect x="40" y="140" width="1120" height="540" rx="16" fill="' + TOK.surface + '" stroke="' + TOK.line + '"/>' +
      '<line x1="60" y1="402" x2="1130" y2="402" stroke="' + TOK.line + '" stroke-width="1.5"/>' +

      /* ENGINE top band */
      '<text x="70" y="196" font-family="' + M + '" font-size="12" font-weight="700" letter-spacing="3" fill="' + TOK.teal + '">THE ENGINE · GLOBAL</text>' +
      '<text x="70" y="236" font-family="' + D + '" font-size="27" font-weight="600" fill="' + TOK.ink + '">Small in number, huge in value</text>' +
      '<text x="70" y="260" font-family="' + S + '" font-size="15" fill="' + TOK.ink2 + '">MNCs · GLCs · foreign subsidiaries — capital, exports, R&amp;D, global markets</text>' +
      chip(70, 290, 320, '~20% of all firms, most of the value') +
      chip(408, 290, 300, 'top-10% earners: ~60% work here') +
      chip(726, 290, 330, 'FDI S$3.1tn ≈ 4\u00d7 GDP') +

      /* DOMESTIC bottom band */
      '<text x="70" y="448" font-family="' + M + '" font-size="12" font-weight="700" letter-spacing="3" fill="' + TOK.teal + '">DOMESTIC LAYER · LOCAL</text>' +
      '<text x="70" y="488" font-family="' + D + '" font-size="27" font-weight="600" fill="' + TOK.ink + '">The whole island by number — a capped market</text>' +
      '<text x="70" y="512" font-family="' + S + '" font-size="15" fill="' + TOK.ink2 + '">SMEs · shops · clinics · tuition — serve the local market</text>' +
      chip(72, 542, 320, '~99.6% of all firms are SMEs') +
      chip(408, 542, 300, '~71\u201372% of employment') +
      chip(726, 542, 330, 'market capped at ~5.9M people') +

      /* payroll flow arrow engine -> domestic */
      '<path d="M1052 330 C 1052 362, 1052 368, 1052 402" fill="none" stroke="' + TOK.teal + '" stroke-width="5" stroke-linecap="round"/>' +
      '<path d="M1044 386 L 1052 404 L 1060 386" fill="none" stroke="' + TOK.teal + '" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<rect x="1002" y="318" width="100" height="28" rx="8" fill="' + TOK.tealTint + '"/>' +
      '<text x="1052" y="336" text-anchor="middle" font-family="' + M + '" font-size="11" font-weight="700" fill="' + TOK.tealStrong + '">PAYROLL</text>' +
      '<text x="1052" y="438" text-anchor="middle" font-family="' + S + '" font-size="12.5" fill="' + TOK.tealStrong + '">\u2192 local demand</text>' +

      '<text x="600" y="688" text-anchor="middle" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">The engine is not your market. It is the pipe that pays for your market.</text>' +
      '</svg>'
    );
  };

  /* ============ WP2 · Four Demographic Waves ============ */
  g.WP02 = function () {
    var b1 = TOK.steel, b2 = TOK.olive, b3 = TOK.terracotta, b4 = TOK.teal;
    var base = 600;
    var bw = 216;
    var cols = [
      { cx: 196, h: 150, c: b1, name: 'Ageing', m: '1 in 5 residents is 65+', word: 'DIGNITY &amp; INDEPENDENCE' },
      { cx: 466, h: 224, c: b2, name: 'Fertility collapse', m: 'TFR 0.87 — under one child', word: 'CONCENTRATION PER CHILD' },
      { cx: 746, h: 292, c: b3, name: 'Shrinking household', m: '1.49M households, more single', word: 'CONVENIENCE' },
      { cx: 1016, h: 366, c: b4, name: 'Care remaking', m: 'care S$0.28\u20130.85bn, growing', word: 'TIME' }
    ];
    var s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="Four structural waves — ageing, fertility collapse, shrinking household, remaking of care. Each rises, and each makes one word scarce: dignity and independence, concentration per child, convenience, and time." font-family="' + S + '">' +
      head('2 · THE DEMOGRAPHICS', 'Four waves, one verdict', 'The people are already here; the money is already spent. Four structural forces change what gets bought.') +
      '<line x1="60" y1="' + base + '" x2="1140" y2="' + base + '" stroke="' + TOK.lineStrong + '" stroke-width="2"/>';
    /* ascending arrow */
    s += '<path d="M150 200 C 120 250, 120 290, 150 336" fill="none" stroke="' + TOK.teal + '" stroke-width="4" stroke-linecap="round"/>' +
      '<path d="M142 326 L 150 338 L 158 326" fill="none" stroke="' + TOK.teal + '" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<text x="164" y="266" font-family="' + M + '" font-size="11" font-weight="700" fill="' + TOK.teal + '">RISING</text>';
    for (var i = 0; i < cols.length; i++) {
      var c = cols[i];
      var top = base - c.h;
      var bx = c.cx - bw / 2;
      s += '<rect x="' + bx + '" y="' + top + '" width="' + bw + '" height="' + c.h + '" rx="10" fill="' + c.c + '" opacity="0.94"/>';
      /* wave label below base */
      s += '<text x="' + c.cx + '" y="' + (base + 28) + '" text-anchor="middle" font-family="' + D + '" font-size="19" font-weight="600" fill="' + TOK.ink + '">' + c.name + '</text>';
      s += '<text x="' + c.cx + '" y="' + (base + 54) + '" text-anchor="middle" font-family="' + S + '" font-size="12" fill="' + TOK.ink2 + '">' + c.m + '</text>';
      /* scarce-word tag atop bar */
      var ww = Math.max(196, c.word.replace(/&amp;/g, ' ').length * 7.0 + 44);
      var wx = c.cx - ww / 2;
      s += '<rect x="' + wx + '" y="' + (top - 40) + '" width="' + ww + '" height="30" rx="15" fill="' + TOK.surface + '" stroke="' + TOK.lineStrong + '"/>' +
        '<text x="' + c.cx + '" y="' + (top - 19) + '" text-anchor="middle" font-family="' + M + '" font-size="11" font-weight="700" letter-spacing="1" fill="' + TOK.ink2 + '">' + c.word + '</text>';
    }
    s += '<text x="600" y="694" text-anchor="middle" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">Height shows momentum, not scale. Each wave\u2019s one-line implication from the paper sits above its bar.</text>';
    return s + '</svg>';
  };

  /* ============ WP3 · The Industry Map (scatter) ============ */
  g.WP03 = function () {
    var plotX = 70, plotW = 1040, plotY = 150, plotH = 470, baseY = plotY + plotH;
    var dots = [
      { name: 'Wholesale', sh: '18.6', x: 890, y: 236, r: 34, c: TOK.steel },
      { name: 'Manufacturing', sh: '16.8', x: 796, y: 296, r: 31, c: TOK.steel },
      { name: 'Finance', sh: '13.2', x: 688, y: 356, r: 28, c: TOK.steel },
      { name: 'Transport', sh: '7.6', x: 578, y: 434, r: 19, c: TOK.steel },
      { name: 'Info & comms', sh: '6.0', x: 502, y: 470, r: 16, c: TOK.steel },
      { name: 'Health', sh: '2.6', x: 268, y: 300, r: 12, c: TOK.teal },
      { name: 'Education', sh: '2.3', x: 234, y: 355, r: 11, c: TOK.teal },
      { name: 'Admin & support', sh: '2.3', x: 200, y: 410, r: 11, c: TOK.teal },
      { name: 'Retail', sh: '1.1', x: 172, y: 465, r: 8, c: TOK.teal },
      { name: 'F&B', sh: '1.0', x: 146, y: 520, r: 8, c: TOK.teal },
      { name: 'Arts & rec', sh: '1.0', x: 124, y: 575, r: 8, c: TOK.teal }
    ];
    var s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="Industry scatter by GDP share and entry difficulty. The big engine industries sit high and hard to enter. The small domestic industries sit low and open — the differentiation slot in between." font-family="' + S + '">' +
      head('3 · THE INDUSTRY MAP', 'Big numbers are busy. The slot is small.', 'Big share of GDP = structurally closed. Small domestic industries are where you can actually compete.') +

      /* the differentiation slot band (left, low share) */
      '<rect x="40" y="' + plotY + '" width="300" height="' + plotH + '" fill="' + TOK.tealTint + '" opacity="0.75"/>' +
      '<text x="190" y="' + (plotY + 28) + '" text-anchor="middle" font-family="' + M + '" font-size="11" font-weight="700" letter-spacing="1" fill="' + TOK.tealStrong + '">THE DIFFERENTIATION SLOT</text>' +
      '<text x="190" y="' + (plotY + 46) + '" text-anchor="middle" font-family="' + S + '" font-size="11" fill="' + TOK.ink3 + '">small domestic industries</text>' +

      '<line x1="' + plotX + '" y1="' + baseY + '" x2="' + (plotX + plotW) + '" y2="' + baseY + '" stroke="' + TOK.lineStrong + '" stroke-width="2"/>' +
      '<line x1="' + plotX + '" y1="' + plotY + '" x2="' + plotX + '" y2="' + baseY + '" stroke="' + TOK.lineStrong + '" stroke-width="2"/>' +
      '<text x="' + (plotX + plotW / 2) + '" y="' + (baseY + 34) + '" text-anchor="middle" font-family="' + S + '" font-size="12.5" fill="' + TOK.ink3 + '">entry difficulty \u2192</text>' +
      '<text x="' + (plotX - 16) + '" y="' + (plotY + 60) + '" transform="rotate(-90 ' + (plotX - 16) + ' ' + (plotY + 60) + ')" text-anchor="middle" font-family="' + S + '" font-size="12.5" fill="' + TOK.ink3 + '">share of GDP \u2192</text>';

    for (var i = 0; i < dots.length; i++) {
      var d = dots[i];
      s += '<circle cx="' + d.x + '" cy="' + d.y + '" r="' + d.r + '" fill="' + d.c + '" opacity="0.9"/>' +
        '<text x="' + d.x + '" y="' + (d.y + 4) + '" text-anchor="middle" font-family="' + M + '" font-size="10" font-weight="700" fill="#fff">' + d.sh + '%</text>';
      if (d.c === TOK.teal) {
        s += '<text x="' + d.x + '" y="' + (d.y + d.r + 16) + '" text-anchor="middle" font-family="' + S + '" font-size="11" fill="' + TOK.tealStrong + '">' + d.name + '</text>';
      }
    }
    s += '<text x="840" y="160" font-family="' + D + '" font-size="17" font-weight="600" fill="' + TOK.ink2 + '">big share = hard to enter</text>' +
      '<text x="700" y="180" font-family="' + S + '" font-size="12.5" fill="' + TOK.ink3 + '">engine territory, structurally closed</text>' +
      '<text x="352" y="330" font-family="' + D + '" font-size="17" font-weight="600" fill="' + TOK.tealStrong + '">where you compete</text>' +
      '<g transform="translate(860,560)">' +
      '<circle cx="8" cy="8" r="7" fill="' + TOK.steel + '"/><text x="24" y="13" font-family="' + S + '" font-size="12" fill="' + TOK.ink3 + '">engine — big, closed</text>' +
      '<circle cx="8" cy="30" r="7" fill="' + TOK.teal + '"/><text x="24" y="35" font-family="' + S + '" font-size="12" fill="' + TOK.ink3 + '">domestic — open, differentiated</text>' +
      '</g>' +
      '<text x="600" y="690" text-anchor="middle" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">Shares are % of Singapore GDP (2025). The engine\u2019s data is high quality; the domestic tail is coarse — that\u2019s why you do your own research.</text>' +
      '</svg>';
    return s;
  };

  /* ============ WP4 · Wall vs Door ============ */
  g.WP04 = function () {
    var tiles = [
      { n: 'Grab', s: 'food delivery ~69%' },
      { n: 'DBS · OCBC · UOB', s: 'the banks' },
      { n: 'PwC · Deloitte · EY · KPMG', s: 'the audits' },
      { n: 'NTUC FairPrice', s: 'groceries ~35\u201342%' }
    ];
    var door = ['TUITION', 'HOME CARE', 'SALONS', 'LAUNDRY', 'BEAUTY'];
    var s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="Wall versus door. Some industries a few names own roughly eighty percent — a wall you do not enter. Others no name owns even a fifth — an open door where the missing brand is the opportunity." font-family="' + S + '">' +
      head('4 · THE BRAND MAP', 'Wall or door?', 'Some industries a few names own \u224880%. Others no name owns even a fifth. The difference is the shape of your entry.') +

      /* LEFT: the wall */
      '<rect x="40" y="140" width="540" height="520" rx="16" fill="' + TOK.surface + '" stroke="' + TOK.line + '"/>' +
      '<text x="60" y="176" font-family="' + M + '" font-size="12" font-weight="700" letter-spacing="2" fill="' + TOK.coral + '">THE WALL</text>' +
      '<text x="60" y="200" font-family="' + S + '" font-size="14" fill="' + TOK.ink2 + '">a few names own ~80%</text>';
    for (var i = 0; i < tiles.length; i++) {
      var t = tiles[i];
      var ty = 226 + i * 92;
      s += '<rect x="56" y="' + ty + '" width="508" height="68" rx="10" fill="' + TOK.surface2 + '" stroke="' + TOK.line + '"/>' +
        '<text x="76" y="' + (ty + 30) + '" font-family="' + S + '" font-size="15" font-weight="600" fill="' + TOK.ink + '">' + t.n + '</text>' +
        '<text x="76" y="' + (ty + 52) + '" font-family="' + S + '" font-size="12.5" fill="' + TOK.ink3 + '">' + t.s + '</text>';
    }
    s += '<text x="60" y="622" font-family="' + S + '" font-size="13.5" fill="' + TOK.coral + '">You don\u2019t enter. You look for the gap the giant left.</text>' +

      /* RIGHT: the door */
      '<rect x="620" y="140" width="540" height="520" rx="16" fill="' + TOK.surface + '" stroke="' + TOK.line + '"/>' +
      '<text x="640" y="176" font-family="' + M + '" font-size="12" font-weight="700" letter-spacing="2" fill="' + TOK.teal + '">THE DOOR</text>' +
      '<text x="640" y="200" font-family="' + S + '" font-size="14" fill="' + TOK.ink2 + '">no name owns even a fifth</text>' +

      /* open door */
      '<path d="M640 230 L868 230 L868 520 L640 520 Z" fill="' + TOK.tealTint + '" stroke="' + TOK.tealLine + '" stroke-width="2"/>' +
      '<path d="M640 230 L842 230 L842 520 L640 520 Z" fill="' + TOK.surface + '" stroke="' + TOK.tealLine + '" stroke-width="2"/>' +
      '<circle cx="838" cy="336" r="5" fill="' + TOK.teal + '"/>' +
      '<text x="742" y="270" text-anchor="middle" font-family="' + D + '" font-size="20" font-weight="600" fill="' + TOK.tealStrong + '">an open door</text>';
    var dy = 250;
    for (var d = 0; d < door.length; d++) {
      var by = dy + d * 49;
      s += '<rect x="650" y="' + by + '" width="208" height="42" rx="8" fill="' + TOK.surface2 + '" stroke="' + TOK.tealLine + '"/>' +
        '<text x="754" y="' + (by + 27) + '" text-anchor="middle" font-family="' + M + '" font-size="14" font-weight="600" fill="' + TOK.tealStrong + '">' + door[d] + '</text>';
    }
    s += '<text x="754" y="505" text-anchor="middle" font-family="' + S + '" font-size="12.5" fill="' + TOK.tealStrong + '">tuition alone: S$1\u20131.8bn a year, no dominant name</text>' +

      '<text x="600" y="676" text-anchor="middle" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">The concentrated own scale, not words. The fragmented have the words, unowned.</text>' +
      '</svg>';
    return s;
  };

  /* ============ WP5 · AI Map: the two-way wedge ============ */
  g.WP05 = function () {
    var left = [
      ['Execution — the DOING', 'copy, campaigns, admin, scheduling'],
      ['Can be automated', 'AI does the work while you sleep'],
      ['Cheap to copy', 'a competitor can rent the same agents']
    ];
    var right = [
      ['Being CHOSEN — the word', 'trust, relationship, reputation'],
      ['Cannot be automated', 'a decade of referrals, not a script'],
      ['The only durable moat', 'the one thing AI can\u2019t copy']
    ];
    var s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="AI is a two-way wedge. It makes the doing cheap — execution, which anyone can copy and no one can defend. It cannot make being chosen cheap — trust, relationship and the word in the customer\u2019s mind." font-family="' + S + '">' +
      head('5 · THE AI MAP', 'AI is a two-way wedge', 'AI makes the doing cheap. It cannot make being chosen cheap. That split decides who wins.') +

      /* LEFT — the DOING (commoditized) */
      '<rect x="40" y="140" width="540" height="520" rx="16" fill="' + TOK.surface + '" stroke="' + TOK.line + '"/>' +
      '<text x="60" y="180" font-family="' + M + '" font-size="12" font-weight="700" letter-spacing="2" fill="' + TOK.coral + '">AI MAKES CHEAP</text>' +
      '<text x="60" y="204" font-family="' + D + '" font-size="24" font-weight="600" fill="' + TOK.ink + '">The DOING</text>' +
      '<text x="60" y="228" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">execution — and execution can\u2019t be defended</text>';
    for (var i = 0; i < left.length; i++) {
      var ty = 260 + i * 100;
      s += '<rect x="44" y="' + ty + '" width="290" height="76" rx="10" fill="' + TOK.surface2 + '" stroke="' + TOK.line + '"/>' +
        '<text x="60" y="' + (ty + 30) + '" font-family="' + S + '" font-size="14.5" font-weight="600" fill="' + TOK.ink + '">' + left[i][0] + '</text>' +
        '<text x="60" y="' + (ty + 54) + '" font-family="' + S + '" font-size="12.5" fill="' + TOK.ink3 + '">' + left[i][1] + '</text>';
    }
    s += '<text x="204" y="600" text-anchor="middle" font-family="' + S + '" font-size="13.5" font-weight="600" fill="' + TOK.coral + '">execution: no moat</text>' +

      /* RIGHT: the CHOSEN (durable) */
      '<rect x="560" y="140" width="610" height="520" rx="16" fill="' + TOK.surface + '" stroke="' + TOK.tealLine + '"/>' +
      '<text x="577" y="180" font-family="' + M + '" font-size="12" font-weight="700" letter-spacing="2" fill="' + TOK.teal + '">AI CANNOT MAKE CHEAP</text>' +
      '<text x="577" y="204" font-family="' + D + '" font-size="24" font-weight="600" fill="' + TOK.ink + '">Being CHOSEN</text>' +
      '<text x="577" y="228" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">the word in the customer\u2019s mind — trust, relationship</text>';
    for (var j = 0; j < right.length; j++) {
      var ry = 260 + j * 100;
      s += '<rect x="574" y="' + ry + '" width="582" height="76" rx="10" fill="' + TOK.tealTint + '" stroke="' + TOK.tealLine + '"/>' +
        '<text x="590" y="' + (ry + 26) + '" font-family="' + S + '" font-size="14.5" font-weight="600" fill="' + TOK.tealStrong + '">' + right[j][0] + '</text>' +
        '<text x="590" y="' + (ry + 54) + '" font-family="' + S + '" font-size="12.5" fill="' + TOK.ink3 + '">' + right[j][1] + '</text>';
    }
    s += '<text x="865" y="600" text-anchor="middle" font-family="' + S + '" font-size="13.5" font-weight="600" fill="' + TOK.tealStrong + '">= the only durable advantage</text>' +

      '<text x="600" y="676" text-anchor="middle" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">Adoption: big firms 2 in 3, small firms 1 in 7 — a 48-point gap, widening because big firms adopt 4\u00d7 faster.</text>' +
      '</svg>';
    return s;
  };

  /* ============ WP6 · The Decision Line ============ */
  g.WP06 = function () {
    var s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="The decision line. A map hands you the terrain — every industry, wave, brand and word. But it does not hand you your spot. Your position is individual and relative, defined only by your rivals and your customers." font-family="' + S + '">' +
      head('6 · THE DECISION LINE', 'The map is the market. Your spot is not on it.', 'The terrain is fully mapped. Where you stand in it is something only your own market can reveal.') +

      '<rect x="40" y="140" width="1120" height="460" rx="16" fill="' + TOK.surface + '" stroke="' + TOK.line + '"/>' +
      '<path d="M80 480 L200 330 L320 470 L440 290 L560 470 L680 330 L800 470 L920 300 L1040 470 L1120 360" fill="none" stroke="' + TOK.teal + '" stroke-width="3" stroke-linejoin="round" opacity="0.5"/>' +
      '<g fill="' + TOK.surface2 + '" stroke="' + TOK.line + '">' +
      '<circle cx="200" cy="330" r="8"/><circle cx="440" cy="290" r="8"/><circle cx="680" cy="330" r="8"/><circle cx="920" cy="300" r="8"/>' +
      '</g>' +
      '<text x="440" y="276" text-anchor="middle" font-family="' + M + '" font-size="12" fill="' + TOK.teal + '">THE TERRAIN</text>' +
      '<text x="440" y="292" text-anchor="middle" font-family="' + S + '" font-size="12" fill="' + TOK.ink3 + '">map of the market</text>' +

      /* the line itself */
      '<line x1="300" y1="500" x2="900" y2="500" stroke="' + TOK.coral + '" stroke-width="4"/>' +
      '<text x="600" y="540" text-anchor="middle" font-family="' + D + '" font-size="26" font-weight="600" fill="' + TOK.coral + '">THE DECISION LINE</text>' +
      '<text x="600" y="566" text-anchor="middle" font-family="' + S + '" font-size="13.5" fill="' + TOK.ink2 + '">where the map stops, and only your own analysis can go on</text>' +

      /* left of line: what the map gives you */
      '<rect x="60" y="190" width="300" height="120" rx="12" fill="' + TOK.surface2 + '" stroke="' + TOK.line + '"/>' +
      '<text x="80" y="220" font-family="' + M + '" font-size="12" font-weight="700" fill="' + TOK.teal + '">WHAT THE MAP GAVE YOU</text>' +
      '<text x="80" y="246" font-family="' + S + '" font-size="13" fill="' + TOK.ink2 + '">two economies · four waves</text>' +
      '<text x="80" y="266" font-family="' + S + '" font-size="13" fill="' + TOK.ink2 + '">every industry · who owns each word</text>' +
      '<text x="80" y="286" font-family="' + S + '" font-size="13" fill="' + TOK.ink2 + '">how AI reshapes it</text>' +

      /* right of the line — your spot (empty) */
      '<rect x="860" y="190" width="280" height="44" rx="12" fill="' + TOK.tealTint + '" stroke="' + TOK.tealLine + '"/>' +
      '<text x="880" y="220" font-family="' + M + '" font-size="12" font-weight="700" fill="' + TOK.tealStrong + '">NOT ON THE MAP</text>' +
      '<text x="880" y="246" font-family="' + S + '" font-size="13" fill="' + TOK.ink2 + '">your competitive set</text>' +
      '<text x="880" y="266" font-family="' + S + '" font-size="13" fill="' + TOK.ink2 + '">your customers\u2019 mental map</text>' +
      '<text x="880" y="286" font-family="' + S + '" font-size="13" fill="' + TOK.ink2 + '">your open slot — your word</text>' +

      '<text x="600" y="686" text-anchor="middle" font-family="' + S + '" font-size="13" fill="' + TOK.ink3 + '">The map is structural and aggregate. A position is individual and relative — true only of your own market.</text>' +
      '</svg>';
    return s;
  };

  /* ---- renderer: inject each [data-wp-graphic] with its SVG ---- */
  function render() {
    var els = document.querySelectorAll('[data-wp-graphic]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var key = el.getAttribute('data-wp-graphic');
      var fn = g[key];
      if (!fn && key && !/^WP/i.test(key)) {
        fn = g['WP' + key];           /* accept "01" or "WP01" */
      }
      if (fn) {
        el.innerHTML = fn();
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
