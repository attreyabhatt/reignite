from django.contrib import admin
from django.urls import include, path, re_path
from conversation import views
from reignitehome.views import ajax_reply_home,home,privacy_policy,terms_and_conditions,refund_policy,contact_view,delete_account_request,safety_standards
from django.views.generic import RedirectView, TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    re_path(
        r'^flirtfix/?$',
        RedirectView.as_view(
            url=(
                "https://play.google.com/store/apps/details?id=com.tryagaintext.flirtfix"
                "&hl=en_IN&referrer=utm_source%%3Dinstagram%%26utm_medium%%3Dbio"
                "%%26utm_campaign%%3Dflirtfix_instagram_bio"
            ),
            permanent=True,
            query_string=False,
        ),
        name='flirtfix_redirect',
    ),
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
