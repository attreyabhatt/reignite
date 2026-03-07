import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AjaxReplyViewTests(TestCase):
    def setUp(self):
        self.url = reverse('ajax_reply')
        self.user = User.objects.create_user(
            username='webtester',
            email='webtester@example.com',
            password='password123',
        )
        self.client.force_login(self.user)

    @patch('conversation.views.generate_custom_response')
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

    @patch('conversation.views.generate_custom_response')
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

