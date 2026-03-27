from django.urls import path

from seoapp.views import (
    pickup_line_detail,
    pickup_lines_index,
    situation_index,
    situation_landing,
)


urlpatterns = [
    path('pickup-lines/', pickup_lines_index, name='pickup_lines_index'),
    path(
        'pickup-lines/<slug:category_slug>/<slug:topic_slug>/',
        pickup_line_detail,
        name='pickup_line_detail',
    ),
    path('situations/', situation_index, name='situation_index'),
    path('situations/<slug:slug>/', situation_landing, name='situation_landing'),
]
