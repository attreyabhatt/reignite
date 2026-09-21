"""A click-cohort funnel using existing, server-recorded mobile events."""
from datetime import timedelta

from django.db.models import Count, DateTimeField, Exists, ExpressionWrapper, OuterRef, Q
from django.utils import timezone

from mobileapi.models import MobileCopyEvent, MobileGenerationEvent, MobileInstallAttributionEvent
from reignitehome.models import MarketingClickEvent


GROUPS = {
    "campaign": ("utm_source", "utm_campaign"),
    "page": ("utm_source", "utm_term"),
    "placement": ("utm_source", "utm_campaign", "utm_content"),
}


def growth_funnel(*, days=28, group="campaign", now=None):
    if days not in (7, 28, 90) or group not in GROUPS:
        raise ValueError("Choose 7, 28 or 90 days and a valid grouping.")
    now = now or timezone.now()
    since = now - timedelta(days=days)
    identity = (Q(user_id=OuterRef("user_id"), user_id__isnull=False)
                | (Q(guest_id_hash=OuterRef("guest_id_hash"), guest_id_hash__isnull=False)
                   & ~Q(guest_id_hash="")))
    activity_window = {
        "created_at__gte": OuterRef("created_at"),
        "created_at__lt": ExpressionWrapper(OuterRef("created_at") + timedelta(days=7), output_field=DateTimeField()),
        "created_at__lte": now,
    }
    generated = MobileGenerationEvent.objects.filter(
        identity, **activity_window,
        action_type__in=["reply", "opener"], source_type="ai",
    )
    copied = MobileCopyEvent.objects.filter(identity, **activity_window)
    installs = MobileInstallAttributionEvent.objects.filter(
        click_event_id=OuterRef("pk"), created_at__gte=OuterRef("created_at"),
        created_at__lt=ExpressionWrapper(OuterRef("created_at") + timedelta(days=7), output_field=DateTimeField()),
        created_at__lte=now,
    ).annotate(generated=Exists(generated), copied=Exists(copied))
    clicks = MarketingClickEvent.objects.filter(
        route_key="flirtfix", created_at__gte=since, created_at__lte=now,
    ).annotate(
        installed=Exists(installs),
        activated=Exists(installs.filter(Q(generated=True) | Q(copied=True))),
        copied=Exists(installs.filter(copied=True)),
    )
    counts = {
        "clicks": Count("pk"),
        "installed": Count("pk", filter=Q(installed=True)),
        "activated": Count("pk", filter=Q(activated=True)),
        "copied": Count("pk", filter=Q(copied=True)),
        "mature": Count("pk", filter=Q(created_at__lte=now - timedelta(days=14))),
    }

    def with_rates(row):
        row["install_rate"] = round(100 * row["installed"] / row["clicks"], 1) if row["clicks"] else 0
        row["activation_rate"] = round(100 * row["activated"] / row["installed"], 1) if row["installed"] else 0
        return row

    rows = []
    for row in clicks.order_by().values(*GROUPS[group]).annotate(**counts).order_by("-clicks", *GROUPS[group]):
        row["label"] = " / ".join(row[field] or "(not supplied)" for field in GROUPS[group])
        rows.append(with_rates(row))
    totals = {field: sum(row[field] for row in rows) for field in counts}
    return {"rows": rows, "totals": with_rates(totals),
            "days": days, "group": group, "since": since, "as_of": now}
