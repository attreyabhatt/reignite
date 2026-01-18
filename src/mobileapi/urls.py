from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("register/", views.register, name="mobile_register"),
    path("login/", views.login, name="mobile_login"),
    path("password-reset/", views.password_reset, name="mobile_password_reset"),
    path("change-password/", views.change_password, name="mobile_change_password"),
    path("google-play/purchase/", views.google_play_purchase, name="google_play_purchase"),
    path("payment-history/", views.payment_history, name="mobile_payment_history"),
    path("profile/", views.profile, name="mobile_profile"),
    
    # Generation with credits
    path("generate/", views.generate_text_with_credits, name="generate_text_with_credits"),
    path("extract-image/", views.extract_from_image_with_credits, name="extract_from_image_with_credits"),
    path("extract-image-stream/", views.extract_from_image_with_credits_stream, name="extract_from_image_with_credits_stream"),
    path("analyze-profile/", views.analyze_profile, name="analyze_profile"),
    path("analyze-profile-stream/", views.analyze_profile_stream, name="analyze_profile_stream"),
    path("report/", views.report_issue, name="report_issue"),
]
