from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from seoapp.models import PickupCategory, PickupTopic
from seoapp.seed_data.search_refresh import PICKUP_REFRESH
from seoapp.seed_data.search_expansion import NEW_PICKUP_TOPICS, PICKUP_EXPANSION


class Command(BaseCommand):
    help = "Publish a reviewed content batch: priority (default) or expansion. Leave unrelated topics intact."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch", choices=("priority", "expansion"), default="priority")

    @transaction.atomic
    def handle(self, *args, **options):
        expansion = options["batch"] == "expansion"
        refreshes = PICKUP_EXPANSION if expansion else PICKUP_REFRESH
        new_topics = NEW_PICKUP_TOPICS if expansion else {}
        category_slugs = {category for category, _ in (*refreshes, *new_topics)}
        # Lock categories so concurrent expansion runs cannot choose the same append positions.
        categories = {category.slug: category for category in
                      PickupCategory.objects.select_for_update().filter(slug__in=category_slugs).order_by("pk")}
        missing = sorted(category_slugs - categories.keys())
        if missing:
            raise CommandError(f"Missing categories: {', '.join(missing)}. No changes saved.")

        targets = {}
        for category, slug in refreshes:
            topic = PickupTopic.objects.select_for_update().filter(category=categories[category], slug=slug).first()
            if not topic:
                raise CommandError(f"Missing {category}/{slug}. Restore this required topic before publishing. No changes saved.")
            targets[(category, slug)] = topic

        for (category, slug), fields in refreshes.items():
            topic = targets[(category, slug)]
            if not options["dry_run"]:
                for field, value in fields.items():
                    setattr(topic, field, value)
                topic.save(update_fields=[*fields, "updated_at"])
            self.stdout.write(f"{'Would refresh' if options['dry_run'] else 'Refreshed'} {category}/{slug}")

        next_orders = {}
        for (category_slug, slug), fields in new_topics.items():
            category = categories[category_slug]
            if PickupTopic.objects.filter(category=category, slug=slug).exists():
                self.stdout.write(f"Skipped existing {category_slug}/{slug}; retained its content and active status")
                continue
            if category_slug not in next_orders:
                maximum = PickupTopic.objects.filter(category=category).aggregate(value=Max("sort_order"))["value"]
                next_orders[category_slug] = maximum + 1 if maximum is not None else 0
            sort_order = next_orders[category_slug]
            if not options["dry_run"]:
                PickupTopic.objects.create(category=category, slug=slug, sort_order=sort_order, **fields)
            next_orders[category_slug] += 1
            self.stdout.write(f"{'Would create' if options['dry_run'] else 'Created'} {category_slug}/{slug} (position {sort_order})")
