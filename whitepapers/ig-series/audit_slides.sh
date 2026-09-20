#!/bin/bash
# Report the archetype of each slide in a post, in order.
cd /Users/seanfzc/projects/observeco-main/whitepapers/ig-series || exit 1
post="${1:-post02}"
for f in $(ls ${post}-slide*.html | sort); do
  kind="text"
  grep -q 'class="cover-full"' "$f" && kind="FRONT COVER"
  grep -q 'class="artifact"'   "$f" && kind="BACK COVER"
  grep -q 'class="cols'        "$f" && kind="comparison"
  grep -q 'class="steps"'      "$f" && kind="steps"
  grep -q 'class="ledger"'     "$f" && kind="ledger"
  grep -q 'class="bars"'       "$f" && kind="bar chart"
  grep -q 'class="payoff"'     "$f" && kind="payoff"
  grep -q 'class="hero"'       "$f" && kind="big number"
  grep -q 'class="cover"'      "$f" && kind="hook headline"
  h=$(grep -o '<h2 class="stat-head">[^<]*' "$f" | sed 's/<h2 class="stat-head">//' | head -c 58)
  printf "%-3s %-14s %s\n" "$(basename "$f" | sed 's/.*-slide\([0-9]*\).*/\1/')" "$kind" "$h"
done
