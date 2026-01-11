from django.contrib import admin
from django.urls import include, path
from conversation import views
from reignitehome.views import ajax_reply_home,home,privacy_policy,terms_and_conditions,refund_policy,contact_view,delete_account_request,safety_standards
from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('conversations/',include('conversation.urls')), 
    path('ajax-reply-home/', ajax_reply_home, name='ajax_reply_home'),
    path('accounts/', include('allauth.urls')),  
    path('pricing/', include('pricing.urls')), 
    path('api/', include('mobileapi.urls')), 
    
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
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
