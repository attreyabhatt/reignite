from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from reignitehome.middleware import PublicCanonicalHostMiddleware
from reignitehome.seo import public_url


@override_settings(ALLOWED_HOSTS=["tryagaintext.com", "www.tryagaintext.com", "localhost", "testserver"])
class PublicCanonicalTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PublicCanonicalHostMiddleware(lambda request: HttpResponse("unchanged"))

    def test_public_redirect_preserves_path_and_tracking(self):
        for method in ("get", "head"):
            request = getattr(self.factory, method)("/pickup-lines/professions/lawyer/?utm_source=instagram&utm_content=video06", HTTP_HOST="tryagaintext.com")
            response = self.middleware(request)
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response["Location"], "https://www.tryagaintext.com/pickup-lines/professions/lawyer/?utm_source=instagram&utm_content=video06")

    def test_canonical_and_local_hosts_do_not_loop(self):
        for host in ("www.tryagaintext.com", "localhost", "testserver"):
            self.assertEqual(self.middleware(self.factory.get("/", HTTP_HOST=host)).status_code, 200)

    def test_api_auth_payments_and_posts_are_not_moved(self):
        for path in ("/api/profile/", "/accounts/login/", "/admin/", "/pricing/", "/conversations/", "/flirtfix?utm_source=website"):
            self.assertEqual(self.middleware(self.factory.get(path, HTTP_HOST="tryagaintext.com")).status_code, 200)
        self.assertEqual(self.middleware(self.factory.post("/", HTTP_HOST="tryagaintext.com")).status_code, 200)

    def test_public_url_cannot_switch_to_another_host(self):
        self.assertEqual(public_url("//elsewhere.example/path"), "https://www.tryagaintext.com/elsewhere.example/path")
