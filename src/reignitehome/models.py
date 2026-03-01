import uuid

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


class MarketingClickEvent(models.Model):
    route_key = models.CharField(max_length=50, db_index=True)
    click_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    utm_source = models.CharField(max_length=120, blank=True, default="", db_index=True)
    utm_medium = models.CharField(max_length=120, blank=True, default="", db_index=True)
    utm_campaign = models.CharField(max_length=160, blank=True, default="", db_index=True)
    utm_content = models.CharField(max_length=160, blank=True, default="")
    utm_term = models.CharField(max_length=160, blank=True, default="")

    referrer_host = models.CharField(max_length=255, blank=True, default="", db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")

    target_url = models.URLField(max_length=500)
    raw_query = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["route_key", "created_at"],
                name="rh_mclick_route_created_idx",
            ),
            models.Index(
                fields=["utm_source", "utm_campaign", "created_at"],
                name="rh_mclick_src_campaign_idx",
            ),
        ]

    def __str__(self):
        source = self.utm_source or "unknown"
        campaign = self.utm_campaign or "unknown"
        return f"{self.route_key} click {self.click_id} ({source}/{campaign})"
