from django.db import models


class PickupCategory(models.Model):
    slug = models.SlugField(max_length=80, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "pickup categories"

    def __str__(self):
        return self.name


class PickupTopic(models.Model):
    category = models.ForeignKey(
        PickupCategory,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    slug = models.SlugField(max_length=120, db_index=True)
    keyword = models.CharField(max_length=200)
    h1 = models.CharField(max_length=300)
    title = models.CharField(max_length=300)
    meta_description = models.TextField()
    seo_intro = models.TextField()
    witty_lines = models.JSONField(default=list)
    flirty_lines = models.JSONField(default=list)
    cheesy_lines = models.JSONField(default=list)
    prefill_text = models.TextField()
    upload_hint = models.TextField()
    her_info_prefill = models.TextField(blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "slug"],
                name="unique_category_topic_slug",
            ),
        ]
        ordering = ["category__sort_order", "sort_order", "keyword"]

    def __str__(self):
        return f"{self.keyword} ({self.category.name})"

    def to_dict(self):
        return {
            "category_slug": self.category.slug,
            "category_name": self.category.name,
            "topic_slug": self.slug,
            "keyword": self.keyword,
            "h1": self.h1,
            "title": self.title,
            "meta_description": self.meta_description,
            "seo_intro": self.seo_intro,
            "witty_lines": self.witty_lines,
            "flirty_lines": self.flirty_lines,
            "cheesy_lines": self.cheesy_lines,
            "prefill_text": self.prefill_text,
            "upload_hint": self.upload_hint,
            "her_info_prefill": self.her_info_prefill,
        }
