from django.urls import path
from . import views
from . import community_views

urlpatterns = [
    # Authentication
    path("register/", views.register, name="mobile_register"),
    path("login/", views.login, name="mobile_login"),
    path("password-reset/", views.password_reset, name="mobile_password_reset"),
    path("change-password/", views.change_password, name="mobile_change_password"),
    path("delete-account/", views.delete_account, name="mobile_delete_account"),
    path("google-play/purchase/", views.google_play_purchase, name="google_play_purchase"),
    path("google-play/verify-subscription/", views.verify_subscription, name="verify_subscription"),
    path("payment-history/", views.payment_history, name="mobile_payment_history"),
    path("profile/", views.profile, name="mobile_profile"),
    
    # Generation with credits
    path("generate/", views.generate_text_with_credits, name="generate_text_with_credits"),
    path("generate-openers-from-image/", views.generate_openers_from_profile_image, name="generate_openers_from_image"),
    path("unlock-reply/", views.unlock_reply, name="unlock_reply"),
    path("recommended-openers/", views.recommended_openers, name="recommended_openers"),
    path("copy-event/", views.copy_event, name="mobile_copy_event"),
    path("install-attribution/", views.install_attribution, name="mobile_install_attribution"),
    path("extract-image/", views.extract_from_image_with_credits, name="extract_from_image_with_credits"),
    path("extract-image-stream/", views.extract_from_image_with_credits_stream, name="extract_from_image_with_credits_stream"),
    path("analyze-profile/", views.analyze_profile, name="analyze_profile"),
    path("analyze-profile-stream/", views.analyze_profile_stream, name="analyze_profile_stream"),
    path("report/", views.report_issue, name="report_issue"),

    # Community
    path("community/posts/", community_views.community_post_list, name="community_post_list"),
    path("community/posts/<int:post_id>/", community_views.community_post_detail, name="community_post_detail"),
    path("community/posts/<int:post_id>/vote/", community_views.community_post_vote, name="community_post_vote"),
    path("community/posts/<int:post_id>/comments/", community_views.community_post_comment, name="community_post_comment"),
    path("community/comments/<int:comment_id>/delete/", community_views.community_comment_delete, name="community_comment_delete"),
    path("community/comments/<int:comment_id>/like/", community_views.community_comment_like, name="community_comment_like"),
]
