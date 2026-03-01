from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from reignitehome.views import (
    ajax_reply_home,
    contact_view,
    delete_account_request,
    flirtfix_redirect,
    home,
    privacy_policy,
    refund_policy,
    safety_standards,
    terms_and_conditions,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    re_path(r'^flirtfix/?$', flirtfix_redirect, name='flirtfix_redirect'),
    path('conversations/',include('conversation.urls')), 
    path('ajax-reply-home/', ajax_reply_home, name='ajax_reply_home'),
    path('accounts/', include('allauth.urls')),  
    path('pricing/', include('pricing.urls')), 
    path('api/', include('mobileapi.urls')), 
    
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    # ScreenClean mobile app privacy policy route
    path(
        'policy/screenclean/',
        TemplateView.as_view(template_name='policy/screenclean/policy.html'),
        name='screenclean_privacy_policy',
    ),
    path('terms/', terms_and_conditions, name='terms_and_conditions'),
    path('refund-policy/', refund_policy, name='refund_policy'),
    path('contact/', contact_view, name='contact'),
    path('delete-account/', delete_account_request, name='delete_account_request'),
    path('safety-standards/', safety_standards, name='safety_standards'),
    
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    

    
]
