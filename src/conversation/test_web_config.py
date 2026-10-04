from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from google.genai import types

from conversation.models import WebAppConfig
from conversation.utils.web import custom_web, image_web


class WebAppConfigAdminTests(TestCase):
    def test_admin_can_save_model_and_thinking_settings(self):
        user = User.objects.create_superuser(
            username="webconfigadmin", email="webconfig@example.com", password="testpassword"
        )
        self.client.force_login(user)
        cfg = WebAppConfig.load()
        url = reverse("admin:conversation_webappconfig_change", args=[cfg.pk])
        settings = {
            "gemini_reply_model": "gemini-3.8-flash",
            "reply_thinking": "medium",
            "gemini_ocr_model": "gemini-3-flash-preview",
            "ocr_thinking": "low",
            "gpt_reply_model": "gpt-4.1",
            "gpt_ocr_model": "gpt-4.1-mini",
        }

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        for field in settings:
            self.assertIn(field, form.fields)

        response = self.client.post(url, {
            **settings,
            "primary_provider": cfg.primary_provider,
            "guest_reply_limit": cfg.guest_reply_limit,
            "signup_bonus_credits": cfg.signup_bonus_credits,
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        cfg.refresh_from_db()
        for field, value in settings.items():
            self.assertEqual(getattr(cfg, field), value)
        self.assertEqual(WebAppConfig.objects.count(), 1)

        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text='[{"message":"Configured reply"}]', usage_metadata=None
        )
        with patch.object(custom_web, "_get_client", return_value=client):
            _, success, meta = custom_web.generate_web_response(
                "you: hi\nher: hey", "stuck_after_reply", return_meta=True
            )
        self.assertTrue(success)
        self.assertEqual(meta["model_used"], settings["gemini_reply_model"])
        self.assertEqual(meta["thinking_used"], settings["reply_thinking"])


class WebConfiguredModelRoutingTests(TestCase):
    def setUp(self):
        self.cfg = WebAppConfig.load()
        self.cfg.gemini_reply_model = "gemini-3.8-flash"
        self.cfg.reply_thinking = "medium"
        self.cfg.gemini_ocr_model = "gemini-3-flash-preview"
        self.cfg.ocr_thinking = "high"
        self.cfg.gpt_reply_model = "gpt-4.1"
        self.cfg.gpt_ocr_model = "gpt-4.1-mini"
        self.cfg.save()

    def _client(self, text='[{"message":"Configured reply"}]'):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=text, usage_metadata=None
        )
        return client

    def test_saved_models_and_thinking_are_used_on_each_generation(self):
        for model, thinking in (
            ("gemini-3.8-flash", "medium"),
            ("gemini-3-flash-preview", "minimal"),
        ):
            self.cfg.gemini_reply_model = model
            self.cfg.reply_thinking = thinking
            self.cfg.save()
            for situation in ("stuck_after_reply", "just_matched"):
                with self.subTest(model=model, situation=situation):
                    client = self._client()
                    with patch.object(custom_web, "_get_client", return_value=client):
                        _, success, meta = custom_web.generate_web_response(
                            "you: hi\nher: hey", situation, return_meta=True
                        )
                    self.assertTrue(success)
                    kwargs = client.models.generate_content.call_args.kwargs
                    self.assertEqual(kwargs["model"], model)
                    self.assertEqual(
                        kwargs["config"].thinking_config.thinking_level,
                        types.ThinkingLevel(thinking.upper()),
                    )
                    self.assertEqual(meta["model_used"], model)
                    self.assertEqual(meta["thinking_used"], thinking)

    def test_configured_gpt_reply_model_is_used_as_primary_or_fallback(self):
        for provider in (WebAppConfig.PROVIDER_GPT, WebAppConfig.PROVIDER_GEMINI):
            with self.subTest(provider=provider):
                self.cfg.primary_provider = provider
                self.cfg.save()
                client = self._client()
                client.models.generate_content.side_effect = RuntimeError("Gemini unavailable")
                with patch.object(custom_web, "_get_client", return_value=client), patch.object(
                    custom_web, "generate_replies_openai_web",
                    return_value=('[{"message":"Configured GPT reply"}]', {}),
                ) as gpt:
                    _, success, meta = custom_web.generate_web_response(
                        "you: hi\nher: hey", "stuck_after_reply", return_meta=True
                    )
                self.assertTrue(success)
                gpt.assert_called_once()
                self.assertEqual(gpt.call_args.kwargs["model"], self.cfg.gpt_reply_model)
                self.assertEqual(meta["model_used"], self.cfg.gpt_reply_model)
                self.assertEqual(meta["thinking_used"], "n/a")
                self.assertEqual(
                    client.models.generate_content.call_count,
                    1 if provider == WebAppConfig.PROVIDER_GEMINI else 0,
                )

    def test_ocr_uses_its_own_model_and_configured_or_explicit_thinking(self):
        for requested, expected in ((None, "high"), ("low", "low")):
            with self.subTest(requested=requested):
                client = self._client("you [10:00]: hi\nher [10:01]: hey")
                with patch.object(image_web, "_get_client", return_value=client), patch.object(
                    image_web, "_resize_image_bytes", side_effect=lambda data: data
                ), patch.object(image_web, "_detect_mime", return_value="image/jpeg"):
                    _, success, meta = image_web.extract_conversation_from_image_web(
                        BytesIO(b"conversation image"),
                        thinking_level=requested,
                        return_meta=True,
                    )
                self.assertTrue(success)
                client.models.generate_content.assert_called_once()
                kwargs = client.models.generate_content.call_args.kwargs
                self.assertEqual(kwargs["model"], self.cfg.gemini_ocr_model)
                self.assertEqual(
                    kwargs["config"].thinking_config.thinking_level,
                    types.ThinkingLevel(expected.upper()),
                )
                self.assertEqual(meta["model_used"], self.cfg.gemini_ocr_model)
                self.assertEqual(meta["thinking_used"], expected)

    def test_both_ocr_attempts_use_selected_model_and_supported_thinking(self):
        self.cfg.gemini_ocr_model = "gemini-3.8-flash"
        self.cfg.ocr_thinking = "minimal"
        self.cfg.save()
        client = self._client()
        client.models.generate_content.side_effect = [
            RuntimeError("Resized image failed"),
            SimpleNamespace(text="you [10:00]: hi", usage_metadata=None),
        ]
        with patch.object(image_web, "_get_client", return_value=client), patch.object(
            image_web, "_resize_image_bytes", return_value=b"resized image"
        ), patch.object(image_web, "_detect_mime", return_value="image/jpeg"):
            _, success, meta = image_web.extract_conversation_from_image_web(
                BytesIO(b"original conversation image"), return_meta=True
            )

        self.assertTrue(success)
        calls = client.models.generate_content.call_args_list
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertEqual(call.kwargs["model"], self.cfg.gemini_ocr_model)
            self.assertEqual(
                call.kwargs["config"].thinking_config.thinking_level, types.ThinkingLevel.LOW
            )
        self.assertEqual(meta["model_used"], self.cfg.gemini_ocr_model)
        self.assertEqual(meta["thinking_used"], "low")

    def test_configured_gpt_ocr_model_is_used_as_primary_or_fallback(self):
        for provider in (WebAppConfig.PROVIDER_GPT, WebAppConfig.PROVIDER_GEMINI):
            with self.subTest(provider=provider):
                self.cfg.primary_provider = provider
                self.cfg.save()
                client = self._client()
                client.models.generate_content.side_effect = RuntimeError("Gemini unavailable")
                with patch.object(image_web, "_get_client", return_value=client), patch.object(
                    image_web, "_resize_image_bytes", side_effect=lambda data: data
                ), patch.object(image_web, "_detect_mime", return_value="image/jpeg"), patch.object(
                    image_web, "extract_conversation_from_image_openai_web",
                    return_value=("you [10:00]: hi", {}),
                ) as gpt:
                    _, success, meta = image_web.extract_conversation_from_image_web(
                        BytesIO(b"conversation image"), return_meta=True
                    )
                self.assertTrue(success)
                gpt.assert_called_once()
                self.assertEqual(gpt.call_args.kwargs["model"], self.cfg.gpt_ocr_model)
                self.assertEqual(meta["model_used"], self.cfg.gpt_ocr_model)
                self.assertEqual(meta["thinking_used"], "n/a")
                self.assertEqual(
                    client.models.generate_content.call_count,
                    2 if provider == WebAppConfig.PROVIDER_GEMINI else 0,
                )
