# X publish record — 20260917 packages

Account: **@1571keplerj** (ObserveCo), X Premium confirmed (`verified_type: blue`, `subscription_type: Premium`).
Auth route: **OAuth1** (HMAC-SHA1) using the consumer key/secret + user token stored by the local Postiz stack.
Signing gotcha: **query params must be included in the signature base**, and the base URL must have its query stripped.

## ✅ DONE — Retweets (verified live)

| Topic | ST post id | RT post id | Verified |
|---|---|---|---|
| Aomorie | `2100505088527667213` | `2100556338854260746` | yes — `retweeted_by` lists `1571keplerj` |
| Construction robots | `2100498693346427019` | `2100556349847613733` | yes — timeline shows `[retweeted]` |

Chosen as canonical because `@straits_times` is the main account (the `@ST_LifeTweets` duplicates were on the same
topic; the Aomorie post also had an earlier variant at `2100396920103375160` with the same bit.ly link).
Verify any time:
```bash
GET /2/users/2054901336500756480/tweets?max_results=5&tweet.fields=referenced_tweets
GET /2/tweets/2100505088527667213/retweeted_by
```

## ⏳ BLOCKED — the two X Articles

Payloads are **built, validated and ready**. Blocked only by a hard per-user daily cap on X's side.

**The cap that bit us (not documented in the endpoint reference):**
| Endpoint | Header | Cap |
|---|---|---|
| `POST /2/articles/draft` | `x-user-limit-24hour-limit` | **10 / 24h** |
| `POST /2/articles/{id}/publish` | `x-user-limit-24hour-limit` | **5 / 24h** |

On 2026-09-17 both hit `x-user-limit-24hour-remaining: 0`, resetting **2026-09-18 18:00 SGT**. The 15-minute
`x-rate-limit-*` headers read a healthy 39,997 — **always read the 24-hour header, or you'll misdiagnose the block.**

Cause of exhaustion: reverse-engineering the payload schema by trial and error against the live endpoint.
**Do not do that.** The authoritative schema is free and offline: `GET https://api.x.com/2/openapi.json`.

### Second, separate blocker — OAuth1 cannot publish
Creating a draft over OAuth1 works (201). Publishing one returns:
```
POST /2/articles/{id}/publish -> 400
{"errors":[{"message":"The specified article could not be found or is not owned by the authenticated user."}]}
```
This was the **first publish call of the day, with full quota** — so it is an ownership failure, not throttling.
Note the earlier skill reference claimed OAuth1 was "verified 201": that 201 was **draft creation**, never the publish.
**OAuth1 publish is unverified.** The scheduled job retries with a 60s settle delay in case the draft simply
wasn't indexed yet; if it fails again, the fix is a **fresh OAuth2 user token with `tweet.write`** (headless
PKCE flow — needs Sean to authorise one URL in a browser).

## Payload shape (validated against openapi.json, dry-run clean)

| Article | Title | Blocks | Entities |
|---|---|---|---|
| Aomorie | "Aomorie Is Genuinely Different. That's Exactly Why It's Still Invisible." | 69 | 3 image + 1 markdown table |
| Construction robots | "Singapore's Construction Robots Aren't Arriving Because They're Better..." | 63 | 3 image + 1 markdown table |

Both carry a `cover_media` banner. Dry-run check confirmed: no schema violations, no `**` or `#` marker leaks.

## How to run / check

```bash
cd /Users/seanfzc/projects/observeco-main/content-writing/20260917
/usr/bin/python3 publish_articles.py          # publishes both, writes the log
/usr/bin/python3 ~/.hermes/scripts/check_articles_published.py   # silent if both live
```
Scheduled job `59fda857044b` ran/will run at **2026-09-18 18:07 SGT** (one-shot).

## Verification discipline
The publish script writes `x-article-publish-results.json`. A **self-report is not proof** — confirm each
article id with `GET https://api.x.com/2/articles/<id>` before telling Sean it is live.
