# FlirtFix Android App Links

The public `/.well-known/assetlinks.json` endpoint associates
`com.tryagaintext.flirtfix` with the website using the **Play app signing**
certificate shown in Play Console. The local upload certificate is different
and must not replace it. Credential sharing is not enabled.

Serve this URL directly with HTTPS, status 200 and application/json on both
`www.tryagaintext.com` and `tryagaintext.com`, without login or redirects. It is
handled by Django, so no static-file collection, tables or migrations are needed.

Mobile build 89 declares only `/flirtfix` and `/flirtfix/` on these two hosts
(HTTP and HTTPS). The link opens or resumes the app through its normal startup
flow. Existing web visitors without the app retain the Play Store redirect and
install-referrer query parameters. Installed-app opens bypass that web redirect,
so those opens do not create the existing website marketing-click record.

After deploying this endpoint, return to Play Console > Grow users > Deep links
and create each website association. Keep Enable credential sharing off. Upload
build 89 to internal testing; build 88 has no app-link intent filter and cannot
provide the same complete behavior. No production mobile release is needed for
internal testing. Check the link with a Play-installed copy of build 89, since
debug and locally upload-signed APKs have different certificates.

The requested link is `https://www.tryagaintext.com/flirtfix`. Homepage, web
account, payment, API and other website paths continue to open on the website.
App Links are subject to the user's Android supported-links settings.

Validation: run `venv/Scripts/python.exe src/manage.py test reignitehome
--settings=reignitehome.test_settings --noinput`. This uses the isolated test
database and does not contact production or AI providers.
