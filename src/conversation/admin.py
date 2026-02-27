from django.contrib import admin
from .models import (
    ChatCredit,
    Conversation,
    CopyEvent,
    GuestTrial,
    TrialIP,
    DeviceDailyUsage,
    RecommendedOpener,
    MobileAppConfig,
    DegradationTier,
    LockedReply,
)

@admin.register(ChatCredit)
class ChatCreditAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'last_updated')
    search_fields = ('user__username',)
    list_select_related = ('user',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('girl_title', 'user', 'last_updated')
    search_fields = ('girl_title', 'user__username')
    list_filter = ('last_updated',)
    list_select_related = ('user',)
    
@admin.register(CopyEvent)
class CopyEventAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'conversation', 'situation', 'created_at')
    search_fields = ('user__username', 'situation', 'copied_message', 'conversation_text')
    list_filter = ('situation', 'created_at')
    list_select_related = ('user', 'conversation')

    def get_username(self, obj):
        return obj.user.username if obj.user else "guest"
    get_username.short_description = 'User'


@admin.register(GuestTrial)
class GuestTrialAdmin(admin.ModelAdmin):
    list_display = ('guest_id', 'ip_address', 'credits_used', 'trial_used', 'last_seen')
    search_fields = ('guest_id', 'ip_address')
    list_filter = ('trial_used', 'last_seen')


@admin.register(TrialIP)
class TrialIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'credits_used', 'trial_used', 'first_seen')
    search_fields = ('ip_address',)
    list_filter = ('trial_used', 'first_seen')


@admin.register(DeviceDailyUsage)
class DeviceDailyUsageAdmin(admin.ModelAdmin):
    list_display = ('device_hash', 'day', 'used_count', 'last_seen')
    search_fields = ('device_hash',)
    list_filter = ('day',)


@admin.register(RecommendedOpener)
class RecommendedOpenerAdmin(admin.ModelAdmin):
    list_display = ('text', 'is_active', 'sort_order', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('text', 'why_it_works')
    ordering = ('sort_order', 'id')


class DegradationTierInline(admin.TabularInline):
    model = DegradationTier
    extra = 1
    fields = ('tier_type', 'sort_order', 'threshold', 'model', 'thinking_level')
    ordering = ('tier_type', 'sort_order')


@admin.register(MobileAppConfig)
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


@admin.register(LockedReply)
class LockedReplyAdmin(admin.ModelAdmin):
    list_display = ('user', 'reply_type', 'unlocked', 'created_at')
    list_filter = ('reply_type', 'unlocked', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('reply_json', 'preview')
