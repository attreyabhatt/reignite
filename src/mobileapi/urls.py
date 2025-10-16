from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("register/", views.register, name="mobile_register"),
    path("login/", views.login, name="mobile_login"),
    path("profile/", views.profile, name="mobile_profile"),
    
    # Generation with credits
    path("generate/", views.generate_text_with_credits, name="generate_text_with_credits"),
    path("extract-image/", views.extract_from_image_with_credits, name="extract_from_image_with_credits"),
    path("analyze-profile/", views.analyze_profile, name="analyze_profile"),
]