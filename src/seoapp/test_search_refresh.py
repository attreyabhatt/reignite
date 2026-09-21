import json
import re
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.html import escape

from seoapp.models import PickupTopic
from seoapp.seed_data.search_refresh import PICKUP_REFRESH


@override_settings(SECURE_SSL_REDIRECT=False)
class SearchRefreshTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pickup_data", stdout=StringIO())

    def test_editorial_pages_answer_intent_and_keep_relevant_tools(self):
        for (category, slug), content in PICKUP_REFRESH.items():
            with self.subTest(slug=slug):
                response = self.client.get(reverse("pickup_line_detail", args=[category, slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, escape(content["guide_content"]["answer"]))
                self.assertContains(response, "Illustrative examples")
                self.assertContains(response, "They replied. What comes next?")
                if slug == "hinge-prompt-answers":
                    self.assertContains(response, "your own Hinge profile")
                    self.assertNotContains(response, "When a girl asks you")
                    self.assertNotContains(response, 'id="playground"')
                else:
                    self.assertContains(response, 'id="playground"')

    def test_refresh_is_targeted_repeatable_and_supports_dry_run(self):
        other = PickupTopic.objects.get(category__slug="professions", slug="nurse")
        other.title = "Locally edited nurse title"
        other.save()
        target = PickupTopic.objects.get(category__slug="professions", slug="lawyer")
        target.title = "Previous lawyer title"
        target.save()
        call_command("refresh_search_content", dry_run=True, stdout=StringIO())
        target.refresh_from_db()
        self.assertEqual(target.title, "Previous lawyer title")
        for _ in range(2):
            call_command("refresh_search_content", stdout=StringIO())
        target.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(target.title, PICKUP_REFRESH[("professions", "lawyer")]["title"])
        self.assertEqual(other.title, "Locally edited nurse title")

    def test_internal_links_do_not_feature_inactive_topics(self):
        PickupTopic.objects.filter(category__slug="hobbies", slug="pilates").update(is_active=False)
        for path in ["/", "/pickup-lines/", "/pickup-lines/hobbies/"]:
            response = self.client.get(path)
            self.assertNotContains(response, 'href="/pickup-lines/hobbies/pilates/"')
        self.assertContains(self.client.get("/"), 'href="/pickup-lines/professions/lawyer/"')

    def test_breadcrumb_json_handles_quotes_and_script_like_titles(self):
        topic = PickupTopic.objects.get(category__slug="professions", slug="lawyer")
        topic.keyword = 'Lawyer "quotes" </script><script>alert(1)</script>'
        topic.save()
        response = self.client.get("/pickup-lines/professions/lawyer/")
        html = response.content.decode()
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        self.assertEqual(len(blocks), 1)
        data = json.loads(blocks[0])
        self.assertEqual(data["itemListElement"][-1]["name"], topic.keyword)
        self.assertNotIn("</script>", blocks[0])
        self.assertTrue(all(item["item"].startswith("https://www.tryagaintext.com/") for item in data["itemListElement"]))

    def test_campaign_labels_survive_landing_page_cta(self):
        response = self.client.get("/pickup-lines/professions/lawyer/", {
            "utm_source": "instagram", "utm_medium": "organic_social",
            "utm_campaign": "flirtfix_reach_2026_09", "utm_content": "video06",
        })
        self.assertContains(response, "utm_source=instagram")
        self.assertContains(response, "utm_content=video06_inline_card")
        self.assertContains(response, "utm_content=video06_android_bar")
        self.assertContains(response, '<link rel="canonical" href="https://www.tryagaintext.com/pickup-lines/professions/lawyer/">')

    def test_arbitrary_tracking_input_is_not_carried_into_ctas(self):
        response = self.client.get("/", {"utm_source": "private-input", "utm_content": "private-message"})
        self.assertNotContains(response, "private-input")
        self.assertNotContains(response, "private-message")
