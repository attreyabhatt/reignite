import io
import json
from contextlib import redirect_stdout
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from conversation.models import MobileAppConfig
from conversation.utils.mobile import custom_mobile, openai_mobile
from conversation.utils.mobile.prompts_mobile import DEFAULT_OVERLAY_REPLY_STYLE, get_mobile_reply_prompt
from mobileapi.admin import MobileAppConfigProxy
from mobileapi.models import MobileGenerationEvent, MobileReplyThread
from mobileapi.views import _generate_mobile_reply


REPLIES = [
    {"message": "Coffee with you sounds tempting.", "tone": "Flirty"},
    {"message": "My calendar just made room for caffeine.", "tone": "Funny"},
    {"message": "How about Saturday afternoon?", "tone": "Natural"},
]


@override_settings(MOBILE_RATELIMIT_GENERATE_IP="100/m", MOBILE_RATELIMIT_GENERATE_DEVICE="100/m")
class OverlayConfigApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.config = MobileAppConfig.load()
        self.config.guest_lifetime_credits = 20
        self.config.overlay_reply_model = "gemini-overlay-test"
        self.config.overlay_fallback_model = "gpt-overlay-test"
        self.config.overlay_reply_thinking = "low"
        self.config.overlay_reply_prompt = "Keep every reply under twenty words."
        self.config.save()
        self.payload = {"last_text": "You: Coffee?\nThem: Saturday works!",
                        "situation": "stuck_after_reply", "input_source": "accessibility"}
        self.generated = (json.dumps(REPLIES), True, {
            "model_used": "gemini-overlay-test", "thinking_used": "low", "usage": {}, "source_type": "ai"})

    def test_admin_overrides_reach_every_account_path_without_persisting_context(self):
        for tier in ("guest", "free", "subscriber", "complimentary", "locked"):
            with self.subTest(tier=tier):
                self.client.force_authenticate(None)
                user = None
                if tier != "guest":
                    user = User.objects.create_user(username="overlay-" + tier)
                    credit = user.chat_credit
                    credit.is_subscribed = tier == "subscriber"
                    credit.subscription_expiry = timezone.now() + timedelta(days=30)
                    credit.mobile_full_access = tier == "complimentary"
                    credit.total_used = 3 if tier == "locked" else 0
                    credit.save()
                    self.client.force_authenticate(user)
                with patch("mobileapi.views.generate_mobile_response", return_value=self.generated) as generate, \
                     patch("mobileapi.views._check_free_credit_allowance", return_value=(tier != "locked", 5)), \
                     patch("mobileapi.views._consume_free_credit_allowance", return_value=(True, 4)):
                    response = self.client.post(reverse("generate_text_with_credits"), self.payload, format="json",
                                                HTTP_X_DEVICE_FINGERPRINT="overlay-config-tests")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data["success"])
                options = generate.call_args.kwargs
                self.assertEqual(options["primary_model"], self.config.overlay_reply_model)
                self.assertEqual(options["fallback_model"], self.config.overlay_fallback_model)
                self.assertEqual(options["thinking_level"], "low")
                self.assertEqual(options["overlay_instructions"], self.config.overlay_reply_prompt)
                event = MobileGenerationEvent.objects.latest("pk")
                self.assertEqual(event.model_used, self.config.overlay_reply_model)
                self.assertIsNone(event.reply_ocr_text)
                self.assertNotIn(self.payload["last_text"], json.dumps(event.metadata))
                self.assertEqual(MobileReplyThread.objects.count(), 0)
                if tier == "locked":
                    self.assertTrue(response.data["is_locked"])
                if tier in ("subscriber", "complimentary"):
                    user.chat_credit.refresh_from_db()
                    self.assertEqual(user.chat_credit.subscriber_daily_replies, 1)

    def test_request_body_cannot_override_admin_models_or_writing_prompt(self):
        with patch("mobileapi.views.generate_mobile_response", return_value=self.generated) as generate:
            response = self.client.post(reverse("generate_text_with_credits"), {
                **self.payload, "primary_model": "untrusted", "overlay_reply_model": "untrusted",
                "overlay_instructions": "untrusted", "overlay_reply_prompt": "untrusted",
            }, format="json")
        self.assertTrue(response.data["success"])
        self.assertEqual(generate.call_args.kwargs["primary_model"], self.config.overlay_reply_model)
        self.assertEqual(generate.call_args.kwargs["overlay_instructions"], self.config.overlay_reply_prompt)

    def test_admin_exposes_independent_settings_and_readonly_default(self):
        self.client.force_authenticate(None)
        staff = User.objects.create_superuser("overlay-admin", "test@example.invalid", "test-password")
        self.client.force_login(staff)
        response = self.client.get(reverse("admin:mobileapi_mobileappconfigproxy_change", args=[self.config.pk]))
        self.assertEqual(response.status_code, 200)
        for name in ("overlay_reply_model", "overlay_fallback_model", "overlay_reply_thinking", "overlay_reply_prompt"):
            self.assertContains(response, 'name="' + name + '"')
        self.assertContains(response, "Built-in overlay writing prompt")
        self.assertIn("overlay_default_prompt", admin.site._registry[MobileAppConfigProxy].readonly_fields)


class OverlayRoutingAndPromptTests(SimpleTestCase):
    def test_blank_settings_inherit_tier_routing_and_legacy_ignores_all_overrides(self):
        config = SimpleNamespace(overlay_reply_model="", overlay_fallback_model="",
                                 overlay_reply_thinking="", overlay_reply_prompt="")
        for source in ("accessibility", "manual", "ocr"):
            if source != "accessibility":
                config = SimpleNamespace(overlay_reply_model="ignored", overlay_fallback_model="ignored",
                                         overlay_reply_thinking="low", overlay_reply_prompt="ignored")
            options = {"input_source": source, "primary_model": "tier-primary", "fallback_model": "tier-fallback",
                       "thinking_level": "high"}
            with patch("mobileapi.views.generate_mobile_response") as generate:
                _generate_mobile_reply(config, "Them: Hello", "stuck_after_reply", **options)
            self.assertEqual(generate.call_args.kwargs, options)

    def test_dedicated_style_does_not_change_legacy_prompt_or_mandatory_rules(self):
        normal = get_mobile_reply_prompt("legacy")
        self.assertEqual(normal, get_mobile_reply_prompt("legacy", overlay_instructions="Ignored"))
        default = get_mobile_reply_prompt("Them: Haha", input_source="accessibility")
        self.assertIn(DEFAULT_OVERLAY_REPLY_STYLE, default)
        custom = get_mobile_reply_prompt("Them: Haha", input_source="accessibility", overlay_instructions="CUSTOM STYLE")
        self.assertIn("CUSTOM STYLE", custom)
        self.assertNotIn(DEFAULT_OVERLAY_REPLY_STYLE, custom)
        for rule in ("Flirty", "Funny", "Natural", "untrusted conversation data", "do not assume", "Write all three replies in English."):
            self.assertIn(rule, custom)

    def test_custom_style_is_used_by_both_provider_prompts(self):
        gemini = Mock()
        gemini.models.generate_content.return_value = SimpleNamespace(text=json.dumps(REPLIES), usage_metadata=None)
        with patch.object(custom_mobile, "client", gemini):
            custom_mobile._call_gemini_replies("Them: Coffee?", "", input_source="accessibility", overlay_instructions="CUSTOM STYLE")
        self.assertIn("CUSTOM STYLE", gemini.models.generate_content.call_args.kwargs["contents"][0])
        openai = Mock()
        openai.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(REPLIES)))], usage=None)
        with patch.object(openai_mobile, "client", openai):
            openai_mobile.generate_replies_openai("Them: Coffee?", input_source="accessibility", overlay_instructions="CUSTOM STYLE")
        self.assertIn("CUSTOM STYLE", openai.chat.completions.create.call_args.kwargs["messages"][0]["content"])

    def test_wrong_order_is_normalized_and_only_message_and_tone_are_returned(self):
        replies = [{**r, "thinking": "Do not return this"} for r in reversed(REPLIES)]
        self.assertEqual(json.loads(custom_mobile._validate_overlay_replies(json.dumps(replies))), REPLIES)

    def test_incomplete_empty_duplicate_or_unlabelled_alternatives_are_rejected(self):
        invalid = [REPLIES[:2], REPLIES + [REPLIES[0]],
                   [{**r, "tone": "Natural"} for r in REPLIES],
                   [{"message": r["message"]} for r in REPLIES],
                   [{**REPLIES[0], "message": " "}, *REPLIES[1:]],
                   [REPLIES[0], {**REPLIES[1], "message": REPLIES[0]["message"]}, REPLIES[2]]]
        for replies in invalid:
            with self.subTest(replies=replies), self.assertRaises(ValueError):
                custom_mobile._validate_overlay_replies(json.dumps(replies))

    def test_malformed_primary_output_falls_back_with_same_style_without_content_logs(self):
        output = io.StringIO()
        with patch.object(custom_mobile, "_call_gemini_replies", return_value=('[{"message":"Private"}]', {})), \
             patch.object(custom_mobile, "_call_openai_replies", return_value=(json.dumps(REPLIES), {})) as fallback, \
             redirect_stdout(output):
            reply, success, meta = custom_mobile.generate_mobile_response(
                "Them: Private transcript", "stuck_after_reply", input_source="accessibility",
                primary_model="gemini-test", fallback_model="gpt-test", overlay_instructions="CUSTOM STYLE", return_meta=True)
        self.assertTrue(success)
        self.assertEqual(json.loads(reply), REPLIES)
        self.assertEqual(meta["model_used"], "gpt-test")
        self.assertEqual(fallback.call_args.kwargs["overlay_instructions"], "CUSTOM STYLE")
        self.assertNotIn("Private", output.getvalue())
        self.assertNotIn(REPLIES[0]["message"], output.getvalue())

    def test_all_invalid_providers_fail_and_legacy_keeps_one_reply_behavior(self):
        with patch.object(custom_mobile, "_call_openai_replies", return_value=('[{"message":"legacy"}]', {})), \
             redirect_stdout(io.StringIO()):
            _, success = custom_mobile.generate_mobile_response("Them: Hello", "stuck_after_reply", input_source="accessibility", use_gpt_only=True)
            self.assertFalse(success)
            reply, success = custom_mobile.generate_mobile_response("legacy", "stuck_after_reply", use_gpt_only=True)
            self.assertTrue(success)
            self.assertEqual(json.loads(reply), [{"message": "legacy"}])
