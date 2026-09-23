import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from pricing.models import CreditPurchase
from .models import Conversation, WebAppConfig, WebConversionEvent
from .web_conversion import DRAFT_KEY, JOURNEY_KEY
from .web_report import web_conversion_report

REPLIES = [{"message": "Coffee sounds good. What's your usual order?"},
           {"message": "I'm a flat-white regular. What about you?"},
           {"message": "Let's compare coffee spots sometime."}]
INPUT = {"last_text": "Me: Coffee or tea?\nThem: Coffee, always.",
         "situation": "stuck_after_reply", "her_info": "We both like hiking."}


class ContinuationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cfg = WebAppConfig.load()
        self.cfg.guest_reply_limit = 3
        self.cfg.signup_bonus_credits = 3
        self.cfg.save()
        self.mock = patch("conversation.views.generate_web_response", return_value=(REPLIES, True)).start()
        self.addCleanup(patch.stopall)

    def generate(self, htmx=True):
        return self.client.post(reverse("ajax_reply"), INPUT,
            HTTP_HX_REQUEST="true" if htmx else "false",
            HTTP_REFERER="https://www.tryagaintext.com/situations/what-to-say-next-over-text/?private=removed")

    def signup(self, **extra):
        return self.client.post(reverse("account_signup"), {"email": "new@example.com",
            "password1": "Testing123!Long", "password2": "Testing123!Long", **extra})

    def test_trial_continues_inline_and_last_result_survives_exhaustion(self):
        for left in (2, 1, 0):
            response = self.generate()
            self.assertContains(response, "Get 3 more free generations")
            self.assertEqual(self.client.session["chat_credits"], left)
        response = self.generate()
        self.assertNotIn("HX-Redirect", response.headers)
        self.assertContains(response, escape(REPLIES[0]["message"]))
        self.assertContains(response, "Continue this conversation")
        self.assertEqual(self.mock.call_count, 3)
        self.assertEqual(WebConversionEvent.objects.filter(kind="generated").count(), 3)

    def test_signup_restores_once_and_links_guest_events_without_another_charge(self):
        self.generate()
        identity = self.client.session[JOURNEY_KEY]
        response = self.signup(next="/conversations/")
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.chat_credit.balance, 3)
        self.assertEqual(self.mock.call_count, 1)
        self.assertEqual(Conversation.objects.filter(user=user).count(), 1)
        convo = Conversation.objects.get(user=user)
        self.assertEqual(convo.content, INPUT["last_text"])
        self.assertEqual(convo.her_info, INPUT["her_info"])
        self.assertEqual(convo.latest_suggestions[0]["message"], REPLIES[0]["message"])
        self.assertNotIn(DRAFT_KEY, self.client.session)
        self.assertEqual(self.client.session[JOURNEY_KEY], identity)
        self.assertEqual(WebConversionEvent.objects.filter(journey_id=identity, user=user).count(), 2)
        for _ in range(2):
            response = self.client.get(reverse("conversation_home"))
            self.assertContains(response, escape(REPLIES[1]["message"]))
        self.assertEqual(Conversation.objects.filter(user=user).count(), 1)
        self.assertEqual(user.chat_credit.balance, 3)

    def test_existing_user_signin_keeps_paid_balance_and_saved_result(self):
        user = User.objects.create_user("existing", "existing@example.com", "Testing123!Long")
        credit = user.chat_credit
        credit.balance = 74
        credit.save()
        self.generate()
        response = self.client.post(reverse("account_login"), {"login": user.email,
            "password": "Testing123!Long", "next": "/conversations/"})
        self.assertEqual(response.status_code, 302)
        credit.refresh_from_db()
        self.assertEqual(credit.balance, 74)
        self.assertEqual(Conversation.objects.filter(user=user).count(), 1)
        self.assertFalse(WebConversionEvent.objects.filter(kind="signup").exists())

    def test_expired_draft_not_imported(self):
        self.generate()
        session = self.client.session
        draft = session[DRAFT_KEY]
        draft["created_at"] = (timezone.now() - timedelta(hours=25)).isoformat()
        session[DRAFT_KEY] = draft
        session.save()
        self.signup()
        self.assertEqual(Conversation.objects.count(), 0)

    def test_failed_generation_does_not_replace_good_draft_or_spend_credit(self):
        self.generate()
        draft = self.client.session[DRAFT_KEY]
        self.mock.return_value = ("", False)
        self.generate()
        self.assertEqual(self.client.session[DRAFT_KEY], draft)
        self.assertEqual(self.client.session["chat_credits"], 2)

    def test_continuing_imported_conversation_updates_it_only_after_success(self):
        self.generate()
        self.signup()
        convo = Conversation.objects.get()
        updated = {**INPUT, "last_text": INPUT["last_text"] + "\nMe: Flat white?", "conversation_id": convo.pk}
        self.mock.return_value = ("", False)
        self.client.post(reverse("ajax_reply"), updated, HTTP_HX_REQUEST="true")
        convo.refresh_from_db()
        self.assertEqual(convo.content, INPUT["last_text"])
        self.assertEqual(convo.user.chat_credit.balance, 3)
        self.mock.return_value = (REPLIES, True)
        self.client.post(reverse("ajax_reply"), updated, HTTP_HX_REQUEST="true")
        convo.refresh_from_db()
        self.assertEqual(convo.content, updated["last_text"])
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(convo.user.chat_credit.balance, 2)

    def test_draft_replay_does_not_duplicate_import(self):
        self.generate()
        draft = self.client.session[DRAFT_KEY]
        self.signup()
        session = self.client.session
        session[DRAFT_KEY] = draft
        session.save()
        self.client.get(reverse("conversation_home"))
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(User.objects.get(email="new@example.com").chat_credit.balance, 3)

    def test_new_conversation_clears_active_result_without_deleting_or_charging(self):
        self.generate()
        self.signup()
        response = self.client.get(reverse("conversation_home"), {"new": "1"})
        self.assertNotContains(response, escape(REPLIES[0]["message"]))
        self.assertNotIn("web_active_conversation", self.client.session)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(User.objects.get(email="new@example.com").chat_credit.balance, 3)
        self.assertNotContains(self.client.get(reverse("conversation_home")), escape(REPLIES[0]["message"]))

    def test_configured_allowance_and_zero_bonus_are_honest(self):
        self.cfg.guest_reply_limit = 1
        self.cfg.signup_bonus_credits = 9
        self.cfg.save()
        self.assertContains(self.generate(), "Get 9 more free generations")
        self.signup()
        self.assertEqual(User.objects.get(email="new@example.com").chat_credit.balance, 9)

    def test_zero_signup_allowance_is_not_replaced_with_default(self):
        self.cfg.signup_bonus_credits = 0
        self.cfg.save()
        self.assertContains(self.generate(), "Create your free account")
        response = self.client.get(reverse("account_signup") + "?message=out_of_credits")
        self.assertNotContains(response, "unlimited")
        self.assertNotContains(response, "3 free generations")

    def test_logged_in_last_credit_shows_starter_pack_and_persists_results(self):
        user = User.objects.create_user("buyer", "buyer@example.com", "Testing123!Long")
        user.chat_credit.balance = 1
        user.chat_credit.save()
        self.client.force_login(user)
        response = self.generate()
        self.assertContains(response, "$1.99")
        self.assertContains(response, "/pricing/purchase/10/")
        self.assertNotContains(response, "Get 3 more free")
        self.assertContains(self.generate(), escape(REPLIES[0]["message"]))
        self.assertEqual(self.mock.call_count, 1)
        convo = Conversation.objects.get(user=user)
        self.assertIn(escape(REPLIES[0]["message"]), self.client.get(reverse("conversation_detail", args=[convo.pk])).json()["result_html"])
        self.assertContains(self.client.get(reverse("conversation_home")), "$1.99")

    def test_pack_selection_survives_auth_and_checkout_is_recorded(self):
        next_url = reverse("pricing:purchase", args=[10])
        response = self.client.get(reverse("account_signup"), {"next": next_url})
        self.assertContains(response, 'name="next" value="/pricing/purchase/10/"')
        self.assertContains(response, "/accounts/login/?next=/pricing/purchase/10/")
        response = self.signup(next=next_url)
        self.assertEqual(response["Location"], next_url)
        response = self.client.get(next_url)
        self.assertIn("test.checkout.dodopayments.com", response["Location"])
        self.assertEqual(WebConversionEvent.objects.get(kind="checkout").credit_pack, 10)
        self.assertFalse(CreditPurchase.objects.exists())

    def test_external_next_does_not_redirect_off_site(self):
        response = self.signup(next="https://evil.example/")
        self.assertNotIn("evil.example", response["Location"])

    def test_copy_actions_link_to_generation_and_retry_deduplicates(self):
        generation = self.generate(False).json()["generation_id"]
        action = str(uuid.uuid4())
        data = {"situation": INPUT["situation"], "copied_message": REPLIES[0]["message"],
                "generation_id": generation, "action_id": action}
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("log_copy"), json.dumps(data), content_type="application/json").status_code, 200)
        event = WebConversionEvent.objects.get(kind="copied")
        self.assertEqual(str(event.generation_id), generation)
        self.assertEqual(event.origin_path, "/situations/what-to-say-next-over-text/")

    def test_offer_events_are_owned_and_deduplicated(self):
        generation = self.generate(False).json()["generation_id"]
        data = {"kind": "offer_shown", "generation_id": generation, "offer_kind": "signup"}
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("web_conversion_event"), json.dumps(data), content_type="application/json").status_code, 200)
        self.assertEqual(WebConversionEvent.objects.filter(kind="offer_shown").count(), 1)
        from django.test import Client
        other = Client()
        self.assertEqual(other.post(reverse("web_conversion_event"), json.dumps(data), content_type="application/json").status_code, 400)


class PlatformLandingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from seoapp.models import PickupCategory, PickupTopic
        for category_slug, slug in (("professions", "lawyer"), ("dating-apps", "instagram-dm-opener")):
            category = PickupCategory.objects.create(slug=category_slug, name=category_slug)
            PickupTopic.objects.create(category=category, slug=slug, keyword=slug, h1=slug,
                                      witty_lines=["Existing guide example"])

    def test_android_primary_action_and_web_fallback(self):
        paths = ["/", "/pickup-lines/professions/lawyer/", "/pickup-lines/dating-apps/instagram-dm-opener/",
                 "/situations/what-to-say-next-over-text/"]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14)")
                self.assertContains(response, "Use the web version")
                placement = b'data-app-promo-placement="hero"' if path == "/" else b'data-app-promo-placement="guide_primary"'
                self.assertLess(response.content.index(placement), response.content.index(b'id="chatForm"'))
                self.assertIn("User-Agent", response["Vary"])
                self.assertContains(response, 'id="chatForm"', count=1)

    def test_iphone_and_desktop_get_web_tool_before_app_promotion(self):
        for agent in ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"):
            for path in ("/", "/pickup-lines/professions/lawyer/", "/pickup-lines/dating-apps/instagram-dm-opener/",
                         "/situations/what-to-say-next-over-text/"):
                with self.subTest(agent=agent, path=path):
                    response = self.client.get(path, HTTP_USER_AGENT=agent)
                    self.assertNotContains(response, 'data-app-promo-placement="guide_primary"')
                    self.assertNotContains(response, 'data-app-promo-placement="hero"')
                    self.assertLess(response.content.index(b'id="chatForm"'), response.content.index(b'data-app-promo-placement="inline_card"'))
                    self.assertContains(response, 'id="chatForm"', count=1)

    def test_android_client_hint_selects_app_even_without_full_user_agent(self):
        response = self.client.get("/", HTTP_SEC_CH_UA_PLATFORM='"Android"')
        self.assertContains(response, 'data-app-promo-placement="hero"')


class ConversionReportTests(TestCase):
    def event(self, kind, at, *, user=None, journey=None, was_guest=True):
        event = WebConversionEvent.objects.create(kind=kind, journey_id=journey or self.journey,
            user=user, was_guest=was_guest, dedupe_key=str(uuid.uuid4()))
        WebConversionEvent.objects.filter(pk=event.pk).update(created_at=at)
        return event

    def payment(self, user, at, transaction="payment-1", provider="dodo"):
        p = CreditPurchase.objects.create(user=user, credits_purchased=10, amount_paid="1.99",
            payment_status="COMPLETED", payment_provider=provider, transaction_id=transaction)
        CreditPurchase.objects.filter(pk=p.pk).update(timestamp=at)

    def setUp(self):
        self.journey = uuid.uuid4()
        self.now = timezone.now()
        self.start = self.now - timedelta(days=10)
        self.user = User.objects.create_user("report", "report@example.com")

    def test_matched_mature_cohort_return_and_duplicate_purchase(self):
        for kind in ("generated", "copied", "signup", "checkout"):
            self.event(kind, self.start, user=self.user)
        self.event("generated", self.start + timedelta(days=2), user=self.user, was_guest=False, journey=uuid.uuid4())
        self.payment(self.user, self.start + timedelta(days=1))
        self.payment(self.user, self.start + timedelta(days=1))
        report = web_conversion_report(28, self.now)
        self.assertEqual(report["cohort_count"], 1)
        self.assertEqual(report["mature_count"], 1)
        self.assertTrue(all(r["mature_count"] == 1 for r in report["milestones"]))
        self.assertEqual(report["purchase_count"], 1)
        self.assertEqual(report["unmatched_buyers"], 0)

    def test_immature_cohort_staff_mobile_and_unmatched_purchases(self):
        self.event("generated", self.now - timedelta(days=1))
        staff = User.objects.create_user("staff", is_staff=True)
        self.event("generated", self.start, user=staff, journey=uuid.uuid4())
        self.payment(staff, self.start, "staff-payment")
        self.payment(self.user, self.start, "mobile-payment", "google_play")
        self.payment(self.user, self.start, "historical-payment")
        report = web_conversion_report(28, self.now)
        self.assertEqual(report["cohort_count"], 1)
        self.assertEqual(report["mature_count"], 0)
        self.assertIsNone(report["milestones"][0]["rate"])
        self.assertEqual(report["first_buyers"], 1)
        self.assertEqual(report["unmatched_buyers"], 1)

    def test_repeat_purchase_does_not_count_as_first_conversion(self):
        self.payment(self.user, self.start - timedelta(days=30), "old")
        self.event("generated", self.start, user=self.user)
        self.payment(self.user, self.start + timedelta(days=1), "repeat")
        report = web_conversion_report(28, self.now)
        self.assertEqual(report["purchase_count"], 1)
        self.assertEqual(report["first_buyers"], 0)
        self.assertEqual(report["milestones"][-1]["count"], 0)

    def test_admin_access_and_period_validation(self):
        url = reverse("admin:conversation_webconversionevent_report")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        for days in (7, 28, 90):
            self.assertEqual(self.client.get(url, {"days": days}).status_code, 200)
        self.assertEqual(self.client.get(url, {"days": 8}).status_code, 400)
