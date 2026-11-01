/* ============================================================
   ObserveCo Consulting — draft site scroll-trigger animations
   Vanilla IntersectionObserver. No libraries, no frameworks.

   Adds class 'in-view' to animated containers when they enter
   the viewport (threshold ~0.2), then unobserves so it fires once.
   Elements already in viewport on load fire immediately (observer
   default behavior) — so the above-the-fold hero flow still animates
   on load.

   Graceful degradation:
   - JS disabled: script never runs, no 'in-view' added, elements
     show their natural final state (no animation, no broken layout).
   - IntersectionObserver unsupported (very old browsers): add
     'in-view' to everything so animations still run.
   ============================================================ */
(function () {
  'use strict';

  var SELECTOR = '.hero-flow, .process-flow, .case-bars, .phase-bar, .stock-chart, .cost-scale, .flywheel-wrap, .rank-bar, .method-pipeline, .data-bar, .odometer, .clicker, .gauge, .usa-map, .volvo-mark, .ladder, .suv, .cmp-bars, .value-chart, .cohort, .ticker, .split, .rank, .white-space-band, .hero-map, .hero-map-col, .outcome-grid, .watch-ws-band, .watch-radar';

  if (!('IntersectionObserver' in window)) {
    // No observer support — fall back to running all animations.
    var all = document.querySelectorAll(SELECTOR);
    for (var i = 0; i < all.length; i++) all[i].classList.add('in-view');
    return;
  }

  var targets = document.querySelectorAll(SELECTOR);
  if (!targets.length) return;

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });

  targets.forEach(function (el) { observer.observe(el); });
})();

/* ============================================================
   NAV DROPDOWN — References (desktop hover + click, mobile click)
   ============================================================ */
(function () {
  'use strict';
  var dropdowns = document.querySelectorAll('.nav-dropdown');
  if (!dropdowns.length) return;

  function closeAll(except) {
    dropdowns.forEach(function (d) {
      if (d !== except) d.classList.remove('open');
      var t = d.querySelector('.nav-dropdown-toggle');
      if (t) t.setAttribute('aria-expanded', 'false');
    });
  }

  dropdowns.forEach(function (dd) {
    var toggle = dd.querySelector('.nav-dropdown-toggle');
    if (!toggle) return;
    // A click-opened dropdown must stay open until outside-click/Escape,
    // even if the cursor leaves the toggle (the menu sits 12px below it,
    // so mouseleave would otherwise fire the instant you reach for it).
    var clickOpened = false;

    function setOpen(open) {
      dd.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (!open) clickOpened = false;
    }

    // Click toggles (works on both desktop and mobile)
    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var isOpen = dd.classList.contains('open');
      closeAll(dd);
      if (!isOpen) { setOpen(true); clickOpened = true; }
    });

    // Desktop hover open
    dd.addEventListener('mouseenter', function () { setOpen(true); });
    dd.addEventListener('mouseleave', function () {
      // Don't close a click-opened dropdown on mouseleave — only outside-click/Escape.
      if (!clickOpened) setOpen(false);
    });
  });

  // Close on outside click
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.nav-dropdown')) closeAll(null);
  });

  // Close on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll(null);
  });
})();

/* ============================================================
   EXPANDING RADIAL PULSE — ambient background
   A fixed canvas behind the page draws ONE small bright amber core
   that expands and lightens outward like a heartbeat of light —
   a radial pulse that blooms into a soft halo, then dissolves and
   re-pulses. There is no hard moving edge: it is a single gradient
   whose radius grows and whose intensity dilutes, so it reads as
   light radiating from the centre, not a travelling object.

   Engineered:
   - Single fixed canvas, full viewport, behind all content.
   - Amber radial gradient: bright small core at start of cycle,
     expanding radius + diluting alpha over the cycle.
   - Eased growth (easeOut) so the bloom feels organic, not linear.
   - Respects prefers-reduced-motion: draws one static dim frame, no loop.
   ============================================================ */
(function () {
  'use strict';

  var REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!document.body || document.documentElement.getAttribute('data-dots') === 'off') return;

  var canvas = document.createElement('canvas');
  canvas.className = 'bg-wash';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.appendChild(canvas);
  var ctx = canvas.getContext('2d');
  if (!ctx) { canvas.remove(); return; }

  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0;

  function resize() {
    W = canvas.width = Math.floor(window.innerWidth * dpr);
    H = canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
  }
  resize();
  window.addEventListener('resize', resize);

  // Amber pulse — reads as a bloom of warm light on paper, not a coloured
  // object. Warm/high-luminance, so peak alpha kept moderate so the text
  // stays readable. One centred radial that grows + dilutes each cycle.
  var AMBER = [201, 138, 61];     // warm amber (sits on #f7f6f3 paper)
  var CYCLE = 6000;               // ms per pulse
  var MAX_R = 0.8;                // max radius as fraction of max dimension
  var PEAK = 0.42;               // peak alpha at the bright core

  function draw(t /* 0..1 progress through cycle */) {
    ctx.clearRect(0, 0, W, H);
    var cx = W / 2, cy = H / 2;
    // Eased growth: slow start then accelerate (easeOut) — organic bloom.
    var ease = 1 - Math.pow(1 - t, 2);
    var r = Math.max(W, H) * MAX_R * ease;
    // Core bright at start, lightens as it expands (outward dilution).
    var peak = PEAK * (1 - 0.7 * t);
    var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(r, 1));
    g.addColorStop(0.00, 'rgba(' + AMBER[0] + ',' + AMBER[1] + ',' + AMBER[2] + ',' + peak + ')');
    g.addColorStop(0.45, 'rgba(' + AMBER[0] + ',' + AMBER[1] + ',' + AMBER[2] + ',' + (peak * 0.4) + ')');
    g.addColorStop(1.00, 'rgba(' + AMBER[0] + ',' + AMBER[1] + ',' + AMBER[2] + ',0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }

  if (REDUCED) { draw(0.12); return; }

  var t0 = performance.now();
  function frame(now) {
    var t = ((now - t0) % CYCLE) / CYCLE;
    draw(t);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();

/* ============================================================
   INTERACTIVE NODE GRID — cursor-reactive background
   A faint grid of teal nodes sits behind the page. Moving the
   cursor through it pushes the nearby nodes aside and brightens
   them, so the disturbed region travels with the mouse. Once the
   cursor stops, the whole grid dissolves back into the paper.

   The technique (squared-falloff proximity + per-node lerp) is the
   standard "interactive dot grid" pattern; the idle-fade and the
   displacement are the parts we add on top.

   Engineered:
   - Fixed full-viewport canvas, pointer-events none, z-index -1,
     so it never intercepts a click, hover, selection or scroll.
   - Squared falloff: t = 1 - dist/reach, influence = t*t — gives a
     soft core with a wide quiet tail instead of a hard disc.
   - Per-node lerp toward the target size/offset/alpha, so nodes
     glide to their new state rather than snapping.
   - Fade state machine: ramps in on mousemove, ramps out once the
     cursor has been still for IDLE_MS. Out is deliberately slower
     than in — it dissolves rather than blinking off.
   - When fully faded it PARKS the rAF loop entirely, so an idle
     page costs no CPU on an invisible effect. Wakes on mousemove.
   - Skipped on coarse pointers (nothing to react to on touch) and
     under prefers-reduced-motion, rather than drawing a static field.

   ponytail: every node is tested and the visible ones drawn each
   frame — O(rows*cols), ~1.5k nodes at 30px spacing, which holds up
   fine because the loop only runs while the cursor is active.
   Upgrade path if spacing ever tightens: cache the resting grid to
   an offscreen canvas and redraw only nodes inside the cursor's
   reach, or move to WebGL points.
   ============================================================ */
(function () {
  'use strict';

  if (!document.body) return;
  if (document.documentElement.getAttribute('data-dots') === 'off') return;
  // Mouse-driven ornament: on a touch / no-hover pointer there is nothing to
  // react to, so don't mount the canvas or its loop at all.
  if (window.matchMedia && window.matchMedia('(pointer: coarse)').matches) return;
  // Decorative motion only — honour the OS setting by drawing nothing.
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var canvas = document.createElement('canvas');
  canvas.className = 'bg-nodes';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.appendChild(canvas);
  var ctx = canvas.getContext('2d');
  if (!ctx) { canvas.remove(); return; }

  var COLOR = '14,110,92';  // --green, reads clean on the paper canvas
  var SPACING = 30;         // px between nodes
  var R_MIN = 1.15;         // resting radius
  var R_MAX = 3.2;          // radius directly under the cursor
  var REACH = 190;          // cursor influence radius, px
  var PUSH = 16;            // max push away from the cursor, px
  var BASE = 0.16;          // resting opacity of the active grid
  var PEAK = 0.5;           // opacity ceiling at the cursor
  var IDLE_MS = 1400;       // stillness before the grid starts to fade
  var IN_RATE = 0.14;       // fade-in per frame
  var OUT_RATE = 0.04;      // fade-out per frame (slower: a dissolve)
  var EASE = 0.16;          // per-node interpolation
  var TAU = 6.283185307179586;

  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0, nodes = [];
  var mx = -9999, my = -9999, lastMove = -Infinity;
  var fade = 0, rafId = null;

  function build() {
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.floor(W * dpr);
    canvas.height = Math.floor(H * dpr);
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var cols = Math.ceil(W / SPACING) + 1;
    var rows = Math.ceil(H / SPACING) + 1;
    nodes = new Array(cols * rows);
    var i = 0;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var ox = c * SPACING, oy = r * SPACING;
        // ox/oy are the rest position; x/y is where the node sits now.
        nodes[i++] = { ox: ox, oy: oy, x: ox, y: oy, r: R_MIN, a: 0 };
      }
    }
  }

  function frame(now) {
    ctx.clearRect(0, 0, W, H);

    var idle = now - lastMove > IDLE_MS;
    fade += ((idle ? 0 : 1) - fade) * (idle ? OUT_RATE : IN_RATE);

    // Fully faded and still: park the loop so it costs nothing.
    if (fade < 0.004) { fade = 0; rafId = null; return; }

    var reach2 = REACH * REACH;
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var tx = 0, ty = 0, inf = 0;
      var dx = n.ox - mx, dy = n.oy - my;
      var d2 = dx * dx + dy * dy;
      if (d2 < reach2) {
        var d = Math.sqrt(d2) || 1e-4;
        var t = 1 - d / REACH;
        inf = t * t;
        tx = (dx / d) * PUSH * inf;   // push outward from the cursor
        ty = (dy / d) * PUSH * inf;
      }
      n.x += (n.ox + tx - n.x) * EASE;
      n.y += (n.oy + ty - n.y) * EASE;
      n.a += ((BASE + (1 - BASE) * inf) - n.a) * EASE;
      n.r += ((R_MIN + (R_MAX - R_MIN) * inf) - n.r) * EASE;

      var alpha = n.a * fade * PEAK;
      if (alpha < 0.006) continue;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, TAU);
      ctx.fillStyle = 'rgba(' + COLOR + ',' + alpha.toFixed(3) + ')';
      ctx.fill();
    }

    rafId = requestAnimationFrame(frame);
  }

  function wake() {
    if (rafId === null) rafId = requestAnimationFrame(frame);
  }

  window.addEventListener('mousemove', function (e) {
    mx = e.clientX;
    my = e.clientY;
    lastMove = performance.now();
    wake();
  }, { passive: true });

  // Cursor left the window / tab lost focus: let the field relax. The idle
  // timer then fades it out on its own.
  function relax() { mx = -9999; my = -9999; }
  window.addEventListener('mouseout', relax);
  window.addEventListener('blur', relax);

  var rt = null;
  window.addEventListener('resize', function () {
    clearTimeout(rt);
    rt = setTimeout(function () { build(); wake(); }, 150);
  });

  build();
})();

/* ============================================================
   REEL SLIDER — coverflow of the case cards
   Reference: scrolltide.co "Reel Slider" (active card faces you, neighbours
   slide out, turn toward it and soften). Hand-authored vanilla JS — the
   gallery is a reference, not a dependency.

   Doctrine: the case grid is an EVIDENCE section, so this is USER-DRIVEN
   only — drag, arrows, keys, click-to-focus. No autoplay, no infinite
   animation. It also degrades: without JS, on narrow screens, or under
   prefers-reduced-motion, .case-grid stays the plain grid.
   ============================================================ */
(function () {
  var mqReduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var mqNarrow = window.matchMedia('(max-width: 860px)');

  var REACH = 3;              // how far the fan extends before cards park offstage
  var reels = [];             // one entry per [data-reel] grid on the page

  function shouldRun() {
    return !mqReduce.matches && !mqNarrow.matches;
  }

  // Status readout label. The case cards carry .case-year; other collections
  // use their own heading, so fall back through the likely candidates.
  function statusLabel(card) {
    var el = card.querySelector('[data-reel-label]') ||
             card.querySelector('.case-year, .kicker, .case-brand, h4, h3, h2');
    return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : '';
  }

  function initReel(grid) {
    var cards = [];
    for (var k = 0; k < grid.children.length; k++) {
      if (grid.children[k].nodeType === 1) cards.push(grid.children[k]);
    }
    if (cards.length < 3) return;    // a fan needs at least three cards

    var S = {
      grid: grid, cards: cards, active: 0, enabled: false, cardH: 0,
      dragging: false, startX: 0, startY: 0, dragged: false, pointerId: null,
      rTimer: null, controls: null, status: null, prevBtn: null, nextBtn: null
    };

    /* Controls are BUILT here rather than authored in the markup. There are
       nine reels across five pages: hand-writing nine control blocks means
       nine sets of duplicate data-attributes that would all match the same
       querySelector, and with no JS a hand-written control would sit on
       screen doing nothing. Generated here, they exist exactly when they
       work. */
    var wrap = document.createElement('div');
    wrap.className = 'reel-controls';
    wrap.hidden = true;
    wrap.innerHTML =
      '<button class="reel-btn" type="button" data-reel-prev aria-label="Previous card">\u2190</button>' +
      '<p class="reel-status" data-reel-status aria-live="polite"></p>' +
      '<button class="reel-btn" type="button" data-reel-next aria-label="Next card">\u2192</button>';
    grid.parentNode.insertBefore(wrap, grid.nextSibling);

    S.controls = wrap;
    S.status   = wrap.querySelector('[data-reel-status]');
    S.prevBtn  = wrap.querySelector('[data-reel-prev]');
    S.nextBtn  = wrap.querySelector('[data-reel-next]');

    /* Height: measure every card at natural size, then pin them all to the
       tallest so the coverflow reads as one rack rather than a ragged row. */
    function measure() {
      var i;
      for (i = 0; i < cards.length; i++) cards[i].style.height = 'auto';
      var tallest = 0;
      for (i = 0; i < cards.length; i++) {
        tallest = Math.max(tallest, cards[i].offsetHeight);
      }
      S.cardH = tallest;
      grid.style.height = tallest + 'px';
      for (i = 0; i < cards.length; i++) cards[i].style.height = tallest + 'px';
    }

    function spacing() {
      var w = grid.clientWidth || 1120;
      return Math.max(200, Math.min(w * 0.27, 320));
    }

    function render() {
      if (!S.enabled) return;
      var step = spacing();

      for (var i = 0; i < cards.length; i++) {
        var card = cards[i];
        var d = i - S.active;
        var ad = Math.abs(d);

        if (ad > REACH) {
          // Park offstage on the correct side so the next move is a slide-in.
          var off = (d > 0 ? 1 : -1) * (step * (REACH + 1.4));
          card.style.transform =
            'translate3d(' + off + 'px,0,-520px) rotateY(' + (d > 0 ? -46 : 46) + 'deg)';
          card.style.opacity = '0';
          card.style.filter = 'blur(6px)';
          card.style.zIndex = '1';
          card.style.pointerEvents = 'none';
          card.classList.remove('is-active');
          card.removeAttribute('aria-current');
          card.setAttribute('aria-hidden', 'true');
          continue;
        }

        // The coverflow: neighbours slide out, turn TOWARD the active card
        // (so their inner edges face you), sink in z and soften.
        var x     = d * step;
        var rotY  = d === 0 ? 0 : (d > 0 ? -30 : 30);
        var z     = -ad * 130;
        var y     = ad * 10;
        var scale = 1 - ad * 0.055;
        var op    = 1 - ad * 0.3;
        var blur  = ad * 1.7;

        card.style.transform =
          'translate3d(' + x + 'px,' + y + 'px,' + z + 'px) ' +
          'rotateY(' + rotY + 'deg) scale(' + scale + ')';
        card.style.opacity = String(Math.max(op, 0));
        card.style.filter = blur ? 'blur(' + blur.toFixed(1) + 'px) saturate(0.86)' : 'none';
        card.style.zIndex = String(100 - ad);
        card.style.pointerEvents = 'auto';
        card.removeAttribute('aria-hidden');

        if (d === 0) {
          card.classList.add('is-active');
          card.setAttribute('aria-current', 'true');
        } else {
          card.classList.remove('is-active');
          card.removeAttribute('aria-current');
        }
      }

      if (S.status) {
        var label = statusLabel(cards[S.active]);
        S.status.textContent = (S.active + 1) + ' / ' + cards.length +
          (label ? ' \u00b7 ' + label : '');
      }
      if (S.prevBtn) S.prevBtn.setAttribute('aria-disabled', S.active === 0 ? 'true' : 'false');
      if (S.nextBtn) S.nextBtn.setAttribute('aria-disabled', S.active === cards.length - 1 ? 'true' : 'false');
    }

    function goTo(i) {
      var next = Math.max(0, Math.min(cards.length - 1, i));
      if (next === S.active) return;
      S.active = next;
      render();
    }
    function next() { goTo(S.active + 1); }
    function prev() { goTo(S.active - 1); }

    function enable() {
      if (S.enabled) return;
      S.enabled = true;
      // The reel class is added here, not in the markup: with no JS the grid
      // stays a plain grid, so the enhancement can never leave a
      // half-positioned reel on screen.
      grid.classList.add('reel');
      for (var i = 0; i < cards.length; i++) cards[i].classList.add('reel-card');
      measure();
      if (S.controls) S.controls.hidden = false;
      if (S.active > cards.length - 1) S.active = cards.length - 1;
      render();
    }

    function clearInline() {
      for (var i = 0; i < cards.length; i++) {
        var c = cards[i];
        c.style.transform = '';
        c.style.opacity = '';
        c.style.filter = '';
        c.style.zIndex = '';
        c.style.height = '';
        c.style.pointerEvents = '';
        c.classList.remove('is-active');
        c.removeAttribute('aria-current');
        c.removeAttribute('aria-hidden');
      }
      grid.style.height = '';
      grid.classList.remove('is-dragging');
    }

    function disable() {
      if (!S.enabled) return;
      S.enabled = false;
      clearInline();
      grid.classList.remove('reel');
      for (var i = 0; i < cards.length; i++) cards[i].classList.remove('reel-card');
      if (S.controls) S.controls.hidden = true;
    }

    function sync() {
      if (shouldRun()) enable();
      else disable();
    }

    function reflow(immediate) {
      if (immediate) {
        sync();
        if (S.enabled) { measure(); render(); }
        return;
      }
      clearTimeout(S.rTimer);
      S.rTimer = setTimeout(function () {
        var was = S.enabled;
        sync();
        if (was && S.enabled) { measure(); render(); }
      }, 150);
    }

    // ── Controls ──────────────────────────────────────────────
    if (S.prevBtn) S.prevBtn.addEventListener('click', prev);
    if (S.nextBtn) S.nextBtn.addEventListener('click', next);

    // ── Keyboard (roving focus on the rack) ───────────────────
    grid.setAttribute('tabindex', '0');
    grid.setAttribute('role', 'group');
    if (!grid.getAttribute('aria-label')) {
      grid.setAttribute('aria-label', 'Card reel — use arrow keys to browse');
    }
    grid.addEventListener('keydown', function (e) {
      if (!S.enabled) return;
      if (e.key === 'ArrowRight') { e.preventDefault(); next(); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
      else if (e.key === 'Home') { e.preventDefault(); goTo(0); }
      else if (e.key === 'End') { e.preventDefault(); goTo(cards.length - 1); }
    });

    // ── Click a neighbour to focus it ─────────────────────────
    cards.forEach(function (card, i) {
      card.addEventListener('click', function (e) {
        if (!S.enabled || i === S.active) return;
        if (e.target.closest('a')) return;     // never hijack a real link
        e.preventDefault();
        goTo(i);
      });
    });

    // ── Drag to spin (pointer events, 1:1 while dragging) ─────
    grid.addEventListener('pointerdown', function (e) {
      if (!S.enabled || e.button !== 0) return;
      if (e.target.closest('a')) return;
      S.dragging = true;
      S.dragged = false;
      S.startX = e.clientX;
      S.startY = e.clientY;
      S.pointerId = e.pointerId;
    });

    grid.addEventListener('pointermove', function (e) {
      if (!S.dragging) return;
      var dx = e.clientX - S.startX;
      var dy = e.clientY - S.startY;

      // Let a vertical gesture be a page scroll, not a spin.
      if (!S.dragged && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 10) {
        S.dragging = false;
        return;
      }
      if (Math.abs(dx) > 6 && !S.dragged) {
        S.dragged = true;
        grid.classList.add('is-dragging');
        try { grid.setPointerCapture(S.pointerId); } catch (err) { /* no-op */ }
      }
    });

    function endDrag(e) {
      if (!S.dragging) return;
      S.dragging = false;
      grid.classList.remove('is-dragging');
      if (!S.dragged) return;      // a tap, not a drag — the click handler decides

      var dx = (e.clientX || 0) - S.startX;
      var threshold = Math.max(40, spacing() * 0.22);
      if (dx <= -threshold) next();
      else if (dx >= threshold) prev();
      e.preventDefault();          // suppress the click that follows a drag
    }

    grid.addEventListener('pointerup', endDrag);
    grid.addEventListener('pointercancel', function () {
      S.dragging = false;
      grid.classList.remove('is-dragging');
    });

    S.reflow = reflow;
    S.isEnabled = function () { return S.enabled; };
    S.cardCount = function () { return cards.length; };
    reels.push(S);
    sync();
  }

  // The case grid is declared first in the DOM; initReel keeps DOM order.
  var grids = document.querySelectorAll('[data-reel]');
  for (var g = 0; g < grids.length; g++) initReel(grids[g]);

  // One shared listener set for every reel on the page.
  var allTimer = null;
  function reflowAll() {
    clearTimeout(allTimer);
    allTimer = setTimeout(function () {
      for (var i = 0; i < reels.length; i++) reels[i].reflow();
    }, 150);
  }
  window.addEventListener('resize', reflowAll);
  if (mqReduce.addEventListener) {
    mqReduce.addEventListener('change', reflowAll);
    mqNarrow.addEventListener('change', reflowAll);
  }

  // Late-loading brand logos and fonts change card heights.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      for (var i = 0; i < reels.length; i++) reels[i].reflow(true);
    });
  }
  window.addEventListener('load', function () {
    for (var i = 0; i < reels.length; i++) reels[i].reflow(true);
  });

  window.__reels = reels;   // exposed for the verification harness
})();

/* ============================================================
   MOTION LAYER — scroll-scrubbed reveals, parallax, inertial scroll
   ============================================================
   The MOTION 2 dial on this site was overruled ("I want motion").
   Measured before this layer: 0 elements moving with no input on a
   mid-page viewport, 0 transforms driven by scrolling, and 63 of the
   site's 67 infinite animations buried in the 3.2s #sg-intro splash
   — all the energy in a screen most visitors skip, then a dead page.
   (Superseded: that splash was a 295KB inline Singapore map, since
   replaced by the cherry-blossom film. The measurement is kept as the
   reason this layer exists, not as a description of the page today.)

   What this layer does:
     · scroll-SCRUBBED reveals — position-driven, not a one-shot fire
     · parallax on whole blocks, so the page keeps answering the scroll
     · inertial scroll, so every gesture has weight
     · a reading rail

   Removed after review, and NOT to be re-added without a rethink:
     · the ambient aurora (a fixed drifting colour wash under everything —
       it competed with the page's own animation)
     · the method marquee (a scrolling word band — a 1990s ticker idiom that
       repeated what the hero already said twice)

   The "too kiddish" rule still holds inside the evidence sections:
   no new loops on the case cards, the stats or the cost table.

   Degradation: reduced-motion users get none of it (CSS hides the rail and
   this IIFE returns before wiring anything). With no JS the inline
   transform/opacity are never written, so every element shows its natural
   final state.
   ============================================================ */
(function () {
  'use strict';

  var mqReduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  // The ambient aurora that used to be created here was REMOVED 19 Oct 2026:
  // a fixed full-viewport colour drift underneath every reveal competed with
  // the page's own animation. See the note in draft.css.

  var rail = document.createElement('div');
  rail.className = 'scroll-progress';
  rail.setAttribute('aria-hidden', 'true');
  document.body.appendChild(rail);

  if (mqReduce.matches) return;   // CSS hides both; nothing to drive

  // Scrub targets. Headings and cards ONLY — body copy (.lead, .kicker) is
  // deliberately excluded: dimming paragraphs while they are being read is
  // a readability cost, not a flourish.
  var SCRUB_SEL = '.hero h1, .section h2, .offer-card, .fork-card, .card-item, .stat-card';

  // Blocks that drift at their own rate. .hero-flow is excluded on purpose:
  // its transform is owned by a CSS .in-view animation, and an inline
  // transform would lose to it.
  // Strength raised -16 -> -80: at -16 the measured displacement was 30px
  // across 500px of scrolling, which is below the perceptual floor.
  var PARALLAX = [
    { sel: '[data-reel]', strength: -80 }
  ];

  var scrubEls = [];
  var parEls = [];
  var vh = window.innerHeight;
  var rafId = null;

  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

  function collect() {
    scrubEls = [];
    var found = document.querySelectorAll(SCRUB_SEL);
    for (var i = 0; i < found.length; i++) {
      var el = found[i];
      // The coverflow owns every transform on its own cards.
      if (el.closest('[data-reel]')) continue;
      el.classList.add('scrub');
      scrubEls.push(el);
    }

    parEls = [];
    PARALLAX.forEach(function (cfg) {
      var els = document.querySelectorAll(cfg.sel);
      for (var k = 0; k < els.length; k++) {
        els[k].classList.add('parallax');
        parEls.push({ el: els[k], strength: cfg.strength });
      }
    });
  }

  function frame() {
    rafId = null;
    var y = window.pageYOffset || document.documentElement.scrollTop || 0;

    // Reading rail — how far through the page you are.
    var max = document.documentElement.scrollHeight - vh;
    rail.style.transform = 'scaleX(' + (max > 0 ? clamp01(y / max) : 0).toFixed(4) + ')';

    // Scrub: 0 while the element is low in the viewport, 1 once it settles.
    for (var i = 0; i < scrubEls.length; i++) {
      var el = scrubEls[i];
      var r = el.getBoundingClientRect();
      if (r.bottom < -120 || r.top > vh + 120) continue;   // offscreen: leave alone
      var start = vh * 0.94;
      var end = vh * 0.52;
      var t = clamp01((start - r.top) / (start - end));
      if (t >= 1) {
        // Settle to natural state and hand transform back to the CSS hover
        // lift — leaving an inline transform would kill every :hover rise.
        if (el.style.transform) { el.style.transform = ''; el.style.opacity = ''; }
      } else {
        // 26px was imperceptible (measured: 30px max across 500px of scroll).
        // 64px with a deeper fade reads as motion while staying understated.
        el.style.transform = 'translate3d(0,' + ((1 - t) * 64).toFixed(1) + 'px,0)';
        el.style.opacity = (0.16 + t * 0.84).toFixed(3);
      }
    }

    // Parallax: drift in proportion to distance from the viewport centre.
    for (var j = 0; j < parEls.length; j++) {
      var pe = parEls[j];
      var pr = pe.el.getBoundingClientRect();
      if (pr.bottom < -240 || pr.top > vh + 240) continue;
      var centre = pr.top + pr.height / 2;
      var off = (centre - vh / 2) / vh;
      pe.el.style.transform = 'translate3d(0,' + (off * pe.strength).toFixed(1) + 'px,0)';
    }
  }

  function onScroll() {
    if (rafId === null) rafId = requestAnimationFrame(frame);
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', function () {
    vh = window.innerHeight;
    onScroll();
  }, { passive: true });

  if (mqReduce.addEventListener) mqReduce.addEventListener('change', function () { onScroll(); });

  /* ── 6. INERTIAL SCROLL (desktop / fine pointer only) ──
     Native scroll feels dead next to Lenis-style inertia, and this is the one
     change that alters the feel of EVERY gesture rather than one section.

     Implemented by easing the REAL scroll position (window.scrollTo) rather
     than transform-hijacking the page, so a fixed header, sticky elements,
     anchor targets and every IntersectionObserver above keep working
     untouched. Easing the document also keeps the scrollbar honest.

     Touch devices are deliberately excluded — their native momentum is better
     than anything we would synthesise. */
  var mqFine = window.matchMedia('(pointer: fine)');
  if (mqFine.matches) {
    var root = document.documentElement;
    var ease = 0.13;
    var target = window.pageYOffset || 0;
    var current = target;
    var driving = false;
    var maxScroll = function () { return root.scrollHeight - window.innerHeight; };

    root.style.scrollBehavior = 'auto';   // we own easing from here on

    var drive = function () {
      var diff = target - current;
      current += diff * ease;
      if (Math.abs(diff) < 0.5) current = target;
      window.scrollTo(0, current);
      if (Math.abs(target - current) < 0.5) { driving = false; return; }
      requestAnimationFrame(drive);
    };
    var startDrive = function () {
      if (!driving) { driving = true; requestAnimationFrame(drive); }
    };

    // Never swallow the gesture when it belongs to a nested scroll area.
    var inScrollable = function (el) {
      while (el && el !== document.body && el.nodeType === 1) {
        var st = getComputedStyle(el);
        if (/(auto|scroll)/.test(st.overflowY) && el.scrollHeight > el.clientHeight + 2) return true;
        el = el.parentElement;
      }
      return false;
    };

    window.addEventListener('wheel', function (e) {
      if (e.ctrlKey || e.metaKey) return;          // never eat pinch-zoom
      if (inScrollable(e.target)) return;          // let inner panes scroll
      e.preventDefault();
      target = Math.max(0, Math.min(maxScroll(), target + e.deltaY));
      startDrive();
    }, { passive: false });

    // Keys, scrollbar drags and browser scroll restoration move the page
    // directly — resync so the next wheel gesture starts from real position.
    window.addEventListener('scroll', function () {
      if (!driving) { target = current = window.pageYOffset || 0; }
    }, { passive: true });

    // With scroll-behavior off, anchor jumps would land abruptly. Drive them.
    document.addEventListener('click', function (e) {
      var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!a) return;
      var href = a.getAttribute('href');
      if (!href || href.length < 2) return;
      var el;
      try { el = document.querySelector(href); } catch (err) { return; }
      if (!el) return;
      e.preventDefault();
      var top = el.getBoundingClientRect().top + (window.pageYOffset || 0) - 84;
      target = Math.max(0, Math.min(maxScroll(), top));
      startDrive();
    });
  }

  collect();
  frame();   // establish initial state so nothing pops on the first scroll

  window.__motion = {
    scrubCount: function () { return scrubEls.length; },
    parallaxCount: function () { return parEls.length; },
    auroraPresent: function () { return !!document.querySelector('.bg-aurora'); }
  };
})();
