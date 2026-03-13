import hashlib
import hmac
import json
import logging
import uuid
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from conversation.models import GuestWebConversationAttempt, WebAppConfig
from conversation.utils.web_guest_logging import log_guest_web_attempt
from conversation.utils.reignite_gpt import generate_reignite_comeback
from reignitehome.models import ContactMessage, MarketingClickEvent, TrialIP
from reignitehome.situation_pages import (
    SITUATION_PAGE_ORDER,
    get_situation_page,
    list_related_pages,
    list_situation_pages,
)
from reignitehome.utils.ip_check import get_client_ip

# Whitelists (match your <select> values in home.html)
PLATFORM_ALLOWED = {
    "Tinder","Bumble","Hinge","Instagram DM","WhatsApp",
    "iMessage/SMS","Snapchat","Telegram","Facebook Messenger","Other",
}
WHAT_ALLOWED = {
    "She left me on read",
    "She replied, but I need help with my next message",
    "She replied with one word, then nothing",
    "She didn’t reply after my question",
    "She ghosted after I asked her out",
    "Conversation just fizzled",
    "She didn’t reply after my joke",
    "She ignored my compliment",
    "I sent something awkward",
    "No reply to my flirty message",
    "Not sure / Just stopped",
    "Other",
}

PLAY_STORE_BASE_URL = "https://play.google.com/store/apps/details"
PLAY_STORE_APP_ID = "com.tryagaintext.flirtfix"
FLIRTFIX_ROUTE_KEY = "flirtfix"
BOT_UA_SUBSTRINGS = (
    "googlebot",
    "google-pagerenderer",
    "bingbot",
    "duckduckbot",
    "yandexbot",
    "baiduspider",
    "applebot",
    "facebookexternalhit",
    "facebot",
    "linkedinbot",
    "twitterbot",
    "slackbot",
    "discordbot",
    "telegrambot",
    "pinterestbot",
    "redditbot",
    "crawler",
    "spider",
    "bot/",
    "bot ",
    "slurp",
    "ahrefsbot",
    "semrushbot",
    "mj12bot",
    "dotbot",
    "bytespider",
    "curl/",
    "wget/",
    "python-requests",
    "okhttp",
    "go-http-client",
)

logger = logging.getLogger(__name__)


def _get_web_config():
    return WebAppConfig.load()


def _build_guest_chat_context(request):
    if "chat_credits" not in request.session:
        request.session["chat_credits"] = _get_web_config().guest_reply_limit

    current_chat_credits = request.session["chat_credits"]

    ip = get_client_ip(request)
    trial_record, created = TrialIP.objects.get_or_create(ip_address=ip)
    if not created and trial_record.trial_used:
        current_chat_credits = 0

    return {
        "chat_credits": current_chat_credits,
    }


def _sanitize_utm_value(raw_value, default="", max_len=160):
    value = str(raw_value or "").strip().lower()
    if not value:
        value = default
    return value[:max_len]


def _is_bot_like_request(request):
    method = (request.method or "").upper()
    if method in {"HEAD", "OPTIONS"}:
        return True

    user_agent = (request.META.get("HTTP_USER_AGENT") or "").strip().lower()
    if not user_agent:
        return True

    return any(signature in user_agent for signature in BOT_UA_SUBSTRINGS)


def _extract_referrer_host(request):
    raw_referrer = (request.META.get("HTTP_REFERER") or "").strip()
    if not raw_referrer:
        return ""

    parsed = urlparse(raw_referrer)
    host = (parsed.netloc or "").lower().strip()
    return host[:255]


def _hash_ip_address(ip_address):
    value = str(ip_address or "").strip()
    if not value:
        return ""

    secret_key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(secret_key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_play_store_redirect_url(utm_data, click_id):
    referrer_params = {
        "utm_source": utm_data["utm_source"],
        "utm_medium": utm_data["utm_medium"],
        "utm_campaign": utm_data["utm_campaign"],
        "ffclid": str(click_id),
    }
    if utm_data["utm_content"]:
        referrer_params["utm_content"] = utm_data["utm_content"]
    if utm_data["utm_term"]:
        referrer_params["utm_term"] = utm_data["utm_term"]

    play_store_params = {
        "id": PLAY_STORE_APP_ID,
        "hl": "en_IN",
        "referrer": urlencode(referrer_params),
    }
    return f"{PLAY_STORE_BASE_URL}?{urlencode(play_store_params)}"


def flirtfix_redirect(request):
    utm_data = {
        "utm_source": _sanitize_utm_value(
            request.GET.get("utm_source"), default="unknown", max_len=120
        ),
        "utm_medium": _sanitize_utm_value(
            request.GET.get("utm_medium"), default="unknown", max_len=120
        ),
        "utm_campaign": _sanitize_utm_value(
            request.GET.get("utm_campaign"), default="unknown", max_len=160
        ),
        "utm_content": _sanitize_utm_value(request.GET.get("utm_content"), default="", max_len=160),
        "utm_term": _sanitize_utm_value(request.GET.get("utm_term"), default="", max_len=160),
    }
    click_id = uuid.uuid4()
    target_url = _build_play_store_redirect_url(utm_data, click_id)
    method = (request.method or "").upper()
    user_agent = (request.META.get("HTTP_USER_AGENT") or "").strip()
    user_agent_preview = user_agent[:120]

    has_campaign_context = any(
        utm_data[key] != "unknown" for key in ("utm_source", "utm_medium", "utm_campaign")
    )
    is_bot_like = _is_bot_like_request(request)
    if not has_campaign_context:
        logger.info(
            "Skipping marketing click persist reason=unknown_utm_triplet method=%s ua=%s",
            method,
            user_agent_preview,
        )
    elif is_bot_like:
        logger.info(
            "Skipping marketing click persist reason=bot_like_request method=%s ua=%s",
            method,
            user_agent_preview,
        )
    else:
        raw_query = {key: request.GET.getlist(key) for key in request.GET.keys()}
        MarketingClickEvent.objects.create(
            route_key=FLIRTFIX_ROUTE_KEY,
            click_id=click_id,
            utm_source=utm_data["utm_source"],
            utm_medium=utm_data["utm_medium"],
            utm_campaign=utm_data["utm_campaign"],
            utm_content=utm_data["utm_content"],
            utm_term=utm_data["utm_term"],
            referrer_host=_extract_referrer_host(request),
            ip_hash=_hash_ip_address(get_client_ip(request)),
            user_agent=user_agent[:255],
            target_url=target_url,
            raw_query=raw_query,
        )

    response = redirect(target_url)
    response["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def ratelimited_error(request, exception=None):
    return JsonResponse(
        {
            "success": False,
            "error": "rate_limited",
            "message": "Too many requests. Please try again shortly.",
        },
        status=429,
    )


def home(request):
    context = _build_guest_chat_context(request)
    context["situation_pages"] = list_situation_pages()

    if request.user.is_authenticated:
        return redirect('conversation_home')
    return render(request, 'home.html',context)


@require_http_methods(["GET"])
def situation_index(request):
    canonical_url = request.build_absolute_uri(reverse("situation_index"))
    context = _build_guest_chat_context(request)
    context.update(
        {
            "situation_pages": list_situation_pages(),
            "meta_description": (
                "Explore texting guides for every dating app scenario, from dry replies to asking for dates. "
                "Open the exact guide and generate send-ready responses."
            ),
            "canonical_url": canonical_url,
            "og_title": "Texting Guides | TryAgainText",
            "og_description": (
                "Browse all TryAgainText scenario guides and jump into the exact texting situation you need help with."
            ),
            "og_url": canonical_url,
        }
    )
    return render(request, "situations_index.html", context)


@require_http_methods(["GET"])
def situation_landing(request, slug):
    situation_page = get_situation_page(slug)
    if not situation_page:
        raise Http404("Situation page not found.")

    canonical_url = request.build_absolute_uri(
        reverse("situation_landing", kwargs={"slug": situation_page["slug"]})
    )
    context = _build_guest_chat_context(request)
    context.update(
        {
            "situation_page": situation_page,
            "related_pages": list_related_pages(situation_page),
            "situation_pages": list_situation_pages(),
            "meta_description": situation_page["meta_description"],
            "canonical_url": canonical_url,
            "og_title": situation_page["title"],
            "og_description": situation_page["meta_description"],
            "og_url": canonical_url,
        }
    )
    return render(request, "situation_layout.html", context)


@require_http_methods(["GET"])
def sitemap_xml(request):
    absolute_urls = [
        request.build_absolute_uri(reverse("home")),
        request.build_absolute_uri(reverse("situation_index")),
        request.build_absolute_uri(reverse("pricing:pricing")),
        request.build_absolute_uri(reverse("privacy_policy")),
        request.build_absolute_uri(reverse("terms_and_conditions")),
        request.build_absolute_uri(reverse("refund_policy")),
        request.build_absolute_uri(reverse("contact")),
        request.build_absolute_uri(reverse("delete_account_request")),
        request.build_absolute_uri(reverse("safety_standards")),
        request.build_absolute_uri(reverse("screenclean_privacy_policy")),
    ]

    for slug in SITUATION_PAGE_ORDER:
        absolute_urls.append(
            request.build_absolute_uri(
                reverse("situation_landing", kwargs={"slug": slug})
            )
        )

    return render(
        request,
        "sitemap.xml",
        {"urls": absolute_urls},
        content_type="application/xml",
    )


@ratelimit(key='ip', rate='10/d', block=True)   # keep your current limit
@require_POST
def ajax_reply_home(request):
    endpoint = GuestWebConversationAttempt.Endpoint.AJAX_REPLY_HOME
    guest_input_payload = {
        "content_type": (request.META.get("CONTENT_TYPE") or "").strip().lower(),
    }

    # 1) Quick size & content-type guards
    clen = int(request.META.get("CONTENT_LENGTH") or 0)
    guest_input_payload["content_length"] = clen
    if clen and clen > 32_768:
        error_message = "Payload too large."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.REQUEST_ERROR,
            http_status=413,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=413)
    if "application/json" not in (request.META.get("CONTENT_TYPE") or ""):
        error_message = "Content-Type must be application/json."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.REQUEST_ERROR,
            http_status=415,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=415)

    # 2) Trial/credits gate (your original logic)
    ip = get_client_ip(request)
    trial_record, created = TrialIP.objects.get_or_create(ip_address=ip)
    if not created and trial_record.trial_used:
        signup_url = reverse('account_signup')
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.CREDITS_BLOCKED,
            http_status=403,
            input_payload=guest_input_payload,
            output_payload={"redirect_url": signup_url},
            error_message="Guest out of credits.",
        )
        return JsonResponse({
            'error': "You're out of chat credits. Sign up to unlock unlimited replies.",
            'redirect_url': signup_url
        }, status=403)

    credits = request.session.get('chat_credits', _get_web_config().guest_reply_limit)
    guest_input_payload["credits_before"] = int(credits)
    if credits <= 0:
        trial_record.trial_used = True
        trial_record.save()
        signup_url = reverse('account_signup')
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.CREDITS_BLOCKED,
            http_status=403,
            input_payload=guest_input_payload,
            output_payload={"redirect_url": signup_url},
            error_message="Guest out of credits.",
        )
        return JsonResponse({
            'error': "You're out of chat credits. Sign up to unlock unlimited replies.",
            'redirect_url': signup_url
        }, status=403)

    # 3) Parse JSON safely
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        error_message = "Invalid JSON."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.REQUEST_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=400)

    last_text = (data.get('last_text') or "").strip()
    platform = (data.get('platform') or "").strip()
    what_happened = (data.get('what_happened') or "").strip()
    guest_input_payload.update({
        "last_text": last_text,
        "platform": platform,
        "what_happened": what_happened,
    })

    # 4) Validate fields
    if not (5 <= len(last_text) <= 1200):
        error_message = "Please enter the full conversation."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.VALIDATION_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=400)
    if platform not in PLATFORM_ALLOWED:
        error_message = "Invalid platform."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.VALIDATION_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=400)
    if what_happened not in WHAT_ALLOWED:
        error_message = "Invalid what_happened."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.VALIDATION_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=400)

    # 5) Call generator; deduct credit only on success
    try:
        custom_response, success = generate_reignite_comeback(last_text, platform, what_happened)
    except Exception:
        error_message = "Generation failed. Try again."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.AI_ERROR,
            http_status=502,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=502)

    if not success:
        error_message = "Generation failed. Try again."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.AI_ERROR,
            http_status=502,
            input_payload=guest_input_payload,
            output_payload={"custom": custom_response, "error": error_message},
            error_message=error_message,
        )
        return JsonResponse({"error": error_message}, status=502)

    request.session['chat_credits'] = max(0, credits - 1)
    payload = {
        "custom": custom_response,
        "credits_left": request.session['chat_credits'],
    }
    log_guest_web_attempt(
        request=request,
        endpoint=endpoint,
        status=GuestWebConversationAttempt.Status.SUCCESS,
        http_status=200,
        input_payload=guest_input_payload,
        output_payload=payload,
    )
    return JsonResponse(payload)



def contact_view(request):
    submitted = False
    if request.method == 'POST':
        reason = request.POST.get('reason')
        title = request.POST.get('title')
        subject = request.POST.get('subject')
        email = request.POST.get('email')

        ContactMessage.objects.create(
            reason=reason,
            title=title,
            subject=subject,
            email=email
        )
        submitted = True  # Flag for thank you message

    return render(request, 'contact.html', {'submitted': submitted})


@require_http_methods(["GET", "POST"])
def delete_account_request(request):
    submitted = False
    errors = {}
    form = {}

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        username = (request.POST.get('username') or '').strip()
        details = (request.POST.get('details') or '').strip()

        form = {
            'email': email,
            'username': username,
            'details': details,
        }

        if not email:
            errors.setdefault('email', []).append('Email is required.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.setdefault('email', []).append('Please enter a valid email.')

        if errors:
            return render(
                request,
                'policy/delete_account.html',
                {'submitted': submitted, 'errors': errors, 'form': form},
            )

        subject_lines = [
            'Account deletion request',
            f'Username: {username or "Not provided"}',
            f'Email: {email}',
        ]
        if details:
            subject_lines.append(f'Details: {details}')
        subject_text = '\n'.join(subject_lines)

        ContactMessage.objects.create(
            reason='other',
            title='Account deletion request',
            subject=subject_text,
            email=email,
        )
        submitted = True

    return render(
        request,
        'policy/delete_account.html',
        {'submitted': submitted, 'errors': errors, 'form': form},
    )


def privacy_policy(request):
    return render(request, "policy/privacy_policy.html")

def terms_and_conditions(request):
    return render(request, "policy/terms_and_conditions.html")

def refund_policy(request):
    return render(request, "policy/refund_policy.html")


def safety_standards(request):
    return render(request, "policy/safety_standards.html")
