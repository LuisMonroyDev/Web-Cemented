"""
Development settings — used for local work.

manage.py selects this module by default, so `python manage.py runserver`
runs with these settings. No .env file is required: the defaults below are
safe for local development only.
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Local SQLite file — zero setup, ideal for learning. Production swaps this
# for PostgreSQL (see prod.py and docs/plan/01-architecture.md).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# The browser blocks the React app (Vite dev server, port 5173) from calling
# this API unless its origin is explicitly listed here.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
