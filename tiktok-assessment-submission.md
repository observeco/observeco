# TikTok Integration Assessment — Unreleased App
## Submission for Access to Content Posting API (pre-publish)

**Applicant:** ObserveCo (observeco.com) · Contact: sean.foo@observeco.com
**App:** ObserveCo Content Posting API (client key awbmvv3jmvaw28xj)
**App type:** Web app
**App URL:** https://postiz.observeco.com

---

## 1. What the app does (plain, verified, not exaggerated)

ObserveCo is a social-media scheduling and management tool for small businesses.
It connects a brand's social accounts (X, Instagram, Facebook, TikTok) into one
dashboard, so a single person can draft, review, and schedule content across
platforms from one place instead of logging into five apps.

Postiz (the open-source engine ObserveCo runs, AGPL-3.0, 30,000+ GitHub stars)
provides the scheduling core. ObserveCo operates it self-hosted.

This application requests the **Content Posting API** with the `video.upload` +
`video.publish` scopes so an ObserveCo user can schedule TikTok videos from the
same dashboard they already use for the other networks.

## 2. Why this benefits TikTok users (the credibility test)

- **Better scheduling for small businesses on TikTok.** Singapore small businesses
  (ObserveCo's focus) routinely post to multiple platforms. Without the API they
  must open the TikTok app for every post and juggle five scheduling UIs. The
  API lets them batch TikTok into their existing workflow — the same videos they
  already produce for Instagram/Douyin go out on TikTok on schedule, consistently.
- **Creators stay in control.** Posts published via the API are disclosed as
  promotional/branded content exactly as TikTok requires. The commercial-content
  disclosure toggle is surfaced in the composer, and the user confirms it before
  publish — never auto-disclosed or hidden.
- **No spam, no scraping, no bulk.** The integration is human-in-the-loop: a user
  composes and confirms each post. No auto-broadcasting of third-party content,
  no engagement manipulation, no repurposing of others' creators' videos.

## 3. The UX flow (maps to the demo video / mockups)

1. User opens postiz.observeco.com and signs in.
2. Settings > Channels > Add TikTok → redirected through TikTok Login Kit OAuth.
3. User authorizes the app; ObserveCo receives the user's open_id + basic profile.
4. User composes/upload.s a video in the calendar, selects TikTok, sets a schedule,
   and confirms the commercial-content disclosure toggle.
5. On schedule, ObserveCo calls Content Posting API → TikTok publishes the user's
   own video to their own account. Status (pending/published/failed) shows in the
   dashboard.

## 4. Scopes requested and their honest purpose

- `video.upload` — to upload the user's selected video file as part of Direct Post
- `video.publish` — to publish that video to the user's own authorized account
- (plus `user.info.basic`, `user.info.profile`, `user.info.stats`, `video.list`
  used only to display the account card and content library)

Each scope is requested only when the user initiates the matching action — never
at app bootstrap.

## 5. Compliance statements (TikTok content-sharing checklist)

- ☐ Creator info queried before publish; privacy/interaction options respected
  (nothing pre-selected).
- ☐ Commercial-content disclosure toggle presented and confirmed by user prior to
  upload; posts labeled Brand Organic / Branded Content accordingly.
- ☐ Express user consent obtained before content is uploaded/published.
- ☐ Upload/reporting status surfaced to the user.
- ☐ API credentials kept unshared and rotated in line with TikTok policy.
- ☐ No collection, sale, or sharing of user data. Tokens stored per-user, used
  only to publish that user's own content.

## 6. Supporting material

- Privacy Policy: https://observeco.com/privacy.html (live, verified)
- Terms of Service: https://observeco.com/terms.html (live, verified)
- Domain verification: observeco.com TXT record verified in TikTok portal
- UX mockups: submitted alongside (the flow above rendered as annotated screens)
- Demo video: submitted (Login Kit OAuth end-to-end; Content Posting flow to be
  demonstrated once access is provisioned, per TikTok's sandbox limitation)

## 7. Honest status of the integration

ObserveCo runs TikTok's login/authorize flow through the production URL today.
Because the Content Posting API cannot be exercised in a sandbox, the live
upload/publish path is ready in code but cannot be demonstrated end-to-end until
access is provisioned. ObserveCo commits to completing TikTok's audit immediately
after access is granted. We understand approval is at TikTok's discretion.
