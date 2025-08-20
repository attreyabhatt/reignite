from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class ChatCredit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_credit')
    balance = models.PositiveIntegerField(default=10)  # Start with 5 free credits
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.balance} credits"

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
        ChatCredit.objects.create(user=instance)
        
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