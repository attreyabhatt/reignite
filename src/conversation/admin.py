from django.contrib import admin
from .models import (
    ChatCredit,
    Conversation,
    CopyEvent,
    GuestWebConversationAttempt,
    WebAppConfig,
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


@admin.register(GuestWebConversationAttempt)
class GuestWebConversationAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "endpoint",
        "status",
        "http_status",
        "session_key_hash",
    )
    list_filter = ("endpoint", "status", "http_status", "created_at")
    search_fields = ("session_key_hash", "error_message")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at",
        "session_key_hash",
        "endpoint",
        "status",
        "http_status",
        "input_payload",
        "output_payload",
        "error_message",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(WebAppConfig)
class WebAppConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Free Usage", {"fields": ("guest_reply_limit", "signup_bonus_credits")}),
        ("Provider Routing", {"fields": ("primary_provider", "fallback_provider_display")}),
    )
    readonly_fields = ("fallback_provider_display",)

    def fallback_provider_display(self, obj):
        if not obj:
            return WebAppConfig.PROVIDER_GPT
        return obj.fallback_provider
    fallback_provider_display.short_description = "Fallback Provider"

    def has_add_permission(self, request):
        return not WebAppConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
