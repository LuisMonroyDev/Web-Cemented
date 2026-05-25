"""
Store models — the content the band edits from the Django admin.

These map to the three admin screens in the Figma mockup:
  * Product       — merch items
  * GalleryImage  — homepage gallery photos
  * SiteSettings  — singleton: Spotify embed URL + social links

Uploaded images are normalized on save (resized + re-encoded). Re-encoding
drops EXIF and discards anything malicious smuggled into an upload, so it
doubles as a security measure.
"""
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image, ImageOps


# --------------------------------------------------------------------------- #
# Image normalization
# --------------------------------------------------------------------------- #
def _process_image(file, *, max_size, quality=85):
    """Resize + re-encode an uploaded image. Returns (ContentFile, extension).

    Shrinks to fit within ``max_size`` (keeping aspect ratio), drops EXIF, and
    re-encodes — which also discards any non-image payload hidden in the file.
    Transparent images stay PNG; everything else becomes optimized JPEG.
    """
    img = Image.open(file)
    img = ImageOps.exif_transpose(img)  # apply camera rotation, then forget it
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    buffer = BytesIO()
    if has_alpha:
        img = img.convert("RGBA")
        img.thumbnail(max_size, Image.LANCZOS)
        img.save(buffer, format="PNG", optimize=True)
        ext = "png"
    else:
        img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        ext = "jpg"
    return ContentFile(buffer.getvalue()), ext


def _normalize(filefield, max_size):
    """Process a freshly uploaded image in place; no-op for already-stored files."""
    if filefield and not filefield._committed:
        content, ext = _process_image(filefield, max_size=max_size)
        filefield.save(f"image.{ext}", content, save=False)


# --------------------------------------------------------------------------- #
# Validators
# --------------------------------------------------------------------------- #
SPOTIFY_EMBED_PREFIX = "https://open.spotify.com/embed/"


def validate_spotify_embed(value):
    """Only allow Spotify *embed* URLs.

    The public site drops this value straight into an <iframe src=...>, so an
    arbitrary URL would be a stored-XSS / open-redirect vector. Allowlisting
    the one safe shape on the server keeps that loop safe.
    """
    if value and not value.startswith(SPOTIFY_EMBED_PREFIX):
        raise ValidationError(
            f"Enter a Spotify embed URL starting with '{SPOTIFY_EMBED_PREFIX}'."
        )


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide this product from the storefront."
    )
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    LOW_STOCK_THRESHOLD = 10

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def status(self):
        """Display status derived from stock — matches the admin mockup."""
        if self.stock == 0:
            return "Sold out"
        if self.stock <= self.LOW_STOCK_THRESHOLD:
            return "Low stock"
        return "Active"

    def save(self, *args, **kwargs):
        _normalize(self.image, max_size=(1200, 1200))
        super().save(*args, **kwargs)


class GalleryImage(models.Model):
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(
        max_length=120, blank=True, help_text="Also used as alt text."
    )
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.caption or f"Photo {self.pk}"

    def save(self, *args, **kwargs):
        _normalize(self.image, max_size=(1600, 1600))
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """Single row of site-wide settings the band can edit."""

    spotify_embed_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[validate_spotify_embed],
        help_text="Spotify embed URL (https://open.spotify.com/embed/...).",
    )
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    spotify_artist_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce a single row
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
