"""Public URLs must not depend on the hostname used to reach the application."""
import json
from django.conf import settings
from django.utils.encoding import iri_to_uri


def public_url(path="/"):
    return settings.PUBLIC_SITE_URL.rstrip("/") + "/" + iri_to_uri(path).lstrip("/")


def breadcrumb_json(items):
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": public_url(path)}
        for i, (name, path) in enumerate(items, 1)
    ]}
    return json.dumps(data).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
