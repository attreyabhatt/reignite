"""First-touch metadata. Never retain arbitrary URLs, query strings or chat text."""
from urllib.parse import urlsplit
import re

from django.conf import settings
from django.urls import Resolver404, resolve
from django.utils.deprecation import MiddlewareMixin

SESSION_KEY = "web_acquisition"
PENDING_KEY = "web_analytics_pending"
PUBLIC_ROUTES = {"home", "about", "situation_index", "situation_landing", "pickup_lines_index",
                 "pickup_category_detail", "pickup_line_detail", "glossary", "pricing",
                 "privacy_policy", "terms_and_conditions", "refund_policy", "contact", "safety_standards",
                 "screenclean_privacy_policy", "delete_account_request"}
SOURCES = {"google", "bing", "duckduckgo", "yahoo", "ecosia", "instagram", "youtube",
           "tiktok", "reddit", "newsletter", "chatgpt", "perplexity"}
MEDIUMS = {"organic", "organic_social", "referral", "email", "cpc", "ai_assistant"}


def public_path(value):
    try:
        path = urlsplit(value).path
        match = resolve(path)
    except (Resolver404, ValueError):
        return ""
    if match.url_name not in PUBLIC_ROUTES:
        return ""
    if match.url_name in {"pickup_category_detail", "pickup_line_detail"}:
        from seoapp.models import PickupTopic
        topics = PickupTopic.objects.filter(category__slug=match.kwargs["category_slug"], is_active=True)
        if match.url_name == "pickup_line_detail":
            topics = topics.filter(slug=match.kwargs["topic_slug"])
        if not topics.exists():
            return ""
    if match.url_name == "situation_landing":
        from seoapp.organic_guides import REDIRECTS
        from seoapp.situation_pages import get_situation_page
        slug = REDIRECTS.get(match.kwargs["slug"], match.kwargs["slug"])
        if not get_situation_page(slug):
            return ""
        path = f"/situations/{slug}/"
    return path[:255]


def source_medium(request):
    source, medium = request.GET.get("utm_source", ""), request.GET.get("utm_medium", "")
    if source in SOURCES and medium in MEDIUMS:
        return source, medium
    try:
        host = (urlsplit(request.headers.get("Referer", "")).hostname or "").lower()
    except ValueError:
        host = ""
    if not host or host in {"tryagaintext.com", "www.tryagaintext.com", request.get_host().split(":")[0]}:
        return "direct", "none"
    if re.fullmatch(r"(?:www\.)?google\.(?:com|[a-z]{2,3}|co\.[a-z]{2}|com\.[a-z]{2})", host):
        return "google", "organic"
    for domain, name, channel in (
        ("bing.com", "bing", "organic"), ("duckduckgo.com", "duckduckgo", "organic"),
        ("search.yahoo.com", "yahoo", "organic"), ("ecosia.org", "ecosia", "organic"),
        ("chatgpt.com", "chatgpt", "ai_assistant"), ("perplexity.ai", "perplexity", "ai_assistant"),
        ("instagram.com", "instagram", "referral"), ("youtube.com", "youtube", "referral"),
        ("reddit.com", "reddit", "referral"), ("tiktok.com", "tiktok", "referral"),
    ):
        if host == domain or host.endswith("." + domain):
            return name, channel
    return "other", "referral"


def acquisition(request):
    value = request.session.get(SESSION_KEY)
    if not isinstance(value, dict):
        value = {"landing_path": public_path(request.path) or public_path(request.headers.get("Referer", ""))}
        value["source"], value["medium"] = source_medium(request)
        request.session[SESSION_KEY] = value
    return value


class WebAcquisitionMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "GET" and public_path(request.path):
            acquisition(request)

    def process_response(self, request, response):
        # allauth may render email templates with the request before redirecting.
        # Only consume queued events after the full web page actually includes them.
        if (settings.WEB_ANALYTICS_ENABLED and not getattr(response, 'streaming', False)
                and response.status_code == 200 and not request.headers.get('HX-Request')
                and 'text/html' in response.get('Content-Type', '')
                and b'id="web-analytics-events"' in response.content):
            request.session.pop(PENDING_KEY, None)
        return response


def analytics_event(event):
    return {"event_id": str(event.generation_id or f"web-{event.pk}"),
            "landing_path": event.landing_path,
            "acquisition_source": event.acquisition_source,
            "acquisition_medium": event.acquisition_medium}


def analytics_context(request):
    # HTMX partials do not render the base template and must not consume signups.
    pending = []
    if settings.WEB_ANALYTICS_ENABLED and not request.headers.get("HX-Request"):
        pending = request.session.get(PENDING_KEY, [])
    path = public_path(request.path)
    if not path:
        path = "/conversations/" if request.path.startswith("/conversations/") else "/accounts/"
    return {"analytics_location": settings.PUBLIC_SITE_URL + path,
            "analytics_referrer": {
                "google": "https://www.google.com/", "bing": "https://www.bing.com/",
                "yahoo": "https://search.yahoo.com/", "duckduckgo": "https://duckduckgo.com/",
                "ecosia": "https://www.ecosia.org/", "chatgpt": "https://chatgpt.com/",
                "perplexity": "https://www.perplexity.ai/", "reddit": "https://www.reddit.com/",
                "instagram": "https://www.instagram.com/", "youtube": "https://www.youtube.com/",
                "tiktok": "https://www.tiktok.com/",
            }.get(source_medium(request)[0], ""),
            "analytics_campaign_source": request.GET.get("utm_source") if request.GET.get("utm_source") in SOURCES and request.GET.get("utm_medium") in MEDIUMS else "",
            "analytics_campaign_medium": request.GET.get("utm_medium") if request.GET.get("utm_source") in SOURCES and request.GET.get("utm_medium") in MEDIUMS else "",
            "analytics_acquisition": request.session.get(SESSION_KEY, {}),
            "web_analytics_events": pending}
