# Assistant reply language fallback

The October 26 Hinge screenshot shows Indonesian suggestions for an English
screen whose newest chat message is laughter. The reader intentionally excludes
the introductory card and its overlapping caption. A matching layout fixture
therefore produces only `Them: Haha`. The previous accessibility prompt asked
the AI to use the conversation's language without an ambiguity rule, and the
overlay did not supply a language preference. This makes an unsupported language
guess a likely explanation. The original production request was not inspected;
captured accessibility transcripts are intentionally not stored.

## Behavior

`POST /api/generate/` accepts an optional `reply_language` for accessibility
requests. The hint is normalized to en/de/es/fr/pt; absent, unsupported or invalid
values safely select English. It is a fallback, not a forced translation of
clear conversation text. Manual and OCR generation keep their existing behavior.

If every message consists only of common language-neutral laughter,
acknowledgements, emoji, numbers or punctuation, the server explicitly tells
both providers to write all three replies in the fallback language. Sender
labels do not count as language evidence. For meaningful message text, the
prompt preserves the established conversation language and uses the fallback
only when unclear. No raw language hint is interpolated into a prompt.

The hint survives primary/fallback provider routing and GPT-only account tiers.
Quoted user context, account/credit behavior and transcript non-persistence are
preserved. The change adds no tables or migrations.

## Deployment

Deploy the backend changes and restart the Python application using the normal
deployment process. This has not been deployed here. Existing build 86 clients
receive the English default once this backend patch is live. Mobile build 87
additionally sends the user's app language, falling back to the supported device
language or English. Install build 87 for that behavior.

No database migration is required for this change. Prior complimentary-access
migrations remain part of the existing backend setup.

## Validation

All 99 mobile backend tests pass with mocked providers and isolated SQLite
settings. Tests cover neutral context, clear-language preservation instructions,
all supported hints, invalid hints, account tiers, primary/fallback and GPT-only
routing, unchanged legacy prompts and transcript/log non-persistence. These are
request/prompt tests, not a live AI quality evaluation.
