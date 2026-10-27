from datetime import date
from django.conf import settings
from django.core.checks import Error, register


@register()
def publication_settings(app_configs, **kwargs):
    if not settings.SEO_GUIDES_PUBLISHED_ON:
        return []
    try:
        date.fromisoformat(settings.SEO_GUIDES_PUBLISHED_ON)
    except (ValueError, TypeError):
        return [Error('SEO_GUIDES_PUBLISHED_ON must be blank or an ISO date (YYYY-MM-DD).', id='seoapp.E001')]
    return []
