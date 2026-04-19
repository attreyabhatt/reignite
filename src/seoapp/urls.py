from django.urls import path

from seoapp.views import (
    glossary_view,
    pickup_category_detail,
    pickup_line_detail,
    pickup_lines_index,
    situation_index,
    situation_landing,
)


urlpatterns = [
    path('pickup-lines/', pickup_lines_index, name='pickup_lines_index'),
    path(
        'pickup-lines/<slug:category_slug>/',
        pickup_category_detail,
        name='pickup_category_detail',
    ),
    path(
        'pickup-lines/<slug:category_slug>/<slug:topic_slug>/',
        pickup_line_detail,
        name='pickup_line_detail',
    ),
    path('situations/', situation_index, name='situation_index'),
    path('situations/<slug:slug>/', situation_landing, name='situation_landing'),
    path('glossary/', glossary_view, name='glossary'),
]
