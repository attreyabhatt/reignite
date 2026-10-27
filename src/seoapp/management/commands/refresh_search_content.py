from django.core.management.base import BaseCommand, CommandError
import json
from pathlib import Path
from django.db import transaction
from django.db.models import Max

from seoapp.models import PickupCategory, PickupTopic
from seoapp.seed_data.search_refresh import PICKUP_REFRESH
from seoapp.seed_data.search_expansion import NEW_PICKUP_TOPICS, PICKUP_EXPANSION
from seoapp.organic_refresh import PICKUP_ORGANIC_REFRESH

BATCH_ID = "organic_2026_10"


class Command(BaseCommand):
    help = "Publish a reviewed content batch: priority (default) or expansion. Leave unrelated topics intact."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch", choices=("priority", "expansion", "organic"), default="priority")
        parser.add_argument("--backup", type=Path, help="New JSON file for the organic batch's original fields")
        parser.add_argument("--restore", type=Path, help="Restore only the five organic targets from a prior backup")
        parser.add_argument("--force", action="store_true", help="Reapply organic content after it has already been published")

    @transaction.atomic
    def handle(self, *args, **options):
        expansion = options["batch"] == "expansion"
        organic = options["batch"] == "organic"
        refreshes = PICKUP_ORGANIC_REFRESH if organic else (PICKUP_EXPANSION if expansion else PICKUP_REFRESH)
        if (options["backup"] or options["restore"] or options["force"]) and not organic:
            raise CommandError("Backup, restore and force apply only to --batch organic.")
        if organic and not options["dry_run"] and not options["restore"] and not options["backup"]:
            raise CommandError("Publishing the organic batch requires --backup NEW_FILE.json.")
        if options["restore"]:
            try:
                backup = json.loads(options["restore"].read_text(encoding="utf-8"))
                if backup["batch"] != BATCH_ID:
                    raise ValueError("Wrong backup batch")
                saved = {(item["category"], item["slug"]): item["fields"] for item in backup["topics"]}
                if set(saved) != set(refreshes) or len(backup["topics"]) != len(refreshes):
                    raise ValueError("Backup targets do not match the organic batch")
                for key, fields in saved.items():
                    if not isinstance(fields, dict) or set(fields) != set(refreshes[key]):
                        raise ValueError("Backup fields do not match the organic batch")
                refreshes = saved
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise CommandError(f"Invalid backup: {exc}") from exc
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

        if organic and options["backup"] and not options["dry_run"]:
            backup = {"batch": BATCH_ID, "topics": [
                {"category": key[0], "slug": key[1],
                 "fields": {field: getattr(targets[key], field) for field in fields}}
                for key, fields in refreshes.items()]}
            try:
                with options["backup"].open("x", encoding="utf-8") as handle:
                    json.dump(backup, handle, ensure_ascii=False, indent=2)
            except OSError as exc:
                raise CommandError(f"Could not create new backup: {exc}") from exc

        for (category, slug), fields in refreshes.items():
            topic = targets[(category, slug)]
            if (organic and not options["restore"] and not options["force"]
                    and topic.guide_content.get("batch_id") == BATCH_ID):
                self.stdout.write(f"Skipped already-published {category}/{slug}; retained subsequent admin edits")
                continue
            fields = dict(fields)
            if organic and not options["restore"]:
                fields["guide_content"] = {**fields["guide_content"], "batch_id": BATCH_ID}
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
