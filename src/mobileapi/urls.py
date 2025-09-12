from django.urls import path
from . import views

urlpatterns = [
    path("generate/", views.generate_text, name="generate_text"),
    path("extract-image/", views.extract_from_image, name="extract_from_image"),
]
