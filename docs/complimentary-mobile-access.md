# Complimentary mobile access

Administrators can grant an existing account all mobile subscription features
without buying or creating a subscription. This includes replies, assistant
replies, image openers, the opener vault, OCR/profile tools and archive access.
The same subscriber usage accounting and configured fair-use/model tiers apply.
Web credit balances and purchase/subscription records are unchanged.
Generation/copy analytics retain the actual subscription classification. Grant
usage is identified in existing generation metadata, rather than recorded as a
fake paid subscription.

## Deployment

Deploy the backend changes and apply the new schema migration using the normal
production database configuration:

```sh
python src/manage.py migrate
```

Migration `conversation.0028_chatcredit_mobile_full_access` adds two fields to
the existing ChatCredit table. Apply it before serving the updated code. No
production database was changed during development; tests use isolated SQLite.
The mobile client needs build 83 or later to recognize this separate access flag.

## Grant or revoke access

1. Have the person register/sign in to the mobile app with their email first.
2. In Django admin, open **Conversation > Chat credits** and search for the
   email address. Check the email on the matching account before editing it.
3. Enable **Complimentary mobile access**. Optionally set **Mobile access
   expires at**; leave it blank for access until you revoke it. Save.
4. Reopen the mobile app to refresh account status. Profile and plan screens
   show complimentary access without asking the person to subscribe.
5. To revoke access, clear the checkbox and save. Expired grants are also
   rejected immediately by the API. The next account/request response updates
   the app. An existing paid subscription continues to work after revocation.

The **Mobile Signup List** also links each known mobile account to its credit
record through **Complimentary mobile access**. Only staff with the normal
ChatCredit change permission (or a superuser) can edit grants. Changes made
through the Django admin retain its normal change history.

## API behavior

- `is_subscribed` continues to mean an active paid subscription.
- `has_mobile_access` means an active paid subscription or active admin grant.
- `mobile_access_granted` identifies the active complimentary grant.
- `mobile_access_expires_at` is its optional ISO timestamp.

Mobile feature gates use server-validated access on every request. Purchase
verification still checks real Google Play purchases. Mobile request bodies
cannot grant access. The client caches the separate grant for UI state, reloads
it across engines, clears it at logout, and refuses expired cached grants.

Validation: all 91 mobile backend tests passed, including nine grant tests and
eight accessibility tests, with mocked providers and isolated settings.
`makemigrations --check --dry-run --settings=reignitehome.test_settings` reports
no missing migrations. Nothing was deployed or granted to a real account.
