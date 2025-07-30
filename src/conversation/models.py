from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class ChatCredit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_credit')
    balance = models.PositiveIntegerField(default=5)  # Start with 5 free credits
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.balance} credits"

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    girl_title = models.CharField(max_length=255)
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.girl_title} ({self.user.username})"

class CreditPurchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_purchases')
    credits_purchased = models.PositiveIntegerField()
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)  # Store PayPal/Stripe txn id

    def __str__(self):
        return f"{self.user.username}: {self.credits_purchased} credits for ${self.amount_paid} on {self.timestamp}"


@receiver(post_save, sender=User)
def create_user_chat_credit(sender, instance, created, **kwargs):
    if created:
        ChatCredit.objects.create(user=instance)