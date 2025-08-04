from django.db import models

class TrialIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    trial_used = models.BooleanField(default=False)

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
