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

    function setOpen(open) {
      dd.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    // Click toggles (works on both desktop and mobile)
    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var isOpen = dd.classList.contains('open');
      closeAll(dd);
      if (!isOpen) setOpen(true);
    });

    // Desktop hover open
    dd.addEventListener('mouseenter', function () { setOpen(true); });
    dd.addEventListener('mouseleave', function () { setOpen(false); });
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
   MOVING GRADIENT WASH — ambient background
   A fixed canvas behind the page draws a soft vertical gradient
   (paper base with a gentle teal tint) that slowly drifts from
   the top of the viewport downward, then loops seamlessly. No
   dots, no lines, no motion of discrete elements — just a slow
   breathing wash of colour that reads as calm, premium ambience.

   Engineered:
   - Single fixed canvas, full viewport, behind all content.
   - Vertical gradient whose stops are periodic (start == end) so
     the downward drift wraps without a visible jump.
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

  // Paper base with a soft silver sheen. A "shiny silver" reads as a
  // highlight on light paper — a cool-grey band lighter than the page,
  // with a faint darker grey edge for the metallic feel.
  // ONE panel, HALF the canvas height (H/2), that drifts down the page
  // and loops. When the panel reaches the bottom it wraps: the part that
  // exits the bottom re-enters the top, so it reads as a single panel
  // looping — never two full panels on screen at once.
  var SILVER_LIGHT = [226, 228, 231];   // cool silver highlight
  var SILVER_DARK = [196, 199, 203];    // subtle grey edge for depth
  var CYCLE = 1.0;                      // gradient period in viewport-heights
  var SPEED = 0.0002;                   // drift speed (fraction of H per ms) — 3x slower

  function draw(offset) {
    // Clear first — the panel is semi-transparent, so without this it
    // would accumulate frame over frame and saturate.
    ctx.clearRect(0, 0, W, H);
    // ONE panel, H/2 tall. p is the panel's top edge, in [0, H].
    var panelH = 0.5 * H;
    var p = offset;
    drawPanel(p, panelH);
    // When the panel has moved more than H/2 down, the part that has
    // exited the bottom re-enters the top — the seamless loop.
    if (p > panelH) drawPanel(p - H, panelH);
  }

  function drawPanel(top, panelH) {
    var g = ctx.createLinearGradient(0, top, 0, top + panelH);
    g.addColorStop(0.00, 'rgba(' + SILVER_LIGHT[0] + ',' + SILVER_LIGHT[1] + ',' + SILVER_LIGHT[2] + ',0.00)');
    g.addColorStop(0.20, 'rgba(' + SILVER_LIGHT[0] + ',' + SILVER_LIGHT[1] + ',' + SILVER_LIGHT[2] + ',0.75)');
    g.addColorStop(0.30, 'rgba(' + SILVER_DARK[0] + ',' + SILVER_DARK[1] + ',' + SILVER_DARK[2] + ',0.30)');
    g.addColorStop(1.00, 'rgba(' + SILVER_LIGHT[0] + ',' + SILVER_LIGHT[1] + ',' + SILVER_LIGHT[2] + ',0.00)');
    ctx.fillStyle = g;
    ctx.fillRect(0, top, W, panelH);
  }

  if (REDUCED) { draw(0); return; }

  var offset = 0;
  var last = 0;
  function frame(now) {
    var dt = Math.min(now - (last || now), 40);
    last = now;
    offset += SPEED * dt * H;
    if (offset >= CYCLE * H) offset -= CYCLE * H;   // seamless loop
    draw(offset);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
