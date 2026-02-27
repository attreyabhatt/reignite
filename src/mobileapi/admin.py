from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Exists, Max, OuterRef, Q
from django.utils import timezone

from conversation.models import (
    ChatCredit,
    DegradationTier,
    DeviceDailyUsage,
    GuestTrial,
    LockedReply,
    MobileAppConfig,
    RecommendedOpener,
)
from mobileapi.models import MobileCopyEvent, MobileGenerationEvent


class MobileGuestTrial(GuestTrial):
    class Meta:
        proxy = True
        app_label = "mobileapi"
        verbose_name = "Guest Trial"
        verbose_name_plural = "Guest Trials"


class MobileDeviceDailyUsage(DeviceDailyUsage):
    class Meta:
        proxy = True
        app_label = "mobileapi"
        verbose_name = "Device Daily Usage"
        verbose_name_plural = "Device Daily Usage"


class MobileRecommendedOpener(RecommendedOpener):
    class Meta:
        proxy = True
        app_label = "mobileapi"
        verbose_name = "Recommended Opener"
        verbose_name_plural = "Recommended Openers"


class MobileAppConfigProxy(MobileAppConfig):
    class Meta:
        proxy = True
        app_label = "mobileapi"
        verbose_name = "Mobile App Config"
        verbose_name_plural = "Mobile App Config"


class MobileLockedReply(LockedReply):
    class Meta:
        proxy = True
        app_label = "mobileapi"
        verbose_name = "Locked Reply"
        verbose_name_plural = "Locked Replies"


class MobileSignupUser(User):
    class Meta:
        proxy = True
        app_label = "mobileapi"
        verbose_name = "Mobile Signup User"
        verbose_name_plural = "Mobile Signup List"


@admin.register(MobileGuestTrial)
class MobileGuestTrialAdmin(admin.ModelAdmin):
    list_display = ("guest_id", "ip_address", "credits_used", "trial_used", "last_seen")
    search_fields = ("guest_id", "ip_address")
    list_filter = ("trial_used", "last_seen")
    ordering = ("-last_seen",)


@admin.register(MobileDeviceDailyUsage)
class MobileDeviceDailyUsageAdmin(admin.ModelAdmin):
    list_display = ("device_hash", "day", "used_count", "last_seen")
    search_fields = ("device_hash",)
    list_filter = ("day",)
    ordering = ("-day", "-last_seen")


@admin.register(MobileRecommendedOpener)
class MobileRecommendedOpenerAdmin(admin.ModelAdmin):
    list_display = ("text", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("text", "why_it_works")
    ordering = ("sort_order", "id")


class DegradationTierInline(admin.TabularInline):
    model = DegradationTier
    extra = 1
    fields = ("tier_type", "sort_order", "threshold", "model", "thinking_level")
    ordering = ("tier_type", "sort_order")


@admin.register(MobileAppConfigProxy)
class MobileAppConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Free User Limits", {"fields": ("free_daily_credit_limit", "guest_lifetime_credits")}),
        ("Guest Models & Thinking", {"fields": (
            "free_reply_model", "free_reply_thinking",
            "free_opener_model", "free_opener_thinking",
        )}),
        ("Signed-In Non-Subscriber Models & Thinking", {"fields": (
            "registered_reply_model", "registered_reply_thinking",
            "registered_opener_model", "registered_opener_thinking",
        )}),
        ("OCR Thinking", {"fields": (
            "ocr_thinking",
        )}),
        ("Fallback & Legacy", {"fields": ("fallback_model", "subscriber_weekly_limit")}),
        ("Blur Settings", {"fields": ("blur_preview_word_count",)}),
    )
    inlines = [DegradationTierInline]

    def has_add_permission(self, request):
        return not MobileAppConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MobileLockedReply)
class MobileLockedReplyAdmin(admin.ModelAdmin):
    list_display = ("user", "reply_type", "unlocked", "created_at")
    list_filter = ("reply_type", "unlocked", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("reply_json", "preview")


@admin.register(MobileGenerationEvent)
class MobileGenerationEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action_type",
        "user_type",
        "user_or_guest",
        "model_used",
        "thinking_used",
        "total_tokens",
        "has_reply_ocr_text",
    )
    list_filter = ("action_type", "user_type", "source_type", "created_at")
    date_hierarchy = "created_at"
    search_fields = (
        "user__username",
        "user__email",
        "guest_id_hash",
        "model_used",
        "generated_json",
    )
    readonly_fields = (
        "created_at",
        "user",
        "guest_id_hash",
        "user_type",
        "action_type",
        "source_type",
        "model_used",
        "thinking_used",
        "input_tokens",
        "output_tokens",
        "thinking_tokens",
        "total_tokens",
        "generated_json",
        "reply_ocr_text",
        "metadata",
    )
    ordering = ("-created_at",)

    def user_or_guest(self, obj):
        if obj.user_id:
            return f"{obj.user.username} ({obj.user.email})".strip()
        return obj.guest_id_hash or "guest"

    def has_reply_ocr_text(self, obj):
        return bool((obj.reply_ocr_text or "").strip())

    has_reply_ocr_text.boolean = True


@admin.register(MobileCopyEvent)
class MobileCopyEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "copy_type",
        "user_type",
        "user_or_guest",
        "copied_text_preview",
        "has_reply_context",
    )
    list_filter = ("copy_type", "user_type", "created_at")
    date_hierarchy = "created_at"
    search_fields = (
        "user__username",
        "user__email",
        "guest_id_hash",
        "copied_text",
        "reply_context_ocr_text",
    )
    readonly_fields = (
        "created_at",
        "user",
        "guest_id_hash",
        "user_type",
        "copy_type",
        "copied_text",
        "reply_context_ocr_text",
        "generation_event",
    )
    ordering = ("-created_at",)

    def user_or_guest(self, obj):
        if obj.user_id:
            return f"{obj.user.username} ({obj.user.email})".strip()
        return obj.guest_id_hash or "guest"

    def copied_text_preview(self, obj):
        text = (obj.copied_text or "").strip()
        if len(text) <= 80:
            return text
        return f"{text[:80]}..."

    def has_reply_context(self, obj):
        return bool((obj.reply_context_ocr_text or "").strip())

    has_reply_context.boolean = True


class MobileSignupSubscriptionFilter(admin.SimpleListFilter):
    title = "subscription status"
    parameter_name = "subscription_status"

    def lookups(self, request, model_admin):
        return (
            ("subscribed", "Subscribed"),
            ("authenticated_non_subscribed", "Authenticated Non-Subscribed"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        value = self.value()
        if value == "subscribed":
            return queryset.filter(
                chat_credit__is_subscribed=True,
            ).filter(
                Q(chat_credit__subscription_expiry__isnull=True)
                | Q(chat_credit__subscription_expiry__gte=now)
            )
        if value == "authenticated_non_subscribed":
            return queryset.exclude(
                Q(chat_credit__is_subscribed=True)
                & (
                    Q(chat_credit__subscription_expiry__isnull=True)
                    | Q(chat_credit__subscription_expiry__gte=now)
                )
            )
        return queryset


@admin.register(MobileSignupUser)
class MobileSignupUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "subscription_status", "last_active", "date_joined")
    list_filter = (MobileSignupSubscriptionFilter, "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)

    def get_queryset(self, request):
        generation_exists = MobileGenerationEvent.objects.filter(user=OuterRef("pk"))
        copy_exists = MobileCopyEvent.objects.filter(user=OuterRef("pk"))

        return (
            super()
            .get_queryset(request)
            .select_related("chat_credit")
            .annotate(
                has_mobile_generation=Exists(generation_exists),
                has_mobile_copy=Exists(copy_exists),
                last_generation_at=Max("mobile_generation_events__created_at"),
                last_copy_at=Max("mobile_copy_events__created_at"),
            )
            .filter(Q(has_mobile_generation=True) | Q(has_mobile_copy=True))
        )

    def subscription_status(self, obj):
        chat_credit = getattr(obj, "chat_credit", None)
        if not isinstance(chat_credit, ChatCredit):
            return "authenticated_non_subscribed"

        if not chat_credit.is_subscribed:
            return "authenticated_non_subscribed"

        expiry = chat_credit.subscription_expiry
        if expiry and expiry < timezone.now():
            return "authenticated_non_subscribed"

        return "subscribed"

    def last_active(self, obj):
        generation_at = getattr(obj, "last_generation_at", None)
        copy_at = getattr(obj, "last_copy_at", None)

        if generation_at and copy_at:
            return generation_at if generation_at >= copy_at else copy_at
        return generation_at or copy_at

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
