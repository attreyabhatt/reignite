from unittest.mock import patch
from datetime import timedelta

from django.contrib import admin
from conversation.models import (
    RecommendedOpener,
    MobileAppConfig,
    DegradationTier,
    GuestTrial as ConversationGuestTrial,
    TrialIP as ConversationTrialIP,
)
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from reignitehome.models import TrialIP as HomeTrialIP
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from mobileapi import admin as mobile_admin
from mobileapi import views
from mobileapi.models import MobileCopyEvent, MobileGenerationEvent


class RedactionHelperTests(TestCase):
    def test_mask_token_never_returns_full_token(self):
        raw = "tok_abcdefghijklmnopqrstuvwxyz1234567890"
        masked = views._mask_token(raw)

        self.assertNotEqual(masked, raw)
        self.assertNotIn(raw, masked)
        self.assertTrue(masked.startswith("tok_abcd"))
        self.assertTrue(masked.endswith("7890"))

    def test_mask_guest_id_and_ip_redacted(self):
        guest_id = "1234567890abcdef1234567890abcdef"
        ip_v4 = "203.0.113.77"
        ip_v6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

        self.assertNotEqual(views._mask_guest_id(guest_id), guest_id)
        self.assertNotEqual(views._mask_ip(ip_v4), ip_v4)
        self.assertNotEqual(views._mask_ip(ip_v6), ip_v6)

        self.assertEqual(views._mask_ip(ip_v4), "203.0.x.x")

    def test_safe_http_error_omits_payload_content(self):
        class FakeHttpError(Exception):
            def __init__(self):
                super().__init__("boom")
                self.status_code = 403
                self.content = b'{"secret":"raw_provider_payload_123"}'

        err = FakeHttpError()
        summary = views._safe_http_error(err)

        self.assertIn("FakeHttpError", summary)
        self.assertIn("status=403", summary)
        self.assertNotIn("raw_provider_payload_123", summary)


class AdminSeparationTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="adminsplit",
            email="adminsplit@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(self.superuser)

    def test_trialip_admin_visibility_split(self):
        self.assertNotIn(ConversationTrialIP, admin.site._registry)
        self.assertIn(HomeTrialIP, admin.site._registry)

    def test_mobile_proxy_admin_pages_resolve(self):
        urls = [
            reverse("admin:mobileapi_mobileguesttrial_changelist"),
            reverse("admin:mobileapi_mobiledevicedailyusage_changelist"),
            reverse("admin:mobileapi_mobilerecommendedopener_changelist"),
            reverse("admin:mobileapi_mobileappconfigproxy_changelist"),
            reverse("admin:mobileapi_mobilelockedreply_changelist"),
            reverse("admin:mobileapi_mobilegenerationevent_changelist"),
            reverse("admin:mobileapi_mobilecopyevent_changelist"),
            reverse("admin:mobileapi_mobilesignupuser_changelist"),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_mobile_proxy_models_registered(self):
        registered_models = set(admin.site._registry.keys())
        expected = {
            mobile_admin.MobileGuestTrial,
            mobile_admin.MobileDeviceDailyUsage,
            mobile_admin.MobileRecommendedOpener,
            mobile_admin.MobileAppConfigProxy,
            mobile_admin.MobileLockedReply,
            mobile_admin.MobileSignupUser,
            MobileGenerationEvent,
            MobileCopyEvent,
        }
        self.assertTrue(expected.issubset(registered_models))


class GuestTrialRoutingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_guest_trial_prefers_guesttrial_when_device_fingerprint_present(self):
        request = self.factory.post(
            "/api/generate/",
            {},
            format="json",
            REMOTE_ADDR="203.0.113.10",
            HTTP_X_DEVICE_FINGERPRINT="device-abc-123",
        )

        trial, created, guest_id, client_ip = views._get_or_create_guest_trial(request)
        self.assertIsInstance(trial, ConversationGuestTrial)
        self.assertEqual(guest_id, "device-abc-123")
        self.assertEqual(client_ip, "203.0.113.10")
        self.assertIn(created, (True, False))

    def test_guest_trial_falls_back_to_legacy_trialip_when_guest_id_missing(self):
        request = self.factory.post(
            "/api/generate/",
            {},
            format="json",
            REMOTE_ADDR="203.0.113.11",
            HTTP_USER_AGENT="legacy-client/1.0",
        )

        with self.assertLogs("mobileapi.views", level="WARNING") as log_ctx:
            trial, created, guest_id, client_ip = views._get_or_create_guest_trial(request)

        self.assertIsInstance(trial, ConversationTrialIP)
        self.assertEqual(guest_id, "")
        self.assertEqual(client_ip, "203.0.113.11")
        self.assertIn(created, (True, False))

        logs = "\n".join(log_ctx.output)
        self.assertIn("Guest trial fallback to legacy conversation.TrialIP", logs)


class LogSafetyTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="logsafeuser",
            email="logsafe@example.com",
            password="StrongPass123!",
        )

    def test_google_play_purchase_failure_logs_masked_token_only(self):
        raw_token = "purchase_token_super_secret_1234567890"
        request = self.factory.post(
            "/api/google-play/purchase/",
            {
                "product_id": "starter_pack_v1",
                "purchase_token": raw_token,
                "order_id": "order-123",
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        with patch(
            "mobileapi.views._verify_google_play_purchase",
            return_value=(False, "google_play_verification_failed"),
        ):
            with self.assertLogs("mobileapi.views", level="WARNING") as log_ctx:
                response = views.google_play_purchase(request)

        combined_logs = "\n".join(log_ctx.output)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(raw_token, combined_logs)
        self.assertIn(views._mask_token(raw_token), combined_logs)

    def test_verify_subscription_logs_masked_token_only(self):
        raw_token = "subscription_token_super_secret_abcdef123456"
        request = self.factory.post(
            "/api/google-play/verify-subscription/",
            {
                "product_id": "monthly_sub_v1",
                "purchase_token": raw_token,
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        with patch(
            "mobileapi.views._verify_google_play_subscription",
            return_value=(False, "google_play_verification_failed", None),
        ):
            with self.assertLogs("mobileapi.views", level="INFO") as log_ctx:
                response = views.verify_subscription(request)

        combined_logs = "\n".join(log_ctx.output)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(raw_token, combined_logs)
        self.assertIn(views._mask_token(raw_token), combined_logs)


class TokenRotationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.username = "tokenrotate"
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            username=self.username,
            email="tokenrotate@example.com",
            password=self.password,
        )

    def test_login_rotates_existing_token(self):
        old_token = Token.objects.create(user=self.user)

        response = self.client.post(
            reverse("mobile_login"),
            {"username": self.username, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get("success"))
        new_token = response.data.get("token")
        self.assertTrue(new_token)
        self.assertNotEqual(new_token, old_token.key)
        self.assertFalse(Token.objects.filter(key=old_token.key).exists())
        self.assertTrue(Token.objects.filter(user=self.user, key=new_token).exists())

    def test_change_password_rotates_token_and_invalidates_old_token(self):
        old_token = Token.objects.create(user=self.user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {old_token.key}")
        response = self.client.post(
            reverse("mobile_change_password"),
            {
                "current_password": self.password,
                "new_password": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get("success"))
        new_token = response.data.get("token")
        self.assertTrue(new_token)
        self.assertNotEqual(new_token, old_token.key)

        old_client = APIClient()
        old_client.credentials(HTTP_AUTHORIZATION=f"Token {old_token.key}")
        old_profile = old_client.get(reverse("mobile_profile"))
        self.assertEqual(old_profile.status_code, 401)

        new_client = APIClient()
        new_client.credentials(HTTP_AUTHORIZATION=f"Token {new_token}")
        new_profile = new_client.get(reverse("mobile_profile"))
        self.assertEqual(new_profile.status_code, 200)
        self.assertTrue(new_profile.data.get("success"))


class PublicEndpointRateLimitTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.ip = "203.0.113.10"
        cache.clear()
        self.user = User.objects.create_user(
            username="rateloginuser",
            email="ratelogin@example.com",
            password="StrongPass123!",
        )
        RecommendedOpener.objects.create(
            text="Test opener",
            why_it_works="It is short and friendly.",
            is_active=True,
            sort_order=1,
        )

    def tearDown(self):
        cache.clear()

    def _image(self, name="test.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\nfakepngdata",
            content_type="image/png",
        )

    @override_settings(
        MOBILE_RATELIMIT_REGISTER_IP="100/m",
        MOBILE_RATELIMIT_REGISTER_EMAIL="100/m",
        MOBILE_RATELIMIT_LOGIN_IP="100/m",
        MOBILE_RATELIMIT_LOGIN_USERNAME="100/m",
        MOBILE_RATELIMIT_PASSWORD_RESET_IP="100/m",
        MOBILE_RATELIMIT_PASSWORD_RESET_EMAIL="100/m",
        MOBILE_RATELIMIT_REPORT_IP="100/m",
        MOBILE_RATELIMIT_GENERATE_IP="100/m",
        MOBILE_RATELIMIT_GENERATE_DEVICE="100/m",
        MOBILE_RATELIMIT_GENERATE_OPENERS_IP="100/m",
        MOBILE_RATELIMIT_GENERATE_OPENERS_DEVICE="100/m",
        MOBILE_RATELIMIT_EXTRACT_IP="100/m",
        MOBILE_RATELIMIT_EXTRACT_DEVICE="100/m",
        MOBILE_RATELIMIT_EXTRACT_STREAM_IP="100/m",
        MOBILE_RATELIMIT_EXTRACT_STREAM_DEVICE="100/m",
        MOBILE_RATELIMIT_ANALYZE_IP="100/m",
        MOBILE_RATELIMIT_ANALYZE_DEVICE="100/m",
        MOBILE_RATELIMIT_ANALYZE_STREAM_IP="100/m",
        MOBILE_RATELIMIT_ANALYZE_STREAM_DEVICE="100/m",
        MOBILE_RATELIMIT_RECOMMENDED_OPENERS_IP="100/m",
    )
    def test_public_endpoints_under_limit(self):
        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", True)):
            with patch(
                "mobileapi.views.generate_mobile_openers_from_image",
                return_value=("opener", True),
            ):
                with patch(
                    "mobileapi.views.extract_conversation_from_image_mobile",
                    return_value="conversation",
                ):
                    with patch(
                        "mobileapi.views.stream_conversation_from_image_bytes",
                        return_value=iter(["delta"]),
                    ):
                        with patch("mobileapi.views.analyze_profile_image", return_value="analysis"):
                            with patch(
                                "mobileapi.views.stream_profile_analysis_bytes",
                                return_value=iter(["analysis"]),
                            ):
                                with patch("mobileapi.views.ResetPasswordForm.save"):
                                    register_resp = self.client.post(
                                        reverse("mobile_register"),
                                        {
                                            "username": "publicrateuser",
                                            "email": "publicrate@example.com",
                                            "password": "StrongPass123!",
                                        },
                                        format="json",
                                        REMOTE_ADDR=self.ip,
                                    )
                                    self.assertNotEqual(register_resp.status_code, 429)

                                    login_resp = self.client.post(
                                        reverse("mobile_login"),
                                        {
                                            "username": "rateloginuser",
                                            "password": "StrongPass123!",
                                        },
                                        format="json",
                                        REMOTE_ADDR=self.ip,
                                    )
                                    self.assertNotEqual(login_resp.status_code, 429)

                                    reset_resp = self.client.post(
                                        reverse("mobile_password_reset"),
                                        {"email": "ratelogin@example.com"},
                                        format="json",
                                        REMOTE_ADDR=self.ip,
                                    )
                                    self.assertNotEqual(reset_resp.status_code, 429)

                                    report_resp = self.client.post(
                                        reverse("report_issue"),
                                        {
                                            "reason": "bug",
                                            "title": "Issue",
                                            "subject": "Something happened",
                                            "email": "report@example.com",
                                        },
                                        format="json",
                                        REMOTE_ADDR=self.ip,
                                    )
                                    self.assertNotEqual(report_resp.status_code, 429)

                                    generate_resp = self.client.post(
                                        reverse("generate_text_with_credits"),
                                        {
                                            "last_text": "hi there",
                                            "situation": "just_matched",
                                            "tone": "Natural",
                                        },
                                        format="json",
                                        REMOTE_ADDR=self.ip,
                                        HTTP_X_DEVICE_FINGERPRINT="device-1",
                                    )
                                    self.assertNotEqual(generate_resp.status_code, 429)

                                    openers_resp = self.client.post(
                                        reverse("generate_openers_from_image"),
                                        {
                                            "profile_image": self._image("openers.png"),
                                        },
                                        format="multipart",
                                        REMOTE_ADDR=self.ip,
                                        HTTP_X_DEVICE_FINGERPRINT="device-1",
                                    )
                                    self.assertNotEqual(openers_resp.status_code, 429)

                                    extract_resp = self.client.post(
                                        reverse("extract_from_image_with_credits"),
                                        {"screenshot": self._image("extract.png")},
                                        format="multipart",
                                        REMOTE_ADDR=self.ip,
                                        HTTP_X_DEVICE_FINGERPRINT="device-1",
                                    )
                                    self.assertNotEqual(extract_resp.status_code, 429)

                                    extract_stream_resp = self.client.post(
                                        reverse("extract_from_image_with_credits_stream"),
                                        {"screenshot": self._image("extract-stream.png")},
                                        format="multipart",
                                        REMOTE_ADDR=self.ip,
                                        HTTP_X_DEVICE_FINGERPRINT="device-1",
                                    )
                                    self.assertNotEqual(extract_stream_resp.status_code, 429)

                                    analyze_resp = self.client.post(
                                        reverse("analyze_profile"),
                                        {"profile_image": self._image("analyze.png")},
                                        format="multipart",
                                        REMOTE_ADDR=self.ip,
                                        HTTP_X_DEVICE_FINGERPRINT="device-1",
                                    )
                                    self.assertNotEqual(analyze_resp.status_code, 429)

                                    analyze_stream_resp = self.client.post(
                                        reverse("analyze_profile_stream"),
                                        {"profile_image": self._image("analyze-stream.png")},
                                        format="multipart",
                                        REMOTE_ADDR=self.ip,
                                        HTTP_X_DEVICE_FINGERPRINT="device-1",
                                    )
                                    self.assertNotEqual(analyze_stream_resp.status_code, 429)

                                    recommended_resp = self.client.post(
                                        reverse("recommended_openers"),
                                        {"count": 1},
                                        format="json",
                                        REMOTE_ADDR=self.ip,
                                    )
                                    self.assertNotEqual(recommended_resp.status_code, 429)

    @override_settings(
        MOBILE_RATELIMIT_REGISTER_IP="2/m",
        MOBILE_RATELIMIT_REGISTER_EMAIL="100/m",
    )
    def test_register_over_limit_returns_json_429(self):
        for idx in range(2):
            response = self.client.post(
                reverse("mobile_register"),
                {
                    "username": f"burstuser{idx}",
                    "email": f"burst{idx}@example.com",
                    "password": "StrongPass123!",
                },
                format="json",
                REMOTE_ADDR=self.ip,
            )
            self.assertNotEqual(response.status_code, 429)

        blocked = self.client.post(
            reverse("mobile_register"),
            {
                "username": "burstuser2",
                "email": "burst2@example.com",
                "password": "StrongPass123!",
            },
            format="json",
            REMOTE_ADDR=self.ip,
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json().get("error"), "rate_limited")

    @override_settings(
        MOBILE_RATELIMIT_GENERATE_IP="2/m",
        MOBILE_RATELIMIT_GENERATE_DEVICE="100/m",
    )
    def test_generate_ip_limit_blocks_rotating_device_ids(self):
        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", True)) as mocked_generate:
            for idx in range(2):
                response = self.client.post(
                    reverse("generate_text_with_credits"),
                    {
                        "last_text": "hello",
                        "situation": "just_matched",
                        "tone": "Natural",
                    },
                    format="json",
                    REMOTE_ADDR=self.ip,
                    HTTP_X_DEVICE_FINGERPRINT=f"device-{idx}",
                )
                self.assertNotEqual(response.status_code, 429)

            blocked = self.client.post(
                reverse("generate_text_with_credits"),
                {
                    "last_text": "hello",
                    "situation": "just_matched",
                    "tone": "Natural",
                },
                format="json",
                REMOTE_ADDR=self.ip,
                HTTP_X_DEVICE_FINGERPRINT="device-rotated",
            )
            self.assertEqual(blocked.status_code, 429)
            self.assertEqual(blocked.json().get("error"), "rate_limited")
            self.assertEqual(mocked_generate.call_count, 2)

    @override_settings(MOBILE_RATELIMIT_RECOMMENDED_OPENERS_IP="1/m")
    def test_authenticated_endpoints_not_affected_by_public_limits(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        profile_response = self.client.get(reverse("mobile_profile"), REMOTE_ADDR=self.ip)
        self.assertEqual(profile_response.status_code, 200)


@override_settings(
    MOBILE_RATELIMIT_GENERATE_IP="100/m",
    MOBILE_RATELIMIT_GENERATE_DEVICE="100/m",
    MOBILE_RATELIMIT_GENERATE_OPENERS_IP="100/m",
    MOBILE_RATELIMIT_GENERATE_OPENERS_DEVICE="100/m",
    MOBILE_RATELIMIT_EXTRACT_IP="100/m",
    MOBILE_RATELIMIT_EXTRACT_DEVICE="100/m",
)
class MobileConfigRoutingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cfg = MobileAppConfig.load()
        self.cfg.guest_lifetime_credits = 10
        self.cfg.fallback_model = "gpt-4.1-mini-2025-04-14"
        self.cfg.save()

    def _image(self, name="test.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\nfakepngdata",
            content_type="image/png",
        )

    def test_guest_reply_uses_configured_model_and_thinking(self):
        self.cfg.free_reply_model = "gemini-3-pro-preview"
        self.cfg.free_reply_thinking = "medium"
        self.cfg.save()

        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", True)) as mocked_generate:
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {
                    "last_text": "hello",
                    "situation": "just_matched",
                    "tone": "Natural",
                },
                format="json",
                REMOTE_ADDR="203.0.113.21",
                HTTP_X_DEVICE_FINGERPRINT="cfg-device-reply",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked_generate.called)
        kwargs = mocked_generate.call_args.kwargs
        self.assertEqual(kwargs.get("primary_model"), self.cfg.free_reply_model)
        self.assertEqual(kwargs.get("fallback_model"), self.cfg.fallback_model)
        self.assertEqual(kwargs.get("thinking_level"), self.cfg.free_reply_thinking)

    def test_guest_openers_use_configured_model_and_thinking(self):
        self.cfg.free_opener_model = "gemini-3-pro-preview"
        self.cfg.free_opener_thinking = "low"
        self.cfg.save()

        with patch("mobileapi.views.generate_mobile_openers_from_image", return_value=("reply", True)) as mocked_generate:
            response = self.client.post(
                reverse("generate_openers_from_image"),
                {"profile_image": self._image("openers-cfg.png")},
                format="multipart",
                REMOTE_ADDR="203.0.113.22",
                HTTP_X_DEVICE_FINGERPRINT="cfg-device-openers",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked_generate.called)
        kwargs = mocked_generate.call_args.kwargs
        self.assertEqual(kwargs.get("primary_model"), self.cfg.free_opener_model)
        self.assertEqual(kwargs.get("fallback_model"), self.cfg.fallback_model)
        self.assertEqual(kwargs.get("thinking_level"), self.cfg.free_opener_thinking)

    def test_registered_non_subscriber_reply_uses_registered_model_and_not_tier(self):
        self.cfg.registered_reply_model = "gemini-3-pro-preview"
        self.cfg.registered_reply_thinking = "minimal"
        self.cfg.free_reply_model = "gemini-3-flash-preview"
        self.cfg.free_reply_thinking = "high"
        self.cfg.save()

        user = User.objects.create_user(
            username="regfreeuser",
            email="regfree@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        chat_credit = user.chat_credit
        chat_credit.is_subscribed = False
        chat_credit.save(update_fields=["is_subscribed"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        with patch("mobileapi.views._get_subscriber_tier") as mocked_tier, patch(
            "mobileapi.views.generate_mobile_response",
            return_value=("reply", True),
        ) as mocked_generate:
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {
                    "last_text": "hello",
                    "situation": "just_matched",
                    "tone": "Natural",
                },
                format="json",
                REMOTE_ADDR="203.0.113.25",
                HTTP_X_DEVICE_FINGERPRINT="cfg-device-registered-reply",
            )

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_generate.call_args.kwargs
        self.assertEqual(kwargs.get("primary_model"), self.cfg.registered_reply_model)
        self.assertEqual(kwargs.get("fallback_model"), self.cfg.fallback_model)
        self.assertEqual(kwargs.get("thinking_level"), self.cfg.registered_reply_thinking)
        mocked_tier.assert_not_called()

    def test_registered_non_subscriber_openers_use_registered_model_and_not_tier(self):
        self.cfg.registered_opener_model = "gemini-3-pro-preview"
        self.cfg.registered_opener_thinking = "minimal"
        self.cfg.free_opener_model = "gemini-3-flash-preview"
        self.cfg.free_opener_thinking = "high"
        self.cfg.save()

        user = User.objects.create_user(
            username="regfreeopeners",
            email="regfreeopeners@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        chat_credit = user.chat_credit
        chat_credit.is_subscribed = False
        chat_credit.save(update_fields=["is_subscribed"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        with patch("mobileapi.views._get_subscriber_tier") as mocked_tier, patch(
            "mobileapi.views.generate_mobile_openers_from_image",
            return_value=("reply", True),
        ) as mocked_generate:
            response = self.client.post(
                reverse("generate_openers_from_image"),
                {"profile_image": self._image("openers-registered-cfg.png")},
                format="multipart",
                REMOTE_ADDR="203.0.113.26",
                HTTP_X_DEVICE_FINGERPRINT="cfg-device-registered-openers",
            )

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_generate.call_args.kwargs
        self.assertEqual(kwargs.get("primary_model"), self.cfg.registered_opener_model)
        self.assertEqual(kwargs.get("fallback_model"), self.cfg.fallback_model)
        self.assertEqual(kwargs.get("thinking_level"), self.cfg.registered_opener_thinking)
        mocked_tier.assert_not_called()

    def test_subscriber_reply_uses_tier_model_and_thinking(self):
        user = User.objects.create_user(
            username="subtieruser",
            email="subtier@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        chat_credit = user.chat_credit
        chat_credit.is_subscribed = True
        chat_credit.subscription_expiry = timezone.now() + timedelta(days=30)
        chat_credit.save(update_fields=["is_subscribed", "subscription_expiry"])

        self.cfg.tiers.all().delete()
        DegradationTier.objects.create(
            config=self.cfg,
            tier_type="reply",
            sort_order=1,
            threshold=100,
            model="gemini-3-pro-preview",
            thinking_level="minimal",
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", True)) as mocked_generate:
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {
                    "last_text": "hello",
                    "situation": "just_matched",
                    "tone": "Natural",
                },
                format="json",
                REMOTE_ADDR="203.0.113.23",
                HTTP_X_DEVICE_FINGERPRINT="cfg-device-sub",
            )

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_generate.call_args.kwargs
        self.assertEqual(kwargs.get("primary_model"), "gemini-3-pro-preview")
        self.assertEqual(kwargs.get("fallback_model"), self.cfg.fallback_model)
        self.assertEqual(kwargs.get("thinking_level"), "minimal")

    def test_extract_uses_configured_ocr_thinking(self):
        self.cfg.ocr_thinking = "medium"
        self.cfg.save()

        with patch("mobileapi.views.extract_conversation_from_image_mobile", return_value="conversation") as mocked_extract:
            response = self.client.post(
                reverse("extract_from_image_with_credits"),
                {"screenshot": self._image("ocr-cfg.png")},
                format="multipart",
                REMOTE_ADDR="203.0.113.24",
                HTTP_X_DEVICE_FINGERPRINT="cfg-device-ocr",
            )

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_extract.call_args.kwargs
        self.assertEqual(kwargs.get("thinking_level"), self.cfg.ocr_thinking)

    def test_subscriber_reply_daily_usage_consumed_only_on_success(self):
        user = User.objects.create_user(
            username="subdailyuser",
            email="subdaily@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        chat_credit = user.chat_credit
        chat_credit.is_subscribed = True
        chat_credit.subscription_expiry = timezone.now() + timedelta(days=30)
        chat_credit.subscriber_daily_replies = 0
        chat_credit.save(
            update_fields=[
                "is_subscribed",
                "subscription_expiry",
                "subscriber_daily_replies",
            ]
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", False)):
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {"last_text": "hello", "situation": "just_matched", "tone": "Natural"},
                format="json",
                REMOTE_ADDR="203.0.113.31",
                HTTP_X_DEVICE_FINGERPRINT="usage-sub-fail",
            )
        self.assertEqual(response.status_code, 200)
        chat_credit.refresh_from_db()
        self.assertEqual(chat_credit.subscriber_daily_replies, 0)

        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", True)):
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {"last_text": "hello", "situation": "just_matched", "tone": "Natural"},
                format="json",
                REMOTE_ADDR="203.0.113.31",
                HTTP_X_DEVICE_FINGERPRINT="usage-sub-success",
            )
        self.assertEqual(response.status_code, 200)
        chat_credit.refresh_from_db()
        self.assertEqual(chat_credit.subscriber_daily_replies, 1)

    def test_free_reply_daily_usage_consumed_only_on_success(self):
        user = User.objects.create_user(
            username="freedailyuser",
            email="freedaily@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        chat_credit = user.chat_credit
        chat_credit.is_subscribed = False
        chat_credit.free_daily_credits_used = 0
        chat_credit.save(update_fields=["is_subscribed", "free_daily_credits_used"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", False)):
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {"last_text": "hello", "situation": "just_matched", "tone": "Natural"},
                format="json",
                REMOTE_ADDR="203.0.113.32",
                HTTP_X_DEVICE_FINGERPRINT="usage-free-fail",
            )
        self.assertEqual(response.status_code, 200)
        chat_credit.refresh_from_db()
        self.assertEqual(chat_credit.free_daily_credits_used, 0)

        with patch("mobileapi.views.generate_mobile_response", return_value=("reply", True)):
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {"last_text": "hello", "situation": "just_matched", "tone": "Natural"},
                format="json",
                REMOTE_ADDR="203.0.113.32",
                HTTP_X_DEVICE_FINGERPRINT="usage-free-success",
            )
        self.assertEqual(response.status_code, 200)
        chat_credit.refresh_from_db()
        self.assertEqual(chat_credit.free_daily_credits_used, 1)

    def test_subscriber_weekly_ocr_usage_consumed_only_on_success(self):
        user = User.objects.create_user(
            username="subocruser",
            email="subocr@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        chat_credit = user.chat_credit
        chat_credit.is_subscribed = True
        chat_credit.subscription_expiry = timezone.now() + timedelta(days=30)
        chat_credit.subscriber_weekly_actions = 0
        chat_credit.save(
            update_fields=[
                "is_subscribed",
                "subscription_expiry",
                "subscriber_weekly_actions",
            ]
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        with patch(
            "mobileapi.views.extract_conversation_from_image_mobile",
            return_value="Failed to extract the conversation with timestamps.",
        ):
            response = self.client.post(
                reverse("extract_from_image_with_credits"),
                {"screenshot": self._image("ocr-fail.png")},
                format="multipart",
                REMOTE_ADDR="203.0.113.33",
                HTTP_X_DEVICE_FINGERPRINT="usage-ocr-fail",
            )
        self.assertEqual(response.status_code, 200)
        chat_credit.refresh_from_db()
        self.assertEqual(chat_credit.subscriber_weekly_actions, 0)

        with patch(
            "mobileapi.views.extract_conversation_from_image_mobile",
            return_value="you []: hi",
        ):
            response = self.client.post(
                reverse("extract_from_image_with_credits"),
                {"screenshot": self._image("ocr-success.png")},
                format="multipart",
                REMOTE_ADDR="203.0.113.33",
                HTTP_X_DEVICE_FINGERPRINT="usage-ocr-success",
            )
        self.assertEqual(response.status_code, 200)
        chat_credit.refresh_from_db()
        self.assertEqual(chat_credit.subscriber_weekly_actions, 1)


@override_settings(
    MOBILE_RATELIMIT_GENERATE_IP="100/m",
    MOBILE_RATELIMIT_GENERATE_DEVICE="100/m",
    MOBILE_RATELIMIT_GENERATE_OPENERS_IP="100/m",
    MOBILE_RATELIMIT_GENERATE_OPENERS_DEVICE="100/m",
    MOBILE_RATELIMIT_RECOMMENDED_OPENERS_IP="100/m",
)
class MobileAnalyticsEventTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cfg = MobileAppConfig.load()
        self.cfg.guest_lifetime_credits = 10
        self.cfg.save()

    def _image(self, name="analytics.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\nanalytics",
            content_type="image/png",
        )

    def test_generate_logs_reply_event_with_ocr_context(self):
        with patch(
            "mobileapi.views.generate_mobile_response",
            return_value=(
                '[{"message":"Sure, let us do Friday."}]',
                True,
                {
                    "model_used": "gemini-3-flash-preview",
                    "thinking_used": "medium",
                    "usage": {
                        "input_tokens": 101,
                        "output_tokens": 22,
                        "thinking_tokens": 41,
                        "total_tokens": 164,
                    },
                    "source_type": "ai",
                },
            ),
        ):
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {
                    "last_text": "you []: hey\nher []: hi",
                    "situation": "stuck_after_reply",
                    "tone": "Natural",
                    "input_source": "ocr",
                    "ocr_text": "you []: hey\nher []: hi",
                },
                format="json",
                REMOTE_ADDR="203.0.113.101",
                HTTP_X_DEVICE_FINGERPRINT="analytics-ocr-device",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MobileGenerationEvent.objects.count(), 1)
        event = MobileGenerationEvent.objects.first()
        self.assertIsNotNone(event)
        self.assertEqual(event.action_type, MobileGenerationEvent.ActionType.REPLY)
        self.assertEqual(event.reply_ocr_text, "you []: hey\nher []: hi")
        self.assertEqual(event.model_used, "gemini-3-flash-preview")
        self.assertEqual(event.total_tokens, 164)
        self.assertEqual(response.data.get("generation_event_id"), event.pk)

    def test_generate_does_not_store_manual_reply_context(self):
        with patch(
            "mobileapi.views.generate_mobile_response",
            return_value=(
                '[{"message":"Got you"}]',
                True,
                {
                    "model_used": "gemini-3-flash-preview",
                    "thinking_used": "low",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "thinking_tokens": 1,
                        "total_tokens": 16,
                    },
                    "source_type": "ai",
                },
            ),
        ):
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {
                    "last_text": "manual message context",
                    "situation": "stuck_after_reply",
                    "tone": "Natural",
                    "input_source": "manual",
                    "ocr_text": "should_not_store",
                },
                format="json",
                REMOTE_ADDR="203.0.113.102",
                HTTP_X_DEVICE_FINGERPRINT="analytics-manual-device",
            )

        self.assertEqual(response.status_code, 200)
        event = MobileGenerationEvent.objects.latest("id")
        self.assertIsNone(event.reply_ocr_text)

    def test_generate_defaults_legacy_input_source_to_ocr(self):
        with patch(
            "mobileapi.views.generate_mobile_response",
            return_value=(
                '[{"message":"Works for me"}]',
                True,
                {
                    "model_used": "gemini-3-flash-preview",
                    "thinking_used": "medium",
                    "usage": {
                        "input_tokens": 15,
                        "output_tokens": 7,
                        "thinking_tokens": 3,
                        "total_tokens": 25,
                    },
                    "source_type": "ai",
                },
            ),
        ):
            response = self.client.post(
                reverse("generate_text_with_credits"),
                {
                    "last_text": "you []: hello\nher []: hi there",
                    "situation": "stuck_after_reply",
                    "tone": "Natural",
                },
                format="json",
                REMOTE_ADDR="203.0.113.107",
                HTTP_X_DEVICE_FINGERPRINT="analytics-legacy-device",
            )

        self.assertEqual(response.status_code, 200)
        event = MobileGenerationEvent.objects.latest("id")
        self.assertEqual(event.reply_ocr_text, "you []: hello\nher []: hi there")
        self.assertEqual(event.metadata.get("input_source"), "ocr")

    def test_generate_openers_logs_event_with_model_thinking_and_tokens(self):
        with patch(
            "mobileapi.views.generate_mobile_openers_from_image",
            return_value=(
                '[{"message":"You look like trouble in a good way."}]',
                True,
                {
                    "model_used": "gemini-3-pro-preview",
                    "thinking_used": "high",
                    "usage": {
                        "input_tokens": 66,
                        "output_tokens": 44,
                        "thinking_tokens": 11,
                        "total_tokens": 121,
                    },
                    "source_type": "ai",
                },
            ),
        ):
            response = self.client.post(
                reverse("generate_openers_from_image"),
                {"profile_image": self._image("openers-analytics.png")},
                format="multipart",
                REMOTE_ADDR="203.0.113.103",
                HTTP_X_DEVICE_FINGERPRINT="analytics-openers-device",
            )

        self.assertEqual(response.status_code, 200)
        event = MobileGenerationEvent.objects.latest("id")
        self.assertEqual(event.action_type, MobileGenerationEvent.ActionType.OPENER)
        self.assertEqual(event.model_used, "gemini-3-pro-preview")
        self.assertEqual(event.thinking_used, "high")
        self.assertEqual(event.total_tokens, 121)
        self.assertEqual(response.data.get("generation_event_id"), event.pk)

    def test_recommended_openers_logs_static_generation_event(self):
        RecommendedOpener.objects.create(
            text="Hey troublemaker.",
            why_it_works="Short and playful.",
            is_active=True,
            sort_order=1,
        )

        response = self.client.post(
            reverse("recommended_openers"),
            {"count": 1},
            format="json",
            REMOTE_ADDR="203.0.113.104",
            HTTP_X_DEVICE_FINGERPRINT="analytics-reco-device",
        )

        self.assertEqual(response.status_code, 200)
        event = MobileGenerationEvent.objects.latest("id")
        self.assertEqual(event.source_type, MobileGenerationEvent.SourceType.RECOMMENDED_STATIC)
        self.assertEqual(event.model_used, MobileGenerationEvent.SourceType.RECOMMENDED_STATIC)
        self.assertEqual(event.total_tokens, 0)
        self.assertEqual(response.data.get("generation_event_id"), event.pk)

    def test_copy_event_accepts_opener_copy_for_guest(self):
        guest_hash = views._hash_device_fingerprint("copy-device-guest")
        generation_event = MobileGenerationEvent.objects.create(
            user_type=MobileGenerationEvent.UserType.FREE,
            action_type=MobileGenerationEvent.ActionType.OPENER,
            source_type=MobileGenerationEvent.SourceType.AI,
            guest_id_hash=guest_hash,
            model_used="gemini-3-flash-preview",
            thinking_used="low",
            generated_json='[{"message":"Hey"}]',
        )

        response = self.client.post(
            reverse("mobile_copy_event"),
            {
                "copied_text": "Hey there",
                "copy_type": "opener",
                "generation_event_id": generation_event.pk,
            },
            format="json",
            REMOTE_ADDR="203.0.113.105",
            HTTP_X_DEVICE_FINGERPRINT="copy-device-guest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("success"), True)
        copy_event = MobileCopyEvent.objects.latest("id")
        self.assertEqual(copy_event.copy_type, MobileCopyEvent.CopyType.OPENER)
        self.assertEqual(copy_event.generation_event_id, generation_event.pk)

    def test_copy_event_requires_reply_ocr_context_for_reply_type(self):
        response = self.client.post(
            reverse("mobile_copy_event"),
            {
                "copied_text": "Let us do Friday",
                "copy_type": "reply",
            },
            format="json",
            REMOTE_ADDR="203.0.113.106",
            HTTP_X_DEVICE_FINGERPRINT="copy-device-invalid",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error"), "reply_context_ocr_text_required")

    def test_copy_event_supports_authenticated_users(self):
        user = User.objects.create_user(
            username="copyauthuser",
            email="copyauth@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        generation_event = MobileGenerationEvent.objects.create(
            user=user,
            user_type=MobileGenerationEvent.UserType.AUTHENTICATED_NON_SUBSCRIBED,
            action_type=MobileGenerationEvent.ActionType.REPLY,
            source_type=MobileGenerationEvent.SourceType.AI,
            model_used="gemini-3-flash-preview",
            thinking_used="medium",
            generated_json='[{"message":"Sounds good"}]',
        )

        response = self.client.post(
            reverse("mobile_copy_event"),
            {
                "copied_text": "Sounds good",
                "copy_type": "reply",
                "reply_context_ocr_text": "you []: hi\nher []: hey",
                "generation_event_id": generation_event.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        copy_event = MobileCopyEvent.objects.latest("id")
        self.assertEqual(copy_event.user_id, user.id)
        self.assertEqual(
            copy_event.user_type,
            MobileCopyEvent.UserType.AUTHENTICATED_NON_SUBSCRIBED,
        )


class MobileSignupAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="adminmobileanalytics",
            email="adminmobileanalytics@example.com",
            password="StrongPass123!",
        )
        self.factory = RequestFactory()

    def test_signup_list_contains_only_users_with_mobile_events(self):
        active_user = User.objects.create_user(
            username="active_mobile_user",
            email="active-mobile@example.com",
            password="StrongPass123!",
        )
        inactive_user = User.objects.create_user(
            username="inactive_mobile_user",
            email="inactive-mobile@example.com",
            password="StrongPass123!",
        )

        MobileGenerationEvent.objects.create(
            user=active_user,
            user_type=MobileGenerationEvent.UserType.AUTHENTICATED_NON_SUBSCRIBED,
            action_type=MobileGenerationEvent.ActionType.REPLY,
            source_type=MobileGenerationEvent.SourceType.AI,
            model_used="gemini-3-flash-preview",
            thinking_used="low",
            generated_json='[{"message":"Hi"}]',
        )

        request = self.factory.get(reverse("admin:mobileapi_mobilesignupuser_changelist"))
        request.user = self.superuser

        admin_obj = mobile_admin.MobileSignupUserAdmin(
            mobile_admin.MobileSignupUser,
            admin.site,
        )
        queryset = admin_obj.get_queryset(request)

        self.assertIn(active_user, queryset)
        self.assertNotIn(inactive_user, queryset)
