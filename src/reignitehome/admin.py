from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path

from .growth import GROUPS, growth_funnel

from .models import ContactMessage, MarketingClickEvent, TrialIP

admin.site.register(ContactMessage)
User = get_user_model()
admin.site.unregister(User)

@admin.register(TrialIP)
class TrialIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'trial_used', 'first_seen')
    search_fields = ('ip_address',)
    list_filter = ('trial_used', 'first_seen')


@admin.register(MarketingClickEvent)
class MarketingClickEventAdmin(admin.ModelAdmin):
    change_list_template = "admin/reignitehome/marketingclickevent/change_list.html"

    def get_urls(self):
        return [path("funnel/", self.admin_site.admin_view(self.funnel_view),
                     name="reignitehome_marketingclickevent_funnel")] + super().get_urls()

    def funnel_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        days = request.GET.get("days", "28")
        group = request.GET.get("group", "campaign")
        if days not in {"7", "28", "90"} or group not in GROUPS:
            return TemplateResponse(request, "admin/reignitehome/marketingclickevent/funnel.html", {
                **self.admin_site.each_context(request), "title": "Acquisition funnel",
                "error": "Choose 7, 28 or 90 days and a valid grouping.",
            }, status=400)
        return TemplateResponse(request, "admin/reignitehome/marketingclickevent/funnel.html", {
            **self.admin_site.each_context(request), "title": "Acquisition funnel",
            **growth_funnel(days=int(days), group=group),
        })

    list_display = (
        "created_at",
        "route_key",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "referrer_host",
        "click_id",
    )
    search_fields = ("click_id", "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
    list_filter = ("route_key", "utm_source", "utm_medium", "utm_campaign", "created_at")
    readonly_fields = (
        "created_at",
        "route_key",
        "click_id",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "referrer_host",
        "ip_hash",
        "user_agent",
        "target_url",
        "raw_query",
    )
    ordering = ("-created_at",)

@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    list_display = ("username", "email", "last_login", "date_joined")
    list_filter = ("last_login", "date_joined")  # add your filters here
