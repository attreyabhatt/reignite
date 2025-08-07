from django.contrib import admin
from .models import CreditPurchase

@admin.register(CreditPurchase)
class CreditPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "credits_purchased",
        "amount_paid",
        "payment_status",
        "payment_provider",
        "timestamp",
        "transaction_id",
    )
    list_filter = (
        "payment_status",
        "payment_provider",
        "timestamp",
    )
    search_fields = (
        "user__username",
        "user__email",
        "transaction_id",
    )
    readonly_fields = (
        "user",
        "credits_purchased",
        "amount_paid",
        "payment_status",
        "payment_provider",
        "timestamp",
        "transaction_id",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        # Prevent manual creation — all purchases should come from webhook or checkout
        return False
