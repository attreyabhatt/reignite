from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    path('', views.pricing, name='pricing'),
    path('purchase/<int:amount>/', views.purchase_credits, name='purchase'),
    path('webhook/dodo/', views.dodo_webhook, name='webhook'),
]
