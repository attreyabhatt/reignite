from django.contrib import admin
from .models import ChatCredit, Conversation, CreditPurchase

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

@admin.register(CreditPurchase)
class CreditPurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'credits_purchased', 'amount_paid', 'timestamp', 'transaction_id')
    search_fields = ('user__username', 'transaction_id')
    list_filter = ('timestamp',)
    list_select_related = ('user',)
