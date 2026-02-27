from django.contrib import admin

from conversation.models import (
    DegradationTier,
    DeviceDailyUsage,
    GuestTrial,
    LockedReply,
    MobileAppConfig,
    RecommendedOpener,
)


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
