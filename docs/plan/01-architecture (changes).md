# Proposed changes to 01-architecture.md

> This file collects proposed additions to `01-architecture.md` for review.
> Nothing here is merged into the original yet.

## Addition — new "Media / image storage" section

Insert between the "Data model" section and "## What v1 explicitly does NOT have":

---

## Media / image storage

Product images are uploaded by the band through the Django admin. *Where* those
uploaded files physically live is a deploy-time decision, deliberately deferred
to keep v1 development simple:

- **During development (now):** Django's built-in file storage — an `ImageField`
  writing to a local `backend/media/` directory (gitignored). Zero extra
  dependencies, zero third-party accounts. This is enough to learn the whole
  flow: uploading through the admin, the `ImageField`, `MEDIA_ROOT`/`MEDIA_URL`,
  and serving images in development.
- **Before the first real deploy (later):** Railway/Render container
  filesystems are ephemeral — locally uploaded files are wiped on every
  redeploy. The storage backend must move to an object store. Cloudinary is the
  planned choice: a generous free tier, and `django-cloudinary-storage` swaps in
  with minimal configuration. This becomes its own small feature file at deploy
  time.

Because Django's storage backend is pluggable, application code barely changes
between the two — `ImageField` usage stays identical; only settings change.
