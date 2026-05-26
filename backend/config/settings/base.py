"""
Base Django settings — shared by every environment.

dev.py and prod.py import everything from this file and override only what
differs between environments (database, DEBUG, allowed hosts, CORS origins).
See docs/plan/03-conventions.md for why the settings are split this way.
"""

import os
from pathlib import Path

# Points at the backend/ directory. This file is backend/config/settings/base.py,
# so the project root is three levels up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

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

# Uploaded media — product images land here during development.
# See docs/plan/01-architecture.md, "Media / image storage".
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
