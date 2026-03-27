import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from reignitehome.views import DEFAULT_TOOL_CONVERSATION_PLACEHOLDER
from seoapp.pickup_pages import list_pickup_topics
from seoapp.situation_pages import SITUATION_PAGE_ORDER, list_situation_pages

class SituationSeoPagesTests(TestCase):
    def test_situations_directory_returns_200_and_links_to_all_situations(self):
        response = self.client.get(reverse("situation_index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All Scenario Guides")

        for page in list_situation_pages():
            expected_href = reverse("situation_landing", kwargs={"slug": page["slug"]})
            self.assertContains(response, f'href="{expected_href}"', html=False)

    def test_all_situation_pages_render_with_expected_ui_defaults(self):
        for page in list_situation_pages():
            with self.subTest(slug=page["slug"]):
                response = self.client.get(
                    reverse("situation_landing", kwargs={"slug": page["slug"]})
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, escape(page["h1"]))
                self.assertContains(
                    response,
                    f'<option value="{page["situation"]}" selected>',
                    html=False,
                )
                self.assertContains(response, 'id="last-reply"', html=False)
                self.assertNotContains(response, escape(page["prefill_text"]))
                self.assertContains(response, 'data-tool-variant="pickup"', html=False)
                self.assertContains(response, 'id="playground"', html=False)

    def test_each_situation_page_renders_structured_seo_sections(self):
        for page in list_situation_pages():
            with self.subTest(slug=page["slug"]):
                response = self.client.get(
                    reverse("situation_landing", kwargs={"slug": page["slug"]})
                )
                self.assertEqual(response.status_code, 200)
                self.assertGreaterEqual(len(page["seo_sections"]), 4)
                self.assertContains(response, escape(page["seo_sections"][0]["heading"]))
                self.assertContains(response, escape(page["seo_sections"][1]["heading"]))
                self.assertContains(response, escape(page["seo_sections"][2]["heading"]))
                self.assertContains(response, '<ul class="seo-rules">', html=False)
                self.assertContains(response, "Pro Tip:")
                self.assertContains(response, escape(page["screenshot_tip"]))
                rendered_html = response.content.decode("utf-8")
                seo_subheading_count = len(re.findall(r"<h2>[^<]+</h2>", rendered_html))
                self.assertGreaterEqual(seo_subheading_count, 3)

                section_2_heading = escape(page["seo_sections"][1]["heading"])
                section_3_heading = escape(page["seo_sections"][2]["heading"])
                section_2_index = rendered_html.find(section_2_heading)
                pro_tip_index = rendered_html.find("Pro Tip:")
                section_3_index = rendered_html.find(section_3_heading)
                self.assertNotEqual(section_2_index, -1)
                self.assertNotEqual(pro_tip_index, -1)
                self.assertNotEqual(section_3_index, -1)
                self.assertGreater(pro_tip_index, section_2_index)
                self.assertLess(pro_tip_index, section_3_index)

                rules = page["seo_sections"][1].get("bullets", [])
                self.assertEqual(len(rules), 3)
                for rule in rules:
                    self.assertContains(response, escape(rule))

    def test_sidebar_uses_short_manual_labels_for_all_situations(self):
        anchor_response = self.client.get(
            reverse("situation_landing", kwargs={"slug": list_situation_pages()[0]["slug"]})
        )
        self.assertEqual(anchor_response.status_code, 200)

        for page in list_situation_pages():
            expected_href = reverse("situation_landing", kwargs={"slug": page["slug"]})
            self.assertContains(anchor_response, f'href="{expected_href}"', html=False)
            self.assertContains(anchor_response, escape(page["sidebar_label"]))
            label_words = [word for word in page["sidebar_label"].split() if word]
            self.assertGreaterEqual(len(label_words), 2)
            self.assertLessEqual(len(label_words), 4)

    def test_related_guides_links_render_on_each_situation_page(self):
        for page in list_situation_pages():
            with self.subTest(slug=page["slug"]):
                response = self.client.get(
                    reverse("situation_landing", kwargs={"slug": page["slug"]})
                )
                self.assertContains(response, "Related Situation Guides")
                for related_slug in page["related_slugs"]:
                    related_href = reverse("situation_landing", kwargs={"slug": related_slug})
                    self.assertContains(response, f'href="{related_href}"', html=False)

    def test_unknown_situation_slug_returns_404(self):
        response = self.client.get("/situations/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_sitemap_contains_public_urls_and_all_situations(self):
        response = self.client.get(reverse("sitemap_xml"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")

        expected_core_urls = [
            "http://testserver/",
            "http://testserver/situations/",
            "http://testserver/pricing/",
            "http://testserver/privacy-policy/",
            "http://testserver/terms/",
            "http://testserver/refund-policy/",
            "http://testserver/contact/",
            "http://testserver/safety-standards/",
            "http://testserver/policy/screenclean/",
        ]

        for absolute_url in expected_core_urls:
            self.assertContains(response, f"<loc>{absolute_url}</loc>", html=False)

        for slug in SITUATION_PAGE_ORDER:
            self.assertContains(
                response,
                f"<loc>http://testserver/situations/{slug}/</loc>",
                html=False,
            )

    def test_robots_includes_sitemap_line_and_existing_disallow_rules(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User-agent: *")
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /accounts/")
        self.assertContains(response, "Sitemap: https://tryagaintext.com/sitemap.xml")

    def test_situation_page_seo_head_includes_canonical_and_meta_description(self):
        page = list_situation_pages()[0]
        response = self.client.get(
            reverse("situation_landing", kwargs={"slug": page["slug"]})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<link rel="canonical" href="http://testserver/situations/{page["slug"]}/">',
            html=False,
        )
        self.assertContains(
            response,
            f'<meta name="description" content="{page["meta_description"]}">',
            html=False,
        )

    def test_situations_directory_seo_head_has_canonical_and_meta(self):
        response = self.client.get(reverse("situation_index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<link rel="canonical" href="http://testserver/situations/">',
            html=False,
        )
        self.assertContains(
            response,
            '<meta name="description" content="Explore texting guides for every dating app scenario, from dry replies to asking for dates. Open the exact guide and generate send-ready responses.">',
            html=False,
        )

    def test_home_no_longer_renders_situations_grid(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Browse All Situations")
        self.assertNotContains(response, "All Scenario Guides")

    def test_footer_contains_texting_guides_link_on_home_and_situation_pages(self):
        home_response = self.client.get(reverse("home"))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'href="/situations/"', html=False)
        self.assertContains(home_response, "Texting Guides")
        self.assertContains(home_response, 'href="/pickup-lines/"', html=False)
        self.assertContains(home_response, "Pickup Lines")

        page = list_situation_pages()[0]
        situation_response = self.client.get(
            reverse("situation_landing", kwargs={"slug": page["slug"]})
        )
        self.assertEqual(situation_response.status_code, 200)
        self.assertContains(situation_response, 'href="/situations/"', html=False)
        self.assertContains(situation_response, "Texting Guides")
        self.assertContains(situation_response, 'href="/pickup-lines/"', html=False)
        self.assertContains(situation_response, "Pickup Lines")

    def test_each_situation_seo_body_word_count_is_in_target_range(self):
        for page in list_situation_pages():
            with self.subTest(slug=page["slug"]):
                text_parts = [page.get("screenshot_tip", "")]
                for section in page.get("seo_sections", []):
                    text_parts.extend(section.get("paragraphs", []))
                    text_parts.extend(section.get("bullets", []))

                text = re.sub(r"<[^>]+>", " ", " ".join(text_parts))
                words = [word for word in re.split(r"\s+", text.strip()) if word]
                self.assertGreaterEqual(len(words), 400)
                self.assertLessEqual(len(words), 600)

    def test_home_and_situation_pages_render_shared_reply_tool_marker(self):
        home_response = self.client.get(reverse("home"))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'data-reply-tool-shared="1"', html=False)
        self.assertContains(home_response, 'id="playground"', html=False)
        self.assertContains(home_response, 'data-tool-variant="pickup"', html=False)
        self.assertContains(
            home_response,
            '<link rel="stylesheet" href="/static/css/pickup_playground.css">',
            html=False,
        )

        first_situation = list_situation_pages()[0]
        situation_response = self.client.get(
            reverse("situation_landing", kwargs={"slug": first_situation["slug"]})
        )
        self.assertEqual(situation_response.status_code, 200)
        self.assertContains(situation_response, 'data-reply-tool-shared="1"', html=False)
        self.assertContains(situation_response, 'id="playground"', html=False)
        self.assertContains(situation_response, 'data-tool-variant="pickup"', html=False)
        self.assertContains(
            situation_response,
            '<link rel="stylesheet" href="/static/css/pickup_playground.css">',
            html=False,
        )

    def test_pickup_pages_render_with_shared_tool_and_just_matched_defaults(self):
        index_response = self.client.get(reverse("pickup_lines_index"))
        self.assertEqual(index_response.status_code, 200)
        self.assertContains(index_response, "Ultra-Niche Pickup Line Guides")

        topic = list_pickup_topics()[0]
        detail_response = self.client.get(
            reverse(
                "pickup_line_detail",
                kwargs={
                    "category_slug": topic["category_slug"],
                    "topic_slug": topic["topic_slug"],
                },
            )
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'data-reply-tool-shared="1"', html=False)
        self.assertContains(detail_response, 'data-tool-variant="pickup"', html=False)
        self.assertContains(detail_response, 'id="playground"', html=False)
        self.assertContains(detail_response, "pickup-playground")
        self.assertContains(detail_response, "pickup-tool-shell")
        self.assertContains(detail_response, 'data-force-show-upload="1"', html=False)
        self.assertContains(
            detail_response,
            'id="screenshot-upload" class="pickup-form-section pickup-upload-shell is-emphasis"',
            html=False,
        )
        self.assertContains(
            detail_response,
            'id="conversation-paste-area" class="pickup-form-section hidden"',
            html=False,
        )
        self.assertContains(
            detail_response,
            'id="her-info-div" class="pickup-form-section"',
            html=False,
        )
        self.assertContains(
            detail_response,
            '<option value="just_matched" selected>',
            html=False,
        )
        self.assertContains(detail_response, 'href="/"', html=False)
        self.assertContains(detail_response, 'href="/pickup-lines/"', html=False)
        self.assertNotContains(detail_response, escape(topic["prefill_text"]))
        self.assertContains(detail_response, 'id="last-reply"', html=False)
        self.assertContains(
            detail_response,
            escape(DEFAULT_TOOL_CONVERSATION_PLACEHOLDER),
        )
        self.assertContains(
            detail_response,
            'id="last-reply"',
            html=False,
        )
        self.assertContains(detail_response, escape(topic["upload_hint"]))
        self.assertContains(detail_response, "data-upload-hint-text", html=False)
        self.assertContains(detail_response, escape(topic["her_info_prefill"]))
        self.assertContains(detail_response, "pickup-empty-state")
        self.assertContains(
            detail_response,
            '<script src="/static/js/web_reply_ui.js"></script>',
            html=False,
        )

    def test_pickup_detail_uses_shared_pickup_playground_css_with_chip_rules(self):
        topic = list_pickup_topics()[0]
        response = self.client.get(
            reverse(
                "pickup_line_detail",
                kwargs={
                    "category_slug": topic["category_slug"],
                    "topic_slug": topic["topic_slug"],
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<link rel="stylesheet" href="/static/css/pickup_playground.css">',
            html=False,
        )

        css_path = Path(settings.BASE_DIR) / "static" / "css" / "pickup_playground.css"
        self.assertTrue(css_path.exists())
        css_content = css_path.read_text(encoding="utf-8")
        self.assertIn('[data-tool-variant="pickup"] .pickup-tool-inputs {', css_content)
        self.assertIn("align-content: start;", css_content)
        self.assertIn('[data-tool-variant="pickup"] .pickup-situation-grid > * {', css_content)
        self.assertIn("grid-auto-rows: max-content;", css_content)
        self.assertIn("min-height: 2.55rem;", css_content)
        self.assertIn(
            '[data-tool-variant="pickup"] .pickup-more-select.more-scenarios-select {',
            css_content,
        )
        self.assertIn("font-size: .74rem;", css_content)
        self.assertIn("font-weight: 600;", css_content)
        self.assertIn("line-height: 1.2;", css_content)

    def test_situation_pages_include_shared_pickup_playground_css(self):
        response = self.client.get(
            reverse("situation_landing", kwargs={"slug": list_situation_pages()[0]["slug"]})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<link rel="stylesheet" href="/static/css/pickup_playground.css">',
            html=False,
        )

    def test_spark_interest_situation_keeps_her_information_hidden_initially(self):
        spark_page = next(
            page for page in list_situation_pages() if page["situation"] == "spark_interest"
        )
        response = self.client.get(
            reverse("situation_landing", kwargs={"slug": spark_page["slug"]})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-tool-variant="pickup"', html=False)
        self.assertContains(response, 'id="playground"', html=False)
        self.assertContains(
            response,
            'id="her-info-div" class="pickup-form-section hidden"',
            html=False,
        )
        self.assertContains(
            response,
            'id="screenshot-upload" class="pickup-form-section pickup-upload-shell"',
            html=False,
        )
        self.assertContains(
            response,
            'id="conversation-paste-area" class="pickup-form-section"',
            html=False,
        )


