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
