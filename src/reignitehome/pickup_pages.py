PICKUP_TOPIC_FIELDS = (
    "category_slug",
    "category_name",
    "topic_slug",
    "keyword",
    "h1",
    "title",
    "meta_description",
    "seo_intro",
    "witty_lines",
    "flirty_lines",
    "cheesy_lines",
    "prefill_text",
    "upload_hint",
    "her_info_prefill",
)


PICKUP_TOPICS = {
    "literature/dostoevsky": {
        "category_slug": "literature",
        "category_name": "Literature",
        "topic_slug": "dostoevsky",
        "keyword": "Dostoevsky",
        "h1": "The Best Dostoevsky Pickup Lines (To Impress a Bookworm).",
        "title": "Best Dostoevsky Pickup Lines | TryAgainText",
        "meta_description": (
            "Use niche Dostoevsky pickup lines that feel witty, flirty, and specific. "
            "Then generate a custom opener from her exact profile vibe."
        ),
        "seo_intro": (
            "Matching with someone who quotes Dostoevsky can feel high pressure fast. "
            "These lines give you a sharper starting point than generic openers. "
            "Use them as inspiration, then personalize with context from her profile."
        ),
        "witty_lines": [
            "Are you Team Karamazov or Team Raskolnikov? Either way, I am ready for a debate over coffee.",
            "Your bio gives strong St. Petersburg energy: elegant, intense, and slightly dangerous.",
            "If your favorite novel is Crime and Punishment, I can promise better first-date ethics than Raskolnikov.",
        ],
        "flirty_lines": [
            "You have the kind of profile that could turn a realist into a romantic in one chapter.",
            "If we match this well in chat, imagine the chemistry in a bookstore aisle.",
            "I was going to play it cool, but your bio deserves a bold opener and a real date plan.",
        ],
        "cheesy_lines": [
            "Are you a Dostoevsky plot twist? Because my calm evening just got complicated.",
            "Call me the underground man, because I have been overthinking this opener for ten minutes.",
            "If attraction were a Russian novel, this match would already be 800 pages.",
        ],
        "prefill_text": (
            "Her bio: Crime and Punishment changed my life. "
            "Write a playful opener that sounds smart, not try-hard."
        ),
        "upload_hint": (
            "Upload a screenshot of her full profile so the opener matches her actual vibe, not just one keyword."
        ),
        "her_info_prefill": (
            "She has a quote from Crime and Punishment in her bio and a coffee shop photo. "
            "She seems witty and intellectual, but not overly serious."
        ),
    }
}

PICKUP_TOPIC_ORDER = [
    "literature/dostoevsky",
]


def list_pickup_topics():
    return [PICKUP_TOPICS[key] for key in PICKUP_TOPIC_ORDER if key in PICKUP_TOPICS]


def get_pickup_topic(category_slug, topic_slug):
    if not category_slug or not topic_slug:
        return None
    key = f"{str(category_slug).strip()}/{str(topic_slug).strip()}"
    return PICKUP_TOPICS.get(key)
