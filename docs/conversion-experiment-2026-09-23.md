# Reply continuation experiment

Prepared September 23, 2026. Experiment ID: `web_continuation_2026_09`.
Status: implemented locally; **not deployed**. Production release timestamp: pending.

Android visitors get the FlirtFix app action first. iPhone and desktop visitors get the web tool first. Android visitors can still choose the web version. This applies to the homepage, lawyer guide, Instagram DM opener guide, and “what to say next” guide. Existing guide content and public URLs remain available. App links retain the existing install attribution.

The web offer keeps the configured guest and signup allowances (currently three each) and the existing packs: 10/$1.99, 50/$6.99, 200/$19.99. One generation uses one credit and requests three suggestions. The experiment changes discovery, explanations, continuation, and checkout entry; it does not change prices or free credit configuration.

After visual review, the original homepage hero grid, phone image, glow, badge, and spacing were restored. The device-specific calls to action remain. Six relevant page and allowance tests passed after this correction, and desktop/mobile browser checks confirmed that the image loads and fits the layout.

## What changed

- Successful guest replies include a nonblocking invitation to keep the conversation. The final free generation gives a clearer signup action.
- One latest successful guest draft lives in the server session, with a 24-hour eligibility window. Signup or sign-in imports the conversation, situation, context, and suggestions once, without another AI call or credit deduction.
- Conversations retain the latest suggestions through refreshes. Continuing a saved conversation updates that conversation after a successful generation.
- At zero account credits, the replies remain visible beside the 10-generation, $1.99 one-time offer. Pack selection survives signup and switching to sign-in.
- Metadata-only web conversion events connect guest generation, copy actions, continuation displays/clicks, signup, and checkout redirects through a stable journey UUID and account ID. Existing conversation/copy logging is unchanged; the new event table contains no conversation text, email, or full user-agent string.

## Reading the reports

Website report: `/admin/conversation/webconversionevent/report/`. Choose 7, 28, or 90 days. Access requires the corresponding admin view permission.

The report shows all-period event totals separately from new guest cohorts. Cohorts start at the first tracked guest generation. Once linked to an account, multiple journeys for that account count as one cohort; anonymous browser sessions remain distinct. Milestones are observed within seven days, regardless of order. Only cohorts old enough to have a full seven-day window contribute to the displayed rates. Return usage means a successful generation on a later UTC date within that window, not simply a page visit.

Purchases come from completed Dodo website payment records, deduplicated by transaction ID. A checkout redirect is not a purchase. First purchase means the account's first completed Dodo purchase across available history. Staff accounts and Google Play purchases are excluded. Blank historical transaction IDs can only be counted as separate records. Buyers outside a matched seven-day cohort are labelled separately, not attributed to this experiment.

The historical guest-generation and copy counters overlap new tracking after release; do not add them together. Historical guest-to-signup links cannot be reconstructed. A copied reply does not prove it was sent or that it helped.

Android app results remain in `/admin/reignitehome/marketingclickevent/funnel/`, linked from the web report. People choosing the web version on Android appear in the web report. Directing Android visitors to the app can change the mix of web users, so evaluate both reports separately before drawing business conclusions.

## Baseline from the earlier read-only review

The supplied GA exports mostly covered August 25–September 21, 2026: 683 active users, 470 Google clicks, 369 clicks on pickup-line pages, and eight pricing views. Database records showed 155 guest browser sessions generating successfully in that period, with 312 successful generations and 124 recorded copy actions. These are different measurement systems, not interchangeable user counts.

For June 22–September 21, the database review found 305 successful guest sessions, 585 generations, 104 sessions using all three credits, and 21 attempting a fourth. Eleven new accounts had observable web activity; one used it on multiple dates. Two website buyers had bought once and returned across multiple months. This supports testing continuation and repeat usefulness; it does not establish why nonbuyers declined to pay.

## Evaluation

Record the actual deployment timestamp and commit when released. Review after 28 days. Extend to day 56 if fewer than 150 guest browser sessions have generated successfully; use the explicit session count, not the account-deduplicated cohort count. Keep the same prices and allowances during the observation period, and record other marketing changes.

Consider confirmed first purchases alongside signups and later-date generation. More signups without repeat use suggest the account offer improved but ongoing value remains weak. More repeat use without purchases calls for interviews about need, alternatives, and the offer. Small counts are directional evidence, not statistical certainty. See `customer-interview-drafts.md`; no messages have been sent.

## Local validation and preview

Run from the repository root:

```powershell
& .\venv\Scripts\python.exe src/manage.py test conversation.test_web_conversion --settings=reignitehome.test_settings --noinput
& .\venv\Scripts\python.exe src/manage.py check --settings=reignitehome.test_settings
& .\venv\Scripts\python.exe src/manage.py makemigrations --check --dry-run --settings=reignitehome.test_settings
& .\venv\Scripts\python.exe scripts/preview_conversion.py
```

The preview creates a disposable SQLite database, seeds public guides, mocks AI/OCR, disables GA, captures email locally, and replaces external checkout with a local redirect. It listens only on `127.0.0.1:8000`. The local admin is `preview` / `PreviewOnly123!`. `/__preview__/android/` renders the Android homepage variant on a desktop browser; this route exists only in the preview script. The optional `--database` argument reuses a prior preview SQLite file. Stop the process with Ctrl+C.

Full-suite command (run from `src`): `..\venv\Scripts\python.exe manage.py test --settings=reignitehome.test_settings --noinput`. **All 189 tests passed.** The old Community navigation test was updated to expect the intentionally hidden link, as confirmed by the owner. Community remains hidden in navigation.

New tests cover configured allowances including zero signup bonus, restoration on signup/sign-in, expiry, replay, failed generations, persisted results, saved-conversation continuation, safe redirects, selected packs, event ownership/deduplication, cohort maturity, return usage, historical first purchases, duplicate transactions, Android exclusion, platform-specific calls to action, and admin permissions.

Browser review uses fixed example replies, not an evaluation of AI quality. Mobile layout checks use a narrow Chrome viewport; they do not substitute for testing on physical iPhones or Android devices. Copy button and nested icon clicks each added exactly one event in the preview database.

## Release notes

Migration `conversation/0026_conversation_guest_draft_id_and_more.py` adds saved results and the event table. Apply it using the deployment's normal database configuration before serving this code, and collect static assets. No migration or data writes have been applied to production during this implementation. Do not use isolated test settings in production.

After release, verify one real guest-to-account journey and its event links, then record the release time here. Deployment, real checkout, and customer outreach are still pending. Rolling back application code can leave the additive schema in place; reversing the migration would remove saved results and experiment events.
