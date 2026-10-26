from django.test import SimpleTestCase, override_settings


@override_settings(ALLOWED_HOSTS=["tryagaintext.com", "www.tryagaintext.com", "testserver"])
class AndroidAppLinksTests(SimpleTestCase):
    def test_verification_is_public_json_on_both_hosts_without_redirects(self):
        for host in ("tryagaintext.com", "www.tryagaintext.com"):
            with self.subTest(host=host):
                response = self.client.get("/.well-known/assetlinks.json", secure=True, HTTP_HOST=host)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "application/json")
                self.assertNotIn("Location", response)
                self.assertIn("public", response["Cache-Control"])
                self.assertNotIn("Cookie", response.get("Vary", ""))
                self.assertEqual(response.json(), [{
                    "relation": ["delegate_permission/common.handle_all_urls"],
                    "target": {
                        "namespace": "android_app",
                        "package_name": "com.tryagaintext.flirtfix",
                        "sha256_cert_fingerprints": [
                            "7C:CF:42:5B:FD:40:FC:15:10:64:A1:4B:09:F8:FA:55:DE:3F:8D:D8:78:C0:60:81:67:F8:C1:FF:0A:89:F5:40",
                        ],
                    },
                }])

    def test_head_can_verify_but_mutations_are_not_supported(self):
        response = self.client.head("/.well-known/assetlinks.json", secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        for method in (self.client.post, self.client.put, self.client.delete):
            self.assertEqual(method("/.well-known/assetlinks.json", secure=True).status_code, 405)
