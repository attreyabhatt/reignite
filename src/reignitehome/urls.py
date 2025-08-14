"""
URL configuration for reignitehome project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from conversation import views
from reignitehome.views import ajax_reply_home,home,privacy_policy,terms_and_conditions,refund_policy,contact_view
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('conversations/',include('conversation.urls')), 
    path('ajax-reply-home/', ajax_reply_home, name='ajax_reply_home'),
    path('accounts/', include('allauth.urls')),  
    path('pricing/', include('pricing.urls')), 
    
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('terms/', terms_and_conditions, name='terms_and_conditions'),
    path('refund-policy/', refund_policy, name='refund_policy'),
    path('contact/', contact_view, name='contact'),
    
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    
]
