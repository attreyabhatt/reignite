import json
from django.core.management.base import BaseCommand
from seoapp.organic_guides import NEW_GUIDES, editorial_metadata


class Command(BaseCommand):
    help = "Read-only manifest of all twelve immediately available guides."

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        rows = [{"slug": slug, "date_published": editorial_metadata(page)['date_published'],
                 "status": "available"}
                for slug, page in NEW_GUIDES.items()]
        if options['json']:
            self.stdout.write(json.dumps({"publication_mode": "all_at_once", "guides": rows}, indent=2))
        else:
            self.stdout.write("All twelve guides are available in this release; no date gates.")
            for row in rows:
                self.stdout.write(f"{row['status']:9}  /situations/{row['slug']}/")
