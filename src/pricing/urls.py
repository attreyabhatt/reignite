from django.urls import include, path
from .views import pricing_home

urlpatterns = [ 
    path('', pricing_home, name='pricing_home'),
]