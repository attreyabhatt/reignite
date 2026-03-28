from django.contrib import admin

from seoapp.models import PickupCategory, PickupTopic


@admin.register(PickupCategory)
class PickupCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "topic_count", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")

    def topic_count(self, obj):
        return obj.topics.count()

    topic_count.short_description = "Topics"


@admin.register(PickupTopic)
class PickupTopicAdmin(admin.ModelAdmin):
    list_display = ("keyword", "category", "slug", "is_active", "sort_order")
    list_filter = ("category", "is_active")
    search_fields = ("keyword", "slug")
    list_select_related = ("category",)
    ordering = ("category__sort_order", "sort_order", "keyword")
    fieldsets = (
        ("Basic Info", {
            "fields": ("category", "slug", "keyword", "is_active", "sort_order"),
        }),
        ("SEO Fields", {
            "fields": ("h1", "title", "meta_description", "seo_intro"),
        }),
        ("Pickup Lines", {
            "fields": ("witty_lines", "flirty_lines", "cheesy_lines"),
        }),
        ("AI Tool Config", {
            "fields": ("prefill_text", "upload_hint", "her_info_prefill"),
        }),
    )
