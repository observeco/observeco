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
