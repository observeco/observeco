#!/bin/bash
# Verification entry point for the IG carousel series.
# Chains the render/overflow steps, then delegates content gates to verify_gates.py.
#
#   bash verify_ig.sh             # every post
#   bash verify_ig.sh post01      # one post
set -u
. "$(dirname "$0")/common.sh"
POST="${1:-post}"
cd "$DIR" || exit 1
fails=0

hdr() { echo; echo "[$1] $2"; }

echo "=============================================="
echo " IG SERIES VERIFICATION — ${POST}*"
echo "=============================================="

hdr 1 "rebuild from generator (reproducibility)"
if python3 build_ig_slides.py >/dev/null; then echo "  OK   generator ran"; else
  echo "  FAIL generator errored"; exit 1
fi

hdr 2 "render PNGs (1080x1350; font pre-flight guards fallback fonts)"
# Do NOT pipe render_ig.sh into sed: the pipeline's exit status comes from sed, so a
# render ABORT (e.g. the font pre-flight failing) would be swallowed and the script
# would happily verify STALE PNGs. Capture, check, then filter.
render_out=$(bash render_ig.sh "$POST*.html" 2>&1); render_rc=$?
printf '%s\n' "$render_out" | grep -i 'font pre-flight' | sed 's/^/  /'
if [ "$render_rc" -ne 0 ]; then
  printf '%s\n' "$render_out" | grep -i 'abort\|font pre-flight' | sed 's/^/  !! /'
  echo "  FAIL render_ig.sh exited $render_rc — PNGs may be stale"
  fails=1
fi
echo "  OK   rendered $(printf '%s\n' "$render_out" | grep -c '\.png$') slides (dims asserted in gate 4)"

hdr 3 "DOM overflow (live layout boxes)"
bash check_fit.sh 2>&1 | sed 's/^/  /'

hdr 4 "content / token / structure"
$PY verify_gates.py "$POST" || fails=1

hdr 5 "contact sheet (freshness after rebuild)"
$PY contact_sheet.py "$POST" 2>&1 | sed 's/^/  /'

echo
echo "=============================================="
[ "$fails" -eq 0 ] && echo " ALL GATES PASSED" || echo " GATE FAILURES — see FAIL lines above"
echo "=============================================="
exit "$fails"
