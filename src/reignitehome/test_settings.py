"""Explicit isolated settings for tests and local previews, never the hosted DB."""
import os

# Override before importing settings so .env cannot select production services.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DJANGO_SECRET_KEY"] = "isolated-local-tests-only"
os.environ["DJANGO_DEBUG"] = "True"

from .settings import *  # noqa: E402,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
WEB_ANALYTICS_ENABLED = False
