from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from mobileapi import views


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
