import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from seo_audit import Page
from seo_report import aggregate


class SeoToolTests(unittest.TestCase):
    def test_hostname_and_redirect_history_are_combined_with_weighted_positions(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'pages.csv'
            with path.open('w', newline='', encoding='utf-8-sig') as handle:
                writer = csv.writer(handle)
                writer.writerow(['Top pages', 'Clicks', 'Impressions', 'CTR', 'Position'])
                writer.writerows([
                    ['https://tryagaintext.com/situations/what-to-text-after-a-date/?utm_source=google', 2, 100, '2%', 10],
                    ['https://www.tryagaintext.com/situations/what-to-text-after-first-date/', 4, 300, '1.33%', 6],
                ])
            result = aggregate(path)
            self.assertEqual(len(result), 1)
            item = result['/situations/what-to-text-after-first-date/']
            self.assertEqual((item['clicks'], item['impressions'], item['position']), (6, 400, 7))

    def test_audit_extracts_indexability_and_excludes_script_text(self):
        page = Page('<link rel="canonical" href="https://www.tryagaintext.com/"><meta name="robots" content="noindex"><h1>Hello</h1><script>hidden</script><a href="/situations/">Guides</a>')
        self.assertEqual(page.canonical, 'https://www.tryagaintext.com/')
        self.assertEqual(page.h1, 1)
        self.assertEqual(page.robots, ['noindex'])
        self.assertEqual(page.links, {'/situations/'})
        self.assertNotIn('hidden', page.text)


if __name__ == '__main__':
    unittest.main()
