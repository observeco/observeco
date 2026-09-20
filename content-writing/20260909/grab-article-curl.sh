#!/bin/bash
# Submit the Grab car marketplace article as a DRAFT on @1571keplerj.
#
# STEP 1 (FREE): upload the cover image -> returns a media_id
# STEP 2 (CHARGED): create the article draft with that media_id as cover
#
# Run ONLY after X API credits are added (currently: credits depleted).
# This creates a draft you review in the X app, then publish manually.

COVER="/Users/seanfzc/projects/observeco-main/content-writing/20260909/cover-grab-car.png"

echo "=== STEP 1: upload cover (FREE) ==="
MEDIA_JSON=$(~/go/bin/xurl -X POST /2/media/upload \
  -H "Content-Type: application/json" \
  -d '{"media_category":"tweet_image","media_data":"$(base64 < "$COVER")"}')
echo "$MEDIA_JSON"
MEDIA_ID=$(echo "$MEDIA_JSON" | /Users/seanfzc/.local/bin/python3.11 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('media_id',''))" 2>/dev/null)
echo "MEDIA_ID=$MEDIA_ID"

echo "=== STEP 2: create article draft (CHARGED) ==="
# Patch the media_id into the payload, then submit
/Users/seanfzc/.local/bin/python3.11 -c "
import json
p=json.load(open('/Users/seanfzc/projects/observeco-main/content-writing/20260909/grab-article-draft.json'))
p['cover_media']={'media_category':'tweet_image','media_id':'$MEDIA_ID'}
json.dump(p, open('/Users/seanfzc/projects/observeco-main/content-writing/20260909/grab-article-draft.json','w'), ensure_ascii=False, indent=2)
"
~/go/bin/xurl -X POST /2/articles/draft \
  -H "Content-Type: application/json" \
  -d @"/Users/seanfzc/projects/observeco-main/content-writing/20260909/grab-article-draft.json"
