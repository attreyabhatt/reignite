# October 2026 organic growth release

Prepared October 27, 2026. Website changes are implemented locally; production deployment and production database publication have not been performed. GA4 `reply_generated` and `sign_up` have been created and marked as key events in the connected TryAgainText property, with no default monetary value and once-per-event counting. Production events will start only after the new code is released.

## Included in the release

- Twelve original situation guides, with ten distinct reply examples and two fictional follow-up conversations each. All twelve become available together when this release is deployed, with no publication date gates.
- Five existing situation guides refreshed: what to say next, confirm a date, end a conversation, accept a compliment, and follow up after a first date. The first four correspond to the priority refreshes; the fifth incorporates the retired overlapping after-a-date page.
- Five database-backed pickup guides refreshed by the targeted `organic` publisher: lawyer, Instagram DM opener, fishing, firefighter and flight attendant. These five need the separate publication command below.
- The retired `/situations/what-to-text-after-a-date/` path permanently redirects to `/situations/what-to-text-after-first-date/`. Old incoming links are rewritten, the retired path is absent from the sitemap, and non-www requests consolidate the hostname and path in one redirect.
- Three guide groups, contextual next-step links, two established incoming guide links per new page, editorial attribution, an About/editorial page, Article metadata, and stable sitemap modification dates. Historical first-publication dates are left unspecified when unknown.
- A primary web tool across devices, with Android links and install attribution retained as secondary actions. Hinge prompt answers remains a profile-writing guide without an unrelated conversation form.
- Built Tailwind CSS, local SVG icon masks, locally hosted existing Latin fonts and a WebP hero image. The hero image fell from 1,170,781 to 105,294 bytes (91% smaller). Typeface and icon licences are included.
- Three 24-second, captioned still-frame product walkthroughs embedded in the relevant guides. They use actual screenshots of the isolated local UI and visibly label fictional messages and illustrative output. Posters and text transcripts are included; videos do not autoplay or preload video data.
- Original landing path and coarse acquisition source/medium on the existing conversion events and report. Signup and successful generation produce deduplicated GA4 events; copies are tracked only after clipboard success. No message content, screenshots, email addresses or raw referrer/query strings are added to these GA4 events.

## Release procedure

Use the application's existing deployment environment and credentials. Do not use isolated test settings against production. The following are release instructions, not a claim that they have already run on the hosted application.

1. Optionally set `SEO_GUIDES_PUBLISHED_ON` to the actual first public release date in `YYYY-MM-DD` format for Article publication metadata. Leave it blank until that date is known; unknown publication dates are omitted. This setting does not control availability. The former `SEO_GUIDE_ROLLOUT_START` setting is no longer used.
2. Build and review static assets before release: `npm ci`, then `npm run build`. Generated CSS, icon masks, fonts, licences and demo files are included in the source, so the Python production image does not need Node to serve them. Run `python scripts/vendor_fonts.py` only when deliberately refreshing font assets; the normal build uses the checked-in files.
3. Apply the additive schema migration using the normal production database configuration: `python src/manage.py migrate`. Migration `conversation/0029_webconversionevent_acquisition.py` adds three blank metadata fields. Old event rows are not backfilled with guessed attribution.
4. Inspect the content update: `python src/manage.py refresh_search_content --batch organic --dry-run`.
5. Publish the five pickup refreshes with a new backup filename: `python src/manage.py refresh_search_content --batch organic --backup seo-before-organic-2026-10-27.json`. Retain that JSON outside the ephemeral application filesystem. The command validates all five targets, runs transactionally, changes only reviewed fields, and refuses to overwrite an existing backup file.
6. Publish collected assets: `python src/manage.py collectstatic --noinput`, then complete the normal application release/restart. All twelve situation guides are code-backed and available immediately; no seed command or scheduled database write is needed for them.
7. Read the release manifest: `python src/manage.py seo_rollout --json`. It lists all twelve guides as available together. Check the current sitemap and representative pages on both hostnames, including the first-date redirect and the Hinge guide.
8. Run one real production guest generation, copy and signup. Check the network event payload/GA4 DebugView and the server report. Confirm that message text is absent from GA4, each action fires once, the original landing page survives signup, the latest guest result is restored, and credits are unchanged apart from the existing generation/signup rules.
9. Record release timestamp, deployed commit and content-backup location below. Re-measure mobile PageSpeed on the deployed pages. Inspect representative new guides in Search Console after verifying their live responses and sitemap entries. Do not repeatedly submit unchanged URLs.

Do not run `seed_pickup_data` on an established production database: it is intended for a fresh database and can overwrite unrelated seeded topics. The targeted publisher does not change prices, allowances, sort order or active status. Re-running the organic batch skips already-published records and preserves subsequent admin edits. `--force`, with a new backup, deliberately reapplies the reviewed fields if required.

### Rollback

Restore only the five targeted content records with `python src/manage.py refresh_search_content --batch organic --restore seo-before-organic-2026-10-27.json --dry-run`, then the same command without `--dry-run`. Invalid target/field sets are rejected. Restore application code and static assets through the normal release mechanism if necessary. Leave the additive acquisition columns in place when reverting application code; reversing their migration would remove the new attribution data.

## Single-release publication

All twelve guides ship together: WYD, how was your day, haha/LOL, good morning, good night, I miss you, thinking of you, after a thank-you for a compliment, before a first date, rescheduling a date, what are you looking for, and declining a second date. Their routes, directory cards, contextual links, tool sidebar entries and sitemap entries are included immediately. No calendar scheduler or waiting period is involved. The earlier two-per-week plan has been superseded by the user's instruction to publish them all at once.

## Baseline and indexing review

The dated baseline is `marketing/seo-baseline-2026-10-27.json`. It preserves the observed Search Console property totals, the separate GA4 dates, and the nine priority pages. Page comparisons combine hostname variants; property and page-export totals can differ. The 700-click day-90 goal is a working target, not a forecast.

The two connected Search Console exclusions were downloaded and all 90 exported rows were fetched. They represent 84 canonical paths. Results are in `.seo-audit/indexing-2026-10-27.csv`:

- 82 rows had no response, canonical, robots or noindex blocker at fetch time.
- Six rows used a historical hostname and redirected to a healthy canonical destination.
- Two were discovery endpoints (`robots.txt` and `sitemap.xml`) that do not need to be indexed as HTML pages.
- All HTML paths had at least one incoming link from the inspected public navigation/category pages. This is a navigation check, not a full backlink inventory.

No robots unblocking or bulk removal was warranted by these findings. Indexability does not guarantee Google's selection for indexing. Continue improving usefulness and topical connections, then reassess priority excluded HTML pages after recrawling. The original 60/30 Search Console counts are historical observations, not a claim that this release has already changed indexing.

Repeat the read-only audit with fresh CSV/ZIP exports:

```text
python scripts/seo_audit.py --crawled crawled-export.zip --discovered discovered-export.zip --output .seo-audit/indexing-next.csv
```

## Weekly review and distribution

Build the private offline dashboard with `python scripts/seo_report.py`. Open `.seo-audit/dashboard.html`. To refresh page comparisons, use ordinary, un-compared complete 28-day Pages exports:

```text
python scripts/seo_report.py --current pages.csv --previous previous-pages.csv
```

The dashboard combines hostname and retired first-date paths, weights average positions by impressions, filters/sorts pages, and includes a CTR scenario slider. Its property cards remain the explicitly dated baseline; it does not mislabel page-export sums as current property totals or connect to Google automatically.

Every week record clicks, impressions, CTR, position, non-brand query coverage, device/country mix, new-guide indexing and successful generations. Use `/admin/conversation/webconversionevent/report/` for first-touch sources, signups, later-date usage and confirmed Dodo purchases. Existing permissions and the seven-day maturity rules apply. Compare complete 28-day windows; GA4 sessions and Google clicks are different measures. Set product-use targets after 14 days of reliable production tracking.

`marketing/seo-outreach-2026-10.md` contains ten researched prospects, five complete personalized drafts, five further tailored angles and source/contact restrictions. `marketing/seo-outreach-tracker.csv` contains 45 weekly slots for weeks 4–12. The first five are prepared; later slots require fresh, individually verified recipients rather than repeated unsolicited notes to the same people. No outreach has been sent, no links purchased and no social videos uploaded to external platforms.

The three demo MP4/VTT/poster sets are under `src/static/demos/`. They will be public on their existing guide pages after deployment. Rebuild them from captured local screenshots using `python scripts/build_demos.py`; the local preview uses fixed illustrative output, disables GA and external checkout, and never accesses the hosted database.

## Validation and practical limits

Run from the repository root:

```text
npm run build
npm run test:analytics
python scripts/test_seo_tools.py
python src/manage.py check --settings=reignitehome.test_settings
python src/manage.py makemigrations --check --dry-run --settings=reignitehome.test_settings
```

Run the full Django suite from `src` using the workspace virtual environment and `--settings=reignitehome.test_settings --noinput`. The tests cover immediate availability of all twelve guides, sitemap dates and canonical metadata, optional publication metadata, distinct examples, incoming links, web-first actions, first-date redirects, publisher backup/restore and admin-edit preservation, first-touch attribution, successful-only generation events and one-time signup delivery. JavaScript tests cover duplicate HTMX events, refreshes, copy events, blocked storage and the metadata whitelist. Tool tests cover hostname/redirect aggregation and HTML indexability extraction.

Final local verification: **255 Django tests, three JavaScript tests and two SEO-tool tests passed**. The Django suite was rerun after removing the schedule and includes all-at-once availability checks. The asset build, Django system check, migration consistency check and Git whitespace check passed. The signup event is retained through intermediate allauth/email template renders and consumed only when included in the full web page.

Browser review used 390-pixel and 1280-pixel viewports. The mobile guide had no horizontal overflow. Generation, copy, signup, configured allowance and saved-result restoration were exercised through the actual local UI. This is not a physical-phone test or an evaluation of model response quality. Local AI outputs are mocked and clearly labelled in demonstrations.

Lighthouse baseline and local-after summaries are recorded in `marketing/seo-performance-2026-10-27.json`. The baseline was measured on production; the after measurements use the local preview with GA disabled and a development static server without production caching/compression. Scores are directional checks, not an apples-to-apples proof of field improvement. Re-measure production after release and use field Core Web Vitals when enough data becomes available. Targets remain LCP at most 2.5 seconds, INP at most 200 ms and CLS at most 0.1.

Production deployment, production event delivery, physical-device checks, live checkout and future ranking/traffic outcomes remain unverified. Weekly review and outreach are ongoing work after release.

## Release record

- Production release timestamp: pending.
- Deployed commit: pending.
- Production content backup: pending.
- GA4 key-event configuration: completed October 27, 2026; screenshot in `.seo-audit/ga4-key-events.jpg`.
- Actual production event smoke test: pending deployment.
