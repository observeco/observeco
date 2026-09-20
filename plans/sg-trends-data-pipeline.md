# ObserveCo — Singapore Trends Data Pipeline (data gathering for YOUR positioning call)

**Prepared by:** Gladwell — 2026-09-08
**Scope:** TikTok Ads Creative Center, Google Trends, Reddit, X, HN — **Singapore topics only.**
**Division of labor:** I gather + present data and insight. You decide positioning (no filter applied by me).

---

## 0. The one-sentence strategy

> Gather *what Singapore is talking about* from 5 free/cheap sources, present it with metadata (source, velocity, recency, sample of actual posts), and hand it to you to pick the topic with a positioning angle.

You don't need a scraper that fights anti-bot. All five sources have a **legal, stable, logged-out (or official) access path**. The job is plumbing each one, not scraping at scale.

---

## 1. Singapore-only data by source (what actually works, verified 2026-09-08)

### 🎵 TikTok Ads Creative Center (best free TikTok trend source)
- **Source of truth:** TikTok Creative Center **Trends Hub** — has a **region filter incl. Singapore**. The official, logged-out, free surface for rising hashtags/sounds/videos.
- **Access path:** Direct URL with region param, or Playwright headless export. No API scraping needed.
- **What you get per topic:** rising hashtags, sounds, videos, by region (SG). Creator + sound metadata.
- **Insight value:** *who in SG is creating, and on what*. Good for the "what are people making viral" layer.
- **Caveat:** It's a JS-heavy browser surface. Some SG data is thin because Singapore is a small market — TikTok's SG trend set is smaller than US/PH/ID. Expect ~tens of SG-relevant hashtags, not hundreds.
- **Recommendation:** Script a Playwright capture that saves the SG-filtered Trends Hub to a timestamped JSON/card. Low effort, high trust (official surface).

### 📈 Google Trends — **IMPORTANT 2026 change**
- **Official Google Trends API (alpha) launched July 2025** — `developers.google.com/search/apis/trends`. Supports **daily/weekly/monthly/yearly aggregation**, and **country + sub-region comparison** (Singapore included). This is now the *official* route, replacing unofficial wrappers.
- **But:** it's a gated **alpha** — you apply to be an alpha tester. Not open to everyone yet.
- **Fallback that still works (mostly):** `pytrends` wrapper — BUT widely reported **"pytrends is dead" in 2026** (Google tightened anti-bot). Treat pytrends as fragile; prefer an **unofficial API service** or the official alpha if you can get in.
- **Two access paths to consider:**
  1. **Zero-code:** the public `trends.google.com/trending?geo=SG` "Trending now – Singapore" page — gives the *actual daily SG trending searches* (news + product queries). Logged-out, free, stable. **Best quick-and-dirty SG snapshot.**
  2. **Automated:** apply for Trends API alpha; meanwhile use a maintained unofficial API (Glimpse, apiserpent, etc.) only if the free page is insufficient.
- **Insight value:** *interest velocity by query* in SG — the cleanest "what SG is searching for" signal. This is your highest-quality SG-intent source.
- **Recommendation:** Start with the free `geo=SG` trending page (curl + parse, zero deps), and simultaneously apply/note the official API alpha for later. Don't build on pytrends (fragile).

### 🔴 Reddit — **Singapore subreddits**
- **Confirmed SG subs:** `r/singapore`, `r/askSingapore` (also `r/SingaporeRaw`, `r/NUS`, `r/singaporehappenings`, `r/SingaporeEats` by niche).
- **Access:** Reddit's `https://www.reddit.com/r/{sub}/hot.json` / `top.json` returns clean JSON **without login** (free). Or use the JSON API via `requests`.
- **Insight value:** LONG-FORM Singapore discourse — the richest source for *how Singaporeans argue about products/companies* (= the frame you'll attack). AskSG is gold: what locals ask about companies, services, pricing, "hidden dark truths of SG industries."
- **Limitations:** Reddit API rate-limits free JSON (works for small volume daily pulls). PushShift (historical) is mostly dead; don't rely on it.
- **Recommendation:** Daily pull of `hot` + `top` from `r/singapore` + `r/askSingapore`, save title/score/num_comments/URL/permalinks. Filter out noise (property, MRT, politics) into your shortlist.

### 🐦 X (Twitter) — **Singapore trends via WOEID** (the key finding)
- **Confirmed:** X API v2 has a **"Trends by WOEID" endpoint** that returns trending topics for a specific geographic location (the official docs page confirmed it exists). **Singapore's WOEID = `1062617`** (Yahoo Where On Earth country code for SG).
- **Access:** `xurl` (we already own this tool) → `GET /2/trends/by/woeid/1062617`. Returns SG trending topics with tweet_count.
- **But — the hard truth:** X API **standard tier access is paid** (pay-per-use, minimum ~$5 buy-in; free tier is effectively gone in 2026). `xurl` currently **is not even installed** on this machine and `auth status` failed. So the Trends-by-WOEID path requires (a) installing xurl, (b) X API credits.
- **Cheaper alternative:** X's public **`https://x.com/trends/` isn't location-API'd**; the reliable SG trending list sits behind the API. For zero-cost, use the **web "Explore Trending" via Playwright geo'd browser** (fragile) OR just note that **Google Trends SG + Reddit SG already capture most of the SG topic signal** X would add.
- **Honest recommendation:** X Trends-by-WOEID is the *cleanest* SG-live-topic feed, but it's the **most costly + least-set-up** of the five. Set xurl up + buy minimal credits ONLY if you want true real-time SG trending. Otherwise it's a "phase 2" source.

### 🔥 Hacker News — NOT Singapore-native
- **Honest limitation:** HN has **no geographic filter**. It's a global tech/startup board. There is no "HN Singapore" surface.
- **How to make it SG-relevant, in order of usefulness:**
  1. **HN Algolia API** (`hn.algolia.com/api` — free) → search for Singapore-identified queries: `"Singapore"`, `"sg"`, `"STEng"`, `"Grab"`, `"Shopee"`, `"Sea Limited"`, `"GovTech"`, `"Singtel"`, `"NUS"`, `"A*STAR"` etc. Get rising stories mentioning SG companies/tech.
  2. Or search the product category you care about (agent-observability, LLM tooling) — global, but lets you spot high-interest products that a Singapore positioning take could ride.
- **Insight value:** which *products/companies* are gaining technical momentum globally → a launch-pad for a "but what does this mean for SG / a Singapore product" take.
- **Recommendation:** Use the **Algolia search API** (free, stable) with a keyword list of SG companies/tech + your product category. This is *not native* SG, so present it as "global tech momentum to localize," clearly labeled.

---

## 2. Recommended architecture (presented for YOUR call — I don't filter positioning)

```
                    ┌─────────────────────────────────────────────┐
  TikTok CC Trends  │  DAILY COLLECTOR (cron)                     │
  (SG filtered) ───▶│  pulls each source → timestamped JSON/MD    │
  Google Trends SG ─▶│  one combined "SG shortlist" file per day  │
  Reddit r/sg,       │                                            │
   r/askSG ────────▶│  PRESENTED to you as: topic | source |      │
  X Trends WOEID ───▶│  velocity | recency | sample posts | link  │
  HN (SG keywords) ─▶│                                            │
                    └─────────────────────────────────────────────┘
                                          │
                                          ▼  (you decide positioning)
                               Choose 1-3 topics → I draft content
```

**Cadence:**
- **Daily (automated cron):** Google Trends SG page, Reddit r/singapore + r/askSingapore, HN Algolia (SG keywords). These three are cheap, legal, stable.
- **2-3×/week (automated or manual):** TikTok Creative Center SG trends (browser).
- **X Trends-by-WOEID:** only after xurl is installed + credits bought. Optional.

**Daily output shape for you (this is what lets you make the call):**
| Topic / Query | Source | Velocity | Recency | Sample (actual post/query) | Link |
|---|---|---|---|---|---|
| "Grab pricing surge" | Reddit r/askSG | ↑ rising (14 pts/2d) | today | "Why does Grab surge every lunch?" | link |
| "LLM observability" | HN (global→localize) | high | 1d | Show HN: token-cost tracker | link |

Presented this way, you scan rows and call the positioning. That's the whole loop. No filter from me.

---

## 3. What I'd recommend you build now (in priority order — honest about effort/payoff)

| Priority | Source | Effort | Cost | Payoff for SG topics | Do it? |
|---|---|---|---|---|---|
| 1 | **Google Trends SG** (free `geo=SG` page) | Low | $0 | High — cleanest SG search signal | ✅ Start here |
| 2 | **Reddit r/singapore + r/askSingapore** (JSON) | Low | $0 | High — rich long-form SG discourse, the frames you attack | ✅ Start here |
| 3 | **HN Algolia** (SG keywords + product category) | Low | $0 | Medium — global momentum to localize | ✅ Start here |
| 4 | **TikTok Creative Center SG** (Playwright) | Medium | $0 | Medium — but thin SG data; browser automation | 🛠️ Week 2 |
| 5 | **X Trends-by-WOEID** | High | Paid | Medium-High — true live SG, but expensive + not set up | 🔜 Phase 2 (only if you want real-time) |

**My recommendation for a first week:** Build a single cron script that:
1. Fetches `trends.google.com/trending?geo=SG` → parses SG trending searches.
2. Pulls `r/singapore/hot.json` + `r/askSingapore/hot.json` → Reddit JSON.
3. Hits `hn.algolia.com/api/v1/search?query="Singapore"` + product keyword → HN.

…and dumps a **daily "SG topic shortlist" markdown** at an agreed path. Run it 7 days, then we review what it actually surfaces before adding TikTok/X. Cheap, legal, zero install friction — validates the whole idea before you spend anything.

**Decision needed from you:**
1. **Target niches/keywords** to seed the collector — e.g. "Grab/Shopee/Sea/Temasek-linked," "agent/LLM/observability," or a specific SG company list. The collector filters on these.
2. **Where should the daily shortlist land?** A file in this repo (e.g. `plans/sg-trends/`), a Telegram digest, or both?
3. **Is X real-time trending essential enough** to set up xurl + pay for API credits now, or defer to phase 2?

---

## 4. Verified facts behind this plan (so you trust the recommendations)

- **Google Trends API is official but alpha-gated** (launched July 2025; country+sub-region incl. SG; requires applying as alpha tester). Official docs confirmed.
- **pytrends is widely reported dead in 2026** — don't build on it.
- **X "Trends by WOEID" endpoint exists** (official docs confirmed). Singapore WOEID = `1062617`. X standard API is **paid** (~$5 min) and `xurl` is **not currently installed** on this machine.
- **Reddit `hot.json`/`top.json` are free, loginless** for small daily pulls. PushShift is mostly dead.
- **HN Algolia search API is free** and stable (`hn.algolia.com/api`).
- **TikTok Creative Center Trends Hub** is the official free SG-filtered trend surface (browser/Playwright).

Everything above is verified or clearly flagged as estimate. No fabricated numbers.
