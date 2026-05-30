"""
Base Django settings — shared by every environment.

dev.py and prod.py import everything from this file and override only what
differs between environments (database, DEBUG, allowed hosts, CORS origins).
See docs/plan/03-conventions.md for why the settings are split this way.
"""

import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

# Points at the backend/ directory. This file is backend/config/settings/base.py,
# so the project root is three levels up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load backend/.env (if present) so local secrets — Stripe keys, etc. — are
# available via os.environ. Real environment variables still take precedence.
load_dotenv(BASE_DIR / ".env")

# A real, secret value must be provided via the environment in production.
# The insecure fallback is acceptable for local development only.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-w!x=b2ju9*zc!zvw^^bicronohl+u#c2m=-7s!)x4z#fn9#3xc",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "anymail",
    # Project apps
    "apps.core",
    "apps.store",
    "apps.accounts",
    "apps.orders",
]

# DRF: authenticate via Django sessions (same mechanism as the admin). Endpoints
# are public by default; views opt into auth with permission_classes.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware must sit as high as possible, and before CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS/JS Django serves itself — mostly for the admin).
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Uploaded media — product images. Defaults to a local folder for development;
# in production DJANGO_MEDIA_ROOT points at a persistent disk (a DigitalOcean
# Volume mount) so images survive droplet rebuilds.
# See docs/plan/01-architecture.md, "Media / image storage".
MEDIA_URL = "media/"
MEDIA_ROOT = os.environ.get("DJANGO_MEDIA_ROOT") or (BASE_DIR / "media")

# --- Stripe ---
# Secrets come from the environment; the secret key never reaches the frontend.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Where Stripe's hosted checkout returns the customer (frontend URLs).
CHECKOUT_SUCCESS_URL = os.environ.get(
    "CHECKOUT_SUCCESS_URL", "http://localhost:5173/?checkout=success"
)
CHECKOUT_CANCEL_URL = os.environ.get(
    "CHECKOUT_CANCEL_URL", "http://localhost:5173/?checkout=cancel"
)

# --- Shipping ---
# A single flat shipping fee (in dollars) added at checkout. The merch is all
# light (shirts, stickers, CDs), so one rate keeps it simple instead of
# weighing packages. We ship to the US only for now.
SHIPPING_FLAT_RATE = Decimal(os.environ.get("SHIPPING_FLAT_RATE", "5.00"))
SHIPPING_ALLOWED_COUNTRIES = ["US"]

# --- Email ---
# A Resend API key (EMAIL_API_KEY) enables real sending via django-anymail.
# Without one, dev falls back to the console backend so the flow stays testable.
EMAIL_API_KEY = os.environ.get("EMAIL_API_KEY", "")
BAND_NOTIFICATION_EMAIL = os.environ.get("BAND_NOTIFICATION_EMAIL", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Cemented <orders@cemented.band>")

if EMAIL_API_KEY:
    EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
    ANYMAIL = {"RESEND_API_KEY": EMAIL_API_KEY}
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
