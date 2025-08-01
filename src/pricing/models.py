from django.db import models
from django.conf import settings

class CreditPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_purchases')
    credits_purchased = models.PositiveIntegerField()
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)  # e.g., Stripe/PayPal ID
    payment_status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')],
        default='PENDING'
    )
    payment_provider = models.CharField(max_length=30, blank=True, null=True)  # 'stripe', 'paypal', etc.

    def __str__(self):
        return f"{self.user.username}: {self.credits_purchased} credits for ${self.amount_paid} ({self.payment_status})"

    class Meta:
        ordering = ['-timestamp']

