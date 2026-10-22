from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from conversation.models import ChatCredit, LockedReply, RecommendedOpener
from mobileapi.views import _has_mobile_access, _is_subscription_active, _subscription_payload
from mobileapi.models import MobileGenerationEvent


@override_settings(
    MOBILE_RATELIMIT_GENERATE_IP="100/m", MOBILE_RATELIMIT_GENERATE_DEVICE="100/m",
    MOBILE_RATELIMIT_GENERATE_OPENERS_IP="100/m", MOBILE_RATELIMIT_GENERATE_OPENERS_DEVICE="100/m",
)
class ComplimentaryMobileAccessTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("invited-tester", email="Invited.Tester@example.com")
        self.credit = self.user.chat_credit
        self.credit.balance = 0
        self.credit.total_used = 3
        self.credit.free_daily_credits_used = 3
        self.credit.free_daily_reset_at = timezone.now()
        self.credit.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.generated = ('[{"message":"How about coffee?"}]', True, {
            "model_used": "test-model", "thinking_used": "low", "source_type": "ai", "usage": {},
        })

    def grant(self, expiry=None):
        self.credit.mobile_full_access = True
        self.credit.mobile_access_expires_at = expiry
        self.credit.save(update_fields=["mobile_full_access", "mobile_access_expires_at"])

    def test_default_has_no_grant_and_does_not_change_web_credits(self):
        self.assertFalse(self.credit.has_mobile_full_access)
        self.assertFalse(_has_mobile_access(self.credit))
        self.grant()
        self.assertFalse(self.credit.use_credit())
        self.assertEqual(self.credit.balance, 0)

    def test_profile_exposes_access_separately_from_paid_subscription(self):
        expiry = timezone.now() + timedelta(days=7)
        self.grant(expiry)
        response = self.client.get(reverse("mobile_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["has_mobile_access"])
        self.assertTrue(response.data["mobile_access_granted"])
        self.assertFalse(response.data["is_subscribed"])
        self.assertEqual(response.data["mobile_access_expires_at"], expiry.isoformat())
        self.assertIsNone(response.data["subscription_product_id"])
        self.assertFalse(response.data["subscription_auto_renewing"])

    def test_grant_unlocks_assistant_replies_without_consuming_free_credits(self):
        self.grant()
        with patch("mobileapi.views.generate_mobile_response", return_value=self.generated), \
             patch("mobileapi.views._check_free_credit_allowance", return_value=(False, 0)) as free_gate, \
             patch("mobileapi.views._consume_free_credit_allowance") as consume:
            response = self.client.post(reverse("generate_text_with_credits"), {
                "last_text": "You: Coffee?\nThem: Sounds good.", "situation": "stuck_after_reply",
                "input_source": "accessibility",
            }, format="json", HTTP_X_DEVICE_FINGERPRINT="grant-reply-test")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertFalse(response.data.get("is_locked", False))
        self.assertTrue(response.data["mobile_access_granted"])
        free_gate.assert_not_called()
        consume.assert_not_called()
        event = MobileGenerationEvent.objects.get(pk=response.data["generation_event_id"])
        self.assertEqual(event.user_type, MobileGenerationEvent.UserType.AUTHENTICATED_NON_SUBSCRIBED)
        self.assertTrue(event.metadata["mobile_access_granted"])
        self.credit.refresh_from_db()
        self.assertEqual(self.credit.free_daily_credits_used, 3)
        self.assertEqual(self.credit.subscriber_daily_replies, 1)
        self.assertFalse(self.credit.is_subscribed)

    def test_grant_unlocks_profile_image_openers_with_exhausted_free_allowance(self):
        self.grant()
        image = SimpleUploadedFile("fictional-profile.png", b"fictional-test-image", content_type="image/png")
        with patch("mobileapi.views.generate_mobile_openers_from_image", return_value=self.generated) as generate, \
             patch("mobileapi.views._check_free_credit_allowance", return_value=(False, 0)) as free_gate:
            response = self.client.post(reverse("generate_openers_from_image"), {"profile_image": image},
                format="multipart", HTTP_X_DEVICE_FINGERPRINT="grant-opener-test")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["mobile_access_granted"])
        self.assertFalse(response.data.get("is_locked", False))
        generate.assert_called_once()
        free_gate.assert_not_called()
        self.credit.refresh_from_db()
        self.assertEqual(self.credit.subscriber_daily_openers, 1)
        self.assertEqual(self.credit.free_daily_credits_used, 3)

    def test_grant_unlocks_locked_replies_and_the_full_opener_vault(self):
        self.grant()
        locked = LockedReply.objects.create(user=self.user, reply_json='[{"message":"Hello"}]', preview=["Hello"], reply_type="reply")
        response = self.client.post(reverse("unlock_reply"), {"locked_reply_id": locked.pk}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_locked"])
        locked.refresh_from_db()
        self.assertTrue(locked.unlocked)
        for i in range(5):
            RecommendedOpener.objects.create(text=f"Opener {i}", why_it_works="Fictional test", is_active=True)
        response = self.client.post(reverse("recommended_openers"), {"mode": "vault"}, format="json",
            HTTP_X_DEVICE_FINGERPRINT="grant-vault-test")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["openers"])
        self.assertTrue(all(not item["is_locked"] for item in response.data["openers"]))

    def test_expired_and_revoked_grants_immediately_lose_access(self):
        self.grant(timezone.now() - timedelta(seconds=1))
        self.assertFalse(_has_mobile_access(self.credit))
        self.assertFalse(_subscription_payload(self.credit)["mobile_access_granted"])
        self.grant(timezone.now() + timedelta(days=1))
        self.assertTrue(_has_mobile_access(self.credit))
        self.credit.mobile_full_access = False
        self.credit.save(update_fields=["mobile_full_access"])
        response = self.client.get(reverse("mobile_profile"))
        self.assertFalse(response.data["has_mobile_access"])
        self.assertFalse(response.data["mobile_access_granted"])
        locked = LockedReply.objects.create(user=self.user, reply_json="[]", preview=[], reply_type="reply")
        response = self.client.post(reverse("unlock_reply"), {"locked_reply_id": locked.pk}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_revoking_a_grant_preserves_an_existing_paid_purchase(self):
        self.grant()
        self.credit.is_subscribed = True
        self.credit.subscription_product_id = "paid-product"
        self.credit.subscription_purchase_token = "fictional-purchase-token"
        self.credit.subscription_expiry = timezone.now() + timedelta(days=30)
        self.credit.mobile_full_access = False
        self.credit.save()
        self.assertTrue(_has_mobile_access(self.credit))
        self.assertTrue(_is_subscription_active(self.credit))
        payload = _subscription_payload(self.credit)
        self.assertTrue(payload["is_subscribed"])
        self.assertFalse(payload["mobile_access_granted"])
        self.credit.refresh_from_db()
        self.assertEqual(self.credit.subscription_purchase_token, "fictional-purchase-token")

    def test_clients_cannot_grant_themselves_access(self):
        with patch("mobileapi.views.generate_mobile_response", return_value=self.generated), \
             patch("mobileapi.views._check_free_credit_allowance", return_value=(False, 0)):
            response = self.client.post(reverse("generate_text_with_credits"), {
                "last_text": "Hello", "situation": "stuck_after_reply", "mobile_full_access": True, "mobile_access_granted": True,
            }, format="json", HTTP_X_DEVICE_FINGERPRINT="forged-grant-test")
        self.assertTrue(response.data["is_locked"])
        self.credit.refresh_from_db()
        self.assertFalse(self.credit.mobile_full_access)

    def test_admin_can_find_an_account_by_email_and_unprivileged_staff_cannot_edit_it(self):
        browser = Client()
        root = User.objects.create_superuser("grant-admin", email="admin@example.com", password="TestPassword1!")
        browser.force_login(root)
        response = browser.get(reverse("admin:conversation_chatcredit_changelist"), {"q": "invited.tester@EXAMPLE.com"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invited.Tester@example.com")
        response = browser.get(reverse("admin:conversation_chatcredit_change", args=[self.credit.pk]))
        self.assertContains(response, 'name="mobile_full_access"')
        self.assertContains(response, 'name="mobile_access_expires_at_0"')
        staff = User.objects.create_user("limited-staff", is_staff=True)
        browser.force_login(staff)
        response = browser.post(reverse("admin:conversation_chatcredit_change", args=[self.credit.pk]),
            {"mobile_full_access": "on"})
        self.assertEqual(response.status_code, 403)
        self.credit.refresh_from_db()
        self.assertFalse(self.credit.mobile_full_access)
