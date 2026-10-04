import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from conversation.models import WebAppConfig
from conversation.web_credits import GUEST_REPLIES_USED_KEY
from seoapp.models import PickupCategory, PickupTopic
from seoapp.situation_pages import list_situation_pages


class WebCreditConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = PickupCategory.objects.create(slug="books", name="Books")
        cls.topic = PickupTopic.objects.create(
            category=category, slug="book-lovers", keyword="Book lovers",
            h1="Pickup lines for book lovers", title="Book lovers pickup lines",
        )

    def setUp(self):
        cache.clear()
        self.cfg = WebAppConfig.load()
        self.cfg.guest_reply_limit = 5
        self.cfg.signup_bonus_credits = 3
        self.cfg.save()
        self.paths = (
            reverse("home"),
            reverse("situation_landing", args=[list_situation_pages()[0]["slug"]]),
            reverse("pickup_line_detail", args=["books", self.topic.slug]),
        )
        self.generator = patch(
            "conversation.views.generate_web_response",
            return_value=('[{"message":"Suggested reply"}]', True),
        ).start()
        self.addCleanup(patch.stopall)

    def _generate(self, htmx=True):
        return self.client.post(
            reverse("ajax_reply"),
            {"last_text": "you: hi\nher: hey", "situation": "stuck_after_reply"},
            HTTP_HX_REQUEST="true" if htmx else "false",
        )

    def _assert_counters(self, expected, client=None):
        client = client or self.client
        for path in self.paths:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertContains(response, f'id="chatCredits">{expected}</span>')

    def test_guest_limit_changes_update_all_tools_in_existing_session(self):
        for limit in (5, 8, 1, 0):
            with self.subTest(limit=limit):
                self.cfg.guest_reply_limit = limit
                self.cfg.save()
                self._assert_counters(limit)
                response = self.client.get(reverse("home"))
                suffix = "" if limit == 1 else "s"
                self.assertContains(response, f"{limit} free generation{suffix} to try")

    def test_limit_changes_preserve_used_credits_even_when_balance_is_zero(self):
        self._generate()
        self._generate()
        self.assertEqual(self.client.session[GUEST_REPLIES_USED_KEY], 2)

        for limit, remaining in ((8, 6), (1, 0), (0, 0), (8, 6)):
            with self.subTest(limit=limit):
                self.cfg.guest_reply_limit = limit
                self.cfg.save()
                self._assert_counters(remaining)
                self.assertEqual(self.client.session[GUEST_REPLIES_USED_KEY], 2)

    def test_generation_uses_changed_limit_and_does_not_overspend(self):
        self.client.get(reverse("home"))
        self.cfg.guest_reply_limit = 1
        self.cfg.save()

        first = self._generate(htmx=False)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["credits_left"], 0)
        blocked = self._generate(htmx=False)
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(self.generator.call_count, 1)
        self._assert_counters(0)

    def test_lowered_limit_updates_the_counter_in_htmx_blocked_response(self):
        self.client.get(reverse("home"))
        self.cfg.guest_reply_limit = 0
        self.cfg.save()

        response = self._generate()
        self.assertContains(response, "Get 3 more free generations")
        self.assertEqual(
            json.loads(response["HX-Trigger"])["creditsUpdated"]["credits_left"], 0
        )
        self.generator.assert_not_called()

    def test_failed_generation_does_not_use_new_allowance(self):
        self._generate()
        self.cfg.guest_reply_limit = 8
        self.cfg.save()
        self.generator.return_value = ("", False)

        response = self._generate(htmx=False)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.client.session[GUEST_REPLIES_USED_KEY], 1)
        self._assert_counters(7)

    def test_existing_session_balances_are_preserved_when_tracking_starts(self):
        for remaining in (0, 3, 5):
            with self.subTest(remaining=remaining):
                self.cfg.guest_reply_limit = 5
                self.cfg.save()
                client = Client()
                session = client.session
                session["chat_credits"] = remaining
                session.save()
                self._assert_counters(remaining, client=client)

                self.cfg.guest_reply_limit = 8
                self.cfg.save()
                self._assert_counters(remaining + 3, client=client)

    @patch("reignitehome.views.generate_reignite_comeback", return_value=("Suggested reply", True))
    def test_home_endpoint_and_shared_tool_track_the_same_allowance(self, home_generator):
        self.client.get(reverse("home"))
        response = self.client.post(
            reverse("ajax_reply_home"),
            json.dumps({
                "last_text": "you: hi\nher: hey", "platform": "Tinder",
                "what_happened": "She left me on read",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["credits_left"], 4)
        self.assertEqual(self.client.session[GUEST_REPLIES_USED_KEY], 1)
        home_generator.assert_called_once()

        self.cfg.guest_reply_limit = 9
        self.cfg.save()
        self._assert_counters(8)
        response = self._generate(htmx=False)
        self.assertEqual(response.json()["credits_left"], 7)

    def test_signup_copy_and_comparison_follow_both_settings(self):
        for limit, bonus in ((5, 3), (8, 11), (1, 1), (0, 0)):
            with self.subTest(limit=limit, bonus=bonus):
                self.cfg.guest_reply_limit = limit
                self.cfg.signup_bonus_credits = bonus
                self.cfg.save()
                response = self.client.get(
                    reverse("account_signup"), {"message": "out_of_credits"}
                )
                self.assertContains(response, f"<td>{limit} to try</td>", html=True)
                self.assertContains(response, f"<td>{bonus} with signup</td>", html=True)
                if bonus:
                    suffix = "" if bonus == 1 else "s"
                    self.assertContains(response, f"{bonus} free generation{suffix} (no card needed)")
                    self.assertContains(response, f"get {bonus} more free generation{suffix}")
                else:
                    self.assertNotContains(response, "free generations (no card needed)")
                    self.assertNotContains(response, "get 3 more free generations")

    def test_signup_offers_use_changed_bonus_on_each_generation(self):
        for bonus in (11, 1, 0):
            with self.subTest(bonus=bonus):
                self.cfg.signup_bonus_credits = bonus
                self.cfg.save()
                response = self._generate()
                if bonus:
                    suffix = "" if bonus == 1 else "s"
                    self.assertContains(response, f"Get {bonus} more free generation{suffix}")
                    self.assertContains(response, f"{bonus} generation{suffix} included with signup.")
                else:
                    self.assertContains(response, "Create your free account")
                    self.assertNotContains(response, "included with signup.")

    def test_config_changes_do_not_replace_signed_in_account_balances(self):
        user = User.objects.create_user("creditowner", "owner@example.com", "testpassword")
        user.chat_credit.balance = 23
        user.chat_credit.save()
        self.client.force_login(user)
        self.cfg.guest_reply_limit = 0
        self.cfg.signup_bonus_credits = 0
        self.cfg.save()

        self.assertContains(
            self.client.get(reverse("conversation_home")), 'id="chatCredits">23</span>'
        )
        for path in self.paths[1:]:
            self.assertContains(self.client.get(path), 'id="chatCredits">23</span>')
        user.chat_credit.refresh_from_db()
        self.assertEqual(user.chat_credit.balance, 23)
