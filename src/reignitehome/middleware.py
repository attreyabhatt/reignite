from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponsePermanentRedirect

from reignitehome.seo import public_url


class PublicCanonicalHostMiddleware:
    """Consolidate public discovery URLs without moving API, auth or payment flows."""
    public_roots = {
        "", "pickup-lines", "situations", "glossary", "privacy-policy", "terms",
        "refund-policy", "safety-standards", "policy", "robots.txt", "sitemap.xml",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        canonical_host = urlsplit(settings.PUBLIC_SITE_URL).hostname
        root = request.path.strip("/").split("/")[0]
        if (request.method in {"GET", "HEAD"}
                and host in {"tryagaintext.com", "www.tryagaintext.com"}
                and host != canonical_host and root in self.public_roots):
            return HttpResponsePermanentRedirect(public_url(request.get_full_path()))
        return self.get_response(request)
