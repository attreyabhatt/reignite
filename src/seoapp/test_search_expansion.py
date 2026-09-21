import json
import re
from html.parser import HTMLParser
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.html import escape

from seoapp.management.commands.seed_pickup_data import SEED_MODULES
from seoapp.models import PickupCategory, PickupTopic
from seoapp.seed_data.search_expansion import NEW_PICKUP_TOPICS, PICKUP_EXPANSION
from seoapp.seed_data.search_refresh import PICKUP_REFRESH
from seoapp.situation_expansion import NEW_SITUATION_PAGES, SITUATION_INCOMING_LINKS


class PageElements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.links = []
        self.app_links = {}
        self.canonicals = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            if "data-app-promo-placement" in attrs:
                self.app_links[attrs["data-app-promo-placement"]] = attrs["href"]
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))


@override_settings(SECURE_SSL_REDIRECT=False)
class SearchExpansionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pickup_data", stdout=StringIO())

    def remove_new_topics(self):
        for category, slug in NEW_PICKUP_TOPICS:
            PickupTopic.objects.filter(category__slug=category, slug=slug).delete()

    def snapshot(self):
        return list(PickupTopic.objects.order_by("pk").values())

    def test_seed_appends_six_topics_without_reordering_existing_content(self):
        for module in SEED_MODULES:
            for order, fields in enumerate(module.DATA["topics"]):
                topic = PickupTopic.objects.get(category__slug=module.DATA["category_slug"], slug=fields["slug"])
                self.assertEqual(topic.sort_order, order)
        expected = sum(len(module.DATA["topics"]) for module in SEED_MODULES) + 6
        self.assertEqual(PickupTopic.objects.count(), expected)
        before = list(PickupTopic.objects.order_by("pk").values_list("category__slug", "slug", "sort_order"))
        call_command("seed_pickup_data", stdout=StringIO())
        self.assertEqual(before, list(PickupTopic.objects.order_by("pk").values_list("category__slug", "slug", "sort_order")))

    def test_all_eighteen_pages_render_content_tools_metadata_and_app_attribution(self):
        pages = [
            (reverse("pickup_line_detail", args=key), fields, "just_matched", "pickup_lines")
            for key, fields in {**NEW_PICKUP_TOPICS, **PICKUP_EXPANSION}.items()
        ] + [
            (reverse("situation_landing", args=[slug]), fields, fields["situation"], "texting_guides")
            for slug, fields in NEW_SITUATION_PAGES.items()
        ]
        self.assertEqual(len(pages), 18)
        for path, fields, scenario, group in pages:
            with self.subTest(path=path):
                response = self.client.get(path, {"private_query": "not-for-tracking"})
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertIn(escape(fields["guide_content"]["answer"]), html)
                self.assertIn(f'<option value="{scenario}" selected>', html)
                self.assertIn("Illustrative examples", html)
                self.assertIn('id="playground"', html)
                self.assertIn("data-android-app-bar hidden", html)
                elements = PageElements(html)
                self.assertEqual(elements.canonicals, ["https://www.tryagaintext.com" + path])
                self.assertEqual(len(elements.ids), len(set(elements.ids)))
                for section in fields["guide_content"]["sections"]:
                    self.assertIn(escape(section["heading"]), html)
                    for item in section["examples"]:
                        self.assertIn(escape(item["why"]), html)
                self.assertTrue({"inline_card", "android_bar", "footer"} <= elements.app_links.keys())
                for placement, href in elements.app_links.items():
                    url = urlparse(href)
                    self.assertEqual(url.path, "/flirtfix")
                    query = parse_qs(url.query)
                    self.assertEqual(query["utm_term"], [path])
                    self.assertEqual(query["utm_campaign"], [f"flirtfix_web_{group}"])
                    self.assertEqual(query["utm_content"], [placement])
                    self.assertNotIn("not-for-tracking", href)
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
                self.assertEqual(len(blocks), 1)
                breadcrumb = json.loads(blocks[0])
                self.assertEqual(breadcrumb["itemListElement"][-1]["item"], "https://www.tryagaintext.com" + path)

    def test_new_pickup_lines_are_distinct_and_render_once(self):
        all_lines = []
        for key, fields in NEW_PICKUP_TOPICS.items():
            with self.subTest(key=key):
                html = self.client.get(reverse("pickup_line_detail", args=key)).content.decode()
                for field in ("witty_lines", "flirty_lines", "cheesy_lines"):
                    self.assertEqual(len(fields[field]), 5)
                    for line in fields[field]:
                        self.assertEqual(html.count(escape(line)), 1, line)
                        all_lines.append(line)
                self.assertEqual(len(fields["guide_content"]["sections"][3]["examples"]), 3)
        self.assertEqual(len(all_lines), 90)
        self.assertEqual(len(set(all_lines)), 90)

    def test_new_pages_are_in_sitemap_directories_and_relevant_incoming_links(self):
        sitemap = self.client.get(reverse("sitemap_xml")).content.decode()
        directory = PageElements(self.client.get(reverse("situation_index")).content.decode())
        for slug in NEW_SITUATION_PAGES:
            path = reverse("situation_landing", args=[slug])
            self.assertIn(path, directory.links)
            self.assertIn(f"<loc>https://www.tryagaintext.com{path}</loc>", sitemap)
        for key in NEW_PICKUP_TOPICS:
            path = reverse("pickup_line_detail", args=key)
            self.assertIn(f"<loc>https://www.tryagaintext.com{path}</loc>", sitemap)
            category = self.client.get(reverse("pickup_category_detail", args=[key[0]]))
            self.assertIn(path, PageElements(category.content.decode()).links)
            self.assertIn(key[1], [topic["topic_slug"] for topic in category.context["featured_topics"]])
            response = self.client.get(path)
            siblings = [topic["topic_slug"] for topic in response.context["featured_topics"]]
            self.assertEqual(set(siblings), {slug for category, slug in NEW_PICKUP_TOPICS if category == key[0] and slug != key[1]})
            self.assertIn("how-to-reply-to-a-pickup-line", [page["slug"] for page in response.context["next_step_guides"]])
        for parent, children in SITUATION_INCOMING_LINKS.items():
            response = self.client.get(reverse("situation_landing", args=[parent]))
            related = [page["slug"] for page in response.context["related_pages"]]
            for slug in children:
                self.assertIn(slug, related)
        for key, child in [
            (("dating-apps", "instagram-dm-opener"), "how-to-reply-to-instagram-story"),
            (("dating-apps", "tinder-opener"), "dating-app-openers-with-no-bio"),
        ]:
            response = self.client.get(reverse("pickup_line_detail", args=key))
            self.assertIn(child, [page["slug"] for page in response.context["next_step_guides"]])

    def test_inactive_new_topics_are_not_featured_or_linked_as_siblings(self):
        PickupTopic.objects.filter(category__slug="hobbies", slug="tennis").update(is_active=False)
        path = reverse("pickup_line_detail", args=["hobbies", "tennis"])
        for source in ["/pickup-lines/hobbies/", "/pickup-lines/hobbies/badminton/"]:
            self.assertNotIn(path, PageElements(self.client.get(source).content.decode()).links)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_expansion_dry_run_writes_nothing(self):
        self.remove_new_topics()
        before = self.snapshot()
        output = StringIO()
        call_command("refresh_search_content", batch="expansion", dry_run=True, stdout=output)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(output.getvalue().count("Would refresh"), 4)
        self.assertEqual(output.getvalue().count("Would create"), 6)

    def test_expansion_creates_missing_topics_preserves_edits_and_appends_after_custom_order(self):
        self.remove_new_topics()
        hobby = PickupCategory.objects.get(slug="hobbies")
        existing = PickupTopic.objects.create(category=hobby, slug="tennis", title="My edited tennis guide", sort_order=999, is_active=False)
        for category, slug in PICKUP_EXPANSION:
            PickupTopic.objects.filter(category__slug=category, slug=slug).update(title="Old editorial title")
        PickupTopic.objects.filter(category__slug="professions", slug="lawyer").update(title="Preserve my priority edit")
        PickupTopic.objects.filter(category__slug="professions", slug="nurse").update(title="Preserve my unrelated edit")
        protected = list(PickupTopic.objects.filter(title__startswith="Preserve my").order_by("pk").values())
        existing_before = PickupTopic.objects.filter(pk=existing.pk).values().get()
        for _ in range(2):
            output = StringIO()
            call_command("refresh_search_content", batch="expansion", stdout=output)
            self.assertIn("Skipped existing hobbies/tennis", output.getvalue())
        self.assertEqual(existing_before, PickupTopic.objects.filter(pk=existing.pk).values().get())
        self.assertEqual(protected, list(PickupTopic.objects.filter(title__startswith="Preserve my").order_by("pk").values()))
        self.assertEqual(PickupTopic.objects.get(category=hobby, slug="badminton").sort_order, 1000)
        self.assertEqual(PickupTopic.objects.get(category=hobby, slug="pickleball").sort_order, 1001)
        for key, fields in PICKUP_EXPANSION.items():
            topic = PickupTopic.objects.get(category__slug=key[0], slug=key[1])
            self.assertEqual(topic.title, fields["title"])
        for category, slug in NEW_PICKUP_TOPICS:
            self.assertEqual(PickupTopic.objects.filter(category__slug=category, slug=slug).count(), 1)

    def test_missing_category_or_refresh_target_aborts_the_batch(self):
        for missing_kind in ("category", "target"):
            with self.subTest(missing_kind=missing_kind):
                # Each failure is tested against a complete baseline.
                call_command("seed_pickup_data", stdout=StringIO())
                self.remove_new_topics()
                if missing_kind == "category":
                    PickupCategory.objects.get(slug="hobbies").delete()
                else:
                    PickupTopic.objects.get(category__slug="fandoms", slug="lord-of-the-rings").delete()
                before = self.snapshot()
                for dry_run in (True, False):
                    with self.assertRaises(CommandError):
                        call_command("refresh_search_content", batch="expansion", dry_run=dry_run, stdout=StringIO())
                    self.assertEqual(before, self.snapshot())

    def test_failure_during_creation_rolls_back_refreshes_and_earlier_inserts(self):
        self.remove_new_topics()
        PickupTopic.objects.filter(category__slug="dating-apps", slug="tinder-opener").update(title="Before failed batch")
        before = self.snapshot()
        original_save = PickupTopic.save

        def fail_on_second_topic(topic, *args, **kwargs):
            if topic.slug == "badminton":
                raise RuntimeError("Simulated interrupted publication")
            return original_save(topic, *args, **kwargs)

        with patch.object(PickupTopic, "save", fail_on_second_topic):
            with self.assertRaisesRegex(RuntimeError, "interrupted publication"):
                call_command("refresh_search_content", batch="expansion", stdout=StringIO())
        self.assertEqual(before, self.snapshot())

    def test_default_command_keeps_its_original_three_page_scope(self):
        self.remove_new_topics()
        before = self.snapshot()
        output = StringIO()
        call_command("refresh_search_content", stdout=output)
        self.assertEqual(output.getvalue().count("Refreshed"), len(PICKUP_REFRESH))
        after = self.snapshot()
        allowed = {PickupTopic.objects.get(category__slug=category, slug=slug).pk for category, slug in PICKUP_REFRESH}
        self.assertEqual([row for row in before if row["id"] not in allowed], [row for row in after if row["id"] not in allowed])
        for category, slug in NEW_PICKUP_TOPICS:
            self.assertFalse(PickupTopic.objects.filter(category__slug=category, slug=slug).exists())
