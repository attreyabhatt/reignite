from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from reignitehome.models import MarketingClickEvent
from seoapp.models import PickupCategory, PickupTopic
from seoapp.situation_pages import list_situation_pages


class AppLinkParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "data-app-promo-placement" in attrs:
            self.links[attrs["data-app-promo-placement"]] = attrs["href"]


@override_settings(SECURE_SSL_REDIRECT=False)
class AndroidAppPromotionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = PickupCategory.objects.create(slug="books", name="Books")
        cls.topic = PickupTopic.objects.create(
            category=category,
            slug="book-lovers",
            keyword="Book lovers",
            h1="Pickup lines for book lovers",
            title="Book lovers pickup lines",
            witty_lines=["A witty opener"],
            flirty_lines=["A flirty opener"],
            cheesy_lines=["A cheesy opener"],
        )

    def test_discovery_pages_offer_attributed_app_links_without_javascript(self):
        pages = [
            (reverse("home"), "home"),
            (reverse("pickup_lines_index"), "pickup_lines"),
            (reverse("pickup_category_detail", args=["books"]), "pickup_lines"),
            (reverse("pickup_line_detail", args=["books", self.topic.slug]), "pickup_lines"),
            (reverse("situation_index"), "texting_guides"),
            *[(reverse("situation_landing", args=[page["slug"]]), "texting_guides")
              for page in list_situation_pages()],
        ]
        for path, group in pages:
            with self.subTest(path=path):
                response = self.client.get(path, {"private_query": "do-not-track"})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "FlirtFix &middot; Our Android app")
                self.assertContains(response, "data-android-app-bar hidden")
                links = AppLinkParser(response.content.decode()).links
                self.assertTrue({"inline_card", "android_bar", "footer"} <= links.keys())
                if group == "home":
                    self.assertIn("hero", links)
                for placement, href in links.items():
                    parsed = urlparse(href)
                    self.assertEqual(parsed.path, reverse("flirtfix_redirect"))
                    query = parse_qs(parsed.query)
                    self.assertEqual(query["utm_source"], ["website"])
                    self.assertEqual(query["utm_medium"], ["home_cta" if group == "home" else "web_cta"])
                    self.assertEqual(query["utm_campaign"], [f"flirtfix_web_{group}"])
                    self.assertEqual(query["utm_term"], [path])
                    self.assertEqual(query["utm_content"], [placement])
                    self.assertNotIn("do-not-track", href)

    def test_app_attribution_survives_redirect_into_play_install_referrer(self):
        response = self.client.get(reverse("pickup_line_detail", args=["books", self.topic.slug]))
        href = AppLinkParser(response.content.decode()).links["inline_card"]
        response = self.client.get(href, HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14)")
        self.assertEqual(response.status_code, 302)
        destination = urlparse(response["Location"])
        self.assertEqual(destination.netloc, "play.google.com")
        query = parse_qs(destination.query)
        self.assertEqual(query["id"], ["com.tryagaintext.flirtfix"])
        referrer = parse_qs(query["referrer"][0])
        self.assertEqual(referrer["utm_campaign"], ["flirtfix_web_pickup_lines"])
        self.assertEqual(referrer["utm_content"], ["inline_card"])
        self.assertEqual(referrer["utm_term"], ["/pickup-lines/books/book-lovers/"])
        click = MarketingClickEvent.objects.get()
        self.assertEqual(referrer["ffclid"], [str(click.click_id)])

    def test_signed_in_web_app_offers_the_android_bar(self):
        user = get_user_model().objects.create_user(username="app-promo-test")
        self.client.force_login(user)
        response = self.client.get(reverse("conversation_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-android-app-bar hidden")
        links = AppLinkParser(response.content.decode()).links
        query = parse_qs(urlparse(links["android_bar"]).query)
        self.assertEqual(query["utm_campaign"], ["flirtfix_web_conversations"])

    def test_login_and_policy_pages_do_not_show_install_bar(self):
        for name in ["account_login", "privacy_policy"]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "data-android-app-bar")
                self.assertNotContains(response, "js/android_app_promo.js")
