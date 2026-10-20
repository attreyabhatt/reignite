# WhatsApp assistant backend release

The release mobile app uses https://tryagaintext.com. On 20 October 2026,
GET /api/generate/ returned HTTP 405 with Allow: OPTIONS, POST. The app checks
this route before uploading an accessibility transcript and requires HTTP 200
with assistant_protocol: 1. Until that support is live, generation stops at
the capability check and the current app shows "assistant unavailable".

## Prepared changes

Release these four source files together through the existing Django release
process, then reload the application workers:

- src/mobileapi/views.py
- src/conversation/utils/mobile/prompts_mobile.py
- src/conversation/utils/mobile/custom_mobile.py
- src/conversation/utils/mobile/openai_mobile.py

The route adds the non-generating GET capability response and accepts
input_source=accessibility on POST. The provider wrappers and prompt changes
preserve You/Them context and suppress conversation-content logging. The
view excludes captured transcripts from reply_ocr_text and archives while
preserving existing generated replies, locked replies and usage records.
The capability flag and provider/privacy changes belong in the same release.

This feature adds no database tables or migrations. Existing mobile generation
responses, account tiers, credits and provider fallback behavior are preserved.
No new mobile bundle is needed to remove this backend blocker.

## Validation

All eight accessibility backend tests passed again with isolated test settings:

    python src/manage.py test mobileapi.test_accessibility --settings=reignitehome.test_settings --noinput

After deployment, verify the public endpoint without sending chat text:

    curl.exe -i https://tryagaintext.com/api/generate/

Expected: HTTP 200 and JSON containing assistant_protocol: 1,
input_source: accessibility, max_messages: 12, max_characters: 6000.
This GET does not invoke AI, consume credits or record a generation.
Then test generation from a fictional one-to-one WhatsApp chat in build 79.

Production deployment has not been performed by the assistant.
