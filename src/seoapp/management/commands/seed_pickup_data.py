from django.core.management.base import BaseCommand

from seoapp.models import PickupCategory, PickupTopic
from seoapp.seed_data import (
    literature, zodiac, mbti, enneagram, hobbies, professions, dog_breeds, fandoms, music_genres,
    attachment_styles, love_languages, astrology_placements, book_genres, gaming_niches, wellness,
    relationship_archetypes, us_cities, dating_apps
)


SEED_MODULES = [
    literature, zodiac, mbti, enneagram, hobbies, professions, dog_breeds, fandoms, music_genres,
    attachment_styles, love_languages, astrology_placements, book_genres, gaming_niches, wellness,
    relationship_archetypes, us_cities, dating_apps
]


class Command(BaseCommand):
    help = "Seed the database with pickup line categories and topics (idempotent)."

    def handle(self, *args, **options):
        total_created = 0
        total_updated = 0

        for module in SEED_MODULES:
            data = module.DATA
            category, _ = PickupCategory.objects.update_or_create(
                slug=data["category_slug"],
                defaults={
                    "name": data["category_name"],
                    "sort_order": data.get("sort_order", 0),
                },
            )

            for i, topic in enumerate(data["topics"]):
                _, created = PickupTopic.objects.update_or_create(
                    category=category,
                    slug=topic["slug"],
                    defaults={
                        "keyword": topic["keyword"],
                        "h1": topic["h1"],
                        "title": topic["title"],
                        "meta_description": topic["meta_description"],
                        "seo_intro": topic["seo_intro"],
                        "witty_lines": topic["witty_lines"],
                        "flirty_lines": topic["flirty_lines"],
                        "cheesy_lines": topic["cheesy_lines"],
                        "prefill_text": topic["prefill_text"],
                        "upload_hint": topic["upload_hint"],
                        "her_info_prefill": topic.get("her_info_prefill", ""),
                        "sort_order": i,
                    },
                )
                if created:
                    total_created += 1
                else:
                    total_updated += 1

            self.stdout.write(
                f"  {category.name}: {len(data['topics'])} topics"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {total_created}, updated {total_updated}."
            )
        )
