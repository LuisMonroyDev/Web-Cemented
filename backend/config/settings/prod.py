"""
Production settings — used by wsgi.py / asgi.py when the app is deployed.

Selected by setting DJANGO_SETTINGS_MODULE=config.settings.prod on the server.
Everything secret or environment-specific comes from environment variables
(see .env.example); nothing sensitive is hard-coded here.
"""

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

# Refuse to boot with the insecure development key. This guarantees a real
# DJANGO_SECRET_KEY is set on the server before the site can serve traffic.
if not os.environ.get("DJANGO_SECRET_KEY"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set in production. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    )

# Comma-separated hostnames/IPs the site answers to, e.g. "cemented.band,123.45.67.89".
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

# --- Database ---
# DATABASE_URL is a single connection string, e.g.
# postgresql://user:password@localhost:5432/cemented. dj-database-url parses it
# into the dict Django expects. conn_max_age keeps connections open for reuse.
DATABASES = {
    "default": dj_database_url.config(conn_max_age=600),
}
if not DATABASES["default"]:
    raise ImproperlyConfigured("DATABASE_URL must be set in production.")

# --- CORS / CSRF for the React SPA ---
# Comma-separated frontend origin(s) allowed to call the API, e.g.
# "https://cemented.band". Session auth from the SPA needs credentialed CORS
# plus the origin trusted for CSRF on write requests.
CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("FRONTEND_ORIGIN", "").split(",") if o]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# --- HTTPS / security headers ---
# Nginx terminates TLS and forwards to Gunicorn over plain HTTP, setting the
# X-Forwarded-Proto header. This tells Django to trust that header so it knows
# the original request was HTTPS (without it, SECURE_SSL_REDIRECT loops forever).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Send users to HTTPS, and only send session/CSRF cookies over HTTPS.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS: tell browsers to use HTTPS for this site for the next year. Start small
# (e.g. 3600) when first enabling, then raise once you've confirmed HTTPS works.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
