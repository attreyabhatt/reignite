import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from conversation.acquisition import SESSION_KEY, PENDING_KEY
from conversation.models import WebConversionEvent
from conversation.test_web_conversion import INPUT, REPLIES


class AcquisitionTests(TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(WEB_ANALYTICS_ENABLED=True)
    def test_original_landing_survives_navigation_generation_and_signup(self):
        self.client.get('/situations/what-to-say-next-over-text/?secret=remove',
                        HTTP_REFERER='https://www.google.co.in/search?q=private-query')
        self.client.get('/pickup-lines/')
        with patch('conversation.views.generate_web_response', return_value=(REPLIES, True)):
            response = self.client.post(reverse('ajax_reply'), INPUT, HTTP_HX_REQUEST='true')
        generated = WebConversionEvent.objects.get(kind='generated')
        self.assertEqual(generated.landing_path, '/situations/what-to-say-next-over-text/')
        self.assertEqual((generated.acquisition_source, generated.acquisition_medium), ('google', 'organic'))
        trigger = json.loads(response['HX-Trigger'])['replyGenerated']
        self.assertEqual(trigger['landing_path'], generated.landing_path)
        self.assertNotIn('private', json.dumps(trigger))
        self.assertNotIn(INPUT['last_text'], json.dumps(trigger))
        self.client.post('/accounts/signup/', {'email': 'acquisition@example.com',
            'password1': 'Testing123!Long', 'password2': 'Testing123!Long', 'next': '/conversations/'})
        signup = WebConversionEvent.objects.get(kind='signup')
        self.assertEqual(signup.landing_path, generated.landing_path)
        self.assertEqual(signup.acquisition_source, 'google')
        self.assertEqual(len(self.client.session[PENDING_KEY]), 1)
        with override_settings(WEB_ANALYTICS_ENABLED=True):
            response = self.client.get('/conversations/')
            self.assertContains(response, '"name": "sign_up"')
            self.assertNotIn(PENDING_KEY, self.client.session)
            self.assertNotContains(self.client.get('/conversations/'), '"name": "sign_up"')

    def test_allowlisted_campaigns_and_private_referrers(self):
        self.client.get('/?utm_source=private@example.com&utm_medium=secret',
                        HTTP_REFERER='https://private.example.com/secret?token=hidden')
        self.assertEqual(self.client.session[SESSION_KEY],
                         {'landing_path': '/', 'source': 'other', 'medium': 'referral'})
        self.client.session.flush()

    def test_failed_generation_and_restored_results_emit_no_generation_event(self):
        with patch('conversation.views.generate_web_response', return_value=('', False)):
            response = self.client.post(reverse('ajax_reply'), INPUT, HTTP_HX_REQUEST='true')
        self.assertNotIn('replyGenerated', response.headers.get('HX-Trigger', ''))
        self.assertFalse(WebConversionEvent.objects.filter(kind='generated').exists())

    def test_unknown_pickup_paths_do_not_become_first_touch_metadata(self):
        self.assertEqual(self.client.get('/pickup-lines/private/unknown-person/').status_code, 404)
        self.assertNotIn(SESSION_KEY, self.client.session)

    @override_settings(WEB_ANALYTICS_ENABLED=True)
    def test_ga_page_location_strips_queries_and_account_secrets(self):
        response = self.client.get('/?private=chat-content', HTTP_REFERER='https://www.google.com/search?q=private-search')
        self.assertContains(response, "page_location: 'https://www.tryagaintext.com/'")
        self.assertContains(response, "page_referrer: 'https://www.google.com/'")
        self.assertNotContains(response, 'private-search')
        self.assertNotContains(response, 'chat-content')
