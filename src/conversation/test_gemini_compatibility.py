from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from google.genai import types

from conversation.utils.gemini_config import normalize_gemini_thinking_level
from conversation.utils.mobile import custom_mobile, image_mobile
from conversation.utils.web import custom_web, image_web


class GeminiThinkingCompatibilityTests(SimpleTestCase):
    MODEL_CASES = (
        ("gemini-3.8-flash", "low"),
        ("gemini-3-flash-preview", "minimal"),
    )

    def _client(self, text='[{"message":"Test reply"}]'):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=text, usage_metadata=None
        )
        return client

    def _assert_request_thinking(self, client, model, expected):
        client.models.generate_content.assert_called_once()
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], model)
        self.assertEqual(
            kwargs["config"].thinking_config.thinking_level,
            types.ThinkingLevel(expected.upper()),
        )

    def test_model_name_and_thinking_normalization(self):
        for model in ("gemini-3.8-flash", " models/GEMINI-3.8-FLASH "):
            with self.subTest(model=model):
                self.assertEqual(
                    normalize_gemini_thinking_level(" MINIMAL ", model), "low"
                )
                self.assertEqual(
                    normalize_gemini_thinking_level(None, model, default="minimal"),
                    "low",
                )

    def test_supported_thinking_levels_are_preserved(self):
        for model, _ in self.MODEL_CASES:
            for level in ("low", "medium", "high"):
                with self.subTest(model=model, level=level):
                    self.assertEqual(
                        normalize_gemini_thinking_level(level, model), level
                    )
            self.assertEqual(
                normalize_gemini_thinking_level("invalid", model), "high"
            )

    def test_mobile_replies_use_model_specific_thinking_and_metadata(self):
        for model, expected in self.MODEL_CASES:
            with self.subTest(model=model):
                client = self._client()
                with patch.object(custom_mobile, "client", client), patch.object(
                    custom_mobile, "_call_openai_replies"
                ) as fallback:
                    reply, success, meta = custom_mobile.generate_mobile_response(
                        "you: hi\nher: hey",
                        "mobile_stuck_reply_prompt",
                        thinking_level="minimal",
                        primary_model=model,
                        return_meta=True,
                    )

                self.assertTrue(success)
                self.assertIn("Test reply", reply)
                self._assert_request_thinking(client, model, expected)
                self.assertEqual(meta["thinking_used"], expected)
                fallback.assert_not_called()

    def test_mobile_openers_use_model_specific_thinking_and_metadata(self):
        for model, expected in self.MODEL_CASES:
            with self.subTest(model=model):
                client = self._client()
                with patch.object(custom_mobile, "client", client), patch.object(
                    custom_mobile, "_call_openai_openers"
                ) as fallback:
                    _, success, meta = custom_mobile.generate_mobile_openers_from_image(
                        b"profile image",
                        thinking_level="minimal",
                        primary_model=model,
                        return_meta=True,
                    )

                self.assertTrue(success)
                self._assert_request_thinking(client, model, expected)
                self.assertEqual(meta["thinking_used"], expected)
                fallback.assert_not_called()

    def test_gemini_fallback_uses_its_own_supported_thinking_level(self):
        client = self._client()
        client.models.generate_content.side_effect = [
            RuntimeError("Primary unavailable"),
            SimpleNamespace(text='[{"message":"Fallback reply"}]', usage_metadata=None),
        ]
        with patch.object(custom_mobile, "client", client):
            _, success, meta = custom_mobile.generate_mobile_response(
                "you: hi\nher: hey",
                "mobile_stuck_reply_prompt",
                thinking_level="minimal",
                primary_model="gemini-3.8-flash",
                fallback_model="gemini-3-flash-preview",
                return_meta=True,
            )

        self.assertTrue(success)
        calls = client.models.generate_content.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            [call.kwargs["config"].thinking_config.thinking_level for call in calls],
            [types.ThinkingLevel.LOW, types.ThinkingLevel.MINIMAL],
        )
        self.assertEqual(meta["model_used"], "gemini-3-flash-preview")
        self.assertEqual(meta["thinking_used"], "minimal")

    def test_openai_fallback_still_reports_no_thinking(self):
        client = self._client()
        client.models.generate_content.side_effect = RuntimeError("Primary unavailable")
        with patch.object(custom_mobile, "client", client), patch.object(
            custom_mobile,
            "_call_openai_replies",
            return_value=('[{"message":"Fallback reply"}]', {}),
        ) as fallback:
            _, success, meta = custom_mobile.generate_mobile_response(
                "you: hi\nher: hey",
                "mobile_stuck_reply_prompt",
                thinking_level="minimal",
                primary_model="gemini-3.8-flash",
                return_meta=True,
            )

        self.assertTrue(success)
        self._assert_request_thinking(client, "gemini-3.8-flash", "low")
        fallback.assert_called_once()
        self.assertEqual(meta["thinking_used"], "n/a")

    def test_web_replies_use_model_specific_thinking_and_metadata(self):
        for model, expected in self.MODEL_CASES:
            with self.subTest(model=model):
                client = self._client()
                with patch.object(custom_web, "GEMINI_FLASH", model), patch.object(
                    custom_web, "_get_client", return_value=client
                ), patch.object(
                    custom_web, "_get_provider_order", return_value=["gemini", "gpt"]
                ), patch.object(custom_web, "generate_replies_openai_web") as fallback:
                    _, success, meta = custom_web.generate_web_response(
                        "you: hi\nher: hey", "stuck_after_reply", return_meta=True
                    )

                self.assertTrue(success)
                self._assert_request_thinking(client, model, expected)
                self.assertEqual(meta["thinking_used"], expected)
                fallback.assert_not_called()

    def test_mobile_ocr_uses_model_specific_thinking_and_metadata(self):
        for model, expected in self.MODEL_CASES:
            with self.subTest(model=model):
                client = self._client("you [10:00]: hi\nher [10:01]: hey")
                with patch.object(image_mobile, "GEMINI_FLASH", model), patch.object(
                    image_mobile, "client", client
                ), patch.object(
                    image_mobile, "_resize_image_bytes", side_effect=lambda data: data
                ), patch.object(image_mobile, "_detect_mime", return_value="image/jpeg"):
                    _, success, meta = image_mobile.extract_conversation_from_image_mobile(
                        BytesIO(b"conversation image"),
                        thinking_level="minimal",
                        return_meta=True,
                    )

                self.assertTrue(success)
                self._assert_request_thinking(client, model, expected)
                self.assertEqual(meta["thinking_used"], expected)

    def test_web_ocr_uses_model_specific_thinking_and_metadata(self):
        for model, expected in self.MODEL_CASES:
            with self.subTest(model=model):
                client = self._client("you [10:00]: hi\nher [10:01]: hey")
                with patch.object(image_web, "GEMINI_FLASH", model), patch.object(
                    image_web, "_get_client", return_value=client
                ), patch.object(
                    image_web, "_get_provider_order", return_value=["gemini", "gpt"]
                ), patch.object(
                    image_web, "_resize_image_bytes", side_effect=lambda data: data
                ), patch.object(image_web, "_detect_mime", return_value="image/jpeg"):
                    _, success, meta = image_web.extract_conversation_from_image_web(
                        BytesIO(b"conversation image"), return_meta=True
                    )

                self.assertTrue(success)
                self._assert_request_thinking(client, model, expected)
                self.assertEqual(meta["thinking_used"], expected)
