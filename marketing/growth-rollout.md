# September 2026 growth rollout

## Ship the website changes

This branch refreshes three database-backed pages (Instagram DM openers, Hinge profile prompt answers and lawyer pickup lines) and three detailed texting guides (what to say next, awkward-text recovery and expressing feelings). Other texting guides now have a direct answer and an illustrative reply, with shared filler removed.

The pickup content remains editable in Django admin under **Pickup topics → Detailed Guide**. Existing unrelated content and URLs are retained. Hinge's profile guide intentionally does not show the conversation-reply form; that form cannot promise to write profile answers.

Run these in the deployment environment using the existing application release process:

```text
python src/manage.py migrate
python src/manage.py refresh_search_content --dry-run
python src/manage.py refresh_search_content
python src/manage.py collectstatic --noinput
```

For a completely new database, run `seed_pickup_data` after migrations. Do not run the full seed command to refresh an established site's three priority pages: it also overwrites other seeded topics. The targeted command updates only the reviewed fields on those three pages, is repeatable, and rolls back if any target is missing. A backup of those three records is appropriate before publishing further editorial changes. To roll back content, restore those records; the new JSON field can remain empty.

Deploy the schema migration before serving code that reads `guide_content`. The migration only adds an empty JSON field. The content command is a separate, explicit publication step. Nothing in this document has been run against production by the assistant.

## Confirm the hostname change

The audited live site returned HTTP 200 and different self-canonical tags on both hostnames. Public discovery routes now redirect the non-www hostname to **https://www.tryagaintext.com**, preserving path and query parameters. Canonical tags, sitemap URLs and breadcrumb structured data use the same origin. Local development is not redirected.

API, account, admin, conversation, payment and app-referral routes are excluded from hostname redirects to avoid interrupting authentication, purchases or mobile clients. Their operational hostnames remain supported. There is no DNS change in this work.

After deployment, check the following from both hostnames:

- `/`, `/pickup-lines/`, `/pickup-lines/dating-apps/instagram-dm-opener/`, `/situations/what-to-say-next-over-text/`: one permanent redirect from non-www, then a successful page on www.
- Tracking query strings survive the redirect; canonical tags exclude those query strings.
- `/robots.txt` points to `https://www.tryagaintext.com/sitemap.xml`; every sitemap entry uses www.
- An authenticated app API request, account login and payment callback still use their existing routes without a new hostname redirect.

In Search Console, submit the www sitemap and inspect the six refreshed URLs. Check the live test and Google-selected canonical after recrawling. The local workspace cannot submit a sitemap to an unconnected Search Console account. Do not repeatedly request indexing as a substitute for checking the deployed page.

## Run the four-week content experiment

The campaign source is `reach-campaign-2026-09.json`. The accompanying `video-playbook.md` contains 12 dated scripts, shot lists, captions and links for Instagram, YouTube and TikTok. Dates are a proposed schedule beginning September 21; shift the calendar if launch happens later. Keep the campaign and video IDs stable so results stay comparable.

Each script is ready to record as a roughly 20–40 second vertical video with readable subtitles and a clear Android CTA. Use your real app interface and fictional example chats. Demonstrate the output the app actually returns; do not present a scripted example as a real generated result or a customer outcome. The scripts do not claim guaranteed replies or a success rate.

Where a platform provides a clickable link, use the matching platform's URL. For an unclickable caption, direct viewers to the corresponding link in your profile or a story link, where available. Do not count comments or views as installs. No videos have been recorded, uploaded, scheduled or published by the assistant, and no social account credentials are needed for these local deliverables.

The guide links carry `utm_source`, `utm_medium=organic_social`, `utm_campaign=flirtfix_reach_2026_09` and a video ID. On the landing page, Android CTAs carry that source and video through `/flirtfix` into the Play install referrer. The placement is appended, for example `video06_inline_card`. Direct-app links are also supplied. Attribution is retained on that landing page, not persisted across unrelated future browsing sessions.

## Read the acquisition report

Open **Django admin → Marketing click events → Acquisition funnel**, or `/admin/reignitehome/marketingclickevent/funnel/`. Viewing it requires the marketing-click model permission. Filter by 7, 28 or 90 days and group by campaign, landing page or placement/video. The same aggregate report is available as JSON:

```text
python src/manage.py growth_report --days 28 --group campaign
python src/manage.py growth_report --days 28 --group page
python src/manage.py growth_report --days 28 --group placement
```

The cohort starts with recorded `/flirtfix` visits. Each click counts at most once per stage:

1. **With reported install**: a mobile install-referrer report links to that click and arrives within seven days of it.
2. **Used app**: an AI reply/opener generation or a copied message from that same actor occurs within seven days after the install report. OCR and merely fetching static suggestions do not qualify.
3. **Copied a message**: a matching copy event occurs within that same activity window.

This is neither a raw Google Play download count nor a unique-person report. It measures tracked clicks with subsequent reported events. Repeated install reports do not multiply conversions. Anonymous activity needs a stable device identifier; logged-in events retain a provided hashed device identifier so guest-to-login activity can be connected. No raw chat text or user/device identifiers appear in the report. Existing records are not backfilled.

The Android client must already send the existing `/api/install-attribution/` payload and its device fingerprint on analytics requests. This repository contains the backend, not the Android source. Validate one real install through a test campaign before interpreting zero conversions as poor marketing. Missing client reporting and older identifiers can undercount. Existing event cleanup defaults to 90-day retention; review changes before that history expires.

Allow up to 14 days for a click's install and activity windows to finish. Recent rates are provisional; the report shows how many clicks have a full observation window. Existing browser events (`android_app_promo_view`, `android_app_cta_click`, `android_app_promo_dismiss`) still provide Android-specific CTA engagement in GA4. The server report also includes direct social app links and should not be treated as a GA4 sessions report.

## Weekly review

Baseline export: March 13–September 18, 2026. Latest 28 days (August 22–September 18): 469 clicks, 14,224 impressions and 3.30% CTR. Previous 28 days: 356 clicks, 9,513 impressions and 3.74% CTR. Mobile supplied 82.3% of clicks across the export; that category includes iPhones.

Record the deployment date and first publication date. Every week, compare the six pages' last 28 days with the previous 28 days in Search Console, with page + query, country and device filters where useful. Track clicks, impressions, CTR and average position together; a change in query mix can change CTR. The original export does not join queries to pages, so confirm query intent in that filtered view before further rewrites.

For the social experiment, record views and landing-page visits from each platform alongside mature reported installs and app use. Repeat topics that produce users who actually use the app. Review after four weeks; do not promise a ranking increase or treat a handful of installs as a conclusive A/B test. Keep canonical URLs stable while experimenting with content.

## Local verification

- 343 public routes rendered successfully against an isolated, freshly migrated and seeded SQLite database. Canonical URLs, JSON-LD parsing and unique element IDs were checked.
- 134 of 135 tests passed across `seoapp`, `reignitehome` and `mobileapi`. The remaining Community navbar assertion also fails with the original templates; it expects a navigation link that was already absent.
- The migration consistency check and Django system checks passed. All 72 links in the video playbook resolve to application routes and carry the intended campaign/video labels.
- No connected browser was available for visual QA. Check the six refreshed pages at phone and desktop widths and the admin funnel after deployment. PostgreSQL execution and a real Android install were not exercised by the local SQLite tests.

Reference guidance: [Google on helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), [canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [internal links](https://developers.google.com/search/docs/crawling-indexing/links-crawlable), and [Hinge on profile prompts](https://help.hinge.co/hc/en-us/articles/36311352171539-How-do-I-edit-my-Prompts).
