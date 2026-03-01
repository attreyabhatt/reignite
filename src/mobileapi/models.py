from django.contrib.auth.models import User
from django.db import models


class MobileGenerationEvent(models.Model):
    class UserType(models.TextChoices):
        FREE = "free", "Free"
        AUTHENTICATED_NON_SUBSCRIBED = (
            "authenticated_non_subscribed",
            "Authenticated Non-Subscribed",
        )
        SUBSCRIBED = "subscribed", "Subscribed"

    class ActionType(models.TextChoices):
        REPLY = "reply", "Reply"
        OPENER = "opener", "Opener"

    class SourceType(models.TextChoices):
        AI = "ai", "AI"
        RECOMMENDED_STATIC = "recommended_static", "Recommended Static"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mobile_generation_events",
        db_index=True,
    )
    guest_id_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    user_type = models.CharField(max_length=32, choices=UserType.choices, db_index=True)
    action_type = models.CharField(max_length=16, choices=ActionType.choices, db_index=True)
    source_type = models.CharField(max_length=32, choices=SourceType.choices, db_index=True)
    model_used = models.CharField(max_length=120)
    thinking_used = models.CharField(max_length=20, null=True, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    thinking_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    generated_json = models.TextField()
    reply_ocr_text = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["guest_id_hash", "created_at"]),
            models.Index(fields=["user_type", "action_type", "created_at"]),
            models.Index(fields=["source_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        actor = self.user.username if self.user_id else (self.guest_id_hash or "guest")
        return f"{self.action_type} ({self.user_type}) by {actor}"


class MobileCopyEvent(models.Model):
    class UserType(models.TextChoices):
        FREE = "free", "Free"
        AUTHENTICATED_NON_SUBSCRIBED = (
            "authenticated_non_subscribed",
            "Authenticated Non-Subscribed",
        )
        SUBSCRIBED = "subscribed", "Subscribed"

    class CopyType(models.TextChoices):
        REPLY = "reply", "Reply"
        OPENER = "opener", "Opener"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mobile_copy_events",
        db_index=True,
    )
    guest_id_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    user_type = models.CharField(max_length=32, choices=UserType.choices, db_index=True)
    copy_type = models.CharField(max_length=16, choices=CopyType.choices, db_index=True)
    copied_text = models.TextField()
    reply_context_ocr_text = models.TextField(null=True, blank=True)
    generation_event = models.ForeignKey(
        MobileGenerationEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="copy_events",
        db_index=True,
    )

    class Meta:
        verbose_name = "Copy Event"
        verbose_name_plural = "Copy Events"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["guest_id_hash", "created_at"]),
            models.Index(fields=["user_type", "copy_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        actor = self.user.username if self.user_id else (self.guest_id_hash or "guest")
        return f"{self.copy_type} copy ({self.user_type}) by {actor}"


class MobileInstallAttributionEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mobile_install_attribution_events",
        db_index=True,
    )
    guest_id_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    install_referrer_raw = models.TextField(blank=True, default="")

    utm_source = models.CharField(max_length=120, blank=True, default="", db_index=True)
    utm_medium = models.CharField(max_length=120, blank=True, default="", db_index=True)
    utm_campaign = models.CharField(max_length=160, blank=True, default="", db_index=True)
    utm_content = models.CharField(max_length=160, blank=True, default="")
    utm_term = models.CharField(max_length=160, blank=True, default="")

    ffclid = models.UUIDField(null=True, blank=True, db_index=True)
    click_event = models.ForeignKey(
        "reignitehome.MarketingClickEvent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mobile_install_events",
        db_index=True,
    )

    install_begin_at = models.DateTimeField(null=True, blank=True, db_index=True)
    referrer_click_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_organic = models.BooleanField(default=False, db_index=True)
    app_version = models.CharField(max_length=50, blank=True, default="")

    idempotency_key = models.CharField(max_length=64, unique=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Install Attribution Event"
        verbose_name_plural = "Install Attribution Events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["created_at", "utm_source", "utm_campaign"],
                name="mobileapi_mi_created_utm_idx",
            ),
            models.Index(
                fields=["guest_id_hash", "created_at"],
                name="mobileapi_mi_guest_created_idx",
            ),
        ]

    def __str__(self):
        actor = self.user.username if self.user_id else (self.guest_id_hash or "guest")
        campaign = self.utm_campaign or "organic"
        return f"install attribution by {actor} ({campaign})"
