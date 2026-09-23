"""Web-only continuation and metadata-only conversion events."""
import uuid
from datetime import timedelta
from urllib.parse import urlencode, urlsplit

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from pricing.catalog import STARTER_PACK
from .models import Conversation, WebAppConfig, WebConversionEvent

DRAFT_KEY = "web_pending_conversation"
JOURNEY_KEY = "web_conversion_journey"
EXPERIMENT = "web_continuation_2026_09"


def journey_id(request):
    value = request.session.get(JOURNEY_KEY)
    if not value:
        value = str(uuid.uuid4())
        request.session[JOURNEY_KEY] = value
    return value


def origin_path(request):
    # Keep a public path, never a query string, chat text, email, or referrer host.
    path = urlsplit(request.headers.get("Referer", "")).path
    if path == "/" or path.startswith(("/pickup-lines/", "/situations/", "/conversations/", "/pricing/")):
        return path[:255]
    return ""


def record_event(request, kind, *, generation_id=None, situation="", origin="", user=None,
                 offer_kind="", credit_pack=None, dedupe_key=None):
    user = user or (request.user if request.user.is_authenticated else None)
    identity = journey_id(request)
    if kind != WebConversionEvent.Kind.GENERATED and not origin:
        previous = WebConversionEvent.objects.filter(journey_id=identity, kind="generated").order_by("created_at").first()
        if previous:
            origin, situation = previous.origin_path, situation or previous.situation
    event, _ = WebConversionEvent.objects.get_or_create(
        dedupe_key=dedupe_key or str(uuid.uuid4()),
        defaults={"journey_id": identity, "user": user, "kind": kind,
                  "generation_id": generation_id, "situation": situation[:150],
                  "origin_path": origin or origin_path(request), "was_guest": user is None,
                  "offer_kind": offer_kind, "credit_pack": credit_pack},
    )
    return event


def link_account(request, user):
    value = request.session.get(JOURNEY_KEY)
    if not value:
        return
    events = WebConversionEvent.objects.filter(journey_id=value)
    if events.filter(user__isnull=False).exclude(user=user).exists():
        request.session.pop(JOURNEY_KEY, None)
        request.session.pop(DRAFT_KEY, None)
        return
    events.filter(user__isnull=True).update(user=user)


def save_pending(request, *, text, situation, her_info, suggestions, generation_id):
    request.session[DRAFT_KEY] = {
        "id": str(generation_id), "created_at": timezone.now().isoformat(),
        "text": text, "situation": situation, "her_info": her_info,
        "suggestions": suggestions,
    }


def pending_draft(request):
    """Read the session draft only while its 24-hour lifetime is valid."""
    from datetime import datetime
    draft = request.session.get(DRAFT_KEY)
    if not draft:
        return None
    try:
        created = datetime.fromisoformat(draft["created_at"])
        if timezone.is_naive(created) or not timezone.now() - timedelta(hours=24) <= created <= timezone.now():
            request.session.pop(DRAFT_KEY, None)
            return None
        uuid.UUID(draft["id"])
    except (KeyError, ValueError, TypeError):
        request.session.pop(DRAFT_KEY, None)
        return None
    return draft


def restore_pending(request, user):
    """Import the latest successful guest result once, without spending credits."""
    draft = pending_draft(request)
    request.session.pop(DRAFT_KEY, None)
    if not draft:
        return None
    draft_id = uuid.UUID(draft["id"])
    with transaction.atomic():
        convo, _ = Conversation.objects.get_or_create(
            guest_draft_id=draft_id,
            defaults={"user": user, "content": draft["text"], "situation": draft["situation"],
                      "her_info": draft["her_info"], "girl_title": "Your saved conversation",
                      "latest_suggestions": draft["suggestions"], "latest_generation_id": draft_id},
        )
    if convo.user_id != user.pk:
        return None
    request.session["web_active_conversation"] = convo.pk
    return convo


def continuation_context(request, credits_left, generation_id=None):
    signup = reverse("account_signup") + "?" + urlencode({"next": reverse("conversation_home")})
    login = reverse("account_login") + "?" + urlencode({"next": reverse("conversation_home")})
    kind = "signup" if not request.user.is_authenticated else ("purchase" if credits_left == 0 else "")
    return {"suggestions_generation_id": str(generation_id or ""),
            "continuation_kind": kind, "result_credits_left": credits_left,
            "continuation_signup_url": signup, "continuation_login_url": login,
            "continuation_bonus": WebAppConfig.load().signup_bonus_credits,
            "starter_pack": STARTER_PACK}


def on_web_login(sender, request, user, **kwargs):
    if request is not None and hasattr(request, "session"):
        link_account(request, user)
        restore_pending(request, user)
