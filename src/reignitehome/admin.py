from django.contrib import admin
from .models import TrialIP,ContactMessage
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

admin.site.register(ContactMessage)
User = get_user_model()
admin.site.unregister(User)

@admin.register(TrialIP)
class TrialIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'trial_used', 'first_seen')
    search_fields = ('ip_address',)
    list_filter = ('trial_used', 'first_seen')

@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    list_display = ("username", "email", "last_login", "date_joined")
    list_filter = ("last_login", "date_joined")  # add your filters here
