"""Observed web milestones; purchases come from completed Dodo records."""
from datetime import timedelta, timezone as dt_timezone

from django.db.models import Min, Q
from django.utils import timezone

from pricing.models import CreditPurchase
from .models import WebConversionEvent, GuestWebConversationAttempt, CopyEvent
from .web_conversion import EXPERIMENT


def web_conversion_report(days=28, now=None):
    if days not in (7, 28, 90):
        raise ValueError("Choose 7, 28 or 90 days.")
    now = now or timezone.now()
    since = now - timedelta(days=days)
    events = WebConversionEvent.objects.exclude(Q(user__is_staff=True) | Q(user__is_superuser=True))
    period = list(events.filter(created_at__gte=since, created_at__lte=now).values(
        "kind", "created_at", "journey_id", "user_id", "origin_path", "situation", "was_guest"))

    def actor(row):
        return ("account", row["user_id"]) if row["user_id"] else ("guest", row["journey_id"])

    starts = events.filter(kind="generated", was_guest=True, created_at__lte=now).values(
        "journey_id", "user_id").annotate(first_at=Min("created_at"))
    first = {}
    for row in starts:
        key = actor(row)
        first[key] = min(first.get(key, row["first_at"]), row["first_at"])
    cohorts = {key: {"start": at, "generated": True, "copied": False, "signup": False,
                     "returned": False, "checkout": False, "purchased": False}
               for key, at in first.items() if since <= at <= now}
    for row in period:
        cohort = cohorts.get(actor(row))
        if not cohort or not cohort["start"] <= row["created_at"] < cohort["start"] + timedelta(days=7):
            continue
        if row["kind"] in ("copied", "signup", "checkout"):
            cohort[row["kind"]] = True
        if (row["kind"] == "generated" and row["created_at"].astimezone(dt_timezone.utc).date()
                > cohort["start"].astimezone(dt_timezone.utc).date()):
            cohort["returned"] = True

    # A repeated webhook transaction must not inflate buyers or revenue reports.
    seen_transactions, first_purchases, purchases = set(), {}, []
    payment_rows = CreditPurchase.objects.filter(payment_provider="dodo", payment_status="COMPLETED",
        timestamp__lte=now).exclude(Q(user__is_staff=True) | Q(user__is_superuser=True)).order_by("timestamp", "pk").values(
        "id", "transaction_id", "user_id", "timestamp", "credits_purchased")
    for payment in payment_rows:
        key = payment["transaction_id"] or f"legacy-row:{payment['id']}"
        if key in seen_transactions:
            continue
        seen_transactions.add(key)
        first_purchases.setdefault(payment["user_id"], payment)
        if payment["timestamp"] >= since:
            purchases.append(payment)
    for user_id, payment in first_purchases.items():
        cohort = cohorts.get(("account", user_id))
        if cohort and cohort["start"] <= payment["timestamp"] < cohort["start"] + timedelta(days=7):
            cohort["purchased"] = True

    mature = [c for c in cohorts.values() if c["start"] <= now - timedelta(days=7)]
    labels = [("generated", "Generated successfully"), ("copied", "Copied a suggestion"),
              ("signup", "Completed signup"), ("returned", "Generated on a later date"),
              ("checkout", "Reached a checkout redirect"), ("purchased", "Made a first website purchase")]
    milestones = []
    for key, label in labels:
        complete = sum(c[key] for c in mature)
        milestones.append({"label": label, "count": sum(c[key] for c in cohorts.values()),
                           "mature_count": complete,
                           "rate": round(100 * complete / len(mature), 1) if mature else None})
    totals = {kind: sum(r["kind"] == kind for r in period) for kind, _ in WebConversionEvent.Kind.choices}
    recent_first = [p for p in first_purchases.values() if p["timestamp"] >= since]
    matched_buyers = sum(c["purchased"] for c in cohorts.values())
    page_rows = {}
    for row in period:
        if row["kind"] != "generated":
            continue
        key = (row["origin_path"] or "Not recorded", row["situation"] or "Not recorded")
        page_rows[key] = page_rows.get(key, 0) + 1
    return {"experiment": EXPERIMENT, "days": days, "since": since, "as_of": now,
            "tracking_started": events.aggregate(at=Min("created_at"))["at"],
            "milestones": milestones, "cohort_count": len(cohorts), "mature_count": len(mature),
            "totals": totals, "purchase_count": len(purchases), "first_buyers": len(recent_first),
            "guest_session_count": len({r["journey_id"] for r in period if r["kind"] == "generated" and r["was_guest"]}),
            "unmatched_buyers": len(recent_first) - matched_buyers,
            "pages": [{"path": k[0], "situation": k[1], "count": v}
                      for k, v in sorted(page_rows.items(), key=lambda item: -item[1])[:30]],
            "legacy_generations": GuestWebConversationAttempt.objects.filter(status="success",
                created_at__gte=since, created_at__lte=now).count(),
            "legacy_copies": CopyEvent.objects.filter(created_at__gte=since, created_at__lte=now)
                .exclude(Q(user__is_staff=True) | Q(user__is_superuser=True)).count()}
