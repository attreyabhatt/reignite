from django.test import TestCase


PLAY_STORE_INSTAGRAM_URL = (
    "https://play.google.com/store/apps/details?id=com.tryagaintext.flirtfix"
    "&hl=en_IN&referrer=utm_source%3Dinstagram%26utm_medium%3Dbio"
    "%26utm_campaign%3Dflirtfix_instagram_bio"
)


class FlirtfixRedirectTests(TestCase):
    def test_flirtfix_redirect_without_trailing_slash(self):
        response = self.client.get("/flirtfix")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], PLAY_STORE_INSTAGRAM_URL)

    def test_flirtfix_redirect_with_trailing_slash(self):
        response = self.client.get("/flirtfix/")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], PLAY_STORE_INSTAGRAM_URL)

    def test_flirtfix_extra_path_is_not_matched(self):
        response = self.client.get("/flirtfix/extra")
        self.assertEqual(response.status_code, 404)
