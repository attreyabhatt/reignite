from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from reignitehome.views import (
    ajax_reply_home,
    community_create,
    community_home,
    community_post_page,
    contact_view,
    delete_account_request,
    flirtfix_redirect,
    home,
    privacy_policy,
    refund_policy,
    safety_standards,
    sitemap_xml,
    terms_and_conditions,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path("community/", community_home, name="community_home"),
    path("community/new/", community_create, name="community_create"),
    path(
        "community/posts/<int:post_id>/",
        community_post_page,
        name="community_post_page",
    ),
    path("", include("seoapp.urls")),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
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
