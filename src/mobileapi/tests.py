from unittest.mock import Mock, patch
from datetime import timedelta
import requests

from django.contrib import admin
from django.db import connection
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
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from reignitehome.models import MarketingClickEvent, TrialIP as HomeTrialIP
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from community.models import (
    CommunityComment,
    CommunityPost,
    PollVote,
    PostPoll,
    PostVote,
    UserBlock,
)

from mobileapi import admin as mobile_admin
from mobileapi import views
from mobileapi.models import (
    MobileCopyEvent,
    MobileGenerationEvent,
    MobileInstallAttributionEvent,
    MobileReplyThread,
)
from mobileapi.push_notifications import send_post_comment_notification


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

    def test_extract_image_logs_ocr_event_with_usage_tokens(self):
        with patch(
            "mobileapi.views.extract_conversation_from_image_mobile",
            return_value=(
                "you []: hi\nher []: hey",
                True,
                {
                    "model_used": "gemini-3-flash-preview",
                    "thinking_used": "low",
                    "usage": {
                        "input_tokens": 222,
                        "output_tokens": 40,
                        "thinking_tokens": 18,
                        "total_tokens": 280,
                    },
                    "source_type": "ai",
                },
            ),
        ):
            response = self.client.post(
                reverse("extract_from_image_with_credits"),
                {"screenshot": self._image("ocr-analytics.png")},
                format="multipart",
                REMOTE_ADDR="203.0.113.108",
                HTTP_X_DEVICE_FINGERPRINT="analytics-ocr-usage-device",
            )

        self.assertEqual(response.status_code, 200)
        event = MobileGenerationEvent.objects.latest("id")
        self.assertEqual(event.action_type, MobileGenerationEvent.ActionType.OCR)
        self.assertEqual(event.model_used, "gemini-3-flash-preview")
        self.assertEqual(event.input_tokens, 222)
        self.assertEqual(event.output_tokens, 40)
        self.assertEqual(event.thinking_tokens, 18)
        self.assertEqual(event.total_tokens, 280)
        self.assertEqual(response.data.get("generation_event_id"), event.pk)

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

    def test_recommended_openers_vault_guest_returns_full_archive_with_one_opened(self):
        RecommendedOpener.objects.all().delete()
        for idx in range(1, 6):
            RecommendedOpener.objects.create(
                text=f"Vault opener {idx}",
                why_it_works=f"Why {idx}",
                is_active=True,
                sort_order=idx,
            )

        response = self.client.post(
            reverse("recommended_openers"),
            {"mode": "vault"},
            format="json",
            REMOTE_ADDR="203.0.113.141",
            HTTP_X_DEVICE_FINGERPRINT="vault-guest-device",
        )

        self.assertEqual(response.status_code, 200)
        openers = response.data.get("openers") or []
        self.assertEqual(len(openers), 5)
        unlocked = [item for item in openers if item.get("is_locked") is False]
        locked = [item for item in openers if item.get("is_locked") is True]
        self.assertEqual(len(unlocked), 1)
        self.assertEqual(len(locked), 4)
        self.assertEqual(openers[0].get("is_locked"), False)
        self.assertEqual(openers[0].get("id"), unlocked[0].get("id"))
        self.assertTrue((unlocked[0].get("message") or "").strip())
        self.assertIsNone(unlocked[0].get("blur_preview"))
        expected_locked_text_by_id = {
            opener.id: opener.text
            for opener in RecommendedOpener.objects.filter(
                id__in=[item.get("id") for item in locked]
            )
        }
        for item in locked:
            self.assertIsNone(item.get("message"))
            self.assertTrue((item.get("blur_preview") or "").strip())
            self.assertEqual(
                (item.get("blur_preview") or "").strip(),
                expected_locked_text_by_id.get(item.get("id"), "").strip(),
            )

        vault_meta = response.data.get("vault_meta") or {}
        self.assertEqual(vault_meta.get("tier"), "guest")
        self.assertEqual(vault_meta.get("cta"), "auth_then_paywall")
        self.assertEqual(vault_meta.get("archive_total"), 5)
        self.assertEqual(vault_meta.get("display_count"), 5)

    def test_recommended_openers_vault_free_is_stable_within_same_day(self):
        RecommendedOpener.objects.all().delete()
        user = User.objects.create_user(
            username="vaultfreeuser",
            email="vaultfree@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        for idx in range(1, 11):
            RecommendedOpener.objects.create(
                text=f"Daily opener {idx}",
                why_it_works=f"Daily why {idx}",
                is_active=True,
                sort_order=idx,
            )

        response1 = self.client.post(
            reverse("recommended_openers"),
            {"mode": "vault"},
            format="json",
            REMOTE_ADDR="203.0.113.142",
            HTTP_X_DEVICE_FINGERPRINT="vault-free-device",
        )
        response2 = self.client.post(
            reverse("recommended_openers"),
            {"mode": "vault"},
            format="json",
            REMOTE_ADDR="203.0.113.142",
            HTTP_X_DEVICE_FINGERPRINT="vault-free-device",
        )

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        openers1 = response1.data.get("openers") or []
        openers2 = response2.data.get("openers") or []
        self.assertEqual(len(openers1), 10)
        self.assertEqual(len(openers2), 10)
        self.assertEqual(
            [item.get("id") for item in openers1],
            [item.get("id") for item in openers2],
        )
        unlocked1 = [item.get("id") for item in openers1 if item.get("is_locked") is False]
        unlocked2 = [item.get("id") for item in openers2 if item.get("is_locked") is False]
        self.assertEqual(len(unlocked1), 3)
        self.assertEqual(unlocked1, unlocked2)
        self.assertTrue(all(item.get("is_locked") is False for item in openers1[:3]))
        self.assertTrue(all(item.get("is_locked") is True for item in openers1[3:]))
        self.assertEqual((response1.data.get("vault_meta") or {}).get("tier"), "free")
        self.assertEqual((response1.data.get("vault_meta") or {}).get("cta"), "paywall")

    def test_recommended_openers_vault_free_admin_priority_controls_unlocked_order(self):
        RecommendedOpener.objects.all().delete()
        user = User.objects.create_user(
            username="vaultfreepriorityuser",
            email="vaultfreepriority@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        openers = []
        for idx in range(1, 7):
            opener = RecommendedOpener.objects.create(
                text=f"Priority opener {idx}",
                why_it_works=f"Priority why {idx}",
                is_active=True,
                sort_order=idx,
            )
            openers.append(opener)

        openers[1].vault_unblurred_priority = 1
        openers[4].vault_unblurred_priority = 2
        openers[5].vault_unblurred_priority = 3
        RecommendedOpener.objects.bulk_update(
            [openers[1], openers[4], openers[5]],
            ["vault_unblurred_priority"],
        )

        response = self.client.post(
            reverse("recommended_openers"),
            {"mode": "vault"},
            format="json",
            REMOTE_ADDR="203.0.113.152",
            HTTP_X_DEVICE_FINGERPRINT="vault-free-priority-device",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.data.get("openers") or []
        self.assertEqual(len(payload), 6)
        expected_top_ids = [openers[1].id, openers[4].id, openers[5].id]
        self.assertEqual([item.get("id") for item in payload[:3]], expected_top_ids)
        self.assertTrue(all(item.get("is_locked") is False for item in payload[:3]))
        self.assertTrue(all(item.get("is_locked") is True for item in payload[3:]))

    def test_recommended_openers_vault_guest_uses_first_admin_priority_opener(self):
        RecommendedOpener.objects.all().delete()
        openers = []
        for idx in range(1, 6):
            opener = RecommendedOpener.objects.create(
                text=f"Guest priority opener {idx}",
                why_it_works=f"Guest priority why {idx}",
                is_active=True,
                sort_order=idx,
            )
            openers.append(opener)

        openers[2].vault_unblurred_priority = 1
        openers[4].vault_unblurred_priority = 2
        RecommendedOpener.objects.bulk_update(
            [openers[2], openers[4]],
            ["vault_unblurred_priority"],
        )

        response = self.client.post(
            reverse("recommended_openers"),
            {"mode": "vault"},
            format="json",
            REMOTE_ADDR="203.0.113.153",
            HTTP_X_DEVICE_FINGERPRINT="vault-guest-priority-device",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.data.get("openers") or []
        self.assertEqual(len(payload), 5)
        self.assertEqual(payload[0].get("id"), openers[2].id)
        self.assertEqual(payload[0].get("is_locked"), False)
        self.assertTrue(all(item.get("is_locked") is True for item in payload[1:]))

    def test_recommended_openers_vault_elite_returns_full_archive(self):
        RecommendedOpener.objects.all().delete()
        user = User.objects.create_user(
            username="vaulteliteuser",
            email="vaultelite@example.com",
            password="StrongPass123!",
        )
        chat_credit = user.chat_credit
        chat_credit.is_subscribed = True
        chat_credit.subscription_expiry = timezone.now() + timedelta(days=30)
        chat_credit.save(update_fields=["is_subscribed", "subscription_expiry"])
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        for idx in range(1, 26):
            RecommendedOpener.objects.create(
                text=f"Elite opener {idx}",
                why_it_works=f"Elite why {idx}",
                is_active=True,
                sort_order=idx,
            )

        response = self.client.post(
            reverse("recommended_openers"),
            {"mode": "vault"},
            format="json",
            REMOTE_ADDR="203.0.113.143",
            HTTP_X_DEVICE_FINGERPRINT="vault-elite-device",
        )

        self.assertEqual(response.status_code, 200)
        openers = response.data.get("openers") or []
        self.assertEqual(len(openers), 25)
        expected_ids = list(
            RecommendedOpener.objects.filter(is_active=True)
            .order_by("sort_order", "id")
            .values_list("id", flat=True)
        )
        self.assertEqual([item.get("id") for item in openers], expected_ids)
        self.assertTrue(all(item.get("is_locked") is False for item in openers))

        vault_meta = response.data.get("vault_meta") or {}
        self.assertEqual(vault_meta.get("tier"), "elite")
        self.assertEqual(vault_meta.get("cta"), "none")
        self.assertEqual(vault_meta.get("archive_total"), 25)
        self.assertEqual(vault_meta.get("display_count"), 25)

    def test_vault_daily_drop_helper_is_stable_and_day_sensitive(self):
        candidates = list(range(1, 101))
        day_a_first = views._select_vault_daily_drop(candidates, "2026-03-02", count=3)
        day_a_second = views._select_vault_daily_drop(candidates, "2026-03-02", count=3)
        day_b = views._select_vault_daily_drop(candidates, "2026-03-03", count=3)

        self.assertEqual(day_a_first, day_a_second)
        self.assertNotEqual(day_a_first, day_b)

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


@override_settings(
    COMMUNITY_RATELIMIT_POST_CREATE="100/m",
    COMMUNITY_RATELIMIT_COMMENT_CREATE="100/m",
)
class CommunityApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.author = User.objects.create_user(
            username="communityauthor",
            email="communityauthor@example.com",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="communityother",
            email="communityother@example.com",
            password="StrongPass123!",
        )
        self.reporter = User.objects.create_user(
            username="communityreporter",
            email="communityreporter@example.com",
            password="StrongPass123!",
        )
        self.staff_user = User.objects.create_superuser(
            username="communitystaff",
            email="communitystaff@example.com",
            password="StrongPass123!",
        )

        self.author_token = Token.objects.create(user=self.author)
        self.other_token = Token.objects.create(user=self.other_user)
        self.reporter_token = Token.objects.create(user=self.reporter)
        self.staff_token = Token.objects.create(user=self.staff_user)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def _as_guest(self):
        self.client.credentials()

    def test_list_hides_future_scheduled_posts_for_non_staff(self):
        now = timezone.now()
        visible_post = CommunityPost.objects.create(
            author=self.author,
            title="Visible Post",
            body="Visible body",
            category="help_me_reply",
            published_at=now - timedelta(hours=1),
        )
        future_post = CommunityPost.objects.create(
            author=self.author,
            title="Future Post",
            body="Future body",
            category="help_me_reply",
            published_at=now + timedelta(hours=1),
        )

        self._as_guest()
        guest_resp = self.client.get(reverse("community_post_list"))
        self.assertEqual(guest_resp.status_code, 200)
        guest_ids = [item["id"] for item in guest_resp.data["posts"]]
        self.assertIn(visible_post.id, guest_ids)
        self.assertNotIn(future_post.id, guest_ids)

        self._auth(self.other_token)
        user_resp = self.client.get(reverse("community_post_list"))
        self.assertEqual(user_resp.status_code, 200)
        user_ids = [item["id"] for item in user_resp.data["posts"]]
        self.assertIn(visible_post.id, user_ids)
        self.assertNotIn(future_post.id, user_ids)

    def test_detail_hides_future_scheduled_posts_for_non_staff(self):
        future_post = CommunityPost.objects.create(
            author=self.author,
            title="Future Detail Post",
            body="Future detail body",
            category="help_me_reply",
            published_at=timezone.now() + timedelta(hours=1),
        )

        self._as_guest()
        guest_resp = self.client.get(
            reverse("community_post_detail", args=[future_post.id])
        )
        self.assertEqual(guest_resp.status_code, 404)

        self._auth(self.other_token)
        other_resp = self.client.get(
            reverse("community_post_detail", args=[future_post.id])
        )
        self.assertEqual(other_resp.status_code, 404)

        self._auth(self.author_token)
        author_resp = self.client.get(
            reverse("community_post_detail", args=[future_post.id])
        )
        self.assertEqual(author_resp.status_code, 404)

    def test_staff_can_view_future_scheduled_post_detail(self):
        future_post = CommunityPost.objects.create(
            author=self.author,
            title="Staff Visible Future Post",
            body="Future body for staff",
            category="help_me_reply",
            published_at=timezone.now() + timedelta(hours=2),
        )

        self._auth(self.staff_token)
        response = self.client.get(reverse("community_post_detail", args=[future_post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], future_post.id)

    def test_create_post_with_string_false_is_not_anonymous(self):
        self._auth(self.author_token)
        response = self.client.post(
            reverse("community_post_list"),
            {
                "title": "Boolean Parse Post",
                "body": "Check string false parsing.",
                "category": "help_me_reply",
                "is_anonymous": "false",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_anonymous"])
        self.assertEqual(response.data["author"]["id"], self.author.id)

        created = CommunityPost.objects.get(pk=response.data["id"])
        self.assertFalse(created.is_anonymous)

    def test_create_and_filter_dating_advice_category(self):
        self._auth(self.author_token)
        create_response = self.client.post(
            reverse("community_post_list"),
            {
                "title": "Dating advice question",
                "body": "Should I text first after the date?",
                "category": "dating_advice",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["category"], "dating_advice")

        CommunityPost.objects.create(
            author=self.author,
            title="Different category",
            body="Control post",
            category="wins",
            published_at=timezone.now() - timedelta(minutes=1),
        )

        self._as_guest()
        filtered = self.client.get(
            reverse("community_post_list"),
            {"category": "dating_advice", "sort": "new", "page": 1},
        )
        self.assertEqual(filtered.status_code, 200)
        ids = [item["id"] for item in filtered.data["posts"]]
        self.assertIn(create_response.data["id"], ids)
        self.assertEqual(len(ids), 1)

    def test_list_paginates_posts(self):
        now = timezone.now()
        for i in range(23):
            CommunityPost.objects.create(
                author=self.author,
                title=f"Paginated post {i}",
                body="Pagination body",
                category="help_me_reply",
                published_at=now - timedelta(minutes=i),
            )

        self._as_guest()
        page_1 = self.client.get(reverse("community_post_list"), {"sort": "new", "page": 1})
        page_2 = self.client.get(reverse("community_post_list"), {"sort": "new", "page": 2})

        self.assertEqual(page_1.status_code, 200)
        self.assertEqual(page_2.status_code, 200)
        self.assertNotIn("total", page_1.data)
        self.assertNotIn("total", page_2.data)
        self.assertEqual(len(page_1.data["posts"]), 20)
        self.assertEqual(len(page_2.data["posts"]), 3)
        self.assertTrue(page_1.data["has_more"])
        self.assertFalse(page_2.data["has_more"])

        page_1_ids = {item["id"] for item in page_1.data["posts"]}
        page_2_ids = {item["id"] for item in page_2.data["posts"]}
        self.assertEqual(len(page_1_ids.intersection(page_2_ids)), 0)

    def test_list_sort_top_uses_vote_score(self):
        now = timezone.now()
        high_score = CommunityPost.objects.create(
            author=self.author,
            title="High score",
            body="High score body",
            category="wins",
            published_at=now - timedelta(days=1),
        )
        low_score = CommunityPost.objects.create(
            author=self.author,
            title="Low score",
            body="Low score body",
            category="wins",
            published_at=now,
        )

        PostVote.objects.create(user=self.other_user, post=high_score, vote_type="up")
        PostVote.objects.create(user=self.reporter, post=high_score, vote_type="up")
        PostVote.objects.create(user=self.other_user, post=low_score, vote_type="down")

        self._as_guest()
        response = self.client.get(reverse("community_post_list"), {"sort": "top", "page": 1})
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["posts"]]
        self.assertLess(ids.index(high_score.id), ids.index(low_score.id))

    def test_list_sort_hot_prefers_recent_posts(self):
        now = timezone.now()
        older_high_score = CommunityPost.objects.create(
            author=self.author,
            title="Older high score",
            body="Older high score body",
            category="wins",
            published_at=now - timedelta(days=2),
        )
        recent_low_score = CommunityPost.objects.create(
            author=self.author,
            title="Recent low score",
            body="Recent low score body",
            category="wins",
            published_at=now - timedelta(minutes=5),
        )

        PostVote.objects.create(user=self.other_user, post=older_high_score, vote_type="up")
        PostVote.objects.create(user=self.reporter, post=older_high_score, vote_type="up")

        self._as_guest()
        response = self.client.get(reverse("community_post_list"), {"sort": "hot", "page": 1})
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["posts"]]
        self.assertLess(ids.index(recent_low_score.id), ids.index(older_high_score.id))

    def test_list_without_sort_uses_admin_default_sort(self):
        now = timezone.now()
        older_high_score = CommunityPost.objects.create(
            author=self.author,
            title="Older top-ranked",
            body="Older top-ranked body",
            category="wins",
            published_at=now - timedelta(days=2),
        )
        recent_low_score = CommunityPost.objects.create(
            author=self.author,
            title="Recent low-ranked",
            body="Recent low-ranked body",
            category="wins",
            published_at=now - timedelta(minutes=5),
        )
        PostVote.objects.create(user=self.other_user, post=older_high_score, vote_type="up")
        PostVote.objects.create(user=self.reporter, post=older_high_score, vote_type="up")

        cfg = MobileAppConfig.load()
        cfg.community_default_sort = "top"
        cfg.save(update_fields=["community_default_sort"])

        self._as_guest()
        response = self.client.get(reverse("community_post_list"), {"page": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sort"], "top")

        ids = [item["id"] for item in response.data["posts"]]
        self.assertLess(ids.index(older_high_score.id), ids.index(recent_low_score.id))

    def test_list_explicit_sort_overrides_admin_default(self):
        now = timezone.now()
        older_high_score = CommunityPost.objects.create(
            author=self.author,
            title="Older top candidate",
            body="Older top candidate body",
            category="wins",
            published_at=now - timedelta(days=2),
        )
        recent_low_score = CommunityPost.objects.create(
            author=self.author,
            title="Recent candidate",
            body="Recent candidate body",
            category="wins",
            published_at=now - timedelta(minutes=5),
        )
        PostVote.objects.create(user=self.other_user, post=older_high_score, vote_type="up")
        PostVote.objects.create(user=self.reporter, post=older_high_score, vote_type="up")

        cfg = MobileAppConfig.load()
        cfg.community_default_sort = "top"
        cfg.save(update_fields=["community_default_sort"])

        self._as_guest()
        response = self.client.get(
            reverse("community_post_list"),
            {"sort": "new", "page": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sort"], "new")

        ids = [item["id"] for item in response.data["posts"]]
        self.assertLess(ids.index(recent_low_score.id), ids.index(older_high_score.id))

    def test_block_toggle_and_blocked_users_list(self):
        blocked_post = CommunityPost.objects.create(
            author=self.other_user,
            title="Blocked User Post",
            body="Should be hidden while blocked",
            category="wins",
            published_at=timezone.now() - timedelta(minutes=5),
        )

        self._auth(self.author_token)
        block_resp = self.client.post(
            reverse("community_block_user", args=[self.other_user.id]),
            {},
            format="json",
        )
        self.assertEqual(block_resp.status_code, 200)
        self.assertEqual(block_resp.data["blocked"], True)
        self.assertTrue(
            UserBlock.objects.filter(
                blocker=self.author, blocked_user=self.other_user
            ).exists()
        )

        blocked_list_resp = self.client.get(reverse("community_blocked_users"))
        self.assertEqual(blocked_list_resp.status_code, 200)
        self.assertIn(self.other_user.id, blocked_list_resp.data["blocked_user_ids"])

        filtered_feed = self.client.get(reverse("community_post_list"))
        filtered_ids = [item["id"] for item in filtered_feed.data["posts"]]
        self.assertNotIn(blocked_post.id, filtered_ids)

        unblock_resp = self.client.post(
            reverse("community_block_user", args=[self.other_user.id]),
            {},
            format="json",
        )
        self.assertEqual(unblock_resp.status_code, 200)
        self.assertEqual(unblock_resp.data["blocked"], False)
        self.assertFalse(
            UserBlock.objects.filter(
                blocker=self.author, blocked_user=self.other_user
            ).exists()
        )

        unblocked_list_resp = self.client.get(reverse("community_blocked_users"))
        self.assertEqual(unblocked_list_resp.status_code, 200)
        self.assertNotIn(
            self.other_user.id,
            unblocked_list_resp.data["blocked_user_ids"],
        )

        unfiltered_feed = self.client.get(reverse("community_post_list"))
        unfiltered_ids = [item["id"] for item in unfiltered_feed.data["posts"]]
        self.assertIn(blocked_post.id, unfiltered_ids)

    def test_permissions_for_community_endpoints(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="Permission Post",
            body="Permission body",
            category="help_me_reply",
        )
        comment = post.comments.create(author=self.other_user, body="Permission comment")

        self._as_guest()
        create_post = self.client.post(
            reverse("community_post_list"),
            {
                "title": "Guest Create",
                "body": "Guest body",
                "category": "wins",
            },
            format="json",
        )
        self.assertEqual(create_post.status_code, 401)

        self.assertEqual(
            self.client.post(
                reverse("community_post_vote", args=[post.id]),
                {"vote_type": "up"},
                format="json",
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                reverse("community_post_comment", args=[post.id]),
                {"body": "Guest comment"},
                format="json",
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.delete(
                reverse("community_comment_delete", args=[comment.id])
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                reverse("community_comment_like", args=[comment.id]),
                {},
                format="json",
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                reverse("community_report_post", args=[post.id]),
                {"reason": "spam"},
                format="json",
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                reverse("community_report_comment", args=[comment.id]),
                {"reason": "spam"},
                format="json",
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                reverse("community_block_user", args=[self.other_user.id]),
                {},
                format="json",
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.get(reverse("community_blocked_users")).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                reverse("community_poll_vote", args=[post.id]),
                {"choice": "send_it"},
                format="json",
            ).status_code,
            401,
        )

    def test_comment_detail_uses_author_display_name_when_present(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="Display name post",
            body="Body",
            category="wins",
            published_at=timezone.now() - timedelta(minutes=1),
        )
        comment = post.comments.create(
            author=self.other_user,
            author_display_name="Concierge Alias",
            body="Alias should be shown.",
        )

        self._as_guest()
        response = self.client.get(reverse("community_post_detail", args=[post.id]))

        self.assertEqual(response.status_code, 200)
        payload_comment = next(
            item for item in response.data["comments"] if item["id"] == comment.id
        )
        self.assertEqual(payload_comment["author"]["username"], "Concierge Alias")

    def test_comment_detail_falls_back_to_username_without_display_name(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="Fallback name post",
            body="Body",
            category="wins",
            published_at=timezone.now() - timedelta(minutes=1),
        )
        comment = post.comments.create(
            author=self.other_user,
            body="Fallback should use username.",
        )

        self._as_guest()
        response = self.client.get(reverse("community_post_detail", args=[post.id]))

        self.assertEqual(response.status_code, 200)
        payload_comment = next(
            item for item in response.data["comments"] if item["id"] == comment.id
        )
        self.assertEqual(
            payload_comment["author"]["username"],
            self.other_user.username,
        )

    def test_post_detail_include_comments_zero_skips_comment_hydration(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="No comments hydration",
            body="Body",
            category="wins",
            published_at=timezone.now() - timedelta(minutes=1),
        )
        CommunityComment.objects.create(post=post, author=self.other_user, body="c1")
        CommunityComment.objects.create(post=post, author=self.reporter, body="c2")

        self._as_guest()
        response = self.client.get(
            reverse("community_post_detail", args=[post.id]),
            {"include_comments": "0"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], post.id)
        self.assertEqual(response.data["comment_count"], 2)
        self.assertEqual(response.data["comments"], [])

    def test_get_comments_endpoint_paginates(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="Comment pagination",
            body="Body",
            category="wins",
            published_at=timezone.now() - timedelta(minutes=1),
        )
        for i in range(23):
            CommunityComment.objects.create(
                post=post,
                author=self.other_user,
                body=f"Comment {i}",
            )

        self._as_guest()
        page_1 = self.client.get(reverse("community_post_comment", args=[post.id]), {"page": 1})
        page_2 = self.client.get(reverse("community_post_comment", args=[post.id]), {"page": 2})

        self.assertEqual(page_1.status_code, 200)
        self.assertEqual(page_2.status_code, 200)
        self.assertEqual(page_1.data["page"], 1)
        self.assertEqual(page_2.data["page"], 2)
        self.assertTrue(page_1.data["has_more"])
        self.assertFalse(page_2.data["has_more"])
        self.assertEqual(len(page_1.data["comments"]), 20)
        self.assertEqual(len(page_2.data["comments"]), 3)
        page_1_ids = {item["id"] for item in page_1.data["comments"]}
        page_2_ids = {item["id"] for item in page_2.data["comments"]}
        self.assertEqual(len(page_1_ids.intersection(page_2_ids)), 0)

    def test_create_vote_comment_poll_report_and_delete_flow(self):
        self._auth(self.author_token)
        create_resp = self.client.post(
            reverse("community_post_list"),
            {
                "title": "End-to-end Community Flow",
                "body": "Main flow body",
                "category": "rate_my_profile",
                "has_poll": True,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201)
        post_id = create_resp.data["id"]
        self.assertIsNotNone(create_resp.data.get("poll"))

        self._auth(self.other_token)
        vote_up = self.client.post(
            reverse("community_post_vote", args=[post_id]),
            {"vote_type": "up"},
            format="json",
        )
        self.assertEqual(vote_up.status_code, 200)
        self.assertEqual(vote_up.data["user_vote"], "up")
        self.assertEqual(vote_up.data["vote_score"], 1)

        vote_clear = self.client.post(
            reverse("community_post_vote", args=[post_id]),
            {"vote_type": "up"},
            format="json",
        )
        self.assertEqual(vote_clear.status_code, 200)
        self.assertEqual(vote_clear.data["user_vote"], None)
        self.assertEqual(vote_clear.data["vote_score"], 0)

        vote_down = self.client.post(
            reverse("community_post_vote", args=[post_id]),
            {"vote_type": "down"},
            format="json",
        )
        self.assertEqual(vote_down.status_code, 200)
        self.assertEqual(vote_down.data["user_vote"], "down")
        self.assertEqual(vote_down.data["vote_score"], -1)

        poll_send_it = self.client.post(
            reverse("community_poll_vote", args=[post_id]),
            {"choice": "send_it"},
            format="json",
        )
        self.assertEqual(poll_send_it.status_code, 200)
        self.assertEqual(poll_send_it.data["send_it_count"], 1)
        self.assertEqual(poll_send_it.data["user_vote"], "send_it")

        poll_clear = self.client.post(
            reverse("community_poll_vote", args=[post_id]),
            {"choice": "send_it"},
            format="json",
        )
        self.assertEqual(poll_clear.status_code, 200)
        self.assertEqual(poll_clear.data["send_it_count"], 0)
        self.assertEqual(poll_clear.data["user_vote"], None)

        comment_resp = self.client.post(
            reverse("community_post_comment", args=[post_id]),
            {"body": "Useful feedback from another user."},
            format="json",
        )
        self.assertEqual(comment_resp.status_code, 201)
        comment_id = comment_resp.data["id"]

        self._auth(self.author_token)
        like_resp = self.client.post(
            reverse("community_comment_like", args=[comment_id]),
            {},
            format="json",
        )
        self.assertEqual(like_resp.status_code, 200)
        self.assertEqual(like_resp.data["liked"], True)
        self.assertEqual(like_resp.data["like_count"], 1)

        unlike_resp = self.client.post(
            reverse("community_comment_like", args=[comment_id]),
            {},
            format="json",
        )
        self.assertEqual(unlike_resp.status_code, 200)
        self.assertEqual(unlike_resp.data["liked"], False)
        self.assertEqual(unlike_resp.data["like_count"], 0)

        non_owner_delete = self.client.delete(
            reverse("community_comment_delete", args=[comment_id])
        )
        self.assertEqual(non_owner_delete.status_code, 403)

        self._auth(self.reporter_token)
        report_post = self.client.post(
            reverse("community_report_post", args=[post_id]),
            {"reason": "spam", "detail": "Looks spammy"},
            format="json",
        )
        self.assertEqual(report_post.status_code, 201)

        report_post_duplicate = self.client.post(
            reverse("community_report_post", args=[post_id]),
            {"reason": "spam", "detail": "Duplicate report"},
            format="json",
        )
        self.assertEqual(report_post_duplicate.status_code, 409)

        report_comment = self.client.post(
            reverse("community_report_comment", args=[comment_id]),
            {"reason": "harassment", "detail": "Hostile language"},
            format="json",
        )
        self.assertEqual(report_comment.status_code, 201)

        report_comment_duplicate = self.client.post(
            reverse("community_report_comment", args=[comment_id]),
            {"reason": "harassment", "detail": "Duplicate comment report"},
            format="json",
        )
        self.assertEqual(report_comment_duplicate.status_code, 409)

        self._auth(self.author_token)
        own_report_post = self.client.post(
            reverse("community_report_post", args=[post_id]),
            {"reason": "spam"},
            format="json",
        )
        self.assertEqual(own_report_post.status_code, 400)

        self._auth(self.other_token)
        own_report_comment = self.client.post(
            reverse("community_report_comment", args=[comment_id]),
            {"reason": "spam"},
            format="json",
        )
        self.assertEqual(own_report_comment.status_code, 400)

        owner_delete_comment = self.client.delete(
            reverse("community_comment_delete", args=[comment_id])
        )
        self.assertEqual(owner_delete_comment.status_code, 200)

        delete_post_non_owner = self.client.delete(
            reverse("community_post_detail", args=[post_id])
        )
        self.assertEqual(delete_post_non_owner.status_code, 403)

        self._auth(self.author_token)
        delete_post_owner = self.client.delete(
            reverse("community_post_detail", args=[post_id])
        )
        self.assertEqual(delete_post_owner.status_code, 200)

        self._as_guest()
        deleted_post_detail = self.client.get(
            reverse("community_post_detail", args=[post_id])
        )
        self.assertEqual(deleted_post_detail.status_code, 404)

    def test_feed_query_budget_stays_constant_with_polls(self):
        now = timezone.now()
        for i in range(25):
            post = CommunityPost.objects.create(
                author=self.author,
                title=f"Perf post {i}",
                body="Body",
                category="wins",
                published_at=now - timedelta(minutes=i),
            )
            if i % 2 == 0:
                poll = PostPoll.objects.create(post=post)
                PollVote.objects.create(
                    poll=poll,
                    user=self.other_user if i % 4 == 0 else self.reporter,
                    choice="send_it" if i % 4 == 0 else "dont_send_it",
                )
            if i % 3 == 0:
                CommunityComment.objects.create(
                    post=post,
                    author=self.other_user,
                    body="Comment",
                )

        self._as_guest()
        with CaptureQueriesContext(connection) as query_ctx:
            response = self.client.get(
                reverse("community_post_list"),
                {"sort": "hot", "page": 1},
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(query_ctx),
            8,
            msg=f"Expected <=8 queries for feed page 1, got {len(query_ctx)}",
        )

    def test_detail_query_budget_stays_constant_with_many_comments(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="Perf detail post",
            body="Body",
            category="wins",
            published_at=timezone.now() - timedelta(minutes=1),
        )
        poll = PostPoll.objects.create(post=post)
        PollVote.objects.create(poll=poll, user=self.other_user, choice="send_it")
        PollVote.objects.create(poll=poll, user=self.reporter, choice="dont_send_it")
        for i in range(30):
            CommunityComment.objects.create(
                post=post,
                author=self.other_user if i % 2 == 0 else self.reporter,
                body=f"Comment {i}",
            )

        self._as_guest()
        with CaptureQueriesContext(connection) as query_ctx:
            response = self.client.get(reverse("community_post_detail", args=[post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["comments"]), 30)
        self.assertLessEqual(
            len(query_ctx),
            8,
            msg=f"Expected <=8 queries for detail with comments, got {len(query_ctx)}",
        )

    def test_comment_create_triggers_notification_with_expected_payload_inputs(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="Notify me",
            body="Body",
            category="wins",
        )
        self._auth(self.other_token)

        with patch("mobileapi.community_views.send_post_comment_notification") as send_mock:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("community_post_comment", args=[post.id]),
                    {"body": "New comment from another user."},
                    format="json",
                )

        self.assertEqual(response.status_code, 201)
        send_mock.assert_called_once()
        kwargs = send_mock.call_args.kwargs
        self.assertEqual(kwargs["post_author_id"], self.author.id)
        self.assertEqual(kwargs["comment_author_id"], self.other_user.id)
        self.assertEqual(kwargs["post_id"], post.id)
        self.assertEqual(kwargs["comment_id"], response.data["id"])

    @override_settings(
        ONESIGNAL_APP_ID="test-app-id",
        ONESIGNAL_REST_API_KEY="test-rest-key",
        ONESIGNAL_COMMENT_NOTIFICATIONS_ENABLED=True,
    )
    def test_sender_skips_self_comment(self):
        with patch("mobileapi.push_notifications.requests.post") as post_mock:
            sent = send_post_comment_notification(
                post_author_id=self.author.id,
                comment_author_id=self.author.id,
                post_id=123,
                comment_id=456,
            )

        self.assertFalse(sent)
        post_mock.assert_not_called()

    @override_settings(
        ONESIGNAL_APP_ID="test-app-id",
        ONESIGNAL_REST_API_KEY="test-rest-key",
        ONESIGNAL_COMMENT_NOTIFICATIONS_ENABLED=True,
    )
    def test_sender_skips_when_users_are_blocked(self):
        UserBlock.objects.create(blocker=self.author, blocked_user=self.other_user)

        with patch("mobileapi.push_notifications.requests.post") as post_mock:
            sent = send_post_comment_notification(
                post_author_id=self.author.id,
                comment_author_id=self.other_user.id,
                post_id=100,
                comment_id=200,
            )

        self.assertFalse(sent)
        post_mock.assert_not_called()

    @override_settings(
        ONESIGNAL_APP_ID="test-app-id",
        ONESIGNAL_REST_API_KEY="test-rest-key",
        ONESIGNAL_COMMENT_NOTIFICATIONS_ENABLED=True,
    )
    def test_sender_payload_uses_external_id_and_action_data(self):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.text = ""

        with patch(
            "mobileapi.push_notifications.requests.post",
            return_value=response_mock,
        ) as post_mock:
            sent = send_post_comment_notification(
                post_author_id=self.author.id,
                comment_author_id=self.other_user.id,
                post_id=77,
                comment_id=88,
            )

        self.assertTrue(sent)
        post_mock.assert_called_once()
        kwargs = post_mock.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Key test-rest-key")
        self.assertEqual(kwargs["json"]["app_id"], "test-app-id")
        self.assertEqual(kwargs["json"]["target_channel"], "push")
        self.assertEqual(
            kwargs["json"]["include_aliases"]["external_id"],
            [str(self.author.id)],
        )
        self.assertEqual(
            kwargs["json"]["headings"],
            {"en": "Ooh, good answer... \U0001F440"},
        )
        self.assertEqual(
            kwargs["json"]["contents"],
            {
                "en": "The community is cooking. Tap to see the latest reply to your post!",
            },
        )
        self.assertEqual(
            kwargs["json"]["data"],
            {
                "action": "community_comment",
                "post_id": 77,
                "comment_id": 88,
            },
        )

    @override_settings(
        ONESIGNAL_APP_ID="test-app-id",
        ONESIGNAL_REST_API_KEY="test-rest-key",
        ONESIGNAL_COMMENT_NOTIFICATIONS_ENABLED=True,
    )
    def test_comment_create_succeeds_when_onesignal_request_fails(self):
        post = CommunityPost.objects.create(
            author=self.author,
            title="Resilient",
            body="Body",
            category="wins",
        )
        self._auth(self.other_token)

        with patch(
            "mobileapi.push_notifications.requests.post",
            side_effect=requests.RequestException("network down"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("community_post_comment", args=[post.id]),
                    {"body": "Still should succeed."},
                    format="json",
                )

        self.assertEqual(response.status_code, 201)


class MobileInstallAttributionEventTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.click_id = "123e4567-e89b-12d3-a456-426614174000"
        self.click_event = MarketingClickEvent.objects.create(
            route_key="flirtfix",
            click_id=self.click_id,
            utm_source="instagram",
            utm_medium="bio",
            utm_campaign="launch_campaign",
            target_url="https://play.google.com/store/apps/details?id=com.tryagaintext.flirtfix",
            raw_query={"utm_source": ["instagram"]},
        )

    def test_install_attribution_links_to_click_event(self):
        payload = {
            "install_referrer_raw": (
                "utm_source=instagram&utm_medium=bio&utm_campaign=launch_campaign"
                f"&ffclid={self.click_id}"
            ),
            "install_begin_timestamp_seconds": 1700000000,
            "referrer_click_timestamp_seconds": 1699999900,
            "app_version": "1.2.3",
        }
        response = self.client.post(
            reverse("mobile_install_attribution"),
            payload,
            format="json",
            REMOTE_ADDR="203.0.113.110",
            HTTP_X_DEVICE_FINGERPRINT="install-device-1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data.get("attributed_click_id"), self.click_id)
        self.assertFalse(response.data.get("is_organic"))
        self.assertEqual(MobileInstallAttributionEvent.objects.count(), 1)

        event = MobileInstallAttributionEvent.objects.get()
        self.assertEqual(event.click_event_id, self.click_event.id)
        self.assertEqual(str(event.ffclid), self.click_id)
        self.assertEqual(event.utm_source, "instagram")
        self.assertEqual(event.utm_medium, "bio")
        self.assertEqual(event.utm_campaign, "launch_campaign")
        self.assertEqual(event.app_version, "1.2.3")
        self.assertIsNotNone(event.install_begin_at)
        self.assertIsNotNone(event.referrer_click_at)

    def test_install_attribution_is_idempotent_for_same_guest_payload(self):
        payload = {
            "install_referrer_raw": "utm_source=reddit&utm_medium=post&utm_campaign=winter_push",
            "install_begin_timestamp_seconds": 1700000000,
        }
        for _ in range(2):
            response = self.client.post(
                reverse("mobile_install_attribution"),
                payload,
                format="json",
                REMOTE_ADDR="203.0.113.111",
                HTTP_X_DEVICE_FINGERPRINT="install-device-idempotent",
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data.get("success"))

        self.assertEqual(MobileInstallAttributionEvent.objects.count(), 1)

    def test_install_attribution_supports_organic_payload(self):
        response = self.client.post(
            reverse("mobile_install_attribution"),
            {"install_referrer_raw": ""},
            format="json",
            REMOTE_ADDR="203.0.113.112",
            HTTP_X_DEVICE_FINGERPRINT="install-device-organic",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get("success"))
        self.assertTrue(response.data.get("is_organic"))

        event = MobileInstallAttributionEvent.objects.get()
        self.assertTrue(event.is_organic)
        self.assertIsNone(event.ffclid)
        self.assertIsNone(event.click_event)

    def test_install_attribution_supports_authenticated_users(self):
        user = User.objects.create_user(
            username="installauthuser",
            email="installauth@example.com",
            password="StrongPass123!",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(
            reverse("mobile_install_attribution"),
            {
                "install_referrer_raw": (
                    "utm_source=instagram&utm_medium=bio&utm_campaign=launch_campaign"
                    f"&ffclid={self.click_id}"
                ),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        event = MobileInstallAttributionEvent.objects.get()
        self.assertEqual(event.user_id, user.id)
        self.assertIsNone(event.guest_id_hash)


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


class MobileReplyThreadApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="archiver",
            email="archiver@example.com",
            password="StrongPass123!",
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def _create_thread(self, suffix: int) -> MobileReplyThread:
        return MobileReplyThread.objects.create(
            user=self.user,
            title=f"Thread {suffix}",
            stitched_transcript=f"line {suffix}",
            latest_replies=[{"message": f"reply {suffix}"}],
        )

    def test_list_marks_only_newest_three_as_unlocked_for_free_users(self):
        for i in range(5):
            self._create_thread(i)

        response = self.client.get(reverse("mobile_reply_threads"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        threads = response.data["threads"]
        self.assertEqual(len(threads), 5)
        self.assertEqual([item["is_locked"] for item in threads], [False, False, False, True, True])
        self.assertEqual(response.data["free_unlocked_count"], 3)

    def test_locked_thread_detail_requires_subscription_for_free_user(self):
        created = [self._create_thread(i) for i in range(4)]
        oldest = created[0]

        response = self.client.get(reverse("mobile_reply_thread_detail", args=[oldest.id]))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"], "subscription_required")
        self.assertTrue(response.data["is_locked"])

    def test_locked_thread_detail_allowed_for_subscribed_user(self):
        created = [self._create_thread(i) for i in range(4)]
        oldest = created[0]

        chat_credit = self.user.chat_credit
        chat_credit.is_subscribed = True
        chat_credit.subscription_expiry = timezone.now() + timedelta(days=7)
        chat_credit.save(update_fields=["is_subscribed", "subscription_expiry"])

        response = self.client.get(reverse("mobile_reply_thread_detail", args=[oldest.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["thread"]["id"], oldest.id)
        self.assertFalse(response.data["thread"]["is_locked"])

    def test_create_and_update_thread_stitches_latest_ocr_and_replaces_latest_replies(self):
        generation_event = MobileGenerationEvent.objects.create(
            user=self.user,
            user_type=MobileGenerationEvent.UserType.AUTHENTICATED_NON_SUBSCRIBED,
            action_type=MobileGenerationEvent.ActionType.REPLY,
            source_type=MobileGenerationEvent.SourceType.AI,
            model_used="gemini-3-flash-preview",
            thinking_used="low",
            generated_json='[{"message":"hello"}]',
        )

        create_response = self.client.post(
            reverse("mobile_reply_threads"),
            {
                "conversation_text": "hi there",
                "latest_ocr_text": "you: hey\nher: hello",
                "latest_replies": [
                    {"message": "reply one", "confidence_score": 0.91},
                    {"message": "reply two", "confidence_score": 0.88},
                    {"message": "reply three", "confidence_score": 0.84},
                ],
                "generation_event_id": generation_event.id,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(create_response.data["success"])
        thread_id = create_response.data["thread"]["id"]

        update_response = self.client.post(
            reverse("mobile_reply_threads"),
            {
                "thread_id": thread_id,
                "latest_ocr_text": "her: hello\nyou: what are you up to?",
                "latest_replies": [
                    {"message": "updated one"},
                    {"message": "updated two"},
                    {"message": "updated three"},
                ],
            },
            format="json",
        )

        self.assertEqual(update_response.status_code, 200)
        thread = MobileReplyThread.objects.get(id=thread_id)
        self.assertEqual(
            thread.stitched_transcript,
            "you: hey\nher: hello\nyou: what are you up to?",
        )
        self.assertEqual(
            [item["message"] for item in thread.latest_replies],
            ["updated one", "updated two", "updated three"],
        )

    def test_delete_thread_removes_resource(self):
        thread = self._create_thread(1)

        delete_response = self.client.delete(
            reverse("mobile_reply_thread_detail", args=[thread.id])
        )

        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(MobileReplyThread.objects.filter(id=thread.id).exists())
