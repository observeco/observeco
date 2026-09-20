#!/bin/bash
# Overflow / fit check for IG slides.
# Reads the LIVE DOM after layout (not a guess) by injecting a measurement probe
# that runs before --dump-dom captures the tree.
set -u
. "$(dirname "$0")/common.sh"

POST="${1:-post}"

for f in "$DIR"/$POST*.html; do
  [ -e "$f" ] || continue
  base=$(basename "$f" .html)
  probe="/tmp/probe-$base.html"

  # probe copy: drop the closing body tag, append the measuring script
  {
    sed 's#</body>##' "$f"
    cat <<'JS'
<script>
(function(){
  var s = document.querySelector('.slide'),
      b = document.querySelector('.slide-body'),
      f = document.querySelector('.slide-foot');   // NULL on a bare cover slide
  // A missing node must be reported, not silently swallowed — an empty probe
  // output previously read as "no overflow". Fail loud (R12).
  if (!s || !b) {
    var d0 = document.createElement('div');
    d0.id = '__probe';
    d0.textContent = 'PROBE_ERROR=missing .slide or .slide-body';
    document.body.appendChild(d0);
    return;
  }
  var out = [
    'SLIDE_SCROLL=' + s.scrollHeight,
    'SLIDE_CLIENT=' + s.clientHeight,
    'BODY_SCROLL='  + b.scrollHeight,
    'BODY_CLIENT='  + b.clientHeight,
    'BODY_TOP='     + Math.round(b.getBoundingClientRect().top),
    'BODY_BOTTOM='  + Math.round(b.getBoundingClientRect().bottom),
    'FOOT_BOTTOM='  + (f ? Math.round(f.getBoundingClientRect().bottom) : 'none')
  ];
  // widest element: anything past 1080 - 96 (safe margin) is a real overflow
  var maxR = 0, worst = '';
  document.querySelectorAll('.slide *').forEach(function(el){
    var r = el.getBoundingClientRect();
    if (r.right > maxR) { maxR = r.right; worst = el.className || el.tagName; }
  });
  out.push('MAX_RIGHT=' + Math.round(maxR), 'WORST=' + worst);

  // ---- text-collision gate (Sean's #1 visual objection) ----
  // Collect leaf text nodes (an element that has text but no text-bearing child)
  // and report any pair whose boxes intersect. Deterministic, no vision model.
  var els = [];
  document.querySelectorAll('.slide-body *').forEach(function(el){
    if (!el.textContent.trim()) return;
    for (var i = 0; i < el.children.length; i++) {
      if (el.children[i].textContent.trim()) return;   // not a leaf — skip
    }
    // Use PER-LINE fragments. An inline element that wraps returns a single
    // union box from getBoundingClientRect(), which falsely "overlaps" the
    // sibling on the line above. getClientRects() gives one box per line.
    var rects = el.getClientRects();
    for (var k = 0; k < rects.length; k++) {
      var r = rects[k];
      if (r.width < 1 || r.height < 1) continue;
      els.push({ tag: (el.className || el.tagName), r: r });
    }
  });
  var ovl = [];
  for (var a = 0; a < els.length; a++) {
    for (var b = a + 1; b < els.length; b++) {
      var A = els[a].r, B = els[b].r;
      var ix = Math.min(A.right, B.right) - Math.max(A.left, B.left);
      var iy = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top);
      if (ix > 1 && iy > 1) {
        ovl.push(els[a].tag + '~' + els[b].tag + ':' + Math.round(ix) + 'x' + Math.round(iy));
      }
    }
  }
  out.push('OVERLAPS=' + ovl.length, 'OVL=' + (ovl.slice(0, 4).join(',') || 'none'));
  var d = document.createElement('div');
  d.id = '__probe';
  d.textContent = out.join(' ');
  document.body.appendChild(d);
})();
</script>
</body></html>
JS
  } > "$probe"

  # --dump-dom echoes the script source too, so extract the probe div payload
  dom=$("$CHROME" --headless --disable-gpu --window-size=1080,1350 --virtual-time-budget=2500 \
        --dump-dom "file://$probe" 2>/dev/null)
  res=$(printf '%s' "$dom" | tr -d '\n' | sed -n 's/.*id="__probe">\([^<]*\)<.*/\1/p')
  echo "$base"
  echo "   $res"
done
