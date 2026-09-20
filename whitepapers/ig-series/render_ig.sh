#!/bin/bash
# Render IG carousel slides to PNG at exactly 1080x1350.
# Chrome headless at window-size 1080x1350 => PNG is the full slide.
set -u
. "$(dirname "$0")/common.sh"

PATTERN="${1:-post*.html}"

# --- pre-flight: web fonts must actually resolve in this headless Chrome -------
# The slides request Playfair Display + Inter from the Google Fonts CDN. If the
# CDN is unreachable (offline, DNS hiccup, rate-limit), Chrome silently renders in
# Georgia/system fallbacks and every PNG is a visual regression with NO error and
# NO gate failure. Fail loudly here instead.
cat > /tmp/__fontcheck.html <<'EOF'
<html><head><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet"></head>
<body>
<!-- Chrome fetches a font face LAZILY: document.fonts.check() reports false for a
     face that no rendered text uses, and document.fonts.ready resolves without it.
     So the probe MUST render sample text in both faces before checking. -->
<div style="font:800 76px 'Playfair Display',serif">Playfair</div>
<div style="font:400 24px 'Inter',sans-serif">Inter</div>
<div id="__probe"></div><script>
document.fonts.ready.then(function(){var d=document.getElementById('__probe');
d.textContent='PLAYFAIR='+document.fonts.check('800 76px "Playfair Display"')
 +' INTER='+document.fonts.check('400 24px "Inter"');});
</script></body></html>
EOF
fc=$("$CHROME" --headless --disable-gpu --window-size=1080,400 --virtual-time-budget=8000 \
      --dump-dom "file:///tmp/__fontcheck.html" 2>/dev/null \
      | tr -d '\n' | sed -n 's/.*id="__probe">\([^<]*\)<.*/\1/p')
echo "font pre-flight: ${fc:-NO_RESULT}"
case "$fc" in
  *PLAYFAIR=true*INTER=true*) : ;;
  *) echo "  ABORT: web fonts did not load — slides would render in fallback fonts." >&2
     echo "  Check network access to fonts.googleapis.com, then re-run." >&2
     exit 1 ;;
esac

for f in "$DIR"/$PATTERN; do
  [ -e "$f" ] || continue
  base=$(basename "$f" .html)
  "$CHROME" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --virtual-time-budget=4000 \
    --screenshot="$DIR/$base.png" --window-size=1080,1350 \
    "file://$f" >/dev/null 2>&1
  echo "$base.png"
done

# Dimensions are asserted by verify_gates.py ("dims 1080x1350") — not repeated here.
