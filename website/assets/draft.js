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
