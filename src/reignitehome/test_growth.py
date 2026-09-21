from datetime import timedelta
from io import StringIO
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from mobileapi.models import MobileCopyEvent, MobileGenerationEvent, MobileInstallAttributionEvent
from mobileapi.views import _persist_mobile_copy_event, _persist_mobile_generation_event
from reignitehome.growth import growth_funnel
from reignitehome.models import MarketingClickEvent


@override_settings(SECURE_SSL_REDIRECT=False)
class GrowthFunnelTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.click_at = self.now - timedelta(days=16)
        self.install_at = self.click_at + timedelta(hours=1)
        self.click = self.create_at(MarketingClickEvent, self.click_at,
            route_key="flirtfix", utm_source="website", utm_campaign="flirtfix_web_pickup_lines",
            utm_content="inline_card", utm_term="/pickup-lines/professions/lawyer/",
            target_url="https://play.google.com/store/apps/details?id=com.tryagaintext.flirtfix")

    def create_at(self, model, when, **fields):
        obj = model.objects.create(**fields)
        model.objects.filter(pk=obj.pk).update(created_at=when)
        obj.refresh_from_db()
        return obj

    def install(self, **overrides):
        fields = dict(click_event=self.click, guest_id_hash="device-a", idempotency_key="install-a")
        fields.update(overrides)
        return self.create_at(MobileInstallAttributionEvent, self.install_at, **fields)

    def generate(self, when=None, **overrides):
        fields = dict(guest_id_hash="device-a", user_type="free", action_type="reply", source_type="ai",
                      model_used="test", generated_json='{"reply":"fixture"}')
        fields.update(overrides)
        return self.create_at(MobileGenerationEvent, when or self.install_at + timedelta(minutes=2), **fields)

    def copy(self, when=None, **overrides):
        fields = dict(guest_id_hash="device-a", user_type="free", copy_type="reply", copied_text="fixture")
        fields.update(overrides)
        return self.create_at(MobileCopyEvent, when or self.install_at + timedelta(minutes=3), **fields)

    def test_duplicate_install_reports_and_actions_count_one_conversion(self):
        self.install()
        self.install(idempotency_key="install-reported-again")
        self.generate()
        self.generate(action_type="opener")
        self.copy()
        report = growth_funnel(now=self.now)
        self.assertEqual(report["totals"], {"clicks": 1, "installed": 1, "activated": 1, "copied": 1,
                                           "mature": 1, "install_rate": 100.0, "activation_rate": 100.0})
        for group in ("page", "placement"):
            self.assertEqual(growth_funnel(now=self.now, group=group)["totals"], report["totals"])

    def test_ocr_static_suggestions_other_devices_and_outside_window_do_not_activate(self):
        self.install()
        self.generate(action_type="ocr")
        self.generate(action_type="opener", source_type="recommended_static")
        self.generate(guest_id_hash="another-device")
        self.generate(when=self.install_at - timedelta(seconds=1))
        self.generate(when=self.install_at + timedelta(days=8))
        self.copy(when=self.install_at + timedelta(days=8))
        self.assertEqual(growth_funnel(now=self.now)["totals"]["activated"], 0)

    def test_copy_alone_is_use_and_missing_actor_never_matches_another_missing_actor(self):
        self.install(guest_id_hash=None)
        self.generate(guest_id_hash=None)
        self.copy(guest_id_hash=None)
        self.assertEqual(growth_funnel(now=self.now)["totals"]["activated"], 0)
        self.install(idempotency_key="identified-install")
        self.copy()
        self.assertEqual(growth_funnel(now=self.now)["totals"]["activated"], 1)

    def test_late_unlinked_and_out_of_period_installs_do_not_inflate_cohort(self):
        self.install_at = self.click_at + timedelta(days=8)
        self.install()
        self.install(click_event=None, idempotency_key="organic")
        self.generate()
        self.assertEqual(growth_funnel(now=self.now)["totals"]["installed"], 0)
        self.assertEqual(growth_funnel(now=self.now, days=7)["totals"]["clicks"], 0)

    def test_signed_in_actions_keep_device_hash_and_match_guest_install(self):
        self.install()
        user = User.objects.create_user(username="converted")
        request = SimpleNamespace(user=user)
        with patch("mobileapi.views._get_guest_hash_for_mobile_analytics", return_value="device-a"):
            generation = _persist_mobile_generation_event(request=request, chat_credit=None, action_type="reply",
                source_type="ai", generated_payload={"reply": "fixture"}, model_used="test", thinking_used="none", usage={})
            copy = _persist_mobile_copy_event(request=request, chat_credit=None, copy_type="reply", copied_text="fixture")
        self.assertEqual(generation.guest_id_hash, "device-a")
        self.assertEqual(copy.guest_id_hash, "device-a")
        self.assertEqual(generation.user_id, user.pk)
        MobileGenerationEvent.objects.filter(pk=generation.pk).update(created_at=self.install_at + timedelta(hours=1))
        MobileCopyEvent.objects.filter(pk=copy.pk).update(created_at=self.install_at + timedelta(hours=2))
        self.assertEqual(growth_funnel(now=self.now)["totals"]["activated"], 1)

    def test_admin_report_requires_model_permission_and_valid_filters(self):
        url = reverse("admin:reignitehome_marketingclickevent_funnel")
        self.assertEqual(self.client.get(url).status_code, 302)
        staff = User.objects.create_user(username="report-reader", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename="view_marketingclickevent"))
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url, {"days": "not-a-number"}).status_code, 400)

    def test_json_report_contains_aggregate_counts_without_chat_or_actor_ids(self):
        self.install()
        self.generate()
        output = StringIO()
        call_command("growth_report", stdout=output)
        self.assertEqual(json.loads(output.getvalue())["totals"]["installed"], 1)
        self.assertNotIn("device-a", output.getvalue())
        self.assertNotIn("fixture", output.getvalue())
