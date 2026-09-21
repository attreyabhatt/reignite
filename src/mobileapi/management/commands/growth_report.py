import json

from django.core.management.base import BaseCommand

from reignitehome.growth import GROUPS, growth_funnel


class Command(BaseCommand):
    help = "Output a privacy-preserving click/install/activation cohort report as JSON."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, choices=[7, 28, 90], default=28)
        parser.add_argument("--group", choices=list(GROUPS), default="campaign")

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(growth_funnel(days=options["days"], group=options["group"]), default=str, indent=2))
