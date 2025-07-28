from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class MessageRole(models.TextChoices):
    USER = 'user', 'User'         
    GIRL = 'girl', 'Girl'

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    participant_label = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.participant_label} ({self.user.username})"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='messages')
    role = models.CharField(max_length=10,choices=MessageRole.choices)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.role.capitalize()} | {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
