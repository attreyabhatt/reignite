from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class TrialIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    trial_used = models.BooleanField(default=False)
    credits_used = models.IntegerField(default=0)  # Track trial credits used

    def __str__(self):
        return f"{self.ip_address} - Trial: {'Used' if self.trial_used else 'Available'}"


class GuestTrial(models.Model):
    guest_id = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    trial_used = models.BooleanField(default=False)
    credits_used = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.guest_id} - Trial: {'Used' if self.trial_used else 'Available'}"

class ContactMessage(models.Model):
    REASON_CHOICES = [
        ('bug', 'Bug Report'),
        ('payment', 'Payments'),
        ('feedback', 'Feedback'),
        ('other', 'Other'),
    ]
    
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    title = models.CharField(max_length=100)
    subject = models.TextField()
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_reason_display()}: {self.title} from {self.email}"

class ChatCredit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_credit')
    balance = models.PositiveIntegerField(default=3)  # Start with 3 free credits
    signup_bonus_given = models.BooleanField(default=False)  # Track if signup bonus was given
    total_earned = models.PositiveIntegerField(default=3)  # Track total credits earned
    total_used = models.PositiveIntegerField(default=0)  # Track total credits used
    last_updated = models.DateTimeField(auto_now=True)
    # Mobile subscription state (does not affect web credit logic)
    is_subscribed = models.BooleanField(default=False)
    subscription_product_id = models.CharField(max_length=200, blank=True, null=True)
    subscription_platform = models.CharField(max_length=50, blank=True, null=True)
    subscription_expiry = models.DateTimeField(blank=True, null=True)
    subscription_auto_renewing = models.BooleanField(default=False)
    subscription_purchase_token = models.TextField(blank=True, null=True)
    subscription_last_checked = models.DateTimeField(blank=True, null=True)
    # Fair-use tracking for subscribers
    subscriber_weekly_actions = models.PositiveIntegerField(default=0)
    subscriber_weekly_reset_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.balance} credits"

    def use_credit(self):
        """Use one credit if available"""
        if self.balance > 0:
            self.balance -= 1
            self.total_used += 1
            self.save()
            return True
        return False

    def add_credits(self, amount, reason=""):
        """Add credits to user account"""
        self.balance += amount
        self.total_earned += amount
        self.save()

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    girl_title = models.CharField(max_length=255)
    content = models.TextField()
    situation = models.CharField(max_length=150)  # e.g. 'left_on_read'
    her_info = models.TextField(blank=True)       # Freeform input about her
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.girl_title} ({self.user.username})"

@receiver(post_save, sender=User)
def create_user_chat_credit(sender, instance, created, **kwargs):
    if created:
        ChatCredit.objects.create(
            user=instance, 
            balance=3,  # Only 3 credits for new signups
            signup_bonus_given=True,
            total_earned=3
        )
        
class CopyEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='copy_events')
    conversation = models.ForeignKey('Conversation', on_delete=models.SET_NULL, null=True, blank=True, related_name='copy_events')

    # snapshot of inputs at time of copy:
    situation = models.CharField(max_length=150)
    her_info = models.TextField(blank=True)
    conversation_text = models.TextField()   # the pasted chat (or OCR)
    copied_message = models.TextField()      # the suggestion the user copied

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        owner = self.user.username if self.user else "guest"
        return f"CopyEvent by {owner} @ {self.created_at:%Y-%m-%d %H:%M}"
