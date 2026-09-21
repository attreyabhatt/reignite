import re
from urllib.parse import urlencode

from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse

from conversation.models import WebAppConfig
from reignitehome.seo import public_url


DEFAULT_WEB_GUEST_REPLY_LIMIT = 5
DEFAULT_WEB_SIGNUP_BONUS_CREDITS = 3


def public_site_metadata(request):
    return {"public_site_url": public_url("/").rstrip("/"),
            "canonical_url": public_url(request.path)}


def android_app_promotion(request):
    """Share app copy and attribution across public discovery pages."""
    match = request.resolver_match
    page_group = {
        "home": "home",
        "pickup_lines_index": "pickup_lines",
        "pickup_category_detail": "pickup_lines",
        "pickup_line_detail": "pickup_lines",
        "situation_index": "texting_guides",
        "situation_landing": "texting_guides",
        "conversation_home": "conversations",
    }.get(match.url_name if match else None)
    if not page_group:
        return {}

    title, description = {
        "pickup_lines": (
            "The opener is only the beginning.",
            "Make it personal with FlirtFix, our Android app. Get openers tailored "
            "to your match, then turn chat screenshots into replies that keep things going.",
        ),
        "texting_guides": (
            "Your next reply, right on your phone.",
            "Put this guide into practice with FlirtFix, our Android app. Upload "
            "your chat screenshot and get reply ideas tailored to your conversation.",
        ),
    }.get(page_group, (
        "Good replies. Wherever the chat goes.",
        "Meet FlirtFix, the Android app from TryAgainText. Turn profile and chat "
        "screenshots into personalized openers and replies, right on your phone.",
    ))
    attribution = {
        "utm_source": "website",
        "utm_medium": "home_cta" if page_group == "home" else "web_cta",
        "utm_campaign": f"flirtfix_web_{page_group}",
        "utm_term": request.path,
    }
    content_prefix = ""
    # Carry this campaign's public video labels through the landing-page app CTA.
    # Arbitrary query strings and conversation input never become attribution.
    source = request.GET.get("utm_source", "")
    video = request.GET.get("utm_content", "")
    if (source in {"instagram", "youtube", "tiktok"}
            and request.GET.get("utm_campaign") == "flirtfix_reach_2026_09"
            and request.GET.get("utm_medium") == "organic_social"
            and re.fullmatch(r"video(?:0[1-9]|1[0-2])", video)):
        attribution.update(utm_source=source, utm_medium="organic_social", utm_campaign="flirtfix_reach_2026_09")
        content_prefix = video + "_"
    query = urlencode(attribution)
    return {"android_app_promo": {
        "page_group": page_group,
        "title": title,
        "description": description,
        "url": f"{reverse('flirtfix_redirect')}?{query}",
        "content_prefix": content_prefix,
    }}


def web_marketing_limits(request):
    del request  # Unused; required by Django context processor signature.

    guest_limit = DEFAULT_WEB_GUEST_REPLY_LIMIT
    signup_bonus = DEFAULT_WEB_SIGNUP_BONUS_CREDITS

    try:
        cfg = WebAppConfig.load()
        guest_limit = int(cfg.guest_reply_limit or DEFAULT_WEB_GUEST_REPLY_LIMIT)
        signup_bonus = int(cfg.signup_bonus_credits or DEFAULT_WEB_SIGNUP_BONUS_CREDITS)
    except (OperationalError, ProgrammingError):
        pass

    return {
        "web_guest_reply_limit": guest_limit,
        "web_signup_bonus_credits": signup_bonus,
    }
