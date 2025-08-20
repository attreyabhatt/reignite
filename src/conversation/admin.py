from django.contrib import admin
from .models import ChatCredit, Conversation, CopyEvent

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

