from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from conversation.models import WebAppConfig
from reignitehome.models import TrialIP
from reignitehome.utils.ip_check import get_client_ip
from django.db.models import Count, Q

from seoapp.models import PickupCategory, PickupTopic
from seoapp.glossary_terms import GLOSSARY_BY_ALPHA
from seoapp.situation_pages import (
    get_situation_page,
    list_related_pages,
    list_situation_pages,
)


DEFAULT_TOOL_CONVERSATION_PLACEHOLDER = "you: hey, free thursday?\nher: (seen, no reply)"
DEFAULT_TOOL_UPLOAD_HINT = "Drag & drop a chat screenshot, or paste your convo below."


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


def _build_tool_config(**overrides):
    config = {
        "ui_variant": "default",
        "selected_situation": "stuck_after_reply",
        "prefill_text": "",
        "upload_hint": DEFAULT_TOOL_UPLOAD_HINT,
        "force_show_upload": False,
        "conversation_placeholder": DEFAULT_TOOL_CONVERSATION_PLACEHOLDER,
        "situation_label": "What's the situation?",
        "her_info_label": "Her Information (optional)",
        "upload_label": "Upload Screenshot",
        "submit_label": "Generate Replies",
        "show_credits": True,
        "credits_label": "Credits Remaining",
        "credits_note_class": "matte-credit-note mt-3 text-center",
        "her_info_placeholder": "Add anything that might help - her bio, hobbies, vibe, or her style.",
        "her_info_prefill": "",
        "wrapper_class": "grid grid-cols-1 lg:grid-cols-3 gap-6",
        "form_col_class": "lg:col-span-2",
        "aside_class": "",
        "suggestions_card_class": "matte-card-tight p-4 h-full",
        "response_heading": "Send-Ready Replies",
        "response_empty_template": "conversation/partials/response_empty.html",
        "sidebar_heading": "Browse All Situations",
        "sidebar_links": [],
    }
    for key, value in overrides.items():
        if value is None:
            continue
        config[key] = value
    return config


def _build_situation_sidebar_links(active_slug):
    links = []
    for page in list_situation_pages():
        links.append(
            {
                "href": reverse("situation_landing", kwargs={"slug": page["slug"]}),
                "label": page["sidebar_label"],
                "is_active": page["slug"] == active_slug,
            }
        )
    return links


def _split_pickup_heading(heading):
    value = str(heading or "").strip()
    if not value:
        return {"lead": "", "accent": "", "tail": ""}

    start = value.find("(")
    end = value.find(")", start + 1) if start != -1 else -1
    if start == -1 or end == -1:
        return {"lead": value, "accent": "", "tail": ""}

    return {
        "lead": value[:start].strip(),
        "accent": value[start + 1:end].strip(),
        "tail": value[end + 1:].strip(),
    }


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
    return render(request, "seoapp/situations/index.html", context)


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
            "meta_description": situation_page["meta_description"],
            "canonical_url": canonical_url,
            "og_title": situation_page["title"],
            "og_description": situation_page["meta_description"],
            "og_url": canonical_url,
            "tool_config": _build_tool_config(
                ui_variant="pickup",
                selected_situation=situation_page["situation"],
                prefill_text="",
                upload_hint=situation_page["upload_hint"],
                force_show_upload=bool(situation_page["force_show_upload"]),
                response_empty_template="conversation/partials/response_empty_pickup.html",
                wrapper_class="",
                form_col_class="",
                suggestions_card_class="",
                credits_note_class="mt-3 text-center text-[#D4AF37] text-sm font-semibold",
                sidebar_links=_build_situation_sidebar_links(situation_page["slug"]),
            ),
        }
    )
    return render(request, "seoapp/situations/landing.html", context)


@require_http_methods(["GET"])
def pickup_lines_index(request):
    canonical_url = request.build_absolute_uri(reverse("pickup_lines_index"))
    categories = (
        PickupCategory.objects
        .annotate(topic_count=Count("topics", filter=Q(topics__is_active=True)))
        .filter(topic_count__gt=0)
        .order_by("sort_order")
    )
    context = _build_guest_chat_context(request)
    context.update(
        {
            "categories": categories,
            "meta_description": (
                "Explore ultra-niche pickup line guides and open one tailored to your exact match context."
            ),
            "canonical_url": canonical_url,
            "og_title": "Pickup Lines Directory | TryAgainText",
            "og_description": (
                "Browse topic-specific pickup line pages and generate context-aware openers with AI."
            ),
            "og_url": canonical_url,
        }
    )
    return render(request, "seoapp/pickup_lines/index.html", context)


@require_http_methods(["GET"])
def pickup_category_detail(request, category_slug):
    try:
        category = PickupCategory.objects.get(slug=category_slug)
    except PickupCategory.DoesNotExist:
        raise Http404("Category not found.")
    topics = [
        t.to_dict()
        for t in PickupTopic.objects.filter(
            category=category, is_active=True
        ).select_related("category").order_by("sort_order", "keyword")
    ]
    if not topics:
        raise Http404("Category not found.")
    canonical_url = request.build_absolute_uri(
        reverse("pickup_category_detail", kwargs={"category_slug": category.slug})
    )
    context = _build_guest_chat_context(request)
    context.update(
        {
            "category": category,
            "pickup_topics": topics,
            "meta_description": f"Browse {len(topics)} {category.name} pickup line guides. Pick a topic and generate a custom opener from her exact profile vibe.",
            "canonical_url": canonical_url,
            "og_title": f"Best {category.name} Pickup Lines | TryAgainText",
            "og_description": f"Browse {len(topics)} ultra-niche {category.name} pickup line guides and generate context-aware openers with AI.",
            "og_url": canonical_url,
        }
    )
    return render(request, "seoapp/pickup_lines/category.html", context)


@require_http_methods(["GET"])
def pickup_line_detail(request, category_slug, topic_slug):
    try:
        topic_obj = (
            PickupTopic.objects
            .select_related("category")
            .get(category__slug=category_slug, slug=topic_slug, is_active=True)
        )
    except PickupTopic.DoesNotExist:
        raise Http404("Pickup line page not found.")
    pickup_topic = topic_obj.to_dict()

    canonical_url = request.build_absolute_uri(
        reverse(
            "pickup_line_detail",
            kwargs={
                "category_slug": pickup_topic["category_slug"],
                "topic_slug": pickup_topic["topic_slug"],
            },
        )
    )
    context = _build_guest_chat_context(request)
    context.update(
        {
            "pickup_topic": pickup_topic,
            "canonical_url": canonical_url,
            "meta_description": pickup_topic["meta_description"],
            "og_title": pickup_topic["title"],
            "og_description": pickup_topic["meta_description"],
            "og_url": canonical_url,
            "pickup_heading": _split_pickup_heading(pickup_topic.get("h1")),
            "tool_config": _build_tool_config(
                ui_variant="pickup",
                selected_situation="just_matched",
                prefill_text="",
                upload_hint=pickup_topic["upload_hint"],
                force_show_upload=True,
                response_empty_template="conversation/partials/response_empty_pickup.html",
                wrapper_class="",
                form_col_class="",
                suggestions_card_class="",
                credits_note_class="mt-3 text-center text-[#8F9BB3] text-xs font-semibold uppercase tracking-wide",
                her_info_prefill=pickup_topic.get("her_info_prefill", ""),
                situation_label="WHAT'S THE SITUATION?",
                her_info_label="HER INFORMATION (optional)",
                upload_label="UPLOAD CONVERSATION",
                submit_label="GENERATE REPLIES",
                response_heading="SEND-READY REPLIES",
            ),
        }
    )
    return render(request, "seoapp/pickup_lines/detail.html", context)

@require_http_methods(["GET"])
def glossary_view(request):
    canonical_url = request.build_absolute_uri()
    context = {
        "meta_description": "Straight definitions for every modern dating term — breadcrumbing, love bombing, situationship, orbiting, and more.",
        "og_title": "Dating Terms Glossary | TryAgainText",
        "og_description": "What does breadcrumbing mean? Orbiting? Situationship? Learn every dating term you need to know.",
        "og_url": canonical_url,
        "canonical_url": canonical_url,
        "glossary_terms": GLOSSARY_BY_ALPHA,
    }
    return render(request, "seoapp/glossary.html", context)
