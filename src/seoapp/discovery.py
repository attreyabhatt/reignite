from django.db.models import Q

from seoapp.models import PickupTopic
from seoapp.situation_pages import get_situation_page


FEATURED_TOPICS = [
    ("dating-apps", "instagram-dm-opener"), ("professions", "lawyer"),
    ("professions", "therapist"), ("hobbies", "pilates"),
    ("zodiac-signs", "cancer"), ("dog-breeds", "pitbull"),
    ("dating-apps", "hinge-prompt-answers"), ("professions", "paramedic"),
    ("professions", "flight-attendant"), ("dog-breeds", "golden-retriever"),
]


def featured_topics(category_slug=None, limit=6):
    keys = [key for key in FEATURED_TOPICS if not category_slug or key[0] == category_slug]
    if not keys:
        return []
    query = Q()
    for category, slug in keys:
        query |= Q(category__slug=category, slug=slug)
    topics = PickupTopic.objects.filter(query, is_active=True).select_related("category")
    return [t.to_dict() for t in sorted(topics, key=lambda t: keys.index((t.category.slug, t.slug)))[:limit]]


def next_step_guides():
    return [get_situation_page(slug) for slug in (
        "what-to-say-next-over-text", "how-to-respond-to-dry-texts", "how-to-ask-her-out-over-text",
    )]
