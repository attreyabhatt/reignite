from django.contrib import admin
from .models import ChatCredit, Conversation, CopyEvent, GuestTrial, TrialIP, RecommendedOpener

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


@admin.register(RecommendedOpener)
class RecommendedOpenerAdmin(admin.ModelAdmin):
    list_display = ('text', 'is_active', 'sort_order', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('text', 'why_it_works')
    ordering = ('sort_order', 'id')
