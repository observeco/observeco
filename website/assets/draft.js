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
   3D PARTICLE NETWORK — dynamic connecting-dots background
   A fixed canvas behind the page draws 3D-projected particles that
   slowly drift and rotate; nearby nodes link into connecting lines,
   and each node lives/fades on its own lifecycle so dots keep
   appearing and disappearing — a living 3D mind map.

   Engineered, not hand-drawn:
   - True 3D: points live in x/y/z space, projected with perspective
     and rotated around two axes — depth reads via scale + alpha.
   - Spatially-hashed neighbor lookup for smooth O(n) links.
   - Lifecycle fade: each dot materializes (0->1), holds, dissolves
     (1->0), reborn at a fresh position — the appearing/disappearing
     loop the brief asks for.
   - Teal constellation accent that fits the consulting paper theme.
   ============================================================ */
(function () {
  'use strict';

  // Respect reduced-motion: draw static dots only, no loop.
  var REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Skip when the body is absent or the site opts out.
  if (!document.body || document.documentElement.getAttribute('data-dots') === 'off') return;

  var canvas = document.createElement('canvas');
  canvas.className = 'dots3d-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.appendChild(canvas);
  var ctx = canvas.getContext('2d');
  if (!ctx) { canvas.remove(); return; }

  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0, cx = 0, cy = 0;
  var SPREAD;

  function resize() {
    // Fixed-position canvas — only the viewport is visible, so allocate
    // just the viewport. Using scrollHeight here would allocate a huge
    // offscreen buffer for tall pages and waste memory.
    W = canvas.width = Math.floor(window.innerWidth * dpr);
    H = canvas.height = Math.floor(window.innerHeight * dpr);
    cx = W / 2;
    cy = H / 2 * 0.8; // bias the cloud slightly up so hero reads clean
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
  }
  resize();
  window.addEventListener('resize', resize);

  // Palette — paper theme, teal constellation.
  var TEAL = [14, 110, 92];    // insight teal
  var INK = [27, 31, 36];      // ink
  var LINE_MAX = 150 * dpr;    // projected link distance

  var COUNT = clampCount();
  var particles = new Array(COUNT);
  SPREAD = 620 * dpr;
  var FOCAL = 700 * dpr;
  var TILT = 0.5;
  var ROT_Y = 0;
  var ROT_SPEED = 0.00012;    // barely-there ambient drift

  function clampCount() {
    var w = window.innerWidth;
    var base = w < 600 ? 55 : w < 1100 ? 80 : 110;
    var hFactor = 0.8 + 0.4 * (Math.min(window.innerHeight, 1200) / 900);
    return Math.round(base * hFactor);
  }

  function spawn(p) {
    p.x = (Math.random() - 0.5) * SPREAD * 2;
    p.y = (Math.random() - 0.5) * SPREAD * 2.6;
    p.z = (Math.random() - 0.5) * SPREAD * 1.2;
    p.life = 0;
    p.phase = 'in';
    p.hold = 5000 + Math.random() * 9000;   // long hold = dots mostly at rest
    p.vx = (Math.random() - 0.5) * 0.06;
    p.vy = (Math.random() - 0.5) * 0.06;
    p.vz = (Math.random() - 0.5) * 0.035;
    p.r = (1.1 + Math.random() * 1.6) * dpr;   // smaller dots
  }
  for (var i = 0; i < COUNT; i++) {
    particles[i] = {};
    spawn(particles[i]);
    // Stagger initial lifecycle so the field is already alive.
    particles[i].life = Math.random();
    particles[i].phase = Math.random() < 0.5 ? 'hold' : 'out';
  }

  // Spatial hash for fast neighbor links.
  var cell = Math.ceil(LINE_MAX);
  var grid = {};

  function buildGrid() {
    grid = {};
    for (var i = 0; i < COUNT; i++) {
      var p = particles[i];
      var gx = Math.floor(p.sx / cell);
      var gy = Math.floor(p.sy / cell);
      var key = gx + ':' + gy;
      (grid[key] = grid[key] || []).push(p);
    }
  }

  var last = 0;

  function frame(now) {
    var dt = Math.min(now - (last || now), 40);
    last = now;

    ctx.clearRect(0, 0, W, H);

    ROT_Y += ROT_SPEED * dt;
    var sinY = Math.sin(ROT_Y), cosY = Math.cos(ROT_Y);
    var sinT = Math.sin(TILT), cosT = Math.cos(TILT);

    // 1) advance lifecycle + project
    for (var i = 0; i < COUNT; i++) {
      var p = particles[i];

      if (!REDUCED) {
        if (p.phase === 'in') {
          p.life += 0.006 * (dt / 16.6);
          if (p.life >= 1) { p.life = 1; p.phase = 'hold'; p.hold = 2600 + Math.random() * 5200; }
        } else if (p.phase === 'hold') {
          p.hold -= dt;
          if (p.hold <= 0) p.phase = 'out';
        } else {
          p.life -= 0.004 * (dt / 16.6);
          if (p.life <= 0) spawn(p);
        }
        p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
        var h = SPREAD;
        if (p.x < -h) p.x = h; if (p.x > h) p.x = -h;
        if (p.y < -h * 1.3) p.y = h * 1.3; if (p.y > h * 1.3) p.y = -h * 1.3;
        if (p.z < -h) p.z = h; if (p.z > h) p.z = -h;
      }

      var x1 = p.x * cosY - p.z * sinY;
      var z1 = p.x * sinY + p.z * cosY;
      var y2 = p.y * cosT - z1 * sinT;
      var z2 = p.y * sinT + z1 * cosT;

      var zf = 1 + z2 / FOCAL;
      var sf = 1 / zf;
      p.sx = cx + x1 * sf;
      p.sy = cy + y2 * sf;
      p.depth = Math.min(sf, 1.6);
      p.alpha = REDUCED ? 0.2 : (0.18 + 0.4 * p.life) * (0.22 + 0.5 * Math.min(p.depth, 1));
    }

    buildGrid();

    // 2) links (under the dots) — very faint ink, fade with distance + lifecycle
    ctx.lineWidth = 0.8;
    for (var k in grid) {
      var list = grid[k];
      for (var a = 0; a < list.length; a++) {
        var pa = list[a];
        for (var b = a + 1; b < list.length; b++) {
          var pb = list[b];
          var dx = pa.sx - pb.sx, dy = pa.sy - pb.sy;
          var d2 = dx * dx + dy * dy;
          if (d2 > LINE_MAX * LINE_MAX) continue;
          var alpha = (1 - Math.sqrt(d2) / LINE_MAX);
          alpha *= pa.alpha * pb.alpha * 0.32;
          if (alpha <= 0.015) continue;
          ctx.strokeStyle = 'rgba(' + INK[0] + ',' + INK[1] + ',' + INK[2] + ',' + alpha.toFixed(3) + ')';
          ctx.beginPath();
          ctx.moveTo(pa.sx, pa.sy);
          ctx.lineTo(pb.sx, pb.sy);
          ctx.stroke();
        }
      }
    }

    // 3) dots — teal halo for near, teal/ink body by depth
    for (var j = 0; j < COUNT; j++) {
      var q = particles[j];
      var qa = q.alpha;
      if (qa <= 0.02) continue;
      var r = q.r * (1 / q.depth) * 0.9;
      if (r > 4.5 * dpr) r = 4.5 * dpr;
      var near = q.depth > 0.7;
      if (near) {
        ctx.fillStyle = 'rgba(' + TEAL[0] + ',' + TEAL[1] + ',' + TEAL[2] + ',' + (qa * 0.10).toFixed(3) + ')';
        ctx.beginPath(); ctx.arc(q.sx, q.sy, r * 2.5, 0, 6.2832); ctx.fill();
      }
      ctx.fillStyle = 'rgba(' + (near ? TEAL[0] : INK[0]) + ',' + (near ? TEAL[1] : INK[1]) + ',' + (near ? TEAL[2] : INK[2]) + ',' + qa.toFixed(3) + ')';
      ctx.beginPath(); ctx.arc(q.sx, q.sy, r, 0, 6.2832); ctx.fill();
    }

    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
})();
