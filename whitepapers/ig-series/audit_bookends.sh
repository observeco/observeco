#!/bin/bash
# Bookend audit: every post must open with the front cover and close with the back cover.
cd /Users/seanfzc/projects/observeco-main/whitepapers/ig-series || exit 1

for p in post01 post02; do
  first=$(ls ${p}-slide01*.html 2>/dev/null)
  last=$(ls ${p}-slide*.html 2>/dev/null | tail -1)
  echo "--- $p ---"
  if grep -q 'class="cover-full"' "$first"; then
    echo "  FIRST: front cover (full-bleed)  img=$(grep -o 'assets/[a-z-]*\.png' "$first" | head -1)"
  else
    echo "  FIRST: !! NOT a cover"
  fi
  if grep -q 'class="artifact"' "$last"; then
    echo "  LAST : back cover artifact       img=$(grep -o 'assets/[a-z-]*\.png' "$last" | head -1)  ($(basename "$last"))"
  else
    echo "  LAST : no back cover artifact    ($(basename "$last"))"
  fi
done
