import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.etree import ElementTree

from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.html import escape

from seoapp.models import PickupTopic
from seoapp.organic_guides import NEW_GUIDES, editorial_metadata
from seoapp.checks import publication_settings
from seoapp.situation_pages import list_situation_pages
from seoapp.test_search_expansion import PageElements


@override_settings(SEO_GUIDES_PUBLISHED_ON="")
class OrganicGrowthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pickup_data", stdout=StringIO())

    def test_all_new_guides_render_examples_links_metadata_and_web_first(self):
        self.assertEqual(len(NEW_GUIDES), 12)
        for slug, page in NEW_GUIDES.items():
            with self.subTest(slug=slug):
                response = self.client.get(reverse("situation_landing", args=[slug]),
                    HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14)")
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                parser = PageElements(html)
                self.assertEqual(parser.canonicals, ["https://www.tryagaintext.com" + response.wsgi_request.path])
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                examples = [item for group in page["guide_content"]["sections"][:3] for item in group["examples"]]
                self.assertGreaterEqual(len(examples), 10)
                self.assertEqual(len({item["text"] for item in examples}), len(examples))
                self.assertEqual(len(page["guide_content"]["sections"][3]["examples"]), 2)
                for item in examples:
                    self.assertIn(escape(item["text"]), html)
                    self.assertIn(escape(item["why"]), html)
                self.assertLess(html.index(escape(page["guide_content"]["answer"])), html.index('id="web-tool"'))
                self.assertLess(html.index('id="chatForm"'), html.index('data-app-promo-placement="inline_card"'))
                self.assertIn('How these examples are prepared', html)
                self.assertGreaterEqual(html.count('class="guide-context-link"'), 3)
                self.assertIn('"@type": "Article"', html)
                self.assertIn(f'<option value="{page["situation"]}" selected>', html)

    def test_all_guides_are_available_together_and_old_schedule_cannot_hide_them(self):
        with override_settings(SEO_GUIDE_ROLLOUT_START="2099-01-01"):
            directory = self.client.get(reverse("situation_index"))
            sitemap = self.client.get(reverse("sitemap_xml"))
            for slug in NEW_GUIDES:
                self.assertEqual(self.client.get(reverse("situation_landing", args=[slug])).status_code, 200)
                self.assertContains(directory, f'/situations/{slug}/')
                self.assertContains(sitemap, f'/situations/{slug}/')

    def test_publication_metadata_is_optional_and_shared_by_all_new_guides(self):
        for page in NEW_GUIDES.values():
            self.assertIsNone(editorial_metadata(page)['date_published'])
        self.assertEqual(publication_settings(None), [])
        with override_settings(SEO_GUIDES_PUBLISHED_ON="2026-10-27"):
            for page in NEW_GUIDES.values():
                self.assertEqual(editorial_metadata(page)['date_published'], '2026-10-27')
            self.assertEqual(publication_settings(None), [])
        with override_settings(SEO_GUIDES_PUBLISHED_ON="invalid"):
            self.assertEqual(publication_settings(None)[0].id, 'seoapp.E001')

    def test_release_manifest_has_no_schedule(self):
        output = StringIO()
        call_command('seo_rollout', json=True, stdout=output)
        manifest = json.loads(output.getvalue())
        self.assertEqual(manifest['publication_mode'], 'all_at_once')
        self.assertEqual(len(manifest['guides']), 12)
        self.assertEqual({row['status'] for row in manifest['guides']}, {'available'})
        self.assertTrue(all(row['date_published'] is None for row in manifest['guides']))

    def test_directory_and_two_established_guides_link_to_every_new_page(self):
        directory = self.client.get('/situations/').content.decode()
        for title in ('Everyday replies', 'Warm and flirty replies', 'Dating plans and intentions'):
            self.assertIn(title, directory)
        old_pages = [p for p in list_situation_pages() if p['slug'] not in NEW_GUIDES]
        for slug in NEW_GUIDES:
            self.assertIn(f'/situations/{slug}/', directory)
            incoming = sum(slug in p['related_slugs'] for p in old_pages)
            self.assertGreaterEqual(incoming, 2)

    def test_consolidation_and_sitemap_dates_are_stable(self):
        response = self.client.get('/situations/what-to-text-after-a-date/')
        self.assertRedirects(response, 'https://www.tryagaintext.com/situations/what-to-text-after-first-date/', status_code=301, fetch_redirect_response=False)
        xml = self.client.get('/sitemap.xml').content
        root = ElementTree.fromstring(xml)
        entries = {row.find('{*}loc').text: row.find('{*}lastmod') for row in root}
        self.assertNotIn('https://www.tryagaintext.com/situations/what-to-text-after-a-date/', entries)
        self.assertIn('https://www.tryagaintext.com/about/', entries)
        self.assertEqual(entries['https://www.tryagaintext.com/situations/what-to-say-next-over-text/'].text, '2026-10-27')
        self.assertEqual(xml, self.client.get('/sitemap.xml').content)

    def test_organic_publisher_dry_run_backup_restore_and_preserves_later_edits(self):
        topic = PickupTopic.objects.get(category__slug='hobbies', slug='fishing')
        unrelated = PickupTopic.objects.get(category__slug='hobbies', slug='cooking')
        unrelated.title = 'Admin text to preserve'
        unrelated.save()
        topic.title = 'Before publication'
        topic.save()
        with TemporaryDirectory() as folder:
            backup = Path(folder) / 'before.json'
            call_command('refresh_search_content', batch='organic', dry_run=True, backup=backup, stdout=StringIO())
            self.assertFalse(backup.exists())
            with self.assertRaises(CommandError):
                call_command('refresh_search_content', batch='organic', stdout=StringIO())
            call_command('refresh_search_content', batch='organic', backup=backup, stdout=StringIO())
            topic.refresh_from_db()
            self.assertNotEqual(topic.title, 'Before publication')
            topic.title = 'Subsequent admin edit'
            topic.save()
            call_command('refresh_search_content', batch='organic', backup=Path(folder) / 'second.json', stdout=StringIO())
            topic.refresh_from_db()
            self.assertEqual(topic.title, 'Subsequent admin edit')
            call_command('refresh_search_content', batch='organic', restore=backup, stdout=StringIO())
            topic.refresh_from_db()
            self.assertEqual(topic.title, 'Before publication')
            bad = json.loads(backup.read_text())
            bad['topics'][0]['fields']['is_active'] = False
            invalid = Path(folder) / 'invalid.json'
            invalid.write_text(json.dumps(bad))
            with self.assertRaises(CommandError):
                call_command('refresh_search_content', batch='organic', restore=invalid, stdout=StringIO())
        unrelated.refresh_from_db()
        self.assertEqual(unrelated.title, 'Admin text to preserve')
