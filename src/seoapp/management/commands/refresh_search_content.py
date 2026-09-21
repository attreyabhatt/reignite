from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from seoapp.models import PickupTopic
from seoapp.seed_data.search_refresh import PICKUP_REFRESH


class Command(BaseCommand):
    help = "Refresh only the three reviewed pickup/profile guides; leave all other topics intact."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        for (category, slug), fields in PICKUP_REFRESH.items():
            topic = PickupTopic.objects.filter(category__slug=category, slug=slug).first()
            if not topic:
                raise CommandError(f"Missing {category}/{slug}. Seed a new database first. No changes saved.")
            if not options["dry_run"]:
                for field, value in fields.items():
                    setattr(topic, field, value)
                topic.save(update_fields=[*fields, "updated_at"])
            self.stdout.write(f"{'Would refresh' if options['dry_run'] else 'Refreshed'} {category}/{slug}")
