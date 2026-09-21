# September 2026 growth rollout

## Ship the website changes

The first growth batch refreshes three database-backed pages (Instagram DM openers, Hinge profile prompt answers and lawyer pickup lines) and three detailed texting guides (what to say next, awkward-text recovery and expressing feelings). Other texting guides have a direct answer and an illustrative reply, with shared filler removed. The second SEO content batch is described below and has its own publication option.

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

## Publish the SEO expansion batch

This batch adds **14 pages** and expands **four existing pages**, retaining the existing Android app card, Android-only bar, page attribution and canonical URLs. These additions are experiments for the site's existing audience; the export does not establish search volume for the new topics.

The six new pickup pages each contain 15 original lines (five witty, five flirty and five deliberately cheesy), explanations, three fictional follow-up conversations and personalization advice:

| Topic | New URL |
| --- | --- |
| Tennis | `/pickup-lines/hobbies/tennis/` |
| Badminton | `/pickup-lines/hobbies/badminton/` |
| Pickleball | `/pickup-lines/hobbies/pickleball/` |
| Data scientist | `/pickup-lines/professions/data-scientist/` |
| Journalist | `/pickup-lines/professions/journalist/` |
| Optometrist | `/pickup-lines/professions/optometrist/` |

The eight new texting guides each provide a direct answer, four specific sections and eight illustrative examples:

- `/situations/how-to-respond-to-hey/`
- `/situations/how-to-respond-to-a-compliment-over-text/`
- `/situations/how-to-reply-to-instagram-story/`
- `/situations/dating-app-openers-with-no-bio/`
- `/situations/how-to-confirm-a-date-over-text/`
- `/situations/how-to-respond-to-im-busy-text/`
- `/situations/how-to-end-a-text-conversation/`
- `/situations/how-to-reply-to-a-pickup-line/`

The existing pickup pages being expanded are `dating-apps/tinder-opener`, `professions/barista`, `professions/flight-attendant` and `fandoms/lord-of-the-rings`. Together those four URLs received 4,480 impressions and 98 clicks in the supplied March 13–September 18 export. Tinder's average position was 34.38, so treat it as a longer-term opportunity. These figures describe existing page performance, not search volumes or a forecast.

Before publication, back up the four records being refreshed. The schema must already include the earlier `guide_content` migration; this batch adds no new migration. Deploying the code makes the eight situation guides available. Then run these commands against the deployment database from the repository root:

```text
python src/manage.py refresh_search_content --batch expansion --dry-run
python src/manage.py refresh_search_content --batch expansion
```

On a database without these six additions, the dry run reports four refreshes and six creations without saving anything. The real command refreshes only the four selected records and appends missing new topics after each category's existing sort order. Already-present new topics are reported as **skipped**: their text, ordering and active status are preserved, including admin edits. Missing required categories or any of the four refresh targets aborts the transaction; a failure during writing also rolls back the whole command.

The default command, without `--batch expansion`, still updates only the original three priority records. Do not run `seed_pickup_data` on an established database to publish this batch: it can overwrite unrelated seeded content. On a fresh database, normal seeding includes all additions, for 302 pickup topics; the code now registers 32 situation guides.

Each new page appears in its directory and the sitemap. New sports pages link to one another; the professions category features the three new professions. Existing situation guides link to the relevant new guides, and Instagram and Tinder opener pages link to story replies and no-bio openers respectively. All six new pickup pages link to the pickup-line reply guide and next-step advice.

After release, check representative pages on an Android phone, verify the app link reaches Google Play, and inspect the new URLs and sitemap in Search Console. Record the actual deployment/publication date. After 28 days, compare the four refreshed pages with the preceding period and review new-page impressions, clicks, CTR and position separately. Use the acquisition report grouped by page for reported installs and subsequent app use; allow its 14-day observation window to mature. No production publication or Search Console submission has been performed by the assistant.

To undo the database publication, restore the four backed-up records and deactivate newly created topics in admin. The eight code-backed situation pages require reverting their code and incoming links if they must be removed.

Local verification for this expansion: all 38 SEO tests passed, along with four canonical tests and four Android promotion tests (46 distinct tests). Checks cover all 18 affected pages, single rendering of each of the 90 new pickup lines, sitemap and incoming links, CTA attribution, repeatable seeding, command dry runs, preservation of edits and rollback after an interrupted write. Django system checks, migration consistency and whitespace checks passed. Testing used an isolated SQLite database; PostgreSQL execution, visual phone/desktop review and a real Android install were not exercised. No connected browser was available for visual review.

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

## First growth batch verification

- 343 public routes rendered successfully against an isolated, freshly migrated and seeded SQLite database. Canonical URLs, JSON-LD parsing and unique element IDs were checked.
- 134 of 135 tests passed across `seoapp`, `reignitehome` and `mobileapi`. The remaining Community navbar assertion also fails with the original templates; it expects a navigation link that was already absent.
- The migration consistency check and Django system checks passed. All 72 links in the video playbook resolve to application routes and carry the intended campaign/video labels.
- No connected browser was available for visual QA. Check the six refreshed pages at phone and desktop widths and the admin funnel after deployment. PostgreSQL execution and a real Android install were not exercised by the local SQLite tests.

Reference guidance: [Google on helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), [canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [internal links](https://developers.google.com/search/docs/crawling-indexing/links-crawlable), and [Hinge on profile prompts](https://help.hinge.co/hc/en-us/articles/36311352171539-How-do-I-edit-my-Prompts).
