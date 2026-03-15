import json
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Conversation, GuestWebConversationAttempt, WebAppConfig

class AjaxReplyViewTests(TestCase):
    def setUp(self):
        self.url = reverse('ajax_reply')
        self.user = User.objects.create_user(
            username='webtester',
            email='webtester@example.com',
            password='password123',
        )
        self.client.force_login(self.user)

    @patch('conversation.views.generate_web_response')
    def test_htmx_success_returns_suggestions_partial(self, mock_generate):
        mock_generate.return_value = (
            '[{"message":"Want to grab coffee?","confidence_score":0.91},'
            '{"message":"Drinks this week?","confidence_score":0.84}]',
            True,
        )

        response = self.client.post(
            self.url,
            data={
                'last_text': 'you: hey\nher: hi',
                'situation': 'stuck_after_reply',
                'her_info': '',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Want to grab coffee?')
        self.assertContains(response, 'Drinks this week?')
        self.assertContains(response, 'data-suggestion-rank="01"', html=False)
        self.assertContains(response, 'data-suggestion-rank="02"', html=False)
        self.assertIn('HX-Trigger', response.headers)

    def test_htmx_invalid_input_returns_inline_error_partial(self):
        response = self.client.post(
            self.url,
            data={
                'last_text': '',
                'situation': 'dry_reply',
                'her_info': '',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Could not generate replies')
        self.assertContains(response, 'Conversation text is required.')

    def test_htmx_redirect_when_user_has_no_credits(self):
        chat_credit = self.user.chat_credit
        chat_credit.balance = 0
        chat_credit.save()

        response = self.client.post(
            self.url,
            data={
                'last_text': 'you: hey\nher: hi',
                'situation': 'stuck_after_reply',
                'her_info': '',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('HX-Redirect'), reverse('pricing:pricing'))

    @patch('conversation.views.generate_web_response')
    def test_non_htmx_success_returns_json_with_custom_and_suggestions(self, mock_generate):
        mock_generate.return_value = (
            '```json\n[{"message":"Line 1","confidence_score":0.91},'
            '{"message":"Line 2","confidence_score":"0.8"},'
            '{"message":"Line 3"}]\n```',
            True,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('custom', payload)
        self.assertIn('suggestions', payload)
        self.assertEqual(len(payload['suggestions']), 3)
        self.assertEqual(payload['suggestions'][0]['message'], 'Line 1')
        self.assertAlmostEqual(payload['suggestions'][1]['confidence_score'], 0.8)

    @patch('conversation.views.generate_web_response')
    def test_just_matched_allows_empty_conversation(self, mock_generate):
        mock_generate.return_value = (
            '[{"message":"You seem fun. What made you smile today?"},'
            '{"message":"You look like trouble in a good way. What is your best weekend plan?"},'
            '{"message":"You seem easy to talk to. What are you currently excited about?"}]',
            True,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': '',
                'situation': 'just_matched',
                'her_info': 'Loves coffee and hiking.',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['suggestions']), 3)
        self.assertEqual(payload['suggestions'][0]['message'], 'You seem fun. What made you smile today?')

    @patch('conversation.views.generate_web_response')
    def test_reply_all_failed_returns_expected_error_shape(self, mock_generate):
        mock_generate.return_value = (
            '[{"message":"We hit a hiccup generating replies. Try again in a moment."}]',
            False,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(
            payload.get("error"),
            "AI failed to generate a proper response. Try again. No credit deducted.",
        )

    @patch('conversation.views.generate_web_response')
    def test_authenticated_paid_credits_are_not_limited_by_signup_bonus_setting(self, mock_generate):
        cfg = WebAppConfig.load()
        cfg.signup_bonus_credits = 0
        cfg.save()

        chat_credit = self.user.chat_credit
        chat_credit.balance = 2
        chat_credit.save(update_fields=["balance"])

        mock_generate.return_value = (
            '[{"message":"Line 1","confidence_score":0.91}]',
            True,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("credits_left"), 1)
        self.assertEqual(GuestWebConversationAttempt.objects.count(), 0)


class ConversationHomeTemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='conversationtemplateuser',
            email='conversationtemplateuser@example.com',
            password='password123',
        )
        self.client.force_login(self.user)

    def test_conversation_home_uses_shared_pickup_playground_and_keeps_sidebar(self):
        convo = Conversation.objects.create(
            user=self.user,
            content='you: hey\nher: hi',
            situation='stuck_after_reply',
            her_info='',
            girl_title='Hi...',
        )

        response = self.client.get(reverse('conversation_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-reply-tool-shared="1"', html=False)
        self.assertContains(response, 'data-tool-variant="pickup"', html=False)
        self.assertContains(response, 'id="playground"', html=False)
        self.assertContains(
            response,
            '<link rel="stylesheet" href="/static/css/pickup_playground.css">',
            html=False,
        )
        self.assertContains(response, 'id="convoList"', html=False)
        self.assertContains(response, f'data-conversation-item-id="{convo.id}"', html=False)
        self.assertContains(response, "No response generated yet.")


class GuestReplyLimitTests(TestCase):
    def setUp(self):
        self.url = reverse('ajax_reply')
        self.cfg = WebAppConfig.load()
        self.cfg.guest_reply_limit = 1
        self.cfg.save()

    @patch('conversation.views.generate_web_response')
    def test_guest_reply_limit_uses_web_app_config(self, mock_generate):
        mock_generate.return_value = (
            '[{"message":"Line 1","confidence_score":0.91}]',
            True,
        )

        first = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json().get("credits_left"), 0)

        second = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi again\nher: hey again',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )
        self.assertEqual(second.status_code, 403)
        self.assertIn("redirect_url", second.json())


class GuestWebConversationAttemptLoggingTests(TestCase):
    def setUp(self):
        self.url = reverse('ajax_reply')

    @patch('conversation.views.generate_web_response')
    def test_guest_success_logs_input_and_output_payloads(self, mock_generate):
        mock_generate.return_value = (
            '[{"message":"Line 1","confidence_score":0.91}]',
            True,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': 'likes coffee',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(GuestWebConversationAttempt.objects.count(), 1)

        event = GuestWebConversationAttempt.objects.get()
        self.assertEqual(
            event.endpoint,
            GuestWebConversationAttempt.Endpoint.CONVERSATIONS_AJAX_REPLY,
        )
        self.assertEqual(event.status, GuestWebConversationAttempt.Status.SUCCESS)
        self.assertEqual(event.http_status, 200)
        self.assertEqual(len(event.session_key_hash), 64)
        self.assertEqual(event.input_payload.get("situation"), "stuck_after_reply")
        self.assertEqual(event.input_payload.get("her_info"), "likes coffee")
        self.assertIn("custom", event.output_payload)
        self.assertIn("suggestions", event.output_payload)

    def test_guest_validation_error_is_logged(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': '',
                'situation': 'dry_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(GuestWebConversationAttempt.objects.count(), 1)

        event = GuestWebConversationAttempt.objects.get()
        self.assertEqual(event.status, GuestWebConversationAttempt.Status.VALIDATION_ERROR)
        self.assertEqual(event.http_status, 400)

    def test_guest_no_credit_block_is_logged(self):
        session = self.client.session
        session["chat_credits"] = 0
        session.save()

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(GuestWebConversationAttempt.objects.count(), 1)

        event = GuestWebConversationAttempt.objects.get()
        self.assertEqual(event.status, GuestWebConversationAttempt.Status.CREDITS_BLOCKED)
        self.assertEqual(event.http_status, 403)
        self.assertIn("redirect_url", event.output_payload)

    @patch('conversation.views.generate_web_response')
    def test_guest_ai_error_is_logged(self, mock_generate):
        mock_generate.side_effect = Exception("boom")

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(GuestWebConversationAttempt.objects.count(), 1)

        event = GuestWebConversationAttempt.objects.get()
        self.assertEqual(event.status, GuestWebConversationAttempt.Status.AI_ERROR)
        self.assertEqual(event.http_status, 500)

    @patch('conversation.views.generate_web_response')
    def test_guest_parse_error_is_logged(self, mock_generate):
        mock_generate.return_value = ("not-json", True)

        response = self.client.post(
            self.url,
            data=json.dumps({
                'last_text': 'you: hi\\nher: hey',
                'situation': 'stuck_after_reply',
                'her_info': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(GuestWebConversationAttempt.objects.count(), 1)

        event = GuestWebConversationAttempt.objects.get()
        self.assertEqual(event.status, GuestWebConversationAttempt.Status.PARSE_ERROR)
        self.assertEqual(event.http_status, 500)


class OcrScreenshotViewTests(TestCase):
    def setUp(self):
        self.url = reverse('ocr_screenshot')
        self.cfg = WebAppConfig.load()

    @patch('conversation.views.extract_conversation_from_image_web')
    def test_ocr_failure_returns_error_json(self, mock_extract):
        self.cfg.primary_provider = WebAppConfig.PROVIDER_GEMINI
        self.cfg.save()
        mock_extract.side_effect = Exception("ocr failure")
        screenshot = SimpleUploadedFile(
            "chat.png",
            b"\x89PNG\r\n\x1a\nmock-image-bytes",
            content_type="image/png",
        )

        response = self.client.post(self.url, data={"screenshot": screenshot})

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload.get("error"), "OCR failed. Please try again.")

    @patch("conversation.utils.web.image_web.extract_conversation_from_image_openai_web")
    @patch("conversation.utils.web.image_web._run_ocr_call")
    def test_ocr_gpt_fallback_success_returns_ocr_text(self, mock_gemini_ocr, mock_openai_ocr):
        self.cfg.primary_provider = WebAppConfig.PROVIDER_GEMINI
        self.cfg.save()
        mock_gemini_ocr.side_effect = [Exception("gemini failed 1"), Exception("gemini failed 2")]
        mock_openai_ocr.return_value = (
            "you []: hi\nher []: hello",
            {"input_tokens": 1, "output_tokens": 1, "thinking_tokens": 0, "total_tokens": 2},
        )

        screenshot = SimpleUploadedFile(
            "chat.png",
            b"\x89PNG\r\n\x1a\nmock-image-bytes",
            content_type="image/png",
        )
        response = self.client.post(self.url, data={"screenshot": screenshot})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("ocr_text", payload)
        self.assertIn("you []:", payload["ocr_text"])
        self.assertEqual(mock_gemini_ocr.call_count, 2)
        self.assertEqual(mock_openai_ocr.call_count, 1)

    @patch("conversation.utils.web.image_web.extract_conversation_from_image_openai_web")
    @patch("conversation.utils.web.image_web._run_ocr_call")
    def test_ocr_primary_gpt_uses_gpt_first(self, mock_gemini_ocr, mock_openai_ocr):
        self.cfg.primary_provider = WebAppConfig.PROVIDER_GPT
        self.cfg.save()
        mock_openai_ocr.return_value = (
            "you []: hi\nher []: hello",
            {"input_tokens": 1, "output_tokens": 1, "thinking_tokens": 0, "total_tokens": 2},
        )

        screenshot = SimpleUploadedFile(
            "chat.png",
            b"\x89PNG\r\n\x1a\nmock-image-bytes",
            content_type="image/png",
        )
        response = self.client.post(self.url, data={"screenshot": screenshot})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("ocr_text", payload)
        self.assertEqual(mock_openai_ocr.call_count, 1)
        self.assertEqual(mock_gemini_ocr.call_count, 0)

    @patch("conversation.utils.web.image_web.extract_conversation_from_image_openai_web")
    @patch("conversation.utils.web.image_web._run_ocr_call")
    def test_ocr_all_failed_returns_failure_text_payload(self, mock_gemini_ocr, mock_openai_ocr):
        self.cfg.primary_provider = WebAppConfig.PROVIDER_GEMINI
        self.cfg.save()
        mock_gemini_ocr.side_effect = [Exception("gemini failed 1"), Exception("gemini failed 2")]
        mock_openai_ocr.side_effect = Exception("openai failed")

        screenshot = SimpleUploadedFile(
            "chat.png",
            b"\x89PNG\r\n\x1a\nmock-image-bytes",
            content_type="image/png",
        )
        response = self.client.post(self.url, data={"screenshot": screenshot})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("ocr_text", payload)
        self.assertIn("Failed to extract the conversation with timestamps.", payload["ocr_text"])


class WebAppConfigModelTests(TestCase):
    def test_load_creates_singleton_with_gemini_default(self):
        WebAppConfig.objects.all().delete()

        cfg = WebAppConfig.load()

        self.assertEqual(cfg.primary_provider, WebAppConfig.PROVIDER_GEMINI)
        self.assertEqual(cfg.guest_reply_limit, 5)
        self.assertEqual(cfg.signup_bonus_credits, 3)
        self.assertEqual(cfg.fallback_provider, WebAppConfig.PROVIDER_GPT)
        self.assertEqual(cfg.provider_order(), [WebAppConfig.PROVIDER_GEMINI, WebAppConfig.PROVIDER_GPT])
        self.assertEqual(WebAppConfig.objects.count(), 1)


class WebFallbackUtilityTests(TestCase):
    @patch("conversation.utils.web.custom_web.generate_replies_openai_web")
    @patch("conversation.utils.web.custom_web._get_client")
    def test_reply_order_primary_gemini_then_gpt(self, mock_gemini_client, mock_openai):
        from conversation.utils.web.custom_web import generate_web_response

        cfg = WebAppConfig.load()
        cfg.primary_provider = WebAppConfig.PROVIDER_GEMINI
        cfg.save()

        call_order = []

        def _gemini_side_effect(*args, **kwargs):
            call_order.append("gemini")
            raise Exception("gemini failure")

        def _openai_side_effect(*args, **kwargs):
            call_order.append("gpt")
            return (
                '[{"message":"Fallback reply","confidence_score":0.8}]',
                {"input_tokens": 10, "output_tokens": 6, "thinking_tokens": 0, "total_tokens": 16},
            )

        mock_gemini_client.return_value.models.generate_content.side_effect = _gemini_side_effect
        mock_openai.side_effect = _openai_side_effect

        ai_reply, success, meta = generate_web_response(
            "you: hi\nher: hey",
            "stuck_after_reply",
            return_meta=True,
        )

        self.assertTrue(success)
        self.assertEqual(call_order, ["gemini", "gpt"])
        self.assertIn("Fallback reply", ai_reply)
        self.assertEqual(meta["model_used"], "gpt-4.1-mini-2025-04-14")
        self.assertEqual(meta["thinking_used"], "n/a")

    @patch("conversation.utils.web.custom_web.generate_replies_openai_web")
    @patch("conversation.utils.web.custom_web._get_client")
    def test_reply_order_primary_gpt_then_gemini(self, mock_gemini_client, mock_openai):
        from conversation.utils.web.custom_web import generate_web_response

        cfg = WebAppConfig.load()
        cfg.primary_provider = WebAppConfig.PROVIDER_GPT
        cfg.save()

        call_order = []

        class _GeminiUsage:
            prompt_token_count = 10
            candidates_token_count = 8
            thoughts_token_count = 2

        class _GeminiResponse:
            text = '[{"message":"Gemini fallback"}]'
            usage_metadata = _GeminiUsage()

        def _openai_side_effect(*args, **kwargs):
            call_order.append("gpt")
            raise Exception("openai failure")

        def _gemini_side_effect(*args, **kwargs):
            call_order.append("gemini")
            return _GeminiResponse()

        mock_openai.side_effect = _openai_side_effect
        mock_gemini_client.return_value.models.generate_content.side_effect = _gemini_side_effect

        ai_reply, success, meta = generate_web_response(
            "you: hi\nher: hey",
            "stuck_after_reply",
            return_meta=True,
        )

        self.assertTrue(success)
        self.assertEqual(call_order, ["gpt", "gemini"])
        self.assertIn("Gemini fallback", ai_reply)
        self.assertEqual(meta["model_used"], "gemini-3-flash-preview")
        self.assertEqual(meta["thinking_used"], "minimal")

    @patch("conversation.utils.web.custom_web.generate_replies_openai_web")
    @patch("conversation.utils.web.custom_web._get_client")
    def test_generate_web_response_all_failed_returns_default_message(self, mock_gemini_client, mock_openai):
        from conversation.utils.web.custom_web import generate_web_response

        cfg = WebAppConfig.load()
        cfg.primary_provider = WebAppConfig.PROVIDER_GEMINI
        cfg.save()

        mock_gemini_client.return_value.models.generate_content.side_effect = Exception("gemini failure")
        mock_openai.side_effect = Exception("openai failure")

        ai_reply, success, meta = generate_web_response(
            "you: hi\nher: hey",
            "stuck_after_reply",
            return_meta=True,
        )

        self.assertFalse(success)
        parsed = json.loads(ai_reply)
        self.assertIn("We hit a hiccup generating replies.", parsed[0]["message"])
        self.assertEqual(meta["model_used"], "none")

