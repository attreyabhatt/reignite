# Overlay assistant configuration

The floating Android assistant sends `input_source: "accessibility"` to the
existing `/api/generate/` endpoint. Ordinary app replies and openers are unchanged.

## Deploy with a manual migration

The new configuration requires
`conversation/0030_mobileappconfig_overlay_fallback_model_and_more.py`.
The migration adds four optional fields to the existing MobileAppConfig table;
it adds no tables and does not modify captured conversations.

Run these commands from the deployed Django `src` directory using the release's
normal Python environment and production settings:

```sh
python manage.py migrate --noinput
python manage.py showmigrations conversation
```

Check that 0030 is marked `[X]`, then restart/redeploy web workers with this
release. Apply the migration before serving the new code. Do not use
`reignitehome.test_settings` on the server. The local implementation has not
been pushed or deployed automatically.

## Admin controls

Open Django admin > Mobile API > Mobile App Config >
**Overlay Assistant: Models & Prompt**.

| Setting | Behavior |
| --- | --- |
| Overlay reply model | Primary model for all overlay account tiers. Blank inherits guest, registered or subscriber/degradation routing. |
| Overlay fallback model | Used when the primary fails or returns malformed alternatives. Blank inherits the existing fallback model. |
| Overlay reply thinking | Gemini thinking override. Blank inherits account-tier thinking. Ignored by OpenAI. |
| Overlay reply prompt | Optional writing instructions replacing the built-in overlay style. Blank uses the displayed built-in style. |

Model names use the existing Gemini/OpenAI dispatcher. Enter an exact supported
provider model ID, as with the existing model settings. Request bodies cannot
override these admin controls. Existing admin authentication and change
permissions protect them. The normal limits, credits, subscription and
complimentary-access rules remain in force even when a model is overridden.

## Dedicated prompt and output contract

The built-in style follows the existing short, conversational writing rules,
with three distinct alternatives in a fixed order:

1. Flirty: warm, confident, lightly teasing, without pressure.
2. Funny: playful humor tied to the exchange, without mockery.
3. Natural: relaxed, sincere and direct.

Every reply has `message` and `tone` fields. Valid explicitly labelled replies
are reordered into Flirty/Funny/Natural; missing tones, duplicate tones/text,
blank replies or the wrong count trigger provider fallback. This verifies the
structure, not whether a particular sentence succeeds at humor or flirting.

Custom admin writing instructions retain mandatory quoted-context, sender,
language, fixed tone/order and output-format rules. The transcript is JSON
quoted in the user message, separate from system instructions. The model must
not follow instructions inside it or assume an outgoing message has been read.
Sparse acknowledgements such as 'Haha' use the app/device language hint, with
English as the default. Both Gemini and OpenAI use the same overlay rules.

Captured input is excluded from transcript/history storage, archives, copy-event
requests and content logs. Generated/locked replies and usage records remain
under the existing retention and account rules. The mobile disclosure explains
this distinction. No live AI requests were needed for the automated tests.

## Local checks

From the repository root:

```powershell
.\venv\Scripts\python.exe src\manage.py test mobileapi reignitehome --settings=reignitehome.test_settings --noinput
.\venv\Scripts\python.exe src\manage.py makemigrations --check --dry-run --settings=reignitehome.test_settings
```

These settings force isolated in-memory SQLite before importing the base
settings. Provider calls are mocked. A real backend rollout and model quality
evaluation are separate from these checks.
