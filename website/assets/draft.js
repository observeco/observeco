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
   BREATHING GLOW — ambient background
   A fixed canvas behind the page draws ONE large, heavily-blurred
   amber radial glow, centred on the viewport, that slowly breathes
   in opacity — from a faint wash to a soft warm glow and back.
   Nothing travels: there is no panel, no band, no translation, so
   nothing reads as a moving object. It reads as light through a
   window — the eye registers warmth, not motion.

   Engineered:
   - Single fixed canvas, full viewport, behind all content.
   - Radial amber gradient (warm, high-luminance) tuned to a lower
     peak opacity than teal so it doesn't wash the text on paper.
   - Alpha eased with a long 8s sine loop. Zero motion of position.
   - Respects prefers-reduced-motion: draws one static frame, no loop.
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

  // Amber glow — reads as light on warm paper, not a coloured object.
  // Warm/high-luminance, so peak alpha kept moderate (0.34) so the text
  // stays readable. The glow is one big centred radial that breathes.
  var AMBER = [201, 138, 61];     // warm amber (sits on #f7f6f3 paper)
  var CYCLE = 8000;               // full breathe cycle in ms
  var PEAK = 0.34;                // peak alpha at the bright phase
  var MIN = 0.10;                 // resting alpha at the dim phase

  function draw(alpha) {
    ctx.clearRect(0, 0, W, H);
    // One large radial glow centred on the viewport, heavily blurred feel
    // (soft falloff -> reads as light, not a ring).
    var cx = W / 2, cy = H / 2, r = Math.max(W, H) * 0.8;
    var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    g.addColorStop(0.00, 'rgba(' + AMBER[0] + ',' + AMBER[1] + ',' + AMBER[2] + ',' + alpha + ')');
    g.addColorStop(0.55, 'rgba(' + AMBER[0] + ',' + AMBER[1] + ',' + AMBER[2] + ',' + (alpha * 0.45) + ')');
    g.addColorStop(1.00, 'rgba(' + AMBER[0] + ',' + AMBER[1] + ',' + AMBER[2] + ',0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }

  if (REDUCED) { draw(MIN); return; }

  var t0 = performance.now();
  function frame(now) {
    var t = (now - t0) % CYCLE;
    // Sine 0..1: bright at t=CYCLE/4, dim at t=0 and t=CYCLE/2.
    var k = (Math.sin((t / CYCLE) * Math.PI * 2 - Math.PI / 2) + 1) / 2;
    var alpha = MIN + (PEAK - MIN) * k;
    draw(alpha);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
