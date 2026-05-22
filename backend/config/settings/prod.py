"""
Production settings — used by wsgi.py / asgi.py when the app is deployed.

NOTE: this is a stub. It is not exercised yet. The real production
configuration (DATABASE_URL parsing, security headers, static file serving)
is finalized in the deployment feature file. Do not deploy from this as-is.
"""

import os

from .base import *

DEBUG = False

# Comma-separated hostnames, e.g. "api.example.com".
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

# Comma-separated frontend origins allowed to call the API.
CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("FRONTEND_ORIGIN", "").split(",") if o]

# DATABASE_URL is provided by the host (Railway/Render). Parsing it cleanly
# needs a small helper (dj-database-url), added with the deployment feature.
