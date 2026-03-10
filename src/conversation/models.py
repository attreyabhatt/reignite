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


class DeviceDailyUsage(models.Model):
    """Per-device daily usage counter for free-user anti-smurf enforcement."""
    device_hash = models.CharField(max_length=64, db_index=True)
    day = models.DateField(db_index=True)
    used_count = models.PositiveIntegerField(default=0)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["device_hash", "day"],
                name="unique_device_hash_day_usage",
            ),
        ]

    def __str__(self):
        return f"{self.device_hash[:10]}... @ {self.day}: {self.used_count}"

class RecommendedOpener(models.Model):
    text = models.TextField()
    why_it_works = models.TextField(blank=True)
    image = models.ImageField(upload_to='recommended_openers/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    vault_unblurred_priority = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Optional admin priority for unlocked vault openers (1 = highest).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.text[:60]

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
    # Fair-use tracking for subscribers (legacy weekly)
    subscriber_weekly_actions = models.PositiveIntegerField(default=0)
    subscriber_weekly_reset_at = models.DateTimeField(blank=True, null=True)
    # Daily fair-use tracking for mobile subscribers
    subscriber_daily_openers = models.PositiveIntegerField(default=0)
    subscriber_daily_replies = models.PositiveIntegerField(default=0)
    subscriber_daily_reset_at = models.DateTimeField(blank=True, null=True)
    # Free user daily tracking (shared pool for replies + openers)
    free_daily_credits_used = models.PositiveIntegerField(default=0)
    free_daily_reset_at = models.DateTimeField(blank=True, null=True)

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
        
class MobileAppConfig(models.Model):
    """Singleton config - editable from Django admin. Only one row should exist."""

    COMMUNITY_SORT_CHOICES = [
        ('new', 'New'),
        ('hot', 'Hot'),
        ('top', 'Top'),
    ]

    # --- Free user limits ---
    free_daily_credit_limit = models.PositiveIntegerField(
        default=3, help_text="Daily shared credit pool for free registered users (replies + openers)"
    )
    guest_lifetime_credits = models.PositiveIntegerField(
        default=3, help_text="Lifetime credits for guest (unauthenticated) users"
    )

    subscriber_weekly_limit = models.PositiveIntegerField(
        default=400, help_text="Legacy weekly fair-use cap for subscribers"
    )

    # --- Community feed defaults ---
    community_default_sort = models.CharField(
        max_length=10,
        choices=COMMUNITY_SORT_CHOICES,
        default='new',
        help_text='Default community feed sort when clients do not pass a sort query param',
    )

    # --- Guest (unauthenticated) model selection ---
    free_reply_model = models.CharField(
        max_length=100, default="gemini-3-flash-preview",
        help_text="AI model for guest (unauthenticated) replies"
    )
    free_opener_model = models.CharField(
        max_length=100, default="gemini-3-flash-preview",
        help_text="AI model for guest (unauthenticated) openers"
    )
    # --- Signed-in non-subscriber model selection ---
    registered_reply_model = models.CharField(
        max_length=100, default="gemini-3-flash-preview",
        help_text="AI model for signed-in non-subscriber replies"
    )
    registered_opener_model = models.CharField(
        max_length=100, default="gemini-3-flash-preview",
        help_text="AI model for signed-in non-subscriber openers"
    )
    fallback_model = models.CharField(
        max_length=100, default="gpt-4.1-mini-2025-04-14",
        help_text="Fallback model (GPT) used after tier2 threshold"
    )

    # --- Guest thinking levels ---
    free_reply_thinking = models.CharField(
        max_length=20, default="high",
        help_text="Thinking level for guest replies (minimal/low/medium/high)"
    )
    free_opener_thinking = models.CharField(
        max_length=20, default="high",
        help_text="Thinking level for guest openers (minimal/low/medium/high)"
    )
    # --- Signed-in non-subscriber thinking levels ---
    registered_reply_thinking = models.CharField(
        max_length=20, default="high",
        help_text="Thinking level for signed-in non-subscriber replies (minimal/low/medium/high)"
    )
    registered_opener_thinking = models.CharField(
        max_length=20, default="high",
        help_text="Thinking level for signed-in non-subscriber openers (minimal/low/medium/high)"
    )
    ocr_thinking = models.CharField(
        max_length=20, default="low",
        help_text="Thinking level for OCR extraction (minimal/low/medium/high)"
    )

    # --- Blur settings ---
    blur_preview_word_count = models.PositiveIntegerField(
        default=3, help_text="Number of visible words shown before the locked block"
    )

    class Meta:
        verbose_name = "Mobile App Config"
        verbose_name_plural = "Mobile App Config"

    def __str__(self):
        return "Mobile App Configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Get or create the singleton config row."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WebAppConfig(models.Model):
    """Singleton config for web AI provider routing."""

    PROVIDER_GEMINI = "gemini"
    PROVIDER_GPT = "gpt"
    PROVIDER_CHOICES = [
        (PROVIDER_GEMINI, "Gemini"),
        (PROVIDER_GPT, "GPT"),
    ]

    primary_provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_GEMINI,
        help_text="Primary AI provider for webapp generation and OCR.",
    )
    guest_reply_limit = models.PositiveIntegerField(
        default=5,
        help_text="Free reply generations for unauthenticated web users.",
    )
    signup_bonus_credits = models.PositiveIntegerField(
        default=3,
        help_text="Free credits granted to newly signed-up web users.",
    )

    class Meta:
        verbose_name = "Web App Config"
        verbose_name_plural = "Web App Config"

    def __str__(self):
        return (
            f"Web App Configuration "
            f"(primary={self.primary_provider}, fallback={self.fallback_provider})"
        )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def fallback_provider(self) -> str:
        if self.primary_provider == self.PROVIDER_GPT:
            return self.PROVIDER_GEMINI
        return self.PROVIDER_GPT

    def provider_order(self):
        return [self.primary_provider, self.fallback_provider]

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DegradationTier(models.Model):
    """One row per degradation tier. Admin can add/remove/reorder."""
    TIER_TYPE_CHOICES = [
        ('opener', 'Opener'),
        ('reply', 'Reply'),
    ]
    config = models.ForeignKey(
        MobileAppConfig, on_delete=models.CASCADE, related_name='tiers'
    )
    tier_type = models.CharField(max_length=10, choices=TIER_TYPE_CHOICES)
    threshold = models.PositiveIntegerField(
        help_text="Use this model/thinking for requests 1..N (cumulative daily count)"
    )
    model = models.CharField(max_length=100, help_text="e.g. gemini-3-pro-preview, gemini-3-flash-preview")
    thinking_level = models.CharField(
        max_length=20, blank=True, default="high",
        help_text="minimal/low/medium/high. Leave blank for GPT models."
    )
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower = used first")

    class Meta:
        ordering = ['tier_type', 'sort_order', 'threshold']
        verbose_name = "Degradation Tier"

    def __str__(self):
        return f"{self.get_tier_type_display()} \u2264{self.threshold}: {self.model} ({self.thinking_level})"


class LockedReply(models.Model):
    """Stores one pending locked reply per user per day. Full text never sent to client until unlocked."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locked_replies')
    reply_json = models.TextField(help_text="Full AI-generated JSON array of suggestions")
    preview = models.JSONField(help_text="List of first N words per suggestion (sent to client)")
    reply_type = models.CharField(max_length=20, choices=[('reply', 'Reply'), ('opener', 'Opener')])
    created_at = models.DateTimeField(auto_now_add=True)
    unlocked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"LockedReply #{self.pk} for {self.user.username} ({'unlocked' if self.unlocked else 'locked'})"


class GuestWebConversationAttempt(models.Model):
    class Endpoint(models.TextChoices):
        CONVERSATIONS_AJAX_REPLY = "conversations_ajax_reply", "Conversations Ajax Reply"
        AJAX_REPLY_HOME = "ajax_reply_home", "Ajax Reply Home"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        VALIDATION_ERROR = "validation_error", "Validation Error"
        CREDITS_BLOCKED = "credits_blocked", "Credits Blocked"
        AI_ERROR = "ai_error", "AI Error"
        PARSE_ERROR = "parse_error", "Parse Error"
        REQUEST_ERROR = "request_error", "Request Error"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    session_key_hash = models.CharField(max_length=64, db_index=True)
    endpoint = models.CharField(max_length=64, choices=Endpoint.choices, db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, db_index=True)
    http_status = models.PositiveSmallIntegerField()
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["endpoint", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.endpoint} {self.status} ({self.http_status})"


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
