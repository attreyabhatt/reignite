from urllib.parse import parse_qs, urlparse
from uuid import UUID

from django.test import TestCase

from reignitehome.models import MarketingClickEvent


class FlirtfixRedirectTests(TestCase):
    def _assert_valid_play_redirect(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Cache-Control"], "no-store, no-cache, max-age=0, must-revalidate"
        )
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")

        location = response["Location"]
        parsed_location = urlparse(location)
        self.assertEqual(parsed_location.scheme, "https")
        self.assertEqual(parsed_location.netloc, "play.google.com")
        self.assertEqual(parsed_location.path, "/store/apps/details")

        query = parse_qs(parsed_location.query)
        self.assertEqual(query.get("id", [""])[0], "com.tryagaintext.flirtfix")
        self.assertEqual(query.get("hl", [""])[0], "en_IN")
        self.assertIn("referrer", query)

        referrer_query = parse_qs(query["referrer"][0])
        self.assertIn("ffclid", referrer_query)
        UUID(referrer_query["ffclid"][0])
        return referrer_query

    def test_flirtfix_redirect_tracks_utm_and_click_without_trailing_slash(self):
        response = self.client.get(
            "/flirtfix",
            {
                "utm_source": "Instagram",
                "utm_medium": "Bio",
                "utm_campaign": "Launch_Campaign",
                "utm_content": "reel_1",
            },
            HTTP_REFERER="https://www.instagram.com/some-profile/",
            HTTP_USER_AGENT="test-agent",
            REMOTE_ADDR="203.0.113.10",
        )
        referrer_query = self._assert_valid_play_redirect(response)
        self.assertEqual(referrer_query.get("utm_source", [""])[0], "instagram")
        self.assertEqual(referrer_query.get("utm_medium", [""])[0], "bio")
        self.assertEqual(referrer_query.get("utm_campaign", [""])[0], "launch_campaign")
        self.assertEqual(referrer_query.get("utm_content", [""])[0], "reel_1")

        self.assertEqual(MarketingClickEvent.objects.count(), 1)
        event = MarketingClickEvent.objects.get()
        self.assertEqual(event.route_key, "flirtfix")
        self.assertEqual(event.utm_source, "instagram")
        self.assertEqual(event.utm_medium, "bio")
        self.assertEqual(event.utm_campaign, "launch_campaign")
        self.assertEqual(event.utm_content, "reel_1")
        self.assertEqual(event.referrer_host, "www.instagram.com")
        self.assertEqual(event.user_agent, "test-agent")
        self.assertTrue(event.ip_hash)
        self.assertEqual(event.target_url, response["Location"])
        self.assertEqual(referrer_query["ffclid"][0], str(event.click_id))
        self.assertEqual(event.raw_query.get("utm_source"), ["Instagram"])
        self.assertEqual(event.raw_query.get("utm_medium"), ["Bio"])

    def test_flirtfix_redirect_skips_persist_when_all_utm_defaults_are_unknown(self):
        response = self.client.get("/flirtfix/")
        referrer_query = self._assert_valid_play_redirect(response)

        self.assertEqual(referrer_query.get("utm_source", [""])[0], "unknown")
        self.assertEqual(referrer_query.get("utm_medium", [""])[0], "unknown")
        self.assertEqual(referrer_query.get("utm_campaign", [""])[0], "unknown")

        self.assertEqual(MarketingClickEvent.objects.count(), 0)

    def test_flirtfix_extra_path_is_not_matched(self):
        response = self.client.get("/flirtfix/extra")
        self.assertEqual(response.status_code, 404)

    def test_flirtfix_redirect_skips_googlebot_user_agent(self):
        response = self.client.get(
            "/flirtfix",
            {
                "utm_source": "instagram",
                "utm_medium": "bio",
                "utm_campaign": "launch_campaign",
            },
            HTTP_USER_AGENT=(
                "Mozilla/5.0 (compatible; Googlebot/2.1; "
                "+http://www.google.com/bot.html)"
            ),
        )
        self._assert_valid_play_redirect(response)
        self.assertEqual(MarketingClickEvent.objects.count(), 0)

    def test_flirtfix_redirect_skips_google_pagerenderer_user_agent(self):
        response = self.client.get(
            "/flirtfix",
            {
                "utm_source": "instagram",
                "utm_medium": "bio",
                "utm_campaign": "launch_campaign",
            },
            HTTP_USER_AGENT=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36 "
                "Google-PageRenderer Google "
                "(+https://developers.google.com/+/web/snippet/)"
            ),
        )
        self._assert_valid_play_redirect(response)
        self.assertEqual(MarketingClickEvent.objects.count(), 0)

    def test_flirtfix_redirect_skips_social_preview_crawler(self):
        response = self.client.get(
            "/flirtfix",
            {
                "utm_source": "instagram",
                "utm_medium": "bio",
                "utm_campaign": "launch_campaign",
            },
            HTTP_USER_AGENT="facebookexternalhit/1.1",
        )
        self._assert_valid_play_redirect(response)
        self.assertEqual(MarketingClickEvent.objects.count(), 0)

    def test_flirtfix_redirect_skips_when_user_agent_missing(self):
        response = self.client.get(
            "/flirtfix",
            {
                "utm_source": "instagram",
                "utm_medium": "bio",
                "utm_campaign": "launch_campaign",
            },
            HTTP_USER_AGENT="",
        )
        self._assert_valid_play_redirect(response)
        self.assertEqual(MarketingClickEvent.objects.count(), 0)

    def test_flirtfix_head_request_is_not_counted(self):
        response = self.client.head(
            "/flirtfix",
            {
                "utm_source": "instagram",
                "utm_medium": "bio",
                "utm_campaign": "launch_campaign",
            },
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        self._assert_valid_play_redirect(response)
        self.assertEqual(MarketingClickEvent.objects.count(), 0)
