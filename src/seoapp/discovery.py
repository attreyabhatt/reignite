from django.db.models import Q

from seoapp.models import PickupTopic
from seoapp.situation_pages import get_situation_page
from seoapp.seed_data.search_expansion import NEW_PICKUP_TOPICS


FEATURED_TOPICS = [
    ("dating-apps", "instagram-dm-opener"), ("professions", "lawyer"),
    ("professions", "therapist"), ("hobbies", "pilates"),
    ("zodiac-signs", "cancer"), ("dog-breeds", "pitbull"),
    ("dating-apps", "hinge-prompt-answers"), ("professions", "paramedic"),
    ("professions", "flight-attendant"), ("dog-breeds", "golden-retriever"),
]


def featured_topics(category_slug=None, limit=6):
    keys = [key for key in FEATURED_TOPICS if not category_slug or key[0] == category_slug]
    if category_slug:
        keys = [key for key in NEW_PICKUP_TOPICS if key[0] == category_slug] + keys
    return _topics_in_order(keys, limit)


def _topics_in_order(keys, limit):
    if not keys:
        return []
    query = Q()
    for category, slug in keys:
        query |= Q(category__slug=category, slug=slug)
    topics = PickupTopic.objects.filter(query, is_active=True).select_related("category")
    return [t.to_dict() for t in sorted(topics, key=lambda t: keys.index((t.category.slug, t.slug)))[:limit]]


def related_pickup_topics(topic, limit=4):
    key = (topic.category.slug, topic.slug)
    if key in NEW_PICKUP_TOPICS:
        keys = [other for other in NEW_PICKUP_TOPICS if other[0] == key[0] and other != key]
        return _topics_in_order(keys, limit)
    return [other.to_dict() for other in PickupTopic.objects.filter(
        category=topic.category, is_active=True,
    ).exclude(pk=topic.pk).select_related("category")[:limit]]


PICKUP_GUIDE_SLUGS = {
    ("dating-apps", "instagram-dm-opener"): (
        "how-to-reply-to-instagram-story", "what-to-say-next-over-text", "how-to-respond-to-hey",
    ),
    ("dating-apps", "tinder-opener"): (
        "dating-app-openers-with-no-bio", "how-to-respond-to-hey", "what-to-say-next-over-text",
    ),
    **{key: ("how-to-reply-to-a-pickup-line", "what-to-say-next-over-text", "how-to-ask-her-out-over-text")
       for key in [*NEW_PICKUP_TOPICS, ("professions", "barista"),
                   ("professions", "flight-attendant"), ("fandoms", "lord-of-the-rings")]},
}


def next_step_guides(category_slug=None, topic_slug=None):
    slugs = PICKUP_GUIDE_SLUGS.get((category_slug, topic_slug), (
        "what-to-say-next-over-text", "how-to-respond-to-dry-texts", "how-to-ask-her-out-over-text",
    ))
    return [get_situation_page(slug) for slug in slugs]
