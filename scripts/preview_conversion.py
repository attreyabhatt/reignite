"""Run a disposable local preview: SQLite, fixed AI replies, no external checkout.

    venv/Scripts/python.exe scripts/preview_conversion.py

Only listens on loopback. Never uses or modifies the hosted database.
"""
import os
import argparse
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["DJANGO_SETTINGS_MODULE"] = "reignitehome.test_settings"

from django.conf import settings

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--database", type=Path, help="Reuse a previous local preview SQLite file")
args = parser.parse_args()
preview_db = args.database or Path(tempfile.mkdtemp(prefix="tryagaintext-preview-")) / "preview.sqlite3"
settings.DATABASES["default"]["NAME"] = str(preview_db)
settings.TEMPLATES[0]["APP_DIRS"] = False
settings.TEMPLATES[0]["OPTIONS"]["loaders"] = [
    "django.template.loaders.filesystem.Loader", "django.template.loaders.app_directories.Loader"]

import django
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.shortcuts import redirect
from conversation.models import WebAppConfig
from conversation.test_web_conversion import REPLIES

call_command("migrate", interactive=False, verbosity=0)
call_command("seed_pickup_data", verbosity=0)
cfg = WebAppConfig.load()
cfg.guest_reply_limit = cfg.signup_bonus_credits = 3
cfg.save()
if not User.objects.filter(username="preview").exists():
    admin = User.objects.create_superuser("preview", "preview@example.com", "PreviewOnly123!")
    admin.chat_credit.balance = 3
    admin.chat_credit.save()

# Preview-only route for checking the server-rendered Android layout on desktop.
from django.urls import path
from reignitehome.urls import urlpatterns
from reignitehome.views import home

def android_preview(request):
    request.META["HTTP_SEC_CH_UA_PLATFORM"] = '"Android"'
    return home(request)

urlpatterns.insert(0, path("__preview__/android/", android_preview, name="home"))

real_redirect = redirect
def local_checkout(destination, *args, **kwargs):
    if isinstance(destination, str) and "checkout.dodopayments.com" in destination:
        return real_redirect("/conversations/?preview_checkout=1")
    return real_redirect(destination, *args, **kwargs)

print(f"Disposable preview database: {settings.DATABASES['default']['NAME']}", flush=True)
print("Preview: http://127.0.0.1:8000/ | Admin: preview / PreviewOnly123!", flush=True)
with patch("conversation.views.generate_web_response", return_value=(REPLIES, True)), \
     patch("reignitehome.views.generate_reignite_comeback", return_value=(REPLIES, True)), \
     patch("conversation.views.extract_conversation_from_image_web", return_value="You: Coffee?\nHer: Yes!"), \
     patch("pricing.views.redirect", side_effect=local_checkout):
    call_command("runserver", "127.0.0.1:8000", use_reloader=False)
